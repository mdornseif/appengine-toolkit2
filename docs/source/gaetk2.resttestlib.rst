gaetk2.resttestlib - Simple Acceptance Tests
============================================

.. py:module:: gaetk2.resttestlib

This module allows you to run simple non-interactive tasks against an installed Version of your application. We found that it helps to catch most simple programming errors and regressions prior to production deployment.

Simple tests look like this::

    from gaetk2.resttestlib import create_testclient_from_cli
    client = create_testclient_from_cli('myserver.appspot.com')

    client.GET('/_ah/warmup').responds_http_status(200)

    client.run_checks(max_workers=4)
    print len(client.responses), "URLs tested"
    sys.exit(client.errors)

This uses the low-level :class:`Response` interface. But usually you will work with the :meth:`TestClient.check()` family of functions. Check can handle more than one URL at once::

    client.check(
        '/mk/pay/start/a6LP3L',
        '/mk/pay/paypal/init/a6LP3L'
    )

Based on file extension we check not only the content type, but also that
the response is well formed - at least to a certain degree::

    client.check(
        '/k/SC10001/artikel',
        '/api/marketsuche.json'
        '/k/SC10001/artikel.csv',
        '/k/SC10001/artikel.html',
        '/k/SC10001/artikel.xml'
    )


:meth:`TestClient.check_redirect()` takes a list of sources and destinations
and ensures that the server redirects to the desired destination::

    client.check_redirect(
        dict(url='/artnr/73005/', to='/artnr/73000/'),
        dict(url='/artnr/73000/', to='/artnr/73000/01/'),
    )


The framework is meant to check for fine grained access controls via
HTTP-Basic-Auth. You can provide a list of ``handle=username:password``
pairs during instantiation or via the command line. You can then refer to
them in your checks the the ``auth`` parameter::

    users = [
        'usera=CK101:FNYBMAMPVC6EU',
        'userb=u1001:TEABPVPGPVGBFE',
        'admin=u2001:LQASNAJC6GUUP4VY',
        'inactiveuser=u22730o:MATLEU4BJA756']
    client = create_testclient_from_cli('myserver.appspot.com', users)
    client.check(
        '/pay/start/testingClassic',
        '/mk/pay/paypal/init/testingMarket',
        auth='usera')
    client.check_redirect(dict(url='/', to='/inactive.html'), auth='inactiveuser')

One of the main uses of `resttestlib` is to check that certain resources are allowed for some users and denied for others::

    client.check_allowdeny(
        '/k/SC10001/auftraege',
        allow=['usera', 'admin'],
        deny=['userb', None]
    )

The special user ``None`` means unauthenticated.


.. todo::

Describe how this is part of the general test and deployment strategy.


Module contents
---------------

.. automodule:: gaetk2.resttestlib
    :members:
    :undoc-members:
