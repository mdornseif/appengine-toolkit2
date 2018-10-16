.. _`gaetk2-aaa`:
Authentication, Authorization & Access Control
==============================================

`Authentication` is finding out who you are dealing with.
`Authorization` is if the `authenticated` user allowed
to do what he does. `Access Control` is the implementation of it all.
All of it together is sometimes called AAA.

 You can configure basic AAA in `app.yaml <https://cloud.google.com/appengine/docs/standard/python/config/appref#syntax>`_.

See the `templatetags-accesscontrol`_ Section in `templatetags`_ Document for of to make your templates dependant on who is logged in.

Authentication
--------------

gaetk2 uses Datastore Backed `Credential` Entities to handle Authentication.
Clients can use

* HTTP-Basic Auth (RfC 7617)
* Session based Authentication via Forms
* Google Appengine :func:`google.appengine.api.users.GetCurrentUser()` Interface / `Google Identity Platform <https://developers.google.com/identity/>`_
* `Auth0 <https://auth0.com>`_
* HTTP-Bearer Auth (RfC 6750) with JSON Web Tokens (JWT, RfC 7519)

to provide authentication information. In addition gaetk2 can identifiy requests
form certain infrastructure:

* App Engine Task-Queues (``X-AppEngine-QueueName``)
* Other App Engine Applications (``X-Appengine-Inbound-Appid``)
* Sentry

To activate Authentication, just inherit from :class:`~gaetk2.handlers.authentication.AuthenticationReaderMixin`. E.g.::

    class DefaultHandler(BasicHandler, AuthenticationReaderMixin):
        pass

Per default :class:`~gaetk2.handlers.authentication.AuthenticationReaderMixin` just decodes Authentication Information provided by the browser on its own. But to log in you have to make the user to authenticate himself. While gaetk2 can use username and password the main usage scenario is login via a third Party (Auth0 or Google). gaetk2 currently supports `Google Identity Platform <https://developers.google.com/identity/>`_ and `Auth0 <https://auth0.com>`_ as login providers. Google because to use App Engine you and your colleagues already use Google Sign-In. Auth0 because it is well designed, powerful, easy to use and has decent debugging support.

`LoginGoogleHandler` and `LoginAuth0Handler` redirect the user to the `OpenID Connect <https://developers.google.com/identity/protocols/OpenIDConnect>`_ process where Google or Auth0 Make sure the user is who he claims. The user is then redirected back to `GoogleOAuth2Callback` or `AuthOAuth2Callback` where the information sent by Google or Auth0 is decoded, verified and on first time a `Credential` entity is created in the database.

.. todo::

    * Explain usage

Currently users are identified by their E-Mail Address. This might be problematic if a user changes his address but is the easiest way to identify the same user across different identity platforms.

For every authenticated user the `uid` (E-Mail) of the `Credential` is safed in the session. You can assume that when `uid` exists in the session the user is authenticated.

Configure Auth0
^^^^^^^^^^^^^^^

Create a new Client `at the Auth0 Dashboard <https://manage.auth0.com/`_. Should be "Regular Web Applications - Traditional web app (with refresh).". Note the "Domain", "Client ID" and "Client Secret" and put them into :file:`appengine_config.py`::

    GAETK2_AUTH0_DOMAIN='exam...ple.eu.auth0.com'
    GAETK2_AUTH0_CLIENT_ID='QJ...um'
    GAETK2_AUTH0_CLIENT_SECRET='mnttt-k0...supersecret'

Now you have to list all allowed URLs where your App may live - even for testing - in "Allowed Callback URLs".


Configure Google
^^^^^^^^^^^^^^^^

Create at https://console.cloud.google.com/apis/credentials


Authenticating Sentry
^^^^^^^^^^^^^^^^^^^^^

If you use Sentry for Log Aggregation and Error Reporting (See :ref:`sentry-configuration`.) then the Sentry Server will try to fetch certain resources like source maps from your App.
Sentry `uses a bilateral token to authenticate these calles <https://blog.sentry.io/2017/06/15/notice-of-address-change>`_.
If you set ``GAETK2_SENTRY_SECURITY_TOKEN`` in :file:`appengine_config` to the same value than in the Sentry Web Page Settings section all calls from the Sentry Sertver will be authenticated automatically with a ``uid`` of ``X-Sentry-Token@auth.gaetk2.23.nu``.


How JWTs work in gaetk2
^^^^^^^^^^^^^^^^^^^^^^^

``/gaetk2/auth/getjwt.txt`` can be requested to get a JWT. To access ``getjwt.txt`` you have to be already authenticated by other means. The JWT  will be returnesd as a plain text string. See `jwt.io <https://jwt.io/>`_ for more information on how JWTs are constucted.

The token obtained this way can be used to authenticate to oter parts
of the gaetk2 app. This is done doing HTTP-Requests with an Authorisation-Header::

    Authorization: bearer <your token>

The tokens provided by ``/gaetk2/auth/getjwt.txt`` are only calid for a limited time.

:class:`AuthenticationReaderMixin` can load credentials from the tokens provided by ``/gaetk2/auth/getjwt.txt``. It also can load credentials based on data provided by Auth0. More documentation is needed.




Authorisation
-------------

Currently gaetk2 assumes each user which is authenticated is also authorized.
Needs work.
