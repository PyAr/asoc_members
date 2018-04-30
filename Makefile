help:
	@echo "help  -- print this help"
	@echo "start -- start docker stack"
	@echo "stop  -- stop docker stack"
	@echo "ps    -- show status"
	@echo "clean -- clean all artifacts"
	@echo "test  -- run tests using docker"
	@echo "dockershell -- run bash inside docker"
	@echo "shell_plus -- run django shell_plus inside docker"
	@echo "bootstrap --build containers, run django migrations, load fixtures and create the a superuser"

RUN=docker-compose run --rm web
MANAGE=${RUN} python3 website/manage.py

build:
	docker-compose build

start:
	docker-compose up

stop:
	docker-compose stop

ps:
	docker-compose ps

clean: stop
	docker-compose rm --force -v

test:
	${MANAGE} test  -v2 --noinput

dockershell:
	${RUN} /bin/bash

migrations:
	${MANAGE} makemigrations

migrate:
	${MANAGE} migrate

shell_plus:
	${MANAGE} shell_plus

.PHONY: help start stop ps clean test dockershell shell_plus only_test pep8
