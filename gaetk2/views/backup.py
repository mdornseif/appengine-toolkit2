#!/usr/bin/env python
# encoding: utf-8
"""
backup.py - Trigger scheduled Backups via Cron.

See https://cloud.google.com/appengine/articles/scheduled_backups

Created by Christian Klein on 2017-02-17.
Copyright (c) 2017 HUDORA. MIT Licensed.
"""
import datetime
import logging

from google.appengine.api import taskqueue
from google.appengine.api.app_identity import get_application_id
from google.appengine.ext.db.metadata import Kind

from ..application import make_app
from ..exc import HTTP403_Forbidden
from ..handlers import DefaultHandler
from ..tools.config import config


class BackupHandler(DefaultHandler):
    """Handler to start scheduled backups."""

    def get(self):
        """To be called by cron and only by cron."""
        if 'X-AppEngine-Cron' not in self.request.headers:
            raise HTTP403_Forbidden('Scheduled backups must be started via cron')

        today = datetime.date.today()
        kinds = [kind for kind in _get_all_datastore_kinds() if kind not in config.BACKUP_BLACKLIST]
        bucketname = '/'.join((
            config.BACKUP_GS_BUCKET,
            get_application_id(),
            today.isoformat())).lstrip('/')
        params = dict(
            name='datastore_backup_' + today.isoformat(),
            gs_bucket_name=bucketname,
            filesystem=config.BACKUP_FILESYSTEM,
            queue=config.BACKUP_QUEUE,
            kind=kinds,
        )
        logging.info(u'backup to %r %r', bucketname, params)

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


application = make_app([
    (r'^backup/$', BackupHandler),
])
