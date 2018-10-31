FROM ubuntu:18.04

# Install system tools
RUN apt-get update && apt-get -y    install wget git \
                                    cmake python3 python3-dev libboost-all-dev \
                                    libbz2-dev python3-pip libzmq3-dev python3-pyqt5
RUN pip3 install PyYAML Pyro4 parse click ipython pyzmq packaging matplotlib numpy

# Install Rogue
ARG branch
WORKDIR /usr/src
RUN git clone https://github.com/slaclab/rogue.git -b pre-release
WORKDIR rogue
RUN mkdir build
WORKDIR build
RUN cmake .. -DROGUE_INSTALL=system
RUN make install
