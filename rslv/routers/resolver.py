"""FastAPI router implementing identifier resolver functionality.
"""
import contextlib
import string
import typing
import urllib.parse
import fastapi
import sqlalchemy
import sqlalchemy.orm
import rslv.lib_rslv.piddefine
import rslv.config

#settings = rslv.config.settings

#ENGINE = None


#def get_engine():
#    global ENGINE
#    if ENGINE is None:
#        ENGINE = sqlalchemy.create_engine(
#            settings.db_connection_string + "?mode=ro", pool_pre_ping=True
#        )
#    return ENGINE


#@contextlib.asynccontextmanager
#async def resolver_lifespan(app: fastapi.FastAPI):
#    engine = get_engine()
#    # The pid config database must already exist and be populated.
#    # rslv.lib_rslv.pidconfig.create_database(engine)
#    yield
#    # Shutdown the engine when done.
#    engine.dispose()


#def create_pidconfig_repository() -> (
#    typing.Iterator[rslv.lib_rslv.piddefine.PidDefinitionCatalog]
#):
#    # We need to get the engine here to support operation on serverless environments where
#    # the lifespan functionality is generally not supported.
#    engine = get_engine()
#    session = sqlalchemy.orm.sessionmaker(bind=engine)()
#    pid_config = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
#    try:
#        yield pid_config
#    except Exception:
#        session.rollback()
#    finally:
#        session.close()


router = fastapi.APIRouter(
    tags=["resolve"],
    # Note, this lifespan is never used! See https://github.com/tiangolo/fastapi/discussions/9664
    # Instead, add lifespan to the app startup.
    # lifespan=resolver_lifespan
)


def pid_format(parts, template):

    """Quick hack to avoid "None" appearing in generated string"""
    _parts = {}
    for k, v in parts.items():
        if v is None:
            v = ""
        _parts[k] = v
    return string.Template(template).substitute(_parts)
    #return template.format(**_parts)


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
def get_info(
    request: fastapi.Request,
    identifier: typing.Optional[str] = None,
):
    """
    Retrieve information about the identifier provided on the path.

    request.state.dbsession is expected to be a DBSession object that will be used
    by the PidDefinitionCatalog to retrieve identifier information from the catalog.

    """
    if not hasattr(request.state, "dbsession"):
        raise fastapi.HTTPException(status_code=500, detail="No dbsession available. Check server configration.")
    pid_config = rslv.lib_rslv.piddefine.PidDefinitionCatalog(request.state.dbsession)
    identifier = urllib.parse.unquote(identifier)
    identifier = identifier.lstrip(" /:.;,")
    # Nothing provided, return information about this service.
    if identifier in ("", "{identifier}"):
        return get_service_info(request)
    # Starlette or fastapi will split the value on the query part, so instead we grab the
    # raw request url and grab the full identifier string ourselves
    request_url = str(request.url)
    request_url = urllib.parse.unquote(request_url)
    # Grab the full identifier, starting with the fastapi parsed identifier string,
    # which will be equal to the start of the full identifier string in the url.
    raw_identifier = request_url[request_url.find(identifier) :]
    # Already in the info request, so discard ARK inflection request parts
    if raw_identifier.endswith("?info"):
        raw_identifier = raw_identifier[:-5]
    raw_identifier = raw_identifier.rstrip("?")
    # Parse the PID and retrieve the matching definition from the catalog
    pid_parts, definition = pid_config.parse(raw_identifier, resolve_synonym=False)
    # TODO: This is where a definition specific handler can be used for
    #   further processing of the PID, e.g. to remove hyphens from an ark.
    #   Basically, add a property to the definition that contains the name
    #   of a handler, then if set, load the handler and have it process the
    #   rendering of the PID.
    if definition is not None:
        pid_parts["target"] = pid_format(pid_parts, definition.target)
        pid_parts["canonical"] = pid_format(pid_parts, definition.canonical)
        pid_parts["status_code"] = definition.http_code
        pid_parts["properties"] = definition.properties
        defn = {
            "uniq": definition.uniq,
            "scheme": definition.scheme,
            "prefix": definition.prefix,
            "value": definition.value,
            "target": definition.target,
            "canonical": definition.canonical,
            "synonym_for": definition.synonym_for,
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
        return pid_parts
    pid_parts["error"] = f"No match was found for {raw_identifier}"
    return fastapi.responses.JSONResponse(
        content=pid_parts,
        status_code=404
    )


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
def get_resolve(
    request: fastapi.Request,
    identifier: typing.Optional[str] = None,
):
    if not hasattr(request.state, "dbsession"):
        raise fastapi.HTTPException(status_code=500, detail="No dbsession available. Check server configration.")
    pid_config = rslv.lib_rslv.piddefine.PidDefinitionCatalog(request.state.dbsession)
    # ARK resolvers have behavior of returning an
    # introspection ("inflection") when the URL ends with
    # "?", "??", or "?info". It is necessary to examine the raw URL
    # to determine this since it is non-standard behavior.
    request_url = str(request.url)
    for check in ("?", "??", "?info"):
        if request_url.endswith(check):
            identifier = identifier[: -len(check)]
            return get_info(request, identifier)
    # Get the raw identifier, i.e. the identifier with any accoutrements
    identifier = urllib.parse.unquote(identifier)
    request_url = urllib.parse.unquote(request_url)
    raw_identifier = request_url[request_url.find(identifier) :]
    pid_parts, definition = pid_config.parse(raw_identifier)
    # TODO: see above in get_info for PID handling with specific schemes.
    if definition is not None:
        # We have a match from the definition catalog.
        # Redirect the response, but include our gathered info in the body
        # to assist with debugging.
        pid_parts["target"] = pid_format(pid_parts, definition.target)
        pid_parts["canonical"] = pid_format(pid_parts, definition.canonical)
        pid_parts["status_code"] = definition.http_code
        headers = {"Location": pid_parts["target"]}
        return fastapi.responses.JSONResponse(
            content=pid_parts,
            headers=headers,
            status_code=pid_parts.get("status_code", 302),
        )
    # Return a 404 response and include the pid parts in the body with a
    # message indicating not found
    pid_parts["error"] = f"No match was found for {raw_identifier}"
    return fastapi.responses.JSONResponse(
        content=pid_parts,
        status_code=404
    )

