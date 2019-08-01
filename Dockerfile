FROM python:3.6
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /code:$PYTHONPATH

RUN mkdir /code
RUN mkdir /config

# Install dependencies
RUN apt-get update && apt-get install -y inkscape && apt-get clean
COPY /config/requirements.txt /config/
RUN pip install --no-cache-dir -r /config/requirements.txt
# Workaround to use pyafipws in python3 (first instally m2crypto pinned to the version that actually builds)
RUN pip install m2crypto==0.33.0

# Copy code
WORKDIR /code
COPY . /code/

# Set working dir
WORKDIR /code/website

# Bring pyafipws branch and install it's dependencies
RUN wget https://github.com/PyAr/pyafipws/archive/py3k.zip && unzip py3k.zip && mv pyafipws-py3k pyafipws
RUN pip install --no-cache-dir -r /code/website/pyafipws/requirements.txt

# Django preparation work
RUN python manage.py collectstatic --noinput 
RUN python manage.py migrate
