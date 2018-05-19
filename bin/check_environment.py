#!/usr/bin/env python
# encoding: utf-8
"""
Check if the stuff needed to develop with appengine toolkit is available.

Created by Maximillian Dornseif on 2018-01-11.
Copyright (c) 2018 Cyberlogi. MIT licensed.
"""
import collections
import os
import subprocess
import sys


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
        print "-> please install", repr(command.split()[0])
        print output
        print 'try %r' % doc
        sys.exit(1)

    print "+ exists", repr(command.split()[0]), output.split('\n')[0]


# file and how to build it if it does not exist
targets = {
'lib/google_appengine/appcfg.py':
"""
    curl -s -O https://storage.googleapis.com/appengine-sdks/featured/google_appengine_{GAE_VERSION}.zip
    unzip -q google_appengine_{GAE_VERSION}.zip
    rm -Rf lib/google_appengine
    mv google_appengine lib/
    rm google_appengine_{GAE_VERSION}.zip
""",
}

for target, commands in targets.items():
    if os.path.exists(target):
        print "+ exists", repr(target)
    else:
        print "-> building", repr(target)
        for line in commands.split('\n'):
            line = line.strip()
            if line:
                cmd = line.format(**config)
                returncode = subprocess.call(cmd, shell=True)
                if returncode:
                    print returncode, cmd


# install required libraries
requirements = os.path.abspath(os.path.join(__file__, '../../requirements-dev.txt'))
cmd = 'pip --quiet install -r {}'.format(requirements)
print "->", cmd
subprocess.check_call(cmd, shell=True)
