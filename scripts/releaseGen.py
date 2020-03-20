#-----------------------------------------------------------------------------
# Title      : Release notes generation
# ----------------------------------------------------------------------------
# This file is part of the SMURF software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the SMURF software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------
import os
import git                # GitPython
from github import Github # PyGithub
from collections import OrderedDict as odict
import re

ghRepo = os.environ.get('GITHUB_REPO')
token  = os.environ.get('GH_REPO_TOKEN')
newTag = os.environ.get('TRAVIS_TAG')

if ghRepo is None:
    exit("GITHUB_REPO not in environment.")

if token is None:
    exit("GH_REPO_TOKEN not in environment.")

if newTag is None:
    exit("TRAVIS_TAG not in environment.")

# Check tag to make sure it is a proper release: va.b.c
vpat = re.compile('v\d+\.\d+\.\d+')

if vpat.match(newTag) is None:
    exit("Not a release version")

# Git server
gh = Github(token)
remRepo = gh.get_repo(ghRepo)

# Find previous tag
oldTag = git.Git('.').describe('--abbrev=0','--tags',newTag + '^')

# Get logs
loginfo = git.Git('.').log(f"{oldTag}...{newTag}",'--grep','Merge pull request')

# Grouping of recors
records= odict({'Core':      odict({'Bug' : [], 'Enhancement':[]}),
                'Client':    odict({'Bug' : [], 'Enhancement':[]}),
                'Unlabled':  [] })

details = []
entry = {}

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
        req = remRepo.get_pull(int(entry['PR'][1:]))
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

        entry['Labels'] = None
        for lbl in req.get_labels():
            if entry['Labels'] is None:
                entry['Labels'] = lbl.name
            else:
                entry['Labels'] += ', ' + lbl.name

        # Add both to details list and sectioned summary list
        found = False
        if entry['Labels'] is not None:
            for section in ['Client','Core']:
                for label in ['Bug','Enhancement']:

                    if section.lower() in entry['Labels'] and label.lower() in entry['Labels']:
                        records[section][label].append(entry)
                        found = True

        if not found:
            records['Unlabled'].append(entry)

        details.append(entry)
        entry = {}

# Generate summary text
md = f'# Pull Requests Since {oldTag}\n'

# Summary list is sectioned
for section in ['Client','Core']:
    subSec = ""

    for label in ['Bug','Enhancement']:
        subLab = ""
        entries = sorted(records[section][label], key=lambda v : v['changes'], reverse=True)
        for entry in entries:
            subLab  += f" 1. {entry['PR']} - {entry['Title']}\n"

        if len(subLab) > 0:
            subSec += f"### {label}\n" + subLab

    if len(subSec) > 0:
        md += f"## {section}\n"
        md += subSec

if len(records['Unlabled']) > 0:
    md += f"### Unlabled\n"

    for entry in records['Unlabled']:
        md += f" 1. {entry['PR']} - {entry['Title']}\n"

# Detailed list
det = '# Pull Request Details\n'

# Sort records
details = sorted(details, key=lambda v : v['changes'], reverse=True)

# Generate detailed PR notes
for entry in details:
    det += f"### {entry['Title']}"
    det += '\n|||\n|---:|:---|\n'

    for i in ['Author','Date','Pull','Branch','Jira','Labels']:
        if entry[i] is not None:
            det += f'|**{i}:**|{entry[i]}|\n'

    det += '\n**Notes:**\n'
    for line in entry['body'].splitlines():
        det += '> ' + line + '\n'
    det += '\n-------\n'
    det += '\n\n'

# Include details
md += det

# Create release using tag
msg = f'Release {newTag}'
remRel = remRepo.create_git_release(tag=newTag,name=msg, message=md, draft=False)

