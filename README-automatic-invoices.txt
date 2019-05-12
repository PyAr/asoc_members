# HOWTO

This is a very manual process, just an experiment to get this working...

# get into the docker
make dockershell

# get the project's py3k branch
git clone https://github.com/reingart/pyafipws.git
cd pyafipws/
git checkout py3k
cd ..

# edit requirements and comment `m2crypto` out
apt install vim
vim pyafipws/requirements.txt

# install m2crypto from Debian's main
apt install python-m2crypto

# install the rest of needed packages from PyPI
pip install -r pyafipws/requirements.txt
