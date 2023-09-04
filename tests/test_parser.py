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
    cfg = rslv.lib_rslv.piddefine.SQLPidConfig(session)
    try:
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinition(
            scheme="DEFAULT",
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinition(
            scheme="ark",
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinition(
            scheme="ark",
            prefix="99999",
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinition(
            scheme="ark",
            prefix="99999",
            value="fk4"
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinition(
            scheme="ark",
            prefix="99999",
            value="fk"
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinition(
            scheme="ark",
            prefix="example",
            synonym_for="ark:99999"
        ))
        do_add(cfg, rslv.lib_rslv.piddefine.PidDefinition(
            scheme="bark",
            synonym_for="ark:"
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
        {"scheme":"ark", "prefix": ""}
    ),
    (
        "ark:99999",
        {"scheme": "ark", "prefix": "99999"}
    ),
    (
        "ark:99999/foo",
        {"scheme": "ark", "prefix": "99999", "value":""}
    ),
    (
        "ark:example/foo",
        {"scheme": "ark", "prefix": "99999", "value":""}
    ),
    (
        "ark:99999/fk44",
        {"scheme": "ark", "prefix": "99999", "value": "fk4"}
    ),
    (
        "ark:99999/fkfoo",
        {"scheme": "ark", "prefix": "99999", "value": "fk"}
    ),
    (
        "ark:99999/fk44wlr;jglerig",
        {"scheme": "ark", "prefix": "99999", "value": "fk4"}
    ),
    (
        "bark:99999/fk44wlr;jglerig",
        {"scheme": "ark", "prefix": "99999", "value": "fk4"}
    ),
)

@pytest.mark.parametrize("test,expected", parse_cases)
def test_parse(test, expected):
    session = get_session()
    cfg = rslv.lib_rslv.piddefine.SQLPidConfig(session)
    try:
        parts, definition = cfg.parse(test)
        if expected is None:
            assert definition is None
        else:
            assert definition.scheme == expected["scheme"]
            assert definition.prefix == expected["prefix"]
    finally:
        session.close()
