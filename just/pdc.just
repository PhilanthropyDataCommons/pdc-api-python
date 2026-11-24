# Runs PDC's CI stack (PDC API, Keycloak, Postgres, S3), refetched from PDC's main branch on every `up`.

set working-directory := '..'

cache := 'local/pdc-stack'
base := 'https://raw.githubusercontent.com/PhilanthropyDataCommons/service/main'
compose := 'docker compose -f ' + cache + '/compose-ci.yml'

_default:
    @just --list pdc --unsorted

# Fetch PDC's compose file and Keycloak realm, adding the admin API access the realm lacks
fetch:
    mkdir -p {{cache}}/keycloak
    curl -fsSL {{base}}/compose-ci.yml -o {{cache}}/compose-ci.yml
    curl -fsSL {{base}}/keycloak/realm.json -o {{cache}}/keycloak/realm.json
    uv run --no-project python -I just/patch_realm.py {{cache}}/keycloak/realm.json

# Start the stack and wait until it is healthy
up: fetch
    {{compose}} pull
    {{compose}} up -d --wait

# Follow the stack's logs
logs:
    {{compose}} logs -f

# Stop the stack, keeping its data
down:
    {{compose}} down --remove-orphans

# Stop the stack and delete its data
reset:
    {{compose}} down --remove-orphans --volumes
