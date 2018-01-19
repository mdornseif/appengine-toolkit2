#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/views/login_google.py - use Google OAuth Connect.

based on EDIhub/login.py

Created by Maximillian Dornseif on 2010-09-24.
Copyright (c) 2010, 2014, 2015 HUDORA. MIT licensed..
"""
import base64
import json
import logging
import os
import unicodedata
import urllib

from ..application import make_app
from ..exc import HTTP302_Found
from ..exc import HTTP403_Forbidden
from ..handlers import AuthenticationReaderMixin
from ..handlers import BasicHandler
from ..tools import http
from ..tools.config import config
from ..tools.ids import guid128


logger = logging.getLogger(__name__)


class LoginGoogleHandler(BasicHandler, AuthenticationReaderMixin):
    """Login via GoogleApps OpenID Connect.

    See https://developers.google.com/identity/protocols/OpenIDConnect#authenticatingtheuser
    for an outline how this works.
    """

    def get(self):
        """Rdirect to google to initiate OpenID Connect Auth."""
        continue_url = self.request.GET.get('continue', '/').encode('ascii', 'ignore')
        assert continue_url

        # 1. AuthenticationReaderMixin already did HTTP basic Auth
        # (see RFC 2617) if `Authorization: basic ` header
        # has been provided.
        #
        # 2. AuthenticationReaderMixin already did HTTP JWT/bearer Auth if `Authorization: bearer ` header
        # has been provided.
        #
        # 3. AuthenticationReaderMixin already did App Engine / Google Apps based Authentication
        #
        # 4. AuthenticationReaderMixin already did session based Authentication

        # Create a state token to prevent request forgery.
        # Store it in the session for later validation.
        if 'oauth_state' not in self.session:
            self.session['oauth_state'] = guid128()

        # try to construct a valid callback URL
        # Callback URLs must be registered at Google to avoid nasty errors
        # so we try to find an URL which has ben registered
        # edit at https://console.cloud.google.com/apis/credentials
        callbackpath = '/gaetk2/auth/google/oauth2callback'

        # First try the host the current request came from
        callback_url = self.request.host_url + callbackpath
        if callback_url not in config.OAUTH_GOOGLE_CONFIG['redirect_uris']:
            logger.critical("%s not valid", callback_url)
            # this did not work. Try to get the Servername from the
            # environment and enforce https
            callback_url = 'https://' + os.environ.get('SERVER_NAME') + callbackpath
            if callback_url not in config.OAUTH_GOOGLE_CONFIG['redirect_uris']:
                logger.debug("%s no valid callback", callback_url)
                # this did not work. Try to use the default version.
                callback_url = 'https://' + os.environ.get('DEFAULT_VERSION_HOSTNAME') + callbackpath
                if callback_url not in config.OAUTH_GOOGLE_CONFIG['redirect_uris']:
                    logger.debug("%s no valid fallback callback", callback_url)
                    # this also did not work. Just use the first available callback URL.
                    callback_url = config.OAUTH_GOOGLE_CONFIG['redirect_uris'][0]
            logger.info('using %s', callback_url)

        self.session['oauth_redirect_uri'] = callback_url
        # Construct OAuth Request.
        params = dict(
            client_id=config.OAUTH_GOOGLE_CONFIG['client_id'],
            response_type="code",
            scope="openid email profile",
            redirect_uri=self.session['oauth_redirect_uri'],
            state=self.session['oauth_state'],
            # login_hint="jsmith@example.com",
            # can be the user's email address or the sub string, which is equivalent
            # to the user's Google ID. If you do not provide a login_hint and the user
            # is currently logged in, the consent screen includes a request for approval
            # to release the user’s email address to your app.
        )
        # help choosing domain name
        if len(config.OAUTH_GOOGLE_ALLOWED_DOMAINS) == 1:
            # Use the hd parameter to optimize the OpenID Connect flow for
            # users of a particular G Suite domain.
            params['hd'] = config.OAUTH_GOOGLE_ALLOWED_DOMAINS[0]
        elif config.OAUTH_GOOGLE_ALLOWED_DOMAINS:
            params['hd'] = '*'

        oauth_url = config.OAUTH_GOOGLE_CONFIG['auth_uri'] + '?' + urllib.urlencode(params)

        # If user is already authenticated, redirect logged in user to `continue_url`,
        # else redirect to Google Apps OAuth Login.
        # if self.credential:
        #    raise HTTP302_Found(location=continue_url)

        # redirect for google to get Authenticated
        logger.info(
            'redirecting with state %r to %s via %s',
            self.session['oauth_state'], self.session['oauth_redirect_uri'], oauth_url)
        raise HTTP302_Found(location=oauth_url)


class GoogleOAuth2Callback(BasicHandler, AuthenticationReaderMixin):
    """Handles OpenID Connect  Callback from Google."""

    def get(self):
        """Fetch user data in response to OpenID call."""
        # see http://filez.foxel.org/0F1Z1m282B1M
        continue_url = self.session.pop('continue_url', '/')

        # 3. Confirm anti-forgery state token
        oauth_state = self.session.pop('oauth_state', None)
        if self.request.get('state') != oauth_state:
            logger.error(
                "wrong state: %r != %r", self.request.get('state'), oauth_state)
            logger.debug("session: %s", self.session)
            logger.debug("request: %s", self.request.GET)
            self.session.terminate()
            # Redirect to try new login
            raise HTTP302_Found(location=continue_url)

        if config.OAUTH_GOOGLE_ALLOWED_DOMAINS:
            if self.request.get('hd') not in config.OAUTH_GOOGLE_ALLOWED_DOMAINS:
                raise HTTP403_Forbidden(
                    "Wrong domain: %r not in %r" % (
                        self.request.get('hd'), config.OAUTH_GOOGLE_ALLOWED_DOMAINS))

        # 4. Exchange code for access token and ID token by requesting data from Google
        url = config.OAUTH_GOOGLE_CONFIG['token_uri']
        # get token
        params = dict(
            code=self.request.get('code'),
            client_id=config.OAUTH_GOOGLE_CONFIG['client_id'],
            client_secret=config.OAUTH_GOOGLE_CONFIG['client_secret'],
            redirect_uri=self.session.pop('oauth_redirect_uri', ''),
            grant_type="authorization_code")
        # data = huTools.http.fetch_json2xx(url, method='POST', content=params)
        data = http.fetch_json(url, params, method='POST')

        logger.info('token: %s', data)
        input_jwt = data['id_token'].split('.')[1]
        input_jwt = unicodedata.normalize('NFKD', input_jwt).encode('ascii', 'ignore')
        # Append extra characters to make original string base 64 decodable.
        input_jwt += '=' * (4 - (len(input_jwt) % 4))
        jwt = base64.urlsafe_b64decode(input_jwt)
        jwt = json.loads(jwt)
        logger.info("jwt = %r", jwt)
        # email_verified True if the user's e-mail address has been verified
        # TODO: use jose for decoding JWT
        # jwt = {
        #   u'aud': u'554091237783-sd3dec8dp3ujd4798djakh7h7a080p05.apps.googleusercontent.com',
        #   u'iss': u'accounts.google.com',
        #   u'email_verified': True,
        #   u'at_hash': u'NvVkh9KqYGb3ao7t01fKvg',
        #   u'exp': 1498461303,
        #   u'azp': u'554091237783-sd3dec8dp3ujd4798djakh7h7a080p05.apps.googleusercontent.com',
        #   u'iat': 1498457703,
        #   u'email': u'k.klingbeil@hudora.de',
        #   u'hd': u'hudora.de',
        #   u'sub': u'114400842898019538607'}
        assert jwt['iss'] == 'accounts.google.com'
        assert jwt['aud'] == config.OAUTH_GOOGLE_CONFIG['client_id']
        if config.OAUTH_GOOGLE_ALLOWED_DOMAINS:
            assert jwt['hd'] in config.OAUTH_GOOGLE_ALLOWED_DOMAINS
        # note that the user is logged in

        # hd FEDERATED_IDENTITY FEDERATED_PROVIDER
        for name in 'USER_EMAIL USER_ID USER_IS_ADMIN USER_NICKNAME USER_ORGANIZATION'.split():
            logger.info("%s: %r", name, os.environ.get(name))

        self._login_user('OAuth2', jwt)
        logger.info("logging in with final destination %s", continue_url)
        raise HTTP302_Found(location=continue_url)


# die URL-Handler fuer's Login via Google OpenID Connect
application = make_app([
    (r'^/gaetk2/auth/google/oauth2callback$', GoogleOAuth2Callback),
    (r'.*', LoginGoogleHandler),
])
