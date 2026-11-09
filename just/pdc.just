# Runs upstream's CI stack (PDC API, Keycloak, Postgres, S3), refetched from PDC's main branch on every `up`.

set working-directory := '..'

cache := 'local/pdc-stack'
base := 'https://raw.githubusercontent.com/PhilanthropyDataCommons/service/main'
compose := 'docker compose -f ' + cache + '/compose-ci.yml'

_default:
    @just --list pdc --unsorted

# Fetch upstream's compose file and Keycloak realm
fetch:
    mkdir -p {{cache}}/keycloak
    curl -fsSL {{base}}/compose-ci.yml -o {{cache}}/compose-ci.yml
    curl -fsSL {{base}}/keycloak/realm.json -o {{cache}}/keycloak/realm.json

# Start the stack and wait until it is healthy
up: fetch
    {{compose}} pull
    {{compose}} up -d --wait

# Follow the stack's logs
logs: fetch
    {{compose}} logs -f

# Stop the stack, keeping its data
down: fetch
    {{compose}} down --remove-orphans

# Stop the stack and delete its data
reset: fetch
    {{compose}} down --remove-orphans --volumes
