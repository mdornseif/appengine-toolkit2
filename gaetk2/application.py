#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gaetk2.application - WSGI Application for webapp2.

Created by Maximillian Dornseif on 2018-01-11.
Copyright (c) 2018 Maximillian Dornseif. MIT Licensed.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import cgitb
import logging
import os

import google.appengine.api.datastore_errors
import google.appengine.api.urlfetch_errors
import google.appengine.runtime
import google.appengine.runtime.apiproxy_errors

from google.appengine.ext import ndb

import jinja2
import requests.exceptions
import urllib3.exceptions
import webapp2

from gaetk2 import exc
from gaetk2.config import gaetkconfig
from gaetk2.config import is_development
from gaetk2.tools.sentry import sentry_client
from webapp2 import Route


__all__ = ['WSGIApplication', 'Route']

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
LOGGER.setLevel(logging.INFO)


# Das fängt leider kein runtime.DeadlineExceededError
class WSGIApplication(webapp2.WSGIApplication):
    """Overwrite exception handling.

    For further information see the paret class at
    http://webapp2.readthedocs.io/en/latest/api/webapp2.html#webapp2.WSGIApplication
    """

    # see https://github.com/GoogleCloudPlatform/webapp2/issues/69
    allowed_methods = frozenset(
        ('GET', 'POST', 'HEAD', 'OPTIONS', 'PUT', 'DELETE', 'TRACE', 'PATCH')
    )

    @ndb.toplevel
    def __call__(self, environ, start_response):
        LOGGER.debug('WSGI __call__ starting', extra={'environ': environ})

        with self.request_context_class(self, environ) as (request, response):
            # context = ndb.get_context()
            # context.set_memcache_timeout_policy(60 * 60 * 12)
            self.setup_logging(request, response)
            try:
                try:
                    if request.method not in self.allowed_methods:
                        # 501 Not Implemented.
                        raise exc.HTTP501_NotImplemented()
                    try:
                        rv = self.router.dispatch(request, response)
                    except exc.HTTP404_NotFound:
                        # some extra logging to find non matching routes
                        LOGGER.info('NotFound: %r', self)
                        LOGGER.info('router: %r', vars(self.router))
                        LOGGER.info('environ: %r', environ)
                        raise
                    if rv is not None:
                        response = rv
                # webapp2 only catches `Exception` not `BaseException`
                except BaseException as e:
                    LOGGER.debug(
                        'Exception %r via %s %s %s %s',
                        e,
                        request.route,
                        request.route_args,
                        request.route_kwargs,
                        self.router,
                    )
                    try:
                        # Try to handle it with a custom error handler.
                        rv = self.handle_exception(request, response, e)
                        if rv is not None:
                            response = rv
                    except exc.HTTPException as e:
                        # Use the HTTP exception as response.
                        response = e
                        if (
                            os.environ.get('GAETK2_WEBTEST')
                            and getattr(e, 'code', 500) >= 500
                        ):
                            # make sure we get nice errors during testing
                            raise
                    except BaseException as e:
                        # Error wasn't handled so we have nothing else to do.
                        LOGGER.debug('internal_error(%s)', e)
                        response = self._internal_error(e)
                        if os.environ.get('GAETK2_WEBTEST'):
                            # make sure we get nice errors during testing
                            raise

                try:
                    self.fix_unicode_headers(response)
                    return response(environ, start_response)
                except BaseException as e:
                    LOGGER.info('_internal_error')
                    return self._internal_error(e)(environ, start_response)
            except Exception:
                LOGGER.critical('uncaught error')
                raise
        LOGGER.debug('WSGI __call__ done', extra={'environ': environ})

    def handle_exception(self, request, response, e):
        """Handles a uncaught exception occurred in :meth:`__call__`.

        Uncaught exceptions can be handled by error handlers registered in
        :attr:`error_handlers`. This is a dictionary that maps HTTP status
        codes to callables that will handle the corresponding error code.
        If the exception is not an ``HTTPException``, the status code 500
        is used.

        The error handlers receive (request, response, exception) and can be
        a callable or a string in dotted notation to be lazily imported.

        If no error handler is found, the exception is re-raised.

        Parameters:
            request: A :class:`Request` instance.
            response: A :class:`Response` instance.
            e: The uncaught exception.

        Returns:
            The returned value from the error handler.

        """
        if isinstance(e, exc.HTTPException):
            code = e.code
        else:
            code = 500

        # WSGIHTTPException come with some further explanations
        notedata = {}
        for attr in ['code', 'explanation', 'detail', 'comment', 'headers']:
            if getattr(e, attr, None):
                notedata[attr] = getattr(e, attr)
        if notedata:
            sentry_client.note('navigation', message='HTTPException', data=notedata)

        handler = self.error_handlers.get(code)
        if handler and not os.environ.get('GAETK2_WEBTEST'):
            LOGGER.debug('using %s', handler)
            return handler(request, response, e)
        else:
            if getattr(e, '_want_trackback', False) or code >= 500:
                # Our default handler
                return self.default_exception_handler(request, response, e)
            else:
                # This should be mostly `exc.HTTPException`s < 500
                # which will be rendered directly to the client
                # but if we have a `explanation` we really want to
                # note that in Sentry:
                if getattr(e, 'explanation', None):
                    notedata.update(self.get_sentry_addon(request))
                    # TODO: http-Headers etc are missing
                    sentry_client.captureMessage(
                        'HTTPException {}: {}'.format(code, e.explanation),
                        level='info',
                        tags={'httpcode': code, 'type': 'Exception'},
                        extra=notedata,
                    )
                logging.debug('HTTP exception:', exc_info=True)
                raise  # pylint: disable=E0704

    def default_exception_handler(self, request, response, exception):
        """Exception aufbereiten und loggen."""
        status, level, fingerprint, tags = self.classify_exception(request, exception)

        # Make sure we have at least some decent infotation in the logfile
        if level == 'error':
            LOGGER.exception(
                'Exception caught for path %s: %s', request.path, exception
            )
            if os.environ.get('GAETK2_WEBTEST'):
                raise  # pylint: disable=E0704
        else:
            LOGGER.info(
                'Exception caught for path %s: %s',
                request.path,
                exception,
                exc_info=True,
            )

        if not is_development():
            event_id = ''

            if sentry_client:
                if not getattr(exception, '_hide_from_sentry', False):
                    event_id = sentry_client.captureException(
                        level=level,
                        extra=self.get_sentry_addon(request),
                        fingerprint=fingerprint,
                        tags=tags,
                    )
                    LOGGER.info('pushing to sentry: %s', event_id)
                else:
                    LOGGER.info('hidden from sentry: %s')
            else:
                LOGGER.info('sentry not configured')

            # render error page for the client
            # we do not use jinja2 here to avoid an additional error source.
            with open(
                os.path.join(
                    os.path.dirname(__file__), '..', 'templates/error/500.html'
                )
            ) as fileobj:
                # set sentry_event_id for GetSentry User Feedback
                template = fileobj.read().decode('utf-8')
                template = template.replace("'{{sentry_event_id}}'", "'%s'" % event_id)
                template = template.replace(
                    "'{{sentry_public_dsn}}'", "'%s'" % gaetkconfig.SENTRY_PUBLIC_DSN
                )
                template = template.replace(
                    '{{exception_text}}', jinja2.escape('%s' % exception)
                )
                response.clear()
                response.headers['Content-Type'] = b'text/html'
                response.out.body = template.encode('utf-8')
        else:
            # On development servers display a nice traceback via `cgitb`.
            LOGGER.info('not pushing to sentry, cgitb()')
            response.clear()
            response.headers['Content-Type'] = b'text/html'
            handler = cgitb.Hook(file=response.out).handle
            handler()
        response.set_status(status)

    def get_sentry_addon(self, request):
        """Try to extract additional data from the request for Sentry after an Exception tootk place.

        Parameters:
            request: The Request Object

        Returns:
            a dict to be sent to sentry as `addon`.

        """
        addon = {}

        # try to recover session information
        # current_session = gaesessions.Session(cookie_key=COOKIE_KEY)
        # addon.update(
        #     login_via=current_session.get('login_via', ''),
        #     login_time=current_session.get('login_time', ''),
        #     uid=current_session.get('uid', ''),
        # )

        # try:
        #     if 'cart' in current_session:
        #         addon['cart'] = vars(current_session['cart'])
        # except Exception:
        #     LOGGER.warn("error decoding cart from session")

        return addon

    def classify_exception(self, request, exception):
        """Based on the exception raised we classify it for logging.

        We not only return an HTTP Status code and `level`, but also
        a `fingerprint` and `dict` of `tags` to help snetry group the errors.
        """
        status = 500
        level = 'error'
        fingerprint = None
        tags = {'url': request.uri}

        k = repr(exception.__class__)
        if 'PermanentTaskFailure' in k:
            level = 'info'
            tags = {'subsystem': 'taskqueue'}
        if (
            'ApiTooSlowError' in k
            or 'TimeoutError' in k
            or 'Deadline exceeded' in k
            or 'CsApiException' in k
            or 'Deadlock waiting for' in k
            or unicode(exception).endswith('timed out')
        ):
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout'}
        if 'Connection closed' in k:
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'abort'}
        if 'TransientError' in k or 'InternalTransientError' in k:
            status = 503  # Service Unavailable
            level = 'warning'
            tags = {'class': 'transienterror'}

        if isinstance(exception, Warning):
            level = 'warning'
        # see https://cloud.google.com/appengine/articles/deadlineexceedederrors
        if isinstance(exception, google.appengine.runtime.DeadlineExceededError):
            # raised if the overall request times out, typically after 60 seconds,
            # or 10 minutes for task queue requests.
            # only one more second before we are killed - messaging to sentry
            # therefore does not work very well
            status = 503  # Service Unavailable
            level = 'warning'
            # this propbably can be done smarter
            # fingerprint = [request.route]
            tags = {'class': 'timeout', 'subsystem': 'appengine'}
        if isinstance(
            exception, google.appengine.runtime.apiproxy_errors.CancelledError
        ):
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout', 'subsystem': 'googlecloud'}
        if isinstance(
            exception, google.appengine.runtime.apiproxy_errors.DeadlineExceededError
        ):
            # raised if an RPC exceeded its deadline.
            # This is typically 5 seconds, but it is settable for some APIs using the 'deadline' option.
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout', 'subsystem': 'googlecloud'}
        # Datastore
        if isinstance(exception, google.appengine.api.datastore_errors.Timeout):
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout', 'subsystem': 'googlecloud', 'api': 'Datastore'}
        if isinstance(
            exception, google.appengine.api.datastore_errors.TransactionFailedError
        ):
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'subsystem': 'googlecloud', 'api': 'Datastore'}
        # urlfetch
        if isinstance(exception, urllib3.exceptions.ProtocolError):
            if 'Connection aborted' in repr(exception):
                status = 504  # Gateway Time-out
                level = 'warning'
                tags = {'subsystem': 'urlfetch', 'api': 'urllib3'}
        if isinstance(exception, requests.exceptions.ConnectionError):
            if 'Connection closed unexpectedly by server' in repr(exception):
                status = 504  # Gateway Time-out
                level = 'warning'
                tags = {'subsystem': 'urlfetch', 'api': 'requests'}
        if isinstance(
            exception, google.appengine.api.urlfetch_errors.ConnectionClosedError
        ):
            status = (
                507
            )  # Insufficient Storage  - passt jetzt nicht wie die Faust auf's Auge ...
            level = 'warning'
            tags = {'subsystem': 'urlfetch'}
        if 'DownloadError' in k or isinstance(
            exception, google.appengine.api.urlfetch_errors.InternalTransientError
        ):
            status = 503  # Service Unavailable
            level = 'warning'
            tags = {'class': 'transienterror', 'subsystem': 'urlfetch'}
        if isinstance(
            exception, google.appengine.api.urlfetch_errors.DeadlineExceededError
        ):
            # raised if the URLFetch times out.
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout', 'subsystem': 'urlfetch'}
        if 'HTTPException: Deadline exceeded while waiting for HTTP response' in repr(
            exception
        ):
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout', 'subsystem': 'urlfetch'}

        if 'dropboxapi' in repr(exception):
            tags['api'] = 'Dropbox'

        return status, level, fingerprint, tags

    def setup_logging(self, request, response):
        """Provide sentry early on with information from the context.

        Called at the beginning of each request. Some information is already set
        in `sentry.py` during initialisation.
        """
        # Its not well documented how to structure the data for sentry
        # https://gist.github.com/cgallemore/4507616

        # see https://docs.sentry.io/clientdev/interfaces/user/
        env = request.environ
        sentry_client.user_context(
            {
                'ip_address': env.get('REMOTE_ADDR'),
                'email': env.get('USER_EMAIL'),
                'id': env.get('USER_ID'),
                'username': env.get(
                    'USER_NICKNAME', env.get('HTTP_X_APPENGINE_INBOUND_APPID')
                ),
                # HTTP_X_APPENGINE_CRON   true
                # USER_ORGANIZATION USER_IS_ADMIN
            }
        )

        extra = {}
        for name in 'HTTP_REFERER HTTP_USER_AGENT'.split():
            if os.environ.get(name):
                extra[name] = os.environ.get(name)
        for name in 'TASKEXECUTIONCOUNT TASKNAME TASKRETRYCOUNT'.split():
            fullname = 'HTTP_X_APPENGINE_' + name
            if os.environ.get(fullname):
                extra['GAE_' + name] = os.environ.get(fullname)
        for attr in 'uri app route route_args route_kwargs'.split():
            try:
                extra[attr] = request.get(attr)
            except Exception:
                LOGGER.exception('problem parsing %s', attr)
        sentry_client.extra_context(extra)
        # server_name: the hostname of the server
        # os.environ.get('SERVER_NAME', '')
        # data[:release] = @release if @release
        # data[:modules] = @modules if @modules
        # if not data.get('level'):
        # if not data.get('modules'):
        # data['release'] = self.release
        # data['culprit'] = culprit
        # self.repos = self._format_repos(o.get('repos'))

        http = {
            'url': request.url,
            # 'query_string': request.query_string, - read by reaven vrom the environment
            # 'method': request.method, - read by reaven vrom the environment
            'cookies': request.cookies,
            'headers': request.headers,  # seems to be ignored
            'env': request.environ,
        }
        if request.method in ['POST', 'PUT', 'PATCH']:
            http['data'] = {'raw': request.body}

        # see also https://docs.sentry.io/clientdev/interfaces/http/
        sentry_client.http_context(http)

        # some are set in sentry.py
        tags = {
            # 'git_commit': 'c0deb10c4'
        }
        # HTTP_X_CLOUD_TRACE_CONTEXT  301334dd3fca3fe29d8625c3a3a115f7/13580140575625565538;o=1
        # REQUEST_ID_HASH 7DB846CB    <type 'str'>
        # REQUEST_LOG_ID  5a5f0ce100ff0c90937db846cb0001737e6412d332d6733343630326234000100
        # INSTANCE_ID
        # SERVER_SOFTWARE
        # AUTH_DOMAIN
        # PATH_TRANSLATED SCRIPT_NAME PATH_INFO
        # HTTP_X_GOOGLE_APPS_METADATA
        # interesting environment variables - see https://david-buxton-test.appspot.com/env#:
        varnames = 'CURRENT_NAMESPACE INBOUND_APPID QUEUENAME TASKRETRYREASON'
        for name in varnames.split():
            fullname = 'HTTP_X_APPENGINE_' + name
            if request.environ.get(fullname):
                tags['GAE_' + name] = os.environ.get(fullname)
        sentry_client.tags_context(tags)

    def fix_unicode_headers(self, response):
        """Ensure all Headers are Unicode."""
        if hasattr(response, 'headers'):
            for name, val in response.headers.items():
                response.headers[str(name)] = str(val)
