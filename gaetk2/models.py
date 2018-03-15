#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.models - NDB Models for gaetk2.

Created by Maximillian Dornseif on 2017-12-15.
Copyright (c) 2017, 2018 HUDORA. MIT licensed.
"""

from google.appengine.ext import ndb

from .tools.ids import guid128


class gaetk_Credential(ndb.Model):
    """Encodes a user and his permissions."""
    _default_indexed = True  # ensure additional properties get indexed
    uid = ndb.StringProperty(required=True)  # == key.id(), oder aus externem System
    email = ndb.StringProperty(required=False)
    secret = ndb.StringProperty(required=True, indexed=False)  # "Password" - NOT user-settable
    name = ndb.StringProperty(required=False, indexed=False, default='')
    text = ndb.StringProperty(required=False, indexed=False)
    permissions = ndb.StringProperty(repeated=True, indexed=False)

    sysadmin = ndb.BooleanProperty(default=False, indexed=True)
    staff = ndb.BooleanProperty(default=False, indexed=True)

    meta = ndb.JsonProperty(indexed=False, default={})
    org_designator = ndb.StringProperty(required=False)  # ref to the "parent", e.g. Customer Number
    external_uid = ndb.StringProperty(required=False)

    last_seen = ndb.DateTimeProperty(required=False, indexed=False)

    deleted = ndb.BooleanProperty(default=False)
    created_at = ndb.DateTimeProperty(auto_now_add=True)
    updated_at = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def create(cls, uid=None, org_designator=None, **kwargs):
        """Creates a credential Object generating a random secret and a random uid if needed."""
        # secret hopfully contains about 40 bits of entropy - more than most passwords
        if not uid:
            uid = "u%s" % (cls.allocate_ids(1)[0])
        if 'secret' not in kwargs:
            kwargs['secret'] = guid128()[1:17]
        if 'permissions' not in kwargs:
            kwargs['permissions'] = []
        ret = cls.get_or_insert(
            uid, uid=uid, org_designator=org_designator, **kwargs)
        return ret

    def __str__(self):
        return str(self.uid)

    @classmethod
    def from_gaetk1(cls, cred1):
        """Generate `gaetk_Credential` from legacy `NdbCredential` and store it."""
        cred2 = cls.create(
            uid=cred1.uid, email=cred1.email, secret=cred1.secret,
            permissions=cred1.permissions, text=cred1.text,
            sysadmin=cred1.admin)
        cred2.put()
        cred2.populate(created_at=cred1.created_at, updated_at=cred1.updated_at)
        if getattr(cred1, 'org_designator', None):
            cred2.meta['org_designator'] = cred1.kundennr
            cred2.org_designator = cred2.meta['org_designator']
        if getattr(cred1, 'name', None) and not cred2.name:
            cred2.name = cred1.name
        cred2.put()
        return cred2
