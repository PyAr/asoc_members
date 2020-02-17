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
MANAGE=${RUN} ./manage.py

# rarely used: only first time project is cloned, or when infrastructure dependencies change
bootstrap:
	docker-compose up -d
	${RUN} pip install -r /code/config/requirements-dev.txt

# run all the tests; do FIXME for run only some of them
test:
	docker-compose start
	${MANAGE} test -v2 --noinput $(ARGS)

# normally used to run the service locally
run:
	docker-compose start
	${MANAGE} migrate
	${MANAGE} runserver 0.0.0.0:8127

# normally used to turn the services off
stop:
	docker-compose stop

# rarely used: only when we want to stop and remove everything created by bootstrapping
clean:
	docker-compose stop
	docker-compose down --rmi local

ps:
	docker-compose ps

createsuperuser:
	${MANAGE} createsuperuser

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
