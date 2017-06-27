#!/usr/bin/env python
# encoding: utf-8
"""ids.py  Tools for generating unique IDs & Passwords.

Based on huTools/luids.py - Tools for generating various local unique IDs.

Use guid128() if you are looking for a compact, URL-save representation of uuid output.
See [shortuuid](https://github.com/stochastic-technologies/shortuuid) for an alternative aproach.

Created by Maximillian Dornseif on 2006-11-08. BSD Licensed.
Copyright 2006 2011-2015, 2017. MIT licensed.
"""

import base64
import hashlib
import os
import uuid


def guid128(salt=None):
    """Generates an 26 character ID which should be globally unique.

    >>> guid128()
    'MTB2ONDSL3YWJN3CA6XIG7O4HM'
    """
    if not salt:
        salt = os.urandom(64)
    data = "%s%s%s" % (salt, uuid.uuid1(), salt)
    return str(base64.b32encode(hashlib.md5(data).digest()).rstrip('='))
