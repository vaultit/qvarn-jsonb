.PHONY: env
env: env/.done env2/.done

env/bin/pip:
	python3.5 -m venv env
	env/bin/pip install --upgrade pip wheel setuptools

env/.done: env/bin/pip setup.py
	env/bin/pip install -r requirements-dev.txt -e .
	touch env/.done

env2/bin/pip:
	virtualenv -p python2 env2
	env2/bin/pip install --upgrade pip wheel setuptools

env2/.done: env2/bin/pip
	env2/bin/pip install -r requirements-dev-py2.txt
	touch env2/.done

env/bin/pip-compile: env/bin/pip
	env/bin/pip install pip-tools

.PHONY: requirements
requirements: env/bin/pip-compile
	env/bin/pip-compile --no-index requirements.in -o requirements.txt
	env/bin/pip-compile --no-index requirements.in requirements-dev.in -o requirements-dev.txt
	env/bin/pip-compile --no-index requirements-dev-py2.in -o requirements-dev-py2.txt

.PHONY: test
test: env
	./check

.PHONY: dist
dist: env/bin/pip
	env/bin/python setup.py sdist bdist_wheel
