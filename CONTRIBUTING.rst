.. highlight:: shell

============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/ahoffm02/catXAS/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~~~

catXAS could always use more documentation, whether as part of the
official catXAS docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at
https://github.com/ahoffm02/catXAS/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? catXAS uses `uv <https://docs.astral.sh/uv/>`_ to manage
the environment and dependencies. Here's how to set up ``catxas`` for local
development.

1. Install uv if you don't have it::

    $ curl -LsSf https://astral.sh/uv/install.sh | sh

2. Fork the ``catXAS`` repo on GitHub, then clone your fork locally::

    $ git clone git@github.com:your_name_here/catXAS.git
    $ cd catXAS

3. Create the environment from the lockfile and enable the git hooks::

    $ uv sync
    $ uv run pre-commit install

   ``uv sync`` creates a ``.venv/`` with the exact locked dependencies. Add
   ``--extra notebooks`` if you need the Jupyter stack.

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. If your change needs a new dependency, add it through uv so that both
   ``pyproject.toml`` and ``uv.lock`` stay in sync::

    $ uv add <package>          # runtime dependency
    $ uv add --dev <package>    # development-only dependency

6. When you're done, check that lint and tests pass::

    $ uv run ruff check .
    $ uv run ruff format .
    $ uv run pytest

   These also run automatically on commit via pre-commit. CI runs the same
   checks across Python 3.10, 3.11, and 3.12.

7. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

   The pre-commit hooks run on commit. If a hook reformats a file or fails on a
   pre-existing lint issue you didn't introduce, re-stage the fixes and commit
   again; use ``git commit --no-verify`` only as a last resort.

8. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests for new functionality.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the README.
3. The pull request should pass CI for all supported Python versions
   (3.10, 3.11, 3.12). The GitHub Actions workflow runs automatically on every
   pull request.

Tips
----

To run a subset of tests::

    $ uv run pytest tests/test_catxas.py
    $ uv run pytest -k <expression>

Deploying
---------

A reminder for the maintainers on how to cut a release.
Make sure all your changes are committed (including an entry in HISTORY.rst),
then build the distribution artifacts::

    $ uv build

This produces a source distribution and a wheel in ``dist/``. Publishing to
PyPI is not yet automated; the recommended modern approach is GitHub Actions
with PyPI Trusted Publishing (OIDC), which is a planned follow-up.
