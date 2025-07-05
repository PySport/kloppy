# Contributing to kloppy

This document lays out guidelines and advice for contributing to kloppy. If
you're thinking of contributing, please start by reading this document and
getting a feel for how contributing to this project works. The guide is split
into sections based on the type of contribution you're thinking of making.


## Bug reports

We use [GitHub issues][issue-tracker] to track bugs. Before creating a new bug
report, please check that your bug has not already been reported, and that
your bug exists on the latest version of kloppy. Include as many details as
possible in your bug report. Ideally, include a minimal code example on
a public dataset that fails. This information will help the maintainers
resolve the issue faster.

## Feature requests

We use [GitHub issues][issue-tracker] to track feature requests. You can
suggest a new feature by opening an issue. Please describe the behavior you
want and why, and provide examples of how kloppy would be used if your feature
were added.

## Code contributions

Code contributions to kloppy should follow a forking workflow further
described in this section whereby contributors fork the repository, make
changes and then create a pull request.

!!! info "What is a forking workflow?"

    If you are new to contributing to projects through forking on GitHub, take
    a look at the GitHub [documentation for contributing to
    projects][gh-quickstart]. GitHub provides a quick tutorial using a test
    repository that may help you become more familiar with forking
    a repository, cloning a fork, creating a feature branch, pushing changes
    and making pull requests.

### Create or find an issue to contribute to

When contributing to this repository, please first discuss any substantial
change you wish to make with the repository owners via [GitHub
issues][issue-tracker]. This is to ensure that there is nobody already working
on the same issue and to ensure your time as a contributor isn't wasted!

If you are brand new to kloppy or don't really know what to work on, we
recommend searching the [GitHub "issues" tab][issue-tracker] to find issues
that interest you. Unassigned issues labeled [`documentation`][documentation-issues]
and [`good first issue`][getting-started-issues] are typically good for newer
contributors.

Once you've found an interesting issue, it's a good idea to assign the issue
to yourself, so nobody else duplicates the work on it. On the GitHub issue,
leave a comment saying that you would like to take it. One of the maintainers
will then assign it to you.

If for whatever reason you are not able to continue working with the issue,
please unassign it, so other people know it's available again. You can check
the list of assigned issues, since people may not be working on them anymore.
If you want to work on one that is assigned, feel free to kindly ask the
current assignee if you can take it.

### Create a fork of kloppy

