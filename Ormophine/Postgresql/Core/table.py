from __future__ import annotations
from .. import Column, ColumnsOperation, BatchOperation, Join, Any

class Table:
    PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
    def __init__(self, obj: Driver, table_name: str):
        """Initialize a Table instance representing an existing database table.

        This constructor retrieves the table's schema from the database using
        `get_table_info()` and dynamically creates `Column` attributes for each
        column, allowing direct access via attribute names (e.g., `table.id`).

        Args:
            obj (Driver): The Driver instance managing the database connection pool.
            table_name (str): The name of the existing table in the database.

        Raises:
            Exception: If the table does not exist or the schema cannot be retrieved.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(host='localhost', port=5432, username='user',
            ...                 password='pass', db_name='mydb')
            >>> users = Table(driver, 'users')
            >>> # Access columns as attributes
            >>> users.id, users.name, users.age
            (<Column 'users'."id">, <Column 'users'."name">, <Column 'users'."age">)
        """
        self.name_ = f'"{table_name}"'
        self.db_obj = obj
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
        for i in self.get_table_info():
            self.__setattr__(i['name'], Column(self, i['name'], i['datatype']))

    def get_table_info(self):
        """Retrieve detailed schema information for all columns of the current table.

        This method queries PostgreSQL's information_schema and related system
        catalogs to obtain comprehensive metadata for each column, including data
        type, nullability, default value, primary key status, auto-increment,
        foreign key references, and more. The returned data is used internally to
        construct `Column` objects and is also useful for introspection.

        Returns:
            list[dict]: A list of dictionaries, each containing the following keys:

                - cid (int): Column ordinal position (1-based).
                - name (str): Column name.
                - type (str): SQL data type name as reported by PostgreSQL.
                - datatype (type): Python type mapping (int, float, str, bytes, or bool)
                inferred from the SQL type.
                - notnull (bool): True if the column is NOT NULL.
                - dflt_value (str or None): Column default value expression, if any.
                - pk (bool): True if the column is part of the primary key.
                - full_type (str): The full user-defined data type name (or the
                base type if not available).
                - auto_increment (bool): True if the column is an identity column
                (GENERATED AS IDENTITY).
                - num_precision (int or None): Numeric precision for numeric/decimal
                columns.
                - num_scale (int or None): Numeric scale for numeric/decimal columns.
                - datetime_precision (int or None): Precision for date/time columns.
                - fk_name (str or None): Name of the foreign key constraint, if any.
                - fk_table (str or None): Referenced table name for a foreign key.
                - fk_column (str or None): Referenced column name for a foreign key.
                - fk_on_update (str or None): ON UPDATE action for foreign key.
                - fk_on_delete (str or None): ON DELETE action for foreign key.

        Raises:
            ProgrammingError: If the query has a syntax error or the table does not exist.
            OperationalError: If a connection issue occurs during execution.
            Exception: Wrapped exceptions from the underlying driver's `_excfp` method.

        Example:
            >>> from ormophine.Postgresql import Driver
            >>> db = Driver(host='localhost', port=5432, username='user',
            ...             password='pass', db_name='test')
            >>> employees = db.employees  # Table object
            >>> info = employees.get_table_info()
            >>> for col in info:
            ...     print(f"{col['name']}: {col['datatype']} (PK: {col['pk']})")
            id: <class 'int'> (PK: True)
            name: <class 'str'> (PK: False)
            salary: <class 'float'> (PK: False)
        """
        query = """
            SELECT
                c.ordinal_position AS cid,
                c.column_name AS name,
                c.data_type AS type,
                CASE WHEN c.is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull,
                c.column_default AS dflt_value,
                CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN 1 ELSE 0 END AS pk,
                c.udt_name AS full_type,
                CASE WHEN c.is_identity = 'YES' THEN 1 ELSE 0 END AS auto_increment,
                c.numeric_precision AS num_precision,
                c.numeric_scale AS num_scale,
                c.datetime_precision AS datetime_precision,
                rc.unique_constraint_name AS fk_name,
                ccu.table_name AS fk_table,
                ccu.column_name AS fk_column,
                rc.update_rule AS fk_on_update,
                rc.delete_rule AS fk_on_delete
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu
                ON c.table_schema = kcu.table_schema
                AND c.table_name = kcu.table_name
                AND c.column_name = kcu.column_name
                AND kcu.position_in_unique_constraint IS NOT NULL
            LEFT JOIN information_schema.referential_constraints rc
                ON kcu.constraint_schema = rc.constraint_schema
                AND kcu.constraint_name = rc.constraint_name
            LEFT JOIN information_schema.constraint_column_usage ccu
                ON rc.constraint_schema = ccu.constraint_schema
                AND rc.constraint_name = ccu.constraint_name
            LEFT JOIN information_schema.table_constraints tc
                ON c.table_schema = tc.table_schema
                AND c.table_name = tc.table_name
                AND tc.constraint_type = 'PRIMARY KEY'
                AND EXISTS (
                    SELECT 1 FROM information_schema.constraint_column_usage ccu2
                    WHERE tc.constraint_name = ccu2.constraint_name
                    AND ccu2.column_name = c.column_name
                )
            WHERE c.table_schema = current_schema()
                AND c.table_name = %s
            ORDER BY c.ordinal_position;
        """
        return [{'cid': row[0],'name': row[1],'type': row[2],'datatype': (int if row[2].lower() in ('smallint', 'integer', 'bigint', 'serial', 'smallserial', 'bigserial') else float) if row[2].lower() in ('smallint', 'integer', 'bigint', 'serial', 'smallserial', 'bigserial', 'bit', 'numeric', 'decimal', 'real', 'double precision', 'money') else str if row[2].lower() in ('character varying', 'character', 'text', 'json', 'jsonb', 'uuid', 'date', 'time without time zone', 'time with time zone', 'timestamp without time zone', 'timestamp with time zone', 'interval') else bytes if row[2].lower() == 'bytea' else bool if row[2].lower() == 'boolean' else str,'notnull': bool(row[3]),'dflt_value': row[4],'pk': bool(row[5]),'full_type': row[6] if row[6] else row[2],'auto_increment': bool(row[7]),'num_precision': row[8],'num_scale': row[9],'datetime_precision': row[10],'fk_name': row[11],'fk_table': row[12],'fk_column': row[13],'fk_on_update': row[14],'fk_on_delete': row[15]} for row in self._excfp(query, (self.name_.strip('"'),))]
        
    def _exc(self, query):
        """Execute a SQL query with no parameters.

        This is an internal wrapper that delegates the execution to the underlying
        :class:`Driver` instance. It is used for statements that do not require
        parameter substitution (e.g., DDL statements, queries with no placeholders).

        Args:
            query (str): The SQL query string to execute.

        Returns:
            None

        Raises:
            Exception: Propagates any exceptions raised by the underlying driver,
                such as :exc:`psycopg.OperationalError` or :exc:`psycopg.ProgrammingError`.

        Example:
            >>> table._exc('DROP INDEX IF EXISTS idx_name;')
        """
        self.db_obj._exc(query)

    def _excp(self, query, params):
        """Execute a parameterized SQL query without fetching results.

        This is a low-level wrapper method that delegates execution to the
        underlying :class:`Driver` instance's ``_excp`` method. It is used
        internally for queries that modify data (INSERT, UPDATE, DELETE, etc.)
        and do not return result sets. The method handles parameter binding
        and transaction management through the driver's connection pool.

        Args:
            query (str): The SQL query string with ``%s`` placeholders for
                parameters.
            params (list or tuple): The parameter values to bind to the query
                placeholders. The number of items must match the number of
                placeholders.

        Returns:
            None: This method does not return any value.

        Raises:
            Exception: Propagates any database-related exceptions (e.g.,
                :class:`psycopg.OperationalError`, :class:`psycopg.ProgrammingError`)
                raised by the underlying driver. The exception message will
                include the query and parameters for debugging.

        Example:
            >>> # Assuming `table` is an instance of Table
            >>> table._excp("UPDATE users SET age = %s WHERE id = %s", [30, 1])
            # The query is executed with the provided parameters.

        Note:
            This method is intended for internal use. For most operations,
            prefer using higher-level methods like :meth:`Table.update`,
            :meth:`Table.insert`, or :meth:`Table.delete_row`.
        """
        self.db_obj._excp(query, params)

    def _excf(self, query):
        """Execute a query and fetch all resulting rows.

        This is a convenience wrapper that delegates to the underlying
        :class:`Driver` object's `_excf` method. It is used internally for
        SELECT queries where all results are needed.

        Args:
            query (str): The SQL query string to execute.

        Returns:
            list[tuple]: A list of tuples representing the fetched rows.

        Raises:
            Exception: Propagates any database errors (OperationalError,
                ProgrammingError, etc.) raised by the driver, with additional
                context about the query.

        Example:
            >>> table = Table(driver, "employees")
            >>> rows = table._excf("SELECT * FROM \"employees\" WHERE id > 10")
            >>> for row in rows:
            ...     print(row)
        """
        return self.db_obj._excf(query)

    def _excfp(self, query, params):
        """Execute a parameterized query and fetch all resulting rows.

        This is a convenience wrapper that delegates to the underlying
        :class:`Driver` object's `_excfp` method. It is used internally for
        SELECT queries that require parameter substitution and return a full
        result set.

        Args:
            query (str): The SQL query string containing placeholder markers
                (e.g., ``%s``) for parameters.
            params (list or tuple): The parameter values to substitute into the
                query placeholders.

        Returns:
            list[tuple]: A list of tuples, each representing a row from the
            query result.

        Raises:
            Exception: Propagates any database errors (OperationalError,
                ProgrammingError, etc.) raised by the driver, with additional
                context about the query and parameters.

        Example:
            >>> table = Table(driver, "employees")
            >>> rows = table._excfp(
            ...     "SELECT name, salary FROM \"employees\" WHERE dept_id = %s",
            ...     [10]
            ... )
            >>> for name, salary in rows:
            ...     print(f"{name}: {salary}")
        """
        return self.db_obj._excfp(query, params)

    def _excm(self, query, params):
        """Execute a query with multiple parameter sets using executemany.

        This is a convenience wrapper that delegates to the underlying
        :class:`Driver` object's `_excm` method. It is used for bulk operations
        such as inserting or updating multiple rows with a single query, where
        each set of parameters corresponds to one row.

        Args:
            query (str): The SQL query string with placeholders (e.g., %s).
            params (list[tuple]): A list of parameter tuples, one for each
                execution. Each tuple contains the values to substitute into
                the query placeholders.

        Returns:
            None: This method does not return any value.

        Raises:
            Exception: Propagates any database errors (OperationalError,
                ProgrammingError, etc.) raised by the driver, with additional
                context about the query and parameters.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> table = Table(driver, "employees")
            >>> # Bulk insert two rows
            >>> query = "INSERT INTO \"employees\" (name, age) VALUES (%s, %s)"
            >>> params = [("Alice", 30), ("Bob", 25)]
            >>> table._excm(query, params)
        """
        self.db_obj._excm(query, params)

    def _excs(self, query_params: list):
        """Execute multiple SQL statements as a batch in a single transaction.

        This internal method delegates to the underlying :class:`Driver` object's
        `_excs` method. It is used to run a list of SQL queries (optionally with
        parameters) together, ensuring atomicity: either all succeed or the entire
        batch is rolled back. This is primarily utilized by :class:`BatchOperation`
        when executing a script.

        Args:
            query_params (list): A list of queries to execute. Each item can be:
                - A string representing a query without parameters.
                - A list or tuple of two elements: ``[query, params]``, where
                ``params`` is a sequence of parameter values.

        Returns:
            None

        Raises:
            Exception: Propagates any database errors (e.g., OperationalError,
                ProgrammingError) raised by the driver. The exception message
                includes details about the failing query and its parameters.

        Example:
            >>> table = Table(driver, "employees")
            >>> queries = [
            ...     ["UPDATE employees SET salary = salary * 1.1 WHERE id = %s", [1]],
            ...     "UPDATE employees SET salary = salary * 1.05 WHERE id = 2"
            ... ]
            >>> table._excs(queries)  # Both updates run in a single transaction
        """
        self.db_obj._excs(query_params)

    def get_columns_name(self):
        """Retrieve the names of all columns in the table.

        This method fetches the current table schema information and returns
        a list containing the name of each column.

        Returns:
            list[str]: A list of column names as strings.

        Example:
            >>> table = Table(driver, "employees")
            >>> columns = table.get_columns_name()
            >>> print(columns)
            ['id', 'name', 'department_id', 'salary']
        """
        return [i['name'] for i in self.get_table_info()]
      
    def batch(self) -> 'BatchOperation':
        """Create a new batch operation builder for this table.

        Batch operations allow multiple SQL statements (INSERT and UPDATE) to be
        grouped together and executed in a single transaction, improving performance
        when performing multiple modifications. This method returns a
        :class:`BatchOperation` instance that can be used to chain multiple
        operations before executing them with :meth:`BatchOperation.run`.

        Returns:
            BatchOperation: A new batch operation builder associated with this table.

        Example:
            Simple batch with an INSERT and an UPDATE:

            >>> employees = driver.employees
            >>> batch_op = employees.batch()
            >>> batch_op.insert({employees.name: "Alice", employees.salary: 60000})
            >>> batch_op.update(
            ...     {employees.salary: 55000},
            ...     employees.department == "Marketing"
            ... )
            >>> batch_op.run()

        Example:
            Complex batch using ColumnsOperation for computed values and conditions:

            >>> from ormophine.Postgresql import ColumnsOperation
            >>> # Increase salary by 10% for managers with more than 5 years experience,
            >>> # and give a bonus to senior engineers.
            >>> batch_op = employees.batch()
            >>> batch_op.update(
            ...     {
            ...         employees.salary: employees.salary * 1.10,
            ...         employees.title: employees.title + " (Senior)"
            ...     },
            ...     (employees.title == "Manager") & (employees.years > 5)
            ... )
            >>> batch_op.update(
            ...     {employees.bonus: employees.salary * 0.05},
            ...     employees.title.contains("Engineer") & (employees.level >= 3)
            ... )
            >>> batch_op.insert({employees.name: "Bob", employees.salary: 70000})
            >>> batch_op.run()
            # This executes all statements in a single transaction.
        """
        return BatchOperation(self)

    def update(self, update: dict[Column, Any], where: 'ColumnsOperation') -> None:
        """Update rows in the table that match a condition.

        This method constructs and executes an UPDATE SQL statement, setting
        specified columns to new values for all rows that satisfy the given
        condition. It safely handles parameterized values to prevent SQL injection.

        Args:
            update (dict[Column, Any]): A dictionary mapping :class:`Column` objects
                to their new values. Values can be literals, other :class:`Column`
                objects (for column-to-column assignment), or
                :class:`ColumnsOperation` objects (for computed expressions).
            where (ColumnsOperation): A :class:`ColumnsOperation` object representing
                the condition that determines which rows to update.

        Returns:
            None: This method executes the update and does not return a value.

        Raises:
            Exception: Propagates any database errors raised during execution,
                including parameter binding or SQL syntax issues.

        Example:
            Simple update with literal values:

            >>> from ormophine.Postgresql import Driver, Table, Column, DataTypes
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> employees = driver.employees
            >>> # Assuming columns exist: id, name, salary, department
            >>> employees.update(
            ...     {employees.salary: 50000},
            ...     employees.department == "Engineering"
            ... )
            >>> # All engineers now have salary 50000.

        Example:
            Complex update using ColumnsOperation for computed values and
            a compound condition:

            >>> from ormophine.Postgresql import ColumnsOperation
            >>> # Increase salary by 10% for managers with experience > 5 years
            >>> employees.update(
            ...     {
            ...         employees.salary: employees.salary * 1.1,  # ColumnOperation
            ...         employees.title: employees.title + " (Senior)"  # string concatenation
            ...     },
            ...     (employees.title == "Manager") & (employees.years > 5)
            ... )
            >>> # This produces: UPDATE "employees" SET "salary" = ("salary" * 1.1),
            >>> # "title" = ("title" || ' (Senior)') WHERE ("title" = 'Manager' AND "years" > 5);
        """
        temp_list = []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        self._excp(f'UPDATE {self.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=%s' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1])
        
    def get_row(self, which_columns: list['Column' | 'ColumnsOperation'], where: 'ColumnsOperation' = None, order_by: 'Column' = None):
        """Fetch rows from the table with selected columns, optional filtering and ordering.

        This method builds and executes a SELECT query. The columns can be plain
        :class:`Column` objects or computed :class:`ColumnsOperation` expressions.
        If only one column is requested, the method returns a flat list of values
        from that column; otherwise, it returns a list of tuples representing the
        full rows.

        Args:
            which_columns (list[Column | ColumnsOperation]): A list of columns or
                expressions to select. Each element can be a :class:`Column` object
                or a :class:`ColumnsOperation` (e.g., arithmetic, string functions).
            where (ColumnsOperation, optional): A condition object for filtering
                rows. Defaults to None (no filter).
            order_by (Column, optional): A :class:`Column` object to order the
                results by. Defaults to None (no ordering).

        Returns:
            list: If only one column is specified in `which_columns`, returns a list
                of the values from that column (one per row). If multiple columns
                are specified, returns a list of tuples, each tuple representing a
                row with values in the order of the selected columns.

        Raises:
            Exception: Propagates any database errors (OperationalError,
                ProgrammingError, etc.) with additional context about the query.

        Example:
            Simple selection with a condition and ordering:

            >>> from ormophine.Postgresql import Driver, Table, Column
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> employees = driver.employees
            >>> # Assume columns: id, name, salary, department
            >>> # Get names of all engineers, ordered by salary
            >>> names = employees.get_row(
            ...     [employees.name],
            ...     where=employees.department == "Engineering",
            ...     order_by=employees.salary
            ... )
            >>> # names is a list like ['Alice', 'Bob', ...]

        Example:
            Complex query with computed columns using :class:`ColumnsOperation`:

            >>> from ormophine.Postgresql import ColumnsOperation
            >>> # Get employee id and full name (concatenated) for those with
            >>> # salary greater than average (using arithmetic and string ops)
            >>> employees.get_row(
            ...     [
            ...         employees.id,
            ...         employees.first_name + " " + employees.last_name  # string concat
            ...     ],
            ...     where=employees.salary > (employees.salary * 0.5 + 30000)  # complex condition
            ... )
            >>> # Returns list of tuples like [(1, 'John Doe'), (2, 'Jane Smith')]
        """
        tl = []
        wc = []
        [wc.append(i.first_name) if isinstance(i,Column) else [wc.append(i._output[0]), tl.extend(i._output[1])] for i in which_columns]
        return [row[0] for row in (self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} WHERE {where._output[0]} {f'ORDER BY {order_by.first_name}' if order_by else ''};', tl+where._output[1]) if where else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',tl) if tl else self._excf(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',))] if len(which_columns) == 1 else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} WHERE {where._output[0]} {f'ORDER BY {order_by.first_name}' if order_by else ''};', tl+where._output[1]) if where else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',tl) if tl else self._excf(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',)
        
    def insert(self, insert: dict['Column', Any]) -> None:
        """Insert a single row into the table.

        This method constructs and executes an INSERT statement, adding a new row
        with the specified column values. It safely parameterizes values to prevent
        SQL injection.

        Args:
            insert (dict[Column, Any]): A dictionary mapping :class:`Column` objects
                to the values to insert. Keys must be :class:`Column` instances
                belonging to this table, and values can be any Python type that
                is compatible with the column's SQL data type.

        Returns:
            None: This method executes the insert and does not return a value.

        Raises:
            Exception: Propagates any database errors (OperationalError,
                ProgrammingError, etc.) raised during execution, with additional
                context about the query and parameters.

        Example:
            Simple insert with literal values:

            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> employees = Table(driver, "employees")
            >>> employees.insert({
            ...     employees.name: "Alice",
            ...     employees.salary: 60000,
            ...     employees.department: "Engineering"
            ... })
            # Inserts a new row with the given values.
        """
        self._excp(f'INSERT INTO {self.name_} ({', '.join(i.first_name for i in list(insert.keys()))}) VALUES ({', '.join(f'%s' for k in insert)})', [v for v in list(insert.values())])

    def custom_execute(self, query: str, params: list = None) -> None:
        """Execute a custom SQL query with optional parameters.

        This method provides a flexible way to execute arbitrary SQL statements
        (e.g., DDL, DML) that are not covered by the ORM's built-in methods.
        It automatically handles parameter binding and connection management
        through the underlying driver.

        Args:
            query (str): The SQL query string to execute.
            params (list, optional): A list of parameter values to bind to the query.
                If provided, the query will be executed using parameterized execution
                to prevent SQL injection. Defaults to None.

        Returns:
            None: This method executes the query and does not return any data.
                For queries that return results, use :meth:`custom_execute_with_fetch`.

        Raises:
            Exception: Propagates any database errors (OperationalError,
                ProgrammingError, etc.) raised during execution, with additional
                context about the query and parameters.

        Example:
            Simple DDL execution:

            >>> employees = Table(driver, "employees")
            >>> employees.custom_execute(
            ...     "ALTER TABLE employees ADD COLUMN bonus DECIMAL(10,2)"
            ... )

        Example:
            Parameterized query for bulk operations:

            >>> employees.custom_execute(
            ...     "UPDATE employees SET salary = salary * 1.05 WHERE department = %s",
            ...     ["Engineering"]
            ... )
            # All engineers get a 5% salary increase.
        """
        self._excp(query, params) if params else self._exc(query)

    def custom_execute_many(self, query: str, params: list = None) -> None:
        """Execute a parameterized SQL statement multiple times with different parameter sets.

        This method is a convenience wrapper around :meth:`_excm` that allows bulk
        execution of the same SQL statement (e.g., INSERT, UPDATE, DELETE) with
        multiple parameter lists. It is useful for batch operations where many rows
        need to be inserted or updated efficiently.

        Args:
            query (str): The SQL query string with placeholders (``%s``) for parameters.
            params (list, optional): A list of parameter tuples or lists, each
                corresponding to one execution of the query. Defaults to None.

        Returns:
            None: This method executes the queries and does not return a value.

        Raises:
            Exception: Propagates any database errors (OperationalError,
                ProgrammingError, etc.) raised by the underlying driver, with
                additional context about the query and parameters.

        Example:
            Simple bulk insert of multiple employee records:

            >>> employees = Table(driver, "employees")
            >>> query = "INSERT INTO \"employees\" (name, salary) VALUES (%s, %s)"
            >>> params = [("Alice", 60000), ("Bob", 55000), ("Charlie", 70000)]
            >>> employees.custom_execute_many(query, params)
            # All three rows are inserted in a single executemany call.

        Example:
            Bulk update with varying conditions:

            >>> query = "UPDATE \"employees\" SET salary = salary * 1.1 WHERE id = %s"
            >>> params = [(1,), (2,), (3,)]
            >>> employees.custom_execute_many(query, params)
            # This updates salaries for employees with IDs 1, 2, and 3.
        """
        self._excm(query, params)

    def custom_execute_with_fetch(self, query: str, params: list = None) -> Any:
        """Execute a custom SQL query and return the fetched results.

        This method provides a flexible way to run arbitrary SELECT queries against
        the table's database connection. It supports both parameterized and
        non‑parameterized queries and returns the full result set.

        Args:
            query (str): The SQL query string to execute. For parameterized queries,
                use `%s` placeholders.
            params (list, optional): A list of parameter values to bind to the query.
                Defaults to None, which executes the query without parameters.

        Returns:
            Any: The query result. Typically this is a list of tuples representing
                the fetched rows, but the exact return type depends on the underlying
                driver's fetchall() implementation.

        Raises:
            Exception: Propagates any database errors (OperationalError,
                ProgrammingError, etc.) with additional context about the query.

        Example:
            Simple query without parameters:

            >>> employees = Table(driver, "employees")
            >>> rows = employees.custom_execute_with_fetch(
            ...     "SELECT * FROM \"employees\" WHERE salary > 50000"
            ... )
            >>> for row in rows:
            ...     print(row)

        Example:
            Parameterized query with placeholders:

            >>> employees = Table(driver, "employees")
            >>> rows = employees.custom_execute_with_fetch(
            ...     "SELECT name, salary FROM \"employees\" WHERE department = %s",
            ...     ["Engineering"]
            ... )
            >>> for name, salary in rows:
            ...     print(f"{name}: {salary}")
        """
        return self._excfp(query, params) if params else self._excf(query)

    def delete_row(self, where: 'ColumnsOperation') -> None:
        """Delete rows from the table that match a condition.

        This method constructs and executes a DELETE SQL statement, removing all
        rows from the table that satisfy the given condition. The condition is
        represented by a :class:`ColumnsOperation` object, which can include
        comparisons, logical operators, and function calls.

        Args:
            where (ColumnsOperation): A :class:`ColumnsOperation` object representing
                the condition that determines which rows to delete.

        Returns:
            None: This method executes the deletion and does not return a value.

        Raises:
            Exception: Propagates any database errors raised during execution,
                including parameter binding or SQL syntax issues.

        Example:
            Simple deletion by a single condition:

            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> employees = Table(driver, "employees")
            >>> # Delete all employees in the "Intern" department
            >>> employees.delete_row(employees.department == "Intern")

        Example:
            Deletion using a compound condition with ColumnsOperation:

            >>> # Delete employees with salary less than 30000 and years > 10
            >>> employees.delete_row(
            ...     (employees.salary < 30000) & (employees.years > 10)
            ... )
            >>> # This produces: DELETE FROM "employees" WHERE ("salary" < 30000 AND "years" > 10);
        """
        self._excp(f'DELETE FROM {self.name_} WHERE {where._output[0]};', where._output[1])

    def delete_table(self, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool) -> None:
        """Permanently drop the current table from the database.

        This method executes a DROP TABLE statement to remove the table and all its
        data from the database. It also deletes the corresponding :class:`Table`
        attribute from the parent :class:`Driver` instance. To prevent accidental
        deletion, three separate confirmation flags must all be `True`.

        Args:
            are_you_sure (bool): First confirmation flag.
            are_you_really_sure (bool): Second confirmation flag.
            for_sure (bool): Third confirmation flag.

        Returns:
            None: This method does not return a value.

        Raises:
            Exception: Propagates any database errors from the underlying driver
                if the DROP TABLE statement fails.

        Example:
            >>> employees = Table(driver, "employees")
            >>> # Permanently delete the employees table
            >>> employees.delete_table(True, True, True)
            >>> # After deletion, the table is no longer accessible via driver.employees

        Note:
            This operation is irreversible. Use the confirmation flags as a safeguard
            against accidental data loss.
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
        """Permanently drop a column from the table.

        This method executes an ALTER TABLE DROP COLUMN statement to remove the
        specified column and all its data from the table. To prevent accidental
        deletion, three separate confirmation flags must all be `True`. After
        successful execution, the corresponding attribute is also removed from the
        Table instance.

        Args:
            column (Column): The :class:`Column` object representing the column to
                drop.
            are_you_sure (bool): First confirmation flag.
            are_you_really_sure (bool): Second confirmation flag.
            for_sure (bool): Third confirmation flag.

        Returns:
            None: This method does not return a value.

        Raises:
            Exception: Propagates any database errors from the underlying driver
                if the ALTER TABLE statement fails.

        Example:
            >>> employees = Table(driver, "employees")
            >>> # Permanently delete the "temp" column
            >>> employees.delete_column(employees.temp, True, True, True)
            >>> # The attribute is removed; accessing it later raises AttributeError

        Note:
            This operation is irreversible. Use the confirmation flags as a safeguard
            against accidental data loss.
        """
        if are_you_sure and are_you_really_sure and for_sure:
            self._exc(f'ALTER TABLE {self.name_} DROP COLUMN {column.first_name};')
            self.__delattr__(column.first_name[1:-1])

    def add_column(self, column_name: str, data_type: str, nullable: bool = True,
                default: Any = None, auto_increment: bool = False,
                primary_key: bool = False, unique: bool = False) -> None:
        """Add a new column to the table.

        This method executes an ``ALTER TABLE ADD COLUMN`` statement and,
        if ``primary_key`` is `True`, also adds a primary key constraint.
        After the column is created, a corresponding :class:`Column` attribute
        is dynamically added to the :class:`Table` instance, allowing it to be
        referenced in future queries (e.g., in ``update()``, ``insert()``, etc.).

        Args:
            column_name (str): The name of the new column.
            data_type (str): The SQL data type string (e.g., from :class:`DataTypes`).
            nullable (bool, optional): Whether the column can contain NULL values.
                Defaults to `True`.
            default (Any, optional): Default value for the column. If a string is
                provided, it will be quoted; otherwise, it is used as-is. Defaults
                to `None`.
            auto_increment (bool, optional): If `True`, makes the column an identity
                column (``GENERATED BY DEFAULT AS IDENTITY``). Only valid for numeric
                or serial types. Defaults to `False`.
            primary_key (bool, optional): If `True`, adds a primary key constraint
                on this column. Note that a primary key column is implicitly ``NOT NULL``.
                Defaults to `False`.
            unique (bool, optional): If `True`, adds a unique constraint to the column.
                Defaults to `False`.

        Returns:
            None: This method mutates the table structure and does not return a value.

        Raises:
            Exception: Propagates database errors if the ALTER TABLE statement fails,
                or if the column addition violates constraints (e.g., duplicate column
                name, invalid data type, etc.).

        Example:
            Simple addition of a non-nullable text column with a default:

            >>> employees = Table(driver, "employees")
            >>> employees.add_column(
            ...     column_name="department",
            ...     data_type=DataTypes.VARCHAR(50),
            ...     nullable=False,
            ...     default="Engineering"
            ... )
            >>> # Now employees.department is available as a Column object.
            >>> employees.update({employees.department: "Marketing"}, employees.id == 1)

        Example:
            Adding an auto-increment primary key column (SERIAL type) and a unique
            constraint:

            >>> from ormophine.Postgresql import DataTypes
            >>> employees.add_column(
            ...     column_name="employee_id",
            ...     data_type=DataTypes.SERIAL(),
            ...     primary_key=True,
            ...     auto_increment=True,
            ...     nullable=False  # SERIAL is implicitly NOT NULL
            ... )
            >>> # The column "employee_id" is now the primary key and auto-increments.
            >>> employees.add_column(
            ...     column_name="email",
            ...     data_type=DataTypes.VARCHAR(100),
            ...     unique=True
            ... )
        """
        col_def = f'"{column_name}" {data_type}'
        col_def += ' NOT NULL' if not nullable else ''
        col_def += (f" DEFAULT '{default}'" if isinstance(default, str) else f" DEFAULT {default}") if default is not None else ''
        col_def += " GENERATED BY DEFAULT AS IDENTITY" if auto_increment and data_type not in ("SMALLSERIAL", "SERIAL", "BIGSERIAL") else ''
        col_def += " UNIQUE" if unique else ''
        self._exc(f"ALTER TABLE {self.name_} ADD COLUMN {col_def};")
        self._exc(f'ALTER TABLE {self.name_} ADD PRIMARY KEY ("{column_name}");') if primary_key else None
        type_lower = data_type.lower().split("(")[0].strip()
        self.__setattr__(column_name, Column(self, column_name, int if type_lower in ("smallint", "integer", "bigint", "smallserial", "serial", "bigserial") else float if type_lower in ("real", "double precision", "numeric", "decimal", "money") else str if type_lower in ("character varying", "character", "text", "json", "jsonb", "uuid", "date", "time without time zone", "time with time zone", "timestamp without time zone", "timestamp with time zone", "interval") else bytes if type_lower == "bytea" else bool if type_lower == "boolean" else str))

    def rename_table(self, new_name: str) -> None:
        """Rename the current table to a new name.

        This method executes an `ALTER TABLE ... RENAME TO` SQL statement to change
        the table name in the database. It also updates the corresponding :class:`Table`
        attribute on the parent :class:`Driver` instance by removing the old attribute
        and creating a new one with the updated name.

        Args:
            new_name (str): The new name for the table.

        Returns:
            None: This method does not return a value.

        Raises:
            Exception: Propagates any database errors from the underlying driver
                if the `ALTER TABLE` statement fails.

        Example:
            >>> from ormophine.Postgresql import Driver
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> employees = Table(driver, "employees")
            >>> # Rename the table from "employees" to "staff"
            >>> employees.rename_table("staff")
            >>> # The table is now accessible as driver.staff
            >>> staff = driver.staff
        """
        self._exc(f'ALTER TABLE {self.name_} RENAME TO "{new_name}";')
        self.db_obj.__delattr__(self.name_[1:-1])
        self.db_obj.__setattr__(new_name, Table(obj=self.db_obj, table_name=new_name))
        self.name_ = f'"{new_name}"'

    def rename_column(self, column: 'Column', new_name: str) -> None:
        """Rename an existing column in the table.

        This method executes an ALTER TABLE statement to rename a column in the
        database and updates the :class:`Table` instance's attributes accordingly.
        The old attribute is removed and a new attribute with the new column name
        is added, preserving the column's data type.

        Args:
            column (Column): The column object to rename.
            new_name (str): The new name for the column. Must be a valid PostgreSQL
                identifier.

        Returns:
            None: This method does not return a value.

        Raises:
            Exception: Propagates any database errors from the underlying driver,
                such as if the column does not exist or the new name is invalid.

        Example:
            >>> employees = Table(driver, "employees")
            >>> # Rename the 'emp_name' column to 'full_name'
            >>> employees.rename_column(employees.emp_name, "full_name")
            >>> # The attribute is now accessible as employees.full_name
        """
        query = f'ALTER TABLE {self.name_} RENAME COLUMN {column.first_name} TO "{new_name}";'
        self._exc(query)
        self.__delattr__(column.first_name.strip('"'))
        self.__setattr__(new_name, Column(self, new_name, column.datatype))

    def create_index(
        self,
        index_name: str,
        columns: list['Column'],
        unique: bool = False,
        where: 'ColumnsOperation' = None
    ) -> None:
        """Create an index on one or more columns of the table.

        This method constructs and executes a CREATE INDEX statement to improve
        query performance on the specified columns. It supports unique indexes,
        multi-column indexes, and partial indexes with a WHERE condition.

        Args:
            index_name (str): The name of the index to create.
            columns (list[Column]): A list of :class:`Column` objects to include
                in the index.
            unique (bool, optional): If `True`, creates a UNIQUE index to enforce
                uniqueness of the indexed columns. Defaults to `False`.
            where (ColumnsOperation, optional): A :class:`ColumnsOperation`
                condition to create a partial index. Only rows satisfying this
                condition are indexed. Defaults to `None`.

        Returns:
            None: This method executes the index creation and does not return
            a value.

        Raises:
            Exception: Propagates any database errors (e.g., duplicate index name,
                column not found, etc.) from the underlying driver.

        Example:
            Simple index on a single column:

            >>> employees = Table(driver, "employees")
            >>> employees.create_index("idx_employees_name", [employees.name])
            # Creates: CREATE INDEX idx_employees_name ON "employees" ("name");

        Example:
            Unique composite index with a partial condition:

            >>> # Create a unique index on (department, title) for active employees
            >>> employees.create_index(
            ...     "idx_employees_dept_title_active",
            ...     [employees.department, employees.title],
            ...     unique=True,
            ...     where=employees.status == "active"
            ... )
            # Creates: CREATE UNIQUE INDEX idx_employees_dept_title_active
            # ON "employees" ("department", "title")
            # WHERE (("status" = 'active'));
        """
        if where:
            wr = f'WHERE {where._output[0]}'
            for i in where._output[1]:
                wr=wr.replace('%s',i if isinstance(i,str) else str(i),1)
        self._excp(f'CREATE {'UNIQUE ' if unique else ''}INDEX {index_name} ON {self.name_} ({','.join(i.first_name for i in columns)}) {wr if where else ''}',[])

    def delete_index(self, index_name: str) -> None:
        """Drop an existing index from the table.

        This method executes a `DROP INDEX IF EXISTS` statement to remove the
        specified index from the database. Using `IF EXISTS` prevents an error
        if the index does not exist.

        Args:
            index_name (str): The name of the index to delete.

        Returns:
            None: This method does not return a value.

        Raises:
            Exception: Propagates any database errors from the underlying driver
                if the DROP INDEX statement fails for reasons other than
                non-existence (e.g., permission issues).

        Example:
            >>> employees = Table(driver, "employees")
            >>> # Create an index on the 'last_name' column
            >>> employees.create_index("idx_last_name", [employees.last_name])
            >>> # Delete the index when no longer needed
            >>> employees.delete_index("idx_last_name")
        """
        self._exc(f'DROP INDEX IF EXISTS "{index_name}";')

    def get_indexes_info(self) -> Any:
        """Retrieve detailed information about all indexes defined on the table.

        This method queries PostgreSQL system catalogs to obtain comprehensive
        metadata for each index associated with the table, including the index name,
        type, definition SQL, uniqueness flag, and primary key status.

        Returns:
            list[dict]: A list of dictionaries, each containing the following keys:
                - idx_name (str): The name of the index.
                - index_type (str): The access method (e.g., 'btree', 'hash').
                - definition (str): The full SQL definition of the index
                (e.g., "CREATE INDEX idx_name ON table (column)").
                - unique (bool): True if the index enforces uniqueness, else False.
                - primary (bool): True if the index is the primary key, else False.

        Raises:
            Exception: Propagates any database errors from the underlying driver
                if the query fails.

        Example:
            >>> employees = Table(driver, "employees")
            >>> indexes = employees.get_indexes_info()
            >>> for idx in indexes:
            ...     print(f"{idx['idx_name']} ({idx['index_type']}): unique={idx['unique']}")
            ...
            employees_pkey (btree): unique=True
            idx_employees_last_name (btree): unique=False
        """
        query = """
            SELECT
                i.relname AS index_name,
                am.amname AS index_type,
                pg_get_indexdef(i.oid) AS index_def,
                indisunique::int AS is_unique,
                indisprimary::int AS is_primary
            FROM pg_index x
            JOIN pg_class c ON c.oid = x.indrelid
            JOIN pg_class i ON i.oid = x.indexrelid
            LEFT JOIN pg_am am ON i.relam = am.oid
            WHERE c.relname = %s
            AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = current_schema())
        """
        return [{'idx_name': r[0],'index_type': r[1],'definition': r[2],'unique': bool(r[3]),'primary': bool(r[4])}for r in self._excfp(query, (self.name_.strip('"'),))]

    def bulk_insert(self, columns: list['Column'], data_list: list) -> None:
        """Insert multiple rows into the table in a single efficient operation.

        This method uses `executemany` to insert many rows at once, which is
        significantly faster than calling :meth:`insert` repeatedly, especially
        for large datasets. The data is passed as a list of rows, where each row
        is a list or tuple of values corresponding to the specified columns.

        Args:
            columns (list[Column]): A list of :class:`Column` objects specifying
                the columns to insert into, in the order that values are provided.
            data_list (list): A list of rows, where each row is a sequence (list
                or tuple) of values to insert. The length and order of values in
                each row must match the `columns` list.

        Returns:
            None: This method executes the insert and does not return a value.

        Raises:
            Exception: Propagates any database errors from the underlying driver,
                including parameter binding errors or constraint violations.

        Example:
            >>> employees = driver.employees
            >>> # Bulk insert multiple employee records
            >>> employees.bulk_insert(
            ...     [employees.name, employees.department, employees.salary],
            ...     [
            ...         ["Alice", "Engineering", 75000],
            ...         ["Bob", "Marketing", 65000],
            ...         ["Charlie", "Sales", 70000],
            ...     ]
            ... )
            >>> # All three rows are inserted in a single executemany call.
        """
        self._excm(f'INSERT INTO {self.name_} ({', '.join(i.first_name for i in columns)}) VALUES ({', '.join('%s' for i in columns)});',data_list)

    def bulk_update(self, update: dict['Column', Any], where: 'ColumnsOperation', data_list: list) -> None:
        """Execute a bulk UPDATE operation with parameterized placeholders.

        This method performs a single UPDATE statement for multiple rows by using
        placeholders (`PLACE_HOLDER`) that are replaced with values from each row
        in `data_list`. It is designed for efficient batch updates where the same
        update structure applies to many rows, but the specific values differ per row.

        The `update` dictionary and the `where` condition can contain the special
        placeholder `self.PLACE_HOLDER` (or `db.PLACE_HOLDER`) to indicate that the
        actual value should be taken from the corresponding position in each row of
        `data_list`. The method constructs the final SQL by replacing `%s` placeholders
        with `PLACE_HOLDER`, builds a parameterized query, and then executes it using
        `executemany` with the `data_list`.

        Args:
            update (dict[Column, Any]): A dictionary mapping :class:`Column` objects
                to new values. Values can be literals, :class:`Column` objects (for
                column-to-column assignment), or :class:`ColumnsOperation` objects.
                Use `PLACE_HOLDER` for values that should come from `data_list`.
            where (ColumnsOperation): A :class:`ColumnsOperation` object representing
                the condition that determines which rows to update. Can also contain
                `PLACE_HOLDER` to be substituted from `data_list`.
            data_list (list): A list of rows, where each row is a list/tuple of values
                corresponding to the `PLACE_HOLDER` occurrences in the `update` and
                `where` clauses (in order of appearance).

        Returns:
            None: This method executes the bulk update and does not return a value.

        Raises:
            Exception: If the number of `PLACE_HOLDER` occurrences does not match the
                number of items in each row of `data_list`. Also propagates other
                database errors.

        Example:
            Simple bulk update using placeholders for column values:

            >>> # Increase salary by a variable amount for each department
            >>> employees = Table(driver, "employees")
            >>> employees.bulk_update(
            ...     {employees.salary: employees.salary + employees.PLACE_HOLDER},
            ...     employees.department == employees.PLACE_HOLDER,
            ...     data_list=[[5000, "Engineering"], [3000, "Marketing"], [4000, "Sales"]]
            ... )
            >>> # This generates: UPDATE "employees" SET "salary" = ("salary" + %s)
            >>> # WHERE "department" = %s; and executes with the given data.

        Example:
            Complex bulk update with computed expressions and multiple placeholders:

            >>> # Set bonus as a percentage of salary and update title for managers
            >>> employees.bulk_update(
            ...     {
            ...         employees.bonus: employees.salary * employees.PLACE_HOLDER / 100,
            ...         employees.title: employees.title + " (Senior)"
            ...     },
            ...     (employees.title == "Manager") & (employees.years > employees.PLACE_HOLDER),
            ...     data_list=[[10, 5], [15, 8], [12, 6]]
            ... )
            >>> # The PLACE_HOLDER in the update (for percentage) and in the where condition
            >>> # (for years threshold) are replaced from data_list rows.
            >>> # Each row provides [percentage, years_threshold].
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
        """Perform a JOIN query on this table with other tables.

        This method constructs and executes a SELECT statement that joins the current
        table with one or more other tables using the specified join types
        (INNER, LEFT, RIGHT). The result set can be filtered with a WHERE clause
        and ordered by a column. Columns are automatically aliased using the format
        ``<table_name>_<column_name>`` to avoid name conflicts.

        Args:
            columns (list[Column]): A list of :class:`Column` objects or
                :class:`ColumnsOperation` expressions to select. Each item will be
                included in the SELECT clause.
            joins_list (list[Union[Join.Inner, Join.Left, Join.Right]]): A list of
                join definitions created using the :class:`Join` inner classes.
                Each join specifies a table and the join condition.
            where (ColumnsOperation, optional): A :class:`ColumnsOperation`
                expression for filtering rows. Defaults to None (no filter).
            order_by (Column, optional): A :class:`Column` to order the results by.
                Defaults to None (no ordering).

        Returns:
            list[tuple]: A list of tuples where each tuple represents a row in the
                result set. The values correspond to the selected columns in the
                order they were specified. If columns include aliases, the result
                tuples will have the aliased names (though the return format is
                raw tuples).

        Raises:
            Exception: Propagates any database errors from the underlying driver,
                including SQL syntax errors or join condition issues.

        Example:
            Simple join between employees and departments:

            >>> from ormophine.Postgresql import Driver, Table, Join
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> employees = driver.employees
            >>> departments = driver.departments
            >>>
            >>> # Join employees with departments on department_id
            >>> results = employees.join(
            ...     columns=[employees.id, employees.name, departments.name],
            ...     joins_list=[Join.Inner(departments, employees.dept_id == departments.id)],
            ...     where=employees.salary > 50000,
            ...     order_by=employees.name
            ... )
            >>> for row in results:
            ...     print(row)  # e.g., (1, 'Alice', 'Engineering')

        Example:
            Complex join with multiple tables and computed columns:

            >>> from ormophine.Postgresql import Join, ColumnsOperation
            >>> # Assume tables: orders, customers, products
            >>> orders = driver.orders
            >>> customers = driver.customers
            >>> products = driver.products
            >>>
            >>> # Select order details with customer name and product price with tax
            >>> results = orders.join(
            ...     columns=[
            ...         orders.id,
            ...         customers.name,
            ...         products.name,
            ...         orders.quantity * orders.unit_price,  # ColumnsOperation
            ...         (orders.quantity * orders.unit_price) * 1.1  # computed total with tax
            ...     ],
            ...     joins_list=[
            ...         Join.Inner(customers, orders.customer_id == customers.id),
            ...         Join.Left(products, orders.product_id == products.id)
            ...     ],
            ...     where=(orders.order_date >= '2024-01-01') & (orders.status == 'completed'),
            ...     order_by=orders.order_date
            ... )
            >>> # Results are returned as tuples with aliased column names
        """
        tl = []
        [tl.extend(i._output[1]) if isinstance(i,ColumnsOperation) else None for i in columns]
        [tl.extend(i._output[1]) for i in joins_list]
        return self._excfp(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}'if isinstance(i,Column)else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")")else i._output[0]} AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'WHERE {where._output[0]}'if where else''} {f'ORDER BY {order_by.name}' if order_by else''}', tl+where._output[1]) if where else self._excfp(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}'if isinstance(i,Column)else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")") else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}'for i in columns)} FROM {self.name_} {' '.join(i._output[0]for i in joins_list)} {f'ORDER BY {order_by.name}' if order_by else''}', tl) if tl else self._excf(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column) else f'{i._output[0][1:-1] if i._output[0].startswith('(') and i._output[0].endswith(')') else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'ORDER BY {order_by.name}'if order_by else''}')
        # The above line is approximately 1381 characters, which is not standard, but it is written this way
        # to improve performance in the Driver class and to avoid checking whether the second item in the query
        # is an empty list for each input.

