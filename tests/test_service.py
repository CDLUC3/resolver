import json
import logging
import os
import fastapi.testclient
import sys
import pytest
import sqlalchemy
import sqlalchemy.orm


# Set configuration overrides before imort app
os.environ["RSLV_JSON_LOGGING"] = "0"
os.environ["RSLV_DB_CONNECTION_STRING"] = "sqlite:///test.db"
os.environ["RSLV_SERVICE_PATTERN"] = "(^https?://testserver/)|(^https?://example.com/)"

import rslv.app
import rslv.config
import rslv.lib_rslv.piddefine

L = logging.getLogger()
L.setLevel(logging.DEBUG)
L.addHandler(logging.StreamHandler(sys.stderr))

#settings = rslv.config.load_settings()
settings = rslv.app.app.state.settings

engine = sqlalchemy.create_engine(settings.db_connection_string, pool_pre_ping=True, echo=False)
rslv.lib_rslv.piddefine.clear_database(engine)
rslv.lib_rslv.piddefine.create_database(engine, "test")

rslv.app.app.state.dbengine = engine

def get_session():
    return sqlalchemy.orm.sessionmaker(bind=engine)()

def setup_config():
    def do_add(cfg, entry):
        result = cfg.add(entry)
        L.info(f"### Added: {result}")

    session = get_session()
    cfg = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
    try:
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="DEFAULT",
                properties={"tag": 0},
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark",
                target="https://example.com/${pid}",
                canonical="ark:/${prefix}/${value}",
                properties={"tag": 1},
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark",
                prefix="99999",
                target="https://example.99999.com/info/${content}",
                properties={"tag": 2},
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark",
                prefix="99999",
                value="fk4",
                target="https://fk4.example.com/${suffix}",
                properties={"tag": 3},
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark",
                prefix="99999",
                value="fk",
                target="http://fk.example.com/${pid}",
                properties={"tag": 4},
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark",
                prefix="example",
                synonym_for="ark:99999",
                target="/.info/ark:${content}",
                properties={"tag": 5},
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="bark",
                synonym_for="ark:",
                properties={"tag": 6},
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="purl",
                target="http://purl.org/${content}",
                properties={"tag": 8}
            ),
        )
        cfg.refresh_metadata()
    finally:
        session.close()

setup_config()



info_cases = (
    ("ark:", {"uniq":"ark:", "tag":1}),
    ("ark:99999", {"uniq":"ark:99999", "tag":2}),
    ("bark:99999", {"uniq":"bark:", "tag":6}),
)

#@pytest.mark.parametrize("test,expected", info_cases)
#def test_info_schemes(test, expected):
#    client = fastapi.testclient.TestClient(rslv.app.app)
#    response = client.get(f"/.info/{test}")
#    _match = response.json()
#    L.info(json.dumps(_match, indent=2))
#    assert _match.get("definition",{}).get("uniq",None) == expected["uniq"]
#    assert _match.get("properties", {}).get("tag", None) == expected["tag"]
#    assert response.status_code == 200


resolve_cases = (
    ("ark:", {"target":"https://example.com/ark:", "status":200, "prefixes":["99999","example",]}),
    ("ARK:", {"target":"https://example.com/ARK:", "status":200}),
    ("ark:99999", {"target":"https://example.99999.com/info/99999", "status":200, "values": ["fk", "fk4",]}),
    ("ark:99999/foo", {"target":"https://example.99999.com/info/99999/foo", "status":302}),
    ("bark:99999/hhdd", {"target":"https://example.99999.com/info/99999/hhdd", "status": 302}),
    ("ark:99999/fkhhdd", {"target": "http://fk.example.com/ark:99999/fkhhdd", "status": 302}),
    ("ark:99999/fkhhdd?info", {"target": "http://fk.example.com/ark:99999/fkhhdd", "status": 200, "tag": 4}),
    ("ark:99999/fk", {"target": "http://fk.example.com/ark:99999/fk", "status": 200}),
    ("ark:99999/fk4", {"target": "https://fk4.example.com/", "status": 200}),
    ("ark:99999/fk4foo", {"target": "https://fk4.example.com/foo", "status": 302}),
    ("purl:dc/terms/creator", {"target": "http://purl.org/dc/terms/creator", "status": 302, "tag": 4}),
    ("purl:dc/terms/creator??", {"target": "http://purl.org/dc/terms/creator", "status": 200, "tag": 8}),
    ("purl:dc/terms/creator?info", {"target": "http://purl.org/dc/terms/creator", "status": 200, "tag": 8}),
    ("http://testserver/ark:99999/hhdd", {"target": "https://example.99999.com/info/99999/hhdd", "status": 302}),
    ("http://example.com/ark:99999/hhdd", {"target": "https://example.99999.com/info/99999/hhdd", "status": 302}),
    ("ark:12345/up", {"target":"https://example.com/ark:12345/up", "status": 302}),
    ("ark:12345/up?info", {"target":"https://example.com/ark:12345/up", "status": 200}),
    ("ark:/12345", {"target": "https://example.com/ark:/12345", "status": 200}),
    ("ark:12345", {"target": "https://example.com/ark:12345", "status": 200}),
)

@pytest.mark.parametrize("test,expected", resolve_cases)
def test_resolve_schemes(test, expected):
    client = fastapi.testclient.TestClient(rslv.app.app, follow_redirects=False)
    response = client.get(f"/{test}")
    _match = response.json()
    L.info(json.dumps(_match, indent=2))
    assert response.status_code == expected["status"]
    if response.status_code == 200:
        assert _match["target"] == expected["target"]
        if "values" in expected:
            for v in expected["values"]:
                assert v in _match["definition"]["values"]
        if "prefixes" in expected:
            for v in expected["prefixes"]:
                assert v in _match["definition"]["prefixes"]
    else:
        assert response.headers.get("location") == expected["target"]
