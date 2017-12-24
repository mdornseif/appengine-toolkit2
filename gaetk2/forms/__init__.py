#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.forms.__init__ - Use WTforms but with custom widgets

Created by Maximillian Dornseif on 2017-12-23.
Copyright (c) 2017. MIT Licensed.
"""

import logging

from gaetk2.forms import widgets

widget_mapping = {
    # Multi Types
    'SelectMultipleField': widgets.Select(multiple=True),
    'SelectField': widgets.Select(),
    'QuerySelectMultipleField': widgets.Select(multiple=True),
    'QuerySelectField': widgets.Select(),
    # 'RadioField': widgets.RadioGroup(),

    # Input Types
    'DateField': widgets.DateInput(),
    'TextField': widgets.TextInput(),
    'StringField': widgets.TextInput(),
    'PasswordField': widgets.PasswordInput(),

    'BooleanField': widgets.CheckboxInput(),
    # 'FileField': widgets.FileInput(),
    # 'SubmitField': widgets.SubmitInput(),
}


def wtfbootstrap3(form):
    """changes a WTForms.Form Instance to use html5/bootstrap Widgets."""
    logging.error('wtfbootstrap3 %s', form)
    for field in form:
        logging.error('wtfbootstrap3.filed %r', field)
        if not hasattr(field.widget, '__webwidget__'):
            if field.type in widget_mapping:
                field.widget = widget_mapping[field.type]
            else:
                logging.critical('unstyled field %s' % field.type)
    return form
