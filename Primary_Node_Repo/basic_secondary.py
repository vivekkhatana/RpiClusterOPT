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
from RpiCluster.SecondaryNodes.RpiBasicSecondaryThread import RpiBasicSecondaryThread
from RpiCluster.NodeConfig import NodeConfig


def start_secondary():    
    
    global basic_secondary_thread
    global solVec
    global OPT_ON 
    global i

    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mastercluster_v2.txt')) # this gives the address of the primary that we want to connect to 
    
    NodeConfig.load(config)
    
    primary_port = config.getint("secondary", "primary_port")
    primary_ip = config.get("secondary", "primary_ip")
    
    # add_file_logger("secondary.log")
    
    # This class creates and runs a basic secondary thread
    basic_secondary_thread = RpiBasicSecondaryThread(primary_ip, primary_port)
    basic_secondary_thread.start()
    basic_secondary_thread.getNbrConnections()
    basic_secondary_thread.bindSecondary()   
    solVec = 0
    OPT_ON = 0
    i = 0

def send_to_primary():
    
    global solVec
    global basic_secondary_thread
    global OPT_ON
    
    while threadGo:    
        basic_secondary_thread.result_to_primary(float(solVec))
        
    


def Update(): 
    global basic_secondary_thread
    global OPT_ON
    
    while threadGo:
        
        maxIter = 1; 
        solDim = 1;
        eta_k = 1e-2;
        consensusTol = 0.00001;
        
        Z = np.zeros(solDim)
        X = np.zeros(solDim)
        
        if isinstance(basic_secondary_thread.functionInfo, str):
            alpha_vec = pd.eval(basic_secondary_thread.functionInfo)
            beta = alpha_vec[0]
            alpha = alpha_vec[1]
        else:              
            beta = 0.5
            alpha = basic_secondary_thread.functionInfo
        
        X = basic_secondary_thread.epsilonconsUpdate(alpha,consensusTol);  
        # OPT_ON = 0
        # time.sleep(1)
        
        # logger.info("alpha = " +str(alpha))
        
        # for iter in range(maxIter):    
        #     Z = X;
        #     for kk in range(500):                
        #         Z = Z - eta_k*( Z - np.multiply(beta,alpha) ) # gradient step
                
        #     # logger.info("input sent = " +str(Z))    
            
        #     X = basic_secondary_thread.epsilonconsUpdate(Z,consensusTol); # Consensus step
        #     # logger.info("output received = " +str(X))   
        #     time.sleep(0.005)
        
        return X


def runOPT():
    global OPT_ON
    global solVec
    
    while threadGo:
        # logger.info(OPT_ON)
        if OPT_ON == 1:  
            solVec = Update()  
            # logger.info("New optimal solution =" +str(solVec))   
            # OPT_ON = 0
        # else:
        #     logger.info("waiting for new measurement")
            
        
def recMeas_from_primary():
    
    global basic_secondary_thread
    global OPT_ON
    global i

    while threadGo:
        we_got_new_parameters = 0
        we_got_new_parameters = basic_secondary_thread.receive_latestMsg_from_Primary() 
        

        if (we_got_new_parameters == 1):
            # logger.info("received new function parameters starting optimization")
            OPT_ON = 1
            i += 1
            if i > 1:
                OPT_ON = 0
        else:
            OPT_ON = 0
        
    
    

if __name__ == "__main__": 
    
    initSuccess = start_secondary()
    
    threadGo = True #set to false to quit threads
    # start a new thread to start the optimization algorithm    
    thread1 = Thread(target=runOPT)
    thread1.daemon = True
    thread1.start()
    
    thread2 = Thread(target=send_to_primary)
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
