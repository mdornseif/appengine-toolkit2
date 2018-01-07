#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/views/default.py - handlers implementing common views for gaetk2.

Created by Maximillian Dornseif on 2011-01-09.
Copyright (c) 2011, 2015, 2017 HUDORA. MIT licensed.
"""
import google.appengine.api.app_identity
import google.appengine.api.memcache

from ..application import make_app
from ..handlers import DefaultHandler
from ..tools.config import get_version
from .tools.config import is_production


class RobotTxtHandler(DefaultHandler):
    """Handler for `robots.txt`.

    Assumes that only the default version should be crawled.
    For the default version the contents of the file `robots.txt`
    are sent. For all other versions `Disallow: /` is sent.
    """

    def get(self):
        """Deliver robots.txt based on application version."""
        if not is_production():
            response = ('# use http://%s/\nUser-agent: *\nDisallow: /\n'
                        % google.appengine.api.app_identity.get_default_version_hostname())
        else:
            try:
                # read robots.txt
                response = open('robots.txt').read().strip()
            except IOError:
                # robots.txt file not available - use somewhat simple-minded default
                response = 'User-agent: *\nDisallow: /intern\nDisallow: /admin\n'

        self.return_text(response)


class VersionHandler(DefaultHandler):
    """Version Handler - allows clients to see the git revision currently running."""

    def get(self):
        """Returns the current Version."""
        self.return_text(get_version())


class WarmupHandler(DefaultHandler):
    """Initialize AppEngine Instance."""

    def warmup(self):
        """Common warmup functionality. Loads big/slow Modules."""
        import datetime.datetime
        import tools.http
        import jinja2
        import gaetk2.admin
        import gaetk2.moduleexporter
        # http://groups.google.com/group/google-appengine-python/browse_thread/thread/efbcffa181c32f33
        datetime.datetime.strptime('2000-01-01', '%Y-%m-%d').date()
        return repr([tools.http, jinja2, gaetk2.admin, gaetk2.moduleexporter])

    def get(self):
        """Handle warm up requests."""
        self.return_text(self.warmup())


application = make_app([
    (r'robots.txt$', RobotTxtHandler),
    (r'version.txt$', VersionHandler),
    (r'^/_ah/warmup$', WarmupHandler),
])
