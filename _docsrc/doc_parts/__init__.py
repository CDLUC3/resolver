from py_markdown_table.markdown_table import markdown_table
import sqlalchemy
import rslv.lib_rslv
import rslv.lib_rslv.piddefine

EXAMPLE_PIDS = [
    "foo",
    "foo:1234",
    "foo:1234/bar",
    "ark:/12345/foo?baz",
    "doi:10.12345/foo?baz",
    "IGSN:AU1243",
    "orcid:0000-0002-5355-2576",
    "z017/biomodels.db:BIOMD0000000048",
    "ark:12148/btv1b8449691v/f29",
    "ark:/12148/btv1b8449691v/f29"
]

DEFINITIONS = [
    rslv.lib_rslv.piddefine.PidDefinition(
        scheme="ark",
        properties={"tag":1},
    ),
    rslv.lib_rslv.piddefine.PidDefinition(
        scheme="ark",
        prefix="99999",
        properties={"tag": 2},
    ),
    rslv.lib_rslv.piddefine.PidDefinition(
        scheme="ark",
        prefix="99999",
        value="fk4",
        properties={"tag": 3},
    ),
    rslv.lib_rslv.piddefine.PidDefinition(
        scheme="ark",
        prefix="99999",
        value="fk",
        properties={"tag": 4},
    ),
    rslv.lib_rslv.piddefine.PidDefinition(
        scheme="ark",
        prefix="example",
        synonym_for="ark:99999",
        properties={"tag": 5},
    ),
    rslv.lib_rslv.piddefine.PidDefinition(
        scheme="bark",
        synonym_for="ark:",
        properties={"tag": 6},
    ),
]

def initialize():
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    rslv.lib_rslv.piddefine.create_database(engine, "Examples")
    catalog = rslv.lib_rslv.piddefine.get_catalog(engine)
    for defn in DEFINITIONS:
        catalog.add_as_definition(defn)
    return engine


def split_examples():
    parsed = []
    for pid in EXAMPLE_PIDS:
        ppid = rslv.lib_rslv.ParsedPID(pid=pid)
        ppid.split()
        parsed.append(ppid.model_dump(mode="json", exclude={"clean_value", }))
    for p in parsed:
        for k,v in p.items():
            if v is None:
                p[k] = ""
            else:
                p[k] = f"`{v}`"
    print(markdown_table(parsed).set_params(row_sep='markdown', quote=False).get_markdown())

def definition_table():
    defns = []
    i = 0
    for defn in DEFINITIONS:
        i += 1
        defns.append({
            "Tag": f"`{defn.properties.get('tag')}`",
            "Scheme": f"`{defn.scheme}`",
            "Prefix": "` `" if defn.prefix is None or defn.prefix == '' else f"`{defn.prefix}`",
            "Value": "` `" if defn.value is None or defn.value == '' else f"`{defn.value}`",
            "Synonym_for": "` `" if defn.synonym_for is None else f"`{defn.synonym_for}`"
        })
    print(markdown_table(defns).set_params(row_sep='markdown', quote=False).get_markdown())


def defn_match_table(pids=EXAMPLE_PIDS):
    engine = initialize()
    catalog = rslv.lib_rslv.piddefine.get_catalog(engine)
    results = []
    for pid in pids:
        ppid = rslv.lib_rslv.ParsedPID(pid=pid)
        ppid.split()
        defn = catalog.get_as_definition(ppid, resolve_synonym=True)
        result = {
            "PID": f"`{pid}`",
            "Defn Tag": "" if defn is None else f"`{defn.properties.get('tag')}`"
        }
        results.append(result)
    print(markdown_table(results).set_params(row_sep='markdown', quote=False).get_markdown())

