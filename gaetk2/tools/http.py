#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2/tools/http.py - simple HTTP API wraping `requests`.

based on huTools.http (c) 2010-2014, 2016-2017.

Created by Maximillian Dornseif on 2017-06-26.
Copyright (c) 2010-2014, 2016-2017 HUDORA. MIT licnsed.
"""
from __future__ import unicode_literals

import logging

import requests


logger = logging.getLogger(__name__)
TIMEOUT = 30.0


def fetch_raw(url, content='', method='GET'):
    """Returns the raw `requests/response`."""
    response = requests.request(method, url, data=content, timeout=TIMEOUT)
    if response.status_code > 400:
        logger.debug('requested %r, data=%r', url, content)
        logger.warn('reply %s: %r', response.status_code, response.text)
    response.raise_for_status()
    return response


def fetch(url, content='', method='GET'):
    """Request data unprocessed."""
    return fetch_raw(url, content, method).text


def fetch_json(url, content='', method='GET'):
    """Request JSON data."""
    return fetch_raw(url, content, method).json()

# def fetch_json2xx(url, content='', method='GET', credentials=None,
# headers=None, multipart=False, ua='', timeout=50, caching=None):


# quoting based on
# http://svn.python.org/view/python/branches/release27-maint/Lib/urllib.py?view=markup&pathrev=82940
# by Matt Giuca
always_safe = (b'ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
               b'abcdefghijklmnopqrstuvwxyz' +
               b'0123456789_.-')
assert isinstance(always_safe, str)
_safe_map = {}
for i, c in zip(xrange(256), [chr(x) for x in xrange(256)]):
    _safe_map[c] = c if (i < 128 and c in always_safe) else (b'%%%02X' % i)
_safe_quoters = {}


def quote(s, safe=b'/', encoding=None, errors=None):
    """quote('abc def') -> 'abc%20def'

    Each part of a URL, e.g. the path info, the query, etc., has a
    different set of reserved characters that must be quoted.

    RFC 2396 Uniform Resource Identifiers (URI): Generic Syntax lists
    the following reserved characters.

    reserved    = ";" | "/" | "?" | ":" | "@" | "&" | "=" | "+" |
                  "$" | ","

    Each of these characters is reserved in some component of a URL,
    but not necessarily in all of them.

    By default, the quote function is intended for quoting the path
    section of a URL.  Thus, it will not encode '/'.  This character
    is reserved, but in typical usage the quote function is being
    called on a path where the existing slash characters are used as
    reserved characters.

    string and safe may be either str or unicode objects.

    The optional encoding and errors parameters specify how to deal with the
    non-ASCII characters, as accepted by the unicode.encode method.
    By default, encoding='utf-8' (characters are encoded with UTF-8), and
    errors='strict' (unsupported characters raise a UnicodeEncodeError).
    """
    # fastpath
    if not s:
        return s

    if encoding is not None or isinstance(s, unicode):
        if encoding is None:
            encoding = 'utf-8'
        if errors is None:
            errors = 'strict'
        s = s.encode(encoding, errors)
    if isinstance(safe, unicode):
        # Normalize 'safe' by converting to str and removing non-ASCII chars
        safe = safe.encode('ascii', 'ignore')

    cachekey = (safe, always_safe)
    try:
        (quoter, safe) = _safe_quoters[cachekey]
    except KeyError:
        safe_map = _safe_map.copy()
        safe_map.update([(c, c) for c in safe])
        quoter = safe_map.__getitem__
        safe = always_safe + safe
        _safe_quoters[cachekey] = (quoter, safe)
    if not s.rstrip(safe):
        return s
    return ''.join(map(quoter, s))


def quote_plus(s, safe=b'', encoding=None, errors=None):
    """Quote the query fragment of a URL; replacing ' ' with '+'"""
    if b' ' in s:
        s = quote(s, safe + b' ', encoding, errors)
        return s.replace(b' ', b'+')
    return quote(s, safe, encoding, errors)


def urlencode(query):
    """Encode a sequence of two-element tuples or dictionary into a URL query string.

    If the query arg is a sequence of two-element tuples, the order of the
    parameters in the output will match the order of parameters in the
    input.
    """

    if hasattr(query, 'items'):
        # mapping objects
        query = query.items()
    l = []
    for k, v in query:
        k = quote_plus(k)
        if isinstance(v, basestring):
            v = quote_plus(v)
            l.append(k + b'=' + v)
        else:
            v = quote_plus(unicode(v))
            l.append(k + b'=' + v)
    return b'&'.join(l)
