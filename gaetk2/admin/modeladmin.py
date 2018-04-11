#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2.admin.modeladmin

Created by Christian Klein on 2011-08-22.
Copyright (c) 2011, 2014, 2017 HUDORA GmbH. All rights reserved.
"""
from __future__ import unicode_literals

import cgi
import collections
import datetime
import logging

from google.appengine.ext import db, deferred, ndb
from wtforms_appengine.db import model_form

import wtforms

from . import util
from .. import exc, modelexporter


# from gaetk.admin.models import DeletedObject


logger = logging.getLogger(__name__)


class ModelAdmin(object):
    """Admin Model - Implements CRUD for NDB"""

    read_only = True
    """User is not allowed to do any changes to the database for this Models Entities."""
    deletable = False
    """User is allowed to delete Entities via the admin interface."""

    list_fields = ()
    """Names of fields to show in Entity listing.

    If you do not want to show all the files you can give a tuple
    of fields to show::

        list_fields = ('designator', 'name', 'plz', 'ort', 'email')

    TBD: relation to fields / only.
    """
    list_per_page = 50
    """Number of items per page."""

    queries = {}
    """TBD"""

    detail_fields = ()
    """TBD"""

    order_field = '-created_at'
    """Sorting. Beware of datastore indices!"""
    ordering = ''
    """TBD Mit 'order_field' laesst sich die Sortierung bei der Anzeige der Model-Instanzen
    im Admin-Bereich anpassen. Als Default werden die Datensaetze in absteigender
    Reihenfolge ihrer Erzeugung sortiert, jedoch kann jede Admin-Klasse die Sortierung
    mit 'order_field' beeinflussen, indem sie ein bel. anderes Feld dort angibt.
    """

    post_create_hooks = []
    """List of functions to be called with the newly created object
    as the sole parameter."""

    db_key_field = None
    """Standardmaessig lassen wir die App Engine fuer das Model automatisch einen
    Key generieren. Es besteht jedoch in der Admin-Klasse die Moeglichkeit, via
    'db_key_field=[propertyname]' ein Feld festzulegen, dessen Inhalt im Formular
    als Key beim Erzeugen der Instanz genutzt wird."""

    raw_id_fields = ()

    fields = None
    exclude = None

    prepopulated_fields = {}

    blob_upload_fields = []

    # Wird dem Field beim Rendern übergeben
    # (ist das erste eigene Attribut)
    field_args = {}

    # Actions, bisher nicht implementiert.
    actions = []

    topic = None
    """The Topic (Application Name in Django) under which the Model is listed in the admin GUI."""

    def __init__(self, model, admin_site, topic=None):
        self.model = model
        self.topic = topic
        self.admin_site = admin_site

        if not self.queries:
            self.queries = {'': self.model.query()}

        if not self.list_fields:
            self.list_fields = self.model._properties.keys()

        if not self.detail_fields:
            self.detail_fields = self.model._properties.keys()

    @property
    def kind(self):
        return self.model._get_kind()

    @property
    def name(self):
        return self.kind

    @property
    def url(self):
        return '/admin2/e/{}/' % self.kind

    def get_ordering(self, request):
        """Return the sort order attribute"""
        order_field = request.get('o')
        direction = request.get('ot', 'asc')

        if not order_field and self.ordering:
            if self.ordering.startswith('-'):
                direction = 'desc'
                order_field = self.ordering[1:]
            elif self.ordering.startswith('+'):
                direction = 'asc'
                order_field = self.ordering[1:]
            else:
                order_field = self.ordering
                direction = 'asc'

        if not order_field:
            return

        return order_field, '-' if direction == 'desc' else '+'

    def get_queryset(self, request):
        """Gib das QuerySet für die Admin-Seite zurück

        Es wird die gewünschte Sortierung durchgeführt.
        """
        ordering = self.get_ordering(request)
        qname = request.get('qtype', '')
        if qname in self.queries:
            query = self.queries[qname]
        else:
            # fallback
            query = self.model.query()
        if ordering:
            attr, direction = ordering
            prop = self.model._properties.get(attr)
            if prop:
                if direction == '-':
                    return query.order(-prop)
                else:
                    return query.order(prop)
        return query

    def get_form(self, **kwargs):
        """Erzeuge Formularklasse für das Model"""

        # Erstmal nur das Form zurückgeben.
        # Soll sich doch jeder selbst um 'only' und 'exclude' kümmern,
        # bei model_form gehen aber leider alle Labels und Descriptions verloren.
        if hasattr(self, 'form'):
            return getattr(self, 'form')

        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)

        defaults = {
            'base_class': self.form,
            'only': self.fields,
            'exclude': (exclude + kwargs.get('exclude', [])) or None,
        }

        klass = model_form(self.model, **defaults)

        # label könnte man noch setzbar machen
        for blob_upload_field in self.blob_upload_fields:
            field = wtforms.FileField()
            setattr(klass, blob_upload_field, field)

        return klass

    def get_object(self, encoded_key):
        """Ermittle die Instanz über den gegeben ID"""
        key = ndb.Key(urlsafe=encoded_key)
        return key.get()

    def handle_blobstore_fields(self, handler, obj, key_name):
        """Upload für Blobs"""
        # Falls das Feld vom Typ cgi.FieldStorage ist, wurde eine Datei zum Upload übergeben
        for blob_upload_field in self.blob_upload_fields:
            blob = handler.request.params.get(blob_upload_field)
            if blob.__class__ == cgi.FieldStorage:
                blob_key = util.upload_to_blobstore(obj, key_name, blob)
                setattr(obj, blob_upload_field, blob_key)

    def change_view(self, handler, object_id, extra_context=None):
        """View zum Bearbeiten eines vorhandenen Objekts"""

        obj = self.get_object(object_id)
        if obj is None:
            raise exc.HTTP404_NotFound

        model_class = type(obj)
        form_class = self.get_form()

        if handler.request.get('delete') == 'yesiwant':
            # Der User hat gebeten, dieses Objekt zu löschen.
            # key = obj.key
            # data = ndb.ModelAdapter().entity_to_pb(obj).Encode()
            # archived = DeletedObject(key_name=str(key), model_class=model_class.__name__,
            #                          old_key=str(key), dblayer='ndb', data=data)
            # archived.put()
            # # Indexierung für Admin-Volltextsuche
            # # from gaetk.admin.search import remove_from_index
            # obj.key.delete()

            # handler.add_message(
            #     'warning',
            #     u'<strong>{} {}</strong> wurde gelöscht. <a href="{}">Objekt wiederherstellen!</a>'.format(
            #         self.model._get_kind(), key.id(), archived.undelete_url()))
            raise exc.HTTP302_Found(location='/admin/%s/%s/' % (
                util.get_app_name(model_class), model_class._get_kind()))

        # Wenn das Formular abgeschickt wurde und gültig ist,
        # speichere das veränderte Objekt und leite auf die Übersichtsseite um.
        if handler.request.method == 'POST':
            form = form_class(handler.request.POST)
            if form.validate():
                key_name = obj.key.id()
                self.handle_blobstore_fields(handler, obj, key_name)
                if hasattr(obj, 'update'):
                    obj.update(form.data)
                else:
                    form.populate_obj(obj)
                key = obj.put()
                handler.add_message(
                    'success',
                    '<strong><a href="/admin/{}/{}/{}/">{} {}</a></strong> wurde gespeichert.'.format(
                        util.get_app_name(self.model),
                        self.model._get_kind(),
                        key.urlsafe(),
                        self.model._get_kind(),
                        key.id()))

                # Indexierung für Admin-Volltextsuche
                from gaetk.admin.search import add_to_index
                deferred.defer(add_to_index, key)
                raise exc.HTTP302_Found(location='/admin/%s/%s/' % (
                    util.get_app_name(model_class), model_class._get_kind()))
        else:
            form = form_class(obj=obj)

        template_values = {'object': obj, 'form': form, 'field_args': self.field_args, 'admin_class': self}
        if extra_context is not None:
            template_values.update(extra_context)
        handler.render(template_values, self.get_template('change'))

    def add_view(self, handler, extra_context=None):
        """View zum Hinzufügen eines neuen Objekts"""
        form_class = self.get_form()

        # Standardmaessig lassen wir die App Engine fuer das Model automatisch einen
        # Key generieren. Es besteht jedoch in der Admin-Klasse die Moeglichkeit, via
        # 'db_key_field=[propertyname]' ein Feld festzulegen, dessen Inhalt im Formular
        # als Key beim Erzeugen der Instanz genutzt wird.
        from . import sitemodel  # cyclic import :-(
        admin_class = sitemodel.site.get_admin_class(self.model)
        key_field = None
        if admin_class and hasattr(admin_class, 'db_key_field'):
            key_field = admin_class.db_key_field

        # Wenn das Formular abgeschickt wurde und gültig ist,
        # speichere das veränderte Objekt und leite auf die Übersichtsseite um.
        if handler.request.method == 'POST':
            form = form_class(handler.request.POST)

            if form.validate():
                form_data = self._convert_property_data(form.data)
                key_name = form_data.get(key_field) if key_field else None

                # TODO: util.create_instance nutzen oder entfernen
                if hasattr(self.model, 'create'):
                    factory = self.model.create
                else:
                    factory = self.model

                if issubclass(self.model, ndb.Model):
                    obj = factory(id=key_name, **form_data)
                else:
                    obj = factory(key_name=key_name, **form_data)

                # Beim Anlegen muss dann halt einmal gespeichert werden,
                # ansonsten ist der ID unbekannt.
                if self.blob_upload_fields and key_name is None:
                    obj.put()
                    key_name = obj.key.id()
                    self.handle_blobstore_fields(handler, obj, key_name)

                key = obj.put()
                handler.add_message(
                    'success',
                    '<strong><a href="/admin/{}/{}/{}/">{} {}</a></strong> wurde angelegt.'.format(
                        util.get_app_name(self.model),
                        self.model._get_kind(),
                        key.urlsafe(),
                        self.model._get_kind(),
                        key.id()))

                # Indexierung für Admin-Volltextsuche
                from gaetk.admin.search import add_to_index
                deferred.defer(add_to_index, key)

                # Call post-create-hooks
                if isinstance(self.post_create_hooks, collections.Iterable):
                    for hook in self.post_create_hooks:
                        deferred.defer(util.call_hook, hook, key.urlsafe())

                raise exc.HTTP302_Found(location='..')
        else:
            form = form_class()

        template_values = {'form': form, 'field_args': self.field_args, 'admin_class': self}
        if extra_context is not None:
            template_values.update(extra_context)
        handler.render(template_values, self.get_template('add'))

    def _convert_property_data(self, form_data):
        """Je nach Art der Model-Property muessen hier noch verschiedene Konvertierungen
           der rohen Eingaben aus dem Form durchgefuehrt werden, bevor sie ins Model geschrieben
           werden koennen."""
        # properties = self.model.properties()
        # for propname in form_data.keys():
        #     prop = properties.get(propname)

        #     bei StringListProperties muss die Eingabe der TextArea
        #     in eine Liste von Strings zerlegt werden
        #     if isinstance(prop, db.StringListProperty):
        #         form_data[propname] = form_data.get(propname, '').split('\n')

        return form_data

    def delete_view(self, handler, extra_context=None):  # pylint: disable=W0613
        """Request zum Löschen von (mehreren) Objekten behandeln.

        Redirectet bei Erfolg zur Objektliste.
        `extra_context` ist für die Signatur erforderlich, wird aber nicht genutzt.
        """
        if handler.request.method != 'POST':
            raise exc.HTTP400_BadRequest(
                'Falsche Request Methode für diesen Aufruf: %s' % handler.request.method)
        # Instanzen sammeln und dann gemeinsam löschen
        keys = []
        for object_id in handler.request.get_all('object_id'):
            obj = self.get_object(object_id)
            if obj is None:
                raise exc.HTTP404_NotFound('Keine Instanz zu ID %s gefunden.' % object_id)
            logger.info('Delete %s', object_id)
            if issubclass(self.model, ndb.Model):
                keys.append(ndb.Key(urlsafe=object_id))
            elif issubclass(self.model, db.Model):
                keys.append(db.Key(object_id))

        if issubclass(self.model, ndb.Model):
            ndb.delete_multi(keys)
        elif issubclass(self.model, db.Model):
            db.delete(keys)

        raise exc.HTTP302_Found(location='..')

    def export_view_csv(self, handler, extra_context=None):  # pylint: disable=W0613
        """Request zum Exportieren von allen Objekten behandeln.

        `extra_context` ist für die Signatur erforderlich, wird aber nicht genutzt.
        """
        # irgendwann werden wir hier einen longtask nutzen muessen
        exporter = modelexporter.ModelExporter(self.model)
        filename = '%s-%s.csv' % (self.model._get_kind(), datetime.datetime.now())
        handler.response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        handler.response.headers['content-disposition'] = \
            'attachment; filename=%s' % filename
        exporter.to_csv(handler.response)

    def export_view_xls(self, handler, extra_context=None):  # pylint: disable=W0613
        """Request zum Exportieren von allen Objekten behandeln.

        `extra_context` ist für die Signatur erforderlich, wird aber nicht genutzt.
        """
        exporter = modelexporter.ModelExporter(self.model)
        filename = '%s-%s.xls' % (self.model._get_kind(), datetime.datetime.now())
        handler.response.headers['Content-Type'] = 'application/msexcel'
        handler.response.headers['content-disposition'] = \
            'attachment; filename=%s' % filename
        exporter.to_xls(handler.response)

    def get_template(self, action):
        """Auswahl des zur `action` passenden templates."""

        # In Jinja2 kann man doch auch eine Liste mit Template-Pfaden zurückgeben.
        # Das wäre hier doch genau das richtige!

        if action == 'delete':
            pass

        attr = action + '_form_template'
        return getattr(self, attr, 'admin/detail.html')


# TODO: use structured_xls
class XlsWriter(object):
    """Compatible to the CSV module writer implementation."""
    def __init__(self):
        from xlwt import Workbook
        self.buff = []
        self.book = Workbook()
        self.sheet = self.book.add_sheet('Export')
        self.rownum = 0

    def writerow(self, row):
        """Write a row of Values."""
        col = 0
        for coldata in row:
            self.sheet.write(self.rownum, col, coldata)
            col += 1
        self.rownum += 1

    def save(self, fd):
        """Write the XLS to fd."""
        self.book.save(fd)
