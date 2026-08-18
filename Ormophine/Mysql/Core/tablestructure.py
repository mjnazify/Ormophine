from __future__ import annotations
from typing import Literal

class DataTypes:
    """
    Complete MySQL 8.0 Data Types as static methods.

    This class provides a comprehensive set of static methods that return SQL
    data type strings for use in table definitions. Each method corresponds to
    a MySQL 8.0 data type, including numeric, string, date/time, spatial, JSON,
    and special types. The returned strings can be directly used in
    :class:`TableStructure` column definitions (e.g., via
    :meth:`TableStructure.add_column`).

    The class also defines the :attr:`TEXT_SIZE` type variable for use with
    the :meth:`TEXT` method.

    All methods are static and do not require an instance. Simply call
    ``DataTypes.INT()``, ``DataTypes.VARCHAR(255)``, etc. Each method accepts
    appropriate parameters (e.g., length, precision, unsigned flags) to tailor
    the generated SQL type definition.

    Examples:
        Defining a table with various data types:

        >>> from ormophine.Mysql import TableStructure, DataTypes
        >>> table = (TableStructure('employees')
        ...          .add_column('id', DataTypes.SERIAL(), primary_key=True,
        ...                      auto_increment=True, not_null=True)
        ...          .add_column('name', DataTypes.VARCHAR(100), not_null=True)
        ...          .add_column('salary', DataTypes.DECIMAL(10,2))
        ...          .add_column('birth_date', DataTypes.DATE())
        ...          .add_column('metadata', DataTypes.JSON()))

        Using the `TEXT_SIZE` literal with :meth:`TEXT`:

        >>> DataTypes.TEXT('LONGTEXT')
        'LONGTEXT'
        >>> DataTypes.TEXT()
        'TEXT'

    This class is intended to be used with the ORM's table creation and
    alteration utilities. All methods are guaranteed to return valid MySQL 8.0
    syntax.
    """
    TEXT_SIZE = Literal['TINYTEXT', 'TEXT', 'MEDIUMTEXT', 'LONGTEXT']
    # ========================
    # Numeric Data Types
    # ========================

    @staticmethod
    def BIT(size: int) -> str:
        """
        Generate a MySQL BIT data type definition.

        The BIT type stores bit-field values, where the length specifies the number
        of bits per value. Valid sizes range from 1 to 64 bits. This method returns
        a string suitable for use in ``CREATE TABLE`` or ``ALTER TABLE`` statements.

        Args:
            size (int): The number of bits in the field. Must be between 1 and 64
                inclusive.

        Returns:
            str: A SQL data type string in the format ``BIT(size)``.

        Raises:
            ValueError: If ``size`` is outside the valid range (1–64).

        Example:
            Create a table with a BIT column::

                from ormophine.Mysql import DataTypes, TableStructure

                struct = (TableStructure('settings')
                        .add_column('id', DataTypes.INT(), primary_key=True,
                                    auto_increment=True, not_null=True)
                        .add_column('flags', DataTypes.BIT(8), default_value=0))

                # The 'flags' column will be defined as BIT(8) in SQL.
        """
        if size:
            if size < 1 or size > 64:
                raise ValueError("Size for BIT must be between 1 and 64.")
        return f"BIT({size})"

    @staticmethod
    def TINYINT(size: int = None, unsigned: bool = False, zerofill: bool = False) -> str:
        """
        Generate a MySQL TINYINT data type definition.

        TINYINT is a very small integer. When signed, its range is -128 to 127.
        When unsigned, the range is 0 to 255. This method returns the SQL string
        that can be used in a ``CREATE TABLE`` or ``ALTER TABLE`` statement.

        Args:
            size (int, optional): The display width. If provided, it must be within
                the signed or unsigned range accordingly. Defaults to ``None``,
                meaning no display width is specified.
            unsigned (bool, optional): If ``True``, the column is defined as
                ``UNSIGNED``, disallowing negative values. Defaults to ``False``.
            zerofill (bool, optional): If ``True``, the column is defined as
                ``ZEROFILL``, which implies ``UNSIGNED`` and pads values with leading
                zeros up to the display width. Defaults to ``False``.

        Returns:
            str: The MySQL TINYINT data type string, e.g., ``"TINYINT(3) UNSIGNED"``.

        Raises:
            ValueError: If the provided ``size`` is outside the valid range for
                the signed or unsigned mode.

        Example:
            Create a table with a TINYINT column::

                from ormophine.Mysql import DataTypes

                # Signed TINYINT with display width 3
                tiny_signed = DataTypes.TINYINT(size=3)

                # Unsigned TINYINT without display width
                tiny_unsigned = DataTypes.TINYINT(unsigned=True)

                # ZEROFILL TINYINT (implies UNSIGNED)
                tiny_zerofill = DataTypes.TINYINT(size=5, zerofill=True)

                # Use in a table structure
                from ormophine.Mysql import TableStructure
                table = (TableStructure('scores')
                        .add_column('score', tiny_unsigned, not_null=True))
        """
        if size is not None:
            if (size < -128 or size > 127) and not unsigned or (size < 0 or size > 255) and unsigned:
                raise ValueError("Size for TINYINT must be between -128 and 127 for signed or 0 to 255 for unsigned.")
        result = "TINYINT"
        if size:
            result += f"({size})"
        if unsigned:
            result += " UNSIGNED"
        if zerofill:
            result += " ZEROFILL"
        return result

    @staticmethod
    def SMALLINT(size: int = None, unsigned: bool = False, zerofill: bool = False) -> str:
        """
        Return the SQL data type string for a SMALLINT column.

        SMALLINT is a small integer type. The signed range is -32768 to 32767,
        and the unsigned range is 0 to 65535. The optional ``size`` parameter
        affects display width but does not change the storage size or value range.
        The ``unsigned`` and ``zerofill`` flags can be used to modify the column
        definition.

        Args:
            size (int, optional): The display width of the column. If provided,
                it must be within the valid range for the chosen signed/unsigned
                mode. Defaults to ``None``, meaning the default display width is used.
            unsigned (bool, optional): If ``True``, the column is defined as
                ``UNSIGNED``, disallowing negative values. Defaults to ``False``.
            zerofill (bool, optional): If ``True``, the column is defined as
                ``ZEROFILL``, which pads displayed values with leading zeros up to
                the display width. Implies ``UNSIGNED``. Defaults to ``False``.

        Returns:
            str: The SQL data type definition, e.g., ``'SMALLINT'``,
            ``'SMALLINT(5)'``, or ``'SMALLINT(5) UNSIGNED ZEROFILL'``.

        Raises:
            ValueError: If the provided ``size`` falls outside the allowed range
                for the chosen signed/unsigned mode. For signed, the allowed
                range is -32768 to 32767; for unsigned, 0 to 65535.

        Example:
            Defining a SMALLINT column with a display width and unsigned flag::

                from ormophine.Mysql import DataTypes

                sql_type = DataTypes.SMALLINT(size=5, unsigned=True)
                # Returns: 'SMALLINT(5) UNSIGNED'

                # Using it in a table structure
                table = (TableStructure('products')
                        .add_column('stock', DataTypes.SMALLINT(unsigned=True, not_null=True)))
        """
        if size is not None:
            if (size < -32768 or size > 32767) and not unsigned or (size < 0 or size > 65535) and unsigned:
                raise ValueError("Size for SMALLINT must be between -32768 and 32767 for signed or 0 to 65535 for unsigned.")
        result = "SMALLINT"
        if size:
            result += f"({size})"
        if unsigned:
            result += " UNSIGNED"
        if zerofill:
            result += " ZEROFILL"
        return result

    @staticmethod
    def MEDIUMINT(size: int = None, unsigned: bool = False, zerofill: bool = False) -> str:
        """
        Return the SQL data type string for a MEDIUMINT column.

        MEDIUMINT is a medium‑sized integer type. The signed range is
        -8,388,608 to 8,388,607, and the unsigned range is 0 to 16,777,215.
        The optional ``size`` parameter controls the display width but does
        not affect storage size or the range of values. The ``unsigned`` and
        ``zerofill`` flags modify the column definition as described below.

        Args:
            size (int, optional): The display width of the column. If provided,
                it must be within the valid range for the chosen signed/unsigned
                mode. Defaults to ``None``, which uses the default display width.
            unsigned (bool, optional): If ``True``, the column is defined as
                ``UNSIGNED``, disallowing negative values. Defaults to ``False``.
            zerofill (bool, optional): If ``True``, the column is defined as
                ``ZEROFILL``, which pads displayed values with leading zeros up to
                the display width. This option implicitly makes the column
                ``UNSIGNED``. Defaults to ``False``.

        Returns:
            str: The SQL data type definition, e.g., ``'MEDIUMINT'``,
            ``'MEDIUMINT(8)'``, or ``'MEDIUMINT(8) UNSIGNED ZEROFILL'``.

        Raises:
            ValueError: If the provided ``size`` falls outside the allowed range
                for the chosen signed/unsigned mode. For signed, the allowed
                range is -8,388,608 to 8,388,607; for unsigned, 0 to 16,777,215.

        Example:
            Defining a MEDIUMINT column with a display width and unsigned flag::

                from ormophine.Mysql import DataTypes

                sql_type = DataTypes.MEDIUMINT(size=8, unsigned=True)
                # Returns: 'MEDIUMINT(8) UNSIGNED'

                # Using it in a table structure
                table = (TableStructure('logs')
                        .add_column('event_count', DataTypes.MEDIUMINT(unsigned=True, not_null=True)))
        """
        if size is not None:
            if (size < -8388608 or size > 8388607) and not unsigned or (size < 0 or size > 16777215) and unsigned:
                raise ValueError("Size for MEDIUMINT must be between -8388608 and 8388607 for signed or 0 to 16777215 for unsigned.")
        result = "MEDIUMINT"
        if size:
            result += f"({size})"
        if unsigned:
            result += " UNSIGNED"
        if zerofill:
            result += " ZEROFILL"
        return result

    @staticmethod
    def INT(size: int = None, unsigned: bool = False, zerofill: bool = False) -> str:
        """
        Return the SQL data type string for an INT (standard integer) column.

        INT is a standard integer type in MySQL. The signed range is -2147483648 to
        2147483647, and the unsigned range is 0 to 4294967295. The optional ``size``
        parameter defines the display width (e.g., ``INT(11)``) but does not affect
        storage size or value range. The ``unsigned`` flag disallows negative values,
        and ``zerofill`` pads displayed values with leading zeros up to the display
        width (which also implies unsigned in standard MySQL, though the ORM allows
        setting them independently).

        Args:
            size (int, optional): The display width of the column. If provided, it
                must fall within the valid range for the chosen signed/unsigned mode.
                For signed, valid values are between -2147483648 and 2147483647;
                for unsigned, between 0 and 4294967295. Defaults to ``None``, which
                uses the default display width.
            unsigned (bool, optional): If ``True``, the column is defined as
                ``UNSIGNED``, disallowing negative values. Defaults to ``False``.
            zerofill (bool, optional): If ``True``, the column is defined as
                ``ZEROFILL``, padding displayed numeric values with leading zeros.
                In MySQL, this typically implies ``UNSIGNED``. Defaults to ``False``.

        Returns:
            str: The SQL data type definition, e.g., ``'INT'``, ``'INT(11)'``,
            ``'INT UNSIGNED'``, or ``'INT(10) UNSIGNED ZEROFILL'``.

        Raises:
            ValueError: If the provided ``size`` is outside the allowed range for
                the chosen signed/unsigned mode.

        Example:
            Defining an INT column with a specific display width and unsigned flag::

                from ormophine.Mysql import DataTypes, TableStructure

                sql_type = DataTypes.INT(size=10, unsigned=True)
                # Returns: 'INT(10) UNSIGNED'

                # Using it in a table structure
                table = (TableStructure('products')
                        .add_column('stock', DataTypes.INT(unsigned=True, not_null=True)))
        """
        if size is not None:
            if (size < -2147483648 or size > 2147483647) and not unsigned or (size < 0 or size > 4294967295) and unsigned:
                raise ValueError("Size for INT must be between -2147483648 and 2147483647 for signed or 0 to 4294967295 for unsigned.")
        result = "INT"
        if size:
            result += f"({size})"
        if unsigned:
            result += " UNSIGNED"
        if zerofill:
            result += " ZEROFILL"
        return result

    @staticmethod
    def BIGINT(size: int = None, unsigned: bool = False, zerofill: bool = False) -> str:
        """
        Return the SQL data type string for a BIGINT column.

        BIGINT is a large integer type. The signed range is -2^63 to 2^63-1
        (-9223372036854775808 to 9223372036854775807), and the unsigned range is
        0 to 2^64-1 (18446744073709551615). The optional ``size`` parameter affects
        the display width but does not change the storage size or value range.
        The ``unsigned`` and ``zerofill`` flags modify the column definition.

        Args:
            size (int, optional): The display width of the column. If provided,
                it must be within the valid range for the chosen signed/unsigned
                mode. Defaults to ``None``, meaning the default display width is used.
            unsigned (bool, optional): If ``True``, the column is defined as
                ``UNSIGNED``, disallowing negative values. Defaults to ``False``.
            zerofill (bool, optional): If ``True``, the column is defined as
                ``ZEROFILL``, which pads displayed values with leading zeros up to
                the display width. Implies ``UNSIGNED``. Defaults to ``False``.

        Returns:
            str: The SQL data type definition, e.g., ``'BIGINT'``,
            ``'BIGINT(20)'``, or ``'BIGINT(20) UNSIGNED ZEROFILL'``.

        Raises:
            ValueError: If the provided ``size`` falls outside the allowed range
                for the chosen signed/unsigned mode. For signed, the allowed range
                is -9223372036854775808 to 9223372036854775807; for unsigned, it is
                0 to 18446744073709551615.

        Example:
            Defining a BIGINT column with a display width and unsigned flag::

                from ormophine.Mysql import DataTypes

                sql_type = DataTypes.BIGINT(size=20, unsigned=True)
                # Returns: 'BIGINT(20) UNSIGNED'

                # Using it in a table structure
                table = (TableStructure('orders')
                        .add_column('order_id', DataTypes.BIGINT(unsigned=True, not_null=True)))
        """
        if size is not None:
            if (size < -9223372036854775808 or size > 9223372036854775807) and not unsigned or (size < 0 or size > 18446744073709551615) and unsigned:
                raise ValueError("Size for BIGINT must be between -9223372036854775808 and 9223372036854775807 for signed or 0 to 18446744073709551615 for unsigned.")
        result = "BIGINT"
        if size:
            result += f"({size})"
        if unsigned:
            result += " UNSIGNED"
        if zerofill:
            result += " ZEROFILL"
        return result

    @staticmethod
    def DECIMAL(precision: int = 10, scale: int = 0) -> str:
        """
        Return the SQL data type string for a DECIMAL (exact fixed-point) column.

        DECIMAL is used to store exact numeric values with a fixed number of digits
        before and after the decimal point. It is ideal for financial and monetary
        data where precision is critical. The storage size depends on the precision
        and scale.

        Args:
            precision (int, optional): The total number of significant digits that
                can be stored, both to the left and right of the decimal point.
                Must be at least 1. Defaults to 10.
            scale (int, optional): The number of digits that can be stored after
                the decimal point. Must be between 0 and ``precision``. Defaults to 0.

        Returns:
            str: The SQL data type definition, e.g., ``'DECIMAL(10,2)'``.

        Raises:
            ValueError: If the provided ``precision`` is less than 1 or ``scale``
                is less than 0 or greater than ``precision`` (currently not enforced
                by the method but documented as the expected behavior).

        Example:
            Defining a DECIMAL column for product prices with 10 total digits and
            2 decimal places::

                from ormophine.Mysql import DataTypes, TableStructure

                price_type = DataTypes.DECIMAL(precision=10, scale=2)
                # Returns: 'DECIMAL(10,2)'

                table = (TableStructure('products')
                        .add_column('price', price_type, not_null=True))
        """
        if precision < 1 or scale < 0 or scale > precision:
            raise ValueError("Precision must be >= 1 and scale must be >= 0 and <= precision.")
        return f"DECIMAL({precision}, {scale})"

    @staticmethod
    def NUMERIC(precision: int = 10, scale: int = 0) -> str:
        """
        Return the SQL data type string for a NUMERIC column.

        NUMERIC is a synonym for DECIMAL in MySQL. It stores exact fixed-point
        numbers with a specified precision (total number of digits) and scale
        (number of digits after the decimal point). The precision must be at least
        1, and the scale must be between 0 and precision inclusive.

        Args:
            precision (int, optional): The total number of significant digits.
                Defaults to 10. Must be >= 1.
            scale (int, optional): The number of digits after the decimal point.
                Defaults to 0. Must be between 0 and ``precision`` inclusive.

        Returns:
            str: The SQL data type definition, e.g., ``'NUMERIC(10,2)'``.

        Raises:
            ValueError: If ``precision`` < 1, ``scale`` < 0, or ``scale`` > ``precision``.

        Example:
            Defining a NUMERIC column with 12 total digits and 4 decimal places::

                from ormophine.Mysql import DataTypes

                sql_type = DataTypes.NUMERIC(precision=12, scale=4)
                # Returns: 'NUMERIC(12, 4)'

                # Using it in a table structure
                table = (TableStructure('products')
                        .add_column('price', DataTypes.NUMERIC(10, 2), not_null=True))
        """
        if precision < 1 or scale < 0 or scale > precision:
            raise ValueError("Precision must be >= 1 and scale must be >= 0 and <= precision.")
        return f"NUMERIC({precision}, {scale})"

    @staticmethod
    def FLOAT(size: int = None, decimals: int = None) -> str:
        """
        Return the SQL data type string for a FLOAT column.

        FLOAT is a single‑precision floating‑point number. The optional ``size``
        and ``decimals`` parameters control the display width and the number of
        digits after the decimal point, respectively. If both are provided, the
        column is defined as ``FLOAT(size, decimals)``; otherwise, the bare
        ``FLOAT`` type is used.

        Note that the storage size and precision are determined by the MySQL
        implementation; specifying a size/decimals does not change the storage
        requirements but affects how values are displayed and parsed.

        Args:
            size (int, optional): The total number of digits (precision). If
                provided, must be a positive integer. Defaults to ``None``.
            decimals (int, optional): The number of digits after the decimal point
                (scale). If provided, must be a non‑negative integer. Defaults to
                ``None``. This parameter is only used when ``size`` is also given.

        Returns:
            str: The SQL data type definition, e.g., ``'FLOAT'`` or
            ``'FLOAT(7,4)'``.

        Raises:
            None: This method does not perform runtime validation of the arguments,
            though it is recommended to pass sensible values (positive integers).

        Example:
            Defining a FLOAT column with a custom precision and scale::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('measurements')
                        .add_column('temperature', DataTypes.FLOAT(5, 2)))
                # Generates: `temperature` FLOAT(5,2)

            Using the bare FLOAT type::

                table.add_column('humidity', DataTypes.FLOAT())
                # Generates: `humidity` FLOAT
        """
        if size is not None and decimals is not None:
            return f"FLOAT({size}, {decimals})"
        return "FLOAT"

    @staticmethod
    def DOUBLE(size: int = None, decimals: int = None) -> str:
        """
        Return the SQL data type string for a DOUBLE column.

        DOUBLE is a double‑precision floating‑point number (also known as ``REAL``
        in some contexts). The optional ``size`` and ``decimals`` parameters control
        the display width and the number of digits after the decimal point,
        respectively. If both are provided, the column is defined as
        ``DOUBLE(size, decimals)``; otherwise, the bare ``DOUBLE`` type is used.

        Note that the storage size and precision are determined by the MySQL
        implementation; specifying a size/decimals does not change the storage
        requirements but affects how values are displayed and parsed.

        Args:
            size (int, optional): The total number of digits (precision). If
                provided, must be a positive integer. Defaults to ``None``.
            decimals (int, optional): The number of digits after the decimal point
                (scale). If provided, must be a non‑negative integer. Defaults to
                ``None``. This parameter is only used when ``size`` is also given.

        Returns:
            str: The SQL data type definition, e.g., ``'DOUBLE'`` or
            ``'DOUBLE(10,4)'``.

        Raises:
            None: This method does not perform runtime validation of the arguments,
            though it is recommended to pass sensible values (positive integers for
            size and non‑negative integers for decimals).

        Example:
            Defining a DOUBLE column with a custom precision and scale::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('scientific_data')
                        .add_column('temperature', DataTypes.DOUBLE(8, 3)))
                # Generates: `temperature` DOUBLE(8,3)

            Using the bare DOUBLE type::

                table.add_column('humidity', DataTypes.DOUBLE())
                # Generates: `humidity` DOUBLE
        """
        if size is not None and decimals is not None:
            return f"DOUBLE({size}, {decimals})"
        return "DOUBLE"

    @staticmethod
    def REAL() -> str:
        """
        Return the SQL data type string for a REAL column.

        REAL is a synonym for ``DOUBLE`` (double-precision floating-point) in MySQL,
        though depending on the server SQL mode, it may be treated as ``FLOAT``
        (single-precision). In practice, MySQL treats ``REAL`` as ``DOUBLE`` by
        default, but this can be changed with the ``REAL_AS_FLOAT`` SQL mode.

        This method returns the exact string ``'REAL'``, leaving the interpretation
        to the MySQL server.

        Args:
            None

        Returns:
            str: The SQL data type definition, always ``'REAL'``.

        Raises:
            None

        Example:
            Using REAL in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('measurements')
                        .add_column('temperature', DataTypes.REAL()))
                # Generates: `temperature` REAL

            Note that the actual precision will depend on the server's SQL mode.
        """
        return "REAL"

    # ========================
    # String Data Types
    # ========================

    @staticmethod
    def CHAR(length: int = 255) -> str:
        """
        Return the SQL data type string for a fixed-length character column.

        ``CHAR`` stores fixed-length strings. Values shorter than the specified
        length are padded with spaces on the right. The maximum length is 255
        characters.

        Args:
            length (int, optional): The maximum number of characters the column
                can store. Must be between 1 and 255. Defaults to 255.

        Returns:
            str: The SQL data type definition, e.g., ``'CHAR(50)'``.

        Raises:
            ValueError: If ``length`` is less than 1 or greater than 255.

        Example:
            Defining a CHAR column with a specific length::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('countries')
                        .add_column('iso_code', DataTypes.CHAR(2), not_null=True))
                # Generates: `iso_code` CHAR(2) NOT NULL

            Using the default length (255)::

                table.add_column('description', DataTypes.CHAR())
                # Generates: `description` CHAR(255)
        """
        if length < 1 or length > 255:
            raise ValueError("Length for CHAR must be between 1 and 255.")
        return f"CHAR({length})"

    @staticmethod
    def VARCHAR(length: int = 255) -> str:
        """
        Return the SQL data type string for a VARCHAR column.

        VARCHAR is a variable‑length character string type. The maximum length is
        65,535 bytes, but the effective maximum may be less depending on the
        character set and row size limits. The specified ``length`` defines the
        maximum number of characters that can be stored.

        Args:
            length (int, optional): The maximum number of characters. Must be
                between 1 and 65535. Defaults to 255.

        Returns:
            str: The SQL data type definition, e.g., ``'VARCHAR(255)'``.

        Raises:
            ValueError: If ``length`` is not between 1 and 65535.

        Example:
            Defining a VARCHAR column for a user's name::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('users')
                        .add_column('full_name', DataTypes.VARCHAR(100)))
                # Generates: `full_name` VARCHAR(100)
        """
        if length < 1 or length > 65535:
            raise ValueError("Length for VARCHAR must be between 1 and 65535.")
        return f"VARCHAR({length})"

    @staticmethod
    def TINYTEXT() -> str:
        """
        Return the SQL data type string for a TINYTEXT column.

        TINYTEXT is a very small text column with a maximum length of 255 bytes
        (characters, depending on the character set). It is suitable for storing
        short strings such as titles, short descriptions, or small code snippets.
        Unlike VARCHAR, TINYTEXT has a fixed maximum size and is stored with a
        length prefix, making it efficient for very short data.

        Returns:
            str: The SQL data type definition, always ``'TINYTEXT'``.

        Example:
            Defining a TINYTEXT column in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('articles')
                        .add_column('title', DataTypes.TINYTEXT()))
                # Generates: `title` TINYTEXT

            This is equivalent to using ``DataTypes.TEXT('TINYTEXT')`` but is
            provided as a convenient shorthand.
        """
        return "TINYTEXT"

    @staticmethod
    def TEXT(size: TEXT_SIZE = None) -> str:
        """
        Return the SQL data type string for a TEXT column.

        TEXT is a variable-length string type with a maximum length determined by
        the specified size variant. By default (when ``size`` is ``None``), this
        returns the standard ``TEXT`` type, which can store up to 65,535 characters.
        The optional ``size`` parameter allows specifying one of the four MySQL
        text size variants: ``'TINYTEXT'``, ``'TEXT'``, ``'MEDIUMTEXT'``, or
        ``'LONGTEXT'``.

        Args:
            size (TEXT_SIZE, optional): A string indicating the desired text size
                variant. Must be one of ``'TINYTEXT'``, ``'TEXT'``, ``'MEDIUMTEXT'``,
                or ``'LONGTEXT'``. Case-insensitive. Defaults to ``None``, which
                returns ``'TEXT'``.

        Returns:
            str: The SQL data type definition, e.g., ``'TEXT'``, ``'LONGTEXT'``,
            or ``'MEDIUMTEXT'``.

        Raises:
            ValueError: If the provided ``size`` is not one of the allowed values.

        Example:
            Defining a column using the default TEXT type::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('articles')
                        .add_column('content', DataTypes.TEXT()))
                # Generates: `content` TEXT

            Using a larger text type::

                table.add_column('long_description', DataTypes.TEXT('LONGTEXT'))
                # Generates: `long_description` LONGTEXT
        """
        if size:
            valid = {"TINYTEXT", "TEXT", "MEDIUMTEXT", "LONGTEXT"}
            if size.upper() in valid:
                return size.upper()
            raise ValueError(f"Invalid TEXT size. Choose from {valid}")
        return "TEXT"

    @staticmethod
    def MEDIUMTEXT() -> str:
        """
        Return the SQL data type string for a MEDIUMTEXT column.

        MEDIUMTEXT is a variable-length string type capable of storing up to
        16,777,215 characters (approximately 16 MB). This is the medium-size
        variant in the MySQL TEXT family, larger than ``TEXT`` (65,535) and
        smaller than ``LONGTEXT`` (4,294,967,295). It is suitable for storing
        moderately large text data, such as articles, JSON documents, or logs.

        Unlike ``VARCHAR``, columns of type MEDIUMTEXT do not have a specified
        maximum length and are stored separately from the row data. They also
        cannot have default values (a restriction enforced by MySQL for all
        TEXT and BLOB types).

        Returns:
            str: The SQL data type definition, which is always the string
            ``'MEDIUMTEXT'``.

        Example:
            Creating a table with a MEDIUMTEXT column for storing detailed
            product descriptions::

                from ormophine.Mysql import DataTypes, TableStructure

                product_table = (TableStructure('products')
                                .add_column('id', DataTypes.INT(), primary_key=True,
                                            auto_increment=True, not_null=True)
                                .add_column('name', DataTypes.VARCHAR(100), not_null=True)
                                .add_column('description', DataTypes.MEDIUMTEXT()))
                # Generates: `description` MEDIUMTEXT

            The MEDIUMTEXT type is also useful for storing long-form content
            such as blog posts or comments::

                blog_table = (TableStructure('blog_posts')
                            .add_column('content', DataTypes.MEDIUMTEXT()))
                # `content` can hold up to ~16 MB of text
        """
        return "MEDIUMTEXT"

    @staticmethod
    def LONGTEXT() -> str:
        """
        Return the SQL data type string for a LONGTEXT column.

        LONGTEXT is the largest text type in MySQL, capable of storing up to
        4,294,967,295 characters (approximately 4 GB). It is suitable for very
        large text content such as extensive articles, logs, or JSON documents
        that exceed the capacity of ``MEDIUMTEXT``.

        Returns:
            str: The SQL data type definition, always ``'LONGTEXT'``.

        Example:
            Defining a column to store very large content::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('documents')
                        .add_column('content', DataTypes.LONGTEXT()))
                # Generates: `content` LONGTEXT
        """
        return "LONGTEXT"

    @staticmethod
    def BINARY(length: int = 1) -> str:
        """
        Return the SQL data type string for a BINARY column.

        BINARY is a fixed‑length binary string type. The ``length`` parameter
        specifies the number of bytes in the column; values shorter than this
        length are right‑padded with zero bytes (``\\x00``) when stored. The
        maximum allowed length is 255 bytes. If a value exceeds the defined
        length, it will be truncated or the database will raise an error
        depending on the SQL mode.

        Args:
            length (int, optional): The fixed byte length of the column. Must be
                between 1 and 255 (inclusive). Defaults to ``1``.

        Returns:
            str: The SQL data type definition, e.g., ``'BINARY(16)'`` or
            ``'BINARY(1)'``.

        Raises:
            None: This method does not perform runtime validation of the length;
                however, passing an invalid length (e.g., 0 or >255) will result
                in a database error when the column is created.

        Example:
            Defining a column to store a UUID (16 bytes) in binary format::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('users')
                        .add_column('uuid', DataTypes.BINARY(16)))
                # Generates: `uuid` BINARY(16)

            Using the default length of 1 byte::

                table.add_column('flag', DataTypes.BINARY())
                # Generates: `flag` BINARY(1)
        """
        return f"BINARY({length})"

    @staticmethod
    def VARBINARY(length: int = 255) -> str:
        """
        Return the SQL data type string for a VARBINARY column.

        VARBINARY is a variable‑length binary string type. It stores binary data
        (bytes) and is suitable for data that should not be interpreted as a
        character string. The maximum length is 65,535 bytes, and the default
        length is 255 bytes if not explicitly specified.

        Args:
            length (int, optional): The maximum number of bytes the column can
                store. Must be an integer between 1 and 65,535. Defaults to 255.

        Returns:
            str: The SQL data type definition, e.g., ``'VARBINARY(255)'`` or
            ``'VARBINARY(1000)'``.

        Raises:
            ValueError: If ``length`` is outside the allowed range (1–65535) –
                though this method does not perform validation itself; it is the
                caller's responsibility to pass a valid length.

        Example:
            Defining a VARBINARY column for storing hashed data (e.g., SHA‑256)::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('users')
                        .add_column('password_hash', DataTypes.VARBINARY(32)))
                # Generates: `password_hash` VARBINARY(32)

            Using the default length::

                table.add_column('binary_data', DataTypes.VARBINARY())
                # Generates: `binary_data` VARBINARY(255)
        """
        return f"VARBINARY({length})"

    @staticmethod
    def TINYBLOB() -> str:
        """
        Return the SQL data type string for a TINYBLOB column.

        TINYBLOB is a binary large object type that can store up to 255 bytes
        of binary data. It is suitable for very small binary content such as
        icons, tiny images, or short binary strings. Unlike text types, BLOB
        types store binary data without a character set or collation, making
        them ideal for non‑text data.

        This type is part of the MySQL BLOB family, which also includes BLOB,
        MEDIUMBLOB, and LONGBLOB for larger storage capacities.

        Returns:
            str: The SQL data type definition, exactly ``'TINYBLOB'``.

        Example:
            Defining a column for a small avatar image::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('users')
                        .add_column('avatar', DataTypes.TINYBLOB()))
                # Generates: `avatar` TINYBLOB
        """
        return "TINYBLOB"

    @staticmethod
    def BLOB(size: str = None) -> str:
        """
        Return the SQL data type string for a BLOB column.

        BLOB (Binary Large Object) is a variable-length binary string type with a
        maximum length determined by the specified size variant. By default (when
        ``size`` is ``None``), this returns the standard ``BLOB`` type, which can
        store up to 65,535 bytes. The optional ``size`` parameter allows specifying
        one of the four MySQL binary large object variants: ``'TINYBLOB'``,
        ``'BLOB'``, ``'MEDIUMBLOB'``, or ``'LONGBLOB'``.

        BLOB columns are used for storing binary data such as images, files, or
        serialized objects. They cannot have default values.

        Args:
            size (str, optional): A string indicating the desired BLOB size variant.
                Must be one of ``'TINYBLOB'``, ``'BLOB'``, ``'MEDIUMBLOB'``, or
                ``'LONGBLOB'``. (Note: the correct values are ``'TINYBLOB'``,
                ``'BLOB'``, ``'MEDIUMBLOB'``, and ``'LONGBLOB'``.) Case-insensitive.
                Defaults to ``None``, which returns ``'BLOB'``.

        Returns:
            str: The SQL data type definition, e.g., ``'BLOB'``, ``'LONGBLOB'``,
            or ``'MEDIUMBLOB'``.

        Raises:
            ValueError: If the provided ``size`` is not one of the allowed values.

        Example:
            Defining a BLOB column using the default size::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('files')
                        .add_column('data', DataTypes.BLOB()))
                # Generates: `data` BLOB

            Using a larger BLOB type::

                table.add_column('large_data', DataTypes.BLOB('LONGBLOB'))
                # Generates: `large_data` LONGBLOB
        """
        if size:
            valid = {"TINYBLOB", "BLOB", "MEDIUMBLOB", "LONGBLOB"}
            if size.upper() in valid:
                return size.upper()
            raise ValueError(f"Invalid BLOB size. Choose from {valid}")
        return "BLOB"

    @staticmethod
    def MEDIUMBLOB() -> str:
        """
        Return the SQL data type string for a MEDIUMBLOB column.

        MEDIUMBLOB is a binary large object type that can store up to
        16,777,215 bytes (16 MiB). It is suitable for storing medium-sized
        binary data such as images, documents, or serialized objects.

        This type cannot have a default value.

        Returns:
            str: The SQL data type definition, exactly ``'MEDIUMBLOB'``.

        Example:
            Defining a MEDIUMBLOB column in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('attachments')
                        .add_column('file_data', DataTypes.MEDIUMBLOB()))
                # Generates: `file_data` MEDIUMBLOB
        """
        return "MEDIUMBLOB"

    @staticmethod
    def LONGBLOB() -> str:
        """
        Return the SQL data type string for a LONGBLOB column.

        LONGBLOB is the largest binary large object type in MySQL, capable of
        storing up to 4,294,967,295 bytes (4 GiB). It is used for very large
        binary data such as videos, large files, or extensive binary blobs.

        Returns:
            str: The SQL data type definition ``'LONGBLOB'``.

        Example:
            Defining a LONGBLOB column for storing large binary files::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('videos')
                        .add_column('video_data', DataTypes.LONGBLOB()))
                # Generates: `video_data` LONGBLOB
        """
        return "LONGBLOB"

    @staticmethod
    def ENUM(*values: str) -> str:
        """
        Return the SQL data type string for an ENUM column.

        ENUM is a string object that can have only one value, chosen from a list of
        permitted values. The values are defined at column creation time and are
        stored as strings. This method constructs the ENUM definition by quoting
        and joining the provided values.

        The ENUM type is useful for columns that should only accept a limited set
        of predefined values, such as status fields or categories.

        Args:
            *values (str): Variable number of string values that define the
                permitted options for the ENUM. Each value will be quoted and
                separated by commas in the resulting SQL.

        Returns:
            str: The SQL data type definition, e.g., ``'ENUM('small', 'medium', 'large')'``.

        Example:
            Defining an ENUM column for product sizes::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('products')
                        .add_column('size', DataTypes.ENUM('small', 'medium', 'large')))
                # Generates: `size` ENUM('small','medium','large')

            Using ENUM for a status field with multiple options::

                table.add_column('status', DataTypes.ENUM('active', 'inactive', 'pending'))
                # Generates: `status` ENUM('active','inactive','pending')
        """
        quoted = ", ".join(f"'{v}'" for v in values)
        return f"ENUM({quoted})"

    @staticmethod
    def SET(*values: str) -> str:
        """
        Return the SQL data type string for a SET column.

        A SET is a string object that can store zero or more values from a
        predefined list of allowed values. Each value must be one of the
        provided strings. The column can store multiple values separated by
        commas, and the maximum number of distinct elements is 64.

        The list of allowed values is defined at table creation time and
        cannot be changed later. The order of values in the SET definition
        determines the internal numeric ordering.

        Args:
            *values (str): Variable number of string values that are permitted
                for this SET column. Each value must be a distinct string.
                The total number of values cannot exceed 64.

        Returns:
            str: The SQL data type definition, e.g., ``"SET('red','green','blue')"``.

        Raises:
            None: This method does not perform runtime validation, though it
                is recommended to ensure values do not contain commas or quotes,
                as they would need escaping.

        Example:
            Defining a SET column for storing favorite colors::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('users')
                        .add_column('favorite_colors', DataTypes.SET('red', 'green', 'blue')))
                # Generates: `favorite_colors` SET('red','green','blue')

            Inserting multiple values::

                db.users.insert({'favorite_colors': 'red,green'})
        """
        quoted = ", ".join(f"'{v}'" for v in values)
        return f"SET({quoted})"

    # ========================
    # Date and Time Data Types
    # ========================

    @staticmethod
    def DATE() -> str:
        """
        Return the SQL data type string for a DATE column.

        The DATE type stores a calendar date value in the format ``YYYY-MM-DD``.
        The supported range is from ``'1000-01-01'`` to ``'9999-12-31'`` in MySQL.
        This method returns the SQL string ``'DATE'``, suitable for use in column
        definitions.

        Returns:
            str: The SQL data type definition ``'DATE'``.

        Example:
            Defining a DATE column in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('events')
                        .add_column('event_date', DataTypes.DATE()))
                # Generates: `event_date` DATE
        """
        return "DATE"

    @staticmethod
    def TIME(precision: int = None) -> str:
        """
        Return the SQL data type string for a TIME column.

        TIME represents a time value in the format ``HH:MM:SS``. An optional
        ``precision`` parameter can be specified to enable fractional seconds
        (microsecond precision) with a value between 0 and 6. If no precision is
        given, the standard ``TIME`` type is returned.

        Args:
            precision (int, optional): The number of digits for fractional seconds.
                Must be an integer between 0 and 6 inclusive. If provided, the
                returned type includes the precision in parentheses, e.g.,
                ``TIME(3)``. Defaults to ``None``, which returns the bare ``TIME``
                type.

        Returns:
            str: The SQL data type definition, e.g., ``'TIME'`` or ``'TIME(3)'``.

        Raises:
            None: This method does not perform runtime validation of the precision
                value, though it is recommended to pass values in the valid range.

        Example:
            Defining a TIME column with microsecond precision::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('events')
                        .add_column('start_time', DataTypes.TIME(3)))
                # Generates: `start_time` TIME(3)

            Using the default TIME type without fractional seconds::

                table.add_column('duration', DataTypes.TIME())
                # Generates: `duration` TIME
        """
        if precision is not None:
            return f"TIME({precision})"
        return "TIME"

    @staticmethod
    def DATETIME(precision: int = None) -> str:
        """
        Return the SQL data type string for a DATETIME column.

        DATETIME represents a date and time combination in the format
        ``YYYY-MM-DD HH:MM:SS``. An optional ``precision`` parameter can be
        specified to enable fractional seconds (microsecond precision) with a
        value between 0 and 6. If no precision is given, the standard
        ``DATETIME`` type is returned.

        Args:
            precision (int, optional): The number of digits for fractional seconds.
                Must be an integer between 0 and 6 inclusive. If provided, the
                returned type includes the precision in parentheses, e.g.,
                ``DATETIME(3)``. Defaults to ``None``, which returns the bare
                ``DATETIME`` type.

        Returns:
            str: The SQL data type definition, e.g., ``'DATETIME'`` or
            ``'DATETIME(3)'``.

        Raises:
            None: This method does not perform runtime validation of the precision
                value, though it is recommended to pass values in the valid range.

        Example:
            Defining a DATETIME column with microsecond precision::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('logs')
                        .add_column('created_at', DataTypes.DATETIME(6)))
                # Generates: `created_at` DATETIME(6)

            Using the default DATETIME type without fractional seconds::

                table.add_column('updated_at', DataTypes.DATETIME())
                # Generates: `updated_at` DATETIME
        """
        if precision is not None:
            return f"DATETIME({precision})"
        return "DATETIME"

    @staticmethod
    def TIMESTAMP(precision: int = None) -> str:
        """
        Return the SQL data type string for a TIMESTAMP column.

        TIMESTAMP represents a date and time combination in the format
        ``YYYY-MM-DD HH:MM:SS``, with a range from ``1970-01-01 00:00:01`` UTC to
        ``2038-01-19 03:14:07`` UTC. An optional ``precision`` parameter can be
        specified to enable fractional seconds (microsecond precision) with a value
        between 0 and 6. If no precision is given, the standard ``TIMESTAMP`` type
        is returned.

        Args:
            precision (int, optional): The number of digits for fractional seconds.
                Must be an integer between 0 and 6 inclusive. If provided, the
                returned type includes the precision in parentheses, e.g.,
                ``TIMESTAMP(3)``. Defaults to ``None``, which returns the bare
                ``TIMESTAMP`` type.

        Returns:
            str: The SQL data type definition, e.g., ``'TIMESTAMP'`` or
            ``'TIMESTAMP(6)'``.

        Raises:
            None: This method does not perform runtime validation of the precision
                value, though it is recommended to pass values in the valid range.

        Example:
            Defining a TIMESTAMP column with microsecond precision::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('logs')
                        .add_column('created_at', DataTypes.TIMESTAMP(3)))
                # Generates: `created_at` TIMESTAMP(3)

            Using the default TIMESTAMP type without fractional seconds::

                table.add_column('updated_at', DataTypes.TIMESTAMP())
                # Generates: `updated_at` TIMESTAMP
        """
        if precision is not None:
            return f"TIMESTAMP({precision})"
        return "TIMESTAMP"

    @staticmethod
    def YEAR() -> str:
        """
        Return the SQL data type string for a YEAR column.

        The YEAR type represents a year value in the range 1901 to 2155, or
        0000. It is stored as a 1‑byte integer and is displayed in the format
        ``YYYY``. This type is commonly used for storing year‑only data such as
        birth years, model years, or fiscal years.

        Returns:
            str: The SQL data type definition, always ``'YEAR'``.

        Example:
            Defining a YEAR column in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('products')
                        .add_column('release_year', DataTypes.YEAR()))
                # Generates: `release_year` YEAR

            The YEAR type does not accept any parameters; the returned string
            is always just ``'YEAR'``.
        """
        return "YEAR"

    # ========================
    # Spatial Data Types
    # ========================

    @staticmethod
    def GEOMETRY() -> str:
        """
        Return the SQL data type string for a GEOMETRY column.

        GEOMETRY is a spatial data type that can store any kind of geometry object,
        such as points, line strings, polygons, or collections thereof. It is the
        base type for all spatial types in MySQL and can be used to store spatial
        data in a generic way.

        When using this type, the column can hold any valid geometry value. For
        more specific spatial types, consider using :meth:`POINT`, :meth:`LINESTRING`,
        :meth:`POLYGON`, or the collection types.

        Returns:
            str: The SQL data type definition, always ``'GEOMETRY'``.

        Example:
            Defining a GEOMETRY column in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('locations')
                        .add_column('geo_data', DataTypes.GEOMETRY()))
                # Generates: `geo_data` GEOMETRY

            Using it with a spatial index (not directly supported by the ORM, but
            can be added via custom SQL)::

                # The column can store points, lines, polygons, etc.
                db.custom_execute(
                    "CREATE SPATIAL INDEX idx_geo ON locations(geo_data);"
                )
        """
        return "GEOMETRY"

    @staticmethod
    def POINT() -> str:
        """
        Return the SQL data type string for a POINT column.

        POINT is a spatial data type representing a point in two-dimensional space
        (X and Y coordinates). It is part of MySQL's geometry type family and can
        be used with spatial indexes and functions for geographic or geometric
        calculations.

        Returns:
            str: The SQL data type definition, always ``'POINT'``.

        Example:
            Defining a POINT column in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('locations')
                        .add_column('coordinates', DataTypes.POINT()))
                # Generates: `coordinates` POINT

            This column can then be used with MySQL's spatial functions like
            ``ST_Contains``, ``ST_Distance``, etc.
        """
        return "POINT"

    @staticmethod
    def LINESTRING() -> str:
        """
        Return the SQL data type string for a LINESTRING column.

        LINESTRING is a spatial data type representing a curve with linear
        interpolated points. It is used in geographic information systems (GIS)
        to store line geometries, such as roads, rivers, or routes. This method
        returns the bare ``LINESTRING`` type definition without any additional
        parameters.

        Returns:
            str: The SQL data type definition, always ``'LINESTRING'``.

        Example:
            Defining a LINESTRING column in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('routes')
                        .add_column('path', DataTypes.LINESTRING()))
                # Generates: `path` LINESTRING
        """
        return "LINESTRING"

    @staticmethod
    def POLYGON() -> str:
        """
        Return the SQL data type string for a POLYGON column.

        POLYGON is a spatial data type representing a closed planar shape defined
        by a set of points forming a boundary. It is commonly used in geographic
        information systems (GIS) to store areas such as countries, lakes, or
        property boundaries. A polygon consists of at least one linear ring (a
        closed loop) and may contain interior rings (holes). This method returns
        the bare ``POLYGON`` type definition without any additional parameters.

        Returns:
            str: The SQL data type definition, always ``'POLYGON'``.

        Example:
            Defining a POLYGON column in a table structure for storing geographic
            areas::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('geographic_areas')
                        .add_column('boundary', DataTypes.POLYGON()))
                # Generates: `boundary` POLYGON
        """
        return "POLYGON"

    @staticmethod
    def MULTIPOINT() -> str:
        """
        Return the SQL data type string for a MULTIPOINT column.

        MULTIPOINT is a spatial data type representing a collection of zero or more
        :class:`POINT` geometries. It is used in geographic information systems
        (GIS) to store multiple point locations, such as clusters of landmarks or
        sensor positions. This method returns the bare ``MULTIPOINT`` type
        definition without any additional parameters.

        Returns:
            str: The SQL data type definition, always ``'MULTIPOINT'``.

        Example:
            Defining a MULTIPOINT column in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('sensor_networks')
                        .add_column('locations', DataTypes.MULTIPOINT()))
                # Generates: `locations` MULTIPOINT
        """
        return "MULTIPOINT"

    @staticmethod
    def MULTILINESTRING() -> str:
        """
        Return the SQL data type string for a MULTILINESTRING column.

        MULTILINESTRING is a spatial data type that represents a collection of
        one or more :class:`LINESTRING` geometries. It is used in geographic
        information systems (GIS) to store multiple line features, such as road
        networks, river systems, or other compound linear geometries. This method
        returns the bare ``MULTILINESTRING`` type definition without additional
        parameters.

        Returns:
            str: The SQL data type definition, always ``'MULTILINESTRING'``.

        Example:
            Defining a MULTILINESTRING column in a table structure for storing
            multiple route paths::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('road_networks')
                        .add_column('routes', DataTypes.MULTILINESTRING()))
                # Generates: `routes` MULTILINESTRING
        """
        return "MULTILINESTRING"

    @staticmethod
    def MULTIPOLYGON() -> str:
        """
        Return the SQL data type string for a MULTIPOLYGON column.

        MULTIPOLYGON is a spatial data type representing a collection of polygons
        in a geographic information system (GIS). It can store multiple polygon
        geometries as a single value, useful for representing complex regions
        such as countries with islands, administrative boundaries, or multi-part
        land parcels. This method returns the bare ``MULTIPOLYGON`` type definition
        without any additional parameters.

        Returns:
            str: The SQL data type definition, always ``'MULTIPOLYGON'``.

        Example:
            Defining a MULTIPOLYGON column in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('countries')
                        .add_column('boundary', DataTypes.MULTIPOLYGON()))
                # Generates: `boundary` MULTIPOLYGON
        """
        return "MULTIPOLYGON"

    @staticmethod
    def GEOMETRYCOLLECTION() -> str:
        """
        Return the SQL data type string for a GEOMETRYCOLLECTION column.

        GEOMETRYCOLLECTION is a spatial data type that can store a collection of
        mixed geometry types, such as points, linestrings, and polygons, all within
        a single column. It is useful for representing complex geographic features
        that consist of multiple geometric shapes. This method returns the bare
        ``GEOMETRYCOLLECTION`` type definition without any additional parameters.

        Returns:
            str: The SQL data type definition, always ``'GEOMETRYCOLLECTION'``.

        Example:
            Defining a GEOMETRYCOLLECTION column in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('geospatial_data')
                        .add_column('mixed_shapes', DataTypes.GEOMETRYCOLLECTION()))
                # Generates: `mixed_shapes` GEOMETRYCOLLECTION
        """
        return "GEOMETRYCOLLECTION"

    # ========================
    # JSON Data Type
    # ========================

    @staticmethod
    def JSON() -> str:
        """
        Return the SQL data type string for a JSON column.

        This method generates the native JSON data type introduced in MySQL 5.7.
        JSON columns store JSON (JavaScript Object Notation) documents and provide
        automatic validation of JSON data. They support efficient indexing and
        querying of JSON values using JSON functions and operators.

        Returns:
            str: The SQL data type definition, always ``'JSON'``.

        Example:
            Defining a JSON column in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('settings')
                        .add_column('configuration', DataTypes.JSON()))
                # Generates: `configuration` JSON
        """
        return "JSON"

    # ========================
    # Special / Other
    # ========================

    @staticmethod
    def SERIAL() -> str:
        """
        Return the SQL data type string for a SERIAL column.

        SERIAL is a MySQL alias for ``BIGINT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE``.
        It is a convenience shorthand commonly used for auto‑incrementing primary keys.
        The type provides a large integer range (0 to 2⁶⁴‑1) and automatically generates
        a unique, non‑null value for each inserted row.

        Returns:
            str: The SQL data type definition, always ``'SERIAL'``.

        Example:
            Using SERIAL as an auto‑increment primary key in a table structure::

                from ormophine.Mysql import DataTypes, TableStructure

                table = (TableStructure('users')
                        .add_column('id', DataTypes.SERIAL(), primary_key=True,
                                    auto_increment=True, not_null=True))
                # Generates: `id` SERIAL

            Note that when using ``DataTypes.SERIAL()``, you typically set
            ``primary_key=True``, ``auto_increment=True``, and ``not_null=True``
            explicitly, or rely on the convenience method in your table builder.
        """
        return "SERIAL"

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
        

