from dataclasses import dataclass
from typing import Any

from keycloak import KeycloakAdmin as _KeycloakAdminClient
from keycloak.exceptions import KeycloakGetError


@dataclass
class KeycloakOrganization:
    id: str
    alias: str
    name: str


@dataclass
class KeycloakUser:
    id: str
    username: str
    email: str


class KeycloakAdmin:
    def __init__(
        self,
        *,
        keycloak_url: str,
        realm: str,
        admin_username: str,
        admin_password: str,
    ):
        # The bootstrap admin lives in the master realm and can administer any realm.
        self._admin = _KeycloakAdminClient(
            server_url=keycloak_url.rstrip("/") + "/",
            username=admin_username,
            password=admin_password,
            realm_name=realm,
            user_realm_name="master",
            client_id="admin-cli",
        )
        self.realm = realm

    def ensure_organization(self, *, name: str, alias: str, domain: str) -> KeycloakOrganization:
        existing = self._find_org_by_alias(alias)
        if existing is not None:
            return KeycloakOrganization(id=existing["id"], alias=existing["alias"], name=existing["name"])
        org_id = self._admin.create_organization(
            {"name": name, "alias": alias, "domains": [{"name": domain, "verified": False}]}
        )
        if org_id is None:
            raise LookupError(f"Keycloak did not return an id for new organization {alias!r}")
        return KeycloakOrganization(id=org_id, alias=alias, name=name)

    def get_organization(self, *, alias: str) -> KeycloakOrganization | None:
        existing = self._find_org_by_alias(alias)
        if existing is None:
            return None
        return KeycloakOrganization(id=existing["id"], alias=existing["alias"], name=existing["name"])

    def _find_org_by_alias(self, alias: str) -> dict[str, Any] | None:
        # Keycloak's org search matches names, not aliases, so filter the full listing.
        organizations: list[dict[str, Any]] = self._admin.get_organizations()
        for org in organizations:
            if org.get("alias") == alias:
                return org
        return None

    def ensure_user(
        self,
        *,
        username: str,
        email: str,
        password: str,
        first_name: str = "Test",
        last_name: str = "User",
    ) -> KeycloakUser:
        # The realm uses email as username, so a user created elsewhere may only match by email.
        existing = self._find_user_by_username(username) or self._find_user_by_email(email)
        if existing is not None:
            # python-keycloak defaults to temporary=True, which forces a password change at next login.
            self._admin.set_user_password(existing["id"], password, temporary=False)
            return KeycloakUser(
                id=existing["id"],
                username=existing["username"],
                email=existing.get("email") or email,
            )
        user_id = self._admin.create_user(
            {
                "username": username,
                "email": email,
                "emailVerified": True,
                "enabled": True,
                "firstName": first_name,
                "lastName": last_name,
                "credentials": [{"type": "password", "value": password, "temporary": False}],
            }
        )
        return KeycloakUser(id=user_id, username=username, email=email)

    def _find_user_by_username(self, username: str) -> dict[str, Any] | None:
        users: list[dict[str, Any]] = self._admin.get_users({"username": username, "exact": True})
        for user in users:
            if user.get("username") == username:
                return user
        return None

    def _find_user_by_email(self, email: str) -> dict[str, Any] | None:
        users: list[dict[str, Any]] = self._admin.get_users({"email": email, "exact": True})
        for user in users:
            if (user.get("email") or "").lower() == email.lower():
                return user
        return None

    def ensure_user_in_organization(self, *, organization_id: str, user_id: str) -> bool:
        for member in self._admin.get_organization_members(organization_id):
            if member.get("id") == user_id:
                return False
        self._admin.organization_user_add(user_id, organization_id)
        return True

    def remove_user_from_organization(self, *, organization_id: str, user_id: str) -> bool:
        for member in self._admin.get_organization_members(organization_id):
            if member.get("id") == user_id:
                self._admin.organization_user_remove(user_id, organization_id)
                return True
        return False

    def assign_realm_role(self, *, user_id: str, role_name: str) -> bool:
        for mapping in self._admin.get_realm_roles_of_user(user_id):
            if mapping.get("name") == role_name:
                return False
        try:
            role = self._admin.get_realm_role(role_name)
        except KeycloakGetError as exc:
            if exc.response_code == 404:
                raise LookupError(f"Realm role {role_name!r} not found in realm {self.realm!r}") from exc
            raise
        self._admin.assign_realm_roles(user_id, [{"id": role["id"], "name": role["name"]}])
        return True

    def ensure_oidc_login_enabled(self, *, client_id: str, redirect_uris: list[str]) -> None:
        target = self._find_client(client_id)
        body: dict[str, Any] = {}
        if not target.get("standardFlowEnabled"):
            body["standardFlowEnabled"] = True
        existing_uris = list(target.get("redirectUris") or [])
        merged = [*existing_uris, *(uri for uri in redirect_uris if uri not in existing_uris)]
        if merged != existing_uris:
            body["redirectUris"] = merged
        if not body:
            return
        self._admin.update_client(target["id"], body)

    def ensure_client_secret(self, *, client_id: str, secret: str) -> bool:
        target = self._find_client(client_id)
        current = self._admin.get_client_secrets(target["id"]).get("value")
        if current == secret:
            return False
        self._admin.update_client(target["id"], {"secret": secret})
        return True

    def ensure_direct_grants_enabled(self, *, client_id: str) -> None:
        target = self._find_client(client_id)
        if target.get("directAccessGrantsEnabled"):
            return
        self.set_direct_grants_enabled(client_id=client_id, enabled=True)

    def is_direct_grants_enabled(self, *, client_id: str) -> bool:
        return bool(self._find_client(client_id).get("directAccessGrantsEnabled"))

    def set_direct_grants_enabled(self, *, client_id: str, enabled: bool) -> None:
        target = self._find_client(client_id)
        self._admin.update_client(target["id"], {"directAccessGrantsEnabled": enabled})

    def _find_client(self, client_id: str) -> dict[str, Any]:
        clients: list[dict[str, Any]] = self._admin.get_clients()
        for client in clients:
            if client.get("clientId") == client_id:
                return client
        raise LookupError(f"Keycloak client {client_id!r} not found in realm {self.realm!r}")
