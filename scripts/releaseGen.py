#-----------------------------------------------------------------------------
# Title      : Release notes generation
# ----------------------------------------------------------------------------
# Description:
# Generate release notes for pull requests relative to a tag.
# Usage: releaseNotes.py tag (i.e. releaseNotes.py v2.5.0
#
# Must be run within an up to date git clone with the proper branch checked out.
#
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
import git                # GitPython
from github import Github # PyGithub
import re

newTag = input("Enter new tag: ")
oldTag = input("Enter old tag: ")

# Attempt to find github token in environment
token = os.environ.get('GITHUB_TOKEN')

if token is None:
    print("\nGITHUB_TOKEN not found in user's environment....")
    token  = input("Enter github token: ")
else:
    print("Using github token from user's environment.")

tagRange = tags = F"{oldTag}..HEAD"

exit(0)

# Local git cone
locRepo = git.Repo('.')

url = locRepo.remote().url
if not url.endswith('.git'): url += '.git'

# Get the git repo's name (assumption that exists in the github.com/slaclab organization)
project = re.compile(r'slaclab/(?P<name>.*?)(?P<ext>\.git?)').search(url).group('name')

# Prevent "dirty" git clone (uncommitted code) from pushing tags
if locRepo.is_dirty():
    raise(Exception("Cannot create tag! Git repo is dirty!"))

# Git server
gh = Github(token)
remRepo = gh.get_repo(f'slaclab/{project}')

loginfo = git.Git('.').log(tags,'--grep','Merge pull request')

records = []
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
        #print(f"{entry['Pull']}")
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

        records.append(entry)
        entry = {}

# Sort the records
records = sorted(records, key=lambda v : v['changes'], reverse=True)

# Generate text
md = f'# Pull Requests Since {oldTag}\n'

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

print(f"\nCreating and pushing tag {newTag} .... ")
msg = f'Rogue Release {newTag}'

ghTag = locRepo.create_tag(path=newTag, message=msg)
locRepo.remotes.origin.push(ghTag)

remRel = remRepo.create_git_release(tag=newTag,name=msg, message=md, draft=False)

print(f"\nDone")

