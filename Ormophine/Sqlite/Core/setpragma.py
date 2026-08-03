from __future__ import annotations
from .. import SimpleQueue

class SetPragma:
    """
    A wrapper for executing SQLite PRAGMA commands on a database connection.

    This class provides convenient methods for setting various SQLite
    PRAGMA configurations, such as journal mode, synchronous mode, cache
    size, WAL settings, foreign key enforcement, and schema write access.
    All PRAGMA commands are executed via the main database queue, ensuring
    thread‑safe operations.

    The class is typically accessed through the :attr:`Driver.SetPragma`
    attribute, which is automatically created when a :class:`Driver`
    instance is initialized.

    Attributes:
        queue (SimpleQueue): The main queue of the :class:`Driver`
            instance used to send PRAGMA commands to the database thread.

    Example:
        Assuming a :class:`Driver` instance named ``db``::

            from ormophine.Sqlite import Driver

            db = Driver('my_database.db')

            # Set journal mode to WAL for better concurrency
            db.SetPragma.journal_mode('WAL')

            # Increase cache size to 10000 pages
            db.SetPragma.cache_size(10000)

            # Enable foreign key constraints
            db.SetPragma.foreign_keys(True)

            # Run a WAL checkpoint
            db.SetPragma.wal_checkpoint('FULL')

            # Optimize the database
            db.SetPragma.optimize()
    """
    
    def __init__(self, connector_obj):
        """Initialize a new SetPragma instance.

        This class provides methods to configure SQLite PRAGMA settings
        (e.g., journal mode, synchronous, cache size) for the database
        connection. The constructor stores a reference to the connector's
        main queue, which is used to execute PRAGMA statements in a
        thread‑safe manner via the database driver thread.

        Args:
            connector_obj: The parent object (typically an instance of
                :class:`Driver`) that holds the main queue used for
                sending commands to the database thread. The object must
                have a ``main_queue`` attribute of type :class:`queue.SimpleQueue`.

        Example:
            Assuming a ``Driver`` instance named ``db``::

                from ormophine.Sqlite import Driver

                db = Driver('my_database.db')
                pragma = db.SetPragma

                # Configure the database
                pragma.journal_mode('WAL')
                pragma.synchronous('NORMAL')
                pragma.cache_size(10000)

        Note:
            The ``connector_obj`` is typically the :class:`Driver` instance
            that owns this ``SetPragma`` object. It is used internally to
            send PRAGMA commands to the database thread.
        """
        self.queue = connector_obj.main_queue

    def _exc(self, cmd: str, query: tuple):
        """Execute a database command and return the result.

        This internal method sends a command (with its query and parameters)
        to the database connection queue, blocks until the operation completes,
        and returns the result if successful, or raises an exception if the
        operation fails.

        The method is used by all public pragma‑setting methods in
        :class:`SetPragma` to centralize queue communication and error handling.

        Args:
            cmd (str): The command type to execute. Expected values are
                ``'qcb'`` (execute a single query that does not return rows),
                but other command types may be supported depending on the
                driver implementation.
            query (tuple): A tuple containing the SQL query and optional
                parameters. Typically of the form ``(sql_string,)`` or
                ``(sql_string, params)``.

        Returns:
            Any: The result returned by the database operation. For
            pragma statements, this is usually ``None`` on success, but
            may be a result set for other command types.

        Raises:
            Exception: If the callback indicates failure, the exception
                message from the callback is re‑raised.

        Example:
            >>> sp = SetPragma(driver)
            >>> sp._exc('qcb', ('PRAGMA journal_mode=WAL;',))
            >>> #OR driver.Setpragma._exc('qcb', ('PRAGMA journal_mode=WAL;',))
            None
        """
        queue_call_back = SimpleQueue()
        self.queue.put((cmd, query, queue_call_back))
        if (callback := queue_call_back.get(block=True))[0]:
            return callback[1]
        else:
            raise Exception(callback[1])

    def journal_mode(self, value: Literal["DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"]):
        """Set the journal mode for the database connection.

        This method executes the SQLite ``PRAGMA journal_mode`` command to
        change the way the database handles rollback journals. The journal
        mode affects performance, durability, and concurrency behavior.

        The available modes correspond to SQLite's standard journal modes:

        * ``DELETE`` – the default, a rollback journal is deleted after each transaction.
        * ``TRUNCATE`` – the journal is truncated to zero length instead of deleted.
        * ``PERSIST`` – the journal header is overwritten, avoiding file deletion.
        * ``MEMORY`` – the journal is stored in memory (fast but not durable).
        * ``WAL`` – Write-Ahead Logging, provides better concurrency.
        * ``OFF`` – no journaling (dangerous, can lead to corruption).

        The PRAGMA is executed synchronously, and the change takes effect
        immediately for the current database connection.

        Args:
            value (Literal["DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"]):
                The journal mode to set. Must be one of the allowed strings.

        Returns:
            None

        Raises:
            Exception: If the PRAGMA execution fails. The exception message
                will contain the underlying SQLite error.

        Example:
            Assuming a :class:`Driver` instance named ``db``::

                # Switch to WAL mode for better concurrency
                db.SetPragma.journal_mode('WAL')

                # Switch back to DELETE mode
                db.SetPragma.journal_mode('DELETE')
        """
        self._exc('qcb', (f"PRAGMA journal_mode = {value};",))

    def synchronous(self, value: Literal["OFF", "NORMAL", "FULL", "EXTRA"]):
        """Set the database synchronization mode.

        This method configures the SQLite ``synchronous`` pragma, which controls
        how aggressively the database engine writes data to disk. Higher levels
        provide better durability but may reduce performance.

        The available modes are:
            - ``OFF``: No synchronization, fastest but unsafe on power loss.
            - ``NORMAL``: Synchronizes at critical moments, a good balance.
            - ``FULL``: Maximum safety, ensures all data is written to disk
            before continuing.
            - ``EXTRA``: Even more synchronous than ``FULL`` (available in
            some SQLite versions).

        Args:
            value (Literal["OFF", "NORMAL", "FULL", "EXTRA"]): The
                synchronization level to set.

        Returns:
            None

        Raises:
            Exception: If the underlying SQLite operation fails, the exception
                is propagated from :meth:`_exc`.

        Example:
            Assuming a :class:`Driver` instance::

                from ormophine.Sqlite import Driver

                db = Driver('app.db')
                # Set to NORMAL for a balance of safety and performance
                db.SetPragma.synchronous('NORMAL')

                # Set to OFF for maximum performance (use with caution)
                db.SetPragma.synchronous('OFF')
        """
        self._exc('qcb', (f"PRAGMA synchronous = {value};",))

    def wal_autocheckpoint(self, pages: int):
        """Set the WAL autocheckpoint threshold.

        This method configures the number of pages after which SQLite
        automatically runs a checkpoint on the Write-Ahead Log (WAL). When
        the WAL file reaches the specified number of pages, SQLite will
        checkpoint the database, moving pages from the WAL file back into
        the main database file.

        Setting this value to 0 disables automatic checkpoints, leaving
        manual checkpointing via :meth:`wal_checkpoint` as the only option.

        Args:
            pages (int): The number of pages in the WAL file that trigger
                an automatic checkpoint. Must be a non-negative integer.
                A value of 0 disables automatic checkpointing.

        Raises:
            ValueError: If ``pages`` is not an integer or is negative.

        Example:
            .. code-block:: python

                from ormophine.Sqlite import Driver

                db = Driver('my_database.db')
                # Set autocheckpoint every 1000 pages
                db.SetPragma.wal_autocheckpoint(1000)

                # Disable automatic checkpoints
                db.SetPragma.wal_autocheckpoint(0)
        """
        if not isinstance(pages, int) or pages < 0:
            raise ValueError("pages must be non-negative integer")
        self._exc('qcb', (f"PRAGMA wal_autocheckpoint = {pages};",))

    def wal_checkpoint(self, mode: Literal["PASSIVE", "FULL", "RESTART", "TRUNCATE"] = "PASSIVE"):
        """Run a WAL checkpoint on the database.

        A WAL (Write-Ahead Log) checkpoint ensures that all transactions in
        the WAL file are written to the main database file. This can help
        reclaim disk space and improve performance. The mode determines how
        the checkpoint is performed:

        * ``PASSIVE`` – Checkpoint as many frames as possible without
        blocking other readers or writers. This is the default.
        * ``FULL`` – Checkpoint all frames, but may block other operations.
        * ``RESTART`` – Like FULL, but also restarts the WAL file so that
        future writes use a fresh WAL.
        * ``TRUNCATE`` – Like RESTART, but also truncates the WAL file to
        zero bytes, freeing disk space.

        This method sends a ``PRAGMA wal_checkpoint`` command to the database
        thread and waits for it to complete.

        Args:
            mode (Literal["PASSIVE", "FULL", "RESTART", "TRUNCATE"], optional):
                The checkpoint mode. Defaults to ``"PASSIVE"``.

        Returns:
            None

        Raises:
            Exception: If the checkpoint fails, an exception is raised with
                the underlying SQLite error message.

        Example:
            Assuming a :class:`Driver` instance named ``db``::

                from ormophine.Sqlite import Driver

                db = Driver('my_database.db')

                # Run a full checkpoint
                db.SetPragma.wal_checkpoint('FULL')

                # Or use the default passive checkpoint
                db.SetPragma.wal_checkpoint()
        """
        self._exc('qcb', (f"PRAGMA wal_checkpoint({mode});",))

    def foreign_keys(self, enable: bool | Literal["ON", "OFF"]):
        """Enable or disable foreign key constraint enforcement.

        This method sets the ``PRAGMA foreign_keys`` option for the current
        database connection. When enabled (``ON``), SQLite will enforce
        foreign key constraints, rejecting operations that violate referential
        integrity. When disabled (``OFF``), foreign key constraints are
        ignored.

        The setting can be provided as a boolean (``True``/``False``) or as a
        string literal (``"ON"``/``"OFF"``). The method sends the appropriate
        PRAGMA command to the database thread and waits for execution.

        Args:
            enable (bool | Literal["ON", "OFF"]): Whether to enable foreign
                key enforcement. Accepts:
                - ``True`` or ``"ON"`` to enable.
                - ``False`` or ``"OFF"`` to disable.

        Returns:
            None

        Raises:
            Exception: If the PRAGMA command fails, an exception is raised
                with the underlying SQLite error message.

        Example:
            Assuming a :class:`Driver` instance named ``db``::

                from ormophine.Sqlite import Driver

                db = Driver('my_database.db')

                # Enable foreign keys
                db.SetPragma.foreign_keys(True)

                # Disable foreign keys
                db.SetPragma.foreign_keys('OFF')

            Foreign key enforcement is often required for maintaining data
            integrity across related tables. Use this method to toggle the
            setting as needed for your operations.
        """
        val = "ON" if enable is True or enable == "ON" else "OFF"
        self._exc('qcb', (f"PRAGMA foreign_keys = {val};",))

    def defer_foreign_keys(self, enable: bool | Literal["ON", "OFF"]):
        """Enable or disable deferred foreign key enforcement.

        This method sets the ``PRAGMA defer_foreign_keys`` option, which controls
        whether foreign key constraints are deferred until the transaction is
        committed. When enabled (``ON``), foreign key constraints are not checked
        immediately after each statement, but only when the transaction is
        committed. This can be useful for complex operations that temporarily
        violate foreign key constraints during a transaction.

        The method accepts either a boolean (``True`` for ON, ``False`` for OFF)
        or the strings ``"ON"`` or ``"OFF"``.

        Args:
            enable (bool | Literal["ON", "OFF"]): The desired state. If ``True``
                or ``"ON"``, defer foreign key enforcement. If ``False`` or
                ``"OFF"``, enforce foreign keys immediately (default behavior).

        Returns:
            None

        Raises:
            Exception: If the pragma execution fails, an exception is raised
                with the underlying SQLite error message.

        Example:
            Assuming a :class:`Driver` instance named ``db``::

                from ormophine.Sqlite import Driver

                db = Driver('my_database.db')

                # Enable deferred foreign keys
                db.SetPragma.defer_foreign_keys(True)

                # Perform operations that may temporarily violate foreign keys
                db.custom_execute('DELETE FROM orders WHERE customer_id = 1')
                db.custom_execute('DELETE FROM customers WHERE id = 1')

                # Commit automatically when the operation finishes,
                # and foreign key constraints are checked at commit time.

                # Disable deferred foreign keys
                db.SetPragma.defer_foreign_keys('OFF')
        """
        val = "ON" if enable is True or enable == "ON" else "OFF"
        self._exc('qcb', (f"PRAGMA defer_foreign_keys = {val};",))

    def cache_size(self, pages_or_kb: int):
        """Set the suggested maximum number of database disk pages that SQLite
        will hold in memory at one time.

        This method executes the `PRAGMA cache_size` command, which controls the
        number of pages in the page cache. A larger cache can improve performance
        for read-heavy workloads by reducing disk I/O, but consumes more memory.

        The value can be specified as either:
        - Positive integer: number of pages (default page size is usually 4096 bytes).
        - Negative integer: number of kilobytes of cache memory (e.g., -1024 means 1 MiB).

        The change is temporary and lasts only for the current database connection;
        it is not persisted across restarts.

        Args:
            pages_or_kb (int): The cache size. Positive values are interpreted as
                number of pages; negative values as kilobytes. For example,
                ``1000`` sets the cache to 1000 pages, while ``-1024`` sets it to
                1 MiB.

        Returns:
            None

        Raises:
            Exception: If the PRAGMA execution fails (e.g., due to a database error),
                an exception is raised with the underlying error message.

        Example:
            Assuming a :class:`Driver` instance named ``db``::

                from ormophine.Sqlite import Driver

                db = Driver('my_database.db')

                # Set cache to 5000 pages
                db.SetPragma.cache_size(5000)

                # Set cache to 2 MiB (negative value means kilobytes)
                db.SetPragma.cache_size(-2048)
        """
        self._exc('qcb', (f"PRAGMA cache_size = {pages_or_kb};",))

    def mmap_size(self, bytes_size: int):
        """Set the maximum number of bytes used for memory-mapped I/O.

        This method configures the SQLite ``mmap_size`` pragma, which controls
        the maximum size of the memory-mapped I/O region for the database.
        Memory-mapped I/O can improve performance by allowing the operating
        system to cache database pages more efficiently. Setting this value
        to 0 disables memory-mapped I/O.

        The change takes effect immediately and persists until the database
        connection is closed or the pragma is set again.

        Args:
            bytes_size (int): The maximum size in bytes for the memory-mapped
                I/O region. Must be non-negative. A value of 0 disables
                memory-mapped I/O.

        Returns:
            None

        Raises:
            ValueError: If ``bytes_size`` is negative.
            Exception: If the underlying SQLite command fails (e.g., due to a
                database error), an exception with the error message is raised.

        Example:
            Assuming a :class:`Driver` instance named ``db``::

                from ormophine.Sqlite import Driver

                db = Driver('my_database.db')

                # Enable memory-mapped I/O with a 256 MB limit
                db.SetPragma.mmap_size(256 * 1024 * 1024)

                # Disable memory-mapped I/O
                db.SetPragma.mmap_size(0)
        """
        if bytes_size < 0:
            raise ValueError("mmap_size cannot be negative")
        self._exc('qcb', (f"PRAGMA mmap_size = {bytes_size};",))

    def shrink_memory(self):
        """Release unused memory back to the operating system.

        This method executes the SQLite ``PRAGMA shrink_memory`` command,
        which attempts to free as much memory as possible from the database
        connection's internal caches and buffers. This can be useful in
        long‑running applications to reduce memory footprint after large
        operations.

        The command is non‑blocking and does not affect the database content.
        It is a best‑effort operation; the actual amount of memory freed
        depends on the system and SQLite's internal state.

        Returns:
            None

        Raises:
            Exception: If the pragma execution fails, an exception is raised
                with the underlying SQLite error message.

        Example:
            Assuming a :class:`Driver` instance named ``db``::

                from ormophine.Sqlite import Driver

                db = Driver('my_database.db')

                # Perform memory‑intensive operations...
                # Then release unused memory
                db.SetPragma.shrink_memory()
        """
        self._exc('qcb', (f"PRAGMA shrink_memory;",))

    def optimize(self, mask: int = 0x10002):
        """Run the SQLite ``PRAGMA optimize`` command to optimize the database.

        This pragma triggers query planner optimizations and can improve
        performance by updating statistics and indexes. The optional
        ``mask`` parameter controls which optimizations are applied.
        The default value (``0x10002``) is recommended for general use.

        Args:
            mask (int, optional): A bitmask specifying the optimization
                settings. Defaults to ``0x10002``. Refer to SQLite
                documentation for valid mask values.

        Returns:
            None

        Raises:
            Exception: If the PRAGMA execution fails, an exception is
                raised with the underlying SQLite error message.

        Example:
            Assuming a :class:`Driver` instance named ``db``::

                from ormophine.Sqlite import Driver

                db = Driver('my_database.db')

                # Run optimize with default mask
                db.SetPragma.optimize()

                # Run optimize with a custom mask
                db.SetPragma.optimize(mask=0x0001)
        """
        self._exc('qcb', (f"PRAGMA optimize({mask});",))

    def automatic_index(self, enable: bool | Literal["ON", "OFF"]):
        """Enable or disable automatic index creation by the SQLite query planner.

        This method sets the ``PRAGMA automatic_index``, which controls whether
        SQLite automatically creates temporary indexes to speed up queries when
        it determines they would be beneficial. Enabling this can improve
        performance for complex queries but may add overhead for index creation.

        Args:
            enable (bool | Literal["ON", "OFF"]): Whether to enable automatic
                indexing. Accepts:
                - ``True`` or ``"ON"`` to enable.
                - ``False`` or ``"OFF"`` to disable.

        Returns:
            None

        Raises:
            Exception: If the PRAGMA execution fails, an exception is raised
                with the underlying SQLite error message.

        Example:
            Assuming a :class:`Driver` instance named ``db``::

                from ormophine.Sqlite import Driver

                db = Driver('my_database.db')

                # Enable automatic indexing
                db.SetPragma.automatic_index(True)

                # Disable it
                db.SetPragma.automatic_index('OFF')
        """
        val = "ON" if enable is True or enable == "ON" else "OFF"
        self._exc('qcb', (f"PRAGMA automatic_index = {val};",))

    def writable_schema(self, value: bool | Literal["ON", "OFF", "RESET"]):
        """Enable, disable, or reset write access to the database schema.

        This method executes the SQLite ``PRAGMA writable_schema`` command,
        which controls whether the ``sqlite_master`` table (the schema table)
        can be modified. By default, it is disabled (``OFF``). Enabling it
        allows direct modifications to the schema, which is useful for
        debugging or recovery but is extremely dangerous and should be used
        with caution. The ``RESET`` value reverts the pragma to its default
        state.

        Args:
            value (bool | Literal["ON", "OFF", "RESET"]): The desired state.
                - ``True`` or ``"ON"`` – enable writable schema.
                - ``False`` or ``"OFF"`` – disable writable schema.
                - ``"RESET"`` – reset to the default (effectively OFF).

        Returns:
            None

        Raises:
            Exception: If the PRAGMA execution fails, an exception is raised
                with the underlying SQLite error message.

        Example:
            Assuming a :class:`Driver` instance named ``db``::

                from ormophine.Sqlite import Driver

                db = Driver('my_database.db')

                # Enable writable schema (use with extreme caution!)
                db.SetPragma.writable_schema(True)

                # Perform schema modifications (e.g., manually update sqlite_master)
                # ... (dangerous operations)

                # Disable when done
                db.SetPragma.writable_schema(False)

                # Or reset to default
                db.SetPragma.writable_schema('RESET')
        """
        if value == "RESET":
            v = "RESET"
        else:
            v = "ON" if value is True or value == "ON" else "OFF"
        self._exc('qcb', (f"PRAGMA writable_schema = {v};",))
