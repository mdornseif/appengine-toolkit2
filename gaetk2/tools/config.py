#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/tools/config.py - Legacy.

Created by Maximillian Dornseif on 2017-05-25.
Copyright (c) 2017, 2018 HUDORA. MIT licensed.
"""
import warnings

from ..config import (gaetkconfig, get_environment, get_release, get_revision, get_version, is_development,
                      is_production)

config = gaetkconfig
warnings.warn('use gaetk.config instead', DeprecationWarning, stacklevel=2)

__all__ = [
    'gaetkconfig',
    'config',
    'get_environment',
    'get_release',
    'get_revision',
    'get_version',
    'is_production',
    'is_development',
]
