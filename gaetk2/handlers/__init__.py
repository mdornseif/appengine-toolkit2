#!/usr/bin/env python
# encoding: utf-8
"""
handlers/__init__.py - default Request Handlers for gaetk2.

Created by Maximillian Dornseif on 2017-06-24.
Copyright (c) 2017 HUDORA. All rights reserved.
"""

from .authentication import AuthenticationReaderMixin
from .authentication import AuthenticationRequiredMixin
from .base import BasicHandler
from .base import JsonBasicHandler
from .mixins.messages import MessagesMixin


class DefaultHandler(BasicHandler, MessagesMixin, AuthenticationReaderMixin):
    """Handle Requests and load self.credential if Authentication is provided."""

    pass


class JsonHandler(JsonBasicHandler, AuthenticationReaderMixin):
    """Send JSON data to client and load self.credential if Authentication is provided."""
    # use JsonMixin
    pass


class AuthenticatedHandler(DefaultHandler, AuthenticationRequiredMixin):
    pass


class AuthenticatedJsonHandler(JsonHandler, AuthenticationRequiredMixin):
    pass
