FROM python:3.6
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /code:$PYTHONPATH

RUN mkdir /code
WORKDIR /code
COPY . /code/

# During PyCamp only ;-)
RUN mkdir ~/.pip/
RUN echo "[global]\nindex-url=http://10.42.0.82:3141/root/pypi/+simple/\ntrusted-host=10.42.0.82\n" > ~/.pip/pip.conf

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install .
