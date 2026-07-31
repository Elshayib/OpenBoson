.PHONY: test lint format typecheck content-check lab-check check build-win

PYTHON ?= python

test:
	$(PYTHON) -m pytest -v

lint:
	$(PYTHON) -m ruff check src/openboson tests scripts
	$(PYTHON) -m ruff format --check src/openboson tests scripts

format:
	$(PYTHON) -m ruff format src/openboson tests scripts
	$(PYTHON) -m ruff check --fix src/openboson tests scripts

typecheck:
	$(PYTHON) -m mypy \
		src/openboson/config.py \
		src/openboson/resource_paths.py \
		src/openboson/settings_store.py \
		src/openboson/logging_setup.py \
		src/openboson/_build_info.py \
		src/openboson/bank_schema.py \
		src/openboson/exsim/objectives.py \
		src/openboson/exsim/blueprint.py \
		src/openboson/exsim/scoring.py \
		src/openboson/netsim/lab_schema.py

content-check:
	$(PYTHON) -m pytest -v tests/exsim/test_content_pools.py tests/exsim/test_objectives.py tests/exsim/test_blueprint.py

lab-check:
	$(PYTHON) -m pytest -v tests/netsim/test_lab_loader.py tests/netsim/test_grader.py tests/netsim/test_lab_session.py

check: lint typecheck test

build-win:
	pwsh -File scripts/build_windows.ps1
