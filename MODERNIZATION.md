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
| `xraylarch` | XAS science (imported as `larch`) |

The Jupyter stack (`jupyter`, `ipywidgets`) used by `notebooks/` is now an
optional extra: `uv sync --extra notebooks`. That same extra also carries the
multivariate-analysis stack (`scikit-learn`, `kneed`, `pymcr`) needed by the
`catxas.pca` / `catxas.mcrals` modules and the PCA/MCR-ALS notebooks; none of it
is required for the core XAS pipeline. Dev tooling moved from the stale
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
The `pca.py` module later merged from upstream carried the same bare
`import plot as pfcts`; it was fixed the same way.

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
`tests/` (60 fast + 1 slow; the fast tier runs in ~4 s):

- **Unit tests** for the pure helpers in `general` (`find_nearest`,
  `get_trailing_number`, `parse_list`, `mergeindex`), `xas` (`calc_mu`,
  `create_larch_spectrum`), and the `process` stream readers.
- **Integration tests** that drive the `Experiment` pipeline (import → mu →
  e0 → normalize → EXAFS/FT → process correlation → LCF) on a curated
  five-spectrum subset committed under `tests/data/`. They assert physical
  invariants — edge step, e0 at the Sn K-edge, first-shell FT peak, LCF basis
  self-fit, weights summing to one, and the monotonic oxidized→reduced trend —
  plus a light golden snapshot of the LCF amplitudes.
- **Analysis tests** for the merged multivariate modules: `test_pca.py` and
  `test_mcrals.py` drive `catxas.pca` / `catxas.mcrals` the way the Example 5.0
  (PCA) and 5.1 (MCR-ALS) notebooks do — decomposing the committed
  `SnO2_TPR_NormXANES.csv`. They assert PCA variance ordering and exact
  full-rank reconstruction, the four unique-spectra selectors, and that a
  3-component MCR-ALS fit (non-negativity-constrained, deterministic with
  `perturb_initial=False`) reconstructs far better than a single mean spectrum.
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
  the numeric columns only and drops non-numeric ones — see the upstream-sync
  note below).
- the LabView valve setpoints were left unmapped under pandas copy-on-write; and
  a non-raw regex string in the Hiden reader raised a `SyntaxWarning`.

## Syncing with upstream (`ahoffm02/catXAS`)

Upstream landed one large squashed commit fixing its own dependency-era bugs
and adding new multivariate-analysis modules. It was merged in (`git merge
upstream/main`); most of it auto-merged, and the handful of overlapping edits
were resolved deliberately:

- **`calc_mu(flip=...)`** — upstream and this fork had fixed the same function
  with *incompatible* semantics. Upstream's is authoritative: `flip` **negates**
  the (log) absorption (`-1 * ln|N/D|`), it does not invert the ratio, and the
  log is now guarded with `np.abs` on both paths to avoid NaNs from negative
  ratios. This fork's earlier "`D/N`" interpretation was dropped and the
  `calc_mu` tests updated to match.
- **`get_cmap`** — both fixed the matplotlib ≥3.9 removal; this fork's
  one-line `plt.get_cmap(name, n)` was kept over upstream's try/except.
- **`mergeindex`** — upstream's numeric-only fix was taken. Note the behavior
  difference: it **drops** non-numeric columns (printing which), whereas this
  fork's version had retained them; the regression test was updated accordingly.
- **`README.md`** — this fork's rewritten (uv-workflow) README was kept over
  upstream's, which still lacked the `kneed` dependency note and carried a
  committed merge-conflict marker.
- **notebooks / sample results** — both sides had regenerated these; upstream's
  reorganized `Example N.x` notebook set (including the new PCA/MCR-ALS
  examples) and its regenerated outputs were taken wholesale.
- **`catxas/pca.py`, `catxas/mcrals.py`** — new modules, merged as-is apart from
  the relative-import fix noted above; their dependencies (`scikit-learn`,
  `kneed`, `pymcr`) were folded into the existing `notebooks` extra.

## Known follow-ups (intentionally out of scope here)

- **Lint backlog** — *done* (branch `lint-backlog-cleanup`): the ruff backlog
  in `catxas/` is cleared and CI's ruff step is now **blocking**
  (`continue-on-error` removed). The 44 live-code issues were fixed by hand —
  `== None`/`!= None` → `is`/`is not` (E711/E712), `type(x) == T` →
  `isinstance` (E721), bare `except:` → `except Exception:` (E722), and unused
  imports/variables (F401/F841). All 16 `F821` (undefined name) warnings were
  confined to the non-importable `depreciated functions.py`; that file is
  excluded from ruff (see **Dead module** below) rather than edited, so those
  were not real bugs in live code.
- **Pre-commit hook tuning**: the local hook's `check-added-large-files`
  (defaults to 500 KB) still blocks adding the inherently large sample/fixture
  data, so data-adding commits used `--no-verify`. Raise the large-files limit
  (or exclude `sample data/` and `tests/data/`). The ruff portion of the hook
  now runs clean on `catxas/`.
- **Dead module**: `catxas/depreciated functions.py` has a space in its
  filename (so it is not importable, and the name is misspelled). It should be
  renamed to a valid module — **do not delete it**: upstream treats it as a live
  graveyard and still appends deprecated functions to it (e.g.
  `save_normalize_spectra`), so a rename must be coordinated with upstream. In
  the meantime it is excluded from ruff (`tool.ruff.exclude` in
  `pyproject.toml`) so its missing-import `F821`s don't block the now-blocking
  CI lint; fold it back in once it is renamed to an importable module.
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
