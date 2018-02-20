gaetk2.handlers - WSGI Request Handlers
=======================================

The :mod:`gaetk2.handlers` package aims to be the working horse on which
you build your application. Instead of a monolytic approach like GAETK1 we
work with mixins here. All of this is based on `webapp2 request handlers <https://webapp2.readthedocs.io/en/latest/guide/handlers.html#handlers-101>`_. Basically you overwrite ``get()`` ``post()``. In there you do a ``self.response.write('foo')``.
gaetk2 provides you with the convinience functions :meth:`~gaetk2.handlers.base.BasicHandler.return_text()` for simple replies and :meth:`~gaetk2.handlers.base.BasicHandler.render()` for rendering jinja2 templates.


:class:`~gaetk2.handlers.base.BasicHandler` provides basic functionality and template variables. :class:`~gaetk2.handlers.base.JsonBasicHandler` is specialized to produce JSON.

Usually you would use :class:`~gaetk2.handlers.DefaultHandler` for your public pages.
This includes :class:`~gaetk2.handlers.base.BasicHandler`, :class:`~gaetk2.handlers.mixins.messages.MessagesMixin`, :class:`~gaetk2.handlers.authentication.AuthenticationReaderMixin`. For JSON output you would use :class:`~gaetk2.handlers.base.JsonBasicHandler` based on :class:`~gaetk2.handlers.base.JsonBasicHandler` and :class:`~gaetk2.handlers.authentication.AuthenticationReaderMixin`.

If you want to ensure Users are authenticated use :class:`~gaetk2.handlers.AuthenticatedHandler` which extends :class:`~gaetk2.handlers.DefaultHandler` with :class:`~gaetk2.handlers.authentication.AuthenticationRequiredMixin`

Mix-Ins
-------

Mix-Ins provide specialized functionality to handlers. They are mostly
implemented using :class:`gaetk2.handlers.basic.BasicHandler` :ref:`Hook Mechanism <handler-hook-mechanism>`. Some Mix-Ins provide just methods manually called by your method handlers.

* :class:`~gaetk2.handlers.mixins.paginate.PaginateMixin` provides pagination of ndb-Queries.
* :class:`gaetk2.handlers.mixins.messages.MessagesMixin` provide short term feedback to a user displayed on the "next page". The concept is similar to `flask's "Message flashing" <http://flask.pocoo.org/docs/0.12/patterns/flashing/>`_.

General Flow
------------

Based on you :file:`app.yaml` Google App Engine executes a WSGI Application. Usually the Application is wraped by a WSGI middleware. This happens via :func:`webapp_add_wsgi_middleware` in :file:`appengine_config.py`. Usually via :mod:`gaetk2.wsgi` session management and error reporting (see :ref:`error-handling`) are added.

Usually the `WSGI Application` is :class:`gaetk2.applicationWSGIApplication` which finds out the handler to call via the `Route`, calls the handler and does a lot of error handling and information gathering. No user-serviceable inside.

All your handlers should inherit their main functionality from :class:`gaetk2.handler.base.BasicHandler` which is a heavily modified `webapp2.RequestHandler <http://webapp2.readthedocs.io/en/latest/api/webapp2.html#webapp2.RequestHandler>`_.

Usually you will overwrite ``get()``, ``post()``, ``head()``, ``options()``, ``put()``, ``delete()`` or ``trace()`` to handle the respective HTTP-Methods. See the `webapp2 Request Handler Documentation <http://webapp2.readthedocs.io/en/latest/guide/handlers.html>`_ for an overview.

To allow easy subclassing and Multiple inheritance :class:`~gaetk2.handler.base.BasicHandler` will ensure that a list of hook function in all parent classes is called. Before the request the following functions are called:

1. ``pre_authentication_hook()`` - done before any authentication is done. E.g. redirecting moved URLs. ``__init__()``-like setup.
2. ``authentication_preflight_hook()`` - used by :class:`~gaetk2.handlers.authentication.AuthenticationReaderMixin` to load authentication Information from the request headers.
3. ``authentication_hook()`` - to handle and ensure Authentication. Used by :class:`~gaetk2.handlers.authentication.AuthenticationRequiredMixin` to ensure that the current user is authenticated.
4. ``authorisation_hook()`` - to check that the authenticated user is allowed to do the request.
5. ``method_preperation_hook()`` - this is probably the most often overwritten hook. It is meant to load data for a set of derived handlers. See below for examples.
6. **The HTTP request method** - usually ``get()`` or ``post()``
7. ``response_overwrite()`` - this is not a hook so without ``super()`` magic only the top level implementation of the method resolution order (MRO) is called - like usual in Python classes. This is used to transform the response to the client. For example in :class:`~gaetk2.handler.base.JsonBasicHandler`.
8. ``finished_hook()`` - called, even if a HTTP-Exception with code < 500 happens. Used to flush buffers etc.
9. ``handle_exception()`` - is called in case of an Exception. See `webapp2 documentation <http://webapp2.readthedocs.io/en/latest/api/webapp2.html#webapp2.RequestHandler.handle_exception>`_.


