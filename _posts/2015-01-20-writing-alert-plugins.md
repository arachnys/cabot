---
layout: page
title: "Writing an Alert Plugin"
category: dev
date: 2015-01-20 22:52:47
order: 2
---

With the release of cabot 0.0.1-dev, Cabot can now be extended through the use of alert plugins. This allows the user to be alerted of any service outages through any means of communication supported by the installed plugins. This tutorial will guide you through the process of writing a simple Cabot plugin.

Before getting started, follow the [development introduction]({% post_url 2014-01-08-get-started %}). Continue when you have set up `docker-compose` and got cabot running locally on your own machine.

You can obtain a ['skeleton' alert plugin](https://github.com/cabotapp/cabot-alert-skeleton) which has all the necessary files to get started with cabot plugin development.

The cabot plugin architecture is designed to give the full power of django to the developer by getting out of his/her way as much as possible. For this reason it is necessary to understand the basics of how a django application works.

### Layout
An alert plugin is essentially a small *packaged* django application and is organised as such.

    cabot-alert-skeleton
    ├── cabot_alert_skeleton
    │   ├── __init__.py
    │   └── models.py
    ├── LICENSE
    ├── README.md
    ├── setup.cfg
    └── setup.py

The root directory contains mostly meta-data, present in almost all python packages, about the plugin.

* **LICENSE**: Contains the license that the plugin is released under. Cabot is released under the MIT license.
* **README.md**: A README containing installation instructions and details about the plugin.
* **setup.py**: Installation script for the plugin. Fairly standard for a python package. Define your dependencies here.
* **setup.cfg**: Configuration file for the installation

The plugin code will all be contained inside the *cabot_alert_skeleton* subdirectory. Naturally you can name this however you wish however we suggest sticking to the naming convention *cabot_alert_service* where *service* is the means of communication i.e. email, twitter, hipchat etc.

As you would expect from a django application, the *models.py* file contains the models that define the functionality of the plugin.

The *\_\_init\_\_.py* file simply tells python that *cabot_alert_skeleton* is a module and defines the default imports.

When you have created, organised and configured your plugin, open up your models.py file.

### Important Classes
When writing alert plugins for cabot, there are two classes that you may wish import:

    from cabot.cabotapp.alert import AlertPlugin
    from cabot.cabotapp.alert import AlertPluginUserData

These two classes are fairly self-descriptive. The *AlertPlugin* class defines a single discrete plugin and how the alert is carried out: i.e. sending a message to the user via Hipchat or sending them an email. The *AlertPluginUserData* is a model which defines any User preferences such as their hipchat alias. The *AlertPluginUserData* model is optional depending on whether you wish the user to be able to configure his/her preferences specifically for that plugin. Note that preferences such as the user's name and email address are stored by Cabot under the user's 'General' preferences and so do not need to be defined specifically by any one plugin.

It is a good idea to write the user preferences first because they shall be referenced in the *AlertPlugin* subclasses that you write.

### AlertPluginUserData
The *AlertPluginUserData* class defines the preferences of a single user. Here is an example from the default skeleton alert plugin. As you can see, it is very simple.

    from django.db import models
    from cabot.cabotapp.alert import AlertPluginUserData

    class SkeletonAlertUserData(AlertPluginUserData):
        name = "Skeleton Plugin"
        favorite_bone = models.CharField(max_length=50, blank=True)

The *name* variable dictates how the plugin will be referenced in the user preferences.

> This section is out of date - Vagrant use is deprecated.

Once you have created your *AlertPluginUserData* subclass, you should test your plugin to make sure that it's working. SSH into your vagrant box then install your plugin:

    $ sudo pip install https+git://github.com/<your_user>/<your_plugin>.git

![Skeleton AlertPluginUserData](/images/skeleton-plugin.png)

If Django throws an exception or you can't see your plugin in the list:

* Make sure that there are no errors in your plugin.
* Make sure that you have installed it correctly.

### AlertPlugin
The *AlertPlugin* class represents the actual plugin itself. It defines the name of the plugin, its author and the way that it handles an alert.

To get started, take a look at the AlertPlugin class from [cabot-alert-skeleton](https://github.com/arachnys/cabot-alert-hipchat)

    class SkeletonAlert(AlertPlugin):
        name = "Skeleton"
        author = "Jack Skellington"

        def send_alert(self, service, users, duty_officers):
            """Implement your send_alert functionality here."""
            return

The name and author are simply meta-data about your plugin. The 'author' field simple exists to give credit where it is due whereas the 'name' field is used when selecting plugins for a service.

* You should avoid using the word 'plugin' in the name in order to keep it short and simple. Everything is a plugin so there is no need to relay redundant information.

![Skeleton Alert Plugin](/images/skeleton-alert-plugin.png)

The *send_alert* function will be called whenever a service goes into a failing state and every 10 minutes after when it is still failing. The function will also be called when the service recovers and returns to a passing state.

* You can change the time in between alert notifications by setting the ALERT_INTERVAL value in your configuration file (normally conf/production.conf).
