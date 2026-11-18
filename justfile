# Keep in sync with just-version in .github/workflows/ci.yml
set minimum-version := '1.55.0'

mod pdc 'just/pdc.just'

python := shell("cat .python-version")

_default:
    @just --list --unsorted

# Lint and check formatting
[group('dev')]
lint:
    uv run ruff check .
    uv run ruff format . --check

# Format and autofix lint issues
[group('dev')]
format:
    uv run ruff format .
    uv run ruff check . --fix

# Run the unit tests against the installed package
[group('test')]
[arg("python", long)]
[arg("lowest_direct", long="lowest-direct", value="true")]
[arg("upgrade", long, value="true")]
test python=python lowest_direct="false" upgrade="false" *args:
    @if [ "{{upgrade}}" = "true" ]; then uv lock --upgrade --dry-run; fi
    uv run --python={{python}} \
        {{ if lowest_direct == "true" { "--resolution=lowest-direct" } else { "" } }} \
        {{ if upgrade == "true" { "--upgrade" } else { "" } }} \
        --isolated --no-editable --no-dev --group tests --reinstall -- \
        python -I -m pytest {{args}}

# Run the integration tests against the installed package and a live PDC stack (run `just pdc up` first)
[group('test')]
[arg("python", long)]
[arg("lowest_direct", long="lowest-direct", value="true")]
[arg("upgrade", long, value="true")]
integration python=python lowest_direct="false" upgrade="false" *args:
    @if [ "{{upgrade}}" = "true" ]; then uv lock --upgrade --dry-run; fi
    uv run --python={{python}} \
        {{ if lowest_direct == "true" { "--resolution=lowest-direct" } else { "" } }} \
        {{ if upgrade == "true" { "--upgrade" } else { "" } }} \
        --isolated --no-editable --no-dev --group tests --reinstall -- \
        python -I -m pytest -c integration_tests/pytest.ini integration_tests/ {{args}}

# Run lint, unit tests, and integration tests (run `just pdc up` first)
[group('test')]
check: lint test integration

# Download the current PDC OpenAPI spec
[group('codegen')]
update-api-spec:
    curl -fsSL https://api.philanthropydatacommons.org/openapi/api.json -o src/pdc_api_client/openapi.json
    uv run python -c "import json; json.load(open('src/pdc_api_client/openapi.json'))"

# Regenerate src/pdc_api_client/_generated.py from src/pdc_api_client/openapi.json
[group('codegen')]
codegen:
    uv run python codegen/preprocess.py src/pdc_api_client/openapi.json codegen/openapi.preprocessed.json
    uv run datamodel-codegen \
      --input codegen/openapi.preprocessed.json --input-file-type openapi \
      --output src/pdc_api_client/_generated.py \
      --output-model-type pydantic_v2.BaseModel \
      --base-class pdc_api_client._base.BaseSchema \
      --snake-case-field --use-annotated --use-standard-collections --use-union-operator \
      --collapse-root-models --capitalise-enum-members --target-python-version 3.12 --disable-timestamp \
      --formatters ruff-format ruff-check
    uv run python codegen/postprocess.py src/pdc_api_client/_generated.py
    uv run ruff format src/pdc_api_client/_generated.py
