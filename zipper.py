#!/bin/python3

import itertools
import git

def build_remote_history(remote):
    pass


if __name__ == "__main__":
    import argparse as ap
    import sys

    pp = ap.ArgumentParser(description='Combine remote repo history based on svn metadata')

    pp.add_argument(
        'remotes',
        metavar='N',
        type=str,
        nargs='+',
        help='list of repos to combine'
    )

    args = pp.parse_args()

    remotes = args.remotes

    ####
    print("Detected specified remotes: ")
    for remote in remotes:
        print("    {}".format(remote))
    ####

    print("Choosing repo at '.'")
    repo = git.Repo('.')

    filtered_remotes = [
        remote.split('/') for remote in remotes if hasattr(repo.remotes, remote.split('/')[0]) and repo.remotes[remote.split('/')[0]].exists()
    ]

    ####
    print("Detected extant remotes: ")
    for remote in filtered_remotes:
        print("    {}".format(remote))
    ####

    # build all commits for remotes
    remote_commits = {}
    for remote, branch in filtered_remotes:
        repo.remotes[remote].fetch(branch)
        remote_commits[remote] = repo.iter_commits('{}/{}'.format(remote, branch))

    # now begin to construct the svn history:
    # svn-hist = { svnrev : [(git commit hash, git commit message)...] }
    svn_history = { }
    for remote in remote_commits:
        commits = remote_commits[remote]
        for commit in commits:
            tokens = commit.message.split()

            # Use itertools.dropwhile to filter out the parts of the commit
            # message we don't need. The token immediately following
            # 'git-svn-id:'
            def is_svn_found(token):
                if token == 'git-svn-id:':
                    is_svn_found.found_svn = True
                    return False
                else:
                    return is_svn_found.found_svn
            is_svn_found.found_svn = False

            for token in itertools.dropwhile(lambda token : not is_svn_found(token), tokens):
                svn_rev = int(token.split('@')[-1].rstrip())
                if svn_rev in svn_history:
                    svn_history[svn_rev].append(commit)
                else:
                    svn_history[svn_rev] = [commit]
                break

    # Now that we've accumulated all the commits we can pull them in:
    # Assume the svn rev order is a sensible commit order
    applied_commits = []
    for rev in sorted(svn_history):
        commits = svn_history[rev]
        for commit in commits:
            # handle merge commits -- for now just assume we only need to apply
            # the unapplied parents directly and that *all* commits are zipped
            # up and *all* relevant branches are specified.
            if commit in applied_commits:
                continue

            print("Picking commit: {}".format(commit))
            if len(commit.parents) > 1:
                repo.git.execute(['git', 'cherry-pick', '--strategy=recursive', '-X', 'theirs', '-m', '1', '-n', commit.hexsha])
            else:
                repo.git.execute(['git', 'cherry-pick', '--strategy=recursive', '-X', 'theirs', '-n', commit.hexsha])
                applied_commits.append(commit)


        # We can just reuse the commit message of the first commit since they
        # all ought to be same since they came from the same svn revision
        repo.git.execute(['git', 'commit', '--allow-empty', '-C', commits[0].hexsha])

    sys.exit(0)
