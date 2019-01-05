# -*- coding: utf-8 -*-
"""
structured.py - handle structured data/dicts/objects

`class Struct` from huTools is not ported.
It was used like https://pypi.org/project/stuf/

Created by Maximillian Dornseif on 2009-12-27.
Copyright (c) 2009-2011, 2015 HUDORA. MIT licensed.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import csv
import sys
import unittest
import xml.etree.cElementTree as ET

from StringIO import StringIO


# Code is based on http://code.activestate.com/recipes/573463/
def convert_dict_to_xml_recurse(parent, dictitem, listnames, sort=True):
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

                    convert_dict_to_xml_recurse(elem, listchild, listnames, sort=sort)
            else:
                if tag.startswith('@'):
                    parent.attrib[tag[1:]] = child
                else:
                    elem = ET.Element(tag)
                    parent.append(elem)
                    convert_dict_to_xml_recurse(elem, child, listnames, sort=sort)
    elif dictitem is not None:
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
    convert_dict_to_xml_recurse(root, xmldict, listnames, sort=sort)
    return root


def list2et(xmllist, root, elementname):
    """Converts a list to an ElementTree.

    See also dict2et().
    """
    basexml = dict2et({root: xmllist}, 'xml', listnames={root: elementname})
    return basexml.find(root)


def dict2xml(
    datadict, roottag='data', listnames=None, pretty=False, sort=True, outfd=None
):
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

    Sends result to `outfd` or returns a string representation if `outfd` is `None`.
    """
    if pretty:
        indent(root)

    tree = ET.ElementTree(root)
    if outfd:
        tree.write(
            outfd,
            encoding=encoding,
            xml_declaration=True,
            default_namespace=default_namespace,
        )
    else:
        fileobj = StringIO()
        tree.write(
            fileobj,
            encoding=encoding,
            xml_declaration=True,
            default_namespace=default_namespace,
        )
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
    csvwriter = csv.writer(fileobj, dialect='excel', delimiter=b'\t')

    def fixer(row):
        return [unicode(x).encode('utf-8') for x in row]

    for row in data:
        csvwriter.writerow(fixer(row))
    return fileobj.getvalue()


def dict2csv(data, datanodename='objects'):
    return list2csv(data[datanodename])


def list2xls(datalist):
    """Export a list of dicts to XLS."""
    from . import structured_xls

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
    i = '\n' + level * ' '
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + ' '
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
        data = {'guid': '3104247-7', 'menge': 7, 'artnr': '14695', 'batchnr': '3104247'}

        self.assertEqual(
            dict2xml(data, roottag='warenzugang'),
            '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<warenzugang><artnr>14695</artnr>'
            '<batchnr>3104247</batchnr><guid>3104247-7</guid><menge>7</menge></warenzugang>',
        )


def test():
    """Run tests"""
    unittest.main()
    failure_count, test_count = doctest.testmod()
    sys.exit(failure_count)


if __name__ == '__main__':
    import doctest

    test()
