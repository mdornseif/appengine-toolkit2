#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/views/login_auth0.py - use Auth0 API to login.

Created by Maximillian Dornseif on 2017-06-28.
Copyright (c) 2017 HUDORA. MIT licensed.
"""
import json
import logging

import urllib

import auth0.v3.authentication

from ..application import make_app
from ..exc import HTTP302_Found
from ..handlers import AuthMixin
from ..handlers import BasicHandler
from ..tools.config import config
from ..tools.ids import guid128


class LoginAuth0Handler(BasicHandler, AuthMixin):
    """Login via Auth0 OpenID Connect.

    This is done by sending the User to the `authorize`-URL. See
    https://auth0.com/docs/api/authentication#authorization-code-grant

    See https://auth0.com/docs/api-auth/tutorials/authorization-code-grant
    and https://auth0.com/docs/quickstart/webapp/python
    """

    def get(self):
        """Reirect to Auth0 to initiate OpenID Connect Auth."""
        # Where do we want to go after auth?
        continue_url = self.request.GET.get('continue', '/').encode('ascii', 'ignore')
        assert continue_url

        # Create a state token to prevent request forgery.
        # Store it in the session for later validation.
        if 'oauth_state' not in self.session:
            self.session['oauth_state'] = guid128()

        # Location of Auth0OAuth2Callback
        callbackpath = '/gaetk2/auth/auth0/oauth2callback'
        callback_url = self.request.host_url + callbackpath
        # This `callback_url` bust be provided in the Auth0
        # Dashboard for yout client under "Allowed Callback URLs"
        self.session['oauth_redirect_uri'] = callback_url

        assert config.AUTH0_DOMAIN != '*unset*'
        assert config.AUTH0_CLIENT_ID != '*unset*'
        # see https://auth0.com/docs/api/authentication#implicit-grant
        # Construct OAuth Request.
        params = dict(
            client_id=config.AUTH0_CLIENT_ID,
            scope="openid email profile",
            response_type="code",
            redirect_uri=self.session['oauth_redirect_uri'],
            state=self.session['oauth_state'],
            audience='https://' + config.AUTH0_DOMAIN + '/userinfo',
        )

        oauth_url = 'https://' + config.AUTH0_DOMAIN + '/authorize' + '?' + urllib.urlencode(params)

        # redirect for google to get Authenticated
        logging.info(
            'redirecting with state %r to %s via %s',
            self.session['oauth_state'],
            self.session['oauth_redirect_uri'],
            oauth_url)
        raise HTTP302_Found(location=oauth_url)


class Auth0OAuth2Callback(BasicHandler, AuthMixin):
    """Handles OpenID Connect Callback from Auth0."""

    def get(self):
        """Fetch user data in response to OpenID call."""
        # see http://filez.foxel.org/0F1Z1m282B1M
        continue_url = self.session.pop('continue_url', '/')

        # 3. Confirm anti-forgery state token
        oauth_state = self.session.pop('oauth_state', None)
        if self.request.get('state') != oauth_state:
            logging.error(
                "wrong state: %r != %r", self.request.get('state'), oauth_state)
            logging.debug("session: %s", self.session)
            logging.debug("request: %s", self.request.GET)
            self.session.terminate()
            # Redirect to try new login
            raise HTTP302_Found(location=continue_url)

        # 4. Exchange code for access token and ID token
        get_token = auth0.v3.authentication.GetToken(config.AUTH0_DOMAIN)
        auth0_users = auth0.v3.authentication.Users(config.AUTH0_DOMAIN)

        token = get_token.authorization_code(config.AUTH0_CLIENT_ID,
                                             config.AUTH0_CLIENT_SECRET,
                                             self.request.get('code'),
                                             self.request.url)
        user_info = json.loads(auth0_users.userinfo(token['access_token']))

        logging.info('user_info: %r', user_info)

        # {u'family_name': u'Dornseif',
        # u'sub': u'salesforce|005D0000001pai7IAA',
        # u'picture': u'https://c.eu4.content.force.com/profilephoto/729D0000000CrOF/F',
        # u'locale': u'de-DE_EURO',
        # u'email_verified': True,
        # u'updated_at': u'2017-06-29T13:53:57.673Z',
        # u'given_name': u'Dr. Maximillian',
        # u'nickname': u'm.dornseif',
        # u'email': u'm.dornseif@hudora.de',
        # u'name': u'Dr. Maximillian Dornseif'}

        # { "admin": true,
        #  "created_at": "2011-10-26 13:00:28.024000",
        #  "created_by": "107704714638677207944/m.dornseif@hudora.de",
        # "updated_at": "2017-06-30 08:05:50.997510",
        # "updated_by": "107704714638677207944/m.dornseif@hudora.de",
        # "env": { "AUTH_DOMAIN": "auth.gaetk2.23.nu",
        # "FEDERATED_IDENTITY": null,
        # "FEDERATED_PROVIDER": null,
        # "USER_NICKNAME": "", "USER_ORGANIZATION": "" },

        self._login_user('OAuth2', user_info)
        logging.info("logging in with final destination %s", continue_url)
        raise HTTP302_Found(location=continue_url)


# die URL-Handler fuer's Login via Google OpenID Connect
application = make_app([
    (r'^/gaetk2/auth/auth0/oauth2callback$', Auth0OAuth2Callback),
    (r'.*', LoginAuth0Handler),
])
