#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.handlers.mixins.multirender - render youtput in different formats

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2010-2017 HUDORA. MIT licensed.
"""
import cStringIO
import functools

import huTools.hujson
import huTools.structured


class MultirenderMixin(object):
    """Provide rendering for a variety of formats with minimal code.

    For the three major formats HTML, JSON, CSV and XML und you can get away
    with virtually no code.

    Still nowadays we discourage the habit of massaging a single view into
    providing different formats of the same data.
    """

    def multirender(self, fmt, data, mappers=None, contenttypes=None, filename='download',
                    defaultfmt='html', html_template='data', html_addon=None,
                    xml_root='data', xml_lists=None,
                    tabular_datanodename='objects'):
        r"""Send Data formated in different ways to the client.

        Some real-world view method might look like this:

            # URL matches '/empfaenger/([A-Za-z0-9_-]+)/rechnungen\.?(json|xml|html)?',
            def get(self, kundennr, fmt):
                query = models.Rechnung.all().filter('kundennr = ', kundennr)
                values = self.paginate(query, 25, datanodename='rechnungen')
                self.multirender(fmt, values,
                                 filename='rechnungen-%s' % kundennr,
                                 html_template='rechnungen.html',
                                 tabular_datanodename='rechnungen')

        `/empfaenger/12345/rechnungen` and `/empfaenger/12345/rechnungen.html` will result in
        `rechnungen.html` beeing rendered.
        `/empfaenger/12345/rechnungen.json` results in JSON being returned with a
        `Content-Disposition` header sending it to the file `rechnungen-12345.json`. Likewise for
        `/empfaenger/12345/rechnungen.xml`.
        If you add the Parameter `disposition=inline` no Content-Desposition header is generated.

        If you use fmt=json with a `callback` parameter, JSONP is generated. See
        http://en.wikipedia.org/wiki/JSONP#JSONP for details.

        If you give a dict in `html_addon` this dict is additionaly passed the the HTML rendering function
        (but not to the rendering functions of other formats).

        You can give the `xml_root` and `xml_lists` parameters to provide `huTools.structured.dict2xml()`
        with defenitions on how to name elements. See the documentation of `roottag` and `listnames` in
        dict2xml documentation.

        For tabular formats like XLS and CSV we assume that `data[tabular_datanodename]` contains
        a list of dicts to be rendered.

        For more sophisticated layout you can give customized mappers. Using functools.partial
        is very helpfiull for thiss. E.g.

            from functools import partial
            multirender(fmt, values,
                        mappers=dict(xml=partial(dict2xml, roottag='response',
                                                 listnames={'rechnungen': 'rechnung', 'odlines': 'odline'},
                                                  pretty=True),
                                     html=lambda x: '<body><head><title>%s</title></head></body>' % x))
        """
        # If no format is given, we assume HTML (or whatever is given in defaultfmt)
        # We also provide a list of convinient default content types and encodings.
        fmt = fmt or defaultfmt

        mapper = self._get_mapper(mappers, fmt, html_template, html_addon, xml_lists,
                                  data, xml_root, tabular_datanodename)
        contenttype = self._generate_content_headers(fmt, filename, contenttypes)
        # If we have gotten a `callback` parameter, we expect that this is a
        # [JSONP](http://en.wikipedia.org/wiki/JSONP#JSONP) can and therefore add the padding
        if self.request.get('callback', None) and fmt == 'json':
            self.response.headers['Content-Type'] = 'text/javascript'
            self.response.write("%s (%s)" % (self.request.get('callback', None), mapper(data)))
        else:
            self.response.headers['Content-Type'] = contenttype
            self.response.write(mapper(data))

    def _get_mapper(self, mappers, fmt, html_template, html_addon, xml_lists, data,
                    xml_root, tabular_datanodename):
        """Return the correct mapper for `fmt`."""
        # We lazy import huTools to keep gaetk usable without hutools

        # Default mappers are there for XML and JSON (provided by huTools) and HTML provided by Jinja2
        # we provide a default dict2xml renderer based on the xml_* parameters given
        # The HTML Render integrates additional data via html_addon
        def htmlrender(_x):
            """Create HTML via jinja2."""
            htmldata = data.copy()
            if html_addon:
                htmldata.update(html_addon)
            buf = cStringIO.StringIO()
            self._render_to_fd(htmldata, html_template, buf)
            return buf.getvalue()

        mymappers = dict(
            xml=functools.partial(
                huTools.structured.dict2xml, roottag=xml_root, listnames=xml_lists, pretty=True),
            json=huTools.hujson2.dumps,
            csv=functools.partial(huTools.structured.dict2csv, datanodename=tabular_datanodename),
            xls=functools.partial(huTools.structured.dict2xls, datanodename=tabular_datanodename),
            html=htmlrender)
        if mappers:
            mymappers.update(mappers)

        # Check early if we have no corospondending configuration to provide more meaningful error messages.
        if fmt not in mymappers:
            raise ValueError('No mapper for format "%r"' % fmt)
        return mymappers[fmt]

    def _generate_content_headers(self, fmt, filename, contenttypes):
        """Generate `Content-Disposition` and `Content-Type`headers."""
        mycontenttypes = dict(pdf='application/pdf',
                              xml="application/xml; encoding=utf-8",
                              json="application/json; encoding=utf-8",
                              html="text/html; encoding=utf-8",
                              csv="text/csv; encoding=utf-8",
                              xls="application/vnd.ms-excel",
                              invoic="application/edifact; encoding=iso-8859-1",
                              desadv="application/edifact; encoding=iso-8859-1")
        if contenttypes:
            mycontenttypes.update(contenttypes)

        # Disposition helps the browser to decide if something should be downloaded to disk or
        # if it should displayed in the browser window. It also can provide a filename.
        # per default we provide downloadable files
        if self.request.get('disposition') != 'inline':
            disposition = "attachment"
        else:
            disposition = "inline"

        if fmt not in ['html', 'json']:
            self.response.headers["Content-Disposition"] = str("%s; filename=%s.%s" % (
                disposition, filename, fmt))

        if fmt not in mycontenttypes:
            raise ValueError('No content-type for format "%s": %r' % (fmt, mycontenttypes))
        return mycontenttypes[fmt]
