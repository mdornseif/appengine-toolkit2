gaetk2.handlers - WSGI Request Handlers
=======================================

The :mod:`gaetk2.handlers` package aims to be the working horse on which
you build your application. Instead of a monolytic approach like GAETK1 we
work with mixins here. All of this is based on `webapp2 request handlers <https://webapp2.readthedocs.io/en/latest/guide/handlers.html#handlers-101>`_. Basically you overwrite ``get()`` ``post()``. In there you do a ``self.response.write('foo')``.
gaetk2 provides you with the convinience functions :meth:`gaetk2.handlers.basic.BasicHandler.return_text` for simple replies and :meth:`gaetk2.handlers.basic.BasicHandler.render` for rendering jinja2 tempates.


* :class:`gaetk2.handlers.basic.BasicHandler` provides basic functionality and template variables. :class:`~gaetk2.handlers.basic.JsonBasicHandler` is specialized to produce JSON.
* :class:`gaetk2.handlers.authentication.AuthenticationReaderMixin`
* :class:`gaetk2.handlers.authentication.AuthenticationRequiredMixin`
* :class:`gaetk2.handlers.base.BasicHandler`
* :class:`gaetk2.handlers.base.JsonBasicHandler`
* :class:`gaetk2.handlers.mixins.messages.MessagesMixin`

Usually you would use :class:`~gaetk2.handlers.DefaultHandler` for your public pages.
This includes :class:`~gaetk2.handlers.base.BasicHandler`, :class:`~gaetk2.handlers.mixins.messages.MessagesMixin`, :class:`~gaetk2.handlers.authentication.AuthenticationReaderMixin`. For JSON output ypou would use :class:`~gaetk2.handlers.base.JsonBasicHandler` based on :class:`~gaetk2.handlers.base.JsonBasicHandler` and :class:`~gaetk2.handlers.authentication.AuthenticationReaderMixin`.

If you want to ensure Users are authenticated use :class:`~gaetk2.handlers.AuthenticatedHandler` which extends :class:`~gaetk2.handlers.DefaultHandler` with :class:`~gaetk2.handlers.authentication.AuthenticationRequiredMixin`


gaetk2\.handlers package
------------------------

.. automodule:: gaetk2.handlers.base
    :members:
    :private-members:
.. automodule:: gaetk2.handlers
    :members:
    :undoc-members:
