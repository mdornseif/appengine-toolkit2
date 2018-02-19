GAETK2 - Concepts
=================

gaetk is for deploying and developing appengine. We do not use local development servers very much. It also does all development and deploying to production in a single Google App Engine :term:`application`. This means development and testing happens on live data. We are fine with that (see :ref:`error-handling` for details) but you may not.

We use very little of the `backends/modules/services features of App Engine <https://cloud.google.com/appengine/docs/standard/python/an-overview-of-app-engine>`_. See ::term:`Services`.


App Engine Building Blocks
--------------------------

.. glossary::

    application
        A pice of software deployed under a specific `Application ID <https://cloud.google.com/appengine/docs/standard/python/glossary#application_id>`_ on Google App Engine. The ``application`` field in your :file:`app.yaml`.

    version
        a deployment target within your :term:`application`. There are specific
        `versions` for specific purposes. :term:`production version`, :term:`staging version`, a :term:`tagged version` is for deployment and user traffic. A :term:`development version` is for developer interaction.

    production version
        is where :term:`version` your users visit. Should be deployed with care and never without testing. Usually all the traffic of your external domain name like ``application.example.com`` goes here. Note that other App Engine Applications should prefer access under the ``application.appspot.com`` name to get Googles Inter-App Authentication. Code can check via :func:`gaetk2.config.is_production()` if running on the production version.

    staging version
        is the :term:`version` for showcase A/B tests and internal training of upcoming stuff. Available under ``staging-dot-application.appspot.com``.

    tagged version
        like ``v180228-cg89bd1-production``. A specific tagged :term:`version` deployed for production testing. The usual approach is to deploy the production branch to a tagged version, run the test suite against it and then deploy the :term:`production version`. This allows easy switching back to the second to last tagged version if there come up issues in the new :term:`production version`. Available under names like ``v180228-cg89bd1-production-dot-application.appspot.com``.

        The name follows the pattern ``v``, `date`, ``-``, `git hash`, ``-``, `branchname`.

    development version
        like ``dev-md``. Postfixed by the developers username. Meant for development and testing. Usually deployed with the local copy of a master or feature branch. Available under names like ``dev-md-dot-application.appspot.com``.
        Also versions staring with ``test`` will be considered development.
        Code can check via :func:`gaetk2.config.is_development()` if running on a development version.

        Prior to pushing to `master` tests should be run against the deployed :term:`development version`.

    services
    modules
        Generally where we are using App Engine Modules/Services we try to run the same codebase on all Modules/Services to keep deployment and versioning in under control. We mostly use them to fine tune latency and instance size.
        When the :term:`production version` is deployed all services should be redeployed.

    release number
        The string used for the :term:`tagged version`. Also found in :file:`gaetk2-release.txt` and available via :func:`gaetk2.config.get_release()`
