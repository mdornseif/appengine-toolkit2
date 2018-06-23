#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2007, 2015, 2016 HUDORA GmbH. BSD Licensed.
"""

from __future__ import unicode_literals

import doctest
import re
import string
import sys
import unicodedata

from types import StringType

from gaetk2.tools import unicode_helper_latin1


def de_utf8(data):
    """This is meant to help with utf-8 data appearing where unicode should apperar."""
    # In particular my DB is returning the wrong thing.
    if isinstance(data, StringType):
        return data.decode('utf-8')
    return data


# native, HTML, default Unicode (Code page 850), Unicode combined Character, Windows-1250
_recodings = {'ae': ['ä', 'ä', '&auml;', '\u00E4', '\u00E4', '\u0308a', '\xc3\xa4'],
              'oe': ['ö', 'ö', '&ouml;', '\u00F6', '\u00F6', '\u0308o', '\xc3\xb6', 'á'],
              'ue': ['ü', 'ü', '&uuml;', '\u00FC', '\u00FC', '\u0308u', '\xc3\xbc'],
              'Ae': ['Ä', 'Ä', '&Auml;', '\u00C4', '\u00C4', '\u0308A', '\xc3\x84'],
              'Oe': ['Ö', 'Ö', '&Ouml;', '\u00D6', '\u00D6', '\u0308O', '\xc3\x96', 'Ó'],
              'Ue': ['Ü', 'Ü', '&Uuml;', '\u00DC', '\u00DC', '\u0308U', '\xc3\x9c'],
              'ss': ['ß', 'ß', '&szlig;', '\u00DF', '\u00DF', '\xc3\x9f', 'ß'],
              'e': ['é', 'é', '\xc3\xa9', 'ê', 'è'],
              'i': ['í', 'í'],
              'E': ['É', 'È'],
              "'": ['´', '´', '`', '`'],
              }


def de_umlaut(data):
    """Converts a text to ASCII acting smart about Umlauts.

    >>> de_umlaut('1 Über Hügel saß René äöüÄÖÜß')
    '1 Ueber Huegel sass Rene aeoeueAeOeUess'
    """

    # maybe https://pypi.python.org/pypi/Unidecode is a nice addition?
    for to_char, from_chars in _recodings.items():
        for from_char in from_chars:
            try:
                data = data.replace(from_char, to_char)
            except UnicodeDecodeError:
                data = data
    # data = unidecode(data)
    try:
        data = unicodedata.normalize('NFKD', data)
    except TypeError:
        pass

    try:
        return data.encode('ascii', 'replace')
    except UnicodeEncodeError as msg:
        raise ValueError('%s: %r' % (msg, data))
    except UnicodeDecodeError as msg:
        raise ValueError('%s: %r' % (msg, data))


# see http://instagram-engineering.tumblr.com/post/118304328152
# to learn more about the mess
try:
    HIGHPOINTS = re.compile('[\U00010000-\U0010ffff]')
    EMOJI = re.compile('([\U00002600-\U000027BF])|([\U0001f300-\U0001f64F])|([\U0001f680-\U0001f6FF])')
except re.error:
    # UCS-2 build
    HIGHPOINTS = re.compile('[\uD800-\uDBFF][\uDC00-\uDFFF]')
    EMOJI = re.compile(
        '([\u2600-\u27BF])|([\uD83C][\uDF00-\uDFFF])|([\uD83D][\uDC00-\uDE4F])|([\uD83D][\uDE80-\uDEFF])')
DASHES = ''
# Crap from Windows-1250: ‚„…‰Š‹ŚŤŽŹ‘’“”•–—™›ˇ¦©«®·»śťžźĄąĽľ
# Crap fom Unicode: …
REPLACRS = {
    # see https://www.cs.tut.fi/~jkorpela/chars/spaces.html
    ' ': '\u00A0'   # NO-BREAK SPACE  foo bar As a space, but often not adjusted
         '\u2000'   # EN QUAD foo bar 1 en (= 1/2 em)
         '\u2001'   # EM QUAD foo bar 1 em (nominally, the height of the font)
         '\u2002'   # EN SPACE    foo bar 1 en (= 1/2 em)
         '\u2003'   # EM SPACE    foo bar 1 em
         '\u2007'   # FIGURE SPACE    foo bar “Tabular width”, the width of digits
         '\u2004'   # THREE-PER-EM SPACE  foo bar 1/3 em
         '\u2005'   # FOUR-PER-EM SPACE   foo bar 1/4 em
         '\u2006'   # SIX-PER-EM SPACE    foo bar 1/6 em
         '\u2008'   # PUNCTUATION SPACE   foo bar The width of a period “.”
         '\u2009'   # THIN SPACE  foo bar 1/5 em (or sometimes 1/6 em)
         '\u200A'   # HAIR SPACE  foo bar Narrower than THIN SPACE
         '\u205F'   # MEDIUM MATHEMATICAL SPACE   foo bar 4/18 em
         '\u3000',  # IDEOGRAPHIC SPACE   foo　bar The width of ideographic (CJK) characters.

    '': '\u1680'   # OGHAM SPACE MARK    foo bar Unspecified; usually not really a space but a dash
        '\u180E'   # MONGOLIAN VOWEL SEPARATOR   foo᠎bar No width
        '\u200B'   # ZERO WIDTH SPACE    foo​bar Nominally no width, but may expand
        '\u202F'   # NARROW NO-BREAK SPACE   foo bar Narrower than NO-BREAK SPACE (or SPACE)
        '\uFEFF',  # ZERO WIDTH NO-BREAK SPACE   foo﻿bar No width (the character is invisible)

    '-': '-‐‑–‒—―',  # see https://www.cs.tut.fi/~jkorpela/dashes.html
    '_': '_﹏',
    '*': '※⁕⁜*⁎∗·•◦‣⦿⦾⁃◘',
    '!': '!¡‼❕',
    '?': '¿⁇❓❔؟‽',
    '~': '~〜',
    '&': '&＆⅋﹠',
    "'": 'ʻˮ՚Ꞌꞌ‘’′',
    '"': '“”″‴〃„',
    '/': '/\⁄\\',
    '|': '¦|',
    '<': '‹«',
    '>': '›»',
}
# this could be an one liner
REVERSEREPLACRS = {}
for result, inputs in REPLACRS.iteritems():
    for c in inputs:
        REVERSEREPLACRS[c] = result
REPLACE_RE = re.compile('[%s]' % ''.join([re.escape(x) for x in REVERSEREPLACRS.keys()]))


def de_noise(data):
    """Removes all stuff which should not appear in normal Western Text.

    >>> de_noise(u'»Susie`s Giga\\Super-Markt®¿«')
    u">Susie's Giga/Super-Markt(R)?<"
    >>> de_noise(u"ümlaut eins:\x01")
    u'\\xfcmlaut eins:'
    >>> de_noise(u'«A» {C} ¿D? „E“ ›F‹')
    u'<A> (C) ?D? "E" >F<'
    >>> de_noise(u'`A´')
    u"'A'"
    >>> de_noise(u'«😎» Umlaute kann doctest !gut {®} ¿👩‍👩‍👧‍👦? „👨‍❤️‍💋‍👨“ ›🎅🏻🎅🏼🎅🏽🎅🏾🎅🏿‹')
    u'<> Umlaute kann doctest !gut ((R)) ?? "" ><'
    >>> de_noise(u'DE37  330 5 13 50 0 010  4414  22')
    u'DE37330513500010441422'
    """
    data = unicodedata.normalize('NFC', unicode(data))

    def noiserepl(matchobj):
        return REVERSEREPLACRS.get(matchobj.group(0), '_')
    data = REPLACE_RE.sub(noiserepl, data)
    data = unicode_helper_latin1.de_noise_latin1(data)
    # data = unicodedata.normalize('NFKC', data) # decruft a little but keep umlauts
    return data


# from http://code.activestate.com/recipes/577257/
_SLUGIFY_STRIP_RE = re.compile(r'[^\w\s-]')
_SLUGIFY_HYPHENATE_RE = re.compile(r'[-\s]+')


def slugify(value):
    """Converts a string to be usable in URLs without excaping.

    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    Inspired by Django's "django/template/defaultfilters.py".
    """
    if value is None:
        return ''

    value = de_noise(de_umlaut(value))
    value = unicodedata.normalize('NFKD', unicode(value)).encode('ascii', 'ignore')
    value = unicode(_SLUGIFY_STRIP_RE.sub('', value).strip().lower())
    return _SLUGIFY_HYPHENATE_RE.sub('-', value)


# from http://stackoverflow.com/questions/561486
ALPHABET = string.digits + string.ascii_uppercase + string.ascii_lowercase
ALPHABET_REVERSE = {c: i for (i, c) in enumerate(ALPHABET)}
BASE = len(ALPHABET)
SHORTALPHABET = string.digits + string.ascii_uppercase
SHORTALPHABET_REVERSE = {c: i for (i, c) in enumerate(SHORTALPHABET)}
SHORTBASE = len(SHORTALPHABET)
SIGN_CHARACTER = '$'


def num_encode(n):
    """Convert an integer to an base62 encoded string."""
    if n < 0:
        return SIGN_CHARACTER + num_encode(-n)
    s = []
    while True:
        n, r = divmod(n, BASE)
        s.append(ALPHABET[r])
        if n == 0:
            break
    return ''.join(reversed(s))


def num_decode(s):
    """Convert the result of num_encode() back to an integer."""
    if s[0] == SIGN_CHARACTER:
        return -num_decode(s[1:])
    n = 0
    for c in s:
        n = n * BASE + ALPHABET_REVERSE[c]
    return n


def num_encode_uppercase(n):
    """Convert an integer to an base36 (unly uppercase and numbers) encoded string."""
    if n < 0:
        return SIGN_CHARACTER + num_encode_uppercase(-n)
    s = []
    while True:
        n, r = divmod(n, SHORTBASE)
        s.append(SHORTALPHABET[r])
        if n == 0:
            break
    return ''.join(reversed(s))


if __name__ == '__main__':
    print de_noise("`Iñtërnâtiônàlizætiøn!'")
    print de_noise('«😎» `Iñtërnâtiônàlizætiøn´ {®} ¿👩‍👩‍👧‍👦? „👨‍❤️‍💋‍👨“ ›🎅🏻🎅🏼🎅🏽🎅🏾🎅🏿‹')
    failure_count, test_count = doctest.testmod()
    sys.exit(failure_count)
