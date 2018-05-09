#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
backup.py - Trigger scheduled Backups via Cron.

See :ref:`backupreplication` for further Information.

See https://cloud.google.com/appengine/articles/scheduled_backups
also https://cloud.google.com/datastore/docs/schedule-export

Created by Christian Klein on 2017-02-17.
Copyright (c) 2017 HUDORA. MIT Licensed.
"""
from __future__ import unicode_literals

import datetime
import logging

from google.appengine.api import taskqueue
from google.appengine.api.app_identity import get_application_id, get_default_gcs_bucket_name
from google.appengine.ext.db.metadata import Kind

from gaetk2.application import Route, WSGIApplication
from gaetk2.config import gaetkconfig
from gaetk2.handlers import DefaultHandler


logger = logging.getLogger(__name__)


# TODO: this woll stop to work https://cloud.google.com/appengine/docs/deprecations/datastore-admin-backups
# needs to be replaced with https://cloud.google.com/datastore/docs/schedule-export
# Something like
# curl \
# -H "Authorization: Bearer $(gcloud auth print-access-token)" \
# -H "Content-Type: application/json" \
# https://datastore.googleapis.com/v1/projects/${PROJECT_ID}:export \
# -d '{
#   "outputUrlPrefix": "gs://'${BUCKET}'",
#   "entityFilter": {
#     "namespaceIds": [""],
#   },
# }'

class BackupHandler(DefaultHandler):
    """Handler to start scheduled backups."""

    def get(self):
        """To be called by cron and only by cron."""
        # if 'X-AppEngine-Cron' not in self.request.headers:
        #     raise HTTP403_Forbidden('Scheduled backups must be started via cron')

        if not gaetkconfig.BACKUP_BUCKET:
            bucket = get_default_gcs_bucket_name()
        else:
            bucket = gaetkconfig.BACKUP_BUCKET

        today = datetime.date.today()
        kinds = [kind for kind in _get_all_datastore_kinds()]
        # if kind not in config.BACKUP_BLACKLIST]
        bucketname = '/'.join([
            bucket,
            get_application_id(),
            today.strftime('%Y-%m-%d')])
        bucketname = bucketname.lstrip('/')
        params = dict(
            name='ds',
            gs_bucket_name=bucketname,
            filesystem='gs',
            queue=gaetkconfig.BACKUP_QUEUE,
            kind=kinds,
        )
        logger.info('backup to %r %r', bucketname, params)

        taskqueue.add(
            url='/_ah/datastore_admin/backup.create',
            method='POST',
            target='ah-builtin-python-bundle',
            params=params,
        )
        self.return_text('OK')


def _get_all_datastore_kinds():
    for kind in Kind.all():
        if not kind.kind_name.startswith('_'):
            yield kind.kind_name


application = WSGIApplication([
    ('/gaetk2/backup/', BackupHandler),
    Route('/gaetk2/backup/', BackupHandler),
    ('.*', BackupHandler),
])
