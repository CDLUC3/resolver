"""FastAPI router implementing identifier resolver functionality.
"""
import contextlib
import typing
import fastapi
import sqlalchemy
import sqlalchemy.orm
import rslv.lib_rslv.piddefine
import rslv.config

engine = None
settings = rslv.config.settings


@contextlib.asynccontextmanager
async def resolver_lifespan(app: fastapi.FastAPI):
    global engine
    engine = sqlalchemy.create_engine(settings.db_connection_string, pool_pre_ping=True)
    # The pid config database must already exist and be populated.
    # rslv.lib_rslv.pidconfig.create_database(engine)
    yield
    # Shutdown the engine when done.
    engine.dispose()


def create_pidconfig_repository() -> (
    typing.Iterator[rslv.lib_rslv.piddefine.PidDefinitionCatalog]
):
    session = sqlalchemy.orm.sessionmaker(bind=engine)()
    pid_config = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
    try:
        yield pid_config
    except Exception:
        session.rollback()
    finally:
        session.close()


router = fastapi.APIRouter(
    tags=["resolve"],
    # Note, this lifespan is never used! See https://github.com/tiangolo/fastapi/discussions/9664
    # Instead, add lifespan to the app startup.
    # lifespan=resolver_lifespan
)


@router.get(
    "/.info/{identifier:path}",
    summary="Retrieve information about the provided identifier.",
)
def get_info(
    request: fastapi.Request,
    identifier: typing.Optional[str] = None,
    pid_config: rslv.lib_rslv.piddefine.PidDefinitionCatalog = fastapi.Depends(
        create_pidconfig_repository
    ),
):
    request_url = str(request.url)
    raw_identifier = request_url[request_url.find(identifier) :]
    pid_parts, definition = pid_config.parse(raw_identifier)
    if definition is not None:
        pid_parts["target"] = definition.target.format(**pid_parts)
        pid_parts["canonical"] = definition.canonical.format(**pid_parts)
        pid_parts["status_code"] = definition.http_code
        pid_parts["properties"] = definition.properties
    return pid_parts


@router.get(
    "/{identifier:path}",
    summary="Redirect to the identified resource or present resolver information.",
)
def get_resolve(
    request: fastapi.Request,
    identifier: typing.Optional[str] = None,
    pid_config: rslv.lib_rslv.piddefine.PidDefinitionCatalog = fastapi.Depends(
        create_pidconfig_repository
    ),
):
    # ARK resolvers have wierd behavior of providing an
    # introspection ("inflection") when the URL ends with
    # "?", "??", or "?info". Need to examine the raw URL
    # to determine these.
    request_url = str(request.url)
    for check in ("?", "??", "?info"):
        if request_url.endswith(check):
            return get_info(request, identifier, pid_config=pid_config)
    # Get the raw identifier, i.e. the identifier with any accoutrements
    raw_identifier = request_url[request_url.find(identifier) :]
    pid_parts, definition = pid_config.parse(raw_identifier)
    if definition is not None:
        pid_parts["target"] = definition.target.format(**pid_parts)
        pid_parts["canonical"] = definition.canonical.format(**pid_parts)
        pid_parts["status_code"] = definition.http_code
        return fastapi.responses.RedirectResponse(
            pid_parts["target"],
            status_code=pid_parts["status_code"]
        )
    return pid_parts