class TableStructure:
    """
    A builder class for constructing MySQL table definitions.

    This class provides a fluent interface for defining columns, primary keys,
    foreign keys, and table-level options (engine, charset, collation). Once
    the structure is fully defined, the :meth:`get_structure` method generates
    a complete ``CREATE TABLE`` SQL statement that can be executed via the
    :class:`Driver` or directly on a database connection.

    The builder pattern allows method chaining (e.g., ``TableStructure(...)
    .add_column(...).add_column(...).foreign_key(...)``) for concise and
    readable table definitions. All columns are stored internally and validated
    for consistency before generating the final SQL.

    Attributes:
        table_query (str): The internal SQL fragment containing column and
            constraint definitions (comma‑separated).
        primary_keys (list): List of column names (with backticks) that form
            the primary key.
        items (dict): Internal storage mapping column names to their properties
            (datatype, default, unique, not_null, primary_key, auto_increment).
        name (str): The table name, enclosed in backticks.
        foreigns (list): List of foreign key constraint fragments.
        charset (str): The character set for the table (e.g., ``'utf8mb4'``).
        collate (str): The collation for the table (e.g., ``'utf8mb4_bin'``).

    Args:
        table_name (str): The name of the table to be created.
        charset (CHARSET, optional): The character set for the table.
            Defaults to ``'utf8mb4'``.
        collate (COLLATE, optional): The collation for the table.
            Defaults to ``'utf8mb4_bin'``.

    Raises:
        Exception: If validation fails during column addition (e.g., duplicate
            column name, invalid AUTO_INCREMENT usage, or conflicting constraints).
        Exception: If :meth:`get_structure` is called with no columns defined.

    Example:
        Creating a table structure for a ``users`` table with various column types
        and constraints, then using it with a :class:`Driver` instance::

            from ormophine.Mysql import TableStructure, DataTypes, Driver

            # Build the table definition
            users_table = (TableStructure('users', charset='utf8mb4')
                           .add_column('id', DataTypes.INT(),
                                       primary_key=True,
                                       auto_increment=True,
                                       not_null=True)
                           .add_column('username', DataTypes.VARCHAR(50),
                                       not_null=True,
                                       unique=True)
                           .add_column('email', DataTypes.VARCHAR(255),
                                       not_null=True)
                           .add_column('age', DataTypes.TINYINT(),
                                       default_value=0)
                           .add_column('bio', DataTypes.TEXT())
                           .add_column('created_at', DataTypes.DATETIME(),
                                       default_value='CURRENT_TIMESTAMP')
                           .foreign_key('email', 'profiles', 'user_email',
                                        on_delete='CASCADE'))

            # Connect to the database and create the table
            db = Driver(host='localhost', port=3306, username='root',
                        password='secret', db_name='myapp')
            db.create_table(users_table)

            # The table is now available as an attribute on the driver
            db.users.insert({'username': 'alice', 'email': 'alice@example.com'})

    Note:
        The class is designed for MySQL and uses MySQL-specific syntax.
        It does not support all advanced features like CHECK constraints or
        partitions, but covers the most common DDL operations.
    """
    ON_ACTION= Literal['CASCADE', 'SET NULL', 'SET DEFAULT', 'RESTRICT', 'NO ACTION']
    CHARSET = Literal[
    "armscii8",
    "ascii",
    "big5",
    "binary",
    "cp1250",
    "cp1251",
    "cp1256",
    "cp1257",
    "cp850",
    "cp852",
    "cp866",
    "cp932",
    "dec8",
    "eucjpms",
    "euckr",
    "gb18030",
    "gb2312",
    "gbk",
    "geostd8",
    "greek",
    "hebrew",
    "hp8",
    "keybcs2",
    "koi8r",
    "koi8u",
    "latin1",
    "latin2",
    "latin5",
    "latin7",
    "macce",
    "macroman",
    "sjis",
    "swe7",
    "tis620",
    "ucs2",
    "ujis",
    "utf16",
    "utf16le",
    "utf32",
    "utf8mb3",
    "utf8mb4"
    ]
    COLLATE = Literal[
    "utf8mb4_0900_ai_ci",
    "utf8mb4_0900_as_cs",
    "utf8mb4_0900_bin",
    "utf8mb4_general_ci",
    "utf8mb4_unicode_ci",
    "utf8mb4_unicode_520_ci",
    "utf8mb4_bin",
    "utf8mb4_persian_ci",
    "utf8mb4_ar_0900_ai_ci",
    "utf8mb4_da_0900_ai_ci",
    "utf8mb4_de_pb_0900_ai_ci",
    "utf8mb4_en_0900_ai_ci",
    "utf8mb4_es_0900_ai_ci",
    "utf8mb4_es_trad_0900_ai_ci",
    "utf8mb4_fr_0900_ai_ci",
    "utf8mb4_it_0900_ai_ci",
    "utf8mb4_nl_0900_ai_ci",
    "utf8mb4_pt_0900_ai_ci",
    "utf8mb4_cs_0900_ai_ci",
    "utf8mb4_hr_0900_ai_ci",
    "utf8mb4_hu_0900_ai_ci",
    "utf8mb4_pl_0900_ai_ci",
    "utf8mb4_ro_0900_ai_ci",
    "utf8mb4_sk_0900_ai_ci",
    "utf8mb4_sl_0900_ai_ci",
    "utf8mb4_sv_0900_ai_ci",
    "utf8mb4_nb_0900_ai_ci",
    "utf8mb4_nn_0900_ai_ci",
    "utf8mb4_is_0900_ai_ci",
    "utf8mb4_lt_0900_ai_ci",
    "utf8mb4_lv_0900_ai_ci",
    "utf8mb4_et_0900_ai_ci",
    "utf8mb4_bg_0900_ai_ci",
    "utf8mb4_sr_latn_0900_ai_ci",
    "utf8mb4_bs_0900_ai_ci",
    "utf8mb4_mk_0900_ai_ci",
    "utf8mb4_ja_0900_as_cs",
    "utf8mb4_ko_0900_as_cs",
    "utf8mb4_zh_0900_as_cs",
    "utf8mb4_tr_0900_ai_ci",
    "utf8mb4_vi_0900_ai_ci",
    "utf8mb4_0900_as_cs",
    "utf8mb4_da_0900_as_cs",
    "utf8mb4_es_0900_as_cs",
    "utf8mb4_fr_0900_as_cs",
    "utf8mb4_it_0900_as_cs",
    "utf8mb4_ja_0900_as_cs",
    "utf8mb4_ko_0900_as_cs",
    "utf8mb4_zh_0900_as_cs",
    "utf8mb4_croatian_ci",
    "utf8mb4_czech_ci",
    "utf8mb4_danish_ci",
    "utf8mb4_esperanto_ci",
    "utf8mb4_estonian_ci",
    "utf8mb4_german2_ci",
    "utf8mb4_hungarian_ci",
    "utf8mb4_icelandic_ci",
    "utf8mb4_latvian_ci",
    "utf8mb4_lithuanian_ci",
    "utf8mb4_polish_ci",
    "utf8mb4_romanian_ci",
    "utf8mb4_slovak_ci",
    "utf8mb4_slovenian_ci",
    "utf8mb4_swedish_ci",
    "utf8mb4_turkish_ci"
    ]

    def __init__(self, table_name: str, charset: CHARSET = "utf8mb4", collate: COLLATE = "utf8mb4_bin"):
        """
        Initialize a new table structure builder for creating a MySQL table.

        The :class:`TableStructure` class is used to programmatically define a table's
        columns, constraints, foreign keys, and table‑level options. This constructor
        sets the table name, character set, and collation. Columns are added via
        :meth:`add_column`, and the final ``CREATE TABLE`` statement is generated
        by :meth:`get_structure`.

        Args:
            table_name (str): The name of the table to be created. It will be
                quoted with backticks internally.
            charset (CHARSET, optional): The default character set for the table.
                Must be one of the valid MySQL character set names (e.g.,
                ``'utf8mb4'``, ``'latin1'``). Defaults to ``'utf8mb4'``.
            collate (COLLATE, optional): The default collation for the table.
                Must be one of the valid MySQL collation names (e.g.,
                ``'utf8mb4_bin'``, ``'utf8mb4_general_ci'``). Defaults to
                ``'utf8mb4_bin'``.

        Returns:
            None

        Example:
            Building a simple table structure::

                from ormophine.Mysql import TableStructure, DataTypes

                users = (TableStructure('users', charset='utf8mb4', collate='utf8mb4_unicode_ci')
                        .add_column('id', DataTypes.INT(), primary_key=True, auto_increment=True, not_null=True)
                        .add_column('username', DataTypes.VARCHAR(50), not_null=True, unique=True)
                        .add_column('created_at', DataTypes.DATETIME(), default_value='CURRENT_TIMESTAMP'))
        """
        self.table_query= ''
        self.primary_keys= []
        self.items= {}
        self.name= f'`{table_name}`'
        self.foreigns= []
        self.charset = charset
        self.collate = collate

    def _validate_column(
        self,
        column_name,
        datatype,
        default_value,
        unique,
        not_null,
        primary_key,
        auto_increment
    ):
        """
        Validate column definition parameters before adding a column.

        This internal method performs comprehensive validation of column properties
        to ensure they are consistent with MySQL rules. It checks data type validity,
        primary key constraints, uniqueness, auto_increment rules, default value
        compatibility, and other logical constraints. If any validation fails, a
        descriptive exception is raised.

        Args:
            column_name (str): The name of the column being validated (already
                backtick-quoted).
            datatype (str): The SQL data type string (e.g., returned by
                :class:`DataTypes` methods).
            default_value (Any): The default value for the column, or ``None``.
            unique (bool): Whether the column should have a UNIQUE constraint.
            not_null (bool): Whether the column is NOT NULL.
            primary_key (bool): Whether the column is a PRIMARY KEY.
            auto_increment (bool): Whether the column has AUTO_INCREMENT.

        Returns:
            None: This method does not return a value; it raises exceptions on
            validation failure.

        Raises:
            TypeError: If ``datatype`` is not a string.
            Exception: For various validation errors, including:
                - PRIMARY KEY columns must be NOT NULL.
                - PRIMARY KEY columns cannot also be UNIQUE.
                - Column name already exists in the table definition.
                - Bytes objects cannot be used as default values.
                - Only one AUTO_INCREMENT column is allowed per table.
                - AUTO_INCREMENT is only allowed on numeric columns.
                - AUTO_INCREMENT column must be PRIMARY KEY or UNIQUE.
                - AUTO_INCREMENT columns cannot have DEFAULT values.
                - TEXT and BLOB columns cannot have default values.
                - SERIAL implies PRIMARY KEY, AUTO_INCREMENT, and NOT NULL.

        Example:
            This method is called internally by :meth:`add_column` and should not
            typically be used directly::

                # Internal usage within TableStructure
                table_structure._validate_column(
                    column_name='`id`',
                    datatype='INT',
                    default_value=None,
                    unique=False,
                    not_null=True,
                    primary_key=True,
                    auto_increment=True
                )
                # Validation passes

                # Invalid: PRIMARY KEY with UNIQUE
                # Raises Exception: "PRIMARY KEY columns cannot be UNIQUE"
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
                raise Exception("Only one AUTO_INCREMENT column is allowed.")

        numeric = (
            "BIT",
            "TINYINT",
            "SMALLINT",
            "MEDIUMINT",
            "INT",
            "BIGINT",
            "DECIMAL",
            "NUMERIC",
            "FLOAT",
            "DOUBLE",
            "REAL"
        )

        if auto_increment:
            if datatype.split("(")[0].split()[0] not in numeric:
                raise Exception("AUTO_INCREMENT is only allowed on numeric columns.")
            if not (primary_key or unique):
                raise Exception("AUTO_INCREMENT column must be PRIMARY KEY or UNIQUE.")
            if default_value is not None:
                raise Exception("AUTO_INCREMENT columns cannot have DEFAULT values.")
            
        if 'TEXT' in datatype or 'BLOB' in datatype:
            if default_value is not None:
                raise Exception("TEXT and BLOB columns cannot have default values.")
            
    def add_column(self, column_name: str, datatype: DataTypes,
                    default_value=None, unique: bool = None,
                    not_null: bool = None,
                    primary_key: bool = None,
                    auto_increment: bool = False):
        """
        Add a column definition to the table structure.

        This method defines a new column with the given name and data type,
        along with optional constraints (default, unique, not null, primary key,
        auto-increment). The column is added to the internal representation of
        the table; the actual SQL is generated later by :meth:`get_structure`.
        The method performs comprehensive validation of the column options to
        ensure they are consistent with MySQL rules.

        If the ``datatype`` is ``'SERIAL'``, the method automatically sets
        ``primary_key``, ``not_null``, and ``auto_increment`` to ``True``,
        overriding any provided values. This follows MySQL's ``SERIAL`` alias
        behavior.

        Args:
            column_name (str): The name of the column. It will be sanitized and
                quoted as an identifier (backticks added).
            datatype (DataTypes): A string returned by one of the :class:`DataTypes`
                static methods, e.g., ``DataTypes.INT()`` or ``DataTypes.VARCHAR(255)``.
            default_value (Any, optional): The default value for the column. If a
                string, it will be quoted in the SQL. Bytes objects are not allowed.
                Defaults to ``None``.
            unique (bool, optional): If ``True``, adds a ``UNIQUE`` constraint.
                Defaults to ``None`` (no constraint). Cannot be used with ``primary_key``.
            not_null (bool, optional): If ``True``, adds a ``NOT NULL`` constraint.
                Defaults to ``None``. Must be ``True`` for primary keys.
            primary_key (bool, optional): If ``True``, designates the column as a
                primary key. Implies ``not_null`` and uniqueness. Defaults to ``None``.
            auto_increment (bool, optional): If ``True``, enables auto-increment.
                Only allowed on numeric columns and requires the column to be a
                primary key or unique. Defaults to ``False``.

        Returns:
            TableStructure: The current instance, allowing method chaining.

        Raises:
            TypeError: If ``datatype`` is not a string.
            Exception: If any validation rule is violated, such as:
                - PRIMARY KEY column not NOT NULL.
                - PRIMARY KEY column also marked UNIQUE.
                - Duplicate column name.
                - Default value is a bytes object.
                - More than one AUTO_INCREMENT column defined.
                - AUTO_INCREMENT on a non-numeric column.
                - AUTO_INCREMENT without PRIMARY KEY or UNIQUE.
                - AUTO_INCREMENT with a default value.
                - DEFAULT on TEXT or BLOB columns.
                - SERIAL used without PRIMARY KEY, AUTO_INCREMENT, and NOT NULL.

        Example:
            Building a table structure with columns::

                from ormophine.Mysql import TableStructure, DataTypes

                table = (TableStructure('users')
                        .add_column('id', DataTypes.INT(), primary_key=True,
                                    auto_increment=True, not_null=True)
                        .add_column('username', DataTypes.VARCHAR(50),
                                    unique=True, not_null=True)
                        .add_column('age', DataTypes.TINYINT(), default_value=0)
                        .add_column('bio', DataTypes.TEXT()))
                # The structure is now ready for get_structure()
        """
        column_name = f'`{column_name.strip()}`'
        auto_increment , not_null, unique = (False, False, False) if 'SERIAL' in datatype else (auto_increment, not_null, unique)
        self._validate_column(column_name,datatype,default_value,unique,not_null,primary_key,auto_increment)
        for item in self.table_query.split(','):
            if item and (column_name in item) and item.split(' ')[1] == column_name:
                raise Exception('You have added this column befor\nif you wanna modify this column , delete this column and then add a new one with desired options')
        if type(default_value) == bytes:
            raise Exception('Cant set bytes object as default value')
        self.primary_keys.append(column_name) if primary_key else None
        self.items[column_name] = [datatype, default_value, unique, not_null, primary_key, auto_increment]
        self.table_query = self.table_query + f' {column_name.strip()} {datatype}{" AUTO_INCREMENT" if auto_increment else ""}{" UNIQUE" if unique else ""}{" NOT NULL" if not_null else ""}{f" DEFAULT {('TRUE' if default_value else 'FALSE') if isinstance(default_value,bool) else f"'{default_value}'" if type(default_value) == str else str(default_value)}" if default_value is not None else ""},'
        return self

    def delete_column(self, column_name: str):
        """
        Remove a column from the table structure definition.

        This method deletes the specified column from the internal column registry,
        updates the accumulated SQL CREATE TABLE query fragment, and returns the
        :class:`TableStructure` instance for method chaining. If the column does
        not exist, an exception is raised.

        Args:
            column_name (str): The name of the column to delete. Leading/trailing
                whitespace is stripped, and the column name is automatically
                quoted with backticks.

        Returns:
            TableStructure: The current instance, allowing further method chaining
            (e.g., adding more columns or generating the final SQL).

        Raises:
            Exception: If no column with the given name exists in the table structure.

        Example:
            Building a table structure and then removing a column::

                from ormophine.Mysql import TableStructure, DataTypes

                table = (TableStructure('users')
                        .add_column('id', DataTypes.INT(), primary_key=True)
                        .add_column('name', DataTypes.VARCHAR(50))
                        .add_column('email', DataTypes.VARCHAR(255)))

                # Remove the 'email' column
                table.delete_column('email')

                # The final CREATE TABLE statement will only include 'id' and 'name'
                print(table.get_structure())
        """
        column_name = f'`{column_name.strip()}`'
        query_list = self.table_query.split(',')
        self.items.pop(column_name)
        for item in query_list:
            if item.strip().startswith(column_name):
                query_list.remove(item)
                self.table_query = ','.join(query_list)
                return self
        raise Exception(f'No column found with name ({column_name})')

    def get_columns(self):
        """
        Retrieve a list of column definitions from the current table structure.

        This method returns a list of dictionaries, each containing detailed
        information about a column that has been added to the table via
        :meth:`add_column`. The returned data reflects the current state of
        the internal structure and can be used for inspection or to generate
        the final ``CREATE TABLE`` statement.

        Returns:
            list of dict: A list where each element is a dictionary with the
            following keys:

            - ``name`` (str): The column name, including backticks (e.g., ``'`id`'``).
            - ``datatype`` (str): The SQL data type string (e.g., ``'INT'``).
            - ``default_value`` (Any): The default value for the column, or
            ``None`` if not set.
            - ``unique`` (bool): ``True`` if the column has a ``UNIQUE``
            constraint, otherwise ``False``.
            - ``not_null`` (bool): ``True`` if the column is ``NOT NULL``,
            otherwise ``False``.
            - ``primari_key`` (bool): ``True`` if the column is part of the
            primary key, otherwise ``False``. (Note the typo in the key name
            which is preserved from the original implementation.)

        Raises:
            None: This method does not raise any exceptions.

        Example:
            Building a table structure and retrieving its column definitions::

                from ormophine.Mysql import TableStructure, DataTypes

                struct = (TableStructure('users')
                        .add_column('id', DataTypes.INT(), primary_key=True,
                                    auto_increment=True, not_null=True)
                        .add_column('name', DataTypes.VARCHAR(100),
                                    not_null=True)
                        .add_column('age', DataTypes.INT(), default_value=0))

                columns = struct.get_columns()
                for col in columns:
                    print(f"{col['name']}: {col['datatype']} "
                        f"(PK: {col['primari_key']}, Not Null: {col['not_null']})")
                # Output:
                # `id`: INT (PK: True, Not Null: True)
                # `name`: VARCHAR(100) (PK: False, Not Null: True)
                # `age`: INT (PK: False, Not Null: False)
        """
        items_list = []
        for item in self.items:
            items_dict = {}
            values = self.items[item]
            items_dict['name']= item
            items_dict['datatype']= values[0]
            items_dict['default_value']= values[1]
            items_dict['unique']= True if values[2] else False
            items_dict['not_null']= True if values[3] else False
            items_dict['primari_key']= True if values[4] else False
            items_list.append(items_dict)
        return items_list

    def foreign_key(self, column: str, refrences_table: 'Table',
                    refrences_column: 'Column', on_delete: ON_ACTION = None,
                    on_update: ON_ACTION = None
                    ):
        """
        Add a foreign key constraint to the table structure.

        This method defines a foreign key relationship between a column in the
        current table and a column in a referenced (parent) table. The constraint
        ensures referential integrity by enforcing that values in the foreign key
        column match existing values in the referenced column. Optional ``ON DELETE``
        and ``ON UPDATE`` actions can be specified to control behavior when the
        referenced row is deleted or updated.

        The constraint is added to the internal list of foreign keys and will be
        included in the final ``CREATE TABLE`` statement generated by
        :meth:`get_structure`. Multiple foreign keys can be added to the same table.

        Args:
            column (str): The name of the column in the current table that will
                serve as the foreign key. This column must already have been
                added via :meth:`add_column`.
            refrences_table (Table): The referenced (parent) table object.
                This is typically an existing table instance from the driver.
            refrences_column (Column): The referenced column object in the
                parent table. This column should be the primary key or have a
                unique constraint.
            on_delete (ON_ACTION, optional): The action to take when a referenced
                row is deleted. Must be one of ``'CASCADE'``, ``'SET NULL'``,
                ``'SET DEFAULT'``, ``'RESTRICT'``, or ``'NO ACTION'``.
                Defaults to ``None`` (no ON DELETE clause).
            on_update (ON_ACTION, optional): The action to take when a referenced
                column value is updated. Same allowed values as ``on_delete``.
                Defaults to ``None`` (no ON UPDATE clause).

        Returns:
            TableStructure: The current instance, allowing method chaining.

        Raises:
            None: This method does not perform validation at call time. However,
                an invalid column name or reference may cause the final SQL
                statement to fail when executed by :meth:`Driver.create_table`
                or :meth:`Table.get_structure`.

        Example:
            Building a table with a foreign key reference to a ``users`` table::

                from ormophine.Mysql import TableStructure, DataTypes, Table

                # Assume `db` is a Driver instance with a `users` table
                users_table = db.users  # Table object

                orders = (TableStructure('orders')
                        .add_column('id', DataTypes.INT(), primary_key=True,
                                    auto_increment=True, not_null=True)
                        .add_column('user_id', DataTypes.INT(), not_null=True)
                        .add_column('product', DataTypes.VARCHAR(100))
                        .foreign_key('user_id', users_table, users_table.id,
                                    on_delete='CASCADE', on_update='CASCADE'))

                db.create_table(orders)
                # The generated table will include:
                # FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
                # ON DELETE CASCADE ON UPDATE CASCADE
        """
        self.foreigns.append(f'FOREIGN KEY ({column}) REFERENCES {refrences_table.name_} ({refrences_column.first_name}){f' ON DELETE {on_delete}' if on_delete else ''}{f' ON UPDATE {on_update}' if on_update else ''}')
        return self

    def get_structure(self):
        """
        Generate the complete CREATE TABLE SQL statement for the current table structure.

        This method assembles the internal column definitions, primary key constraints,
        foreign key constraints, and table options (engine, charset, collation) into
        a valid MySQL ``CREATE TABLE`` statement. It validates that at least one
        column has been defined before generating the SQL.

        Returns:
            str: A fully-formed ``CREATE TABLE`` SQL statement that can be executed
            to create the table in the database.

        Raises:
            Exception: If no columns have been added to the structure (i.e.,
                :meth:`get_columns` returns an empty list). The error message will
                indicate that at least one column is required.

        Example:
            Building a table structure and obtaining its SQL statement::

                from ormophine.Mysql import TableStructure, DataTypes

                struct = (TableStructure('users')
                        .add_column('id', DataTypes.INT(), primary_key=True,
                                    auto_increment=True, not_null=True)
                        .add_column('name', DataTypes.VARCHAR(100), not_null=True)
                        .add_column('email', DataTypes.VARCHAR(255), unique=True)
                        .foreign_key('email', 'profiles', 'user_email',
                                    on_delete='CASCADE'))

                sql = struct.get_structure()
                print(sql)
                # Output:
                # CREATE TABLE `users` (`id` INT NOT NULL AUTO_INCREMENT,
                # `name` VARCHAR(100) NOT NULL, `email` VARCHAR(255) UNIQUE,
                # PRIMARY KEY (`id`),
                # FOREIGN KEY (`email`) REFERENCES `profiles` (`user_email`) ON DELETE CASCADE)
                # ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
        """
        if self.get_columns():
            return f'CREATE TABLE {self.name} ({self.table_query[:-1]}{f', PRIMARY KEY({', '.join(self.primary_keys)})' if self.primary_keys else ''}{f', {','.join(self.foreigns)}' if self.foreigns else ''})  ENGINE=InnoDB DEFAULT CHARSET={self.charset} COLLATE={self.collate};' 
        else :
            raise Exception('You must add at least one column to create a table')

