"""FastAPI router implementing identifier resolver functionality.
"""
import dataclasses
import re
import string
import typing
import urllib.parse
import fastapi
import werkzeug.http
import werkzeug.datastructures
import rslv.lib_rslv.piddefine
import rslv.config


router = fastapi.APIRouter(
    tags=["resolve"],
    # Note, this lifespan is never used! See https://github.com/tiangolo/fastapi/discussions/9664
    # Instead, add lifespan to the app startup.
    # lifespan=resolver_lifespan
)


def pid_format(parts, template):
    """Given a dict of identifier parts and a template, return the filled template.
    """
    # Quick hack to avoid "None" appearing in generated string.
    if template is None:
        template = "/.info/${pid}"
    _parts = {}
    for k, v in parts.items():
        if v is None:
            v = ""
        _parts[k] = v
    return string.Template(template).substitute(_parts)


def adjust_response_status_code_for_method(request:fastapi.Request, status_code:int) -> int:
    """Adjust the status_code value to align with request method semantics.
    If request method is any of POST, PUT, DELETE, ensure a status code of 307 or 308 is returned.
    """
    if request.method in ["POST", "PUT", "DELETE"]:
        if status_code == 302:
            # temporary redirect
            return 307
        if status_code == 301:
            # permanent redirect
            return 308
    return status_code


@dataclasses.dataclass
class CleanedIdentifierRequest:
    original: str
    cleaned: typing.Optional[str] = None
    is_introspection: bool = False
    has_service_url: bool = False

    @classmethod
    def from_request_url(cls, request_url: str, app_extracted: str, service_pattern:typing.Optional[str] = None) -> 'CleanedIdentifierRequest':
        """Factory method creating an instance from a request URL and the APP pattern matched identifier string

        service_pattern is a regexp string used to match the service URL
        """
        cleaned = urllib.parse.unquote(app_extracted)
        cleaned = cleaned.lstrip(" /:.;,")
        has_service_url = False
        is_introspection = False
        if service_pattern is not None:
            (cleaned, n_subs) = re.subn(service_pattern, "", cleaned, count=1, flags=re.IGNORECASE)
            if n_subs > 0:
                has_service_url = True
        request_url = urllib.parse.unquote(request_url)
        requested_identifier = request_url[request_url.find(cleaned) :]
        _original = requested_identifier

        # ARK resolvers have behavior of returning an
        # introspection ("inflection") when the URL ends with
        # "?", "??", or "?info". It is necessary to examine the raw URL
        # to determine this since it is non-standard behavior.
        for check in ("??", "?info", "?", ):
            if request_url.endswith(check):
                if requested_identifier.endswith(check):
                    requested_identifier = requested_identifier[:-len(check)]
                is_introspection = True
                break
        return CleanedIdentifierRequest(original=_original, cleaned=requested_identifier, is_introspection=is_introspection, has_service_url=has_service_url)


@router.head(
    "/.info",
    summary="Retrieve information about the service.",
    response_class=rslv.routers.PrettyJSONResponse
)
@router.get(
    "/.info",
    summary="Retrieve information about the service.",
    response_class=rslv.routers.PrettyJSONResponse
)
def get_service_info(
    request: fastapi.Request,
    valid: bool = True
):
    pid_config = rslv.lib_rslv.piddefine.PidDefinitionCatalog(request.state.dbsession)
    schemes = pid_config.list_schemes(valid_targets_only=valid)
    return {
        "about": pid_config.get_metadata(),
        "api": "/api",
        "schemes": [s[0] for s in schemes],
    }


def handle_get_info(request: fastapi.Request, cleaned_identifier: CleanedIdentifierRequest):
    pid_config = rslv.lib_rslv.piddefine.PidDefinitionCatalog(request.state.dbsession)
    pid_parts, definition = pid_config.parse(cleaned_identifier.cleaned, resolve_synonym=False)
    # TODO: This is where a definition specific handler can be used for
    #   further processing of the PID, e.g. to remove hyphens from an ark.
    #   Basically, add a property to the definition that contains the name
    #   of a handler, then if set, load the handler and have it process the
    #   rendering of the PID.
    if definition is not None:
        pid_parts["target"] = pid_format(pid_parts, definition.target)
        pid_parts["canonical"] = pid_format(pid_parts, definition.canonical)
        pid_parts["status_code"] = adjust_response_status_code_for_method(request, definition.http_code)
        pid_parts["properties"] = definition.properties
        defn = {
            "uniq": definition.uniq,
            "scheme": definition.scheme,
            "prefix": definition.prefix,
            "value": definition.value,
            "target": definition.target,
            "canonical": definition.canonical,
            "synonym_for": definition.synonym_for,
            "http_code": definition.http_code
        }
        if pid_parts["prefix"] == "":
            prefixes = pid_config.list_prefixes(pid_parts["scheme"])
            defn["prefixes"] = [p[0] for p in prefixes]
        elif pid_parts["value"] in (
            "",
            None,
        ):
            values = pid_config.list_values(pid_parts["scheme"], pid_parts["prefix"])
            defn["values"] = [v[0] for v in values]
        pid_parts["definition"] = defn

        # if templates are available from the app, then
        # Response based on client Accept
        try:
            templates = request.app.state.templates
            accept = werkzeug.http.parse_accept_header(request.headers.get("Accept", "*/*"), werkzeug.datastructures.MIMEAccept)
            if accept.accept_html or accept.accept_xhtml:
                # Return HTML using template
                return templates.TemplateResponse(
                    "introspection.html",
                    {
                        "request": request,
                        "identifier": cleaned_identifier.cleaned,
                        "pid_parts": pid_parts,
                    }
                )
        except KeyError:
            pass
        return pid_parts
    pid_parts["error"] = f"No match was found for {cleaned_identifier.cleaned}"
    return fastapi.responses.JSONResponse(
        content=pid_parts,
        status_code=404
    )


