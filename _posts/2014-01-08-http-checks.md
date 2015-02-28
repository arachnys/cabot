---
layout: page
title: "HTTP checks"
category: use
date: 2014-01-08 22:53:32
order: 8
---

### Getting started

To add a new check:

Click **New ▾** and then **Http check**.

Most form fields are self-explanatory.

*   `Text match` - this will be parsed as a regular expression and run against the raw HTML - not the rendered DOM - of the page retrieved from `Endpoint`. Of course, a simple word is a perfectly acceptable regular expression.
*   `Status code` - currently you must specify a single status code, not a range.
*   `Timeout` - the length of time Cabot will attempt to send a request to `Endpoint`.
*   `Debounce` - number of consecutive failures to tolerate.
    *   We introduced this because we found ourselves getting occasional unreproduceable errors from Cloudflare's CDN (in particular.)

### Why monitor HTTP endpoints?

To check that your servers are running and not just showing `Service unavailable`. Currently, if you want to get a telephone alert if your front page goes down, you have to:

*   Sign up to PagerDuty and Pingdom
*   Build some solution yourself
