#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/handlers/auth.py - Authentication MixIns for gaetk2.

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2010-2017 HUDORA. MIT licensed.
"""
import datetime
import logging
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

from jose import jwt

from ..exc import HTTP302_Found
from ..exc import HTTP400_BadRequest
from ..exc import HTTP401_Unauthorized
from ..tools.config import config
from ..tools.ids import guid128


class AuthMixin(object):
    """Class which adds authentivation."""

    def load_credential(self):
        """Find out if the User is authenticated in any sane way and if so load the credential."""
        # Automatically called by `dispatch`.
        # This funcion is somewhat involved. We accept
        # 1) Authentication via HTTP-Auth
        # 2) Authentication via JWT
        # 3) Authentication via Session
        # 4) Login via OAuth with speciffic domains registered at Google Apps

        # TODO: X-Appengine-Cron: true
        # x-appengine-user-is-admin
        # x-appengine-auth-domain
        # x-google-real-ip
        # X-Appengine-Inbound-Appid
        # X-AppEngine-QueueName
        # https://cloud.google.com/appengine/docs/standard/python/taskqueue/push/creating-handlers

        self.credential = None
        uid, secret = None, None
        # 1. Check for valid HTTP-Basic Auth Login
        if self.request.headers.get('Authorization', '').lower().startswith('basic '):
            auth_type, encoded = self.request.headers.get('Authorization').split(None, 1)
            decoded = encoded.decode('base64')
            # If the Client send us invalid credentials, let him know , else parse into
            # username and password
            if ':' not in decoded:
                raise HTTP400_BadRequest("invalid credentials %r" % decoded)
            uid, secret = decoded.strip().split(':', 1)

            self.credential = self.get_credential(uid or ' *invalid* ')
            if self.credential and self.credential.secret == secret.strip():
                # Successful login
                return self._login_user('HTTP')
            else:
                logging.error(
                    "failed HTTP-Login from %s/%s %s", uid, self.request.remote_addr,
                    self.request.headers.get('Authorization'))
                raise HTTP401_Unauthorized(
                    "Invalid HTTP-Auth",
                    headers={'WWW-Authenticate': 'Basic realm="API Login"'})

        # 2. Check for valid Authentication via JWT
        if self.request.headers.get('Authorization', '').lower().startswith('bearer '):
            auth_type, token = self.request.headers.get('Authorization').split(None, 1)
            unverified_header = jwt.get_unverified_header(token)
            # TODO: get public key
            userdata = jwt.decode(
                token,
                config.JWT_SECRET_KEY,
                algorithms=unverified_header["alg"],
                # audience=API_AUDIENCE,
                # issuer="https://"+AUTH0_DOMAIN+"/"
            )
            logging.warn('jwt: %s', userdata)

        # 3. Check for App Engine / Google Apps based Login
        user = users.get_current_user()
        if user:
            self.credential = self.get_credential(user.email())
            if self.credential:
                # We do not check the password because get_current_user() is trusted
                return self._login_user('Goole User OpenID Connect')

        # 4. Check for session based login
        if self.session.get('uid'):
            self.credential = self.get_credential(self.session['uid'])
            if self.credential:
                # We do not check the password because session storage is trusted
                return self._login_user('session')
            else:
                logging.warn(
                    "No Credential for Session: %s. Progressing unauthenticated",
                    self.session.get('uid'))
                self._clear_session()

    def authchecker(self, method, *args, **kwargs):
        """Function to allow implementing authentication for all subclasses.

        To be overwritten. Is called by BasicHandler before the HTTP-Method
        is called. Must exit with a HTTP-Exception if the USer is unauthorized.
        """
        # Example: ensure that users with empty password are never logged in
        # not really deeded, because `login_user()` ensures this.
        sup = super(AuthMixin, self)
        if hasattr(sup, 'authchecker'):
            sup.authchecker(method, *args, **kwargs)

        if self.credential and not self.credential.secret:
            logging.debug('%r %r %r', method, args, kwargs)
            raise HTTP401_Unauthorized("Account disabled")

    def login_required(self):
        """Forces login."""
        if not self.credential:
            # Login not successful
            # now we have to decide if we want ot enable HTTP-Login via a
            # `HTTP401_Unauthorized` response og redirect and use
            # Browser-Based Login

            if self._interactive_client():
                logging.debug("302 headers: %r", self.request.headers)
                # we assume the request came via a browser - redirect to the "nice" login page
                # let login.py handle it from there
                absolute_url = self.abs_url(
                    "/_ah/login_required?continue=%s" % urllib.quote(self.request.url))
                logging.info("enforcing interactive login as %s", absolute_url)
                logging.info("session %r", self.session)
                raise HTTP302_Found(location=absolute_url)
            else:
                # We assume the access came via cURL et al, request Auth via 401 Status code.
                logging.info("requesting HTTP-Auth %s %s", self.request.remote_addr,
                             self.request.headers.get('Authorization'))
                raise HTTP401_Unauthorized(headers={'WWW-Authenticate': 'Basic realm="API Login"'})

    def _login_user(self, via, jwt=None):
        """Ensure the system knows that a user has been logged in."""
        # user did not exist before but we have a validated jwt
        if not self.credential and jwt:
            # create credential from JWT
            self._create_credential_jwt(jwt)

        # ensure that users with empty password are never logged in
        if self.credential and not self.credential.secret:
            raise HTTP401_Unauthorized("Account disabled")

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
        logging.debug(
            "%s logged in via %s since %s sid:%s",
            self.credential.uid, self.session['login_via'], self.session['login_time'], self.session.sid)

    def _create_credential_jwt(self, jwt):
        logging.debug('JWT: %s', jwt)
        if jwt.get('email_verified'):
            uid = jwt['email']
        else:
            uid = jwt['sub'] + '#google.' + jwt['hd']
        self.credential = NdbCredential.create(
            id=uid,
            tenant=jwt.get('hd', jwt['email'].split('@')[-1]),
            uid=uid,
            admin=True,
            text='created via OAuth2',
            email=jwt['email'])
        self.credential.put()

    def _interactive_client(self):
        if (self.request.is_xhr or
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
        return NdbCredential.get_by_id(username)


class NdbCredential(ndb.Expando):
    """Encodes a user and his permissions."""

    _default_indexed = True
    uid = ndb.StringProperty(required=True)  # == key.id()
    user = ndb.UserProperty(required=False)  # Google (?) User
    tenant = ndb.StringProperty(required=False, default='_unknown', indexed=False)  # hudora.de
    email = ndb.StringProperty(required=False)
    secret = ndb.StringProperty(required=True, indexed=False)  # "Password" - NOT user-settable
    admin = ndb.BooleanProperty(default=False, indexed=False)
    text = ndb.StringProperty(required=False, indexed=False)
    permissions = ndb.StringProperty(repeated=True, indexed=False)
    created_at = ndb.DateTimeProperty(auto_now_add=True)
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_by = ndb.UserProperty(required=False, indexed=False, auto_current_user_add=True)
    updated_by = ndb.UserProperty(required=False, indexed=False, auto_current_user=True)

    @classmethod
    def _get_kind(cls):
        return 'Credential'

    @classmethod
    def create(cls, uid=None, tenant='_unknown', user=None, admin=False, **kwargs):
        """Creates a credential Object generating a random secret and a random uid if needed."""
        # secret hopfully contains about 40 bits of entropy - more than most passwords
        secret = guid128()[1:16]
        if not uid:
            uid = "u%s" % (cls.allocate_ids(1)[0])
        kwargs['permissions'] = ['generic_permission']
        ret = cls.get_or_insert(uid, uid=uid, secret=secret, tenant=tenant,
                                user=user, admin=admin, **kwargs)
        return ret

    def __str__(self):
        return str(self.uid)

    def __repr__(self):
        return "<gaetk.NdbCredential %s>" % self.uid
