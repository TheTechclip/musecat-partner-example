"""Server-side API playground: fixed issuer, documented routes, no browser tokens."""

import json
import mimetypes
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid

from werkzeug.utils import secure_filename

from flask import Blueprint, current_app, jsonify, render_template, request

from .api_examples import OPERATIONS, SPEC, curl_example, resolve, select_media
from .client import authorized_link, verify_link
from .common import NoRedirect, ProtocolError, require_csrf, require_user

bp = Blueprint("explorer", __name__)


@bp.app_context_processor
def examples_context():
    return {
        "resolve": resolve,
        "curl_example": lambda operation: curl_example(
            operation, current_app.config["MUSECAT_ISSUER"]
        ),
    }


@bp.before_request
def upload_limit():
    if request.endpoint == "explorer.run":
        request.max_content_length = 160_000_000


@bp.get("/api-examples")
def index():
    require_user()
    selected = OPERATIONS.get(request.args.get("operation", ""))
    if selected:
        selected = select_media(selected, request.args.get("media"))
    return render_template(
        "api-examples.html",
        operations=OPERATIONS.values(),
        selected=selected,
        result=None,
    )


@bp.get("/api-examples/openapi.json")
def openapi():
    return jsonify(SPEC)


@bp.post("/api-examples/run")
def run():
    require_csrf()
    require_user()
    operation = OPERATIONS.get(request.form.get("operation", ""))
    if not operation or not operation["runnable"]:
        raise ProtocolError("example_not_runnable")
    media = request.form.get("media", operation["media"])
    if media and media not in operation["request_content"]:
        raise ProtocolError("unsupported_example_media")
    operation = select_media(operation, media)
    if (
        operation["method"] not in ("GET", "HEAD")
        and request.form.get("confirm") != operation["method"]
    ):
        raise ProtocolError("explicit_mutation_confirmation_required")
    path = operation["path"]
    query = []
    extra_headers = {}
    for raw in operation["parameters"]:
        parameter = resolve(raw)
        value = request.form.get("param:" + parameter["name"], "").strip()
        if parameter.get("required") and not value:
            raise ProtocolError("required_parameter_missing")
        if not value:
            continue
        if parameter["in"] == "path":
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
                raise ProtocolError("invalid_path_parameter")
            path = path.replace("{" + parameter["name"] + "}", value)
        elif parameter["in"] == "query":
            schema = resolve(parameter.get("schema", {}))
            values = (
                [part.strip() for part in value.split(",")]
                if schema.get("type") == "array" and parameter.get("explode", True)
                else [value]
            )
            query.extend((parameter["name"], part) for part in values)
        elif parameter["in"] == "header":
            name = parameter["name"]
            if (
                name.lower()
                in ("authorization", "host", "cookie", "content-length", "content-type")
                or "\r" in value
                or "\n" in value
            ):
                raise ProtocolError("invalid_example_header")
            extra_headers[name] = value
    if "{" in path:
        raise ProtocolError("required_parameter_missing")
    if query:
        path += "?" + urllib.parse.urlencode(query)
    headers = {"Accept": "application/json", **extra_headers}
    link = None
    if operation["authenticated"]:
        uid, link = authorized_link()
        headers["Authorization"] = "Bearer " + link["access"]
    body = None
    if operation["media"]:
        try:
            values = json.loads(request.form.get("body", "{}"))
        except ValueError:
            raise ProtocolError("invalid_json_body") from None
        media = operation["media"]
        if media == "multipart/form-data":
            if not isinstance(values, dict):
                raise ProtocolError("invalid_multipart_fields")
            boundary = "sample-" + uuid.uuid4().hex
            chunks = []
            for key, value in values.items():
                if not re.fullmatch(r"[A-Za-z0-9_\[\]-]{1,100}", key):
                    raise ProtocolError("invalid_multipart_field")
                if value == "<UPLOAD_FILE>" or value == ["<UPLOAD_FILE>"]:
                    continue
                chunks.append(
                    (
                        f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n'
                        + (value if isinstance(value, str) else json.dumps(value))
                        + "\r\n"
                    ).encode()
                )
            properties = resolve(operation["schema"]).get("properties", {})
            if sum(len(uploads) for _, uploads in request.files.lists()) > 10:
                raise ProtocolError("too_many_uploads")
            for key, uploads in request.files.lists():
                schema = resolve(properties.get(key, {}))
                item = resolve(schema.get("items", {}))
                if schema.get("format") != "binary" and item.get("format") != "binary":
                    raise ProtocolError("invalid_upload_field")
                if len(uploads) > (
                    schema.get("maxItems", 10) if schema.get("type") == "array" else 1
                ):
                    raise ProtocolError("too_many_uploads")
                for upload in uploads:
                    content = upload.read(15_000_001)
                    if len(content) > 15_000_000:
                        raise ProtocolError("upload_too_large", 413)
                    filename = secure_filename(upload.filename or "") or "upload"
                    content_type = (
                        mimetypes.guess_type(filename)[0] or "application/octet-stream"
                    )
                    chunks.append(
                        f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'.encode()
                        + content
                        + b"\r\n"
                    )
            body = b"".join(chunks) + f"--{boundary}--\r\n".encode()
            headers["Content-Type"] = media + "; boundary=" + boundary
        elif media == "application/x-www-form-urlencoded":
            if not isinstance(values, dict):
                raise ProtocolError("invalid_form_body")
            body = urllib.parse.urlencode(values).encode()
            headers["Content-Type"] = media
        elif media == "application/json":
            body = json.dumps(values).encode()
            headers["Content-Type"] = media
        else:
            raise ProtocolError("unsupported_example_media")
    url = current_app.config["MUSECAT_ISSUER"] + path
    try:
        response = urllib.request.build_opener(NoRedirect).open(
            urllib.request.Request(
                url, data=body, headers=headers, method=operation["method"]
            ),
            timeout=15,
        )
    except urllib.error.HTTPError as error:
        response = error
    except urllib.error.URLError:
        raise ProtocolError("musecat_request_failed", 502) from None
    with response:
        raw = response.read(1_048_577)
        if len(raw) > 1_048_576:
            result = {"status": response.code, "error": "response_too_large"}
        elif "json" in response.headers.get("Content-Type", ""):
            try:
                result = {
                    "status": response.code,
                    "body": json.loads(raw) if raw else None,
                }
            except ValueError:
                result = {"status": response.code, "error": "invalid_json_response"}
        else:
            result = {
                "status": response.code,
                "content_type": response.headers.get("Content-Type"),
                "bytes": len(raw),
            }
    if link:
        verify_link(uid, link)
    return render_template(
        "api-examples.html",
        operations=OPERATIONS.values(),
        selected=operation,
        result=result,
    )
