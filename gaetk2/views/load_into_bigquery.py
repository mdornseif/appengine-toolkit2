#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
load_into_big_query.py - Load Cloud Datastore Backups into BigQuery.

See :ref:`backupreplication` for further Information.

Es werden Daten eines Datastore-Backups zu BigQuery exportiert.
Für Backups, siehe
https://cloud.google.com/appengine/articles/scheduled_backups
https://github.com/mdornseif/appengine-toolkit/blob/master/gaetk2/views/backup.py

Zum Laden siehe https://cloud.google.com/bigquery/docs/loading-data-cloud-datastore

Extrahiert aus huWaWi
Created by Christian Klein on 2017-04-19.
Copyright (c) 2017, 2018 HUDORA. All rights reserved.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import logging
import re
import time

from google.appengine.api.app_identity import get_application_id
from google.appengine.api.app_identity import get_default_gcs_bucket_name
from google.cloud import bigquery

import cloudstorage

from gaetk2 import exc
from gaetk2.application import Route
from gaetk2.application import WSGIApplication
from gaetk2.config import gaetkconfig
from gaetk2.handlers import DefaultHandler
from gaetk2.taskqueue import defer
from gaetk2.tools.datetools import convert_to_date


logger = logging.getLogger(__name__)


def create_job(filename):
    """Erzeuge Job zum Upload einer Datastore-Backup-Datei zu Google BigQuery"""
    bigquery_client = bigquery.Client(project=gaetkconfig.BIGQUERY_PROJECT)
    if not gaetkconfig.BIGQUERY_DATASET:
        dataset = get_default_gcs_bucket_name()
    else:
        dataset = gaetkconfig.BIGQUERY_DATASET

    tablename = filename.split('.')[-2]
    # see https://cloud.google.com/bigquery/docs/reference/rest/v2/jobs#configuration.load
    resource = {
        'configuration': {
            'load': {
                'destinationTable': {
                    'projectId': gaetkconfig.BIGQUERY_PROJECT,
                    'datasetId': dataset,
                    'tableId': tablename,
                },
                'maxBadRecords': 0,
                'sourceUris': ['gs:/' + filename],
                'projectionFields': [],
                'sourceFormat': 'DATASTORE_BACKUP',
                'writeDisposition': 'WRITE_TRUNCATE',
            }
        },
        'jobReference': {
            'projectId': gaetkconfig.BIGQUERY_PROJECT,
            'jobId': 'import-{}-{}'.format(tablename, int(time.time())),
        },
    }

    # POST https://www.googleapis.com/bigquery/v2/projects/projectId/jobs
    job = bigquery_client.job_from_resource(resource)
    return job


def upload_backup_file(filename):
    """Lade Datastore-Backup-Datei zu Google BigQuery"""
    logger.info('uploading %r', filename)
    job = create_job(filename)
    job.result()  # Waits for table load to complete.
    # try:
    #     job.begin()
    # except google.cloud.exceptions.Conflict:
    #     logger.warn(u'Konflikt bei %s', job.name)
    #     return

    # while True:
    #     job.reload()
    #     if job.state == 'DONE':
    #         if job.error_result:
    #             raise RuntimeError(u'FAILED JOB, error_result: %s' % job.error_result)
    #         break
    #     logger.debug("waiting for job in state %s", job.state)
    #     time.sleep(5)  # ghetto polling


class BqReplication(DefaultHandler):
    """Steuerung der Replizierung zu Google BigQuery."""

    def get(self):
        """Regelmäßig von Cron aufzurufen."""
        if not gaetkconfig.BIGQUERY_PROJECT:
            return self.return_text('BIGQUERY_PROJECT not provided, exiting')

        if not gaetkconfig.BACKUP_BUCKET:
            bucket = get_default_gcs_bucket_name()
        else:
            bucket = gaetkconfig.BACKUP_BUCKET

        bucketpath = '/'.join((bucket, get_application_id()))
        bucketpath = '/{}/'.format(bucketpath.strip('/'))
        logger.info('searching backups in %r', bucketpath)

        objs = cloudstorage.listbucket(bucketpath, delimiter=b'/')
        subdirs = sorted((obj.filename for obj in objs if obj.is_dir), reverse=True)
        # Find Path of newest available backup
        # typical path:
        # '/appengine-backups-eu-nearline/hudoraexpress/2017-05-02/ag9...EM.ArtikelBild.backup_info'
        dirs = {}
        for subdir in subdirs:
            try:
                datum = convert_to_date(subdir.rstrip('/').split('/')[-1])
            except ValueError:
                continue
            else:
                dirs[datum] = subdir

        if not dirs:
            raise RuntimeError('No Datastore Backup found in %r' % (bucketpath))

        datum = max(dirs)
        if datum < datetime.date.today() - datetime.timedelta(days=7):
            raise exc.RuntimeError(
                'Latest Datastore Backup in {!r} is way too old!'.format(bucketpath)
            )

        countdown = 1
        subdir = dirs[datum]
        logger.info('Uploading Backup %s from directory %s', datum, subdir)
        regexp = re.compile(subdir + r'([\w-]+)\.(\w+)\.backup_info')
        for obj in cloudstorage.listbucket(subdir):
            if regexp.match(obj.filename):
                defer(upload_backup_file, obj.filename, _countdown=countdown)
                countdown += 2
        self.response.write('ok, countdown=%d\n' % (countdown))


application = WSGIApplication([Route('/gaetk2/load_into_bigquery', BqReplication)])
