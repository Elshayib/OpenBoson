# OpenBoson developer commands (Windows PowerShell)
param(
    [Parameter(Position = 0)]
    [ValidateSet("test", "lint", "format", "typecheck", "content-check", "lab-check", "check", "build-win")]
    [string]$Command = "check"
)

$ErrorActionPreference = "Stop"
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

function Invoke-Test {
    & $Python -m pytest -v
}

function Invoke-Lint {
    & $Python -m ruff check src/openboson tests scripts
    & $Python -m ruff format --check src/openboson tests scripts
}

function Invoke-Format {
    & $Python -m ruff format src/openboson tests scripts
    & $Python -m ruff check --fix src/openboson tests scripts
}

function Invoke-Typecheck {
    & $Python -m mypy `
        src/openboson/config.py `
        src/openboson/resource_paths.py `
        src/openboson/settings_store.py `
        src/openboson/logging_setup.py `
        src/openboson/_build_info.py `
        src/openboson/bank_schema.py `
        src/openboson/exsim/objectives.py `
        src/openboson/exsim/blueprint.py `
        src/openboson/exsim/scoring.py `
        src/openboson/netsim/lab_schema.py
}

function Invoke-ContentCheck {
    & $Python -m pytest -v tests/exsim/test_content_pools.py tests/exsim/test_objectives.py tests/exsim/test_blueprint.py
}

function Invoke-LabCheck {
    & $Python -m pytest -v tests/netsim/test_lab_loader.py tests/netsim/test_grader.py tests/netsim/test_lab_session.py
}

switch ($Command) {
    "test" { Invoke-Test }
    "lint" { Invoke-Lint }
    "format" { Invoke-Format }
    "typecheck" { Invoke-Typecheck }
    "content-check" { Invoke-ContentCheck }
    "lab-check" { Invoke-LabCheck }
    "check" {
        Invoke-Lint
        Invoke-Typecheck
        Invoke-Test
    }
    "build-win" {
        & "$PSScriptRoot/build_windows.ps1"
    }
}
