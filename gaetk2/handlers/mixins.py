#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/handlers/mixins.py - misc functionality to be added to gaetk handlers.

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2010-2017 HUDORA. MIT licensed.
"""

import urllib

from functools import partial

from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import db
from google.appengine.ext import ndb

from ..tools.config import get_version
from ..tools.config import is_production


class BootstrapMixin(object):
    """Support for the supplied bootstrap templates."""

    def add_jinja2env_globals(self, env):
        """Set variables to be used in the supplied bootstrap templates."""
        sup = super(BootstrapMixin, self)
        if hasattr(sup, 'add_jinja2env_globals'):
            sup.add_jinja2env_globals(env)

        env.globals['ist_produktion'] = is_production()  # TODO: use `gaetk_production`
        env.globals['beta_banner'] = ''
        env.globals['release'] = get_version()
        if not is_production():
            # from https://codepen.io/eode9/pen/twkKm
            env.globals['beta_banner'] = (
                '<style>.corner-ribbon{z-index: 1001; width: 200px; background: #e43; position: absolute;'
                'top: 25px; left: -50px; text-align: center; line-height: 50px;'
                'letter-spacing: 1px; color: #f0f0f0; transform: rotate(-45deg);'
                '-webkit-transform: rotate(-45deg); }\n'
                '.corner-ribbon.sticky{ position: fixed; }\n'
                '.corner-ribbon.shadow{ box-shadow: 0 0 3px rgba(0,0,0,.3); }\n'
                '.corner-ribbon.bottom-right{ top: auto; right: -50px; bottom: 25px;'
                'left: auto; transform: rotate(-45deg); -webkit-transform: rotate(-45deg);}\n'
                '.corner-ribbon.red{background: #e43;}\n'
                '</style><div class="corner-ribbon bottom-right sticky red shadow">Development</div>')


class PaginateMixin(object):
    """Show data in a paginated fashion."""

    def paginate(self, query, defaultcount=25, datanodename='objects', calctotal=False, formatter=None):
        """Pagination. Somewhat obsoleted by `listviewer`.

        See http://mdornseif.github.com/2010/10/02/appengine-paginierung.html

        Returns something like
            {more_objects=True, prev_objects=True,
             prev_start=10, next_start=30,
             objects: [...], cursor='ABCDQWERY'}

        `formatter` is called for each object and can transfor it into something suitable.
        If no `formatter` is given and objects have a `as_dict()` method, this is used
        for formating.

        if `calctotal == True` then the total number of matching rows is given as an integer value. This
        is a ecpensive operation on the AppEngine and results might be capped at 1000.

        `datanodename` is the key in the returned dict, where the Objects resulting form the query resides.

        `defaultcount` is the default number of results returned. It can be overwritten with the
        HTTP-parameter `limit`.

        The `start` HTTP-parameter can skip records at the beginning of the result set.

        If the `cursor` HTTP-parameter is given we assume this is a cursor returned from an earlier query.
        See http://blog.notdot.net/2010/02/New-features-in-1-3-1-prerelease-Cursors and
        http://code.google.com/appengine/docs/python/datastore/queryclass.html#Query_cursor for
        further Information.
        """
        if calctotal:
            # We count up to maximum of 10000. Counting is a somewhat expensive operation on AppEngine
            # doing thhis asyncrounously would be smart
            total = query.count(10000)  # has to happen before `_paginate_query()`

        clean_qs = dict([(k, self.request.get(k)) for k in self.request.arguments()
                         if k not in ['start', 'cursor', 'cursor_start']])
        objects, cursor, start, ret = self._paginate_query(query, defaultcount)
        ret['total'] = None
        if calctotal:
            ret['total'] = total

        if ret['more_objects']:
            if cursor:
                ret['cursor'] = cursor.urlsafe()
                ret['cursor_start'] = start + ret['limit']
                # query string to get to the next page
                qs = dict(cursor=ret['cursor'], cursor_start=ret['cursor_start'])
                qs.update(clean_qs)
                ret['next_qs'] = urllib.urlencode(qs)
            else:
                qs = dict(start=ret['next_start'])
                qs.update(clean_qs)
                ret['next_qs'] = urllib.urlencode(qs)
        if ret['prev_objects']:
            # query string to get to the next previous page
            qs = dict(start=ret['prev_start'])
            qs.update(clean_qs)
            ret['prev_qs'] = urllib.urlencode(qs)
        if formatter:
            ret[datanodename] = [formatter(x) for x in objects]
        else:
            ret[datanodename] = []
            for obj in objects:
                ret[datanodename].append(obj)
        return ret

    def _paginate_query(self, query, defaultcount):
        """Help paginate to construct queries."""
        start_cursor = self.request.get('cursor', '')
        limit = self.request.get_range('limit', min_value=1, max_value=1000, default=defaultcount)
        if start_cursor:
            objects, cursor, more_objects = _xdb_fetch_page(
                query, limit, start_cursor=start_cursor)
            start = self.request.get_range('cursor_start', min_value=0, max_value=10000, default=0)
            prev_objects = True
        else:
            start = self.request.get_range('start', min_value=0, max_value=10000, default=0)
            objects, cursor, more_objects = _xdb_fetch_page(query, limit, offset=start)
            prev_objects = start > 0

        # TODO: catch google.appengine.api.datastore_errors.BadRequestError
        # retry without parameters

        prev_start = max(start - limit - 1, 0)
        next_start = max(start + len(objects), 0)

        ret = dict(more_objects=more_objects, prev_objects=prev_objects,
                   prev_start=prev_start, next_start=next_start,
                   limit=limit)
        return objects, cursor, start, ret


def _xdb_fetch_page(query, limit, offset=None, start_cursor=None):
    """Pagination-ready fetching a some entities in a cross plattform way (db and ndb)."""
    if isinstance(query, ndb.Query):
        if start_cursor:
            if isinstance(start_cursor, basestring):
                start_cursor = Cursor(urlsafe=start_cursor)
            objects, cursor, more_objects = query.fetch_page(limit, start_cursor=start_cursor)
        else:
            objects, cursor, more_objects = query.fetch_page(limit, offset=offset)
    elif isinstance(query, db.Query) or isinstance(query, db.GqlQuery):
        if start_cursor:
            if isinstance(start_cursor, Cursor):
                start_cursor = start_cursor.urlsafe()
            query.with_cursor(start_cursor)
            objects = query.fetch(limit)
            cursor = Cursor(urlsafe=query.cursor())
            more_objects = len(objects) == limit
        else:
            objects = query.fetch(limit, offset=offset)
            # MultiQuery kann keine Cursor
            if len(getattr(query, '_Query__query_sets', [])) < 2:
                _cursor = query.cursor()
                more_objects = query.with_cursor(_cursor).count(1) > 0
                cursor = Cursor(urlsafe=_cursor)
            else:
                more_objects = len(objects) == limit
                cursor = None
    else:
        raise RuntimeError('unknown query class: %s' % type(query))
    return objects, cursor, more_objects


class MultirenderMixin(object):
    """Multirender is meant to provide rendering for a variety of formats with minimal code.

    For the three major formats HTML, XML und JSON you can get away with virtually no code.
    """

    def multirender(self, fmt, data, mappers=None, contenttypes=None, filename='download',
                    defaultfmt='html', html_template='data', html_addon=None,
                    xml_root='data', xml_lists=None,
                    tabular_datanodename='objects'):
        r"""Send Data formated in different ways to the client.

        Some real-world view method might look like this:

            # URL matches '/empfaenger/([A-Za-z0-9_-]+)/rechnungen\.?(json|xml|html)?',
            def get(self, kundennr, fmt):
                query = models.Rechnung.all().filter('kundennr = ', kundennr)
                values = self.paginate(query, 25, datanodename='rechnungen')
                self.multirender(fmt, values,
                                 filename='rechnungen-%s' % kundennr,
                                 html_template='rechnungen.html',
                                 tabular_datanodename='rechnungen')

        `/empfaenger/12345/rechnungen` and `/empfaenger/12345/rechnungen.html` will result in
        `rechnungen.html` beeing rendered.
        `/empfaenger/12345/rechnungen.json` results in JSON being returned with a
        `Content-Disposition` header sending it to the file `rechnungen-12345.json`. Likewise for
        `/empfaenger/12345/rechnungen.xml`.
        If you add the Parameter `disposition=inline` no Content-Desposition header is generated.

        If you use fmt=json with a `callback` parameter, JSONP is generated. See
        http://en.wikipedia.org/wiki/JSONP#JSONP for details.

        If you give a dict in `html_addon` this dict is additionaly passed the the HTML rendering function
        (but not to the rendering functions of other formats).

        You can give the `xml_root` and `xml_lists` parameters to provide `huTools.structured.dict2xml()`
        with defenitions on how to name elements. See the documentation of `roottag` and `listnames` in
        dict2xml documentation.

        For tabular formats like XLS and CSV we assume that `data[tabular_datanodename]` contains
        a list of dicts to be rendered.

        For more sophisticated layout you can give customized mappers. Using functools.partial
        is very helpfiull for thiss. E.g.

            from functools import partial
            multirender(fmt, values,
                        mappers=dict(xml=partial(dict2xml, roottag='response',
                                                 listnames={'rechnungen': 'rechnung', 'odlines': 'odline'},
                                                  pretty=True),
                                     html=lambda x: '<body><head><title>%s</title></head></body>' % x))
        """
        # If no format is given, we assume HTML (or whatever is given in defaultfmt)
        # We also provide a list of convinient default content types and encodings.
        fmt = fmt or defaultfmt

        mapper = self._get_mapper(mappers, fmt, html_template, html_addon, xml_lists,
                                  data, xml_root, tabular_datanodename)
        contenttype = self._generate_content_headers(fmt, filename, contenttypes)
        # If we have gotten a `callback` parameter, we expect that this is a
        # [JSONP](http://en.wikipedia.org/wiki/JSONP#JSONP) can and therefore add the padding
        if self.request.get('callback', None) and fmt == 'json':
            self.response.headers['Content-Type'] = 'text/javascript'
            self.response.write("%s (%s)" % (self.request.get('callback', None), mapper(data)))
        else:
            self.response.headers['Content-Type'] = contenttype
            self.response.write(mapper(data))

    def _get_mapper(self, mappers, fmt, html_template, html_addon, xml_lists, data,
                    xml_root, tabular_datanodename):
        """Return the correct mapper for `fmt`."""
        # We lazy import huTools to keep gaetk usable without hutools
        import huTools.hujson
        import huTools.structured

        # Default mappers are there for XML and JSON (provided by huTools) and HTML provided by Jinja2
        # we provide a default dict2xml renderer based on the xml_* parameters given
        # The HTML Render integrates additional data via html_addon
        def htmlrender(_x):
            """Create HTML via jinja2."""
            htmldata = data.copy()
            if html_addon:
                htmldata.update(html_addon)
            return self.rendered(htmldata, html_template)

        mymappers = dict(
            xml=partial(huTools.structured.dict2xml, roottag=xml_root, listnames=xml_lists, pretty=True),
            json=huTools.hujson2.dumps,
            csv=partial(huTools.structured.dict2csv, datanodename=tabular_datanodename),
            xls=partial(huTools.structured.dict2xls, datanodename=tabular_datanodename),
            html=htmlrender)
        if mappers:
            mymappers.update(mappers)

        # Check early if we have no corospondending configuration to provide more meaningful error messages.
        if fmt not in mymappers:
            raise ValueError('No mapper for format "%r"' % fmt)
        return mymappers[fmt]

    def _generate_content_headers(self, fmt, filename, contenttypes):
        """Generate `Content-Disposition` and `Content-Type`headers."""
        mycontenttypes = dict(pdf='application/pdf',
                              xml="application/xml; encoding=utf-8",
                              json="application/json; encoding=utf-8",
                              html="text/html; encoding=utf-8",
                              csv="text/csv; encoding=utf-8",
                              xls="application/vnd.ms-excel",
                              invoic="application/edifact; encoding=iso-8859-1",
                              desadv="application/edifact; encoding=iso-8859-1")
        if contenttypes:
            mycontenttypes.update(contenttypes)

        # Disposition helps the browser to decide if something should be downloaded to disk or
        # if it should displayed in the browser window. It also can provide a filename.
        # per default we provide downloadable files
        if self.request.get('disposition') != 'inline':
            disposition = "attachment"
        else:
            disposition = "inline"

        if fmt not in ['html', 'json']:
            self.response.headers["Content-Disposition"] = str("%s; filename=%s.%s" % (
                disposition, filename, fmt))

        if fmt not in mycontenttypes:
            raise ValueError('No content-type for format "%s": %r' % (fmt, mycontenttypes))
        return mycontenttypes[fmt]
