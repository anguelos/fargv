PYTHON      := python
PYTEST      := pytest
RUFF        := ruff
SPHINX      := sphinx-build
SRC_DIR     := fargv
TEST_DIR    := test
UNITTEST_DIR := test/unittest
BUILD_DIR   := dist
DOC_DIR     := docs
DOC_BUILD   := docs/_build

.PHONY: all clean build doc htmldoc pdfdoc test testfull unittest testlint autolint

all: build

# ── Cleaning ──────────────────────────────────────────────────────────────────

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "tmp" -exec rm -rf {} +
	rm -rf $(BUILD_DIR) $(DOC_BUILD) .pytest_cache .ruff_cache .coverage htmlcov

# ── Build ─────────────────────────────────────────────────────────────────────

build: clean
	$(PYTHON) setup.py sdist bdist_wheel

# ── Documentation ─────────────────────────────────────────────────────────────

htmldoc:
	$(SPHINX) -b html $(DOC_DIR) $(DOC_BUILD)/html

doc: htmldoc

pdfdoc:
	$(SPHINX) -b simplepdf $(DOC_DIR) $(DOC_BUILD)/pdf

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	$(PYTEST) $(TEST_DIR) -x

testfull:
	$(PYTEST) $(TEST_DIR)

unittest:
	$(PYTEST) $(UNITTEST_DIR) 		--cov=$(SRC_DIR) 		--cov-config=pyproject.toml 		--cov-report=term-missing 		--cov-report=html

# ── Linting ───────────────────────────────────────────────────────────────────

testlint:
	$(RUFF) check $(SRC_DIR) $(TEST_DIR)

autolint:
	$(RUFF) check --fix $(SRC_DIR) $(TEST_DIR)
	$(RUFF) format $(SRC_DIR) $(TEST_DIR)
