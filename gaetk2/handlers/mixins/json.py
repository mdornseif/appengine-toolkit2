#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/handlers/mixins.py - misc functionality to be added to gaetk handlers.

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2018 Maximillian Dornseif. MIT licensed.
"""
import webapp2

from gaetk2.tools import hujson2


class JsonMixin(object):
    """Handler which is specialized for returning JSON.

    Excepts the method to return

    * dict(), e.g. `{'foo': bar}`

    Dict is converted to JSON. `status` is used as HTTP status code. `cachingtime`
    is used to generate a `Cache-Control` header. If `cachingtime is None`, no header
    is generated. `cachingtime` defaults to 60 seconds.
    """

    # Our default caching is 60s
    default_cachingtime = 60
    # supress warnings about response-type
    _gaetk2_allow_strange_responses = True

    def serialize(self, content):
        """convert content to JSON."""
        return hujson2.dumps(content)

    def response_overwrite_overwrite(self, response, method, *args, **kwargs):
        """Function to transform response. To be overwritten."""
        # do serialisation bef ore generating Content-Type Header so Errors will display nicely
        content = self.serialize(response) + '\n'
        self.response.headers[str('Content-Type')] = str('application/json')
        self.response.write(content)
        # self.response.cache_control = 'public'
        self.response.cache_control.max_age = self.default_cachingtime
        return self.response
