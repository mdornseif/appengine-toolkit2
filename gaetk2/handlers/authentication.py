#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2.handlers.authentication

AuthenticationReaderMixin - Authentication MixIns for gaetk2.

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2010-2018 HUDORA. MIT licensed.
"""
from __future__ import unicode_literals

import datetime
import json
import logging
import os
import urllib

from google.appengine.api import users

import requests

from gaetk2 import exc
from gaetk2 import models
from gaetk2.config import gaetkconfig
from gaetk2.helpers import check404
from gaetk2.tools.caching import lru_cache_memcache
from gaetk2.tools.sentry import sentry_client
from jose import jwt


logger = logging.getLogger(__name__)


class AuthenticationReaderMixin(object):
    """Class which adds authentication."""

    def authentication_preflight_hook(self, method, *args, **kwargs):
        """Find out if the User is authenticated in any sane way and if so load the credential."""
        # Automatically called by `dispatch`.
        # This funcion is somewhat involved. We accept
        # 1) Authentication via HTTP-Auth
        # 2) Authentication via JWT
        # 3) Authentication via Session
        # 4) Login via OAuth with speciffic domains registered at Google Apps
        # 5) Login for Google Special Calls from Cron & TaskQueue

        self.credential = None
        uid, secret = None, None
        # 1. Check for valid HTTP-Basic Auth Login
        if self.request.headers.get('Authorization', '').lower().startswith('basic '):
            auth_type, encoded = self.request.headers.get('Authorization').split(None, 1)
            decoded = encoded.decode('base64')
            # If the Client send us invalid credentials, let him know , else parse into
            # username and password
            if ':' not in decoded:
                raise exc.HTTP400_BadRequest(explanation='invalid credentials %r' % decoded)
            uid, secret = decoded.strip().split(':', 1)
            sentry_client.note(
                'user', 'HTTP-Auth attempted for %r' % uid,
                data=dict(auth_typ=auth_type, decoded=decoded))

            self.credential = self.get_credential(uid or ' *invalid* ')
            if self.credential and self.credential.secret == secret.strip():
                # Successful login
                return self._login_user('HTTP')
            else:
                logger.error(
                    'failed HTTP-Login from %s/%s %s %s %r %r', uid, self.request.remote_addr,
                    self.request.headers.get('Authorization'),
                    self.credential, self.credential.secret, secret.strip())
                logger.info('Falsches Credential oder kein secret')
                raise exc.HTTP401_Unauthorized(
                    'Invalid HTTP-Auth Infomation',
                    headers={'WWW-Authenticate': 'Basic realm="API Login"'})

        # 2. Check for valid Authentication via JWT via GAETK2 or Auth0 Tokens
        if self.request.headers.get('Authorization', '').lower().startswith('bearer '):
            auth_type, access_token = self.request.headers.get('Authorization').split(None, 1)
            # non standards extension to allow us to transport access and id token
            id_token = None
            if ' ' in access_token:
                access_token, id_token = access_token.split(None, 1)
            logging.debug('token: %s', access_token)
            unverified_header = jwt.get_unverified_header(access_token)
            if gaetkconfig.JWT_SECRET_KEY and unverified_header['alg'] == 'HS256':
                # gaetk2 JWT for internal use
                userdata = self.decode_jwt(access_token, gaetkconfig.JWT_SECRET_KEY, algorithms=['HS256'])
                # 'sub': u'm.dornseif@hudora.de'}
                self.credential = check404(
                    self.get_credential(userdata['sub']),
                    'unknown uid %r' % userdata['sub'])
                # We do not check the password because get_current_user() is trusted
                return self._login_user('gaetk2 JWT')
            else:
                # Auth0 JWT, see http://filez.foxel.org/2P2o1O3j2f1N
                userdata = self.decode_jwt(
                    access_token, get_jwt_key(unverified_header['kid']), algorithms=['RS256'])
                # For Auth0 / OpenID authentication there should be an user in our database
                self.credential = models.gaetk_Credential.query(
                    models.gaetk_Credential.external_uid == userdata['sub']).get()
                email = None
                if not self.credential:
                    # if not: can we find one by id_token?
                    if userdata.get('email_verified'):
                        email = userdata.get('email')
                    else:
                        if id_token:
                            userdata = self.decode_jwt(
                                id_token, get_jwt_key(unverified_header['kid']),
                                algorithms=['RS256'], access_token=access_token)
                            if userdata.get('email_verified'):
                                email = userdata.get('email')
                    if email:
                        self.credential = models.gaetk_Credential.query(
                            models.gaetk_Credential.email == email).get()
                        logging.info('%s zugeordnet', self.credential)
                        # if self.credential:
                        #     self.credential.external_uid = userdata['sub']
                        #     self.credential.put()
                self.credential = check404(
                    self.credential,
                    '%s not found' % userdata['sub'])
                # We do not check the password because get_current_user() is trusted
                return self._login_user('Auth0 JWT')

        # 3. Check for App Engine / Google Apps based Login
        user = users.get_current_user()
        if user:
            self.credential = self.get_credential(user.email())
            if self.credential:
                # We do not check the password because get_current_user() is trusted
                return self._login_user('Google User OpenID Connect')

        # 4. Check for session based login
        if self.session.get('uid'):
            logger.debug('trying session based login')
            self.credential = self.get_credential(self.session['uid'])
            if self.credential:
                # We do not check the password because session storage is trusted
                return self._login_user('session')
            else:
                logger.warn(
                    'No Credential for Session: %s. Progressing unauthenticated',
                    self.session.get('uid'))
                self._clear_session()

        # 5. Login for Google Special Calls from Cron & TaskQueue
        # X-AppEngine-QueueName
        # https://cloud.google.com/appengine/docs/standard/python/config/cron#securing_urls_for_cron
        if self.request.headers.get('X-AppEngine-QueueName'):
            uid = 'X-AppEngine-Taskqueue-{}'.format(
                self.request.headers.get('X-AppEngine-QueueName'))
            self.credential = models.gaetk_Credential.create(
                id=uid, uid=uid, text='created automatically via gaetk2')
            return self._login_user('AppEngine')
        # X-Appengine-Inbound-Appid
        # https://cloud.google.com/appengine/docs/standard/python/appidentity/#asserting_identity_to_other_app_engine_apps
        ibaid = self.request.headers.get('X-Appengine-Inbound-Appid')
        if ibaid:
            if ibaid in gaetkconfig.INBOUND_APP_IDS:
                uid = 'X-Appengine-Inbound-Appid-{}'.format(ibaid)
                self.credential = models.gaetk_Credential.create(
                    id=uid, uid=uid, text='created automatically via gaetk2')
                return self._login_user('AppEngine')
            else:
                logging.debug(
                    'configure INBOUND_APP_IDS to allow %s access',
                    self.request.headers.get('X-Appengine-Inbound-Appid'))
        # TODO:
        # x-appengine-user-is-admin
        # x-appengine-auth-domain
        # x-google-real-ip
        # https://cloud.google.com/appengine/docs/standard/python/appidentity/
        # X-Appengine-Cron: true

        # 6. log in by Sentry bot
        # see https://blog.sentry.io/2017/06/15/notice-of-address-change
        if self.request.headers.get('X-Sentry-Token'):
            if gaetkconfig.SENTRY_SECURITY_TOKEN:
                if self.request.headers.get('X-Sentry-Token') == gaetkconfig.SENTRY_SECURITY_TOKEN:
                    uid = 'X-Sentry-Token@auth.gaetk2.23.nu'
                    self.credential = models.gaetk_Credential.create(
                        id=uid, uid=uid, text='created automatically via gaetk2')
                    return self._login_user('Sentry')

        logger.info(
            'user unauthenticated: Authorization:%r User:%r Session:%r QueueName:%r Appid:%r Sentry:%r',
            self.request.headers.get('Authorization', ''),
            users.get_current_user(),
            self.session,
            self.request.headers.get('X-AppEngine-QueueName'),
            self.request.headers.get('X-Appengine-Inbound-Appid'),
            self.request.headers.get('X-Sentry-Token')
        )

    def decode_jwt(self, token, key, algorithms=['RS256'], access_token=None):
        """Decode data from JWT and handle common failures."""
        # See http://python-jose.readthedocs.io/en/latest/jwt/api.html#jose.jwt.decode
        try:
            userdata = jwt.decode(
                token,
                key,
                algorithms=algorithms,
                # audience=gaetkconfig.JWT_AUDIENCE[0],
                issuer=[
                    'https://{}/'.format(gaetkconfig.AUTH0_DOMAIN),
                    'http://auth.gaetk2.23.nu/'],
                access_token=access_token,
                options={'verify_aud': False}
            )
        except jwt.ExpiredSignatureError:
            logger.debug('token: %s audience: %s', token, gaetkconfig.JWT_AUDIENCE)
            raise exc.HTTP400_BadRequest('ExpiredSignatureError')
        except jwt.JWTClaimsError, e:
            logger.debug('audience: %s', gaetkconfig.JWT_AUDIENCE)
            logger.debug('audience: %s', token)
            logger.debug('claims: %s', jwt.get_unverified_claims(token))
            raise exc.HTTP400_BadRequest('Wrong Claim: %s' % e)
        except jwt.JWTError, e:
            logger.debug('claims: %s', jwt.get_unverified_claims(token))
            raise exc.HTTP400_BadRequest('JWT Error: %s' % e)
        return userdata

    def _login_user(self, via, jwtinfo=None):
        """Ensure the system knows that a user has been logged in."""
        # user did not exist before but we have a validated jwt
        sentry_client.note(
            'user', 'logging in via %s' % via,
            data=dict(jwtinfo=jwtinfo, credential=self.credential))
        if not self.credential and jwtinfo:
            # create credential from JWT
            self.credential = allow_credential_from_jwt(jwtinfo)
            if not self.credential:
                # here we could redirect the user to a page
                # explaining that we couldn't match the data
                # given by him to our local database.
                raise exc.HTTP401_Unauthorized(
                    explanation="Couldn't assign {} to a local user".format(jwtinfo))

        # ensure that users with empty password are never logged in
        if self.credential and not self.credential.secret:
            raise exc.HTTP403_Forbidden(explanation='Account %s disabled' % self.credential.uid)

        if not self.credential:
            raise RuntimeError('unknown user via %r' % via)

        if 'uid' not in self.session or self.session['uid'] != self.credential.uid:
            self.session['uid'] = self.credential.uid
        if 'login_via' not in self.session:
            self.session['login_via'] = via
        if 'login_time' not in self.session:
            self.session['login_time'] = datetime.datetime.now()
        # if AppEngine did not set Variables, we fake them
        # this is helpful for things like `ndb.UserProperty(auto_current_user=True)`
        if not os.environ.get('USER_ID', None):
            os.environ['USER_ID'] = self.credential.uid
            os.environ['AUTH_DOMAIN'] = 'auth.gaetk2.23.nu'
            # os.environ['USER_IS_ADMIN'] = credential.admin
            if self.credential.email:
                os.environ['USER_EMAIL'] = self.credential.email
            else:
                # fake email-address
                os.environ['USER_EMAIL'] = '%s@auth.gaetk2.23.nu' % self.credential.uid

        sentry_client.note(
            'user', '%s logged in via %s since %s sid:%s' % (
                self.credential.uid,
                self.session.get('login_via'),
                self.session.get('login_time'),
                getattr(self.session, 'sid', '?')),
            data=dict(
                credential=self.credential,
                login_via=self.session.get('login_via'),
                login_time=self.session.get('login_time'),
                sid=getattr(self.session, 'sid', '?')))
        sentry_client.user_context({
            'email': os.environ.get('USER_EMAIL'),
            'id': self.credential.uid,
            'username': self.credential.name,
            # HTTP_X_APPENGINE_CRON   true
            # USER_ORGANIZATION USER_IS_ADMIN
        })
        self.response.headers.add_header(b'X-uid', str(self.credential.uid))

    def _interactive_client(self):
        """Check if we cvan redirect the client for login."""
        if (self.request.is_xhr or self.request.get('no401redirect') == '1' or
                'xmlhttprequest' in self.request.headers.get('X-Requested-With', '').lower() or
                # ES6 Fetch API
                'Fetch' in self.request.headers.get('X-Requested-With', '') or
                # JSON only client
                self.request.headers.get('Accept', '') == 'application/json'):
            return False
        return (
            'text/' in self.request.headers.get('Accept', '') or
            'image/' in self.request.headers.get('Accept', '') or
            'Mozilla' in self.request.headers.get('User-Agent', ''))

    def get_credential(self, username):
        """Read a credential from the database or return None."""
        cred = models.gaetk_Credential.get_by_id(username)
        if not cred:
            logger.debug('could not get credential %r', username)
            # legacy, update from gaetk1
            import gaetk.handler
            cred1 = gaetk.handler._get_credential(username)
            if cred1:
                cred = models.gaetk_Credential.create(
                    uid=cred1.uid, email=cred1.email, secret=cred1.secret,
                    permissions=cred1.permissions, text=cred1.text,
                    sysadmin=cred1.admin)
                cred.put()
                cred.populate(created_at=cred1.created_at, updated_at=cred1.updated_at)
                if getattr(cred1, 'source', None):
                    cred.org_designator = cred1.source.id()
                elif getattr(cred1, 'kundennr', None):
                    cred.org_designator = cred1.kundennr
                cred.put()
        if cred:
            if cred.meta is None:
                cred.meta = {}
                cred.put()
            if (not cred.staff) and cred.email:
                if (cred.email.endswith('@hudora.de') or cred.email.endswith('@cyberlogi.de')):
                    cred.staff = True
                    cred.put()

        return cred


def allow_credential_from_jwt(jwt):
    # Tested with:
    # * GitHub
    # * Google-Apps
    # * Salesforce
    logger.debug('JWT: %s', jwt)
    if jwt.get('email_verified') and jwt['email'].endswith('@hudora.de'):
        return models.gaetk_Credential.create(
            id=jwt['email'],
            uid=jwt['email'],
            text='created via OAuth2/JWT',
            email=jwt['email'])
    else:
        return None


@lru_cache_memcache(ttl=60 * 60 * 12)
def get_jwt_key(kid):
    """Get the public key via http."""
    # from https://github.com/auth0-samples/auth0-python-api-samples/blob/master/00-Starter-Seed/server.py
    # This is only as secure as our HTTP connection is secure ...
    url = 'https://{}/.well-known/jwks.json'.format(gaetkconfig.AUTH0_DOMAIN)
    response = requests.get(url)
    logger.info('reading keys from %r', url)
    jwks = json.loads(response.content)
    rsa_key = {}
    for key in jwks['keys']:
        if key['kid'] == kid:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }
    return rsa_key


class AuthenticationRequiredMixin(AuthenticationReaderMixin):
    """Class which adds authorisation."""

    def authentication_hook(self, method, *args, **kwargs):
        """Function to enforce that users `are authenticated."""

        if self.credential and not self.credential.secret:
            logger.debug('%r %r %r', method, args, kwargs)
            raise exc.HTTP403_Forbidden('Account disabled')

        if not self.credential:
            # Login not successful
            # now we have to decide if we want ot enable HTTP-Login via a
            # `HTTP401_Unauthorized` response or redirect and use
            # Browser-Based Login

            if self._interactive_client():
                logger.debug('302 headers: %r', self.request.headers)
                # we assume the request came via a browser - redirect to the "nice" login page
                # let login.py handle it from there
                absolute_url = self.abs_url(
                    '/_ah/login_required?continue=%s' % urllib.quote(self.request.url))
                logger.info('enforcing interactive login as %s', absolute_url)
                logger.info('session %r', self.session)
                raise exc.HTTP302_Found(location=absolute_url)
            else:
                # We assume the access came via cURL et al, request Auth via 401 Status code.
                logger.info(
                    'requesting HTTP-Auth %s %s', self.request.remote_addr,
                    self.request.headers.get('Authorization'))
                raise exc.HTTP401_Unauthorized(headers={'WWW-Authenticate': 'Basic realm="API Login"'})
