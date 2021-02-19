# -*- coding: utf-8 -*-
import os
from .. import runbot


def docker_get_gateway_ip():
    """Return the host ip of the docker default bridge gateway
because the maihog is installed local and smtp must be local at port 1024

"""
    return '127.0.0.1'

if os.environ.get('RUNBOT_MODE') != 'test':
    print("****not in test mode\n"*40)
    runbot.container.docker_get_gateway_ip = docker_get_gateway_ip

