.. _backupreplication:

Backup and Replication Guide
============================

The general flow ist that you do a `Managed Export <https://cloud.google.com/datastore/docs/export-import-entities>`_ of your datastore entities to Google Cloud Storage. Than load that data into Google BigQuery
via a `load job <https://cloud.google.com/bigquery/docs/loading-data-cloud-datastore>`_ and do all further exporting and analysis
from there.

This replaces `gaetk_replication <https://github.com/hudora/gaetk_replication>` which was able export to MySQL and JSON on S3 directly
although unreliably.

Following Parameters in :file:`gaetk2_config.py` (see :mod:`gaetk2.config`) define the behaviour of managed export and loding into BigQuery.

.. index::
   pair: gaetk2_config.py; GAETK2_BACKUP_BUCKET

``GAETK2_BACKUP_BUCKET`` defines where in Cloud Storage the backup should be saved. Defaults to :func:`google.appengine.api.app_identity.get_default_gcs_bucket_name()`.


.. index::
   pair: gaetk2_config.py; GAETK2_BACKUP_QUEUE

``GAETK2_BACKUP_QUEUE`` defines the TaskQueue to use for backup. Defaults to ``default``.


.. index::
   pair: gaetk2_config.py; GAETK2_BIGQUERY_PROJECT

``GAETK2_BIGQUERY_PROJECT`` is the BigQuery Project to load data in to. If not set, no data loading will happen.


.. index::
   pair: gaetk2_config.py; GAETK2_BIGQUERY_DATASET

``GAETK2_BIGQUERY_DATASET`` is the dataset to use for the load job. If not set, :func:`google.appengine.api.app_identity.get_default_gcs_bucket_name()` is used.


To use the functionality, you have to add two handlers to ``cron.yaml``::

	cron:
	- description: Scheduled Backup - für BigQuery
	  url: /gaetk2/backup/
	  schedule:  every day 04:01
	  timezone: Europe/Berlin
	- description: Replikation zu BigQuery
	  url: /gaetk_replication/bigquery/cron
	  schedule:  every day 05:01
	  timezone: Europe/Berlin

See :class:`gaetk2.views.backup.BackupHandler` and :class:`gaetk2.views.load_into_bigquery.BqReplication` for the actual implementation.
