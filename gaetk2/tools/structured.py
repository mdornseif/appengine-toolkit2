# encoding: utf-8
"""
structured.py - handle structured data/dicts/objects

Created by Maximillian Dornseif on 2009-12-27.
Copyright (c) 2009-2011, 2015 HUDORA. All rights reserved.
"""
import csv
import unittest
import xml.etree.cElementTree as ET

from StringIO import StringIO


# Basic conversation goal here is converting a dict to an object allowing
# more comfortable access. `Struct()` and `make_struct()` are used to archive
# this goal.
# See http://stackoverflow.com/questions/1305532/convert-python-dict-to-object for the inital Idea
#
# The reasoning for this is the observation that we ferry arround hundreds of dicts via JSON
# and accessing them as `obj['key']` is tiresome after some time. `obj.key` is much nicer.
class Struct(object):
    """Emulate a cross over between a dict() and an object()."""

    def __init__(self, entries, default=None, nodefault=False):
        # ensure all keys are strings and nothing else
        entries = dict([(str(x), y) for x, y in entries.items()])
        self.__dict__.update(entries)
        self.__default = default
        self.__nodefault = False if default is not None else nodefault

    def __getattr__(self, name):
        """Emulate Object access.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.a
        'b'
        >>> obj.foobar
        'c'

        `hasattr` results in strange behaviour if you give a default value. This might change in the future.
        >>> hasattr(obj, 'a')
        True
        >>> hasattr(obj, 'foobar')
        True
        """
        if name.startswith('_'):
            # copy expects __deepcopy__, __getnewargs__ to raise AttributeError
            # see http://groups.google.com/group/comp.lang.python/browse_thread/thread/6ac8a11de4e2526f/
            # e76b9fbb1b2ee171?#e76b9fbb1b2ee171
            raise AttributeError("'<Struct>' object has no attribute '%s'" % name)
        if self.__nodefault:
            raise AttributeError("'<Struct>' object has no attribute '%s'" % name)
        return self.__default

    def __getitem__(self, key):
        """Emulate dict like access.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj['a']
        'b'

        While the standard dict access via [key] uses the default given when creating the struct,
        access via get(), results in None for keys not set. This might be considered a bug and
        should change in the future.
        >>> obj['foobar']
        'c'
        >>> obj.get('foobar')
        'c'
        """
        # warnings.warn("dict_accss[foo] on a Struct, use object_access.foo instead",
        #                DeprecationWarning, stacklevel=2)
        if self.__nodefault:
            return self.__dict__[key]
        return self.__dict__.get(key, self.__default)

    def get(self, key, default=None):
        """Emulate dictionary access.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.get('a')
        'b'
        >>> obj.get('foobar')
        'c'
        """
        if key in self.__dict__:
            return self.__dict__[key]
        if not self.__nodefault:
            return self.__default
        return default

    def __contains__(self, item):
        """Emulate dict 'in' functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> 'a' in obj
        True
        >>> 'foobar' in obj
        False
        """
        return item in self.__dict__

    def __nonzero__(self):
        """Returns whether the instance evaluates to False"""
        return bool(self.items())

    def has_key(self, item):
        """Emulate dict.has_key() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.has_key('a')
        True
        >>> obj.has_key('foobar')
        False
        """
        return item in self

    def items(self):
        """Emulate dict.items() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.items()
        [('a', 'b')]
        """
        return [(k, v) for (k, v) in self.__dict__.items() if not k.startswith('_Struct__')]

    def keys(self):
        """Emulate dict.keys() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.keys()
        ['a']
        """
        return [k for (k, _v) in self.__dict__.items() if not k.startswith('_Struct__')]

    def values(self):
        """Emulate dict.values() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.values()
        ['b']
        """
        return [v for (k, v) in self.__dict__.items() if not k.startswith('_Struct__')]

    def __repr__(self):
        return "<Struct: %r>" % dict(self.items())

    def as_dict(self):
        """Return a dict representing the content of this struct."""
        return self.__dict__