You will need your own copy of kloppy (aka fork) to work on the code. Go to
the [kloppy project page](https://github.com/PySport/kloppy) and hit the
`Fork` button. Please uncheck the box to copy only the main branch before
selecting `Create Fork`. You will want to clone your fork to your machine:

```bash
git clone https://github.com/your-user-name/kloppy.git kloppy-dev
cd kloppy-dev
git remote add upstream https://github.com/PySport/kloppy.git
git fetch upstream
```

This creates the directory `kloppy-dev` and connects your repository to the
upstream (main project) kloppy repository.

### Create a feature branch

Your local `master` branch should always reflect the current state of the
kloppy repository. First ensure it’s up-to-date with the main kloppy
repository.

```bash
git checkout master
git pull upstream master --ff-only
```

Then, create a feature branch for making your changes. For example:

```bash
git checkout -b feat/shiny-new-feature
```

This changes your working branch from `master` to the `feat/shiny-new-feature`
branch. Keep any changes in this branch specific to one bug or feature, so it
is clear what the branch brings to kloppy. You can have many feature branches
and switch in between them using the `git checkout` command.

### Make your changes

Before modifying any code, ensure you follow the guidelines to [set up an
appropriate development environment](./dev-environment.md).

Then, make your code changes and commit to your local repository with an
explanatory commit message.

```bash
git add path/to/file-to-be-added-or-changed.py
git commit -m "your commit message goes here"
```

### Update your feature branch

It is important that updates in the kloppy master branch are reflected in your
feature branch. To update your feature branch with changes in the kloppy
master branch, run:

```bash
git checkout feat/shiny-new-feature
git fetch upstream
git merge upstream/main
```

If there are no conflicts (or they could be fixed automatically), a file with
a default commit message will open, and you can simply save and quit this
file.

If there are merge conflicts, you need to [solve those conflicts][gh-fix-conflicts].

### Push your changes

When you want your changes to appear publicly on your GitHub page, push your
forked feature branch’s commits:

```bash
git push origin shiny-new-feature
```

Here `origin` is the default name given to your remote repository on GitHub.
If you added the upstream repository as described above you will see something
like

```text
origin  git@github.com:yourname/kloppy.git (fetch)
origin  git@github.com:yourname/kloppy.git (push)
upstream        git://github.com/PySport/kloppy.git (fetch)
upstream        git://github.com/PySport/kloppy.git (push)
```

Now your code is on GitHub, but it is not yet a part of the kloppy project.
For that to happen, a pull request needs to be submitted on GitHub.

### Submit a pull request

If everything looks good, you are ready to [make a pull request (PR)][gh-create-pr].

In the PR template, please describe the change, including the
motivation/context, and any other relevant information. Please note if the PR
is a breaking change or if it is related to an open GitHub issue.

A core maintainer will review your PR and provide feedback on any changes it
requires to be approved. To improve the chances of your pull request being
reviewed, you should:

- **Reference an open issue** for non-trivial changes to clarify the purpose of the PR.
- **Ensure you have appropriate tests.** These should be the first part of any PR.
- **Keep your pull requests as simple as possible.** Larger PRs take longer to review.
- **Ensure that CI is in a green state.** Reviewers may not even look otherwise.
- **Keep updating your pull request**, either by request or every few days.

Once approved and all the tests pass, the reviewer will click the "Squash and
merge" button in GitHub 🥳.

Your PR is now merged into kloppy! We'll shout out your contribution in the
release notes.

## Documentation contributions

Contributing to the documentation benefits everyone who uses kloppy. If
something in the docs doesn't make sense to you, updating the relevant section
after you figure it out is a great way to ensure it will help the next person.

Contributing to the documentation is quick and straightforward, as you do not
have to set up a development environment to make small changes. Instead, you
can [edit files directly on GitHub][gh-editing-files] and suggest changes.

To make more extensive changes to the docs, it is recommended to follow the
steps for [code contributions](#code-contributions) outlined above.

### About the kloppy documentation

The documentation files live in the `docs/` directory of the codebase. They're
written in [Markdown](https://daringfireball.net/projects/markdown/), and use
[MkDocs](https://www.mkdocs.org/) to generate the full suite of documentation.
The [Markdown Guide](https://www.markdownguide.org/) provides an excellent
tutorial on how to write Markdown. To perform more complex changes to the
documentation, it is recommended to review the
[MkDocs](https://www.mkdocs.org/user-guide/writing-your-docs) documentation as
well.

### Previewing changes

Once, the pull request is submitted, [Netlify](https://www.netlify.com/) will
automatically build the documentation. To view the built site:

1. Wait for the "Pages changed" check to complete.
1. Click "..." → "View details" next to it.
1. Click on "view" next to one of the changed pages to preview them.


[issue-tracker]: https://github.com/PySport/kloppy/issues "GitHub issues"
[documentation-issues]: https://github.com/PySport/kloppy/issues?q=is%3Aopen+sort%3Aupdated-desc+label%3Adocumentation+no%3Aassignee
[getting-started-issues]: https://github.com/PySport/kloppy/issues?q=is%3Aopen+sort%3Aupdated-desc+label%3A%22good+first+issue%22+no%3Aassignee

[gh-quickstart]: https://docs.github.com/en/get-started/quickstart/contributing-to-projects "Contributing to a GitHub project"
[gh-fix-conflicts]: https://help.github.com/articles/resolving-a-merge-conflict-using-the-command-line/ "Fixing merge conflicts"
[gh-create-pr]: https://help.github.com/en/articles/creating-a-pull-request-from-a-fork
[gh-editing-files]: https://docs.github.com/en/repositories/working-with-files/managing-files/editing-files "Editing a file on GitHub"
