#!/usr/bin/env python
# encoding: utf-8
"""
jinja_filters - custom jinja2 filters for gaetk2.

Copyright (c) 2010, 2012, 2014, 2017, 2018 Maximillian Dornseif. MIT Licensed.
"""
import decimal
import json
import logging
import re
import urllib
import warnings

import jinja2
from jinja2.utils import Markup
from gaetk2.tools.datetools import convert_to_date, convert_to_datetime

import markdown2

logger = logging.getLogger(__name__)


# Access Control

@jinja2.contextfilter
def authorize(context, value, permission_types):
    """Display content only if the current logged in user has a specific permission."""
    if not isinstance(permission_types, list):
        permission_types = [permission_types]

    # Permissions disabled -> granted
    granted = context.get('request').get('_gaetk_disable_permissions', False)
    for permission in permission_types:
        if context.get('credential') and permission in context.get('credential').permissions:
            granted = True
            break

    if granted:
        value = '<span class="restricted">%s</span>' % (value)
    else:
        value = u'…<!-- Berechtigung %s -->' % (', '.join(permission_types))
        if not context.get('credential'):
            logger.info('context has no credential!')

    if context.eval_ctx.autoescape:
        return Markup(value)
    return value


BLOCKTAGS = """address article aside blockquote canvas div dl
fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 header hgroup
hr li main nav noscript ol output p pre section table tfoot ul video""".split()
NOTAGS = """dd dt thead tfoot tbody tr td""".split()


@jinja2.contextfilter
def onlystaff(ctx, value, tag=None):
    """Display content only if the current logged in user `is_staff()`.

    This tag generatyes HTML. If you don't wan't HTML use this construct::

        {% if is_staff() %}Internal Info{% endif %}

    The Tag encloses content in a ``<span>`` or ``<div>`` depending
    on it's contents::

        {{ "bla"|onlystaff }}
        <!-- is rendered to: -->
        <span class="gaetk_onlystaff">bla</span>

        {% filter onlystaff %}
            <form  ...></form>
        {% endfilter %}
        <!-- is rendered to: -->
        <div class="gaetk_onlystaff">
            <form ...></form>
        </div>

        {% filter onlystaff %}
            <i>test text</i>
        {% endfilter %}
        <!-- is rendered to: -->
        <span class="gaetk_onlystaff"><i>test text</i></span>

    If you not happy with how the filter chooses between ``<span>`` and ``<div>``
    you can provide a tag to be used. Or you can provide empty data to avoid
    all markup::

        {% filter onlystaff('p') %}
            <i>test text</i>
        {% endfilter %}
        <!-- is rendered to: -->
        <p class="gaetk_onlystaff">bla</p>

        {% filter onlystaff('') %}
            foo
        {% endfilter %}
        <!-- is rendered to: -->
        foo

    Automatic detection does not work perfectly within tables.
    Your milage may vary.

    If the user is not staff an empty tag is generated::

        {% filter onlystaff %}
            supersecret
        {% endfilter %}
        <!-- is rendered to: -->
        <span class="gaetk_onlystaff-denied"><!-- !is_staff() --></span>

        {% filter onlystaff('') %}
            supersecret
        {% endfilter %}
        <!-- is rendered to: (nothing) -->
    """

    if tag is None:
        tag = u'span'
        m = re.search(r'$\s*<(%s)' % '|'.join(NOTAGS), value)
        if m:
            tag = u''
        else:
            m = re.search(r'<(%s)' % '|'.join(BLOCKTAGS), value)
            if m:
                tag = u'div'

    granted = False
    if ctx.get('credential') and ctx.get('credential').staff:
        granted = True

    if granted:
        if not tag:
            return value
        value = u'<{tag} class="gaetk_onlystaff">{value}</{tag}>'.format(
            tag=tag, value=jinja2.escape(value))
    else:
        if not ctx.get('credential'):
            logger.info('context has no credential!')
        if not tag:
            return u''
        value = u'<{tag} class="gaetk_onlystaff-denied"><!-- !is_staff() --></{tag}>'.format(
            tag=tag)
    return Markup(value)


# Encoding