def make_struct(obj, default=None, nodefault=False):
    """Converts a dict to an object, leaves objects untouched.

    Someting like obj.vars() = dict() - Read Only!

    >>> obj = make_struct(dict(foo='bar'))
    >>> obj.foo
    'bar'

    `make_struct` leaves objects alone.
    >>> class MyObj(object): pass
    >>> data = MyObj()
    >>> data.foo = 'bar'
    >>> obj = make_struct(data)
    >>> obj.foo
    'bar'

    `make_struct` also is idempotent
    >>> obj = make_struct(make_struct(dict(foo='bar')))
    >>> obj.foo
    'bar'

    `make_struct` recursively handles dicts and lists of dicts
    >>> obj = make_struct(dict(foo=dict(bar='baz')))
    >>> obj.foo.bar
    'baz'

    >>> obj = make_struct([dict(foo='baz')])
    >>> obj
    [<Struct: {'foo': 'baz'}>]
    >>> obj[0].foo
    'baz'

    >>> obj = make_struct(dict(foo=dict(bar=dict(baz='end'))))
    >>> obj.foo.bar.baz
    'end'

    >>> obj = make_struct(dict(foo=[dict(bar='baz')]))
    >>> obj.foo[0].bar
    'baz'
    >>> obj.items()
    [('foo', [<Struct: {'bar': 'baz'}>])]
    """
    if isinstance(obj, Struct):
        return obj
    if hasattr(obj, 'iteritems') and (not hasattr(obj, '__dict__')):
        # this should be a dict
        struc = Struct(obj, default, nodefault)
        # handle recursive sub-dicts and lists
        for key, val in obj.iteritems():
            if isinstance(val, (basestring, int, long)):
                # optimisation saving a function call
                setattr(struc, key, val)
            else:
                setattr(struc, key, make_struct(val, default, nodefault))
        return struc
    elif hasattr(obj, '__getitem__'):
        # a list
        ret = []
        for val in obj:
            if isinstance(val, (basestring, int, long)):
                # optimisation saving a function call
                ret.append(val)
            else:
                ret.append(make_struct(val, default, nodefault))
        return ret
    else:
        return obj


# Code is based on http://code.activestate.com/recipes/573463/
def _convert_dict_to_xml_recurse(parent, dictitem, listnames, sort=True):
    """Helper Function for XML conversion."""

    if isinstance(dictitem, list):
        raise TypeError('Unable to convert bare lists')

    if isinstance(dictitem, dict):
        items = dictitem.iteritems()
        if sort:
            items = sorted(items)
        for (tag, child) in items:
            if isinstance(child, list):
                # iterate through the array and convert
                itemname = listnames.get(tag, 'item')
                if itemname is not None:
                    listelem = ET.SubElement(parent, tag)
                else:
                    listelem = parent

                for listchild in child:
                    if itemname is not None:
                        elem = ET.SubElement(listelem, itemname)
                    else:
                        elem = ET.SubElement(listelem, tag)

                    _convert_dict_to_xml_recurse(elem, listchild, listnames, sort=sort)
            else:
                if tag.startswith('@'):
                    parent.attrib[tag[1:]] = child
                else:
                    elem = ET.Element(tag)
                    parent.append(elem)
                    _convert_dict_to_xml_recurse(elem, child, listnames, sort=sort)
    elif not dictitem is None:
        parent.text = unicode(dictitem)


