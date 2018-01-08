#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.handlers.mixins.paginate - Paginate NDB Queries.

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2010-2018 HUDORA. MIT licensed.
"""

import urllib

from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb


class PaginateMixin(object):
    """Show data in a paginated fashion.

    Call :meth:`paginate` in your Request-Method handler.

    Example:
        Build a view function like this::

            from ..handlers import AuthenticatedHandler
            from ..handlers.mixins import PaginateMixin

            class MyView(AuthenticatedHandler, PaginateMixin):
                def get(self):
                    query = MyModel.query().order('-created_at)
                    template_values = self.paginate(query)
                    self.render(template_values, 'template.html')

        Your ``template.html`` could look like this::

            <ul>
              {% for obj in object_list %}
                <li>{{ obj }}</li>
              {% endfor %}
            </ul>

            {{ paginator }}

        The ``{{ paginator }}`` expression renders a Bootstrap 4 Paginator object.
        If you dont want that you can add your own links::

            {% if prev_objects %}
              <a href="?{{ prev_qs }}">&larr; Prev</a>
            {% endif %}
            {% if more_objects %}
              <a href="?{{ next_qs }}">Next &rarr;</a>
            {% endif %}


    """

    def paginate(self, query, defaultcount=25, datanodename='objects', calctotal=False, formatter=None):
        """Add NDB-based pagination to Views.

        Provides a template environment by calling ``self.paginate()``.

        Parameters:
            query: a ndb query object
            defaultcount (int): how many items to display per page
            datanodename (string): name of template variable to hold the entties
            calctotal (boolean): do you want to provide the total number of entities
            formatter: function to transform entities for output.

        `formatter` is called for each object and can transform it into something suitable.
        If no `formatter` is given and objects have a `as_dict()` method, this is used
        for formating.

        if `calctotal == True` then the total number of matching rows is given as an integer value. This
        is a ecpensive operation on the AppEngine and results might be capped at 1000.

        `datanodename` is the key in the returned dict, where the Objects resulting form the query resides.

        `defaultcount` is the default number of results returned. It can be overwritten with the
        HTTP-parameter `limit`.

        We handle the additional query parameters ``start``, ``cursor``,
        ``cursor_start`` from the HTTP-Request to note what is currently displayed.
        ``limit`` can be used to overwrite ``defaultcount``.

        The `start` HTTP-parameter can skip records at the beginning of the result set.

        If the `cursor` HTTP-parameter is given we assume this is a cursor returned from an earlier query.

        Returns:
            A dict like this to be used in the template::

                {more_objects=True, prev_objects=True,
                 prev_start=10, next_start=30, limit=10, total=None,
                 objects=[...], cursor='ABCDQWERY',
                 prev_qs='?start=10', next_qs='?start=30&cursor=ABCDQWERY',
                 paginator='<html ...>'
                }

        `paginator` is generated by rendering `gaetk_fragments/PaginateMixin.paginator.html`
        with the other return values. You can overwrite the output by
        providing your own `gaetk_fragments/PaginateMixin.paginator.html`
        in your search path.

        See Also:
            http://mdornseif.github.com/2010/10/02/appengine-paginierung.html

            http://blog.notdot.net/2010/02/New-features-in-1-3-1-prerelease-Cursors

            http://code.google.com/appengine/docs/python/datastore/queryclass.html#Query_cursor

        Note:
            Somewhat obsoleted by `listviewer`.
        """
        if calctotal:
            # We count up to maximum of 10000. Counting is a somewhat expensive
            # operation on AppEngine doing thhis asyncrounously would be smart
            total = query.count(10000)  # has to happen before `_paginate_query()`!

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
        ret['paginator'] = self.get_paginator_template(ret)
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

    def get_paginator_template(self, values):
        env = self._create_jinja2env()
        template = env.get_template('gaetk_fragments/PaginateMixin.paginator.html')
        values = self._reduce_all_inherited('build_context', values)
        return template.render(values)


def _xdb_fetch_page(query, limit, offset=None, start_cursor=None):
    """Pagination-ready fetching a some entities.

    Returns:
        (objects, cursor, more_objects)
    """
    if start_cursor:
        if isinstance(start_cursor, basestring):
            start_cursor = Cursor(urlsafe=start_cursor)
        return query.fetch_page(limit, start_cursor=start_cursor)
    else:
        return query.fetch_page(limit, offset=offset)
