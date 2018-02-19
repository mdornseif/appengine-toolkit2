#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/views/default.py - handlers implementing common views for gaetk2.

Created by Maximillian Dornseif on 2011-01-09.
Copyright (c) 2011, 2015, 2017, 2018 HUDORA. MIT licensed.
"""
import logging
import os

import google.appengine.api.app_identity
import google.appengine.api.memcache
import google.appengine.ext.deferred.deferred

from gaetk2.application import Route, WSGIApplication
from gaetk2.handlers import DefaultHandler
from gaetk2.config import get_release, get_revision, get_version, is_development, is_production


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
        """Returns the current version."""
        self.return_text(get_version())


class RevisionHandler(DefaultHandler):
    """Version Handler - allows clients to see the git revision currently running."""

    def get(self):
        """Returns the current revision."""
        self.return_text(get_revision())


class ReleaseHandler(DefaultHandler):
    """Version Handler - allows clients to see the git release currently running."""

    def get(self):
        """Returns the current release."""
        self.return_text(get_release())


class WarmupHandler(DefaultHandler):
    """Initialize AppEngine Instance."""

    def warmup(self):
        """Common warmup functionality. Loads big/slow Modules."""
        import datetime
        import jinja2
        import gaetk2.admin  # this will pull in a lot of code, good for warming up
        import gaetk2.modelexporter
        import gaetk2.tools.http
        # http://groups.google.com/group/google-appengine-python/browse_thread/thread/efbcffa181c32f33
        datetime.datetime.strptime('2000-01-01', '%Y-%m-%d').date()
        logging.debug(u"is_production=%s is_development=%s", is_production(), is_development())
        logging.debug(u"SERVER_SOFTWARE %r", os.environ.get('SERVER_SOFTWARE', ''))
        logging.debug(u"SERVER_NAME %r", os.environ.get('SERVER_NAME', ''))
        return repr([gaetk2.tools.http, jinja2, gaetk2.admin, gaetk2.modelexporter])

    def get(self):
        """Handle warm up requests."""
        self.return_text(self.warmup())


application = WSGIApplication([
    Route('/robots.txt', RobotTxtHandler),
    Route('/version.txt', VersionHandler),
    Route('/revision.txt', RevisionHandler),
    Route('/release.txt', ReleaseHandler),
    Route('/_ah/warmup', WarmupHandler),
    (r'^/_ah/queue/deferred.*', google.appengine.ext.deferred.deferred.TaskHandler),
])
