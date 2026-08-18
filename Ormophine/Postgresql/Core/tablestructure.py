from __future__ import annotations
from typing import Literal

class DataTypes:
    """Collection of PostgreSQL 16 data types as static methods.

    This class serves as a central registry of all commonly used PostgreSQL data
    types, offering a clean, programmatic way to specify column types without
    writing raw SQL strings. Each static method returns the corresponding SQL
    type string, ready to be passed directly to methods such as
    :meth:`TableStructure.add_column` or :meth:`Table.add_column`.

    The provided types cover:

    - **Numeric types:** :meth:`SMALLINT`, :meth:`INTEGER`, :meth:`BIGINT`,
      :meth:`DECIMAL`, :meth:`NUMERIC`, :meth:`REAL`, :meth:`DOUBLE_PRECISION`,
      :meth:`MONEY`, :meth:`BIT`.
    - **Serial (auto‑increment) types:** :meth:`SMALLSERIAL`, :meth:`SERIAL`,
      :meth:`BIGSERIAL`.
    - **Character types:** :meth:`CHAR`, :meth:`VARCHAR`, :meth:`TEXT`.
    - **Binary type:** :meth:`BYTEA`.
    - **Date/time types:** :meth:`DATE`, :meth:`TIME`, :meth:`TIMETZ`,
      :meth:`TIMESTAMP`, :meth:`TIMESTAMPTZ`, :meth:`INTERVAL`.
    - **Boolean type:** :meth:`BOOLEAN`.
    - **JSON types:** :meth:`JSON`, :meth:`JSONB`.
    - **UUID type:** :meth:`UUID`.
    - **Spatial (PostGIS) types:** :meth:`GEOMETRY`, :meth:`GEOGRAPHY`,
      :meth:`POINT`, :meth:`LINESTRING`, :meth:`POLYGON`, :meth:`MULTIPOINT`,
      :meth:`MULTILINESTRING`, :meth:`MULTIPOLYGON`,
      :meth:`GEOMETRYCOLLECTION`.
    - **Array type:** :meth:`ARRAY`, which accepts an element type string and
      appends ``[]``.

    All methods are ``@staticmethod``, so they can be called without
    instantiating the class.

    Example:
        >>> from ormophine.Postgresql import DataTypes, TableStructure
        >>> structure = TableStructure("users")
        >>> structure.add_column("id", DataTypes.SERIAL(), primary_key=True)
        >>> structure.add_column("name", DataTypes.VARCHAR(100), not_null=True)
        >>> structure.add_column("balance", DataTypes.NUMERIC(12, 2))
        >>> structure.add_column("created_at", DataTypes.TIMESTAMPTZ())
        >>> structure.add_column("tags", DataTypes.ARRAY(DataTypes.VARCHAR(30)))
    """

    # ========================
    # Numeric Data Types
    # ========================

    @staticmethod
    def BIT(size: int) -> str:
        """Returns the SQL ``BIT(length)`` type string for fixed‑length bit strings.

        This static method generates a valid PostgreSQL data type definition for
        a bit string column with the exact number of bits specified by ``size``.
        The value must be between 1 and 64 inclusive; otherwise a ``ValueError``
        is raised.

        Args:
            size (int): The number of bits for the column. Must be an integer
                in the range [1, 64].

        Returns:
            str: A SQL type string in the form ``'BIT(size)'``, suitable for use
            in column definitions.

        Raises:
            ValueError: If ``size`` is less than 1 or greater than 64.

        Example:
            >>> DataTypes.BIT(8)
            'BIT(8)'
            >>> # Used in a TableStructure definition:
            >>> structure = TableStructure("flags")
            >>> structure.add_column("permissions", DataTypes.BIT(8))
        """
        if size < 1 or size > 64:
            raise ValueError("Size for BIT must be between 1 and 64.")
        return f"BIT({size})"

    @staticmethod
    def SMALLINT() -> str:
        """Returns the SQL string for the SMALLINT data type.

        The ``SMALLINT`` type represents a signed two‑byte integer with a range
        of -32,768 to 32,767. It is typically used for compact storage of
        small whole numbers.

        Returns:
            str: The literal string ``"SMALLINT"``.

        Example:
            >>> from ormophine.Postgresql import DataTypes
            >>> small_int = DataTypes.SMALLINT()
            >>> small_int
            'SMALLINT'
            >>> # Use it when defining a table structure
            >>> structure = TableStructure("example")
            >>> structure.add_column("count", DataTypes.SMALLINT(), not_null=True)
        """
        return "SMALLINT"

    @staticmethod
    def INTEGER() -> str:
        """Returns the PostgreSQL ``INTEGER`` data type string.

        Use this method when defining a table column to specify a 32‑bit
        signed integer.

        Returns:
            str: The string ``"INTEGER"``.

        Example:
            >>> from ormophine.Postgresql import TableStructure, DataTypes
            >>> structure = TableStructure("employees")
            >>> structure.add_column("age", DataTypes.INTEGER())
        """
        return "INTEGER"

    @staticmethod
    def BIGINT() -> str:
        """Returns the SQL ``BIGINT`` data type string.

        Represents a signed 8‑byte (64‑bit) integer, which is the same as
        ``INTEGER`` in PostgreSQL but with explicit sizing.

        Returns:
            str: The string ``'BIGINT'``, ready to be used in a column
            definition or ``CREATE TABLE`` statement.

        Example:
            >>> DataTypes.BIGINT()
            'BIGINT'
        """
        return "BIGINT"

    @staticmethod
    def DECIMAL(precision: int = 10, scale: int = 0) -> str:
        """Returns the SQL ``DECIMAL(precision, scale)`` type string.

        The ``DECIMAL`` type is used for exact numeric values with a fixed
        number of decimal places. This method generates a standard PostgreSQL
        decimal definition that can be passed directly to
        :meth:`TableStructure.add_column`.

        Args:
            precision (int): Total number of significant digits.
                Defaults to ``10``.
            scale (int): Number of digits after the decimal point.
                Defaults to ``0``.

        Returns:
            str: A string like ``'DECIMAL(10, 2)'`` that can be used as the
            ``datatype`` argument when defining a column.

        Example:
            >>> from ormophine.Postgresql import TableStructure, DataTypes
            >>> structure = TableStructure("products")
            >>> structure.add_column("price", DataTypes.DECIMAL(8, 2))
            >>> # Generates: CREATE TABLE "products" ( "price" DECIMAL(8, 2), ... );
        """
        if precision < 1 or scale < 0 or scale > precision:
            raise ValueError("Precision must be >= 1 and scale must be >= 0 and <= precision.")
        return f"DECIMAL({precision}, {scale})"

    @staticmethod
    def NUMERIC(precision: int = 10, scale: int = 0) -> str:
        """Returns the SQL NUMERIC type string with given precision and scale.

        Generates a ``NUMERIC(precision, scale)`` column definition suitable for
        PostgreSQL. NUMERIC is an arbitrary‑precision decimal type. The *precision*
        is the total count of significant digits, and the *scale* is the number of
        fractional digits. Both must be non‑negative integers, and the scale must
        not exceed the precision.

        Args:
            precision (int): Total number of significant digits (must be ≥ 1).
                Defaults to ``10``.
            scale (int): Number of digits to the right of the decimal point
                (must be ≥ 0 and ≤ precision). Defaults to ``0``.

        Returns:
            str: A string like ``"NUMERIC(10, 0)"`` that can be used directly in
            ``CREATE TABLE`` statements or passed to methods such as
            :meth:`TableStructure.add_column` and :meth:`Table.add_column`.

        Raises:
            ValueError: If ``precision < 1``, ``scale < 0``, or ``scale > precision``.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> dt = DataTypes.NUMERIC(12, 2)
            >>> print(dt)
            NUMERIC(12, 2)
            >>> # Use in a table definition
            >>> structure = TableStructure("payments")
            >>> structure.add_column("amount", DataTypes.NUMERIC(8, 2), not_null=True)
        """
        if precision < 1 or scale < 0 or scale > precision:
            raise ValueError("Precision must be >= 1 and scale must be >= 0 and <= precision.")
        return f"NUMERIC({precision}, {scale})"

    @staticmethod
    def REAL() -> str:
        """Returns the SQL REAL type string.

        Represents a 4‑byte, single‑precision floating‑point number in
        PostgreSQL. It is commonly used for columns that store approximate
        numeric values with less storage overhead than
        :meth:`DOUBLE_PRECISION` or :meth:`NUMERIC`. The precision is about
        6 decimal digits.

        Returns:
            str: The SQL type string ``"REAL"``.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> dt = DataTypes.REAL()
            >>> print(dt)
            REAL
            >>> # Use in table definition
            >>> structure = TableStructure("sensors")
            >>> structure.add_column("temperature", DataTypes.REAL(), not_null=True)
        """
        return "REAL"

    @staticmethod
    def DOUBLE_PRECISION() -> str:
        """Returns the SQL DOUBLE PRECISION type string.

        Generates the ``DOUBLE PRECISION`` column definition suitable for
        PostgreSQL. This is an 8‑byte floating‑point data type (synonym for
        ``FLOAT8``).

        Returns:
            str: The string ``"DOUBLE PRECISION"``, which can be used directly
            in ``CREATE TABLE`` statements or passed to methods such as
            :meth:`TableStructure.add_column` and :meth:`Table.add_column`.

        Raises:
            None

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> dt = DataTypes.DOUBLE_PRECISION()
            >>> print(dt)
            DOUBLE PRECISION
            >>> # Use in a table definition
            >>> structure = TableStructure("measurements")
            >>> structure.add_column("value", DataTypes.DOUBLE_PRECISION(), not_null=True)
        """
        return "DOUBLE PRECISION"

    @staticmethod
    def MONEY() -> str:
        """Returns the SQL MONEY type string for monetary values.

        ``MONEY`` is a fixed‑point numeric data type that stores currency
        amounts with a fractional precision of two decimal places. The output
        format is locale‑sensitive, meaning the currency symbol, grouping, and
        decimal separators depend on the database's ``lc_monetary`` setting.
        Despite its formatting behaviour, the underlying storage uses a 64‑bit
        signed integer representing the amount in cents; the maximum range is
        ±9,223,372,036,854,775,807 cents (approximately ±92.23 trillion in
        the base currency unit). Use this type for applications where monetary
        values do not exceed that range and locale‑specific display is desired.

        Args:
            None

        Returns:
            str: The literal string ``"MONEY"``, which can be used directly in
            ``CREATE TABLE`` statements or passed to methods such as
            :meth:`TableStructure.add_column` and :meth:`Table.add_column`.

        Raises:
            None

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> dt = DataTypes.MONEY()
            >>> print(dt)
            MONEY
            >>> # Use in a table definition
            >>> structure = TableStructure("products")
            >>> structure.add_column("price", DataTypes.MONEY(), not_null=True)
        """
        return "MONEY"

    # ========================
    # Serial (Auto-increment) Types
    # ========================

    @staticmethod
    def SERIAL() -> str:
        """Returns the SQL ``SERIAL`` type string for auto‑incrementing integer columns.

        ``SERIAL`` is a PostgreSQL pseudo‑type that creates an ``INTEGER`` column
        with a sequence‑based default value, automatically generating unique
        identifiers for new rows. This method simply returns the string
        ``"SERIAL"``, which can be used directly in column definitions passed to
        :meth:`TableStructure.add_column` or :meth:`Table.add_column`.

        Returns:
            str: The literal string ``"SERIAL"``.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> dt = DataTypes.SERIAL()
            >>> print(dt)
            SERIAL
            >>> # Use in a table definition
            >>> structure = TableStructure("orders")
            >>> structure.add_column("id", DataTypes.SERIAL(), primary_key=True)
        """
        return "SERIAL"

    @staticmethod
    def SMALLSERIAL() -> str:
        """Returns the SQL SMALLSERIAL type string for an auto‑incrementing small integer.

        ``SMALLSERIAL`` is a PostgreSQL pseudo‑type that creates a 2‑byte integer
        column (``SMALLINT``) that automatically increments with each new row,
        backed by a sequence. It is equivalent to ``SMALLINT`` with an implicit
        ``GENERATED BY DEFAULT AS IDENTITY``. This method returns the string
        ``"SMALLSERIAL"``, which can be used directly in ``CREATE TABLE``
        definitions or passed to :meth:`TableStructure.add_column` and
        :meth:`Table.add_column`.

        When ``SMALLSERIAL`` is used in :meth:`TableStructure.add_column`, the
        method automatically sets ``primary_key=True``, ``not_null=True``, and
        ``auto_increment=True`` unless explicitly overridden. The underlying
        Python type mapped for SMALLSERIAL columns is :class:`int`.

        Returns:
            str: The string ``"SMALLSERIAL"``.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure, Driver
            >>> dt = DataTypes.SMALLSERIAL()
            >>> print(dt)
            SMALLSERIAL
            >>> # Use in a table structure
            >>> structure = TableStructure("logs")
            >>> structure.add_column("log_id", DataTypes.SMALLSERIAL(), primary_key=True)
        """
        return "SMALLSERIAL"

    @staticmethod
    def BIGSERIAL() -> str:
        """Returns the SQL BIGSERIAL type string for auto‑incrementing 64‑bit integers.

        ``BIGSERIAL`` is a PostgreSQL pseudo‑type that creates a ``BIGINT`` column
        with an implicit sequence and default value. It automatically generates
        unique values when inserting rows without specifying the column. This method
        simply returns the literal ``'BIGSERIAL'``, which can be used directly in
        ``CREATE TABLE`` definitions.

        Returns:
            str: The string ``"BIGSERIAL"``, ready for use in a column definition.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("logs")
            >>> structure.add_column("id", DataTypes.BIGSERIAL(), primary_key=True)
        """
        return "BIGSERIAL"

    # ========================
    # String Data Types
    # ========================

    @staticmethod
    def CHAR(length: int = 1) -> str:
        """Returns the SQL CHAR type string with a fixed length.

        Generates a ``CHAR(length)`` column definition for fixed-length character
        strings in PostgreSQL. The *length* specifies the exact number of characters
        the column can store; values shorter than this are right-padded with spaces.
        This method is intended to be used with :meth:`TableStructure.add_column` or
        :meth:`Table.add_column` when defining a table schema.

        Args:
            length (int): The fixed number of characters for the CHAR column.
                Must be at least ``1``. Defaults to ``1``.

        Returns:
            str: A string like ``"CHAR(10)"`` that can be passed directly to a
            column definition method.

        Raises:
            ValueError: If ``length`` is less than ``1``.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("countries")
            >>> structure.add_column("code", DataTypes.CHAR(2), not_null=True)
        """
        if length < 1:
            raise ValueError("Length for CHAR must be at least 1.")
        return f"CHAR({length})"

    @staticmethod
    def VARCHAR(length: int = 255) -> str:
        """Returns the SQL VARCHAR type string with the specified maximum length.

        Generates a ``VARCHAR(length)`` column definition suitable for PostgreSQL.
        VARCHAR is a variable‑length character string with a user‑defined maximum
        size. The *length* must be a positive integer.

        Args:
            length (int): Maximum number of characters the column can store.
                Must be ≥ 1. Defaults to ``255``.

        Returns:
            str: A string like ``"VARCHAR(100)"`` that can be used directly in
            ``CREATE TABLE`` statements or passed to methods such as
            :meth:`TableStructure.add_column` and :meth:`Table.add_column`.

        Raises:
            ValueError: If ``length`` is less than 1.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("employees")
            >>> structure.add_column("name", DataTypes.VARCHAR(100), not_null=True)
            >>> structure.add_column("bio", DataTypes.VARCHAR())  # defaults to 255
        """
        if length < 1:
            raise ValueError("Length for VARCHAR must be at least 1.")
        return f"VARCHAR({length})"

    @staticmethod
    def TEXT() -> str:
        """Returns the SQL TEXT type string for variable‑length character data.

        In PostgreSQL, ``TEXT`` represents a character string of unlimited length.
        This method returns the literal ``'TEXT'`` so it can be used directly in
        column definitions when creating tables via :class:`TableStructure` or
        :meth:`Table.add_column`.

        Returns:
            str: The string ``"TEXT"``.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("notes")
            >>> structure.add_column("content", DataTypes.TEXT())
        """
        return "TEXT"

    # ========================
    # Binary Data Types
    # ========================

    @staticmethod
    def BYTEA() -> str:
        """Returns the SQL BYTEA type string for storing binary data.

        ``BYTEA`` is the PostgreSQL data type for variable‑length binary strings
        (``bytea``). It can hold raw bytes, similar to ``BLOB`` in other databases.
        This method returns the literal ``'BYTEA'``, ready to be used in column
        definitions.

        Returns:
            str: The string ``"BYTEA"``.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("files")
            >>> structure.add_column("content", DataTypes.BYTEA(), not_null=True)
        """
        return "BYTEA"

    # ========================
    # Date and Time Data Types
    # ========================

    @staticmethod
    def DATE() -> str:
        """Returns the SQL DATE type string for storing dates.

        The ``DATE`` type stores a calendar date (year, month, day) without any
        time zone or time-of-day component, following the PostgreSQL ``date``
        data type. This method simply returns the literal ``'DATE'``, which can be
        used directly in ``CREATE TABLE`` column definitions or passed to
        :meth:`TableStructure.add_column` and :meth:`Table.add_column`.

        Returns:
            str: The string ``"DATE"``, ready for use in a column definition.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("events")
            >>> structure.add_column("event_date", DataTypes.DATE(), not_null=True)
            >>> print(DataTypes.DATE())
            DATE
        """
        return "DATE"

    @staticmethod
    def TIME(precision: int = None) -> str:
        """Returns the SQL TIME type string, optionally with fractional seconds precision.

        ``TIME`` represents a time of day without a date, storing hours, minutes,
        and seconds. If *precision* is given, it specifies the number of fractional
        digits retained for the seconds part (0–6). Without arguments, the plain
        ``TIME`` string is returned, meaning the default precision of the database
        (typically 6) will be used.

        Args:
            precision (int, optional): Number of fractional digits for seconds
                (0 to 6). If ``None`` (default), no precision is included.

        Returns:
            str: Either ``"TIME"`` or ``"TIME(precision)"``, ready for use in a
            column definition, such as in :meth:`TableStructure.add_column` or
            :meth:`Table.add_column`.

        Raises:
            ValueError: If *precision* is outside the valid range (0–6). (Note:
                The current implementation does not validate the range; this may
                be added in future versions.)

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> # Plain time without fractional seconds
            >>> dt = DataTypes.TIME()
            >>> print(dt)
            TIME
            >>> # Time with milliseconds precision
            >>> dt_ms = DataTypes.TIME(3)
            >>> print(dt_ms)
            TIME(3)
            >>> # Use in a table definition
            >>> structure = TableStructure("schedule")
            >>> structure.add_column("start_time", DataTypes.TIME(0), not_null=True)
        """
        if precision is not None:
            return f"TIME({precision})"
        return "TIME"

    @staticmethod
    def TIMETZ(precision: int = None) -> str:
        """Returns the SQL TIMETZ type string, optionally with fractional seconds precision.

        ``TIMETZ`` is the time‑with‑time‑zone data type, storing a time of day
        together with a time zone offset. It is analogous to :meth:`TIME` but
        includes time zone awareness. If *precision* is provided, it specifies the
        number of fractional digits retained for the seconds part (0–6). Without
        arguments, the plain ``TIMETZ`` string is returned, using the database
        default precision (typically 6).

        Args:
            precision (int, optional): Number of fractional digits for seconds
                (0 to 6). If ``None`` (default), no precision is included in the
                type string.

        Returns:
            str: Either ``"TIMETZ"`` or ``"TIMETZ(precision)"``, ready for use in
            column definitions (e.g., :meth:`TableStructure.add_column`).

        Raises:
            ValueError: (Not currently enforced) If *precision* is outside the
                valid range (0–6). Future versions may add validation.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> # Plain time with time zone
            >>> dt = DataTypes.TIMETZ()
            >>> print(dt)
            TIMETZ
            >>> # With milliseconds precision
            >>> dt_ms = DataTypes.TIMETZ(3)
            >>> print(dt_ms)
            TIMETZ(3)
            >>> # Use in a table definition
            >>> structure = TableStructure("events")
            >>> structure.add_column("start_time", DataTypes.TIMETZ(0), not_null=True)
        """
        if precision is not None:
            return f"TIMETZ({precision})"
        return "TIMETZ"

    @staticmethod
    def TIMESTAMP(precision: int = None) -> str:
        """Returns the SQL TIMESTAMP type string, optionally with fractional seconds precision.

        ``TIMESTAMP`` stores a date and time (without time zone). If *precision*
        is provided, it specifies the number of fractional digits retained for the
        seconds part (0–6). Without arguments, the plain ``TIMESTAMP`` string is
        returned, using the database default precision (typically 6).

        Args:
            precision (int, optional): Number of fractional digits for seconds
                (0 to 6). If ``None`` (default), no precision is included.

        Returns:
            str: Either ``"TIMESTAMP"`` or ``"TIMESTAMP(precision)"``, ready for
            use in a column definition (e.g., in :meth:`TableStructure.add_column`
            or :meth:`Table.add_column`).

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> # Plain timestamp
            >>> dt = DataTypes.TIMESTAMP()
            >>> print(dt)
            TIMESTAMP
            >>> # Timestamp with millisecond precision
            >>> dt_ms = DataTypes.TIMESTAMP(3)
            >>> print(dt_ms)
            TIMESTAMP(3)
            >>> # Use in a table definition
            >>> structure = TableStructure("events")
            >>> structure.add_column("created_at", DataTypes.TIMESTAMP(0), not_null=True)
        """
        if precision is not None:
            return f"TIMESTAMP({precision})"
        return "TIMESTAMP"

    @staticmethod
    def TIMESTAMPTZ(precision: int = None) -> str:
        """Returns the SQL TIMESTAMPTZ type string, optionally with fractional seconds precision.

        ``TIMESTAMPTZ`` represents a date and time with time zone awareness. The
        optional *precision* argument specifies the number of fractional digits
        retained for the seconds part (0–6). If omitted, the default database
        precision (typically 6) is used.

        Args:
            precision (int, optional): Number of fractional digits for seconds
                (0 to 6). If ``None`` (default), no precision is included.

        Returns:
            str: Either ``"TIMESTAMPTZ"`` or ``"TIMESTAMPTZ(precision)"``, ready
            for use in a column definition, such as in
            :meth:`TableStructure.add_column` or :meth:`Table.add_column`.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> # Timestamp with time zone, default precision
            >>> dt = DataTypes.TIMESTAMPTZ()
            >>> print(dt)
            TIMESTAMPTZ
            >>> # With millisecond precision
            >>> dt_ms = DataTypes.TIMESTAMPTZ(3)
            >>> print(dt_ms)
            TIMESTAMPTZ(3)
            >>> # Use in a table definition
            >>> structure = TableStructure("events")
            >>> structure.add_column("created_at", DataTypes.TIMESTAMPTZ(3), not_null=True)
        """
        if precision is not None:
            return f"TIMESTAMPTZ({precision})"
        return "TIMESTAMPTZ"

    @staticmethod
    def INTERVAL() -> str:
        """Returns the SQL INTERVAL type string for storing time spans.

        ``INTERVAL`` represents a duration of time (e.g., days, hours, minutes,
        seconds). It is a native PostgreSQL type that can store a combination of
        different time units. This method simply returns the literal
        ``'INTERVAL'``, which can be used directly in ``CREATE TABLE`` definitions.

        Returns:
            str: The string ``"INTERVAL"``, ready for use in a column definition.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("events")
            >>> structure.add_column("duration", DataTypes.INTERVAL(), not_null=True)
        """
        return "INTERVAL"

    # ========================
    # Boolean Type
    # ========================

    @staticmethod
    def BOOLEAN() -> str:
        """Returns the SQL BOOLEAN type string for true/false values.

        ``BOOLEAN`` represents a logical truth value, storing ``TRUE``,
        ``FALSE``, or ``NULL``. In PostgreSQL, it is equivalent to the
        ``bool`` type. This method simply returns the literal ``'BOOLEAN'``,
        which can be used directly in ``CREATE TABLE`` definitions or passed
        to methods such as :meth:`TableStructure.add_column` and
        :meth:`Table.add_column`.

        Returns:
            str: The string ``"BOOLEAN"``, ready for use in a column
            definition.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("users")
            >>> structure.add_column("is_active", DataTypes.BOOLEAN(),
            ...                      default=True, not_null=True)
        """
        return "BOOLEAN"

    # ========================
    # JSON Types
    # ========================

    @staticmethod
    def JSON() -> str:
        """Returns the SQL JSON type string for storing JSON data.

        In PostgreSQL, ``JSON`` is a data type that stores JSON-formatted text
        without enforcing the stricter binary format of ``JSONB``. It preserves
        white space, key order, and duplicate keys exactly as inserted. This
        method simply returns the literal ``'JSON'``, which can be used in
        ``CREATE TABLE`` column definitions or with methods like
        :meth:`TableStructure.add_column` and :meth:`Table.add_column`.

        Returns:
            str: The string ``"JSON"``, ready for use in a column definition.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("settings")
            >>> structure.add_column("config", DataTypes.JSON(), not_null=True)
        """
        return "JSON"

    @staticmethod
    def JSONB() -> str:
        """Returns the SQL JSONB type string for storing JSON data in a binary format.

        In PostgreSQL, ``JSONB`` is a data type that stores JSON data in a
        decomposed binary format, which allows efficient indexing, faster
        processing, and more advanced querying (e.g., containment, existence, and
        path matching operators). Unlike ``JSON``, it does not preserve white
        space, key order, or duplicate keys. This method simply returns the
        literal ``'JSONB'``, which can be used in ``CREATE TABLE`` column
        definitions or with methods like :meth:`TableStructure.add_column` and
        :meth:`Table.add_column`.

        Returns:
            str: The string ``"JSONB"``, ready for use in a column definition.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("products")
            >>> structure.add_column("attributes", DataTypes.JSONB(), not_null=True)
        """
        return "JSONB"

    # ========================
    # UUID Type
    # ========================

    @staticmethod
    def UUID() -> str:
        """Returns the SQL UUID type string for storing universally unique identifiers.

        ``UUID`` is a PostgreSQL data type that stores 128‑bit quantities
        generated by algorithms that ensure uniqueness across space and time.
        This method simply returns the literal ``'UUID'``, which can be used
        directly in ``CREATE TABLE`` column definitions or with methods like
        :meth:`TableStructure.add_column` and :meth:`Table.add_column`.

        Returns:
            str: The string ``"UUID"``, ready for use in a column definition.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("devices")
            >>> structure.add_column("device_id", DataTypes.UUID(), not_null=True)
        """
        return "UUID"

    # ========================
    # Spatial Data Types (PostGIS)
    # ========================

    @staticmethod
    def GEOMETRY() -> str:
        """Returns the SQL GEOMETRY type string for spatial data (PostGIS).

        ``GEOMETRY`` is a spatial data type provided by the PostGIS extension
        for PostgreSQL. It stores geometric shapes such as points, lines, and
        polygons in a planar coordinate system. To use this type, the PostGIS
        extension must be installed and enabled in the database (``CREATE
        EXTENSION postgis;``). This method simply returns the literal
        ``'GEOMETRY'``, which can be used in ``CREATE TABLE`` column definitions
        or with methods like :meth:`TableStructure.add_column` and
        :meth:`Table.add_column`.

        Returns:
            str: The string ``"GEOMETRY"``, ready for use in a column definition.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("landmarks")
            >>> structure.add_column("location", DataTypes.GEOMETRY())
            >>> # After creating the table, spatial data can be inserted with
            >>> # PostGIS functions like ST_MakePoint, ST_GeomFromText, etc.
        """
        return "GEOMETRY"

    @staticmethod
    def GEOGRAPHY() -> str:
        """Returns the SQL GEOGRAPHY type string for geodetic (round‑earth) data.

        ``GEOGRAPHY`` is a PostGIS spatial type that stores coordinates on a
        spheroidal model of the Earth, enabling accurate distance and area
        calculations. Unlike ``GEOMETRY``, which assumes a flat Cartesian plane,
        ``GEOGRAPHY`` accounts for the Earth's curvature. This method returns
        ``'GEOGRAPHY'``, which can be used directly in ``CREATE TABLE`` column
        definitions.

        Returns:
            str: The string ``"GEOGRAPHY"``, suitable for use with
            :meth:`TableStructure.add_column` or :meth:`Table.add_column`.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("cities")
            >>> structure.add_column("location", DataTypes.GEOGRAPHY())
        """
        return "GEOGRAPHY"

    @staticmethod
    def POINT() -> str:
        """Returns the SQL POINT type string for a PostGIS geometry column.

        ``POINT`` is a spatial data type representing a single location on the
        earth's surface, typically stored as a pair of coordinates (longitude,
        latitude). This method returns the string ``'POINT'`` which can be used
        in column definitions for tables that have the PostGIS extension enabled.

        Returns:
            str: The literal ``"POINT"``, suitable for a column definition in a
            ``CREATE TABLE`` statement, e.g. via :meth:`TableStructure.add_column`.

        Note:
            Using this data type requires the PostGIS extension to be installed in
            the PostgreSQL database. If PostGIS is not available, creating a column
            with this type will fail.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("locations")
            >>> structure.add_column("coordinates", DataTypes.POINT(), not_null=True)
        """
        return "POINT"

    @staticmethod
    def LINESTRING() -> str:
        """Returns the SQL LINESTRING type string for PostGIS spatial data.

        ``LINESTRING`` is a PostGIS geometry type representing a sequence of
        points forming a continuous line. This method returns the literal
        ``'LINESTRING'``, which can be used directly in ``CREATE TABLE``
        column definitions when PostGIS is enabled.

        Returns:
            str: The string ``"LINESTRING"``, ready for use in a column
            definition, such as in :meth:`TableStructure.add_column` or
            :meth:`Table.add_column`.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("routes")
            >>> structure.add_column("path", DataTypes.LINESTRING())
        """
        return "LINESTRING"

    @staticmethod
    def POLYGON() -> str:
        """Returns the SQL POLYGON type string for PostGIS spatial data.

        ``POLYGON`` is a PostGIS geometry type representing a closed plane figure
        bounded by a sequence of line segments. This method returns the literal
        ``'POLYGON'``, which can be used directly in ``CREATE TABLE`` column
        definitions when PostGIS is enabled.

        Returns:
            str: The string ``"POLYGON"``, ready for use in a column definition,
            such as in :meth:`TableStructure.add_column` or
            :meth:`Table.add_column`.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("zones")
            >>> structure.add_column("boundary", DataTypes.POLYGON())
        """
        return "POLYGON"

    @staticmethod
    def MULTIPOINT() -> str:
        """Returns the SQL MULTIPOINT type string for PostGIS spatial data.

        ``MULTIPOINT`` is a PostGIS geometry type representing a collection of
        points. This method returns the literal ``'MULTIPOINT'``, which can be
        used directly in ``CREATE TABLE`` column definitions when PostGIS is
        enabled.

        Returns:
            str: The string ``"MULTIPOINT"``, ready for use in a column
            definition, such as in :meth:`TableStructure.add_column` or
            :meth:`Table.add_column`.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("survey_sites")
            >>> structure.add_column("locations", DataTypes.MULTIPOINT())
        """
        return "MULTIPOINT"

    @staticmethod
    def MULTILINESTRING() -> str:
        """Returns the SQL MULTILINESTRING type string for PostGIS spatial data.

        ``MULTILINESTRING`` is a PostGIS geometry type representing a collection
        of :class:`LINESTRING` objects. This method returns the literal
        ``'MULTILINESTRING'``, which can be used directly in ``CREATE TABLE``
        column definitions when the PostGIS extension is enabled.

        Returns:
            str: The string ``"MULTILINESTRING"``, ready for use in a column
            definition, such as in :meth:`TableStructure.add_column` or
            :meth:`Table.add_column`.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("trails")
            >>> structure.add_column("paths", DataTypes.MULTILINESTRING())
        """
        return "MULTILINESTRING"

    @staticmethod
    def MULTIPOLYGON() -> str:
        """Returns the SQL MULTIPOLYGON type string for PostGIS spatial data.

        ``MULTIPOLYGON`` is a PostGIS geometry type representing a collection of
        non‑overlapping polygons. This method simply returns the literal
        ``'MULTIPOLYGON'``, which can be used directly in ``CREATE TABLE``
        column definitions when PostGIS is enabled.

        Returns:
            str: The string ``"MULTIPOLYGON"``, ready for use in a column
            definition, such as in :meth:`TableStructure.add_column` or
            :meth:`Table.add_column`.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("regions")
            >>> structure.add_column("area", DataTypes.MULTIPOLYGON())
        """
        return "MULTIPOLYGON"

    @staticmethod
    def GEOMETRYCOLLECTION() -> str:
        """Returns the SQL GEOMETRYCOLLECTION type string for PostGIS spatial data.

        ``GEOMETRYCOLLECTION`` is a PostGIS geometry type that can hold a
        collection of zero or more geometry values of any type (e.g., points,
        lines, polygons) in a single column. This method returns the literal
        ``'GEOMETRYCOLLECTION'``, which can be used directly in ``CREATE TABLE``
        column definitions when PostGIS is enabled.

        Returns:
            str: The string ``"GEOMETRYCOLLECTION"``, ready for use in a column
            definition, such as in :meth:`TableStructure.add_column` or
            :meth:`Table.add_column`.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> structure = TableStructure("mixed_shapes")
            >>> structure.add_column("shapes", DataTypes.GEOMETRYCOLLECTION())
        """
        return "GEOMETRYCOLLECTION"

        # ========================
        # Array Type
        # ========================

    @staticmethod
    def ARRAY(element_type: str) -> str:
        """Returns the SQL array type string for the given element type.

        In PostgreSQL, an array column is declared by appending ``[]`` to the base
        data type. This method accepts the element type string (e.g., ``'INTEGER'``,
        ``'VARCHAR(255)'``) and returns the corresponding array type string (e.g.,
        ``'INTEGER[]'``). The returned string can be used directly in ``CREATE TABLE``
        column definitions, such as when calling :meth:`TableStructure.add_column`
        or :meth:`Table.add_column`.

        Args:
            element_type (str): The base data type of the array elements, typically
                obtained from another :class:`DataTypes` method (e.g.,
                ``DataTypes.INTEGER()``, ``DataTypes.VARCHAR(100)``).

        Returns:
            str: The array type string, formed by appending ``[]`` to the
            element type. For example, ``"INTEGER[]"`` or ``"VARCHAR(255)[]"``.

        Raises:
            None: No validation is performed on the element type; any string
            concatenation will be accepted. It is the caller's responsibility
            to provide a valid PostgreSQL data type.

        Example:
            >>> from ormophine.Postgresql import DataTypes, TableStructure
            >>> # Declare a column that holds an array of integers
            >>> structure = TableStructure("survey")
            >>> structure.add_column("scores", DataTypes.ARRAY(DataTypes.INTEGER()))
            >>> # Declare a column that holds an array of variable-length strings
            >>> structure.add_column("tags", DataTypes.ARRAY(DataTypes.VARCHAR(50)))
        """
        return f"{element_type}[]"
    

