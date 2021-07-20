#!/bin/bash
foreman run python manage.py syncdb
foreman run python manage.py migrate
