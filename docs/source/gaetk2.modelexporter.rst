gaetk2\.modelexporter module
============================

This module provides functionality to write datastore Models or Queries
to the client as XLS or CSV Files. Usage like this in your handler::

    exporter = ModelExporter(ic_AuftragsPosition)
    filename = '%s-%s.xls' % (compat.xdb_kind(ic_AuftragsPosition), datetime.datetime.now())
    handler.response.headers['Content-Type'] = 'application/msexcel'
    handler.response.headers['content-disposition'] = \
        'attachment; filename=%s' % filename
    exporter.to_xls(handler.response)
    # or:
    # exporter.to_csv(handler.response)


Module contents
---------------

.. automodule:: gaetk2.modelexporter
    :members:
    :undoc-members:
    :show-inheritance:

