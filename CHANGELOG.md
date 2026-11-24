# Changelog

This project follows [Semantic Versioning](https://semver.org). Until 1.0, a minor version may include breaking changes.

PDC does not bump its spec version for every API change, so each entry names the spec version and the date the spec was downloaded.

## Unreleased

Spec: PDC 0.43.0, downloaded 2026-11-24.

- `Organization` has `keycloak_organization_id`, `keycloak_organization_name`, `disabled_at`, `members`, and `former_members`. `members` and `former_members` are `None` when the caller may not see membership, or when PDC has not yet synced the organization from Keycloak.
- `get_organizations` walks `GET /organizations`.
- `pdc_api.testing` adds `user_payload`, and `organization_payload` takes the new fields.

## 0.4.1 (2026-11-20)

- `pdc-api` is published on [PyPI](https://pypi.org/project/pdc-api/). Install it with `pip install pdc-api`.

## 0.4.0 (2026-11-19)

Breaking changes that make names consistent before a wider release:

- The distribution is now `pdc-api` (was `pdc-python-client`), the import name is `pdc_api` (was `pdc_api_client`), and the repository is `PhilanthropyDataCommons/pdc-api-python`.
- `get_basefields` is now `get_base_fields`, `create_changemaker_proposal` is `create_proposal`, `create_changemaker_proposal_version` is `create_proposal_version`, and `register_file_upload` is `create_file`.
- `get_application_form` takes `application_form_id` instead of `form_id`.
- `list_permission_grants` filters by `changemaker_id`, `funder_short_code`, and `proposal_id` instead of `changemaker`, `funder`, and `proposal`.
- The permission grant create and update functions take `grant` instead of `spec`.
- `ProposalNotFoundError`, `ChangemakerNotFoundError`, `FunderNotFoundError`, and `ChangemakerFieldValueBatchNotFoundError` now subclass `PDCNotFoundError`, and their `.detail` names the missing resource.
- Seeding's `ensure_funder_for_kc_org`, `ensure_changemaker_for_kc_org`, and `ensure_data_provider_for_kc_org` are now `ensure_*_for_keycloak_org`, with a `keycloak_org` argument.
- Seeding drops its own `link_changemaker_to_proposal`; use the client function of the same name.

Other changes:

- `ChangemakerFieldValueBatchNotFoundError` and `TokenRequestError` can be imported from `pdc_api`.

## 0.3.0 (2026-11-18)

- The package is now type checked with mypy (including strict mode), pyrefly, and ty, so its `py.typed` marker is accurate. The testing helpers and seeding modules are fully annotated.
- The minimum versions are now `requests>=2.34`, `urllib3>=2`, and, for the `seeding` extra, `faker>=26`, the first releases that ship type information.
- `APISession(timeout=...)` accepts a float.
- `KeycloakAdmin.ensure_organization` raises `LookupError` if Keycloak creates an organization without returning its id.

## 0.2.1 (2026-11-12)

- `create_initiative` and `create_initiative_field_value` create an initiative and add a field value to it. `seed_initiative` and `seed_initiative_field_value` now call them.

## 0.2.0 (2026-11-09)

- `create_changemaker_source`, `create_changemaker_field_value_batch`, and `create_changemaker_field_value` write a changemaker's own field values.
- Seeding drops `seed_changemaker_field_value_batch` and `seed_changemaker_field_value`; use the client functions above.
- `APISession` retries a GET or HEAD up to three times, with backoff, on a 502, 503, or 504 or a dropped connection. Other methods never retry.
- `SeededProposalBundle.changemaker` may be `None`, for a proposal seeded without a changemaker.

## 0.1.0 (2026-11-09)

The first release.

- Models generated from the PDC API spec labeled 0.42.0, downloaded 2026-11-06, including the `User` fields `syncedFromKeycloakAt` and `disabledAt`, and `UserSyncTask`.
- `APISession` with bearer auth, URL building, and one exception class per HTTP error status.
- `KeycloakClientCredentialsProvider` for service-account access.
- Read functions for changemakers, funders, data providers, proposals, initiatives, application forms, organizations, field values, and base fields, plus `get_bundle_page` for paginated reads.
- `get_application_form_by_name` returns the first application form with a given name, and raises `ApplicationFormNotFoundError` when there is none.
- `session` is positional and every other argument keyword-only, across all functions.
- Write functions for proposals, proposal versions, changemaker-proposal links, and file uploads.
- Full create, read, update, and delete support for permission grants and default permission grants.
- Optional `testing` and `seeding` extras.
