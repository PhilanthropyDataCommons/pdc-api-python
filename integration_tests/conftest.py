import os
import uuid

import pytest
import requests

from pdc_api.errors import TokenRequestError
from pdc_api.models import FunderCollaborativeMemberBundle
from pdc_api.seeding.keycloak_admin import KeycloakAdmin
from pdc_api.seeding.pdc_entities import (
    SeededFunderCollaborative,
    SeededProposalBundle,
    seed_funder_collaborative_with_members,
    seed_proposal_bundle,
    seed_proposal_corpus,
)
from pdc_api.token import KeycloakClientCredentialsProvider
from pdc_api.transport import APISession

PDC_API_URL = os.environ.get("PDC_API_URL", "http://localhost:3030")
KEYCLOAK_SERVER_URL = os.environ.get("KEYCLOAK_SERVER_URL", "http://pdc-auth:8780")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "pdc")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "pdc-dev-ingest")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "password")
PDC_API_TIMEOUT = float(os.environ.get("PDC_API_TIMEOUT", "30"))
KEYCLOAK_ADMIN_USERNAME = os.environ.get("KEYCLOAK_ADMIN_USERNAME", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin")


@pytest.fixture(scope="session")
def api_session() -> APISession:
    return APISession(
        base_url=PDC_API_URL,
        token_provider=KeycloakClientCredentialsProvider(
            server_url=KEYCLOAK_SERVER_URL,
            realm=KEYCLOAK_REALM,
            client_id=KEYCLOAK_CLIENT_ID,
            client_secret=KEYCLOAK_CLIENT_SECRET,
            timeout=PDC_API_TIMEOUT,
        ),
        timeout=PDC_API_TIMEOUT,
    )


@pytest.fixture(scope="session", autouse=True)
def seeded_pdc_stack(api_session) -> SeededProposalBundle:
    return seed_proposal_bundle(api_session)


@pytest.fixture(scope="session")
def seeded_pdc_corpus(api_session, seeded_pdc_stack) -> list[SeededProposalBundle]:
    return seed_proposal_corpus(api_session)


@pytest.fixture(scope="session")
def keycloak_admin() -> KeycloakAdmin:
    return KeycloakAdmin(
        keycloak_url=KEYCLOAK_SERVER_URL,
        realm=KEYCLOAK_REALM,
        admin_username=KEYCLOAK_ADMIN_USERNAME,
        admin_password=KEYCLOAK_ADMIN_PASSWORD,
    )


@pytest.fixture(scope="session")
def keycloak_client_id() -> str:
    return KEYCLOAK_CLIENT_ID


@pytest.fixture(scope="session")
def seeded_large_collaborative(api_session) -> SeededFunderCollaborative:
    return seed_funder_collaborative_with_members(
        api_session,
        member_count=FunderCollaborativeMemberBundle.default_page_size + 1,
    )


TEST_USER_PASSWORD = "integration-test-password"


class _StaticTokenProvider:
    def __init__(self, token: str):
        self._token = token

    def get_token(self) -> str:
        return self._token

    def refresh_if_necessary(self) -> None:
        pass


@pytest.fixture(scope="session")
def session_narrowed_to():

    def make(username: str, org_alias: str) -> APISession:
        response = requests.post(
            f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": KEYCLOAK_CLIENT_ID,
                "client_secret": KEYCLOAK_CLIENT_SECRET,
                "username": username,
                "password": TEST_USER_PASSWORD,
                "scope": f"openid organizations:{org_alias}",
            },
            timeout=PDC_API_TIMEOUT,
        )
        response.raise_for_status()
        return APISession(
            base_url=PDC_API_URL,
            token_provider=_StaticTokenProvider(response.json()["access_token"]),
            timeout=PDC_API_TIMEOUT,
        )

    return make


@pytest.fixture(scope="session")
def test_user_password() -> str:
    return TEST_USER_PASSWORD


@pytest.fixture
def suffix() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture
def fresh_keycloak_org(keycloak_admin, suffix):
    alias = f"fresh-org-{suffix}"
    return keycloak_admin.ensure_organization(
        name=f"Fresh Org {suffix}",
        alias=alias,
        domain=f"{alias}.example.com",
    )


@pytest.fixture
def add_user_to_org(keycloak_admin, keycloak_client_id, test_user_password):
    keycloak_admin.ensure_direct_grants_enabled(client_id=keycloak_client_id)

    def add(username: str, *orgs) -> None:
        user = keycloak_admin.ensure_user(username=username, email=username, password=test_user_password)
        for org in orgs:
            keycloak_admin.ensure_user_in_organization(organization_id=org.id, user_id=user.id)

    return add


# PDC's CI realm offers kc-admin-api only once service's realm.json defines it; until then the sync can't run.
@pytest.fixture(scope="session")
def admin_api_session() -> APISession:
    token_provider = KeycloakClientCredentialsProvider(
        server_url=KEYCLOAK_SERVER_URL,
        realm=KEYCLOAK_REALM,
        client_id=KEYCLOAK_CLIENT_ID,
        client_secret=KEYCLOAK_CLIENT_SECRET,
        timeout=PDC_API_TIMEOUT,
        scope="kc-admin-api",
    )
    try:
        token_provider.get_token()
    except TokenRequestError as error:
        if "invalid_scope" not in str(error.detail):
            raise
        pytest.skip(f"Keycloak does not offer the kc-admin-api scope to {KEYCLOAK_CLIENT_ID}")
    return APISession(base_url=PDC_API_URL, token_provider=token_provider, timeout=PDC_API_TIMEOUT)
