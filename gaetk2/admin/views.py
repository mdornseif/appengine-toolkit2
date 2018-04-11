#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2.admin.views - administrationsinterface - inspieriert von Django.

Created by Christian Klein on 2011-08-10.
Copyright (c) 2011, 2013-2015, 2017-2018 HUDORA GmbH. MIT Licensed.
"""
from __future__ import unicode_literals

import logging

from google.appengine.api import app_identity

# from gaetk2.admin import search
# from gaetk2.admin.models import DeletedObject
import gaetk2.admin

from gaetk2.admin import autodiscover
from gaetk2.application import Route, WSGIApplication
from gaetk2.ext import snippets
from gaetk2.helpers import check404

from .. import exc
from ..handlers import AuthenticatedHandler
from ..handlers.mixins.paginate import PaginateMixin


# import gaetk.handler
# import gaetk.snippets


logger = logging.getLogger(__name__)


class _AbstractAdminHandler(AuthenticatedHandler):
    pass
    # todo: ensure is_Staff
    # values.update(
    #     request=self.request,
    #     now=datetime.datetime.now(),
    #     kw=datetime.date.today().isocalendar()[1],
    #     is_admin=self.is_admin())

    # if self.credential:
    #     values['permissions'] = self.credential.permissions
    # # if hasattr(config, 'PROJECTNAME'):
    # #     values['projectname'] = config.PROJECTNAME


class AdminIndexHandler(_AbstractAdminHandler):
    """Übersichtsseite aller registrierter Models sortiert nach Applikationen"""

    def get(self):
        """Zeige Template mit allen registrierten Models an"""

        apps = {}
        for kind in gaetk2.admin.site.kinds():
            modeladm = gaetk2.admin.site.get_admin_by_kind(kind)
            apps.setdefault(modeladm.topic, []).append(kind)

        topics = {}
        for topic in gaetk2.admin.site.topics():
            topics.setdefault(topic, {})['layout'] = gaetk2.admin.site.get_layout_by_topic(topic)
            topics.setdefault(topic, {})['modeladmins'] = gaetk2.admin.site.get_admin_by_topic(topic)

        logger.debug('topics=%r', topics)
        self.render({
            'apps': apps,
            'topics': topics,
            'default_version_hostname': app_identity.get_default_version_hostname(),
            'default_gcs_bucket_name': app_identity.get_default_gcs_bucket_name(),
            'application_id': app_identity.get_application_id(),
        }, 'admin2/index.html')


class AdminListHandler(_AbstractAdminHandler, PaginateMixin):
    """Übersichtsseite eines Models mit Liste aller Entities"""

    def get(self, kind):

        admin_class = check404(gaetk2.admin.site.get_admin_by_kind(kind))
        model_class = check404(gaetk2.admin.site.get_model_by_kind(kind))

        # unsupported: Link-Fields (oder wie das heißt)
        # unsupported: callables in List_fields
        query = admin_class.get_queryset(self.request)
        template_values = self.paginate(
            query,
            defaultcount=admin_class.list_per_page,
            datanodename='object_list',
            calctotal=False)
        template_values.update(
            qtype=self.request.get('qtype'),
            admin_class=admin_class,
            model_class=model_class)
        self.render(template_values, 'admin2/list.html')


class AdminExportXLSHandler(_AbstractAdminHandler):
    """Detailseite zu einer Entity"""

    def get(self, kind, action_or_objectid):
        """Handler, der die richtige Methode für die Aktion aufruft"""

        admin_class = check404(gaetk2.admin.site.get_admin_by_kind(kind))
        admin_class.export_view_xls(self)


class AdminExportCSVHandler(_AbstractAdminHandler):
    """Detailseite zu einer Entity"""

    def get(self, kind, action_or_objectid):
        """Handler, der die richtige Methode für die Aktion aufruft"""

        admin_class = check404(gaetk2.admin.site.get_admin_by_kind(kind))
        admin_class.export_view_csv(self)


class AdminSearchHandler(_AbstractAdminHandler):
    """Suche im Volltextsuchindex des Administrationsinterfaces"""
    pass
    # def get(self, model):
    #     """Erwartet den Parameter `q`"""

    #     model_class = site.get_model_class(application, model)
    #     if not model_class:
    #         raise gaetk.handler.HTTP404_NotFound('No model %s' % ('%s.%s' % (application, model)))

    #     pagesize = 40
    #     term = self.request.get('q')

    #     limit = self.request.get_range('limit', default=40, min_value=10)
    #     offset = self.request.get_range('offset', default=0, min_value=0)
    #     # hits, total = search.fsearch(term, model, limit=limit, offset=offset)

    #     self.render(dict(app=application,
    #                      model=model,
    #                      model_class=model_class,
    #                      hits=hits,
    #                      total=total,
    #                      term=term,
    #                      page=offset // pagesize,
    #                      pagesize=pagesize),
    #                 'admin2/search.html')


class AdminDetailHandler(_AbstractAdminHandler):
    """Detailseite zu einer Entity"""

    def get(self, kind, objectid):
        """Handler, der die richtige Methode für die Aktion aufruft"""

        admin_class = check404(gaetk2.admin.site.get_admin_by_kind(kind))
        obj = check404(admin_class.get_object(objectid))
        self.render({'obj': obj, 'admin_class': admin_class}, 'admin2/detail.html')


class AdminChangeHandler(_AbstractAdminHandler):
    """Detailseite zu einer Entity"""

    def get(self, kind, action_or_objectid):
        """Handler, der die richtige Methode für die Aktion aufruft"""

        admin_class = check404(gaetk2.admin.site.get_admin_by_kind(kind))
        # Bestimme Route! Da könnte man dann auch einen Handler mit angeben.
        # Das muss irgendwie besser gehen als Keys und Actions zu mischen.
        if action_or_objectid == 'add':
            if admin_class.read_only:
                raise exc.HTTP403_Forbidden
            admin_class.add_view(self)
        elif action_or_objectid == 'delete':
            if admin_class.read_only:
                raise exc.HTTP403_Forbidden
            elif not admin_class.deletable:
                raise exc.HTTP403_Forbidden
            else:
                admin_class.delete_view(self)
        else:
            if admin_class.read_only:
                raise exc.HTTP403_Forbidden
            # TODO: view only is missing
            admin_class.change_view(self, action_or_objectid,
                                    extra_context=dict(app=application))  # model=model


# class AdminUndeleteHandler(AdminHandler):
#     """Daten, die gelöscht wurden, wieder herstellen."""

#     def get(self, key):
#         """Objekt mit <key> wiederherstellen."""
#         archived = DeletedObject.get(key)
#         if archived.dblayer == 'ndb':
#             entity = ndb.ModelAdapter().pb_to_entity(entity_pb.EntityProto(archived.data))
#         else:
#             # precondition: model class must be imported
#             entity = db.model_from_protobuf(entity_pb.EntityProto(archived.data))
#         entity.put()
#         archived.delete()
#         self.add_message(
#             'success',
#             u'Objekt <strong><A href="/admin/%s/%s/%s/">%s</a></strong> wurde wieder hergestellt.' % (
#                 get_app_name(entity.__class__), entity.__class__.__name__, entity.key(), entity))
#         raise gaetk.handler.HTTP301_Moved(location='/admin/%s/%s/' % (
#             get_app_name(entity.__class__), entity.__class__.__name__))


autodiscover()
application = WSGIApplication(([
    # (r'^/admin2/_undelete/(.+)', AdminUndeleteHandler),
    Route('/admin2/', AdminIndexHandler),
    Route('/admin2/q/<kind>/', AdminListHandler),
    Route('/admin2/q/<kind>/export_xls/', AdminExportXLSHandler),
    Route('/admin2/q/<kind>/export_csv/', AdminExportCSVHandler),
    Route('/admin2/q/<kind>/search/', AdminSearchHandler),
    Route('/admin2/e/<kind>/<objectid>/', AdminDetailHandler),
    Route('/admin2/snippet/edit/', snippets.SnippetEditHandler),
    # Route('/admin2/e/<kind>/<action_or_objectid>/', AdminChangeHandler),
]))
