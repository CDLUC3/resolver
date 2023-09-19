"""
Script for basic management of the pid configuration sqlite instance.
"""
import dataclasses
import json
import logging
import logging.config
import os.path
import sys
import click
import httpx
import sqlalchemy

import rslv.lib_rslv.n2tutils
import rslv.lib_rslv.piddefine
import rslv.config

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(name)s:%(levelname)s: %(message)s",
            "dateformat": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "": {
            "handlers": [
                "console",
            ],
            "level": "INFO",
            "propogate": False,
        },
    },
}

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "FATAL": logging.CRITICAL,
    "CRITICAL": logging.CRITICAL,
}


def get_logger():
    return logging.getLogger("rslv")


@click.group()
@click.pass_context
@click.option("-V", "--verbosity", default="ERROR", help="Logging level")
def main(ctx, verbosity):
    verbosity = verbosity.upper()
    logging_config["loggers"][""]["level"] = verbosity
    logging.config.dictConfig(logging_config)
    L = get_logger()
    ctx.ensure_object(dict)
    ctx.obj["engine"] = sqlalchemy.create_engine(
        rslv.config.settings.db_connection_string, pool_pre_ping=True
    )
    ctx.obj["L"] = L
    return 0


@main.command("initialize")
@click.pass_context
@click.argument("description")
def initialize_configuration(ctx, description):
    os.makedirs(os.path.join(rslv.config.BASE_FOLDER, "data"), exist_ok=True)
    rslv.lib_rslv.piddefine.create_database(ctx.obj["engine"], description)


@main.command("schemes")
@click.pass_context
def list_schemes(ctx):
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        schemes = definitions.list_schemes()
        scheme_list = [s[0] for s in schemes]
        print(json.dumps(scheme_list, indent=2))
    finally:
        session.close()


@main.command("prefixes")
@click.pass_context
@click.argument("scheme")
def list_prefixes(ctx, scheme):
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        prefixes = definitions.list_prefixes(scheme)
        prefix_list = [p[0] for p in prefixes]
        print(json.dumps(prefix_list, indent=2))
    finally:
        session.close()


@main.command("values")
@click.pass_context
@click.argument("scheme")
@click.argument("prefix")
def list_value(ctx, scheme, prefix):
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        prefixes = definitions.list_values(scheme, prefix)
        prefix_list = [p[0] for p in prefixes]
        print(json.dumps(prefix_list, indent=2))
    finally:
        session.close()


@main.command("uniqs")
@click.pass_context
def list_uniqs(ctx):
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        uniqs = definitions.list_all()
        for uniq in uniqs:
            print(uniq[0])
    finally:
        session.close()


@main.command("add")
@click.pass_context
@click.option("-s", "--scheme", help="Scheme value for entry")
@click.option("-p", "--prefix", help="Prefix value for entry", default=None)
@click.option("-v", "--value", help="infix value for entry", default=None)
@click.option(
    "-t", "--target", help="Pattern for creation of target values", default="{pid}"
)
@click.option(
    "-c",
    "--canonical",
    help="Pattern for creation of canonical values",
    default="{pid}",
)
@click.option(
    "-y", "--synonym", default=None, help="This entry is a synonym for this uniq value."
)
def add_entry(ctx, scheme, prefix, value, target, canonical, synonym):
    defn = rslv.lib_rslv.piddefine.PidDefinition(
        scheme=scheme,
        prefix=prefix,
        value=value,
        target=target,
        canonical=canonical,
        synonym=synonym
    )
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        result = definitions.add_as_definition(defn)
        definitions.refresh_metadata()
        print(result)
    finally:
        session.close()


@main.command("add-json")
@click.pass_context
@click.option(
    "-d",
    "--definition",
    type=click.File("rt"),
    default=sys.stdin,
    help="File with JSON representation of the defintion to add, default=stdin"
)
def add_json(ctx, definition):
    defn = rslv.lib_rslv.piddefine.PidDefinition.model_validate_json(definition)
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        result = definitions.add_as_definition(defn)
        definitions.refresh_metadata()
        print(result)
    finally:
        session.close()


@main.command("get")
@click.pass_context
@click.argument("uniq")
def get_entry(ctx, uniq):
    """
    Retrieve a PidDefinition by its uniq key ("scheme:prefix/value").

    Args:
        ctx: context
        uniq: str the Key to find.

    Returns:
        PidDefinition as json or None
    """
    L = ctx.obj["L"]
    uniq = uniq.strip(" /")
    L.info("Looking for entry: '%s'", uniq)
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        entry = definitions.get_definition_by_uniq(uniq)
        if entry is None:
            L.warning("No definition found for %s", uniq)
            print(json.dumps(None))
        else:
            print(entry.model_dump_json(indent=2))
    finally:
        session.close()

@main.command("delete")
@click.pass_context
@click.argument("uniq")
def delete_entry(ctx, uniq):
    """
    Delete the pid definition with the provided key.
    Args:
        ctx: context
        uniq: unique key for the defintion to delete

    Returns:
        JSON of the deleted object or None if not found.
    """
    L = ctx.obj["L"]
    uniq = uniq.strip(" /")
    L.info("Looking for entry: '%s'", uniq)
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        entry = definitions.delete(uniq)
        if entry is None:
            L.warning("No definition found for %s", uniq)
            print(json.dumps(None))
        else:
            print(entry.model_dump_json(indent=2))
    finally:
        session.close()


