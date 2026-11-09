import json
import sys
from pathlib import Path


# Organization marks its nullable roles required, and codegen drops "| None" on a required $ref.
def relax_organization_nullable_roles(spec: dict) -> None:
    org = spec["components"]["schemas"]["Organization"]
    roles = {"changemaker", "dataProvider", "funder"}
    org["required"] = [name for name in org.get("required", []) if name not in roles]


# Source is a oneOf over its related entity, which codegen renders as an opaque union; callers read it as one flat record.
def flatten_source(spec: dict) -> None:
    schemas = spec["components"]["schemas"]
    base = schemas["Source"]["allOf"][0]
    schemas["Source"] = {
        "type": "object",
        "description": base.get("description", ""),
        "properties": {
            "id": {"$ref": "#/components/schemas/id", "readOnly": True},
            "label": {"type": "string"},
            "createdAt": {"type": "string", "format": "date-time", "readOnly": True},
            "createdBy": {"type": "string", "format": "uuid", "readOnly": True},
            "dataProviderShortCode": {"type": ["string", "null"]},
            "dataProvider": {"anyOf": [{"$ref": "#/components/schemas/DataProvider"}, {"type": "null"}]},
            "funderShortCode": {"type": ["string", "null"]},
            "funder": {"anyOf": [{"$ref": "#/components/schemas/Funder"}, {"type": "null"}]},
            "changemakerId": {"type": ["number", "null"]},
            "changemaker": {"anyOf": [{"$ref": "#/components/schemas/ShallowChangemaker"}, {"type": "null"}]},
        },
        "required": ["id", "label", "createdAt"],
    }


# Codegen renders the grant oneOf as ~120 numbered classes; permission_grants.py models the union by hand.
def drop_permission_grant_schemas(spec: dict) -> None:
    schemas = spec["components"]["schemas"]
    for name in [key for key in schemas if "PermissionGrant" in key and "enum" not in schemas[key]]:
        del schemas[name]


# PDC adds permission scopes and verbs over time, and a strict enum here would fail every funder and changemaker parse.
def loosen_permissions_map(spec: dict) -> None:
    permissions_map = spec["components"]["schemas"]["PermissionsMap"]
    del permissions_map["propertyNames"]
    permissions_map["additionalProperties"] = {"type": "array", "items": {"type": "string"}}


# Since datamodel-code-generator 0.72 (koxudaxi/datamodel-code-generator#3664), the untyped Bundle.entries overrides each bundle's narrowed type.
def move_bundle_entries_onto_subclasses(spec: dict) -> None:
    schemas = spec["components"]["schemas"]
    bundle = schemas["Bundle"]
    description = bundle["properties"].pop("entries").get("description")
    bundle["required"] = [name for name in bundle.get("required", []) if name != "entries"]

    for schema in schemas.values():
        branches = schema.get("allOf") if isinstance(schema, dict) else None
        if not branches or {"$ref": "#/components/schemas/Bundle"} not in branches:
            continue
        for branch in branches:
            entries = branch.get("properties", {}).get("entries")
            if entries is not None:
                entries.setdefault("description", description)


# Codegen renders PresignedPost.fields as a model that would drop the dynamic S3 form fields.
def make_presigned_post_fields_freeform(spec: dict) -> None:
    props = spec["components"]["schemas"]["PresignedPost"]["properties"]
    props["fields"] = {"type": "object", "additionalProperties": {"type": "string"}}


# Bounds on id make codegen wrap nullable id references in an Id RootModel, and would reject ids if PDC moves to bigint.
def strip_id_numeric_bounds(spec: dict) -> None:
    id_schema = spec["components"]["schemas"]["id"]
    id_schema.pop("minimum", None)
    id_schema.pop("maximum", None)


# Proposal field values from before PDC migration 0021 (March 2024) have a null isValid the spec types as boolean.
def allow_null_is_valid(spec: dict) -> None:
    spec["components"]["schemas"]["FieldValueBase"]["properties"]["isValid"]["type"] = ["boolean", "null"]


# AnyUrl is not a str, so URLs like File.download_url would fail str fields and json.dumps.
def uri_strings_to_plain_str(spec: dict) -> None:

    def visit(node) -> None:
        if isinstance(node, dict):
            if node.get("format") in ("uri", "url", "uri-reference"):
                del node["format"]
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(spec["components"]["schemas"])


def _is_array(prop: dict) -> bool:
    type_ = prop.get("type")
    return type_ == "array" or (isinstance(type_, list) and "array" in type_)


# PDC omits optional collections it hides from the caller, such as Changemaker.fiscalSponsors; a missing collection means empty.
def default_arrays_to_empty(spec: dict) -> None:
    def visit(node) -> None:
        if isinstance(node, dict):
            props = node.get("properties")
            if isinstance(props, dict):
                required = node.get("required", [])
                for name, prop in props.items():
                    if isinstance(prop, dict) and _is_array(prop) and name not in required:
                        prop["default"] = []
            for key, value in node.items():
                if key != "example":
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(spec["components"]["schemas"])


# File creation responses carry presignedPost but no storage fields; reads carry downloadUrl but no presignedPost.
def relax_file_required(spec: dict) -> None:
    spec["components"]["schemas"]["File"]["required"] = ["id", "name"]


RULES = (
    relax_organization_nullable_roles,
    flatten_source,
    drop_permission_grant_schemas,
    loosen_permissions_map,
    move_bundle_entries_onto_subclasses,
    relax_file_required,
    make_presigned_post_fields_freeform,
    strip_id_numeric_bounds,
    allow_null_is_valid,
    uri_strings_to_plain_str,
    default_arrays_to_empty,
)


def preprocess(spec: dict) -> dict:
    for rule in RULES:
        rule(spec)
    return spec


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    spec = preprocess(json.loads(src.read_text()))
    dst.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
