import socket
import random
import numpy as np
import time
import json
from operator import itemgetter
from threading import Thread
from RpiCluster.MainLogger import logger
from RpiCluster.RpiClusterClient import RpiClusterClient
from RpiCluster.ConnectionHandler import ConnectionHandler
# from RpiCluster.RpiInfluxClient import RpiInfluxClient


class RpiPrimary:
    """Class to create a primary node which will handle connections coming in from a secondary

        This will form the basis of a general primary node which will be in charge of listening for connections
        and handling each one.

        Attributes:
            socket_bind_ip: IP address to bind the listening socket server to
            socket_port: Port number to bind the listening socket server to
            connected_clients: Dict of connected clients
    """

    def __init__(self, socket_bind_ip, socket_port, agentConfigFile): #, influxdb_host, influxdb_port, influxdb_database_prefix
        self.socket_bind_ip = socket_bind_ip
        self.socket_port = socket_port

        self.connected_clients = {}
        self.connected_client_addresses = {}
        self.connected_client_sockets = {}

        self.connected_nodeIDs = {}
        
        self.number_of_secondary_nodes = 10
        self.agentConfigFile = agentConfigFile


    def start(self):
        """Set up the primary to handle the various responsibilities"""
        logger.info("Starting primary...")



        # Start the handling of the secondary nodes
        listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening_socket.bind((self.socket_bind_ip, self.socket_port))

        
        listening_socket.listen(self.number_of_secondary_nodes)  # listen to "self.number_of_secondary_nodes" secondary node-connects

        ii = 0;

        while True:
            (clientsocket, address) = listening_socket.accept()
            logger.info("Got client at {address}".format(address=address))
            self.connected_nodeIDs[ii] = ii
            self.connected_client_addresses[ii] = address
            self.connected_client_sockets[ii] = clientsocket
            
            # agentSetup = self.agentConfigFile.get(str(self.connected_nodeIDs[ii]), "function")  # send objective function parameters to the secondary
            
            Thread(target=self.add_new_secondary, args=(ii,clientsocket, address, self.number_of_secondary_nodes)).start()
        
            ii += 1
            
            if (ii == self.number_of_secondary_nodes):
                logger.info("Total secondary nodes connected to me = " +str(ii))
                break
         
        time.sleep(1)    
        self.send_Nbr_info_to_secondary()
        
    
    def add_new_secondary(self, index, clientsocket, address, networkDiam):
        rpi_client = RpiClusterClient(self, clientsocket, address, index, networkDiam) # create a channel for each secondary on your end
        self.connected_clients[rpi_client.nodeID] = rpi_client
        rpi_client.start() 
        logger.info("I connected to a new secondary node with ID", + "rpi_client.nodeID");
    

    def remove_client(self, rpi_client):
        """Removes a given client from the list of connected clients, typically called after disconnection"""
        del self.connected_clients[rpi_client.nodeID]

    
    def send_Nbr_info_to_secondary(self):
        """Allows sending info to every secondary connected to the primary"""
        # logger.info("sending nbr info to secondary nodes")
        for nodeID in self.connected_nodeIDs:
            myNbrslist = self.agentConfigFile.get(str(nodeID), "neighbors")
            # logger.info("nodeID =" + str(nodeID))
            myNbrslist = [int(float(x)) for x in myNbrslist if x not in ['[', ',', ']']]
            # logger.info("myNbrslist = " +str(myNbrslist))
            # logger.info(self.connected_client_addresses)
            NbrAdds = [self.connected_client_addresses[key] for key in myNbrslist]
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            
            NbrInfo = {
                "NbrIDs": myNbrslist,
                "NbrAdds": NbrAdds,
            }
            # logger.info("NbrAdds = " +str(NbrAdds))
            # data = json.dumps({"type": 'NbrInfo', "payload": NbrAdds})
            myconnection_handler.send_message(NbrInfo, "NbrInfo")
            # logger.info("I sent this to the secondary")
        
        logger.info("sent neighbor info to all the secondary nodes")



    def get_secondary_details(self):
        """Allows retrieving some basic information of every secondary connected to the primary"""
        secondary_details = {}
        for nodeID in self.connected_nodeIDs:
            secondary_details[nodeID] = {
                "uuid": nodeID,
                "address": str(self.connected_clients[nodeID].address[0]) + ":" + str(self.connected_clients[nodeID].address[1]),
            }

        return secondary_details
    
    
    def get_sol_from_secondary(self):
        """Allows retrieving the solution of every secondary connected to the primary"""
        secondary_sols = {}
        for nodeID in self.connected_nodeIDs:
            secondary_sols[nodeID] = {
                "nodeID": nodeID,
                "convgFlag": self.connected_clients[nodeID].conv_flag,
                "solution": self.connected_clients[nodeID].sol,
            }

        return secondary_sols

   
    def send_latest_updated_info_secondary(self, latestInfo):
        """Allows sending info to every secondary connected to the primary"""
        
        for nodeID in self.connected_nodeIDs:
            mylatestparameters = latestInfo[nodeID]
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(mylatestparameters, "latest_parameters")            
        # logger.info("updated function parameters sent to all secondaries = " +str(latestInfo))
        
    def send_stop_to_agents(self):
        for nodeID in self.connected_nodeIDs:
            mystopflag = 1.0
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(mystopflag, "stop_flag")        
        logger.info("sent stop communication to all the agents")



        