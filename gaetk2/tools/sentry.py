#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.sentry - Client Instance and Helpers for sentry logging.

Builds on https://github.com/getsentry/raven-python

Created by Maximillian Dornseif on 2018-01-11.
Copyright (c) 2018 Maximillian Dornseif. MIT Licensed.
"""
import logging
import os

from gaetk2.tools import hujson2
from gaetk2.tools.config import config as gaetkconfig
from gaetk2.tools.config import get_version
from gaetk2.tools.config import is_development

logger = logging.getLogger(__name__)
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


if gaetkconfig.SENTRY_DSN:
    import raven
    import raven.breadcrumbs
    from raven.transport.http import HTTPTransport

    if gaetkconfig.SENTRY_DSN and not is_development():
        # see https://docs.sentry.io/clients/python/advanced/
        sentry_client = raven.Client(
            gaetkconfig.SENTRY_DSN,
            # inform the client which parts of code are yours
            release=get_version(),
            transport=HTTPTransport,
            tags={
                'MODULE_ID': os.environ.get('CURRENT_MODULE_ID'),
                'VERSION_ID': os.environ.get('CURRENT_VERSION_ID'),
                'APPLICATION_ID': os.environ.get('APPLICATION_ID'),
                'GAE_RUNTIME': os.environ.get('GAE_RUNTIME'),
                'GAE_ENV': os.environ.get('GAE_ENV'),
            },
            exclude_paths=['cs', 'google'],
            auto_log_stacks=True,
            # environment = 'staging'
            # TODO: study https://github.com/getsentry/raven-python/blob/master/raven/versioning.py
            # https://docs.sentry.io/clientdev/interfaces/repos/
            # this results in `ImportError: Import by filename is not supported`:
            # repos={
            #     'lib/appengine-toolkit2': {
            #         # the name of the repository as registered in Sentry
            #         'name': 'mdornseif/appengine-toolkit2',
            #     }
            # }
            # # ignore_exceptions = ['Http404', ValueError, ]
        )
        sentry_client.is_active = True

    def note(category, message=None, data=None):
        """bei Bedarf strukturiert loggen, Sentry breadcrumbs """
        assert category in ['rpc', 'input', 'external', 'storage', 'auth', 'flow']
        if not data:
            data = dict()

        # 'flatten' data
        data = hujson2.loads(hujson2.dumps(data))

        raven.breadcrumbs.record(
            data=data,
            category=category,
            message=message
        )
else:
    def note(category, message=None, data=None):
        assert category in ['rpc', 'input', 'external', 'storage', 'auth', 'flow']
        logger.debug("%s %r", message, data)


if not sentry_client:
    sentry_client = _Dummy()

sentry_client.note = note


def setup_logging():
    """Set up logging to sentry if Sentry is configured."""
    if gaetkconfig.SENTRY_DSN:
        import raven.handlers.logging
        import raven.conf
        # Configure the default client
        handler = raven.handlers.logging.SentryHandler(gaetkconfig.SENTRY_DSN)
        handler.setLevel(logging.ERROR)
        raven.conf.setup_logging(handler)
