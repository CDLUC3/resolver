"""
`rslv` - General purpose identifier resolver service

This software is developed with support from the [California Digital Library](https://cdlib.org/).

This software implements a general purpose identifier resolver. Given an identifier string,
it will parse the identifier, locate a corresponding definition, and either present information
about the identifier or redirect the user to the registered target.
"""
import contextlib
import functools
import typing

import fastapi
import fastapi.responses
import fastapi.middleware.cors
import fastapi.staticfiles
import starlette.templating
import jinja2
import sqlalchemy
import rslv
import rslv.config
import rslv.log_middleware
import rslv.routers.resolver

@functools.lru_cache(maxsize=None)
def get_engine(dbcnstr: str) -> sqlalchemy.engine.base.Engine:
    return sqlalchemy.create_engine(dbcnstr, pool_pre_ping=True)

@contextlib.contextmanager
def get_dbsession(dbengine) -> typing.Iterator[sqlalchemy.orm.Session]:
    dbsession = sqlalchemy.orm.sessionmaker(bind=dbengine)()
    try:
        yield dbsession
    except Exception:
        dbsession.rollback()
        raise
    finally:
        dbsession.close()

@contextlib.asynccontextmanager
async def dbengine_lifespan(app: fastapi):
    dbcnstr = app.state.settings.db_connection_string
    app.state.dbengine = get_engine(dbcnstr)
    yield
    if app.state.dbengine is not None:
        app.state.dbengine.dispose()

def create_app() -> fastapi.FastAPI:

    settings = rslv.config.load_settings()

    # Setup access logging
    L = rslv.log_middleware.get_logger("rslv", log_filename=settings.log_filename)

    # Intialize the application
    app = fastapi.FastAPI(
        title="RSLV",
        description=__doc__,
        version=rslv.__version__,
        contact={"name": "Dave Vieglais", "url": "https://github.com/datadavev/"},
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/license/mit/",
        },
        lifespan=dbengine_lifespan,
        openapi_url="/api/v1/openapi.json",
        docs_url="/api",
    )

    app.state.settings = settings

    app.add_middleware(
        rslv.log_middleware.LogMiddleware,
        logger=L,
    )

    @app.middleware("http")
    async def add_db_session_middleware(request: fastapi.Request, call_next):
        with get_dbsession(request.app.state.dbengine) as dbsession:
            request.state.dbsession = dbsession
            response = await call_next(request)
            return response

    # Enables CORS for UIs on different domains
    app.add_middleware(
        fastapi.middleware.cors.CORSMiddleware,
        allow_origins= settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*", ],
        allow_headers=["*", ],
    )

    # static files and templates
    app.mount(
        "/static",
        fastapi.staticfiles.StaticFiles(directory=settings.static_dir),
        name="static",
    )

    templates = starlette.templating.Jinja2Templates(
        directory=settings.template_dir,
        loader=jinja2.ChoiceLoader(
            [
                jinja2.FileSystemLoader(settings.template_dir),
                jinja2.PackageLoader("rslv", "templates"),
            ]
        )
    )
    app.state.templates = templates

    @app.get("/", include_in_schema=False)
    async def redirect_docs(request:fastapi.Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/favicon.ico", include_in_schema=False)
    async def get_favicon():
        raise fastapi.HTTPException(status_code=404, detail="Not found")

    app.include_router(rslv.routers.resolver.router)
    return app


app = create_app()

if __name__ == "__main__":
    try:
        import uvicorn
        settings = rslv.config.load_settings()
        uvicorn.run(
            "app:app",
            port = settings.port,
            host = settings.host,
            reload=True
        )
    except ImportError as e:
        print("Unable to run as uvicorn is not available.")
        print(e)
