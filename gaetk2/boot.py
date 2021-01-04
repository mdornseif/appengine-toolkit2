#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
Copyright (c) 2017, 2018 Maximillian Dornseif. MIT Licensed.
"""
# pylint: skip-file
# flake8: noqa
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import os.path
import sys
import warnings

from google.appengine.ext import vendor


# something redirects warning to logging.error() on App Engine (stderr?).
# Fix it.
logging.captureWarnings(True)

warnings.simplefilter('always')  # reset filter to see DeprecationWarning
warnings.filterwarnings('ignore', module='cgitb')
warnings.filterwarnings(
    'ignore', module='ssl_'
)  # SNIMissingWarning, InsecurePlatformWarning
warnings.filterwarnings('ignore', module='pkgutil')
warnings.filterwarnings('ignore', message='decode_param_names is deprecated')
warnings.filterwarnings(
    'ignore', message='cgi.parse_qs is deprecated, use urlparse.parse_qs instead'
)
warnings.filterwarnings(
    'ignore', message='urllib3 is using URLFetch on Google App Engine sandbox'
)
warnings.filterwarnings(
    'ignore', message='Required is going away in WTForms 3.0, use DataRequired'
)
warnings.filterwarnings(
    'ignore', message='The TextField alias for StringField has been deprecated'
)

# Include libraries
# `google.appengine.ext.vendor.add` is just `site.addsitedir()` with path shuffling

vendor.add('./lib')  # processes `.pth` files
try:
    vendor.add('./lib/site-packages')  # processes `.pth` files
except ValueError:
    pass


def setup_sdk_imports():
    """Sets up appengine SDK third-party imports."""
    # https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/appengine/standard/appengine_helper.py

    sdk_path = os.environ.get('GAE_SDK_PATH')

    if not sdk_path:
        return

    if os.path.exists(os.path.join(sdk_path, 'google_appengine')):
        sdk_path = os.path.join(sdk_path, 'google_appengine')

    if 'google' in sys.modules:
        sys.modules['google'].__path__.append(os.path.join(sdk_path, 'google'))

    # This sets up libraries packaged with the SDK, but puts them last in
    # sys.path to prevent clobbering newer versions
    sys.path.append(sdk_path)
    # import dev_appserver
    # sys.path.extend(dev_appserver.EXTRA_PATHS)

    # Fixes timezone and other os-level items.
    import google.appengine.tools.os_compat

    (google.appengine.tools.os_compat)


# fixing botocore
os.path.expanduser = lambda x: x

try:
    import requests  # isort:skip
    import requests_toolbelt.adapters.appengine  # isort:skip
    requests_toolbelt.adapters.appengine.monkeypatch(validate_certificate=False)
    # this breaks code like
    #    session = requests.session()
    #    session.mount('https://', appengine.AppEngineAdapter())
    #    return dropbox.Dropbox(access_token session=session)
    # But without that session mounting you would get ChunkedEncodingError.
except ImportError:
    pass

try:
    # suppress SSL warnings we can not do anything about
    import urllib3  # isort:skip
    urllib3.disable_warnings()
except ImportError:
    pass

try:
    # incerase global HTTP-Timeout from 5 to 30 seconds
    import google.appengine.api.urlfetch  # isort:skip
    google.appengine.api.urlfetch.set_default_fetch_deadline(30)
except ImportError:
    pass

# ensure we can see the funcname for convinience and the logger name for selective supression
# see https://docs.python.org/2/library/logging.html#logrecord-attributes
fr = logging.Formatter('%(funcName)s(): %(message)s [%(name)s]')
logging.getLogger().handlers[0].setFormatter(fr)

# get info from the `warnings` module into Sentry
logging.captureWarnings(True)

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

# pkg_resources.get_distribution() seems only to work for eggs, not if you use 'vendoring'.
# But several Google packages use it to get the current package version.
# Monkey-Patching let's us use these Packages.
# See https://github.com/lepture/flask-wtf/issues/261
# and https://github.com/GoogleCloudPlatform/google-cloud-python/issues/1893
try:
    import pkg_resources

    def get_distribution_dummy(name):
        """Simulating :func:`pkg_resources.get_distribution`."""

        class DummyObj(object):
            """Simulating :class:`pkg_resources.distribution`."""

            version = 'unknown'
            parsed_version = 'unknown'

        return DummyObj()

    pkg_resources.get_distribution = get_distribution_dummy
except ImportError:
    pass


# often we get at this point a "Mamespace Package" in `lib/site-packages/google`
# which shadows the App Engine SDK stored at `lib/google_appengine/google`
# Seemingly only monkey patching `sys.modules['google'].__path__`
# can solve this.

# ensure conflictiong modules are loaded to pull in the Namespace Package
for modname in ['google.cloud.exceptions', 'google.cloud.bigquery', 'google.cloud.datastore']:
    try:
        __import__(modname)
    except ImportError:
        pass
    except pkg_resources.DistributionNotFound:
        pass

setup_sdk_imports()
# print('PYTHONPATH={}'.format(':'.join(sys.path)))
NOW_THIS_WORKS = __import__('google.appengine.ext')
