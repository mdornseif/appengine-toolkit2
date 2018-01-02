#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.modelexporter Export db/ndb Tables / Models.

Created by Dr. Maximillian Dornseif on 2014-12-10.
Copyright (c) 2014-2017 HUDORA GmbH. MIT Licensed.
"""
import csv
import datetime
import time

from gaetk2.datastore import query_iterator
from gaetk2.tools.structured_xls import XLSwriter


class ModelExporter(object):
    """Export all entities of a Model as XLS, CSV.

    :param ndb.Model model: Model to be exported, required.
    :param query: Query to limit the records to be exported.
    :type query: ndb.Query or None
    :param str uid: Encodes the person doing the Export in the Output.
    :param only: List of Field-/Propertynames to export
    :type only: list(str) or None
    :param ignore: List of Field-/Propertynames not to export
    :type ignore: list(str) or None
    :param additional_fields: The priority of the message, can be a number 1-5
    :type additional_fields: list(str) or None
    :param int maxseconds: Truncate exporting after this many seconds.

    Intatiate a :class:`ModelExporter` and call :meth:`to_xls` or :meth:`to_csv`
    to get an export of the Entities on Disk.

    """

    def __init__(self, model,
                 query=None, uid='', only=None, ignore=None, additional_fields=None, maxseconds=40):

        self.model = model
        self.uid = uid
        self.maxseconds = maxseconds
        if query is None:
            self.query = model.query()
        else:
            self.query = query

        self.only = only
        self.ignore = ignore
        self.additional_fields = additional_fields

    @property
    def fields(self):
        """Property with list of files to export.

        Can be overwritten. Current implementation is cached."""
        if not hasattr(self, '_fields'):
            fields = []
            props = self.model._properties
            for prop in props.values():
                name = prop._name
                if self.only:
                    if name in self.only:
                        fields.append((prop._creation_counter, name))
                elif self.ignore:
                    if name not in self.ignore:
                        fields.append((prop._creation_counter, name))
                else:
                    fields.append((prop._creation_counter, name))

            if self.additional_fields:
                fields.extend((999, n) for n in self.additional_fields)

            self._fields = [n for (_, n) in sorted(fields)]

        return self._fields

    def create_header(self, output, fixer=lambda x: x):
        """Generates one or more header rows in `output`.

        Can be overwritten.
        """
        if self.uid:
            output.writerow(fixer([
                '# Exported at:',
                str(datetime.datetime.now()),
                'for',
                self.uid]))
        else:
            output.writerow(fixer(['# Exported at:', str(datetime.datetime.now())]))
        output.writerow(fixer(self.fields + [u'Datenbankschlüssel']))

    def create_row(self, output, data, fixer=lambda x: x):
        """Generates a single output row.

        Can be overwritten.
        """
        row = []
        for field in self.fields:
            attr = getattr(data, field)
            if callable(attr):
                tmp = attr()
            else:
                tmp = attr
            row.append(unicode(tmp))
        if callable(data.key):
            row.append(unicode(data.key()))
        else:
            row.append(unicode(data.key.urlsafe()))
        output.writerow(fixer(row))

    def create_csvwriter(self, fileobj):
        """Generates an outputstream from fileobj.

        Can be overwritten to change the
        :class:`csv.writer`
        `csv.writer <https://docs.python.org/2/library/csv.html>`_
        options.
        """
        return csv.writer(fileobj, dialect='excel', delimiter='\t')

    def to_csv(self, fileobj):
        """Generate CSV in fileobj.

        Overwrite :meth:`create_csvwriter()` to change CSV Style."""
        csvwriter = self.create_csvwriter(fileobj)

        def _fixer(row):
            """:module:`csv` does not work with unicode, so encode to UTF-8."""
            return [unicode(x).encode('utf-8') for x in row]

        self.create_header(csvwriter, _fixer)
        start = time.time()
        for row in query_iterator(self.query):
            self.create_row(csvwriter, row, _fixer)
            if time.time() - self.maxseconds > start:
                # creation took to long, truncate output
                csvwriter.writerow(['truncated ...'])
                break

    def to_xls(self, fileobj):
        """generate XLS in fileobj"""
        xlswriter = XLSwriter()
        self.create_header(xlswriter)
        start = time.time()
        for row in query_iterator(self.query):
            self.create_row(xlswriter, row)
            if time.time() - self.maxseconds > start:
                # creation took to long, truncate output
                xlswriter.writerow(['truncated ...'])
                break
        # :class:`XLSwriter` needs a finalisation.
        xlswriter.save(fileobj)
