# encoding: utf-8
"""
DSL zur Beschreibung von REST-interfaces, angelehnt an https://gist.github.com/805540

File created by Philipp Benjamin Koeppchen on 2011-02-23
Copyright (c) 2011, 2013, 2016, 2017, 2017 HUDORA. MIT Licensed.
"""

import json
import logging
import optparse
import os
import random
import sys
import time
import urlparse
import xml.dom.minidom

from collections import Counter
from functools import partial

import concurrent.futures
import requests

from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
FOREGROUND = 30
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"

MAX_WORKERS = 6

# save slowest access to each URL
slowstats = Counter()
traceids = {}

if False:
    MAX_WORKERS = 1
    # these two lines enable debugging at httplib level (requests->urllib3->httplib)
    # you will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # the only thing missing will be the response.body which is not logged.
    import httplib
    httplib.HTTPConnection.debuglevel = 1
    logger.getLogger().setLevel(logger.DEBUG)
    requests_log = logger.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logger.DEBUG)
    requests_log.propagate = True


def create_testclient_from_cli(default_hostname, users):
    """ Creates a Testclient with it's arguments from the Commandline.

    the CLI understands the options, --hostname, --credentials-user, their default
    values are taken from this functions args

    default_hostname: hostname, on wich to run tests, if none is provided via CLI

    returns a `TestClient`
    """
    parser = optparse.OptionParser()
    parser.add_option(
        '-H', '--hostname', dest='hostname',
        help='Hostname, on which the tests should be run',
        default=default_hostname)
    parser.add_option(
        '-u', '--credentials-user', dest='users', action='append', default=[],
        help='user credentials for HTTP Basic Auth')
    parser.add_option(
        '-d', '--debug', dest='debug', default=False, action='store_true')

    opts, args = parser.parse_args()
    if args:
        parser.error('positional arguments are not accepted')

    if os.environ.get('RESTTESTHOST'):
        default_hostname = os.environ.get('RESTTESTHOST')
    # Das `or` sorgen dafür, dass --option='' als 'nicht angegeben' gewertet wird, siehe aufruf im Makefile.

    if users is None:
        users = []
    if opts.users:
        users.extend(opts.users)

    client = TestClient(opts.hostname or default_hostname, users=users, debug=opts.debug)

    return client


