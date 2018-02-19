Migrating from appengine-toolkit 1 to Version2
==============================================

Some suggestions on moving from Appengine Toolkit Version 1
(`gaetk <https://github.com/mdornseif/appengine-toolkit>`_)
to GAETK2. Obviously you need to add gaetk2 to your
source tree::

    git submodule add https://github.com/mdornseif/appengine-toolkit2.git lib/appengine-toolkit2


First get all the :ref:`error-handling` goodness from GAETK2.

Just ensure that you import the right WSGI Application::

    from gaetk2.application import WSGIApplication
    ....
    application = WSGIApplication([ ...

Often you might have to replace `make_app` by
:class:`~gaetk2.application.WSGIApplication`.

With that you did the most important change. GAETK1 and GAETK2 get along quite well so you might leave it at that for a moment.


Change configuration-files
--------------------------

In :file:`app.yaml` make sure :file:`lib/appengine-toolkit2/include.yaml`
is included and ``jinja2`` is not included via Google (we need jinja 2.10,
Google provides 2.6)::

    includes:
    - lib/appengine-toolkit2/include.yaml
    ...
    libraries:
    - name: ssl
      version: latest
    - name: pycrypto
      version: "latest"
    - name: numpy
      version: "1.6.1"
    - name: PIL
      version: latest

Your :file:`requirements.txt` should end with
``-r lib/appengine-toolkit2/requirements-lib.txt``.

At the top of your :file:`appengine_configuration.py` include this::

    # load gaetk2 bootstrap code without using `sys.path`
    import imp
    (fp, filename, data) = imp.find_module('boot', ['./lib/appengine-toolkit2/gaetk2/'])
    imp.load_module('gaetk_boot', fp, filename, data)

This will set up paths as needed. To get error- and session-handling and
add the following lines at the end of :file:`appengine_config.py`.

    from gaetk2.wsgi import webapp_add_wsgi_middleware  # pylint: disable=W0611

Various configuration needs to be done in :file:`gaetk2_config.py`.
Try ``grep GAETK2_ >> gaetk2_config.py``. Minimal contents would be::


    GAETK2_SECRET='13f221234567890fae123-c0decafe'
    GAETK2_TEMPLATE_DIRS=['./templates', './lib/CentralServices/templates']


Replace Imports
---------------

Replace this::

    from google.appengine.ext.deferred import defer
    from gaetk.infrastructure import taskqueue_add_multi
    from gaetk2.tools import hujson2
    from gaetk.tools import slugify
    from huTools.unicode import deUmlaut
    from huTools import cache


With this::

    from gaetk2.taskqueue import defer
    from gaetk2.taskqueue import taskqueue_add_multi
    from gaetk2.tools import hujson2
    from gaetk2.tools.unicode import slugify
    from gaetk2.tools.unicode import de_umlaut
    from gaetk2.tools.caching import lru_cache, lru_cache_memcache


s/import gaetk.handler/from gaetk2 import exc/
/raise gaetk.handler.HTTP/raise exc.HTTP/


Use a local logger
------------------

At the top of each module create a local logger instance::


    logger = logging.getLogger(__name__)

Then replace calls to :func:`logging.info()` et. al. with calls to
``logger.info()``  et. al.


Change your views / handlers
----------------------------

.. todo::


    * Replace `default_template_vars()` with `build_context()` - no `super()` calls necessary anymore.
    * Authentication has changed significanty. `authchecker()` now handled by `pre_authentication_hook()`, `authentication_hook` and `authorisation_hook()`.
    * if you used the `get_impl()` pattern to wrap your handler functions, you don't need that anymore. The often used `read_basedata()` can be moved into `method_preperation_hook()`.
    * Replace `self.is_admin()` with `self.is_staff()` (or `self.is_sysadmin()`).
    * attrencode to xmlattr:
        ``<meta property="og:price:amount" content="{{ preis|euroword|attrencode }}" />``
        to ``<meta property="og:price:amount" {{ {'content': preis|euroword}|xmlattr }} />``
    * ``authchecker`` to ``authorisation_hook``



This::

    def authchecker(self, method, *args, **kwargs):
        """Sicherstellen, das Sources diese Seiten nicht anschauen dürfen."""
        super(MasterdataHomepage, self).authchecker(method, *args, **kwargs)
        if self.credential.get_typ() == 'source':
            raise exc.HTTP403_Forbidden('Dies ist ein reiner Kundenbereich')

Becomes that::

    def (self, method_name, *args, **kwargs):
        u"""Sicherstellen, dass nur kunden diese seite sehen düfen."""
        if self.credential.get_typ() == 'source':
            raise exc.HTTP403_Forbidden('Dies ist ein reiner Kundenbereich')



Templates
---------

.. todo::

    * Autoescaping

Migrate to Bootstrap 4
----------------------

See `Migrating to v4 <https://getbootstrap.com/docs/4.0/migration/>`_ for
general guidelines. See :ref:`frondend-guidelines` for the desired results.

Usually you want to use ``{% extends "gaetk_base_bs4.html" %}``.

Breadcrubs are now implemented by gaetk. See :ref:`breadcrumbs`.





