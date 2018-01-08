#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.tools.caching - based on huTools.decorators and gaetk1/tools.py

Created by Maximillian Dornseif on 2007-05-10.
Copyright (c) 2007, 2015, 2018 HUDORA GmbH. All rights reserved.
"""
import threading
import time

from collections import namedtuple
from functools import update_wrapper


# from http://code.activestate.com/recipes/578078-py26-and-py30-backport-of-python-33s-lru-cache/
# with added TTL

_CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "maxsize", "currsize"])


def lru_cache(maxsize=64, typed=True, ttl=60 * 60 * 12):
    """Least-recently-used cache decorator.

    Parameters:
        maxsize (int or None): if None, the LRU features are disabled and
            the cache can grow without bound.
        typed (boolean): if `True`, arguments of different types will be
            cached separately. For example, f(3.0) and f(3) will be treated
            as distinct calls with distinct results.
        ttl (int or None): if set, cache entries are only served for `ttl` seconds.

    Arguments to the cached function must be hashable.

    View the cache statistics named tuple (hits, misses, maxsize, currsize) with
    f.cache_info().  Clear the cache and statistics with f.cache_clear().
    Access the underlying function with f.__wrapped__.

    See:  http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    Example:
        ::

            @lru_cache(maxsize=6)
            def _fetchbrands():
                query = mk_models.mk_Brand.query()
                return [brand.name for brand in query.iter() if not brand.deleted]


    """
    # Users should only access the lru_cache through its public API:
    #       cache_info, cache_clear, and f.__wrapped__
    # The internals of the lru_cache are encapsulated for thread safety and
    # to allow the implementation to change (including a possible C version).

    def decorating_function(user_function):

        cache = dict()
        maxage = dict()                 # stores the timestamp after wich result should be regeneratd
        stats = [0, 0]                  # make statistics updateable non-locally
        HITS, MISSES = 0, 1             # names for the stats fields
        make_key = _make_key
        cache_get = cache.get           # bound method to lookup key or return None
        maxage_get = maxage.get
        _len = len                      # localize the global len() function
        lock = threading.RLock()                  # because linkedlist updates aren't threadsafe
        root = []                       # root of the circular doubly linked list
        root[:] = [root, root, None, None]      # initialize by pointing to self
        nonlocal_root = [root]                  # make updateable non-locally
        PREV, NEXT, KEY, RESULT = 0, 1, 2, 3    # names for the link fields

        if maxsize == 0:

            def wrapper(*args, **kwds):
                # no caching, just do a statistics update after a successful call
                result = user_function(*args, **kwds)
                stats[MISSES] += 1
                return result

        elif maxsize is None:

            def wrapper(*args, **kwds):
                # simple caching without ordering or size limit
                key = make_key(args, kwds, typed)
                result = cache_get(key, root)   # root used here as a unique not-found sentinel
                if result is not root:
                    if time.time() <= maxage_get(key, 0):
                        stats[HITS] += 1
                        return result
                result = user_function(*args, **kwds)
                cache[key] = result
                if ttl:
                    maxage[key] = int(time.time() + ttl)
                stats[MISSES] += 1
                return result

        else:

            def wrapper(*args, **kwds):
                # size limited caching that tracks accesses by recency
                key = make_key(args, kwds, typed) if kwds or typed else args
                with lock:
                    link = cache_get(key)
                    if link is not None:
                        if time.time() <= maxage_get(key, None):
                            # record recent use of the key by moving it to the front of the list
                            root, = nonlocal_root
                            link_prev, link_next, key, result = link
                            link_prev[NEXT] = link_next
                            link_next[PREV] = link_prev
                            last = root[PREV]
                            last[NEXT] = root[PREV] = link
                            link[PREV] = last
                            link[NEXT] = root
                            stats[HITS] += 1
                            return result
                result = user_function(*args, **kwds)
                if ttl:
                    maxage[key] = int(time.time() + ttl)
                with lock:
                    root, = nonlocal_root
                    if key in cache:
                        # getting here means that this same key was added to the
                        # cache while the lock was released.  since the link
                        # update is already done, we need only return the
                        # computed result and update the count of misses.
                        pass
                    elif _len(cache) >= maxsize:
                        # use the old root to store the new key and result
                        oldroot = root
                        oldroot[KEY] = key
                        oldroot[RESULT] = result
                        # empty the oldest link and make it the new root
                        root = nonlocal_root[0] = oldroot[NEXT]
                        oldkey = root[KEY]
                        oldvalue = root[RESULT]
                        root[KEY] = root[RESULT] = None
                        # now update the cache dictionary for the new links
                        del cache[oldkey]
                        cache[key] = oldroot
                    else:
                        # put result in a new link at the front of the list
                        last = root[PREV]
                        link = [last, root, key, result]
                        last[NEXT] = root[PREV] = cache[key] = link
                    stats[MISSES] += 1
                return result

        def cache_info():
            """Report cache statistics"""
            with lock:
                return _CacheInfo(stats[HITS], stats[MISSES], maxsize, len(cache))

        def cache_clear():
            """Clear the cache and cache statistics"""
            with lock:
                cache.clear()
                root = nonlocal_root[0]
                root[:] = [root, root, None, None]
                stats[:] = [0, 0]

        wrapper.__wrapped__ = user_function
        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return wrapper
        return update_wrapper(wrapper, user_function)

    return decorating_function


class _HashedSeq(list):
    __slots__ = 'hashvalue'

    def __init__(self, tup, hash=hash):
        self[:] = tup
        self.hashvalue = hash(tup)

    def __hash__(self):
        return self.hashvalue


def _make_key(args, kwds, typed,
              kwd_mark=(object(),),
              fasttypes={int, str, frozenset, type(None)},
              sorted=sorted, tuple=tuple, type=type, len=len):
    """Make a cache key from optionally typed positional and keyword arguments"""
    key = args
    if kwds:
        sorted_items = sorted(kwds.items())
        key += kwd_mark
        for item in sorted_items:
            key += item
    if typed:
        key += tuple(type(v) for v in args)
        if kwds:
            key += tuple(type(v) for k, v in sorted_items)
    elif len(key) == 1 and type(key[0]) in fasttypes:
        return key[0]
    return _HashedSeq(key)


class lru_cache_memcache(object):
    """Use :func:`lru_cache` with memcache as an fallback.

    Arguments are the same as :func:`lru_cache`.

    Example:
        ::

            @lru_cache_memcache(ttl=3600)
            def _fetchbrands():
                query = mk_models.mk_Brand.query()
                return [brand.name for brand in query.iter() if not brand.deleted]

    """

    def __init__(self, maxsize=8, typed=True, ttl=60 * 60 * 12):
        """
        If there are decorator arguments, the function
        to be decorated is not passed to the constructor!
        """
        self.ttl = ttl
        self.maxsize = maxsize
        self.typed = typed

    def __call__(self, user_function):
        """
        If there are decorator arguments, __call__() is only called
        once, as part of the decoration process! You can only give
        it a single argument, which is the function object.
        """
        import memorised.decorators
        # first warp in memcache. `maxsize` is ignored there.
        wraped = memorised.decorators.memorise(ttl=self.ttl)(user_function)
        # and warp that in lru_cache.
        return lru_cache(maxsize=self.maxsize, typed=self.typed, ttl=self.ttl)(wraped)
