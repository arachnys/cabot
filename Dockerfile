FROM python:2.7

ENV PYTHONUNBUFFERED 1

RUN mkdir /code

WORKDIR /code

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y \
        apt-utils \
        python-dev \
        libsasl2-dev \
        libldap2-dev \
        libpq-dev \
        npm \ 
        wget

RUN npm install -g \
        --registry http://registry.npmjs.org/ \
        coffee-script \
        less@1.3

RUN ln -s `which nodejs` /usr/bin/node

RUN pip install --upgrade pip

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY requirements-plugins.txt ./
RUN pip install --no-cache-dir -r requirements-plugins.txt

COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

ENV DOCKERIZE_VERSION v0.3.0
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

ADD . /code/

ENTRYPOINT ["./docker-entrypoint.sh"]
