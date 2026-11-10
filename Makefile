PYTHON ?= python3
DIST_DIR ?= dist
VERSION ?= $(shell $(PYTHON) -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
TEST_ARGS ?=
INTEGRATION_ARGS ?=

.PHONY: help build unit integration package-check check publish

help:
	@printf '%s\n' \
	  'Targets:' \
	  '  build          Build the wheel and source archive' \
	  '  unit           Run unit tests (options: TEST_ARGS="...")' \
	  '  integration    Run Podman Compose tests (options: INTEGRATION_ARGS="...")' \
	  '  package-check  Build and validate distribution artifacts' \
	  '  check          Run all tests and validate distribution artifacts' \
	  '  publish        Verify and publish the current version to PyPI' \
	  '  Tools: test and release extras'

build:
	$(PYTHON) -m build --outdir "$(DIST_DIR)" .

unit:
	$(PYTHON) -m pytest tests/ --ignore=tests/integration $(TEST_ARGS)

integration:
	./scripts/test-integration.sh $(INTEGRATION_ARGS)

package-check: build
	$(PYTHON) -m twine check "$(DIST_DIR)"/ttlama_cli-$(VERSION)*

check: unit integration package-check

publish: check
	@test -n "$${TWINE_PASSWORD:-}" || { printf 'TWINE_PASSWORD must contain a PyPI API token.\n' >&2; exit 1; }
	TWINE_USERNAME=__token__ $(PYTHON) -m twine upload --non-interactive --repository pypi "$(DIST_DIR)"/ttlama_cli-$(VERSION)*