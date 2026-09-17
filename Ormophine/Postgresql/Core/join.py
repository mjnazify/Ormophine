from __future__ import annotations
from .. import Column, ColumnsOperation


class JoinQuery:
    """
    Fluent builder for PostgreSQL JOIN queries with automatic table aliasing.

    ``JoinQuery`` is returned by :meth:`Table.inner_join`,
    :meth:`Table.left_join`, and :meth:`Table.right_join`. It accumulates
    join clauses lazily (without executing SQL) and lets the caller chain
    additional joins before finally materializing the result set through
    :meth:`get_row`.

    The builder is **immutable**: every call to :meth:`inner_join`,
    :meth:`left_join`, or :meth:`right_join` returns a *new*
    ``JoinQuery`` instance, leaving the original object unchanged. This
    makes it safe to reuse a partially-built query as a starting point for
    multiple downstream queries.

    Automatic table aliasing
    ------------------------
    If the same :class:`Table` object participates in a join more than
    once, a unique alias (e.g. ``orders_0``, ``orders_1``) is generated
    for each additional reference. All column references in subsequent
    ``ON``, ``WHERE``, ``SELECT`` and ``ORDER BY`` clauses are rewritten
    to use these aliases, so ambiguous column references are handled
    transparently.

    Internal state
    --------------
    table_obj (Table): The base table (left side of the first join).
    joins (list[dict]): Accumulated join descriptors. Each dict contains
        the keys ``type`` (e.g. ``"INNER JOIN"``), ``table`` (a
        :class:`Table`), ``condition`` (a :class:`ColumnsOperation`), and
        ``alias`` (a string or ``None``).
    params (list): Bind parameters accumulated from all join conditions,
        kept in the order their placeholders appear in the generated SQL.
    _output (tuple[str, list]): A ``(sql_fragment, parameter_list)`` pair
        mirroring the shape of :class:`ColumnsOperation._output`, so a
        ``JoinQuery`` can be embedded in other expressions if needed.

    Example:
        Chain multiple joins and execute with ``get_row``::

            >>> users = driver.users_j
            >>> orders = driver.orders_j
            >>> products = driver.products_j
            >>> rows = (users.inner_join(orders,   orders.user_id == users.id)
            ...             .inner_join(products, products.id == orders.product_id)
            ...             .get_row([users.username, products.name],
            ...                      where=products.price < 100,
            ...                      order_by=products.price * -1,
            ...                      limit=10))

        Reuse a partial query for two different downstream queries::

            >>> base = users.inner_join(orders, orders.user_id == users.id)
            >>> q1 = base.get_row([users.username])
            >>> q2 = base.get_row([orders.amount],
            ...                   where=orders.amount > 100)
            >>> # `base` is not mutated by either call.

    Note:
        - The condition passed to any ``*_join`` method must be a
          :class:`ColumnsOperation` (e.g. ``orders.user_id == users.id``).
          Passing a string or any other type raises an ``Exception``
          immediately, before any SQL is built.
        - Unlike :class:`Table.get_row`, ``JoinQuery.get_row`` always
          returns a list of tuples — even when only one column is
          selected — because the JOIN may involve multiple tables.
    """

    def __init__(self, table_obj, joins=None, params=None):
        """Initialize a new :class:`JoinQuery` builder.

        This constructor is normally called indirectly through
        :meth:`Table.inner_join`, :meth:`Table.left_join`, or
        :meth:`Table.right_join`. It is also used internally by
        :meth:`_add_join` to produce a new immutable instance when a join is
        appended.

        Args:
            table_obj (Table): The base table on the left side of the first
                join. This table is used as the ``FROM`` clause of the final
                ``SELECT`` statement.
            joins (list[dict], optional): A list of previously accumulated
                join descriptors. Each item must be a dict with keys
                ``type``, ``table``, ``condition``, and ``alias``.
                Defaults to ``None`` (empty join list).
            params (list, optional): Bind parameters accumulated from
                previously added join conditions. Defaults to ``None``
                (empty parameter list).

        Returns:
            None: This method initializes the instance.

        Note:
            The ``_output`` attribute is computed immediately in the
            constructor. When ``joins`` is empty, ``_output`` is set to
            ``('', [])``. Otherwise it is set to ``(self._join_sql(),
            list(self.params))`` so that the resulting fragment is always
            consistent with the current accumulated state.
        """
        self.table_obj = table_obj
        self.joins = joins if joins is not None else []
        self.params = params if params is not None else []
        # _output must be computed after joins/params are stored
        self._output = (self._join_sql(), list(self.params)) if self.joins else ('', [])

    def inner_join(self, table, condition, alias=None) -> 'JoinQuery':
        """Add an ``INNER JOIN`` clause and return a new :class:`JoinQuery`.

        An ``INNER JOIN`` only keeps rows where the ``ON`` condition is true
        on both sides. If the same ``table`` object has already been joined
        earlier in the chain, a unique alias is generated automatically and
        all column references inside ``condition`` (and any subsequent
        ``WHERE`` / ``ORDER BY`` / ``SELECT`` expressions) are rewritten to
        use that alias.

        Args:
            table (Table): The right-hand table to join.
            condition (ColumnsOperation): The ``ON`` condition, expressed as
                a :class:`ColumnsOperation` comparison (e.g.
                ``orders.user_id == users.id``). Passing a non-
                :class:`ColumnsOperation` value raises an exception
                immediately.
            alias (str, optional): An explicit alias for ``table``. When
                ``None`` (default), an alias is generated automatically only
                if the table has already been joined; otherwise the table is
                referenced by its own name.

        Returns:
            JoinQuery: A new :class:`JoinQuery` instance with the
            ``INNER JOIN`` clause appended. The original instance is not
            modified.

        Raises:
            Exception: If ``condition`` is not a :class:`ColumnsOperation`.
                The error message suggests building the condition with
                column comparisons such as ``table1.col == table2.col``.

        Example:
            Single inner join::

                >>> users  = driver.users_j
                >>> orders = driver.orders_j
                >>> rows = (users.inner_join(orders, orders.user_id == users.id)
                ...             .get_row([users.username, orders.amount]))

            Chained inner joins::

                >>> products = driver.products_j
                >>> rows = (users.inner_join(orders,   orders.user_id == users.id)
                ...             .inner_join(products, products.id == orders.product_id)
                ...             .get_row([users.username, products.name]))
        """
        return self._add_join('INNER JOIN', table, condition, alias)

    def left_join(self, table, condition, alias=None) -> 'JoinQuery':
        """Add a ``LEFT JOIN`` clause and return a new :class:`JoinQuery`.

        A ``LEFT JOIN`` keeps all rows from the base (left) table and fills
        columns of the joined table with ``NULL`` when no matching row
        exists. Automatic aliasing and column rewriting behave exactly like
        :meth:`inner_join`.

        Args:
            table (Table): The right-hand table to join.
            condition (ColumnsOperation): The ``ON`` condition (e.g.
                ``orders.user_id == users.id``).
            alias (str, optional): An explicit alias for ``table``. When
                ``None`` (default), an alias is generated automatically if
                the table has already been joined.

        Returns:
            JoinQuery: A new :class:`JoinQuery` instance with the ``LEFT
            JOIN`` clause appended.

        Raises:
            Exception: If ``condition`` is not a :class:`ColumnsOperation`.

        Example:
            Keep unmatched users (with ``NULL`` amounts)::

                >>> rows = (users.left_join(orders, orders.user_id == users.id)
                ...             .get_row([users.username, orders.amount]))
                >>> # Users without orders appear with `None` amount.

            Filter only the unmatched rows::

                >>> rows = (users.left_join(orders, orders.user_id == users.id)
                ...             .get_row([users.username, orders.amount],
                ...                      where=orders.amount == None))
        """
        return self._add_join('LEFT JOIN', table, condition, alias)

    def right_join(self, table, condition, alias=None) -> 'JoinQuery':
        """Add a ``RIGHT JOIN`` clause and return a new :class:`JoinQuery`.

        A ``RIGHT JOIN`` keeps all rows from the joined (right) table and
        fills columns of the base table with ``NULL`` when no matching row
        exists. Automatic aliasing and column rewriting behave exactly like
        :meth:`inner_join`.

        Args:
            table (Table): The right-hand table to join.
            condition (ColumnsOperation): The ``ON`` condition (e.g.
                ``orders.user_id == users.id``).
            alias (str, optional): An explicit alias for ``table``. When
                ``None`` (default), an alias is generated automatically if
                the table has already been joined.

        Returns:
            JoinQuery: A new :class:`JoinQuery` instance with the ``RIGHT
            JOIN`` clause appended.

        Raises:
            Exception: If ``condition`` is not a :class:`ColumnsOperation`.

        Example:
            Keep unmatched orders (with ``NULL`` usernames)::

                >>> rows = (users.right_join(orders, orders.user_id == users.id)
                ...             .get_row([users.username, orders.amount]))

        Note:
            In practice ``RIGHT JOIN`` is less commonly used than
            ``LEFT JOIN``; swapping the two tables and using ``left_join``
            produces the same result and is often clearer.
        """
        return self._add_join('RIGHT JOIN', table, condition, alias)

    def _make_unique_alias(self, table) -> str:
        """Generate a unique alias for a table within this join chain.

        Called internally when the same :class:`Table` object is joined more
        than once. The generated alias follows the pattern
        ``<table_name>_<counter>`` (e.g. ``orders_0``, ``orders_1``), where
        ``counter`` starts at 0 and increases until an unused alias is found.

        Args:
            table (Table): The table for which an alias is needed.

        Returns:
            str: A unique alias string that does not collide with any alias
            already used by the joins accumulated on this instance.

        Example:
            Internal usage::

                >>> # First join of `orders` uses no alias,
                >>> # second join gets 'orders_0', third gets 'orders_1', ...
                >>> alias = self._make_unique_alias(orders)

        Note:
            The surrounding double quotes of the table name are stripped
            before the counter suffix is appended; the alias is later
            re-quoted when it is emitted in the SQL.
        """
        base = table.name_[1:-1]  
        used = {j['alias'] for j in self.joins if j['alias']}
        i = 0
        while f'{base}_{i}' in used:
            i += 1
        return f'{base}_{i}'

    def _add_join(self, join_type, table, condition, alias):
        """Append a join descriptor to the chain and return a new instance.

        This is the shared implementation used by :meth:`inner_join`,
        :meth:`left_join`, and :meth:`right_join`. It validates the
        condition type, auto-generates an alias if the table is already
        joined, and produces a new immutable :class:`JoinQuery` containing
        the extended join list and parameter list.

        Args:
            join_type (str): The SQL join keyword, e.g. ``"INNER JOIN"``,
                ``"LEFT JOIN"``, or ``"RIGHT JOIN"``.
            table (Table): The right-hand table being joined.
            condition (ColumnsOperation): The ``ON`` condition.
            alias (str or None): An explicit alias for ``table``, or ``None``
                to let the method decide (auto-alias only if the table is
                already present in ``self.joins``).

        Returns:
            JoinQuery: A new :class:`JoinQuery` instance whose ``joins``
            list is ``self.joins + [new_descriptor]`` and whose ``params``
            list is extended with the parameters of ``condition``.

        Raises:
            Exception: If ``condition`` is not a
                :class:`ColumnsOperation`.

        Note:
            This method does **not** mutate the current instance. Each call
            returns a brand-new ``JoinQuery``, which is what makes the
            builder safe to reuse.
        """
        if not isinstance(condition, ColumnsOperation):
            raise Exception(
                f"Join condition must be a ColumnsOperation, got "
                f"{type(condition).__name__}. Build it with column comparisons "
                f"like `table1.col == table2.col`."
            )

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
        """Build the SQL fragment for all accumulated join clauses.

        Iterates over ``self.joins`` in insertion order and produces a single
        string of the form::

            INNER JOIN "orders" ON (...)
            LEFT  JOIN "products" AS "products_0" ON (...)
            ...

        When a join descriptor carries an alias, all occurrences of the
        table's fully qualified prefix (e.g. ``"orders".``) inside its
        condition are rewritten to the alias prefix (e.g. ``"orders_0".``)
        before the fragment is emitted.

        Returns:
            str: The concatenated join SQL fragment, ready to be inserted
            after the ``FROM <base_table>`` clause. Returns an empty string
            when no joins have been added.

        Example:
            Internal usage::

                >>> jq = users.inner_join(orders, orders.user_id == users.id)
                >>> jq._join_sql()
                'INNER JOIN "orders" ON ("orders"."user_id" = "users"."id")'
        """
        parts = []
        for j in self.joins:
            tbl = j['table']
            cond_sql = j['condition']._output[0]
            if j['alias']:
                cond_sql = cond_sql.replace(
                    f'{tbl.name_}.', f'"{j["alias"]}".'
                )
                parts.append(
                    f'{j["type"]} {tbl.name_} AS "{j["alias"]}" ON {cond_sql}'
                )
            else:
                parts.append(f'{j["type"]} {tbl.name_} ON {cond_sql}')
        return ' '.join(parts)

    def _resolve_column_ref(self, col) -> str:
        """Return the SQL reference for a column, using its join alias if any.

        Given a :class:`Column`, this helper scans the accumulated joins and,
        if the column's parent table appears with an alias, rewrites the
        reference to use that alias. This is necessary when the same table
        has been joined more than once and the plain ``table.column`` form
        would be ambiguous.

        Args:
            col (Column): The column whose SQL reference is needed.

        Returns:
            str: Either the plain qualified name (e.g.
            ``'"users"."id"'``) or the aliased form (e.g.
            ``'"users_0"."id"'``) when the parent table is aliased.

        Example:
            Internal usage::

                >>> ref = jq._resolve_column_ref(users.id)
                >>> ref
                '"users"."id"'
        """
        for j in self.joins:
            if j['table'] is col.table_obj:
                if j['alias']:
                    return f'"{j["alias"]}"."{col.first_name[1:-1]}"'
                return col.name
        return col.name

    def _rewrite_expr(self, expr: str) -> str:
        """Rewrite table references inside a SQL expression to use aliases.

        This helper walks through the accumulated joins and, for each join
        that carries an alias, replaces occurrences of the table's fully
        qualified prefix (e.g. ``"orders".``) with the alias prefix (e.g.
        ``"orders_0".``). It is used to preprocess strings produced by
        :class:`ColumnsOperation` before they are placed in the final SQL.

        Args:
            expr (str): A SQL fragment that may contain table-qualified
                column references.

        Returns:
            str: The same fragment with aliased table references.

        Example:
            Internal usage::

                >>> jq._rewrite_expr('("orders"."total" * %s)')
                '("orders_0"."total" * %s)'
        """
        for j in self.joins:
            if j['alias']:
                expr = expr.replace(
                    f'{j["table"].name_}.', f'"{j["alias"]}".'
                )
        return expr

    def get_row(
        self,
        which_columns: list,
        where: 'ColumnsOperation' = None,
        order_by: 'Column | ColumnsOperation' = None,
        limit: int = None,
        offset: int = None,
        ):
        """Execute the accumulated JOIN query and return the fetched rows.

        Builds and runs a ``SELECT ... FROM base_table <joins> [WHERE ...]
        [ORDER BY ...] [LIMIT ...] [OFFSET ...]`` statement using the joins
        accumulated on this :class:`JoinQuery` instance. Column references
        inside ``which_columns``, ``where`` and ``order_by`` are automatically
        rewritten to use table aliases when a table participates in the join
        more than once, preventing ambiguous column errors.

        Args:
            which_columns (list[Column | ColumnsOperation]): The columns or
                computed expressions to include in the ``SELECT`` list. Each
                element can be a :class:`Column` (returned as-is with a
                ``<table>_<column>`` alias) or a :class:`ColumnsOperation`
                (e.g. ``orders.total * -1``, ``users.name.upper()``). The
                method returns a list of tuples, one per row.
            where (ColumnsOperation, optional): A condition object for
                filtering rows. Both sides of the condition may reference
                columns from any table in the join; aliases are applied
                automatically. Defaults to ``None`` (no filter).
            order_by (Column | ColumnsOperation, optional): The expression
                to order the results by. May be a plain :class:`Column`
                (e.g. ``users.id``) or a computed
                :class:`ColumnsOperation` (e.g. ``orders.total * -1``,
                ``users.name.upper()``). Sorting direction follows SQL
                semantics — use ``col * -1`` for descending order.
                Defaults to ``None`` (no ordering).
            limit (int, optional): Maximum number of rows to return. A value
                of ``0`` returns an empty list. Defaults to ``None`` (no
                limit).
            offset (int, optional): Number of rows to skip before returning
                results. When ``offset`` is greater than the total number of
                rows, an empty list is returned. Defaults to ``None`` (no
                offset).

        Returns:
            list[tuple]: A list of tuples, one per returned row, where each
            tuple contains the values in the order of ``which_columns``.

        Raises:
            Exception: Propagates any database errors
                (:class:`OperationalError`, :class:`ProgrammingError`, etc.)
                with additional context about the failing query.

        Example:
            Basic inner join::

                >>> users = driver.users_j
                >>> orders = driver.orders_j
                >>> rows = (users.inner_join(orders, orders.user_id == users.id)
                ...             .get_row([users.username, orders.amount]))
                >>> # [('alice', 1000), ('alice', 20), ('bob', 50)]

            Chained joins with a computed ``ORDER BY``::

                >>> rows = (users.inner_join(orders, orders.user_id == users.id)
                ...             .inner_join(products,
                ...                        products.id == orders.product_id)
                ...             .get_row([users.username, products.name],
                ...                      where=products.price < 100,
                ...                      order_by=products.price * -1,
                ...                      limit=2,
                ...                      offset=1))

            Using ``order_by`` with a string operation (case-insensitive sort)::

                >>> rows = (users.inner_join(orders, orders.user_id == users.id)
                ...             .get_row([users.id],
                ...                      order_by=users.username.upper()))

            Full stack: filter + computed order + pagination::

                >>> rows = (users.inner_join(orders, orders.user_id == users.id)
                ...             .get_row([orders.amount],
                ...                      where=orders.amount > 20,
                ...                      order_by=orders.amount * -1 + 1000,
                ...                      limit=2,
                ...                      offset=1))
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

        ob = []
        if isinstance(order_by, Column):
            order_sql = self._resolve_column_ref(order_by)
        elif isinstance(order_by, ColumnsOperation):
            order_sql = self._rewrite_expr(order_by._output[0])
            ob.extend(order_by._output[1])
        else:
            order_sql = None

        sql = (
            f"SELECT {', '.join(select_parts)} "
            f"FROM {self.table_obj.name_} "
            f"{self._join_sql()}"
        )
        all_params = tl + list(self.params)

        if where is not None:
            sql += f' WHERE {self._rewrite_expr(where._output[0])}'
            all_params += list(where._output[1])

        if order_sql is not None:
            sql += f' ORDER BY {order_sql}'
            all_params += ob

        if limit is not None:
            sql += ' LIMIT %s'
            all_params.append(limit)
        if offset is not None:
            sql += ' OFFSET %s'
            all_params.append(offset)

        sql += ';'

        rows = self.table_obj._excfp(sql, all_params) if all_params else self.table_obj._excf(sql)
        return rows