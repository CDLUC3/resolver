"""
Tests for parsing identifiers to their components.
"""
import pytest
import sqlalchemy
import sqlalchemy.orm
import rslv.lib_rslv.piddefine

# In memory database for testing
db_connection_string = "sqlite://"
# db_connection_string = "sqlite:///test_data/cfg.sqlite"
engine = sqlalchemy.create_engine(db_connection_string, pool_pre_ping=True, echo=False)
rslv.lib_rslv.piddefine.clear_database(engine)
rslv.lib_rslv.piddefine.create_database(engine, "test")


def get_session():
    return sqlalchemy.orm.sessionmaker(bind=engine)()


def setup_config():
    def do_add(cfg, entry):
        result = cfg.add(entry)
        print(f"### Added: {result}")

    with rslv.lib_rslv.piddefine.get_catalog(engine) as cfg:
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="DEFAULT",
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark",
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark",
                prefix="99999",
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark", prefix="99999", value="fk4"
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark", prefix="99999", value="fk"
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark", prefix="example", synonym_for="ark:99999"
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(scheme="bark", synonym_for="ark:"),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark", prefix="12345", value="up", properties={"name": "Frank"}
            ),
        )
        do_add(
            cfg,
            rslv.lib_rslv.piddefine.PidDefinition(
                scheme="ark", prefix="12345", value="nostrip",
                properties={"name": "Frank", "strip_hyphens":False}
            ),
        )
        cfg.refresh_metadata()


setup_config()


parse_cases = (
    ("base:test", None),
    ("ark:foo", {"scheme": "ark", "prefix": ""}),
    ("ark:99999", {"scheme": "ark", "prefix": "99999"}),
    ("ark:99999/foo", {"scheme": "ark", "prefix": "99999", "value": ""}),
    ("ark:example/foo", {"scheme": "ark", "prefix": "99999", "value": ""}),
    ("ark:99999/fk44", {"scheme": "ark", "prefix": "99999", "value": "fk4"}),
    ("ark:99999/fkfoo", {"scheme": "ark", "prefix": "99999", "value": "fk"}),
    ("ark:99999/fk44wlr;jglerig", {"scheme": "ark", "prefix": "99999", "value": "fk4"}),
    (
        "bark:99999/fk44wlr;jglerig",
        {"scheme": "ark", "prefix": "99999", "value": "fk4"},
    ),
    (
        "ark:12345/nostrip-test",
        {"scheme": "ark", "prefix": "12345", "value": "nostrip", "suffix":"-test"},
    )
)


@pytest.mark.parametrize("test,expected", parse_cases)
def test_parse(test, expected):
    with rslv.lib_rslv.piddefine.get_catalog(engine) as cfg:
        parts, definition = cfg.parse(test)
        if expected is None:
            assert definition is None
        else:
            assert definition.scheme == expected["scheme"]
            assert definition.prefix == expected["prefix"]
            assert definition.value == expected.get("value", '')


def test_update():
    with rslv.lib_rslv.piddefine.get_catalog(engine) as cfg:
        revised_entry = rslv.lib_rslv.piddefine.PidDefinition(
            scheme="ark", prefix="12345", value="up", properties={"name": "Frank"}
        )
        revised_entry.uniq = rslv.lib_rslv.piddefine.calculate_definition_uniq(
            revised_entry.scheme, revised_entry.prefix, revised_entry.value
        )
        n = cfg.update(revised_entry)
        assert n == 0
        revised_entry = None
        revised_entry = rslv.lib_rslv.piddefine.PidDefinition(
            scheme="ark", prefix="12345", value="up", properties={"name": "Henry"}
        )
        revised_entry.uniq = rslv.lib_rslv.piddefine.calculate_definition_uniq(
            revised_entry.scheme, revised_entry.prefix, revised_entry.value
        )
        n = cfg.update(revised_entry)
        assert n == 1
        e = cfg.get_by_uniq(revised_entry.uniq)
        assert e.properties == revised_entry.properties
