#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2.config - Configuration helpers for gaetk2/appengine.

Created by Maximillian Dornseif on 2018-02-17.
Copyright (c) HUDORA. MIT licensed.
"""
from __future__ import absolute_import
import os
import time
import warnings

from gaetk2.tools.caching import lru_cache

from .runtime import get_config, set_config
from .internal import gaetkconfig

__all__ = [
    'gaetkconfig',
    'get_config',
    'set_config',
    'get_environment',
    'get_release',
    'get_revision',
    'get_version',
    'get_userversion',
    'get_productiondomain',
    'is_production',
]


@lru_cache(1)
def get_release():
    """Get the :term:`tagged version` of the current deployment.

    Which usually means the first line :file:`gaetk2-release.txt`.
    E.g. ``v180228-cg89bd1-production-dot-application.appspot.com``.
    """
    try:
        version = open('gaetk2-release.txt').readline().strip()
    except IOError:
        # if there is no version.txt file we return something fom the environment.
        version = '{}-{}'.format(
            os.environ.get('CURRENT_VERSION_ID', 'dev'), time.time()
        )
    return version


def get_version():
    """Do not use this."""
    warnings.warn(
        '`get_version` is deprecated, use `get_release`',
        DeprecationWarning,
        stacklevel=2,
    )
    return get_release()


@lru_cache(1)
def get_revision():
    """Get the git SHA1 revision of the current deployment.

    Get the first line of :file:`gaetk2-revision.txt`.
    E.g. ``14006259d78fa918054f774d20480b52e38c4707``.
    """
    try:
        version = open('gaetk2-revision.txt').readline().strip()
    except IOError:
        version = 'HEAD'
    return version


@lru_cache(1)
def get_userversion():
    u"""Return the User-Visible Version (eg `2018.11.3`)."""
    import yaml

    configyaml = yaml.safe_load(open('gaetk-conf.yaml'))
    return configyaml['userversion']


@lru_cache(1)
def get_uservisible_name():
    """Get the user visible public name of the Applicationt.

    E.g. ``huWaWi``.
    """
    import yaml

    configyaml = yaml.safe_load(open('gaetk-conf.yaml'))
    return configyaml['name']


@lru_cache(1)
def get_productiondomain():
    import yaml

    configyaml = yaml.safe_load(open('gaetk-conf.yaml'))
    return configyaml['productiondomain']


def get_environment():
    """Returns ``production``, ``staging``, ``testing`` or ``development`` depending on the Server Name.

    See :term:`production version`, :term:`staging version`, :term:`testing version`,
    and :term:`production version` for meaning.
    """
    if os.environ.get('SERVER_NAME', '').startswith('production'):
        return 'production'
    elif os.environ.get('SERVER_NAME', '').startswith('staging'):
        return 'staging'
    elif os.environ.get('SERVER_NAME', '').startswith('v') and os.environ.get(
        'SERVER_NAME', ''
    ).endswith('appspot.com'):
        return 'testing'
    elif os.environ.get('SERVER_NAME', '').startswith('test'):
        return 'test'
    return 'development'


def is_production():
    """checks if we can assume to run on a production version instance.

    ... unless called by the resttest-client.
    See :term:`production version` what this means.

    There are suble differences to
    :func:`get_environment()` - read the code for details.
    """
    if is_development():
        return False
    elif os.environ.get('SERVER_NAME', '').startswith(
        ('production', 'blue', 'green', 'staging', 'hotfix')
    ):
        return True
    elif os.environ.get('SERVER_NAME', '').startswith('v') and os.environ.get(
        'SERVER_NAME', ''
    ).endswith('appspot.com'):
        return False
    else:
        return False


def is_development():
    """Checks if we are running on a development system.

    See :term:`development version` what this means.
    """
    name = os.environ.get('SERVER_NAME', '')
    return (
        os.environ.get('SERVER_SOFTWARE', '').startswith('Development')
        or name.startswith('dev-')
        or name.startswith('test')
        or name.startswith('master')
    )
