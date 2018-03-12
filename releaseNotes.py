#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Release notes generation
# ----------------------------------------------------------------------------
# File       : releaseNotes.py
# Created    : 2018-03-12
# ----------------------------------------------------------------------------
# Description:
# Generate release notes for pull requests relative to a tag.
# Usage: releaseNotes.py tag (i.e. releaseNotes.py v2.5.0
#
# Must be run within an up to date git clone with the proper branch checked out.
# Currently github complains if you run this script too many times in a short
# period of time. I am still looking at ssh key support for PyGithub
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------
import os,sys
import git   # GitPython
from github import Github # PyGithub
import pyperclip

if len(sys.argv) != 2:
    print("Usage: {} prev_release".format(sys.argv[0]))
    print("    Must be called in a git clone directory")
    exit()

prev = sys.argv[1]
print('Using previous release {}'.format(prev))

# Local git clone
g = git.Git('.')
g.fetch()

# Git server
gh = Github()
repo = gh.get_repo('slaclab/rogue')

loginfo = g.log('{}..origin/master'.format(prev),'--grep','Merge pull request')

print("Got log:")

records = []
msgEn = False

for line in loginfo.splitlines():
    entry = {}

    if line.startswith('Author:'):
        entry['author'] = line[7:]

    elif line.startswith('Date:'):
        entry['date'] = line[5:]

    elif 'Merge pull request' in line:
        entry['num'] = int(line.split()[3][1:])
        entry['branch'] = line.split()[5]

        # Get PR info
        req = repo.get_pull(int(entry[num]))
        entry['title'] = req.title
        entry['body']  = req.body

        # Detect JIRA
        if src.startswith('slaclab/ES'):
            entry['jira'] = 'https://jira.slac.stanford.edu/issues/{}'.format(entry['branch'].split('/')[1])

    records.append(entry)

# Generate text
txt = ''
for entry in records:
    txt += '--------------------------------------------------------------------------------------------------\n"
    txt += 'Author: {}'.format(entry['author'])



txt = ''
for l in out:
    print(l)
    txt += (l + '\n')

pyperclip.copy(txt)
print('')
print('---------------------------------')
print('Release notes copied to clipboard')
print('---------------------------------')

