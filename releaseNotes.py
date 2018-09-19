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
#
# Release steps:
#    - Merge pre-release into master
#       > git fetch
#       > git co master
#       > git merge origin/master
#       > git merge origin/pre-release
#       > git push
#    - Tag the release in master: 
#       > git tag -a vMAJOR.MINOR.0
#       > git push --tags
#    - Create release using tag on github.com, use this script to generate notes
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
import re
import argparse
import pyperclip
from getpass import getpass

parser = argparse.ArgumentParser('Release notes generator')
parser.add_argument('tag', type=str, help='reference tag or range. (i.e. v2.5.0 or v2.5.0..v2.6.0)')
parser.add_argument('--user', type=str, help='Username for github, password will be prompted')
parser.add_argument('--nosort', help='Disable sort by change counts', action="store_true")
parser.add_argument('--copy', help='Copy to clipboard', action="store_true")
args = parser.parse_args()

if '..' in args.tag:
    tags = args.tag
else:
    tags = F"{args.tag}..HEAD"

print(f"Using range: {tags}")

# Local git clone
g = git.Git('.')
g.fetch()
project = re.compile(r'slaclab/(?P<name>.*?).git').search(g.remote('get-url','origin')).group('name')

user = args.user
password = None

if user is not None:
    password = getpass("Password for github: ")

# Git server
gh = Github(user,password)
repo = gh.get_repo(f'slaclab/{project}')

loginfo = g.log(tags,'--grep','Merge pull request')

records = []
entry = {}

#print("# Pull Requests")

# Parse the log entries
for line in loginfo.splitlines():

    if line.startswith('Author:'):
        entry['Author'] = line[7:].lstrip()

    elif line.startswith('Date:'):
        entry['Date'] = line[5:].lstrip()

    elif 'Merge pull request' in line:
        entry['PR'] = line.split()[3].lstrip()
        entry['Branch'] = line.split()[5].lstrip()

        # Get PR info from github
        #print(f"{entry['Pull']}")
        req = repo.get_pull(int(entry['PR'][1:]))
        entry['Title'] = req.title
        entry['body']  = req.body

        entry['changes'] = req.additions + req.deletions
        entry['Pull'] = entry['PR'] + f" ({req.additions} additions, {req.deletions} deletions, {req.changed_files} files changed)"

        # Detect JIRA entry
        if entry['Branch'].startswith('slaclab/ES'):
            url = 'https://jira.slac.stanford.edu/issues/{}'.format(entry['Branch'].split('/')[1])
            entry['Jira'] = url
        else:
            entry['Jira'] = None

        records.append(entry)
        entry = {}

if args.nosort is False:
    records = sorted(records, key=lambda v : v['changes'], reverse=True)

# Generate text
md = '# Pull Requests\n'

for i, entry in enumerate(records):
    md += f" 1. {entry['PR']} - {entry['Title']}\n"

md += '## Pull Request Details\n'

for entry in records:

    md += f"### {entry['Title']}"

    md += '\n|||\n|---:|:---|\n'

    for i in ['Author','Date','Pull','Branch','Jira']:
        if entry[i] is not None:
            md += f'|**{i}:**|{entry[i]}|\n'

    md += '\n**Notes:**\n'
    for line in entry['body'].splitlines():
        md += '> ' + line + '\n'
    md += '\n-------\n'         
    md += '\n\n'

print(md)

if args.copy:
    try:	
        pyperclip.copy(md)	
        print('Release notes copied to clipboard')	
    except:	
        print("Copy to clipboard failed!")

