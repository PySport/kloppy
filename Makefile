format-check:
	black --check .
typecheck:
	mypy -p kloppy --strict --no-incremental