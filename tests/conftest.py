from functools import partial

import pytest
import responses

from pdc_api_client import testing as pdc_testing
from pdc_api_client.transport import APISession

BASE_URL = "https://pdc.test/"


class FakeTokenProvider:
    def get_token(self) -> str:
        return "fake-token"

    def refresh_if_necessary(self) -> None:
        pass


@pytest.fixture(autouse=True)
def _intercept_requests():
    responses.start()
    yield
    responses.stop()
    responses.reset()


@pytest.fixture
def session() -> APISession:
    return APISession(base_url=BASE_URL, token_provider=FakeTokenProvider())


@pytest.fixture
def add_json_response():
    return partial(pdc_testing.add_json_response, base_url=BASE_URL)


@pytest.fixture
def add_page_response():
    return partial(pdc_testing.add_page_response, base_url=BASE_URL)


@pytest.fixture
def add_changemaker_response():
    return partial(pdc_testing.add_changemaker_response, base_url=BASE_URL)


@pytest.fixture
def add_funder_response():
    return partial(pdc_testing.add_funder_response, base_url=BASE_URL)


@pytest.fixture
def add_proposal_response():
    return partial(pdc_testing.add_proposal_response, base_url=BASE_URL)


@pytest.fixture
def add_application_form_response():
    return partial(pdc_testing.add_application_form_response, base_url=BASE_URL)


@pytest.fixture
def add_organization_response():
    return partial(pdc_testing.add_organization_response, base_url=BASE_URL)
