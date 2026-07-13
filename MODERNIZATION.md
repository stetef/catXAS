# catXAS Modernization Summary

This document summarizes a set of modernization changes to the `catXAS`
packaging, dependencies, and developer tooling, and explains the motivation
behind each. The functional analysis code in `catxas/` is unchanged except for
a small import-correctness fix and a behavior-preserving lint cleanup, both
described below.

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

  This describes the hook set as first added; the content-rewriting hooks were
  later pared back so commits run clean against the legacy code — see
  [§7](#7-post-modernization-cleanup-lint-versioning-pre-commit).

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

### 7. Post-modernization cleanup (lint, versioning, pre-commit)

Three items first tracked as follow-ups have since been completed, each on its
own branch merged to `main`:

- **Lint backlog cleared; CI lint made blocking** (`lint-backlog-cleanup`).
  The ruff backlog in `catxas/` is fixed and the CI ruff step is now **blocking**
  (`continue-on-error` removed). The 44 live-code issues were fixed by hand —
  `== None`/`!= None` → `is`/`is not` (E711/E712), `type(x) == T` → `isinstance`
  (E721), bare `except:` → `except Exception:` (E722), and unused imports/
  variables (F401/F841). All 16 `F821` (undefined name) warnings were confined
  to the non-importable `depreciated functions.py` (see the **Dead module**
  follow-up); that file is excluded from ruff (`tool.ruff.exclude` in
  `pyproject.toml`) rather than edited, so none were real bugs in live code.
- **Version single-sourced** (`single-source-version`). The version literal now
  lives only in `catxas/__init__.py`; `pyproject.toml` declares
  `dynamic = ["version"]` and `[tool.hatch.version]` reads it from that module,
  so there is one source of truth. (`bump-my-version` is left unconfigured to
  avoid re-introducing a second literal — bump `__init__.py` by hand, or wire up
  hatch-vcs/git tags later if tooled bumps become worth it.)
- **Pre-commit tuned so commits run clean** (`precommit-tuning`).
  `uv run pre-commit run --all-files` now passes with no `--no-verify`.
  `check-added-large-files` keeps the 500 KB guard for code but excludes the
  dirs that legitimately hold large data / fixtures / notebook outputs
  (`sample data/`, `sample results/`, `tests/data/`, `notebooks/`). The
  content-*rewriting* hooks (`ruff-format`, `trailing-whitespace`,
  `end-of-file-fixer`, `mixed-line-ending`) were dropped: the legacy code and
  committed instrument data carry trailing whitespace on most lines, so those
  hooks would have rewritten ~2400 lines on first touch and produced recurring,
  invisible-to-eyeball whitespace conflicts on every `git merge upstream/main`
  (ruff's rule set doesn't enforce trailing whitespace anyway). Only validating
  hooks remain. If whitespace enforcement is ever wanted, do a one-off cleanup
  right after an upstream sync, not via a hook.

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

## Performance: eliminating the O(N²) import/interpolation cost (proposed)

Profiling the per-file data path (prompted by comparing against a batch
reimplementation of the same processing) surfaced that importing a directory of
spectra scales **quadratically** in the number of files, not linearly. The cost
is pure bookkeeping — sorting, dict-rebuilding, and DataFrame accumulation — not
XAS physics, so it can be removed with small, behavior-preserving changes. The
fixes below are **not yet implemented**; they are recorded here as a scoped
follow-up.

**Measurement context.** The O(N) batch reimplementation processes a 1.2 GB /
590-scan dataset in **~57 s single-threaded**; the corresponding catXAS-style
per-scan pipeline on comparable data is reported to take on the order of hours at
~5 GB. Most of that gap is the two structural issues below (the rest is the
per-scan Larch granularity noted at the end). The speed-up figures are
**analytical estimates** from the complexity change (O(N²) → O(N)), not a
measured catXAS before/after — they should be confirmed with a profiling run.

### 1. Hoist collection-finalization out of the per-file import loop (largest win)

`import_spectrum` (singular, one file) does *whole-collection* finalization on
**every** call — it re-sorts the entire summary, rebuilds the full
`self.spectra` dict, and recomputes elapsed-time (TOS) for every file loaded so
far ([`experiment.py:519-535`](catxas/experiment.py#L519-L535)). Because
`import_spectra` (plural) calls it once per file, importing N files does that
O(N) finalization N times → **O(N²)**. This is the dominant term.

*Fix:* add a `finalize=True` flag to `import_spectrum`; have the batch loop pass
`finalize=False` and call the finalization block **once** after the loop.
Standalone `import_spectrum()` calls still finalize by default, so no external
behavior changes.

```python
def import_spectrum(self, ..., finalize=True):
    ...
    self.summary['XAS Spectra Files'] = pd.concat(
        [self.summary['XAS Spectra Files'], temp_df], axis=0, ignore_index=False)
    self.spectra[fname]['Time'] = time
    if finalize:
        self._finalize_spectra(time_stamp)   # sort / rebuild dict / TOS, moved here

def import_spectra(self, ...):
    for file in files:
        self.import_spectrum(..., finalize=False)
    self._finalize_spectra(time_stamp=True)   # once, not per file
```

*Estimated speed-up:* the import phase drops from O(N²) to O(N). The relative
win grows with dataset size — negligible at tens of files, but roughly **N/2×**
on the finalization work at N files (e.g. ~hundreds-fold fewer sort/rebuild
passes on a 1000-scan set), turning an import phase measured in minutes into one
measured in seconds. A further micro-optimization — accumulating rows in a
Python list and building the summary DataFrame once at finalize instead of
per-file `pd.concat` at [`experiment.py:514`](catxas/experiment.py#L514) — is
optional and captures a smaller remaining slice.

### 2. One `pd.concat` instead of N in the interpolation loops

`interpolate_spectra` ([`experiment.py:1414`](catxas/experiment.py#L1414)) and
`interpolate_spectra_E` ([`experiment.py:1475`](catxas/experiment.py#L1475))
grow `results_df` by `pd.concat`-ing one interpolated column per scan inside the
loop — each concat re-copies the whole accumulating frame, so the loop is
**O(N²)** in the column count. Every column targets the same `results_df.index`
grid, so they can be collected and concatenated once:

```python
cols = []
for key in self.spectra.keys():
    ...
    cols.append(fcts.interp_df(temp_df, results_df.index))
results_df = pd.concat([results_df] + cols, axis=1, join="inner")   # single concat
```

The interpolation math (`np.interp`) is unchanged; only the accumulation is
fixed. *Estimated speed-up:* O(N²) → O(N) on the interpolation assembly —
similar N-dependent scaling to Fix 1, material once there are many scans.

### 3. Vectorize the TOS computation

Inside the finalization, the elapsed-time loop
([`experiment.py:526-530`](catxas/experiment.py#L526-L530)) is one NumPy
expression:

```python
idx = self.summary['XAS Spectra Files'].index.values
self.summary['XAS Spectra Files']['TOS [s]'] = (idx - idx[0]) / np.timedelta64(1, 's')
```

Once Fix 1 makes this run only once (not per file), it is already O(N) overall;
vectorizing is a free tidy-up rather than an asymptotic change.

### Not addressed by the above (architectural, linear cost)

catXAS creates one Larch group and runs `autobk`/`pre_edge`/`xftf` **per
single-scan file** ([`experiment.py:1693`](catxas/experiment.py#L1693) and
neighbors). That cost is already linear in the number of scans, so the fixes
above do not touch it — it is the floor the import phase drops toward. Reducing
it further is a larger effort: either parallelize across files with a process
pool, or move to a vectorized many-scans-per-file μ-matrix model (a core
data-model change, out of scope for a bookkeeping fix). Both are noted only for
context; neither is proposed here.

## Remaining follow-ups (intentionally out of scope here)

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
