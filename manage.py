#!/usr/bin/env python
import os
import sys
from cabot.config import config_charge




if __name__ == "__main__":

    #carga de enviroment
    config_charge()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cabot.settings")
    

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
