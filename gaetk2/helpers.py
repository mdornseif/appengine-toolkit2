#!/usr/bin/env python
# encoding: utf-8
"""
helpers.py - smal view-helper-functions

Created by Maximillian Dornseif on 2016-12-15.
Copyright (c) 2016, 2018 Cyberlogi. MIT Licensed.
"""
import os
import urlparse

from google.appengine.api import app_identity

from gaetk2.config import get_productiondomain

from .exc import HTTP404_NotFound


def check404(obj, message='Object not found.'):
    """Raises 404 if ``bool(obj)`` is ``False``.

    The major usecase is to replace::

        def post(self, kundennr):
            kunde = m_api.get_kunde(kundennr)
            if not kunde:
                raise HTTP404_NotFound
            do_some_work()

    with::

        def post(self, kundennr):
            kunde = check404(m_api.get_kunde(kundennr))
            do_some_work()

    This has the potential to make view-Functions much more readable.
    """
    if not obj:
        raise HTTP404_NotFound(message)
    return obj


def abs_url(url):
    """Convert a relative URL to an absolute URL.

    You really should prefer :meth:`gaetk2.handler.base.BasicHandler.abs_url()`
    because it has better information about the request and host.
    """
    # bischen hacky, weil wir am Stack vorbei arbeiten
    if 'HTTP_X_APPENGINE_QUEUENAME' in os.environ:
        # when called in a taskqueue, we don't want to provide the .appspot.com name
        if os.environ.get('HTTP_HOST') == app_identity.get_default_version_hostname():
            return urlparse.urljoin('https://{}/'.format(get_productiondomain()), url)
    return urlparse.urljoin('https://' + os.environ['HTTP_HOST'], url)
