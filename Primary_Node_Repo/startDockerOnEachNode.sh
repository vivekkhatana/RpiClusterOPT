#!/bin/bash
#for x in 37 35 34 33 32 31 30 29 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 5 4 3 2 1 
#for x in 37 30
#for x in $1
for x in $(seq 1 47 )
do
ip=$((201+$x))
echo "Running docker on 10.79.118.${ip}"
sed -i '$ d' test.sh
sed -i '$ d' test.sh
echo "ssh picocluster@10.79.118.$ip 'uname -n && sudo docker run -p 3000:3000 salapakalab/dftc_consensus:physicalDevice && exit'" >> test.sh
echo "exit" >> test.sh
sleep 0.5
xterm -e bash -c './test.sh' &
#ssh picocluster@10.79.118.$ip 'uname -n'
done
