.. highlight:: shell

============
Installation
============


Stable release
--------------

To install catXAS, run this command in your terminal:

.. code-block:: console

    $ pip install catxas

This is the preferred method to install catXAS, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources for catXAS can be downloaded from the `Github repo`_.

Clone the public repository:

.. code-block:: console

    $ git clone https://github.com/ahoffm02/catXAS.git
    $ cd catXAS

catXAS uses `uv`_ for environment and dependency management. Create the
environment from the lockfile with:

.. code-block:: console

    $ uv sync

Add ``--extra notebooks`` to include the Jupyter stack used by the example
notebooks. See ``CONTRIBUTING.rst`` for the full development workflow.

.. _uv: https://docs.astral.sh/uv/


.. _Github repo: https://github.com/ahoffm02/catxas
.. _tarball: https://github.com/ahoffm02/catxas/tarball/master
