# Contributing to F-UJI

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs at <https://github.com/pangaea-data-publisher/fuji/issues>.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with [bug][bug-issues] and [help wanted][help-wanted-issues] is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with [enhancement][feature-issues] and [help wanted][help-wanted-issues] is open to whoever wants to implement it.

### Write Documentation

F-UJI could always use more documentation, whether as part of the
official F-UJI docs, in docstrings, or even on the web in blog posts,
articles, and such.

### Submit Feedback

The best way to send feedback is to file an issue at <https://github.com/pangaea-data-publisher/fuji/issues>.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome.

## Get Started!

Ready to contribute?

You need Python 3.12+ and [hatch](https://github.com/pypa/hatch). You can install it globally with [pipx](https://github.com/pypa/pipx):

```console
$ pipx install hatch
```

or locally with (this will install it in the local virtual environment):

```console
$ pip install hatch
```

Here's how to set up F-UJI for local development.

1. Fork the F-UJI repository on GitHub.
2. Clone your fork locally:
    ```console
    $ git clone git@github.com:username/fuji.git
    ```
3. Install your local copy into a virtualenv. Assuming you have virtualenvwrapper installed, this is how you set up your fork for local development:
    ```console
    $ cd fuji
    $ hatch shell
    ```
4. Create a branch for local development:
    ```console
    $ git checkout -b name-of-your-bugfix-or-feature
    ```
   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass pre-commit and the
   tests:
    ```console
    $ hatch run lint
    $ hatch test
    ```

6. Commit your changes and push your branch to GitHub:
    ```console
    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature
    ```

7. Submit a pull request through the GitHub website.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring.
3. The pull request should work for Python >= 3.12. Check
   <https://github.com/pangaea-data-publisher/fuji/pulls>
   and make sure that all the tests pass.

## Tips

To run a subset of tests:

```console
$ hatch test tests/api
$ hatch test -m smoke
```

---

*This contributor guide is adapted from [cookiecutter-pypackage (BSD 3-Clause License)](https://github.com/audreyfeldroy/cookiecutter-pypackage/blob/master/%7B%7Bcookiecutter.project_slug%7D%7D/CONTRIBUTING.rst).*

<!-- Markdown links -->
[bug-issues]: https://github.com/pangaea-data-publisher/fuji/issues?q=is%3Aopen+is%3Aissue+label%3Abug
[feature-issues]: https://github.com/pangaea-data-publisher/fuji/issues?q=is%3Aopen+is%3Aissue+label%3Aenhancement
[help-wanted-issues]: https://github.com/pangaea-data-publisher/fuji/issues?q=is%3Aopen+is%3Aissue+label%3A%22help+wanted%22
