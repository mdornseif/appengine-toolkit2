gaetk2.tools.unicode - string handling
======================================

This are functions which help to handle data from a pre-Unicode world.
Much of this code is acient and has no use in a worl where JSON and XML
ensure somewhat clean encoding. But still there are so many places where
you are allowd to send only ASCII subsets.

.. py:module:: gaetk2.tools.unicode

.. contents::


Data Cleanup
------------

* :func:`deNoise` - removed Unicode Characters which normally have no place in buiseness documents (eg street names). This includes Emojii but also protected spaces unusual quotation marks etc. This data is usually included dut to cut and paste errors. Read source to see what is replaced.
* :func:`deUmlaut` - converts data to plain ASCII while converting german Umlauts to something reasonable. 
* :func:`deUTF8` - "repair" wrongly decoded UTF-8.


Number Conversion
-----------------

:func:`num_encode` and :func:`num_decode` convert arbitrary long numbers to strings and back again. Works nice for datastore IDs. Uses base 62 (lowwer and upper letters and numbers) to get a compact representation.

:func:`num_encode_uppercase` uses base36 which is less compact but case insensitive.

You can use these functions to getsomewhat easy to tipe compact datastore ids::

    class SomeEntity(ndb.Model):
        nr = ndb.ComputedProperty(lambda num_encode(self: self.key.id()) if self.key.id() else '?')


Module contents
---------------

.. automodule:: gaetk2.tools.unicode
    :members:
    :undoc-members:
    :show-inheritance:
