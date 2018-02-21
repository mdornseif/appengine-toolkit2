gaetk2\.config module
=====================

Framework Configuration
-----------------------

`gaetk2` expects it information to be found in :file:`gaetk2_config.py`.
Minimal content is::

    GAETK2_SECRET='*some random value*'

.. index::
   pair: gaetk2_config.py; GAETK2_SECRET

``GAETK2_SECRET`` is used for Session generation etc. Try something like ``(dd if=/dev/urandom count=1000 ) | shasum`` to get a nice value for `GAETK2_SECRET`.

.. index:: <entries>
This directive contains one or more index entries. Each entry consists of a type and a value, separated by a colon.

.. todo::

    Document other configuration values.



Runtime Information
---------------------

The functions :func:`~gaetk2.config.get_environment()`,
:func:`~gaetk2.config.get_release()` and
:func:`~gaetk2.config.get_revision()` allow the caller to find out about
the deployment.


Runtime Configuration
---------------------

:func:`~gaetk2.config.get_config()` and :func:`~gaetk2.config.set_config()` allow
you to set datastore backed configration values. These are saved via :class:`gaetk_Configuration`. `NDB caching <https://cloud.google.com/appengine/docs/standard/python/ndb/cache>`_ applies so keep in mind that changing
the values in the datastore via the Google App Engine Admin Console does not update this cache.

.. todo::

    Document the view to change runtime configuration values.


Module contents
---------------

.. automodule:: gaetk2.config
    :members:
    :undoc-members:
    :show-inheritance:


