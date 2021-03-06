#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2.config.runtime

This module provides a generic configuration object.
The two functions get_config and set_config are used
to get or set the configuration object.

>>> from gaetk2 import config.runtime
>>> config.runtime.get_config('MY-KEY-NAME')
None
>>> config.runtime.get_config('MY-KEY-NAME', default=55555)
55555
>>> config.runtime.set_config('MY-KEY-NAME', u'5711')
>>> config.runtime.get_config('MY-KEY-NAME')
u'5711'

Created by Christian Klein on 2011-11-24.
Copyright (c) 2011, 2012, 2016, 2017, 2018 HUDORA. All rights reserved.
"""
from __future__ import unicode_literals

import json

from google.appengine.ext import ndb


class gaetk_Configuration(ndb.Model):
    """Generic configuration object"""
    _use_cache = False
    value = ndb.TextProperty(default='', indexed=False)
    updated_at = ndb.DateTimeProperty(auto_now_add=True, auto_now=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)


def get_config(key, default=None):
    """Get configuration value for key"""

    obj = gaetk_Configuration.get_by_id(key)
    if obj:
        return json.loads(obj.value)
    return set_config(key, default)


def set_config(key, value):
    """Set configuration value for key"""

    obj = gaetk_Configuration(id=key, value=json.dumps(value))
    obj.put()
    return value


# class ConfigHandler(gaetk.handler.JsonResponseHandler):
#     """Handler für Configurationsobjekte"""

#     def authchecker(self, *args, **kwargs):
#         """Nur Admin-User"""

#         self.login_required()
#         if not self.is_admin():
#             raise gaetk.handler.HTTP403_Forbidden

#     def get(self, key):
#         """Lese Konfigurationsvariable"""
#         obj = gaetk.handler.get_object_or_404(gaetk_Configuration, key)
#         self.response.headers['Last-Modified'] = obj.updated_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
#         return obj.value

#     def post(self, key):
#         """Schreibe Konfigurationsvariable"""

#         header = self.request.headers.get('Content-Type')
#         if header.split(';', 1)[0] == 'application/json':
#             data = self.request.body
#         else:
#             data = self.request.get('value', '')

#         try:
#             value = json.loads(data)
#         except (ValueError, TypeError) as exception:
#             logging.exception(u'Err: %r, %s', data, exception)
#             raise gaetk.handler.HTTP400_BadRequest
#         return set_config(key, value)


# application = gaetk.handler.WSGIApplication([
#     (r'.*/([\w_-]+)/', ConfigHandler),
# ])
