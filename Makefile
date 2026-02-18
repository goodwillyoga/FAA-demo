.PHONY: test build-data run-cli run-api

test:
	PYTHONPATH=src python3 -m pytest -q

run-cli: build-data
	./scripts/run_cli.sh

run-api: build-data
	./scripts/run_api.sh

build-data:
	./scripts/build_data.sh
