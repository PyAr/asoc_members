FROM python:3.6
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /code:$PYTHONPATH

RUN mkdir /code
RUN mkdir /config

# Install dependencies
RUN apt-get update && apt-get install -y inkscape && apt-get clean
COPY /config/requirements.txt /config/
RUN pip install --no-cache-dir -r /config/requirements.txt
# Workaround to install pyafipws in python3 (first instally m2crypto pinned to the version that actually builds)
RUN pip install m2crypto==0.33.0
RUN wget https://raw.githubusercontent.com/reingart/pyafipws/master/requirements.txt -O /tmp/req_pyafipws.txt && pip install --no-cache-dir -r /tmp/req_pyafipws.txt
RUN pip install https://github.com/PyAr/pyafipws/archive/py3k.zip

# Copy code
WORKDIR /code
COPY . /code/

WORKDIR /code/website
