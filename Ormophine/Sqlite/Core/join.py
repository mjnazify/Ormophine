from __future__ import annotations
from queue import SimpleQueue
from typing import Any
from .. import Column, ColumnsOperation


class JoinQuery:
    """
    Immutable, fluent builder for SQL ``JOIN`` queries with automatic table aliasing.

    :class:`JoinQuery` is the object returned by :meth:`Table.inner_join`,
    :meth:`Table.left_join`, and :meth:`Table.right_join`.  It collects one
    or more join descriptors and, when the user finally calls
    :meth:`get_row`, renders a complete ``SELECT ... FROM ... JOIN ...
    WHERE ... ORDER BY ... LIMIT ... OFFSET ...`` statement and executes it
    on the underlying driver.

    Why a dedicated class?
    ----------------------

    * **Chainable joins.**  Multiple joins can be layered on top of each
      other without writing the SQL by hand::

          q = users.inner_join(orders, orders.user_id == users.id) \\
                   .left_join(payments, payments.order_id == orders.id)

    * **Safe self‑joins.**  Joining the *same* :class:`Table` object twice
      normally produces ambiguous SQL (two ``[orders]`` references in the
      same statement).  :class:`JoinQuery` detects this situation and
      automatically assigns a unique alias (``orders_0``, ``orders_1``,
      …), rewriting every reference to the aliased table inside ON
      conditions, the SELECT list, the WHERE clause, and the ORDER BY
      clause.

    * **Immutable-style chaining.**  Every call to :meth:`inner_join`,
      :meth:`left_join`, or :meth:`right_join` returns a **new**
      :class:`JoinQuery` instance; the receiver is never mutated.  This
      makes it safe to fork a base join and build several independent
      queries from it::

          base = users.inner_join(orders, orders.user_id == users.id)
          q_active = base.get_row([users.name], where=users.active == 1)
          q_recent = base.get_row([users.name], where=orders.total > 1000)

    * **Expression support.**  Both plain :class:`Column` objects and
      :class:`ColumnsOperation` expressions can be used in the SELECT list,
      the WHERE clause, and the ORDER BY clause.  Table references inside
      expressions are rewritten to the correct alias automatically.

    Attributes:
        table_obj (Table): The base (left‑hand) table of the join chain.
            This becomes the ``FROM`` table in the generated SQL.
        joins (list[dict]): An internal list of join descriptors.  Each
            entry is a dictionary with the keys ``'type'`` (e.g.
            ``'INNER JOIN'``), ``'table'`` (a :class:`Table`),
            ``'condition'`` (a :class:`ColumnsOperation`), and ``'alias'``
            (a string or ``None``).
        params (list): The accumulated parameter values from every join's
            ON condition, in the order the joins were added.
        _output (tuple): A ``(join_sql_fragment, params)`` tuple, computed
            eagerly when the object is constructed.  Mostly an internal
            detail.

    Column aliasing in the result
    -----------------------------

    When :meth:`get_row` is called, every plain :class:`Column` in
    ``which_columns`` is aliased in the output as
    ``<table>_<column>`` (e.g. ``users_name``, ``orders_total``) so that
    columns with the same name in different tables do not collide.  This
    matters if you plan to feed the result into another layer that reads
    by column name.

    Example — basic usage::

        from ormophine.Sqlite import Driver

        db = Driver('shop.db')
        users = db.users
        orders = db.orders

        # A single INNER JOIN
        rows = users.inner_join(
            orders, orders.user_id == users.id
        ).get_row([users.name, orders.total])
        # rows -> [('Alice', 150.0), ('Bob', 200.0), ...]

    Example — chained joins::

        payments = db.payments
        rows = (
            users
            .inner_join(orders,  orders.user_id  == users.id)
            .left_join(payments, payments.order_id == orders.id)
            .get_row([users.name, orders.total, payments.amount])
        )

    Example — self‑join with automatic alias::

        # Find each user's manager (both live in the same table)
        rows = users.inner_join(
            users, users.manager_id == users.id
        ).get_row([users.name, users.name])
        # The second `users` is aliased to `users_0` automatically,
        # and its columns are rewritten to `[users_0].[...]`.

    Example — WHERE / ORDER BY / LIMIT / OFFSET::

        rows = users.inner_join(
            orders, orders.user_id == users.id
        ).get_row(
            [users.name, orders.total],
            where=orders.total > 100,
            order_by=orders.total,
            limit=10,
            offset=5,
        )

    Example — expression columns and ``order_by`` with ``ColumnsOperation``::

        # SELECT users.[name] || '!', orders.[total] * 1.1
        # ORDER BY the computed discounted total
        rows = users.inner_join(
            orders, orders.user_id == users.id
        ).get_row(
            [users.name.add_end('!'), orders.total * 1.1],
            order_by=orders.total * 1.1,
        )

    Example — non‑blocking read via the reader pool::

        rows = users.inner_join(
            orders, orders.user_id == users.id
        ).get_row([users.name], from_readers_pool=True)

    Note:
        SQLite does not support ``RIGHT JOIN`` natively.  The
        :meth:`right_join` method is provided for compatibility, but on
        stock SQLite you should swap the tables and use a ``LEFT JOIN``
        instead.  See :meth:`right_join` for details.
    """

    def __init__(self, table_obj, joins=None, params=None):
        """Initialize a new :class:`JoinQuery` builder for a base table.

        This class provides a fluent interface for constructing SQL JOIN
        queries with automatic table aliasing.  It is designed to be created
        indirectly through the :meth:`Table.inner_join`, :meth:`Table.left_join`,
        and :meth:`Table.right_join` methods, and then progressively extended
        by calling :meth:`inner_join`, :meth:`left_join`, or :meth:`right_join`
        on the returned object.

        Each call to one of the join methods returns a **new** :class:`JoinQuery`
        instance (immutable-style chaining), so the original object is never
        mutated.  This makes it safe to reuse a base :class:`JoinQuery` as a
        starting point for multiple independent queries.

        When the same table appears multiple times in the join chain, the
        builder automatically assigns a unique alias (e.g. ``orders_0``,
        ``orders_1``) and rewrites all references to the aliased table inside
        ON conditions, the SELECT list, the WHERE clause, and the ORDER BY
        clause.

        Args:
            table_obj: The base :class:`Table` object on which the join is
                performed.  This becomes the ``FROM`` table of the generated
                SQL statement.
            joins (list[dict], optional): Internal list of join descriptors
                already accumulated on this instance.  Each entry is a dict
                with the keys ``'type'`` (e.g. ``'INNER JOIN'``), ``'table'``
                (a :class:`Table`), ``'condition'`` (a
                :class:`ColumnsOperation`), and ``'alias'`` (a string or
                ``None``).  Defaults to ``None`` (empty list).
            params (list, optional): Parameter values collected from all
                join conditions.  Defaults to ``None`` (empty list).

        Example:
            Direct instantiation is not recommended; prefer the :class:`Table`
            helpers::

                from ormophine.Sqlite import Driver

                db = Driver('shop.db')
                users = db.users
                orders = db.orders

                # Start a join via Table helper
                q = users.inner_join(orders, orders.user_id == users.id)
                # q is a JoinQuery instance ready for further chaining or .get_row()

                # Or construct manually for advanced use cases:
                from ormophine.Sqlite import JoinQuery
                q2 = JoinQuery(users)
                q2 = q2.inner_join(orders, orders.user_id == users.id)
        """
        self.table_obj = table_obj
        self.joins = joins if joins is not None else []
        self.params = params if params is not None else []
        self._output = (self._join_sql(), list(self.params)) if self.joins else ('', [])

    def inner_join(self, table, condition, alias=None) -> 'JoinQuery':
        """Add an ``INNER JOIN`` clause to the query builder.

        The returned :class:`JoinQuery` instance is a **new** object that
        contains all previous joins plus the newly added one; the current
        instance is left unmodified.  This enables safe chaining and reuse.

        If the same :class:`Table` object has already been joined earlier in
        the chain and no explicit ``alias`` is provided, a unique alias is
        automatically generated (e.g. ``orders_0``, ``orders_1``) and all
        references to that table inside the ON condition are rewritten to use
        the alias.

        Args:
            table (Table): The right‑hand table to join with.
            condition (ColumnsOperation): The ``ON`` condition that links the
                two tables.  It must be a :class:`ColumnsOperation` produced
                by comparing columns (e.g. ``orders.user_id == users.id``).
            alias (str, optional): An explicit alias for the joined table.
                If ``None`` and the table has been joined previously, a
                unique alias is generated automatically.  Defaults to ``None``.

        Returns:
            JoinQuery: A new :class:`JoinQuery` instance with the INNER JOIN
            added.  Use it for further chaining or for executing the query
            via :meth:`get_row`.

        Raises:
            Exception: If ``condition`` is not a :class:`ColumnsOperation`
                instance.

        Example:
            Assuming ``users`` and ``orders`` tables::

                from ormophine.Sqlite import Driver

                db = Driver('shop.db')
                users = db.users
                orders = db.orders

                # Simple INNER JOIN
                rows = users.inner_join(
                    orders,
                    orders.user_id == users.id
                ).get_row([users.name, orders.total])
                # Equivalent SQL:
                # SELECT users.[name] AS users_name, orders.[total] AS orders_total
                # FROM [users] INNER JOIN [orders] ON (orders.[user_id] = users.[id])

                # Self-join with automatic alias
                managers = db.managers  # assume a second table object for managers
                rows2 = users.inner_join(
                    users,  # same table, will receive alias 'users_0'
                    users.id == users.manager_id
                ).get_row([users.name])
        """
        return self._add_join('INNER JOIN', table, condition, alias)

    def left_join(self, table, condition, alias=None) -> 'JoinQuery':
        """Add a ``LEFT JOIN`` clause to the query builder.

        Behaves identically to :meth:`inner_join` but emits a ``LEFT JOIN``
        (also known as ``LEFT OUTER JOIN``).  The returned object is a new
        :class:`JoinQuery` instance; the current one is left unmodified.

        All rows from the left (base) table are preserved.  Columns from the
        right table that have no matching row will be ``NULL`` in the result.

        Args:
            table (Table): The right‑hand table to join with.
            condition (ColumnsOperation): The ``ON`` condition linking the
                two tables (e.g. ``orders.user_id == users.id``).
            alias (str, optional): An explicit alias for the joined table.
                Defaults to ``None`` (auto‑generated if needed).

        Returns:
            JoinQuery: A new :class:`JoinQuery` instance with the LEFT JOIN
            added.

        Raises:
            Exception: If ``condition`` is not a :class:`ColumnsOperation`.

        Example:
            Assuming ``users`` and ``orders`` tables, find every user along
            with their order totals (users with no orders get ``None``)::

                from ormophine.Sqlite import Driver

                db = Driver('shop.db')
                users = db.users
                orders = db.orders

                rows = users.left_join(
                    orders,
                    orders.user_id == users.id
                ).get_row([users.name, orders.total])
                # Equivalent SQL:
                # SELECT users.[name] AS users_name, orders.[total] AS orders_total
                # FROM [users] LEFT JOIN [orders] ON (orders.[user_id] = users.[id])
        """
        return self._add_join('LEFT JOIN', table, condition, alias)
    
    def right_join(self, table, condition, alias=None) -> 'JoinQuery':
        """Add a ``RIGHT JOIN`` clause to the query builder.

        .. warning::
            SQLite does **not** natively support ``RIGHT JOIN``.  The
            generated SQL will use the literal ``RIGHT JOIN`` keyword and
            will fail on stock SQLite.  This method is provided only for
            compatibility with other SQL backends or for forward‑compat if
            SQLite adds support.  For SQLite, prefer swapping the table
            order and using a ``LEFT JOIN``.

        Behaves identically to :meth:`inner_join` in terms of chaining and
        aliasing.  Returns a new :class:`JoinQuery` instance.

        Args:
            table (Table): The right‑hand table to join with.
            condition (ColumnsOperation): The ``ON`` condition linking the
                two tables.
            alias (str, optional): An explicit alias for the joined table.
                Defaults to ``None``.

        Returns:
            JoinQuery: A new :class:`JoinQuery` instance with the RIGHT JOIN
            added.

        Raises:
            Exception: If ``condition`` is not a :class:`ColumnsOperation`.

        Example:
            Emitting a RIGHT JOIN (will fail on vanilla SQLite)::

                from ormophine.Sqlite import Driver

                db = Driver('shop.db')
                users = db.users
                orders = db.orders

                q = users.right_join(orders, orders.user_id == users.id)
                # The generated SQL contains 'RIGHT JOIN' which SQLite rejects.

            SQLite‑compatible alternative (swap the tables)::

                # Equivalent to users RIGHT JOIN orders
                # = orders LEFT JOIN users
                rows = orders.left_join(users, users.id == orders.user_id) \\
                             .get_row([users.name, orders.total])
        """
        return self._add_join('RIGHT JOIN', table, condition, alias)
    
    def _make_unique_alias(self, table) -> str:
        """Generate a unique alias for a table being joined a second time.

        The generated alias has the form ``<table_name>_<N>`` where ``N`` is
        the smallest non‑negative integer such that the alias is not already
        used by another join in the current :attr:`joins` list.

        This method is used internally by :meth:`_add_join` when the same
        :class:`Table` object is joined multiple times, ensuring the
        generated SQL is unambiguous.

        Args:
            table (Table): The :class:`Table` for which a unique alias is
                needed.  The table's bracket‑wrapped name (e.g. ``[orders]``)
                is stripped of its brackets and used as the base alias.

        Returns:
            str: A unique alias such as ``'orders_0'`` or ``'orders_1'``.

        Example:
            Typically called indirectly.  For a table named ``orders`` that
            has already been joined without an alias, calling this method
            returns ``'orders_0'``::

                q = users.inner_join(orders, orders.user_id == users.id)
                # Next inner_join of the same orders table will receive
                # the auto‑generated alias 'orders_0'.
        """
        base = table.name_[1:-1]
        used = {j['alias'] for j in self.joins if j['alias']}
        i = 0
        while f'{base}_{i}' in used:
            i += 1
        return f'{base}_{i}'
    
    def _add_join(self, join_type, table, condition, alias):
        """Internal helper that appends a join descriptor and returns a new builder.

        Validates the ``condition`` type, optionally assigns a unique alias
        when the same table is joined multiple times, and constructs a new
        :class:`JoinQuery` instance carrying the extended ``joins`` and
        ``params`` lists.  The current instance is **not** mutated.

        This method is called by :meth:`inner_join`, :meth:`left_join`, and
        :meth:`right_join`; it should not normally be called directly.

        Args:
            join_type (str): The SQL join keyword, e.g. ``'INNER JOIN'``,
                ``'LEFT JOIN'``, or ``'RIGHT JOIN'``.
            table (Table): The right‑hand table to join.
            condition (ColumnsOperation): The ``ON`` condition.  Must be a
                :class:`ColumnsOperation` instance; otherwise an exception
                is raised.
            alias (str, optional): An explicit alias for the joined table.
                If ``None`` and the table is already present in
                :attr:`joins`, a unique alias is generated automatically.

        Returns:
            JoinQuery: A new :class:`JoinQuery` with the added join.

        Raises:
            Exception: If ``condition`` is not a :class:`ColumnsOperation`.
                The error message suggests building the condition via
                column comparisons like ``table1.col == table2.col``.

        Example:
            This is used internally::

                # Equivalent to:
                q = users.inner_join(orders, orders.user_id == users.id)
                # Internally calls:
                # q = users._add_join('INNER JOIN', orders, orders.user_id == users.id, None)
        """
        if not isinstance(condition, ColumnsOperation):
            raise Exception(
                f"Join condition must be a ColumnsOperation, got "
                f"{type(condition).__name__}. Build it with column comparisons "
                f"like `table1.col == table2.col`."
            )

        # If table already joined (or explicit alias), assign a unique alias.
        already_joined = any(j['table'] is table for j in self.joins)
        if alias is None and already_joined:
            alias = self._make_unique_alias(table)

        new_joins = self.joins + [{
            'type': join_type,
            'table': table,
            'condition': condition,
            'alias': alias,
        }]
        new_params = self.params + list(condition._output[1])
        return JoinQuery(self.table_obj, new_joins, new_params)
    
    def _join_sql(self) -> str:
        """Build the SQL fragment containing all JOIN clauses.

        Iterates over :attr:`joins` in insertion order and produces a single
        SQL string such as::

            INNER JOIN [orders] ON (orders.[user_id] = [users].[id])
            LEFT JOIN [orders] AS [orders_0] ON (orders_0.[user_id] = [users].[id])

        When a join descriptor carries an alias, the ON condition is rewritten
        so that references to the original table (``[orders].[col]``) are
        replaced with the aliased form (``[orders_0].[col]``).

        This method is called during :meth:`__init__` to compute
        :attr:`_output` and again by :meth:`get_row`; it should not normally
        be called directly.

        Returns:
            str: A space‑separated sequence of JOIN clauses, or an empty
            string if no joins have been added.

        Example:
            Assuming two joins have been added, the returned string resembles::

                'INNER JOIN [orders] ON (orders.[user_id] = [users].[id])'
        """
        parts = []
        for j in self.joins:
            tbl = j['table']
            cond_sql = j['condition']._output[0]
            if j['alias']:
                # [orders].[col] → [orders_0].[col]
                cond_sql = cond_sql.replace(
                    f'{tbl.name_}.', f'[{j["alias"]}].'
                )
                parts.append(
                    f'{j["type"]} {tbl.name_} AS [{j["alias"]}] ON {cond_sql}'
                )
            else:
                parts.append(f'{j["type"]} {tbl.name_} ON {cond_sql}')
        return ' '.join(parts)
    
    def _resolve_column_ref(self, col) -> str:
        """Return the SQL reference for a column, honouring any join alias.

        Searches :attr:`joins` in order and returns the first join that
        references the column's parent table.  If that join has an alias,
        the reference is rewritten as ``[<alias>].[<column>]``; otherwise the
        column's own :attr:`~Column.name` (``[table].[column]``) is returned.
        If the column's table is not part of any join, the column's raw name
        is returned unchanged.

        This method is used internally by :meth:`get_row` to produce SELECT
        and ORDER BY clauses; it should not normally be called directly.

        Args:
            col (Column): The :class:`Column` whose SQL reference should be
                resolved.

        Returns:
            str: The SQL reference for the column, either in the aliased form
            ``'[alias].[column]'`` or the plain form ``'[table].[column]'``.

        Example:
            When ``orders`` has been joined twice and received the alias
            ``orders_0``, calling::

                q._resolve_column_ref(orders.total)
                # returns '[orders_0].[total]'
        """
        for j in self.joins:
            if j['table'] is col.table_obj:
                if j['alias']:
                    return f'[{j["alias"]}].[{col.first_name[1:-1]}]'
                return col.name
        return col.name
    
    def _rewrite_expr(self, expr: str) -> str:
        """Rewrite table references inside a SQL expression to use aliases.

        Given an SQL fragment that may contain table‑qualified references
        such as ``[orders].[total]``, this method replaces every reference
        to an aliased table with the corresponding ``[<alias>].[column]``
        form.  Tables that were joined without an alias are left untouched.

        This method is used internally by :meth:`get_row` to normalise the
        SELECT expressions, the WHERE clause, and the ORDER BY clause; it
        should not normally be called directly.

        Args:
            expr (str): The SQL expression fragment whose table references
                should be rewritten.

        Returns:
            str: The expression with all aliased table references replaced.

        Example:
            With ``orders`` aliased as ``orders_0``::

                q._rewrite_expr("([orders].[total] > ?)")
                # returns "([orders_0].[total] > ?)"
        """
        for j in self.joins:
            if j['alias']:
                expr = expr.replace(
                    f'{j["table"].name_}.', f'[{j["alias"]}].'
                )
        return expr
    
    def get_row(
        self,
        which_columns: list,
        where: 'ColumnsOperation' = None,
        order_by: 'Column | ColumnsOperation' = None,
        limit: int = None,
        offset: int = None,
        from_readers_pool: bool = False
    ):
        """Execute the JOIN query and return the fetched rows.

        Builds a complete ``SELECT ... FROM <base_table> <joins> [WHERE ...]
        [ORDER BY ...] [LIMIT ...] [OFFSET ...]`` statement from the
        accumulated join chain, then executes it on the writer thread (or on
        a reader‑pool connection if ``from_readers_pool`` is ``True``).

        Each column requested in ``which_columns`` is aliased in the output
        as ``<table>_<column>`` (e.g. ``users_name``, ``orders_total``) to
        avoid ambiguity when two joined tables share column names.  Plain
        :class:`Column` objects and :class:`ColumnsOperation` expressions are
        both supported; expressions are rewritten to use join aliases where
        needed.

        Args:
            which_columns (list): A list of :class:`Column` and/or
                :class:`ColumnsOperation` objects describing the columns to
                select.  At least one element is required; an empty list
                returns ``[]`` immediately.
            where (ColumnsOperation, optional): An optional filtering
                condition.  Table references inside the condition are
                rewritten to use join aliases where applicable.  Defaults
                to ``None`` (no WHERE clause).
            order_by (Column | ColumnsOperation, optional): An optional
                ORDER BY expression.
                * If a :class:`Column` is given, the rows are ordered by
                  that column (using the join alias if the column's table
                  was joined more than once).
                * If a :class:`ColumnsOperation` is given, the rows are
                  ordered by the computed expression.  Table references
                  inside the expression are rewritten to use join aliases
                  automatically, and any parameter values embedded in the
                  expression are appended to the bind list in order.
                Defaults to ``None`` (no ordering).
            limit (int, optional): Maximum number of rows to return.
                Defaults to ``None`` (no LIMIT).
            offset (int, optional): Number of rows to skip.  When provided
                without ``limit``, an implicit ``LIMIT -1`` is used (SQLite
                requires LIMIT when OFFSET is used).  Defaults to ``None``.
            from_readers_pool (bool): If ``True``, execute the query on a
                reader‑pool connection instead of the writer thread.
                Defaults to ``False``.

        Returns:
            list[tuple]: A list of tuples, one per matching row.  Each tuple
            contains the selected values in the order they appear in
            ``which_columns``.  An empty list is returned if no rows match.

        Raises:
            Exception: If the underlying SQL execution fails, or (when
                ``from_readers_pool=True``) a reader‑pool connection cannot
                be acquired.

        Example:
            Assuming ``users`` and ``orders`` tables::

                from ormophine.Sqlite import Driver

                db = Driver('shop.db')
                users = db.users
                orders = db.orders

                # Basic INNER JOIN selecting columns from both tables
                rows = users.inner_join(
                    orders,
                    orders.user_id == users.id
                ).get_row([users.name, orders.total])
                # rows -> [('Alice', 150.0), ('Bob', 200.0), ...]

                # With WHERE, ORDER BY, LIMIT and OFFSET
                rows2 = users.inner_join(
                    orders,
                    orders.user_id == users.id
                ).get_row(
                    [users.name, orders.total],
                    where=orders.total > 100,
                    order_by=orders.total,
                    limit=10,
                    offset=5
                )

                # With an expression column (concatenation)
                rows3 = users.inner_join(
                    orders,
                    orders.user_id == users.id
                ).get_row([users.name.add_end('!'), orders.total])

                # Using the reader pool
                rows4 = users.inner_join(
                    orders,
                    orders.user_id == users.id
                ).get_row([users.name], from_readers_pool=True)
                                # ORDER BY a computed expression (ColumnsOperation)
                # — sort by the discounted total instead of the raw total.
                rows5 = users.inner_join(
                    orders, orders.user_id == users.id
                ).get_row(
                    [users.name, orders.total * 0.9],
                    order_by=orders.total * 0.9,
                )

                # ORDER BY a string expression — e.g. by the length of the
                # user's name or by an uppercased version of it.
                rows6 = users.inner_join(
                    orders, orders.user_id == users.id
                ).get_row(
                    [users.name, orders.total],
                    order_by=users.name.upper(),
                )

                # Combine WHERE + ORDER BY with expressions on the join
                rows7 = users.inner_join(
                    orders, orders.user_id == users.id
                ).get_row(
                    [users.name, orders.total * 1.1],
                    where=orders.total > 100,
                    order_by=orders.total * 1.1,
                    limit=20,
                )
        """
        if not which_columns:
            return []

        tl = []
        select_parts = []
        for i in which_columns:
            if isinstance(i, Column):
                ref = self._resolve_column_ref(i)
                alias = f'{i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}'
                select_parts.append(f'{ref} AS {alias}')
            else:
                expr = self._rewrite_expr(i._output[0])
                tl.extend(i._output[1])
                if expr.startswith('(') and expr.endswith(')'):
                    expr = expr[1:-1]
                alias = (
                    f'{i.col_obj.table_obj.name_[1:-1]}_'
                    f'{i.col_obj.first_name[1:-1]}'
                )
                select_parts.append(f'{expr} AS {alias}')

        base_sql = (
            f"SELECT {', '.join(select_parts)} "
            f"FROM {self.table_obj.name_} "
            f"{self._join_sql()}"
        )
        all_params = tl + list(self.params)
        if where is not None:
            where_sql = self._rewrite_expr(where._output[0])
            base_sql += f' WHERE {where_sql}'
            all_params += list(where._output[1])
        if order_by is not None:
            if isinstance(order_by, Column):
                base_sql += f' ORDER BY {self._resolve_column_ref(order_by)}'
            elif isinstance(order_by, ColumnsOperation):
                order_sql = self._rewrite_expr(order_by._output[0])
                base_sql += f' ORDER BY {order_sql}'
                all_params += list(order_by._output[1])
        extra_params = []
        if limit is not None and offset is not None:
            base_sql += ' LIMIT ? OFFSET ?'
            extra_params = [limit, offset]
        elif limit is not None:
            base_sql += ' LIMIT ?'
            extra_params = [limit]
        elif offset is not None:
            base_sql += ' LIMIT ? OFFSET ?'
            extra_params = [-1, offset]
        all_params += extra_params

        query = (base_sql, all_params) if all_params else (base_sql,)

        if not from_readers_pool:
            return self.table_obj._exc('qf', query)
        else:
            queueCallBack = SimpleQueue()
            connection_queue = self.table_obj.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', query, queueCallBack])
            self.table_obj.db_obj.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return callback[1]
            else:
                raise Exception(callback[1])