@main.command("match")
@click.pass_context
@click.argument("identifier")
def match_entry(ctx, identifier):
    """
    Return the best match for the provided identifier string.

    Args:
        ctx:
        identifier:

    Returns:

    """
    L = ctx.obj["L"]
    pid = rslv.lib_rslv.ParsedPID(pid=identifier)
    pid.split()
    L.info("Looking for entry %s", pid.pid)
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        entry = definitions.get_as_definition(pid)
        if entry is None:
            L.warning("No definition found for %s", pid.pid)
            print(json.dumps(None))
        else:
            L.info("Matched %s to definition %s", pid.pid, entry.uniq)
            print(entry.model_dump_json(indent=2))
    finally:
        session.close()


@main.command("naans")
@click.pass_context
@click.option(
    "-u",
    "--url",
    help="URL from which to retrieve public NAAN registry JSON.",
    default="https://cdluc3.github.io/naan_reg_public/naans_public.json",
)
@click.option(
    "-z",
    "--ezid-naans",
    help="JSON list of NAANs managed by EZID",
    default="ezid_naans.json"
)
def load_public_naans(ctx, url, ezid_naans):
    """
    Load NAAN definitions from the Public NAAN registry.

    Note that some NAAN registrants have targets associated with "shoulders" that
    have been registered with N2T and are not expressed in the NAAN registry.
    Gathering this information requires pulling from the legacy N2T prefixes
    list at https://n2t.net/e/n2t_full_prefixes.yaml and locating the records
    of type "shoulder".

    Args:
        ctx: context
        url: URL of the public NAANs JSON.
        ezid_naans: path to JSON list of NAANs managed by EZID
    Returns:

    """

    L = get_logger()
    ezid_naan_list = []
    if os.path.exists(ezid_naans):
        with open(ezid_naans, "r") as inf:
            ezid_naan_list = json.load(inf)
        L.info("Loaded %s EZID NAANs from %s", len(ezid_naan_list), ezid_naans)
    else:
        L.warning("No EZID NAAN list available, missing: %s", ezid_naans)

    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        L.debug("Loading NAAN JSON from: %s", url)
        response = httpx.get(url)
        if response.status_code != 200:
            L.error("Download failed. Response status code: %s", response.status_code)
            return
        try:
            data = response.json()
        except Exception as e:
            L.exception(e)
            return

        canonical = "ark:/{prefix}/{value}"
        try:
            # Add a base ark: scheme definition.
            entry = rslv.lib_rslv.piddefine.PidDefinitionSQL(
                scheme="ark",
                target="/.info/{pid}",
                canonical=canonical,
                synonym_for=None,
                properties={
                    "what": "ark",
                    "name": "Archival Resource Key",
                },
            )
            definitions.add(entry)
        except Exception as e:
            L.warning(e)
            pass
        for naan, record in data.items():
            naan = str(naan)
            L.debug("Loading %s", naan)
            properties = record
            target = record.get("target", None)
            if target is None:
                target = "/.info/{pid}"
            else:
                if naan in ezid_naan_list:
                    # Special case of a NAAN that is managed by EZID
                    # Need to override the target
                    L.info("EZID NAAN: %s", naan)
                    target = "https://ezid.cdlib.org/ark:/{prefix}/{value}"
                else:
                    L.debug("NAAN: %s", naan)
                    target = target.replace("$arkpid", "ark:/{prefix}/{value}")
            entry = rslv.lib_rslv.piddefine.PidDefinitionSQL(
                scheme="ark",
                prefix=naan,
                value=None,
                target=target,
                properties=properties,
                canonical=canonical,
                synonym_for=None,
            )
            L.debug("Saving entry for NAAN: %s", naan)
            definitions.add(entry)
        definitions.refresh_metadata()
    finally:
        session.close()


@main.command("naan_shoulders")
@click.pass_context
@click.option(
    "-s",
    "--source",
    help="Name of ANVL source file downloaded from https://n2t.net/e/pub/shoulder_registry.txt.",
    default="shoulder_registry.txt",
)
def load_naan_shoulders(ctx, source):
    # TODO: More work needed here. EZID managed entries should be redirected to
    #  EZID for resolution
    L = get_logger()
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        anvl_src = open(source, "r").read()
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        canonical = "ark:{prefix}/{value}"
        for entry in rslv.lib_rslv.n2tutils.naa_records_from_anvl_text(anvl_src):
            parts = rslv.lib_rslv.split_identifier_string(entry.get("id", ""))
            if parts["value"] is None or parts["scheme"] != "ark":
                continue
            target = entry.get("nma_url", None)
            if len(target) < 1:
                continue
            target = target[0] + "{pid}"
            print(json.dumps(entry))
            definition = rslv.lib_rslv.piddefine.PidDefinitionSQL(
                scheme=parts["scheme"],
                prefix=parts["prefix"],
                value=parts["value"],
                target=target,
                properties=entry,
                canonical=canonical,
                synonym_for=None,
            )
            L.info("Saving entry for: %s", entry["id"])
            definitions.add(definition)
        definitions.refresh_metadata()
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
