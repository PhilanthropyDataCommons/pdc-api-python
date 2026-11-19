from typing import Any

import pytest
import responses

from pdc_api.errors import PDCServiceError, TokenRequestError
from pdc_api.token import KeycloakClientCredentialsProvider

SERVER = "https://kc.test"
REALM = "pdc"
TOKEN_URL = f"{SERVER}/realms/{REALM}/protocol/openid-connect/token"


def _provider(**kwargs):
    return KeycloakClientCredentialsProvider(
        server_url=SERVER,
        realm=REALM,
        client_id="svc",
        client_secret="shh",
        timeout=5,
        **kwargs,
    )


def _add_token(*, access_token="abc", expires_in=300, status=200):
    add_kwargs: dict[str, Any] = {
        "method": responses.POST,
        "url": TOKEN_URL,
        "status": status,
    }
    if status == 200:
        add_kwargs["json"] = {"access_token": access_token, "expires_in": expires_in}
        add_kwargs["match"] = [
            responses.matchers.urlencoded_params_matcher(
                {"grant_type": "client_credentials", "client_id": "svc", "client_secret": "shh"}
            )
        ]
    else:
        add_kwargs["json"] = {"error": "invalid_client"}
    responses.add(**add_kwargs)


class TestKeycloakClientCredentialsProvider:
    def test_obtains_and_caches_token(self):
        _add_token(access_token="abc", expires_in=300)

        provider = _provider()

        assert provider.get_token() == "abc"
        assert provider.get_token() == "abc"
        assert len(responses.calls) == 1

    def test_refetches_after_expiry(self):
        _add_token(access_token="first", expires_in=0)
        _add_token(access_token="second", expires_in=300)

        provider = _provider()

        assert provider.get_token() == "first"
        assert provider.get_token() == "second"
        assert len(responses.calls) == 2

    def test_raises_token_request_error_on_non_200(self):
        _add_token(status=401)

        provider = _provider()

        with pytest.raises(TokenRequestError):
            provider.get_token()

    def test_raises_token_request_error_on_non_json_error_body(self):
        responses.add(method=responses.POST, url=TOKEN_URL, body="<html>502 Bad Gateway</html>", status=502)

        provider = _provider()

        with pytest.raises(TokenRequestError):
            provider.get_token()

    def test_raises_token_request_error_on_non_json_success_body(self):
        responses.add(method=responses.POST, url=TOKEN_URL, body="<html>not json</html>", status=200)

        provider = _provider()

        with pytest.raises(TokenRequestError):
            provider.get_token()

    def test_raises_token_request_error_on_missing_access_token(self):
        responses.add(method=responses.POST, url=TOKEN_URL, json={"expires_in": 300}, status=200)

        provider = _provider()

        with pytest.raises(TokenRequestError):
            provider.get_token()

    def test_raises_service_error_on_connection_failure(self):
        provider = _provider()  # no response registered -> ConnectionError

        with pytest.raises(PDCServiceError):
            provider.get_token()
