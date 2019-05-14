### How do I setup? ###

* This project been tested with Ubuntu 16.04 LTS. 
* Install openvswitch 2.3.0 or higher.
* Install mininet version 2.2 by following instructions here: http://mininet.org/download/
* Get RYU version 4.3 from their repo at: http://osrg.github.io/ryu/
* Install Ubuntu Python package dependencies:\
``` sudo apt install python-pip python-scipy python-numpy python-matplotlib ```
* Install pip packages:\
``` sudo pip install sortedcontainers networkx netaddr httplib2 ```
* Setup PYTHONPATH to src folder by adding following line to your ~/.bashrc: \
```export PYTHONPATH=${PYTHONPATH}:/home/flow/flow_validator/src/```
* Allow PYTHONPATH to be retained by sudo by modifying sudoers configuration using visudo and adding the following line: \ 
```Defaults env_keep += "PYTHONPATH"```
* Install bazel version 0.22, here: https://docs.bazel.build/versions/master/install.html

### How do I get going with an example? ###
* Take a look at the simple example of validation in the file: flow_validator/src/experiments/playground.py
* To run cd into flow_validator/src/experiments and run: sudo python playground.py

### Generate the proto files for the python code ###
* pushd flow_validator/src/rpc/
* sudo python -m grpc_tools.protoc -I../../sdnsim/proto --python_out=. --grpc_python_out=. ../../sdnsim/proto/sdnsim.proto
