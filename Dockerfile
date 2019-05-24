FROM python:3.6
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /code:$PYTHONPATH

RUN mkdir /code
RUN mkdir /config

# Install dependencies
COPY /config/requirements.txt /config/
RUN pip install --no-cache-dir -r /config/requirements.txt
# Workaround to install pyafipws in python3.
RUN wget https://raw.githubusercontent.com/reingart/pyafipws/master/requirements.txt -O /tmp/req_pyafipws.txt && pip install --no-cache-dir -r /tmp/req_pyafipws.txt
RUN pip install https://github.com/PyAr/pyafipws/archive/py3k.zip

# Copy code
WORKDIR /code
COPY . /code/

VOLUME /code/static
EXPOSE 8000

WORKDIR /code/website
CMD ["tail", "-f", "/dev/null"]