def _attrencode(value):
    """Makes a string valid as an XML attribute value.

    Includes the quotation marks. Eg::

        {{ "jim's garage"|attrencode }}
        >>> '"jim\' garage"'

    `xmlattr <http://jinja.pocoo.org/docs/2.10/templates/#xmlattr>`_
    in jinja2 is a more sophisticated version of this.
    """
    warnings.warn("`attrencode` is deprecated, use `xmlattr`", DeprecationWarning, stacklevel=2)
    import xml.sax.saxutils
    if value is None:
        return u''
    if hasattr(value, 'unescape'):  # jinja2 Markup
        value = value.unescape()
    return xml.sax.saxutils.quoteattr(value)[1:-1]


def cssencode(value):
    """Makes a string valid as an CSS class name.

    This ensured only valid characters are used and the class name starts
    with an character. This is enforced by prefixing `CSS` if the string
    does not start with an character::

        <div class="{{ 5711|cssencode }} {{ 'root beer'|cssencode }}">
        >>> '<div class="CSS5711 root-beer">'
    """
    if value is None:
        return u''
    ret = re.sub('[^A-Za-z0-9-_]+', '-', unicode(value))
    if ret.startswith(tuple('-0123456789')):
        ret = 'CSS' + ret
    return ret


def _to_json(value):
    """Convert the given Value to JSON.

    Very helpful to use in Javascript. Similar to
    `tojson <http://jinja.pocoo.org/docs/2.10/templates/#tojson>`_, but
    we try to be smarter about encoding of datastore properties.
    """
    warnings.warn("`to_json` is deprecated, use `tojson`", DeprecationWarning, stacklevel=2)
    return json.dumps(value)


# Date-Formatting

def dateformat(value, formatstring='%Y-%m-%d', nonchar=u''):
    """Formates a date.

    Tries to convert the given ``value`` to a ``date`` object and then formats
    it according to ``formatstring``::

        {{ date.today()|dateformat }}
        {{ "20171224"|dateformat('%Y-%W') }}
    """
    if not value:
        return nonchar
    return Markup(convert_to_date(value).strftime(formatstring).replace('-', '&#8209;'))


def datetimeformat(value, formatstring='%Y-%m-%d %H:%M', nonchar=u''):
    """Formates a datetime.

    Tries to convert the given ``value`` to a ``datetime`` object and then formats
    it according to ``formatstring``::

        {{ datetime.now()|datetimeformat }}
        {{ "20171224T235959"|datetimeformat('%H:%M') }}
    """
    if not value:
        return nonchar
    return Markup(convert_to_datetime(value).strftime(formatstring).replace('-', '&#8209;'))


def _datetime(value, formatstring='%Y-%m-%d %H:%M'):
    """Legacy function, to be removed."""
    warnings.warn("`datetime` is deprecated, use `datetimeformat`", DeprecationWarning, stacklevel=2)
    return datetimeformat(value, formatstring='%Y-%m-%d %H:%M')


def tertial(value, nonchar=u'␀'):
    """Change a Date oder Datetime-Objekt into a Tertial-String.

    Tertials are third-years as opposed to quater years::

        {{ "20170101"|tertial }} {{ "20170606"|tertial }} {{ "20171224"|tertial }}
        >>> "2017-A" "2017-B" "2017-C"
    """
    from huTools.calendar.formats import tertial
    if not value:
        return nonchar
    return tertial(value)


# Number-Formating

def nicenum(value, spacer=u'\u202F', nonchar=u'␀'):
    """Format the given number with spacer as delimiter, e.g. `1 234 456`.

    Default spacer is NARROW NO-BREAK SPACE U+202F.
    Probably `style="white-space:nowrap; word-spacing:0.5em;"` would be an CSS based alternative.
    """
    if value is None:
        return nonchar
    rev_value = (u"%d" % int(value))[::-1]
    return spacer.join(reversed([rev_value[i:i + 3][::-1] for i in range(0, len(rev_value), 3)]))


def intword(value, nonchar=u'␀'):
    """Converts a large integer to a friendly text representation.

    Works best for numbers over 1 million. For example,
    1000000 becomes '1.0 Mio', 1200000 becomes '1.2 Mio' and
    '1200000000' becomes '1200 Mio'.
    """
    return _formatint(value, nonchar)


def _formatint(value, nonchar=u'␀'):
    """Format an Integer nicely with spacing."""
    # Inspired by Django
    # https://github.com/django/django/blob/master/django/contrib/humanize/templatetags/humanize.py
    if value is None:
        return nonchar
    value = int(value)
    if abs(value) < 1000000:
        rev_value = (u"%d" % int(value))[::-1]
        return u' '.join(reversed([rev_value[i:i + 3][::-1] for i in range(0, len(rev_value), 3)]))
    else:
        new_value = value / 1000000.0
        return '%(value).1f Mio' % {'value': new_value}
    return value