def dict2et(xmldict, roottag='data', listnames=None, sort=True):
    """Converts a dict to an ElementTree.

    Converts a dictionary to an XML ElementTree Element::

    >>> data = {"nr": "xq12", "positionen": [{"m": 12}, {"m": 2}]}
    >>> root = dict2et(data)
    >>> ET.tostring(root)
    '<data><nr>xq12</nr><positionen><item><m>12</m></item><item><m>2</m></item></positionen></data>'

    Per default everything is put in an enclosing '<data>' element. Also per default lists are converted
    to collections of `<item>` elements. By provding a mapping between list names and element names,
    you can generate different elements:

    >>> data = {"positionen": [{"m": 12}, {"m": 2}]}
    >>> root = dict2et(data, roottag='xml')
    >>> ET.tostring(root)
    '<xml><positionen><item><m>12</m></item><item><m>2</m></item></positionen></xml>'

    >>> root = dict2et(data, roottag='xml', listnames={'positionen': 'position'})
    >>> ET.tostring(root)
    '<xml><positionen><position><m>12</m></position><position><m>2</m></position></positionen></xml>'

    If you explictly set the elementname to None, a flat list is created:
    >>> root = dict2et(data, roottag='flat', listnames={'positionen': None})
    >>> ET.tostring(root)
    '<flat><positionen><m>12</m></positionen><positionen><m>2</m></positionen></flat>'

    >>> data = {"kommiauftragsnr":2103839, "anliefertermin":"2009-11-25", "prioritaet": 7,
    ... "ort": u"Hücksenwagen",
    ... "positionen": [{"menge": 12, "artnr": "14640/XL", "posnr": 1},],
    ... "versandeinweisungen": [{"guid": "2103839-XalE", "bezeichner": "avisierung48h",
    ...                          "anweisung": "48h vor Anlieferung unter 0900-LOGISTIK avisieren"},
    ... ]}

    >>> print ET.tostring(dict2et(data, 'kommiauftrag',
    ... listnames={'positionen': 'position', 'versandeinweisungen': 'versandeinweisung'}))
    ...  # doctest: +SKIP
    '''<kommiauftrag>
    <anliefertermin>2009-11-25</anliefertermin>
    <positionen>
        <position>
            <posnr>1</posnr>
            <menge>12</menge>
            <artnr>14640/XL</artnr>
        </position>
    </positionen>
    <ort>H&#xC3;&#xBC;cksenwagen</ort>
    <versandeinweisungen>
        <versandeinweisung>
            <bezeichner>avisierung48h</bezeichner>
            <anweisung>48h vor Anlieferung unter 0900-LOGISTIK avisieren</anweisung>
            <guid>2103839-XalE</guid>
        </versandeinweisung>
    </versandeinweisungen>
    <prioritaet>7</prioritaet>
    <kommiauftragsnr>2103839</kommiauftragsnr>
    </kommiauftrag>'''

    Sorting can be disabled which is only useful for collections.OrderedDict.
    """

    if not listnames:
        listnames = {}
    root = ET.Element(roottag)
    _convert_dict_to_xml_recurse(root, xmldict, listnames, sort=sort)
    return root


def list2et(xmllist, root, elementname):
    """Converts a list to an ElementTree.

        See also dict2et()
    """

    basexml = dict2et({root: xmllist}, 'xml', listnames={root: elementname})
    return basexml.find(root)


def dict2xml(datadict, roottag='data', listnames=None, pretty=False, sort=True, outfd=None):
    """Converts a dictionary to an UTF-8 encoded XML string.

    See also dict2et()
    """
    root = dict2et(datadict, roottag, listnames, sort=sort)
    return to_string(root, pretty=pretty, outfd=outfd)


def list2xml(datalist, roottag, elementname, pretty=False, outfd=None):
    """Converts a list to an UTF-8 encoded XML string.

    See also dict2et()
    """
    root = list2et(datalist, roottag, elementname)
    return to_string(root, pretty=pretty, outfd=outfd)


def to_string(root, encoding='utf-8', pretty=False, default_namespace=None, outfd=None):
    """Converts an ElementTree to a string.

    Sends result to `outfd` or returns a string representation if `outfd` is `None`."""

    if pretty:
        indent(root)

    tree = ET.ElementTree(root)
    if outfd:
        tree.write(
            outfd,
            encoding=encoding,
            xml_declaration=True,
            default_namespace=default_namespace)
    else:
        fileobj = StringIO()
        tree.write(
            fileobj,
            encoding=encoding,
            xml_declaration=True,
            default_namespace=default_namespace)
        return fileobj.getvalue()


