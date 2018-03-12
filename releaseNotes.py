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

# Git server
gh = Github()
repo = gh.get_repo('slaclab/rogue')

loginfo = g.log('{}..HEAD'.format(prev),'--grep','Merge pull request')

print("Got log:")

out = []
msgEn = False

for line in loginfo.splitlines():

    if line.startswith('commit'):
        msgEn = False

    elif line.startswith('Author:'):
        out.append("--------------------------------------------------------------------------------------------------")
        out.append(line)

    elif line.startswith('Date:'):
        out.append(line)

    # get pull request
    elif 'Merge pull request' in line:
        pr = line.split()[3]
        src = line.split()[5]

        # Get PR info
        req = repo.get_pull(int(pr[1:]))

        out.append('Pull Req: {}'.format(pr))
        out.append('Branch: {}'.format(src))

        if src.startswith('slaclab/ES'):
            out.append('Jira: https://jira.slac.stanford.edu/issues/{}'.format(src.split('/')[1]))

        out.append('Title: {}'.format(req.title))
        out.append("\n" + req.body + "\n")

txt = ''
for l in out:
    print(l)
    txt += (l + '\n')

pyperclip.copy(txt)
print('')
print('---------------------------------')
print('Release notes copied to clipboard')
print('---------------------------------')

