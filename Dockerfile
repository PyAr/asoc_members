FROM python:3.14-slim
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /code:$PYTHONPATH

RUN mkdir /code
RUN mkdir /config

# Install dependencies
RUN apt-get update && apt-get install -y inkscape wget wget unzip zlib1g-dev libjpeg-dev libpq-dev gcc && apt-get clean

# Install uv and dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv* /bin/
COPY pyproject.toml /code/
WORKDIR /code
RUN uv pip install --system --no-cache -e .[dev]

# Copy code
WORKDIR /code
COPY . /code/

# Set working dir
WORKDIR /code/website

# Patch SSL config so we can work with AFIP (see the following issue 
# for more info: https://github.com/PyAr/asoc_members/issues/133 )
RUN sed -i 's/CipherString = DEFAULT@SECLEVEL=2/CipherString = DEFAULT@SECLEVEL=1/' /etc/ssl/openssl.cnf

# Bring pyafipws branch and install its dependencies
RUN wget https://github.com/PyAr/pyafipws/archive/main.zip && unzip main.zip && mv pyafipws-main pyafipws
RUN uv pip install --system --no-cache -r /code/website/pyafipws/requirements.txt
