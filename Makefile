.PHONY: install data test test-fast report report-quick lint

install:
	pip install -e ".[dev]"

data:
	casebook data

test:
	pytest

test-fast:
	pytest -m "not slow"

report:          ## full run: figures + reports/metrics.json (~5 min)
	casebook report

report-quick:
	casebook report --quick

lint:
	ruff check src tests
