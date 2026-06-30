.PHONY: clean clean-test clean-pyc clean-build clean-docs docs servedocs lint format test coverage dist release install help
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := uv run python -c "$$BROWSER_PYSCRIPT"

help:
	@uv run python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test clean-docs ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache
	rm -fr .ruff_cache

clean-docs: ## remove generated docs
	rm -f docs/catxas.rst docs/modules.rst
	rm -fr docs/_build

lint: ## check code with ruff
	uv run ruff check .

format: ## auto-format code with ruff
	uv run ruff format .

test: ## run tests with pytest
	uv run pytest

coverage: ## measure code coverage and open the HTML report
	uv run pytest --cov=catxas --cov-report=term-missing --cov-report=html
	$(BROWSER) htmlcov/index.html

docs: clean-docs ## generate Sphinx HTML documentation, including API docs
	uv run sphinx-apidoc -o docs/ catxas
	uv run sphinx-build -b html docs docs/_build/html
	$(BROWSER) docs/_build/html/index.html

servedocs: ## live-rebuild and serve the docs while editing
	uv run sphinx-autobuild docs docs/_build/html

dist: clean ## build source and wheel packages
	uv build
	ls -l dist

release: dist ## upload a release to PyPI (build with `uv build` first)
	uv run twine upload dist/*

install: ## sync the project environment from the lockfile
	uv sync
