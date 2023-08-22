FROM python:3.9
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /code:$PYTHONPATH

RUN mkdir /code
RUN mkdir /config

# Install dependencies
RUN apt-get update && apt-get install -y inkscape && apt-get clean
COPY /config/requirements.txt /config/
RUN pip install --no-cache-dir -r /config/requirements.txt

# Copy code
WORKDIR /code
COPY . /code/

# Set working dir
WORKDIR /code/website

# Patch SSL config so we can work with AFIP (see the following issue 
# for more info: https://github.com/PyAr/asoc_members/issues/133 )
RUN sed -i 's/CipherString = DEFAULT@SECLEVEL=2/CipherString = DEFAULT@SECLEVEL=1/' /etc/ssl/openssl.cnf

# Bring pyafipws branch and install it's dependencies
RUN wget https://github.com/PyAr/pyafipws/archive/main.zip && unzip main.zip && mv pyafipws-main pyafipws
RUN pip install --no-cache-dir -r /code/website/pyafipws/requirements.txt
