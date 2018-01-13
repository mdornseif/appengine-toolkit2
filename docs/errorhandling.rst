.. _error-handling:

Error Handling
==============

**td;dr:** See `Installing Error Handling`_ how to just get started.

Generally when working on large distributed systems we have to life
with lots of transient errors. So you have to be careful that your data
is always in a consistent state. Making your application
`idempotent <http://restcookbook.com/HTTP%20Methods/idempotency/>`_
in most places is very helpful for that.

..

    **Crash Early.**
    A dead program normally does a lot less damage than a crippled one.

    -- `The Pragmatic Programmer <https://pragprog.com/the-pragmatic-programmer/extracts/tips>`_


One approach which works well is to crash early and let the infrastructure
handle the retries. For App Engine Applications this are usually
`taskqueues <https://cloud.google.com/appengine/docs/standard/python/taskqueue/push/>`_
or by :func:`~gaetk2.tskqueue.defer` which uses taskqueues behind the scenes.
In other instances the retry may be initiated by the user and his web browser
or by an external service (like Mail delivery).

This means there are certain types of errors we care only a about
if they happen often (like timeouts) others we want to know about immediately
(like Syntax Errors).

We strongly suggest to use an external log aggregation service. We use
`Sentry <https://github.com/getsentry/sentry>`_ in the hosted variant
provided by `GetSentry <https://sentry.io>`_. What convinced us to use that is
that Armin Ronacher started working there. Armin created so many things we
use every day so we thought sentry.io probably is great, too.

In gaetk2 we use three levels of error reporting: `high level` in application
code, `medium level` in library code and `low level` in infrastructure code.

Error handling should be as simple as possible to avoid errors during
error handling. Error Display to end users should be robust, plain, simple
and without flashy design or wording.


High Level Error Handling
-------------------------

Most Errors will happen in request handlers. High Level Error Handling
is happening in :meth:`gaetk2.application.WSGIApplication` so all
request handlers called via this application will get our error handling.

.. note::

    Be also aware that exceptions are also used to communicate HTTP-Status-Codes
    throughout the systems. These we do not consider errors.

    Also in parts of `webapp2` only ``Exception`` is caught. But some
    AppEngine Exceptions are derivered from ``BaseException``.

Exceptions happening in Request-Handlers are caught in
:meth:`~gaetk2.handlers.base.BasicHandler.dispatch()` and forwarded to
:meth:`~gaetk2.handlers.base.BasicHandler.handle_exception()`. This is
the place where you might implement your own exception handling or logging.

The exceptions are recaught in
:meth:`gaetk2.application.WSGIApplication.__call__()` and forwarded to
:meth:`gaetk2.application.WSGIApplication.handle_exception()`. There all the
special stuff is happening. This is:

* `Handling of HTTPException`_
* `Exception Classification`_
* `Error-Page for the Client`_
* `Push Error Information to Log Aggregator`_


Handling of HTTPException
^^^^^^^^^^^^^^^^^^^^^^^^^

:exc:`gaetk2.exc.HTTPException` are a clever concept introduced by webobj.
They are used by request handlers to abort execution and set return status
codes.

So instead of something like::

    self.response.write('you are unauthenticated')
    self.redirect('/login', permanent=False)
    return

you can do something like this::

    raise exc.HTTP301_Moved('you are unauthenticated', location='/login')

This makes control flow much more explicit. This functionality is implemented
in :meth:`gaetk2.application.WSGIApplication.__call__()` where all instances
of :exc:`~gaetk2.exc.HTTPException` and it's subclasses are just sent to the,
client. :exc:`~gaetk2.exc.HTTPException` generates the necessary headers and
body.

All other Exceptions are handled further down the line.

.. note::

   In `gaetk1` / `gaetk_common` the same effect was reached via
   :func:`make_app()` which set ``app.error_handlers[500] = handle_500``.
   `gaetk2` integrates the functionality within
   :class:`gaetk2.application.WSGIApplication`.




Exception Classification
^^^^^^^^^^^^^^^^^^^^^^^^

Some Exceptions we usually just don't want to know about, like
:exc:`gaetk2.exc.HTTP301_Moved`. Others we consider mere warnings
which do not need actions of the admin or programmer like
:exc:`google.appengine.api.datastore_errors.Timeout`.

