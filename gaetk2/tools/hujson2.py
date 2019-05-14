#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hujson2.py - encode Google App Engine Models and stuff.

hujson can encode additional types like decimal and datetime into valid json.

Created by Maximillian Dornseif on 2010-09-10.
Copyright (c) 2010, 2012, 2013, 2017, 2018 HUDORA. MIT licensed.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import decimal
import json
import logging
import time


# see raven/utils/json.py for an other nice aproach


def _unknown_handler(value):
    """Helper for json.dmps())."""
    # originally from `huTools.hujson` (c) 2010
    if isinstance(value, datetime.datetime):
        return value.isoformat().rstrip('Z') + 'Z'
    elif isinstance(value, (datetime.date)):
        return unicode(value)
    # elif hasattr(value, 'dict_mit_positionen') and callable(value.dict_mit_positionen):
    #     # helpful for our internal data-modelling
    #     return value.dict_mit_positionen()
    elif hasattr(value, 'as_dict') and callable(value.as_dict):
        # helpful for structured.Struct() Objects
        return value.as_dict()
    # for Google AppEngine
    elif hasattr(value, 'to_dict') and callable(value.to_dict):
        # helpful for ndb.Model Objects
        if (
            hasattr(value, 'key')
            and hasattr(value.key, 'id')
            and callable(value.key.id)
        ):
            return dict(value.to_dict(), **dict(_id=value.key.id()))
        else:
            return value.to_dict()
    # for Google AppEngine `ndb`
    elif (
        hasattr(value, '_properties')
        and hasattr(value._properties, 'items')
        and callable(value._properties.items)
    ):
        return {k: v._get_value(value) for k, v in value._properties.items()}
    elif hasattr(value, 'urlsafe') and callable(value.urlsafe):
        return str(value.urlsafe())
    elif hasattr(value, '_to_entity') and callable(value._to_entity):
        retdict = {}
        value._to_entity(retdict)
        return retdict
    elif hasattr(value, 'properties') and callable(value.properties):
        properties = value.properties()
        if isinstance(properties, dict):
            keys = (
                key
                for (key, datatype) in properties.iteritems()
                if datatype.__class__.__name__ not in ['BlobProperty']
            )
        elif isinstance(properties, (set, list)):
            keys = properties
        else:
            return {}
        return {key: getattr(value, key) for key in keys}

    tv = str(type(value))
    if 'google.appengine.api.users.User' in tv:
        return '{}/{}'.format(value.user_id(), value.email())
    elif 'google.appengine.api.datastore_types.Key' in tv:
        return str(value)
    elif 'google.appengine.api.datastore_types.BlobKey' in tv:
        return str(value)
    elif isinstance(value, decimal.Decimal):
        return unicode(value)
    else:
        return unicode(value)
    raise TypeError('{}({})'.format(type(value), value))


def dump(val, fd, indent=' ', sort_keys=True):
    """Dump `val` into `fd` encoded as JSON."""
    json.dump(
        val,
        fd,
        sort_keys=sort_keys,
        indent=bool(indent),
        ensure_ascii=True,
        default=_unknown_handler,
    )


def dumps(val, indent=' ', sort_keys=True):
    """Return a JSON string containing encoded `val`."""
    start = time.time()
    ret = json.dumps(
        val,
        sort_keys=sort_keys,
        indent=bool(indent),
        ensure_ascii=True,
        default=_unknown_handler,
    )
    delta = time.time() - start
    if delta > 1:
        logging.warn('dumps took %f seconds', delta)
    return ret


def loads(data):
    """Parse `data` as JSON and return Python data."""
    return json.loads(data)


def htmlsafe_json_dumps(obj, **kwargs):
    """Use `jinja2.utils.htmlsafe_json_dumps` with our dumper."""
    import jinja2.utils

    return jinja2.utils.htmlsafe_json_dumps(obj, dumper=dumps, **kwargs)
