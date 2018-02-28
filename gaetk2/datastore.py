#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.datastore - Helper for ndb datastore usage.

Created by Maximillian Dornseif on 2011-01-07.
Copyright (c) 2011, 2012, 2016, 2017 Cyberlogi/HUDORA. All rights reserved.
"""
import warnings

from google.appengine.ext import ndb


class Model(ndb.Model):
    """Generic fields to keep datastore organized."""

    # these fields work only if the user was logges in via google infrastructure
    created_at = ndb.DateTimeProperty(auto_now_add=True, indexed=True)
    # `updated_at` is needed for replication
    updated_at = ndb.DateTimeProperty(auto_now=True, indexed=True)

    # see https://docs.python.org/2/glossary.html#term-hashable
    def __hash__(self):
        return hash(self.key.id())

    def __eq__(self, other):
        return self.key.id() == other.key.id()

    def as_dict(self):
        u"""Gibt eine Repräsentation des Objektes zurück."""
        warnings.warn("`as_dict` is deprecated, use `to_dict()`", DeprecationWarning, stacklevel=2)
        return self.to_dict()


class AuditedModel(Model):
    """Fields to add an Audit-Trail to the Datastore."""

    # these fields work only if the user was logges in via google infrastructure
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
    props = dict((
        v._code_name, v.__get__(e, klass))
        for v in klass._properties.itervalues()
        if type(v) is not ndb.ComputedProperty)
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


def write_on_change2(instance, data):
    """Apply new data to an entity and write to datastore if anything changed.

    This should save you money since reads are 3 times cheaper than writes.
    It also helps you do leave not given attributes unchanged.

    Usage::

        instance = ndb.Model...get()
        dirty = write_on_change2(instance, ...,
          dict(id=123, amout_open=500, score=5, ...)
    """

    assert instance
    dirty = False
    for key, value in data.iteritems():
        if value != getattr(instance, key, None):
            setattr(instance, key, value)
            dirty = True
    if dirty:
        instance.put()

    return dirty


def reload_obj(obj):
    """Returns a reloaded Entity from disk."""
    return obj.key.get(use_cache=False, use_memcache=False)
