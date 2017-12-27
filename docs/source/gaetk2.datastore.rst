gaetk2\.datastore module
========================

gaetk2.datastore tries to codify a common set of expectations and usages for
gaetk2.

Inherit from ``gaetk.datastore.gaetkModel`` instead of ndb.Model to get some
added functionality. The rationale there is that e common interface and thus
admin- and programmer-time is more important than savings on space and and
processing time. To we add possible unneded database fields. You can
remove them on a case by case basis in derivered classes.

* :func:`query_iterator` - helps to iterate over big query results
* :func:`copy_entity` - can write an entity with a different key to the datastore
* :func:`write_on_change2` - basically implements conditional ``put()``
* :func:`reload_obj` - forces an object to be re-read from disk


Module contents
---------------

.. automodule:: gaetk2.datastore
    :members:
    :undoc-members:
    :show-inheritance:

