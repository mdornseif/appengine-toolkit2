#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
handlers/__init__.py - default Request Handlers for gaetk2.

Created by Maximillian Dornseif on 2017-06-24.
Copyright (c) 2017, 2019 HUDORA. All rights reserved.
"""

from .authentication import AuthenticationReaderMixin
from .authentication import AuthenticationRequiredMixin
from .base import BasicHandler
from .mixins.messages import MessagesMixin
from .mixins.json import JsonMixin


class DefaultHandler(BasicHandler, MessagesMixin, AuthenticationReaderMixin):
    """Handle Requests and load self.credential if Authentication is provided."""

    pass


class JsonHandler(DefaultHandler, JsonMixin):
    """Send JSON data to client and load self.credential if Authentication is provided."""

    pass


class AuthenticatedHandler(DefaultHandler, AuthenticationRequiredMixin):
    pass


class AuthenticatedJsonHandler(JsonHandler, AuthenticationRequiredMixin):
    pass
