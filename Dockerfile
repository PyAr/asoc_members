FROM python:3.6
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /code:$PYTHONPATH

RUN mkdir /code

# Install dependencies
COPY /config/requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt

# Copy code
WORKDIR /code
COPY . /code/

WORKDIR /code/website
