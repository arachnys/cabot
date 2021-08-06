FROM python:3.6-alpine AS builder-image

RUN  apk update && apk add --no-cache \
        postgresql-dev \
        mariadb-dev \
        py-pip \
        postgresql-dev \
        mariadb-dev \
        gcc \
        curl \
        curl-dev \
        libcurl \
        musl-dev \
        libffi-dev \
        openldap-dev \
        ca-certificates \
        cargo \
        build-base \
        python3-dev \
        musl-dev \
        libevent-dev \
        bash

# create and activate virtual environment
# using final folder name to avoid path issues with packages
RUN python3 -m venv /home/cabot/venv
ENV PATH="/home/cabot/venv/bin:$PATH"


ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip

RUN mkdir /code

WORKDIR /code

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

########################################################
FROM python:3.6-alpine AS runner-image

RUN adduser -S cabot
COPY --from=builder-image /home/cabot/venv /home/cabot/venv

USER cabot
RUN mkdir /home/cabot/code
WORKDIR /home/cabot/code

COPY cabot .
COPY manage.py ./cabot

EXPOSE 8000

# make sure all messages always reach console
ENV PYTHONUNBUFFERED=1

# activate virtual environment
ENV VIRTUAL_ENV=/home/cabot/venv
ENV PATH="/home/cabot/venv/bin:$PATH"

# /dev/shm is mapped to shared memory and should be used for gunicorn heartbeat
# this will improve performance and avoid random freezes
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


#ENTRYPOINT ["./docker-entrypoint.sh"]