#!/bin/bash

curl -O https://repo.anaconda.com/archive/Anaconda3-2019.03-MacOSX-x86_64.sh;
bash Anaconda3-2019.03-MacOSX-x86_64.sh -b;

~/anaconda3/bin/conda init bash;
source ~/.bash_profile; # just in case;

conda create --name srRockEnv;

source ~/anaconda3/etc/profile.d/conda.sh;
conda activate srRockEnv;
conda info --envs;


conda install tensorflow=1.12; # for linux
conda install pillow;
conda install -c conda-forge gooey;
pip install tensorlayer==1.11;

conda install ipython; # for debugging;
