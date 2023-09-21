import datetime
import typing
import pydantic
import sqlalchemy as sqla
import sqlalchemy.orm as sqlorm
import sqlalchemy.types
import sqlalchemy.sql.expression

import rslv.lib_rslv


def current_time():
    return datetime.datetime.now(tz=datetime.timezone.utc)


class Base(sqlalchemy.orm.DeclarativeBase):
    pass


def default_definition_uniq(context):
    """Create a single string representation of scheme:prefix/value.

    Used when adding a record to the config database to provide a unique
    label for each record based on its properties. This is used for
    synonym target lookup.
    """
    params = context.get_current_parameters()
    s = params["scheme"] if params["scheme"] is not None else ""
    p = params["prefix"] if params["prefix"] is not None else ""
    if params["value"] is not None:
        return f"{s}:{p}/{params['value']}"
    return f"{s}:{p}"


class PidDefinitionSQL(Base):
    """Defines a database record that contains configuration for a
    particular combination of scheme:prefix/value.

    Each record is a potential redirect target and contains the information
    needed to handle a redirect or present metadata about the identifier.
    """

    __tablename__ = "piddef"

    uniq: sqlorm.Mapped[str] = sqlorm.mapped_column(
        doc="Unique key for this record, constructed from scheme:prefix/value",
        index=True,
        default=default_definition_uniq,
    )
    scheme: sqlorm.Mapped[str] = sqlorm.mapped_column(
        primary_key=True, doc="Lower case scheme name.", index=True
    )
    # Unique constraint is not enforced in sqlite if values are NULL, so set default to empty string
    prefix: sqlorm.Mapped[str] = sqlorm.mapped_column(
        primary_key=True, default="", doc="PID prefix portion match.", index=True
    )
    value: sqlorm.Mapped[str] = sqlorm.mapped_column(
        primary_key=True, default="", doc="PID value portion match.", index=True
    )
    splitter: sqlorm.Mapped[typing.Optional[str]] = sqlorm.mapped_column(
        doc="Optional alternate splitter function to use."
    )
    pid_model: sqlorm.Mapped[str] = sqlorm.mapped_column(
        default="", doc="Identifier class to use for pids matching this definition."
    )
    # Note we can extend this to support alternate targets based on content negotiation
    # (media-type, profile, etc) by making this a dict and matching request
    # properties with the key, e.g. target = {"*":{"target":PATTERN, "http_code": 302}, ...}
    target: sqlorm.Mapped[str] = sqlorm.mapped_column(
        default="{pid}", doc="Pattern for target string generation."
    )
    http_code: sqlorm.Mapped[int] = sqlorm.mapped_column(
        default=302, doc="HTTP status code for response."
    )
    canonical: sqlorm.Mapped[str] = sqlorm.mapped_column(
        default="{pid}", doc="Pattern for canonical string representation."
    )
    properties: sqlorm.Mapped[dict[str, typing.Any]] = sqlorm.mapped_column(
        type_=sqlalchemy.types.JSON,
        nullable=True,
        doc="Additional metadata properties associated with this entry.",
    )
    synonym_for: sqlorm.Mapped[str] = sqlorm.mapped_column(
        default=None,
        nullable=True,
        doc="Indicates this entry is a synonym for the referenced entry.",
    )

    # Only allow unique combinations of scheme, group, and value
    __table_args__ = (sqla.UniqueConstraint("scheme", "prefix", "value"),)

    @sqlalchemy.orm.validates("scheme")
    def validate_scheme(self, key, scheme):
        scheme = scheme.strip(":/ ")
        if "/" in scheme:
            raise ValueError("'/' is not allowed in scheme.")
        if ":" in scheme:
            raise ValueError("':' is not allowed in scheme.")
        return scheme

    @sqlalchemy.orm.validates("prefix")
    def validate_prefix(self, key, prefix):
        if prefix is None:
            return ""
        prefix = prefix.strip("/ ")
        if "/" in prefix:
            raise ValueError("'/' is not allowed in prefix.")
        return prefix


class PidDefinition(pydantic.BaseModel):
    """
    Defines a PID definition record representation that exists outside
    of the repository. Repository entries should use this model for
    transfer to other uses.
    """
    scheme: str
    prefix: typing.Optional[str] = ""
    value: typing.Optional[str] = ""
    #if not set, is computed by the sql model
    uniq: typing.Optional[str] = None
    splitter: typing.Optional[str] = None
    pid_model: typing.Optional[str] = None
    target: str = "{pid}"
    http_code: int = 302
    canonical: str = "{pid}"
    synonym_for: typing.Optional[str] = None
    properties: typing.Optional[dict[str, typing.Any]] = None


