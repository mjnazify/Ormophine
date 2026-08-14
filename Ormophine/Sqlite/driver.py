from . import SetPragma, TableStructure, Table
from traceback import print_exc
from time import sleep
from sqlite3 import connect
from typing import Any, Literal
from threading import Thread, Event
from queue import SimpleQueue

class Driver:
    """
    Comprehensive SQLite Driver for Ormophine.

    The Driver class serves as the central gateway to the SQLite database,
    managing connections, threading, and high‑level operations. It provides
    a thread‑safe, non‑blocking environment where a single writer thread
    serialises all write operations, while an optional pool of reader threads
    handles concurrent read queries without interfering with the writer.

    Key Features
    ------------
    - **Automatic Table Discovery** – Existing tables are immediately
      available as attributes (e.g. ``driver.users``) right after
      initialisation.
    - **Strict Schema Creation** – Use ``TableStructure`` and ``DataTypes``
      to define tables with constraints, defaults, foreign keys, and
      conflict resolutions.
    - **Full CRUD via ``Table`` Objects** – Each table exposes fluent
      APIs for insert, update, delete, select, joins, batch operations,
      indexes, and column manipulation.
    - **Pragma Management** – Pragmas are set through the ``driver.SetPragma``
      helper that safely serialises commands onto the writer thread.
    - **WAL Mode & Checkpointing** – Easily enable WAL mode; a background
      checkpoint timer keeps the WAL file tidy.
    - **Non‑blocking Reads** – Fetches can be directed to a separate
      reader pool, avoiding contention with writes.
    - **Graceful Shutdown** – ``disconnect()`` stops all threads, commits
      pending work, and closes connections cleanly.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file. If the file does not exist,
        SQLite will create it.
    isolation_level : {'DEFERRED', 'IMMEDIATE', 'EXCLUSIVE'}, optional
        Transaction isolation level (default ``'DEFERRED'``).
    cache_size : int, optional
        Number of cached SQL statements per connection (default 128).
    none_block_reader_pool_size : int, optional
        Number of reader threads to spawn. Each thread holds its own
        SQLite connection. Increase for highly concurrent read workloads
        (default 1).
    setup_time : float, optional
        Time in seconds to wait after initial table discovery (allows
        ``Table`` objects to populate their column attributes). Usually
        no need to change (default 0.5).

    Attributes
    ----------
    db_path : str
        The database file path.
    main_queue : queue.SimpleQueue
        Internal command queue for the writer thread.
    SetPragma : SetPragma
        Pragma interface (see :class:`SetPragma`).
    PLACE_HOLDER : str
        String used internally for complex parameter substitution. May
        be changed if it conflicts with real data (default
        ``'_MY_S4ULT3D_PL4C3_H0LD3R_?_'``).

    Examples
    --------
    >>> # 1. Connect
    >>> driver = Driver('example.db', isolation_level='IMMEDIATE')

    >>> # 2. Create a table with strict schema
    >>> schema = TableStructure('users', strict=True)
    >>> schema.add_column(
    ...     'id', DataTypes.INTEGER(),
    ...     primary_key=True
    ... ).add_column(
    ...     'name', DataTypes.TEXT(max_length=100),
    ...     not_null=True
    ... ).add_column(
    ...     'age', DataTypes.TINYINT(unsigned=True)
    ... )
    >>> users = driver.create_table(schema)

    >>> # 3. Insert a row
    >>> users.insert({users.name: 'Alice', users.age: 30})

    >>> # 4. Query with conditions
    >>> where = (users.name == 'Alice') & (users.age > 25)
    >>> row = users.get_row([users.id, users.name, users.age], where)
    >>> print(row)   # e.g. (1, 'Alice', 30)

    >>> # 5. Update
    >>> users.update({users.age: 31}, where)

    >>> # 6. Bulk insert
    >>> users.bulk_insert(
    ...     [users.name, users.age],
    ...     [('Bob', 25), ('Carol', 28)]
    ... )

    >>> # 7. Complex join
    >>> orders = driver.table_object('orders')  # assuming orders table exists
    >>> joined = users.join(
    ...     columns=[users.name, orders.total],
    ...     joins_list=[Join.Inner(orders, users.id == orders.user_id)],
    ...     where=orders.total > 100
    ... )
    >>> print(joined)

    >>> # 8. Non-blocking read (reader pool)
    >>> res = users.get_row([users.name], from_readers_pool=True)

    >>> # 9. PRAGMA
    >>> driver.SetPragma.journal_mode('WAL')
    >>> driver.SetPragma.foreign_keys(True)

    >>> # 10. Disconnect
    >>> driver.disconnect()
    """

    ISOLATION_LEVEL= Literal['DEFERRED', 'IMMEDIATE', 'EXCLUSIVE']
    PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_?_'
    def __init__(self, db_path: str, isolation_level: ISOLATION_LEVEL = 'DEFERRED',cache_size: int = 128, none_block_reader_pool_size: int = 1,setup_time: float = 0.5):
        """Initialises the database connection and the worker threads.

        Opens (and immediately closes) a test connection to verify the path,
        then starts a main writer thread and a pool of non‑blocking reader threads.
        All schema objects (tables) are discovered and exposed as attributes on the
        driver instance (e.g. ``driver.my_table``).  SetPragma helper is also
        attached as :attr:`SetPragma`.

        Args:
            db_path: Path to the SQLite database file.  If the file does not exist
                it will be created by the underlying writer thread.
            isolation_level: One of ``'DEFERRED'``, ``'IMMEDIATE'``, or
                ``'EXCLUSIVE'``.  Controls the transaction isolation mode.
                Defaults to ``'DEFERRED'``.
            cache_size: Number of compiled SQL statements to keep in the
                statement cache (passed to :func:`sqlite3.connect` as
                ``cached_statements``).  Defaults to 128.
            none_block_reader_pool_size: Number of separate reader connections
                and threads to create for non‑blocking read operations (used by
                the ``from_readers_pool`` parameter of various methods).
                Defaults to 1.
            setup_time: Time (in seconds) to sleep after discovering tables,
                giving each :class:`Table` instance time to fetch its column
                metadata before the constructor returns.  Defaults to 0.5.

        Raises:
            Exception: If the initial test connection fails (e.g. invalid path,
                permission denied).  Also raised if the subsequent master table
                query fails.

        Example:
            >>> driver = Driver('app.db', isolation_level='IMMEDIATE',
            ...                 none_block_reader_pool_size=3)
            >>> # Access a table directly
            >>> users = driver.users
            >>> # Use pragma helper
            >>> driver.SetPragma.journal_mode('WAL')
        """

        try:
            connector = connect(db_path , isolation_level=isolation_level , cached_statements=cache_size)
            connector.close()
        except Exception as e:
            raise Exception(e)
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_?_'
        self.db_path= db_path
        self.main_queue= SimpleQueue()
        self.wal_stop= Event()
        self.wal_enabled= Event()
        self.SetPragma= SetPragma(self)
        self.reader_pool_size = none_block_reader_pool_size
        self.pool_holder = SimpleQueue()
        self._connected = True
        for i in range(self.reader_pool_size):
            connection_queue = SimpleQueue()
            Thread(target=Driver.reader_driver, args=(connection_queue, self.db_path, isolation_level, cache_size)).start()
            self.pool_holder.put(connection_queue)
        Thread(target=Driver.simple_driver, args=(self.main_queue, self.db_path, isolation_level, cache_size)).start()
        QueueCallBack=SimpleQueue()
        self.main_queue.put(['qf', ('SELECT * FROM SQLITE_MASTER;',), QueueCallBack])
        if (callback:= QueueCallBack.get(block=True))[0]:
            [self.__setattr__(i[1], Table(self, i[1])) if i[0] == 'table' and i[1] != 'sqlite_sequence' else None for i in callback[1]]
            sleep(setup_time) #give Table objects some time to fetch from database and do __setattr__ 
        else:
            raise Exception(callback[1])
        
    def _exc(self, cmd: str, query: tuple) -> Any:
        """Send a command to the writer queue and return the result synchronously.

        This internal helper is the primary communication channel for all write
        operations.  It places a ``(cmd, query, callback_queue)`` tuple on
        :attr:`main_queue`, blocks until the writer thread has processed the
        request, and either returns the result or raises an exception.

        Args:
            cmd: A short string identifying the operation type. Supported values
                are ``'qf'`` (query‑fetch), ``'qcb'`` (query‑commit),
                ``'qsb'`` (script‑batch), ``'qmb'`` (executemany‑batch), and
                ``'cp'`` (checkpoint).  These map to the writer thread's
                ``match`` cases.
            query: The SQL statement and optional parameters. The exact format
                depends on *cmd*:
                - For ``'qf'`` and ``'qcb'``: ``(sql_statement,)`` or
                ``(sql_statement, parameters)``.
                - For ``'qsb'``: a list of such query tuples.
                - For ``'qmb'``: ``(sql_statement, sequence_of_parameters)``.

        Returns:
            The result produced by the writer thread:
            - For ``'qf'``, a list of rows (possibly empty).
            - For ``'qcb'``, ``'qsb'``, and ``'qmb'``, ``None`` on success.
            - For ``'cp'``, ``None`` (checkpoints are fire‑and‑forget from the
            caller's perspective).

        Raises:
            Exception: If the writer thread catches an exception during
                execution, it is re‑raised here with the original traceback
                message.  This includes SQLite operational errors, constraint
                violations, etc.

        Example:
            Usually called indirectly by higher‑level methods, but can be used
            for custom low‑level queries::

                driver = Driver('app.db')
                # Execute a simple PRAGMA
                driver._exc('qcb', ("PRAGMA user_version = 1;",))
                # Fetch results from a system table
                rows = driver._exc('qf', ('SELECT * FROM sqlite_master;',))
        """
        if not self._connected:
            raise RuntimeError("Driver Disconnected")
        queue_call_back = SimpleQueue()
        self.main_queue.put((cmd, query, queue_call_back))
        if (callback := queue_call_back.get(block=True))[0]:
            return callback[1]
        else:
            raise Exception(callback[1])

    @staticmethod
    def reader_driver(receiver: SimpleQueue, db_path: str, isolation_level: str, cache_size: int):
        """Run a dedicated reader thread that executes queries from a queue.

        This static method is intended to be started as a separate thread. It
        continuously listens on the *receiver* queue for commands of the form
        ``['qf', (sql, [params]), callback_queue]`` or ``['dc']`` (disconnect).
        Each read query is executed on its own SQLite connection, and the
        result (or exception) is put into the *callback_queue*.

        The method is used internally by :class:`Driver` to create the non‑blocking
        reader pool. Applications normally do not call it directly.

        Args:
            receiver: Queue from which the thread receives work items. Each item
                is a list ``[command, query_tuple, callback_queue]``.
            db_path: Path to the SQLite database file.
            isolation_level: SQLite isolation level (e.g. ``'DEFERRED'``).
            cache_size: Number of cached statements for the connection.

        Returns:
            None. The function runs an infinite loop until a ``'dc'`` command is
            received, at which point it returns.

        Raises:
            No exceptions are propagated; any errors during query execution are
            returned to the caller through the callback queue as
            ``(False, exception)``.

        Example:
            This method is launched by :meth:`Driver.__init__` when creating the
            reader pool. For every configured reader a thread similar to::

                Thread(
                    target=Driver.reader_driver,
                    args=(connection_queue, db_path, isolation_level, cache_size)
                ).start()

            is started. A typical command sent to the queue looks like::

                callback = SimpleQueue()
                connection_queue.put(['qf', ('SELECT * FROM users',), callback])
                success, data = callback.get()
        """

        while True:
            try:
                connector = connect(db_path , isolation_level=isolation_level , cached_statements=cache_size)
                cursor = connector.cursor()
                break
            except:
                pass
        while True:
            try:
                query = receiver.get(block=True, timeout=0.05)
                if query[0] == 'dc':
                    break
            except:
                continue
            try:
                query[2].put((True, cursor.execute(query[1][0]).fetchall())) if len(query[1]) == 1 else query[2].put((True, cursor.execute(query[1][0], query[1][1]).fetchall()))
            except Exception as e:
                query[2].put((False, e))

    @staticmethod
    def simple_driver(receiver: SimpleQueue, db_path: str, isolation_level: str, cache_size: int):
        """Runs the main writer thread that processes all database commands serially.

        This static method is intended to be executed in a dedicated background thread.
        It opens a single SQLite connection, creates a cursor, and then enters an
        infinite loop waiting for commands on `receiver`.  Each command is a tuple
        of the form ``(cmd, payload, callback_queue)``.  Supported ``cmd`` values:

        * ``'qf'`` – execute a query and return the fetched rows via the callback.
        * ``'qcb'`` – execute a statement and commit (or rollback on error).
        * ``'qsb'`` – execute a list of statements as a single transaction.
        * ``'qmb'`` – execute a parameterised statement with ``executemany``.
        * ``'cp'`` – force a WAL checkpoint (``PRAGMA wal_checkpoint(TRUNCATE)``).
        * ``'dc'`` – commit, signal shutdown, and break the loop.

        On any exception the transaction is rolled back and an ``(False, exception)``
        tuple is sent back through the callback queue.  Successful operations return
        ``(True, result)``.

        Args:
            receiver: A :class:`queue.SimpleQueue` from which the thread reads
                commands.  Each command is a list/tuple with three elements:
                the command string, the query (with optional parameters), and a
                callback :class:`queue.SimpleQueue` to receive the result.
            db_path: Path to the SQLite database file.
            isolation_level: The transaction isolation level (e.g.
                ``'DEFERRED'``, ``'IMMEDIATE'``, ``'EXCLUSIVE'``) passed to
                :func:`sqlite3.connect`.
            cache_size: Number of compiled statements to cache (``cached_statements``
                parameter).

        Returns:
            None.  The method blocks until a ``'dc'`` command is received and then
            returns.

        Raises:
            This method does not raise exceptions directly; all database errors are
            caught and reported through the callback queue.

        Example:
            Typically this method is not called directly by users.  It is started
            internally by the :class:`Driver` constructor::

                Thread(target=Driver.simple_driver,
                    args=(self.main_queue, db_path, isolation_level, cache_size)).start()

            To simulate a command from outside (for testing purposes) you might do::

                import queue
                receiver = queue.SimpleQueue()
                # start the thread
                thread = Thread(target=Driver.simple_driver,
                                args=(receiver, 'test.db', 'DEFERRED', 128))
                thread.start()
                # send a command
                callback = queue.SimpleQueue()
                receiver.put(('qcb', ('CREATE TABLE t(x INTEGER)',), callback))
                success, _ = callback.get()
                print(success)  # True
                # stop the thread
                receiver.put(('dc', None, callback))
                thread.join()
        """
        
        connector = connect(db_path , isolation_level=isolation_level , cached_statements=cache_size)
        cursor = connector.cursor()
        while True:
            try:
                try:
                    query = receiver.get(block=True, timeout=0.05)
                    cmd = query[0]
                except:
                    continue
                match cmd:
                    case 'qf':
                        try:
                            query[2].put((True, cursor.execute(query[1][0]).fetchall())) if len(query[1]) == 1 else query[2].put((True,cursor.execute(query[1][0], query[1][1]).fetchall()))
                        except Exception as e:
                            query[2].put((False, e))
                    case 'qcb':
                        try:
                            cursor.execute(query[1][0]) if len(query[1]) == 1 else cursor.execute(query[1][0], query[1][1])
                            connector.commit()
                            query[2].put((True, None))
                        except Exception as e:
                            connector.rollback()
                            query[2].put((False, e))
                    case 'qsb':
                        try:
                            [cursor.execute(i[0]) if len(i) == 1 else cursor.execute(i[0], i[1]) for i in query[1]]
                            connector.commit()
                            query[2].put((True, None))
                        except Exception as e:
                            connector.rollback()
                            query[2].put((False, e))
                    case 'qmb':
                        try:
                            cursor.executemany(query[1][0]) if len(query[1]) == 1 else cursor.executemany(query[1][0], query[1][1])
                            connector.commit()
                            query[2].put((True, None))
                        except Exception as e:
                            connector.rollback()
                            query[2].put((False, e))
                    case 'cp':
                        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                        query[1].put(True)
                    case 'dc':
                        try:
                            connector.commit()
                            query[1].put((True, None))
                        except Exception as e:
                            connector.rollback()
                            query[1].put((False, e))
                        break
            except Exception as e:
                print_exc()

    @staticmethod
    def checkpoint_timer(main_commit_queue: SimpleQueue, timer: int, stop: Event):
        """Continuously triggers WAL checkpoints at a fixed interval.

        This static method is designed to run in a dedicated thread.  It
        periodically sends a ``'cp'`` command (WAL checkpoint TRUNCATE) to
        the main writer queue, helping to keep the WAL file size under
        control when WAL mode is enabled.  The loop runs until the
        *stop* :class:`~threading.Event` is set.

        This is an internal helper called by :meth:`Driver.set_WAL_mode` and
        should not normally be invoked directly.

        Args:
            main_commit_queue: The :class:`queue.SimpleQueue` used by the
                writer thread.  A ``['cp', callback_queue]`` message is
                placed into this queue to request a checkpoint.
            timer: Number of seconds to sleep between consecutive checkpoint
                requests.
            stop: A :class:`~threading.Event` that signals the loop to
                terminate.  When set, the function prints a message and
                returns.

        Returns:
            None: The function does not return; it blocks indefinitely until
            the stop event is signalled.

        Example:
            This function is started automatically when WAL mode is activated:

            >>> driver = Driver('app.db')
            >>> driver.set_WAL_mode(True, wal_timer=30)
            # Internally starts a thread running checkpoint_timer
        """

        while True:
            if stop.is_set():
                print('checkpoint stopped')
                break
            sleep(timer)
            call_back_queue = SimpleQueue()
            main_commit_queue.put(['cp', call_back_queue])
            try:
                call_back_queue.get(timeout=5.0)
            except:
                pass

    def table_object(self, table_name: str) -> 'Table':
        """Returns a :class:`Table` instance for the given table name.

        This method looks up the table in the database by calling
        :meth:`get_tables` and returns a freshly‑constructed
        :class:`Table` object.  It is useful when you need to work with
        a table that was not automatically exposed as an attribute of the
        :class:`Driver` instance, or when you prefer explicit access.

        Args:
            table_name: The exact name of the table (case‑sensitive) as
                it appears in the SQLite schema.

        Returns:
            A :class:`Table` object bound to this driver and the named
            table.  All column attributes are immediately available.

        Raises:
            Exception: If there are no tables at all in the database
                (``'No table found'``).
            Exception: If the requested *table_name* does not exist
                (``'No such table named …'``).

        Example:
            >>> driver = Driver('app.db')
            >>> # if table 'logs' is not already driver.logs
            >>> logs = driver.table_object('logs')
            >>> print(logs.get_columns_name())
            ['timestamp', 'message', 'level']
        """

        tables = self.get_tables()
        if not table_name in tables:
            if len(tables) == 0:
                raise Exception(f'No table found')
            raise Exception(f'No such table named {table_name} in this db')
        return Table(self, table_name)

    def custom_execute(self, query: str, params: list = None) -> None:
        """Execute a raw SQL statement on the main writer connection.

        Sends *query* and optional *params* to the background writer thread.
        The statement is committed immediately if it succeeds; on failure the
        transaction is rolled back and an exception is raised.

        Args:
            query: The SQL statement to execute.  May contain ``?``
                placeholders if *params* is supplied.
            params: A list of values to bind to the placeholders in *query*.
                Defaults to ``None``.

        Raises:
            Exception: If the writer thread encounters an error (e.g. syntax
                error, constraint violation).  The underlying exception
                message is propagated.

        Example:
            >>> driver = Driver('app.db')
            >>> driver.custom_execute('PRAGMA user_version = 1')
            >>> driver.custom_execute(
            ...     'INSERT INTO logs (message) VALUES (?)',
            ...     ['startup complete']
            ... )
        """

        return self._exc('qcb', (query, params)) if params else self._exc('qcb', (query,))
        
    def custom_execute_many(self, query: str, params: list = None) -> None:
        """Execute a raw SQL statement with multiple parameter sets (``executemany``).

        Sends the statement and the list of parameter sequences to the writer
        queue for execution inside a single transaction.  This is the
        recommended way to run bulk inserts, updates, or deletes that require
        multiple parameter sets but only one SQL command.

        Args:
            query: The SQL query string.  It must contain placeholders
                (``?``) that will be replaced by the elements of each
                parameter tuple in *params*.
            params: A list of tuples (or lists) where each element
                provides the values for one execution of the statement.
                If omitted or ``None``, the statement is executed once
                with no parameters (effectively the same as
                :meth:`custom_execute`).

        Returns:
            ``None``.  The operation is performed asynchronously; if it
            fails an exception will be raised.

        Raises:
            Exception: If the statement execution fails.  The exception
                contains the original SQLite error message.

        Example:
            >>> driver = Driver('app.db')
            >>> driver.custom_execute(
            ...     'CREATE TABLE logs (message TEXT, level INTEGER)'
            ... )
            >>> data = [("startup", 1), ("shutdown", 2), ("error", 3)]
            >>> driver.custom_execute_many(
            ...     'INSERT INTO logs VALUES (?, ?)',
            ...     data
            ... )
        """
        if params is None:
            return self._exc('qcb', (query,))
        if not params:
            return  
        self._exc('qmb', (query, params))

    def custom_execute_with_fetch(self, query: str, params: list = None, from_readers_pool: bool = False) -> Any:
        """Execute an arbitrary SQL query and return the fetched rows.

        This is a low‑level method that submits a read query (typically a
        ``SELECT``) to the worker thread infrastructure.  By default it uses the
        main writer thread; when *from_readers_pool* is ``True`` it borrows a
        connection from the non‑blocking reader pool, which is useful for
        long‑running queries that should not block other writers.

        Args:
            query: The SQL statement to execute (usually a ``SELECT``).
            params: Optional list or tuple of bind parameters to substitute
                into *query* (using SQLite ``?`` placeholders).  Defaults to
                ``None``.
            from_readers_pool: If ``True`` the query is executed on a reader
                pool connection; otherwise the main writer thread is used.
                Defaults to ``False``.

        Returns:
            The result of ``cursor.fetchall()`` after executing the query.
            Typically a list of tuples (one tuple per row).  The exact format
            depends on the SQL statement.

        Raises:
            Exception: If the underlying worker reports an error (e.g.
                malformed SQL, missing table, or parameter mismatch).

        Example:
            >>> driver = Driver('app.db')
            >>> rows = driver.custom_execute_with_fetch(
            ...     "SELECT name FROM users WHERE age > ?", [18]
            ... )
            >>> # Use the reader pool to avoid blocking the writer
            >>> heavy = driver.custom_execute_with_fetch(
            ...     "SELECT * FROM large_logs WHERE processed = 0",
            ...     from_readers_pool=True
            ... )
        """

        if not from_readers_pool:
            return self._exc('qf', (query,params)) if params else self._exc('qf', (query,))
        else:
            queueCallBack = SimpleQueue()
            connection_queue = self.pool_holder.get(block=True)
            connection_queue.put(['qf', (query,params), queueCallBack]) if params else connection_queue.put(['qf', (query,), queueCallBack])
            self.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return callback[1]
            else:
                raise Exception(callback[1])

    def get_tables(self) -> dict[str, 'Table']:
        """Retrieve a dictionary of all user tables in the database.

        Queries the ``SQLITE_MASTER`` table via
        :meth:`custom_execute_with_fetch` and returns a mapping from table
        name (string) to :class:`Table` instance for every table that is not
        the internal ``sqlite_sequence``.  The :class:`Table` objects are
        freshly constructed and have their column attributes populated.

        Returns:
            A dictionary where keys are table names (``str``) and values
            are corresponding :class:`Table` objects.

        Raises:
            Exception: Propagated from the underlying writer thread if the
                ``SQLITE_MASTER`` query fails.

        Example:
            >>> driver = Driver('app.db')
            >>> all_tables = driver.get_tables()
            >>> for name, tbl in all_tables.items():
            ...     print(f'{name}: {len(tbl.get_columns_name())} columns')
            users: 5 columns
            orders: 8 columns
        """

        tables_list = self.custom_execute_with_fetch('SELECT * FROM SQLITE_MASTER;')
        tables_dict = {}
        for item in tables_list:
            if item[0] == 'table' and not item[1] == 'sqlite_sequence':
                tables_dict[item[1]] = Table(self, item[1])
        return tables_dict

    def create_table(self, table_structure: 'TableStructure') -> 'Table':
        """Creates a new table in the database from a :class:`TableStructure` definition.

        Executes the ``CREATE TABLE`` statement generated by
        :meth:`TableStructure.get_structure`, then immediately makes the
        table accessible as an attribute of the driver instance (e.g.
        ``driver.new_table``) and returns the corresponding :class:`Table`
        object.  All column metadata is fetched and attached to the table.

        Args:
            table_structure: A fully configured :class:`TableStructure`
                instance describing the columns, constraints, foreign keys,
                and strict mode setting.

        Returns:
            :class:`Table`: The newly created table object, ready for
            inserts, updates, queries, etc.

        Raises:
            Exception: Propagated from the writer thread if the SQL
                execution fails (e.g. syntax error in the structure,
                duplicate table name, or violation of database constraints).

        Example:
            >>> structure = TableStructure('employees', strict=True)
            >>> structure.add_column('id', DataTypes.INTEGER(), primary_key=True)
            >>> structure.add_column('name', DataTypes.TEXT(max_length=100))
            >>> structure.add_column('salary', DataTypes.REAL(min_val=0.0))
            >>> driver = Driver('company.db')
            >>> emp_table = driver.create_table(structure)
            >>> # Now driver.employees is also available
            >>> driver.employees.insert({emp_table.name: 'John'})
        """

        self._exc('qcb', (table_structure.get_structure(),))
        self.__setattr__(table_structure.name, Table(self,table_structure.name))
        return Table(self, table_structure.name)

    def defragment(self) -> None:
        """Rebuilds the database file and updates statistics for the query planner.

        Executes the SQLite ``VACUUM`` command followed by ``PRAGMA optimize``.
        ``VACUUM`` rebuilds the entire database, reclaiming unused space and
        defragmenting the file.  ``PRAGMA optimize`` analyzes the database
        and updates internal statistics to help the query planner choose
        efficient execution plans.

        Returns:
            None.  The operation is performed synchronously on the writer
            thread.

        Raises:
            Exception: If either the ``VACUUM`` or ``PRAGMA optimize``
                command fails (e.g. disk full, permission error).

        Example:
            >>> driver = Driver('my_data.db')
            >>> driver.defragment()
            # The database file is now compacted and optimized.
        """
        self._exc('qcb', ("VACUUM;",))
        self._exc('qcb', ("PRAGMA optimize;",))

    def set_WAL_mode(self, is_set: bool, wal_timer: int = 1) -> None:
        """Enables or disables Write‑Ahead Logging (WAL) mode.

        When enabled, the journal mode is set to ``WAL`` and a background
        thread periodically performs truncate checkpoints (see
        :meth:`checkpoint_timer`).  When disabled, the checkpoint timer is
        stopped, journal mode is switched back to ``PERSIST``, and a final
        manual checkpoint is executed.

        Args:
            is_set: ``True`` to enable WAL mode, ``False`` to disable it.
            wal_timer: Interval in seconds between automatic checkpoints
                while WAL is active.  Ignored when ``is_set`` is ``False``.
                Defaults to 60.

        Returns:
            None.

        Raises:
            Exception: Propagated from the writer thread if a ``PRAGMA``
                statement fails (e.g. database is locked).

        Example:
            >>> driver = Driver('mydb.db')
            >>> # Enable WAL with 30‑second checkpoints
            >>> driver.set_WAL_mode(True, wal_timer=30)
            >>> # ... perform heavy writes ...
            >>> # Disable WAL and return to PERSIST
            >>> driver.set_WAL_mode(False)
        """

        if is_set:
            self.wal_enabled.set()
            self.wal_stop.clear()
            self._exc('qcb', ("PRAGMA journal_mode=WAL;",))
            Thread(target=Driver.checkpoint_timer, args=(self.main_queue, wal_timer, self.wal_stop), daemon=True).start()
        else:
            self.wal_stop.set()
            self._exc('qcb', ("PRAGMA journal_mode=PERSIST;",))
        call_back_queue = SimpleQueue()
        self.main_queue.put(['cp', call_back_queue])
        call_back_queue.get(block=True)

    def disconnect(self) -> None:
        """Gracefully shut down the database connection and all worker threads.

        This method shuts down the driver in a controlled order:

        1. It signals any active WAL-checkpoint timer to stop.
        2. If WAL mode was enabled, it triggers a final checkpoint through the
           main writer thread and waits for completion.
        3. It sends a disconnect command to the writer thread so pending work
           is committed and the connection is closed.
        4. It sends disconnect commands to every reader-pool connection so the
           reader threads can exit cleanly.

        After this call, the driver instance should no longer be used.

        Raises:
            Exception: May propagate exceptions from the writer thread if the
                final commit or rollback fails.

        Example:
            >>> driver = Driver('app.db')
            >>> driver.disconnect()
        """
        if not self._connected:
            raise RuntimeError("Driver Already Disconnected")
        self.wal_stop.set()
        callback_dc = SimpleQueue()
        self._connected = False
        if self.wal_enabled.is_set():
            call_back_queue = SimpleQueue()
            self.main_queue.put(['cp', call_back_queue])
            self.main_queue.put(['dc' , callback_dc])
            call_back_queue.get(block=True)
        else:
            self.main_queue.put(['dc' , callback_dc])
        callback_dc.get(block=True)
        for i in range(self.reader_pool_size):
            connection_queue = self.pool_holder.get(block=True)
            connection_queue.put(['dc'])
