import json
import sys
from pathlib import Path

ADMIN_API_SCOPE = {
    "name": "kc-admin-api",
    "description": "Grants access to the Keycloak Admin REST API by adding its required audience to the token",
    "protocol": "openid-connect",
    "attributes": {"include.in.token.scope": "true", "display.on.consent.screen": "false"},
    "protocolMappers": [
        {
            "name": "admin-api-audience",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-admin-api-audience-mapper",
            "consentRequired": False,
            "config": {"access.token.claim": "true", "introspection.token.claim": "true"},
        }
    ],
}
ADMIN_API_CLIENTS = {"pdc-dev-ingest", "pdc-openapi-docs"}
ORGANIZATION_ROLES = ["query-organizations", "view-organizations", "manage-organizations"]


# Keycloak creates kc-admin-api for new and migrated realms but not imported ones; remove once service's realm.json defines it.
def add_admin_api_access(realm: dict) -> None:
    realm["clientScopes"].append(ADMIN_API_SCOPE)
    for client in realm["clients"]:
        if client["clientId"] in ADMIN_API_CLIENTS:
            client["optionalClientScopes"].append(ADMIN_API_SCOPE["name"])
    [admin_group] = [group for group in realm["groups"] if group["name"] == "pdc-admin"]
    admin_group["clientRoles"]["realm-management"].extend(ORGANIZATION_ROLES)


def main(path: Path) -> None:
    realm = json.loads(path.read_text())
    if any(scope["name"] == ADMIN_API_SCOPE["name"] for scope in realm["clientScopes"]):
        print(f"warning: {path} already defines kc-admin-api; delete just/patch_realm.py", file=sys.stderr)
        return
    add_admin_api_access(realm)
    path.write_text(json.dumps(realm, indent="\t") + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
