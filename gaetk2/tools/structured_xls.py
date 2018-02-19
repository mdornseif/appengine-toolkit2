#!/usr/bin/env python
# encoding: utf-8
"""
huTools/structured_xls.py - csv.py compatible Excel Export.

Created by Maximillian Dornseif on 2014-02-24.
Copyright (c) 2014, 2015, 2017 HUDORA. All rights reserved.
"""
import datetime
from cStringIO import StringIO

from xlwt import Workbook, XFStyle

datestyle = XFStyle()
datestyle.num_format_str = 'YYYY-MM-DD'


class XLSwriter(object):
    """:mod:`csv` - Module compatible Interface to generate excel files.

    ... but you have to call :meth:`save()` oder :meth:`getvalue()`
    to generate the final XLS file.

    :param output: *optional* File-Like Object for :func:`save` to export to.
    :type output: file or None
    :param str sheetname: *optional* Name of the single Worksheet we export to.

    Uses the deprecated `xlwt <https://pypi.python.org/pypi/xlwt>`_.

    Usage::

        xlswriter = XLSwriter()
        xlswriter.writerow(['foo', 1, 2])
        xlswriter.writerow(['bar', 3, datetime.date.today()])
        xlswriter.save(open('test.xls')
    """

    # openpyxl or xlsxwriter might be better output alternatives nowadays
    def __init__(self, output=None, sheetname='This Sheet'):
        self.book = Workbook()
        self.sheet = self.book.add_sheet(sheetname)
        self.rownum = 0
        self.output = output

    def writerow(self, row):
        """Eine Zeile schreiben. Row ist eine Liste von Werten."""
        col = 0
        for coldata in row:
            if isinstance(coldata, (datetime.datetime, datetime.date, datetime.time)):
                self.sheet.write(self.rownum, col, coldata, datestyle)
            else:
                if len(unicode(coldata)) > 8192:
                    # übergroße Felder RADIKAL verkürzen
                    self.sheet.write(self.rownum, col, "%s ..." % unicode(coldata)[:64])
                else:
                    self.sheet.write(self.rownum, col, coldata)
            col += 1
        self.rownum += 1

    def save(self, fd=None):
        """Write rendered XLS file to `fd` or `self.output`."""
        if not fd:
            fd = self.output
        assert fd
        self.book.save(fd)
        return fd

    def getvalue(self):
        """Returns rendered XLS file as a :class:`StringIO()`."""
        fd = StringIO()
        self.book.save(fd)
        return fd.getvalue()
