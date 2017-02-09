---
layout: page
title: "Deployment"
category: use
date: 2014-01-08 23:52:19
order: 2
---

### General notes

Our experience has been that Cabot is reasonably reliable. However, hardware fails, networks have issues and things go generally go wrong. So you should plan for the worst.

For that reason we strongly recommend that you deploy Cabot somewhere that its failure - should it occur - should be uncorrelated with other infrastructure issues that you may experience.

For example, if you host the majority of your infrastructure on AWS it might be reasonable to deploy Cabot to a VPS on Linode, or SoftLayer, or DigitalOcean. If your infrastructure is on OVH, put it on AWS. (Don't use a micro instance though, they are not very reliable.)

A guide to getting started on DigitalOcean using the `tugboat` CLI is included in this documentation.

### Upgrading

Upgrading to a new version should be as simple as merging in changes from upstream and deploying over the top of your existing install.

There are 2 exceptions. If upgrading from any version below [0.6.0](https://github.com/arachnys/cabot/tree/0.6.0) you must first upgrade to [0.6.0](https://github.com/arachnys/cabot/tree/0.6.0) as your database must be correctly migrated before the Django 1.7 version change. You will then need to run `python manage.py migrate --fake-initial` after upgrading to the latest version.

If you are upgrading from any version pre [3872565](https://github.com/arachnys/cabot/commit/38725651445df61eda06b86a6933317153088e4b) you need a few additional steps as that commit changed the paths of the celery workers so they will not be shut down properly by new deploys. The best way of upgrading in this case is to:

*   Stop Cabot (`sudo service cabot stop`) - should stop all "old" workers
*   Deploy (which will start new workers)

If you deploy without stopping the old workers first you may need to kill the old ones by hand. (You'll be able to see them by running `ps aux | grep app.cabotapp`)

### Failover and redundancy

Currently Cabot only supports a single telephone provider for alerts, making Cabot dependent on connecting to Twilio's servers and on those servers working correctly whenever Cabot tries to send an SMS or phone alert.

Adding a backup provider, such as Plivo, might give further confidence that urgent messages will get through. If you would like to implement this please send a pull request.

If high availability and reliability of paramount importance it may be worth looking at a commercial solution like [Pagerduty](http://pagerduty.com). However even [commercial providers have infrequent outages](http://blog.pagerduty.com/2013/12/outage-post-mortem-dec-11-2013/) under extreme conditions. What do you do, eh?

### Quis custodiet ipsos custodes?

One practical challenge with monitoring is: how do we monitor whether or not the monitor itself is working correctly?

In order to provide some protection from failures of Cabot itself, Cabot provides an unauthenticated endpoint `/status/` that can be polled by other services and will return a response body of:

*   `Checks running`
    *   If checks are running and all seems fine.
*   `Checks not running`
    *   If checks are not running, i.e. something has gone wrong with task scheduling and the service needs to be restarted.

#### Monitor from Jenkins

At [Arachnys](https://www.arachnys.com) we simply run a regular Jenkins job which polls this endpoint and checks for the text "Checks running":

    curl -XGET https://cabot.yourcompany.com/status/ | grep "Checks running"

If:

*   Request times out
*   Server error occurs
*   Server returns `Checks not running`

This job will fail and sends us an alert.

#### Monitor from second Cabot instance

Another option would be to run an entirely separate instance of Cabot on a different server, whose only job was to check for the `Checks running` output from `/status/` via an [HTTP check](http-checks.html).

It goes without saying that you should host this second instance on totally separate infrastructure from the instance it is monitoring.

