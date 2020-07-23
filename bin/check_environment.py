#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check if the stuff needed to develop with appengine toolkit is available.

Created by Maximillian Dornseif on 2018-01-11.
Copyright (c) 2018, 2020 Cyberlogi. MIT licensed.
"""
from __future__ import unicode_literals

import collections
import os
import subprocess
import sys

import pkg_resources


config = dict(
    GAE_VERSION='1.9.69'
)


# tools which have to be installed and how to install them
# key is command to check
# value should be installation on how to install
tools = collections.OrderedDict([
    ('python --version', 'Irgendwas ist ganz fishy, weenn Python nicht gefunden wird'),
    ('pip --version', 'https://pip.pypa.io/en/stable/installing/'),
    # ('brew --version', 'https://docs.brew.sh/Installation.html'),
    ('make --version', 'https://developer.apple.com/downloads/index.action'),
    ('npm bin', 'https://nodejs.org/en/'),
    ('yarn versions', 'https://classic.yarnpkg.com/en/docs/install/'),
    ('gcloud --version', 'https://cloud.google.com/sdk/downloads'),
    ('docker --version', 'https://docs.docker.com/docker-for-mac/'),
    ('git --version', 'brew install git'),
    ('yarn --version', 'brew install yarn'),
])

for command, doc in tools.items():
    output = ''
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True, close_fds=True)
    except subprocess.CalledProcessError:
        print '-> please install', repr(command.split()[0])
        print output
        print 'try %r' % doc
        sys.exit(1)

    print '+ exists', repr(command.split()[0]), output.split('\n')[0]

# install required libraries
dpath, _ = os.path.split(__file__)
rpath = os.path.join(dpath, '../requirements-dev.txt')
dependencies = open(rpath).read().splitlines()
try:
    pkg_resources.require(dependencies)
except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict), e:
    print '-> please install python modules',
    print e
    print 'try `sudo pip2 install -r lib/appengine-toolkit2/requirements-dev.txt`'
    sys.exit(1)
print '+ exists', 'Python Modules in', rpath
