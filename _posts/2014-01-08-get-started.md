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

    $ vagrant up
    # start Vagrant and provision the virtual machine using bin/provision

    $ vagrant ssh
    # log in to provisioned Vagrant box

    $ foreman start
    # run webserver and celery tasks using Django dev server

### Running tests

    $ foreman run python manage.py test cabotapp

Test coverage is currently pretty poor so any contributions are welcome.

Tests can be found in `app/cabotapp/tests/`. Currently using `Mock` for mocking out external calls.

### Requirements

*   [Vagrant](http://vagrantup.com)
*   [Virtualbox](https://www.virtualbox.org)

There's nothing to stop you developing locally without Vagrant but don't blame us if you get tangled.
