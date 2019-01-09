#!/usr/bin/env python

import imp
import re
import sys
sys.dont_write_bytecode = True # .pyc generation -> ugly 'git-repo-filterc' files

# python makes importing files with dashes hard, sorry.  Renaming would
# allow us to simplify this to "import git_repo_filter"; however,
# since git style commands are dashed and git-repo-filter is used more
# as a tool than a library, renaming is not an option.
with open("../../git-repo-filter") as f:
  repo_filter = imp.load_module('repo_filter', f, "git-repo-filter", ('.py', 'U', 1))

class InterleaveRepositories:
  def __init__(self, repo1, repo2, output_dir):
    self.repo1 = repo1
    self.repo2 = repo2
    self.output_dir = output_dir

    self.commit_map = {}
    self.last_commit = None

  def skip_reset(self, reset):
    reset.skip()

  def hold_commit(self, commit):
    commit.skip(new_id = commit.id)
    letter = re.match('Commit (.)', commit.message).group(1)
    self.commit_map[letter] = commit

  def weave_commit(self, commit):
    letter = re.match('Commit (.)', commit.message).group(1)
    prev_letter = chr(ord(letter)-1)

    # Splice in any extra commits needed
    if prev_letter in self.commit_map:
      new_commit = self.commit_map[prev_letter]
      new_commit.from_commit = self.last_commit
      new_commit.dump(self.out._output)
      commit.from_commit = new_commit.id

    # Dump our commit now
    commit.dump(self.out._output)

    # Make sure that commits that depended on new_commit.id will now depend
    # on commit.id
    if prev_letter in self.commit_map:
      self.last_commit = commit.id
      repo_filter.record_id_rename(new_commit.id, commit.id)

  def run(self):
    args = repo_filter.FilteringOptions.parse_args(['--debug', '--target', self.output_dir])
    out = repo_filter.RepoFilter(args)
    out.importer_only()
    self.out = out

    i1args = repo_filter.FilteringOptions.parse_args(['--debug', '--source', self.repo1])
    i1 = repo_filter.RepoFilter(i1args,
                                reset_callback  = lambda r: self.skip_reset(r),
                                commit_callback = lambda c: self.hold_commit(c))
    i1.set_output(out)
    i1.run()

    i2args = repo_filter.FilteringOptions.parse_args(['--debug', '--source', self.repo2])
    i2 = repo_filter.RepoFilter(i2args,
                                commit_callback = lambda c: self.weave_commit(c))
    i2.set_output(out)
    i2.run()
    out.run()

splicer = InterleaveRepositories(sys.argv[1], sys.argv[2], sys.argv[3])
splicer.run()
