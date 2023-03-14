# -*- coding: utf-8 -*-
"""
Created on Sun Mar  5 15:09:37 2023

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
from RpiCluster.SecondaryNodes.RpiBasicSecondaryThread_v3 import RpiBasicSecondaryThread
from RpiCluster.NodeConfig import NodeConfig


def start_secondary():    
    
    global basic_secondary_thread
    global solVec
    global OPT_ON 
    global i
    global beta
    global alpha

    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mastercluster_opal.txt')) # this gives the address of the primary that we want to connect to 
    
    NodeConfig.load(config)
    
    primary_port = config.getint("secondary", "primary_port")
    primary_ip = config.get("secondary", "primary_ip")
    
    # add_file_logger("secondary.log")
    
    # This class creates and runs a basic secondary thread
    basic_secondary_thread = RpiBasicSecondaryThread(primary_ip, primary_port)
    basic_secondary_thread.start()
    basic_secondary_thread.getNbrConnections() 
    # basic_secondary_thread.bindSecondary()  
    solVec = 0
    i = 0
    OPT_ON = 0 
    alpha = 0    
    


def Update(): 
    global basic_secondary_thread
    global OPT_ON
    global alpha
    
    logger.info("here")
    
        
    maxIter = 1; 
    solDim = 1;
    eta_k = 1e-2;
    consensusTol = 1e-2;
    
    Z = np.zeros(solDim)
    X = np.zeros(solDim)
    
    beta = 0.5
    
    for iter in range(maxIter):    
        Z = X;
        for kk in range(500):                
            Z = Z - eta_k*( Z - np.multiply(beta,alpha) ) # gradient step
            
        # logger.info("input sent = " +str(Z))    
        basic_secondary_thread.bindSecondary()  
        X = basic_secondary_thread.epsilonconsUpdate(Z,consensusTol); # Consensus step
        basic_secondary_thread.flag_to_primary(0)
        # logger.info("output received = " +str(X))  
        time.sleep(0.05)
    
    return X


def runOPT():
    global OPT_ON
    global solVec
    
    while threadGo:
        # logger.info(OPT_ON)
        if OPT_ON == 1:  
            solVec = Update()  
            logger.info("New optimal solution =" +str(solVec))   
            # OPT_ON = 0
        # else:
        #     logger.info("waiting for new measurement")
            
def recMeas_from_primary():  
    global basic_secondary_thread
    global alpha
    global OPT_ON
    
    while threadGo:
        message = basic_secondary_thread.connection_handler.get_message() 
        
        if message['type'] == 'latest_parameters':
            # logger.info("msg = " +str(message['payload']))
            if abs(message['payload']) > 0:
                alpha = message['payload']
                OPT_ON = 1
                # if abs(alpha - message['payload']) < 2:
                #     pass
                # else:
                #     alpha = message['payload']
                #     OPT_ON = 1
        # logger.info("my latest function parameter =" + str(alpha))


        
# def recMeas_from_primary():
    
#     global basic_secondary_thread
#     global OPT_ON
#     global i

#     while threadGo:
#         we_got_new_parameters = 0
#         we_got_new_parameters = basic_secondary_thread.receive_latestMsg_from_Primary() 
        

#         if (we_got_new_parameters == 1):
#             # logger.info("received new function parameters starting optimization")
#             OPT_ON = 1
#             # i += 1
#             # if i > 1:
#             #     OPT_ON = 0
#         else:
#             OPT_ON = 0
        
def recStopFlag_from_primary():
    
    global basic_secondary_thread

    while threadGo:
        basic_secondary_thread.receive_stopFlag_from_Primary() 


if __name__ == "__main__": 
    
    initSuccess = start_secondary()
    
    threadGo = True #set to false to quit threads
    # start a new thread to start the optimization algorithm    
    thread1 = Thread(target=runOPT)
    thread1.daemon = True
    thread1.start()
    
    thread2 = Thread(target=recStopFlag_from_primary)
    thread2.daemon = True
    thread2.start()    # Send the optimization result to the primary node
    
    thread3 = Thread(target=recMeas_from_primary)
    thread3.daemon = True
    thread3.start()   # Receive latest measurement from primary node
    
    
    
    ## do infinite while to keep main alive so that logging from threads shows in console
    try:
        while True:
            time.sleep(0.001)
    except KeyboardInterrupt:
        sys.exit()
        logger.info("cleaning up threads and exiting...")
        threadGo = False
        logger.info("done.")
