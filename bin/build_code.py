#!/usr/bin/env python
# encoding: utf-8
"""
Build all JS and misc code required in a gaetk2 project.

Created by Maximillian Dornseif on 2018-01-11.
Copyright (c) 2018 Cyberlogi. MIT licensed.
"""
import collections
import optparse
import os
import subprocess
import sys

config = dict(
    GAE_VERSION='1.9.51'
)


taskrunners = collections.OrderedDict([
    ('package.json', 'yarn --global'),
    ('Gruntfile.js', 'grunt'),
    ('js_src/package.json', '(cd js_src; yarn)'),
])


def main():
       """Main Entry Point."""
    parser = optparse.OptionParser()
    parser.add_option('-p', '--production', default=False, action='store_true', help=u'build production version')
    options, args = parser.parse_args()

    if optparse.production:
        os.environ['NODE_ENV'] = 'production'
        os.environ['GAETK_PRODUCTION'] = 1

    for target, command in taskrunners.items():
        if os.path.exists(target):
            print "-> executing {} for {}".format(command, target)
            cmd = command.format(**config)
            subprocess.check_call(cmd, shell=True)


# # install required libraries
# print '-> pip --quiet install -r requirements-dev.txt'
# subprocess.check_call('pip --quiet install -r requirements-dev.txt', shell=True)


if __name__ == '__main__':
    main()