def eurocent(value, spacer=u'\u202F', decimalplaces=2, nonchar=u'␀'):
    """Format the given cents as Euro with spacer as delimiter, e.g. '1 234 456.23'.

    Obviously works also with US$ and other 100-based. currencies.

    This is like :func:nicenum. Use ``decimalplaces=0`` to cut of cents, but even better use :func:euroword.

    Default spacer is NARROW NO-BREAK SPACE U+202F.
    Probably `style="white-space:nowrap; word-spacing:0.5em;"` would be an CSS based alternative.
    """
    if value is None:
        return nonchar
    tmp = str(int(value) / decimal.Decimal(100))
    # Cent anhängen
    if '.' not in tmp:
        tmp += '.'
    euro_value, cent_value = tmp.split('.')
    cent_value = cent_value.ljust(decimalplaces, '0')[:decimalplaces]
    rev_value = euro_value[::-1]
    euro_value = spacer.join(reversed([rev_value[i:i + 3][::-1] for i in range(0, len(rev_value), 3)]))
    return u'%s.%s' % (euro_value, cent_value)


def euroword(value, plain=False, nonchar=u'␀'):
    """Fomat Cents as pretty Euros."""
    if value is None:
        return nonchar
    return _formatint(value / 100)


def g2kg(value, spacer=u'\u202F', nonchar=u'␀'):
    """Wandelt meist g in kg um, aber auch in andere Einheiten."""
    if value is None:
        return nonchar
    if not value:
        return value
    elif value < 100:
        return u"{:d}{}g".format(value, spacer)
    elif value < 1000 * 50:
        return u"{:.2f}{}kg".format(value / 1000.0, spacer)
    elif value < 1000 * 1000:
        return u"{:.1f}{}kg".format(value / 1000.0, spacer)
    else:
        return u"{:.1f}{}t".format(value / 1000.0 ** 2, spacer)


def percent(value, nonchar=u'␀'):
    """Fomat Percent and handle None."""
    if value is None:
        return nonchar
    return '%.0f' % float(value)


def iban(value, spacer=u'\u202F', nonchar=u'␀'):
    """Format the given string like an IBAN Account Number.

    Default spacer is NARROW NO-BREAK SPACE U+202F.

    Eg::

        {{ "DE77123413500000567844"|iban }}
        DE77 1234 1350 0000 5678 44
    """
    if not value:
        return nonchar
    return spacer.join([value[i:i + 4] for i in range(0, len(value), 4)])


# Text-Formatting

def markdown(value):
    """Renders a string as Markdown.

    Syntax:
        {{ value|markdown }}

    We are using `markdown2 <https://pypi.python.org/pypi/markdown2>`_ to do the rendering.
    """
    return Markup(markdown2.markdown(value))


@jinja2.evalcontextfilter
def nl2br(eval_ctx, value):
    """Newlines in <br/>-Tags konvertieren."""
    paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')
    result = u'\n\n'.join(u'<p>%s</p>' % paragraph.replace('\n', '<br>\n')
                          for paragraph in paragraph_re.split(value))
    if eval_ctx.autoescape:
        return Markup(result)
    return result


def left_justify(value, width):
    """Prefix the given string with spaces until it is width characters long."""
    return unicode(value or '').ljust(int(width))


def right_justify(value, width):
    """Postfix the given string with spaces until it is width characters long."""
    stripped = unicode(value or '')[0:width]
    return stripped.rjust(int(width))


# Boolean-Formatting (and None)

def yesno(value, answers=u'yes,no,maybe'):
    """Output a text based on Falsyness, Trueyness and ``is None``.

        Example: ``{{ value|yesno:"yeah,nope,maybe" }}``.
    """
    bits = answers.split(u',')
    if len(bits) == 3:
        vyes, vno, vmaybe = bits
    elif len(bits) == 2:
        vyes, vno, vmaybe = bits[0], bits[1], bits[1]
    else:
        return value

    if value is None:
        return vmaybe
    if value:
        return vyes
    return vno


