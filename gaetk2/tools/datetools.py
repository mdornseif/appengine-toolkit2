#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2.tools.datetools - formating and parsing of timestamps.

Created as huTools.calendar.formats and huTools.calendar.formats
by Maximillian Dornseif and Christian Klein on 2007-06-24.
And on workdays.py created by Christian Klein on 2006-11-28.
Copyright (c) 2007, 2010, 2012, 2013, 2018 HUDORA GmbH. MIT licensed.
"""
import calendar
import datetime
import doctest
import email.utils
import sys
import time
import unittest
import warnings


def tertial(date):
    """Wandelt ein Date oder Datetime-Objekt in einen Tertial-String"""
    ret = date.strftime('%Y-%m')
    ret = ret[:-2] + {'01': 'A', '02': 'A', '03': 'A', '04': 'A',
                      '05': 'B', '06': 'B', '07': 'B', '08': 'B',
                      '09': 'C', '10': 'C', '11': 'C', '12': 'C'}[ret[-2:]]
    return ret


def rfc3339_date(date=None):
    """Formates a datetime object according to RfC 3339."""
    date = date or datetime.datetime.now()
    return date.strftime('%Y-%m-%dT%H:%M:%SZ')


def rfc3339_date_parse(date):
    """Parses an RfC 3339 timestamp into a datetime object."""
    return datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')


def convert_to_date(date):
    """Converts argument into a date object.

    Assumes argument to be a RfC 3339 coded date or a date(time) object.
    """

    if hasattr(date, 'date') and callable(date.date):
        # e.g. datetime objects
        return date.date()
    elif isinstance(date, datetime.date):
        return date
    elif not date:
        return None
    elif isinstance(date, basestring):
        date = date[:10]  # strip time
        try:
            return datetime.datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            try:
                date = date[:8]  # strip time
                return datetime.datetime.strptime(date, '%Y%m%d').date()
            except ValueError:
                pass  # Error will be raised later on
    raise ValueError("Unknown date value %r (%s)" % (date, type(date)))


def convert_to_datetime(date):
    """Converts argument into a datetime object.

    Assumes argument to be a RfC 3339 coded date or a date(time) object.
    """

    if isinstance(date, datetime.datetime):
        return date
    elif isinstance(date, datetime.date):  # order mattes! datetime is a subclass of date
        return datetime.datetime(date.year, date.month, date.day)
    elif isinstance(date, basestring):
        if len(date) < 11:
            return convert_to_datetime(convert_to_date(date))
        else:
            # remove Timezone
            if date.endswith(' +0000'):
                date = date.rstrip(' +0')
            date = date.rstrip('Z')

            # handle milliseconds
            ms = 0
            if '.' in date:
                date, ms = date.split('.')
            if len(date.split(':')) > 1 and len(date.split(':')) < 3:
                date = date + ':00'  # append seconds
            try:
                ret = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                try:
                    ret = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    ret = datetime.datetime.strptime(date, '%Y%m%dT%H%M%S')
            if ms:
                return datetime.datetime(ret.year, ret.month, ret.day,
                                         ret.hour, ret.minute, ret.second, int(ms))
            return ret
    elif not date:
        return None
    raise ValueError("Unknown value %r (%s)" % (date, type(date)))


def rfc2616_date(date=None):
    """Formates a datetime object according to RfC 2616.

    RfC 2616 is a subset of RFC 1123 date.
    Weekday and month names for HTTP date/time formatting; always English!
    """
    date = date or datetime.datetime.now()
    return email.utils.formatdate(time.mktime(date.timetuple()), usegmt=True)


def rfc2616_date_parse(data):
    """Parses an RfC 2616/2822 timestapm into a datetime object."""
    return datetime.datetime.fromtimestamp(email.utils.mktime_tz(email.utils.parsedate_tz(data)))


def date_trunc(trtype, timestamp):
    """
    Truncate date or datetime object. Truncated object of the given type.

    This function is inspired by date_trunc from PostgreSQL, see
    http://www.postgresql.org/docs/8.1/static/functions-datetime.html#FUNCTIONS-DATETIME-TRUNC

    Supported types are year, quarter, month, week, day, hour, minute, second.

    >>> date_trunc('week', datetime.datetime(1974, 8, 21))
    datetime.datetime(1974, 8, 19, 0, 0)
    >>> date_trunc('week', datetime.date(1973, 8, 8))
    datetime.date(1973, 8, 6)
    """

    if isinstance(timestamp, basestring):
        # we are called with the old calling convention
        warnings.warn("`date_trunc` should be called with a date/datetime object as the second parameter",
                      DeprecationWarning, stacklevel=2)
        timestamp, trtype = trtype, timestamp

    tmp = timestamp.timetuple()
    if trtype == "year":
        ret = datetime.datetime(tmp.tm_year, 1, 1)
    elif trtype == "tertial":
        ret = datetime.datetime(tmp.tm_year, 1 + (get_tertial(timestamp) - 1) * 4, 1)
    elif trtype == "quarter":
        ret = datetime.datetime(tmp.tm_year, 3 * (get_quarter(timestamp) - 1) + 1, 1)
    elif trtype == "month":
        ret = datetime.datetime(tmp.tm_year, tmp.tm_mon, 1)
    elif trtype == "week":
        firstday = timestamp - datetime.timedelta(days=tmp.tm_wday)
        ret = datetime.datetime.combine(firstday, datetime.time(0))
    elif trtype == "day":
        ret = datetime.datetime(tmp.tm_year, tmp.tm_mon, tmp.tm_mday)
    elif trtype == "hour":
        ret = datetime.datetime(tmp.tm_year, tmp.tm_mon, tmp.tm_mday, tmp.tm_hour)
    elif trtype == "minute":
        ret = datetime.datetime(tmp.tm_year, tmp.tm_mon, tmp.tm_mday, tmp.tm_hour, tmp.tm_min)
    elif trtype == "second":
        ret = datetime.datetime(tmp.tm_year, tmp.tm_mon, tmp.tm_mday, tmp.tm_hour, tmp.tm_min, tmp.tm_sec)
    else:
        raise ValueError("Unknown truncation type %s" % trtype)
    # if we where given a datetime object return it, else assume a date object and cast our return
    # value to that
    if isinstance(timestamp, datetime.datetime):
        return ret
    return ret.date()


def get_tertial(date):
    """
    Calculates the tertial

    >>> get_tertial(datetime.date(2015, 1, 9))
    1
    >>> get_tertial(datetime.datetime(2015, 2, 19))
    1
    >>> get_tertial(datetime.date(2015, 3, 9))
    1
    >>> get_tertial(datetime.datetime(2015, 4, 20))
    1
    >>> get_tertial(datetime.datetime(2015, 5, 4))
    2
    >>> get_tertial(datetime.datetime(2015, 6, 11))
    2
    >>> get_tertial(datetime.datetime(2015, 7, 22))
    2
    >>> get_tertial(datetime.date(2015, 8, 3))
    2
    >>> get_tertial(datetime.date(2015, 9, 23))
    3
    >>> get_tertial(datetime.datetime(2015, 10, 24))
    3
    >>> get_tertial(datetime.date(2015, 11, 11))
    3
    >>> get_tertial(datetime.datetime(2015, 12, 6))
    3
    """
    return (date.month - 1) / 4 + 1


def get_quarter(date):
    """
    Calculates the quarter

    >>> get_quarter(datetime.date(2015, 1, 9))
    1
    >>> get_quarter(datetime.datetime(2015, 2, 19))
    1
    >>> get_quarter(datetime.date(2015, 3, 9))
    1
    >>> get_quarter(datetime.datetime(2015, 4, 20))
    2
    >>> get_quarter(datetime.datetime(2015, 5, 4))
    2
    >>> get_quarter(datetime.datetime(2015, 6, 11))
    2
    >>> get_quarter(datetime.datetime(2015, 7, 22))
    3
    >>> get_quarter(datetime.date(2015, 8, 3))
    3
    >>> get_quarter(datetime.date(2015, 9, 23))
    3
    >>> get_quarter(datetime.datetime(2015, 10, 24))
    4
    >>> get_quarter(datetime.date(2015, 11, 11))
    4
    >>> get_quarter(datetime.datetime(2015, 12, 6))
    4
    """
    return (date.month - 1) / 3 + 1


def get_yearspan(date):
    """Gibt den ersten und letzten Tag des Jahres zurück in dem `date` liegt

    >>> get_yearspan(datetime.date(1980, 5, 4))
    (datetime.date(1980, 1, 1), datetime.date(1980, 12, 31))
    >>> get_yearspan(datetime.date(1986, 3, 11))
    (datetime.date(1986, 1, 1), datetime.date(1986, 12, 31))
    """
    startdate = date_trunc('year', date)
    enddate = type(startdate)(startdate.year, 12, 31)
    return startdate, enddate


def get_tertialspan(date):
    """Gibt den ersten und den letzten Tag des Tertials zurück in dem `date` liegt

    >>> get_tertialspan(datetime.date(1978, 9, 23))
    (datetime.date(1978, 9, 1), datetime.date(1978, 12, 31))
    """
    startdate = date_trunc('tertial', date)
    enddate = date_trunc('tertial', startdate + datetime.timedelta(days=130)) - datetime.timedelta(days=1)
    return startdate, enddate


def get_quarterspan(date):
    """Gibt den ersten und den letzten Tag des Quartals zurück in dem `date` liegt

    >>> get_quarterspan(datetime.date(1978, 6, 12))
    (datetime.date(1978, 4, 1), datetime.date(1978, 6, 30))
    """

    startdate = date_trunc('quarter', date)
    # The date 100 days after the beginning of a quarter is always right inside the next quarter
    enddate = date_trunc('quarter', startdate + datetime.timedelta(days=100)) - datetime.timedelta(days=1)
    return startdate, enddate


def get_monthspan(date):
    """Gibt den ersten und letzten Tag des Monats zurück in dem `date` liegt

    >>> get_monthspan(datetime.date(1980, 5, 4))
    (datetime.date(1980, 5, 1), datetime.date(1980, 5, 31))
    """
    startdate = date_trunc('month', date)
    _, days = calendar.monthrange(startdate.year, startdate.month)
    enddate = type(startdate)(startdate.year, startdate.month, days)
    return startdate, enddate


def get_weekspan(date):
    """Gibt den ersten und den letzten Tag der Woche, in der `date` liegt, zurück.

    Dabei ist Montag der erste Tag der woche und Sonntag der letzte.

    >>> get_weekspan(datetime.date(2011, 3, 23))
    (datetime.date(2011, 3, 21), datetime.date(2011, 3, 27))
    """
    startdate = date_trunc('week', date)
    enddate = startdate + datetime.timedelta(days=6)
    return startdate, enddate


def get_timespan(period, date):
    """
    Get given timespan for date

    Convenience function as a wrapper for the other get_*span functions
    """
    if period == "year":
        return get_yearspan(date)
    elif period == "tertial":
        return get_tertialspan(date)
    elif period == "quarter":
        get_quarterspan(date)
    elif period == "month":
        return get_monthspan(date)
    elif period == "week":
        return get_weekspan(date)
    elif period == "day":
        return date, date
    else:
        raise ValueError("Unknown truncation type %s" % trtype)


STATIC_GERMAN_HOLIDAYS = ((1, 1),    # Neujahr
                          (5, 1),    # Tag der Arbeit
                          (10, 3),   # Tag der deutschen Einheit
                          (11, 1),   # Allerheiligen
                          (12, 25),  # Erster Weihnachtstag
                          (12, 26),  # Zweiter Weihnachtstag
                          )


def add_to_day(day, offset):
    "Returns the date n days before or after day"
    return day + datetime.timedelta(days=offset)


def easter(year):
    """Returns the day of Easter sunday for 'year'.
    This function only works betweeen 1900 and 2099"""
    h = (24 + 19 * (year % 19)) % 30
    i = h - (h / 28)
    j = (year + (year / 4) + i - 13) % 7
    l = i - j

    easter_month = 3 + ((l + 40) / 44)
    easter_day = l + 28 - 31 * (easter_month / 4)

    return (easter_month, easter_day)


def easter_related_holidays(year):
    "Returns a list of holidays which are related to easter for 'year'."
    easter_days = []
    easter_month, easter_day = easter(year)
    easter_sunday = datetime.date(year, easter_month, easter_day)

    # Karfreitag
    easter_days.append(add_to_day(easter_sunday, -2))
    # Ostermontag
    easter_days.append(add_to_day(easter_sunday, 1))
    # Christi Himmelfahrt
    easter_days.append(add_to_day(easter_sunday, 39))
    # Pfingstmontag
    easter_days.append(add_to_day(easter_sunday, 50))
    # Fronleichnam
    easter_days.append(add_to_day(easter_sunday, 60))

    return easter_days


def holidays_german(start, end):
    """Returns a list of dates between start and end that are holidays."""
    hdays = []
    # Berechne alle Feiertage in den Jahren a bis b.
    # Falls a == b werden auch die Feiertage des nächsten
    # Jahres mitberechnet, aber die Liste muss sowieso
    # nochmal gefiltert werden.
    for year in range(start.year, end.year + 1):
        for month, day in STATIC_GERMAN_HOLIDAYS:
            hdays.append(datetime.date(year, month, day))
        hdays += easter_related_holidays(year)
    return hdays


def workdays(start, end):
    """Calculates the number of working days (Mo-Fr) between two given dates.

    Whereas the workdays are calculated siilar to Python slice notation: [start : end[
    Example:
    >>> workdays(datetime.date(2007, 1, 26), datetime.date(2007,  1,  27)) # Fr - Sa
    1
    >>> workdays(datetime.date(2007, 1, 28), datetime.date(2007,  1,  29)) # Su - Mo
    0
    """
    start = convert_to_date(start)
    end = convert_to_date(end)
    if start > end:
        return -1 * _workdays(end, start)
    else:
        return _workdays(start, end)


def _workdays(start, end):
    "Helper for `workdays()`."

    if start > end:
        raise ValueError("can't handle  negative timespan! %r > %r" % (start, end))

    # Wenn Anfangstag auf Wochenende liegt, addiere Tage bis Montag
    while start.isoweekday() > 5:
        start = add_to_day(start, 1)

    # Wenn Endtag auf Wochenende liegt, substrahiere Tage bis Freitag
    while end.isoweekday() > 5:
        end = add_to_day(end, 1)

    days = (end - start).days

    # Count weekends:
    # if weekday start < weekday end: n / 7
    # if weekday start > weekday end: (n / 7) + 1
    number_of_weekends = days / 7
    if start.isoweekday() > end.isoweekday():
        number_of_weekends += 1
    days = days - 2 * number_of_weekends
    if days < 0:
        raise RuntimeError("%r days difference %r|%r|%r" % (days, start, end, number_of_weekends))
    return days


def workdays_german(start, end):
    """Calculates the number of working days between two given dates while considering german holidays."""

    if isinstance(start, datetime.datetime):
        start = start.date()
    if isinstance(end, datetime.datetime):
        end = end.date()

    days = workdays(start, end)
    # Deduct Holidays (but only the ones not on weekends)
    holid = [x for x in holidays_german(start, end) if (x >= start) and (x < end) and (x.isoweekday() < 6)]
    return days - len(holid)


def is_workday_german(day):
    """Checks if a day is a workday in germany (NRW).

    >>> is_workday_german(datetime.date(2007, 1, 1))
    False
    >>> is_workday_german(datetime.date(2007, 1, 2))
    True
    """
    if day.isoweekday() > 5:
        return False  # weekend
    if isinstance(day, datetime.datetime):
        day = day.date()
    return day not in holidays_german(day, day)


def next_workday_german(startday):
    """Returns the next workday after startday.

    >>> next_workday_german(datetime.date(2006, 12, 29))
    datetime.date(2007, 1, 2)
    """

    next_day = add_to_day(startday, 1)
    while not is_workday_german(next_day):
        next_day = add_to_day(next_day, 1)
    return next_day


def previous_workday_german(startday):
    """Returns the workday before startday.

    >>> previous_workday_german(datetime.date(2007, 1, 2))
    datetime.date(2006, 12, 29)
    """

    prev_day = add_to_day(startday, -1)
    while not is_workday_german(prev_day):
        prev_day = add_to_day(prev_day, -1)
    return prev_day


def add_workdays_german(startday, count):
    """Adds <count> workdays to <startday>."""

    day = startday
    while count > 0:
        day = next_workday_german(day)
        count -= 1
    while count < 0:
        day = previous_workday_german(day)
        count += 1
    return day


class _FormatsTests(unittest.TestCase):

    def test_rfc3339_date(self):
        """Test basic rfc3339_date output."""
        self.assertEqual(rfc3339_date(datetime.datetime(2007, 2, 3, 4, 5, 6)), '2007-02-03T04:05:06Z')

    def test_rfc3339_date_parse(self):
        """Test basic rfc3339_date_parse output."""
        self.assertEqual(rfc3339_date_parse('2007-02-03T04:05:06Z'),
                         datetime.datetime(2007, 2, 3, 4, 5, 6))

    def test_rfc2616_date(self):
        """Test basic rfc2616_date output."""
        self.assertEqual(rfc2616_date(datetime.datetime(2007, 2, 3, 4, 5, 6)),
                         'Sat, 03 Feb 2007 03:05:06 GMT')

    def test_rfc2616_date_parse(self):
        """Test basic rfc2616_date_parse output."""
        self.assertEqual(rfc2616_date_parse('Sat, 03 Feb 2007 03:05:06 GMT'),
                         datetime.datetime(2007, 2, 3, 4, 5, 6))

    def test_convert_to_datetime(self):
        """Test convert_to_datetime() and convert_to_date() functionality"""
        self.assertEqual(convert_to_datetime(datetime.date(2007, 2, 3)),
                         datetime.datetime(2007, 2, 3, 0, 0))
        self.assertEqual(convert_to_datetime(datetime.datetime(2007, 2, 3, 13, 14, 15, 16)),
                         datetime.datetime(2007, 2, 3, 13, 14, 15, 16))
        self.assertEqual(convert_to_datetime('2007-02-03'), datetime.datetime(2007, 2, 3, 0, 0))
        self.assertEqual(convert_to_datetime('2007-2-3'), datetime.datetime(2007, 2, 3, 0, 0))
        self.assertEqual(convert_to_datetime('20070203'), datetime.datetime(2007, 2, 3, 0, 0))
        self.assertEqual(convert_to_datetime('20070203T131415'), datetime.datetime(2007, 2, 3, 13, 14, 15))
        self.assertEqual(convert_to_datetime('2007-02-03T13:14:15'),
                         datetime.datetime(2007, 2, 3, 13, 14, 15))
        self.assertEqual(convert_to_datetime('2007-02-03T13:14:15.16'),
                         datetime.datetime(2007, 2, 3, 13, 14, 15, 16))
        self.assertEqual(convert_to_datetime('2007-02-03 13:14:15'),
                         datetime.datetime(2007, 2, 3, 13, 14, 15))
        self.assertEqual(convert_to_datetime('2007-02-03 13:14:15.16'),
                         datetime.datetime(2007, 2, 3, 13, 14, 15, 16))
        self.assertEqual(convert_to_datetime('2013-09-03 21:39:09 +0000'),
                         datetime.datetime(2013, 9, 3, 21, 39, 9))
        self.assertEqual(convert_to_datetime('2013-12-03 13:14'),
                         datetime.datetime(2013, 12, 3, 13, 14, 0, 0))


class _WeekspanTestCase(unittest.TestCase):
    """Unittests for get_weekspan"""

    def test_monday(self):
        """get_weekspan for a monday"""
        date = datetime.date(1981, 5, 4)
        self.assertEqual(date.isoweekday(), 1)
        start_date, end_date = get_weekspan(date)
        self.assertEqual(start_date.isoweekday(), 1)
        self.assertEqual(end_date.isoweekday(), 7)
        self.assertTrue(start_date.toordinal() <= date.toordinal() <= end_date.toordinal())

    def test_tuesday(self):
        """get_weekspan for a tuesday"""
        date = datetime.date(1982, 5, 4)
        self.assertEqual(date.isoweekday(), 2)
        start_date, end_date = get_weekspan(date)
        self.assertEqual(start_date.isoweekday(), 1)
        self.assertEqual(end_date.isoweekday(), 7)
        self.assertTrue(start_date.toordinal() <= date.toordinal() <= end_date.toordinal())

    def test_wednesday(self):
        """get_weekspan for a wednesday"""
        date = datetime.date(1988, 5, 4)
        self.assertEqual(date.isoweekday(), 3)
        start_date, end_date = get_weekspan(date)
        self.assertEqual(start_date.isoweekday(), 1)
        self.assertEqual(end_date.isoweekday(), 7)
        self.assertTrue(start_date.toordinal() <= date.toordinal() <= end_date.toordinal())

    def test_thursday(self):
        """get_weekspan for a thursday"""
        date = datetime.date(1989, 5, 4)
        self.assertEqual(date.isoweekday(), 4)
        start_date, end_date = get_weekspan(date)
        self.assertEqual(start_date.isoweekday(), 1)
        self.assertEqual(end_date.isoweekday(), 7)
        self.assertTrue(start_date.toordinal() <= date.toordinal() <= end_date.toordinal())

    def test_friday(self):
        """get_weekspan for a friday"""
        date = datetime.date(1984, 5, 4)
        self.assertEqual(date.isoweekday(), 5)
        start_date, end_date = get_weekspan(date)
        self.assertEqual(start_date.isoweekday(), 1)
        self.assertEqual(end_date.isoweekday(), 7)
        self.assertTrue(start_date.toordinal() <= date.toordinal() <= end_date.toordinal())

    def test_saturday(self):
        """get_weekspan for a saturday"""
        date = datetime.date(1985, 5, 4)
        self.assertEqual(date.isoweekday(), 6)
        start_date, end_date = get_weekspan(date)
        self.assertEqual(start_date.isoweekday(), 1)
        self.assertEqual(end_date.isoweekday(), 7)
        self.assertTrue(start_date.toordinal() <= date.toordinal() <= end_date.toordinal())

    def test_sunday(self):
        """get_weekspan for a sunday"""
        date = datetime.date(1980, 5, 4)
        self.assertEqual(date.isoweekday(), 7)
        start_date, end_date = get_weekspan(date)
        self.assertEqual(start_date.isoweekday(), 1)
        self.assertEqual(end_date.isoweekday(), 7)
        self.assertTrue(start_date.toordinal() <= date.toordinal() <= end_date.toordinal())


class _MonthSpanTestCase(unittest.TestCase):
    """Unittests for get_monthspan"""

    def test_january(self):
        date = datetime.date(1980, 1, 1)
        start_date, end_date = get_monthspan(date)
        self.assertTrue(isinstance(start_date, datetime.date))
        self.assertTrue(isinstance(end_date, datetime.date))
        self.assertEqual(start_date, datetime.date(1980, 1, 1))
        self.assertEqual(end_date, datetime.date(1980, 1, 31))
        date = datetime.datetime(1980, 1, 31)
        start_date, end_date = get_monthspan(date)
        self.assertTrue(isinstance(start_date, datetime.datetime))
        self.assertTrue(isinstance(end_date, datetime.datetime))
        self.assertEqual(start_date, datetime.datetime(1980, 1, 1))
        self.assertEqual(end_date, datetime.datetime(1980, 1, 31))

    def test_february(self):
        date = datetime.date(1945, 2, 19)
        start_date, end_date = get_monthspan(date)
        self.assertTrue(isinstance(start_date, datetime.date))
        self.assertTrue(isinstance(end_date, datetime.date))
        self.assertEqual(start_date, datetime.date(1945, 2, 1))
        self.assertEqual(end_date, datetime.date(1945, 2, 28))
        date = datetime.datetime(1945, 2, 1)
        start_date, end_date = get_monthspan(date)
        self.assertTrue(isinstance(start_date, datetime.datetime))
        self.assertTrue(isinstance(end_date, datetime.datetime))
        self.assertEqual(start_date, datetime.datetime(1945, 2, 1))
        self.assertEqual(end_date, datetime.datetime(1945, 2, 28))

    def test_february_leap(self):
        date = datetime.date(1980, 2, 19)
        start_date, end_date = get_monthspan(date)
        self.assertTrue(isinstance(start_date, datetime.date))
        self.assertTrue(isinstance(end_date, datetime.date))
        self.assertEqual(start_date, datetime.date(1980, 2, 1))
        self.assertEqual(end_date, datetime.date(1980, 2, 29))
        date = datetime.datetime(1980, 2, 19)
        start_date, end_date = get_monthspan(date)
        self.assertTrue(isinstance(start_date, datetime.datetime))
        self.assertTrue(isinstance(end_date, datetime.datetime))
        self.assertEqual(start_date, datetime.datetime(1980, 2, 1))
        self.assertEqual(end_date, datetime.datetime(1980, 2, 29))

    def test_june(self):
        date = datetime.date(1978, 6, 12)
        start_date, end_date = get_monthspan(date)
        self.assertTrue(isinstance(start_date, datetime.date))
        self.assertTrue(isinstance(end_date, datetime.date))
        self.assertEqual(start_date, datetime.date(1978, 6, 1))
        self.assertEqual(end_date, datetime.date(1978, 6, 30))
        date = datetime.datetime(1978, 6, 12)
        start_date, end_date = get_monthspan(date)
        self.assertTrue(isinstance(start_date, datetime.datetime))
        self.assertTrue(isinstance(end_date, datetime.datetime))
        self.assertEqual(start_date, datetime.datetime(1978, 6, 1))
        self.assertEqual(end_date, datetime.datetime(1978, 6, 30))


class _QuarterspanTestCase(unittest.TestCase):
    """Unittests for get_quarterspan"""

    def test_first(self):
        """Tests for first quarter of a year"""
        start_date, end_date = get_quarterspan(datetime.date(1980, 1, 1))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 1, 1))
        self.assertEqual(end_date, datetime.date(1980, 3, 31))

        start_date, end_date = get_quarterspan(datetime.date(1980, 2, 29))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 1, 1))
        self.assertEqual(end_date, datetime.date(1980, 3, 31))

        start_date, end_date = get_quarterspan(datetime.date(1980, 3, 31))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 1, 1))
        self.assertEqual(end_date, datetime.date(1980, 3, 31))

    def test_second(self):
        """Tests for second quarter of a year"""
        start_date, end_date = get_quarterspan(datetime.date(1980, 4, 1))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 4, 1))
        self.assertEqual(end_date, datetime.date(1980, 6, 30))

        start_date, end_date = get_quarterspan(datetime.date(1980, 5, 4))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 4, 1))
        self.assertEqual(end_date, datetime.date(1980, 6, 30))

        start_date, end_date = get_quarterspan(datetime.date(1980, 6, 30))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 4, 1))
        self.assertEqual(end_date, datetime.date(1980, 6, 30))

    def test_third(self):
        """Tests for third quarter of a year"""
        start_date, end_date = get_quarterspan(datetime.date(1980, 7, 1))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 7, 1))
        self.assertEqual(end_date, datetime.date(1980, 9, 30))

        start_date, end_date = get_quarterspan(datetime.date(1980, 8, 4))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 7, 1))
        self.assertEqual(end_date, datetime.date(1980, 9, 30))

        start_date, end_date = get_quarterspan(datetime.date(1980, 9, 30))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 7, 1))
        self.assertEqual(end_date, datetime.date(1980, 9, 30))

    def test_fourth(self):
        """Tests the fourth quarter of a year"""
        start_date, end_date = get_quarterspan(datetime.date(1980, 10, 1))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 10, 1))
        self.assertEqual(end_date, datetime.date(1980, 12, 31))

        start_date, end_date = get_quarterspan(datetime.date(1980, 10, 1))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 10, 1))
        self.assertEqual(end_date, datetime.date(1980, 12, 31))

        start_date, end_date = get_quarterspan(datetime.date(1980, 12, 31))
        self.assertTrue(start_date < end_date)
        self.assertEqual(start_date, datetime.date(1980, 10, 1))
        self.assertEqual(end_date, datetime.date(1980, 12, 31))

    def test_all(self):
        """Tests the whole year"""

        # year = 1980  #unused
        date = datetime.date(1980, 1, 1)
        while date < datetime.date(1981, 1, 1):
            if date.month <= 3:
                mindate, maxdate = datetime.date(1980, 1, 1), datetime.date(1980, 3, 31)
            elif date.month <= 6:
                mindate, maxdate = datetime.date(1980, 4, 1), datetime.date(1980, 6, 30)
            elif date.month <= 9:
                mindate, maxdate = datetime.date(1980, 7, 1), datetime.date(1980, 9, 30)
            else:
                mindate, maxdate = datetime.date(1980, 10, 1), datetime.date(1980, 12, 31)

            startdate, enddate = get_quarterspan(date)
            self.assertTrue(startdate >= mindate)
            self.assertTrue(startdate <= maxdate)
            self.assertTrue(enddate >= mindate)
            self.assertTrue(enddate <= maxdate)

            date += datetime.timedelta(days=1)


class _TertialspanTestCase(unittest.TestCase):
    """Unittests for get_tertialspan"""

    def test_all(self):
        """Tests the whole year"""

        date = datetime.date(1980, 1, 1)
        while date < datetime.date(1981, 1, 1):
            if date.month <= 4:
                mindate, maxdate = datetime.date(1980, 1, 1), datetime.date(1980, 4, 30)
            elif date.month <= 8:
                mindate, maxdate = datetime.date(1980, 5, 1), datetime.date(1980, 8, 31)
            else:
                mindate, maxdate = datetime.date(1980, 9, 1), datetime.date(1980, 12, 31)

            startdate, enddate = get_tertialspan(date)
            self.assertTrue(startdate >= mindate)
            self.assertTrue(startdate <= maxdate)
            self.assertTrue(enddate >= mindate)
            self.assertTrue(enddate <= maxdate)

            date += datetime.timedelta(days=1)


class _WorkdayTests(unittest.TestCase):
    """Testcases for workdays module. Calendar hint:
        November 2006         December 2006          January 2007
     S  M Tu  W Th  F  S   S  M Tu  W Th  F  S   S  M Tu  W Th  F  S
              1  2  3  4                  1  2      1  2  3  4  5  6
     5  6  7  8  9 10 11   3  4  5  6  7  8  9   7  8  9 10 11 12 13
    12 13 14 15 16 17 18  10 11 12 13 14 15 16  14 15 16 17 18 19 20
    19 20 21 22 23 24 25  17 18 19 20 21 22 23  21 22 23 24 25 26 27
    26 27 28 29 30        24 25 26 27 28 29 30  28 29 30 31
                          31
    """

    def test_workdays(self):
        """Simple minded tests for workdays()."""
        date = datetime.date

        self.assertEqual(0, workdays(date(2007, 1, 25), date(2007, 1, 25)))    # Th - Th
        self.assertEqual(1, workdays(date(2007, 1, 25), date(2007, 1, 26)))    # Th - Fr
        self.assertEqual(2, workdays(date(2007, 1, 25), date(2007, 1, 27)))    # Th - Sa
        self.assertEqual(1, workdays(date(2007, 1, 26), date(2007, 1, 27)))    # Fr - Sa
        self.assertEqual(1, workdays(date(2007, 1, 26), date(2007, 1, 28)))    # Fr - Su
        self.assertEqual(1, workdays(date(2007, 1, 26), date(2007, 1, 29)))    # Fr - Mo
        self.assertEqual(0, workdays(date(2007, 1, 28), date(2007, 1, 29)))    # Su - Mo
        self.assertEqual(2, workdays(date(2007, 1, 26), date(2007, 1, 30)))    # Fr - Tu
        self.assertEqual(1, workdays(date(2007, 1, 28), date(2007, 1, 30)))    # Su - Tu

        self.assertEqual(0, workdays(date(2007, 1, 26), date(2007, 1, 26)))    # Fr - Fr
        self.assertEqual(1, workdays(date(2007, 1, 26), date(2007, 1, 27)))    # Fr - Sa
        self.assertEqual(1, workdays(date(2007, 1, 26), date(2007, 1, 28)))    # Fr - Su
        self.assertEqual(0, workdays(date(2007, 1, 27), date(2007, 1, 28)))    # Sa - So
        self.assertEqual(0, workdays(date(2007, 1, 27), date(2007, 1, 29)))    # Sa - Mo
        self.assertEqual(1, workdays(date(2007, 1, 27), date(2007, 1, 30)))    # Fr - Tu

        self.assertEqual(0, workdays(date(2006, 11, 29), date(2006, 11, 29)))  # We - We
        self.assertEqual(1, workdays(date(2006, 11, 29), date(2006, 11, 30)))  # We - Th
        self.assertEqual(1, workdays(date(2006, 11, 30), date(2006, 12, 1)))   # Th - Fr
        self.assertEqual(5, workdays(date(2006, 12, 12), date(2006, 12, 19)))  # Tu - Tu
        self.assertEqual(0, workdays(date(2006, 11, 20), date(2006, 11, 20)))
        self.assertEqual(1, workdays(date(2006, 11, 20), date(2006, 11, 21)))
        self.assertEqual(4, workdays(date(2006, 11, 20), date(2006, 11, 24)))
        self.assertEqual(5, workdays(date(2006, 11, 20), date(2006, 11, 25)))  # Mo - Sa
        self.assertEqual(5, workdays(date(2006, 11, 20), date(2006, 11, 26)))  # Mo - Su
        self.assertEqual(5, workdays(date(2006, 11, 20), date(2006, 11, 27)))
        self.assertEqual(5, workdays(date(2006, 12, 25), date(2007, 1, 1)))
        self.assertEqual(6, workdays(date(2006, 12, 8), date(2006, 12, 18)))
        self.assertEqual(5, workdays(date(2006, 12, 9), date(2006, 12, 18)))
        self.assertEqual(0, workdays(date(2006, 12, 17), date(2006, 12, 18)))
        self.assertEqual(1, workdays(date(2006, 12, 17), date(2006, 12, 19)))
        self.assertEqual(4, workdays(date(2006, 12, 17), date(2006, 12, 22)))
        self.assertEqual(5, workdays(date(2006, 12, 17), date(2006, 12, 23)))  # Su - Sa
        self.assertEqual(5, workdays(date(2006, 12, 17), date(2006, 12, 24)))  # Su - Su
        self.assertEqual(5, workdays(date(2006, 12, 17), date(2006, 12, 25)))
        self.assertEqual(261, workdays(date(2004, 1, 1), date(2004, 12, 31)))
        self.assertEqual(260, workdays(date(2005, 1, 1), date(2005, 12, 31)))
        self.assertEqual(260, workdays(date(2006, 1, 1), date(2006, 12, 31)))
        self.assertEqual(260, workdays(date(2007, 1, 1), date(2007, 12, 31)))
        self.assertEqual(261, workdays(date(2008, 1, 1), date(2008, 12, 31)))
        self.assertEqual(260 + 260, workdays(date(2005, 1, 1), date(2006, 12, 31)))
        self.assertEqual(260 + 260 + 260, workdays(date(2005, 1, 1), date(2007, 12, 31)))
        self.assertEqual(260 + 260 + 260, workdays(datetime.datetime(2005, 1, 1),
                                                   datetime.datetime(2007, 12, 31)))

    def test_workdays_german(self):
        """Simple minded tests for workdays_german()."""
        date = datetime.date
        self.assertEqual(0, workdays_german(date(2007, 1, 25), date(2007, 1, 25)))  # Th - Th
        self.assertEqual(1, workdays_german(date(2007, 1, 25), date(2007, 1, 26)))  # Th - Fr
        self.assertEqual(2, workdays_german(date(2007, 1, 25), date(2007, 1, 27)))  # Th - Sa
        self.assertEqual(1, workdays_german(date(2007, 1, 26), date(2007, 1, 27)))  # Fr - Sa
        self.assertEqual(1, workdays_german(date(2007, 1, 26), date(2007, 1, 28)))  # Fr - Su
        self.assertEqual(1, workdays_german(date(2007, 1, 26), date(2007, 1, 29)))  # Fr - Mo
        self.assertEqual(0, workdays_german(date(2007, 1, 28), date(2007, 1, 29)))  # Su - Mo
        self.assertEqual(2, workdays_german(date(2007, 1, 26), date(2007, 1, 30)))  # Fr - Tu
        self.assertEqual(1, workdays_german(date(2007, 1, 28), date(2007, 1, 30)))  # Su - Tu

        self.assertEqual(0, workdays_german(date(2007, 1, 26), date(2007, 1, 26)))  # Fr - Fr
        self.assertEqual(1, workdays_german(date(2007, 1, 26), date(2007, 1, 27)))  # Fr - Sa
        self.assertEqual(1, workdays_german(date(2007, 1, 26), date(2007, 1, 28)))  # Fr - Su
        self.assertEqual(0, workdays_german(date(2007, 1, 27), date(2007, 1, 28)))  # Sa - So
        self.assertEqual(0, workdays_german(date(2007, 1, 27), date(2007, 1, 29)))  # Sa - Mo
        self.assertEqual(1, workdays_german(date(2007, 1, 27), date(2007, 1, 30)))  # Fr - Tu

        self.assertEqual(3, workdays_german(date(2006, 12, 25), date(2007, 1, 1)))
        self.assertEqual(1, workdays_german(date(2007, 2, 2), date(2007, 2, 5)))
        self.assertEqual(252, workdays_german(date(2005, 1, 1), date(2005, 12, 31)))
        self.assertEqual(250, workdays_german(date(2006, 1, 1), date(2006, 12, 31)))
        self.assertEqual(249, workdays_german(date(2007, 1, 1), date(2007, 12, 31)))
        self.assertEqual(251, workdays_german(date(2008, 1, 1), date(2008, 12, 31)))
        # Christi Himmelfahrt
        self.assertEqual(1, workdays_german(date(2007, 5, 16), date(2007, 5, 17)))
        self.assertEqual(1, workdays_german(date(2007, 5, 16), date(2007, 5, 18)))
        self.assertEqual(1, workdays_german(datetime.datetime(2007, 5, 16), datetime.datetime(2007, 5, 18)))
        # Pfingsten
        self.assertEqual(1, workdays_german(date(2007, 5, 24), date(2007, 5, 25)))  # Th - Fr
        self.assertEqual(1, workdays_german(date(2007, 5, 25), date(2007, 5, 26)))  # Fr - Sa
        self.assertEqual(1, workdays_german(date(2007, 5, 25), date(2007, 5, 27)))  # Fr - So
        self.assertEqual(1, workdays_german(date(2007, 5, 25), date(2007, 5, 28)))  # Fr - Mo
        self.assertEqual(1, workdays_german(date(2007, 5, 25), date(2007, 5, 29)))  # Fr - Tu
        # Christi Himmelfahrt
        self.assertEqual(1, workdays_german(date(2007, 6, 6), date(2007, 6, 7)))
        self.assertEqual(1, workdays_german(date(2007, 6, 6), date(2007, 6, 8)))
        self.assertEqual(252 + 250, workdays_german(date(2005, 1, 1), date(2006, 12, 31)))
        self.assertEqual(252 + 250 + 249, workdays_german(date(2005, 1, 1), date(2007, 12, 31)))

        self.assertEqual(252 + 250 + 249, workdays_german(datetime.datetime(2005, 1, 1),
                                                          datetime.datetime(2007, 12, 31)))

    def test_is_workday_german(self):
        self.assertTrue(is_workday_german(datetime.date(2011, 4, 21)))  # Gründonnerstag
        self.assertFalse(is_workday_german(datetime.date(2011, 4, 22)))   # karfreitag

        self.assertTrue(is_workday_german(datetime.datetime(2011, 4, 21, 0, 0)))
        self.assertFalse(is_workday_german(datetime.datetime(2011, 4, 22, 0, 0)))

    def test_next_workday_german(self):
        """Simple minded tests for next_workday_german()."""
        date = datetime.date
        self.assertEqual(date(2007, 5, 21), next_workday_german(date(2007, 5, 18)))  # Fr
        self.assertEqual(date(2007, 5, 22), next_workday_german(date(2007, 5, 21)))  # Mo
        self.assertEqual(date(2007, 5, 25), next_workday_german(date(2007, 5, 24)))  # Th
        # Pfingsten
        self.assertEqual(date(2007, 5, 29), next_workday_german(date(2007, 5, 25)))  # Fr
        self.assertEqual(date(2007, 5, 29), next_workday_german(date(2007, 5, 26)))  # Sa
        self.assertEqual(date(2007, 5, 29), next_workday_german(date(2007, 5, 27)))  # Su
        self.assertEqual(date(2007, 5, 29), next_workday_german(date(2007, 5, 28)))  # Mo ( Holiday)
        self.assertEqual(date(2007, 5, 31), next_workday_german(date(2007, 5, 30)))
        self.assertEqual(datetime.datetime(2007, 5, 31), next_workday_german(datetime.datetime(2007, 5, 30)))

    def test_add_workdays_german(self):
        """Simple minded tests for add_workdays_german,"""
        date = datetime.date
        self.assertEqual(date(2008, 11, 24), add_workdays_german(date(2008, 11, 24), 0))
        self.assertEqual(date(2008, 11, 25), add_workdays_german(date(2008, 11, 24), 1))
        self.assertEqual(date(2008, 12, 1), add_workdays_german(date(2008, 11, 24), 5))
        self.assertEqual(date(2008, 11, 21), add_workdays_german(date(2008, 11, 24), -1))
        self.assertEqual(date(2008, 11, 14), add_workdays_german(date(2008, 11, 24), -6))
        self.assertEqual(datetime.datetime(2008, 11, 14),
                         add_workdays_german(datetime.datetime(2008, 11, 24), -6))


class _ApiTests(unittest.TestCase):

    def test_defaults(self):
        """Test rfc3339_date defaults"""
        rfc3339_date()
        rfc2616_date()


class _DateTruncTestCase(unittest.TestCase):
    """Unittests for date_trunc"""

    def test_truncate_year(self):
        self.assertEqual(date_trunc('year', datetime.datetime(1980, 5, 4)), datetime.datetime(1980, 1, 1))
        self.assertEqual(date_trunc('year', datetime.datetime(1980, 5, 4)).date(), datetime.date(1980, 1, 1))
        self.assertEqual(date_trunc('year', datetime.date(1980, 5, 4)),
                         datetime.date(1980, 1, 1,))
        self.assertEqual(date_trunc('year', datetime.date(1980, 5, 4)), datetime.date(1980, 1, 1))

    def test_truncate_tertial(self):
        self.assertEqual(date_trunc('tertial', datetime.datetime(2011, 4, 30)), datetime.datetime(2011, 1, 1))
        self.assertEqual(date_trunc('tertial', datetime.datetime(2011, 4, 30)).date(),
                         datetime.date(2011, 1, 1))
        self.assertEqual(date_trunc('tertial', datetime.date(2011, 5, 1)),
                         datetime.date(2011, 5, 1))
        self.assertEqual(date_trunc('tertial', datetime.date(2011, 8, 31)), datetime.date(2011, 5, 1))
        self.assertEqual(date_trunc('tertial', datetime.date(2011, 9, 1)), datetime.date(2011, 9, 1))

    def test_truncate_quarter(self):
        self.assertEqual(date_trunc('quarter', datetime.datetime(1945, 2, 19)), datetime.datetime(1945, 1, 1))
        self.assertEqual(date_trunc('quarter', datetime.datetime(1945, 2, 19)).date(),
                         datetime.date(1945, 1, 1))
        self.assertEqual(date_trunc('quarter', datetime.date(1945, 2, 19)),
                         datetime.date(1945, 1, 1))
        self.assertEqual(date_trunc('quarter', datetime.date(1945, 2, 19)), datetime.date(1945, 1, 1))

        self.assertEqual(date_trunc('quarter', datetime.datetime(1980, 5, 4)), datetime.datetime(1980, 4, 1))
        self.assertEqual(date_trunc('quarter', datetime.datetime(1980, 5, 4)).date(),
                         datetime.date(1980, 4, 1))
        self.assertEqual(date_trunc('quarter', datetime.date(1980, 5, 4)),
                         datetime.date(1980, 4, 1))
        self.assertEqual(date_trunc('quarter', datetime.date(1980, 5, 4)), datetime.date(1980, 4, 1))

        self.assertEqual(date_trunc('quarter', datetime.datetime(1951, 7, 22)), datetime.datetime(1951, 7, 1))
        self.assertEqual(date_trunc('quarter', datetime.datetime(1951, 7, 22)).date(),
                         datetime.date(1951, 7, 1))
        self.assertEqual(date_trunc('quarter', datetime.date(1951, 7, 22)),
                         datetime.date(1951, 7, 1))
        self.assertEqual(date_trunc('quarter', datetime.date(1951, 7, 22)), datetime.date(1951, 7, 1))

        self.assertEqual(date_trunc('quarter', datetime.datetime(2000, 12, 31)),
                         datetime.datetime(2000, 10, 1))
        self.assertEqual(date_trunc('quarter', datetime.datetime(2000, 12, 31)).date(),
                         datetime.date(2000, 10, 1))
        self.assertEqual(date_trunc('quarter', datetime.date(2000, 12, 31)),
                         datetime.date(2000, 10, 1))
        self.assertEqual(date_trunc('quarter', datetime.date(2000, 12, 31)), datetime.date(2000, 10, 1))

    def test_truncate_month(self):
        self.assertEqual(date_trunc('month', datetime.datetime(1978, 6, 12)), datetime.datetime(1978, 6, 1))
        self.assertEqual(date_trunc('month', datetime.datetime(1978, 6, 12)).date(),
                         datetime.date(1978, 6, 1))
        self.assertEqual(date_trunc('month', datetime.date(1978, 6, 12)),
                         datetime.date(1978, 6, 1))
        self.assertEqual(date_trunc('month', datetime.date(1978, 6, 12)), datetime.date(1978, 6, 1))

    def test_truncate_week(self):
        self.assertEqual(date_trunc('week', datetime.datetime(2000, 1, 1)), datetime.datetime(1999, 12, 27))
        self.assertEqual(date_trunc('week', datetime.datetime(2000, 1, 1)).date(),
                         datetime.date(1999, 12, 27))
        self.assertEqual(date_trunc('week', datetime.date(2000, 1, 1)),
                         datetime.date(1999, 12, 27))
        self.assertEqual(date_trunc('week', datetime.date(2000, 1, 1)), datetime.date(1999, 12, 27))

    def test_truncate_day(self):
        self.assertEqual(date_trunc('day', datetime.datetime(2006, 2, 25, 23, 17, 40)),
                         datetime.datetime(2006, 2, 25))
        self.assertEqual(date_trunc('day', datetime.datetime(2006, 2, 25)), datetime.datetime(2006, 2, 25))
        self.assertEqual(date_trunc('day', datetime.date(2006, 2, 25)),
                         datetime.date(2006, 2, 25))
        self.assertEqual(date_trunc('day', datetime.date(2006, 2, 25)), datetime.date(2006, 2, 25))

    def test_truncate_hour(self):
        self.assertEqual(date_trunc('hour', datetime.datetime(2006, 2, 25, 23, 17, 40), ),
                         datetime.datetime(2006, 2, 25, 23))
        self.assertEqual(date_trunc('hour', datetime.datetime(2006, 2, 25, 23, 17, 40)),
                         datetime.datetime(2006, 2, 25, 23, 0, 0))
        self.assertEqual(date_trunc('hour', datetime.date(2006, 2, 25)),
                         datetime.date(2006, 2, 25))
        self.assertEqual(date_trunc('hour', datetime.date(2006, 2, 25)), datetime.date(2006, 2, 25))

    def test_truncate_minute(self):
        self.assertEqual(date_trunc('minute', datetime.datetime(2006, 2, 25, 23, 17, 40)),
                         datetime.datetime(2006, 2, 25, 23, 17, 0))
        self.assertEqual(date_trunc('minute', datetime.date(2006, 2, 25)),
                         datetime.date(2006, 2, 25))
        self.assertEqual(date_trunc('minute', datetime.date(2006, 2, 25)),
                         datetime.date(2006, 2, 25))

    def test_truncate_second(self):
        self.assertEqual(date_trunc('second', datetime.datetime(2006, 2, 25, 23, 17, 40)),
                         datetime.datetime(2006, 2, 25, 23, 17, 40))
        self.assertEqual(date_trunc('second', datetime.date(2006, 2, 25)),
                         datetime.date(2006, 2, 25))
        self.assertEqual(date_trunc('second', datetime.date(2006, 2, 25)),
                         datetime.date(2006, 2, 25))

    def test_invalid(self):
        self.assertRaises(ValueError, date_trunc, 'alex', datetime.datetime.now())


if __name__ == '__main__':
    failure_count, test_count = doctest.testmod()
    unittest.main()
    sys.exit(failure_count)
