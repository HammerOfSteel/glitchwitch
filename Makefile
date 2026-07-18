GODOT ?= .tooling/godot

.PHONY: setup assets test test-python test-godot import lint format run clean

setup:
	python3 tools/bootstrap.py --all

assets:
	python3 -m tools.assetgen.build

test: test-python test-godot

test-python:
	python3 -m pytest tests/python -q

import:
	$(GODOT) --headless --path . --import

test-godot: import
	$(GODOT) --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit --ignoreHeadlessMode

lint:
	python3 -m gdtoolkit.linter src tests/unit
	python3 -m gdtoolkit.formatter --check src tests/unit

format:
	python3 -m gdtoolkit.formatter src tests/unit

run:
	$(GODOT) --path .

clean:
	rm -rf .godot assets/generated build exports reports
