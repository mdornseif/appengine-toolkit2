#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gaetk2.forms.__init__ - Use WTforms but with custom widgets

Created by Maximillian Dornseif on 2017-12-23.
Copyright (c) 2017. MIT Licensed.
"""

import logging

from gaetk2.forms import widgets3, widgets4

logger = logging.getLogger(__name__)
widget_mapping3 = {
    # Multi Types
    'SelectMultipleField': widgets3.Select(multiple=True),
    'SelectField': widgets3.Select(),
    'QuerySelectMultipleField': widgets3.Select(multiple=True),
    'QuerySelectField': widgets3.Select(),
    # 'RadioField': widgets.RadioGroup(),

    # Input Types
    'DateField': widgets3.DateInput(),
    'TextField': widgets3.TextInput(),
    'StringField': widgets3.TextInput(),
    'PasswordField': widgets3.PasswordInput(),

    'BooleanField': widgets3.CheckboxInput(),
    # 'FileField': widgets.FileInput(),
    # 'SubmitField': widgets.SubmitInput(),
}


widget_mapping4 = {
    # Multi Types
    'SelectMultipleField': widgets4.Select(multiple=True),
    'SelectField': widgets4.Select(),
    'QuerySelectMultipleField': widgets4.Select(multiple=True),
    'QuerySelectField': widgets4.Select(),
    # 'RadioField': widgets.RadioGroup(),

    # Input Types
    'DateField': widgets4.DateInput(),
    'TextField': widgets4.TextInput(),
    'StringField': widgets4.TextInput(),
    'PasswordField': widgets4.PasswordInput(),

    'BooleanField': widgets4.CheckboxInput(),
    # 'FileField': widgets.FileInput(),
    # 'SubmitField': widgets.SubmitInput(),
}


def wtfbootstrap3(form):
    """changes a WTForms.Form Instance to use html5/bootstrap Widgets."""
    logger.debug('wtfbootstrap3 %s', form)
    for field in form:
        logger.debug('wtfbootstrap3.filed %r', field)
        if not hasattr(field.widget, '__webwidget__'):
            if field.type in widget_mapping3:
                field.widget = widget_mapping3[field.type]
            else:
                logger.critical('unstyled field %s' % field.type)
    return form


def wtfbootstrap4(form):
    """changes a WTForms.Form Instance to use html5/bootstrap Widgets."""
    logger.debug('wtfbootstrap4 %s', form)
    for field in form:
        logger.debug('wtfbootstrap4.filed %r', field)
        if not hasattr(field.widget, '__webwidget__'):
            if field.type in widget_mapping4:
                field.widget = widget_mapping4[field.type]
            else:
                logger.critical('unstyled field %s' % field.type)
    return form
