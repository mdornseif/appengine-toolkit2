#!/usr/bin/env python
# encoding: utf-8
"""
helpers.py - smal view-helper-functions

Created by Maximillian Dornseif on 2016-12-15.
Copyright (c) 2016 Cyberlogi. All rights reserved.
"""


from .exc import HTTP404_NotFound


def check404(obj, message='Object not found.'):
    """Raises 404 if ``bool(obj)`` is ``False``.

    The major usecase is to replace::

        def post(self, kundennr):
            kunde = m_api.get_kunde(kundennr)
            if not kunde:
                raise HTTP404_NotFound
            do_some_work()

    with::

        def post(self, kundennr):
            kunde = check404(m_api.get_kunde(kundennr))
            do_some_work()

    This has the potential to make view-Functions much more readable.
    """
    if not obj:
        raise HTTP404_NotFound(message)
    return obj
