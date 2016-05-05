FROM python:2.7

ENV PYTHONUNBUFFERED 1

RUN mkdir /code

WORKDIR /code

RUN apt-get update && apt-get install -y \
        python-dev \
        libsasl2-dev \
        libldap2-dev \
        libpq-dev \
        npm

RUN npm install -g \
        --registry http://registry.npmjs.org/ \
        coffee-script \
        less@1.3

RUN ln -s `which nodejs` /usr/bin/node

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY requirements-plugins.txt ./requirements-plugins.txt
RUN pip install --no-cache-dir -r requirements-plugins.txt


ADD . /code/
