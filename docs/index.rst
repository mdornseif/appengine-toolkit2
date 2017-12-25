.. Google App Engine Toolkit 2 documentation master file, created by
   sphinx-quickstart on Sun Dec 17 20:40:22 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

GAETK2 - Google App Engine Toolkit 2
====================================

`gaetk2` is a modern approach to developing Python Code on Google App Engine. It is a reimplementation of `appengine-toolkit <https://github.com/mdornseif>`_appengine-toolkit). `appengine-toolkit` was a transfer of the techniques we used before in Django to the Google App Engine Plattform. It was different time when it was developed - back then XML was still cool and REST was all the rage.
`webapp2 <https://webapp2.readthedocs.io/>`_ had not been developed.

`gaetk2` is used in some big internal projects and tries to cover most of
what an Web Application might need.


Features
--------

* :func:`gaetk2.forms.wtfbootstrap3` to teach a WTForm bootstrap rendering.
* :func:`gaetk2.helpers.check404` to save boilerplate on loading datastore entries etc.
* Lot's of Template-Filters we use day to day in :mod:`gaetk2.jinja_filters`.

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   source/gaetk2.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
