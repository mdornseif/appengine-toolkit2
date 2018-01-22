#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.admin.sitemodel

Created by Christian Klein on 2018-01-19.
Copyright (c) 2018 HUDORA GmbH. MIT Licensed.
"""
import logging

from . import layout
from . import modeladmin
from . import util


logger = logging.getLogger(__name__)


class AdminSite(object):
    """Registry for Models and other Stuff to be administered via Web GUI.

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
        self._layoutbytopic = {}

    def registerlayoutclass(self, layout_class, topic=None):
        if topic is None:
            topic = _get_topic_name(layout_class)
        self._layoutbytopic[topic] = layout_class

    def registermodel(self, model_class, admin_class=None, topic=None):
        """Registers the given model with the given admin class."""

        if admin_class is None:
            admin_class = modeladmin.ModelAdmin
        if topic is None:
            topic = _get_topic_name(model_class)
        # Instantiate the admin class to save in the registry
        admininstance = admin_class(model_class, self, topic=topic)

        if admininstance.kind in self._modelbykind:
            logger.warn(u'The model %s is already registered', admininstance.kind)

        self._modelbykind[admininstance.kind] = model_class
        self._adminbykind[admininstance.kind] = admininstance
        self._adminbytopic.setdefault(topic, []).append(admininstance)

    def topics(self):
        alltopics = set(self._adminbytopic.keys() + self._layoutbytopic.keys())
        # ensure we have a layout for every topic
        for topic in alltopics:
            if topic not in self._layoutbytopic:
                self._layoutbytopic[topic] = layout.AdminLayout
        return alltopics

    def get_layout_by_topic(self, topic):
        self.topics()  # To ensure default-values are set
        return self._layoutbytopic.get(topic)

    def get_admin_by_topic(self, topic):
        return self._adminbytopic.get(topic, [])

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
                logger.error(
                    "wrong application: %s, %s, %s, %s",
                    application, model,
                    util.get_app_name(model_class._get_kind()),
                    model_class)


def _get_topic_name(klass):
    """Try to extract the Name of an Admin Topic from the path.

    Still somewhat like Django App-Names.

    >>> get_app_name('frontend.news.models.NewsItem')
    'news'
    >>> get_app_name('common.models.Sparepart')
    'Sparepart'
    """
    if not hasattr(klass, '__module__'):
        return u''
    components = klass.__module__.split('.')
    logging.debug('components=%r', components)
    if len(components) > 3:
        return components[-3]
    elif len(components) > 2:
        return components[-2]
    else:
        return components[-1]


# The global AdminSite instance
site = AdminSite()
