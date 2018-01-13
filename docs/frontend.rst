Frontend Guidelines
===================

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


Progressive enhancements
------------------------

* gaetkenhance-confirm


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
