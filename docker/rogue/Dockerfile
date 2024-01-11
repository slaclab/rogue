FROM ubuntu:22.04

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
    python3-pyqt5.qtsvg \
    libreadline6-dev \
 && rm -rf /var/lib/apt/lists/*

# PIP Packages
RUN pip3 install PyYAML parse click ipython pyzmq packaging matplotlib numpy p4p jsonpickle sqlalchemy pyserial
RUN pip3 install pydm>=1.18.0

# Install Rogue
ARG branch=main
WORKDIR /usr/local/src
RUN git clone https://github.com/slaclab/rogue.git -b $branch
WORKDIR rogue
RUN mkdir build
WORKDIR build
RUN cmake .. -DROGUE_INSTALL=system
RUN make -j4 install
RUN echo /usr/local/lib >> /etc/ld.so.conf.d/rogue_epics.conf
RUN ldconfig
ENV PYQTDESIGNERPATH /usr/local/lib/python3.10/dist-packages/pyrogue/pydm
ENV PYDM_DATA_PLUGINS_PATH /usr/local/lib/python3.10/dist-packages/pyrogue/pydm/data_plugins
ENV PYDM_TOOLS_PATH /usr/local/lib/python3.10/dist-packages/pyrogue/pydm/tools
WORKDIR /root
