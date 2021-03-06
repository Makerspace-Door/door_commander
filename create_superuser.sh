#!/bin/bash
set -euf -o pipefail
COMPOSE="docker-compose -f docker-compose.yml"

test -f secrets.env
source secrets.env

$COMPOSE build --parallel
# recreate the containers with the new password.
$COMPOSE up --no-start --force-recreate
$COMPOSE run --rm python ./manage.py check --deploy
$COMPOSE run --rm python ./manage.py migrate
$COMPOSE run --rm python ./manage.py createsuperuser

