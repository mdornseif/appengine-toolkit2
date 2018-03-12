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

Be carefull to do only minimal initialisation here. Since this is imported
in `appengine_config.py` nothing you import should use `lib_config` which
uses `appengine_config.py`.

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
warnings.filterwarnings('ignore', message='The TextField alias for StringField has been deprecated')

# Include libraries
# `google.appengine.ext.vendor.add` is just `site.addsitedir()` with path shuffling

from google.appengine.ext import vendor
vendor.add('./lib')  # processes `.pth` files
vendor.add('./lib/site-packages') # processes `.pth` files

# fixing botocore
os.path.expanduser = lambda x: x

import google.appengine.api.urlfetch    # isort:skip
import requests    # isort:skip
import requests_toolbelt.adapters.appengine    # isort:skip
import urllib3   # isort:skip

requests_toolbelt.adapters.appengine.monkeypatch(validate_certificate=False)
# this breaks code like
#    session = requests.session()
#    session.mount('https://', appengine.AppEngineAdapter())
#    return dropbox.Dropbox(access_token session=session)
# But without that session mounting you would get ChunkedEncodingError.

# suppress SSL warnings we can not do anything about
urllib3.disable_warnings()

# incerase global HTTP-Timeout from 5 to 50 seconds
google.appengine.api.urlfetch.set_default_fetch_deadline(50)


# ensure we can see the funcname for convinience and the logger name for selective supression
# see https://docs.python.org/2/library/logging.html#logrecord-attributes
fr = logging.Formatter('%(funcName)s(): %(message)s [%(name)s]')
logging.getLogger().handlers[0].setFormatter(fr)

# make certain libraries log less
logging.getLogger('raven').setLevel(logging.WARNING)

# import httplib
# httplib.HTTPConnection.debuglevel = 1
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True
# import logging
# urllib3_logger = logging.getLogger('urllib3')
# urllib3_logger.setLevel(logging.CRITICAL)
# logging.getLogger('requests').setLevel(logging.CRITICAL)
# Could also use the dictionary directly:
# logging.Logger.manager.loggerDict['requests'].setLevel(logging.CRITICAL)

# TODO: add sentry: https://docs.sentry.io/clients/python/integrations/logging/


# pkg_resources.get_distribution() seems only to work for eggs, if you use 'vendoring'.
# But several Google packages use it to get the current package version.
# Monkey-Patching let's us use these Packages.
# See https://github.com/lepture/flask-wtf/issues/261
# and https://github.com/GoogleCloudPlatform/google-cloud-python/issues/1893
try:
    import pkg_resources
    def get_distribution_dummy(name):
        class DummyObj(object):
            version = 'unknown'
        return DummyObj()

    pkg_resources.get_distribution = get_distribution_dummy
    logging.debug('disabled `pkg_resources.get_distribution() for GAE compability`')
except ImportError:
    pass


