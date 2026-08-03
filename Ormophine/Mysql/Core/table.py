from __future__ import annotations
from .. import Column, ColumnsOperation, BatchOperation, Join, Any

class Table:
    """
    Represents a database table and provides an ORM-like interface for operations.

    The :class:`Table` class is the primary interface for interacting with a
    specific database table. It is typically created automatically by the
    :class:`Driver` when a connection is established, and each table in the
    database becomes an attribute of the driver instance (e.g., ``db.users``).

    Each :class:`Table` instance dynamically creates :class:`Column` attributes
    for every column in the table, allowing you to reference columns as
    attributes (e.g., ``users.id``, ``users.name``). These columns can be used
    in queries, comparisons, and operations.

    The class provides a full suite of methods for:
        - Inserting, updating, deleting rows.
        - Querying with optional filtering and ordering.
        - Batch operations for performance.
        - Joining tables.
        - Index management.
        - Schema modification (adding/dropping columns, renaming tables/columns).
        - Executing custom SQL.

    **Placeholder Mechanism for Bulk Updates**
        The :attr:`PLACE_HOLDER` attribute (a unique string) is used internally
        in :meth:`bulk_update` to mark positions where values from the data list
        should be substituted. If you need to change this placeholder, you can
        override it on a per-table basis::

            table.PLACE_HOLDER = 'MY_CUSTOM_PLACEHOLDER'

        However, ensure that this string does not appear in your actual data,
        as it is used for string replacement.

    Attributes:
        name_ (str): The table name wrapped in backticks (e.g., ``'`users`'``).
        db_obj (Driver): The parent driver instance that owns this table.
        PLACE_HOLDER (str): A unique placeholder string used in bulk updates
            (default: ``'_MY_S4ULT3D_PL4C3_H0LD3R_%s_'``).
        <column_name> (Column): For each column in the table, a :class:`Column`
            attribute is dynamically created (e.g., ``table.id``, ``table.name``).

    Example:
        Assuming a driver instance ``db`` connected to a database with a
        ``users`` table::

            # Access the table
            users = db.users

            # Insert a new user
            users.insert({users.name: 'Alice', users.age: 30})

            # Update a user
            users.update(
                {users.age: 31},
                where=users.name == 'Alice'
            )

            # Query rows
            rows = users.get_row(
                which_columns=[users.name, users.age],
                where=users.age >= 18,
                order_by=users.name
            )
            # rows is a list of tuples: [('Alice', 31), ('Bob', 25), ...]

            # Batch insert
            users.bulk_insert(
                columns=[users.name, users.age],
                data_list=[['Charlie', 40], ['Dave', 22]]
            )

            # Delete rows
            users.delete_row(where=users.age > 100)

        For more advanced operations like joins and batch updates, refer to the
        individual method documentation.
    """
    PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
    def __init__(self, obj: Driver, table_name: str):
        """
        Initialize a Table instance representing a database table.

        This constructor stores the provided :class:`Driver` instance and the
        table name. It then retrieves the table's schema information using
        :meth:`get_table_info`, and for each column, dynamically creates an
        attribute on the instance. The attribute name is the column name, and
        its value is a :class:`Column` object representing that column.

        Args:
            obj (Driver): The driver instance managing the database connection
                and connection pool. This is used to execute queries against
                the table.
            table_name (str): The name of the database table. This will be
                quoted as an identifier (surrounded by backticks) internally.

        Returns:
            None

        Raises:
            Exception: If the table does not exist or the database query fails
                (propagated from :meth:`get_table_info`). The exception message
                will include the original error and context.

        Example:
            Assuming a configured :class:`Driver` instance ``db`` connected to
            a database containing a table named ``users``::

                # The Table instance is automatically created when the driver
                # loads existing tables, but you can also create one manually:
                users_table = Table(db, 'users')

                # Access columns as attributes:
                users_table.id           # Column object for 'id'
                users_table.username     # Column object for 'username'

                # The instance is also added as an attribute of the driver:
                # db.users is the same object if the table existed at driver init.
        """
        self.name_= '`'+table_name+'`'
        self.db_obj = obj
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
        for i in self.get_table_info():
            self.__setattr__(i['name'], Column(self, i['name'], i['datatype']))

    def _exc(self, query):
        """
        Execute a SQL query without parameters and commit the transaction.

        This is an internal wrapper method that delegates the execution to the
        underlying :class:`Driver` instance's :meth:`~Driver._exc` method.
        It is used for queries that do not require parameter substitution, such as
        ``CREATE TABLE``, ``DROP TABLE``, or ``ALTER TABLE`` statements. The
        transaction is automatically committed upon successful execution.

        Args:
            query (str): The SQL query string to execute. Must not contain
                placeholders (``%s``), as no parameters are provided.

        Returns:
            None

        Raises:
            Exception: If an operational or programming error occurs during
                execution. The exception is propagated from the driver layer
                and includes details about the query and the original error.

        Example:
            Renaming a column using the internal method::

                # Assuming `users` is a Table instance
                users._exc("ALTER TABLE `users` ADD COLUMN `age` INT;")
        """
        self.db_obj._exc(query)

    def _excp(self, query, params):
        """
        Execute a parameterized SQL query on the table's database connection.

        This internal method delegates to the underlying :class:`Driver` instance's
        ``_excp`` method, which handles connection pooling, transaction management,
        and error recovery. It is intended for use by other :class:`Table` methods
        that require parameterized queries.

        Args:
            query (str): The SQL query string containing placeholders (``%s``) for
                parameters.
            params (list or tuple): The parameter values to substitute into the query.

        Returns:
            None

        Raises:
            Exception: If an operational or programming error occurs during query
                execution. The exception message will include the original error,
                the query, and the parameters to aid debugging. This method
                propagates any exceptions raised by the driver's ``_excp`` method.

        Example:
            This method is typically used internally, but can be called directly
            for executing custom parameterized queries on a specific table::

                # Assuming `users` is a Table instance
                users._excp(
                    "UPDATE users SET age = %s WHERE id = %s",
                    (25, 1)
                )
        """
        self.db_obj._excp(query, params)

    def _excf(self, query):
        """
        Execute a query without parameters and fetch all results.

        This internal method delegates to the underlying :class:`Driver`'s
        ``_excf`` method, which retrieves a connection from the pool, executes
        the provided query, commits the transaction, and returns the fetched
        rows. It is used internally by various :class:`Table` methods that
        need to retrieve data without parameterized queries.

        Args:
            query (str): The SQL query string to execute. Must not contain
                parameter placeholders.

        Returns:
            list of tuple: A list of rows, where each row is a tuple of column
                values. The structure depends on the query.

        Raises:
            Exception: If the query execution fails (e.g., syntax error,
                connection issue, or other database error). The original error
                and query are included in the exception message.

        Example:
            This method is typically used internally, not directly by user code.
            However, it can be used for custom queries::

                table = db.users
                result = table._excf("SELECT id, name FROM users WHERE active = 1")
                for row in result:
                    print(row)  # e.g., (1, 'Alice')
        """
        return self.db_obj._excf(query)

    def _excfp(self, query, params):
        """
        Execute a parameterized query and fetch all results.

        This internal method delegates to the underlying :class:`Driver`'s
        ``_excfp`` method, which retrieves a connection from the pool, executes
        the provided query with the given parameters, commits the transaction,
        and returns the fetched rows. It is used internally by various
        :class:`Table` methods that need to retrieve data with parameterized
        queries.

        Args:
            query (str): The SQL query string containing ``%s`` placeholders
                for parameters.
            params (list or tuple): The parameter values to substitute into
                the query. Must match the number and order of placeholders.

        Returns:
            list of tuple: A list of rows, where each row is a tuple of column
                values. The structure depends on the query.

        Raises:
            Exception: If the query execution fails (e.g., syntax error,
                parameter mismatch, connection issue, or other database error).
                The original error and query/params are included in the exception
                message.

        Example:
            This method is typically used internally, not directly by user code.
            However, it can be used for custom parameterized queries::

                table = db.users
                result = table._excfp(
                    "SELECT id, name FROM users WHERE age > %s",
                    (18,)
                )
                for row in result:
                    print(row)  # e.g., (1, 'Alice')
        """
        return self.db_obj._excfp(query, params)

    def _excm(self, query, params):
        """
        Execute a parameterized query multiple times with different parameter sets.

        This internal method delegates to the underlying :class:`Driver`'s
        ``_excm`` method, which retrieves a connection from the pool, executes
        the provided query once for each parameter set in the list using
        ``cursor.executemany()``, commits the transaction, and returns the
        connection to the pool. It is typically used for bulk operations like
        :meth:`bulk_insert` and :meth:`bulk_update`.

        Args:
            query (str): The SQL query string containing placeholders (``%s``) for
                parameters.
            params (list of tuple or list of list): A sequence of parameter sets,
                where each set contains the values to substitute into the query
                for one execution. The number of elements in each set must match
                the number of placeholders in the query.

        Returns:
            None

        Raises:
            Exception: If the query execution fails (e.g., syntax error, data type
                mismatch, connection issue, or other database error). The original
                error, query, and parameters are included in the exception message
                to aid debugging.

        Example:
            This method is typically used internally by bulk operations.
            For example, to insert multiple rows::

                table = db.users
                query = "INSERT INTO users (name, age) VALUES (%s, %s)"
                params = [("Alice", 30), ("Bob", 25), ("Charlie", 35)]
                table._excm(query, params)
                # All three rows are inserted in a single round-trip.
        """
        self.db_obj._excm(query, params)

    def _excs(self, query_params: list):
        """
        Execute a batch of SQL statements with optional parameters.

        This internal method delegates to the underlying :class:`Driver`'s
        ``_excs`` method, which processes multiple SQL queries sequentially
        within a single transaction. Each query in the batch can optionally
        include parameter placeholders. The method is used internally by
        :class:`BatchOperation` to execute batched updates or inserts.

        Args:
            query_params (list): A list where each element is either:

                - A list or tuple of exactly two elements: ``[query, params]``,
                where ``query`` is a SQL string with placeholders and ``params``
                is a list/tuple of parameter values.
                - A single string (or a list with one element) representing a
                query without parameters.

        Returns:
            None

        Raises:
            Exception: If any query in the batch fails. The exception message
                includes the original error and a list of all queries and their
                parameters for debugging. The transaction is rolled back on failure.

        Example:
            This method is typically used internally, but can be called for
            batch execution::

                table = db.users
                queries = [
                    ["UPDATE users SET active = 1 WHERE id = %s", [1]],
                    ["UPDATE users SET active = 1 WHERE id = %s", [2]],
                ]
                table._excs(queries)
        """
        self.db_obj._excs(query_params)

    def get_columns_name(self):
        """
        Retrieve the names of all columns in the table.

        This method executes a ``SHOW COLUMNS`` query and extracts the column names
        from the result set. It is a convenient way to get a list of column
        identifiers without fetching the full schema information.

        Returns:
            list of str: A list of column names as strings, in the order they
            appear in the table definition.

        Raises:
            Exception: If the underlying query fails (e.g., the table does not
                exist, connection issues, or permission problems). The original
                error and the query are included in the exception message.

        Example:
            Assuming a ``Table`` instance ``users`` exists::

                columns = users.get_columns_name()
                print(columns)  # e.g., ['id', 'name', 'email', 'created_at']
        """
        return [i[0] for i in self._excf(f'SHOW COLUMNS FROM {self.name_}')]
    
    def get_table_info(self):
        """
        Retrieve complete metadata information about all columns in the table.

        This method queries the MySQL ``INFORMATION_SCHEMA`` database to obtain
        detailed column information, including data type, nullability, default
        values, primary key status, foreign key relationships, and other
        attributes. The returned data is similar in structure to SQLite's
        ``PRAGMA table_info`` but with additional MySQL‑specific fields.

        The method is called during :class:`Table` initialization to dynamically
        create :class:`Column` attributes for each table column.

        Returns:
            list of dict: A list where each dictionary represents a column and
            contains the following keys:

            - ``cid`` (int): Column ordinal position (1‑based).
            - ``name`` (str): Column name.
            - ``type`` (str): MySQL data type name (e.g., ``'int'``, ``'varchar'``).
            - ``datatype`` (type): Python type mapping (``int``, ``float``, ``str``,
            or ``bytes``) inferred from the MySQL type.
            - ``notnull`` (bool): ``True`` if the column is ``NOT NULL``.
            - ``dflt_value`` (Any): Default value for the column, or ``None``.
            - ``pk`` (bool): ``True`` if the column is part of the primary key.
            - ``full_type`` (str): Complete column type definition (e.g.,
            ``'int(11)'``, ``'varchar(255)'``).
            - ``extra`` (str): Additional information (e.g., ``'auto_increment'``).
            - ``charset`` (str): Character set name, or ``None``.
            - ``collation`` (str): Collation name, or ``None``.
            - ``numeric_precision`` (int): Numeric precision for numeric types.
            - ``numeric_scale`` (int): Numeric scale for numeric types.
            - ``datetime_precision`` (int): Fractional seconds precision for
            temporal types.
            - ``auto_increment`` (bool): ``True`` if the column has
            ``AUTO_INCREMENT``.
            - ``fk_table`` (str): Referenced table name for foreign keys, or
            ``None``.
            - ``fk_column`` (str): Referenced column name for foreign keys, or
            ``None``.
            - ``fk_on_update`` (str): ``ON UPDATE`` action for foreign key, or
            ``None``.
            - ``fk_on_delete`` (str): ``ON DELETE`` action for foreign key, or
            ``None``.

        Raises:
            Exception: If the underlying database query fails (e.g., connection
                issue, table does not exist). The original error and query are
                included in the exception message.

        Example:
            Retrieving column information for a table::

                db = Driver(...)
                table = db.users
                info = table.get_table_info()
                for col in info:
                    print(f"{col['name']} ({col['type']}) PK: {col['pk']}")
                # Example output:
                # id (int) PK: True
                # name (varchar) PK: False
        """
        
        query = f"""
            SELECT 
                c.ORDINAL_POSITION AS cid,
                c.COLUMN_NAME AS name,
                c.DATA_TYPE AS type,
                CASE WHEN c.IS_NULLABLE = 'NO' THEN 1 ELSE 0 END AS notnull,
                c.COLUMN_DEFAULT AS dflt_value,
                CASE WHEN c.COLUMN_KEY = 'PRI' THEN 1 ELSE 0 END AS pk,
                c.COLUMN_TYPE AS full_type,
                c.EXTRA AS extra,
                c.CHARACTER_SET_NAME AS charset,
                c.COLLATION_NAME AS collation,
                c.NUMERIC_PRECISION AS num_precision,
                c.NUMERIC_SCALE AS num_scale,
                c.DATETIME_PRECISION AS datetime_precision,
                CASE WHEN c.EXTRA LIKE '%%auto_increment%%' THEN 1 ELSE 0 END AS auto_increment,
                kcu.REFERENCED_TABLE_NAME AS fk_table,
                kcu.REFERENCED_COLUMN_NAME AS fk_column,
                rc.UPDATE_RULE AS fk_on_update,
                rc.DELETE_RULE AS fk_on_delete
            FROM INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                ON kcu.TABLE_SCHEMA = c.TABLE_SCHEMA
                AND kcu.TABLE_NAME = c.TABLE_NAME
                AND kcu.COLUMN_NAME = c.COLUMN_NAME
                AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            LEFT JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
                AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                AND rc.TABLE_NAME = c.TABLE_NAME
            WHERE c.TABLE_SCHEMA = DATABASE()
            AND c.TABLE_NAME = %s
            ORDER BY c.ORDINAL_POSITION
        """
        return [{
            'cid': row[0],           # ORDINAL_POSITION
            'name': row[1],          # COLUMN_NAME
            'type': row[2],          # DATA_TYPE (MySQL type name)
            'datatype': int if row[2].lower().split('(')[0] in ('int', 'integer', 'tinyint', 'smallint', 'mediumint', 'bigint', 'serial', 'year', 'bit') else float if row[2].lower().split('(')[0] in ('real', 'float', 'double', 'decimal', 'numeric') else str if row[2].lower().split('(')[0] in ('char', 'varchar', 'text', 'tinytext', 'mediumtext', 'longtext', 'enum', 'set', 'json', 'date', 'time', 'datetime', 'timestamp') else bytes if row[2].lower().split('(')[0] in ('blob', 'tinyblob', 'mediumblob', 'longblob', 'binary', 'varbinary', 'geometry', 'point', 'linestring', 'polygon', 'multipoint', 'multilinestring', 'multipolygon', 'geometrycollection') else str,  # Python type (int, str, float, bytes)
            'notnull': bool(row[3]), # True/False
            'dflt_value': row[4],    # COLUMN_DEFAULT
            'pk': bool(row[5]),      # True/False
            'full_type': row[6],     # COLUMN_TYPE (مثلاً 'int(11)')
            'extra': row[7],         # EXTRA (auto_increment, etc.)
            'charset': row[8],       # CHARACTER_SET_NAME
            'collation': row[9],     # COLLATION_NAME
            'numeric_precision': row[10],  # NUMERIC_PRECISION
            'numeric_scale': row[11],      # NUMERIC_SCALE
            'datetime_precision': row[12], # DATETIME_PRECISION
            'auto_increment': bool(row[13]),  # True/False
            'fk_table': row[14],     # REFERENCED_TABLE_NAME
            'fk_column': row[15],    # REFERENCED_COLUMN_NAME
            'fk_on_update': row[16], # UPDATE_RULE
            'fk_on_delete': row[17]  # DELETE_RULE
        } for row in self._excfp(query, (self.name_[1:-1],))]

    def batch(self) -> 'BatchOperation':
        """
        Create a new batch operation builder for this table.

        Batch operations allow multiple ``UPDATE`` and ``INSERT`` statements to be
        queued together and executed in a single transaction. This is useful for
        performing multiple related changes efficiently or for constructing dynamic
        scripts where each statement depends on previous data. The returned
        :class:`BatchOperation` object provides chainable ``update()`` and
        ``insert()`` methods to build the batch, and a ``run()`` method to execute
        all queued statements.

        Returns:
            BatchOperation: A new batch operation instance bound to this table.

        Example (Simple)::
            # Simple batch with one update and one insert
            table = db.users

            (table.batch()
                .update({'age': 30}, table.age < 18)
                .insert({'name': 'John', 'age': 25})
                .run())

        Example (Complex using ColumnsOperation)::
            # Complex batch with arithmetic and string operations
            table = db.products
            batch = table.batch()

            # Increase price by 10% for products with low stock
            batch.update(
                {table.price: table.price * 1.10},
                table.stock < 5
            )

            # Set description to concatenate name and category, with uppercase
            batch.update(
                {table.description: table.name.add_end(' - ').add_end(table.category).upper()},
                table.description == ''
            )

            # Insert a new product with a computed value
            batch.insert({
                table.name: 'Premium Item',
                table.price: table.price + 20,
                table.stock: 100
            })

            # Execute all statements in one transaction
            batch.run()
        """
        return BatchOperation(self)

    def update(self, update: dict[Column, Any], where: 'ColumnsOperation') -> None:
        """
        Update rows in the table that match the given condition.

        This method constructs and executes an ``UPDATE`` SQL statement. The
        ``update`` dictionary specifies the columns to modify and the new values.
        The keys are :class:`Column` objects representing the target columns.
        The values can be:
        - Literal Python values (e.g., integers, strings), which are
            parameterized and safely escaped.
        - Other :class:`Column` objects, to set a column to the value of
            another column (e.g., ``{table.col1: table.col2}``).
        - :class:`ColumnsOperation` expressions, to perform arithmetic,
            string concatenation, function calls, etc., computed on the
            database side.

        The ``where`` parameter is a :class:`ColumnsOperation` expression that
        defines which rows to update (e.g., ``table.id == 5``). Rows that do
        not satisfy the condition remain unchanged.

        The update is executed in a single transaction (via the driver's
        connection pool) and immediately committed unless an error occurs,
        in which case the transaction is rolled back.

        Args:
            update (dict[Column, Any]): A mapping from :class:`Column` objects
                to new values. The values can be literals, :class:`Column`
                references, or :class:`ColumnsOperation` expressions.
            where (ColumnsOperation): A condition that selects the rows to
                update. Must be a :class:`ColumnsOperation` instance, typically
                built using comparison operators (``==``, ``>``, etc.) or
                logical operators (``&``, ``|``).

        Returns:
            None: This method updates rows in the database and does not
            return any value.

        Raises:
            Exception: If the underlying SQL execution fails (e.g., syntax
                error, constraint violation, connection issue). The original
                error, query, and parameters are included in the exception
                message.

        Example (Simple)::
            # Update age of a specific user
            table = db.users
            table.update(
                update={table.age: 30},
                where=table.id == 5
            )

        Example (Complex using ColumnsOperation)::
            # Increase price by 10% for products with low stock, and set
            # description to uppercase concatenation of name and category.
            table = db.products
            table.update(
                update={
                    table.price: table.price * 1.10,
                    table.description: table.name.add_end(' - ').add_end(table.category).upper()
                },
                where=table.stock < 5
            )
        """
        temp_list = []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        self._excp(f'UPDATE {self.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=%s' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1])
        
    def get_row(self, which_columns: list['Column' | 'ColumnsOperation'], where: 'ColumnsOperation' = None, order_by: 'Column' = None):
        """
        Retrieve rows from the table with flexible column selection and filtering.

        This method executes a ``SELECT`` query on the table. It supports specifying
        columns as either :class:`Column` objects or :class:`ColumnsOperation`
        expressions (which allow arithmetic, string functions, aliases, etc.).
        The results are returned as a list of tuples (or a list of single values
        if only one column is selected). The method automatically handles
        parameter binding for security.

        Args:
            which_columns (list[Column | ColumnsOperation]): A list of columns
                or column operations to select. Each element can be a
                :class:`Column` object (returned as a table attribute) or a
                :class:`ColumnsOperation` expression (e.g., from arithmetic
                or string operations).
            where (ColumnsOperation, optional): A :class:`ColumnsOperation`
                expression representing the ``WHERE`` clause. If not provided,
                all rows are returned.
            order_by (Column, optional): A :class:`Column` object to order the
                results by. If provided, the query includes an ``ORDER BY`` clause
                on that column.

        Returns:
            If ``len(which_columns) == 1``: a list of the single column values
            (e.g., ``[1, 2, 3]``).
            Otherwise: a list of tuples, each tuple containing the selected columns
            in the given order (e.g., ``[(1, 'Alice'), (2, 'Bob')]``).

        Raises:
            Exception: If the underlying database operation fails (e.g., syntax
                error, column does not exist). The original error and query are
                included in the exception message.

        Example (Simple):
            Retrieve specific columns with a condition::

                table = db.users
                # Get names and ages of users older than 18
                result = table.get_row(
                    which_columns=[table.name, table.age],
                    where=table.age > 18
                )
                # result: [('Alice', 25), ('Bob', 30), ...]

                # Get only names, ordered by age
                names = table.get_row(
                    which_columns=[table.name],
                    where=table.age > 18,
                    order_by=table.age
                )
                # names: ['Alice', 'Bob', ...]

        Example (Complex using ColumnsOperation):
            Use arithmetic and string operations in column selection::

                from ormophine.Mysql import ColumnsOperation

                table = db.products
                # Select product name, price with 10% tax, and full description
                # (concat name and category with a dash, then uppercase)
                expr = (table.name.add_end(' - ').add_end(table.category).upper())
                result = table.get_row(
                    which_columns=[
                        table.name,
                        table.price * 1.10,          # arithmetic
                        expr                         # string concatenation + upper
                    ],
                    where=(table.stock > 0) & (table.price < 100)
                )
                # result: [('Widget', 55.0, 'WIDGET - GADGETS'), ...]
        """
        tl = []
        wc = []
        [wc.append(i.first_name) if isinstance(i,Column) else [wc.append(i._output[0]), tl.extend(i._output[1])] for i in which_columns]
        return [row[0] for row in (self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} WHERE {where._output[0]} {f'ORDER BY {order_by.first_name}' if order_by else ''};', tl+where._output[1]) if where else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',tl) if tl else self._excf(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',))] if len(which_columns) == 1 else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} WHERE {where._output[0]} {f'ORDER BY {order_by.first_name}' if order_by else ''};', tl+where._output[1]) if where else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',tl) if tl else self._excf(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',)
        
    def insert(self, insert: dict['Column', Any]) -> None:
        """
        Insert a single row into the table.

        This method constructs an ``INSERT INTO`` SQL statement using the provided
        column-value mapping, executes it with parameterized placeholders, and
        commits the transaction. The keys of the dictionary must be :class:`Column`
        objects belonging to this table, and the values are the data to be inserted.

        Args:
            insert (dict[Column, Any]): A dictionary mapping :class:`Column` objects
                to their corresponding values for the new row. The values can be of
                any type supported by the database driver (e.g., strings, integers,
                floats, dates, None for NULL).

        Returns:
            None

        Raises:
            Exception: If the insert fails (e.g., constraint violation, type mismatch,
                connection error). The exception message includes the original error,
                the generated query, and the parameters for debugging.

        Example:
            Assuming a :class:`Driver` instance ``db`` with a table ``users`` that
            has columns ``id`` (auto-increment), ``name``, and ``age``::

                # Insert a new user
                db.users.insert({
                    db.users.name: 'Alice',
                    db.users.age: 30
                })

            The method automatically handles parameterized queries, so values are
            safely escaped.
        """
        self._excp(f'INSERT INTO {self.name_} ({', '.join(i.first_name for i in list(insert.keys()))}) VALUES ({', '.join(f'%s' for k in insert)})', [v for v in list(insert.values())])

    def custom_execute(self, query: str, params: list = None) -> None:
        """
        Execute a custom SQL query with optional parameters.

        This method provides a flexible way to run any SQL statement on the table's
        database connection. It automatically selects the appropriate execution path
        based on whether parameters are provided. If ``params`` is given, the query
        is executed with parameter substitution using the driver's ``_excp`` method;
        otherwise, the query is executed without parameters using ``_exc``.

        Args:
            query (str): The SQL query string to execute. May contain ``%s``
                placeholders if ``params`` are provided.
            params (list, optional): A list of parameter values to substitute into
                the query. Defaults to ``None``.

        Returns:
            None

        Raises:
            Exception: If the query execution fails. The original error and query
                are included in the exception message (propagated from the driver).

        Example:
            Executing a custom update with parameters::

                table = db.users
                table.custom_execute(
                    "UPDATE users SET active = %s WHERE id = %s",
                    [1, 42]
                )

            Executing a query without parameters::

                table.custom_execute("TRUNCATE TABLE logs")
        """
        self._excp(query, params) if params else self._exc(query)
            
    def custom_execute_many(self, query: str, params: list = None) -> None:
        """
        Execute a parameterized query multiple times with different parameter sets.

        This method is a convenience wrapper around :meth:`_excm` that allows
        executing the same SQL query repeatedly with a list of parameter sets.
        It is useful for performing batch inserts or updates where many rows
        need to be inserted or updated in a single round-trip to the database.
        The query should contain placeholders (``%s``) for parameters, and the
        `params` argument should be a list of tuples or lists, each representing
        one set of parameters.

        Args:
            query (str): The SQL query string with ``%s`` placeholders for
                parameters.
            params (list, optional): A list of parameter sequences (tuples or lists)
                to be substituted into the query. Each inner sequence corresponds
                to one execution. If ``None``, the method raises an error or
                behaves unpredictably; this parameter is required for this method.

        Returns:
            None

        Raises:
            Exception: If the query execution fails (e.g., syntax error,
                constraint violation, or connection issue). The original error
                and the query/parameters are included in the exception message.

        Example:
            Batch inserting multiple rows into a table::

                table = db.users
                query = "INSERT INTO users (name, age) VALUES (%s, %s)"
                data = [("Alice", 30), ("Bob", 25), ("Charlie", 35)]
                table.custom_execute_many(query, data)
        """
        self._excm(query, params)

    def custom_execute_with_fetch(self, query: str, params: list = None) -> Any:
        """
        Execute a custom SQL query and return the fetched results.

        This method allows executing arbitrary parameterized or non-parameterized
        SQL queries and retrieves all result rows. It is useful for complex
        queries that are not covered by the built-in ORM methods. If ``params``
        are provided, the query is executed with parameter substitution; otherwise,
        it is executed as a plain query. The result is the full set of rows
        returned by the query.

        Args:
            query (str): The SQL query string. May contain ``%s`` placeholders
                for parameters if ``params`` is provided.
            params (list, optional): A list or tuple of parameter values to
                substitute into the query. Defaults to ``None``, meaning the
                query has no parameters.

        Returns:
            Any: The fetched result, typically a list of tuples where each tuple
            represents a row. The exact structure depends on the query.

        Raises:
            Exception: If the query execution fails (e.g., syntax error,
                connection issue, or invalid parameters). The original error
                and query details are included in the exception message.

        Example:
            Executing a custom SELECT query with parameters::

                table = db.users
                results = table.custom_execute_with_fetch(
                    "SELECT id, name FROM users WHERE age > %s",
                    [25]
                )
                for row in results:
                    print(f"ID: {row[0]}, Name: {row[1]}")

            Executing a query without parameters::

                results = table.custom_execute_with_fetch(
                    "SELECT COUNT(*) FROM users"
                )
                count = results[0][0] if results else 0
        """
        return self._excfp(query, params) if params else self._excf(query)

    def delete_row(self, where: 'ColumnsOperation') -> None:
        """
        Delete rows from the table that match a given condition.

        This method executes a ``DELETE FROM`` SQL statement with a ``WHERE``
        clause constructed from the provided :class:`ColumnsOperation` object.
        The operation is performed immediately and the transaction is committed
        (or rolled back on failure) by the underlying connection.

        Args:
            where (ColumnsOperation): A condition object that defines which rows
                to delete. The condition is typically built using column objects
                and comparison operators (e.g., ``column == value``,
                ``column > other_column``, etc.). The object must have a valid
                ``_output`` attribute with the SQL condition string and the
                corresponding parameter list.

        Returns:
            None

        Raises:
            Exception: If the query execution fails (e.g., invalid condition,
                connection issue, or other database error). The original error,
                query, and parameters are included in the exception message.

        Example:
            Assuming a ``users`` table and a configured :class:`Driver` instance
            ``db``::

                # Delete a user with a specific ID
                db.users.delete_row(db.users.id == 5)

                # Delete users older than 30
                db.users.delete_row(db.users.age > 30)

                # Delete users whose name starts with 'A'
                db.users.delete_row(db.users.name.startswith('A'))
        """
        self._excp(f'DELETE FROM {self.name_} WHERE {where._output[0]};', where._output[1])

    def delete_table(self, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool) -> None:
        """
        Permanently delete the entire table from the database.

        This method executes a ``DROP TABLE`` statement, which irreversibly removes
        the table and all its data, indexes, and constraints. To prevent accidental
        deletion, three explicit confirmation flags are required. All three must be
        ``True`` for the operation to proceed. After successful deletion, the table
        attribute is also removed from the parent :class:`Driver` instance.

        Args:
            are_you_sure (bool): First-level confirmation flag.
            are_you_really_sure (bool): Second-level confirmation flag.
            for_sure (bool): Final confirmation flag.

        Returns:
            None

        Raises:
            Exception: If the underlying SQL execution fails (e.g., insufficient
                privileges or the table does not exist). The original error and
                query are included in the exception message.

        Example:
            Assuming a :class:`Table` instance named ``users`` attached to a
            :class:`Driver` instance ``db``::

                # Danger: this deletes the 'users' table
                users.delete_table(True, True, True)

            If any flag is ``False``, nothing happens::

                users.delete_table(True, True, False)  # No effect
        """
        if are_you_sure and are_you_really_sure and for_sure:
            self._exc(f'DROP TABLE {self.name_};')
            self.db_obj.__delattr__(self.name_[1:-1])

    def delete_column(
        self,
        column: 'Column',
        are_you_sure: bool,
        are_you_really_sure: bool,
        for_sure: bool
    ) -> None:
        """
        Permanently delete a column from the table.

        This method executes an ``ALTER TABLE ... DROP COLUMN`` statement to remove
        the specified column from the table schema. All data stored in that column
        is irreversibly lost. To prevent accidental deletion, three explicit
        confirmation flags are required; all three must be ``True`` for the
        operation to proceed. After successful deletion, the corresponding
        :class:`Column` attribute is also removed from the :class:`Table` instance.

        Args:
            column (Column): The :class:`Column` object representing the column
                to delete.
            are_you_sure (bool): First-level confirmation flag.
            are_you_really_sure (bool): Second-level confirmation flag.
            for_sure (bool): Final confirmation flag.

        Returns:
            None

        Raises:
            Exception: If the underlying SQL execution fails (e.g., the column does
                not exist, insufficient privileges, or the table is locked). The
                original error and query are included in the exception message.

        Example:
            Assuming a :class:`Table` instance named ``users`` that has a column
            ``temp_data``::

                # Danger: this deletes the 'temp_data' column
                users.delete_column(users.temp_data, True, True, True)

            If any flag is ``False``, nothing happens::

                users.delete_column(users.temp_data, True, True, False)  # No effect
        """
        if are_you_sure and are_you_really_sure and for_sure:
            self._exc(f'ALTER TABLE {self.name_} DROP COLUMN {column.first_name};')
            self.__delattr__(column.first_name[1:-1])

    def add_column(
        self,
        column_name: str,
        data_type: str,          # خروجی از DataTypes (مثلاً DataTypes.INT())
        nullable: bool = True,
        default: Any = None,
        auto_increment: bool = False,
        primary_key: bool = False,
        unique: bool = False,
        comment: str = None,
        after: Column = None,
        first: bool = False
    ) -> None:
        """
        Add a new column to the table.

        This method executes an ``ALTER TABLE ADD COLUMN`` statement to add a new
        column to the existing table. It supports various column options such as
        nullability, default value, auto‑increment, uniqueness, primary key, and
        positioning (via the ``after`` or ``first`` parameters). If ``primary_key``
        is ``True``, an additional ``ALTER TABLE ADD PRIMARY KEY`` statement is
        executed. After the column is added, the method dynamically attaches a
        :class:`Column` object to the current :class:`Table` instance, making the
        new column accessible as an attribute (e.g., ``table.new_column``).

        Args:
            column_name (str): The name of the new column. It will be quoted
                automatically.
            data_type (str): The SQL data type definition, typically returned by
                one of the static methods in :class:`DataTypes` (e.g.,
                ``DataTypes.INT()``, ``DataTypes.VARCHAR(255)``).
            nullable (bool, optional): If ``True``, the column allows ``NULL``
                values. If ``False``, the column is ``NOT NULL``. Defaults to
                ``True``.
            default (Any, optional): The default value for the column. If provided,
                it will be used in the ``DEFAULT`` clause. For strings, the value
                is automatically quoted. Defaults to ``None`` (no default).
            auto_increment (bool, optional): If ``True``, the column is set to
                ``AUTO_INCREMENT``. This is typically used for numeric primary keys.
                Defaults to ``False``.
            primary_key (bool, optional): If ``True``, the column is added as the
                primary key (or part of it) via a separate ``ALTER TABLE ADD
                PRIMARY KEY`` statement. Defaults to ``False``.
            unique (bool, optional): If ``True``, the column is defined as
                ``UNIQUE``. Defaults to ``False``.
            comment (str, optional): A comment for the column, added as
                ``COMMENT '...'``. Defaults to ``None``.
            after (Column, optional): An existing :class:`Column` object after
                which the new column should be placed. This is translated to the
                ``AFTER column_name`` clause. Defaults to ``None``.
            first (bool, optional): If ``True``, the new column is placed at the
                beginning of the table (``FIRST`` clause). Defaults to ``False``.

        Returns:
            None

        Raises:
            Exception: If the underlying SQL execution fails (e.g., invalid data
                type, duplicate column name, constraint violation, or permission
                error). The original error and query are included in the exception
                message.

        Example:
            Adding a new ``email`` column to an existing ``users`` table::

                from ormophine.Mysql import DataTypes

                # Assuming `users` is a Table instance
                users.add_column(
                    column_name='email',
                    data_type=DataTypes.VARCHAR(255),
                    nullable=False,
                    unique=True,
                    comment='User email address',
                    after=users.id
                )

            Adding an auto‑increment primary key column::

                users.add_column(
                    column_name='id',
                    data_type=DataTypes.INT(),
                    nullable=False,
                    auto_increment=True,
                    primary_key=True,
                    first=True
                )
        """
        self._exc(f'ALTER TABLE {self.name_} ADD COLUMN {column_name} {data_type} {' NOT NULL' if not nullable else ''}{' AUTO_INCREMENT' if auto_increment else ''}{f" DEFAULT '{default}'" if default is not None and isinstance(default,str) else f' DEFAULT {default}' if default is not None else ''}{' UNIQUE' if unique else ''}{f" COMMENT '{comment}'" if comment else ''}{' FIRST' if first else f" AFTER {after.first_name[1:-1]}" if after else ''};')
        self._exc(f"ALTER TABLE {self.name_} ADD PRIMARY KEY (`{column_name}`);") if primary_key else ''
        self.__setattr__(column_name, Column(self, column_name, int if data_type.lower().split('(')[0] in ('int', 'integer', 'tinyint', 'smallint', 'mediumint', 'bigint', 'serial', 'year', 'bit') else float if data_type.lower().split('(')[0] in ('real', 'float', 'double', 'decimal', 'numeric') else str if data_type.lower().split('(')[0] in ('char', 'varchar', 'text', 'tinytext', 'mediumtext', 'longtext', 'enum', 'set', 'json', 'date', 'time', 'datetime', 'timestamp') else bytes if data_type.lower().split('(')[0] in ('blob', 'tinyblob', 'mediumblob', 'longblob', 'binary', 'varbinary', 'geometry', 'point', 'linestring', 'polygon', 'multipoint', 'multilinestring', 'multipolygon', 'geometrycollection') else str))

    def rename_table(self, new_name: str) -> None:
        """
        Rename the database table and update the corresponding attribute on the driver.

        This method executes an ``ALTER TABLE ... RENAME TO`` statement to change the
        table's name in the database. After a successful rename, it removes the old
        table attribute from the parent :class:`Driver` instance and adds a new
        attribute with the new name, which is a fresh :class:`Table` instance
        representing the renamed table. The internal ``name_`` attribute is also
        updated.

        Args:
            new_name (str): The new name for the table. Must be a valid MySQL
                table name identifier.

        Returns:
            None

        Raises:
            Exception: If the underlying SQL execution fails (e.g., the new name
                already exists, insufficient privileges, or a syntax error). The
                original error and query are included in the exception message.

        Example:
            Assuming a :class:`Table` instance named ``old_users`` attached to a
            :class:`Driver` instance ``db``::

                # Rename the table from 'old_users' to 'users'
                old_users.rename_table('users')

                # After renaming, the table is accessible as db.users
                db.users.insert({'name': 'Alice'})
        """
        self._exc(f'ALTER TABLE {self.name_} RENAME TO `{new_name}`;')
        self.db_obj.__delattr__(self.name_[1:-1])
        self.db_obj.__setattr__(new_name, Table(obj=self.db_obj, table_name=new_name))
        self.name_ = f'`{new_name}`'


    def rename_column(self, column: 'Column', new_name: str) -> None:
        """
        Rename an existing column in the table.

        This method alters the table schema by changing the name of a column
        while preserving its data type, constraints, and other attributes.
        It retrieves the current full column type definition using
        :meth:`get_table_info`, constructs an ``ALTER TABLE ... CHANGE COLUMN``
        statement, and executes it. After a successful rename, the table's
        dynamic attribute for the column is updated to reflect the new name,
        and the old attribute is removed.

        Note:
            This operation may fail if the new name already exists or if the
            column is involved in foreign key constraints that do not allow
            renaming. The specific behavior depends on the database engine.

        Args:
            column (Column): The :class:`Column` object representing the column
                to be renamed. This object must belong to this table.
            new_name (str): The new name for the column. Must be a valid
                identifier (not a reserved keyword) and unique within the table.

        Returns:
            None

        Raises:
            Exception: If the underlying SQL execution fails (e.g., column does not
                exist, new name already in use, permission denied, or foreign key
                constraint). The original error message and query are included in
                the exception.

        Example:
            Renaming a column in a ``users`` table::

                from ormophine.Mysql import Table, Driver

                # Assume db is a Driver instance and users is a Table
                users = db.users
                old_col = users.username
                users.rename_column(old_col, 'user_name')

                # The column is now accessible as users.user_name
                users.insert({'user_name': 'alice', 'email': 'alice@example.com'})
        """
        for col_info in self.get_table_info():
            if col_info['name'] == column.first_name[1:-1]:
                full_type = col_info['full_type']  
                break
        query = f'ALTER TABLE {self.name_} CHANGE COLUMN {column.first_name} `{new_name}` {full_type};'
        self._exc(query)
        self.__delattr__(column.first_name[1:-1])
        self.__setattr__(new_name, Column(self, new_name, column.datatype))

    def create_index(
        self,
        index_name: str,
        columns: list['Column'],
        unique: bool = False,
        where: 'ColumnsOperation' = None
    ) -> None:
        """
        Create an index on one or more columns of the table.

        This method generates and executes a ``CREATE INDEX`` statement. If the
        ``unique`` parameter is ``True``, a unique index is created, enforcing
        uniqueness of the indexed column values. If a ``where`` condition is
        provided, the index is created as a filtered (partial) index, which only
        includes rows that satisfy the condition. The condition is constructed
        using a :class:`ColumnsOperation` object, and its parameter values are
        substituted directly into the SQL string (since MySQL does not support
        parameter placeholders in index definitions).

        Args:
            index_name (str): The name of the index to create.
            columns (list[Column]): A list of :class:`Column` objects specifying
                the columns to include in the index.
            unique (bool, optional): If ``True``, a unique index is created.
                Defaults to ``False``.
            where (ColumnsOperation, optional): A condition expression that defines
                which rows to include in the index. If provided, only rows matching
                this condition are indexed. Defaults to ``None``.

        Returns:
            None

        Raises:
            Exception: If the SQL execution fails (e.g., index name already exists,
                invalid column names, or permission denied). The original error
                and the generated query are included in the exception.

        Example:
            Creating a non‑unique index on a single column::

                users.create_index('idx_users_name', [users.name])

            Creating a unique index on multiple columns::

                users.create_index('idx_users_email_unique', [users.email], unique=True)

            Creating a filtered index on active users::

                from ormophine.Mysql import ColumnsOperation

                # Assuming users.active is a Column
                condition = users.active == 1
                users.create_index('idx_users_active', [users.last_login], where=condition)
        """
        if where:
            wr = f'WHERE {where._output[0]}'
            for i in where._output[1]:
                wr=wr.replace('%s',i if isinstance(i,str) else str(i),1)
        self._excp(f'CREATE {'UNIQUE ' if unique else ''}INDEX {index_name} ON {self.name_} ({','.join(i.first_name for i in columns)}) {wr if where else ''}',[])

    def delete_index(self, index_name: str) -> None:
        """
        Drop an index from the table.

        This method executes a ``DROP INDEX`` statement to permanently remove an
        existing index from the table. The index name must exactly match the name
        used when the index was created (case‑sensitive depending on the database
        and collation settings). Dropping an index can improve write performance
        but may negatively affect read queries that relied on the index.

        Args:
            index_name (str): The name of the index to drop.

        Returns:
            None

        Raises:
            Exception: If the index does not exist, if the user lacks sufficient
                privileges, or if a database error occurs. The original error
                and the executed query are included in the exception message.

        Example:
            Dropping an index named ``idx_users_email`` from the ``users`` table::

                users.delete_index('idx_users_email')
        """
        self._exc(f'DROP INDEX {index_name} ON {self.name_};')

    def get_indexes_info(self) -> Any:
        """
        Retrieve detailed information about all indexes on the table.

        This method executes a ``SHOW INDEX FROM`` query and returns a list of
        dictionaries, each containing comprehensive metadata about an index,
        including its name, uniqueness, column(s), collation, cardinality, and
        other properties. The result is similar to the output of MySQL's
        ``SHOW INDEX`` statement but formatted as a list of dicts for easier
        programmatic access.

        Returns:
            list of dict: A list where each element is a dictionary with the
            following keys:

            - ``idx_name`` (str): The name of the index.
            - ``non_unique`` (bool): ``True`` if the index allows duplicate values,
            ``False`` if it is a unique index.
            - ``seq_in_idx`` (int): The column sequence number within the index
            (starting from 1).
            - ``Columns_name`` (str): The name of the column that is part of the
            index.
            - ``collation`` (str): The collation order (e.g., ``'A'`` for
            ascending, ``'D'`` for descending, or ``None`` if not applicable).
            - ``cardinality`` (int): An estimate of the number of unique values in
            the index.
            - ``sub_part`` (int): The index prefix length (if the column is only
            partially indexed), or ``None``.
            - ``packed`` (str): Indicates whether the index is packed (usually
            ``None``).
            - ``nullable`` (str): ``'YES'`` if the column can contain ``NULL``
            values, otherwise ``'NO'``.
            - ``idx_type`` (str): The index type (e.g., ``'BTREE'``, ``'HASH'``).
            - ``comment`` (str): Any comment associated with the index.

        Raises:
            Exception: If the underlying query fails (e.g., the table does not
                exist or the user lacks privileges). The original error and the
                executed query are included in the exception message.

        Example:
            Retrieving index information for the ``users`` table::

                from ormophine.Mysql import Driver

                db = Driver(host='localhost', port=3306, username='root',
                            password='pass', db_name='myapp')
                users = db.users
                indexes = users.get_indexes_info()
                for idx in indexes:
                    print(f"Index: {idx['idx_name']}, Column: {idx['Columns_name']}, "
                        f"Unique: {idx['non_unique']}")
                # Output example:
                # Index: PRIMARY, Column: id, Unique: False
                # Index: idx_users_email, Column: email, Unique: True
        """
        return [{'idx_name':i[2], 'non_unique':bool(i[1]), 'seq_in_idx':i[3], 'Columns_name':i[4],'collation':i[5], 'cardinality':i[6], 'sub_part':i[7], 'packed':i[8], 'nullable':i[9], 'idx_type':i[10], 'comment':i[11]} for i in self._excf(f'SHOW INDEX FROM {self.name_}')]

    def bulk_insert(self, columns: list['Column'], data_list: list) -> None:
        """
        Insert multiple rows into the table in a single efficient operation.

        This method uses the ``executemany`` feature of the underlying DB driver
        to insert many rows at once. It takes a list of :class:`Column` objects
        specifying the target columns and a list of rows (each row being a list
        or tuple of values) to insert. The number and order of values in each
        row must match the specified columns.

        Bulk insertion is significantly faster than inserting rows individually
        when dealing with large datasets because it reduces the number of round‑trips
        to the database.

        Args:
            columns (list['Column']): A list of :class:`Column` objects representing
                the columns into which data will be inserted. The order of columns
                determines the order of values expected in each row of ``data_list``.
            data_list (list): A list of rows, where each row is a list or tuple of
                values corresponding to the specified columns. All rows must have
                the same length and the values must be compatible with the column
                data types.

        Returns:
            None

        Raises:
            Exception: If a database error occurs (e.g., data type mismatch, duplicate
                key violation, or connection issues). The original error and the
                executed query are included in the exception message.

        Example:
            Inserting multiple users into a ``users`` table::

                # Assume `users` is a Table instance with columns: id, name, age
                users.bulk_insert(
                    columns=[users.name, users.age],
                    data_list=[
                        ['Alice', 30],
                        ['Bob', 25],
                        ['Charlie', 35]
                    ]
                )
                # This will execute a single INSERT with multiple rows.
        """
        self._excm(f'INSERT INTO {self.name_} ({', '.join(i.first_name for i in columns)}) VALUES ({', '.join('%s' for i in columns)});',data_list)

    def bulk_update(self, update: dict['Column', Any], where: 'ColumnsOperation', data_list: list) -> None:
        """
        Perform a bulk update operation using a list of parameter sets.

        This method constructs a single parameterized ``UPDATE`` query where each
        occurrence of the ``PLACE_HOLDER`` string (by default
        ``'_MY_S4ULT3D_PL4C3_H0LD3R_%s_'``) in the SET clause and WHERE condition
        is replaced with a positional placeholder (``%s``). The actual values for
        each row are taken from the ``data_list``, and the query is executed once
        per row using ``executemany``. This is efficient for updating many rows
        with different data.

        The placeholder string is a class attribute and can be customized by
        assigning a new value to ``Table.PLACE_HOLDER`` or the instance attribute.

        Args:
            update (dict[Column, Any]): A dictionary mapping :class:`Column`
                objects to the new values. Values can be:

                - A :class:`Column` object (to set a column to the value of
                another column).
                - A :class:`ColumnsOperation` object (to set a column to a
                computed expression).
                - A literal value (e.g., ``int``, ``str``). If the value is a
                literal, it will be replaced with a placeholder unless it is
                the placeholder string itself (used for dynamic substitution
                from ``data_list``).
            where (ColumnsOperation): A :class:`ColumnsOperation` object
                representing the ``WHERE`` condition. The condition can contain
                placeholders to be substituted from ``data_list``.
            data_list (list): A list of sequences (lists or tuples), where each
                sequence contains the values to substitute for each placeholder
                in the order they appear in the query (first from SET clause,
                then from WHERE clause). The number of items in each sequence
                must match the total number of placeholders.

        Returns:
            None

        Raises:
            Exception: If the number of placeholders in the query does not match
                the number of items in each row of ``data_list``, an exception
                is raised with a detailed message. Also re-raises any database
                errors that occur during execution.

        Example:
            Updating multiple rows with different values::

                # Assume db is a Driver instance and users table has columns id, name, age.
                # We want to update age for users where name matches a list of names.

                # Define the update: set age = value from data_list (placeholder)
                # where name = value from data_list (placeholder)
                users.bulk_update(
                    update={users.age: users.PLACE_HOLDER},
                    where=users.name == users.PLACE_HOLDER,
                    data_list=[
                        [30, 'Alice'],
                        [25, 'Bob'],
                        [28, 'Charlie']
                    ]
                )
                # This executes:
                # UPDATE users SET age = %s WHERE name = %s;
                # with each pair from data_list.
        """
        temp_list = []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        query_splited = f'UPDATE {self.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value, Column) else f'{key.first_name}={self.PLACE_HOLDER}' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0].replace('%s', self.PLACE_HOLDER)}' for key , value in list(update.items()))} WHERE {where._output[0].replace('%s', self.PLACE_HOLDER)};'.split(self.PLACE_HOLDER)
        query= query_splited[0]
        for a,i in enumerate(temp_list+where._output[1]):
            query = query +( f'"{i}"' if isinstance(i,str) and not i == self.PLACE_HOLDER else str(i))+ query_splited[a+1] #All "? || '%'" thing are because of Column.contain() method and .startswith() and .endswith() that have "%" in output value
        try:
            self._excm(query.replace(self.PLACE_HOLDER, '%s'), data_list)
        except Exception as e:
            if "Incorrect number of bindings" in str(e):
                raise Exception(f'number of `PLACE_HOLDERS` must be equals to number of items in each of `data_list` items.\n if it is so, make sure that there is no "{self.PLACE_HOLDER}" literal string in your query because it is reserved for this orm. you can change it on you own need with `mytable.PLACE_HOLDER = "you own idea"`')
            else:
                raise

    def join(
        self,
        columns: list['Column'],
        joins_list: list['Join.Inner | Join.Left | Join.Right'],
        where: 'ColumnsOperation' = None,
        order_by: 'Column' = None
    ) -> Any:
        """
        Perform a SELECT query with JOINs across multiple tables.

        This method constructs and executes a SQL query that joins this table
        with other tables specified in ``joins_list``. The selected columns are
        returned with automatically generated aliases in the format
        ``{table_name}_{column_name}`` to avoid name collisions when columns from
        different tables have the same name. The result is fetched using the
        underlying driver's fetch method and returned as a list of tuples.

        Args:
            columns (list[Column]): A list of :class:`Column` objects or
                :class:`ColumnsOperation` expressions to select. Each will be
                included in the SELECT clause. For ``ColumnsOperation`` objects,
                the SQL expression is used as-is.
            joins_list (list[Union[Join.Inner, Join.Left, Join.Right]]): A list
                of join objects (inner, left, or right) that define which tables
                to join and the join conditions. Each join object is constructed
                with a target table and a condition (a :class:`ColumnsOperation`
                expression).
            where (ColumnsOperation, optional): A :class:`ColumnsOperation`
                expression for the WHERE clause. If provided, only rows satisfying
                this condition are returned. Defaults to ``None``.
            order_by (Column, optional): A :class:`Column` object to order the
                results by. If provided, an ``ORDER BY`` clause is added.
                Defaults to ``None``.

        Returns:
            list of tuple: A list of rows, where each row is a tuple of values
            corresponding to the selected columns (in the order given). The
            column values are accessible by position.

        Raises:
            Exception: If the underlying SQL execution fails (e.g., syntax error,
                invalid table or column references). The original error and the
                full query are included in the exception message.

        Example:
            Performing a join between the ``users`` table and an ``orders`` table::

                from ormophine.Mysql import Join

                # Assume we have table objects: users, orders
                # and column objects: users.id, users.name, orders.amount, orders.user_id

                # Build join objects
                inner_join = Join.Inner(
                    orders,
                    users.id == orders.user_id
                )

                # Select columns from both tables
                results = users.join(
                    columns=[users.id, users.name, orders.amount],
                    joins_list=[inner_join],
                    where=users.id > 100,
                    order_by=users.name
                )

                for row in results:
                    # row[0] -> user.id, row[1] -> user.name, row[2] -> order.amount
                    print(f"User {row[1]} (ID: {row[0]}) has order amount {row[2]}")
        """
        tl = []
        [tl.extend(i._output[1]) if isinstance(i,ColumnsOperation) else None for i in columns]
        [tl.extend(i._output[1]) for i in joins_list]
        return self._excfp(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}'if isinstance(i,Column)else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")")else i._output[0]} AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'WHERE {where._output[0]}'if where else ''} {f'ORDER BY {order_by.name}' if order_by else ''}', tl+where._output[1]) if where else self._excfp(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column) else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")") else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'ORDER BY {order_by.name}' if order_by else ''}', tl) if tl else self._excf(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column) else f'{i._output[0][1:-1] if i._output[0].startswith('(') and i._output[0].endswith(')') else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'ORDER BY {order_by.name}' if order_by else ''}')
        # The above line is approximately 1000 characters, which is not standard, but it is written this way
        # to improve performance in the Driver class and to avoid checking whether the second item in the query
        # is an empty list for each input.

