#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.admin

Created by Christian Klein on 2011-08-19.
Copyright (c) 2011, 2017, 2018 HUDORA GmbH. MIT Licensed.
"""
import logging
import os
import sys

from . import modeladmin
from . import sitemodel

logger = logging.getLogger(__name__)
# The global AdminSite instance
site = sitemodel.site

__all__ = ['autodiscover', 'site', 'modeladmin']


def autodiscover(appsdirs=None):
    """
    Finde alle Admin-Klassen und registriere sie beim globalen Site-Objekt.
    """

    if appsdirs is None:
        appsdirs = ['modules']

    basedir = '.'
    for directory in appsdirs:
        root = os.path.join(basedir, directory)
        if not os.path.exists(root):
            continue
        for subdir in os.listdir(root):
            # Ignoriere alle Unterverzeichnisse, in der keine Datei 'admin.py' liegt.
            # Dabei spielt es keine Rolle, ob subdir wirklich ein Verzeichnis ist oder ob
            # es nur eine Datei ist.
            if not os.path.exists(os.path.join(root, subdir, 'admin_gaetk2.py')):
                continue

            module_name = '.'.join((directory, subdir, 'admin_gaetk2'))
            try:
                _import_module(module_name)
            except ImportError as error:
                logger.critical(u'Error while importing %s: %s', module_name, error)


def _import_module(name):
    """Import a module by name."""

    if name not in sys.modules:
        __import__(name)
    return sys.modules[name]
