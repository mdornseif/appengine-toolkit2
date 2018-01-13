#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.sentry - Client Instance and Helpers for sentry logging.

Builds on https://github.com/getsentry/raven-python

Created by Maximillian Dornseif on 2018-01-11.
Copyright (c) 2018 Maximillian Dornseif. MIT Licensed.
"""

import os

from gaetk2.tools.config import config as gaetkconfig
from gaetk2.tools.config import get_version
from gaetk2.tools.config import is_production


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


if gaetkconfig.SENTRY_DSN:
    import raven
    # from raven import breadcrumbs
    # from raven.middleware import Sentry
    from raven.transport.http import HTTPTransport

    if gaetkconfig.SENTRY_DSN and is_production():
        sentry_client = raven.Client(
            gaetkconfig.SENTRY_DSN,
            # inform the client which parts of code are yours
            release=get_version(),
            # exclude_paths=['cs.gaetk_common'],
            transport=HTTPTransport,
            tags=dict(module=os.environ.get('CURRENT_MODULE_ID')),
        )
        sentry_client.is_active = True


if not sentry_client:
    sentry_client = _Dummy()
