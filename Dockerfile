FROM tidair/rogue-base:v3.0.2

# Install Rogue
ARG branch
WORKDIR /usr/local/src
RUN git clone https://github.com/slaclab/rogue.git -b $branch
WORKDIR rogue
RUN mkdir build
WORKDIR build
RUN cmake .. -DROGUE_INSTALL=system -DDO_EPICS=1
RUN make -j4 install
RUN ldconfig
ENV PYQTDESIGNERPATH /usr/local/lib/python3.10/dist-packages/pyrogue/pydm
ENV PYDM_DATA_PLUGINS_PATH /usr/local/lib/python3.10/dist-packages/pyrogue/pydm/data_plugins
ENV PYDM_TOOLS_PATH /usr/local/lib/python3.10/dist-packages/pyrogue/pydm/tools
WORKDIR /root
