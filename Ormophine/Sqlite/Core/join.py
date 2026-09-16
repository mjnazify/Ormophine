from __future__ import annotations
from queue import SimpleQueue
from typing import Any
from .. import Column, ColumnsOperation


class JoinQuery:
    """
    Fluent builder for SQL JOIN queries with automatic table aliasing.

    Joins the same table twice safely by automatically assigning unique
    aliases (e.g. ``orders_0``, ``orders_1``) and rewriting all references
    to the aliased table inside conditions, SELECT lists, WHERE, and ORDER BY.
    """

    def __init__(self, table_obj, joins=None, params=None):
        self.table_obj = table_obj
        # joins: list of dicts {type, table, condition, alias|None}
        self.joins = joins if joins is not None else []
        self.params = params if params is not None else []
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
        base = table.name_[1:-1]
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

    # --- SQL generation helpers ---------------------------------------- #
    def _join_sql(self) -> str:
        """Build the JOIN fragments, rewriting table refs to aliases."""
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
        """
        Return the SQL reference for a Column.

        Uses the alias of the FIRST join that references this table.
        If that first join has no alias, the raw table name is used
        (which is unambiguous because only one unaliased instance exists).
        """
        for j in self.joins:
            if j['table'] is col.table_obj:
                if j['alias']:
                    return f'[{j["alias"]}].[{col.first_name[1:-1]}]'
                return col.name
        return col.name

    def _rewrite_expr(self, expr: str) -> str:
        """Rewrite table refs inside an expression to use aliases."""
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
        order_by: 'Column' = None,
        limit: int = None,         
        offset: int = None,        
        from_readers_pool: bool = False
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
            where_sql = self._rewrite_expr(where._output[0])
            base_sql += f' WHERE {where_sql}'
            all_params += list(where._output[1])

        if order_by is not None:
            base_sql += f' ORDER BY {self._resolve_column_ref(order_by)}'

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
        # -----------------------------------------------------

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