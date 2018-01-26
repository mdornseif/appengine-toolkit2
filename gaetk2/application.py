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
from gaetk2.tools.config import is_development
from gaetk2.tools.sentry import sentry_client
from google.appengine.ext import ndb
from webapp2 import Route

__all__ = ['WSGIApplication', 'Route']

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# Das fängt leider kein runtime.DeadlineExceededError
class WSGIApplication(webapp2.WSGIApplication):
    """Overwrite exception handling.

    For further information see the paret class at
    http://webapp2.readthedocs.io/en/latest/api/webapp2.html#webapp2.WSGIApplication
    """

    @ndb.toplevel
    def __call__(self, environ, start_response):
        with self.request_context_class(self, environ) as (request, response):
            self.setup_logging(request, response)
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
                    logger.debug(
                        "Exception %r via %s %s %s", e, request.route,
                        request.route_args, request.route_kwargs)
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
                        logger.debug('internal_error(%s)', e)
                        response = self._internal_error(e)

                try:
                    return response(environ, start_response)
                except BaseException as e:
                    logger.info('_internal_error')
                    return self._internal_error(e)(environ, start_response)
            except:
                logger.critical("uncaught error")
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

        # WSGIHTTPException come with some further explanations
        notedata = {}
        for attr in ['code', 'explanation', 'detail', 'comment', 'headers']:
            if hasattr(e, attr):
                notedata[attr] = getattr(e, attr)
        sentry_client.note('flow', message=u'HTTPException', data=notedata)

        handler = self.error_handlers.get(code)
        if handler:
            logger.debug('using %s', handler)
            return handler(request, response, e)
        else:
            if code >= 500:
                # Our default handler
                return self.default_exception_handler(request, response, e)
            else:
                # This should be mostly `exc.HTTPException`s < 500
                # which will be rendered directly to the client
                # but if we have a `explanation` we really want to
                # note that in Sentry:
                if hasattr(e, 'explanation'):
                    sentry_client.captureMessage(
                        'HTTP Exception: %s' % e.explanation,
                        level='info',
                        tags={'httpcode': code, 'type': 'Exception'},
                        extra=notedata)
                raise

    def default_exception_handler(self, request, response, exception):
        status, level, fingerprint, tags = self.classify_exception(request, exception)

        # Make sure we have at least some decent infotation in the logfile
        logger.exception(u'Exception caught for path %s: %s', request.path, exception)
        response.set_status(status)

        if not is_development():
            event_id = ''

            if sentry_client:
                event_id = sentry_client.captureException(
                    level=level,
                    extra=self.get_sentry_addon(request),
                    fingerprint=fingerprint,
                    tags=tags,
                )
                logger.info("pushing to sentry: %s", event_id)
            else:
                logger.info("sentry not configured")

            # render error page for the client
            # we do not use jinja2 here to avoid an additional error source.
            with open(os.path.join(os.path.dirname(__file__), '..', 'templates/error/500.html')) as fileobj:
                # set sentry_event_id for GetSentry User Feedback
                template = fileobj.read().decode('utf-8')
                template = template.replace(u"'{{sentry_event_id}}'", u"'%s'" % event_id)
                template = template.replace(u"'{{sentry_public_dsn}}'", gaetkconfig.SENTRY_PUBLIC_DSN)
                template = template.replace(u"{{exception_text}}", jinja2.escape(u"%s" % exception))
                response.clear()
                response.out.body = template.encode('utf-8')
        else:
            # On development servers display a nice traceback via `cgitb`.
            logger.info(u"not pushing to sentry, cgitb()")
            logger.debug(u"SERVER_SOFTWARE %r", os.environ.get('SERVER_SOFTWARE', ''))
            logger.debug(u"SERVER_NAME %r", os.environ.get('SERVER_NAME', ''))
            response.clear()
            handler = cgitb.Hook(file=response.out).handle
            handler()

    def get_sentry_addon(self, request):
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

        # interesting environment variables - see https://david-buxton-test.appspot.com/env#:
        for attr in ('REQUEST_ID_HASH INSTANCE_ID REQUEST_LOG_ID HTTP_X_CLOUD_TRACE_CONTEXT '
                     'USER_IS_ADMIN USER_ORGANIZATION SERVER_SOFTWARE'
                     'AUTH_DOMAIN'
                     'PATH_TRANSLATED DEFAULT_VERSION_HOSTNAME'
                     'HTTP_X_GOOGLE_APPS_METADATA SCRIPT_NAME PATH_INFO').split():
            if attr in request.environ:
                addon[attr] = request.environ.get(attr)

        # Its not well documented how to structure the data for sentry
        # https://gist.github.com/cgallemore/4507616

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
        #     logger.warn("error decoding cart from session")

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

    def setup_logging(self, request, response):
        """Provide sentry early on with information from the context."""
        sentry_client.user_context({
            'ip_address': os.environ.get('REMOTE_ADDR'),
            'email': os.environ.get('USER_EMAIL'),
            'id': os.environ.get('USER_ID'),
            'username': os.environ.get('USER_NICKNAME', os.environ.get('HTTP_X_APPENGINE_INBOUND_APPID')),
            # USER_ORGANIZATION
        })
        # HTTP_X_APPENGINE_CRON   true

        # http_context
        # 'cookies': dict(request.COOKIES),
        # 'data': data,
        # 'data': {},
        # 'env': dict(get_environ(environ)
        # 'env': dict(get_environ(request.environ)),
        # 'headers': dict(get_headers(environ)),
        # 'headers': dict(get_headers(request.environ)),
        # 'method': request.method,
        # 'method': request.method,
        # 'query_string': '...',
        # 'query_string': urlparts.query,
        # 'url': '%s://%s%s' % (urlparts.scheme, urlparts.netloc, urlparts.path),
        # 'url': '...',

        # extra_context
        # server_name => INSTANCE_ID,
        # server_name: the hostname of the server
        # os.environ.get('SERVER_NAME', '')

        # sentry_client.setTagsContext({
        #     environment: "production"
        # })
        # some are set in sentry.py
        tags = {
            # environment: 'production'
            # 'git_commit': 'c0deb10c4'
        }
        # DEFAULT_VERSION_HOSTNAME    david-buxton-test.appspot.com
        # HTTP_X_CLOUD_TRACE_CONTEXT  301334dd3fca3fe29d8625c3a3a115f7/13580140575625565538;o=1
        # REQUEST_ID_HASH 7DB846CB    <type 'str'>
        # REQUEST_LOG_ID  5a5f0ce100ff0c90937db846cb0001737e6412d332d6733343630326234000100
        varnames = 'CURRENT_NAMESPACE INBOUND_APPID QUEUENAME TASKRETRYREASON'
        for name in varnames.split():
            fullname = 'HTTP_X_APPENGINE_' + name
            if os.environ.get(fullname):
                tags['GAE_' + name] = os.environ.get(fullname)
        sentry_client.tags_context(tags)

        extra = {}
        varnames = 'TASKEXECUTIONCOUNT TASKNAME TASKRETRYCOUNT'
        for name in varnames.split():
            fullname = 'HTTP_X_APPENGINE_' + name
            if os.environ.get(fullname):
                extra['GAE_' + name] = os.environ.get(fullname)
        sentry_client.extra_context(extra)

        http = {}
        # 'url': '%s://%s%s' % (urlparts.scheme, urlparts.netloc, urlparts.path),
        # 'query_string': urlparts.query,
        # 'method': request.method,
        # 'data': data,
        # 'headers': dict(get_headers(request.environ)),
        # 'env': dict(get_environ(request.environ)),
        varnames = 'HTTP_REFERER HTTP_USER_AGENT REQUEST_METHOD'
        for name in varnames.split():
            if os.environ.get(name):
                extra[name] = os.environ.get(name)
        sentry_client.http_context(http)

        # extra={
        # 'args': args,
        # 'kwargs': kwargs,
        # 'app': app,
        # },
        # data['tags'].setdefault('site', settings.SITE_ID)
        # data[:server_name] = @server_name if @server_name
        # data[:release] = @release if @release
        # data[:modules] = @modules if @modules
        # if not data.get('level'):
        # if not data.get('modules'):
        # data['release'] = self.release
        # data['environment'] = self.environment
        #     data['culprit'] = culprit
        # self.repos = self._format_repos(o.get('repos'))
