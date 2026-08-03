from __future__ import annotations
from .. import Column, ColumnsOperation, BatchOperation, Join
from queue import SimpleQueue
from typing import Any

class Table:
    """Represents a database table with methods for data manipulation, schema changes, and queries.

    The `Table` class provides a high‑level, Pythonic interface to interact with a SQLite table.
    It dynamically creates `Column` attributes for each column, and offers methods for:
        - CRUD operations: `insert()`, `update()`, `get_row()`, `delete_row()`
        - Bulk operations: `bulk_insert()`, `bulk_update()`, `batch()`
        - Schema management: `add_column()`, `rename_column()`, `delete_column()`, `create_index()`
        - Joins: `join()` (using `Join` helper classes)
        - Raw SQL: `custom_execute()`, `custom_execute_many()`, `custom_execute_with_fetch()`

    All methods are **blocking** – each call waits until the operation is completed.
    Exceptions are raised immediately on failure.

    Attributes:
        name_ (str): Bracket‑wrapped table name, e.g., `'[users]'`.
        main_queue (SimpleQueue): Queue for sending commands to the writer thread.
        db_obj (Driver): Parent Driver instance.

    Examples:
        Basic CRUD:
        >>> db = Driver('company.db')
        >>> employees = db.employees  # Table object
        >>> employees.insert({employees.name: 'Alice', employees.salary: 5000})
        >>> employees.update({employees.salary: 5500}, where=employees.name == 'Alice')
        >>> rows = employees.get_row([employees.name, employees.salary], where=employees.salary > 4000)
        >>> employees.delete_row(where=employees.name == 'Alice')

        Selecting with expressions and slicing:
        >>> employees.get_row([employees.name.upper(), employees.salary * 1.1, employees.email[:-4]])

        Joining tables:
        >>> orders = db.orders
        >>> customers = db.customers
        >>> result = orders.join(
        ...     columns=[customers.name, orders.amount],
        ...     joins_list=[Join.Inner(customers, customers.id == orders.customer_id)],
        ...     where=orders.amount > 100
        ... )

        Bulk operations:
        >>> employees.bulk_insert([employees.name, employees.salary],
        ...                       [['Bob', 3000], ['Charlie', 3500]])
        >>> employees.bulk_update({employees.salary: '?'}, where=employees.name == '?',
        ...                       data_list=[[4000, 'Bob'], [4500, 'Charlie']])

        Batch (transaction):
        >>> (employees.batch()
        ...     .insert({employees.name: 'Dave', employees.salary: 2000})
        ...     .update({employees.salary: employees.salary + 500}, where=employees.name == 'Dave')
        ...     .run())

        Schema changes (dangerous, use with caution):
        >>> employees.add_column('department', str, default_value='general')
        >>> employees.rename_column(employees.department, 'dept')
        >>> employees.delete_column(employees.dept, True, True, True)

        Index management:
        >>> employees.create_index('idx_salary', [employees.salary])
        >>> employees.get_indexes()
        >>> employees.delete_index('idx_salary')
    """
    PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_?_'
    def __init__(self, obj: Driver, table_name: str):
        """
        Initialize a Table object representing a database table.

        This constructor fetches the table's schema information via
        :meth:`get_table_info` and dynamically creates :class:`Column`
        attributes for each column in the table. The column names become
        attributes on the Table instance, allowing access like
        ``table.column_name``. Additionally, a special attribute ``ROWID``
        is added to represent SQLite's implicit rowid.

        The table name is normalized with square brackets for safe SQL
        usage (e.g., ``[table_name]``). The Table object uses the provided
        :class:`Driver` instance to communicate with the database via its
        main queue and reader pool.

        Args:
            obj (Driver): The driver instance that manages the database
                connection and thread pool.
            table_name (str): The name of the table to represent.

        Raises:
            Exception: If the table schema cannot be retrieved (e.g., the
                table does not exist or the database is inaccessible).

        Example:
            Assuming a database with a ``users`` table::

                db = Driver('my.db')
                users = db.users #Tables are available as properties
                # Now users.name, users.age, etc., are Column objects.
                # Also users.ROWID is available.
        """
        self.name_= '['+table_name+']'
        self.main_queue: SimpleQueue= obj.main_queue
        self.db_obj= obj
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_?_'
        for i in self.get_table_info():
            self.__setattr__(i['name'], Column(self, i['name'], i['datatype']))
        self.__setattr__('ROWID', Column(self, 'ROWID', int))

    def _exc(self, cmd: str, query: tuple):
        """Send a command and query to the database thread and wait for the result.

        This is a low‑level internal method used by :class:`Table` to
        communicate with the main database thread via the driver's queue.
        It packages the command and query into a message, places it on the
        queue, and blocks until a response is received. If the execution
        succeeds, the result (or ``None``) is returned; otherwise, an
        exception is raised with the error message.

        Args:
            cmd (str): The command type to execute. Valid values include:
                - ``'qf'``: execute a query and fetch results.
                - ``'qcb'``: execute a query that commits changes.
                - ``'qsb'``: execute a script (batch) of statements.
                - ``'qmb'``: execute a query with multiple parameter sets.
            query (tuple): The SQL query string and optional parameters.
                Typically a 1‑ or 2‑tuple, e.g., ``(sql,)`` or ``(sql, params)``.

        Returns:
            Any: The result of the database operation if successful. For
                ``'qf'``, this is the fetched rows; for other commands,
                it is ``None``.

        Raises:
            Exception: If the database operation fails, an exception is
                raised with the underlying SQLite error message.

        Example:
            This method is used internally by other :class:`Table` methods::

                table._exc('qf', ('SELECT * FROM users WHERE id = ?', (1,)))
                # returns the fetched row(s) for the query

                table._exc('qcb', ('UPDATE users SET name = ? WHERE id = ?', ('Alice', 1)))
                # updates the user and returns None on success
        """
        queue_call_back = SimpleQueue()
        self.main_queue.put((cmd, query, queue_call_back))
        if (callback := queue_call_back.get(block=True))[0]:
            return callback[1]
        else:
            raise Exception(callback[1])
    
    def batch(self) -> 'BatchOperation':
        """Create a batch operation context bound to this table.

        Returns a :class:`BatchOperation` instance that allows multiple
        INSERT and UPDATE statements to be grouped into a single atomic
        transaction. The batch is executed by calling its :meth:`~BatchOperation.run`
        method, which sends all queued operations to the table's thread‑safe
        main queue and waits for the result.

        This is useful for bundling related changes that must succeed or fail
        together, avoiding intermediate commits.

        Returns:
            BatchOperation: A new batch operation object pre‑configured to use
                this table's queue and name.

        Raises:
            Exception: If any operation in the batch fails when :meth:`~BatchOperation.run`
                is called, the exception from SQLite is propagated.

        Example:
            Simple usage with literal values::

                table = db.employees
                batch = table.batch()
                batch.insert({table.name: "John", table.salary: 50000})
                batch.update({table.department: "Engineering"},
                            where=table.id.eq(42))
                batch.run()

        Example:
            Complex usage using :class:`ColumnsOperation` expressions for both
            the value to be set and the condition::

                batch = table.batch()
                # Give a 10% raise to everyone in 'Sales' earning less than 60000
                batch.update(
                    {table.salary: table.salary * 1.10},
                    where=(table.department == "Sales") & (table.salary < 60000)
                )
                # Set display_name to first_name + ' ' + last_name for a specific row
                batch.update(
                    {table.display_name: table.first_name.add_end(" ").add_end(table.last_name)},
                    where=table.id.eq(99)
                )
                batch.run()
        """
        return BatchOperation(self)
    
    def update(self, update: dict[Column, Any], where: 'ColumnsOperation') -> None:
        """Updates rows in the table that match the given condition.

        Constructs and executes an ``UPDATE`` SQL statement, setting column values
        as specified in the ``update`` dictionary for all rows where the
        ``where`` condition holds. The values can be plain Python scalars,
        other :class:`Column` objects (to copy values between columns), or
        :class:`ColumnsOperation` instances (to use SQL expressions).
        Placeholders (``?``) are automatically generated for scalar values;
        column references and operation outputs are embedded directly into the
        SQL.

        Args:
            update: A dictionary mapping :class:`Column` instances to the new
                value. The value can be:

                * A plain Python scalar (``int``, ``float``, ``str``, ``bytes``).
                It will be passed as a parameter.
                * Another :class:`Column` object – the column's value will be
                copied.
                * A :class:`ColumnsOperation` representing a SQL expression
                (e.g., arithmetic, string concatenation). Its parameters are
                merged into the query's parameter list.
            where: A :class:`ColumnsOperation` representing the ``WHERE``
                clause condition. It must be created from column comparisons
                (e.g., using :meth:`Column.eq`, ``==``, ``>``, etc.).

        Returns:
            None

        Raises:
            Exception: If the database operation fails. The exception message
                contains details from SQLite.

        Example:
            Simple update with scalar values::

                # Assume driver and table are already set up
                users = driver.users
                name_col = users.name
                age_col = users.age

                # Update age to 30 where name is 'Alice'
                users.update(
                    update={age_col: 30},
                    where=name_col == 'Alice'
                )

            Complex update with a :class:`ColumnsOperation` expression::

                # Increment the 'score' column by 10 for all rows where
                # the 'level' column is greater than 5.
                score_col = users.score
                level_col = users.level

                # Create an operation: score + 10
                score_plus_10 = score_col + 10   # returns a ColumnsOperation

                users.update(
                    update={score_col: score_plus_10},
                    where=level_col > 5
                )

            Using column-to-column copy and string concatenation::

                fullname_col = users.fullname
                first_col = users.first
                last_col = users.last

                # Concatenate first and last name into fullname
                fullname_expr = first_col.add_end(' ').add_end(last_col)
                users.update(
                    update={fullname_col: fullname_expr},
                    where=fullname_col == ''  # only empty fullnames
                )
        """
        temp_list = []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        query = (f'UPDATE {self.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=?' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1])
        self._exc('qcb', query)

    def get_table_info(self, from_readers_pool: bool = False):
        """Retrieves column metadata for the table from the SQLite database.

        Uses the ``PRAGMA table_info({self.name_})`` statement to fetch column
        details, including name, data type, nullability, default value, and
        primary key status. The data type is mapped to Python types: ``int``
        for ``INTEGER``, ``str`` for ``TEXT``, ``float`` for ``REAL``/
        ``NUMERIC``, ``bytes`` for ``BLOB``; otherwise defaults to ``str``.

        Args:
            from_readers_pool (bool): If ``False`` (default), the query is
                executed on the main writer connection. If ``True``, a
                connection from the reader pool is obtained, allowing
                non‑blocking reads in multi‑threaded scenarios.

        Returns:
            list[dict]: A list of column information dictionaries, each with
            the following keys:
                - ``id`` (int): column ID (position).
                - ``name`` (str): column name.
                - ``datatype`` (type): Python type inferred from SQL type.
                - ``notnull`` (int): 1 if NOT NULL, 0 otherwise.
                - ``default_value`` (Any|None): default value if set.
                - ``primary_key`` (int): 1 if part of primary key, 0 otherwise.

        Raises:
            Exception: If the database query or reader‑pool acquisition fails.

        Example:
            >>> users = driver.users
            >>> cols = users.get_table_info()
            >>> for col in cols:
            ...     print(f"{col['name']}: {col['datatype']}")
            id: <class 'int'>
            username: <class 'str'>
            ...
            >>> # Using a reader‑pool connection:
            >>> cols_async = users.get_table_info(from_readers_pool=True)
        """
        query = f'PRAGMA table_info({self.name_})'
        if not from_readers_pool:
            columns = self._exc('qf', (query,))
        else:
            queueCallBack = SimpleQueue()
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', (query,), queueCallBack])
            if (callback := queueCallBack.get(block=True))[0]:
                columns = callback[1]
            else:
                raise Exception(callback[1])
            self.db_obj.pool_holder.put(connection_queue)
        
        return [{'id':i[0], 'name':i[1], 'datatype':int if 'INTEGER' in i[2]  else str if 'TEXT' in i[2] else float if 'REAL' in i[2] else bytes if 'BLOB' in i[2] else float if 'NUMERIC' in i[2] else str, 'notnull': i[3], 'default_value':i[4], 'primary_key':i[5]}for i in columns]

    def get_columns_name(self, from_readers_pool: bool = False) -> list[str]:
        """Retrieve the names of all columns in the table.

        Fetches column metadata using ``PRAGMA table_info`` and returns a list
        containing only the column name strings.  This is a convenience wrapper
        around :meth:`get_table_info` that discards other column details.

        The operation can be performed on either the main writer connection
        (default) or on a dedicated reader thread from the connection pool.
        When ``from_readers_pool`` is ``True``, the method acquires a reader
        queue from :attr:`Driver.pool_holder`, executes the query there, and
        returns the queue back to the pool.  This avoids blocking the writer
        thread and is suitable for read-heavy workloads.

        Args:
            from_readers_pool (bool): If ``True``, use a read-only connection
                from :attr:`Driver.pool_holder`.  Defaults to ``False``, which
                sends the query through the main writer connection.

        Returns:
            list[str]: A list of column names as plain strings (without brackets
            or escaping).

        Raises:
            Exception: Propagated from the underlying execution if the query
                fails or the reader callback reports an error.

        Example:
            >>> table = db.users
            >>> cols = table.get_columns_name()
            >>> print(cols)
            ['id', 'name', 'email']
        """        
        query = f'PRAGMA table_info({self.name_})'
        
        if not from_readers_pool:
            columns = self._exc('qf', (query,))
        else:
            queueCallBack = SimpleQueue()
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', (query,), queueCallBack])
            if (callback := queueCallBack.get(block=True))[0]:
                columns = callback[1]
            else:
                raise Exception(callback[1])
            self.db_obj.pool_holder.put(connection_queue)
        return [i[1] for i in columns]

    def get_row(
        self,
        which_columns: list['Column' | 'ColumnsOperation'],
        where: 'ColumnsOperation' = None,
        order_by: 'Column' = None,
        from_readers_pool: bool = False
    ) -> list[Any] | list[tuple]:
        """Fetch rows from the table with optional filtering, ordering, and expression columns.

        Builds and executes a ``SELECT`` query on the table. The columns to retrieve can be
        plain :class:`Column` objects or complex :class:`ColumnsOperation` expressions.
        If a single column/operation is requested, a flat list of values is returned;
        otherwise a list of tuples (one per selected column) is returned.

        Args:
            which_columns (list): List of columns or operations to select. Each element can be a
                :class:`Column` instance (retrieves its raw value) or a
                :class:`ColumnsOperation` object (evaluates the expression in SQL).
            where (:class:`ColumnsOperation`, optional): Filtering condition. Only rows for which
                the condition evaluates to true are included. Defaults to ``None`` (all rows).
            order_by (:class:`Column`, optional): Column to order results by. If omitted, ordering
                falls back to the ``ROWID`` pseudo-column.
            from_readers_pool (bool, optional): If ``True``, the query is dispatched to a dedicated
                reader thread from the connection pool, which can improve concurrency for
                read‑heavy workloads. Defaults to ``False``.

        Returns:
            list: If ``which_columns`` contains a single element, a flat list of column values
            (e.g., ``['Alice', 'Bob']``). Otherwise a list of tuples, each tuple containing
            the selected column values in the same order as ``which_columns``.

        Raises:
            Exception: If the underlying SQL execution fails. The exception message contains
                the database error details.

        Example:
            Simple retrieval of a single column:

            >>> names = my_table.get_row([my_table.name])
            >>> print(names)
            ['Alice', 'Bob']

            Retrieving multiple columns:

            >>> rows = my_table.get_row([my_table.name, my_table.age])
            >>> for name, age in rows:
            ...     print(f"{name} is {age} years old")

            Adding a filter and ordering:

            >>> adults = my_table.get_row(
            ...     [my_table.name],
            ...     where=my_table.age > 18,
            ...     order_by=my_table.name
            ... )
            >>> print(adults)
            ['Charlie', 'Diana']

            Using a :class:`ColumnsOperation` expression (arithmetic, concatenation, etc.):

            >>> full_name = my_table.first_name + ' ' + my_table.last_name  # __add__ on Column creates ColumnsOperation
            >>> # Filtering on the computed column
            >>> condition = full_name.contains('John')
            >>> results = my_table.get_row([full_name, my_table.age], where=condition)
            >>> for name, age in results:
            ...     print(f"Full name: {name}, Age: {age}")

            Slicing and string operations:

            >>> first_initial = my_table.name[:1]  # substring just like python
            >>> initials_and_ages = my_table.get_row([first_initial, my_table.age], where=my_table.age >= 30)
        """

        tl = []
        wc = []
        [wc.append(i.first_name) if isinstance(i,Column) else [wc.append(i._output[0]), tl.extend(i._output[1])] for i in which_columns]
        
        query = (f'SELECT {', '.join(wc)} FROM {self.name_} WHERE {where._output[0]} ORDER BY {order_by.first_name if order_by else 'ROWID'};', tl+where._output[1]) if where else (f'SELECT {', '.join(wc)} FROM {self.name_} ORDER BY {order_by.first_name if order_by else 'ROWID'};',tl) if tl else (f'SELECT {', '.join(wc)} FROM {self.name_} ORDER BY {order_by.first_name if order_by else 'ROWID'};',)
        if not from_readers_pool:
            return [row[0] for row in self._exc('qf', query)] if len(which_columns) == 1 else self._exc('qf', query)
        else:
            queueCallBack = SimpleQueue()
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', query, queueCallBack])
            self.db_obj.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return [row[0] for row in callback[1]] if len(which_columns) == 1 else callback[1]
            else:
                raise Exception(callback[1])

    def insert(self, insert: dict['Column', Any]) -> None:
        """Insert a single row into the table.

        Builds and executes an ``INSERT INTO`` statement using the provided mapping
        of :class:`Column` objects to their values. All values are parameterised to
        prevent SQL injection.

        Args:
            insert (dict[:class:`Column`, Any]): A dictionary where each key is a
                :class:`Column` instance belonging to this table, and the corresponding
                value is the Python data to store in that column.

        Returns:
            None

        Raises:
            Exception: If the underlying database operation fails (e.g., constraint
                violation, syntax error). The exception message contains the database
                error details.

        Example:
            Simple insertion of a single row with literal values::

                db = Driver('my_db.sqlite')
                user_table = db.user_table  # User table already created

                user_table.insert({
                    user_table.name: 'Alice',
                    user_table.age: 30,
                    user_table.email: 'alice@example.com'
                })

            Insert a row and then verify it using a :class:`ColumnsOperation` in a
            subsequent ``get_row`` call::

                # Insert a product
                products_table.insert({
                    products_table.name: 'Widget',
                    products_table.price: 19.99,
                    products_table.quantity: 150
                })

                # Retrieve products with low stock using an operation
                low_stock = products_table.quantity < 50
                result = products_table.get_row(
                    [products_table.name],
                    where=low_stock
                )
                print(result)  # [] because quantity is 150

                # Now insert a product that meets the low-stock condition
                products_table.insert({
                    products_table.name: 'Gadget',
                    products_table.price: 9.99,
                    products_table.quantity: 30
                })

                result = products_table.get_row(
                    [products_table.name],
                    where=low_stock
                )
                print(result)  # ['Gadget']
        """
        query = (f'INSERT INTO {self.name_} ({', '.join(i.first_name for i in list(insert.keys()))}) VALUES ({', '.join(f'?' for k in insert)})', [v for v in list(insert.values())])
        self._exc('qcb', query)
 
    def custom_execute(self, query: str, params: list = None) -> None:
        """Executes a raw SQL statement on the table's database connection.

        Sends the query to the writer queue and waits for completion. The statement
        is executed immediately and committed on success; on failure a rollback is
        performed and an exception is raised. This method is intended for data
        manipulation statements (INSERT, UPDATE, DELETE, DDL, etc.) that do not
        return rows.

        Args:
            query (str): The SQL statement to execute. Placeholders (``?``) are
                allowed for parameterised queries.
            params (list, optional): A list of parameters to bind to the
                placeholders in `query`. Defaults to None, in which case the
                statement is executed without parameters.

        Returns:
            None

        Raises:
            Exception: If the database operation fails. The original exception
                from sqlite3 is propagated.

        Example:
            >>> users_table.custom_execute(
            ...     "INSERT INTO [users] (name, age) VALUES (?, ?)",
            ...     ["Alice", 30]
            ... )
            >>> # Simple DDL
            >>> users_table.custom_execute("CREATE INDEX idx_name ON [users](name)")
        """        
        self._exc('qcb', (query, params)) if params else self._exc('qcb', (query,))
            
    def custom_execute_many(self, query: str, params: list = None) -> None:
        """Executes a single SQL statement against multiple parameter sets.

        This method sends a ``qmb`` (query many batch) command to the
        underlying driver thread, which uses ``cursor.executemany()`` to
        efficiently process the same statement with different bound values.
        It is ideal for bulk inserts, updates, or deletes where the SQL
        structure remains identical but the data changes.

        Note:
            This is a non‑fetching operation; no result set is returned.

        Args:
            query (str): The SQL statement to execute. Use ``?`` placeholders
                for parameter binding.
            params (list, optional): An iterable of parameter sequences (e.g.,
                list of tuples or lists). Each item must match the number of
                placeholders in ``query``. If ``None``, the statement is
                executed once without parameters (though ``executemany`` with
                no parameters is equivalent to a single ``execute``).

        Returns:
            None

        Raises:
            Exception: If the database operation fails (e.g., constraint
                violation, malformed SQL). The original exception from the
                driver thread is propagated.

        Example:
            Batch‑insert users using a custom statement::

                users = db.users
                users.custom_execute_many(
                    "INSERT INTO users (username, score) VALUES (?, ?)",
                    [
                        ("alice", 95),
                        ("bob", 87),
                        ("carol", 92)
                    ]
                )

            This is equivalent to, but often more convenient than, building
            a :class:`BatchOperation` manually.
        """
        self._exc('qmb', (query, params)) if params else self._exc('qmb', (query,))

    def custom_execute_with_fetch(self, query: str, params: list = None, from_readers_pool: bool = False) -> Any:
        """Execute a custom SQL query and return fetched results.

        Sends the provided SQL query and optional parameters to the database
        connection. If ``from_readers_pool`` is ``False`` (default), the query
        is executed on the main writer connection; otherwise a connection from
        the non‑blocking reader pool is used. The result is the same as
        ``cursor.fetchall()`` – a list of tuples, each representing a row.

        Args:
            query (str): The SQL statement to execute. Placeholders ``?`` can
                be used for parameterized queries.
            params (list, optional): A list of values to bind to the
                placeholders in ``query``. Defaults to ``None``.
            from_readers_pool (bool): If ``True``, the query is run against a
                reader‑pool connection (non‑blocking). Defaults to ``False``.

        Returns:
            Any: The rows returned by the query as a list of tuples. For
            example, ``[(val1, val2), ...]``.

        Raises:
            Exception: If the database operation fails or a reader‑pool
                connection cannot be acquired.

        Example:
            Assuming ``users`` is a :class:`Table` instance:

            >>> rows = users.custom_execute_with_fetch(
            ...     "SELECT id, username FROM users WHERE age > ?",
            ...     params=[18]
            ... )
            >>> for row in rows:
            ...     print(row)
            (1, 'alice')
            (2, 'bob')

            To use a reader pool connection for better concurrency:

            >>> rows = users.custom_execute_with_fetch(
            ...     "SELECT COUNT(*) FROM users",
            ...     from_readers_pool=True
            ... )
        """
        if not from_readers_pool:
            return self._exc('qf', (query, params)) if params else self._exc('qf', (query,))
        else:
            queueCallBack = SimpleQueue()
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', (query, params), queueCallBack]) if params else connection_queue.put(['qf', (query,), queueCallBack])
            self.db_obj.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return callback[1]
            else:
                raise Exception(callback[1])

    def delete_row(self, where: 'ColumnsOperation') -> None:
        """Deletes all rows from the table that match the given condition.

        Constructs a ``DELETE FROM ... WHERE ...`` SQL statement using the
        provided :class:`ColumnsOperation` expression. The operation is sent
        to the writer queue and executed atomically in a thread‑safe manner.

        Args:
            where (ColumnsOperation): A condition expression built from
                :class:`Column` objects and comparison methods (e.g.,
                :meth:`Column.eq`, :meth:`Column.gt`). The
                :attr:`ColumnsOperation._output` attribute contains the SQL
                fragment and the corresponding bind parameters.

        Returns:
            None: This method does not return a value.

        Raises:
            Exception: If the underlying SQL execution fails (e.g., constraint
                violation, syntax error in the condition). The exception
                message includes details from the database driver.

        Example:
            >>> # Assume `db` is a Driver instance and `users` is a Table.
            >>> users = db.users
            >>> # Delete all users with an age less than 18.
            >>> condition = users.age < 18
            >>> users.delete_row(condition)
        """
        query = (f'DELETE FROM {self.name_} WHERE {where._output[0]};', where._output[1])
        self._exc('qcb', query)

    def delete_table(self, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool) -> None:
        """Drops the table from the database and removes it from the driver.

        This method executes a ``DROP TABLE`` statement, permanently deleting
        the table and all its data. As a safety measure, all three boolean
        flags must be ``True`` for the operation to proceed. After successful
        deletion, the table's attribute is removed from the parent
        :class:`Driver` instance, making it inaccessible through the ORM.

        Args:
            are_you_sure (bool): First confirmation flag.
            are_you_really_sure (bool): Second confirmation flag.
            for_sure (bool): Third confirmation flag.

        Returns:
            None: This method mutates the database and the driver state, but
            returns nothing.

        Raises:
            Exception: If any of the confirmation flags are not ``True``, or
                if the database operation fails (e.g., the table does not exist).

        Example:
            >>> db = Driver('mydb.sqlite')
            >>> # assuming a table 'temp_logs' exists
            >>> temp_logs = db.table_object('temp_logs')
            >>> temp_logs.delete_table(True, True, True)
            >>> # Now the table is dropped and 'temp_logs' attribute is gone
            >>> 'temp_logs' in dir(db)
            False
        """
        if are_you_sure and are_you_really_sure and for_sure:
            query = f'DROP TABLE {self.name_};'
            self._exc('qcb', (query,))
            self.db_obj.__delattr__(self.name_[1:-1])

    def delete_column(
        self,
        column: 'Column',
        are_you_sure: bool,
        are_you_really_sure: bool,
        for_sure: bool
        ) -> None:
        """Drops a column from the table permanently.

        Executes an ``ALTER TABLE ... DROP COLUMN`` statement on the database
        and removes the corresponding attribute from the :class:`Table` object.
        The operation is gated by three explicit boolean flags that must all be
        ``True`` to proceed – this is a safety mechanism to prevent accidental
        column deletion.

        Args:
            column (Column): The column object to be deleted. Must belong to
                this table.
            are_you_sure (bool): First confirmation flag.
            are_you_really_sure (bool): Second confirmation flag.
            for_sure (bool): Third confirmation flag. All three must be
                ``True`` for the deletion to execute.

        Returns:
            None: The column is dropped from the schema and the attribute is
            removed from the :class:`Table` instance.

        Raises:
            Exception: If the database operation fails (e.g., the column does
                not exist, or the table is locked). The original error from the
                writer thread is re‑raised.

        Note:
            After successful deletion, the :class:`Column` object passed as
            ``column`` is no longer valid for queries because its underlying
            database column no longer exists. The attribute is also removed
            from the table object, so accessing it later will raise an
            :class:`AttributeError`.

        Example:
            >>> db = Driver("mydb.sqlite3")
            >>> users = db.users
            >>> # Delete the "age" column with triple confirmation
            >>> age_col = users.age  # Column instance
            >>> users.delete_column(
            ...     age_col,
            ...     are_you_sure=True,
            ...     are_you_really_sure=True,
            ...     for_sure=True
            ... )
            >>> # Now users.age will raise AttributeError
        """
        if are_you_sure and are_you_really_sure and for_sure:
            query = f'ALTER TABLE {self.name_} DROP COLUMN {column.first_name};'
            self._exc('qcb', (query,))
            self.__delattr__(column.first_name[1:-1])

    def add_column(self, column_name: str, datatype: int|str|float|bytes, default_value=None, not_null: bool=None) -> None:
        """Adds a new column to the table.

        Executes an ``ALTER TABLE ... ADD COLUMN`` statement using the provided
        ``datatype`` string. The string is expected to come from one of the
        :class:`DataTypes` static methods (e.g., ``DataTypes.INTEGER()``) and
        contains the placeholder ``my_saulted_x``, which is automatically
        replaced with the actual column name. After the database operation
        succeeds, a corresponding :class:`Column` attribute is set on the
        :class:`Table` instance, making it immediately available for queries.

        Args:
            column_name (str): The name of the new column.
            datatype (int | str | float | bytes): The SQL column definition
                string, typically obtained from a :meth:`DataTypes` method.
                The placeholder ``my_saulted_x`` inside this string will be
                replaced with ``column_name``.
            default_value: The default value for the column. If the value is a
                string, it is automatically quoted in the SQL. Defaults to
                ``None`` (no DEFAULT clause).
            not_null (bool): If ``True``, a ``NOT NULL`` constraint is added
                to the column definition. Defaults to ``None``.

        Returns:
            None: The column is added to the database schema and the attribute
            is created on the :class:`Table` object.

        Raises:
            Exception: If the database operation fails (e.g., the column
                already exists, the table is locked, or the ``datatype``
                string is invalid). The original error from the writer thread
                is re‑raised.

        Example:
            >>> db = Driver("mydb.sqlite3")
            >>> users = db.users
            >>> # Add a TEXT column with a default value
            >>> users.add_column(
            ...     "status",
            ...     DataTypes.TEXT(max_length=20),
            ...     default_value="active",
            ...     not_null=True
            ... )
            >>> # Now users.status is a Column object
            >>> print(users.status.first_name)
            [status]
        """
        query = f'ALTER TABLE {self.name_} ADD COLUMN {datatype.replace('my_saulted_x',column_name)}{' NOT NULL' if not_null else ''}{f' DEFAULT {f"'{default_value}'" if type(default_value) == str else default_value}' if default_value else ''}'
        self._exc('qcb', (query,))
        self.__setattr__(column_name, Column(self, column_name, int if 'INTEGER' in datatype  else str if 'TEXT' in datatype else float if 'REAL' in datatype else bytes if 'BLOB' in datatype else float if 'NUMERIC' in datatype else str))

    def rename_table(self, new_name: str) -> None:
        """Renames the table in the database and updates all associated objects.

        Executes an ``ALTER TABLE ... RENAME TO`` statement to change the
        table's name. On success, the old attribute on the :class:`Driver`
        object is removed, a new :class:`Table` attribute with the new name is
        added, and this instance's :attr:`name_` is updated to reflect the new
        name.

        Args:
            new_name (str): The new name for the table (without brackets;
                they will be added automatically).

        Returns:
            None: The table is renamed in place; the :class:`Table` instance
            itself is mutated and the :class:`Driver` attribute is updated.

        Raises:
            Exception: If the ``ALTER TABLE`` command fails (e.g., a table
                with the new name already exists, or the database is locked).
                The original error from the writer thread is re‑raised.

        Example:
            >>> db = Driver("mydb.sqlite3")
            >>> old_users = db.users  # original Table object
            >>> old_users.rename_table("clients")
            >>> # Now db.clients exists, db.users no longer does
            >>> # The old_users variable still refers to the same Table
            >>> # instance, but its name_ attribute is now '[clients]'
            >>> print(db.clients.name_)
            [clients]
        """
        query = f'ALTER TABLE {self.name_} RENAME TO {new_name};'
        self._exc('qcb', (query,))
        self.db_obj.__delattr__(self.name_[1:-1])
        self.db_obj.__setattr__(new_name, Table(obj=self.db_obj, table_name=new_name))
        self.name_ = f'[{new_name}]'

    def rename_column(self, column: 'Column', new_name: str) -> None:
        """Renames an existing column in the table.

        Executes an ``ALTER TABLE ... RENAME COLUMN`` statement to change the
        column name in the database schema. After a successful rename, the
        original :class:`Column` attribute is removed from the :class:`Table`
        instance and a new :class:`Column` attribute with the same datatype
        is added under the new name.

        Args:
            column (Column): The column object to rename. Must be an existing
                column of this table.
            new_name (str): The new name for the column (without brackets).

        Returns:
            None: The table schema and the object's internal attribute
            mapping are updated in place.

        Raises:
            Exception: If the database operation fails (e.g., column does not
                exist, table is locked, or the new name conflicts). The error
                is propagated from the writer thread.

        Example:
            >>> db = Driver("mydb.sqlite3")
            >>> users = db.users
            >>> # Rename the column currently named "age" to "years"
            >>> users.rename_column(users.age, "years")
            >>> # Now users.years exists and users.age raises AttributeError
            >>> print(users.years.first_name)
            '[years]'
        """
        query = f'ALTER TABLE {self.name_} RENAME COLUMN {column.first_name} TO {new_name};'
        self._exc('qcb', (query,))
        self.__delattr__(column.first_name[1:-1])
        self.__setattr__(new_name, Column(self, new_name, column.datatype))

    def create_index(
        self,
        index_name: str,
        columns: list['Column'],
        unique: bool = False,
        where: 'ColumnsOperation' = None
    ) -> None:
        """Creates a new index on the table.

        Builds and executes a ``CREATE INDEX`` (or ``CREATE UNIQUE INDEX``)
        statement. Supports specifying a partial index via a ``WHERE``
        condition built from a :class:`ColumnsOperation` object.

        The parameters inside the ``WHERE`` clause are directly
        interpolated into the SQL string as literals (not using bound
        parameters), so this is safe for trusted data only. The final query
        is executed through the thread‑safe writer queue.

        Args:
            index_name (str): The name of the index to create. Must be
                unique within the database.
            columns (list[Column]): A list of :class:`Column` objects that
                define the indexed columns.
            unique (bool): If ``True``, creates a ``UNIQUE`` index that
                enforces uniqueness of the indexed column combination.
                Defaults to ``False``.
            where (ColumnsOperation, optional): A column operation
                representing the ``WHERE`` clause for a partial index. The
                expression and its parameter values are baked into the SQL.
                Defaults to ``None``.

        Returns:
            None: The operation mutates the database schema; it does not
            return any value.

        Raises:
            Exception: Propagated from the writer thread if the index
                creation fails (e.g., duplicate name, invalid column).

        Example:
            >>> db = Driver("mydb.sqlite3")
            >>> users = db.users
            >>> # Simple index on username
            >>> users.create_index("idx_username", [users.username])
            >>> # Unique composite index
            >>> users.create_index(
            ...     "idx_email_status",
            ...     [users.email, users.status],
            ...     unique=True
            ... )
            >>> # Partial index: only active users
            >>> users.create_index(
            ...     "idx_active_names",
            ...     [users.name],
            ...     where=users.status == 'active'
            ... )
        """
        if where:
            wr = f'WHERE {where._output[0]}'
            for i in where._output[1]:
                wr=wr.replace('?',i if isinstance(i,str) else str(i),1)
        
        query = (f'CREATE {'UNIQUE ' if unique else ''}INDEX {index_name} ON {self.name_} ({','.join(i.first_name for i in columns)}) {wr if where else ''}',[])
        self._exc('qcb', query)

    def delete_index(self, index_name: str) -> None:
        """Drops a database index by its name.

        Sends a ``DROP INDEX`` statement to the writer thread, which
        immediately removes the index from the SQLite schema. This operation
        cannot be undone.

        Args:
            index_name (str): The name of the index to drop. This is the
                identifier used when the index was created (see
                :meth:`create_index`).

        Returns:
            None: The index is removed from the database.

        Raises:
            Exception: If the writer thread encounters an error (e.g., the
                index does not exist, or the database is locked). The original
                error message from SQLite is re‑raised.

        Example:
            >>> db = Driver("app.db")
            >>> users = db.users
            >>> # Create an index for demonstration
            >>> users.create_index("idx_username", [users.username])
            >>> # Later, drop it
            >>> users.delete_index("idx_username")
        """
        query = (f'DROP INDEX {index_name}',)
        self._exc('qcb', query)

    def reindex(self, index_name: str) -> None:
        """Rebuilds a specific index from scratch.

        Issues a ``REINDEX`` command on the given index name to recreate it,
        which can be useful after bulk data changes or to recover from index
        corruption. The operation is executed on the writer connection and
        blocks until complete.

        Args:
            index_name (str): The name of the index to rebuild. Must already
                exist on this table.

        Returns:
            None: The method returns ``None`` after the index has been
            successfully rebuilt.

        Raises:
            Exception: If the ``REINDEX`` command fails (e.g., the index
                does not exist, or the database is locked). The original
                error from the writer thread is re‑raised.

        Example:
            >>> db = Driver("mydb.sqlite3")
            >>> users = db.users
            >>> # Rebuild the "idx_username" index after bulk updates
            >>> users.reindex("idx_username")
        """
        query = (f'REINDEX {index_name}',)
        self._exc('qcb', query)

    def get_indexes(self, from_readers_pool: bool = False) -> Any:
        """Retrieves a list of all index names defined on the table.

        Executes the ``PRAGMA index_list({self.name_})`` statement to obtain
        the names of every index associated with the table. The operation can
        optionally use a reader‑pool connection for non‑blocking reads.

        Args:
            from_readers_pool (bool): If ``False`` (default), the query runs
                on the main writer connection. If ``True``, a connection from
                the reader pool is obtained, allowing concurrent reads without
                blocking write operations.

        Returns:
            list[str]: A list of index name strings. For example,
            ``["idx_username", "idx_email"]``.

        Raises:
            Exception: If the pragma query fails or (when
                ``from_readers_pool=True``) a reader connection cannot be
                acquired. The original exception from the database thread is
                re‑raised.

        Example:
            >>> db = Driver("mydb.sqlite3")
            >>> users = db.users
            >>> indexes = users.get_indexes()
            >>> print(indexes)
            ['idx_username', 'idx_email']
            >>> # Use reader pool for a non‑blocking call
            >>> idx_from_reader = users.get_indexes(from_readers_pool=True)
        """
        query = (f'PRAGMA index_list({self.name_});',)
        if not from_readers_pool: 
            return [i[1] for i in  self._exc('qf', query)]
        else:
            queueCallBack= SimpleQueue()  
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', query, queueCallBack])
            self.db_obj.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return [i[1] for i in callback[1]]
            else:
                raise Exception(callback[1])

    def get_index_info(self, index_name: str, from_readers_pool: bool = False) -> Any:
        """Retrieves detailed information about a specific index.

        Executes ``PRAGMA index_info({index_name})`` to obtain the list of
        columns that the index covers. The result is returned as a dictionary
        containing the index name and the names of the indexed columns.

        Args:
            index_name (str): The name of the index to inspect. Must already
                exist on this table.
            from_readers_pool (bool): If ``False`` (default), the query runs
                on the main writer connection. If ``True``, a connection from
                the reader pool is used, allowing non‑blocking reads.

        Returns:
            dict: A dictionary with two keys:
                - ``'name'`` (str): the index name (same as *index_name*).
                - ``'indexed_columns'`` (list[str]): the column names that
                are part of the index, in the order they appear in the
                index definition.

        Raises:
            Exception: If the database query fails (e.g., the index does not
                exist) or the reader‑pool connection cannot be acquired. The
                original error from the driver thread is re‑raised.

        Example:
            >>> db = Driver("mydb.sqlite3")
            >>> users = db.users
            >>> info = users.get_index_info("idx_email")
            >>> print(info['name'])
            idx_email
            >>> print(info['indexed_columns'])
            ['email']

            Using a reader‑pool connection:
            >>> info = users.get_index_info("idx_email", from_readers_pool=True)
        """
        query = (f'PRAGMA index_info({index_name});',)
        if not from_readers_pool:
            return {'name':index_name, 'indexed_columns':[i[2] for i in self._exc('qf', query)]}
        else:
            queueCallBack= SimpleQueue() 
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', query, queueCallBack])
            self.db_obj.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return {'name':index_name, 'indexed_columns':[i[2] for i in callback[1]]}
            else:
                raise Exception(callback[1])

    def bulk_insert(self, columns: list['Column'], data_list: list) -> None:
        """Inserts multiple rows into the table in a single batch operation.

        Builds a parameterized ``INSERT`` statement with placeholders for the
        specified columns and uses ``executemany`` to execute all rows at once,
        which is significantly faster than individual inserts in a loop.
        The operation runs on the writer connection and commits automatically
        on success.

        Args:
            columns (list[Column]): A list of :class:`Column` objects defining
                the columns to be populated. The order must match the values
                provided in each element of ``data_list``.
            data_list (list[list | tuple]): A list of rows, where each row is
                an iterable (e.g., list or tuple) of values corresponding to
                ``columns``. All rows must have the same number of elements.

        Returns:
            None: The method returns ``None`` after all rows have been
            successfully inserted.

        Raises:
            Exception: If the database operation fails (e.g., constraint
                violation, type mismatch, or connection error). The original
                exception from the writer thread is re‑raised.

        Example:
            Simple usage – insert two rows into the "users" table.

            >>> db = Driver("app.db")
            >>> users = db.users
            >>> users.bulk_insert(
            ...     [users.name, users.age],
            ...     [("Alice", 30), ("Bob", 25)]
            ... )

        """
        query = f'INSERT INTO {self.name_} ({', '.join(i.first_name for i in columns)}) VALUES ({', '.join('?' for i in columns)});'
        self._exc('qmb', (query, data_list))

    def bulk_update(self, update: dict['Column', Any], where: 'ColumnsOperation', data_list: list) -> None:
        """Performs a batch UPDATE of multiple rows with varying values in one transaction.

        Constructs an ``UPDATE`` statement with ``?`` placeholders and executes it using
        SQLite's ``executemany``. The ``update`` dictionary maps :class:`Column` objects
        to the new values or expressions. Literal values become ``?`` in the template;
        :class:`Column` references are used directly; :class:`ColumnsOperation`
        expressions are inserted as SQL. The ``where`` condition is built from a
        :class:`ColumnsOperation`.

        Because ``executemany`` also relies on ``?``, the method temporarily replaces all
        ``?`` in the template with :attr:`Table.PLACE_HOLDER` (default
        ``'_MY_S4ULT3D_PL4C3_H0LD3R_?_'``) to avoid interference. After building the
        query string, the placeholder is swapped back to ``?`` before execution. The
        order of values in each tuple of ``data_list`` must match the order of ``?``
        placeholders that appear in the final query (including those from the ``where``
        clause if it contains bindings).

        Args:
            update (dict[:class:`Column`, Any]): A dictionary where each key is a
                :class:`Column` to update. Values can be:
                - a literal (int, float, str, bytes, etc.) – becomes ``?``,
                - a :class:`Column` – references another column,
                - a :class:`ColumnsOperation` – an SQL expression.
            where (:class:`ColumnsOperation`): The condition selecting which rows to
                update (e.g., ``table.id == some_value``).
            data_list (list[tuple]): A list of tuples, each containing the values that
                replace all ``?`` placeholders in the generated query, in the order they
                appear. The length of each tuple must exactly match the number of ``?``
                markers.

        Returns:
            None: The updates are committed on the writer thread.

        Raises:
            Exception: If the database operation fails. A special descriptive error is
                raised when the number of bindings in a ``data_list`` element does not
                match the number of ``?`` placeholders, possibly because the literal
                string :attr:`Table.PLACE_HOLDER` appeared in the data.

        Example:
            **Simple example**: update the ``age`` column for multiple users.

            >>> db = Driver('mydb.sqlite3')
            >>> users = db.users
            >>> # Update ages: user id 1 → 30, id 2 → 25, id 3 → 35
            >>> users.bulk_update(
            ...     update={users.age: users.PLACE_HOLDER},
            ...     where=users.id == users.PLACE_HOLDER,
            ...     data_list=[
            ...         (30, 1),
            ...         (25, 2),
            ...         (35, 3)
            ...     ]
            ... )

            **Complex example**: increase salary by a bonus that varies per user, but only
            for those whose department name matches a given value.

            >>> dept = db.departments
            >>> employees = db.employees
            >>> # update: salary = salary + bonus, where department name = ?
            >>> employees.bulk_update(
            ...     update={employees.salary: employees.salary + db.PLACE_HOLDER},
            ...     where=(employees.dept_id == dept.id) & (dept.name == db.PLACE_HOLDER),
            ...     data_list=[
            ...         (100.0, 'Engineering'),
            ...         (200.0, 'Sales'),
            ...         (150.0, 'Engineering')
            ...     ]
            ... )
        """
        temp_list = []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        query_splited = f'UPDATE {self.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value, Column) else f'{key.first_name}={self.PLACE_HOLDER}' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0].replace('?', self.PLACE_HOLDER)}' for key , value in list(update.items()))} WHERE {where._output[0].replace('?', self.PLACE_HOLDER)};'.split(self.PLACE_HOLDER)
        query= query_splited[0]
        for a,i in enumerate(temp_list+where._output[1]):
            query = query +( f'"{i}"' if isinstance(i,str) and not i == self.PLACE_HOLDER else str(i))+ query_splited[a+1] #All "? || '%'" thing are because of Column.contain() method and .startswith() and .endswith() that have "%" in output value
        try:
            self._exc('qmb', (query.replace(self.PLACE_HOLDER, '?'), data_list))
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
        order_by: 'Column' = None,
        from_readers_pool: bool = False
        ) -> Any:
        """Executes a SELECT query with one or more JOIN clauses on this table.

        Builds and runs a SQL query that selects the given columns from this
        table, joining other tables as specified. Column expressions can be
        raw :class:`Column` instances or :class:`ColumnsOperation` objects
        (e.g., the result of arithmetic or string operations). The method
        automatically generates aliases to avoid name collisions.

        Args:
            columns: A list of columns to retrieve. Each element can be a
                :class:`Column` (which will be aliased as
                ``{tablename}_{columnname}``) or a :class:`ColumnsOperation`
                (the expression is used directly, aliased similarly).
            joins_list: A list of join objects created with :class:`Join.Inner`,
                :class:`Join.Left`, or :class:`Join.Right`. Each specifies the
                table and the join condition (a :class:`ColumnsOperation`).
            where: An optional :class:`ColumnsOperation` representing the
                ``WHERE`` clause. Defaults to ``None`` (no filter).
            order_by: An optional :class:`Column` by which to sort the results.
                Defaults to ``None`` (no explicit ordering).
            from_readers_pool: If ``True``, the query is executed on one of the
                reader‑pool connections, allowing concurrent reads without
                blocking the writer. Defaults to ``False`` (uses the main
                writer connection).

        Returns:
            list[tuple]: The fetched rows as tuples. Each tuple corresponds to
            the order of ``columns``. If an error occurs, an exception is
            raised rather than returning a value.

        Raises:
            Exception: If the query fails (syntax error, constraint violation,
                reader‑pool exhaustion, etc.). The original error is re‑raised.

        Examples:
            Simple join between two tables:

            >>> db = Driver("store.db")
            >>> users = db.users
            >>> orders = db.orders
            >>> # INNER JOIN users with orders on user_id
            >>> result = users.join(
            ...     columns=[users.name, orders.total],
            ...     joins_list=[Join.Inner(orders, users.id == orders.user_id)]
            ... )
            >>> for row in result:
            ...     print(row)
            ('Alice', 150.0)
            ('Bob', 200.0)

            Complex example with multiple joins, expressions, and filtering:

            >>> # Using column operations (string concatenation) and LEFT JOIN
            >>> full_name = users.first_name + ' ' + users.last_name
            >>> condition = (orders.total > 100) & (orders.status == 'active')
            >>> result = users.join(
            ...     columns=[full_name, orders.total, products.name],
            ...     joins_list=[
            ...         Join.Inner(orders, users.id == orders.user_id),
            ...         Join.Left(products, orders.product_id == products.id)
            ...     ],
            ...     where=condition,
            ...     order_by=orders.total
            ... )
            >>> for row in result:
            ...     print(row)
            ('Alice Smith', 150.0, 'Widget')
            ('Bob Johnson', 200.0, 'Gadget')
        """
        tl = []
        [tl.extend(i._output[1]) if isinstance(i,ColumnsOperation) else None for i in columns]
        [tl.extend(i._output[1]) for i in joins_list]
        query= (f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column)  else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")") else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output for i in joins_list)} {f'WHERE {where._output[0]}' if where else ''} {f'ORDER BY {order_by.name}' if order_by else ''}', tl+where._output[1]) if where else (f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column)  else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")") else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output for i in joins_list)} {f'ORDER BY {order_by.name}' if order_by else ''}', tl) if tl else (f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column)  else f'{i._output[0][1:-1] if i._output[0].startswith('(') and i._output[0].endswith(')') else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output for i in joins_list)} {f'ORDER BY {order_by.name}' if order_by else ''}',)
        # The above line is approximately 1000 characters, which is not standard, but it is written this way
        # to improve performance in the Driver class and to avoid checking whether the second item in the query
        # is an empty list for each input.
        if not from_readers_pool:
            return self._exc('qf', query)
        else:
            queueCallBack= SimpleQueue()
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', query, queueCallBack])
            self.db_obj.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return callback[1]
            else:
                raise Exception(callback[1])

