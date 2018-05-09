#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2/tools/introspection.py

Created by Maximillian Dornseif on 2018-04-17.
MIT licensed.
"""

from __future__ import unicode_literals

import inspect


def get_class_that_defined_method(meth):
    """Find where a method is comming from."""
    try:
        return _get_class_that_defined_method2(meth)
    except AttributeError:
        return _get_class_that_defined_method3(meth)
    except:
        raise


def _get_class_that_defined_method2(meth):
    'https://stackoverflow.com/a/961057/49407'
    for cls in inspect.getmro(meth.im_class):
        if meth.__name__ in cls.__dict__:
            return cls
    return None


def _get_class_that_defined_method3(meth):
    'From https://stackoverflow.com/questions/3589311/get/25959545#25959545'
    if inspect.ismethod(meth):
        for cls in inspect.getmro(meth.__self__.__class__):
            if cls.__dict__.get(meth.__name__) is meth:
                return cls
        meth = meth.__func__  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)  # handle special descriptor objects
