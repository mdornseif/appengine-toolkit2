#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/tools/config.py - Configuration via appengine_config.py.

Created by Maximillian Dornseif on 2017-05-25.
Copyright (c) 2017, 2018 HUDORA. MIT licensed.
"""
import os
import time
import warnings

from google.appengine.api import lib_config

gaetkconfig = lib_config.register(
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
        SECRET='',
        APP_NAME='',
        SENTRY_DSN='',
        SENTRY_PUBLIC_DSN='',
        SENTRY_SECURITY_TOKEN='',
    )
)


# add our own template directory
gaetkconfig.TEMPLATE_DIRS.append(
    os.path.join(
        os.path.dirname(__file__),
        '../..',
        'templates'))
# legacy
config = gaetkconfig


def get_release():
    """Get the :term:`tagged version` of the current deployment.

    Get the first line of `gaetk2-release.txt`.
    """

    try:
        version = open('gaetk2-release.txt').readline().strip()
    except IOError:
        # if there is no version.txt file we return something fom the environment.
        version = '{}-{}'.format(os.environ.get('CURRENT_VERSION_ID', 'dev'), time.time())
    return version


def get_version():
    """Do not use this."""
    warnings.warn("`get_version` is deprecated, use `get_release`", DeprecationWarning, stacklevel=2)
    return get_release()


def get_revision():
    """Get the git SHA1 revision of the current deployment.

    Get the first line of ` gaetk2-revision.txt`.

    When deploying we do something like `git show-ref --hash=7 HEAD > version.txt` just before
    `appcfg.py update`. This allows to retrive the data."""

    try:
        version = open('gaetk2-revision.txt').readline().strip()
    except IOError:
        version = 'HEAD'
    return version


def is_production():
    """checks if we can assume to run on a production version instance.

    ... unless called by the resttest-client."""
    if is_development:
        return False
    if os.environ.get('HTTP_USER_AGENT').startswith('resttest'):
        return False
    elif os.environ.get('SERVER_NAME', '').startswith('production'):
        return True
    elif os.environ.get('SERVER_NAME', '').startswith('staging'):
        return True
    elif (os.environ.get('SERVER_NAME', '').startswith('v') and
          os.environ.get('SERVER_NAME', '').endswith('appspot.com')):
        return False
    else:
        return True


def is_development():
    """Checks if we are running on a development system.

    See :term:`development version` what this means."""
    name = os.environ.get('SERVER_NAME', '')
    return (os.environ.get('SERVER_SOFTWARE', '').startswith('Development') or
            name.startswith('dev-') or name.startswith('test'))


def get_environment():
    """Returns `production`, `staging`, `testing` or `development`."""
    if os.environ.get('SERVER_NAME', '').startswith('production'):
        return 'production'
    elif os.environ.get('SERVER_NAME', '').startswith('staging'):
        return 'staging'
    elif (os.environ.get('SERVER_NAME', '').startswith('v') and
          os.environ.get('SERVER_NAME', '').endswith('appspot.com')):
        return 'testing'
    elif os.environ.get('SERVER_NAME', '').startswith('test'):
        return 'test'
    return 'development'
