---
layout: page
title: "Get started"
category: dev
date: 2014-01-08 23:13:30
order: 1
---

### Hack on this repo

    $ git clone git@github.com:arachnys/cabot.git
    # Clone repo
    $ cd cabot
    $ cp conf/development.env.example conf/development.env
    # Create settings template copy
    $ vim conf/development.env
    # Edit settings - add Twilio, Hipchat etc

    $ docker-compose build
    # Build the web and worker services
    $ docker-compose run --rm web bash bin/build-app
    # Prepare the application: create DB tables, apply migrations, collect assets
    $ docker-compose run --rm web python manage.py createsuperuser
    # Create the first user (as a super-user)

    $ docker-compose up -d
    # Run webserver and Celery tasks using Django dev server
    # You can access your dev instance at http://localhost:5001/

### Running tests

    $ docker-compose run --rm web python manage.py test cabot

Test coverage is currently pretty poor so any contributions are welcome.

Tests can be found in `cabot/cabotapp/tests/`. Currently using `Mock` for mocking out external calls.

### Requirements

*   [Docker](https://www.docker.com/)
*   [docker-compose](https://docs.docker.com/compose/)

Please refer to the Docker documentation to install it on Mac, Windows or Linux.
