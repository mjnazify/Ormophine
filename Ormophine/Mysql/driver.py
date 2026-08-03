from . import Literal, SimpleQueue, Empty, TableStructure, Table
from MySQLdb import connect, OperationalError, ProgrammingError

class Driver():
    """
    MySQL connection manager with thread-safe connection pooling and ORM capabilities.

    The ``Driver`` class serves as the main entry point for database interactions.
    It manages a pool of MySQL connections (using ``SimpleQueue``) for thread-safe
    execution of queries, automatically handles reconnection on connection errors,
    and dynamically maps existing tables to :class:`Table` objects as attributes.

    When instantiated, it establishes an initial connection to validate credentials,
    optionally creates the database, sets up a connection pool of the specified size,
    and introspects the database to create :class:`Table` instances for every table,
    attaching them as attributes (e.g., ``db.users``, ``db.orders``). Each table
    attribute provides access to columns, CRUD operations, batch operations, joins,
    and schema management.

    The driver supports MySQL 8.0+ features, including transaction isolation levels,
    SQL modes, and InnoDB flush settings. It also provides user management methods
    (create, drop, grant, revoke) and administrative utilities.

    Attributes:
        host (str): Database server hostname or IP address.
        port (int): Database server port number.
        username (str): MySQL username for authentication.
        password (str): MySQL password.
        db_name (str): Name of the default database to connect to.
        charset (CHARSET): Character set for the connection (default ``'utf8mb4'``).
        collate (COLLATE): Collation for the connection (default ``'utf8mb4_bin'``).
        connect_timeout (int): Connection timeout in seconds (default ``10``).
        sql_modes (list): List of SQL modes to enable on each connection.
        config (dict): Full configuration dictionary passed to MySQLdb connections.
        connection_pool (SimpleQueue): Queue holding available (connection, cursor) tuples.
        connection_pool_storage (list): List of all connection objects for cleanup.
        _connected (bool): Internal flag indicating whether the driver is active.
        PLACE_HOLDER (str): String used as a placeholder in bulk operations for
            parameter substitution (default ``'_MY_S4ULT3D_PL4C3_H0LD3R_%s_'``).

    Note:
        All public database operations are thread-safe because each query acquires
        a dedicated connection from the pool and returns it after commit/rollback.

    Example:
        Create a driver instance and interact with the database::

            from ormophine.Mysql import Driver, DataTypes, TableStructure

            # Connect to an existing database
            db = Driver(
                host='localhost',
                port=3306,
                username='root',
                password='secret',
                db_name='myapp',
                pool_size=10
            )

            # Access a table dynamically
            users = db.users
            print(users.get_columns_name())

            # Perform a query
            results = users.get_row(
                which_columns=[users.id, users.name],
                where=users.age > 18
            )

            # Create a new table using TableStructure
            new_table = (TableStructure('products')
                         .add_column('id', DataTypes.INT(), primary_key=True,
                                     auto_increment=True, not_null=True)
                         .add_column('name', DataTypes.VARCHAR(100), not_null=True)
                         .add_column('price', DataTypes.DECIMAL(10,2)))
            db.create_table(new_table)

            # Use the newly created table
            db.products.insert({'name': 'Laptop', 'price': 999.99})

            # Disconnect when done
            db.disconnect()
    """
    PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
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
    ISOLATION_LEVEL = Literal['READ UNCOMMITTED', 'READ COMMITTED', 'REPEATABLE READ', 'SERIALIZABLE']
    INNODB_FLUSH_LOG = Literal[0,1,2]
    PRIVILEGES = Literal['ALL PRIVILEGES', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'INDEX', 'REFERENCES', 'EXECUTE', 'GRANT OPTION', 'TRIGGER']
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        db_name: str,
        create_new_db: bool = False,
        pool_size: int = 5,
        connect_timeout: int = 10,
        charset: CHARSET = "utf8mb4",
        collate: COLLATE = "utf8mb4_bin",
        sql_modes: list = None,
        isolation_level: ISOLATION_LEVEL = 'REPEATABLE READ',
        innodb_flush_log_at_trx_commit: INNODB_FLUSH_LOG = 1
    ):
        """
        Initialize a new MySQL database driver with connection pooling and table ORM.

        This constructor establishes a connection pool to the specified MySQL database,
        optionally creates the database if it does not exist, and dynamically attaches
        `Table` objects for each existing table as attributes of the driver instance.
        The driver uses a thread‑safe queue to manage connections and supports custom
        SQL modes, transaction isolation levels, and InnoDB flush settings.

        Args:
            host (str): MySQL server hostname or IP address.
            port (int): TCP port number of the MySQL server.
            username (str): Username for authentication.
            password (str): Password for authentication.
            db_name (str): Name of the database to connect to (or create).
            create_new_db (bool, optional): If ``True``, create the database if it
                does not exist. Defaults to ``False``.
            pool_size (int, optional): Number of connections to keep in the pool.
                Defaults to 5.
            connect_timeout (int, optional): Connection timeout in seconds.
                Defaults to 10.
            charset (CHARSET, optional): Character set for the connection.
                Defaults to ``"utf8mb4"``. Must be a valid MySQL charset literal.
            collate (COLLATE, optional): Collation for the connection.
                Defaults to ``"utf8mb4_bin"``. Must be a valid MySQL collation literal.
            sql_modes (list, optional): List of additional SQL modes to enable
                (e.g., ``['ANSI_QUOTES']``). Defaults to an empty list.
                The session always enables ``PIPES_AS_CONCAT`` automatically.
            isolation_level (ISOLATION_LEVEL, optional): Transaction isolation level.
                Must be one of ``'READ UNCOMMITTED'``, ``'READ COMMITTED'``,
                ``'REPEATABLE READ'``, or ``'SERIALIZABLE'``.
                Defaults to ``'REPEATABLE READ'``.
            innodb_flush_log_at_trx_commit (INNODB_FLUSH_LOG, optional): InnoDB
                flush log setting (0, 1, or 2). Defaults to 1.

        Raises:
            RuntimeError: If the connection pool cannot be created or the database
                does not exist and ``create_new_db`` is ``False``.
            OperationalError: If connection fails due to network issues, authentication
                errors, or other MySQL server problems.
            ProgrammingError: If the SQL syntax for creating the database is invalid.
            Exception: If the initial connection attempt fails and the pool cannot be
                replenished.

        Example:
            >>> from ormophine.Mysql import Driver
            >>> db = Driver(
            ...     host='localhost',
            ...     port=3306,
            ...     username='root',
            ...     password='secret',
            ...     db_name='my_app',
            ...     create_new_db=True,
            ...     pool_size=10,
            ...     charset='utf8mb4',
            ...     isolation_level='READ COMMITTED'
            ... )
            >>> # Existing tables are now available as attributes, e.g. db.users
            >>> users_table = db.users
            >>> # Use the driver to execute raw queries
            >>> db.custom_execute("SET SESSION wait_timeout = 28800")

        Notes:
            - The driver automatically adds `Table` attributes for every table
            currently in the database. For example, if a table named `orders`
            exists, it can be accessed as ``db.orders``.
            - The connection pool is implemented using a :class:`queue.SimpleQueue`
            and is thread‑safe. Each connection is wrapped with a cursor.
            - The constructor sets the session SQL mode to include ``PIPES_AS_CONCAT``
            to allow the ``||`` operator for string concatenation, which is used by
            the ORM's :class:`ColumnsOperation` and :class:`Column` classes.
            - When `create_new_db` is ``True``, the database is created with the
            given charset and collation. If the database already exists, no error
            is raised.
            - If a connection breaks during operation, the driver automatically
            recreates it and puts it back into the pool.
        """
        self.CONNECTION_ERRORS = (2002, 2003, 2005, 2006, 2012, 2013, 2026, 2049, 2055, 2000)
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
        self.host = host
        self.port = port
        self._connected = True
        self.username = username
        self.password = password
        self.db_name = db_name
        self.charset = charset
        self.collate = collate
        self.connect_timeout = connect_timeout
        self.sql_modes = [] if sql_modes is None else sql_modes
        self.config = {
            "host":self.host,
            "port":self.port,
            "user":self.username,
            "password":self.password,
            "db":self.db_name,
            "charset":self.charset,
            "connect_timeout":self.connect_timeout,
            "init_command": f'SET SESSION TRANSACTION ISOLATION LEVEL {isolation_level}; SET SESSION innodb_flush_log_at_trx_commit = {innodb_flush_log_at_trx_commit};'
        }
        self.connection_pool = SimpleQueue()
        self.connection_pool_storage = []
        
        #To make sure inputs are valid
        conf = {
        "host":self.host,
        "port":self.port,
        "user":self.username,
        "password":self.password,
        "charset":self.charset,
        "connect_timeout":self.connect_timeout
        }
        connection = connect(**conf)
        if not create_new_db:
            try:
                connection.select_db(self.db_name)
                connection.close()
            except Exception:
                connection.close()
                raise
        else:
            try:
                cur = connection.cursor()
                query = f"CREATE DATABASE {self.db_name} CHARACTER SET {self.charset} COLLATE {self.collate};"
                cur.execute(query)
                connection.close()
            except Exception:
                connection.close()
                print(query)
                raise                

        [self._create_connection() for _ in range(pool_size)]

        for i in self.get_tables():
            self.__setattr__(i, Table(self, i))

    def _create_connection(self):
        """
        Create a new database connection and add it to the connection pool.

        This method establishes a new MySQL connection using the stored configuration
        (host, port, username, password, database, charset, etc.) and initializes its
        cursor. The connection and cursor are then placed into the pool for later use.
        The session is configured to enable the `PIPES_AS_CONCAT` SQL mode and any
        additional modes provided during driver initialization.

        This method is called automatically when the pool is empty and a connection
        is requested via :meth:`_get_connection`. It ensures that the pool always has
        available connections.

        Raises:
            RuntimeError: If the driver has been disconnected (i.e., :attr:`_connected`
                is ``False``), creating new connections is not allowed.
            MySQLdb.OperationalError: If the connection attempt fails due to network
                issues, invalid credentials, or other operational errors.

        Example:
            # Internal usage within the driver:
            driver = Driver(host='localhost', username='root', password='pass', db_name='test')
            # If the pool is empty, _get_connection will call _create_connection automatically.
            con, cur = driver._get_connection()
            # ... use con/cur ...
            driver.connection_pool.put((con, cur))
        """
        if not self._connected:
            raise RuntimeError('You have closed the connection, you can not create new connections')
        try:
            con = connect(**self.config)
            cur = con.cursor()
            self.connection_pool.put((con, cur))
            self.connection_pool_storage.append(con)
            cur.execute("SET SESSION sql_mode = 'PIPES_AS_CONCAT';")
            for i in self.sql_modes:
                cur.execute(f"SET SESSION sql_mode = CONCAT(@@sql_mode, ',{i}');")
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:  
                con = connect(**self.config)
                cur = con.cursor()
                self.connection_pool.put((con, cur))
                self.connection_pool_storage.append(con)
                cur.execute("SET SESSION sql_mode = 'PIPES_AS_CONCAT';")
                for i in self.sql_modes:
                    cur.execute(f"SET SESSION sql_mode = CONCAT(@@sql_mode, ',{i}');")
            else:
                raise

    def _get_connection(self):
        """
        Retrieve a database connection and its cursor from the connection pool.

        This method attempts to get a (connection, cursor) pair from the internal
        :class:`~queue.SimpleQueue` pool. If the pool is empty, it creates a new
        connection (via :meth:`_create_connection`) and retries. If the pool is
        still empty after that, an exception is raised.

        This is an internal helper used by all execution methods
        (``_exc``, ``_excp``, ``_excf``, ``_excfp``, ``_excs``, ``_excm``) to
        obtain a working connection in a thread‑safe manner.

        Returns:
            tuple: A pair ``(connection, cursor)`` where both are active MySQL
            connection objects from the pool.

        Raises:
            Exception: If the connection pool remains empty after attempting to
                create a new connection. This typically indicates that the pool
                size is too small and the timeout (0.5 seconds) is insufficient,
                or that the database server is unreachable.

        Example:
            .. code-block:: python

                # Internal usage only
                con, cur = driver._get_connection()
                try:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    con.commit()
                finally:
                    driver.connection_pool.put((con, cur))
        """
        try:
            return self.connection_pool.get(block=True, timeout=0.5)
        except Empty:
            self._create_connection()
            try:
                return self.connection_pool.get(block=True, timeout=0.5)
            except Empty as e:
                raise Exception(f'{e}\n\nEmpty connection pool, you better increase `pool_size`')

    def _excfp(self, query, params):
        """Execute a parameterized SQL query and return all fetched rows.

        This method acquires a database connection from the internal connection pool,
        executes the given query with the provided parameters, commits the transaction,
        and returns the complete result set. It automatically handles connection
        failures (e.g., server has gone away) by recreating the connection and
        retrying the operation once. In case of any SQL error, the transaction is
        rolled back, the connection is returned to the pool, and an exception with
        detailed context (including the query and parameters) is raised.

        This is an internal method primarily used by public methods like
        :meth:`Driver.custom_execute_with_fetch` and :meth:`Table.get_table_info`.

        Args:
            query (str): The SQL query to execute. Use ``%s`` placeholders for
                parameters (MySQLdb style).
            params (list, tuple, or dict): The parameter values to bind to the
                query placeholders. The type must be compatible with the MySQLdb
                cursor's ``execute()`` method.

        Returns:
            list of tuple: All rows returned by the query. Each row is represented
            as a tuple of column values.

        Raises:
            Exception: Wraps any underlying :class:`MySQLdb.OperationalError` or
                :class:`MySQLdb.ProgrammingError`. The raised exception includes the
                original error message, the query string, and the parameter values
                to aid debugging.

        Example:
            Assuming a ``Driver`` instance ``db`` and a table ``users`` with columns
            ``id`` and ``name``:

            >>> result = db._excfp("SELECT id, name FROM users WHERE age > %s", (18,))
            >>> print(result)
            [(1, 'Alice'), (3, 'Charlie')]

        Note:
            This method uses the connection pool. If the pool is empty, it will
            create a new connection (up to the pool size limit). It is safe for
            concurrent use.
        """
        con, cur = self._get_connection()
        try:
            cur.execute(query, params)
            res = cur.fetchall()
            con.commit()
            self.connection_pool.put((con, cur))
            return res
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.execute(query, params)
                    res = cur.fetchall()
                    con.commit()
                    self.connection_pool.put((con, cur))
                    return res
                except OperationalError as e2:
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
        """
        Execute a read-only SQL query and fetch all results.

        This internal method retrieves a connection from the pool, executes the
        given query without parameters, fetches all rows, and returns them.
        It handles connection errors by automatically reconnecting and retrying
        once. The method also manages transaction commits and rollbacks, and
        returns the connection to the pool after execution.

        **Note:** This method is intended for internal use by other methods in
        the :class:`Driver` class. It is used when no parameter substitution is
        required and the query is expected to return result sets (e.g., SELECT).

        Args:
            query (str): The SQL query string to execute. Must not contain
                parameter placeholders (use :meth:`_excfp` for parameterized
                queries).

        Returns:
            tuple: A tuple of rows returned by the query. Each row is a tuple
                of column values as returned by the MySQL driver.

        Raises:
            Exception: If an :class:`MySQLdb.OperationalError` occurs that is not
                a connection error, or if a :class:`MySQLdb.ProgrammingError` is
                raised. In these cases, the original error message is augmented
                with the query text to aid debugging. Connection errors are
                handled internally and a retry is attempted.

        Example:
            .. code-block:: python

                driver = Driver(...)
                # Fetch all table names in the current database
                rows = driver._excf("SHOW TABLES")
                for (table_name,) in rows:
                    print(table_name)

        .. seealso:: :meth:`_excfp` for parameterized queries that return results.
        """
        con, cur = self._get_connection()
        try:
            cur.execute(query)
            res = cur.fetchall()
            con.commit()
            self.connection_pool.put((con, cur))
            return res
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:
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
        """
        Execute a parameterized SQL query and commit the transaction.

        This internal method retrieves a connection from the pool, executes the provided
        query with the given parameters, commits the transaction, and returns the
        connection to the pool. If a connection error occurs (e.g., server gone away),
        it attempts to reconnect and retry the execution. On any other SQL error,
        it rolls back the transaction and raises an exception with detailed context.

        Args:
            query (str): The SQL query string containing placeholders (``%s``) for
                parameters.
            params (list or tuple): The parameter values to substitute into the query.

        Returns:
            None: This method does not return any value; it only executes the query.

        Raises:
            Exception: If an operational or programming error occurs. The exception
                message includes the original error, the query, and the parameters
                to aid debugging.
            RuntimeError: If the connection pool is empty and a new connection cannot
                be created (indirectly via :meth:`_get_connection`).

        Example:
            Assuming a ``Driver`` instance ``db`` and a table ``users``::

                db._excp(
                    "INSERT INTO users (name, age) VALUES (%s, %s)",
                    ("Alice", 30)
                )
        """
        con, cur = self._get_connection()
        try:
            cur.execute(query, params)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:
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
        """
        Execute a SQL query without parameters and commit the transaction.

        This internal method retrieves a connection from the pool, executes the provided
        query (which should contain no placeholders), commits the transaction, and
        returns the connection to the pool. If a connection error occurs (e.g., server
        gone away), it attempts to reconnect and retry the execution. On any other SQL
        error, it rolls back the transaction and raises an exception with detailed
        context.

        Args:
            query (str): The SQL query string to execute (no parameters).

        Returns:
            None: This method does not return any value; it only executes the query.

        Raises:
            Exception: If an operational or programming error occurs. The exception
                message includes the original error and the query to aid debugging.
            RuntimeError: If the connection pool is empty and a new connection cannot
                be created (indirectly via :meth:`_get_connection`).

        Example:
            Assuming a ``Driver`` instance ``db``::

                # Create a table
                db._exc("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(50));")

                # Drop a table (use with caution)
                db._exc("DROP TABLE IF EXISTS temp;")
        """
        con, cur = self._get_connection()
        try:
            cur.execute(query)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:
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
        """
        Execute a script of multiple parameterized SQL queries in a single transaction.

        This internal method processes a list of query definitions, each of which may
        include parameters. It retrieves a connection from the pool, executes each
        query in sequence, commits the transaction, and returns the connection to
        the pool. If a connection error occurs (e.g., server gone away), it attempts
        to reconnect and retry the entire script. On any other SQL error, it rolls
        back the transaction and raises an exception with detailed context.

        Args:
            query_params (list): A list of query definitions. Each item can be:
                - A list of length 2: ``[query_string, params_list]`` for a
                parameterized query.
                - A list of length 1: ``[query_string]`` for a query without
                parameters.

        Returns:
            None: This method does not return any value; it only executes the queries.

        Raises:
            Exception: If an operational or programming error occurs. The exception
                message includes the original error and a formatted list of all
                queries and their parameters to aid debugging.
            RuntimeError: If the connection pool is empty and a new connection cannot
                be created (indirectly via :meth:`_get_connection`).

        Example:
            Assuming a ``Driver`` instance ``db`` and a table ``users``::

                script = [
                    ["INSERT INTO users (name, age) VALUES (%s, %s)", ("Alice", 30)],
                    ["UPDATE users SET age = %s WHERE name = %s", (31, "Alice")],
                    ["DELETE FROM users WHERE age < %s", (18,)]
                ]
                db._excs(script)
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
            if e.args[0] in self.CONNECTION_ERRORS:
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
        """
        Execute a parameterized query multiple times with different parameter sets.

        This internal method retrieves a connection from the pool, uses
        :meth:`MySQLdb.cursor.executemany` to execute the given query for each
        parameter tuple in the list, commits the transaction, and returns the
        connection to the pool. It is primarily used for bulk INSERT, UPDATE, or
        DELETE operations where many rows are affected with the same query pattern.

        If a connection error occurs (e.g., server gone away), the method attempts
        to handle it by discarding the broken connection, creating a new one, and
        retrying the entire operation. On any other SQL error, the transaction is
        rolled back and an exception is raised with detailed context.

        Args:
            query (str): The SQL query string containing placeholders (``%s``) for
                parameters. The same query is used for all executions.
            params (list of tuples or list of lists): A sequence of parameter
                sequences, where each inner sequence contains the values to
                substitute into the query for one execution.

        Returns:
            None: This method does not return any value; it only executes the query.

        Raises:
            Exception: If an operational or programming error occurs. The exception
                message includes the original error, the query, and the parameters
                to aid debugging.
            RuntimeError: If the connection pool is empty and a new connection cannot
                be created (indirectly via :meth:`_get_connection`).

        Example:
            Assuming a ``Driver`` instance ``db`` and a table ``users`` with columns
            ``name`` and ``age``::

                db._excm(
                    "INSERT INTO users (name, age) VALUES (%s, %s)",
                    [("Alice", 30), ("Bob", 25), ("Charlie", 35)]
                )
        """
        con, cur = self._get_connection()
        try:
            cur.executemany(query, params)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:
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
        """
        Handle a broken database connection by cleaning up and creating a replacement.

        This internal method is called when a connection error (e.g., server gone away)
        is detected. It attempts to close the broken connection, removes it from the
        internal connection storage list, and creates a new connection via
        :meth:`_create_connection` to replenish the pool. This ensures that the
        connection pool maintains the configured size even after failures.

        Args:
            con: The broken MySQL connection object (from `MySQLdb`). This connection
                is closed and discarded.

        Returns:
            None

        Raises:
            RuntimeError: If the driver has been disconnected (``_connected`` is
                ``False``) and :meth:`_create_connection` is called, this exception
                will propagate.

        Example:
            This method is typically used internally by query execution methods::

                try:
                    cursor.execute(query)
                except OperationalError as e:
                    if e.args[0] in self.CONNECTION_ERRORS:
                        self._handle_broken_connection(connection)
                        # Retry the query with a new connection
        """
        try:
            con.close()
        except:
            pass
        # حذف از storage اگر وجود دارد
        if con in self.connection_pool_storage:
            self.connection_pool_storage.remove(con)
        # ایجاد اتصال جدید برای جایگزینی
        self._create_connection()

    def delete_table(self, table: Table, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool):
        """
        Permanently drop the specified table from the database.

        This method executes a ``DROP TABLE`` SQL statement to delete the given table.
        To prevent accidental deletion, three separate confirmation flags must all be
        ``True``. After successful deletion, the table reference is also removed from
        the driver instance's attributes.

        Args:
            table (Table): The :class:`Table` object representing the table to delete.
            are_you_sure (bool): First confirmation flag; must be ``True`` to proceed.
            are_you_really_sure (bool): Second confirmation flag; must be ``True``.
            for_sure (bool): Third confirmation flag; must be ``True``.

        Returns:
            None: This method does not return a value.

        Raises:
            Exception: If the underlying SQL execution fails (e.g., table does not exist,
                permission denied). The exception is propagated from :meth:`Driver._exc`.

        Example:
            Assuming a ``Driver`` instance ``db`` and a table ``users`` already exists::

                db.delete_table(db.users, True, True, True)  # Deletes the 'users' table.

            The table reference ``db.users`` will no longer be available.

        Warning:
            This operation is irreversible. Ensure you have a backup or are certain
            before calling this method.
        """
        if are_you_sure and are_you_really_sure and for_sure:
            self._exc(f'DROP TABLE {table.name_};')
            self.__delattr__(table.name_[1:-1])

    def delete_database(self, database_name: str, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool):
        """
        Permanently delete an entire MySQL database.

        This method executes a ``DROP DATABASE`` statement, which irreversibly removes
        the specified database and all its tables, data, and schema objects. To prevent
        accidental deletion, three explicit confirmation flags are required. All three
        must be ``True`` for the operation to proceed.

        Args:
            database_name (str): The name of the database to delete.
            are_you_sure (bool): First-level confirmation flag.
            are_you_really_sure (bool): Second-level confirmation flag.
            for_sure (bool): Final confirmation flag.

        Returns:
            None

        Raises:
            Exception: If any database error occurs (e.g., insufficient privileges,
                the database does not exist, or the connection fails). The exception
                message will include the original error and the query.

        Example:
            Assuming a ``Driver`` instance named ``db`` connected to a MySQL server::

                # Danger: this will delete the database 'old_data'
                db.delete_database('old_data', True, True, True)

            If any flag is ``False``, nothing happens::

                db.delete_database('old_data', True, True, False)  # No effect
        """
        if are_you_sure and are_you_really_sure and for_sure:
            self._exc(f'DROP DATABASE {database_name};')

    def custom_execute_with_fetch(self, query, params = None):
        """
        Execute a custom SQL query and return the fetched result set.

        This method provides a flexible way to run arbitrary SQL queries (e.g., SELECT)
        with optional parameter binding. It automatically chooses the appropriate
        internal execution method based on whether parameters are provided. If
        ``params`` is ``None``, the query is executed without parameters; otherwise,
        the query is executed with the given parameters. The method always fetches
        all rows and returns them as a list of tuples.

        Args:
            query (str): The SQL query to execute.
            params (list or tuple, optional): Parameter values to substitute into the
                query. If provided, the query should contain ``%s`` placeholders.
                Defaults to ``None``.

        Returns:
            list[tuple]: The fetched rows, where each row is represented as a tuple
                of column values. If the query returns no rows, an empty list is
                returned.

        Raises:
            Exception: If an operational or programming error occurs (e.g., syntax
                error, connection failure, or invalid parameters). The exception
                message includes the original error, the query, and the parameters
                (if any) for debugging.
            RuntimeError: If the connection pool is exhausted and a new connection
                cannot be created.

        Example:
            Assuming a ``Driver`` instance named ``db`` connected to a database
            with a table ``users``::

                # Execute a SELECT query without parameters
                rows = db.custom_execute_with_fetch("SELECT * FROM users")
                for row in rows:
                    print(row)

                # Execute a parameterized query
                rows = db.custom_execute_with_fetch(
                    "SELECT name FROM users WHERE age > %s",
                    [25]
                )
                print(rows)  # e.g., [('Alice',), ('Bob',)]
        """
        return self._excfp(query, params) if params else self._excf(query)
    
    def custom_execute(self, query: str, params: list = None) -> None:
        """
        Execute a custom SQL query with optional parameters.

        This method serves as a public wrapper around the internal execution methods
        :meth:`_exc` (for queries without parameters) and :meth:`_excp` (for queries
        with parameters). It automatically selects the appropriate method based on
        whether ``params`` are provided. The query is executed using a connection
        from the pool, committed, and the connection is returned to the pool.

        Args:
            query (str): The SQL query string to execute. If using parameters,
                use ``%s`` placeholders.
            params (list, optional): A list or tuple of parameter values to substitute
                into the query. Defaults to ``None``, in which case the query is
                executed without parameters.

        Returns:
            None: This method does not return any value; it only executes the query
            and commits the transaction.

        Raises:
            Exception: If an operational or programming error occurs. The exception
                message includes the original error, the query, and the parameters
                (if any) to aid debugging.
            RuntimeError: If the connection pool is empty and a new connection cannot
                be created (indirectly via :meth:`_get_connection`).

        Example:
            Assuming a ``Driver`` instance named ``db`` connected to a MySQL server
            with a table ``users``::

                # Execute a query without parameters
                db.custom_execute("DELETE FROM users WHERE age < 18")

                # Execute a parameterized query
                db.custom_execute(
                    "UPDATE users SET active = %s WHERE id = %s",
                    [False, 42]
                )
        """
        return self._excp(query, params) if params else self._exc(query)
    
    def custom_execute_many(self, query, params):
        """
        Execute the same parameterized SQL query multiple times with different parameter sets.

        This method is a wrapper around the internal :meth:`_excm` method, which uses
        ``cursor.executemany()`` for efficient bulk execution. It is ideal for batch
        inserts, updates, or deletes where the same query structure is repeated with
        varying data.

        Args:
            query (str): The SQL query string containing placeholders (``%s``) for
                parameters. The query must be compatible with ``executemany()``.
            params (list of tuple or list of list): A sequence of parameter sets.
                Each inner sequence provides values for the placeholders in the query.
                For example, ``[(1, 'Alice'), (2, 'Bob')]`` for a query like
                ``"INSERT INTO users (id, name) VALUES (%s, %s)"``.

        Returns:
            None: This method does not return a value. It executes the queries and
            commits the transaction upon success.

        Raises:
            Exception: If a database error occurs (e.g., connection issues, syntax
                errors, or constraint violations). The exception message includes
                the original error, the query, and the parameters to facilitate
                debugging.
            RuntimeError: If the connection pool is exhausted and a new connection
                cannot be established (indirectly via :meth:`_get_connection`).

        Example:
            Assuming a ``Driver`` instance named ``db`` and a table ``users``
            with columns ``id`` and ``name``::

                # Bulk insert multiple users
                db.custom_execute_many(
                    "INSERT INTO users (id, name) VALUES (%s, %s)",
                    [(1, 'Alice'), (2, 'Bob'), (3, 'Charlie')]
                )

                # Bulk update salaries
                db.custom_execute_many(
                    "UPDATE employees SET salary = salary * 1.1 WHERE id = %s",
                    [(101,), (102,), (103,)]
                )

            For large datasets, this method is significantly faster than calling
            :meth:`custom_execute` in a loop.
        """
        return self._excm(query, params)
    
    def get_databases(self):
        """
        Retrieve the list of all databases on the MySQL server.

        This method executes a ``SHOW DATABASES`` query and returns the names of
        all databases accessible by the current connection. The result is a flat
        list of database names.

        Returns:
            list[str]: A list of database names available on the server.

        Raises:
            Exception: If any database error occurs (e.g., connection lost,
                insufficient privileges). The exception message will include the
                original error and the executed query.

        Example:
            Assuming a connected ``Driver`` instance named ``db``::

                databases = db.get_databases()
                print(databases)  # e.g., ['information_schema', 'mysql', 'my_app_db']
        """
        return [i[0] for i in self._excf('SHOW DATABASES;')]
    
    def get_tables(self):
        """
        Retrieve the names of all tables in the currently selected database.

        This method executes a ``SHOW TABLES`` query and returns a list of table
        names as strings. It uses the internal :meth:`_excf` method to fetch the
        results.

        Returns:
            list[str]: A list of table names in the current database. If there are
            no tables, an empty list is returned.

        Raises:
            Exception: If a database error occurs (e.g., connection lost, insufficient
                privileges). The exception will include the original error message
                and the executed query.

        Example:
            Assuming a :class:`Driver` instance named ``db`` connected to a MySQL
            server::

                tables = db.get_tables()
                print(tables)  # e.g., ['users', 'orders', 'products']

            This method is automatically called during :class:`Driver` initialization
            to create :class:`Table` objects for each existing table.
        """
        return [i[0] for i in self._excf('SHOW TABLES;')]
    
    def create_table(self, table_structure: TableStructure):
        """
        Create a new database table based on the provided table structure.

        This method takes a :class:`TableStructure` object, retrieves the complete
        ``CREATE TABLE`` SQL statement via its :meth:`~TableStructure.get_structure`
        method, executes it on the database, and then dynamically adds the newly
        created table as an attribute on the driver instance (so it can be accessed
        as ``db.new_table``). The attribute is an instance of :class:`Table`
        representing the new table.

        Args:
            table_structure (TableStructure): A fully configured table structure
                object containing column definitions, constraints, foreign keys,
                and table options (charset, collate, etc.). Must have at least one
                column defined; otherwise, :meth:`~TableStructure.get_structure`
                raises an exception.

        Returns:
            None

        Raises:
            Exception: If the table structure has no columns (propagated from
                :meth:`~TableStructure.get_structure`).
            Exception: If a database error occurs during execution (e.g., table
                already exists, invalid data type, permission denied). The original
                error message and query are included in the exception.

        Example:
            Assuming a configured :class:`Driver` instance ``db`` and a
            :class:`TableStructure` object built for a ``users`` table::

                from ormophine.Mysql import TableStructure, DataTypes

                # Build the table structure
                users_table = (TableStructure('users')
                            .add_column('id', DataTypes.INT(), primary_key=True,
                                        auto_increment=True, not_null=True)
                            .add_column('username', DataTypes.VARCHAR(50),
                                        not_null=True, unique=True)
                            .add_column('email', DataTypes.VARCHAR(255))
                            .add_column('created_at', DataTypes.DATETIME(),
                                        default_value='CURRENT_TIMESTAMP'))

                # Create the table in the database
                db.create_table(users_table)

                # Now the table is available as an attribute
                db.users.insert({'username': 'alice', 'email': 'alice@example.com'})
        """
        self._exc(table_structure.get_structure())
        self.__setattr__(table_structure.name.strip('`'), Table(self, table_structure.name.strip('`')))

    def optimize(self):
        """
        Optimize and analyze all tables in the current database.

        This method iterates over all tables in the database (as returned by
        :meth:`get_tables`) and executes both ``OPTIMIZE TABLE`` and ``ANALYZE TABLE``
        on each. ``OPTIMIZE TABLE`` reclaims unused space and defragments the table
        data and indexes. ``ANALYZE TABLE`` updates table statistics to help the
        query optimizer make better execution plans. Running these operations
        regularly can improve database performance, especially after large data
        modifications.

        The operations are performed sequentially; if an error occurs on one table,
        the method may stop and raise an exception, leaving subsequent tables
        unprocessed.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If any database error occurs during the optimization or
                analysis of a table (e.g., table does not exist, permission denied,
                connection failure). The exception message includes the original
                error and the failing query.

        Example:
            Assuming a configured :class:`Driver` instance ``db`` connected to a
            database with tables ``users`` and ``orders``::

                # Perform maintenance on all tables
                db.optimize()

                # This will execute:
                # OPTIMIZE TABLE users;
                # ANALYZE TABLE users;
                # OPTIMIZE TABLE orders;
                # ANALYZE TABLE orders;
        """
        for i in self.get_tables():
            self._exc(f"OPTIMIZE TABLE {i};")
            self._exc(f"ANALYZE TABLE {i}")

    def create_user(self, username: str, password: str, host: str = 'localhost'):
        """
        Create a new MySQL user account.

        This method executes a ``CREATE USER`` statement with the specified username,
        password, and host. The password is passed as a parameter to prevent SQL
        injection. The username and host are escaped by doubling single quotes to
        avoid syntax errors. If the user already exists or the current user lacks
        sufficient privileges, an exception is raised.

        Args:
            username (str): The username for the new account. Single quotes will be
                escaped automatically.
            password (str): The password for the new account. This is passed as a
                parameter, so it is safe from injection.
            host (str, optional): The host from which the user can connect. Defaults
                to ``'localhost'``.

        Returns:
            None

        Raises:
            Exception: If a database error occurs (e.g., user already exists,
                insufficient privileges, connection failure). The exception message
                includes the original error and the query for debugging.

        Example:
            Assuming a :class:`Driver` instance ``db`` connected to a MySQL server::

                # Create a user 'app_user' with password 'secure123' from localhost
                db.create_user('app_user', 'secure123')

                # Create a user 'remote_user' allowed to connect from any host
                db.create_user('remote_user', 'pass456', host='%')
        """
        query = f"CREATE USER '{username.replace("'", "''")}'@'{host.replace("'", "''")}' IDENTIFIED BY %s;"
        self._excp(query, (password,))

    def drop_user(self, username: str, host: str = 'localhost'):
        """
        Permanently delete a MySQL user account.

        This method executes a ``DROP USER`` statement, which removes the specified
        user account from the MySQL server. The user account is identified by the
        combination of username and host. All privileges associated with the user
        are also revoked automatically.

        The method sanitizes the input by doubling single quotes (``'``) within
        the username and host to prevent SQL injection attacks. However, it is
        recommended to use parameterized queries for user-supplied input whenever
        possible.

        Args:
            username (str): The username of the account to drop. Single quotes
                within the string are automatically escaped.
            host (str, optional): The host part of the account (e.g., ``'localhost'``,
                ``'%'``, or a specific IP). Defaults to ``'localhost'``.

        Returns:
            None

        Raises:
            Exception: If the user does not exist, the current user lacks
                the ``DROP USER`` privilege, or a database error occurs. The
                original error message is included in the raised exception.

        Example:
            Assuming a configured :class:`Driver` instance named ``db``::

                # Drop user 'johndoe' at localhost
                db.drop_user('johndoe')

                # Drop user 'appuser' from any host
                db.drop_user('appuser', host='%')
        """
        query = f"DROP USER '{username.replace("'", "''")}'@'{host.replace("'", "''")}';"
        self._exc(query)

    def change_password(self, username: str, new_password: str, host: str = 'localhost'):
        """
        Change the password for an existing MySQL user account.

        This method executes an ``ALTER USER`` statement to update the password
        for the specified user at the given host. The password is passed as a
        parameter to prevent SQL injection. The change takes effect immediately
        for new connections; existing connections remain unaffected.

        Args:
            username (str): The name of the user whose password is to be changed.
            new_password (str): The new password for the user account.
            host (str, optional): The host part of the user account. Defaults to
                ``'localhost'``.

        Returns:
            None

        Raises:
            Exception: If the user does not exist, the current connection lacks
                sufficient privileges (e.g., ``CREATE USER`` or ``ALTER USER``
                privileges), or any other database error occurs. The exception
                message will contain the original error and the executed query.

        Example:
            Assuming a :class:`Driver` instance named ``db`` connected with
            administrative privileges::

                # Change password for 'app_user' on localhost
                db.change_password('app_user', 'new_secure_password_123')

                # Change password for a user on a specific host
                db.change_password('remote_user', 'p@ssw0rd', host='192.168.1.100')
        """
        query = f"ALTER USER '{username.replace("'", "''")}'@'{host.replace("'", "''")}' IDENTIFIED BY %s;"
        self._excp(query, (new_password,))

    def rename_user(self, old_username: str, old_host: str, new_username: str, new_host: str):
        """
        Rename an existing MySQL user account.

        This method executes a ``RENAME USER`` statement, which changes both the
        username and the host portion of an existing user account. Both the old and
        new host values must be specified, as MySQL identifies users by the
        combination of username and host. The method automatically escapes single
        quotes in the provided strings to prevent SQL injection.

        Args:
            old_username (str): The current username of the account to rename.
            old_host (str): The current host part of the account (e.g., ``'localhost'``
                or ``'%'``).
            new_username (str): The new username for the account.
            new_host (str): The new host part for the account.

        Returns:
            None

        Raises:
            Exception: If the ``RENAME USER`` statement fails (e.g., the old user
                does not exist, insufficient privileges, or the new user already
                exists). The exception includes the original error message and the
                generated query.

        Example:
            Assuming a :class:`Driver` instance ``db`` with appropriate privileges::

                # Rename user 'john'@'localhost' to 'jane'@'%'
                db.rename_user('john', 'localhost', 'jane', '%')

                # Rename user 'app_user'@'192.168.1.100' to 'prod_user'@'10.0.0.5'
                db.rename_user('app_user', '192.168.1.100', 'prod_user', '10.0.0.5')
        """
        query = f"RENAME USER '{old_username.replace("'", "''")}'@'{old_host.replace("'", "''")}' TO '{new_username.replace("'", "''")}'@'{new_host.replace("'", "''")}';"
        self._exc(query)

    def grant_privileges(self, username: str, host: str, privileges: PRIVILEGES, database: str, table: str = '*'):
        """
        Grant specific privileges on a database table to a MySQL user.

        This method constructs and executes a ``GRANT`` statement, allowing the
        specified user to perform the given operations on the target table. The
        privileges are granted immediately and take effect without requiring a
        flush (though the driver also provides :meth:`flush_privileges` if needed).

        Args:
            username (str): The name of the user to receive the privileges. Single
                quotes and special characters are automatically escaped.
            host (str): The host from which the user connects (e.g., ``'localhost'``
                or ``'%'``). Escaped automatically.
            privileges (PRIVILEGES): A privilege string from the driver's
                :attr:`PRIVILEGES` type literal (e.g., ``'SELECT'``, ``'ALL PRIVILEGES'``,
                ``'INSERT, UPDATE'``). Multiple privileges can be combined in a
                comma-separated string.
            database (str): The name of the database on which privileges are granted.
                Escaped automatically.
            table (str, optional): The table name within the database. Defaults to
                ``'*'``, meaning all tables in the database.

        Returns:
            None

        Raises:
            Exception: If the underlying SQL execution fails (e.g., user does not
                exist, invalid privilege name, insufficient permissions). The
                exception message includes the original error and the query.

        Example:
            Grant ``SELECT`` and ``INSERT`` on the ``users`` table to user
            ``'app_user'`` from localhost::

                db.grant_privileges(
                    username='app_user',
                    host='localhost',
                    privileges='SELECT, INSERT',
                    database='myapp',
                    table='users'
                )

            Grant all privileges on all tables in the database::

                db.grant_privileges(
                    username='admin',
                    host='%',
                    privileges='ALL PRIVILEGES',
                    database='myapp'
                )
        """
        query = f"GRANT {privileges} ON {database.replace("'", "''")}.{table.replace("'", "''")} TO '{username.replace("'", "''")}'@'{host.replace("'", "''")}';"
        self._exc(query)

    def revoke_privileges(self, username: str, host: str, privileges: PRIVILEGES, database: str, table: str = '*'):
        """
        Revoke specific privileges on a database table from a MySQL user.

        This method constructs and executes a ``REVOKE`` statement, removing the
        specified privileges from the given user on the target table. The changes
        take effect immediately; a subsequent :meth:`flush_privileges` is not
        required but can be called if needed.

        Args:
            username (str): The name of the user from whom to revoke privileges.
                Single quotes and special characters are automatically escaped.
            host (str): The host from which the user connects (e.g., ``'localhost'``
                or ``'%'``). Escaped automatically.
            privileges (PRIVILEGES): A privilege string from the driver's
                :attr:`PRIVILEGES` type literal (e.g., ``'SELECT'``, ``'ALL PRIVILEGES'``,
                ``'INSERT, UPDATE'``). Multiple privileges can be combined in a
                comma-separated string.
            database (str): The name of the database from which privileges are revoked.
                Escaped automatically.
            table (str, optional): The table name within the database. Defaults to
                ``'*'``, meaning all tables in the database.

        Returns:
            None

        Raises:
            Exception: If the underlying SQL execution fails (e.g., user does not
                exist, invalid privilege name, insufficient permissions). The
                exception message includes the original error and the query.

        Example:
            Revoke ``DELETE`` and ``UPDATE`` privileges on the ``users`` table from
            user ``'app_user'`` connecting from localhost::

                db.revoke_privileges(
                    username='app_user',
                    host='localhost',
                    privileges='DELETE, UPDATE',
                    database='myapp',
                    table='users'
                )

            Revoke all privileges on all tables in the database::

                db.revoke_privileges(
                    username='app_user',
                    host='%',
                    privileges='ALL PRIVILEGES',
                    database='myapp'
                )
        """
        query = f"REVOKE {privileges} ON {database.replace("'", "''")}.{table.replace("'", "''")} FROM '{username.replace("'", "''")}'@'{host.replace("'", "''")}';"
        self._exc(query)

    def flush_privileges(self):
        """
        Reload the MySQL privilege tables from the grant tables in the system database.

        This method executes the ``FLUSH PRIVILEGES`` statement, which forces MySQL
        to reload the privilege tables (stored in the ``mysql`` database) into memory.
        This is necessary after manually editing grant tables or when using privilege
        management statements like :meth:`grant_privileges` or :meth:`revoke_privileges`
        that do not automatically trigger a reload (though in most cases MySQL does
        it automatically). Calling this method ensures that all privilege changes
        take effect immediately for all active connections.

        Returns:
            None

        Raises:
            Exception: If the database execution fails (e.g., insufficient privileges
                to flush privileges, or a connection error). The exception message
                includes the original error and the query.

        Example:
            After granting or revoking privileges, you may explicitly flush::

                db.grant_privileges('app_user', 'localhost', 'SELECT', 'myapp')
                db.flush_privileges()  # Ensure the change is loaded
        """
        self._exc("FLUSH PRIVILEGES;")

    def disconnect(self):
        """
        Close all database connections and release resources.

        This method terminates the connection pool by closing every active MySQL
        connection stored in the pool, clearing the internal queue, and setting the
        connection status flag to ``False``. After calling this method, the driver
        instance cannot be used for further database operations; any attempt to
        execute a query or create a new connection will raise a :class:`RuntimeError`
        (via :meth:`_create_connection`). If you need to reconnect, you must create
        a new :class:`Driver` instance.

        The method attempts to close each connection, ignoring any errors that occur
        during the close process (e.g., connections already closed). It then drains
        the queue of any remaining connection objects.

        Args:
            None

        Returns:
            None

        Raises:
            None: While the method itself does not raise exceptions, subsequent
                database operations will fail with a :class:`RuntimeError` if
                attempted after disconnection.

        Example:
            Gracefully shut down the database connection pool::

                db = Driver(host='localhost', username='root', password='pass',
                            db_name='myapp')
                # ... perform operations ...
                db.disconnect()

            After disconnection, attempting to use the driver will fail::

                db.disconnect()
                db.get_tables()  # Raises RuntimeError: You have closed the connection...
        """
        self._connected = False
        for i in self.connection_pool_storage:
            try:
                i.close()
            except:
                pass
        while not self.connection_pool.empty():
            self.connection_pool.get_nowait()

