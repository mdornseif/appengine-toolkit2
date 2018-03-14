WSGI Application
================

The code in here is basically a vanilla

`webapp2.WSGIApplication <http://webapp2.readthedocs.io/en/latest/api/webapp2.html#webapp2.WSGIApplication>`_ class with additional error handling capabilites. See :ref:`error-handling` for a reference.

Also `Route <http://webapp2.readthedocs.io/en/latest/api/webapp2.html#webapp2.Route>`_ is included for your convenience.

For example in `app.yaml <https://cloud.google.com/appengine/docs/standard/python/config/appref#syntax>`_ add::

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



gaetk2\.application package
---------------------------

.. automodule:: gaetk2.application
   :members:
