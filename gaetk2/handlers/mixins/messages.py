#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/handlers/mixins.py - misc functionality to be added to gaetk handlers.

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2010-2017 HUDORA. MIT licensed.
"""
import time

import jinja2


class MessagesMixin(object):
    """MessagesMixin provides the possibility to send messages to the user.

    Like Push-Notifications without the pushing.
    """

    def add_message(self, typ, text, ttl=15):
        """Sets a user specified message to be displayed to the currently logged in user.

        `typ` can be `error`, `success`, `info` or `warning`
        `text` is the text do be displayed
        `ttl` is the number of seconds after we should stop serving the message.

        If you want to pass in HTML, you need to use `jinja2.Markup([string]).`"""
        html = jinja2.escape(text)
        self._expire_messages()
        messages = self.session.get('_gaetk_messages', [])
        messages.append(dict(type=typ, html=html, expires=time.time() + ttl))
        # We can't use `.append()` because this doesn't result in automatic session saving.
        self.session['_gaetk_messages'] = messages

    def build_context(self, uservalues):
        u"""Default variablen für Breadcrumbs etc."""
        myvalues = dict(_gaetk_messages=self.session.get('_gaetk_messages', []))
        myvalues.update(uservalues)
        self._expire_messages()
        return myvalues

    def _expire_messages(self):
        """Remove Messages already displayed."""
        new = []
        for message in self.session.get('_gaetk_messages', []):
            if message.get('expires', 0) > time.time():
                new.append(message)
        if len(new) != len(self.session.get('_gaetk_messages', [])):
            self.session['_gaetk_messages'] = new
