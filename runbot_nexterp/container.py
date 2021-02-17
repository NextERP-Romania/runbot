# -*- coding: utf-8 -*-
# modify to add also the mailhog ports
import os
from .. import runbot


def docker_run_with_mailhog(*args, **kwargs):
    if len(args)>4:
        args[0]= '/bin/mailhog -ui-bind-addr "0.0.0.0:8071" & ; '+args[0]
    if 'cmd' in kwargs:
        kwargs['cmd'] = '/bin/mailhog -ui-bind-addr "0.0.0.0:8071" & ; '+kwargs['cmd']
    return runbot.container._docker_run(args, kwargs)

def docker_get_gateway_ip():
    """Return the host ip of the docker default bridge gateway"""
    return '127.0.0.1'

if os.environ.get('RUNBOT_MODE') != 'test':
    runbot.container.docker_run = docker_run_with_mailhog
    runbot.container.docker_get_gateway_ip = docker_get_gateway_ip

