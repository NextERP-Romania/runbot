# -*- coding: utf-8 -*-
# modify to add also the mailhog ports

import argparse
import configparser
import datetime
import io
import json
import logging
import os
import re
import shutil
import subprocess
import time
from .. import runbot


_logger = logging.getLogger(__name__)


def docker_run_with_mailhog(*args, **kwargs):
    if len(args)>4:
        args[0]= '/bin/mailhog -ui-bind-addr "0.0.0.0:8071" & ; '+args[0]
    if 'cmd' in kwargs:
        kwargs['cmd']= '/bin/mailhog -ui-bind-addr "0.0.0.0:8071" & ; '+kwargs['cmd']
    return runbot.container._docker_run(args, kwargs)

if os.environ.get('RUNBOT_MODE') != 'test':
    runbot.container.docker_run = docker_run_with_mailhog
