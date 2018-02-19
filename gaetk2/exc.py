#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/exec - Exception including HTTP Status Codes.

Just a mapping of `webob.exec`.

Created by Maximillian Dornseif on 2017-06-26.
Copyright (c) 2017 HUDORA. MIT licnsed.
"""

from webob.exc import HTTPBadRequest as HTTP400_BadRequest
from webob.exc import HTTPConflict as HTTP409_Conflict
from webob.exc import HTTPForbidden as HTTP403_Forbidden
from webob.exc import HTTPFound as HTTP302_Found
from webob.exc import HTTPGone as HTTP410_Gone
from webob.exc import HTTPMethodNotAllowed as HTTP405_HTTPMethodNotAllowed
from webob.exc import HTTPMovedPermanently as HTTP301_Moved
from webob.exc import HTTPNotAcceptable as HTTP406_NotAcceptable
from webob.exc import HTTPNotFound as HTTP404_NotFound
from webob.exc import HTTPNotImplemented as HTTP501_NotImplemented
from webob.exc import HTTPRequestEntityTooLarge as HTTP413_TooLarge
from webob.exc import HTTPSeeOther as HTTP303_SeeOther
from webob.exc import HTTPServerError as HTTP500_ServerError
from webob.exc import HTTPServiceUnavailable as HTTP503_ServiceUnavailable
from webob.exc import HTTPTemporaryRedirect as HTTP307_TemporaryRedirect
from webob.exc import HTTPUnauthorized as HTTP401_Unauthorized
from webob.exc import HTTPUnsupportedMediaType as HTTP415_UnsupportedMediaType
from webob.exc import HTTPException

__all__ = [
    'HTTPException',
    'HTTP301_Moved',
    'HTTP302_Found',
    'HTTP303_SeeOther',
    'HTTP307_TemporaryRedirect',
    'HTTP400_BadRequest',
    'HTTP401_Unauthorized',
    'HTTP403_Forbidden',
    'HTTP404_NotFound',
    'HTTP405_HTTPMethodNotAllowed',
    'HTTP406_NotAcceptable',
    'HTTP307_TemporaryRedirect',
    'HTTP409_Conflict',
    'HTTP410_Gone',
    'HTTP413_TooLarge',
    'HTTP415_UnsupportedMediaType',
    'HTTP500_ServerError',
    'HTTP501_NotImplemented',
    'HTTP503_ServiceUnavailable'
]

# acoid unwanted Information being pushed to Sentry
HTTP301_Moved.explanation = None
HTTP302_Found.explanation = None
HTTP303_SeeOther.explanation = None
HTTP307_TemporaryRedirect.explanation = None
HTTP401_Unauthorized.explanation = None
HTTP403_Forbidden.explanation = None
HTTP404_NotFound.explanation = None
HTTP405_HTTPMethodNotAllowed.explanation = None
