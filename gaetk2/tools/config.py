#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/tools/config.py - Configuration via appengine_config.py.

Created by Maximillian Dornseif on 2017-05-25.
Copyright (c) 2017, 2018 HUDORA. MIT licensed.
"""
import os
import time

from google.appengine.api import lib_config
from google.appengine.api.app_identity import get_application_id


config = lib_config.register(
    'GAETK2',
    dict(
        TEMPLATE_DIRS=['./templates'],
        # auth
        AUTH_DISABLE_HTTPBASIC_AUTH=False,
        AUTH_DISABLE_SESSION_AUTH=False,
        CREDENTIAL_CACHE_TIMEOUT=600,
        JWT_SECRET_KEY='*unset*',
        OAUTH_GOOGLE_CONFIG={},  # see https://console.developers.google.com/apis/credentials?project=huwawi2
        OAUTH_GOOGLE_ALLOWED_DOMAINS=['hudora.de'],
        AUTH0_DOMAIN='*unset*',
        AUTH0_CLIENT_ID='*unset*',
        AUTH0_CLIENT_SECRET='*unset*',
        # Backup To Google CloudStorage (or BlobStore)
        BACKUP_GS_BUCKET='*unset*',
        BACKUP_FILESYSTEM='gs',
        BACKUP_QUEUE='default',
        BACKUP_BLACKLIST=[],
        APP_NAME='{}'.format(get_application_id()).capitalize(),
        SECRET='*changeme"*',
        SENTRY_DSN='',
        SENTRY_PUBLIC_DSN='',
    )
)


# add our own template directory
config.TEMPLATE_DIRS.append(os.path.join(os.path.dirname(__file__), '../..', 'templates'))


def get_version():
    """Get GIT-Version.

    Returns the first line of version.txt.

    When deploying we do something like `git show-ref --hash=7 HEAD > version.txt` just before
    `appcfg.py update`. This allows to retrive the data."""

    try:
        version = open("version.txt").readline().strip()
    except IOError:
        # if there is no version.txt file we return something fom the environment.
        version = '{}-{}'.format(os.environ.get('CURRENT_VERSION_ID', 'dev'), time.time())
    return version


def is_production():
    """checks if we can assume to run on a production version machine"""
    if is_development:
        return False
    elif os.environ.get('SERVER_NAME', '').startswith('production'):
        return True
    elif os.environ.get('SERVER_NAME', '').startswith('staging'):
        return False
    elif (os.environ.get('SERVER_NAME', '').startswith('v') and
        os.environ.get('SERVER_NAME', '').endswith('appspot.com')):
        return False
    else:
        return True

def is_development():
    """Checks if we are running on a development system.

    See :term:`development version` what this means."""
    return (os.environ.get('SERVER_SOFTWARE', '').startswith('Development') or
            os.environ.get('SERVER_NAME', '').startswith('dev-'))