class ConfigMeta(Base):
    __tablename__ = "piddef_meta"

    key: sqlorm.Mapped[int] = sqlorm.mapped_column(primary_key=True)
    created: sqlorm.Mapped[datetime.datetime] = sqlorm.mapped_column(
        default=current_time, doc="Time when this configuration was created."
    )
    max_value_length: sqlorm.Mapped[int] = sqlorm.mapped_column(
        doc="Computed maximum length of value entries"
    )
    description: sqlorm.Mapped[str] = sqlorm.mapped_column(
        nullable=True, doc="Human readable description of this configuration."
    )


class PidDefinitionCatalog:
    """A repository of identifier configuration details.

    This class provides methods for operating on the database containing
    the identifier configuration details.
    """

    def __init__(self, session: sqlorm.Session):
        """
        Initial the config repository instance.

        Args:
            session: Returned by engine.connect()
        """
        self._session = session
        # Cache this value as it is used often. -1 indicates it is unset.
        self._cached_max_len = -1

    def initialize_configuration(self, description: str) -> ConfigMeta:
        """
        Initializes the configuration metadata. This should be
        called when creating a new configuration.

        Args:
            description: Human readable description of the configuration.

        Returns: ConfigMeta record.
        """
        meta = ConfigMeta(key=0, max_value_length=0, description=description)
        self._session.add(meta)
        self._session.commit()
        return meta

    def refresh_metadata(self):
        """
        Update the value length count.

        Computes and stores the maximum value length. Call this method
        after altering any definition records.
        """
        max_len_q = sqlalchemy.select(
            sqlalchemy.sql.expression.func.max(
                sqlalchemy.sql.expression.func.char_length(PidDefinitionSQL.value)
            )
        )
        result = self._session.execute(max_len_q).fetchone()[0]
        meta = self._session.get(ConfigMeta, 0)
        meta.max_value_length = result
        self._cached_max_len = result
        self._session.commit()

    def get_metadata(self) -> dict:
        """Retrieve metadata about this configuration.

        Returns:
            (dict) Basic information about the configuration.
        """
        meta = self._session.get(ConfigMeta, 0)
        return {
            "description": meta.description,
            "created": meta.created.isoformat()
        }

    def get_max_value_length(self) -> int:
        """
        Find the longest value in the available definition entries.

        Returns:
            (int) Length of the longest value.
        """
        if self._cached_max_len > 0:
            return self._cached_max_len
        meta = self._session.get(ConfigMeta, 0)
        self._cached_max_len = meta.max_value_length
        return self._cached_max_len

    @classmethod
    def sqldefinition_to_definition(cls, sql_def: PidDefinitionSQL) -> PidDefinition:
        """
        Map a definition from the SQL store to a PidDefinition object which is used elsewhere.

        Args:
            sql_def: The definition to convert

        Returns:
            (PidDefinition) The converted definition.
        """
        return PidDefinition(
            scheme=sql_def.scheme,
            prefix=sql_def.prefix,
            value=sql_def.value,
            uniq=sql_def.uniq,
            splitter=sql_def.splitter,
            pid_model=sql_def.pid_model,
            target=sql_def.target,
            http_code=sql_def.http_code,
            canonical=sql_def.canonical,
            synonym_for=sql_def.synonym_for,
            properties=sql_def.properties
        )

    def get_by_uniq(self, uniq: str) -> typing.Optional[PidDefinitionSQL]:
        """
        Returns the definition matching the uniq value.

        Note that records with no prefix or value entry have
        an empty string, so the in the case of a record with
        scheme=foo, and not prefix or value set, the uniq
        value will be "foo:/".

        Args:
            uniq: (str) The uniq value to match (scheme:prefix/value)

        Returns:
            PidDefinitionSQL if found, otherwise None
        """
        q = sqlalchemy.select(PidDefinitionSQL).where(PidDefinitionSQL.uniq == uniq)
        result = self._session.execute(q)
        try:
            return result.fetchone()[0]
        except TypeError:
            pass
        return None

    def get_definition_by_uniq(self, uniq: str) -> typing.Optional[PidDefinition]:
        record = self.get_by_uniq(uniq)
        if record is None:
            return None
        return PidDefinitionCatalog.sqldefinition_to_definition(record)

    def _get(
        self,
        scheme: str,
        prefix: typing.Optional[str] = None,
        value: typing.Optional[str] = None,
    ) -> typing.Optional[PidDefinitionSQL]:
        # scheme and prefix are exact matches
        if (value is None or value == "") and (prefix is None or prefix == ""):
            q = sqlalchemy.select(PidDefinitionSQL).where(
                sqlalchemy.and_(
                    PidDefinitionSQL.scheme == scheme,
                    PidDefinitionSQL.prefix == "",
                    PidDefinitionSQL.value == "",
                ),
            )
            result = self._session.execute(q)
            try:
                return result.fetchone()[0]
            except TypeError:
                pass
            return None
        if value is None or value == "":
            q = sqlalchemy.select(PidDefinitionSQL).where(
                sqlalchemy.and_(
                    PidDefinitionSQL.scheme == scheme,
                    PidDefinitionSQL.prefix == prefix,
                    PidDefinitionSQL.value == "",
                ),
            )
            result = self._session.execute(q)
            try:
                return result.fetchone()[0]
            except TypeError:
                pass
            return None

        in_length_max = min(len(value), self.get_max_value_length())
        in_values = []
        for i in range(in_length_max, 1, -1):
            in_values.append(value[:i])
        q = (
            sqlalchemy.select(PidDefinitionSQL)
            .where(
                sqlalchemy.and_(
                    PidDefinitionSQL.scheme == scheme,
                    PidDefinitionSQL.prefix == prefix,
                    PidDefinitionSQL.value.in_(in_values),
                )
            )
            .order_by(
                sqlalchemy.sql.expression.func.char_length(PidDefinitionSQL.value).desc()
            )
        )
        result = self._session.execute(q)
        try:
            return result.fetchone()[0]
        except TypeError:
            pass
        return None

    def get(
        self,
        scheme: str,
        prefix: typing.Optional[str] = None,
        value: typing.Optional[str] = None,
        resolve_synonym: bool = True,
    ) -> typing.Optional[PidDefinitionSQL]:
        """
        Return the best matching definition.

        Matches on scheme and prefix values are exact.

        The value match is for the definition with the longest
        value entry that matches the start of the value portion
        of the parsed identifier string. For example, given two
        definitions with value = "fk" and "fk4", a match for
        the identifier with value portion "fkfoo" woruld return
        the definition with value "fk".

        The default behavior is to return the synonym target.

        Args:
            scheme: Scheme string to match.
            prefix: Optional prefix to match.
            value: Optional value portion to match.
            resolve_synonym: (bool) If return the synonym target.

        Returns:
            Matching PidDefinitionSQL or None if not match.
        """
        # TODO: See if there is an alternate splitter for the scheme
        #       if so, then should re-split the pid with the alternate
        #       splitter and handle things like ignored chars
        #       (e.g. "-" in ARKs)
        entry = self._get(scheme, prefix=prefix, value=value)
        if entry is None:
            entry = self._get(scheme=scheme, prefix=prefix, value=None)
        if entry is None:
            entry = self._get(scheme=scheme, prefix=None, value=None)
        if entry is None:
            return None
        if entry.synonym_for is None or not resolve_synonym:
            return entry
        synonym_parts = rslv.lib_rslv.split_identifier_string(entry.synonym_for)
        _scheme = (
            synonym_parts["scheme"] if synonym_parts["scheme"] is not None else scheme
        )
        _prefix = synonym_parts["prefix"] if synonym_parts["prefix"] != "" else prefix
        _value = synonym_parts["value"] if synonym_parts["value"] is not None else value
        return self.get(_scheme, prefix=_prefix, value=_value)

    def get_as_definition(
        self,
        pid:rslv.lib_rslv.ParsedPID,
        resolve_synonym: bool = True
    ) -> typing.Optional[PidDefinition]:
        """
        Returns an instance of PidDefinition if a match can be found.

        If uniq is set, then other arguments are ignored. If uniq is
        not set, then at least scheme must be set.

        This method does not reconcile synonyms. That must be done by
        the caller by checking the returned object to see if it is
        a synonym for another entry.

        Args:
            uniq:
            scheme:
            prefix:
            value:

        Returns:
            PidDefinition
        """
        record = self.get(pid.scheme, prefix=pid.prefix, value=pid.clean_value, resolve_synonym=resolve_synonym)
        if record is None:
            return None
        return PidDefinitionCatalog.sqldefinition_to_definition(record)

    def add(self, entry: PidDefinitionSQL) -> str:
        """
        Add an entry to the repository database.

        The entry must be unique otherwise it will fail with a
        UniqueConstraint exception.

        Args:
            entry: A populated PidDefinitionSQL for storing in the database.

        Returns:
            str: The computed unique value

        """
        self._session.add(entry)
        self._session.commit()
        return entry.uniq

    def add_as_definition(self, entry:PidDefinition) -> str:
        entry = PidDefinitionSQL(
            uniq=entry.uniq,
            scheme=entry.scheme,
            prefix=entry.prefix,
            value=entry.value,
            splitter=entry.splitter,
            pid_model=entry.pid_model,
            target=entry.target,
            http_code=entry.http_code,
            canonical=entry.canonical
        )
        return self.add(entry)

    def delete(self, uniq:str) -> typing.Optional[PidDefinition]:
        sql_defn = self.get_by_uniq(uniq)
        if sql_defn is None:
            return None
        self._session.delete(sql_defn)
        self._session.commit()
        return PidDefinitionCatalog.sqldefinition_to_definition(sql_defn)

    def parse(self, pid_str: str) -> typing.Tuple[dict, typing.Optional[PidDefinitionSQL]]:
        parts = rslv.lib_rslv.split_identifier_string(pid_str)
        pid_definition = self.get(
            scheme=parts["scheme"], prefix=parts["prefix"], value=parts["value"]
        )
        if pid_definition is None:
            return parts, None
        if pid_definition.splitter is not None:
            # TODO: implement additional split
            pass
        # Compute the suffix
        _content = parts.get("content", None)
        if _content is not None:
            pd_value = "" if pid_definition.value is None else pid_definition.value
            suffix_pos = pid_str.find(_content) + len(
                f"{pid_definition.prefix}/{pd_value}"
            )
            parts["suffix"] = pid_str[suffix_pos:]
        return parts, pid_definition

    def parse_as_definition(self, pid_str: str) -> typing.Tuple[rslv.lib_rslv.ParsedPID, typing.Optional[PidDefinition]]:
        parts = rslv.lib_rslv.ParsedPID(pid=pid_str)
        parts.split()
        pid_definition = self.get_as_definition(parts)
        # TODO: Suffix
        return parts, pid_definition

    def list_all(self):
        q = sqlalchemy.select(PidDefinitionSQL.uniq)
        return self._session.execute(q)

    def list_schemes(self):
        q = sqlalchemy.select(PidDefinitionSQL.scheme).distinct(PidDefinitionSQL.scheme)
        result = self._session.execute(q)
        return result

    def list_prefixes(self, scheme: str):
        q = (
            sqlalchemy.select(PidDefinitionSQL.prefix)
            .distinct(PidDefinitionSQL.prefix)
            .where(
                sqlalchemy.and_(
                    PidDefinitionSQL.scheme == scheme, PidDefinitionSQL.prefix != ""
                )
            )
        )
        result = self._session.execute(q)
        return result

    def list_values(self, scheme: str, prefix: str):
        q = (
            sqlalchemy.select(PidDefinitionSQL.value)
            .distinct(PidDefinitionSQL.value)
            .where(
                sqlalchemy.and_(
                    PidDefinitionSQL.scheme == scheme,
                    PidDefinitionSQL.prefix == prefix,
                    PidDefinitionSQL.value != "",
                )
            )
        )
        result = self._session.execute(q)
        return result


def get_session(engine):
    return sqlalchemy.orm.sessionmaker(bind=engine)()


def create_database(engine, description: str):
    """
    Executes the DDL to set up the database.

    Args:
        engine: Database instance
    """
    Base.metadata.create_all(engine)
    # See if we need to initialize the metadata
    session = get_session(engine)
    try:
        cfg = PidDefinitionCatalog(session)
        meta = session.get(ConfigMeta, 0)
        if meta is None:
            cfg.initialize_configuration(description)
    finally:
        session.close()


def clear_database(engine):
    """
    Drop all tables from the database.

    Args:
        engine: Database instance
    """
    Base.metadata.drop_all(engine)
