#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gaetk2.sentry - Client Instance and Helpers for sentry logging.

Builds on https://github.com/getsentry/raven-python

Created by Maximillian Dornseif on 2018-01-11.
Copyright (c) 2018 Maximillian Dornseif. MIT Licensed.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import os
import warnings

from gaetk2.config import gaetkconfig
from gaetk2.config import get_environment
from gaetk2.config import get_release
from gaetk2.config import is_development
from gaetk2.tools import hujson2


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
sentry_client = None


class _Dummy(object):
    """A class just droping any requests.

    It also evaluates to `False`.
    """

    def __bool__(self):
        return False

    __nonzero__ = __bool__

    def captureException(*args, **kwargs):  # noqa: N802
        return 'dummy-id'

    def captureMessage(self, message, **kwargs):  # noqa: N802
        return

    def user_context(*args, **kwargs):
        return

    def tags_context(*args, **kwargs):
        return

    def extra_context(*args, **kwargs):
        return

    def http_context(*args, **kwargs):
        return


if gaetkconfig.SENTRY_DSN and os.environ.get('SERVER_SOFTWARE', '').startswith(
    'Google App Engine'
):
    import raven
    import raven.breadcrumbs
    from raven.transport.http import HTTPTransport

    if gaetkconfig.SENTRY_DSN and not is_development():
        # see https://docs.sentry.io/clients/python/advanced/
        sentry_client = raven.Client(
            gaetkconfig.SENTRY_DSN,
            release=get_release(),
            transport=HTTPTransport,
            tags={
                'MODULE_ID': os.environ.get('CURRENT_MODULE_ID'),
                'VERSION_ID': os.environ.get('CURRENT_VERSION_ID'),
                'APPLICATION_ID': os.environ.get('APPLICATION_ID'),
                'GAE_RUNTIME': os.environ.get('GAE_RUNTIME'),
                'GAE_ENV': os.environ.get('GAE_ENV'),
            },
            # This results in crashes
            # repos={
            #     'huExpress': {
            #         # the name of the repository as registered in Sentry
            #         'name': 'hudora/huExpress',
            #         'commit': get_revision()
            #     }
            # },
            # https://docs.sentry.io/clientdev/interfaces/repos/
            # this results in `ImportError: Import by filename is not supported`:
            # repos={
            #     'lib/appengine-toolkit2': {
            #         # the name of the repository as registered in Sentry
            #         'name': 'mdornseif/appengine-toolkit2',
            #     }
            # }
            include_paths=['modules', 'common'],
            exclude_paths=['google', 'raven', 'logging', 'site-packages'],
            auto_log_stacks=True,
            environment=get_environment(),
            # TODO: study https://github.com/getsentry/raven-python/blob/master/raven/versioning.py
            # # ignore_exceptions = ['Http404', ValueError, ]
        )
        sentry_client.is_active = True

    def note(category, message=None, data=None, typ=None):
        """bei Bedarf strukturiert loggen, Sentry breadcrumbs."""
        assert category in [
            'http',
            'navigation',
            'user',
            'rpc',
            'input',
            'external',
            'storage',
            'auth',
            'flow',
        ]
        if not data:
            data = {}

        # see https://docs.sentry.io/clients/python/breadcrumbs/
        # and https://github.com/getsentry/sentry/blob/master/src/sentry/static/sentry/less/group-detail.less
        # for valid values
        if category == 'auth':
            category == 'user'
            warnings.warn(
                'use `user` instead of `auth`', DeprecationWarning, stacklevel=2
            )
        if category == 'http':
            category = 'rpc'
            typ = 'http'

        # 'flatten' data
        jsondata = hujson2.dumps(data)
        data = hujson2.loads(jsondata)
        if len(jsondata) > 10000:
            # shorten data
            try:
                if hasattr(data, 'items'):
                    for key, value in data.items():
                        data[key] = value[:200]
                else:
                    data = str(data)[:1024]
            except Exception as e:
                data = {'error': 'data too big', 'exception': str(e)}

        logger.debug('note: %s: %s %r', category, message, data)
        raven.breadcrumbs.record(
            data=data, category=category, type=typ, message=message
        )


else:

    def note(category, message=None, data=None):
        """Dummy Funktion, die loggt statt zu Sentry zu senden."""
        assert category in [
            'http',
            'navigation',
            'user',
            'rpc',
            'input',
            'external',
            'storage',
            'auth',
            'flow',
        ]
        logger.debug('note: %s: %s %r', category, message, data)


if not sentry_client:
    sentry_client = _Dummy()

sentry_client.note = note


def setup_logging():
    """Set up logging to sentry if Sentry is configured."""
    if gaetkconfig.SENTRY_DSN and sentry_client.is_active:
        import raven.handlers.logging
        import raven.conf

        # Configure the default client
        handler = raven.handlers.logging.SentryHandler(sentry_client)
        handler.setLevel(logging.ERROR)
        raven.conf.setup_logging(handler)
