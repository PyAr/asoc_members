help:
	@echo "help  -- print this help"
	@echo "bootstrap -- rarely used: only first time project is cloned, or when infrastructure dependencies change"
	@echo "test  -- run all the tests"
	@echo "run  -- normally used to run the service locally"
	@echo "stop  -- normally used to turn the services off"
	@echo "clean -- rarely used: only when we want to stop and remove everything created by bootstrapping"
	@echo "ps    -- show status"
	@echo "dockershell -- run bash inside docker"
	@echo "shell_plus -- run django shell_plus inside docker"
	@echo "load_members_testdata -- populate the DB with members"
	@echo "load_providers_test_data -- populate the DB with providers"

RUN=docker-compose exec web
MANAGE=${RUN} ./manage.py

# rarely used: only first time project is cloned, or when infrastructure dependencies change
bootstrap:
	docker-compose up -d
	${RUN} pip install -r /code/config/requirements-dev.txt

# run all the tests; to avoid migrations everytime and run only some of them, do for example:
# 	make test ARGS="-k members.tests.ReportCompleteTests"
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

load_members_testdata:
	${MANAGE} load_data_test 20

load_providers_test_data:
	${MANAGE} load_providers_data 20

.PHONY: help start stop ps clean test dockershell shell_plus only_test pep8