@router.head(
    "/.info/{identifier:path}",
    summary="Retrieve information about the provided identifier.",
    response_class=rslv.routers.PrettyJSONResponse
)
@router.get(
    "/.info/{identifier:path}",
    summary="Retrieve information about the provided identifier.",
    response_class=rslv.routers.PrettyJSONResponse
)
@router.post(
    "/.info/{identifier:path}",
    summary="Retrieve information about the provided identifier.",
    response_class=rslv.routers.PrettyJSONResponse
)
@router.put(
    "/.info/{identifier:path}",
    summary="Retrieve information about the provided identifier.",
    response_class=rslv.routers.PrettyJSONResponse
)
@router.delete(
    "/.info/{identifier:path}",
    summary="Retrieve information about the provided identifier.",
    response_class=rslv.routers.PrettyJSONResponse
)
def get_info(
    request: fastapi.Request,
    identifier: typing.Optional[str] = None,
):
    """
    Retrieve information about the identifier provided on the path.

    request.state.dbsession is expected to be a DBSession object that will be used
    by the PidDefinitionCatalog to retrieve identifier information from the catalog.

    """
    if not hasattr(request.app.state, "settings"):
        raise fastapi.HTTPException(status_code=500, detail="Settings are not accessible from handlers. Check server implementation.")
    if not hasattr(request.state, "dbsession"):
        raise fastapi.HTTPException(status_code=500, detail="No dbsession available. Check server configuration.")

    cleaned_identifier = CleanedIdentifierRequest.from_request_url(
        str(request.url),
        identifier,
        request.app.state.settings.service_pattern
    )

    return handle_get_info(request, cleaned_identifier)


@router.head(
    "/{identifier:path}",
    summary="Redirect to the identified resource or present resolver information.",
    response_class=rslv.routers.PrettyJSONResponse
)
@router.get(
    "/{identifier:path}",
    summary="Redirect to the identified resource or present resolver information.",
    response_class=rslv.routers.PrettyJSONResponse
)
@router.post(
    "/{identifier:path}",
    summary="Redirect to the identified resource or present resolver information.",
    response_class=rslv.routers.PrettyJSONResponse
)
@router.put(
    "/{identifier:path}",
    summary="Redirect to the identified resource or present resolver information.",
    response_class=rslv.routers.PrettyJSONResponse
)
@router.delete(
    "/{identifier:path}",
    summary="Redirect to the identified resource or present resolver information.",
    response_class=rslv.routers.PrettyJSONResponse
)
def get_resolve(
    request: fastapi.Request,
    identifier: typing.Optional[str] = None,
):
    '''
    Redirect to the identified resource or present identifier information.

    Args:
        request: The starlette / FastAPI request object
        identifier: The identifier from the URL pattern match.

    Returns:
        A HTTP response that either redirects client to registered target or presents information
        about the provided identifier.

    '''
    if not hasattr(request.app.state, "settings"):
        raise fastapi.HTTPException(status_code=500, detail="Settings are not accessible from handlers. Check server implementation.")
    if not hasattr(request.state, "dbsession"):
        raise fastapi.HTTPException(status_code=500, detail="No dbsession available. Check server configration.")

    # Clean up the identifier extracted from the request URL
    cleaned_identifier = CleanedIdentifierRequest.from_request_url(
        str(request.url),
        identifier,
        request.app.state.settings.service_pattern
    )

    # If the request was for introspection (inflection) use the info handler
    if cleaned_identifier.is_introspection:
        return handle_get_info(request, cleaned_identifier)

    # Get the identifier configuration catalog
    pid_config = rslv.lib_rslv.piddefine.PidDefinitionCatalog(request.state.dbsession)

    # Split the identifier string into components and find the best match from the catalog
    pid_parts, definition = pid_config.parse(cleaned_identifier.cleaned)
    # TODO: see above in get_info for PID handling with specific schemes.

    if definition is None:
        # Return a 404 response and include the pid parts in the body with a
        # message indicating not found
        pid_parts["error"] = f"No match was found for {cleaned_identifier.original}"
        return fastapi.responses.JSONResponse(
            content=pid_parts,
            status_code=404
        )
    # We have a match from the definition catalog.
    # Redirect the response, but include our gathered info in the body
    # to assist with debugging.
    response_status_code = adjust_response_status_code_for_method(request, definition.http_code)
    pid_parts["target"] = pid_format(pid_parts, definition.target)
    _target = pid_parts["target"]
    # If there's no value component in the PID, then return the information
    # this service has about the identifier.
    # TODO: Should this be checking the content portion instead of the value? That is, if the
    # content matches the definition content, then engage auto-introspection.
    if request.app.state.settings.auto_introspection and pid_parts["value"] in [None, ""]:
        return handle_get_info(request, cleaned_identifier)
    # If the PID value part matches the value part of the matched definition,
    # then return the definition information. This is sketchy behavior but included
    # here because it follows the legacy N2T behavior. It can be disabled through
    # the auto_introspection configuration boolean value.
    if request.app.state.settings.auto_introspection and pid_parts["value"] == definition.value:
        return handle_get_info(request, cleaned_identifier)
    # OK, past all the edge cases, redirect the client to the registered target.
    pid_parts["canonical"] = pid_format(pid_parts, definition.canonical)
    pid_parts["status_code"] = response_status_code
    headers = {"Location": _target}
    return fastapi.responses.JSONResponse(
        content=pid_parts,
        headers=headers,
        status_code=response_status_code,
    )

