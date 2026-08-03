.PHONY: install test lint typecheck check demo

install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy src

check: lint typecheck test

demo:
	kindle-notes inspect "examples/My Clippings.txt"
	kindle-notes pdf "examples/My Clippings.txt" --output dist/demo.pdf
