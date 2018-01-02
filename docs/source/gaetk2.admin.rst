gaetk2\.admin package
=====================

This package implemets automatic administration facilities. It aims to be
a mix of the concepts of Django Admin and the Google App Engine Admin Console.
It is aimed to be used not by Developers, Dev Ops or System Administrators
but by the regular staff using your application - so it apptempts to give you
less opportunity to shoot your self in the foot.

It also aims at giving you building blocks for your own user facing pages.

These Services provided by the Admin-Package are automatically available at `/admin2/`
in your URL-Tree.

.. image:: http://filez.foxel.org/0t2h2G0o1g0r/Image%202018-01-19%20at%201.02.18%20PM.jpg

With minimal configuration you can get an admin site as above. Just add a
file :file:`admin_gaetk2.py` e.g. in ``modules/pay/`` or any other directory
within your the ``modules`` directory::

    from gaetk2.admin import site
    from gaetk2.admin.layout import AdminLayout
    from . import pay_models

    class MyLayout(AdminLayout):
        links = [
            ('SEPA-Dateien',
             'https://console.cloud.google.com/storage/browser/foobar'),
        ]
    site.registerlayoutclass(MyLayout)
    site.registermodel(pay_models.pay_Lastschriftmandat)
    site.registermodel(pay_models.pay_IPNRecord)
    site.registermodel(pay_models.pay_Kontovorgang)

Files named ``modules/**/admin_gaetk2.py`` are automatically found an
included in the Admin Site.



Adding Datastore Models to the Admin Site
-----------------------------------------

You have to manually add all ndb models you want to have in the Admin Site
in like this to :file:`admin_gaetk2.py`::

    from gaetk2.admin import site
    from . import pay_models
    site.registermodel(pay_models.pay_Lastschriftmandat)


:class:`gaetk2.admin.modeladmin.ModelAdmin` is the main mechanism for changing the automatically generated admin interface. You intantiate it for each model you want to have administered::

    class LastschriftmandatAdmin(ModelAdmin):
        list_fields = ['mandatsreferenz', 'ist_aktiv', 'last_used',
            'kundennr', 'kontoinhaber', 'iban', 'updated_at', 'created_at']
    site.registermodel(pay_models.pay_Lastschriftmandat, LastschriftmandatAdmin)



.. todo::

    KundeForm = model_form(
        m_Kunde,
        exclude=['designator', 'empfaengernr', 'updated_at', 'created_at', 'name1', 'name2'],
        field_args={
            'owner': {'default': 'cyberlogi'},
            'email': {'validators': [express_email_validator]},
        })



.. todo::

    * rename ``application_id`` to topic everywhere
    * reimplement search


Package contents
----------------

.. automodule:: gaetk2.admin
    :members:
    :undoc-members:

.. automodule:: gaetk2.admin.modeladmin
    :members:
    :undoc-members:

.. automodule:: gaetk2.admin.views
    :members:
    :undoc-members:
