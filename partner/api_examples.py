"""Examples derived from the checked-in official Developer OpenAPI snapshot."""

import json
import shlex
from pathlib import Path

SPEC = json.loads(Path(__file__).with_name("developer-openapi.json").read_text())
METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def resolve(value):
    if not isinstance(value, dict) or "$ref" not in value:
        return value
    pointer = value["$ref"]
    if not pointer.startswith("#/"):
        raise ValueError("Only bundled schema references are supported")
    result = SPEC
    for part in pointer[2:].split("/"):
        result = result[part.replace("~1", "/").replace("~0", "~")]
    return result


def example(schema, depth=0):
    schema = resolve(schema)
    if depth > 7 or not isinstance(schema, dict):
        return None
    for key in ("example", "default"):
        if key in schema:
            return schema[key]
    if schema.get("enum"):
        return schema["enum"][0]
    if schema.get("oneOf") or schema.get("anyOf"):
        return example((schema.get("oneOf") or schema["anyOf"])[0], depth + 1)
    if schema.get("allOf"):
        result = {}
        for part in schema["allOf"]:
            value = example(part, depth + 1)
            if isinstance(value, dict):
                result.update(value)
        return result
    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        return {
            key: example(value, depth + 1)
            for key, value in schema.get("properties", {}).items()
        }
    if kind == "array":
        return [example(schema.get("items", {}), depth + 1)]
    if kind == "integer" or kind == "number":
        return schema.get("minimum", 1)
    if kind == "boolean":
        return False
    return {
        "date": "2026-10-20",
        "date-time": "2026-10-20T00:00:00Z",
        "binary": "<UPLOAD_FILE>",
        "uri": "https://example.com",
    }.get(schema.get("format"), "<REPLACE>")


def operations():
    result = {}
    for path, route in SPEC["paths"].items():
        for method, operation in route.items():
            if method not in METHODS:
                continue
            key = method.upper() + " " + path
            parameters = [
                resolve(value)
                for value in route.get("parameters", [])
                + operation.get("parameters", [])
            ]
            request = resolve(operation.get("requestBody", {}))
            content = request.get("content", {})
            media = next(iter(content), "")
            schema = content.get(media, {}).get("schema", {})
            security = operation.get("security", SPEC.get("security", []))
            scopes = sorted(
                {
                    scope
                    for option in security
                    for scope in option.get("delegatedOAuth", [])
                }
            )
            runnable = path.startswith("/developer/v1/") and all(
                set(option).issubset({"delegatedOAuth"}) for option in security
            )
            public = (
                not security
                and method == "get"
                and path
                in {
                    "/.well-known/openid-configuration",
                    "/.well-known/oauth-authorization-server",
                    "/oauth/jwks",
                    "/developer/sign-in-with-musecat.md",
                }
            )
            result[key] = {
                "id": key,
                "method": method.upper(),
                "path": path,
                "summary": operation.get("summary", key),
                "description": operation.get("description", ""),
                "parameters": parameters,
                "media": media,
                "schema": schema,
                "request_content": content,
                "body_example": content.get(media, {}).get("example", example(schema))
                if content
                else None,
                "scopes": scopes,
                "security": security,
                "runnable": runnable or public,
                "authenticated": runnable,
                "responses": operation.get("responses", {}),
                "response_examples": {
                    code: {
                        media: entry.get("example", example(entry.get("schema", {})))
                        for media, entry in resolve(response).get("content", {}).items()
                    }
                    for code, response in operation.get("responses", {}).items()
                },
            }
    return result


OPERATIONS = operations()


def curl_example(operation, issuer):
    path = operation["path"]
    for parameter in operation["parameters"]:
        if parameter["in"] == "path":
            path = path.replace(
                "{" + parameter["name"] + "}", "<" + parameter["name"] + ">"
            )
    query = [
        parameter["name"] + "=<value>"
        for parameter in operation["parameters"]
        if parameter["in"] == "query"
    ]
    if query:
        path += "?" + "&".join(query)
    lines = ["curl --request " + operation["method"] + " " + shlex.quote(issuer + path)]
    schemes = {name for option in operation["security"] for name in option}
    if "delegatedOAuth" in schemes:
        lines.append('  --header "Authorization: Bearer ${MUSECAT_ACCESS_TOKEN}"')
    elif "oauthClientBasic" in schemes:
        lines.append('  --user "${MUSECAT_CLIENT_ID}:${MUSECAT_CLIENT_SECRET}"')
    elif "bearerAuth" in schemes:
        lines.append('  --header "Authorization: Bearer ${MUSECAT_SESSION_TOKEN}"')
    for parameter in operation["parameters"]:
        if parameter["in"] == "header" and parameter["name"].lower() != "authorization":
            lines.append("  --header " + shlex.quote(parameter["name"] + ": <value>"))
    if operation["media"] == "application/json":
        lines.append("  --header 'Content-Type: application/json'")
        lines.append(
            "  --data "
            + shlex.quote(json.dumps(operation["body_example"], ensure_ascii=False))
        )
    elif operation["media"] in (
        "multipart/form-data",
        "application/x-www-form-urlencoded",
    ):
        for key, value in (operation["body_example"] or {}).items():
            file = value == "<UPLOAD_FILE>" or value == ["<UPLOAD_FILE>"]
            encoded = value if isinstance(value, str) else json.dumps(value)
            argument = key + "=" + ("@/path/to/file" if file else encoded)
            lines.append(
                (
                    "  --form "
                    if operation["media"] == "multipart/form-data"
                    else "  --data-urlencode "
                )
                + shlex.quote(argument)
            )
    return " ".join(line.strip() for line in lines)


def select_media(operation, media=None):
    operation = dict(operation)
    content = operation["request_content"]
    selected = media if media in content else operation["media"]
    operation["media"] = selected
    schema = content.get(selected, {}).get("schema", {})
    operation["schema"] = schema
    operation["body_example"] = (
        content.get(selected, {}).get("example", example(schema)) if content else None
    )
    return operation