def dict2tabular(items, fieldorder=None):
    """Converts a dict of dicts to a list of lists."""
    if not fieldorder:
        fieldorder = []
    allfieldnames = set()
    for item in items.values():
        allfieldnames.update(item.keys())
    for fielname in fieldorder:
        allfieldnames.remove(fielname)
    fieldorder = fieldorder + list(sorted(allfieldnames))
    yield fieldorder
    for item in items.values():
        yield [item.get(key, '') for key in fieldorder]


def list2tabular(items, fieldorder=None):
    """Converts a list of dicts to a list of lists."""
    if not fieldorder:
        fieldorder = []
    allfieldnames = set()
    for item in items:
        allfieldnames.update(item.keys())
    for fielname in fieldorder:
        allfieldnames.remove(fielname)
    fieldorder = fieldorder + list(sorted(allfieldnames))
    yield fieldorder
    for item in items:
        yield [item.get(key, '') for key in fieldorder]


def x2tabular(datalist):
    if hasattr(datalist, 'items'):
        return dict2tabular(datalist)
    else:
        return list2tabular(datalist)


def list2csv(datalist):
    """Export a list of dicts to CSV."""
    data = x2tabular(datalist)
    fileobj = StringIO()
    csvwriter = csv.writer(fileobj, dialect='excel', delimiter='\t')
    fixer = lambda row: [unicode(x).encode('utf-8') for x in row]
    for row in data:
        csvwriter.writerow(fixer(row))
    return fileobj.getvalue()


def dict2csv(data, datanodename='objects'):
    return list2csv(data[datanodename])


def list2xls(datalist):
    """Export a list of dicts to XLS."""
    import structured_xls
    data = x2tabular(datalist)
    writer = structured_xls.XLSwriter()
    for row in data:
        writer.writerow(row)
    return writer.getvalue()


def dict2xls(data, datanodename='objects'):
    return list2xls(data[datanodename])


# From http://effbot.org/zone/element-lib.htm
# prettyprint: Prints a tree with each node indented according to its depth. This is
# done by first indenting the tree (see below), and then serializing it as usual.
# indent: Adds whitespace to the tree, so that saving it as usual results in a prettyprinted tree.
# in-place prettyprint formatter

def indent(elem, level=0):
    """XML prettyprint: Prints a tree with each node indented according to its depth."""
    i = "\n" + level * " "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + " "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent(child, level + 1)
        if child:
            if not child.tail or not child.tail.strip():
                child.tail = i
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i



class TestCase(unittest.TestCase):
    """Simple Unittests"""

    def test_dict2xml(self):
        """Most basic test for dict2xml"""

        data = {"guid": "3104247-7",
                "menge": 7,
                "artnr": "14695",
                "batchnr": "3104247"}

        self.assertEqual(
            dict2xml(data, roottag='warenzugang'),
            '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<warenzugang><artnr>14695</artnr>'
            '<batchnr>3104247</batchnr><guid>3104247-7</guid><menge>7</menge></warenzugang>')

    def test_struct(self):
        struct = make_struct({
            'item1': 'string',
            'item2': ['dies', 'ist', 'eine', 'liste'] * 100,
            'item3': dict(dies=1, ist=2, ein=3, dict=4),
            'item4': 10,
            'item5': [dict(dict=1, in_einer=2, liste=3)] * 100})

        self.assertEqual(struct.item1, 'string')

    def test_struct_default(self):
        struct = make_struct({}, default=u'*')
        self.assertEqual(struct.non_existing, u'*')

    def test_struct_nodefault(self):
        struct = make_struct({}, nodefault=True)
        with self.assertRaises(AttributeError):
            self.assertFalse(struct.non_existing)

    def test_struct_default_nodefault(self):
        struct = make_struct({}, default=u'?', nodefault=True)
        self.assertEqual(struct.non_existing, u'?')


def test():
    """Run tests"""
    unittest.main()
    failure_count, test_count = doctest.testmod()
    sys.exit(failure_count)


if __name__ == '__main__':
    import doctest
    test()
