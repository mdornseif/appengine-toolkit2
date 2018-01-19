#!/usr/bin/env python
# encoding: utf-8
"""gaetk2.tools.auth0.py  Tools for working with auth0

Created by Maximillian Dornseif on 2017-12-05.
Copyright 2017 HUDROA. MIT Licensed.
"""

import logging

from auth0.v3.authentication import GetToken
from auth0.v3.exceptions import Auth0Error
from auth0.v3.management import Auth0
from gaetk2.tools.config import config as gaetk2config
from google.appengine.api import memcache


logger = logging.getLogger(__name__)


def get_auth0_access_token():
    """Get a Token for the Management-API."""
    ret = memcache.get('get_auth0_access_token()')
    if not ret:
        assert gaetk2config.AUTH0_DOMAIN != '*unset*'
        assert gaetk2config.AUTH0_CLIENT_ID != '*unset*'
        get_token = GetToken(gaetk2config.AUTH0_DOMAIN)
        token = get_token.client_credentials(
            gaetk2config.AUTH0_CLIENT_ID,
            gaetk2config.AUTH0_CLIENT_SECRET,
            'https://{}/api/v2/'.format(gaetk2config.AUTH0_DOMAIN))
        ret = token['access_token']
        memcache.set('get_auth0_access_token()', ret, token['expires_in'] / 2)
    return ret


def create_from_credential(credential):
    """Create an entry in the Auth0.DefaultDatabase for a credential."""
    if credential.external_uid:
        return
    if not credential.secret:
        return
    assert credential.email
    if not getattr(credential, 'name', None):
        credential.name = credential.text
    if not getattr(credential, 'name', None):
        credential.name = credential.org_designator

    auth0api = Auth0(gaetk2config.AUTH0_DOMAIN, get_auth0_access_token())
    payload = {
        "connection": 'DefaultDatabase',
        "email": credential.email,
        "password": credential.secret,
        "user_id": credential.uid,
        "user_metadata": {
            "name": credential.name,
            "nickname": "User fuer {}".format(credential.org_designator)
        },
        "email_verified": True,
        "verify_email": False,
        "app_metadata": {
            'org_designator': credential.org_designator,
            'permissions': credential.permissions,
        }
    }
    newuser = None
    try:
        newuser = auth0api.users.create(payload)
    except Auth0Error as ex:
        if ex.status_code == 400 and ex.message == u'The user already exists.':
            logger.info("The user already exists: %s %r %s", credential.uid, ex, payload)
            try:
                newuser = auth0api.users.get('auth0|{}'.format(credential.uid))
            except:
                logger.warn('email collision? %s', credential.uid)
                # propbably we have an E-Mail Address collision. This means
                # several Credentials with the same E-Mail Adresses.
                reply = auth0api.users.list(
                    connection='DefaultDatabase',
                    q='email:"{}"'.format(credential.email),
                    search_engine='v2')
                if reply['length'] > 0:
                    logger.info('reply=%s', reply)
                    other_uid = reply['users'][0]['user_id']
                    newuser = auth0api.users.get(other_uid)
                    # doppelbelegung bei Auth0 notieren
                    if newuser.get('app_metadata'):
                        logger.debug('app_metadata=%r', newuser['app_metadata'])
                        altd = newuser['app_metadata'].get('org_designator_alt', [])
                        altd = list(set(altd + [credential.org_designator]))
                        altu = newuser['app_metadata'].get('uid_alt', [])
                        altu = list(set(altu + [credential.uid]))
                        logger.warn('updating duplicate Auth0 %s %s %s %s', altd, altu, other_uid, newuser)
                        auth0api.users.update(
                            other_uid,
                            {'app_metadata': {'org_designator_alt': altd,
                                              'uid_alt': altu}})
        else:
            logger.error('%r newuser = %s %s', 'auth0|{}'.format(credential.uid), newuser, ex)
            raise
    except:
        logger.warn("payload = %s", payload)
        raise
    if newuser is None or (newuser.get('error')):
        logger.warn("reply=%s payload = %s", newuser, payload)
        raise RuntimeError("Auth0-Fehler: %s" % newuser)

    logger.info("new auth0 user %s", newuser)
    credential.meta['auth0_user_id'] = credential.external_uid = newuser['user_id']
    credential.put()
    return
