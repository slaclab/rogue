#!/usr/bin/env python3

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
        out.append("\n" + req.body)

txt = ''
for l in out:
    print(l)
    txt += (l + '\n')

pyperclip.copy(txt)
print('')
print('---------------------------------')
print('Release notes copied to clipboard')
print('---------------------------------')

