Build Commands & Deployment
===========================

gaetk2 based Application still use old school Makefiles as their main interface for comand line building, testing and deploying. But because make is too complex for young people to understand we use Python helpers in the background and let grunt and webpack do some of the work. This is not optimal and slowish.

.. warning::

This is not implemented so far in gaetk2. It has to be ported over from gaetk1.


Commands
--------

.. glossary::

    doit openlogs
        open App Engine logfiles in Browser

    doit deploy
        installs the current checkout as a developer specific version and
        opens it in the browser

    doit build
        builds assets (Javascript, CSS) and other dependencies for development

    doit mergeproduction
        process to merge `master` into `production`

    doit check
        TBD

    doit staging_deploy
        TBD

    testing_deploy
        TBD

    testing_test
        TBD

    doit production_clean_checkout
        TBD

    doit production_build
        like `doit built` but produces minified, optimized versions

    doit production_deploy
        TBD

    Parameter -a, --always-execute
        execute even if dependencies are up to date

    Parameter -v ARG, --verbosity=ARG
        0-2

    Parameter -s, --single
        Execute only specified tasks ignoring their dependencies

    doit doit info -s <task>
        Show on what the task depends
