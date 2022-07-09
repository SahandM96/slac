from ast import Await
import asyncio
from enum import IntEnum
import logging
from typing import Awaitable
from cp_handler import (
    CPHandler,
    CPStates ,
)

from slac_session import (
    SlacEvseSession,
)

from zmq_handler import (
    CommunicationHandler,
)

from utils import(
    wait_for_tasks,
    cancel_task,
)
from enums import (
    SlacState,
    ProgramState,
)



logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("Low_Level_Handler")


class LowLevelCommHandler :
    def __init__(self) -> None:
        self.slac_handler = SlacEvseSession(iface="enp0s31f6" , evse_id="Pokileda")
        self.cp_handler = CPHandler(self.cp_event)
        self.comm_handler = CommunicationHandler()


        self.buffered_state :CPStates = CPStates.NONE

        self.state : ProgramState = ProgramState.INITIAL_SETUP

        self.slac_state :SlacState = SlacState.STATE_UNMATCHED

        slac_start_task : Awaitable = None

        slac_stop_task : Awaitable = None

        logger.info(f"State Initialized at ProgramState.INITIAL" )


    async def start (self) :
        #First Initializing The Comm and Connect it to controller
        await self.comm_handler.start()
        await self.module_initialization()
        await self.cp_handler.start() ,    
       

    async def cp_event (self,cp_state : CPStates) :
        
        
        logger.info("CP Value Change Changed")
        await self.handle_cp_change(cp_state)
        

    async def module_initialization (self) :
        #The Initial Setup Phase of Program
        self.state = ProgramState.INITIAL_SETUP
        #Reading CP Value for first time
        self.cp_handler.cp_current_state = await self.cp_handler.cp_state_calculator()
        #Getting The CP STATE For Initial State And Write it on Hardware
        cp_write_value = await self.comm_handler.get_cp_write_from_controller()
        await self.cp_handler.write_cp(cp_write_value)
        #informing Controller about the SLAC,CP States
        await self.comm_handler.infrom_controller_cp_state(self.cp_handler.cp_current_state)
        await self.comm_handler.inform_slac_process(SlacState.STATE_UNMATCHED)
        self.buffered_state = self.cp_handler.cp_current_state 
        
        self.state = ProgramState.WORK


    async def handle_cp_change(self,cp_state : CPStates) :
        logger.info("Running CP Change Handle")
        logger.info(f"SLAC :{self.slac_state}")
        
        match self.slac_state :

            case SlacState.STATE_UNMATCHED :
                if self.buffered_state == CPStates.A and cp_state == CPStates.B :
                    self.slac_start_task = asyncio.create_task(self.slac_start_ass_handle())



            case SlacState.STATE_MATCHING :
                print("OPSSSSS")
                await cancel_task(self.slac_start_task)
                await self.slac_stop_ass_handle()
                self.slac_state = SlacState.STATE_UNMATCHED

            case SlacState.STATE_MATCHED :
                if self.buffered_state == CPStates.B and cp_state == CPStates.A :
                    await self.slac_stop_ass_handle()
            

            case SlacState.STATE_UNMACHING :
                pass
        


        

        self.buffered_state = cp_state



    async def slac_start_ass_handle (self) :

        self.slac_state = SlacState.STATE_MATCHING
        await self.comm_handler.inform_slac_process(self.slac_state)
        await self.slac_handler.evse_start_slac_association() 
        self.slac_state = SlacState.STATE_MATCHED
        await self.comm_handler.inform_slac_process(self.slac_state)
        logger.info(">>>Matching Finished<<<")


    async def slac_stop_ass_handle (self) :

        self.slac_state = SlacState.STATE_UNMACHING
        await self.comm_handler.inform_slac_process(self.slac_state)
        await self.slac_handler.evse_stop_slac_association()
        self.slac_state = SlacState.STATE_UNMATCHED
        await self.comm_handler.inform_slac_process(self.slac_state)
        logger.info(">>>Unmaching Finished<<<")



        


            






            

            


                    
                    


                

                
            







    


