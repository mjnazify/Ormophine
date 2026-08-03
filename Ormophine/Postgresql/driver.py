from . import TableStructure, Table
from psycopg  import connect, OperationalError, ProgrammingError
from queue import SimpleQueue, Empty
from typing import Literal

            
class Driver():
    """High-level PostgreSQL driver for Ormophine.

    The driver is the main entry point for working with PostgreSQL databases.
    It manages connection pooling, auto-discovers existing tables, and exposes
    table objects directly as attributes on the driver instance. It also provides
    a Pythonic API for CRUD operations, joins, batch transactions, and schema
    management.

    The PostgreSQL implementation follows the same public approach as the other
    backends: applications import the public symbols from the package root and
    work with the returned table objects and schema helpers.

    Parameters
    ----------
    host : str
        Database server host.
    port : int
        Port number.
    username : str
        Database user name.
    password : str
        Database password.
    db_name : str
        Database name.
    create_new_db : bool, optional
        If ``True``, attempt to create the database before connecting.
    pool_size : int, optional
        Number of pooled connections. Defaults to ``5``.
    connect_timeout : int, optional
        Connection timeout in seconds. Defaults to ``10``.
    client_encoding : str, optional
        Connection encoding. Defaults to ``"UTF8"``.
    collate : str or None, optional
        Collation used when creating a new database.
    isolation_level : str, optional
        Transaction isolation level. One of ``'READ UNCOMMITTED'``,
        ``'READ COMMITTED'``, ``'REPEATABLE READ'``, or
        ``'SERIALIZABLE'``.

    Example
    -------
    >>> from Ormophine.Postgresql import Driver, DataTypes, TableStructure
    >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
    >>> users = driver.users
    >>> structure = TableStructure("products")
    >>> structure.add_column("id", DataTypes.SERIAL(), primary_key=True)
    >>> structure.add_column("name", DataTypes.VARCHAR(100))
    >>> driver.create_table(structure)
    >>> driver.products.insert({driver.products.name: "Widget"})
    >>> driver.disconnect()
    """
    PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
    CHARSET = Literal[
    "UTF8",
    "LATIN1",
    "SQL_ASCII",
    "WIN1252",
    "WIN1256",
    "KOI8R",
    "ISO_8859_5",
    "ISO_8859_6",
    "ISO_8859_7",
    "ISO_8859_8",
    "EUC_JP",
    "EUC_KR",
    "EUC_CN",
    "EUC_TW",
    "GB18030",
    "GBK",
    "BIG5",
    "SHIFT_JIS_2004",
    "UHC",
    "JOHAB"
    ]
    COLLATE = Literal[
    "en_US.UTF-8",
    "de_DE.UTF-8",
    "fr_FR.UTF-8",
    "fa_IR.UTF-8",
    "C",
    "POSIX"
    ]
    ISOLATION_LEVEL = Literal['READ UNCOMMITTED', 'READ COMMITTED', 'REPEATABLE READ', 'SERIALIZABLE']
    PRIVILEGES = Literal['ALL PRIVILEGES', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER', 'CREATE', 'CONNECT', 'TEMPORARY', 'EXECUTE', 'USAGE']

    def __init__(self, host: str, port: int, username: str, password: str, db_name: str, create_new_db: bool = False, pool_size: int = 5, connect_timeout: int = 10, client_encoding: CHARSET = "UTF8", collate: COLLATE = None, isolation_level: ISOLATION_LEVEL = 'READ COMMITTED'):
        """Initializes a PostgreSQL driver with a connection pool and table reflection.

        Creates a pool of database connections using `psycopg` and reflects all
        user tables in the current schema as :class:`Table` attributes on the
        driver instance. Optionally creates the target database if it does not
        yet exist. Connection settings (host, port, credentials, encoding,
        collation, timeout, and transaction isolation) are stored for pool
        management and automatic reconnection on transient failures.

        Args:
            host (str): PostgreSQL server hostname or IP address.
            port (int): Port number (usually 5432).
            username (str): Database user name.
            password (str): User password.
            db_name (str): Name of the database to connect to (or to create).
            create_new_db (bool): If ``True``, the driver first connects to the
                ``postgres`` maintenance database and executes ``CREATE DATABASE``
                with the given encoding and optional collation, then connects to
                the newly created database. Defaults to ``False``.
            pool_size (int): Number of persistent connections maintained in the
                pool. Defaults to ``5``.
            connect_timeout (int): Maximum time in seconds to wait for a new
                connection. Defaults to ``10``.
            client_encoding (CHARSET): PostgreSQL encoding, e.g. ``"UTF8"``,
                ``"LATIN1"``. Defaults to ``"UTF8"``.
            collate (COLLATE): Collation and character type (LC_COLLATE,
                LC_CTYPE) used when creating a new database, e.g.
                ``"en_US.UTF-8"``. Only meaningful when ``create_new_db=True``.
                Defaults to ``None``.
            isolation_level (ISOLATION_LEVEL): Transaction isolation level for
                all sessions in the pool. Must be one of ``'READ UNCOMMITTED'``,
                ``'READ COMMITTED'``, ``'REPEATABLE READ'``, or
                ``'SERIALIZABLE'``. Defaults to ``'READ COMMITTED'``.

        Returns:
            None

        Raises:
            Exception: If a connection to the given database (or to
                ``postgres`` when creating a new database) fails.
            RuntimeError: If attempting to create new connections after
                :meth:`disconnect` has been called.

        Example:
            Connect to an existing database:

            >>> db = Driver(
            ...     host='127.0.0.1',
            ...     port=5432,
            ...     username='postgres',
            ...     password='secret',
            ...     db_name='my_db',
            ...     pool_size=10
            ... )
            >>> # Access tables as attributes
            >>> users = db.users  # Table object

            Create a new database and connect:

            >>> db = Driver(
            ...     host='127.0.0.1',
            ...     port=5432,
            ...     username='postgres',
            ...     password='secret',
            ...     db_name='new_database',
            ...     create_new_db=True,
            ...     client_encoding='UTF8',
            ...     collate='en_US.UTF-8'
            ... )
        """
        self.CONNECTION_ERRORS = ('08003', '08006', '08001', '57P01', '57P02', '57P03', '53300', '53000')
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
        self.host = host
        self.port = port
        self._connected = True
        self.username = username
        self.password = password
        self.db_name = db_name
        self.client_encoding = client_encoding
        self.collate = collate
        self.connect_timeout = connect_timeout
        self.isolation_level = isolation_level
        self.config = {
            "host": self.host,
            "port": self.port,
            "user": self.username,
            "password": self.password,
            "dbname": self.db_name,
            "client_encoding": self.client_encoding,
            "connect_timeout": self.connect_timeout
        }
        self.connection_pool = SimpleQueue()
        self.connection_pool_storage = []
        conf = {
            "host": self.host,
            "port": self.port,
            "user": self.username,
            "password": self.password,
            "client_encoding": self.client_encoding,
            "connect_timeout": self.connect_timeout
        }
        if not create_new_db:
            try:
                connection = connect(**self.config)
                connection.close()
            except Exception as e:
                if 'connection' in locals():
                    connection.close()
                raise            
        else:
            try:
                connection = connect(**conf, dbname='postgres')
                connection.autocommit = True
                cur = connection.cursor()
                query = f"CREATE DATABASE {self.db_name} ENCODING '{self.client_encoding}'"
                if self.collate:
                    query += f" LC_COLLATE = '{self.collate}' LC_CTYPE = '{self.collate}'"
                cur.execute(query)
                connection.close()
            except Exception:
                connection.close()
                raise                

        [self._create_connection() for _ in range(pool_size)]

        for i in self.get_tables():
            self.__setattr__(i, Table(self, i))

    def _create_connection(self):
        """Create a new database connection and add it to the connection pool.

        This internal method establishes a fresh connection to the PostgreSQL
        database using the configuration stored in :attr:`config`. It also
        opens a cursor, appends the connection to
        :attr:`connection_pool_storage`, puts the (connection, cursor) tuple
        into :attr:`connection_pool`, and immediately sets the session
        transaction isolation level to :attr:`isolation_level`.

        If an :class:`OperationalError` is raised during connection and its
        ``sqlstate`` is one of the transient error codes listed in
        :attr:`CONNECTION_ERRORS`, the method retries once before giving up.
        All other exceptions (including non‑transient
        :class:`OperationalError`) are re‑raised.

        Args:
            None (``self`` only).

        Returns:
            None: The connection is placed in the pool; nothing is returned.

        Raises:
            RuntimeError: If :attr:`_connected` is ``False``, meaning the
                driver has been disconnected and no new connections can be
                created.
            OperationalError: If the connection attempt fails with a
                non‑transient error code, or if the retry also fails.

        Example:
            Typically called automatically when the pool is exhausted:

            >>> # Inside the driver, after checking pool:
            >>> self._create_connection()
            >>> # Now pool has one more (connection, cursor) pair.
        """
        if not self._connected:
            raise RuntimeError('You have closed the connection, you can not create new connections')
        try:
            con = connect(**self.config)
            cur = con.cursor()
            self.connection_pool.put((con, cur))
            self.connection_pool_storage.append(con)
            cur.execute(f"SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL {self.isolation_level};")
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:  
                con = connect(**self.config)
                cur = con.cursor()
                self.connection_pool.put((con, cur))
                self.connection_pool_storage.append(con)
                cur.execute(f"SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL {self.isolation_level};")
            else:
                raise

    def _get_connection(self):
        """Retrieves a database connection and cursor from the connection pool.

        This internal method attempts to obtain a (connection, cursor) tuple
        from the thread‑safe :attr:`connection_pool` queue. If the pool is
        empty, a new connection is created via :meth:`_create_connection` and
        a second attempt is made. The method blocks for up to 0.5 seconds on
        each queue retrieval.

        Returns:
            tuple: A ``(psycopg.connection, psycopg.cursor)`` pair that can
            be used to execute queries. The connection's transaction isolation
            level is already set.

        Raises:
            Exception: If the connection pool remains empty even after
                attempting to create a new connection. The exception message
                suggests increasing the ``pool_size``.
        """
        try:
            return self.connection_pool.get(block=True, timeout=0.5)
        except Empty:
            self._create_connection()
            try:
                return self.connection_pool.get(block=True, timeout=0.5)
            except Empty as e:
                raise Exception(f'{e}\n\nEmpty connection pool, you better increase `pool_size`')#TODO Create get_schema() from table and db and column 

    def _excfp(self, query, params):
        """Execute a parameterized query, fetch all results, and return them.

        This internal method acquires a connection and cursor from the
        connection pool, executes the given SQL query with the provided
        parameters, fetches all rows, and then returns the result set after
        committing the transaction and releasing the connection back to the
        pool. If a connection-level error (e.g., broken connection) is
        detected, the method attempts to recover by discarding the broken
        connection and retrying the operation once with a newly created
        connection. In case of a programming error, the transaction is
        rolled back before re‑raising. 

        Args:
            query (str): The SQL statement to execute. Placeholders must be
                ``%s`` style (as used by ``psycopg``).
            params (tuple | list): The parameter values to substitute into
                the query. Can be ``None`` if the query has no placeholders
                (though :meth:`_excf` is preferred in that case).

        Returns:
            list[tuple]: The list of rows returned by the query, where each
            row is a tuple of column values in the order specified by the
            ``SELECT`` clause.

        Raises:
            Exception: If the query fails due to an operational error
                (including after a retry) or a programming error. The
                exception message includes the original error, the query,
                and the parameters for debugging.

        Example:
            >>> # Internal usage: fetch column info for a table
            >>> query = "SELECT column_name FROM information_schema.columns WHERE table_name = %s"
            >>> result = db._excfp(query, ('users',))
            >>> print(result)
            [('id',), ('name',), ('email',)]
        """
        con, cur = self._get_connection()
        try:
            cur.execute(query, params)
            res = cur.fetchall()
            con.commit()
            self.connection_pool.put((con, cur))
            return res
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.execute(query, params)
                    res = cur.fetchall()
                    con.commit()
                    self.connection_pool.put((con, cur))
                    return res
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')

    def _excf(self, query):
        """Execute a parameterless query and return all fetched rows.

        Obtains a connection and cursor from the internal connection pool,
        runs the SQL statement, fetches the complete result set, commits
        (if successful), and returns the data. The connection is always
        returned to the pool afterwards. When the connection is broken
        (e.g., due to a server restart), it transparently replaces the
        connection and retries the query once. If the error is a client-side
        programming mistake, a rollback is issued before re-raising.

        Args:
            query (str): The SQL query string to be executed. Must not contain
                parameters; use :meth:`_excfp` for parameterised queries.

        Returns:
            list[tuple]: A list of tuples, where each tuple represents a row.
            The order of values in each tuple corresponds to the columns in
            the ``SELECT`` list.

        Raises:
            Exception: If an :class:`OperationalError` or
                :class:`ProgrammingError` occurs. The exception message
                includes the original error and the failing query for
                debugging.

        Example:
            This method is normally called internally by higher-level APIs,
            but can be used directly for custom raw queries:

            >>> db = Driver(...)
            >>> rows = db._excf("SELECT * FROM users WHERE active = true;")
            >>> for row in rows:
            ...     print(row)
        """
        con, cur = self._get_connection()
        try:
            cur.execute(query)
            res = cur.fetchall()
            con.commit()
            self.connection_pool.put((con, cur))
            return res
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.execute(query)
                    res = cur.fetchall()
                    con.commit()
                    self.connection_pool.put((con, cur))
                    return res
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                raise Exception(f'{e}\nQuery:\n\t{query}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}')

    def _excp(self, query, params):
        """Executes a parameterized query and commits the transaction immediately.

        This method obtains a connection from the driver's pool, executes the
        given SQL statement with the provided parameters, and commits the
        changes. If a connection error occurs (e.g., server restart), it
        discards the broken connection, acquires a new one, and retries the
        operation once. For other errors, the transaction is rolled back and
        a descriptive exception is raised. The connection is always returned
        to the pool after use (or after a failure cleanup).

        Args:
            query (str): The SQL statement to execute (e.g., ``INSERT``,
                ``UPDATE``, ``DELETE``). Use ``%s`` placeholders for parameters.
            params (tuple | list | None): The parameter values to bind to the
                query. Can be ``None`` if the query has no placeholders.

        Returns:
            None

        Raises:
            Exception: If the query fails due to a programming error (e.g.,
                invalid syntax, missing table) or a non-retryable operational
                error, the original exception is wrapped with the query text
                and parameters for debugging. Fatal connection errors are
                re-raised after a retry attempt.

        Example:
            >>> driver._excp(
            ...     "INSERT INTO users (name, age) VALUES (%s, %s)",
            ...     ("Alice", 30)
            ... )
        """
        con, cur = self._get_connection()
        try:
            cur.execute(query, params)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.execute(query, params)
                    con.commit()
                    self.connection_pool.put((con, cur))
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')

    def _exc(self, query):
        """Executes a SQL command without parameters and commits immediately.

        This internal helper obtains a connection from the driver's connection pool,
        executes the given query, and commits the transaction. If a recoverable
        connection error occurs (e.g., server restart), it discards the broken
        connection, creates a new one, and retries the operation once. For
        non-recoverable operational errors or programming mistakes, the transaction
        is rolled back and a descriptive exception is raised. The connection is
        always returned to the pool after use (or after a failure cleanup).

        Args:
            query (str): The SQL statement to execute. It should not contain
                placeholders; for parameterized queries use :meth:`_excp`.

        Returns:
            None

        Raises:
            Exception: If the query fails due to a programming error (e.g.,
                invalid syntax, missing table) or a non-retryable operational
                error, the original exception is wrapped with the query text
                for debugging. Fatal connection errors are re-raised after a
                retry attempt.

        Example:
            >>> driver._exc("DROP TABLE users;")
        """
        con, cur = self._get_connection()
        try:
            cur.execute(query)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.execute(query)
                    con.commit()
                    self.connection_pool.put((con, cur))
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                raise Exception(f'{e}\nQuery:\n\t{query}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}')

    def _excs(self, query_params: list):
        """Executes a batch of SQL statements within a single transaction.

        Iterates over a list of query specifications. Each item can be a plain
        SQL string (executed directly) or a two-element list/tuple ``[query,
        params]`` for parameterized execution. All statements are run on a
        single connection obtained from the driver's pool. If a connection‑loss
        error is detected, the broken connection is discarded, a new one is
        acquired, and the entire batch is retried once. For other operational
        or programming errors, the transaction is rolled back and a descriptive
        exception is raised, including the list of queries and their parameters.

        Args:
            query_params (list[tuple | str]): A list of query specifications.
                Each element may be:
                - a string containing the SQL statement, or
                - a list/tuple of exactly two elements: ``[query_string,
                params]``, where ``params`` is a tuple or list of parameter
                values to be passed to the driver's parameter substitution
                (``%s`` placeholders).

        Returns:
            None

        Raises:
            Exception: If any statement fails due to a programming error
                (e.g., invalid SQL) or a non‑retryable operational error. The
                exception message includes the original error and a summary of
                all queries and parameters. Fatal connection errors are
                re‑raised after a retry attempt.

        Example:
            >>> driver._excs([
            ...     "INSERT INTO log (msg) VALUES ('start')",
            ...     ["UPDATE users SET age = %s WHERE name = %s", (30, "Alice")]
            ... ])
        """
        con, cur = self._get_connection()
        try:
            for q in query_params:
                if len(q) == 2:
                    cur.execute(q[0], q[1])
                else:
                    cur.execute(q[0])
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    for q in query_params:
                        if len(q) == 2:
                            cur.execute(q[0], q[1])
                        else:
                            cur.execute(q[0])
                    con.commit()
                    self.connection_pool.put((con, cur))
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                queries_str = '\n'.join([f'Query: {q[0]}\nParams: {q[1] if len(q)>1 else ""}' for q in query_params])
                raise Exception(f'{e}\n{queries_str}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            queries_str = '\n'.join([f'Query: {q[0]}\nParams: {q[1] if len(q)>1 else ""}' for q in query_params])
            raise Exception(f'{e}\n{queries_str}')

    def _excm(self, query, params):
        """Executes a parameterized SQL statement with multiple rows using ``executemany``.

        Retrieves a connection from the driver's pool, runs the given query once
        for each element in ``params`` via the cursor's ``executemany`` method,
        and commits the transaction. If a connection error occurs (e.g., server
        restart), it discards the broken connection, acquires a new one, and
        retries the operation once. For other errors, the transaction is rolled
        back and a descriptive exception is raised. The connection is always
        returned to the pool after use.

        Args:
            query (str): The SQL statement to execute. Use ``%s`` placeholders
                for parameters.
            params (list[tuple] | list[list]): A sequence of parameter groups,
                where each group provides the values for the ``%s`` placeholders
                in one execution.

        Returns:
            None

        Raises:
            Exception: If the query fails due to a programming error (e.g.,
                invalid syntax, missing table) or a non-retryable operational
                error, the original exception is wrapped with the query text
                and parameters for debugging. Fatal connection errors are
                re-raised after a retry attempt.

        Example:
            >>> driver._excm(
            ...     "INSERT INTO users (name, age) VALUES (%s, %s)",
            ...     [("Alice", 30), ("Bob", 25), ("Charlie", 35)]
            ... )
        """
        con, cur = self._get_connection()
        
        try:
            cur.executemany(query, params)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.executemany(query, params)
                    con.commit()
                    self.connection_pool.put((con, cur))
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')

    def _handle_broken_connection(self, con):
        """Closes a broken connection, removes it from the pool, and creates a fresh one.

        This internal method is called when a database operation fails with a
        connection‑error SQLSTATE (e.g., ``08003``, ``08006``). It attempts to
        close the faulty connection safely, removes it from the driver's
        internal storage list, and then delegates to
        :meth:`_create_connection` to add a new, healthy connection to the pool.

        Args:
            con (psycopg.Connection): The broken database connection to be
                discarded.

        Returns:
            None

        Raises:
            OperationalError: Propagated from :meth:`_create_connection` if
                establishing a replacement connection fails.

        Example:
            >>> # Internally, after catching an OperationalError with
            >>> # a connection‑error SQLSTATE:
            >>> except OperationalError as e:
            ...     if e.sqlstate in self.CONNECTION_ERRORS:
            ...         self._handle_broken_connection(con)
            ...         con, cur = self._get_connection()
        """
        try:
            con.close()
        except:
            pass
        if con in self.connection_pool_storage:
            self.connection_pool_storage.remove(con)
        self._create_connection()

    def delete_table(self, table: Table, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool):
        """Drops a table from the database and removes it from the driver instance.

        Executes the ``DROP TABLE`` statement for the given :class:`Table` object.
        The operation is gated by three explicit confirmation flags that must all be
        ``True`` to proceed, preventing accidental deletion. After successful
        execution, the corresponding attribute on the :class:`Driver` instance is
        deleted, so any subsequent access will raise an ``AttributeError``.

        Args:
            table (:class:`Table`): The table object to be dropped. Must exist in
                the database and be an attribute of this :class:`Driver`.
            are_you_sure (bool): First confirmation flag.
            are_you_really_sure (bool): Second confirmation flag.
            for_sure (bool): Third confirmation flag. All three must be ``True``
                to execute the deletion.

        Returns:
            None

        Raises:
            Exception: If the ``DROP TABLE`` statement fails (e.g., table does
                not exist, insufficient privileges, or connection error). The
                original error is re‑raised with query details.

        Example:
            >>> db = Driver(host='localhost', port=5432, username='user',
            ...             password='pass', db_name='mydb')
            >>> users = db.users  # existing Table object
            >>> db.delete_table(users, are_you_sure=True,
            ...                 are_you_really_sure=True, for_sure=True)
            >>> # Accessing db.users now raises AttributeError
        """
        if are_you_sure and are_you_really_sure and for_sure:
            self._exc(f'DROP TABLE {table.name_};')
            self.__delattr__(table.name_.strip('"'))

    def delete_database(self, database_name: str, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool):
        """Drops an entire PostgreSQL database.

        This method deletes the specified database from the server. Because
        ``DROP DATABASE`` cannot execute inside a transaction block, the
        connection's autocommit mode is temporarily enabled for the duration
        of the command. The operation is gated by three explicit boolean
        flags that must all be ``True`` to proceed – a safety mechanism to
        prevent accidental database deletion. If any flag is ``False``, the
        method silently returns without performing any action.

        Args:
            database_name (str): The name of the database to drop.
            are_you_sure (bool): First confirmation flag.
            are_you_really_sure (bool): Second confirmation flag.
            for_sure (bool): Third confirmation flag. All three must be
                ``True`` for the deletion to execute.

        Returns:
            None: The database is dropped if all confirmation flags are
            ``True``; otherwise, the method returns immediately.

        Raises:
            Exception: If the ``DROP DATABASE`` command fails (e.g.,
                database does not exist or there are active connections).
                The original exception from the database driver is re‑raised
                after resetting autocommit.

        Example:
            >>> driver = Driver("localhost", 5432, "postgres", "secret", "mydb")
            >>> # Drop the database "old_project" with triple confirmation
            >>> driver.delete_database(
            ...     "old_project",
            ...     are_you_sure=True,
            ...     are_you_really_sure=True,
            ...     for_sure=True
            ... )
        """
        if are_you_sure and are_you_really_sure and for_sure:
            con, cur = self._get_connection()
            try:
                con.autocommit = True
                cur.execute(f'DROP DATABASE "{database_name}";')
                con.autocommit = False
                self.connection_pool.put((con, cur))
            except Exception:
                con.autocommit = False
                self.connection_pool.put((con, cur))
                raise
            
    def custom_execute_with_fetch(self, query, params=None):
        """Executes a raw SQL query and returns the fetched results.

        This method provides direct access to the database for custom
        ``SELECT`` or other read‑only queries. It automatically obtains a
        connection from the pool, executes the query, fetches all rows, and
        returns them. If a connection error occurs (e.g., server restart), it
        discards the broken connection, acquires a new one, and retries once.
        For other errors, the transaction is rolled back and a descriptive
        exception is raised, including the query text and parameters.

        Args:
            query (str): The SQL statement to execute. Use ``%s``
                placeholders for parameters.
            params (tuple | list | None): Parameter values to bind into the
                query. If ``None``, the query is executed without parameters.

        Returns:
            list[tuple]: A list of tuples, where each tuple represents a row
            of the result set. If the query returns no rows, an empty list is
            returned.

        Raises:
            Exception: If the query fails due to a programming error (e.g.,
                invalid syntax, missing table) or a non‑retryable operational
                error. The exception message includes the query text and
                parameters for debugging.

        Example:
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> rows = driver.custom_execute_with_fetch(
            ...     "SELECT id, name FROM users WHERE age > %s",
            ...     (25,)
            ... )
            >>> for row in rows:
            ...     print(row)
            (1, 'Alice')
            (2, 'Bob')
        """
        return self._excfp(query, params) if params else self._excf(query)

    def custom_execute(self, query, params=None):
        """Executes an arbitrary SQL statement with optional parameters and commits.

        This is a convenience method that wraps the driver's internal execution
        functions. If ``params`` is provided, the statement is executed with
        parameterized placeholders (``%s``) via :meth:`_excp`. Otherwise, the
        raw statement is executed via :meth:`_exc`. The transaction is
        committed immediately upon success. Connection errors are automatically
        retried once with a fresh connection.

        Args:
            query (str): The SQL statement to execute (e.g., ``INSERT``,
                ``UPDATE``, ``DELETE``, or any DDL/DML). Use ``%s``
                placeholders for parameters.
            params (tuple | list | None): The parameter values to bind to the
                query. Defaults to ``None`` for statements without parameters.

        Returns:
            None

        Raises:
            Exception: If the query fails due to a programming error (e.g.,
                invalid syntax, missing table) or a non‑retryable operational
                error. The exception message includes the original error,
                the query text, and the parameters (if any) for debugging.

        Example:
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> # Execute a parameterized INSERT
            >>> driver.custom_execute(
            ...     "INSERT INTO employees (name, salary) VALUES (%s, %s)",
            ...     ("Jane Doe", 75000)
            ... )
            >>> # Execute a DDL statement without parameters
            >>> driver.custom_execute("CREATE INDEX idx_name ON employees (name);")
        """
        return self._excp(query, params) if params else self._exc(query)

    def custom_execute_many(self, query: str, params: list) -> None:
        """Executes a SQL statement multiple times with different parameter sets.

        This is a convenience wrapper around :meth:`_excm` that uses the driver's
        connection pool to run a parameterized query with ``executemany``.
        It is suitable for bulk ``INSERT``, ``UPDATE``, or ``DELETE``
        operations where the same SQL template is executed with multiple
        parameter tuples. The operation is performed atomically on a single
        connection and commits after all statements have been processed.

        Args:
            query (str): The SQL template to execute. Use ``%s`` placeholders
                for parameters.
            params (list[tuple]): A list of parameter tuples, where each
                tuple contains the values to bind for one execution of the
                query. Each tuple must have the same length and order as the
                ``%s`` placeholders in the query.

        Returns:
            None: The method returns after the batch has been committed
            successfully.

        Raises:
            Exception: If the execution fails (e.g., connection error,
                programming error). The original ``psycopg`` error is wrapped
                with the query text and parameters for debugging. In case of
                connection errors, a retry attempt is made automatically.

        Example:
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> # Insert multiple rows into the 'users' table
            >>> query = "INSERT INTO users (name, age) VALUES (%s, %s)"
            >>> data = [("Alice", 30), ("Bob", 25), ("Charlie", 35)]
            >>> driver.custom_execute_many(query, data)
        """
        return self._excm(query, params)

    def get_databases(self):
        """Retrieves a list of all user databases on the PostgreSQL server.

        Queries the ``pg_database`` system catalog, filtering out template
        databases (e.g., ``template0``, ``template1``). The result is a list
        of database names available to the current user.

        Returns:
            list[str]: A list of database names as strings. Only non‑template
            databases are included.

        Raises:
            Exception: If the underlying query fails (e.g., connection
                loss or permission error). The original exception from
                :meth:`_excf` is propagated.

        Example:
            >>> driver = Driver("localhost", 5432, "postgres", "secret", "mydb")
            >>> dbs = driver.get_databases()
            >>> print(dbs)
            ['mydb', 'testdb', 'analytics']
        """
        return [i[0] for i in self._excf('SELECT datname FROM pg_database WHERE datistemplate = false;')]

    def get_tables(self):
        """Retrieves the names of all tables in the current schema.

        Queries the PostgreSQL system catalog to obtain a list of table names
        that exist in the schema associated with the current connection's
        search path (typically ``public``). The result excludes system tables
        and views.

        Returns:
            list[str]: A list of table name strings, ordered arbitrarily by
            the database. An empty list is returned if no tables exist.

        Example:
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> tables = driver.get_tables()
            >>> print(tables)
            ['employees', 'departments', 'projects']
        """
        return [i[0] for i in self._excf("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = current_schema();")]
    
    def create_table(self, table_structure: TableStructure):
        """Creates a new table in the database from a :class:`TableStructure` definition.

        Executes the SQL ``CREATE TABLE`` statement generated by
        :meth:`TableStructure.get_structure` and then attaches a :class:`Table`
        object as an attribute of the driver instance, using the table name
        (without quotes) as the attribute name. This allows direct access to the
        table via ``driver.table_name``.

        Args:
            table_structure (:class:`TableStructure`): A populated table
                structure object that defines columns, constraints, and
                foreign keys. Must have at least one column added via
                :meth:`~TableStructure.add_column`.

        Returns:
            None: The method does not return a value. After successful
            execution, the table can be accessed as an attribute of the
            :class:`Driver` instance (e.g., ``driver.mytable``).

        Raises:
            Exception: If the ``CREATE TABLE`` statement fails (e.g., table
                already exists, invalid column definition, or database
                connection error). The original database error is wrapped
                and re‑raised.

        Example:
            >>> from ormophine.Postgresql import Driver, DataTypes, TableStructure
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> structure = TableStructure("employees")
            >>> structure.add_column("id", DataTypes.SERIAL(), primary_key=True)
            >>> structure.add_column("name", DataTypes.VARCHAR(100), not_null=True)
            >>> structure.add_column("salary", DataTypes.NUMERIC(10, 2))
            >>> driver.create_table(structure)
            >>> # Now the table is available as driver.employees
            >>> employees_table = driver.employees
            >>> employees_table.insert({employees_table.name: "Alice",
            ...                          employees_table.salary: 75000.00})
        """
        self._exc(table_structure.get_structure())
        self.__setattr__(table_structure.name.strip('"'), Table(self, table_structure.name.strip('"')))

    def optimize(self):
        """Performs maintenance on all user tables to reclaim storage and update statistics.

        Runs ``VACUUM (ANALYZE)`` on every table in the current schema. This
        cleans up dead rows, reclaims disk space, and refreshes the query planner
        statistics, which can significantly improve performance after large
        inserts, updates, or deletes. The operation temporarily enables
        autocommit on a connection from the pool because ``VACUUM`` cannot run
        inside a transaction block. The connection is returned to the pool after
        completion, even if an error occurs.

        Returns:
            None: The method returns after all tables have been vacuumed and
            analyzed.

        Raises:
            Exception: If any ``VACUUM (ANALYZE)`` command fails (e.g.,
                insufficient privileges or a table that cannot be vacuumed).
                The original database error is re‑raised after resetting
                autocommit and returning the connection.

        Example:
            >>> driver = Driver("localhost", 5432, "user", "pass", "mydb")
            >>> # After bulk data changes, run maintenance
            >>> driver.optimize()
        """
        tables = self.get_tables()
        con, cur = self._get_connection()
        try:
            con.autocommit = True
            for i in tables:
                cur.execute(f'VACUUM (ANALYZE) "{i}";')
            con.autocommit = False
            self.connection_pool.put((con, cur))
        except Exception:
            con.autocommit = False
            self.connection_pool.put((con, cur))
            raise

    def create_user(self, username: str, password: str):
        """Creates a new PostgreSQL user (role) with a login password.

        Executes a ``CREATE USER`` statement to add a new database user.
        The username is escaped to prevent SQL injection (double quotes within
        the username are replaced with ``""``). The password is provided in
        plain text and will be stored encrypted by PostgreSQL.

        Args:
            username (str): The name of the user to create. Must be a valid
                PostgreSQL identifier. Double quotes in the name are escaped
                automatically.
            password (str): The password for the user. It will be passed as
                a literal string in the SQL statement.

        Returns:
            None: The method returns ``None`` after the user is created.

        Raises:
            Exception: If the ``CREATE USER`` command fails (e.g., the user
                already exists or the connection is broken). The original
                database error is wrapped and re‑raised.

        Example:
            >>> driver = Driver("localhost", 5432, "admin", "secret", "mydb")
            >>> # Create a new user 'john_doe' with password 's3cur3!'
            >>> driver.create_user("john_doe", "s3cur3!")
        """
        query = f"CREATE USER \"{username.replace('\"', '\"\"')}\" WITH PASSWORD '{password}';"
        self._exc(query)

    def drop_user(self, username: str):
        """Drops (deletes) a PostgreSQL user/role.

        Executes a ``DROP USER`` statement for the given username. The username
        is safely escaped by doubling any embedded double quotes before being
        placed in the SQL command. The operation is performed on a connection
        from the driver's pool and committed immediately.

        Args:
            username (str): The name of the user/role to drop. Double quotes
                inside the name are escaped automatically.

        Returns:
            None

        Raises:
            Exception: If the ``DROP USER`` command fails (e.g., the user
                does not exist, or the current user lacks privileges). The
                original database error is wrapped and re‑raised.

        Example:
            >>> driver = Driver("localhost", 5432, "postgres", "secret", "mydb")
            >>> driver.drop_user("app_user")
        """
        query = f'DROP USER "{username.replace('"', '""')}";'
        self._exc(query)

    def change_password(self, username: str, new_password: str):
        """Changes the password for a PostgreSQL user.

        Executes an ``ALTER USER ... WITH PASSWORD`` SQL statement to set
        the new password for the specified database user. The username is
        escaped to prevent double‑quote injection, and the new password is
        passed directly into the command string. No confirmation flags are
        required.

        Args:
            username (str): The name of the existing database user whose
                password should be changed.
            new_password (str): The new plain‑text password to assign. Note
                that the password is interpolated into the SQL command; any
                single quotes in the password will cause a syntax error and
                should be avoided or escaped externally.

        Returns:
            None: The operation is committed immediately on the database.

        Raises:
            Exception: If the ``ALTER USER`` command fails (e.g., the user
                does not exist, insufficient permissions, or an invalid
                password syntax). The original database error is wrapped
                and re‑raised.

        Example:
            >>> driver = Driver("localhost", 5432, "admin", "secret", "mydb")
            >>> # Change password for user 'alice'
            >>> driver.change_password("alice", "new_secure_password")
        """
        query = f"ALTER USER \"{username.replace('\"', '\"\"')}\" WITH PASSWORD '{new_password}';"
        self._exc(query)

    def rename_user(self, old_username: str, new_username: str):
        """Renames a PostgreSQL user (role).

        Executes the ``ALTER USER ... RENAME TO ...`` command to change the
        name of an existing database user. The usernames are safely quoted
        and any embedded double quotes are escaped to prevent SQL injection.

        Args:
            old_username (str): The current name of the user to rename.
            new_username (str): The new name to assign to the user.

        Returns:
            None: The method does not return a value. The user is renamed
            immediately.

        Raises:
            Exception: If the ``ALTER USER`` command fails (e.g., the old user
                does not exist, the new name is already taken, or the caller
                lacks sufficient privileges). The original database error is
                wrapped and re‑raised.

        Example:
            >>> driver = Driver("localhost", 5432, "postgres", "secret", "mydb")
            >>> driver.rename_user("john_doe", "jane_doe")
        """
        query = f'ALTER USER "{old_username.replace('"', '""')}" RENAME TO "{new_username.replace('"', '""')}";'
        self._exc(query)

    def grant_privileges(self, username: str, privileges: PRIVILEGES, database: str, table: str = '*'):
        """Grants database or table privileges to a user.

        Executes the appropriate SQL ``GRANT`` statement to assign the specified
        privileges to the given user on either an entire database or a specific
        table. If ``table`` is ``'*'`` (the default), the privileges are granted
        at the database level; otherwise, they are granted on the specified table.

        Args:
            username (str): The name of the database user receiving the privileges.
            privileges (PRIVILEGES): One of the predefined privilege strings,
                e.g., ``'SELECT'``, ``'INSERT'``, ``'ALL PRIVILEGES'``. The
                allowed values are defined in the :class:`Driver` class attribute
                ``PRIVILEGES``.
            database (str): The name of the database on which to grant privileges.
            table (str): The table name for table‑level grants. Defaults to
                ``'*'``, which grants database‑wide privileges.

        Returns:
            None

        Raises:
            Exception: If the ``GRANT`` statement fails (e.g., insufficient
                privileges or invalid username), the original database error
                is re‑raised.

        Example:
            >>> driver = Driver("localhost", 5432, "admin", "secret", "mydb")
            >>> # Grant SELECT and INSERT on the entire database
            >>> driver.grant_privileges("alice", "SELECT, INSERT", "mydb")
            >>> # Grant ALL PRIVILEGES on a specific table
            >>> driver.grant_privileges(
            ...     "bob", "ALL PRIVILEGES", "mydb", table="employees"
            ... )
        """
        if table == '*':
            query = f'GRANT {privileges} ON DATABASE "{database}" TO "{username}";'
        else:
            query = f'GRANT {privileges} ON TABLE "{database}"."{table}" TO "{username}";'
        self._exc(query)

    def revoke_privileges(self, username: str, privileges: PRIVILEGES, database: str, table: str = '*'):
        """Revokes database or table privileges from a user.

        Executes the appropriate SQL ``REVOKE`` statement to remove the specified
        privileges from the given user on either an entire database or a specific
        table. If ``table`` is ``'*'`` (the default), the privileges are revoked
        at the database level; otherwise, they are revoked on the specified table.

        Args:
            username (str): The name of the database user whose privileges are
                being revoked.
            privileges (PRIVILEGES): One of the predefined privilege strings,
                e.g., ``'SELECT'``, ``'INSERT'``, ``'ALL PRIVILEGES'``. The
                allowed values are defined in the :class:`Driver` class attribute
                ``PRIVILEGES``.
            database (str): The name of the database on which to revoke
                privileges.
            table (str): The table name for table‑level revocation. Defaults to
                ``'*'``, which revokes database‑wide privileges.

        Returns:
            None

        Raises:
            Exception: If the ``REVOKE`` statement fails (e.g., insufficient
                privileges or invalid username), the original database error
                is re‑raised.

        Example:
            >>> driver = Driver("localhost", 5432, "admin", "secret", "mydb")
            >>> # Revoke SELECT and INSERT from the entire database
            >>> driver.revoke_privileges("alice", "SELECT, INSERT", "mydb")
            >>> # Revoke ALL PRIVILEGES from a specific table
            >>> driver.revoke_privileges(
            ...     "bob", "ALL PRIVILEGES", "mydb", table="employees"
            ... )
        """
        if table == '*':
            query = f'REVOKE {privileges} ON DATABASE "{database}" FROM "{username}";'
        else:
            query = f'REVOKE {privileges} ON TABLE "{database}"."{table}" FROM "{username}";'
        self._exc(query)

    def disconnect(self):
        """Closes all database connections and shuts down the driver.

        Sets the internal ``_connected`` flag to ``False``, preventing any new
        connections from being created. It then iterates over all connections in
        the pool's storage list, attempting to close each one. Finally, it drains
        the connection pool queue to remove any remaining references. After calling
        this method, the driver instance cannot be used for database operations.

        Returns:
            None

        Example:
            >>> driver.disconnect()
        """
        self._connected = False
        for i in self.connection_pool_storage:
            try:
                i.close()
            except:
                pass
        while not self.connection_pool.empty():
            self.connection_pool.get_nowait()

