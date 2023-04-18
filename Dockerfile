FROM ubuntu:18.04

# Install system tools
RUN apt-get update && apt-get install -y \
    wget \
    git \
    cmake \
    python3 \
    python3-dev \
    libboost-all-dev \
    libbz2-dev \
    python3-pip \
    libzmq3-dev \
    python3-pyqt5 \
    libreadline6-dev \
 && rm -rf /var/lib/apt/lists/*

# PIP Packages
RUN pip3 install PyYAML Pyro4 parse click ipython pyzmq packaging matplotlib numpy p4p pydm jsonpickle sqlalchemy pyserial

# Install Rogue
ARG branch
WORKDIR /usr/local/src
RUN git clone https://github.com/slaclab/rogue.git -b $branch
WORKDIR rogue
RUN mkdir build
WORKDIR build
RUN cmake .. -DROGUE_INSTALL=system
RUN make -j4 install
