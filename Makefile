.PHONY: build test serve migrate clean

build:          ## Build the site into build/
	.venv/bin/python -m src.build

test:           ## Run the whole test suite
	.venv/bin/python -m pytest -q

serve: build    ## Build, then serve on http://localhost:8000
	.venv/bin/python -m http.server 8000 --directory build

migrate:        ## Re-run the one-time corpus migration (writes to recipes/)
	.venv/bin/python tools/migrate_corpus.py --dry-run

clean:
	rm -rf build
