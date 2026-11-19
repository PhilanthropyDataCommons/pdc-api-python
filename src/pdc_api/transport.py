from typing import Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from pdc_api import errors
from pdc_api.token import TokenProvider

_ERRORS_BY_STATUS = {
    400: errors.PDCBadRequestError,
    401: errors.PDCUnauthorizedError,
    403: errors.PDCForbiddenError,
    404: errors.PDCNotFoundError,
    409: errors.PDCConflictError,
    422: errors.PDCUnprocessableEntityError,
}


class APISession:
    def __init__(
        self,
        *,
        base_url: str,
        token_provider: TokenProvider,
        timeout: float = 15,
        request_kwargs: dict[str, Any] | None = None,
        keep_alive: bool = True,
    ) -> None:
        # Without the trailing slash, urljoin drops the last path segment of a base like "https://host/api".
        self._base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.auth = token_provider
        self._timeout = timeout
        self._request_kwargs = request_kwargs or {}
        self._session = requests.Session()
        self._session.headers["Accept"] = "application/json"
        # A proxy in front of PDC can answer a healthy upstream with a one-off 502; only idempotent reads retry.
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(502, 503, 504),
            allowed_methods=("GET", "HEAD"),
            raise_on_status=False,
        )
        for scheme in ("https://", "http://"):
            self._session.mount(scheme, HTTPAdapter(max_retries=retries))
        # Idle pooled connections can be closed server-side and raise RemoteDisconnected on reuse.
        if not keep_alive:
            self._session.headers["Connection"] = "close"

    def _make_api_url(self, path: str) -> str:
        return urljoin(self._base_url, path.lstrip("/"))

    def _make_api_request(
        self, method: str, url: str, data: Any = None, params: Any = None, **kwargs: Any
    ) -> requests.Response:
        if not url.startswith("http"):
            url = self._make_api_url(url)
        timeout = kwargs.pop("timeout", self._timeout)

        self.auth.refresh_if_necessary()
        self._session.headers["Authorization"] = f"Bearer {self.auth.get_token()}"

        try:
            response = self._session.request(
                method, url, data=data, params=params, timeout=timeout, **{**self._request_kwargs, **kwargs}
            )
        except requests.Timeout as exc:
            raise errors.PDCServiceError(detail="Request to PDC timed out") from exc
        except requests.ConnectionError as exc:
            raise errors.PDCServiceError(detail="Could not connect to PDC") from exc

        if response.status_code >= 300:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text or f"HTTP {response.status_code}"
            error_class: type[errors.PDCException]
            if response.status_code >= 500:
                error_class = errors.PDCServiceError
            else:
                error_class = _ERRORS_BY_STATUS.get(response.status_code, errors.PDCException)
            raise error_class(detail=detail, code=response.status_code)
        return response

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self._make_api_request("GET", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        return self._make_api_request("PUT", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self._make_api_request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> requests.Response:
        return self._make_api_request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self._make_api_request("DELETE", path, **kwargs)
