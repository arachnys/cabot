---
layout: page
title: "Operations"
category: use
date: 2014-01-08 23:52:19
order: 3
---

### Operations

During day-to-day use of Cabot you may want to do some operations on it for, apart from [deployment or upgrade](deployment.html).

To do that follow these simple steps:

1. Go into the Cabot repository you cloned during the 1st step of [Quickstart](/qs/quickstart.html)

2. Use [Fabric](http://docs.fabfile.org/) to do some command on your Cabot instance:

        $ fab <command> -H ubuntu@your.server.hostname
          
..where &lt;command&gt; is one of the following:

* **stop** - stops your Cabot instance, obviously,
* **restart** - restarts it,
* **backup** - backups Cabot's database locally
