#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.forms.widgets - wtforms extention to render Bootstrap/HTML5 fields.

based on https://github.com/nickw444/wtforms-webwidgets

Created by Maximillian Dornseif on 2017-02-28.
Coded (c) 2017. No rights reserved.
"""

from abc import ABCMeta
from functools import wraps

import wtforms.widgets.core as wt_core
import wtforms.widgets.html5 as wt_html5
from wtforms.widgets.core import HTMLString


class CustomWidgetMixin(object):
    """A mixin to apply to a widget to identify it as a non-wtforms builtin."""

    __metaclass__ = ABCMeta
    __webwidget__ = True


def custom_widget_wrapper(cls):
    """A decorator to wrap a widget to identify it as non-wtforms builtin."""
    cls.__webwidget__ = True
    return cls


def render_field_errors(field):
    """Render field errors as html."""
    if field.errors:
        html = u"""<p class="help-block">Error: {errors}</p>""".format(
            errors=u'. '.join(field.errors)
        )
        return HTMLString(html)

    return None


def render_field_description(field):
    """Render a field description as HTML."""
    if hasattr(field, 'description') and field.description != '':
        html = u"""<p class="help-block">{field.description}</p>"""
        html = html.format(
            field=field
        )
        return HTMLString(html)

    return ''


def form_group_wrapped(f):
    """Wrap a field within a bootstrap form-group.

    Additionally sets has-error
    This decorator sets has-error if the field has any errors.
    """
    @wraps(f)
    def wrapped(self, field, *args, **kwargs):
        u"""Closure, die bootstrap-gemässes HTML um eine Form-Group baut."""
        classes = ['form-group']
        if field.errors:
            classes.append('has-error')

        html = u"""<div class="{classes}">{rendered_field}</div>""".format(
            classes=' '.join(classes),
            rendered_field=f(self, field, *args, **kwargs)
        )
        return HTMLString(html)

    return wrapped


def meta_wrapped(f):
    """Add a field label, errors, and a description (if it exists) to a field."""
    @wraps(f)
    def wrapped(self, field, *args, **kwargs):
        u"""Closure, die bootstrap-gemässes HTML um ein Feld baut."""
        html = u"{label}{errors}{original}<small>{description}</small>".format(
            label=field.label(class_='control-label'),
            original=f(self, field, *args, **kwargs),
            errors=render_field_errors(field) or u'',
            description=render_field_description(field)
        )
        return HTMLString(html)
    return wrapped


def bootstrap_styled(cls=None, add_meta=True, form_group=True, input_class='form-control'):
    """
    Wrap a widget to conform with Bootstrap's html control design.

    Args:
        input_class: Class to give to the rendered <input> control.
        add_meta: bool:
    """
    def real_decorator(cls):
        u"""Funktion (Closure), die wir on demand bauen und zurück geben."""
        class NewClass(cls):
            u"""Klasse (Closure), die wir on demand bauen und zurück geben."""

            pass

        NewClass.__name__ = cls.__name__
        newclass = custom_widget_wrapper(NewClass)

        _call = newclass.__call__

        def call(*args, **kwargs):
            u"""Handler für `NewClass.__call__`."""
            if input_class:
                kwargs.setdefault('class', input_class)

            return _call(*args, **kwargs)

        if add_meta:
            call = meta_wrapped(call)
        if form_group:
            call = form_group_wrapped(call)

        newclass.__call__ = call
        return newclass

    if cls:
        # Allow calling decorator(cls) instead of decorator()(cls)
        rv = real_decorator(cls)
        return rv

    return real_decorator


class BootstrapPlainCheckboxRadio(wt_core.CheckboxInput, CustomWidgetMixin):
    """Abstract widget for a Bootstrap Checkbox or Radio implementation."""

    __metaclass__ = ABCMeta

    def __call__(self, field, **kwargs):
        """Aufruf zum Rendern."""
        label = getattr(field, 'label', None)
        if label in kwargs:
            label = kwargs.pop('label').strip()

        html = u"""
        <div class="{input_type}">
            <label>{rendered_field}{label}</label>
        </div>
        """.format(
            label=label,
            input_type=self.input_type,
            rendered_field=super(BootstrapPlainCheckboxRadio, self).__call__(field, **kwargs)
        )
        return HTMLString(html)


class PlainCheckbox(BootstrapPlainCheckboxRadio):
    """Render a checkbox without any bootstrap container classes."""

    def __init__(self):
        """Setze den richtigen input_type."""
        super(PlainCheckbox, self).__init__()
        self.input_type = 'checkbox'


class PlainRadio(BootstrapPlainCheckboxRadio):
    """Render a radio without any bootstrap container classes."""

    def __init__(self):
        """Setze den richtigen input_type."""
        super(PlainRadio, self).__init__()
        self.input_type = 'radio'


CheckboxInput = PlainCheckbox
RadioInput = PlainRadio
Input = bootstrap_styled(wt_core.Input)
TextInput = bootstrap_styled(wt_core.TextInput)
PasswordInput = bootstrap_styled(wt_core.PasswordInput)
HiddenInput = wt_core.HiddenInput  # We don't need to style this.
TextArea = bootstrap_styled(wt_core.TextArea)
Select = bootstrap_styled(wt_core.Select)

ColorInput = bootstrap_styled(wt_html5.ColorInput)
DateInput = bootstrap_styled(wt_html5.DateInput)
DateTimeInput = bootstrap_styled(wt_html5.DateTimeInput)
DateTimeLocalInput = bootstrap_styled(wt_html5.DateTimeLocalInput)
EmailInput = bootstrap_styled(wt_html5.EmailInput)
MonthInput = bootstrap_styled(wt_html5.MonthInput)
NumberInput = bootstrap_styled(wt_html5.NumberInput)
RangeInput = bootstrap_styled(wt_html5.RangeInput)
SearchInput = bootstrap_styled(wt_html5.SearchInput)
TelInput = bootstrap_styled(wt_html5.TelInput)
TimeInput = bootstrap_styled(wt_html5.TimeInput)
URLInput = bootstrap_styled(wt_html5.URLInput)
WeekInput = bootstrap_styled(wt_html5.WeekInput)

default_widgets = {
    # Multi Types
    'SelectMultipleField': Select(multiple=True),
    'SelectField': Select(),
    'QuerySelectMultipleField': Select(multiple=True),
    'QuerySelectField': Select(),
    # 'RadioField': RadioGroup(),

    # Input Types
    'DateField': DateInput(),
    # 'TextField': TextInput(),
    'StringField': TextInput(),
    'PasswordField': PasswordInput(),

    'BooleanField': CheckboxInput(),
    # 'FileField': FileInput(),
    # 'SubmitField': SubmitInput(),
}
