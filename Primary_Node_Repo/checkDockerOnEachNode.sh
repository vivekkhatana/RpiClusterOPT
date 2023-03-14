#!/bin/sh
for x in $(seq 0 47)
do
echo "Checking docker on pc$x"
ssh pc$x "sudo docker images"
done

