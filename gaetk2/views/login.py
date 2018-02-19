#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.views.login - generic logout & authentication views.

based on EDIhub:login.py

Created by Maximillian Dornseif on 2010-09-24.
Copyright (c) 2010, 2014, 2015 HUDORA. MIT licensed.
"""
import hashlib
import logging
import os
from datetime import datetime, timedelta

from gaetk2.tools import hujson2
from google.appengine.api import users

from jose import jwt

from ..application import WSGIApplication
from ..exc import HTTP400_BadRequest, HTTP403_Forbidden, HTTP404_NotFound
from ..handlers import DefaultHandler, JsonHandler
from ..handlers.auth import gaetk_Credential
from ..config import config

logger = logging.getLogger(__name__)


class Debug(JsonHandler):
    """Handler for showing Authentication Data."""

    def get(self):
        """Build dict of Auth Data and return it as JSON."""
        env = {}
        attrs = ['AUTH_DOMAIN',
                 'USER_EMAIL', 'USER_ID', 'USER_IS_ADMIN',
                 'USER_NICKNAME', 'USER_ORGANIZATION',
                 'FEDERATED_IDENTITY', 'FEDERATED_PROVIDER']
        for name in attrs:
            env[name] = os.environ.get(name)

        return dict(
            env=env,
            google_user=users.get_current_user(),
            credential=self.credential,
            uid=self.session.get('uid'),
            # headers=self.request.headers,
        )


class GetJWTtxt(DefaultHandler):
    """Create our own hudora-specific JWT."""

    def get_jwt(self):
        iat = datetime.utcnow()
        nbf = iat + timedelta(seconds=0)
        exp = iat + timedelta(seconds=3600)
        jti = hashlib.md5(os.urandom(128)).hexdigest()

        jwt_payload = {
            'exp': exp, 'iat': iat, 'nbf': nbf, 'jti': jti,  # 'aud': 'hudora.de',
            'sub': self.credential.uid,
            "Email": self.credential.email
        }
        return jwt.encode(jwt_payload, config.JWT_SECRET_KEY, algorithm='HS256')

    def get(self):
        """Build JWT and return it as plaintext."""

        if not self.credential:
            self.return_text('// NAK - unauthenticated')

        self.return_text('// ACK - ' + self.get_jwt())


class LogoutHandler(DefaultHandler):
    """Handler for Logout functionality."""

    def get(self):
        """Logout user and terminate the current session."""
        logger.info("forcing logout")

        # log out Google and either redirect to 'continue' or display
        # the default logout confirmation page
        continue_url = self.request.get('continue', '')

        # delete coockies
        self.response.delete_cookie('SACSID')  # Appengine Secure User Service Login
        self.response.delete_cookie('ACSID')  # Appengine User Service Login
        self.response.delete_cookie('gaetkoauthmail')  # gaetk Login
        self.response.delete_cookie('gaetkuid')  # gaetk Login
        # domain = gaetk.tools.get_cookie_domain()
        # self.response.delete_cookie('gaetkuid', domain='.%s' % domain)  # gaetk Login

        self._clear_session()

        user = users.get_current_user()
        if user:
            logger.info("Google User %s", user)
            path = self.request.path
            logout_url = users.create_logout_url(path)
            logger.info("logging out via %s", logout_url)
            self.redirect(logout_url)
        else:
            if continue_url:
                self.redirect(continue_url)
            else:
                self.render({}, 'logout.html')


class CredentialsHandler(JsonHandler):
    """Credentials - show, generate or update."""

    def authenticationchecker(self, *args, **kwargs):
        """Only admin users are allowed to access credentials."""
        if not self.is_sysadmin():
            raise HTTP403_Forbidden

    def get(self):
        """Returns information about the credential referenced by parameter `uid`."""
        uid = self.request.get('uid')
        if not uid:
            raise HTTP404_NotFound

        credential = self.get_credential(uid)
        if credential is None:
            raise HTTP404_NotFound

        return dict(
            uid=credential.uid, admin=credential.admin, text=credential.text,
            email=credential.email,
            permissions=credential.permissions,
            created_at=credential.created_at, updated_at=credential.updated_at)

    def post(self):
        r"""Create or update a credential.

        Use it like this

            curl -u $uid:$secret -X POST -F admin=True \
                -F text='fuer das Einspeisen von SoftM Daten' -F email='edv@shpuadmora.de' \
                http://example.appspot.com/gaetk2/auth/credentials
            {
             "secret": "aJNKCDUZW5PIBT23LYX7XXVFENA",
             "uid": "u66666o26ec4b"
            }
        """
        # The data can be submitted either as a json encoded body or form encoded
        if self.request.headers.get('Content-Type', '').startswith('application/json'):
            data = hujson2.loads(self.request.body)
        else:
            data = self.request

        admin = str(data.get('admin', '')).lower() == 'true'
        text = data.get('text', '')
        uid = data.get('uid')
        email = data.get('email')
        permissions = data.get('permissions', '')
        if isinstance(permissions, basestring):
            permissions = permissions.split(',')

        if uid:
            credential = self.get_credential(uid)
        else:
            credential = None

        if credential:
            # if a credential already exists we only have to modify it
            credential.admin = admin
            credential.text = text
            credential.email = email
            credential.permissions = []
            for permission in permissions:
                if permission not in getattr(config, 'ALLOWED_PERMISSIONS', []):
                    raise HTTP400_BadRequest("invalid permission %r" % permission)
                credential.permissions.append(permission)
            credential.put()
        else:
            # if not, we generate a new one
            credential = gaetk_Credential.create(
                admin=admin, text=text, email=email)

        self.response.headers["Content-Type"] = "application/json"
        self.response.set_status(201)
        self.response.out.write(hujson2.dumps(dict(
            uid=credential.uid, secret=credential.secret,
            admin=credential.admin, text=credential.text,
            email=credential.email,
            permissions=credential.permissions,
            created_at=credential.created_at,
            updated_at=credential.updated_at)))


application = WSGIApplication([
    (r'^/gaetk2/auth/debug$', Debug),
    (r'^/gaetk2/auth/getjwt.txt$', GetJWTtxt),
    (r'^/gaetk2/auth/logout$', LogoutHandler),
])

#     (r'auth/credentials$', CredentialsHandler),
