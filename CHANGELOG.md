# Changelog

This project follows [Semantic Versioning](https://semver.org). Until 1.0, a minor version may include breaking changes.

PDC does not bump its spec version for every API change, so each entry names the spec version and the date the spec was downloaded.

## Unreleased

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
