#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/handlers/legacy.py - emulate gaetk Version 1 interfaces.

Created by Maximillian Dornseif on 2017-06-26.
Copyright (c) 2017 HUDORA. MIT licnsed.
"""
import warnings


from .mixins import BootstrapMixin
from .mixins import PaginateMixin


class OldGaetkMixin(PaginateMixin, BootstrapMixin):
    """Emulate gaetk.handler methods which have been removed in gaetk2."""

    def abort(self, code, *args, **kwargs):
        """Emulate ambigus Method."""
        warnings.warn(
            "abort() hides control flow. `raise WSGIHTTPException` instead.",
            DeprecationWarning, stacklevel=2)
        return super(OldGaetkMixin, self).abort(code, *args, **kwargs)

    def redirect(self, uri, permanent=False, abort=False, code=None,
                 body=None):
        """Emulate ambigus Method."""
        warnings.warn(
            "redirect() hides control flow. `raise HTTPRedirection` instead.",
            DeprecationWarning, stacklevel=2)
        return super(OldGaetkMixin, self).redirect(
            uri, permanent=permanent, abort=abort, code=code, body=body)

    def redirect_to(self, _name, _permanent=False, _abort=False, _code=None,
                    _body=None, *args, **kwargs):
        """Emulate ambigus Method."""
        warnings.warn(
            "redirect_to() hides control flow. `raise HTTPRedirection` instead.",
            DeprecationWarning, stacklevel=2)
        return super(OldGaetkMixin, self).redirect_to(
            _name, _permanent=_permanent, _abort=_abort, _code=_code,
            _body=_body, *args, **kwargs)

    def is_admin(self):
        """Emulate ambigus Method."""
        warnings.warn(
            "use is_admin() is ambigus, use `is_sysadmin()` instead.",
            DeprecationWarning, stacklevel=2)
        return self.is_sysadmin()

    def create_jinja2env(self):
        """Emulate old - and unneeded - Method."""
        warnings.warn(
            "use create_jinja2env() is not needed anymore, overwrite `add_jinja2env_globals()` instead.",
            DeprecationWarning, stacklevel=2)
        return self._create_jinja2env()
