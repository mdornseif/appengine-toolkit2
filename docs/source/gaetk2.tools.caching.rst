gaetk2.tools.caching - smart caching
====================================

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


.. py:module:: gaetk2.tools.caching


Module contents
---------------

.. automodule:: gaetk2.tools.caching
    :members:
    :undoc-members:
