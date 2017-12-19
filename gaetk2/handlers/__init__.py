#!/usr/bin/env python
# encoding: utf-8
"""
handlers/__init__.py - default Request Handlers for gaetk2.

Created by Maximillian Dornseif on 2017-06-24.
Copyright (c) 2017 HUDORA. All rights reserved.
"""

from .authentication import AuthenticationReaderMixin
from .base import BasicHandler
from .base import JsonBasicHandler


class DefaultHandler(BasicHandler, AuthenticationReaderMixin):
    """Handle Requests and load self.credential if Authentication is provided."""

    pass


class JsonHandler(JsonBasicHandler, AuthenticationReaderMixin):
    """Send JSON data to client and load self.credential if Authentication is provided."""

    pass
