---
layout: page
title: "Writing a Check Plugin"
category: dev
date: 2017-09-28 09:42:47
order: 3
---

With the release of 0.11.1, Cabot can be extended through the use of check plugins. This allows the user to check additional data sources beyond the default ones.

Before getting started, follow the [development introduction]({% post_url 2014-01-08-get-started %}). Continue when you have set up `docker-compose` and got cabot running locally on your own machine.

You can get inspiration from these two check plugins:

* ['Network' check plugin](https://github.com/cabotapp/cabot-check-network) is an extremely simple plugin, with a very narrow feature set.
* ['CloudWatch' check plugin](https://github.com/cabotapp/cabot-check-cloudwatch) is a more advanced example, using more specific fields and advanced features like autocompletion.
* ['SSLCert' check plugin](https://github.com/decryptus/cabot-check-sslcert) is a simple plugin to check SSL certificates, you can specify days before expiration.
