#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/handlers/legacy.py - emulate gaetk Version 1 interfaces.

Created by Maximillian Dornseif on 2017-06-26.
Copyright (c) 2017, 2018 HUDORA. MIT licnsed.
"""
import warnings

from gaetk2.config import get_release, is_production

from .mixins.multirender import MultirenderMixin
from .mixins.paginate import PaginateMixin


class Gaetk1Mixin(PaginateMixin, MultirenderMixin):
    """Emulate gaetk.handler methods which have been removed in gaetk2."""

    def abort(self, code, *args, **kwargs):
        """Emulate ambigus Method."""
        warnings.warn(
            "abort() hides control flow. `raise WSGIHTTPException` instead.",
            DeprecationWarning, stacklevel=2)
        return super(Gaetk1Mixin, self).abort(code, *args, **kwargs)

    def redirect(self, uri, permanent=False, abort=False, code=None,
                 body=None):
        """Emulate ambigus Method."""
        warnings.warn(
            "redirect() hides control flow. `raise HTTPRedirection` instead.",
            DeprecationWarning, stacklevel=2)
        return super(Gaetk1Mixin, self).redirect(
            uri, permanent=permanent, abort=abort, code=code, body=body)

    def redirect_to(self, _name, _permanent=False, _abort=False, _code=None,
                    _body=None, *args, **kwargs):
        """Emulate ambigus Method."""
        warnings.warn(
            "redirect_to() hides control flow. `raise HTTPRedirection` instead.",
            DeprecationWarning, stacklevel=2)
        return super(Gaetk1Mixin, self).redirect_to(
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
            "use create_jinja2env() is not needed anymore, use `add_jinja2env_globals()` instead.",
            DeprecationWarning, stacklevel=2)
        return self._create_jinja2env()

    def add_jinja2env_globals(self, env):
        """Set variables to be used in the supplied bootstrap templates."""
        sup = super(Gaetk1Mixin, self)
        if hasattr(sup, 'add_jinja2env_globals'):
            sup.add_jinja2env_globals(env)

        env.globals['ist_produktion'] = is_production()  # TODO: use `gaetk_production`
        env.globals['beta_banner'] = ''
        env.globals['release'] = get_release()
        # if not is_production():
        #     # from https://codepen.io/eode9/pen/twkKm
        #     env.globals['beta_banner'] = (
        #         '<style>.corner-ribbon{z-index: 1001; width: 200px; background: #e43; position: absolute;'
        #         'top: 25px; left: -50px; text-align: center; line-height: 50px;'
        #         'letter-spacing: 1px; color: #f0f0f0; transform: rotate(-45deg);'
        #         '-webkit-transform: rotate(-45deg); }\n'
        #         '.corner-ribbon.sticky{ position: fixed; }\n'
        #         '.corner-ribbon.shadow{ box-shadow: 0 0 3px rgba(0,0,0,.3); }\n'
        #         '.corner-ribbon.bottom-right{ top: auto; right: -50px; bottom: 25px;'
        #         'left: auto; transform: rotate(-45deg); -webkit-transform: rotate(-45deg);}\n'
        #         '.corner-ribbon.red{background: #e43;}\n'
        #         '</style><div class="corner-ribbon bottom-right sticky red shadow">Development</div>')
        return env
