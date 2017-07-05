---
layout: page
title: "Operations"
category: use
date: 2014-01-08 23:52:19
order: 3
---

### Operations

During day-to-day use of Cabot you may want to do some operations on it for, apart from [deployment or upgrade](deployment.html).

To do that, please SSH onto your host and run commands. If using docker-compose:

* backup: `docker-compose exec postgres pg_dump -U postgres postgres > cabot.sql`