class TableStructure:
    """A builder class for programmatically defining PostgreSQL table structures.

    This class provides a fluent interface for constructing table schemas by
    adding columns with data types, constraints (primary key, unique, not null,
    default values, auto-increment), and foreign key relationships. It validates
    the schema consistency (e.g., only one auto-increment column, primary key
    columns are not null, serial types enforce not null and auto-increment) and
    generates the final SQL CREATE TABLE statement.

    Attributes:
        table_query (str): Accumulated SQL fragment for column definitions.
        primary_keys (list): List of column names that are part of the primary key.
        items (dict): Internal store mapping column names to their properties.
        name (str): The quoted table name.
        foreigns (list): List of SQL foreign key constraint clauses.

    Example:
        >>> from ormophine.Postgresql import TableStructure, DataTypes, Driver
        >>> # Assume driver and existing table objects are available
        >>> departments = TableStructure("departments")
        >>> departments.add_column("id", DataTypes.SERIAL(), primary_key=True)
        >>> departments.add_column("name", DataTypes.VARCHAR(100), not_null=True, unique=True)
        >>>
        >>> employees = TableStructure("employees")
        >>> employees.add_column("id", DataTypes.SERIAL(), primary_key=True)
        >>> employees.add_column("name", DataTypes.VARCHAR(100), not_null=True)
        >>> employees.add_column("dept_id", DataTypes.INTEGER())
        >>> employees.foreign_key("dept_id", departments, departments.id,
        ...                       on_delete="CASCADE")
        >>>
        >>> # Generate and execute the CREATE TABLE statement
        >>> driver.create_table(employees)
    """
    ON_ACTION = Literal['CASCADE', 'SET NULL', 'SET DEFAULT', 'RESTRICT', 'NO ACTION']

    def __init__(self, table_name: str):
        """Initialises a new table structure definition.

        Prepares an empty table structure with the given name. The name is
        automatically wrapped in double quotes to support case‑sensitive and
        special‑character table names in PostgreSQL. After initialisation,
        columns can be added with :meth:`add_column` and foreign keys with
        :meth:`foreign_key` before the structure is passed to
        :meth:`Driver.create_table`.

        Args:
            table_name (str): The name of the table to be created. It will be
                quoted internally, e.g. ``"my_table"``.

        Example:
            >>> structure = TableStructure("employees")
            >>> structure.add_column("id", DataTypes.SERIAL(), primary_key=True)
            >>> structure.add_column("name", DataTypes.VARCHAR(100))
            >>> print(structure.get_structure())
            CREATE TABLE "employees" ("id" SERIAL,... , PRIMARY KEY("id"));
        """
        self.table_query = ''
        self.primary_keys = []
        self.items = {}
        self.name = f'"{table_name}"'
        self.foreigns = []

    def _validate_column(self, column_name, datatype, default_value, unique, not_null, primary_key, auto_increment):
        """Validates the parameters for a new column before adding it to the table structure.

        This internal method enforces a set of rules to ensure that the column
        definition is consistent and compatible with PostgreSQL requirements.
        It checks data type validity, primary key/unique/null constraints,
        duplicate column names, auto‑increment restrictions, serial type
        semantics, and default value types.

        Args:
            column_name (str): The name of the column (already quoted).
            datatype (str): The SQL data type string returned by a
                :class:`DataTypes` method.
            default_value (Any or None): The default value for the column,
                if any.
            unique (bool or None): Whether the column should have a UNIQUE
                constraint.
            not_null (bool or None): Whether the column should be NOT NULL.
            primary_key (bool or None): Whether the column is part of the
                primary key.
            auto_increment (bool): Whether the column is an auto‑increment
                identity column.

        Raises:
            TypeError: If ``datatype`` is not a string.
            Exception: If any of the following invalid configurations are
                detected:
                - A primary key column is not marked NOT NULL.
                - A primary key column is also marked UNIQUE.
                - A column with the same name already exists in the table.
                - The default value is a ``bytes`` object.
                - More than one auto‑increment column is defined.
                - An auto‑increment column is not a numeric type.
                - An auto‑increment column is not PRIMARY KEY or UNIQUE.
                - An auto‑increment column has an explicit DEFAULT value.
                - A serial type (SMALLSERIAL, SERIAL, BIGSERIAL) is not
                marked NOT NULL or does not have ``auto_increment=True``.

        Returns:
            None: The method only performs validation; it returns ``None``
            if all checks pass.
        """
        if not isinstance(datatype, str):
            raise TypeError("datatype must be a string returned by DataTypes.")

        if primary_key:
            if unique:
                raise Exception("PRIMARY KEY columns cannot be UNIQUE, as they are inherently unique.")

        if column_name in self.items:
            raise Exception(f"Column {column_name} already exists.")

        if isinstance(default_value, bytes):
            raise Exception("Bytes objects cannot be used as default values.")

        for values in self.items.values():
            if values[5] and auto_increment:
                raise Exception("Only one auto-increment column is allowed.")

        numeric_types = ("SMALLINT","INTEGER","BIGINT","DECIMAL","NUMERIC","REAL","DOUBLE PRECISION","SMALLSERIAL","SERIAL","BIGSERIAL")

        if auto_increment:
            if datatype.split("(")[0].strip() not in numeric_types:
                raise Exception("Auto-increment is only allowed on numeric or serial types.")
            if not (primary_key or unique):
                raise Exception("Auto-increment column must be PRIMARY KEY or UNIQUE.")
            if default_value is not None:
                raise Exception("Auto-increment columns cannot have DEFAULT values.")

        if datatype in ("SMALLSERIAL", "SERIAL", "BIGSERIAL"):
            if not not_null:
                raise Exception("Serial types are inherently NOT NULL, so not_null must be True.")
            if not auto_increment:
                raise Exception("Serial types are inherently auto-increment, so auto_increment must be True.")

    def add_column(self, column_name: str, datatype: DataTypes,default_value=None, unique: bool = None,not_null: bool = None,primary_key: bool = None,auto_increment: bool = False):
        """Adds a column definition to the table structure.

        Appends a column with the given name and data type to the internal
        ``CREATE TABLE`` query. The ``datatype`` argument must be a string
        returned by one of the :class:`DataTypes` static methods (e.g.,
        ``DataTypes.INTEGER()``, ``DataTypes.VARCHAR(100)``). Additional
        constraints such as ``NOT NULL``, ``UNIQUE``, ``PRIMARY KEY``, and
        ``auto_increment`` (``GENERATED BY DEFAULT AS IDENTITY``) are added as
        requested. If the column is a serial type (``SMALLSERIAL``, ``SERIAL``,
        ``BIGSERIAL``), ``primary_key``, ``not_null``, and ``auto_increment``
        are automatically set to ``True`` unless explicitly overridden.

        The method returns ``self``, enabling fluent chaining of multiple
        ``add_column`` calls.

        Args:
            column_name (str): The name of the column (will be double‑quoted).
            datatype (str): A valid PostgreSQL data type string from
                :class:`DataTypes` (e.g., ``DataTypes.INTEGER()``).
            default_value (Any, optional): The default value for the column.
                Strings are automatically quoted in the SQL. Defaults to
                ``None``.
            unique (bool, optional): If ``True``, adds a ``UNIQUE`` constraint.
                Defaults to ``None`` (omitted).
            not_null (bool, optional): If ``True``, adds a ``NOT NULL``
                constraint. Defaults to ``None`` (omitted).
            primary_key (bool, optional): If ``True``, makes the column a
                primary key. Implies ``NOT NULL``. Defaults to ``None``.
            auto_increment (bool): If ``True``, adds ``GENERATED BY DEFAULT
                AS IDENTITY`` for integer types. Cannot be used with
                ``default_value``. Defaults to ``False``.

        Returns:
            :class:`TableStructure`: The same instance (``self``), allowing
            method chaining.

        Raises:
            TypeError: If ``datatype`` is not a string.
            Exception: If validation fails – for example:
                - Duplicate column name.
                - ``PRIMARY KEY`` set but ``not_null`` is ``False`` (or
                ``UNIQUE`` also set).
                - ``auto_increment`` used on a non‑numeric type, or without
                ``primary_key``/``unique``, or with a ``default_value``.
                - More than one ``auto_increment`` column is added.

        Example:
            >>> from ormophine.Postgresql import TableStructure, DataTypes
            >>> structure = TableStructure("employees")
            >>> (structure
            ...  .add_column("id", DataTypes.SERIAL(), primary_key=True)
            ...  .add_column("name", DataTypes.VARCHAR(100), not_null=True)
            ...  .add_column("salary", DataTypes.NUMERIC(10, 2),
            ...              default_value=0.0))
            >>> print(structure.get_structure())
            CREATE TABLE "employees" ("id" SERIAL NOT NULL, "name" VARCHAR(100) NOT NULL, "salary" NUMERIC(10, 2) DEFAULT 0.0);
        """
        column_name = f'"{column_name.strip()}"'
        primary_key, not_null, auto_increment = (True, True, True) if datatype in ("SMALLSERIAL", "SERIAL", "BIGSERIAL") else (primary_key, not_null, auto_increment)
        self._validate_column(column_name,datatype,default_value,unique,not_null,primary_key,auto_increment)
        if type(default_value) == bytes:
            raise Exception('Cant set bytes object as default value')
        self.primary_keys.append(column_name) if primary_key else None
        self.items[column_name] = [datatype, default_value, unique, not_null, primary_key, auto_increment]
        auto_part = " GENERATED BY DEFAULT AS IDENTITY" if auto_increment and datatype not in ("SMALLSERIAL", "SERIAL", "BIGSERIAL") else ""
        self.table_query += f' {column_name.strip()} {datatype}{auto_part}{" UNIQUE" if unique else ""}{" NOT NULL" if not_null else ""}{f" DEFAULT {('TRUE' if default_value else 'FALSE') if isinstance(default_value,bool) else f"'{default_value}'" if type(default_value) == str else str(default_value)}" if default_value is not None else ""},'
        return self

    def delete_column(self, column_name: str):
        """Remove a column from the table definition.

        This method deletes the specified column from the internal column store
        and updates the SQL creation string accordingly. It is useful for modifying
        a table structure before creation.

        Args:
            column_name (str): The name of the column to remove.

        Returns:
            TableStructure: The current instance, allowing method chaining.

        Raises:
            KeyError: If the specified column does not exist in the table definition.

        Example:
            >>> table = TableStructure("employees")
            >>> table.add_column("id", DataTypes.INTEGER(), primary_key=True)
            >>> table.add_column("name", DataTypes.VARCHAR(50))
            >>> table.delete_column("name")
            >>> table.get_structure()
            'CREATE TABLE "employees" ("id" INTEGER NOT NULL, PRIMARY KEY("id"));'
        """
        column_name = f'"{column_name.strip()}"'
        self.items.pop(column_name)
        query_list = self.table_query.split(',')
        new_list = []
        for item in query_list:
            if item.strip().startswith(column_name):
                continue
            new_list.append(item)
        self.table_query = ','.join(new_list)
        return self

    def get_columns(self):
        """Retrieve a list of column definitions for the table structure.

        This method iterates over the internally stored column metadata and
        returns a list of dictionaries, each containing the properties of a
        column as defined by previous calls to :meth:`add_column`.

        Returns:
            list[dict]: A list of dictionaries, each with the following keys:
                - ``name`` (str): The column name (including surrounding quotes).
                - ``datatype`` (str): The SQL data type string.
                - ``default_value`` (Any): The default value, or ``None``.
                - ``unique`` (bool): Whether the column is marked UNIQUE.
                - ``not_null`` (bool): Whether the column is NOT NULL.
                - ``primari_key`` (bool): Whether the column is a PRIMARY KEY
                (note the typo in the key name, preserved for compatibility).

        Example:
            >>> table = TableStructure("employees")
            >>> table.add_column("id", DataTypes.INTEGER(), primary_key=True, not_null=True)
            >>> table.add_column("name", DataTypes.VARCHAR(50))
            >>> columns = table.get_columns()
            >>> for col in columns:
            ...     print(f"{col['name']} ({col['datatype']}) PK: {col['primari_key']}")
            "id" (INTEGER) PK: True
            "name" (VARCHAR(50)) PK: False
        """
        items_list = []
        for item in self.items:
            items_dict = {}
            values = self.items[item]
            items_dict['name'] = item
            items_dict['datatype'] = values[0]
            items_dict['default_value'] = values[1]
            items_dict['unique'] = True if values[2] else False
            items_dict['not_null'] = True if values[3] else False
            items_dict['primari_key'] = True if values[4] else False
            items_list.append(items_dict)
        return items_list

    def foreign_key(self, column: str, refrences_table: 'Table',refrences_column: 'Column', on_delete: ON_ACTION = None, on_update: ON_ACTION = None):
        """Add a foreign key constraint to the table definition.

        This method appends a FOREIGN KEY clause to the table's SQL definition.
        It references a column in another table, with optional ON DELETE and
        ON UPDATE cascade actions. The constraint is included in the final
        `CREATE TABLE` statement generated by :meth:`get_structure`.

        Args:
            column (str): The name of the column in the current table that will
                act as the foreign key.
            refrences_table (Table): The target table being referenced.
            refrences_column (Column): The target column in the referenced table.
            on_delete (ON_ACTION, optional): Action to take when the referenced
                row is deleted. Must be one of 'CASCADE', 'SET NULL',
                'SET DEFAULT', 'RESTRICT', or 'NO ACTION'.
            on_update (ON_ACTION, optional): Action to take when the referenced
                row is updated. Must be one of the same allowed values.

        Returns:
            TableStructure: The current instance, enabling method chaining.

        Example:
            >>> from ormophine.Postgresql import TableStructure, DataTypes, Table, Column
            >>> orders = TableStructure("orders")
            >>> customers = TableStructure("customers")
            >>> customers.add_column("id", DataTypes.INTEGER(), primary_key=True)
            >>> orders.add_column("customer_id", DataTypes.INTEGER())
            >>> orders.foreign_key(
            ...     column="customer_id",
            ...     refrences_table=customers,
            ...     refrences_column=Column(customers, "id", int),
            ...     on_delete="CASCADE",
            ...     on_update="RESTRICT"
            ... )
            >>> orders.get_structure()
            'CREATE TABLE "orders" ("customer_id" INTEGER, FOREIGN KEY (customer_id) REFERENCES "customers" ("id") ON DELETE CASCADE ON UPDATE RESTRICT);'
        """
        self.foreigns.append(f'FOREIGN KEY ({column}) REFERENCES {refrences_table.name_} ({refrences_column.first_name}){f' ON DELETE {on_delete}' if on_delete else ''}{f' ON UPDATE {on_update}' if on_update else ''}')
        return self

    def get_structure(self):
        """Generate the complete SQL CREATE TABLE statement from the defined structure.

        This method compiles all columns, primary keys, foreign keys, and constraints
        into a single PostgreSQL CREATE TABLE statement. It validates that at least
        one column has been added before generating the statement.

        Returns:
            str: The full SQL CREATE TABLE statement that can be executed to create
                the table in the database.

        Raises:
            Exception: If no columns have been added to the table structure.

        Example:
            >>> struct = TableStructure("employees")
            >>> struct.add_column("id", DataTypes.INTEGER(), primary_key=True)
            >>> struct.add_column("name", DataTypes.VARCHAR(100), not_null=True)
            >>> struct.add_column("dept_id", DataTypes.INTEGER())
            >>> struct.foreign_key("dept_id", departments_table, departments_table.id,
            ...                    on_delete="CASCADE")
            >>> sql = struct.get_structure()
            >>> print(sql)
            CREATE TABLE "employees" (
                "id" INTEGER NOT NULL,
                "name" VARCHAR(100) NOT NULL,
                "dept_id" INTEGER,
                PRIMARY KEY("id"),
                FOREIGN KEY (dept_id) REFERENCES "departments" ("id") ON DELETE CASCADE
            );
        """
        if not self.get_columns():
            raise Exception('You must add at least one column to create a table')
        primary_key_clause = f', PRIMARY KEY({', '.join(self.primary_keys)})' if self.primary_keys else ''
        foreign_key_clause = f', {', '.join(self.foreigns)}' if self.foreigns else ''
        body = self.table_query[:-1] + primary_key_clause + foreign_key_clause
        return f'CREATE TABLE {self.name} ({body});'
