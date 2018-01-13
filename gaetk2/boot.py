#!/usr/bin/env python
# encoding: utf-8
"""
boot.py - Inital setup. Best to be imported first in `appengine_config.py`

This does some AppEngine specific configuration and monkey-patching.

The most robust approach in `appengine_config.py` would be:

    # load gaetk2 bootstrap code without using `sys.path`
    import imp
    (fp, filename, data) = imp.find_module(
        'boot',
        ['./lib/appengine-toolkit2/gaetk2/'])
    imp.load_module('gaetk_boot', fp, filename, data)

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
warnings.filterwarnings('ignore', module='pkgutil')
warnings.filterwarnings('ignore', message='decode_param_names is deprecated')
warnings.filterwarnings('ignore', message='cgi.parse_qs is deprecated, use urlparse.parse_qs instead')
warnings.filterwarnings('ignore', message='urllib3 is using URLFetch on Google App Engine sandbox')
warnings.filterwarnings('ignore', message='Required is going away in WTForms 3.0, use DataRequired')

# Include libraries
# `google.appengine.ext.vendor.add` is just `site.addsitedir()` with path shuffling

from google.appengine.ext import vendor
vendor.add('./lib')  # processes `.pth` files
vendor.add('./lib/site-packages') # processes `.pth` files

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

# TODO: add sentry: https://docs.sentry.io/clients/python/integrations/logging/
