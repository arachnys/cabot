---
layout: page
title: "Get started"
category: qs
date: 2014-01-08 22:49:24
---

Getting started is easy using [docker-compose](https://docs.docker.com/compose/).

You can either set it up behind you're own reverse proxy (e.g. nginx) or use [Caddy](https://caddyserver.com/)


### Step by step


1.  Clone the docker-cabot repo:

        $ git clone git@github.com:cabotapp/docker-cabot.git

2.  Add your keys for external services to `conf/production.env` using `production.env.example` as a template:

        $ cp conf/production.env.example conf/production.env

3.  (a) Run docker compose with caddy as a reverse proxy:

        $ cp conf/Caddyfile.example conf/Caddyfile
        $ docker-compose -f docker-compose.yml -f docker-compose-caddy.yml up -d

    (b) OR run just cabot and set up your own reverse proxy (using e.g. nginx, apache or caddy)

            $ docker-compose up -d

    > Note: The `-d` is to daemonize - making it run in the background.

4.  That's it! If you go to your server in your browser you should see the first time setup screen

> Note: Without a reverse-proxy by default it will only listen to local requests.
To make it listen publicly on the internet change '127.0.0.1:5000:5000' to '80:5000'
in docker-compose.yml
