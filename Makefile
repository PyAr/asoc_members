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

RUN=docker-compose exec web
COMPOSE_PROD=docker-compose -f docker-compose.prod.yml
RUN_PROD=${COMPOSE_PROD} exec web
MANAGE=${RUN} ./manage.py

build-dev:
	docker-compose build

build-prod:
	${COMPOSE_PROD} build
	${COMPOSE_PROD} pull

start-dev:
	docker-compose up -d
	${MANAGE} migrate
	${MANAGE} runserver 0.0.0.0:8000

install-dev:
	${RUN} pip install -r /code/config/requirements-dev.txt

createsuperuser:
	${MANAGE} createsuperuser

up-prod:
	${COMPOSE_PROD} up -d

stop-dev:
	docker-compose stop

stop-prod:
	${COMPOSE_PROD} stop

ps-dev:
	docker-compose ps

ps-prod:
	${COMPOSE_PROD} ps

clean-dev:
	docker-compose down

clean-prod:
	${COMPOSE_PROD} down

test:
	${MANAGE} test -v2 --noinput $(ARGS)

dockershell:
	${RUN} /bin/bash

migrations:
	${MANAGE} makemigrations

migrate:
	${MANAGE} migrate

collectstatic:
	${MANAGE} collectstatic

shell_plus:
	${MANAGE} shell_plus

.PHONY: help start stop ps clean test dockershell shell_plus only_test pep8
