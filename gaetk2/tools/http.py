#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/tools/http.py - simple HTTP API wraping `requests`.

based on huTools.http (c) 2010-2014, 2016-2017.

Created by Maximillian Dornseif on 2017-06-26.
Copyright (c) 2010-2014, 2016-2017 HUDORA. MIT licnsed.
"""

import logging

import requests

TIMEOUT = 30.0


def fetch_raw(url, content='', method='GET'):
    """Returns the raw `requests/response`."""
    response = requests.request(method, url, data=content, timeout=TIMEOUT)
    if response.status_code > 400:
        logging.debug('requested %r, data=%r', url, content)
        logging.warn('reply %s: %r', response.status_code, response.text)
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
