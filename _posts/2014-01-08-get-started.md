---
layout: page
title: "Get started"
category: dev
date: 2014-01-08 23:13:30
order: 1
---

### Hack on this repo

    $ git clone git@github.com:arachnys/cabot.git
    $ cd cabot
    $ cp conf/development.env.example conf/development.env
    $ vim conf/development.env
    # Edit settings - add Twilio, Hipchat etc

    $ docker-compose build
    # Build the web and worker services

    $ docker-compose up -d
    # Run webserver and Celery tasks using Django dev server
    # You can access your dev instance at http://localhost:5001/

### Running tests

    $ docker-compose run --rm web python manage.py test -v2

### Requirements

*   [Docker](https://www.docker.com/)
*   [docker-compose](https://docs.docker.com/compose/)

Please refer to the Docker documentation to install it on Mac, Windows or Linux.
