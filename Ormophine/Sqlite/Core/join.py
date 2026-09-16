from __future__ import annotations
from queue import SimpleQueue


class JoinQuery:
    """
    A fluent builder for SQL JOIN queries.

    This class is returned by Table.inner_join(), Table.left_join(), and
    Table.right_join(). It allows chaining multiple joins and then executing
    the query with get_row().

    The class maintains an internal SQL fragment in _output (similar to
    ColumnsOperation) as a tuple (sql_string, params_list).

    Attributes:
        table_obj (Table): The base table (left side of the first join).
        joins_list (list[str]): Accumulated SQL join fragments.
        params (list): Accumulated bind parameters from join conditions.
        _output (tuple[str, list]): (sql_fragment, params_list) – same
            convention as ColumnsOperation, so it can be embedded in other
            expressions if needed.

    Example:
        >>> db = Driver('store.db')
        >>> users = db.users
        >>> orders = db.orders
        >>> banlist = db.banlist
        >>> result = (
        ...     users.left_join(orders, orders.user == users.username)
        ...          .inner_join(banlist, banlist.id == users.id)
        ...          .get_row([orders.ordername, users.age], where=banlist.id > 20)
        ... )
    """

    def __init__(self, table_obj, joins_list=None, params=None):
        """
        Initialize a JoinQuery for a base table.

        Args:
            table_obj (Table): The base table on which the query starts.
            joins_list (list[str], optional): Already accumulated join SQL
                fragments (used internally for chaining).
            params (list, optional): Already accumulated bind parameters.
        """
        self.table_obj = table_obj
        self.joins_list = joins_list if joins_list is not None else []
        self.params = params if params is not None else []
        self._output = (' '.join(self.joins_list), self.params)

    def _add_join(self, join_type: str, table, condition) -> 'JoinQuery':
        """
        Internal helper: build a new JoinQuery with an additional join clause.

        Args:
            join_type (str): One of 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN'.
            table (Table): The table to join.
            condition (ColumnsOperation): The ON condition. Must be a
                ColumnsOperation (e.g. produced by comparing two Columns).

        Returns:
            JoinQuery: A new JoinQuery instance with the added join.
        """
        if not isinstance(condition, ColumnsOperation):
            raise Exception(
                f"Join condition must be a ColumnsOperation, got {type(condition).__name__}. "
                f"Build it with column comparisons like `table1.col == table2.col`."
            )
        new_joins = self.joins_list + [
            f'{join_type} {table.name_} ON {condition._output[0]}'
        ]
        new_params = self.params + list(condition._output[1])
        return JoinQuery(self.table_obj, new_joins, new_params)

    def inner_join(self, table, condition) -> 'JoinQuery':
        """
        Add an INNER JOIN clause to the query.

        Args:
            table (Table): The table to join (right side).
            condition (ColumnsOperation): The ON condition.

        Returns:
            JoinQuery: A new JoinQuery with the INNER JOIN appended.
                Chain further joins or call get_row().
        """
        return self._add_join('INNER JOIN', table, condition)

    def left_join(self, table, condition) -> 'JoinQuery':
        """
        Add a LEFT JOIN clause to the query.

        Args:
            table (Table): The table to join (right side).
            condition (ColumnsOperation): The ON condition.

        Returns:
            JoinQuery: A new JoinQuery with the LEFT JOIN appended.
        """
        return self._add_join('LEFT JOIN', table, condition)

    def right_join(self, table, condition) -> 'JoinQuery':
        """
        Add a RIGHT JOIN clause to the query.

        Note: SQLite does not natively support RIGHT JOIN, but the syntax
        is generated for compatibility with other backends.

        Args:
            table (Table): The table to join (right side).
            condition (ColumnsOperation): The ON condition.

        Returns:
            JoinQuery: A new JoinQuery with the RIGHT JOIN appended.
        """
        return self._add_join('RIGHT JOIN', table, condition)

    def get_row(
        self,
        which_columns: list,
        where: 'ColumnsOperation' = None,
        order_by: 'Column' = None,
        from_readers_pool: bool = False
    ):
        """
        Execute the JOIN query and return the selected rows.

        Args:
            which_columns (list): List of Column or ColumnsOperation to
                select. Each will be aliased as ``{tablename}_{columnname}``
                in the generated SQL.
            where (ColumnsOperation, optional): Optional WHERE condition.
            order_by (Column, optional): Optional ORDER BY column.
            from_readers_pool (bool, optional): If True, run the query on a
                reader-pool connection (non-blocking). Defaults to False.

        Returns:
            list[tuple]: The fetched rows.

        Raises:
            Exception: Propagated from the writer/reader thread on error.
        """
        if not which_columns:
            return []

        # Collect params from ColumnsOperation expressions in select list
        tl = []
        for i in which_columns:
            if isinstance(i, ColumnsOperation):
                tl.extend(i._output[1])

        # Build SELECT column expressions with aliases
        select_parts = []
        for i in which_columns:
            if isinstance(i, Column):
                alias = f'{i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}'
                select_parts.append(f'{i.name} AS {alias}')
            else:
                expr = i._output[0]
                # Strip a single outer pair of parentheses for cleaner SQL
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
            f"{' '.join(self.joins_list)}"
        )
        all_params = tl + self.params

        if where is not None:
            base_sql += f' WHERE {where._output[0]}'
            all_params += list(where._output[1])

        if order_by is not None:
            base_sql += f' ORDER BY {order_by.name}'

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