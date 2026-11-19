import uuid

import pytest

from pdc_api_client.errors import PDCNotFoundError
from pdc_api_client.permission_grants import (
    DefaultPermissionGrant,
    PermissionGrantEntityType,
    PermissionGrantGranteeType,
    PermissionGrantVerb,
    create_default_permission_grant,
    delete_default_permission_grant,
    get_default_permission_grant,
    list_default_permission_grants,
    update_default_permission_grant,
)


@pytest.fixture()
def created_default_grant_ids(api_session):
    ids: list[int] = []
    yield ids
    for grant_id in ids:
        try:
            delete_default_permission_grant(api_session, grant_id=grant_id)
        except PDCNotFoundError:
            pass


def _changemaker_view_spec() -> DefaultPermissionGrant:
    return DefaultPermissionGrant(
        context_entity_type=PermissionGrantEntityType.CHANGEMAKER,
        grantee_type=PermissionGrantGranteeType.USER_GROUP,
        grantee_keycloak_organization_id=uuid.uuid4(),
        verbs=[PermissionGrantVerb.VIEW],
        scope=[PermissionGrantEntityType.PROPOSAL],
    )


class TestDefaultPermissionGrantsLifecycle:
    def test_create_get_update_delete_roundtrip(self, api_session, created_default_grant_ids):
        spec = _changemaker_view_spec()

        created = create_default_permission_grant(api_session, grant=spec)
        created_default_grant_ids.append(created.id)

        assert created.id is not None
        assert created.context_entity_type == PermissionGrantEntityType.CHANGEMAKER
        assert created.grantee_keycloak_organization_id == spec.grantee_keycloak_organization_id

        assert get_default_permission_grant(api_session, grant_id=created.id) == created

        spec.verbs = [PermissionGrantVerb.VIEW, PermissionGrantVerb.EDIT]
        updated = update_default_permission_grant(api_session, grant_id=created.id, grant=spec)
        assert set(updated.verbs) == {PermissionGrantVerb.VIEW, PermissionGrantVerb.EDIT}

        delete_default_permission_grant(api_session, grant_id=created.id)
        created_default_grant_ids.remove(created.id)

        with pytest.raises(PDCNotFoundError):
            get_default_permission_grant(api_session, grant_id=created.id)

    def test_list_includes_created_grant(self, api_session, created_default_grant_ids):
        created = create_default_permission_grant(api_session, grant=_changemaker_view_spec())
        created_default_grant_ids.append(created.id)

        bundle = list_default_permission_grants(api_session, count_per_page=200)

        assert created in bundle.entries


class TestDefaultPermissionGrantsErrors:
    def test_get_nonexistent_raises_not_found(self, api_session):
        with pytest.raises(PDCNotFoundError):
            get_default_permission_grant(api_session, grant_id=999_999_999)

    def test_delete_nonexistent_raises_not_found(self, api_session):
        with pytest.raises(PDCNotFoundError):
            delete_default_permission_grant(api_session, grant_id=999_999_999)
