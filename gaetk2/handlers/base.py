#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gaetk2.handlers.base - default Request Handler for gaetk2.

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2010-2019 HUDORA. All rights reserved.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import inspect
import logging
import os
import os.path
import time
import urlparse
import warnings

from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.api.app_identity import get_application_id

import jinja2
import webapp2

from gaetk2 import exc
from gaetk2 import jinja_filters
from gaetk2.config import gaetkconfig
from gaetk2.config import get_release
from gaetk2.config import is_development
from gaetk2.config import is_production
from gaetk2.tools import hujson2
from gaetk2.tools import introspection
from gaetk2.tools.sentry import sentry_client


try:
    # if mixing gaetk1 and gaetk2 we need to use the same module
    # to get the rifght thread local storage
    from gaetk import gaesessions
except:
    from gaetk2 import _gaesessions as gaesessions

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
_jinja_env_cache = None

# Your app usually will extend a `BasicHandler` or `DefaultHandler`
# (for added authentication). These based on
# [webapp2.RequestHandler](http://webapp2.readthedocs.io/en/latest/api/webapp2.html#webapp2.RequestHandler)
# See [The webapp2 Guide](http://webapp2.readthedocs.io/en/latest/guide/handlers.html)
# for an introduction.


class BasicHandler(webapp2.RequestHandler):
    """Generic Handler functionality.

    You usually overwrite :meth:`get()` or :meth:`post()` and call
    :meth:`render()` in there. See :ref:`gaetk2.handlers` for examples.

    For Returning Data to the user you can access the `self.response` object
    or use :meth:`return_text` and :meth:`render`. See :meth:`get_jinja2env`
    to understand the jinja2 context being used.

    Helper functions are :meth:`abs_url()` and :meth:`is_production`.

    See Also:
        :meth:`is_sysadmin`, :meth:`is_staff` and :meth:`has_permission`
        are meant to work with
        :class:`~gaetk2.handlers.authentication.AuthenticationReaderMixin`
        for ``self.request`` see `webapp2 Documentation
        <http://webapp2.readthedocs.io/en/latest/guide/request.html
        #common-request-attributes>`_

    Attributes:
        request: See webapp2 documentation
        credential: authenticated user, see :class:`~gaetk2.handlers.authentication.AuthenticationReaderMixin`
        session: current session which is based on https://github.com/dound/gae-sessions.
        default_cachingtime (None or int): Class Variable. Which cache headers to generate,
            see :meth:`_set_cache_headers`.

    Note:
        gaetk2 adds various variables to the template context. Other mixins provide
        additional template variables. See the Index :ref:`genindex` under "Template Context"
        to get an overview.

        These :index:`Template Variables <Template Context>` are provided:

        * :index:`request <Template Context; request>`
        * :index:`credential <Template Context; credential>`
        * :index:`is_staff <Template Context; is_staff>` (self.is_staff())
        * :index:`is_sysadmin <Template Context; is_sysadmin>` (self.is_sysadmin())
        * :index:`gaetk_production <Template Context; gaetk_production>` (is_production())
        * :index:`gaetk_development <Template Context; gaetk_development>` (is_development())
        * :index:`gaetk_release <Template Context; gaetk_development>` (get_release())
        * :index:`gaetk_app_name <Template Context; gaetk_app_name>` (gaetkconfig.APP_NAME)
        * :index:`gaetk_gae_version <Template Context; gaetk_gae_version>` (CURRENT_VERSION_ID)
        * :index:`gaetk_sentry_dsn <Template Context; gaetk_app_name>` (gaetkconfig.APP_NAME)
        * :index:`gaetk_logout_url <Template Context; gaetk_logout_url>`
        * :index:`gaetk_path <Template Context; gaetk_path>` (self.request.path)


    .. _handler-hook-mechanism:

    Warning:
        :class:`BasicHandler` implements a rather unusual way to implement
        Multi-Inherance/Mix-Ins. Instead of insisting that every parent class
        and everty Mix-In implements all possible methods and calls super on them
        :class:`BasicHandler` uses a custom dispatch mechanism which calls all
        methods in all parent and sibling classes.

        The following functions are called on all parent and sibling classes:

        * :meth:`pre_authentication_hook`.
        * :meth:`authentication_preflight_hook`.
        * :meth:`authentication_hook`.
        * :meth:`authorisation_hook`.
        * :meth:`method_preperation_hook`.
        * :meth:`finished_hook` - called even if a :exc:`exc.HTTPException` < 500 occurs.

        :meth:`build_context` is special because the output is "chained".
        So the rendering is done with something like the output of
        ``Child.build_context(Parent.build_context(MixIn.build_context({})))``

    :meth:`response_overwrite` and :meth:`finished_overwrite` can be overwritten
    to provide special functionality like in :class:`JsonBasicHandler`.

    You are encouraged to study the source code of :class:`BasicHandler`!

    """

    default_cachingtime = None

    def __init__(self, *args, **kwargs):
        """Initialize RequestHandler."""
        self.credential = None
        self.session = {}
        self._last_template_exception = None
        # Careful! `webapp2.RequestHandler` does not call super()!
        super(BasicHandler, self).__init__(*args, **kwargs)
        # ... so we route arround that
        super(webapp2.RequestHandler, self).__init__()

    # helper methods

    def abs_url(self, url):
        """Converts an relative into an qualified absolute URL.

        Args:
            url (str): an path to a web resource.

        Returns:
            str: A fully qualified url.

        Example:
                >>> BasicHandler().abs_url('/foo')
                'http://server.example.com/foo'

        """
        if self.request:
            return urlparse.urljoin(self.request.uri, url)
        return urlparse.urljoin(os.environ.get('HTTP_ORIGIN', ''), url)

    def is_sysadmin(self):
        """Checks if the current user is logged in as a SysOp/SystemAdministrator.

        We use various souces to deterine the Status of the user.
        Returns `True` if:

        * google.appengine.api.users.is_current_user_admin()
        * the request came from `127.0.0.1` local address
        * `self.credential.sysadmin == True`

        Returns:
            boolean: the status of the currently logged in user.

        """
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

    def is_staff(self):
        """Returns if the current user is considered internal.

        This means he has access to not only his own but to all
        settings pages, etc.

        * :meth:`is_sysadmin`
        * `self.credential.staff == True`

        Returns:
            boolean: the status of the currently logged in user is considered internal.

        """
        if self.is_sysadmin():
            return True
        elif self.credential is None:
            return False
        return getattr(self.credential, 'staff', False)

    def has_permission(self, permission):
        """Checks if user has a given permission."""
        if self.credential:
            return permission in self.credential.permissions
        return False

    def render(self, values, template_name):
        """Render a Jinja2 Template and write it to the client.

        If rendering takes an unusual long time this is logged.

        Parameters:
            values (dict): variables for template context.
            template_name (str): name of the template to render.

        See Also:
            :meth:`build_context()`also provides data to the template
            context and is often extended by plugins. See
            :class:`BasicHandler` docsting for standard template variables.

        """
        start = time.time()
        self._render_to_fd(values, template_name, self.response.out)
        delta = time.time() - start
        if delta > 500:
            LOGGER.warn('rendering took %d ms', (delta * 1000.0))

    def return_text(
        self, text, status=200, content_type='text/plain', encoding='utf-8'
    ):
        """Quick and dirty sending of some plaintext to the client.

        Parameters:
            text (str or unicode): Data to be sent to the cliend. A NEWLINE is appended.
            status (int): status code to be sent to the client. Defaults to 200.
            content_type: to be sent to the client in respective header.
            encoding: to be used when sending to the client.

        """
        self.response.set_status(status)
        self.response.headers[b'Content-Type'] = str(content_type)
        if isinstance(text, unicode):
            text = text.encode(encoding)
        self.response.out.write(text)
        self.response.out.write('\n')

    # to be overwritten / extended

    def build_context(self, values):
        """Helper to provide additional request-specific values to HTML Templates.

        Will be called on all Parents and MixIns, no `super()` needed.

        def build_context(self, values):
            myvalues = dict(navsection='kunden', ...)
            myvalues.update(values)
            return myvalues
        """
        ret = {
            'request': self.request,
            'credential': self.credential,
            'gaetk_logout_url': '/gaetk2/auth/logout',
            'gaetk_path': self.request.path,
            'is_staff': self.is_staff(),
            'is_sysadmin': self.is_sysadmin(),
        }
        ret.update(values)
        return ret

    def _add_jinja2env_globals(self, env):
        """Helper to provide additional Globals to Jinja2 Environment.

        This should be considered one time initialisation.

        Example::
            env.globals['bottommenuurl'] = '/admin/'
            env.globals['bottommenuaddon'] = '<i class="fa fa-area-chart"></i> Admin'
            env.globals['profiler_includes'] = gae_mini_profiler.templatetags.profiler_includes

        """
        if not gaetkconfig.APP_NAME:
            gaetkconfig.APP_NAME = get_application_id().capitalize()
        env.globals.update(
            dict(
                gaetk_production=is_production(),
                gaetk_development=is_development(),
                gaetk_release=get_release(),
                gaetk_app_name=gaetkconfig.APP_NAME,
                gaetk_sentry_dsn=gaetkconfig.SENTRY_PUBLIC_DSN,
                gaetk_gae_version=os.environ.get('CURRENT_VERSION_ID', 'dev'),
            )
        )
        return env

    def debug(self, message, *args):
        """Detailed logging for development.

        This logging will only happen, if :class:`WSGIApplication` was
        initialized with ``debug=True``. Is meant for local inspection
        of the stack during development.
        Messages are prefixed with the method name from where they are called.
        """
        if self.app.debug:
            curframe = inspect.currentframe()
            calframe = inspect.getouterframes(curframe, 2)
            callfile = calframe[1][1].split('/')[-1]
            callfunc = calframe[1][3]
            message = '{} {}(): {}'.format(callfile, callfunc, message)
            LOGGER.debug(message, *args)
            # filename, lineno, function, code_context, index).

    # For MixIns:

    def pre_authentication_hook(self, method_name, *args, **kwargs):
        """Might do redirects before even authentication data is loaded.

        Called on all parent and sibling classes.
        """
        return

    def authentication_preflight_hook(self, method_name, *args, **kwargs):
        """Might load Authentication data from Headers.

        Called on all parent and sibling classes.
        """
        return

    def authentication_hook(self, method_name, *args, **kwargs):
        """Might verify Authentication data.

        Called on all parent and sibling classes.
        """
        return

    def authorisation_hook(self, method_name, *args, **kwargs):
        """Might check if authenticated user is authorized.

        Called on all parent and sibling classes.
        """
        return

    def method_preperation_hook(self, method_name, *args, **kwargs):
        """Is Called just before GEP, POST, PUT, DELETE etc. is called.

        Used to provide common data in child classes.
        E.g. to set up variables, load Date etc.
        """
        return

    def response_overwrite(self, response, method, *args, **kwargs):
        """Function to transform response. To be overwritten."""
        if hasattr(self, 'response_overwrite_overwrite'):  # hack for JsonMixin
            return self.response_overwrite_overwrite(response, method, *args, **kwargs)
        return response

    def finished_hook(self, method, *args, **kwargs):
        """To be called at the end of an request."""

    def finished_overwrite(self, response, method, *args, **kwargs):
        """Function to allow logging etc. To be overwritten."""
        # not called when exceptions are raised

    def clear_session(self):
        """Terminate the session reliably."""
        LOGGER.info('clearing session')
        self.session['uid'] = None
        if self.session and self.session.is_active():
            self.session.terminate()
        self.session.regenerate_id()

    # internal stuff

    def get_jinja2env(self):
        """Initialise and return a jinja2 Environment instance."""
        global _jinja_env_cache

        if not _jinja_env_cache:
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(gaetkconfig.TEMPLATE_DIRS),
                auto_reload=False,  # unneeded on App Engine production
                trim_blocks=True,  # first newline after a block is removed
                # lstrip_blocks=True,
                bytecode_cache=jinja2.MemcachedBytecodeCache(memcache, timeout=3600),
                # This needs jinja2 > Version 2.8
                autoescape=jinja2.select_autoescape(['html', 'xml']),
            )

            env.exception_handler = self._jinja2_exception_handler

            jinja_filters.register_custom_filters(env)
            env.policies['json.dumps_function'] = hujson2.htmlsafe_json_dumps
            env = self._add_jinja2env_globals(env)
            _jinja_env_cache = env

        return _jinja_env_cache

    # internal stuff

    def _jinja2_exception_handler(self, traceback):
        """Is called during Jinja2 Exception processing to provide logging."""
        global _jinja_env_cache
        # see http://jinja.pocoo.org/docs/2.10/faq/#my-tracebacks-look-weird-what-s-happening
        # see http://flask.pocoo.org/snippets/74/
        # here we still get the correct traceback information, it will be discarded later on
        LOGGER.info('Template globals = %r', getattr(_jinja_env_cache, 'globals', None))
        LOGGER.exception('Template Exception %r', traceback.render_as_text())
        # this logs the correct exception to Sentry
        # but results in a duplocate incorrect one.
        sentry_client.captureException(exc_info=traceback.exc_info)
        self._last_template_exception = traceback.exc_info[1]

    def _render_to_fd(self, values, template_name, fd):
        """Sends the rendered content of a Jinja2 Template to Output.

        Per default the template is provided with output of ``build_context(values)``.
        """
        env = self.get_jinja2env()
        try:
            template = env.get_template(template_name)
        except jinja2.TemplateNotFound:
            # better error reporting - we want to see the name of the base template
            raise jinja2.TemplateNotFound(template_name)
        except (jinja2.TemplateAssertionError, jinja2.TemplateRuntimeError):
            # better logging
            LOGGER.debug('values=%r', values)
            LOGGER.debug('env.globals=%r', env.globals.keys())
            LOGGER.debug('env.filters=%r', env.filters.keys())
            if self._last_template_exception:
                # at his point the treceback is damaged
                # but we send it earlier on to Sentry.
                self._last_template_exception._hide_from_sentry = True
                raise self._last_template_exception
            raise

        # to collect template variables from all Parent-Classes and MisIns.
        # this keeps parents from having all to implement the function and
        # use `super()`
        values = self._reduce_all_inherited('build_context', values)

        # for debugging provide access to all variables if `_gaetk_dump` is
        # given in the URL
        if self.is_sysadmin() and self.request.get('_gaetk_dump'):
            self.body = ''
            self.response.headers['Content-Type'] = 'application/json'
            fd.write(
                hujson2.htmlsafe_json_dumps(
                    {
                        'gaetk_globalcontext_json': env.globals,
                        'gaetk_localcontext_json': values,
                    }
                )
            )
            return None

        try:
            template.stream(values).dump(fd, encoding='utf-8')
            # we do not want to rely on webob.Response magically transforming unicode
        except jinja2.TemplateNotFound:  # can happen for includes etc.
            # better error reporting
            # TODO: https://docs.sentry.io/clientdev/interfaces/template/
            LOGGER.info('jinja2 environment: %s', vars(env))
            LOGGER.info('template dirs: %s', gaetkconfig.TEMPLATE_DIRS)
            raise

        # TODO: warn about undeclared variables
        # http://jinja.pocoo.org/docs/dev/api/#the-meta-api
        # from jinja2 import Environment, PackageLoader, meta
        # env = Environment(loader=PackageLoader('gummi', 'templates'))
        # template_source = env.loader.get_source(env,   'page_content.html')[0]
        # parsed_content = env.parse(template_source)
        # meta.find_undeclared_variables(parsed_content)

    def _set_cache_headers(self, caching_time=None):
        """Set Cache Headers.

        Parameters:
            caching_time (None or int): the number of seconds, the result should
                be  cachetd at frontend caches. ``None`` means no Caching-Headers.
                See also :any:`default_cachingtime`. `0` or negative Values generate
                an comand to disable all caching.

        """
        ct = self.default_cachingtime
        if caching_time is not None:
            ct = caching_time

        if ct is not None:
            if ct > 0:
                self.response.headers[b'Cache-Control'] = b'max-age=%d public' % ct
            elif ct <= 0:
                self.response.headers[b'Cache-Control'] = b'no-cache public'

    def _call_all_inherited(self, funcname, *args, **kwargs):
        """In all SuperClasses call `funcname` - if it exists."""
        # We don't want to burden all mixins with implementing
        # the required methods and calling `super().meth()`
        # so we don't use a call chain provided by the
        # Parents and MixIns but instead work through them as a list.
        # it also reverses the call order

        self._debug_callstack = []
        # This code is based in ideas from Guido van Rossum, see
        # https://www.python.org/download/releases/2.2/descrintro/#cooperation
        for cls in reversed(self.__class__.__mro__):
            if funcname in cls.__dict__:
                x = cls.__dict__[funcname]
                if hasattr(x, '__get__'):
                    x = x.__get__(self)
                if callable(x):
                    self._debug_callstack.append(x)
                    LOGGER.debug(
                        'calling %s.%s(*%r, **%r)', cls, funcname, args, kwargs
                    )
                    try:
                        x(*args, **kwargs)
                    except TypeError as e:
                        e.message = '{} while calling {}.{}(*{!r}, **{!r})'.format(
                            str(e), cls, funcname, args, kwargs
                        )
                        LOGGER.exception(
                            'failure calling %s.%s(*%r, **%r)',
                            cls,
                            funcname,
                            args,
                            kwargs,
                        )
                        raise e
                    except BaseException as e:
                        if not isinstance(e, exc.HTTPException):
                            LOGGER.exception(
                                'failure calling %s.%s(*%r, **%r)',
                                cls,
                                funcname,
                                args,
                                kwargs,
                            )
                        raise
                else:
                    LOGGER.warn('not clallable: %r', x)

    def _reduce_all_inherited(self, funcname, initial):
        """In all SuperClasses call `funcname` with the output of the previus call."""
        # We don't want to burden all mixins with mplementing
        # the required methods and calling `super().meth()`
        # so we don't use a call chaon provided by the
        # Parents and MixIns but instead work through them as a list.
        # it also reverses the call order

        ret = initial
        # This code is based in ideas from Guido van Rossum, see
        # https://www.python.org/download/releases/2.2/descrintro/#cooperation
        for cls in reversed(self.__class__.__mro__):
            if funcname in cls.__dict__:
                x = cls.__dict__[funcname]
                if hasattr(x, '__get__'):
                    x = x.__get__(self)
                if callable(x):
                    LOGGER.debug('reducing %s.%s(%r)', cls, funcname, ret)
                    try:
                        ret = x(ret)
                    except:
                        LOGGER.debug('error reducing %s.%s(%r)', cls, funcname, ret)
                        raise
                else:
                    LOGGER.warn('not callable: %r', x)
                if ret is None:
                    raise RuntimeError(
                        '{}.{} did not provide a return value'.format(cls, funcname)
                    )
        return ret

    def dispatch(self):
        """Dispatches the requested method fom the WSGI App.

        Meant for internal use by the stack.
        """
        request = self.request
        method_name = request.route.handler_method
        if not method_name:
            method_name = webapp2._normalize_handler_method(request.method)

        method = getattr(self, method_name, None)
        if hasattr(self, '__class__'):
            sentry_client.tags_context(
                {'handler': self.__class__.__name__, 'method': method_name}
            )

        if method is None:
            # 405 Method Not Allowed.
            valid = b', '.join(webapp2._get_handler_methods(self))
            raise exc.HTTP405_HTTPMethodNotAllowed(
                'Method not allowed in {}'.format(self.__class__.__name__),
                headers=[(b'Allow', valid)],
            )

        # The handler only receives *args if no named variables are set.
        args, kwargs = request.route_args, request.route_kwargs
        if kwargs:
            args = ()

        # bind session on dispatch (not in __init__)
        try:
            self.session = gaesessions.get_current_session()
        except AttributeError:
            # probably session middleware not loaded
            self.session = {}

        if str(self.session) != 'uninitialized session':
            sentry_client.note(
                'storage', 'Session loaded', data=dict(session=self.session)
            )

        try:
            self._call_all_inherited(
                'pre_authentication_hook', method_name, *args, **kwargs
            )
            self._call_all_inherited(
                'authentication_preflight_hook', method_name, *args, **kwargs
            )
            self._call_all_inherited(
                'authentication_hook', method_name, *args, **kwargs
            )
            self._call_all_inherited('authorisation_hook', method_name, *args, **kwargs)
            self._call_all_inherited(
                'method_preperation_hook', method_name, *args, **kwargs
            )
            try:
                response = method(*args, **kwargs)
            except TypeError:
                # parameter missmatch is the error we see most often
                # so help to pin down where it happens
                klass = introspection.get_class_that_defined_method(method)
                methname = method.__name__
                sourcepos = '{}:{}'.format(
                    os.path.basename(method.__func__.__code__.co_filename),
                    method.__func__.__code__.co_firstlineno,
                )
                LOGGER.debug(
                    'method called: %s.%s(%r) from %s',
                    klass.__name__,
                    methname,
                    (args, kwargs),
                    sourcepos,
                )
                LOGGER.debug('defined at: %s %s', klass, sourcepos)
                raise
            response = self.response_overwrite(response, method, *args, **kwargs)
        except exc.HTTPException as e:
            # for HTTP exceptions execute `finished_hooks`
            if e.code < 500:
                self._call_all_inherited('finished_hook', method_name, *args, **kwargs)
            return self.handle_exception(e, self.app.debug)
        except BaseException as e:
            return self.handle_exception(e, self.app.debug)

        if response and not getattr(self, '_gaetk2_allow_strange_responses', False):
            assert isinstance(response, webapp2.Response)

        self._set_cache_headers()
        self._call_all_inherited('finished_hook', method_name, *args, **kwargs)
        self.finished_overwrite(response, method, *args, **kwargs)
        return response

    def handle_exception(self, exception, debug):
        """Called if this handler throws an exception during execution.

        The default behavior is to re-raise the exception to be handled by
        :meth:`WSGIApplication.handle_exception`.

        Parameters:
            exception: The exception that was thrown.
            debug_mode: True if the web application is running in debug mode.

        Returns:
            response to be sent to the client.

        """
        raise


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
        warnings.warn(
            'use `class Handler(BasicHandler, JsonMixin)`',
            DeprecationWarning,
            stacklevel=2,
        )
        return hujson2.dumps(content)

    def response_overwrite(self, response, method, *args, **kwargs):
        """Function to transform response. To be overwritten."""
        # do serialisation bef ore generating Content-Type Header so Errors will display nicely
        content = self.serialize(response) + '\n'

        # If we have gotten a `callback` parameter, we expect that this is a
        # [JSONP](http://en.wikipedia.org/wiki/JSONP#JSONP) can and therefore add the padding
        if self.request.get('callback', None):
            response = '{} ({})'.format(self.request.get('callback', None), response)
            self.response.headers['Content-Type'] = 'text/javascript'
        else:
            self.response.headers['Content-Type'] = 'application/json'
        return webapp2.Response(content)
