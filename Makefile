
.PHONY: coverage
coverage:
	@-coverage run --source=sheets -m unittest discover tests &> /dev/null
	@coverage report -m
	@rm .coverage

.PHONY: test
test:
	@python3 -m unittest discover tests

.PHONY: lint
lint:
	@pylint --rcfile=.pylintrc sheets