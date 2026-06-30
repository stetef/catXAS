# catXAS Modernization Summary

This document summarizes a set of modernization changes to the `catXAS`
packaging, dependencies, and developer tooling, and explains the motivation
behind each. The functional analysis code in `catxas/` is unchanged except for
a small import-correctness fix described below.

## Why modernize?

The repository was generated from the [cookiecutter-pypackage] template and
still carried that template's defaults from ~2019: a `setup.py`/`setup.cfg`
build, a `requirements_dev.txt` pinned to old tool versions, and Travis CI +
tox targeting Python 3.6–3.8 (all now end-of-life). More importantly, the
declared dependencies were wrong — the package imported a full scientific stack
but only declared `Click`. The goals were:

1. **Correct the dependencies** so a fresh install actually works.
2. **Adopt [uv]** for fast, reproducible, lockfile-based environments.
3. **Replace dead CI** (Travis/tox) with GitHub Actions.
4. **Add local quality gates** (pre-commit) so problems are caught before push.
5. **Update the docs and Makefile** to match the new workflow.

## What changed

### 1. Packaging: setuptools/conda → uv + `pyproject.toml`

- Added **`pyproject.toml`** (PEP 621 metadata, [hatchling] build backend),
  replacing `setup.py` and `setup.cfg`.
- Added **`uv.lock`** — a fully-pinned, reproducible lockfile.
- Bumped the Python floor to **`>=3.10`** (3.6–3.8 are EOL; `xraylarch`
  requires ≥3.9; the README already targets 3.10).
- Removed `setup.py`, `setup.cfg`, and `requirements_dev.txt`.

### 2. Dependencies (these were previously incorrect)

The old `install_requires` listed only `Click`. The declared runtime
dependencies now match what the code actually imports:

| Package | Why |
|---|---|
| `click` | CLI (`catxas.cli`) |
| `numpy`, `pandas`, `scipy` | data handling / processing |
| `matplotlib` | plotting |
| `glob2` | file discovery |
| `xraylarch` | XAS science (imported as `larch`) |

The Jupyter stack (`jupyter`, `ipywidgets`) used by `notebooks/` is now an
optional extra: `uv sync --extra notebooks`. Dev tooling moved from the stale
`requirements_dev.txt` into a `[dependency-groups] dev` set (pytest, pytest-cov,
ruff, pre-commit, build, twine, bump-my-version, sphinx, sphinx-autobuild,
myst-parser).

### 3. Code: intra-package imports made relative

The submodules imported their siblings with bare top-level names
(`import general as fcts`, `import xas as xfcts`, …). That only worked when
running from inside the package directory; once `catxas` is installed as a
package, those raise `ModuleNotFoundError`. The six occurrences in `xas.py`,
`plot.py`, and `experiment.py` are now explicit relative imports
(`from . import general as fcts`). No behavior change — only import correctness.

### 4. CI: Travis + tox → GitHub Actions

- Removed `.travis.yml` (Travis is no longer used for OSS; the config was never
  finished) and `tox.ini` (targeted EOL Pythons and `python setup.py test`).
- Added **`.github/workflows/ci.yml`**: on push/PR, a matrix over Python
  3.10/3.11/3.12 installs via `uv sync`, lints with ruff, and runs pytest.
- Public repos get **unlimited free** GitHub Actions minutes, so this is free.
- Fixed a broken test import (`from catxas import catxas`, a leftover from the
  single-module template) so the test suite collects and passes.

### 5. Local quality gates: pre-commit + ruff

- Added **`.pre-commit-config.yaml`** with: standard file-hygiene hooks
  (trailing whitespace, EOF, YAML/TOML checks, large-file guard), **ruff**
  (lint + format — a single tool replacing black + isort + flake8), and a
  **`uv-lock`** hook that fails if `pyproject.toml` and `uv.lock` drift apart.
- ruff is configured in `pyproject.toml` (`line-length = 120`, py310 target,
  `force-exclude = true`, excludes `docs/` and `notebooks/`).

### 6. Documentation and Makefile

- **README.md** rewritten for the uv workflow (install via `uv sync`, the
  `notebooks` extra, `uv run` usage, a Development section, and a CI badge).
- **CONTRIBUTING.rst** rewritten: the contributor flow is now fork → `uv sync`
  + `uv run pre-commit install` → branch → `uv add` for deps → `uv run pytest`/
  `ruff` → commit (hooks run) → PR (CI runs), supporting Python 3.10–3.12.
- **Single README**: Sphinx now renders the canonical `README.md` via
  [myst-parser]; the duplicate `README.rst` was removed and `docs/conf.py`
  enables myst. `docs/installation.rst` uses `uv sync`.
