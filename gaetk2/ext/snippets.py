#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2.ext.snippets - editable parts of webpages

Created by Maximillian Dornseif on 2014-11-22.
Copyright (c) 2014, 2017, 2018 Maximillian Dornseif. All rights reserved.
"""

from __future__ import unicode_literals

import cgi
import logging
import os
import random
import re
import unicodedata

from google.appengine.api import memcache, users
from google.appengine.ext import ndb

import jinja2
import markdown2

from gaetk2 import exc
from gaetk2.handlers import AuthenticatedHandler
from gaetk2.jinja_filters import cssencode
from gaetk2.tools import http
from gaetk2.tools.sentry import sentry_client


class gaetk_Snippet(ndb.Model):
    """Encodes a small pice of text for a jinja2 template."""
    name = ndb.StringProperty()
    markdown = ndb.TextProperty()
    path_info = ndb.StringProperty(default='')
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)


_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')


def _slugify(value):
    """"Legacy: slightly different from gaetk2.tools.unicode.slugify."""
    if value is None:
        return ''
    value = unicodedata.normalize('NFKD', unicode(value)).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)


@jinja2.contextfunction
def show_snippet(ctx, name, default=''):
    """Render a snippet inside a jinja2 template."""
    env = ctx.environment  # see http://jinja.pocoo.org/docs/2.10/api/#jinja2.runtime.Context
    db_name = _slugify(name.replace(' ', ''))
    url_name = http.quote(db_name)
    css_name = cssencode(db_name)
    path_info = os.environ.get('PATH_INFO', '?').decode('utf-8', 'replace')

    # display edit-button to admin users
    edit = ''
    if users.is_current_user_admin():
        edit = '''<div
            id="{css_name}"
            style="float:right"
        ><a
            href="/admin2/snippet/edit/?id={url_name}#edit&continue_url={path_info}#{css_name}"
            class="snippet_edit_button"
            id="snippet_{css_name}_button"
        ><i class="fa fa-pencil-square-o">
        </i></a></div>
        <script>
            $("#snippet_{css_name}_button").mouseover(function() {{
                $(this).parents(".snippetenvelope").effect("highlight")
            }})
        </script>
    '''.format(name=name, css_name=css_name, url_name=url_name, path_info=path_info)

    content = memcache.get('gaetk_snippet2:%s:rendered' % db_name)
    if random.random() < 0.01 or content is None:
        snippet = gaetk_Snippet.get_by_id(db_name)
        if not snippet:
            logging.info('generating snippet %s', db_name)
            snippet = gaetk_Snippet(id=db_name, name=db_name, markdown=default)
            snippet.put()

        if snippet.path_info is None or not path_info.startswith(snippet.path_info.encode('utf-8', 'ignore')):
            # with 1% chance we overwrite the existing path
            if not snippet.path_info or random.random() < 0.01:
                snippet.path_info = path_info
                snippet.put()

        # generate snippet
        if content is None:
            try:
                content = render(name, env, snippet.markdown)
            except Exception as exception:
                sentry_client.captureException()
                logging.exception('Fehler beim Rendern des Snippet %s: %s', snippet.key.id(), exception)
                ret = 'Fehler!<!-- Rendering error: %s -->%s' % (cgi.escape(str(exception)), edit)
                return jinja2.Markup(ret)

    assert content is not None
    return jinja2.Markup('''<div
            class="snippetenvelope"
            id="snippet_{css_name}_envelop"
            data-snippet="{name}">{edit}<div
            class="snippet" id="snippet_{css_name}">{content}
        </div></div>'''.format(
        css_name=css_name, name=name, edit=edit, content=content))


def render(name, env, markdown):
    """Snippet mit Jinja2 rendern und in memcache speichern"""
    template = env.from_string(markdown2.markdown(markdown))
    content = template.render({})
    if not memcache.set('gaetk_snippet2:%s:rendered' % name, content, 600):
        logging.error('Memcache set failed.')
    return content


class SnippetEditHandler(AuthenticatedHandler):
    """Allow a admin-user to change a snippet."""

    def authchecker(self, *args, **kwargs):
        """Only admin-users may edit a snippet"""
        self.login_required()
        if not self.is_admin():
            raise exc.HTTP403_Forbidden('Access denied!')

    def get(self):
        name = self.request.get('id')
        if not name:
            raise exc.HTTP404_NotFound
        snippet = gaetk_Snippet.get_by_id(id=name)
        continue_url = self.request.get('continue_url', '')
        self.render(
            dict(title='Edit %s' % name, name=name, snippet=snippet, continue_url=continue_url),
            'gaetk_snippet_edit.html')

    def post(self):
        name = self.request.get('name')
        markdown = self.request.get('sniptext', '')
        continue_url = self.request.get('continue_url', '')
        try:
            env = self.get_jinja2env()
            render(name, env, markdown)
        except Exception as exception:
            logging.exception('Fehler beim Rendern des Snippet: %s', exception)
            self.add_message('error', 'Fehler: %s' % exception)
            raise exc.HTTP303_SeeOther(location=self.request.referer)

        snippet = gaetk_Snippet.get_or_insert(name, name=name, path_info='')
        snippet.markdown = markdown
        snippet.put()

        if continue_url:
            location = continue_url
        elif snippet.path_info:
            location = snippet.path_info
        else:
            location = '/admin/'
        raise exc.HTTP303_SeeOther(location=location)
