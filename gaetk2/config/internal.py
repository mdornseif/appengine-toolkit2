#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.config.internal - Configuration via appengine_config.py.

Created by Maximillian Dornseif on 2017-05-25.
Copyright (c) 2017, 2018 HUDORA. MIT licensed.
"""
import logging
import os

from google.appengine.api import lib_config


logger = logging.getLogger(__name__)


_gaetk_registry = lib_config.LibConfigRegistry('gaetk2_config')
gaetkconfig = _gaetk_registry.register(
    'GAETK2',
    dict(
        SECRET='',  # needed for everything
        TEMPLATE_DIRS=['./templates'],
        # auth
        JWT_SECRET_KEY=None,
        OAUTH_GOOGLE_CONFIG={},  # see https://console.developers.google.com/apis/credentials?project=huwawi2
        OAUTH_GOOGLE_ALLOWED_DOMAINS=['hudora.de'],
        AUTH0_DOMAIN='*unset*',
        AUTH0_CLIENT_ID='*unset*',
        AUTH0_CLIENT_SECRET=None,
        # Backup To Google CloudStorage (or BlobStore)
        BACKUP_GS_BUCKET=None,
        BACKUP_FILESYSTEM='gs',
        BACKUP_QUEUE='default',
        BACKUP_BLACKLIST=[],
        APP_NAME='',
        SENTRY_DSN='',
        SENTRY_PUBLIC_DSN='',
        SENTRY_SECURITY_TOKEN='',
        INBOUD_APP_IDS=[],
    )
)


# add our own template directory
gaetkconfig.TEMPLATE_DIRS.append(
    os.path.join(
        os.path.dirname(__file__),
        '../..',
        'templates'))

if not gaetkconfig.SECRET:
    logger.warning('No gaetk2_config.SECRET provided')
