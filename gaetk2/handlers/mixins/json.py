#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2/handlers/mixins/json.py - misc functionality to be added to gaetk handlers.

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2018 Maximillian Dornseif. MIT licensed.
"""
from __future__ import unicode_literals

import urllib

from gaetk2.tools import hujson2
from gaetk2.tools.sentry import sentry_client


class JsonMixin(object):
    """Handler which is specialized for returning JSON.

    Excepts the method to return

    * dict(), e.g. `{'foo': bar}`

    Dict is converted to JSON. `status` is used as HTTP status code. `cachingtime`
    is used to generate a `Cache-Control` header. If `cachingtime is None`, no header
    is generated. `cachingtime` defaults to 60 seconds.

    If the Request contained a body it be made available in parsed form as
    `self.request.json`.
    """

    # Our default caching is 60s
    default_cachingtime = 60
    # supress warnings about response-type
    _gaetk2_allow_strange_responses = True

    def method_preperation_hook(self, method, *args, **kwargs):
        """Try to read request body as JSON.

        The parsed data will be available as `self.request.json`."""
        rawdata = self.request.body
        data = None
        if not rawdata:
            data = None
        elif self.request.headers['Content-Type'].startswith('application/json'):
            data = hujson2.loads(rawdata)
        else:
            # some strange is being sent
            if self.request.headers.get('Content-Type').startswith('application/x-www-form-urlencoded'):
                data = hujson2.loads(urllib.unquote_plus(self.request.body).strip('=\n'))
        self.request.json = data
        sentry_client.note('rpc', message='JSON API Call', data=dict(data=data))

    def serialize(self, content):
        """convert content to JSON."""
        return hujson2.dumps(content)

    def response_overwrite_overwrite(self, response, method, *args, **kwargs):
        """Function to transform response. Not to be overwritten."""
        # do serialisation bef ore generating Content-Type Header so Errors will display nicely
        content = self.serialize(response) + '\n'
        self.response.headers[str('Content-Type')] = str('application/json')
        self.response.write(content)
        # self.response.cache_control = 'public'
        self.response.cache_control.max_age = self.default_cachingtime
        return self.response
