# Pull Python Base Image
FROM arm32v7/python:3


# Copy the folder containg codes for the secondary node
COPY Secondary_Node_Repo .



# Install dependencies
RUN apt-get update && apt-get install -y \
	openssh-server sshpass \
    python \
    python-dev \
    python-pip 

RUN apt-get update

# Define default command
CMD ["python", "./secondary_node_v2.py"]
