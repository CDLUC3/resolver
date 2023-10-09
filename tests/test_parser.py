"""
Tests for parsing identifiers to their components.
"""
import pytest
import sqlalchemy
import sqlalchemy.orm
import rslv.lib_rslv.piddefine

# In memory database for testing
db_connection_string = "sqlite://"
#db_connection_string = "sqlite:///test_data/cfg.sqlite"
engine = sqlalchemy.create_engine(db_connection_string, pool_pre_ping=True, echo=False)
rslv.lib_rslv.piddefine.clear_database(engine)
rslv.lib_rslv.piddefine.create_database(engine, "test")


def get_session():
    return sqlalchemy.orm.sessionmaker(bind=engine)()


def setup_config():
    def do_add(cfg, entry):
        result = cfg.add(entry)
        print(f"### Added: {result}")

    session = get_session()
    cfg = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
    try:
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinitionSQL(
            scheme="DEFAULT",
            properties={"tag":0},
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinitionSQL(
            scheme="ark",
            properties={"tag": 1},
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinitionSQL(
            scheme="ark",
            prefix="99999",
            properties={"tag": 2},
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinitionSQL(
            scheme="ark",
            prefix="99999",
            value="fk4",
            properties={"tag": 3},
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinitionSQL(
            scheme="ark",
            prefix="99999",
            value="fk",
            properties={"tag": 4},
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinitionSQL(
            scheme="ark",
            prefix="example",
            synonym_for="ark:99999",
            properties={"tag": 5},
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinitionSQL(
            scheme="bark",
            synonym_for="ark:",
            properties={"tag": 6},
        ))
        cfg.refresh_metadata()
    finally:
        session.close()


setup_config()


parse_cases = (
    (
        "base:test",
        None
    ),
    (
        "ark:foo",
        {"scheme":"ark", "prefix": "", "value":"", "tag":1}
    ),
    (
        "ark:99999",
        {"scheme": "ark", "prefix": "99999", "value":"", "tag":2}
    ),
    (
        "ark:99999/foo",
        {"scheme": "ark", "prefix": "99999", "value":"", "tag":2}
    ),
    (
        "ark:example/foo",
        {"scheme": "ark", "prefix": "99999", "value":"", "tag":2}
    ),
    (
        "ark:99999/fk44",
        {"scheme": "ark", "prefix": "99999", "value": "fk4", "tag":3}
    ),
    (
        "ark:99999/fkfoo",
        {"scheme": "ark", "prefix": "99999", "value": "fk", "tag":4}
    ),
    (
        "ark:99999/fk44wlr;jglerig",
        {"scheme": "ark", "prefix": "99999", "value": "fk4", "tag": 3}
    ),
    (
        "bark:99999/fk44wlr;jglerig",
        {"scheme": "ark", "prefix": "99999", "value": "fk4", "tag":3}
    ),
)

@pytest.mark.parametrize("test,expected", parse_cases)
def test_parse(test, expected):
    session = get_session()
    cfg = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
    try:
        parts, definition = cfg.parse(test)
        if expected is None:
            assert definition is None
        else:
            assert definition.scheme == expected["scheme"]
            assert definition.prefix == expected["prefix"]
            assert definition.value == expected.get("value")
            assert definition.properties.get("tag") == expected.get("tag")
    finally:
        session.close()


@pytest.mark.parametrize("test,expected", parse_cases)
def test_parse_struct(test, expected):
    session = get_session()
    cfg = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
    try:
        ppid = rslv.lib_rslv.ParsedPID(pid=test)
        ppid.split()
        definition = cfg.get_as_definition(ppid, resolve_synonym=True)
        if expected is None:
            assert definition is None
        else:
            assert definition.scheme == expected["scheme"]
            assert definition.prefix == expected["prefix"]
            assert definition.value == expected.get("value")
            assert definition.properties.get("tag") == expected.get("tag")
    finally:
        session.close()
