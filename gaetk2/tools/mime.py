#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2.tools.mime - Content-Type helpers for gaetk2.

Created by Maximillian Dornseif on 2018-10-16.
Copyright (c) 2018 Maximillian Dornseif. MIT Licensed.
"""

from __future__ import unicode_literals

import logging


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.WARNING)


def magic(data):
    """Mime-Type anhand eines Datenstroms raten."""
    if data[0:2] == '\xff\xd8':  # JPEG Start of Image
        return 'image/jpeg', '.jpg'
    elif data[0:4] == '\x89PNG':
        return 'image/png', '.png'
    elif data[0:4] == '%PDF':
        return 'application/pdf', '.pdf'
    else:
        LOGGER.warn('Unknown magic value: %s', data[:10].encode('hex'))
    return 'binary/octet-stream', ''
