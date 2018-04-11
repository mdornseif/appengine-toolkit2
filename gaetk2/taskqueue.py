#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2.taskqueue

Created by Maximillian Dornseif on 2011-01-07.
Copyright (c) 2011, 2012, 2016-2018 Cyberlogi/HUDORA. All rights reserved.
"""
from __future__ import unicode_literals

import datetime
import hashlib
import logging
import re
import zlib

import google.appengine.ext.deferred.deferred

from google.appengine.api import taskqueue
from google.appengine.ext import deferred

from .config import is_production
from .tools.datetools import date_trunc
from .tools.unicode import slugify


logger = logging.getLogger(__name__)


def taskqueue_add_multi(qname, url, paramlist, **kwargs):
    """Adds more than one Task to the same Taskqueue/URL.

    This helps to save API-Calls. Usage pattern::

        tasks = []
        for kdnnr in kunden.get_changed():
            tasks.append(dict(kundennr=kdnnr))
        taskqueue_add_multi('softmq', '/some/path', tasks)
    """

    tasks = []
    for params in paramlist:
        tasks.append(taskqueue.Task(url=url, params=params, **kwargs))
        # Batch Addition to Taskqueue
        if len(tasks) >= 50:
            taskqueue.Queue(name=qname).add(tasks)
            tasks = []
    if tasks:
        taskqueue.Queue(name=qname).add(tasks)


def taskqueue_add_multi_payload(name, url, payloadlist, **kwargs):
    """like taskqueue_add_multi() but transmit a json encoded payload instead a query parameter.

    In the Task handler you can get the data via ``zdata = json.loads(self.request.body)``.
    See http://code.google.com/appengine/docs/python/taskqueue/tasks.html"""

    import huTools.hujson
    tasks = []
    for payload in payloadlist:
        payload = huTools.hujson.dumps(payload)
        payload = zlib.compress(payload)
        tasks.append(taskqueue.Task(url=url, payload=payload, **kwargs))
        # Patch Addition to Taskqueue
        if len(tasks) >= 50:
            taskqueue.Queue(name=name).add(tasks)
            tasks = []
    if tasks:
        taskqueue.Queue(name=name).add(tasks)
    logger.debug('%d tasks queued to %s', len(payloadlist), url)


# See also https://github.com/freshplanet/AppEngine-Deferred
# and https://medium.com/the-infinite-machine/problems-with-deferred-bad13cac3216
# and https://pypi.python.org/pypi/appenginetaskutils

def defer(obj, *args, **kwargs):
    """Defers a callable for execution later.

    like https://cloud.google.com/appengine/articles/deferred
    but adds the function name to the url for easier debugging.

    Add this to `app.yaml`:
        handlers:
            # needed to allow abritary postfixes and better error handling
            - url: /_ah/queue/deferred(.*)
              script: gaetk2.views.default.application
              login: admin

    Parameters starting with ``_`` are handed down to
    `taskqueue.add() <https://cloud.google.com/appengine/docs/standard/python/refdocs/
    google.appengine.api.taskqueue.taskqueue#google.appengine.api.taskqueue.taskqueue.add>`_

    """

    suffix = '{}({!s},{!r})'.format(
        obj.__name__,
        ','.join(_to_str(arg) for arg in args),
        ','.join('%s=%s' % (
            key, _to_str(value)) for (key, value) in kwargs.items() if not key.startswith('_'))
    )
    suffix = re.sub(r'-+', '-', suffix.replace(' ', '-'))
    suffix = re.sub(r'[^/A-Za-z0-9_,.:@&+$\(\)\-]+', '', suffix)
    url = google.appengine.ext.deferred.deferred._DEFAULT_URL + '/' + suffix[:200]
    kwargs['_url'] = kwargs.pop('_url', url)
    # kwargs["_queue"] = kwargs.pop("_queue", 'workersq')
    if is_production():
        # we only route to the workers backend/module on production machines
        pass
        # kwargs["_target"] = kwargs.pop("_target", 'workers')
    try:
        task = deferred.defer(obj, *args, **kwargs)
        logging.debug('started task %r', task.name)
        return task.name
    except taskqueue.TaskAlreadyExistsError:
        logger.info('Task already exists')
    except taskqueue.TombstonedTaskError:
        logger.info('Task did already run')


def _to_str(value):
    """Convert all datatypes to str"""
    if isinstance(value, basestring):
        try:
            value = value.encode('ascii', errors='replace')[:50]
        except UnicodeDecodeError:  # how can this happen?
            value = repr(value)
        value = slugify(value)
    value = str(value)
    if len(value) > 20:
        value = '{}...'.format(value[:20])
    return value


def defer_once_per_hour(obj, *args, **kwargs):
    """Like :func:`defer()` but only once per hour.

    Eexecutes the same function with the same parameters not more
    often than once per hour. The heuristic for doing so are not
    exact so do not rely on this mechanism for anything importatant.

    This is more for updating cloud services with statistics etc.
    """
    key = ','.join(unicode(arg) for arg in args)
    key += ','.join('{}={}'.format(
        key, unicode(value)) for (key, value) in kwargs.items())
    key = key.encode('utf-8', errors='replace')
    name = '{}.{}-{}-{}'.format(
        obj.__module__, obj.__name__,
        date_trunc('hour', datetime.datetime.now()).strftime('%Y%m%dT%H'),
        hashlib.md5(key).hexdigest()
    )
    return defer(obj, _name=slugify(name), *args, **kwargs)