def onoff(value):
    """Display Boolean as Font Awesome Icon Icon darstellen.

    We use Font Awesome `toogle-on <http://fontawesome.io/icon/toggle-on/>`_
    and `toogle-of <http://fontawesome.io/icon/toggle-off/>`_ to indicate state.
    """
    if value:
        return Markup('<i class="fa fa-toggle-on" aria-hidden="true" style="color:green"></i>')
    else:
        return Markup('<i class="fa fa-toggle-off" aria-hidden="true" style="color:gray"></i>')


def none(value, nonchar=u''):
    """Converts ``None`` to ``''``.

    Similar to ``|default('', true)`` in jinja2 but more explicit.
    """
    if value is None:
        return nonchar
    return value


# Datastore Protocol

def otag(obj):
    """Link like this: `<a href="obj.url">obj.designator</a>`."""
    if not getattr(obj, 'url'):
        return
    link = obj.url
    designator = obj.designator
    style = ''
    klass = ''
    # # wir machen ein bischen intelligente Formatierung hier
    # # TODO: inaktiv und erledigt und storniert unterscheiden
    # if getattr(obj, 'erledigt', False):
    #     style = ''
    #     klass = 'class="cs_erledigt"'
    return Markup('<a href="{}" {} {}>{}</a>'.format(
        link, style, klass, jinja2.escape(designator)))


def datastore(entity, attr=None, value=None, text=None):
    """Generate HTML a-Tag to Google Datastore Query.

        {{ credential|datastore }} -> queries for key
        {{ credential|datastore('email') }} -> queries for email
        {{ credential|datastore('name', '') }} -> queries for credential.name == ''
        {{ credential|datastore(text='Search in Datastore') }} -> changes Link-Text
    """

    if not attr:
        attr = '__key__'
        value = entity.key.urlsafe()
        typ = 'KEY'
        qtext = "SELECT * FROM {} WHERE __key__ = KEY('{}')".format(entity._get_kind(), value)
    else:
        if not value:
            value = getattr(entity, attr, '')
        typ = 'STR'
        qtext = "SELECT * FROM {} WHERE __key__ = '{}'".format(entity._get_kind(), value)
    query = {
        # TODO: auch INT? auch andere Vergleichsoperatoren?
        'filter': '{}/{}|{}|EQ|{}/{}'.format(
            len(attr), attr, typ, len(value), value),
        'kind': entity._get_kind()}
    url = 'https://console.cloud.google.com/datastore/entities/query?' + urllib.urlencode(query)
    if text is None:
        text = qtext
    content = '<a href="{}">{}</a>'.format(url, jinja2.escape(text))
    return Markup(content)


# Misc

def plural(value, singular_str, plural_str):
    """Return value with singular or plural form.

    ``{{ l|length|plural('Items', 'Items') }}``
    """
    if not isinstance(value, (int, long)):
        return singular_str

    if value == 1:
        return singular_str
    return plural_str


def register_custom_filters(jinjaenv):
    """Register the filters to the given Jinja environment."""
    jinjaenv.filters['authorize'] = authorize
    jinjaenv.filters['onlystaff'] = onlystaff
    jinjaenv.filters['attrencode'] = _attrencode
    jinjaenv.filters['cssencode'] = cssencode
    jinjaenv.filters['to_json'] = _to_json
    jinjaenv.filters['dateformat'] = dateformat
    jinjaenv.filters['datetimeformat'] = datetimeformat
    jinjaenv.filters['datetime'] = _datetime
    jinjaenv.filters['tertial'] = tertial
    jinjaenv.filters['nicenum'] = nicenum
    jinjaenv.filters['intword'] = intword
    jinjaenv.filters['eurocent'] = eurocent
    jinjaenv.filters['euroword'] = euroword
    jinjaenv.filters['percent'] = percent
    jinjaenv.filters['g2kg'] = g2kg
    jinjaenv.filters['iban'] = iban
    jinjaenv.filters['markdown'] = markdown
    jinjaenv.filters['nl2br'] = nl2br
    jinjaenv.filters['ljustify'] = left_justify
    jinjaenv.filters['rjustify'] = right_justify
    jinjaenv.filters['yesno'] = yesno
    jinjaenv.filters['onoff'] = onoff
    jinjaenv.filters['none'] = none
    jinjaenv.filters['otag'] = otag
    jinjaenv.filters['datastore'] = datastore
    jinjaenv.filters['plural'] = plural
