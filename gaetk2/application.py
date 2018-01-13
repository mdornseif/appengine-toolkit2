#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.application - WSGI Application for webapp2.

Created by Maximillian Dornseif on 2018-01-11.
Copyright (c) 2018 Maximillian Dornseif. MIT Licensed.
"""
import cgitb
import logging
import os

import google.appengine.api.datastore_errors
import google.appengine.api.urlfetch_errors
import google.appengine.runtime
import google.appengine.runtime.apiproxy_errors
import google.storage.speckle.python.api.rdbms
import jinja2
import requests.exceptions
import urllib3.exceptions
import webapp2

from gaetk2 import exc
from gaetk2.tools.config import config as gaetkconfig
from gaetk2.tools.config import is_production
from gaetk2.tools.sentry import sentry_client
from google.appengine.ext import ndb
from webapp2 import Route

__all__ = ['WSGIApplication', 'Route']


# Das fängt leider kein runtime.DeadlineExceededError
class WSGIApplication(webapp2.WSGIApplication):
    """Overwrite exception handling.

    For further information see the paret class at
    http://webapp2.readthedocs.io/en/latest/api/webapp2.html#webapp2.WSGIApplication
    """

    @ndb.toplevel
    def __call__(self, environ, start_response):
        with self.request_context_class(self, environ) as (request, response):
            try:
                try:
                    if request.method not in self.allowed_methods:
                        # 501 Not Implemented.
                        raise exc.HTTP501_NotImplemented()

                    rv = self.router.dispatch(request, response)
                    if rv is not None:
                        response = rv
                # webapp2 conly catches `Exception` not `BaseException`
                except BaseException as e:
                    try:
                        # Try to handle it with a custom error handler.
                        rv = self.handle_exception(request, response, e)
                        if rv is not None:
                            response = rv
                    except exc.HTTPException as e:
                        # Use the HTTP exception as response.
                        response = e
                    except BaseException as e:
                        # Error wasn't handled so we have nothing else to do.
                        response = self._internal_error(e)

                try:
                    return response(environ, start_response)
                except BaseException as e:
                    return self._internal_error(e)(environ, start_response)
            except:
                logging.critical("uncaught error")
                raise

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

        handler = self.error_handlers.get(code)
        if handler:
            return handler(request, response, e)
        else:
            if code == 500:
                # Our default handler
                self.default_exception_handler(request, response, e)
            # Alternatively: raise

    def default_exception_handler(self, request, response, exception):
        status, level, fingerprint, tags = self.classify_exception(request, exception)

        # Make sure we have at least some decent infotation in the logfile
        logging.exception(u'Exception caught for path %s: %s', request.path, exception)
        response.set_status(status)

        if is_production():
            event_id = ''
            logging.info("pushed to sentry: %s", event_id)
            # render error page for the client
            # we do not use jinja2 here to avoid an additional error source.
            with open(os.path.join(__file__, '..', 'templates/error/500.html')) as fileobj:
                # set sentry_event_id for GetSentry User Feedback
                template = fileobj.read().decode('utf-8')
                template = template.replace(u"'{{sentry_event_id}}'", u"'%s'" % event_id)
                template = template.replace(u"'{{sentry_public_dsn}}'", gaetkconfig.GAETK2_SENTRY_PUBLIC_DSN)
                template = template.replace(u"{{exception_text}}", jinja2.escape(u"%s" % exception))
                response.clear()
                response.out.body = template.encode('utf-8')

            if sentry_client:
                event_id = sentry_client.captureException(
                    level=level,
                    extra=self.get_sentry_addon(request),
                    fingerprint=fingerprint,
                    tags=tags,
                )
        else:
            # On development servers display a nice traceback via `cgitb`.
            logging.info(u"not pushing to sentry.")
            response.clear()
            handler = cgitb.Hook(file=response.out).handle
            handler()

        def get_sentry_addon(request):
            """This tries to extract additional data from the request for Sentry.

            Parameters:
                request: The Request Object

            Returns:
                a dict to be sent to sentry as `addon`.
            """

            addon = {}

            # Things worth considering
            # request.app = None
            # request.route = None
            # request.route_args = None
            # request.route_kwargs = None
            # request.query/query_string)
            # request.script_name/SCRIPT_NAME
            # request.path_info / PATH_INFO
            # request.application_url() = The URL including SCRIPT_NAME (no PATH_INFO or query string)
            # request.path_url(): The URL including SCRIPT_NAME and PATH_INFO, but not QUERY_STRING
            # request.path(self): The path of the request, without host or query string
            # request.path_qs: The path of the request, without host but with query string

            # copy environment variables of interest
            for attr in ('REQUEST_ID_HASH INSTANCE_ID REQUEST_LOG_ID HTTP_X_CLOUD_TRACE_CONTEXT '
                         'USER_IS_ADMIN USER_ORGANIZATION USER_ID USER_EMAIL USER_NICKNAME SERVER_SOFTWARE'
                         'AUTH_DOMAIN HTTP_REFERER APPENGINE_RUNTIME DATACENTER REQUEST_METHOD'
                         'APPLICATION_ID CURRENT_MODULE_ID CURRENT_VERSION_ID PATH_TRANSLATED'
                         'HTTP_X_GOOGLE_APPS_METADATA SCRIPT_NAME PATH_INFO').split():
                if attr in request.environ:
                    addon[attr] = request.environ.get(attr)

            # further analysis needed:
            # CURRENT_MODULE_ID
            # 'DEFAULT_VERSION_HOSTNAME': 'xxx.appspot.com',
            # 'HTTP_ACCEPT': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            # tags: {git_commit: 'c0deb10c4'}

            # Its not well documented how to structure the data for sentry
            # https://gist.github.com/cgallemore/4507616

            # try to recover session information
            # current_session = gaesessions.Session(cookie_key=COOKIE_KEY)
            # addon.update(
            #     login_via=current_session.get('login_via', ''),
            #     login_time=current_session.get('login_time', ''),
            #     uid=current_session.get('uid', ''),
            # )

            # if request.environ.get('USER_EMAIL'):
            #     SENTRY_CLIENT.user_context({
            #         'email': request.environ.get('USER_EMAIL')
            #     })

            # try:
            #     if 'cart' in current_session:
            #         addon['cart'] = vars(current_session['cart'])
            # except Exception:
            #     logging.warn("error decoding cart from session")

            return addon

    def classify_exception(self, request, exception):
        """Based on the exception raised we classify it for logging.

        We not only return an HTTP Status code and `level`, but also
        a `fingerprint` and `dict` of `tags` to help snetry group the errors.
        """

        status = 500
        level = 'error'
        fingerprint = None
        tags = {}

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
            fingerprint = [request.route]
            tags = {'class': 'timeout', 'subsystem': 'appengine'}
        if isinstance(exception, google.appengine.runtime.apiproxy_errors.CancelledError):
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout', 'subsystem': 'googlecloud'}
        if isinstance(exception, google.appengine.runtime.apiproxy_errors.DeadlineExceededError):
            # raised if an RPC exceeded its deadline.
            # This is typically 5 seconds, but it is settable for some APIs using the 'deadline' option.
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout', 'subsystem': 'googlecloud'}
        if isinstance(exception, google.appengine.runtime.DeadlineExceededError):
            # Not to be confused with runtime.apiproxy_errors.DeadlineExceededError.
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout', 'subsystem': 'google'}
        if isinstance(exception, google.appengine.api.datastore_errors.Timeout):
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout', 'subsystem': 'googlecloud', 'api': 'Datastore'}
        if isinstance(exception, google.appengine.api.datastore_errors.TransactionFailedError):
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'subsystem': 'googlecloud', 'api': 'Datastore'}
        if isinstance(exception, google.storage.speckle.python.api.rdbms.OperationalError):
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'subsystem': 'googlecloud', 'api': 'CloudSQL'}
        if isinstance(exception, urllib3.exceptions.ProtocolError):
            if 'Connection aborted' in str(exception):
                status = 504  # Gateway Time-out
                level = 'warning'
                tags = {'subsystem': 'urlfetch', 'api': 'urllib3'}
        if isinstance(exception, requests.exceptions.ConnectionError):
            if 'Connection closed unexpectedly by server' in str(exception):
                status = 504  # Gateway Time-out
                level = 'warning'
                tags = {'subsystem': 'urlfetch', 'api': 'requests'}
        if isinstance(exception, google.appengine.api.urlfetch_errors.ConnectionClosedError):
            status = 507  # Insufficient Storage  - passt jetzt nicht wie die Faust auf's Auge ...
            level = 'warning'
            tags = {'subsystem': 'urlfetch'}
        if isinstance(exception, google.appengine.api.urlfetch_errors.DeadlineExceededError):
            # raised if the URLFetch times out.
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout', 'subsystem': 'urlfetch'}
        if 'HTTPException: Deadline exceeded while waiting for HTTP response' in str(exception):
            status = 504  # Gateway Time-out
            level = 'warning'
            tags = {'class': 'timeout', 'subsystem': 'urlfetch'}

        if 'dropboxapi' in str(exception):
            tags['api'] = 'Dropbox'

        return status, level, fingerprint, tags
