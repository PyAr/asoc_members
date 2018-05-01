FROM python:3.6
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /code:$PYTHONPATH

# During PyCamp only ;-)
RUN mkdir ~/.pip/
RUN echo "[global]\nindex-url=http://10.42.0.82:3141/root/pypi/+simple/\ntrusted-host=10.42.0.82\n" > ~/.pip/pip.conf

RUN mkdir /code
RUN mkdir /config

# Install dependencies
COPY /config/requirements.txt /config/
RUN pip install --no-cache-dir -r /config/requirements.txt

# Copy code
WORKDIR /code
COPY . /code/

VOLUME /code/static
EXPOSE 8000

WORKDIR /code/website
CMD ["tail", "-f", "/dev/null"]
