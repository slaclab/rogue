#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Release notes generation
# ----------------------------------------------------------------------------
# File       : releaseNotes.py
# Created    : 2018-03-12
# ----------------------------------------------------------------------------
# Description:
# Generate release notes for pull requests relative to a tag.
# Usage: releaseNotes.py tag out_file (i.e. releaseNotes.py v2.5.0 notes.txt)
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

if len(sys.argv) != 3:
    print("Usage: {} prev_release out_file".format(sys.argv[0]))
    print("    Replace out_file with - to copy to clipboard")
    print("    Must be called in a git clone directory")
    print("    Example {} v2.5.0 notes.txt")
    exit()

sortByChanges = True

prev = sys.argv[1]
out  = sys.argv[2]
print('Using previous release {}'.format(prev))
print("Please wait...")

# Local git clone
g = git.Git('.')
g.fetch()

# Git server
gh = Github()
repo = gh.get_repo('slaclab/rogue')

loginfo = g.log('{}..origin/master'.format(prev),'--grep','Merge pull request')

records = []
entry = {}

# Parse the log entries
for line in loginfo.splitlines():

    if line.startswith('Author:'):
        entry['Author'] = line[7:].lstrip()

    elif line.startswith('Date:'):
        entry['Date'] = line[5:].lstrip()

    elif 'Merge pull request' in line:
        entry['Pull'] = line.split()[3].lstrip()
        entry['Branch'] = line.split()[5].lstrip()

        # Get PR info from github
        req = repo.get_pull(int(entry['Pull'][1:]))
        entry['Title'] = req.title
        entry['body']  = req.body

        entry['changes'] = req.additions + req.deletions
        entry['Pull'] += f" ({req.additions} additions, {req.deletions} deletions, {req.changed_files} files changed)"

        # Detect JIRA entry
        if entry['Branch'].startswith('slaclab/ES'):
            url = 'https://jira.slac.stanford.edu/issues/{}'.format(entry['Branch'].split('/')[1])
            entry['Jira'] = f'<a href={url}>{url}</a>'
        else:
            entry['Jira'] = None

        records.append(entry)
        entry = {}

if sortByChanges:
    records = sorted(records, key=lambda v : v['changes'], reverse=True)

# Generate text
md = '### Pull Requests\n'
for entry in records:
    md += '---\n'
    md += '<table boder=0>\n'

    for i in ['Title','Author','Date','Pull','Branch','Jira']:
        if entry[i] is not None:
            md += f'<tr><td align=right><b>{i}:</b></td><td align=left>{entry[i]}</td></tr>\n'
    md += '</table>\n'

    md += '\n' + entry['body'] + '\n\n'

if out == "-":
    try:
        pyperclip.copy(md)
        print('Release notes copied to clipboard')
    except:
        print("Copy to clipboard failed, use file output instead!")

else:
    with open(out,'w') as f:
        f.write(md)
    print('Release notes written to {}'.format(out))
