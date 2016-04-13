---
layout: page
title: "Configuration"
category: use
date: 2014-01-08 23:52:15
order: 1
---

### Files to edit

All configuration takes place through environment variables managed by Foreman.

#### Production

Production configuration lives in `conf/production.env`. You should copy and customise the template file included as `conf/production.env.example`.

To change env variables on a running instance, modify `conf/production.env` locally and deploy your changes with `fab deploy -H ubuntu@your.server.hostname` (as in the [5th step of the quickstart guide](/qs/quickstart.html)).

#### Development

See `conf/development.env.example`.

### Settings available

In order to use all functionality the following settings must be configured in `conf/production.env`. If you use `fab deploy` it will automatically generate an upstart service config including these:

#### SMTP settings

Secure TLS/SSL email backend is used.

* `SES_HOST`
* `SES_USER`
* `SES_PASS`
* `SES_PORT`

#### Calendar sync and [team rota](rota.html)

*   `CALENDAR_ICAL_URL`
    *   URL of the linked Google Calendar which contains team rota data, e.g. `http://www.google.com/calendar/ical/blah%40group.calendar.google.com/`

#### [Graphite](graphite-checks.html) integration

These settings are required for [Graphite checks](graphite-checks.html).

*   `GRAPHITE_API`
    *   URL of Graphite server, e.g. `https://graphite.mycompany.com/`
*   `GRAPHITE_USER`
*   `GRAPHITE_PASS`
    *   username and password (basic auth) for Graphite server
*   `GRAPHITE_FROM`
    *   Cabot by default set [this parameter](http://graphite.readthedocs.org/en/latest/render_api.html?highlight=minute%20hour#from-until) to `-10min` but if you want to set another time horizon you can put it here using the naming defined by Graphite.

#### [Jenkins](jenkins-checks.html) integration

These settings are required for [Jenkins checks](jenkins-checks.html).

*   `JENKINS_API`
    *   URL of Jenkins server, e.g. `https://jenkins.mycompany.com/`
*   `JENKINS_USER`
*   `JENKINS_PASS`
    *   username and password for API access (basic auth)

#### Hipchat [alerting](alerting.html)

You must set these correctly if you want Cabot to be able to send alerts to your Hipchat room.

*   `HIPCHAT_URL`
    * Hipchat API URL. Set to `https://api.hipchat.com/v1/rooms/message` for ondemand hipchat.
*   `HIPCHAT_ALERT_ROOM`
    *   numeric ID of the Hipchat room you want alerts sent to, e.g. `14256`
*   `HIPCHAT_API_KEY`
    *   write-only API key for Hipchat

#### Twilio (SMS and phone [alerts](alerting.html)) integration

These credentials are required for SMS and phone alerts.

*   `TWILIO_ACCOUNT_SID`
    *   SID of Twilio account
*   `TWILIO_AUTH_TOKEN`
    *   Auth token
*   `TWILIO_OUTGOING_NUMBER`
    *   number for called ID of phone and SMS alerts, e.g. `+442035551234`

#### Links back to server

*   `WWW_HTTP_HOST`
    *   FQDN of Cabot server, e.g. `cabot.yourcompany.com`

#### Using MySQL?

Cabot uses Postgresql by default but it's easy enough to set it up with another database backend such as MySQL: https://github.com/arachnys/cabot/issues/29#issuecomment-34172620

See also [JensRantil's branch](https://github.com/JensRantil/cabot/commit/2a5f04849c10b58ca2424bc55d2b203c8d5627bb) which has provisioning setup for MySQL.
