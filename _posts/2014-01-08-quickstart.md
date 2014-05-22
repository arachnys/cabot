---
layout: page
title: "Get started"
category: qs
date: 2014-01-08 22:49:24
---

Getting started is easy via a VPS on [AWS](https://aws.amazon.com) or [DigitalOcean](https://www.digitalocean.com) (although Cabot can be hosted anywhere). Cabot is designed for deployment on Ubuntu 12.04 LTS.

###Step by step

1.  Clone:

        $ git clone git@github.com:arachnys/cabot.git
        # Clone the repo

        $ cd cabot

2.  Add your keys for external services to `conf/production.env`:

        $ cp conf/production.env.example conf/production.env

3.  Spin up a new VPS instance (on e.g. AWS or DigitalOcean) - you can create a new DigitalOcean "droplet" from the command line via [`tugboat`](https://github.com/pearkes/tugboat)

        $ tugboat create cabot --size=66 --image=3101045 --region=1
        # create a new droplet called `cabot` with 1GB of memory running Ubuntu 12.04 in New York region
        # --image and --size arguments seem to change, see tugboat docs for details

4.  Provision the newly-created VPS using [Fabric](http://docs.fabfile.org/)

        $ fab provision -H root@your.server.hostname
        # This will:
        # * install dependencies on the new server
        # * create a new `ubuntu` user that will be able to connect over SSH (for API compatibility with Amazon's Ubuntu AMIs).

5.  Deploy to the provisioned server:

        $ fab deploy -H ubuntu@your.server.hostname
        # NB using `ubuntu` not `root` as above
        # Will prompt you to create a Django superuser which you'll use to log in via web and create additional users.

6.  Navigate in web browser to `your.server.hostname`, log in as superuser, and create your first `Service`s and `Check`s using the web interface.

7.  *(Optional) get woken up at 3 a.m. by an automated phone call telling you the server you're monitoring has crashed.*

Currently provisioning is done by the `bin/setup_dependencies.sh` script.
