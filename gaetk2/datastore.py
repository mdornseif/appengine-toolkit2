#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2.datastore - Helper for ndb datastore usage.

Created by Maximillian Dornseif on 2011-01-07.
Copyright (c) 2011, 2012, 2016, 2017, 2018 Cyberlogi/HUDORA. All rights reserved.
"""
from __future__ import unicode_literals

import logging
import warnings

from google.appengine.ext import ndb

from gaetk2.taskqueue import defer


logger = logging.getLogger(__name__)


class Model(ndb.Model):
    """Generic fields to keep datastore organized."""

    created_at = ndb.DateTimeProperty(auto_now_add=True, indexed=True)
    # `updated_at` is needed for replication
    updated_at = ndb.DateTimeProperty(auto_now=True, indexed=True)

    # see https://docs.python.org/2/glossary.html#term-hashable
    def __hash__(self):
        return hash(self.key.id())

    def __eq__(self, other):
        return self.key.id() == other.key.id()

    def as_dict(self):
        """Gibt eine Repräsentation des Objektes zurück."""
        warnings.warn('`as_dict` is deprecated, use `to_dict()`', DeprecationWarning, stacklevel=2)
        return self.to_dict()


class DeletableModel(Model):
    """Functionality to implement (soft) delete."""
    deleted = ndb.BooleanProperty(default=False, indexed=True)


class AuditedModel(Model):
    """Fields to add an Audit-Trail to the Datastore."""

    # these fields work only if the user was logged in via google infrastructure
    created_by = ndb.UserProperty(required=False, auto_current_user_add=True, indexed=True)
    updated_by = ndb.UserProperty(required=False, auto_current_user=True, indexed=True)


class DeletableAuditedModel(Model):

    deleted = ndb.BooleanProperty(default=False, indexed=True)
    # these fields work only if the user was logged in via google infrastructure
    created_by = ndb.UserProperty(required=False, auto_current_user_add=True, indexed=True)
    updated_by = ndb.UserProperty(required=False, auto_current_user=True, indexed=True)


def query_iterator(query, limit=50):
    """Iterates over a datastore query while avoiding timeouts via a cursor.

    Especially helpful for usage in backend-jobs."""
    cursor = None
    while True:
        bucket, cursor, more_objects = query.fetch_page(limit, start_cursor=cursor)
        if not bucket:
            break
        for entity in bucket:
            yield entity
        if not more_objects:
            break


def copy_entity(e, **extra_args):
    """Copy ndb entity but change values in kwargs.

    Usage::
        b = copy_entity(a, id='new_id_here')
        b.put()
    """
    # see https://stackoverflow.com/a/2712401
    klass = e.__class__
    props = {
        v._code_name: v.__get__(e, klass)
        for v in klass._properties.itervalues()
        if type(v) is not ndb.ComputedProperty}
    props.update(extra_args)
    return klass(**props)


@ndb.transactional
def get_or_insert_if_new(cls, id, **kwds):
    """Like ndb.get_or_insert()` but returns `(entity, new)`.

    This allows you to see if something has been created or if there was an
    already existing entity::

        >>> get_or_insert_if_new(Model, 'newid')
        (<instance>, True)
        >>> get_or_insert_if_new(Model, 'newid')
        (<instance>, False)
    """
    # from https://stackoverflow.com/a/14549493/49407
    # See https://cloud.google.com/appengine/docs/standard/python/ndb/modelclass#Model_get_or_insert
    key = ndb.Key(cls, id)
    ent = key.get()
    if ent is not None:
        return (ent, False)  # False meaning "not created"
    ent = cls(**kwds)
    ent.key = key
    ent.put()
    return (ent, True)  # True meaning "created"


def write_on_change2(obj, data):
    """Apply new data to an entity and write to datastore if anything changed.

    This should save you money since reads are 3 times cheaper than writes.
    It also helps you do leave not given attributes unchanged.

    Usage::

        instance = ndb.Model...get()
        dirty = write_on_change2(instance, ...,
          dict(id=123, amout_open=500, score=5, ...)
    """

    assert obj
    dirty = False
    for key, value in data.iteritems():
        if value != getattr(obj, key, None):
            setattr(obj, key, value)
            dirty = True
    if dirty:
        obj.put()

    return dirty


def update_obj(obj, **kwargs):
    """More modern Interface to :func:`write_on_change2`."""
    return write_on_change2(obj, kwargs)


def reload_obj(obj):
    """Returns a reloaded Entity from disk."""
    return obj.key.get(use_cache=False, use_memcache=False)


def apply_to_all_entities(func, model, batch_size=0, num_updated=0, num_processed=0, cursor=None):
    """Appliy a certain task all entities of `model`.

    It scans every entity in the datastore for the
    model, exectues `func(entity)` on it and re-saves it
    if func trturns true.
    Tries to keep `updated_at` and `updated_by` unchanged.

    Example:
        def _fixup_MyModel_updatefunc(obj):
            if obj.wert_waehrung is not None:
                obj.wert_waehrung = int(obj.wert_waehrung)
                return True
            return False

        def fixup_MyModel():
            apply_to_all_entities(_fixup_app_angebotspos_updatefunc, MyModel)
    """
    # from https://cloud.google.com/appengine/articles/update_schema

    # Get all of the entities for this Model.
    query = model.query()
    if not batch_size:
        objects, next_cursor, more = query.fetch_page(
            5, start_cursor=cursor)
    else:
        batch_size = 100
        objects, next_cursor, more = query.fetch_page(
            batch_size, start_cursor=cursor)

    updated_now = 0
    for obj in objects:
        num_processed += 1
        if 'updated_at' in obj._properties:
            obj._properties['updated_at'].auto_now = False
            obj._properties['updated_at']._auto_now = False
        if 'updated_by' in obj._properties:
            obj._properties['updated_by'].auto_current_user = False
            obj._properties['updated_by']._auto_current_user = False

        if func(obj):
            obj.put()  # use_cache=False, use_memcache=False)
            num_updated += 1
            updated_now += 1

        if 'updated_at' in obj._properties:
            obj._properties['updated_at'].auto_now = True
            obj._properties['updated_at']._auto_now = True
        if 'updated_by' in obj._properties:
            obj._properties['updated_by'].auto_current_user = True
            obj._properties['updated_by']._auto_current_user = True
    logger.debug(
        'Put %s entities to Datastore for a total of %s/%s', updated_now,
        num_updated, num_processed)

    # If there are more entities, re-queue this task for the next page.
    if more:
        defer(
            apply_to_all_entities, func, model,
            batch_size=100, cursor=next_cursor,
            num_updated=num_updated, num_processed=num_processed)
    else:
        logger.info(
            'update_schema_task complete with %s entities resulting in %s updates!',
            num_processed, num_updated)
