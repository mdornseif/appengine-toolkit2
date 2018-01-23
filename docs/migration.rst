Migrating from appengine-toolkit 1 to Version2
==============================================

Some suggestions on moving from Appengine Toolkit Version 1
(`gaetk <https://github.com/mdornseif/appengine-toolkit>`_)
to GAETK2.

First get all the :ref:`error-handling` goodness from GAETK2.

Just ensure that you import the right WSGI Application::

    from gaetk2.application import WSGIApplication
    ....
    application = WSGIApplication([ ...

Often you might ahve to replace `make_app` by
:class:`~gaetk2.application.WSGIApplication`.

With that you did the most important change. GAETK1 and GAETK2 get along quite well so you might leave it at that for a moment.


Replace Imports
---------------

Replace this::

    from google.appengine.ext.deferred import defer
    from gaetk.infrastructure import taskqueue_add_multi

With this::

    from gaetk2.taskqueue import defer
    from gaetk2.taskqueue import taskqueue_add_multi


s/import gaetk.handler/from gaetk2 import exc/
/raise gaetk.handler.HTTP/raise exc.HTTP/


Use a local logger
------------------

At the top of each module create a local logger instance::


    logger = logging.getLogger(__name__)

Then replace calls to :func:`logging.info()` et. al. with calls to
``logger.info()``  et. al.