When you call :func:`~gaetk2.handler.base.BasicHandler.render()` :func:`~gaetk2.handler.base.BasicHandler.build_context()` in all parent classes and Mix-Ins is called to construct the render context.


The following Sample Implementation implements (parts) of a shopping cart to illustrate usage::

    from gaetk2 import exc
    from gaetk2.handlers import AuthenticatedHandler
    from gaetk2.application import WSGIApplication, Route

    class AbstractSiteHandler(AuthenticatedHandler):
        """General stuff used all over the site."""

        def pre_authentication_hook(self, method_name, *args, **kwargs):
            self.analytics = analytics.Client()

        def build_context(self, values):
            if 'title' not in values:
                values['title'] = 'My Cool Site'
            return values

        def finished_hook(self, *args, **kwargs):
            self.analytics.flush()

    class BaseCartHandler(AbstractSiteHandler):
        """Functionality used for the cart."""

        def method_preperation_hook(self, method_name, *args, **kwargs):
            self.cart = self.session.get('cart3', {'items': []})

        def finished_hook(self, *args, **kwargs):
            self.session['cart3'] = self.cart  # this marks session as dirty
            # store cart len so client side code can read it
            cart3_len = str(len(self.cart.get('items', [])))
            self.response.set_cookie('cart3_len', cart3_len, max_age=7*24*60*60)

        def handle_exception(self, e, debug):
            """On Exceptions flush the cart to provide a clean 'reboot'."""
            if not getattr(e, 'code', 500) < 500:
                # no fluch on redirect etc.
                self.flush_cart()
            raise


    class AddToCartHandler(BaseCartHandler):

        def get(self):
            sku = self.request.get('sku', '')
            menge = int(self.request.get('menge_%s' % sku, 1))
            self.cart['items'].append((sku, menge))
            raise exc.HTTP302_Found(location='/cart3')


    class UpdateCartHandler(BaseCartHandler):

        def get(self):
            self.update(self.request.GET)
            raise exc.HTTP302_Found(location='/cart3')

        def post(self):
            self.update(self.request.POST)
            if self.request.POST.get('action') == 'checkout':
                raise exc.HTTP302_Found(location='/cart3/checkout/')
            raise exc.HTTP302_Found(location='/cart3')


    class CheckoutHandler(BaseCartHandler):

        def get(self):
            self.render(
                dict(title='Your cart', cart=self.cart),
                'cart3/checkout.html')
            self.analytics.track('Checkout Started')

        def post(self):
            orderid = generate_order(self.cart)
            self.cart = {'items': []}
            defer(inform_about_order, orderid)
            # from :class:`~gaetk2.handlers.mixins.messages.MessagesMixin`
            self.add_message(
                'success', jinja2.Markup('Order {} created.'.format(orderid)))
            self.track('Order Completed')
            raise exc.HTTP302_Found(location='/')


    application = WSGIApplication([
        Route('/cart3/addtocart/', AddToCartHandler),
        Route('/cart3/updatecart/', UpdateCartHandler),
        Route('/cart3/checkout/', CheckoutHandler),
        Route('/cart3/', ShowCartHandler),
        Route('/cart3.<fmt>', ShowCartHandler),
    ])


An other common usage is that you have a group of pages with a common URL prefix and all of them extracting information from the U|RL, e.g. customer number. So you might have::

    * /k/<userid>/dettings/
    * /k/<userid>/orders/
    * /k/<userid>/orders/<orderid>
    * /k/<userid>/orders/<orderid>/invoice.pdf

TBD

gaetk2\.handlers package
------------------------

.. automodule:: gaetk2.handlers
    :members:
    :undoc-members:
.. automodule:: gaetk2.handlers.base
    :members:
    :private-members:
.. automodule:: gaetk2.handlers.mixins.paginate
    :members:
.. automodule:: gaetk2.handlers.mixins.messages
    :members:
.. automodule:: gaetk2.handlers.mixins.multirender
    :members:
