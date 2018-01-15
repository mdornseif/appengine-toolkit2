HOWTO - Guides
==============

A collection of examples and best practices.


30x Redirect
------------

Usually you just `raise` an 30x Exception like this::

    from gaetk2.handlers import DefaultHandler
    from gaetk2.application import WSGIApplication, Route
    from gaetk2 import exc

    class ExampleHandler(DefaultHandler):
        def get(self):
            raise exc.HTTP302_Found(location='/bar')

    app = WSGIApplication([Route('/foo', ExampleHandler)])


404 Not Found
-------------

Like a `30x Redirect`_ you just raise :exc:`~exc.HTTP404_NotFound`::

    class ExampleHandler(DefaultHandler):
        def get(self, customernumber):
            obj = Customer.get_by_id(customernumber)
            if not obj:
                raise exc.HTTP404_NotFound('')
            self.return_text('found')

But this common case can be handled much more elegant with :func:`gaetk2.helpers.check404()`::

    from gaetk2.helpers import check404

    class ExampleHandler(DefaultHandler):
        def get(self, customernumber):
            obj = check404(Customer.get_by_id(customernumber))
            self.return_text('found')

This will `raise` :exc:`~exc.HTTP404_NotFound` whenever ``obj`` evaluates
to ``False``.


.. todo::

    * How to implement nice error pages
