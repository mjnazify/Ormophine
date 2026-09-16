from __future__ import annotations
from .. import Column, ColumnsOperation


class JoinQuery:
    """
    Fluent builder for MySQL/MariaDB JOIN queries with automatic table aliasing.

    Returned by Table.inner_join(), Table.left_join(), and Table.right_join().
    Supports chaining multiple joins and finally executing with get_row().

    Internal state:
        table_obj (Table): base table (left side of the first join)
        joins (list[dict]): each item is {'type', 'table', 'condition', 'alias'}
        params (list): accumulated bind parameters (%s placeholders)
        _output (tuple[str, list]): same shape as ColumnsOperation — a SQL
            fragment and its parameter list, so JoinQuery can be embedded in
            other expressions if needed.

    MySQL/MariaDB note:
        Identifier quoting uses backticks (`` `table` ``), unlike PostgreSQL
        which uses double quotes. RIGHT JOIN is supported by both MySQL and
        MariaDB natively.

    Example:
        >>> users.left_join(orders, orders.user == users.username) \\
        ...      .inner_join(banlist, banlist.id == users.id) \\
        ...      .get_row([orders.ordername, users.age], where=banlist.id > 20)
    """

    def __init__(self, table_obj, joins=None, params=None):
        self.table_obj = table_obj
        self.joins = joins if joins is not None else []
        self.params = params if params is not None else []
        # _output must be computed after joins/params are stored
        self._output = (self._join_sql(), list(self.params)) if self.joins else ('', [])

    # ------------------------------------------------------------------ #
    #  Public join builders                                              #
    # ------------------------------------------------------------------ #
    def inner_join(self, table, condition, alias=None) -> 'JoinQuery':
        return self._add_join('INNER JOIN', table, condition, alias)

    def left_join(self, table, condition, alias=None) -> 'JoinQuery':
        return self._add_join('LEFT JOIN', table, condition, alias)

    def right_join(self, table, condition, alias=None) -> 'JoinQuery':
        return self._add_join('RIGHT JOIN', table, condition, alias)

    # ------------------------------------------------------------------ #
    #  Internals                                                         #
    # ------------------------------------------------------------------ #
    def _make_unique_alias(self, table) -> str:
        """Generate an alias like ``orders_0`` that isn't already used."""
        base = table.name_[1:-1]  # strip the surrounding backticks
        used = {j['alias'] for j in self.joins if j['alias']}
        i = 0
        while f'{base}_{i}' in used:
            i += 1
        return f'{base}_{i}'

    def _add_join(self, join_type, table, condition, alias):
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

    # --- SQL generation helpers ---------------------------------------- #
    def _join_sql(self) -> str:
        """Build the JOIN fragments, rewriting table refs to aliases."""
        parts = []
        for j in self.joins:
            tbl = j['table']
            cond_sql = j['condition']._output[0]
            if j['alias']:
                # `orders`.`col` → `orders_0`.`col`
                cond_sql = cond_sql.replace(
                    f'{tbl.name_}.', f'`{j["alias"]}`.'
                )
                parts.append(
                    f'{j["type"]} {tbl.name_} AS `{j["alias"]}` ON {cond_sql}'
                )
            else:
                parts.append(f'{j["type"]} {tbl.name_} ON {cond_sql}')
        return ' '.join(parts)

    def _resolve_column_ref(self, col) -> str:
        """
        Return the SQL reference for a Column using the alias of the FIRST
        join that references this table.
        """
        for j in self.joins:
            if j['table'] is col.table_obj:
                if j['alias']:
                    return f'`{j["alias"]}`.`{col.first_name[1:-1]}`'
                return col.name
        return col.name

    def _rewrite_expr(self, expr: str) -> str:
        """Rewrite table refs inside an expression to use aliases."""
        for j in self.joins:
            if j['alias']:
                expr = expr.replace(
                    f'{j["table"].name_}.', f'`{j["alias"]}`.'
                )
        return expr

    def get_row(
        self,
        which_columns: list,
        where: 'ColumnsOperation' = None,
        order_by: 'Column' = None,
        limit: int = None,
        offset: int = None,
    ):
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
            base_sql += f' WHERE {self._rewrite_expr(where._output[0])}'
            all_params += list(where._output[1])

        if order_by is not None:
            base_sql += f' ORDER BY {self._resolve_column_ref(order_by)}'

        # ---- LIMIT / OFFSET ----
        if limit is not None:
            base_sql += ' LIMIT %s '
            all_params.append(limit)

        if offset is not None:
            if limit is None:
                base_sql += ' LIMIT 18446744073709551615 '
            base_sql += ' OFFSET %s '
            all_params.append(offset)

        base_sql += ';'

        if all_params:
            return self.table_obj._excfp(base_sql, all_params)
        return self.table_obj._excf(base_sql)