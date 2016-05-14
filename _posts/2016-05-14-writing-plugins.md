---
layout: page
title: "Writing Plugins"
category: dev
date: 2016-05-14 22:52:47
order: 2
---

With the release of Cabot 1.0.0, Cabot has the ability to be extended by both alert and status check plugins. These allow you to run custom checks tailored to your infrastructure and alert you in ways convenient to your team. This tutorial will guide you through the, hopefully painless, process of learning, writing and deploying custom plugins for cabot.

### Preparation

Before getting started, follow the [development introduction]({% post_url 2014-01-08-get-started %}) which will show you how to get a development version of Cabot running locally on a virtual machine. You should also understand how to [install plugins]({% post_url 2016-05-14-installing-plugins %}).

You can obtain a ['skeleton' alert plugin](https://github.com/cabotapp/cabot-alert-skeleton) or a ['skeleton' check plugin](https://github.com/cabotapp/cabot-check-skeleton) which has all the necessary files to get started with cabot plugin development.

Cabot is built on Django and the Cabot plugin architecture is designed to offer the full power of Django to the developer by getting out of his/her way as much as possible. For this reason it is necessary to understand the basics of how a Django application works.

To get started, create a plugin\_dev directory in the cabot project directory and git clone a copy of one of the skeleton plugins into it. Skeleton folder structures for Alert Plugins and Status Check Plugins can be found on GitHub.

### Layout
An plugin is essentially a small *packaged* Django application. It is organised in the following way. If the plugin adds its own URLs and views to Cabot then it will have a urls.py and views.py in line with Django standards.

    cabot-plugin-skeleton
    ├── cabot_plugin_skeleton
    │   ├── __init__.py
    │   └── plugin.py
    ├── LICENSE
    ├── README.md
    ├── setup.cfg
    └── setup.py

The root directory contains mostly meta-data, present in almost all python packages, about the plugin.

* **LICENSE**: Contains the license that the plugin is released under. Cabot is released under the MIT license.
* **README.md**: A README containing installation instructions and details about the plugin.
* **setup.py**: Installation script for the plugin. Fairly standard for a python package. Define your dependencies here.
* **setup.cfg**: Configuration file for the installation

The *\_\_init\_\_.py* file simply tells python that *cabot_alert_skeleton* is a module.

The plugin code will all be contained inside the *cabot_plugin_skeleton* subdirectory. Naturally you can name this however you wish however we suggest sticking to the naming convention *cabot_alert_service* or *cabot_check_service* where *service* is the means of communication or check i.e. email, twitter, hipchat, graphite, http etc. Make sure that you update the information in setup.py to include the name of your plugin and its purpose.

The main plugin code will go into `plugin.py`


### Alert Plugins
Let's examine the plugin.py code for cabot\_alert\_skeleton and go through it line by line.

    from cabot.plugins.models import AlertPlugin
    from django import forms
    from os import environ as env 

    from logging import getLogger
    logger = getLogger(__name__)

    class SkeletonAlertUserSettingsForm(forms.Form):
        favorite_bone = forms.CharField(max_length=100)

    class SkeletonAlertPlugin(AlertPlugin):
        name = "Skeleton"
        slug = "cabot_alert_skeleton"
        author = "Jonathan Balls"
        version = "0.0.1"
        font_icon = "fa fa-code"

        user_config_form = SkeletonAlertUserSettingsForm

        def send_alert(self, service, users, duty_officers):
            calcium_level = env.get('CALCIUM_LEVEL') 
            message = service.get_status_message()
            for u in users:
                logger.info('{} - This is bad for your {}.'.format(
                    message,
                    u.cabot_alert_skeleton_settings.favorite_bone))

            return True

The first line says `from cabot.plugins.models import AlertPlugin`. The AlertPlugin class is the only Cabot specific class that you will use during AlertPlugin development. Django's inbuilt forms are used for user settings.

Once we have subclassed AlertPlugin, we need to add various meta information. This is completed as follows:

* `name`: The name of the plugin/service providing the alert.
* `slug`: A unique name for the plugin. This is how your plugin is referred to internally by Cabot. It should be unique. You can usually just use the name of the package if you are only defining one.
* `author`: The author of the plugin.
* `version`: The version of the plugin.
* `font_icon`: The [glyphicon](http://getbootstrap.com/components/#glyphicons) or [font-awesome](http://fontawesome.io/icons/) icon name.
* `user_config_form`: The form that will be used to define individual user settings. Read up on the [Django forms documentation](https://docs.djangoproject.com/en/1.9/topics/forms/) for more information about how these are implemented and written. SkeletonAlertUserSettingsForm is an example of one of these.

The actual implementation of the AlertPlugin is in the mandatory send\_alert() function. The send\_alert() function receives three arguments.

The first argument is an object representing the Service that has gone into failing status. It has the following properties that you can access:

* `name`: The name of the Service.
* `url`: The URL of the Service.
* `instances`: A list of instances associated with the Service.
* `last_alert_sent`: The time that the last alert was sent.
* `overall_status`: The current status of the Service.

The Service also has a get\_status\_message() function which returns a string detailing information about the current status and which checks have failed. This is useful for creating a message to send to users.

The second argument is a list of users that have elected to receive alerts for problems when the Service goes down. The third argument is a list users who are 'Duty officers' at the current time. See [duty rotas]({% post_url 2014-01-08-rota %}) for more information.

Accessing user information is also very easy. It can be accessed using `User.plugin_slug_settings.setting_name`. In the skeleton example above, `u.cabot_alert_skeleton_settings.favorite_bone`. would return the 'favorite\_bone' setting of the user.

You should return True if your alert succeeds.

Implementation of the send\_alert() function are left largely up to the user but have a look at the [official Cabot plugins](https://github.com/cabotapp/) for more examples.

### Status Check Plugins
Cabot also has the capability to extend the way it runs checks on instances and services to assert that they are functioning properly.

First make sure that you have read the sections above about preparation and layout of a plugin. We will be using ['skeleton' check plugin](https://github.com/cabotapp/cabot-check-skeleton) to start the development. The functionality of the plugin is implemented in the `plugin.py` file just like in alert plugins. Open it up and take a look at the code.

    from cabot.plugins.models import StatusCheckPlugin
    from django import forms
    from os import environ as env

    class SkeletonStatusCheckForm(forms.Form):
	    bone_name = forms.CharField(
                help_text = 'Name of the bone to check',
            )

    class SkeletonStatusCheckPlugin(StatusCheckPlugin):

        name = 'SkeletonStatusCheckPlugin'
        slug = 'cabot_check_skeleton'
        author = 'Jonathan Balls'
        version = '0.0.1'
        font_icon = 'glyphicon glyphicon-skull'

        config_form = SkeletonStatusCheckForm

        plugin_variables = [
            'SKELETON_LIST_OF_BONES',
        ]

        def run(self, check, result):

            list_of_bones = env.get('SKELETON_LIST_OF_BONES', None)

            if not list_of_bones:
                result.succeeded = False
                result.error = u'SKELETON_LIST_OF_BONES is not' +\
                                'defined in environment variables'
                return result

            list_of_bones = list_of_bones.split(',')

            if check.bone_name in list_of_bones:
                result.succeeded = True
                return result
            else:
                result.succeeded = False
                result.error = u'%s is not in the list of bones' % check.bone_name
                return result

        def description(self, check):
            return 'Check whether %s is in list of bones.' % check.bone_name
	
The first line is an import of the plugin class - `StatusCheckPlugin`. As with Alert Plugins, this will be the only Cabot specific class that you will need to import. Custom Status Check variables are implemented using Django forms (as you can see in SkeletonStatusCheckForm). The name, slug, author, version, plugin\_variables and font\_icon meta variables have the same purpose as those in Alert Plugins. The `config_form` variable is a form used to define additional check specific variables to a status check. These are written using [Django forms](https://docs.djangoproject.com/en/1.9/topics/forms/).

The implementation of the status check is done in the `run(self, check, result)` method. The implementation is left up to the programmer - the only requirement being that the method returns the result object. The run method receives two arguments.

The first argument is an object representing the status check created by the user. It has the following variables:

* `name`: The name of the check
* `instance_set`: The set of Instances associated with the check
* `service_set`: The set of Services associated with the check

The check will also have all variables defined in the config form.

The second argument is an object representing a 'result'. It only has two variables:

* `succeeded`: A boolean representing whether the check has passed or not. This is False by default.
* `error`: A string holding an error message if the check fails. This should explain what caused the error to happen. If you catch a python Exception then you should put its message here.

A StatusCheckPlugin also has `description` method. It has the simple purpose of returning a string describing the StatusCheck that is passed to it in its arguments. The description should describe what that specific StatusCheck does. For example 'ICMP check pointing towards 216.58.208.174'.

For more examples of StatusCheck implementations have a look at the [official Cabot plugins](https://github.com/cabotapp/).

### Testing your plugin
Every plugin has a tests.py file containing all tests related to the plugin. These are implemented using the [Django testing framework](https://docs.djangoproject.com/en/1.9/topics/testing/). How you test is completely left up to the plugin author.
