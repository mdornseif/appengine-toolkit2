.. py:module:: gaetk2.tools

gaetk2.tools Package
====================

Thees package contains functionality mostly used intenally.

.. contents::

.. todo::

    * ids.py
    * hujson2.py
    * http.py
    * config.py
    * auth0tools.py
    * sentry.py


gaetk2.tools.caching - smart caching
------------------------------------

Caching on Google App Engine makes your application faster and cheaper.
While for `key.get()` operations ndp provides caching for you, queries are
nwver cached by the datastore infrastructure.

After years of experimentation we come to the conclusion that you should
always use some time-based cache invalidation. This will result in "eventual
consitency" even if you do not get your cache invalidation strategy perfectly
right.

We provide :func:`lru_cache()` with a default TTL of 12 hours. It does local instance memory caching and is an extension of :mod:`functools` from
Python 3.3.

:func:`lru_cache_memcache()` is an extension using a two-level strategy:
content which is not found in the local instance cache is pulled from the
shared memcache. Cache entries are not shared between different versions of
your application.

It is suggested, that you use a relatively small `maxsize` with :func:`lru_cache_memcache()` to save on instance memory.


.. automodule:: gaetk2.tools.caching
    :members:
    :undoc-members:




gaetk2\.tools\.datetools
------------------------

.. todo::

    * Explain what gaetk2.tools.datetools is for



.. automodule:: gaetk2.tools.datetools
    :members:
    :undoc-members:



gaetk2.tools.unicode - string handling
--------------------------------------

This are functions which help to handle data from a pre-Unicode world.
Much of this code is acient and has no use in a worl where JSON and XML
ensure somewhat clean encoding. But still there are so many places where
you are allowd to send only ASCII subsets.


Data Cleanup
^^^^^^^^^^^^

* :func:`de_noise` - removed Unicode Characters which normally have no place in buiseness documents (eg street names). This includes Emojii but also protected spaces unusual quotation marks etc. This data is usually included dut to cut and paste errors. Read source to see what is replaced.
* :func:`de_umlaut` - converts data to plain ASCII while converting german Umlauts to something reasonable.
* :func:`de_utf8` - "repair" wrongly decoded UTF-8.


Number Conversion
^^^^^^^^^^^^^^^^^

:func:`num_encode` and :func:`num_decode` convert arbitrary long numbers to strings and back again. Works nice for datastore IDs. Uses base 62 (lowwer and upper letters and numbers) to get a compact representation.

:func:`num_encode_uppercase` uses base36 which is less compact but case insensitive.

You can use these functions to getsomewhat easy to tipe compact datastore ids::

    class SomeEntity(ndb.Model):
        nr = ndb.ComputedProperty(lambda num_encode(self: self.key.id()) if self.key.id() else '?')


Module contents
^^^^^^^^^^^^^^^

.. automodule:: gaetk2.tools.unicode
    :members:
    :undoc-members:


gaetk2\.tools\.structured_xls package
-------------------------------------

.. todo::

    * Explain what gaetk2.tools.structured_xls is for


.. automodule:: gaetk2.tools.structured_xls
    :members:
    :undoc-members:


