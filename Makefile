.PHONY: test run-cli run-api

test:
	PYTHONPATH=src python3 -m pytest -q

run-cli:
	./scripts/run_cli.sh

run-api:
	./scripts/run_api.sh
