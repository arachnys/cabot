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
    
    $ foreman run python manage.py syncdb --migrate
    # Create DB tables and apply migrations
    $ foreman start
    # run webserver and celery tasks using Django dev server
    # You can access the cabot deployment at http://localhost:5001/


#### Running OSX?

If you're on OSX there's a [guide to how to set up your development environment on OSX](https://gist.github.com/jirutka/8636572)contributed by [Jakub Jirutka](https://gist.github.com/jirutka).

### Running tests

    $ foreman run python manage.py test cabot

Test coverage is currently pretty poor so any contributions are welcome.

Tests can be found in `cabot/cabotapp/tests/`. Currently using `Mock` for mocking out external calls.

### Requirements

*   [Vagrant](http://vagrantup.com)
*   [Virtualbox](https://www.virtualbox.org)

There's nothing to stop you developing locally without Vagrant but don't blame us if you get tangled.
