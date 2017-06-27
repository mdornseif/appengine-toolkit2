#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/tools/config.py - Configuration via appengine_config.py.

Created by Maximillian Dornseif on 2017-05-25.
Copyright (c) 2017 HUDORA. MIT licensed.
"""

import os

from google.appengine.api import lib_config


config = lib_config.register(
    'GAETK2',
    dict(
        TEMPLATE_DIRS=['./templates'],
        # auth
        CREDENTIAL_CACHE_TIMEOUT=600,
        JWT_SECRET_KEY='*unset*',
        GOOGLE_OAUTH_CONFIG={},  # see https://console.developers.google.com/apis/credentials?project=huwawi2
        GOOGLE_OAUTH_ALLOWED_DOMAINS=['hudora.de'],
        # Backup To Google CloudStorage (or BlobStore)
        BACKUP_GS_BUCKET='*unset*',
        BACKUP_FILESYSTEM='gs',
        BACKUP_QUEUE='default',
        BACKUP_BLACKLIST=[],
    )
)


def get_version():
    """Get GIT-Version.

    Returns the first line of version.txt.

    When deploying we do something like `git show-ref --hash=7 HEAD > version.txt` just before
    `appcfg.py update`. This allows to retrive the data."""

    try:
        version = open("version.txt").readline().strip()
    except IOError:
        # if there is no version.txt file we return something fom the environment.
        version = os.environ.get('CURRENT_VERSION_ID', '?')
    return version


def is_production():
    """checks if we can assume to run on a development machine"""
    if os.environ.get('SERVER_NAME', '').startswith('dev-'):
        return False
    elif os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
        return False
    else:
        return True