class TestClient(object):
    """Hilfsklasse zum Ausfuehren von HTTP-Requests im Rahmen von Tests."""

    def __init__(self, host, users, debug=False):
        self.debug = debug
        self.host = host
        self.authdict = {}
        self.responses = []
        self.protocol = 'https'
        self.sessions = {None: requests.Session()}
        self.sessions[None].trust_env = False  # avoid reading .netrc!
        self.queue = []  # contains URLs to be checked, kwargs, and checks to be done
        self.urlfile = open('.resttest-urls.txt', 'w')  # für JavaScript Tests
        self.curlfile = open('.resttest-curl.txt', 'w')  # für JavaScript Tests

        for user in users:
            key, creds = user.split('=', 1)
            self.add_credentials(key, creds)

    def add_credentials(self, auth, creds):
        """Stellt dem Client credentials zur Verfügung, die in GET genutzt werden können.

        auth: key der Credentials
        creds: HTTP-Credentials in der Form 'username:password'
        """
        self.authdict[auth] = creds
        self.sessions[auth] = requests.Session()

    def GET(self, path, auth=None, accept=None, headers={}, **kwargs):  # NOQA pylint: disable=N0802
        """Führt einen HTTP-GET auf den gegebenen [path] aus.
        Nutzt dabei ggf. die credentials zu [auth] und [accept]."""
        if isinstance(auth, list):
            raise ValueError("unsuitable auth %r" % auth)
        if auth and auth not in self.authdict:
            raise ValueError("Unknown auth '%s'" % auth)

        self.cloudtrace = "%032x" % (random.getrandbits(128))
        myheaders = {
            'User-Agent': 'resttest/%s' % requests.utils.default_user_agent(),
            'X-Cloud-Trace-Context': '%s/0;o=1' % self.cloudtrace}
        if accept:
            myheaders['Accept'] = accept
        myheaders.update(headers)

        url = urlparse.urlunparse((self.protocol, self.host, path, '', '', ''))
        start = time.time()
        self.sessions[auth].cookies.clear()
        if self.authdict.get(auth):
            r = self.sessions[auth].get(
                url,
                headers=myheaders,
                auth=HTTPBasicAuth(*self.authdict.get(auth).split(':')),
                timeout=300,
                **kwargs)
        else:
            r = self.sessions[auth].get(
                url,
                headers=myheaders,
                timeout=300,
                **kwargs)
        duration = int((time.time() - start) * 1000)
        slowstats[url] = duration

        response = Response(self, 'GET:%s' % auth, url, r.status_code, r.headers, r.content, duration, r)
        self.responses.append(response)
        self.curlfile.write(_to_curl(r.request) + '\n')
        return response

    # New API

    def check(self, *args, **kwargs):
        # see http://stackoverflow.com/questions/9872824/
        typ = kwargs.pop('typ', u'').lower()
        for url in args:
            path = urlparse.urlparse(url).path
            if typ == 'json' or path.endswith('.json'):
                checkers = [_responds_json]
            elif path.endswith('.pdf'):
                checkers = [_responds_pdf]
            elif path.endswith(('.xml', '/xml/')):
                checkers = [_responds_xml]
            elif path.endswith(('.csv', '/csv/', '/xls/', '.xls')):
                checkers = [_responds_basic]
            elif path.endswith('jpeg'):
                checkers = [_responds_jpeg]
            elif typ == 'txt' or path.endswith('txt'):
                checkers = [_responds_plaintext]
            else:
                checkers = [_responds_html]
                self.urlfile.write(url + '\n')

            self.queue.append((url, kwargs, checkers))

    def check_allowdeny(self, *args, **kwargs):
        allow = kwargs.get('allow', [])
        if 'allow' in kwargs:
            del kwargs['allow']
        deny = kwargs.get('deny', [])
        if 'deny' in kwargs:
            del kwargs['deny']

        assert len(allow) + len(deny) > 0  # IRGENDWAS muessen wir ja testen

        for auth in allow:
            self.check(*args, auth=auth, **kwargs)
        for auth in deny:
            # 40x detection is messy, because `login: admin` in app.yaml
            # results in redirects to a 200
            myargs = dict(allow_redirects=False, auth=auth)
            myargs.update(kwargs)
            for url in args:
                self.queue.append((url, myargs, [_responds_4xx]))

    def check_redirect(self, *args, **kwargs):
        for urldict in args:
            fromurl = urldict.get('url')
            del urldict['url']
            tourl = urldict.get('to')
            del urldict['to']
            myargs = dict(allow_redirects=False)
            myargs.update(kwargs)
            myargs.update(urldict)
            self.queue.append((fromurl, myargs, [partial(_responds_redirect, to=tourl)]))

    def check_statuscode(self, *args, **kwargs):
        statuscode = kwargs.get('statuscode')
        if 'statuscode' in kwargs:
            del kwargs['statuscode']

        def responds_closure(response):
            response._expect_condition(
                response.status == statuscode,
                'expected status statuscode, got %s' % response.status)

        for url in args:
            self.queue.append((url, kwargs, [responds_closure]))

    def run_checks(self, max_workers=MAX_WORKERS):
        """run queued checks."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            while self.queue:
                url, kwargs, checkers = self.queue.pop()
                futures[executor.submit(self._check_helper, checkers, url, **kwargs)] = url
        for future in concurrent.futures.as_completed(futures):
            # exceptions occure here
            try:
                future.result()
                sys.stdout.flush()
            except:
                print futures[future]
                sys.stdout.flush()
                raise
        finished, not_done = concurrent.futures.wait(futures)
        if not_done:
            print "unfinished:", not_done

    def _check_helper(self, checkers, url, **kwargs):
        response = self.GET(url, **kwargs)
        for checker in checkers:
            checker(response)
        return "%s:%s" % (kwargs.get('auth'), url)

    @property
    def errors(self):
        """Anzahl der fehlgeschlagenen Zusicherungen, die für Anfragen dieses Clients gefroffen wurden."""
        return sum(r.errors for r in self.responses)


def _colored(text, color):
    """Färbt den Text mit Terminalsequenzen ein.

    >>> colored('whatever', RED)
    '\033[1;32mwhatever\033[0m' # wuerde dann in rot erscheinen, wenn man es ausgibt
    """
    start = COLOR_SEQ % (FOREGROUND + color)
    return start + text + RESET_SEQ


class Response(object):
    """Repräsentiert das Ergebnis einer REST-Anfrage.
    Mittels responds_* koennen zusicherungen geprueft werden:

    r.responds_http_status(200)
    r._responds_html()
    """

    def __init__(self, client, method, url, status, headers, content, duration, response):
        self.client = client
        self.method = method
        self.url = url
        self.status = status
        self.headers = headers
        self.content = content
        self.errors = 0
        self.duration = duration
        self.response = response

    def _fail(self, message):
        """Negatives Ergebnis einer Zusicherung."""
        self.errors += 1
        url = self.url
        if self.response.url != url:
            url = u'%r (->%r)' % (url, self.response.url)
        print u'%s %s -> %s: %s' % (self.method, url, _colored("FAIL", RED), message)
        if self.response.history:
            for hres in self.response.history:
                print u'->', hres.url
        print _to_curl(self.response.request)
        # if 'X-Cloud-Trace-Context' in self.headers:
        #     print ('http://console.developer.google.com/traces/details/%s'
        #            % self.headers['X-Cloud-Trace-Context'].split(';')[0])
        print

    def _succeed(self, message):
        """Positives Ergebnis einer Zusicherung."""
        if self.client.debug:
            print '%s %s -> %s: %s' % (self.method, self.url, _colored("SUCCESS", GREEN), message)

    def _expect_condition(self, condition, message):
        """sichert eine boolsche Bedingung zu. sollte nicht direkt aufgerufen werden"""
        if not self.errors:
            if not condition:
                self._fail(message)
            else:
                self._succeed(message)
        # else: ignore

    # high-level-beschreibungen
    def responds_normal(self):
        """Sichert zu, dass ein Dokument gefunden wurde."""
        self.responds_http_status(200)

    def responds_not_found(self):
        """Sichert zu, dass kein Dokument gefunden wurde."""
        self.responds_http_status(404)
        return self

    def responds_access_denied(self):
        """Sichert zu, dass der Zugriff verweigert wurde."""
        self.responds_http_status(401)
        return self

    def responds_forbidden(self):
        """Sichert zu, dass der Zugriff verweigert wurde."""
        self.responds_http_status(403)
        return self

    def responds_with_content_location(self, expected_location):
        """Sichert zu, dass die Antwort einen location-header hat."""
        content_location = self.headers.get('content-location', '')
        self._expect_condition(
            content_location.endswith(expected_location),
            'expected content-location to end with %r, got %r.' % (expected_location, content_location))
        return self

    # low-level-beschreibungen der erwartungen
    def responds_http_status(self, expected_status):
        """sichert zu, dass mit dem gegebenen HTTP-status geantwortet wurde."""
        self._expect_condition(
            self.status == expected_status,
            'expected status %s, got %s' % (expected_status, self.status))
        return self

    def responds_content_type(self, expected_type):
        """sichert zu, dass mit dem gegebenen Content-Type geantwortet wurde."""
        actual_type = self.headers.get('content-type')
        # evtl wird dem contenttype ein encoding nachgestellt, dies soll abgetrennt werden
        actual_type = actual_type.split(';')[0]
        self._expect_condition(
            actual_type == expected_type,
            'expected content type %r, got %r' % (expected_type, actual_type))
        return self

    def converter_succeeds(self, converter, message):
        """Sichert zu, dass content mittels converter(self.content) ohne exception konvertiert werden kann."""
        if not self.errors:
            try:
                converter(self.content)
            except Exception:
                self._fail(message)
            else:
                self._succeed(message)


def _responds_json(response):
    """sichert zu, dass die Antwort ein well-formed JSON-Dokument war."""
    response.responds_http_status(200)
    response.responds_content_type('application/json')
    response.converter_succeeds(json.loads, 'expected valid json')


def _responds_xml(response):
    """sichert zu, dass die Antwort ein well-formed XML-Dokument war."""
    response.responds_http_status(200)
    response.responds_content_type('application/xml')
    response.converter_succeeds(xml.dom.minidom.parseString, 'expected valid xml')


def _responds_plaintext(response):
    """sichert zu, dass die Antwort plaintext war."""
    response.responds_http_status(200)
    response.responds_content_type('text/plain')


def _responds_pdf(response):
    """sichert zu, dass die Antwort ein well-formed PDF-Dokument war."""
    response.responds_http_status(200)
    response.responds_content_type('application/pdf')
    # .startswith('%PDF-1')


def _responds_jpeg(response):
    """sichert zu, dass die Antwort ein JPEG"""
    response.responds_http_status(200)
    response.responds_content_type('image/jpeg')
    # .startswith('%PDF-1')


def _responds_basic(response):
    """sichert zu, dass die Antwort einen vernünftigen Statuscode hat."""
    response.responds_http_status(200)


def _responds_html(response):
    """sichert zu, dass die Antwort ein HTML war."""
    response.responds_http_status(200)
    response.responds_content_type('text/html')
    # TODO: delayed HTML validation
    # response.responds_with_valid_html()
    # todo: links responds_with_valid_links


def _responds_4xx(response):
    """sichert zu, dass die Antwort ein Denial war."""
    # 40x detection is messy, because `login: admin` in app.yaml
    # results in redirects to a 302
    if response.status == 302:
        # we now generally handle 302 as a form of denial
        return
        # response._expect_condition(
        #    response.headers.get('location').startswith(
        #         'https://www.google.com/accounts/ServiceLogin'),
        #    'expected status 302 redirect to google')
    else:
        response._expect_condition(
            response.status >= 400 and response.status < 500,
            'expected status 4xx, got %s' % response.status)


def _responds_redirect(response, to=None):
    """sichert zu, dass die Antwort umleitet."""
    # oder location = self.response.url
    location = urlparse.urlparse(response.headers.get('location', '/')).path
    response._expect_condition(
        (300 <= response.status < 400) and location.startswith(to),
        'expected redirect to %r, got %r:%r' % (
            to,
            response.response.status_code,
            location))


def _to_curl(request):
    """From https://github.com/oeegor/curlify/blob/master/curlify.py."""
    headers = ["'{0}: {1}'".format(k, v) for k, v in request.headers.items()]
    headers = " -H ".join(sorted(headers))

    command = "curl -i -X {method} -H {headers} -d '{data}' '{uri}'".format(
        data=request.body or "",
        headers=headers,
        method=request.method,
        uri=request.url,
    )
    return command
