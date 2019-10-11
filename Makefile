clean: clean-eggs clean-build
	@find . -iname '*.pyc' -delete
	@find . -iname '*.pyo' -delete
	@find . -iname '*~' -delete
	@find . -iname '*.swp' -delete
	@find . -iname '__pycache__' -delete

clean-eggs:
	@find . -name '*.egg' -print0|xargs -0 rm -rf --
	@rm -rf .eggs/

clean-build:
	@rm -fr build/
	@rm -fr dist/
	@rm -fr *.egg-info

deps:
	poetry install

test: deps
	poetry run pytest -vvv

build: test
	poetry build

/usr/local/bin/package_cloud:
	sudo gem install package_cloud

package_cloud: /usr/local/bin/package_cloud

version = `cat CHANGES.rst | awk '/^[0-9]+\.[0-9]+(\.[0-9]+)?/' | head -n1`
bump_version:
	poetry version $(version)
	git add pyproject.toml
	git commit -m"Bump version $(version)"

release: package_cloud clean build
	git rev-parse --abbrev-ref HEAD | grep '^master$$'
	git tag $(version)
	git push origin $(version)
	package_cloud push olist/v2/python dist/*.whl
	package_cloud push olist/v2/python dist/*.tar.gz

lint:
	pre-commit install && pre-commit run -a -v

pyformat:
	black .

update:
	poetry update
