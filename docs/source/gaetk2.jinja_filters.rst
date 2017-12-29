gaetk2.jinja_filters module - template filters
==============================================

.. py:module:: gaetk2.jinja_filters

These filters do a lot of formatting and conversion. They are
Build with German localisation and HTML in mind to extend
`Jinja's own filters <http://jinja.pocoo.org/docs/2.10/templates/#list-of-builtin-filters>`_

Use them like this in your templates::

    {{ body|markdown }}
    <div class="{{ obj.designator|cssencode }}">

If you use gaetk2.handlers these filters are made available automatically.
If not youncan include them via :func:`register_custom_filters`.


Spacing Issues
--------------

We surrently use u'\u202F' NARROW NO-BREAK SPACE U+202F to separate numbers.
Unfortunately this `is missing in most fonts and not well supported in browsers <https://stackoverflow.com/a/1570664/49407>`_.


.. contents::


Services provided
=================


Access Control
--------------

These Access Control filters are somewhat more involved because they need the cooperation of the rest of gaetk2. They are meant to show certain parts of a template only to certain users.

See :meth:`gaetk2.handler.base.is_staff` and
:class:`gaetk.models.gaetk_Credential` for further Reference.

* :func:`onlystaff` - display content only if the currently logged in user :meth:`~gaetk2.handler.base.is_staff`.

.. todo::
    This functionality is not finalized so far.

    * :func:`authorize`
    * Write Authorisation tutorial.


Encoding
--------

Ensure a variable is a valid value for CSS, URL, XML attribute.

* :func:`cssencode`
* `urlencode <http://jinja.pocoo.org/docs/2.10/templates/#urlencode>`_ - legacy, now part of Jinja >= 2.7.

See also `urlencode <http://jinja.pocoo.org/docs/2.10/templates/#urlencode>`_, `escape <http://jinja.pocoo.org/docs/2.10/templates/#escape>`_, `xmlattr <http://jinja.pocoo.org/docs/2.10/templates/#xmlattr>`_ and `tojson <http://jinja.pocoo.org/docs/2.10/templates/#tojson>`_ in jinja2.


Date-Formatting
---------------

* :func:`dateformat` - formats a ``date`` object.
* :func:`datetimeformat` - formats a ``datetime`` object.
* :func:`tertial` - outputs a tertial (opposed to quater).


Number-Formating
----------------

User-Readable Number formatting. All of these assume you are outputting HTML.

* :func:`nicenum` - seperates thousands by spaces
* :func:`intword` - 1200000 becomes '1.2 Mio' and
* :func:`euroword` - divides cents by 100 and returns an :func:`intword`
* :func:`eurocent` - divides cants by 100 and returns an :func:`nicenum`.
* :func:`g2kg` - convert to a human readable weigth measurment in g/kg/t. See also `filesizeformat <http://jinja.pocoo.org/docs/2.10/templates/#filesizeformat>`_ in jinja2.
* :func:`percent` - a ``None`` tollerant ``"%.0f"``
* :func:`iban` - Format An International Banking Code.

Text-Formatting
---------------

Many of these functions are most relevant for settings where you
have ``<pre>>`` or want to reach a similar effect in HTML.

* :func:`markdown` - convert Markdown to HTML.
* :func:`nl2br` - basically get the output of ``<pre>`` without using ``<pre>``.
* :func:`left_justify`
* :func:`right_justify`

See also `urlize <http://jinja.pocoo.org/docs/2.10/templates/#urlize>`_, `indent <http://jinja.pocoo.org/docs/2.10/templates/#indent>`_ and `center <http://jinja.pocoo.org/docs/2.10/templates/#center>`_ in jinja2.


Boolean-Formatting (and None)
-----------------------------

Displaying Booleans with the ability to distinguish between ``(True, False, None)``.

* :func:`yesno` - output yes, no, maybe
* :func:`onoff` - unse Font Awesome icons to display boolean
* :func:`none` - Supress ``None`` output. See also `default <http://jinja.pocoo.org/docs/2.10/templates/#default>`_ in jinja2.


Misc
----

* :func:`plural` - Pluralize (works for German).


GAETK1 Compability
------------------

* ``datetime`` has been renamed to datetimeformat.
* ``to_json`` is gone, use `tojson <http://jinja.pocoo.org/docs/2.10/templates/#tojson>`_ in jinja2 2.9.
* ``urlencode`` is gone, use `urlencode <http://jinja.pocoo.org/docs/2.10/templates/#urlencode>`_ in jinja2 2.7. the `urlencode <http://jinja.pocoo.org/docs/2.10/templates/#urlencode>`_ provided by jinja has much more features than we had.
* ``attrencode`` is gone, use `xmlattr <http://jinja.pocoo.org/docs/2.10/templates/#xmlattr>`_ in jinja2 2.9.
* generally we now return only Unicode Plain Text, no HTML. ``nicenum``, ``eurocent``and ``g2kg`` are changed by that.
* the `urlencode <http://jinja.pocoo.org/docs/2.10/templates/#urlencode>`_ provided by jinja2


Module contents
===============

.. automodule:: gaetk2.jinja_filters
    :members:
    :undoc-members:
    :show-inheritance:
