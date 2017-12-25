# appengine-toolkit2

`gaetk2` is a modern approach to developing Python Code on Google App Engine. It is a reimplementation of [appengine-toolkit](https://github.com/mdornseif/appengine-toolkit). `appengine-toolkit` was a transfer of the techniques we used before in Django to the Google App Engine Plattform. It was different time when it was developed - back when XML was still cool and REST was all the rage.

It most noteworthly contribution of gaetk was that it integrated seamless authentication with GoogleInfrastructure - OpenID for Google Apps / Google Suite and Gmail.


See https://docs.pylonsproject.org/projects/webob/en/stable/api/request.html


## Documentation

Documentation is - as always - a work in progress. Check
http://appengine-toolkit2.readthedocs.io/ for the current state of
affairs.


## Authentication

gaetk2 uses Datastore Backed `Credential` Entities to handle Authentication.
Clients can use HTTP-Basic Auth (RfC 7617), Session based Authentication
via Forms, Google Appengine `google.appengine.api.users.GetCurrentUser()`
Interface, HTHP-Bearer Auth (RfC 6750) with JSON Web Tokens (JWT, RfC 7519) to
provide authentication information. In addition gaetk2 can identifiy requests
from AppEnine infrastructure coming via Task-Queues (`X-AppEngine-QueueName`)
and other App Engine Applications (`X-Appengine-Inbound-Appid`).

To activate Authentication, just inherit from `AuthMixin`. E.g.:

```
class DefaultHandler(BasicHandler, AuthMixin):
	pass
```

Per default `AuthMixin` just decodes Authentication Information provided
by the browser on its own. But to log in you have to make the user to
authenticate hinself. While gaetk2 can use username and pasword the main
usage scenario is login via a third Party. gaetk2 currently supports
[Google Identity Platform](https://developers.google.com/identity/)
and [Auth0](https://auth0.com) as login providers. Google because
to use App Engine you and your colleagues already use Google Sign-In.
Auth0 because it is well designed, powerful, easy to use and has decent
debugging support.


`LoginGoogleHandler` and `LoginAuth0Handler` redirect the user to the
[OpenID Connect](https://developers.google.com/identity/protocols/OpenIDConnect)
process where Google or Auth0 Make sure the user is who he claims.
The user is then redirected back to `GoogleOAuth2Callback` or
`AuthOAuth2Callback` where the information sent by Google or Auth0 is
decoded, verified and on first time a `Credential` entity is created in the
database.

Currently users are identified by their E-Mail adress. This might be
problematic if a user changes his address but is the easiest way to identify
the same user across different identity platforms.

For every authenticated user the `uid` (E-Mail) of the `Credential` is safed
in the session. You can assume that when `uid` exists in the session the user
is authenticated.



### Configure Auth0

Create a new Client [at the Auth0 Dashboard](https://manage.auth0.com/). Should be "Regular Web Applications - Traditional web app (with refresh).". Note the "Domain", "Client ID" and "Client Secret" and put them into `appengine_config.py`.

    GAETK2_AUTH0_DOMAIN='exam...ple.eu.auth0.com'
    GAETK2_AUTH0_CLIENT_ID='QJ...um'
    GAETK2_AUTH0_CLIENT_SECRET='mnttt-k0...supersecret'

Now you have to list all allowed URLs where your App mal live = even for testing in "Allowed Callback URLs".


### Configure Google

Create at https://console.cloud.google.com/apis/credentials

## Authorisation

Currently gaetk2 assumes each user which is authenticated is also authrized.


# Generel Flow

## Error Tracking: Sentry

https://docs.sentry.io/learn/releases/
https://blog.sentry.io/2017/05/01/release-commits.html
https://github.com/blog/2388-how-to-fix-errors-in-production-with-github-and-sentry
Dazu machen: `Fixes MYAPP-317`
https://docs.sentry.io/learn/releases/#tell-sentry-about-deploys