`webapp2` usually adds a status code 500 to all Python Exceptions. For finer
grained logging we want to offer a bunch of different status code and also
decide if we consider the event a `note` (e.g. Page Not Found) a `warning`
(e.g. Timeout) or an `error` (e.g. Syntax Error).

This is happening in :meth:`gaetk2.application.WSGIApplication.classify_exception()`
which you are encouraged extend to fit your needs.


Error-Page for the Client
^^^^^^^^^^^^^^^^^^^^^^^^^

If we are not running in production mode (see :func:`~gaetk2.tools.config.is_production()`) extensive traceback information is
sent to the client using the :mod:`cgitb` module. Be aware that this might
expose server secrets!

If running in production mode a simple error page is generated from
:file:`templates/error/500.html` and sent to the client. Currently the
file name is hardcoded.



Push Error Information to Log Aggregator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Optionally Log information can be sent to Sentry for log aggregation.
This automatically happens when a Sentry DSN (see below) is configured.
We do our best to add all kinds of useful information to the Sentry message.

.. todo::

    * Only send Traceback information to admins.
    * Allow changing of 500.html template



Medium Level Error Handling
---------------------------

Errors occurring within the framework (e.g. during error handling or in
code not based on :class:`gaetk2.handlers.base.BasicHandler` are handled by
a WSGI-Middleware. This is usually installed automatically if
:func:`gaetk2.tools.config.is_production()` by importing :func:`gaetk2.wsgi.webapp_add_wsgi_middleware`.

Error-Handling will be a little less sophisticated than `High Level Error
Handling`.


Low Level Error Handling
------------------------

Some Errors we just can't handle via python code. Most notable syntax errors
in low level modules and timeouts. But App Engine can display error pages
for them.

For basic error handling add this to your `app.yaml <https://cloud.google.com/appengine/docs/standard/python/config/appref#syntax>`_::

	error_handlers:
	- file: lib/appengine-toolkit2/templates/error/500.html

To get better error reporting we suggest you create a copy of
`error/500.html` with some Javascript code to handle Javascript based
front end error logging of the incident.


Frontend Error Handling
-----------------------

You want to log Javascript errors happening at the Client Side. Sentry and
similar services offer that. gaetk2 allows easy integration.


Sentry Configuration
--------------------

If you do not configure Sentry you loose a lot of the error handling
functionality.

To setup Sentry, just create a Project at `Sentry <https://github.com/getsentry/sentry>`_. There you can get your. Insert it into ``appengine_config.py``::

    GAETK2_SENTRY_DSN='https://15e...4ed:f10...passwd...2b2@app.getsentry.com/76098'
    # for Client Side Javascript we obmit the Password
    GAETK2_SENTRY_PUBLIC_DSN='https://15e...4ed@app.getsentry.com/76098'

This should be all you need. In the Default-Templates it will install `raven-js <https://github.com/getsentry/raven-js>`_ and start logging frontend errors. This is be archived by :class:`gaetk2.handlers.base.BasicHandler` and
``templates/gaetk_base_bs4.html``.


Installing Error Handling
-------------------------

To install error handling, configure Sentry as shown above. Then add this to
``appengine_config.py`` to get `Medium Level Error Handling`::

    # load gaetk2 bootstrap code without using `sys.path`
    import imp
    (fp, filename, data) = imp.find_module(
        'boot', ['./lib/appengine-toolkit2/gaetk2/'])
    imp.load_module('gaetk_boot', fp, filename, data)

    # install middleware
    from gaetk2.wsgi import webapp_add_wsgi_middleware

This will not only install Error Handling on production but also session
handling etc. See :any:`gaetk2.wsgi` for detailed documentation.
The WSGI middleware now should catch all exceptions not being caught by
our handlers or WSGI applications.

For `High Level Error Handling`_ just use
:class:`gaetk2.application.WSGIApplication`. For example in `app.yaml`_ add::

    handlers:
        - url: /
          script: home.app

``home.py`` should look like this::

    from gaetk2.handlers import DefaultHandler
    from gaetk2.application import WSGIApplication, Route

    class HomeHandler(DefaultHandler):
        def get(self):
            self.return_text('it worked')

    app = WSGIApplication([Route('/', handler=HomeHandler)])

And don't forget to add ``GAETK2_SENTRY_DSN`` to ``appengine_config.py``!



.. todo::
    * Describe how to add front end logging via Sentry to Low Level Error Handling
    * gaetk2.wsgi Documentation
    * Manual Logging
