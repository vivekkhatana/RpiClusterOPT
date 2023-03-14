# -*- coding: utf-8 -*-
"""
Created on Tue Mar  7 12:47:45 2023

@author: khata010
"""

#!/usr/bin/env python3

import os
from threading import Thread
import time
import pandas as pd
import sys
import configparser
import numpy as np
from RpiCluster.MainLogger import add_file_logger
from RpiCluster.MainLogger import logger
from RpiCluster.SecondaryNodes.RpiBasicSecondaryThread_v4 import RpiBasicSecondaryThread
from RpiCluster.NodeConfig import NodeConfig


def start_secondary():    
    
    global basic_secondary_thread
    global solVec
    global OPT_ON 
    global i
    global beta
    global alpha
    global stopFlag

    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mastercluster_opal.txt')) # this gives the address of the primary that we want to connect to 
    
    NodeConfig.load(config)
    
    primary_port = config.getint("secondary", "primary_port")
    primary_ip = config.get("secondary", "primary_ip")
    
    # add_file_logger("secondary.log")
    
    # This class creates and runs a basic secondary thread
    basic_secondary_thread = RpiBasicSecondaryThread(primary_ip, primary_port)
    basic_secondary_thread.start()
    basic_secondary_thread.getNbrInfo() 
    basic_secondary_thread.bindSecondary()             
    solVec = 0
    i = 0
    OPT_ON = 0 
    alpha = 0  
    stopFlag = 1


def runOPT():
    global OPT_ON
    global solVec
    global basic_secondary_thread
    global alpha
    global stopFlag
    
    while threadGo:
        # logger.info(OPT_ON)
        if OPT_ON == 1:  

            if stopFlag == 1:
                
                # logger.info("New optimal solution =" +str(basic_secondary_thread.myRatio))   
                
                maxIter = 1; 
                solDim = 1;
                eta_k = 1e-2;
                
                Z = np.zeros(solDim)
                X = np.zeros(solDim)
                
                # logger.info("latest alpha = " +str(alpha))
                
                beta = 0.5
                
                for iter in range(maxIter):    
                    Z = X;
                    for kk in range(500):                
                        Z = Z - eta_k*( Z - beta*alpha ) # gradient step
                basic_secondary_thread.StartNewCons = 1    
                basic_secondary_thread.newStartConsVal = Z
                stopFlag = 0
                     
def startConsensus():
    
    global basic_secondary_thread
    
    while threadGo:        
        consensusTol = 1e-3;
        basic_secondary_thread.epsilonconsUpdate(consensusTol)
            

def recMeas_from_primary():  
    global basic_secondary_thread
    global alpha
    global OPT_ON
    global stopFlag
    
    while threadGo:
        message = basic_secondary_thread.connection_handler.get_message() 
        
        if message['type'] == 'latest_parameters':
            # logger.info("msg = " +str(message['payload']))
            if abs(message['payload']) > 0:
                alpha = message['payload']
                OPT_ON = 1
        elif message['type'] == 'stop_flag':
            stopFlag = message['payload']  
            # logger.info("stopFlag =" +str(stopFlag))

if __name__ == "__main__": 
    
    initSuccess = start_secondary()
    
    threadGo = True #set to false to quit threads
    # start a new thread to start the optimization algorithm    
    thread1 = Thread(target=runOPT)
    thread1.daemon = True
    thread1.start()
    
    thread2 = Thread(target=recMeas_from_primary)
    thread2.daemon = True
    thread2.start()   # Receive latest measurement from primary node
    
    thread3 = Thread(target=startConsensus)
    thread3.daemon = True
    thread3.start() # start running consensus
    
    
    ## do infinite while to keep main alive so that logging from threads shows in console
    try:
        while True:
            time.sleep(0.001)
    except KeyboardInterrupt:
        sys.exit()
        logger.info("cleaning up threads and exiting...")
        threadGo = False
        logger.info("done.")
