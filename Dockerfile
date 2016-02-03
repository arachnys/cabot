FROM python:2.7
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
ADD . /code/
RUN apt-get update && \
  apt-get install -y \
    python-dev \
    libsasl2-dev \
    libldap2-dev \
    libpq-dev \
    npm
RUN npm install -g coffee-script less@1.3 --registry http://registry.npmjs.org/
RUN [ ! -f /usr/bin/node ] && ln -s /usr/bin/nodejs /usr/bin/node
RUN python setup.py install