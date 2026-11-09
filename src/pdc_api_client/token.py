import time
from typing import Protocol, runtime_checkable

import requests

from pdc_api_client.errors import PDCServiceError, TokenRequestError


@runtime_checkable
class TokenProvider(Protocol):
    def get_token(self) -> str: ...

    def refresh_if_necessary(self) -> None: ...


class KeycloakClientCredentialsProvider:
    def __init__(
        self,
        *,
        server_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        timeout: float,
        expiry_leeway_seconds: float = 30.0,
    ):
        self._token_url = f"{server_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout
        self._leeway = expiry_leeway_seconds
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        if self._token is None or time.monotonic() >= self._expires_at - self._leeway:
            self._request_token()
        return self._token

    def refresh_if_necessary(self) -> None:
        pass

    def _request_token(self) -> None:
        try:
            response = requests.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=self._timeout,
            )
        except requests.Timeout as exc:
            raise PDCServiceError(detail="Request to PDC auth timed out") from exc
        except requests.ConnectionError as exc:
            raise PDCServiceError(detail="Could not connect to PDC auth") from exc
        if response.status_code != 200:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise TokenRequestError(detail=detail, code=response.status_code)
        # A fronting proxy can return 200 with a body that isn't a token.
        try:
            payload = response.json()
            self._token = payload["access_token"]
            self._expires_at = time.monotonic() + payload["expires_in"]
        except (ValueError, KeyError) as exc:
            raise TokenRequestError(
                detail="Malformed token response from auth server", code=response.status_code
            ) from exc
