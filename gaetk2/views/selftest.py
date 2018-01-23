#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/views/selftest - views for simple testing and Demonstration.

based on EDIhub:login.py

Created by Maximillian Dornseif on 2017-06-26.
Copyright (c) 2017 HUDORA. MIT licnsed.
"""
import datetime

from ..application import WSGIApplication
from ..exc import HTTP400_BadRequest
from ..handlers import DefaultHandler
from ..handlers import JsonHandler


class T1(DefaultHandler):
    """Test simple text responses."""

    def get(self):
        """`return_text()` generates simple `text/plain` responses."""
        self.return_text("T1")

    def post(self):
        """Other Methods than `GET` are possible."""
        self.return_text("T1")


class T2(DefaultHandler):
    """Test Output Stream."""

    def get(self):
        """The output stream can be accssed via `self.response.out`."""
        self.response.out.write("T2")


class T3(JsonHandler):
    """Test simple JSON."""

    def get(self):
        """Simple Data is encoded as JSON."""
        return u'T3'


class T4(JsonHandler):
    """Test JSON encoding."""

    def get(self):
        """Arbitrary Datastructures (within Limits) can be sent."""
        return [u'💾', 1, {'a': 2.2}, datetime.datetime.now()]


class T5(DefaultHandler):
    """Test raise."""

    def get(self):
        """HTTP-Exceptions result in certain status codes beeing sent."""
        raise HTTP400_BadRequest('irgendwas')


application = WSGIApplication([
    (r'^/gaetk2/test/t1$', T1),
    (r'^/gaetk2/test/t2$', T2),
    (r'^/gaetk2/test/t3$', T3),
    (r'^/gaetk2/test/t4$', T4),
    (r'^/gaetk2/test/t5$', T5),
])
