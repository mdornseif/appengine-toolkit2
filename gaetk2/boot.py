#!/usr/bin/env python
# encoding: utf-8
"""
boot.py - Inital setup. Best to be imported first in `appengine_config.py`

This does some AppEngine specific configuration and monkey-patching.

Created by Maximillian Dornseif on 2017-06-24.
Copyright (c) 2017 Maximillian Dornseif. MIT Licensed.
"""

# pylint: skip-file
# flake8: noqa

import logging
import os.path
import warnings

# something redirects warning to logging.error() on App Engine (stderr?).
# Fix it.
logging.captureWarnings(True)

warnings.simplefilter('always')  # reset filter to see DeprecationWarning
warnings.filterwarnings('ignore', module='cgitb')
warnings.filterwarnings('ignore', module='ssl_')  # SNIMissingWarning, InsecurePlatformWarning
warnings.filterwarnings('ignore', message='decode_param_names is deprecated')
warnings.filterwarnings('ignore', message='cgi.parse_qs is deprecated, use urlparse.parse_qs instead')
warnings.filterwarnings('ignore', message='decode_param_names is deprecated and')

# Include libraries
from google.appengine.ext import vendor
from site import addsitedir
addsitedir('lib')
vendor.add('lib/site-packages')

import google.appengine.api.urlfetch
import requests
import requests_toolbelt.adapters.appengine
import urllib3

# fixing botocore
os.path.expanduser = lambda x: x

# make python-requests play nice with AppEngine and
# suppress SSL warnings we can not do anything about
requests_toolbelt.adapters.appengine.monkeypatch(validate_certificate=False)
urllib3.disable_warnings()

# incerase global HTTP-Timeout from 5 to 50 seconds
google.appengine.api.urlfetch.set_default_fetch_deadline(50)

# import httplib
# httplib.HTTPConnection.debuglevel = 1

# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True
