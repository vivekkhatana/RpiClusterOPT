# -*- coding: utf-8 -*-
"""
Created on Tue Mar  7 12:39:17 2023

@author: khata010
"""

import threading
import time
import socket
import json
import numpy as np
from threading import Thread
from RpiCluster.MainLogger import logger
from RpiCluster.ConnectionHandler import ConnectionHandler
from RpiCluster.RpiClusterExceptions import DisconnectionException


class RpiBasicSecondaryThread(threading.Thread):
    """
        Creating children from this base will allow more complex systems to be created. This inherits from thread so
        you are able to start this running and perform other processing at the same time.

        Attributes:
            uuid and myID: A UUID and myID to represent the secondary thread. This is assigned by the primary
            primary_address: A tuple representing the IP address and port to use for the primary
            connection_handler: A connection handler object which will be used for sending/receiving messages.
    """
    def __init__(self, primary_ip, primary_port):
        threading.Thread.__init__(self)
        self.uuid = None
        self.myID = None
        self.NbrAdds = {} # list of out-neighbors' (including myself) addresses 
        self.NbrIDs = {}
                
        self.myNbrSockets = {} 
        self.myNbrAddresses = {}
        
        
        self.primary_address = (primary_ip, primary_port)
        self.connection_handler = None

        # self.my_address = {}
        self.my_listening_ip = None
        self.my_listening_port = None
        
        # self.functionInfo = {} # function parameters of the secondary
        
        self.my_listening_socket = None

        self.IN_neighborNums = []
        self.IN_neighborDens = []
        self.IN_neighborMaxs = []
        self.IN_neighborMins = []
        self.OutBufNums = []
        self.OutBufDens = []
        self.OutBufMaxs = []
        self.OutBufMins = []
        # self.IN_neighborlocalFlags = []
        # self.IN_neighborglobalFlags = []
        
        self.myNum = 0
        self.myDen = 0
        self.myRatio = 0
        self.myMax = 0
        self.myMin = 0
        self.myMXP = 0
        self.myMNP = 0
        self.myflag = 0
        self.StartNewCons = 0     
        self.newStartConsVal = 0
        self.iteration = 0
        self.NbrPastIters = []
        # self.mybitFlag = 0
        # self.Nbrsflag = 0
        # self.global_flag = 0
        # self.conv_flag = 0
        
        
        self.Diam = 10;  # can be passed as an input in a later update

    def start(self):
        """Base method to begin running the thread, this will connect to the primary and then repeatedly call self.result_to_primary"""
        logger.info("Starting script...")

        while True:
            logger.info("Connecting to the primary...")
            connected = False
            while connected is False:
                try:
                    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    connection.connect(self.primary_address)
                    self.my_listening_ip, self.my_listening_port = connection.getsockname()
                    # logger.info(self.my_listening_ip)
                    # logger.info(self.my_listening_port)
                    self.connection_handler = ConnectionHandler(connection)
                    connected = True
                except socket.error as e:
                    logger.info("Failed to connect to primary, waiting 20 seconds and trying again")
                    time.sleep(30)

            logger.info("Successfully connected to the primary")
            

            try:
                logger.info("Sending an initial hello to primary")
                # Getting initial settings
                self.connection_handler.send_message("nodeID", "info")
                message = self.connection_handler.get_message()
                self.myID = message['payload']
                logger.info("My assigned ID is " + str(self.myID))
                
                # self.connection_handler.send_message("funcInfo", "info")
                # message = self.connection_handler.get_message()
                # self.functionInfo = message['payload']
                # logger.info("My function value is ")
                # logger.info(self.functionInfo)                
                break;
                
            except DisconnectionException as e:
                logger.info("Got disconnection exception with message: " + e.message)
                logger.info("Secondary will try and reconnect once primary is back online")



    def getNbrInfo(self):
        
        while True:         
            message = self.connection_handler.get_message()         
            if message['type'] == 'NbrInfo':
                # logger.info("I am here")
                # logger.info(message)
                dummy = message['payload'] # We consider out-neighbors here
                
                self.NbrIDs = dummy['NbrIDs']
                self.NbrAdds = dummy['NbrAdds']
                # logger.info("my Nbr addresses")              
                # logger.info(self.NbrAdds)
                logger.info("my Nbr IDs")              
                logger.info(self.NbrIDs)
                self.NbrPastIters = np.zeros(np.array(self.NbrIDs).max() + 1)
                break
                
                
    def bindSecondary(self):
        self.my_listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_listening_socket.bind((self.my_listening_ip, self.my_listening_port)) 
        self.my_listening_socket.listen(len(self.NbrIDs))
        myaddress = (self.my_listening_ip, self.my_listening_port)
        logger.info("I am bound to {address}".format(address=myaddress))         



    def broadcastMsgto_OUT_Nbrs(self):
                   
        outDeg = len(self.NbrIDs)
        weight = 1/(outDeg + 1)

        # n = np.multiply(self.myNum,weight)
        
        # d = np.multiply(self.myDen,weight) 
        
        n = np.multiply(self.OutBufNums[0],weight)
        
        d = np.multiply(self.OutBufDens[0],weight) 
        
        n = str(n)
        n = n.strip('.]').strip('.[')
        n = float(n)            
        d = str(d)
        d = d.strip('.]').strip('.[')
        d = float(d)

        # myUpdate = json.dumps({"numerator": n, "denominator": d, "max": float(self.myMax), "min": float(self.myMin), "local_flag": float(self.myflag),"global_flag": float(self.Nbrsflag)})  
        # myUpdate = json.dumps({"numerator": n, "denominator": d, "max": float(self.myMax), "min": float(self.myMin), "local_flag": float(self.mybitFlag)})
        myUpdate = json.dumps({"numerator": n, "denominator": d, "max": float(self.OutBufMaxs[0]), "min": float(self.OutBufMins[0]), "iteration": self.iteration, "NbrID": self.myID})
        
        # start making connections with the neighbors                
        self.my_listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_listening_socket.bind((self.my_listening_ip, self.my_listening_port))  
        # logger.info("ready to connect to nbrs")
        self.my_listening_socket.listen(len(self.NbrIDs))  # listen to NbrInfo number of neighbor node-connects
        
        # Sockets to send messages to 
        for Nbr in range(len(self.NbrIDs)):
            with socket.socket() as Nbr_socket:
                try:                    
                    Nbr_address = tuple(self.NbrAdds[Nbr])
                    # logger.info("sent to nbr=" + str(Nbr_address))
                    Nbr_socket.connect(Nbr_address)
                    connection_handler_Nbr = ConnectionHandler(Nbr_socket)  
                    # logger.info("myUpdate =" +str(myUpdate))
                    connection_handler_Nbr.send_message(myUpdate, "myUpdate")                                   
                except socket.error as e:
                    logger.info("Failed to connect to my out Nbr, waiting 1 seconds and trying again")
                    time.sleep(1)       
        
                
        self.OutBufNums =  np.delete(self.OutBufNums,0)
        self.OutBufDens =  np.delete(self.OutBufDens,0)
        self.OutBufMaxs =  np.delete(self.OutBufMaxs,0)
        self.OutBufMins =  np.delete(self.OutBufMins,0)

        
        # logger.info("I sent update to all my out-neighbors")
   
    
    def receiveMsgfrom_IN_Nbrs(self):
        
          
        self.my_listening_socket.listen(len(self.NbrIDs)*100000000)  # listen to NbrInfo number of neighbor node-connects

        
        self.IN_neighborNums = []
        self.IN_neighborDens = []
        self.IN_neighborMaxs = []
        self.IN_neighborMins = [] 
        
        ii = 0
        
        usedNbrs = []
        
        ii = 0
        while True:
            
            connection, address = self.my_listening_socket.accept()
            connection_handler_Nbr = ConnectionHandler(connection) 
            data = connection_handler_Nbr.get_message()      
            if data['type'] == 'myUpdate':   
                dummy = json.loads(data['payload'])  
                if ( np.any(usedNbrs == dummy['NbrID']) ):
                    connection.close()
                else:
                    # logger.info("self.NbrPastIters =" +str(self.NbrPastIters))
                    # logger.info("self.iteration = " +str(self.iteration))
                    # logger.info(data)
                    if np.abs( dummy['iteration'] - self.iteration ) >= 0:
                    # if ( dummy['iteration'] - self.NbrPastIters[dummy['NbrID']] ) > 0:
                        usedNbrs = np.concatenate((np.array(usedNbrs),np.array(dummy['NbrID'])),axis=None)
                        self.NbrPastIters[dummy['NbrID']] = dummy['iteration']
                        self.IN_neighborNums = np.concatenate((np.array(self.IN_neighborNums),np.array(dummy['numerator'])),axis=None)
                        self.IN_neighborDens = np.concatenate((np.array(self.IN_neighborDens),np.array(dummy['denominator'])),axis=None)
                        self.IN_neighborMaxs = np.concatenate((np.array(self.IN_neighborMaxs),np.array(dummy['max'])),axis=None)
                        self.IN_neighborMins = np.concatenate((np.array(self.IN_neighborMins),np.array(dummy['min'])),axis=None)
                        ii += 1;
                    else:
                        connection.close()
            
           
            if (ii == len(self.NbrIDs)):
                break
        
    
    def epsilonconsUpdate(self, consTol):  
        
        
        outDeg = len(self.NbrIDs)
        weight = 1/(outDeg + 1)

        iteration = 0;
        diff = 1000;

        while True: 
            
            if (self.StartNewCons == 1):
                # logger.info("asked to stop at = " + str(self.myRatio))
                self.myNum = self.newStartConsVal
                self.myDen = 1
                self.myRatio = self.myNum
                self.myMax = self.myNum
                self.myMin = self.myNum
                self.myflag = 0
                self.myMXP = 1000
                self.myMNP = 0
                diff = 1000
                self.NbrPastIters = np.zeros(np.array(self.NbrIDs).max() + 1)
                self.flag_to_primary(self.myflag)
                self.iteration = 0
                self.StartNewCons = 0
                
                self.OutBufNums = []
                self.OutBufDens = []
                self.OutBufMaxs = []
                self.OutBufMins = []
                
                        
                self.IN_neighborNums = []
                self.IN_neighborDens = []
                self.IN_neighborMaxs = []
                self.IN_neighborMins = [] 
                
                logger.info("Starting new consensus with the initial value = " +str(self.myNum))
                # self.broadcastMsgto_OUT_Nbrs()
                         
            else:
                
                if (self.myDen == 0):
                    self.iteration = 0
                else:
                    
                    self.iteration += 1; 
                    
                    
                    if self.iteration < 0:
                        self.OutBufNums = np.concatenate((np.array(self.OutBufNums),self.myNum),axis=None)
                        self.OutBufDens = np.concatenate((np.array(self.OutBufDens),self.myDen),axis=None)
                        self.OutBufMaxs = np.concatenate((np.array(self.OutBufMaxs),self.myMax),axis=None)
                        self.OutBufMins = np.concatenate((np.array(self.OutBufMins),self.myMin),axis=None)
                        Thread(target=self.broadcastMsgto_OUT_Nbrs()).start()
                        # # time.sleep(1)    
                        Thread(target=self.receiveMsgfrom_IN_Nbrs()).start()
                        
                    else:                       
                        
                        self.OutBufNums = np.concatenate((np.array(self.OutBufNums),self.myNum),axis=None)
                        self.OutBufDens = np.concatenate((np.array(self.OutBufDens),self.myDen),axis=None)
                        self.OutBufMaxs = np.concatenate((np.array(self.OutBufMaxs),self.myMax),axis=None)
                        self.OutBufMins = np.concatenate((np.array(self.OutBufMins),self.myMin),axis=None)
                        
        
                        Thread(target=self.broadcastMsgto_OUT_Nbrs()).start()
                        # # time.sleep(1)    
                        Thread(target=self.receiveMsgfrom_IN_Nbrs()).start()
            
                        tempNum = np.multiply(self.myNum,weight)
                        tempDen = np.multiply(self.myDen,weight)
                                    
                        self.myNum = tempNum + np.sum(self.IN_neighborNums)
                        self.myDen = tempDen + np.sum(self.IN_neighborDens)
            
                        self.myRatio = np.divide(self.myNum, self.myDen)
                        
                        dummyMax = np.array(self.IN_neighborMaxs)
                        dummyMin = np.array(self.IN_neighborMins)
            
                        self.myMax = np.maximum(self.myMax, dummyMax.max())
                        self.myMin = np.minimum(self.myMin, dummyMin.min())

                            
                        if (np.mod(iteration, self.Diam) == 0):
                            
                            self.myMXP = self.myMax
                            self.myMNP = self.myMin
            
                            diff = np.abs(self.myMXP - self.myMNP)
                            logger.info("my converged value = " + str(self.myRatio) +str(self.myMXP) +str(self.myMNP) + str(diff))
                            
                            # logger.info("diff = " +str(diff))
                            
                            if (diff < consTol):
                                # logger.info("seems like consensus is reached" + str(self.myRatio)) 
                                if (self.myMXP == 0 and self.myMNP == 0):
                                    pass
                                else:
                                    self.myflag = 1
                                
                                # logger.info("my converged value = " + str(self.myRatio))
                                self.result_to_primary(float(self.myRatio))
                                self.flag_to_primary(self.myflag)
                                
                                self.myMax = self.myRatio
                                self.myMin = self.myRatio
            
                            else:                
                                self.myMax = self.myRatio
                                self.myMin = self.myRatio
                        
        
    def result_to_primary(self, converged_value):
        converged_value = json.dumps(converged_value)
        self.connection_handler.send_message(converged_value, "converged_value")

    def flag_to_primary(self, flag):
        flag = json.dumps(flag)
        self.connection_handler.send_message(flag, "flag")
     

