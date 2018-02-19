#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.wsgi - WSGI Middlewares.

Created by Maximillian Dornseif on 2018-01-11.
Copyright (c) 2018 Maximillian Dornseif. MIT Licensed.
"""
# WARNING
# =======
# since we are imported by `appengine_config.py` we can not use
# gaetk2.config.gaetkconfig at module level because this
# wants to read from appengine_config.py via `lib_config`
import logging

try:
    # if mixing gaetk1 and gaetk2 we need to use the same module
    # to get the rifght thread local storage
    from gaetk import gaesessions
except:
    from gaetk2 import _gaesessions as gaesessions

logger = logging.getLogger(__name__)


def wrap_errorhandling(application):
    """If Sentry is to be activated wrap the app in it."""
    # We use a Sentry WSGI Middleware to catch erros which are not
    # handled by the framework. Usually higher layers should catch
    # and display errors.
    import gaetk2.tools.sentry
    from gaetk2.config import gaetkconfig
    from raven.middleware import Sentry

    if not gaetkconfig.SENTRY_DSN:
        return application
    return Sentry(application, gaetk2.tools.sentry.sentry_client)


def wrap_session(application):
    """Put gaesession around the app."""
    from gaetk2.config import gaetkconfig
    return gaesessions.SessionMiddleware(
        application,
        cookie_key=gaetkconfig.SECRET,
        ignore_paths='^/(hua|static|asserts)/.*'
    )


def webapp_add_wsgi_middleware(application):
    """Called with each WSGI application initialisation.

    The most common usage pattern is to just import it in
    ``appengine_config.py``::

        from gaetk2.wsgi import webapp_add_wsgi_middleware
    """

    # initialize Sentry logging if configured and not development
    import gaetk2.config
    import gaetk2.tools.sentry
    if not gaetk2.config.is_development():
        gaetk2.tools.sentry.setup_logging()

    application = wrap_session(application)
    # if ist_entwicklungsversion():
    #     app = gae_mini_profiler.profiler.ProfilerWSGIMiddleware(app)
    if not gaetk2.config.is_development():
        application = wrap_errorhandling(application)
    return application
