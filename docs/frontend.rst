.. _frondend-guidelines:

Frontend Guidelines
===================

See :class:`gaetk2.handers.base.BasicHandler` for generic Template Variables etc.

Frontends are assumed to be generated using Jinja2 and Bootstrap 4.
All displayed content is based in ``templates/gaetk_base_bs4.html``

The usual approach is to generate one Template inherited from
``gaetk_base_bs4.html`` for your app where you set defaults an then inherit
in all your actual templates from that and only overwrite ``maincontent``.

So for example your ``base_myapp.html`` looks like this::

	{% extends "gaetk_base_bs4.html" %}
	{% block header %}
	 My Cool Navbar
	{% endblock %}
	{% block secondarycontent %}
	<div class="card" style="width: 18rem;">
	<div class="card-body">
	  <p class="card-text">navigation, current news</p>
	</div>
	</div>
	{% endblock secondarycontent %}

The individual templates then just inherit from ``base_myapp.html``::

	{% extends "base_bs4.html" %}
	{% block maincontent %}
	Here are our most recent offers:
	...
	{% endblock maincontent %}

The main structure of the layout look like this:

.. image:: http://filez.foxel.org/032O1A2V0C0k/Image%202018-01-09%20at%205.54.55%20PM.jpg

Available blocks to overwrite:

* ``maincontent`` - where the content of your app lives. ``<h1>{{title}}</h1>`` is displayed above it. (The `<h1>` and title can be overwritten with ``{% block title %}``)
* ``secondarycontent`` - sidebar style content to the right.
* ``header`` - usually filled with the auto-generated navbar. To hide it, use ``{% block header %}{% endblock header %}``.
* ``footer`` - below ``maincontent`` and ``secondarycontent``.
* ``page`` basically overwrites ``header``, ``<h1>{{title}}</h1>``, ``maincontent`` and ``secondarycontent`` leaving only ``footer``.


.. _breadcrumbs:
Breadcrumbs
-----------

If you add something like this to your template Variables::

    breadcrumbs = [('Market', '/'), (kundennr, '#'), (u'Aufträge', '#')]

There will be a list of breadcrumbs rendered above the Title.


Snippets
--------

Snippets are gaetk2's stab at simple CMS functionality. You still write
hardcoded HTML-Templates. But inside you can insert parts editable by
your staff in the browser without the need to update the application.

This happens by adding ``show_snippet`` template tags::

    {{ show_snippet('welcome') }}

When the resulting page is rendered there will be no text because
the snippet has no content so far. But there should be an edit icons.

.. image:: http://filez.foxel.org/103F2Z0S3d1i/Image%202018-04-11%20at%208.07.06%20PM.jpg

If you click on it you will be redirected to an editing page where you can
change the Snippet. You can also provide a default text to be used for initial
snippet content::

    {{ show_snippet('welcome', 'Welcome to our Site!') }}

..  todo::

  * insert ``show_snippet`` into template contest to make it usable
  * remove pagedown_bootstrap and replace it with something usable


Progressive enhancements
------------------------

..  todo::

  * gaetkenhance-confirm, table
  * ChiqView
  * Breadcrumbs with hooks

Best Practices
--------------

No Tables for Definition Lists
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Don't use Tables for non tabular Data. ``dl-horizontal`` (Bootstrap 3) is way
to go. In Bootstrap 4 the Markup is somewhat convoluted::

    <dl class="row">
      <dt class="col-3">AuftragsNr</dt>
      <dd class="col-9">{{ a.auftragsnr }}</dd>

      <dt class="col-3">Auftragsdatum / Status</dt>
      <dd class="col-9">{{ a.eingegangen_am|dateformat }} / {{ a.nicestatus }}</dd>
    </dl>


Table Styling
^^^^^^^^^^^^^

Tagles we usually style with ``class="table table-striped table-sm"``.
For large rows like Product Listing with Images we use ``class="table table-hover"``.
