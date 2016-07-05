---
layout: page
title: "Installing Plugins"
category: dev
date: 2015-01-20 22:52:47
order: 2
---

The ways that Cabot monitors your infrastructure and the way that it alerts you can be extended effectively through the use of plugins. With the release of Cabot 1.0.0, plugins can be installed and easily integrated into Cabot with only one modification to your configuration file.

1. Open your `conf/production.env` file on your local machine.
2. Find the line starting with CABOT_PLUGINS_ENABLED.
3. Append the name of the plugin to end of the list taking care to separate it by a comma from the previous plugin.
4. Redeploy.

If the plugin is not listed in PyPI then you will need to install it manually.

1. SSH into your server using `ubuntu@yourcabotserver.com`.
2. Enter the python virtual environment using `. venv/bin/activate`. Notice the space between the `.` and the `venv/bin/activate`
3. Install your plugin to the server using pip. [This explains installing from GitHub.](http://stackoverflow.com/questions/8247605/configuring-so-that-pip-install-can-work-from-github)
4. Append the plugin name to the `CABOT_PLUGINS_ENABLED` variable in your conf file located at `~/cabot/conf/production.env`.

