#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hujson2.py - encode Google App Engine Models and stuff.

hujson can encode additional types like decimal and datetime into valid json.

Created by Maximillian Dornseif on 2010-09-10.
Copyright (c) 2010, 2012, 2013, 2017, 2018 HUDORA. MIT licensed.
"""
from __future__ import unicode_literals

import datetime
import decimal
import json


# see raven/utils/json.py for an other nice aproach


def _unknown_handler(value):
    """Helper for json.dmps())."""
    # originally from `huTools.hujson` (c) 2010
    if isinstance(value, datetime.date):
        return str(value)
    elif isinstance(value, datetime.datetime):
        return value.isoformat() + 'Z'
    elif isinstance(value, decimal.Decimal):
        return unicode(value)
    elif hasattr(value, 'dict_mit_positionen') and callable(value.dict_mit_positionen):
        # helpful for our internal data-modelling
        return value.dict_mit_positionen()
    elif hasattr(value, 'as_dict') and callable(value.as_dict):
        # helpful for structured.Struct() Objects
        return value.as_dict()
    elif hasattr(value, 'to_dict') and callable(value.to_dict):
        # helpful for ndb.Model Objects
        return value.to_dict()
    # for Google AppEngine
    elif hasattr(value, 'properties') and callable(value.properties):
        properties = value.properties()
        if isinstance(properties, dict):
            keys = (key for (key, datatype) in properties.iteritems()
                    if datatype.__class__.__name__ not in ['BlobProperty'])
        elif isinstance(properties, (set, list)):
            keys = properties
        else:
            return {}
        return {key: getattr(value, key) for key in keys}
    elif hasattr(value, 'to_dict') and callable(value.to_dict):
        # ndb
        tmp = value.to_dict()
        if 'id' not in tmp and hasattr(value, 'key') and hasattr(value.key, 'id') and callable(value.key.id):
            tmp['id'] = value.key.id()
        return tmp
    elif hasattr(value, '_to_entity') and callable(value._to_entity):
        retdict = {}
        value._to_entity(retdict)
        return retdict
    elif 'google.appengine.api.users.User' in str(type(value)):
        return '%s/%s' % (value.user_id(), value.email())
    elif 'google.appengine.api.datastore_types.Key' in str(type(value)):
        return str(value)
    elif 'google.appengine.api.datastore_types.BlobKey' in str(type(value)):
        return str(value)
    # for Google AppEngine `ndb`
    elif (hasattr(value, '_properties') and hasattr(value._properties, 'items') and
          callable(value._properties.items)):
        return {k: v._get_value(value) for k, v in value._properties.items()}
    elif hasattr(value, 'urlsafe') and callable(value.urlsafe):
        return str(value.urlsafe())
    # elif hasattr(value, '_get_value') and callable(value._get_value):
    #    retdict = dict()
    #    value._get_value(retdict)
    #    return retdict
    else:
        return str(value)
    raise TypeError('%s(%s)' % (type(value), value))


def dump(val, fd, indent=' ', sort_keys=True):
    """Dump `val` into `fd` encoded as JSON."""
    json.dump(val, fd, sort_keys=sort_keys, indent=bool(indent), ensure_ascii=True,
              default=_unknown_handler)


def dumps(val, indent=' ', sort_keys=True):
    """Return a JSON string containing encoded `val`."""
    return json.dumps(val, sort_keys=sort_keys, indent=bool(indent), ensure_ascii=True,
                      default=_unknown_handler)


def loads(data):
    """Parse `data` as JSON and return Python data."""
    return json.loads(data)


def htmlsafe_json_dumps(obj, **kwargs):
    """Use `jinja2.utils.htmlsafe_json_dumps` with our dumper."""
    import jinja2.utils
    return jinja2.utils.htmlsafe_json_dumps(obj, dumper=dumps, **kwargs)
