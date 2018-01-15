GAETK2 - Google App Engine Toolkit 2
====================================

`gaetk2` is a modern approach to developing Python Code on Google App Engine. It is a reimplementation of `appengine-toolkit <https://github.com/mdornseif/appengine-toolkit)`. `appengine-toolkit` was a transfer of the techniques we used before in Django to the early Google App Engine Plattform. It was different time when it was developed - back then XML was still cool and REST was all the rage and App Engine was nearly feature free. Even `webapp2 <https://webapp2.readthedocs.io/>`_ had not been developed.

`gaetk2` is used in some big internal projects and tries to cover most of
what an Web Application might need.


Features
--------

* Sane Error Logging and Reporting with nice tracebacks during development. Including Error Reporting to `Sentry <http://sentry.io/>`_. See :ref:`error-handling`.
* A Simple, roubust framework for acceptance tests in :mod:`~gaetk2.resttestlib`
* :func:`gaetk2.forms.wtfbootstrap3` to teach a WTForm bootstrap rendering.
* :func:`gaetk2.helpers.check404` to save boilerplate on loading datastore entries etc.
* Lot's of Template-Filters we use day to day in :mod:`~gaetk2.jinja_filters`.
* Common conventions for ndb/datastore usage in :mod:`~gaetk2.datastore`.
* Day-do-day functionality in :mod:`~gaetk2.tools` Most noteworty:

  * :mod:`gaetk2.tools.caching` provides cache decorators.
  * :mod:`gaetk2.tools.unicode` encode integers in base32, get rid of 😎 etc in strings.


.. toctree::
   :maxdepth: 3
   :caption: Contents:

   concepts.rst
   errorhandling.rst
   frontend.rst
   howto.rst
   source/gaetk2.rst


.. todolist::

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
