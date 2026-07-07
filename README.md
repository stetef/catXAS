# catXAS

[![CI](https://github.com/stetef/catXAS/actions/workflows/ci.yml/badge.svg)](https://github.com/stetef/catXAS/actions/workflows/ci.yml)

A Python-based XAS analysis workflow that also correlates process data streams
to the XAS spectra. Built for in-situ catalysis XAS data collected via CXAS at
SSRL.

## Requirements

- Python **3.10+**
- [uv](https://docs.astral.sh/uv/) for environment and dependency management

Install uv (once, if you don't have it):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation

Clone the repository and let uv create the environment from the lockfile:

```bash
git clone https://github.com/ahoffm02/catXAS.git
cd catXAS
uv sync
```

`uv sync` creates a `.venv/` with the exact, locked versions of all
dependencies (numpy, pandas, scipy, matplotlib, xraylarch, etc.). To include
the Jupyter stack and the multivariate-analysis packages (scikit-learn, kneed,
pymcr) used by the notebooks in `notebooks/`:

```bash
uv sync --extra notebooks
```

> **Prefer conda?** xraylarch also installs cleanly under conda. You can create
> a `python=3.10` environment and `pip install .` into it, but the uv workflow
> above is the supported path for development.

## Usage

Run anything inside the project environment with `uv run` (no manual
activation needed):

```bash
uv run python -c "import catxas; print(catxas.__version__)"
uv run catxas            # the CLI entry point
```

In your own code:

```python
from catxas import xas, process, plot, experiment
```

The `notebooks/` directory contains example end-to-end workflows.

## Development

```bash
uv sync                      # set up the environment
uv run pre-commit install    # enable git hooks (one time)

uv run pytest                # run the test suite
uv run ruff check .          # lint
uv run ruff format .         # auto-format

uv add <package>             # add a runtime dependency (updates pyproject + lock)
uv add --dev <package>       # add a dev-only dependency
```

Linting/formatting (ruff) and dependency-lock checks run automatically on every
commit via pre-commit, and the same checks plus tests run in CI across Python
3.10–3.12. See [CONTRIBUTING.rst](CONTRIBUTING.rst) for the full contributor
workflow and [MODERNIZATION.md](MODERNIZATION.md) for the rationale behind the
current tooling.

## License

GNU General Public License v3. See [LICENSE](LICENSE).
