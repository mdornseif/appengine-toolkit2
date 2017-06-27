#!/usr/bin/env python
# encoding: utf-8
"""
handlers/base.py - default Request Handler for gaetk2.

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2010-2017 HUDORA. All rights reserved.
"""

import logging
import os
import time
import urlparse

from google.appengine.api import memcache
from google.appengine.api import users

import jinja2
import webapp2

from .. import _jinja_filters
from ..tools import hujson2
from ..tools.config import config
from ..tools.config import is_production
from gaetk.lib._gaesessions import get_current_session


_jinja_env_cache = None


class BasicHandler(webapp2.RequestHandler):
    """Generic Handler functionality.

    provides

    * `self.session` which is based on https://github.com/dound/gae-sessions.
    * `abs_url()` ensures URLs are absolute
    * `is_production()` checks if running in development mode
    """

    default_cachingtime = None

    def __init__(self, *args, **kwargs):
        """Initialize RequestHandler."""
        self.credential = None
        self.session = {}   # session is only available later in `dispatch()`.
        # Careful! `webapp2.RequestHandler` does not call super()!
        super(BasicHandler, self).__init__(*args, **kwargs)

    # helper methods

    def abs_url(self, url):
        """Converts an relative into an absolute URL."""
        if self.request:
            return urlparse.urljoin(self.request.uri, url)
        return urlparse.urljoin(os.environ.get('HTTP_ORIGIN', ''), url)

    def is_sysadmin(self):
        """Returns if the currently logged in user is admin."""
        # Google App Engine Administrators
        if users.is_current_user_admin():
            return True
        # Requests from localhost (on dev_appserver) are always admin
        if self.request.remote_addr == '127.0.0.1':
            return True
        # User with Admin permissions via Credential entities
        if not hasattr(self, 'credential'):
            return False
        elif self.credential is None:
            return False
        return getattr(self.credential, 'sysadmin', False)

    def has_permission(self, permission):
        """
        Checks if user has a given permission.

        Returns False, if no user is logged in.
        """
        if self.credential:
            return permission in self.credential.permissions
        return False

    def render(self, values, template_name):
        """Render a Jinja2 Template and write it to the client."""
        start = time.time()
        self._render_to_client(values, template_name)
        delta = time.time() - start
        if delta > 500:
            logging.warn("rendering took %d ms", (delta * 1000.0))

    def return_text(self, text, status=200, content_type='text/plain', encoding='utf-8'):
        """Quick and dirty sending of some plaintext to the client."""
        self.response.set_status(status)
        self.response.headers['Content-Type'] = content_type
        if isinstance(text, unicode):
            text = text.encode(encoding)
        self.response.out.write(text)
        self.response.out.write('\n')

    # to be overwritten / extended

    def default_template_vars(self, values):
        """Helper to provide additional values to HTML Templates. To be overwritten in subclasses. E.g.

        def default_template_vars(self, values):
            myval = dict(credential_empfaenger=self.credential_empfaenger,
                         navsection=None)
            myval.update(values)
            return myval
        """
        ret = dict(
            request=self.request,
            credential=self.credential,
            is_sysadmin=self.is_sysadmin,
            gaetk_production=is_production(),
            gaetk_logout_url='/gaetk2/auth/logout',
        )
        ret.update(values)
        return ret

    def add_jinja2env_globals(self, env):
        """To be everwritten  by subclasses.

        Eg:

            env.globals['bottommenuurl'] = '/admin/'
            env.globals['bottommenuaddon'] = '<i class="fa fa-area-chart"></i> Admin'
            env.globals['profiler_includes'] = gae_mini_profiler.templatetags.profiler_includes

        """
        super(BasicHandler, self).add_jinja2env_globals(env)

    def response_hook(self, response, method, *args, **kwargs):
        """Function to transform response. To be overwritten."""
        return response

    def finished_hook(self, response, method, *args, **kwargs):
        """Function to allow logging etc. To be overwritten."""
        # not called when exceptions are raised

        # simple sample implementation: check compliance for headers/wsgiref
        for name, val in self.response.headers.items():
            if not (isinstance(name, basestring) and isinstance(val, basestring)):
                logging.error("Header names and values must be strings: {%r: %r} in %s(%r, %r) => %r",
                              name, val, method, args, kwargs, response)

    # internal stuff

    def _clear_session(self):
        logging.info("clearing session")
        self.session['uid'] = None
        if self.session.is_active():
            self.session.terminate()
        self.session.regenerate_id()

    def _create_jinja2env(self):
        """Initialise and return a jinja2 Environment instance."""
        global _jinja_env_cache

        if not _jinja_env_cache:
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(config.TEMPLATE_DIRS),
                auto_reload=False,  # unneeded on App Engine production
                trim_blocks=True,  # first newline after a block is removed
                # lstrip_blocks=True,
                bytecode_cache=jinja2.MemcachedBytecodeCache(memcache, timeout=3600)
            )
            _jinja_filters.register_custom_filters(env)
            self.add_jinja2env_globals(env)
            _jinja_env_cache = env

        return _jinja_env_cache

    def _render_to_client(self, values, template_name):
        """Sends the rendered content of a Jinja2 Template to Output.

        Per default the template is provided with contents of `default_template_vars()` plus everything
        which is given in `values`.
        """
        env = self._create_jinja2env()
        try:
            template = env.get_template(template_name)
        except jinja2.TemplateNotFound:
            # better error reporting - we want to see the name of the base template
            raise jinja2.TemplateNotFound(template_name)
        except jinja2.TemplateAssertionError:
            # better logging
            logging.debug("env=%r", env)
            logging.debug("env.globals=%r", env.globals)
            logging.debug("env.filters=%r", env.filtersx)
            raise

        myval = self.default_template_vars(values)
        try:
            template.stream(myval).dump(self.response.out)
        except jinja2.TemplateNotFound:
            # better error reporting
            # TODO: https://docs.sentry.io/clientdev/interfaces/template/
            logging.info('jinja2 environment: %s', env)
            logging.info('template dirs: %s', config.TEMPLATE_DIRS)
            raise

    def _set_cache_headers(self, caching_time=None):
        """Set Cache Headers.

        The parameter `caching_time` describes the number of seconds,
        the result should be cachet at frontend caches.
        None means no Caching-Headers. Se also `default_cachingtime`
        0 or negative Values generate an comand to disable all caching.
        """
        ct = self.default_cachingtime
        if caching_time is not None:
            ct = caching_time

        if ct is not None:
            if ct > 0:
                self.response.headers['Cache-Control'] = 'max-age=%d public' % ct
            elif ct <= 0:
                self.response.headers['Cache-Control'] = 'no-cache public'

    def dispatch(self):
        """Dispatches the requested method."""
        request = self.request
        method_name = request.route.handler_method
        if not method_name:
            method_name = webapp2._normalize_handler_method(request.method)

        method = getattr(self, method_name, None)
        if method is None:
            # 405 Method Not Allowed.
            valid = ', '.join(webapp2._get_handler_methods(self))
            self.abort(405, headers=[('Allow', valid)])

        # The handler only receives *args if no named variables are set.
        # TODO: Warum?
        args, kwargs = request.route_args, request.route_kwargs
        if kwargs:
            args = ()

        # bind session on dispatch (not in __init__)
        try:
            self.session = get_current_session()
        except AttributeError:
            # session handling not activated
            self.session = {}  # pylint: disable=R0204

        if hasattr(self, 'load_credential') and callable(self.load_credential):
            self.load_credential()
        # Give authentication hooks opportunity to do their thing
        if hasattr(self, 'authchecker') and callable(self.authchecker):
            self.authchecker(method, *args, **kwargs)

        try:
            response = method(*args, **kwargs)
        except Exception, e:
            return self.handle_exception(e, self.app.debug)
        response = self.response_hook(response, method, *args, **kwargs)
        if response:
            assert isinstance(response, webapp2.Response)

        self._set_cache_headers()
        self.finished_hook(response, method, *args, **kwargs)
        return response


class JsonBasicHandler(BasicHandler):
    """Handler which is specialized for returning JSON.

    Excepts the method to return

    * dict(), e.g. `{'foo': bar}`

    Dict is converted to JSON. `status` is used as HTTP status code. `cachingtime`
    is used to generate a `Cache-Control` header. If `cachingtime is None`, no header
    is generated. `cachingtime` defaults to 60 seconds.
    """

    # Our default caching is 60s
    default_cachingtime = 60

    def serialize(self, content):
        """convert content to JSON."""
        return hujson2.dumps(content)

    def response_hook(self, response, method, *args, **kwargs):
        """Function to transform response. To be overwritten."""
        # do serialisation bef ore generating Content-Type Header so Errors will display nicely
        content = self.serialize(response) + '\n'

        # If we have gotten a `callback` parameter, we expect that this is a
        # [JSONP](http://en.wikipedia.org/wiki/JSONP#JSONP) can and therefore add the padding
        if self.request.get('callback', None):
            response = "%s (%s)" % (self.request.get('callback', None), response)
            self.response.headers['Content-Type'] = 'text/javascript'
        else:
            self.response.headers['Content-Type'] = 'application/json'
        return webapp2.Response(content)
