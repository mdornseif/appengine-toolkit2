#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.handlers.authentication

AuthenticationReaderMixin - Authentication MixIns for gaetk2.

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2010-2017 HUDORA. MIT licensed.
"""
import datetime
import logging
import os
import urllib

from google.appengine.api import users

from jose import jwt

from .. import models

from ..exc import HTTP302_Found
from ..exc import HTTP400_BadRequest
from ..exc import HTTP401_Unauthorized
from ..tools.config import config


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
                return self._login_user('Google User OpenID Connect')

        # 4. Check for session based login
        logging.debug("session")
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

        # 5. Login for Google Special Calls from Cron & TaskQueue
        # TODO: X-Appengine-Cron: true
        # x-appengine-user-is-admin
        # x-appengine-auth-domain
        # x-google-real-ip
        # X-Appengine-Inbound-Appid
        # X-AppEngine-QueueName
        # https://cloud.google.com/appengine/docs/standard/python/taskqueue/push/creating-handlers
        if self.request.headers.get('X-AppEngine-QueueName'):
            self.credential = self.get_credential('X-AppEngine-Taskqueue-{}@auth.gaetk2.23.nu'.format(
                self.request.headers.get('X-AppEngine-QueueName')))
            return self._login_user('AppEngine')

        logging.info('user unauthenticated')

    def _login_user(self, via, jwtinfo=None):
        """Ensure the system knows that a user has been logged in."""
        # user did not exist before but we have a validated jwt
        if not self.credential and jwtinfo:
            # create credential from JWT
            self.credential = allow_credential_from_jwt(jwtinfo)
        if not self.credential:
            # here we could redirect the user to a page
            # explaining that we couldn't match the data
            # given by him to our local database.
            raise HTTP401_Unauthorized("Couldn't assign {} to a local user".format(jwtinfo))

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
            self.credential.uid,
            self.session.get('login_via'),
            self.session.get('login_time'),
            getattr(self.session, 'sid', '?'))
        self.response.headers.add_header("X-uid", str(self.credential.uid))

    def _interactive_client(self):
        """Check if we cvan redirect the client for login."""
        if (self.request.is_xhr or self.request.get('no401redirect') == '1' or
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
        logging.debug("get_credential()")
        cred = models.gaetk_Credential.get_by_id(username)
        if not cred:
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
                if getattr(cred1, 'kundennr', None):
                    cred.meta['designator'] = cred1.kundennr
                    cred.org_designator = cred.meta['designator']
                if getattr(cred1, 'source', None):
                    cred.meta['designator'] = cred1.source.id()
                    cred.org_designator = cred.meta['designator']
                cred.put()
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
    logging.debug('JWT: %s', jwt)
    if jwt.get('email_verified') and jwt['email'].endswith('@hudora.de'):
        return models.gaetk_Credential.create(
            id=jwt['email'],
            uid=jwt['email'],
            text='created via OAuth2/JWT',
            email=jwt['email'])
    else:
        return None


class AuthenticationRequiredMixin(AuthenticationReaderMixin):
    """Class which adds authentication."""

    def authentication_hook(self, method, *args, **kwargs):
        """Function to enforce that users `are authenticated."""

        if self.credential and not self.credential.secret:
            logging.debug('%r %r %r', method, args, kwargs)
            raise HTTP401_Unauthorized("Account disabled")

        if not self.credential:
            # Login not successful
            # now we have to decide if we want ot enable HTTP-Login via a
            # `HTTP401_Unauthorized` response or redirect and use
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