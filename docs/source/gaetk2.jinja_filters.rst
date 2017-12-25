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

.. contents::


Access Control
--------------

These Access Control filters are somewhat more involved because they need the cooperation of the rest of gaetk2. They are meant to show certain parts of a template only to certain users.

.. todo:: 
    This functionality is not finalized so far.

    * onlystaff :func:`onlystaff`
    * authorize :func:`authorize`

Encoding
--------

Ensure a variable is a valid value for CSS, URL, XML attribute.

* cssencode :func:`cssencode`
* urlencode `urlencode <http://jinja.pocoo.org/docs/2.10/templates/#urlencode>`_ - legacy, now part of Jinja >= 2.7.

See also `urlencode <http://jinja.pocoo.org/docs/2.10/templates/#urlencode>`_, `escape <http://jinja.pocoo.org/docs/2.10/templates/#escape>`_, `xmlattr <http://jinja.pocoo.org/docs/2.10/templates/#xmlattr>`_ and `tojson <http://jinja.pocoo.org/docs/2.10/templates/#tojson>`_ in jinja2.


Date-Formatting
---------------

* dateformat :func:`dateformat` - formats a ``date`` object.
* datetime :func:`datetimeformat` - formats a ``datetime`` object.
* tertial :func:`tertial` - outputs a tertial (opposed to quater).


Number-Formating
----------------

User-Readable Number formation. All of these assume you are outputting HTML.

* nicenum :func:`nicenum` - seperates thousands by spaces
* intword :func:`intword` - 1200000 becomes '1.2 Mio' and
* euroword :func:`euroword` - divides cents by 100 and returns an :func:`intword`
* eurocent :func:`eurocent` - divides cants by 100 and returns an :func:`nicenum`.
* g2kg :func:`g2kg` - convert to a human readable weigth measurment in g/kg/t. See also `filesizeformat <http://jinja.pocoo.org/docs/2.10/templates/#filesizeformat>`_ in jinja2.
* percent :func:`percent` - a ``None`` tollerant ``"%.0f"``


Text-Formatting
---------------

Many of these functions are most relevant for settings where you 
have ``<pre>>`` or want to reach a similar effect in HTML.

* markdown :func:`markdown` - convert Markdown to HTML.
* nl2br :func:`nl2br` - basically get the output of ``<pre>`` without using ``<pre>``.
* ljustify :func:`left_justify`
* rjustify :func:`right_justify`

See also `urlize <http://jinja.pocoo.org/docs/2.10/templates/#urlize>`_, `indent <http://jinja.pocoo.org/docs/2.10/templates/#indent>`_ and `center <http://jinja.pocoo.org/docs/2.10/templates/#center>`_ in jinja2.


Boolean-Formatting (and None)
-----------------------------

Displaying Booleans with the ability to distinguish between ``(True, False, None)``.

* yesno :func:`yesno` - output yes, no, maybe
* onoff :func:`onoff` - unse Font Awesome icons to display boolean
* none :func:`none` - Supress ``None`` output. See also `default <http://jinja.pocoo.org/docs/2.10/templates/#default>`_ in jinja2.


Misc
----

* plural :func:`plural`


GAETK1 Compability
------------------

* ``datetime`` has been renamed to datetimeformat.
* ``to_json`` is gone, use `tojson <http://jinja.pocoo.org/docs/2.10/templates/#tojson>`_ in jinja2 2.9.
* ``urlencode`` is gone, use `urlencode <http://jinja.pocoo.org/docs/2.10/templates/#urlencode>`_ in jinja2 2.7. the `urlencode <http://jinja.pocoo.org/docs/2.10/templates/#urlencode>`_ provided by jinja has much more features than we had.
* ``attrencode`` is gone, use `xmlattr <http://jinja.pocoo.org/docs/2.10/templates/#xmlattr>`_ in jinja2 2.9.
* generally we now return only Unicode Plain Text, no HTML. ``nicenum``, ``eurocent``and ``g2kg`` are changed by that.
* the `urlencode <http://jinja.pocoo.org/docs/2.10/templates/#urlencode>`_ provided by jinja2 


Module contents
---------------

.. automodule:: gaetk2.jinja_filters
    :members:
    :undoc-members:
    :show-inheritance:
