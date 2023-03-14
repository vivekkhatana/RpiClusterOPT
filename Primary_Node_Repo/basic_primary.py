# !/usr/bin/env python3

import os
import numpy as np
import struct
import socket
import sys
import time
import re
from threading import Thread
import configparser
from RpiCluster.MainLogger import logger
from RpiCluster.MainLogger import add_file_logger
from RpiCluster.PrimaryNodes.RpiPrimary import RpiPrimary
from RpiCluster.NodeConfig import NodeConfig



def start_primary():
    
    global dispatch_matrix
    global listen_latestInfo_port
    global listen_latestInfo_ip
    global opal_ip
    global opal_port
    global primary
    global NumNodes
    global Estar
    global prevAdj
    global droopCoeff
    global measVec

    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mastercluster_v2.txt'))
    
    NodeConfig.load(config)
    
    agentConfigFile = configparser.ConfigParser()
    agentConfigFile.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'agentConfig_5nodes.txt'))
    
    
    socket_bind_ip = config.get("primary", "socket_bind_ip")
    socket_port = config.getint("primary", "socket_port")

    listen_latestInfo_ip = config.get("primary", "listen_opal_ip")
    listen_latestInfo_port = config.getint("primary", "listen_opal_port")
   
    opal_ip = config.get("opalrt", "opal_ip")
    opal_port = config.getint("opalrt", "opal_port")
    
    
    add_file_logger("primary.log")
    
    # The RpiPrimary class handles all of the interesting bits of work that the primary performs
    primary = RpiPrimary(socket_bind_ip, socket_port, agentConfigFile) # socket_bind_ip and socket_port give the primary node address
                                                                       # and agentConfigFile sent to the secondary to make its neighbor connections
    
    # start the primary node and send the secondary nodes their configuration and neighbor information
    primary.start()
    primary.send_Nbr_info_to_secondary()
    
    solDim = 1;
    NumNodes = primary.number_of_secondary_nodes;
    dispatch_matrix = np.zeros(NumNodes);
    Estar = 240*np.sqrt(2)*np.ones(NumNodes);
    MeasVeclen = NumNodes
    measVec = np.zeros(MeasVeclen);
    prevAdj = np.zeros(NumNodes);
    # droop coeff of the generators
    droopCoeff = 2e-4*np.ones(NumNodes);



def send_dispatch_to_OPAL(outVec):
    
    global opal_ip
    global opal_port
    
    #send via UDP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Use UDP sockets
    p = len(outVec) #determine how many floats we are sending\n",
    msgBytes = struct.pack('<{}'.format('f'*p),*outVec.tolist()) #bytepack numpy row vector - use little Endian format (required by Opal-RT)\n",
    REMOTE_HOST_ADDR = (opal_ip, opal_port)
    s.sendto(msgBytes, REMOTE_HOST_ADDR)
    logger.info("sent UDP packets to OPAL =" +str(outVec))


def get_updates_from_secondary():  
    
    global dispatch_matrix
    global primary
    global NumNodes
    global prevAdj
    global measVec    
    
    logger.info("dispatch send to OPAL")
    
    while threadGo:    
        
        inputVec = measVec
        
        dispatch_json = primary.get_sol_from_secondary()    
        for k in range(NumNodes):
            dummy = dispatch_json[k]
            node = dummy['nodeID']
            if np.isnan(dispatch_matrix[node]):
                dispatch_matrix[node] = 0  
            else:        
                dum = str(dummy['solution'])
                dum = dum.strip('.]').strip('.[')
                dum = float(dum)
                # dispatch_matrix[node] = (dum - inputVec[node]);
                dispatch_matrix[node] = dum 
        
        average = np.sum(dispatch_matrix)/NumNodes;
                
        for k in range(NumNodes):  
            dispatch_matrix[node] = (average - inputVec[node]);
                            
        prevAdj = dispatch_matrix;
        
        send_dispatch_to_OPAL(dispatch_matrix)
        time.sleep(5)
        
    
    
def receive_meas_OPAL():
    """
    Listen for measurements provided by the real-time simulated power system model
    Upon receipt of a measurement, send the latest info to the secondary nodes 
    """    
    global listen_latestInfo_port
    global listen_latestInfo_ip
    global primary
    global NumNodes
    global prevAdj
    global measVec
    global measurement_reception_started
       
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Use UDP sockets
    LOCAL_UDP_ADDR = (listen_latestInfo_ip, listen_latestInfo_port)
    s.bind(LOCAL_UDP_ADDR) #IP:Port here is for the computer running this script
    logger.info('Bound to ' + str(LOCAL_UDP_ADDR) + ' and waiting for UDP packet-based measurements')
    
    while threadGo:        
        
        data,addr = s.recvfrom(10000) #buffer size can be smaller if needed, but this works fine
        l = len(data)
        # p = int(l/4) # get number of floats sent: OPAL
        p = int(l/8) # get number of floats sent : Simulink
        
        # vector = np.array(struct.unpack('<{}'.format('f'*p),data)) # For OPAL RT
        vector = np.array(struct.unpack('<{}'.format('d'*p),data)) # For simulink simulations
        
        inputmeasveclen = NumNodes
        
        if len(vector) == inputmeasveclen:   
            measurement_reception_started = 1
            measVec = Estar - vector;
            measVec = np.asarray(measVec)
            # measVec = np.asarray(vector)

        # newVec = measVec - prevAdj
        newVec = measVec
        newVec = np.array(newVec).tolist()
        
        # logger.info("sending new updates to all secondaries= " +str(newVec))
        primary.send_latest_updated_info_secondary(newVec)
        time.sleep(25)
        


# main program begin...
if __name__ == "__main__":
      
    #remove any existing log file that we appended to last time
    try:
        os.remove("primary.log")
    except FileNotFoundError as e:
        pass
    
    initSuccess = start_primary()
    
    threadGo = True #set to false to quit threads
    
    # start a new thread to receive messages from the secondary nodes                
    thread1 = Thread(target=get_updates_from_secondary)
    thread1.daemon = True
    thread1.start()
    
    # start a new thread to receive measurements from OPAL RT                    
    thread2 = Thread(target=receive_meas_OPAL)
    thread2.daemon = True
    thread2.start()
    
    ## do infinite while to keep main alive so that logging from threads shows in console
    try:
        while True:
            time.sleep(0.001)
    except KeyboardInterrupt:
        sys.exit()
        logger.info("cleaning up threads and exiting...")
        threadGo = False
        logger.info("done.")
