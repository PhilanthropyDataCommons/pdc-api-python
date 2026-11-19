import pytest
import requests
import responses
from conftest import BASE_URL, FakeTokenProvider

from pdc_api.errors import (
    PDCBadRequestError,
    PDCConflictError,
    PDCException,
    PDCForbiddenError,
    PDCNotFoundError,
    PDCServiceError,
    PDCUnauthorizedError,
    PDCUnprocessableEntityError,
)
from pdc_api.transport import APISession

URL = f"{BASE_URL}test-endpoint"


class TestPDCException:
    def test_sets_detail_and_code(self):
        exc = PDCException(detail="something went wrong", code=400)
        assert exc.detail == "something went wrong"
        assert exc.code == 400


class TestAPISession:
    @pytest.mark.parametrize(
        ("status", "error_class"),
        [
            (400, PDCBadRequestError),
            (401, PDCUnauthorizedError),
            (403, PDCForbiddenError),
            (404, PDCNotFoundError),
            (409, PDCConflictError),
            (422, PDCUnprocessableEntityError),
            (500, PDCServiceError),
            (503, PDCServiceError),
            (429, PDCException),
        ],
    )
    def test_raises_mapped_exception_on_error_status(self, session, status, error_class):
        responses.get(URL, json={"error": "test error"}, status=status)
        with pytest.raises(PDCException) as exc_info:
            session.get("/test-endpoint")
        assert type(exc_info.value) is error_class
        assert exc_info.value.code == status
        assert exc_info.value.detail == {"error": "test error"}

    def test_uses_text_detail_on_non_json_error_body(self, session):
        responses.get(URL, body="<html>Service Unavailable</html>", status=500)
        with pytest.raises(PDCServiceError) as exc_info:
            session.get("/test-endpoint")
        assert exc_info.value.detail == "<html>Service Unavailable</html>"

    @pytest.mark.parametrize("exception", [requests.Timeout, requests.ConnectionError])
    def test_raises_service_error_on_network_failure(self, session, exception):
        responses.get(URL, body=exception())
        with pytest.raises(PDCServiceError):
            session.get("/test-endpoint")

    @pytest.mark.parametrize("status", [502, 503, 504])
    def test_get_retries_on_gateway_error(self, session, status):
        responses.get(URL, status=status)
        responses.get(URL, json={"ok": True})

        assert session.get("/test-endpoint").json() == {"ok": True}
        assert len(responses.calls) == 2

    def test_get_raises_service_error_on_exhausted_retries(self, session):
        responses.get(URL, json={"error": "bad gateway"}, status=502)

        with pytest.raises(PDCServiceError) as exc_info:
            session.get("/test-endpoint")

        assert (exc_info.value.code, exc_info.value.detail) == (502, {"error": "bad gateway"})
        assert len(responses.calls) == 4

    def test_get_retries_with_keep_alive_disabled(self):
        session = APISession(base_url=BASE_URL, token_provider=FakeTokenProvider(), keep_alive=False)
        responses.get(URL, status=502)
        responses.get(URL, json={"ok": True})

        assert session.get("/test-endpoint").json() == {"ok": True}

    def test_post_does_not_retry(self, session):
        responses.post(URL, status=502)

        with pytest.raises(PDCServiceError):
            session.post("/test-endpoint")

        assert len(responses.calls) == 1

    def test_get_does_not_retry_on_other_server_errors(self, session):
        responses.get(URL, status=500)

        with pytest.raises(PDCServiceError):
            session.get("/test-endpoint")

        assert len(responses.calls) == 1

    def test_sends_bearer_token(self, session):
        responses.get(URL, json={})
        session.get("/test-endpoint")
        assert responses.calls[0].request.headers["Authorization"] == "Bearer fake-token"

    def test_keeps_connection_alive_by_default(self, session):
        assert session._session.headers.get("Connection") != "close"

    def test_sends_connection_close_when_keep_alive_is_false(self):
        session = APISession(base_url=BASE_URL, token_provider=FakeTokenProvider(), keep_alive=False)
        assert session._session.headers["Connection"] == "close"

    @pytest.mark.parametrize(
        ("base", "path", "expected"),
        [
            ("https://host/api", "users", "https://host/api/users"),
            ("https://host/api", "/users", "https://host/api/users"),
            ("https://host/api/", "users", "https://host/api/users"),
            ("https://host", "users", "https://host/users"),
            ("https://host/", "/users", "https://host/users"),
        ],
    )
    def test_make_api_url_preserves_base_path(self, base, path, expected):
        session = APISession(base_url=base, token_provider=FakeTokenProvider())
        assert session._make_api_url(path) == expected
