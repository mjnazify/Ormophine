from __future__ import annotations
from typing import Literal
import re

class DataTypes:
    """
    Factory for SQLite column definitions with built‑in CHECK constraints.

    This class provides static methods that generate SQL column definition
    strings for various data types. Each method returns a string that
    includes the column name placeholder ``'my_saulted_x'``, the SQLite
    type, and optional ``CHECK`` constraints to enforce limits, ranges,
    or allowed values.

    The placeholder ``'my_saulted_x'`` is a special marker that is
    replaced with the actual column name when the definition is used in
    a :class:`TableStructure` (specifically by :meth:`TableStructure.add_column`).
    This design allows the same definition to be reused for multiple
    columns.

    All methods are static and are meant to be called directly on the
    class, e.g., ``DataTypes.INTEGER(unsigned=True)``.

    Supported data types include:
      - Integer types: :meth:`INTEGER`, :meth:`INT`, :meth:`BIGINT`,
        :meth:`TINYINT`, :meth:`SMALLINT`, :meth:`MEDIUMINT`
      - Floating‑point types: :meth:`REAL`, :meth:`FLOAT`, :meth:`DOUBLE`,
        :meth:`DECIMAL`, :meth:`NUMERIC`
      - Text types: :meth:`TEXT`, :meth:`VARCHAR`, :meth:`CHAR`
      - Binary: :meth:`BLOB`
      - Boolean: :meth:`BOOLEAN`
      - Enum: :meth:`ENUM`
      - Custom: :meth:`CUSTOM`
      - Other: :meth:`NULL`

    Each method accepts optional parameters to define constraints such as
    minimum/maximum values, unsigned ranges, length limits, or allowed
    enumerations. These constraints are translated into SQLite ``CHECK``
    clauses.

    Example:
        Using :class:`DataTypes` with :class:`TableStructure` to define
        a table::

            from ormophine.Sqlite import DataTypes, TableStructure

            # Define a table structure
            structure = TableStructure('products', strict=True)

            # Add columns using DataTypes
            structure.add_column(
                column_name='id',
                datatype=DataTypes.INTEGER(unsigned=True, min_val=1)
            )
            structure.add_column(
                column_name='name',
                datatype=DataTypes.VARCHAR(max_length=100)
            )
            structure.add_column(
                column_name='price',
                datatype=DataTypes.DECIMAL(precision=10, scale=2, unsigned=True)
            )
            structure.add_column(
                column_name='status',
                datatype=DataTypes.ENUM('active', 'inactive', 'pending')
            )
            structure.add_column(
                column_name='is_active',
                datatype=DataTypes.BOOLEAN()
            )

            # Create the table using Driver
            db = Driver('store.db')
            db.create_table(structure)
    """

    @staticmethod
    def INTEGER(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """Generate a SQLite column definition for an INTEGER type with optional constraints.

        This method returns a string that can be used as a column definition in a
        ``CREATE TABLE`` or ``ALTER TABLE ADD COLUMN`` statement. The placeholder
        ``my_saulted_x`` is used for the column name and will be replaced by the
        actual column name when used (e.g., in :class:`TableStructure.add_column`).

        The method supports range constraints via ``min_val`` and ``max_val``, and
        an unsigned constraint. If multiple constraints are given, they are combined
        with ``AND`` in a ``CHECK`` clause. If no constraints are specified, the
        definition is simply ``my_saulted_x INTEGER``.

        Args:
            min_val (int, optional): Minimum allowed value (inclusive). If provided,
                adds a ``CHECK(my_saulted_x >= min_val)`` constraint.
            max_val (int, optional): Maximum allowed value (inclusive). If provided,
                adds a ``CHECK(my_saulted_x <= max_val)`` constraint.
            unsigned (bool, optional): If ``True``, adds a
                ``CHECK(my_saulted_x >= 0)`` constraint. This is applied in addition
                to any min/max constraints (but does not override them). Defaults to
                ``False``.

        Returns:
            str: A SQL column definition string. Examples:
                - ``"my_saulted_x INTEGER"``
                - ``"my_saulted_x INTEGER CHECK(my_saulted_x >= 0)"``
                - ``"my_saulted_x INTEGER CHECK(my_saulted_x >= 1 AND my_saulted_x <= 100)"``

        Example:
            Using with :class:`TableStructure`:

            >>> from ormophine.Sqlite import DataTypes, TableStructure
            >>> table = TableStructure('products')
            >>> table.add_column('id', DataTypes.INTEGER(unsigned=True))
            >>> table.add_column('price', DataTypes.INTEGER(min_val=0, max_val=9999))
            >>> print(table.get_structure())
            CREATE TABLE [products] ( [id] INTEGER CHECK([id] >= 0), [price] INTEGER CHECK([price] >= 0 AND [price] <= 9999),) ;
        """
        if min_val is not None and max_val is not None and min_val > max_val:
            raise ValueError("min_val cannot be greater than max_val")
        checks = []
        if unsigned and min_val is None:
            checks.append("my_saulted_x >= 0")
        if min_val is not None:
            checks.append(f"my_saulted_x >= {min_val}")
        if max_val is not None:
            checks.append(f"my_saulted_x <= {max_val}")
        if checks:
            return f"my_saulted_x INTEGER CHECK({' AND '.join(checks)})"
        return f"my_saulted_x INTEGER"

    @staticmethod
    def REAL(min_val: float = None, max_val: float = None, unsigned: bool = False) -> str:
        """Generate a column definition string for a floating‑point number (REAL).

        This method returns a SQLite column definition for a REAL (8‑byte float)
        column, optionally with CHECK constraints for range and/or unsigned
        values. The placeholder ``my_saulted_x`` in the returned string will
        be replaced by the actual column name when used in table creation or
        alteration.

        If ``unsigned`` is ``True``, a constraint ``my_saulted_x >= 0`` is
        added. If ``min_val`` and/or ``max_val`` are provided, additional
        range constraints are generated. All constraints are combined with
        AND.

        Args:
            min_val (float, optional): The minimum allowed value (inclusive).
                If provided, a ``>=`` constraint is added.
            max_val (float, optional): The maximum allowed value (inclusive).
                If provided, a ``<=`` constraint is added.
            unsigned (bool, optional): If ``True``, restricts values to
                non‑negative (``>= 0``). Defaults to ``False``.

        Returns:
            str: A SQL column definition string, e.g.,
            ``"my_saulted_x REAL CHECK(my_saulted_x >= 0 AND my_saulted_x <= 100)"``.

        Example:
            Using the method in a table structure::

                from ormophine.Sqlite import DataTypes, TableStructure

                table = TableStructure('products')
                table.add_column('price', DataTypes.REAL(min_val=0.0, max_val=999.99))
                # The column definition will be:
                # my_saulted_x REAL CHECK(my_saulted_x >= 0.0 AND my_saulted_x <= 999.99)
                # which is then replaced with the column name 'price' to produce:
                # [price] REAL CHECK([price] >= 0.0 AND [price] <= 999.99)
        """
        if unsigned and min_val is not None and min_val < 0:
            raise ValueError("Cannot use unsigned=True with negative min_val")
        checks = []
        if unsigned:
            checks.append("my_saulted_x >= 0")
        if min_val is not None:
            checks.append(f"my_saulted_x >= {min_val}")
        if max_val is not None:
            checks.append(f"my_saulted_x <= {max_val}")
        if checks:
            return f"my_saulted_x REAL CHECK({' AND '.join(checks)})"
        return f"my_saulted_x REAL"

    @staticmethod
    def FLOAT(min_val: float = None, max_val: float = None, unsigned: bool = False) -> str:
        """Define a floating-point column with optional range and unsigned constraints.

        This method is a synonym for :meth:`REAL` and generates a SQL column
        definition of type ``REAL`` (8‑byte floating‑point number). It supports
        the same validation options: an ``unsigned`` flag to enforce non‑negative
        values, and optional ``min_val``/``max_val`` to enforce a value range.

        The placeholder ``my_saulted_x`` in the generated SQL will be replaced
        with the actual column name by the :class:`TableStructure` builder.

        Args:
            min_val (float, optional): Minimum allowed value (inclusive). If
                provided, adds a ``CHECK(my_saulted_x >= min_val)`` constraint.
            max_val (float, optional): Maximum allowed value (inclusive). If
                provided, adds a ``CHECK(my_saulted_x <= max_val)`` constraint.
            unsigned (bool, optional): If ``True``, enforces that the value is
                non‑negative by adding ``CHECK(my_saulted_x >= 0)``. Defaults
                to ``False``.

        Returns:
            str: A SQL column definition string with the appropriate ``REAL``
            type and optional ``CHECK`` constraints. The placeholder
            ``my_saulted_x`` is used for the column name.

        Example:
            Creating a table with a floating‑point price column that must be
            between 0 and 999.99::

                from ormophine.Sqlite import TableStructure, DataTypes

                table = TableStructure('products')
                table.add_column(
                    column_name='price',
                    datatype=DataTypes.FLOAT(min_val=0.0, max_val=999.99)
                )
                # The generated column definition will be:
                # my_saulted_x REAL CHECK(my_saulted_x >= 0.0 AND my_saulted_x <= 999.99)
                # (after replacing my_saulted_x with [price])
        """
        return DataTypes.REAL(min_val, max_val, unsigned)

    @staticmethod
    def DOUBLE(min_val: float = None, max_val: float = None, unsigned: bool = False) -> str:
        """Synonym for :meth:`REAL` for compatibility with other databases.

        This method is an alias for the :meth:`REAL` data type, providing a
        name that is commonly used in other SQL databases (e.g., MySQL,
        PostgreSQL). It returns the same column definition string, including
        optional range and unsigned checks, as the REAL type.

        The returned string uses the placeholder ``my_saulted_x``, which
        will be replaced by the actual column name when used in
        :meth:`TableStructure.add_column` or :meth:`Table.add_column`.

        Args:
            min_val (float, optional): Minimum allowed value for the column.
                If provided, a ``CHECK(my_saulted_x >= min_val)`` constraint
                is added. Defaults to ``None``.
            max_val (float, optional): Maximum allowed value for the column.
                If provided, a ``CHECK(my_saulted_x <= max_val)`` constraint
                is added. Defaults to ``None``.
            unsigned (bool, optional): If ``True``, adds a
                ``CHECK(my_saulted_x >= 0)`` constraint (unless a custom
                ``min_val`` is also given). Defaults to ``False``.

        Returns:
            str: A column definition string in the format
            ``"my_saulted_x REAL"`` with optional ``CHECK`` constraints.

        Example:
            Creating a table with a DOUBLE column::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('measurements')
                structure.add_column('temperature', DataTypes.DOUBLE(
                    min_val=-273.15, max_val=1000.0
                ))
                # Adds column: my_saulted_x REAL CHECK(my_saulted_x >= -273.15 AND my_saulted_x <= 1000.0)
        """
        return DataTypes.REAL(min_val, max_val, unsigned)

    @staticmethod
    def DECIMAL(precision: int = None, scale: int = None,
                min_val: float = None, max_val: float = None,
                unsigned: bool = False) -> str:
        """
        Generate a column definition string for a fixed‑point decimal type.

        This method returns a SQLite column definition for a decimal number,
        stored as a ``REAL`` type, with optional ``CHECK`` constraints for
        range validation. The placeholder ``my_saulted_x`` will be replaced
        by the actual column name when the definition is used in a table
        creation or addition.

        The method infers default minimum and maximum values from the
        ``precision`` and ``scale`` parameters if they are provided.
        - If both ``precision`` and ``scale`` are given, the default range
        is ``[0, 10^(precision-scale) - 10^(-scale)]`` for unsigned,
        or ``[-default_max, default_max]`` for signed.
        - If only ``precision`` is given, the default range is
        ``[0, 10^precision - 1]`` for unsigned, or symmetric around zero
        for signed.
        - If neither is given, no default range is applied, but custom
        ``min_val`` and ``max_val`` are still respected.

        The generated string can be used directly in a ``CREATE TABLE`` or
        ``ALTER TABLE ADD COLUMN`` statement.

        Args:
            precision (int, optional): The total number of digits (including
                fractional part). Used only to compute default range bounds.
            scale (int, optional): The number of digits after the decimal
                point. Used together with ``precision`` to compute the
                default maximum value. If not given, default range is
                computed as if scale = 0.
            min_val (float, optional): Custom minimum allowed value.
                Overrides any default inferred from precision/scale.
            max_val (float, optional): Custom maximum allowed value.
                Overrides any default inferred from precision/scale.
            unsigned (bool, optional): If ``True``, the default range is
                non‑negative (minimum = 0). This is ignored if a custom
                ``min_val`` is provided. Defaults to ``False``.

        Returns:
            str: A complete column definition string, e.g.,
            ``"my_saulted_x REAL CHECK(my_saulted_x BETWEEN 0 AND 99.99)"``.
            The placeholder ``my_saulted_x`` must be replaced with the actual
            column name before use.

        Raises:
            ValueError: If both ``precision`` and ``scale`` are provided and
                ``scale`` is greater than ``precision`` (impossible to represent).

        Example:
            Using ``DECIMAL`` in a table definition::

                from ormophine.Sqlite import DataTypes, TableStructure

                ts = TableStructure('products')
                ts.add_column('price', DataTypes.DECIMAL(precision=10, scale=2))
                # Produces: "my_saulted_x REAL CHECK(my_saulted_x BETWEEN -99999999.99 AND 99999999.99)"

                # Custom constraints
                ts.add_column('rating', DataTypes.DECIMAL(min_val=0, max_val=5))
                # Produces: "my_saulted_x REAL CHECK(my_saulted_x >= 0 AND my_saulted_x <= 5)"

                # Unsigned with precision/scale
                ts.add_column('score', DataTypes.DECIMAL(precision=5, scale=2, unsigned=True))
                # Produces: "my_saulted_x REAL CHECK(my_saulted_x >= 0 AND my_saulted_x BETWEEN 0 AND 999.99)"
        """
        if precision is not None and precision < 1:
            raise ValueError("precision must be at least 1")
        if scale is not None and scale < 0:
            raise ValueError("scale must be >= 0")
        if precision is not None and scale is not None and scale > precision:
            raise ValueError("scale cannot be greater than precision")
        checks = []
        if unsigned:
            checks.append("my_saulted_x >= 0")
        if precision is not None and scale is not None:
            default_max = 10 ** (precision - scale) - 10 ** (-scale)
            default_min = 0 if unsigned else -default_max
            actual_min = min_val if min_val is not None else default_min
            actual_max = max_val if max_val is not None else default_max
            checks.append(f"my_saulted_x BETWEEN {actual_min} AND {actual_max}")
        elif precision is not None and scale is None:
            default_max = 10 ** precision - 1
            default_min = 0 if unsigned else -default_max
            actual_min = min_val if min_val is not None else default_min
            actual_max = max_val if max_val is not None else default_max
            checks.append(f"my_saulted_x BETWEEN {actual_min} AND {actual_max}")
        elif scale is not None:  # <-- افزودن این حالت
            # اگر فقط scale داده شده، یک محدوده پیش‌فرض در نظر بگیرید
            default_max = 10 ** (10 - scale) - 10 ** (-scale)  # فرض precision=10
            default_min = 0 if unsigned else -default_max
            actual_min = min_val if min_val is not None else default_min
            actual_max = max_val if max_val is not None else default_max
            checks.append(f"my_saulted_x BETWEEN {actual_min} AND {actual_max}")
        else:
            if min_val is not None:
                checks.append(f"my_saulted_x >= {min_val}")
            if max_val is not None:
                checks.append(f"my_saulted_x <= {max_val}")
        if checks:
            return f"my_saulted_x REAL CHECK({' AND '.join(checks)})"
        return f"my_saulted_x REAL"

    @staticmethod
    def NUMERIC(precision: int = None, scale: int = None,
                min_val: float = None, max_val: float = None,
                unsigned: bool = False) -> str:
        """Synonym for :meth:`DECIMAL`.

        This method is an alias for :meth:`DECIMAL` and returns a fixed-point
        decimal column definition for SQLite. The generated SQL uses the
        placeholder ``my_saulted_x`` and is later replaced with the actual
        column name during table creation.

        When both ``precision`` and ``scale`` are provided, a default numeric
        range is inferred from those values. If only ``precision`` is given,
        the default maximum becomes ``10^precision - 1``. Custom bounds supplied
        through ``min_val`` and ``max_val`` override the inferred defaults.

        Args:
            precision (int, optional): Total number of digits, including the
                fractional part.
            scale (int, optional): Number of digits after the decimal point.
            min_val (float, optional): Minimum allowed value.
            max_val (float, optional): Maximum allowed value.
            unsigned (bool, optional): If ``True``, add a non-negative check.
                Defaults to ``False``.

        Returns:
            str: A column definition fragment such as
            ``'my_saulted_x REAL CHECK(...)'``.

        Example:
            Using ``NUMERIC`` in a :class:`TableStructure`::

                from Ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('products')
                structure.add_column(
                    column_name='price',
                    datatype=DataTypes.NUMERIC(precision=10, scale=2, unsigned=True)
                )
        """
        return DataTypes.DECIMAL(precision, scale, min_val, max_val, unsigned)

    @staticmethod
    def TEXT(min_length: int = None, max_length: int = None) -> str:
        """
        Generate a column definition for a TEXT type with optional length constraints.

        This method returns a SQLite column definition string for a ``TEXT`` column.
        If ``min_length`` and/or ``max_length`` are provided, the definition includes
        a ``CHECK`` constraint that enforces the length range using the SQLite
        ``LENGTH()`` function. The placeholder ``my_saulted_x`` in the returned
        string is replaced with the actual column name when the table is created.

        Args:
            min_length (int, optional): Minimum allowed length (in characters) for
                the text value. If provided, adds a check like
                ``LENGTH(my_saulted_x) >= min_length``.
            max_length (int, optional): Maximum allowed length (in characters) for
                the text value. If provided, adds a check like
                ``LENGTH(my_saulted_x) <= max_length``.

        Returns:
            str: A column definition fragment that can be used inside a
            :class:`TableStructure` definition. For example:
            ``'my_saulted_x TEXT CHECK(LENGTH(my_saulted_x) >= 1 AND LENGTH(my_saulted_x) <= 100)'``.

        Example:
            Using ``TEXT`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('users')
                structure.add_column(
                    column_name='username',
                    datatype=DataTypes.TEXT(min_length=3, max_length=20)
                )
                # Generated SQL fragment:
                # my_saulted_x TEXT CHECK(LENGTH(my_saulted_x) >= 3 AND LENGTH(my_saulted_x) <= 20)

                # No length constraints:
                structure.add_column(
                    column_name='bio',
                    datatype=DataTypes.TEXT()
                )
                # Returns: my_saulted_x TEXT
        """
        checks = []
        if min_length is not None:
            checks.append(f"LENGTH(my_saulted_x) >= {min_length}")
        if max_length is not None:
            checks.append(f"LENGTH(my_saulted_x) <= {max_length}")
        if checks:
            return f"my_saulted_x TEXT CHECK({' AND '.join(checks)})"
        return f"my_saulted_x TEXT"

    def BLOB() -> str:
        """Generate a column definition for binary large object (BLOB) data.

        This method returns a column definition string for storing binary data
        (e.g., images, files, serialized objects) in SQLite. The generated
        string contains the placeholder ``'my_saulted_x'`` which is replaced
        with the actual column name when used in a :class:`TableStructure`
        definition.

        SQLite's ``BLOB`` type stores data exactly as provided, without any
        character set conversion. It is suitable for any binary content.

        Returns:
            str: A column definition fragment (e.g., ``'my_saulted_x BLOB'``).

        Example:
            Using ``BLOB`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('files')
                structure.add_column(
                    column_name='file_data',
                    datatype=DataTypes.BLOB()
                )
                # Generated column: my_saulted_x BLOB
        """
        return f"my_saulted_x BLOB"

    @staticmethod
    def NULL() -> str:
        """Generate a column definition for a NULL‑type column.

        This method returns a SQL column definition fragment using SQLite's
        ``NULL`` type. In SQLite, ``NULL`` is a valid type affinity, but it is
        rarely used explicitly; columns without a specified type affinity
        default to ``NUMERIC``. This method is provided primarily for
        completeness and compatibility.

        The returned string contains the placeholder ``'my_saulted_x'``, which
        is replaced with the actual column name at table creation time (e.g.,
        by :class:`TableStructure.add_column`).

        Returns:
            str: A column definition fragment in the form
            ``'my_saulted_x NULL'``.

        Example:
            Using ``NULL`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('example')
                structure.add_column(
                    column_name='nullable_col',
                    datatype=DataTypes.NULL()
                )
                # Generated column: my_saulted_x NULL

        Note:
            This type is rarely needed; consider using other affinities
            (e.g., ``TEXT``, ``INTEGER``) for most use cases.
        """
        return f"my_saulted_x NULL"

    @staticmethod
    def VARCHAR(min_length: int = None, max_length: int = None) -> str:
        """Create a column definition for a variable-length string (VARCHAR).

        This method is a synonym for :meth:`TEXT`. It generates a column
        definition fragment for a string column with optional length
        constraints, enforced by ``CHECK`` clauses using the ``LENGTH()``
        function. The placeholder ``'my_saulted_x'`` is used in the generated
        string and is replaced by the actual column name at table creation time.

        If ``min_length`` is provided, a constraint ``LENGTH(my_saulted_x) >= min_length``
        is added. If ``max_length`` is provided, a constraint
        ``LENGTH(my_saulted_x) <= max_length`` is added. If neither is given,
        no constraints are imposed and the column is simply of type ``TEXT``.

        Args:
            min_length (int, optional): Minimum allowed number of characters.
            max_length (int, optional): Maximum allowed number of characters.

        Returns:
            str: A column definition fragment (e.g.,
            ``'my_saulted_x TEXT CHECK(LENGTH(my_saulted_x) <= 255)'``) that
            can be used in a :class:`TableStructure` definition.

        Example:
            Using ``VARCHAR`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('users')
                structure.add_column(
                    column_name='username',
                    datatype=DataTypes.VARCHAR(max_length=50)
                )
                # Generated column: my_saulted_x TEXT CHECK(LENGTH(my_saulted_x) <= 50)

                # With both min and max length
                structure.add_column(
                    column_name='code',
                    datatype=DataTypes.VARCHAR(min_length=3, max_length=10)
                )
        """
        return DataTypes.TEXT(min_length, max_length)

    @staticmethod
    def TINYINT(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """
        Generate a column definition for a tiny integer with optional range checks.

        SQLite does not have a native TINYINT type, but this method returns an
        ``INTEGER`` column definition with a ``CHECK`` constraint that enforces
        the range typical for a tiny integer. By default, the signed range is
        -128 to 127, and the unsigned range is 0 to 255. These defaults can be
        overridden by providing custom ``min_val`` and/or ``max_val``.

        The generated string contains the placeholder ``'my_saulted_x'``, which
        will be replaced by the actual column name when used in a
        :class:`TableStructure` definition.

        Args:
            min_val (int, optional): The minimum allowed value. If not provided,
                uses the default for the chosen signed/unsigned mode.
            max_val (int, optional): The maximum allowed value. If not provided,
                uses the default for the chosen signed/unsigned mode.
            unsigned (bool, optional): If ``True``, the default range is 0–255;
                otherwise, the default range is -128–127. Defaults to ``False``.

        Returns:
            str: A column definition fragment, e.g.,
            ``'my_saulted_x INTEGER CHECK(my_saulted_x BETWEEN -128 AND 127)'``.
            If no constraints are needed, returns ``'my_saulted_x INTEGER'``.

        Example:
            Creating a table with a TINYINT column::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('users')
                structure.add_column(
                    column_name='age',
                    datatype=DataTypes.TINYINT(unsigned=True)  # 0–255
                )
                # Generated fragment: my_saulted_x INTEGER CHECK(my_saulted_x BETWEEN 0 AND 255)

                # Custom range: values between 10 and 20
                structure.add_column(
                    column_name='score',
                    datatype=DataTypes.TINYINT(min_val=10, max_val=20)
                )
                # Generated fragment: my_saulted_x INTEGER CHECK(my_saulted_x BETWEEN 10 AND 20)
        """
        if unsigned:
            default_min, default_max = 0, 255
        else:
            default_min, default_max = -128, 127
        actual_min = min_val if min_val is not None else default_min
        actual_max = max_val if max_val is not None else default_max
        if actual_min is not None or actual_max is not None:
            return f"my_saulted_x INTEGER CHECK(my_saulted_x BETWEEN {actual_min} AND {actual_max})"
        return f"my_saulted_x INTEGER"

    @staticmethod
    def SMALLINT(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """Generate a column definition for a SMALLINT with optional CHECK constraints.

        This method returns a SQLite column definition string suitable for a
        small integer type. The default range is -32,768 to 32,767 when
        ``unsigned=False``, and 0 to 65,535 when ``unsigned=True``.
        Custom minimum and maximum values can be specified to override the
        defaults, and the resulting ``CHECK`` clause ensures that the column
        values stay within the defined bounds.

        The placeholder ``'my_saulted_x'`` in the returned string is replaced
        with the actual column name during table creation (typically by the
        :meth:`TableStructure.add_column` method).

        Args:
            min_val (int, optional): The minimum allowed value. If provided,
                overrides the default minimum for the chosen signed/unsigned
                mode.
            max_val (int, optional): The maximum allowed value. If provided,
                overrides the default maximum for the chosen signed/unsigned
                mode.
            unsigned (bool, optional): If ``True``, the default range is
                0 to 65,535. If ``False`` (the default), the default range is
                -32,768 to 32,767.

        Returns:
            str: A column definition fragment like
            ``'my_saulted_x INTEGER CHECK(my_saulted_x BETWEEN -32768 AND 32767)'``
            or a plain ``'my_saulted_x INTEGER'`` if no constraints apply.

        Example:
            Using ``SMALLINT`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('scores')
                structure.add_column(
                    column_name='score',
                    datatype=DataTypes.SMALLINT(unsigned=True)  # 0..65535
                )
                structure.add_column(
                    column_name='temperature',
                    datatype=DataTypes.SMALLINT(min_val=-100, max_val=100)
                )
        """
        if unsigned:
            default_min, default_max = 0, 65535
        else:
            default_min, default_max = -32768, 32767
        actual_min = min_val if min_val is not None else default_min
        actual_max = max_val if max_val is not None else default_max
        if actual_min is not None or actual_max is not None:
            return f"my_saulted_x INTEGER CHECK(my_saulted_x BETWEEN {actual_min} AND {actual_max})"
        return f"my_saulted_x INTEGER"

    @staticmethod
    def MEDIUMINT(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """Generate a column definition for a MEDIUMINT with optional CHECK constraints.

        This method returns a SQLite column definition string for a medium‑sized
        integer type. The default range is -8,388,608 to 8,388,607 when
        ``unsigned=False``, and 0 to 16,777,215 when ``unsigned=True``.
        Custom minimum and maximum values can be specified to override the
        defaults, and the resulting ``CHECK`` clause ensures that the column
        values stay within the defined bounds.

        The placeholder ``'my_saulted_x'`` in the returned string is replaced
        with the actual column name during table creation (typically by the
        :meth:`TableStructure.add_column` method).

        Args:
            min_val (int, optional): The minimum allowed value. If provided,
                overrides the default minimum for the chosen signed/unsigned
                mode.
            max_val (int, optional): The maximum allowed value. If provided,
                overrides the default maximum for the chosen signed/unsigned
                mode.
            unsigned (bool, optional): If ``True``, the default range is
                0 to 16,777,215. If ``False`` (the default), the default range
                is -8,388,608 to 8,388,607.

        Returns:
            str: A column definition fragment like
            ``'my_saulted_x INTEGER CHECK(my_saulted_x BETWEEN -8388608 AND 8388607)'``
            or a plain ``'my_saulted_x INTEGER'`` if no constraints apply.

        Example:
            Using ``MEDIUMINT`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('events')
                structure.add_column(
                    column_name='counter',
                    datatype=DataTypes.MEDIUMINT(unsigned=True)  # 0..16777215
                )
                structure.add_column(
                    column_name='temperature',
                    datatype=DataTypes.MEDIUMINT(min_val=-1000, max_val=1000)
                )
        """
        if unsigned:
            default_min, default_max = 0, 16777215
        else:
            default_min, default_max = -8388608, 8388607
        actual_min = min_val if min_val is not None else default_min
        actual_max = max_val if max_val is not None else default_max
        if actual_min is not None or actual_max is not None:
            return f"my_saulted_x INTEGER CHECK(my_saulted_x BETWEEN {actual_min} AND {actual_max})"
        return f"my_saulted_x INTEGER"

    @staticmethod
    def INT(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """Generate a column definition for an integer with optional CHECK constraints.

        This method returns a SQLite column definition string for an ``INTEGER``
        type (64‑bit signed). It supports optional range constraints via
        ``min_val`` and ``max_val``, and an ``unsigned`` flag that adds a
        ``CHECK(my_saulted_x >= 0)`` unless a custom ``min_val`` is explicitly
        provided. All constraints are combined into a single ``CHECK`` clause.

        The placeholder ``'my_saulted_x'`` in the returned string is replaced
        with the actual column name during table creation (typically by the
        :meth:`TableStructure.add_column` method).

        Args:
            min_val (int, optional): Minimum allowed value. If provided, adds
                ``CHECK(my_saulted_x >= min_val)``.
            max_val (int, optional): Maximum allowed value. If provided, adds
                ``CHECK(my_saulted_x <= max_val)``.
            unsigned (bool, optional): If ``True`` and no explicit ``min_val``
                is given, adds ``CHECK(my_saulted_x >= 0)``. Defaults to
                ``False``.

        Returns:
            str: A column definition fragment. If constraints are present, the
            string includes a ``CHECK`` clause, e.g.:
            ``'my_saulted_x INTEGER CHECK(my_saulted_x >= 0 AND my_saulted_x <= 100)'``.
            If no constraints, returns ``'my_saulted_x INTEGER'``.

        Example:
            Using ``INT`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('products')
                structure.add_column(
                    column_name='quantity',
                    datatype=DataTypes.INT(min_val=0, max_val=9999)
                )
                # Generated column: my_saulted_x INTEGER CHECK(my_saulted_x >= 0 AND my_saulted_x <= 9999)

                structure.add_column(
                    column_name='score',
                    datatype=DataTypes.INT(unsigned=True)
                )
                # Generated column: my_saulted_x INTEGER CHECK(my_saulted_x >= 0)
        """
        checks = []
        if unsigned and min_val is None:
            checks.append("my_saulted_x >= 0")
        if min_val is not None:
            checks.append(f"my_saulted_x >= {min_val}")
        if max_val is not None:
            checks.append(f"my_saulted_x <= {max_val}")
        if checks:
            return f"my_saulted_x INTEGER CHECK({' AND '.join(checks)})"
        return f"my_saulted_x INTEGER"

    @staticmethod
    def BIGINT(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """Generate a column definition for a BIGINT (64‑bit integer) with optional constraints.

        This method is an alias for :meth:`INT` and returns a column definition
        string for a 64‑bit integer. In SQLite, all integer types are stored
        as 64‑bit, so this is functionally identical to ``INT``. It provides
        the same optional range and unsigned checks via ``CHECK`` constraints.

        The placeholder ``'my_saulted_x'`` in the returned string is replaced
        with the actual column name during table creation (typically by the
        :meth:`TableStructure.add_column` method).

        Args:
            min_val (int, optional): The minimum allowed value. If provided,
                adds a ``CHECK(my_saulted_x >= min_val)`` constraint.
            max_val (int, optional): The maximum allowed value. If provided,
                adds a ``CHECK(my_saulted_x <= max_val)`` constraint.
            unsigned (bool, optional): If ``True``, adds a ``CHECK`` that the
                value is >= 0 (unless a custom ``min_val`` overrides it).
                Defaults to ``False``.

        Returns:
            str: A column definition fragment like
            ``'my_saulted_x INTEGER CHECK(...)'`` or a plain
            ``'my_saulted_x INTEGER'`` if no constraints are needed.

        Example:
            Using ``BIGINT`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('logs')
                structure.add_column(
                    column_name='timestamp',
                    datatype=DataTypes.BIGINT(unsigned=True)  # only non‑negative timestamps
                )
                structure.add_column(
                    column_name='score',
                    datatype=DataTypes.BIGINT(min_val=-1000, max_val=1000)
                )
        """
        return DataTypes.INT(min_val, max_val, unsigned)

    @staticmethod
    def CHAR(min_length: int = None, max_length: int = None) -> str:
        """Generate a column definition for a fixed‑length character type.

        This method is a synonym for :meth:`TEXT` and returns a SQLite column
        definition string of type ``TEXT`` with optional length constraints
        enforced via ``CHECK``. It is named ``CHAR`` to mirror SQL fixed‑length
        semantics, but SQLite does not natively support fixed‑length storage;
        the constraints are implemented using ``LENGTH()`` checks.

        If both ``min_length`` and ``max_length`` are provided, the column
        will have a ``CHECK`` that the length is between them. If only one is
        given, only that bound is enforced. To enforce an exact length, pass
        the same value for both.

        The placeholder ``'my_saulted_x'`` in the returned string is replaced
        with the actual column name during table creation.

        Args:
            min_length (int, optional): The minimum allowed length (inclusive).
                If provided, adds a ``CHECK(LENGTH(my_saulted_x) >= min_length)``.
            max_length (int, optional): The maximum allowed length (inclusive).
                If provided, adds a ``CHECK(LENGTH(my_saulted_x) <= max_length)``.

        Returns:
            str: A column definition fragment such as
            ``'my_saulted_x TEXT CHECK(LENGTH(my_saulted_x) BETWEEN 5 AND 10)'``
            or ``'my_saulted_x TEXT'`` if no constraints are specified.

        Example:
            Using ``CHAR`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('users')
                structure.add_column(
                    column_name='country_code',
                    datatype=DataTypes.CHAR(min_length=2, max_length=2)  # exactly 2 chars
                )
                structure.add_column(
                    column_name='status',
                    datatype=DataTypes.CHAR(max_length=20)  # at most 20 chars
                )
        """
        return DataTypes.TEXT(min_length, max_length)

    @staticmethod
    def ENUM(*values: str) -> str:
        """
        Generate a column definition for an enumeration of allowed string values.

        This method returns a SQLite column definition string that restricts
        the column's values to a predefined list of strings. The constraint
        is enforced by a ``CHECK`` clause using the ``IN`` operator, and the
        column is defined as type ``TEXT``.

        The placeholder ``'my_saulted_x'`` in the returned string is replaced
        with the actual column name when the column is added to a table (e.g.,
        by :meth:`TableStructure.add_column`).

        Args:
            *values (str): A variable number of string values that are
                permitted in the column. Each value will be quoted in the
                resulting SQL.

        Returns:
            str: A column definition fragment like
            ``'my_saulted_x TEXT CHECK(my_saulted_x IN ('value1', 'value2'))'``.

        Example:
            Using ``ENUM`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('users')
                structure.add_column(
                    column_name='status',
                    datatype=DataTypes.ENUM('active', 'inactive', 'pending')
                )
                # Generates:
                # my_saulted_x TEXT CHECK(my_saulted_x IN ('active', 'inactive', 'pending'))

                structure.add_column(
                    column_name='role',
                    datatype=DataTypes.ENUM('admin', 'user', 'guest')
                )
                # Generates a separate CHECK constraint for the role column.
        """        
        if not values:
            raise ValueError("ENUM requires at least one value")
        quoted = ", ".join(f"'{v}'" for v in values)
        return f"my_saulted_x TEXT CHECK(my_saulted_x IN ({quoted}))"

    @staticmethod
    def BOOLEAN() -> str:
        """Generate a column definition for a boolean type stored as INTEGER 0/1.

        This method returns a SQLite column definition string that enforces
        boolean values (0 for false, 1 for true) using a ``CHECK`` constraint.
        The placeholder ``'my_saulted_x'`` in the returned string is replaced
        with the actual column name during table creation (e.g., by
        :meth:`TableStructure.add_column`).

        The generated definition ensures that only the integers 0 or 1 can be
        inserted into the column, providing a simple boolean representation.

        Returns:
            str: A column definition fragment like
            ``'my_saulted_x INTEGER CHECK(my_saulted_x IN (0, 1))'``.

        Example:
            Using ``BOOLEAN`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('users')
                structure.add_column(
                    column_name='is_active',
                    datatype=DataTypes.BOOLEAN()
                )
                # Creates a column definition:
                # my_saulted_x INTEGER CHECK(my_saulted_x IN (0, 1))
        """
        return f"my_saulted_x INTEGER CHECK(my_saulted_x IN (0, 1))"

    @staticmethod
    def CUSTOM(type_name: str, check: str = None) -> str:
        """Generate a custom column definition with an optional CHECK constraint.

        This method allows you to define a column with a custom SQLite data type
        name (e.g., when strict mode is disabled) and optionally add a CHECK
        constraint. The placeholder ``'my_saulted_x'`` in the returned string
        is replaced with the actual column name during table creation (e.g., by
        :meth:`TableStructure.add_column`).

        This is useful for using database‑specific types (like ``GEOMETRY``,
        ``JSON``, or user‑defined types) that are not standard in SQLite, or for
        adding custom validation logic.

        Args:
            type_name (str): The custom SQLite type name to use for the column.
                This will be inserted directly into the column definition.
            check (str, optional): A CHECK constraint expression to enforce on
                the column. The expression should use the placeholder
                ``'my_saulted_x'`` to refer to the column's value. If provided,
                it is wrapped in a ``CHECK(...)`` clause. Defaults to ``None``.

        Returns:
            str: A column definition fragment like
            ``'my_saulted_x GEOMETRY CHECK(my_saulted_x IS NOT NULL)'``, or
            ``'my_saulted_x JSON'`` if no check is given.

        Example:
            Using ``CUSTOM`` in a :class:`TableStructure`::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('shapes')
                # Add a geometry column with a NOT NULL check
                structure.add_column(
                    column_name='shape',
                    datatype=DataTypes.CUSTOM(
                        'GEOMETRY',
                        check='my_saulted_x IS NOT NULL'
                    )
                )
                # Generated column: my_saulted_x GEOMETRY CHECK(my_saulted_x IS NOT NULL)

                # Add a JSON column without any check
                structure.add_column(
                    column_name='metadata',
                    datatype=DataTypes.CUSTOM('JSON')
                )
                # Generated column: my_saulted_x JSON
        """
        if not type_name:
            raise ValueError("type_name cannot be empty")
        if check:
            return f"my_saulted_x {type_name} CHECK({check})"
        return f"my_saulted_x {type_name}"


class TableStructure:
    """
    A builder for defining SQLite table schemas programmatically.

    This class provides a fluent interface for constructing a table
    definition, including columns, data types with constraints, primary
    keys, foreign keys, and the optional ``STRICT`` mode. The final
    ``CREATE TABLE`` SQL statement is generated by calling
    :meth:`get_structure` and can be executed via
    :meth:`Driver.create_table`.

    The class maintains an internal representation of the table schema,
    storing column definitions (with their types, defaults, uniqueness,
    nullability, and primary key status), foreign key constraints, and
    primary key configuration. It supports adding and removing columns
    before the table is created.

    **Usage pattern:**

    1. Instantiate ``TableStructure`` with the desired table name and
       optional ``STRICT`` mode.
    2. Add columns using :meth:`add_column` (each call returns ``self``
       for chaining).
    3. Optionally add foreign keys using :meth:`foreign_key`.
    4. Call :meth:`get_structure` to obtain the SQL string.
    5. Pass the structure to :meth:`Driver.create_table` to create the
       actual table in the database.

    **Placeholder replacement:**

    The class relies on the placeholder ``'my_saulted_x'`` in data type
    definitions (from :class:`DataTypes`). When a column is added, the
    placeholder is automatically replaced with the actual column name
    (wrapped in square brackets) to generate the correct column definition.

    Attributes:
        ON_CONFLICT (Literal): Type alias for conflict resolution options
            (``'ABORT'``, ``'ROLLBACK'``, ``'FAIL'``, ``'IGNORE'``,
            ``'REPLACE'``).
        ON_ACTION (Literal): Type alias for foreign key actions
            (``'CASCADE'``, ``'SET NULL'``, ``'SET DEFAULT'``,
            ``'RESTRICT'``, ``'NO ACTION'``).
        ON_INIT (Literal): Type alias for deferral initialization
            (``'DEFERRED'``, ``'IMMEDIATE'``).

    Example:
        Defining a simple table with primary key and foreign key::

            from ormophine.Sqlite import TableStructure, DataTypes, Driver

            # Build the structure
            structure = TableStructure('orders', strict=True)
            structure.add_column('id', DataTypes.INTEGER(), primary_key=True)
            structure.add_column('customer_id', DataTypes.INTEGER(), not_null=True)
            structure.add_column('total', DataTypes.DECIMAL(precision=10, scale=2))
            structure.add_column('status', DataTypes.ENUM('pending', 'shipped', 'delivered'))

            # Assume customers table already exists
            customers = db.table_object('customers')
            structure.foreign_key(
                column='customer_id',
                refrences_table=customers,
                refrences_column=customers.id,
                on_delete='CASCADE',
                on_update='RESTRICT'
            )

            # Create the table
            db = Driver('store.db')
            orders_table = db.create_table(structure)
    """
    ON_CONFLICT= Literal['ABORT', 'ROLLBACK', 'FAIL', 'IGNORE', 'REPLACE']
    ON_ACTION= Literal['CASCADE', 'SET NULL', 'SET DEFAULT', 'RESTRICT', 'NO ACTION']
    ON_INIT= Literal['DEFERRED', 'IMMEDIATE']

    def __init__(self, table_name: str, strict: bool = False, primarykey_on_conflict: ON_CONFLICT = 'ABORT'):
        """Initialize a new table structure definition.

        This class is used to build the complete definition of a database table
        before creation. It collects column definitions, primary keys, and foreign
        key constraints, and can generate the final ``CREATE TABLE`` SQL statement.
        The definition is mutable and supports adding/removing columns.

        Args:
            table_name (str): The name of the table to be created.
            strict (bool, optional): If ``True``, adds the ``STRICT`` keyword to
                the table definition, enforcing strict type checking in SQLite.
                Defaults to ``False``.
            primarykey_on_conflict (ON_CONFLICT, optional): The conflict resolution
                algorithm to use for the primary key when a constraint violation
                occurs. Must be one of ``'ABORT'``, ``'ROLLBACK'``, ``'FAIL'``,
                ``'IGNORE'``, or ``'REPLACE'``. Defaults to ``'ABORT'``.

        Attributes:
            strict (bool): Whether strict mode is enabled.
            table_query (str): The accumulated column definition string.
            primary_keys (list): List of column names that are part of the primary key.
            items (dict): Internal dictionary storing column metadata.
            name (str): The table name.
            foreigns (list): List of foreign key constraint strings.
            pkonc (str): The primary key conflict resolution.

        Example:
            Defining a table structure::

                from ormophine.Sqlite import DataTypes, TableStructure

                # Create a new table structure for 'users'
                structure = TableStructure('users', strict=True)

                # Add columns
                structure.add_column('id', DataTypes.INTEGER(primary_key=True))
                structure.add_column('username', DataTypes.VARCHAR(max_length=50))
                structure.add_column('age', DataTypes.TINYINT(unsigned=True))

                # Generate the CREATE TABLE statement
                create_sql = structure.get_structure()
                # CREATE TABLE [users] ( [id] INTEGER, [username] TEXT CHECK(LENGTH([username]) <= 50), [age] INTEGER CHECK([age] BETWEEN 0 AND 255), PRIMARY KEY([id]) ON CONFLICT ABORT ) STRICT;
        """
        self.strict= strict
        self.table_query= ''
        self.primary_keys= []
        self.items= {}
        self.name= table_name
        self.foreigns= []
        self.pkonc = primarykey_on_conflict

    def add_column(self, column_name: str, datatype: DataTypes,
                default_value=None, unique: bool = None,
                unique_on_conflict: ON_CONFLICT = 'ABORT',
                not_null: bool = None,
                not_null_on_conflict: ON_CONFLICT = 'ABORT',
                primary_key: bool = None):
        """Add a column definition to the table structure.

        This method appends a column definition to the internal query string
        used to generate the final ``CREATE TABLE`` statement. It validates
        that the column name is not already defined, and raises an exception
        if a duplicate is found. The method also stores column metadata in
        the ``items`` dictionary for later retrieval (e.g., via
        :meth:`get_columns`).

        The ``datatype`` parameter should be one of the type strings returned
        by the :class:`DataTypes` factory methods (e.g.,
        ``DataTypes.INTEGER()``, ``DataTypes.TEXT(max_length=50)``, etc.).
        These strings contain the placeholder ``'my_saulted_x'`` which is
        replaced with the actual column name (properly bracketed) in this
        method.

        Args:
            column_name (str): The name of the column to add.
            datatype (DataTypes): A column definition string from
                :class:`DataTypes` (e.g., ``DataTypes.INTEGER()``). The
                placeholder ``'my_saulted_x'`` will be replaced with the
                column name.
            default_value (optional): The default value for the column.
                Cannot be a ``bytes`` object. If provided, it is added as
                ``DEFAULT <value>``; strings are quoted, others are used
                as‑is.
            unique (bool, optional): If ``True``, adds a ``UNIQUE``
                constraint. Defaults to ``None``.
            unique_on_conflict (ON_CONFLICT, optional): Conflict resolution
                for the UNIQUE constraint (e.g., ``'ABORT'``, ``'IGNORE'``,
                ``'REPLACE'``). Defaults to ``'ABORT'``.
            not_null (bool, optional): If ``True``, adds a ``NOT NULL``
                constraint. Defaults to ``None``.
            not_null_on_conflict (ON_CONFLICT, optional): Conflict resolution
                for the NOT NULL constraint. Defaults to ``'ABORT'``.
            primary_key (bool, optional): If ``True``, marks this column as
                part of the primary key. The column name is added to the
                ``primary_keys`` list. Defaults to ``None``.

        Returns:
            TableStructure: The current instance, allowing method chaining.

        Raises:
            Exception: If a column with the same name has already been added.
            Exception: If ``default_value`` is of type ``bytes`` (not
                supported).

        Example:
            Building a table structure::

                from ormophine.Sqlite import TableStructure, DataTypes

                structure = TableStructure('users')
                structure.add_column(
                    'id',
                    DataTypes.INTEGER(unsigned=True),
                    primary_key=True
                ).add_column(
                    'username',
                    DataTypes.VARCHAR(max_length=50),
                    unique=True,
                    not_null=True
                ).add_column(
                    'age',
                    DataTypes.TINYINT(min_val=0, max_val=150),
                    default_value=18
                )

                # The structure can then be used to create a table:
                # db.create_table(structure)
        """
        for item in self.table_query.split(','):
            if column_name in item:
                raise Exception('You have added this column befor\nif you wanna modify this column , delete this column and then add a new one with desired options') if item.split(' ')[0] == column_name else None
        if type(default_value) == bytes:
            raise Exception('Cant set bytes object as default value')
        if default_value is not None:
            if isinstance(default_value, bool):
                default_value_sql = "1" if default_value else "0"
            elif isinstance(default_value, str):
                default_value_sql = f"'{default_value}'"
            else:
                default_value_sql = str(default_value)
            default_clause = f" DEFAULT {default_value_sql}"
        else:
            default_clause = ""
        self.primary_keys.append(column_name) if primary_key else None
        self.items[column_name] = [datatype, default_value, unique, unique_on_conflict, not_null, not_null_on_conflict, primary_key]
        self.table_query = self.table_query + f' {datatype.replace('my_saulted_x' , f'[{column_name.strip()}]')}{f' UNIQUE ON CONFLICT {unique_on_conflict}' if unique else ''}{f' NOT NULL ON CONFLICT {not_null_on_conflict}' if not_null else ''}{default_clause},'
        return self

    def delete_column(self, column_name: str):
        """Remove a column from the table structure definition.

        This method deletes a column that was previously added via
        :meth:`add_column`. It updates the internal SQL query fragment and
        the column metadata dictionary. If the column does not exist, an
        exception is raised.

        The method is typically used when building a table structure
        dynamically before creation. After deletion, the column will not
        appear in the generated ``CREATE TABLE`` statement.

        Args:
            column_name (str): The name of the column to remove.

        Returns:
            TableStructure: The current instance, allowing method chaining.

        Raises:
            Exception: If no column with the given name exists in the
                structure.

        Example:
            Building a table structure and removing a column::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('users')
                structure.add_column('id', DataTypes.INTEGER())
                structure.add_column('name', DataTypes.VARCHAR(50))
                structure.add_column('age', DataTypes.TINYINT())

                # Remove the 'age' column
                structure.delete_column('age')
                # The 'age' column will not appear in the final CREATE TABLE.

                # Create the table without the 'age' column
                db.create_table(structure)
        """
        if column_name not in self.items:
            raise Exception(f"No column found with name ({column_name})")
        pattern = r'\s*\[{}\]\s+[^,]+(?:,|$)'.format(re.escape(column_name.strip()))
        self.table_query = re.sub(pattern, '', self.table_query).rstrip(',')
        if not self.table_query.strip():
            self.table_query = ''
        self.items.pop(column_name, None)
        return self

    def get_columns(self):
        """Retrieve metadata for all columns defined in the table structure.

        This method returns a list of dictionaries, each containing detailed
        information about a column that has been added to this table structure
        via :meth:`add_column`. The metadata includes the column name, data type,
        default value, uniqueness constraints, nullability, conflict handling
        settings, and primary key status.

        The returned dictionaries have the following keys:

        * ``name`` (str): The column name.
        * ``datatype`` (str): The column definition string (including CHECK
        constraints) as returned by a :class:`DataTypes` method.
        * ``default_value`` (Any): The default value for the column, or ``None``.
        * ``unique`` (bool): Whether the column has a UNIQUE constraint.
        * ``unique_on_conflict`` (str): The ON CONFLICT clause for the UNIQUE
        constraint (e.g., 'ABORT', 'REPLACE').
        * ``not_null`` (bool): Whether the column has a NOT NULL constraint.
        * ``not_null_on_conflict`` (str): The ON CONFLICT clause for the NOT NULL
        constraint.
        * ``primary_key`` (bool): Whether the column is part of the primary key.
        (Note: the key is intentionally misspelled to match the implementation.)

        Returns:
            list[dict]: A list of dictionaries, one per column, in the order
            they were added. The list is empty if no columns have been defined.

        Example:
            Using ``get_columns`` to inspect a table structure::

                from ormophine.Sqlite import DataTypes, TableStructure

                structure = TableStructure('users')
                structure.add_column('id', DataTypes.INTEGER(), primary_key=True)
                structure.add_column('name', DataTypes.VARCHAR(max_length=50), unique=True)
                structure.add_column('age', DataTypes.TINYINT(min_val=0, max_val=150))

                columns = structure.get_columns()
                for col in columns:
                    print(f"{col['name']}: unique={col['unique']}, pk={col['primari_key']}")
                # Output:
                # id: unique=False, pk=True
                # name: unique=True, pk=False
                # age: unique=False, pk=False
        """
        items_list = []
        for item in self.items:
            items_dict = {}
            values = self.items[item]
            items_dict['name'] = item
            items_dict['datatype'] = values[0]
            items_dict['default_value'] = values[1]
            items_dict['unique'] = True if values[2] else False
            items_dict['unique_on_conflict'] = values[3]
            items_dict['not_null'] = True if values[4] else False
            items_dict['not_null_on_conflict'] = values[5]
            items_dict['primary_key'] = True if values[6] else False
            items_list.append(items_dict)
        return items_list

    def foreign_key(self, column: str, refrences_table: 'Table',
                    refrences_column: 'Column', on_delete: ON_ACTION = None,
                    on_update: ON_ACTION = None, deferrable: bool = True,
                    initially: ON_INIT = 'DEFERRED'):
        """Add a foreign key constraint to the table structure.

        This method appends a ``FOREIGN KEY`` definition to the internal list
        of foreign keys, which will be included in the final ``CREATE TABLE``
        statement. The method supports specifying actions for ``ON DELETE``
        and ``ON UPDATE``, as well as deferrability and initialization timing.

        The foreign key references a column in another table, enforcing
        referential integrity at the database level.

        Args:
            column (str): The name of the column in the current table that
                acts as the foreign key.
            refrences_table (Table): The referenced table object (the parent
                table). Note: This is a forward reference to a :class:`Table`
                instance.
            refrences_column (Column): The referenced column object in the
                parent table.
            on_delete (ON_ACTION, optional): Action to take when the referenced
                row is deleted. Valid values are from the ``ON_ACTION`` type:
                ``'CASCADE'``, ``'SET NULL'``, ``'SET DEFAULT'``,
                ``'RESTRICT'``, or ``'NO ACTION'``. Defaults to ``None``
                (no action specified).
            on_update (ON_ACTION, optional): Action to take when the referenced
                column is updated. Same options as ``on_delete``. Defaults to
                ``None``.
            deferrable (bool, optional): If ``True``, the constraint can be
                deferred until the transaction commits. If ``False``, it is
                checked immediately. Defaults to ``True``.
            initially (ON_INIT, optional): Defines the initial deferral state.
                Can be ``'DEFERRED'`` (default) or ``'IMMEDIATE'``. Only
                relevant if ``deferrable`` is ``True``.

        Returns:
            TableStructure: The current instance (``self``), allowing method
            chaining for building the table structure.

        Example:
            Assuming two tables ``orders`` and ``customers``::

                from ormophine.Sqlite import Driver, Table, TableStructure, DataTypes

                db = Driver('store.db')

                # Build customers table first
                customers_structure = TableStructure('customers')
                customers_structure.add_column('id', DataTypes.INTEGER(primary_key=True))
                customers_structure.add_column('name', DataTypes.VARCHAR(max_length=50))

                # Build orders table with a foreign key
                orders_structure = TableStructure('orders')
                orders_structure.add_column('id', DataTypes.INTEGER(primary_key=True))
                orders_structure.add_column('customer_id', DataTypes.INTEGER())
                orders_structure.add_column('total', DataTypes.DECIMAL(10,2))

                # Add foreign key referencing customers.id
                # First create the Table objects (or use existing ones)
                customers_table = db.create_table(customers_structure)

                # Add foreign key to orders_structure before creation
                orders_structure.foreign_key(
                    column='customer_id',
                    refrences_table=customers_table,
                    refrences_column=customers_table.id,
                    on_delete='CASCADE',
                    on_update='RESTRICT',
                    deferrable=False
                )

                # Then create orders table
                db.create_table(orders_structure)
                # This ensures referential integrity between orders and customers.
        """
        fk = f'FOREIGN KEY({column}) REFERENCES {refrences_table.name_}({refrences_column.first_name})'
        if on_delete:
            fk += f' ON DELETE {on_delete}'
        if on_update:
            fk += f' ON UPDATE {on_update}'
        if deferrable is not None:
            fk += ' DEFERRABLE' if deferrable else ' NOT DEFERRABLE'
            if initially is not None:
                fk += f' INITIALLY {initially}'
        self.foreigns.append(fk)
        return self

    def get_structure(self):
        """Generate the complete SQL `CREATE TABLE` statement for the table structure.

        This method constructs and returns the full SQL `CREATE TABLE` command
        based on the columns, constraints, foreign keys, primary keys, and
        strict mode settings that have been added to this `TableStructure`
        instance. The returned string includes column definitions with data
        types, `CHECK` constraints, `UNIQUE`, `NOT NULL`, `DEFAULT` values,
        primary key definitions, foreign key constraints, and the optional
        `STRICT` mode.

        The generated SQL uses the table name as provided in the constructor,
        and wraps column names in square brackets (`[]`) for safety.

        Returns:
            str: A complete SQL `CREATE TABLE` statement that can be executed
            to create the table in the database.

        Example:
            Creating a `TableStructure` and getting its SQL::

                from ormophine.Sqlite import TableStructure, DataTypes

                structure = TableStructure('users', strict=True)
                structure.add_column('id', DataTypes.INTEGER(), primary_key=True)
                structure.add_column('name', DataTypes.VARCHAR(max_length=50), not_null=True)
                structure.add_column('age', DataTypes.TINYINT(min_val=0, max_val=150))

                sql = structure.get_structure()
                # sql will be something like:
                # CREATE TABLE [users] (
                #   [id] INTEGER,
                #   [name] TEXT CHECK(LENGTH([name]) <= 50) NOT NULL ON CONFLICT ABORT,
                #   [age] INTEGER CHECK([age] BETWEEN 0 AND 150),
                #   PRIMARY KEY([id]) ON CONFLICT ABORT
                # ) STRICT;
        """
        if not self.table_query.strip():
            raise Exception("You must add at least one column")
        return f'CREATE TABLE [{self.name}] ({self.table_query[:-1]}{',' if self.primary_keys else ''}{f'PRIMARY KEY({', '.join(self.primary_keys)}) ON CONFLICT {self.pkonc}' if self.primary_keys else ''}{',' if self.foreigns else ''}{','.join(self.foreigns) if self.foreigns else ''}) {'STRICT' if self.strict else ''};'

