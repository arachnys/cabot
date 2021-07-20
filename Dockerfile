FROM python:3.6.5-jessie

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
                    default-libmysqlclient-dev \
                    build-essential \
                    python3-dev \
                    python2.7-dev \
                    libldap2-dev \
                    libsasl2-dev \
                    slapd \
                    ldap-utils \
                    python-tox \
                    lcov \
                    valgrind\
                    curl\
                    python-dev \
                    gcc \
                    musl-dev \
                    libffi-dev \
                    ca-certificates \
                    bash

ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip

RUN mkdir /code

WORKDIR /code

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY requirements-plugins.txt ./
RUN pip install --no-cache-dir -r requirements-plugins.txt

ADD . /code/



ENTRYPOINT ["./docker-entrypoint.sh"]