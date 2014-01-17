Cabot
=====

Cabot is a free, open-source, self-hosted infrastructure monitoring platform that provides some of the best features of [PagerDuty](http://www.pagerduty.com), [Server Density](http://www.serverdensity.com), [Pingdom](http://www.pingdom.com) and [Nagios](http://www.nagios.org) without their cost and complexity. (Nagios, I'm mainly looking at you.)

It provides a web interface that allows you to monitor services (e.g. "Stage Redis server", "Production ElasticSearch cluster") and send telephone, sms or hipchat/email alerts to your on-duty team if those services start misbehaving or go down - all without writing a line of code. Best of all, you can use data that you're already pushing to Graphite/statsd to generate alerts, rather than implementing and maintaining a whole new system of data collectors.

You can alert based on:

*   Metrics from [Graphite](https://github.com/graphite-project/graphite-web)
*   Status code and response content of web endpoints
*   [Jenkins](http://jenkins-ci.org) build statuses

We built Cabot as a Christmas project at [Arachnys](https://www.arachnys.com) because we couldn't wrap our heads around Nagios, and nothing else out there seemed to fit our use case. We're open-sourcing it in the hope that others find it useful.

Cabot is written in Python and uses [Django](https://www.djangoproject.com/), [Bootstrap](http://getbootstrap.com/), [Font Awesome](http://fontawesome.io) and a whole host of other goodies under the hood.

## Screenshots

### Services dashboard

![Services dashboard](https://dl.dropboxusercontent.com/s/cgpxe3929is2uar/cabot-service-dashboard.png?dl=1&token_hash=AAHrlDisUzWRxpg892LhlKQWFRNSkZKD7l_zdSxND-YKhw)

### Single service overview

![Individual service overview](https://dl.dropboxusercontent.com/s/541p0kbq3pwone6/cabot-service-status.png?dl=1&token_hash=AAGpSI6lyHm3-xCQSFOyyZ_SkJOzfdMIxfa-gYgCVS25pw)

## Quickstart

Deploy in 5 minutes or less using [official quickstart guide at cabotapp.com](http://cabotapp.com/qs/quickstart.html).

## How it works

Docs have moved to [cabotapp.com](http://cabotapp.com)

Sections:

*   [Configuration](http://cabotapp.com/use/configuration.html)
*   [Deployment](http://cabotapp.com/use/deployment.html)
*   [Services](http://cabotapp.com/use/services.html)
*   [Graphite checks](http://cabotapp.com/use/graphite-checks.html)
*   [Jenkins checks](http://cabotapp.com/use/jenkins-checks.html)
*   [HTTP checks](http://cabotapp.com/use/http-checks.html)
*   [Alerting](http://cabotapp.com/use/alerting.html)
*   [Users](http://cabotapp.com/use/users.html)
*   [Rota](http://cabotapp.com/use/rota.html)

For those who want to contribute:

*   [Help develop](http://cabotapp.com/dev/get-started.html)
*   [Contribute code](http://cabotapp.com/dev/contribute-code.html)

## FAQ

### Why "Cabot"?

My dog is called Cabot and he loves monitoring things. Mainly the presence of food in his immediate surroundings, or perhaps the frequency of squirrel visits to our garden. He also barks loudly to alert us on certain events (e.g. the postman coming to the door).

![Cabot watching... something](https://dl.dropboxusercontent.com/sc/w0k0185wur929la/RN6X-PkZIl/0?dl=1&token_hash=AAEvyK-dMHsvMPwMsx89tSHXsUlMC8WN_fIu_H1Vo9wxWA)

It's just a lucky coincidence that his name sounds like he could be an automation tool.

## License

See `LICENSE` file in this repo.
