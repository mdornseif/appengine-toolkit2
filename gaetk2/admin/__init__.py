#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.admin

Created by Christian Klein on 2011-08-19.
Copyright (c) 2011, 2017 HUDORA GmbH. MIT Licensed.
"""
import logging
import os
import sys

from . import modeladmin
from . import util


class _AdminSite(object):
    """Regestry for Models and other Stuff to be administered via Web GUI.

    Cenceptually Our Grandparent - Django Admin - Lives in a world of
    "Applications" out of which your Django Installation is composed.

    GAETK2 does not follow this approach very much. We assum each
    Model/Kind Name is unique in the whole deployed Web-Application and don't use
    djangos term "application" to avoid confusion. We speak of "Topics" whose
    sole purpose is to organize contant in the admin interface.
    """

    def __init__(self):
        """Konstruktor."""
        self._adminbykind = {}
        self._adminbytopic = {}
        self._modelbykind = {}

    def registermodel(self, model_class, admin_class=None, topic=None):
        """Registers the given model with the given admin class."""

        kind = model_class._get_kind()
        if kind in self._modelbykind:
            logging.warn(u'The model %s is already registered', kind)

        if topic is None:
            topic = util.get_topic_name(kind)

        if admin_class is None:
            admin_class = modeladmin.ModelAdmin

        # Instantiate the admin class to save in the registry
        admininstance = admin_class(model_class, self, topic=topic)
        self._modelbykind[kind] = model_class
        self._adminbykind[kind] = admininstance
        self._adminbytopic[topic] = admininstance

    def kinds(self):
        return self._adminbykind.keys()
    def get_admin_by_kind(self, kind):
        return self._adminbykind[kind]

    def get_model_by_kind(self, kind):
        return self._modelbykind[kind]

    def get_model_class(self, application, model):
        """Klasse zu 'model' zurückgeben."""

        for model_class in self._registry:
            if model == model_class._get_kind() and application == util.get_app_name(model_class._get_kind()):
                return model_class
            else:
                logging.error(
                    "wrong application: %s, %s, %s, %s",
                    application, model,
                    util.get_app_name(model_class._get_kind()),
                    model_class)


logger = logging.getLogger(__name__)
# The global AdminSite instance
site = _AdminSite()


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