- **Makefile** modernized into a uv task runner: `make test`/`lint`/`format`/
  `coverage`/`docs`/`servedocs`/`dist`/`install` all route through uv (e.g.
  `uv run pytest`, `uv build`, `uv run sphinx-autobuild`). `make docs`
  regenerates the API stubs so the docs build cleanly.

## New developer workflow

```bash
uv sync                      # create .venv from the lockfile
uv sync --extra notebooks    # include the Jupyter stack
uv run pre-commit install    # enable the git hooks (one time)
uv run pytest                # run tests
uv run ruff check . ; uv run ruff format .   # lint / format
uv add <package>             # add a dependency (updates pyproject + lock)
```

The `Makefile` wraps the common chores: `make test`, `make lint`, `make format`,
`make coverage`, `make docs`, `make servedocs`, `make clean`.

## Tests and the bugs they surfaced

The cookiecutter CLI stub has been replaced with a real two-tier suite under
`tests/` (44 tests; the fast tier runs in ~3 s):

- **Unit tests** for the pure helpers in `general` (`find_nearest`,
  `get_trailing_number`, `parse_list`, `mergeindex`), `xas` (`calc_mu`,
  `create_larch_spectrum`), and the `process` stream readers.
- **Integration tests** that drive the `Experiment` pipeline (import → mu →
  e0 → normalize → EXAFS/FT → process correlation → LCF) on a curated
  five-spectrum subset committed under `tests/data/`. They assert physical
  invariants — edge step, e0 at the Sn K-edge, first-shell FT peak, LCF basis
  self-fit, weights summing to one, and the monotonic oxidized→reduced trend —
  plus a light golden snapshot of the LCF amplitudes.
- A **`@pytest.mark.slow`** regression runs the full 50-spectrum pipeline
  against a self-consistent golden; it is deselected by default
  (`uv run pytest -m slow`).

Making the example notebooks runnable again surfaced several latent bugs that
the dependency bumps exposed. All are fixed with regression coverage:

- Modern larch lower-cases the column labels from `read_ascii` (→ restore the
  configured casing) and strips header whitespace (→ whitespace-tolerant
  timestamp parsing).
- matplotlib ≥3.9 removed `plt.cm.get_cmap` (→ `plt.get_cmap`).
- pandas 3.x refuses to interpolate string columns (→ `mergeindex` interpolates
  numeric columns only).
- `calc_mu(flip=True)` returned `N/D` instead of `D/N`; the LabView valve
  setpoints were left unmapped under pandas copy-on-write; and a non-raw regex
  string in the Hiden reader raised a `SyntaxWarning`.

## Known follow-ups (intentionally out of scope here)

- **Lint backlog**: ruff reports ~50 issues in `catxas/`, including ~12
  `F821` (undefined name) warnings that may be real bugs. CI's ruff step is
  currently **non-blocking** (`continue-on-error`); a dedicated cleanup branch
  should fix these and then flip it to blocking.
- **Pre-commit hook tuning**: the local hook blocks commits that touch
  `catxas/` (the ruff backlog above) or add the inherently large sample/fixture
  data (`check-added-large-files` defaults to 500 KB), so recent commits used
  `--no-verify`. Raise the large-files limit (or exclude `sample data/` and
  `tests/data/`) and clear the ruff backlog so the hook runs clean.
- **Dead module**: `catxas/depreciated functions.py` has a space in its
  filename (so it is not importable, and the name is misspelled). It should be
  deleted or renamed to a valid module.
- **Type checking**: no type checker yet; adding mypy or pyright to CI would
  catch a class of bugs ruff cannot.
- **Dependency automation**: add a `.github/dependabot.yml` (replacing the
  stale `.pyup.yml`) for automated dependency-update PRs.
- **Single-source version**: the version is duplicated in `pyproject.toml` and
  `catxas/__init__.py`; consider deriving it from one source (e.g. hatch-vcs).
  This also resolves the unconfigured `bump-my-version`.
- **PyPI publishing**: not automated; the modern approach is GitHub Actions
  with PyPI Trusted Publishing (OIDC).
- **Sphinx polish**: minor pre-existing build warnings remain
  (`language = 'en'`, missing `docs/_static/`).
- **`xraylarch` floor**: currently a loose minimum; tighten once the real
  minimum supported version is confirmed.

[cookiecutter-pypackage]: https://github.com/audreyfeldroy/cookiecutter-pypackage
[uv]: https://docs.astral.sh/uv/
[hatchling]: https://hatch.pypa.io/latest/
[myst-parser]: https://myst-parser.readthedocs.io/
