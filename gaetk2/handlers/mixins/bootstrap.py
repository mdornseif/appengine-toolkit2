#!/usr/bin/env python
# encoding: utf-8
"""
gaetk2/handlers/mixins.py - misc functionality to be added to gaetk handlers.

Created by Maximillian Dornseif on 2010-10-03.
Copyright (c) 2010-2017 HUDORA. MIT licensed.
"""
from gaetk2.tools.config import get_version
from gaetk2.tools.config import is_production


class BootstrapMixin(object):
    """Support for the supplied bootstrap templates."""

    def add_jinja2env_globals(self, env):
        """Set variables to be used in the supplied bootstrap templates."""
        sup = super(BootstrapMixin, self)
        if hasattr(sup, 'add_jinja2env_globals'):
            sup.add_jinja2env_globals(env)

        env.globals['ist_produktion'] = is_production()  # TODO: use `gaetk_production`
        env.globals['beta_banner'] = ''
        env.globals['release'] = get_version()
        if not is_production():
            # from https://codepen.io/eode9/pen/twkKm
            env.globals['beta_banner'] = (
                '<style>.corner-ribbon{z-index: 1001; width: 200px; background: #e43; position: absolute;'
                'top: 25px; left: -50px; text-align: center; line-height: 50px;'
                'letter-spacing: 1px; color: #f0f0f0; transform: rotate(-45deg);'
                '-webkit-transform: rotate(-45deg); }\n'
                '.corner-ribbon.sticky{ position: fixed; }\n'
                '.corner-ribbon.shadow{ box-shadow: 0 0 3px rgba(0,0,0,.3); }\n'
                '.corner-ribbon.bottom-right{ top: auto; right: -50px; bottom: 25px;'
                'left: auto; transform: rotate(-45deg); -webkit-transform: rotate(-45deg);}\n'
                '.corner-ribbon.red{background: #e43;}\n'
                '</style><div class="corner-ribbon bottom-right sticky red shadow">Development</div>')
