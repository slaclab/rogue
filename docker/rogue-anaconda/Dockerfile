FROM continuumio/anaconda3

RUN apt-get update && \
    apt-get install -y \
      g++ \
      gcc \
      git \
      cmake \
      make

RUN conda config --set channel_priority strict &&\
    conda install -n base conda-libmamba-solver &&\
    conda config --set solver libmamba

RUN conda create -n rogue_tag -c tidair-tag -c conda-forge rogue

RUN echo "source activate rogue_tag" > ~/.bashrc

ENV PATH /opt/conda/envs/rogue_tag/bin:$PATH
