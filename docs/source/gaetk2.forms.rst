gaetk2\.forms package - form handling via WTForms
=================================================

gaetk2.forms aims at making `Bootstrap 3 Forms <http://getbootstrap.com/docs/3.3/css/#forms>`_
and `WTForms <https://wtforms.readthedocs.io/en/latest/>`_ play nice together.
This means for the normal form you don't have to write any HTML.

Together with `wtforms-appengine <https://github.com/wtforms/wtforms-appengine>`_
you can get a very smooth form handling experience.

.. py:function:: wtfbootstrap3(form)

    Takes a form instance and changes the widgets within to conform to
    bootstrap / HTML5 layout including labels, error-messages, etc.

    So usage would look like this::

        # Define an Datastore / NDB - Model
        from google.appengine.ext import ndb
        class pay_Lastschriftmandat(ndb.Model):
            kundennr = ndb.StringProperty(required=True)
            kontoinhaber = ndb.StringProperty(required=True)
            iban = ndb.StringProperty()
            bic = ndb.StringProperty()
            datum = ndb.DateTimeProperty()
            mandatsreferenz = ndb.StringProperty(required=True)
            glaeubigernr = ndb.StringProperty(required=True)
            updated_at = ndb.DateTimeProperty(auto_now=True)
            created_at = ndb.DateTimeProperty(auto_now_add=True)

        # build the WTForm from Model
        from wtforms_appengine.ndb import model_form
        LastschriftmandatForm = model_form(
            pay_Lastschriftmandat,
            only=['bic', 'iban', 'datum']
        )

        # Render form
        from gaetk2.forms import wtfbootstrap3
        class View(gaetk.handlers.DefaultHandler):
            def get(self):
                # instantiate form
                form = LastschriftmandatForm()
                # style form
                form = wtfbootstrap3(form)
                self.render({'form': form}, 'view.html')

    Now you could render it in your template like this::

        <form method="POST">
          <div class="form-body form-group">
            {% for field in form %}
              {% if field.flags.required %}
                {{ field(required=True) }}
              {% else %}
                  {{ field() }}
              {% endif %}
            {% endfor %}
          </div><!-- /form-body -->
          <div class="text-right">
            <button type="submit" id="{{ domid }}-submit-button" form="{{ domid }}-form" data-loading-indicator="true" class="btn btn-primary" autocomplete="off">{{ buttonname }}</button>
          </div>
        </form>

.. |Sample Form generated| image:: https://d3vv6lp55qjaqc.cloudfront.net/items/2N0b3h3B0r0v2l0M0j1b/Image%202017-12-24%20at%2011.59.31%20AM.jpg


.. todo::

    * Add validation. Use https://validators.readthedocs.io/en/latest/
    * Add some standard way to render a complete Form not just fields.


Module contents
---------------

.. automodule:: gaetk2.forms
    :members:
    :undoc-members:
    :show-inheritance:

