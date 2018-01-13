#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.wsgi - WSGI Middlewares.

Created by Maximillian Dornseif on 2018-01-11.
Copyright (c) 2018 Maximillian Dornseif. MIT Licensed.
"""
import logging

try:
    # if mixing gaetk1 and gaetk2 we need to use the same module
    # to get the rifght thread local storage
    from gaetk import gaesessions
except:
    from gaetk2 import _gaesessions as gaesessions

from gaetk2.tools.config import config as gaetkconfig
from gaetk2.tools.config import is_production


def wrap_errorhandling(application):
    """If Sentry is to be activated wrap the app in it."""
    # We use a Sentry WSGI Middleware to catch erros which are not
    # handled by the framework. Usually higher layers should catch
    # and display errors.

    if not gaetkconfig.SENTRY_DSN:
        return application

    from raven import Client
    from raven.middleware import Sentry
    return Sentry(application, Client(gaetkconfig.SENTRY_DSN))


def wrap_session(application):
    """Put gaesession around the app."""
    logging.debug('SessionMiddleware %r', gaetkconfig.SECRET)
    return gaesessions.SessionMiddleware(
        application,
        cookie_key=gaetkconfig.SECRET,
        ignore_paths='^/(hua|static|asserts)/.*'
    )


def webapp_add_wsgi_middleware(application):
    """Called with each WSGI application initialisation.

    The most common usage pattern is to just import that into
    ``appengine_config.py``::

        from gaetk2.wsgi import webapp_add_wsgi_middleware  # pylint: disable=W0611
    """

    application = wrap_session(application)
    logging.debug('SessionMiddleware added %s', application)
    # if ist_entwicklungsversion():
    #     app = gae_mini_profiler.profiler.ProfilerWSGIMiddleware(app)
    if is_production():
        application = wrap_errorhandling(application)
    return application
