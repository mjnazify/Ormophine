from __future__ import annotations

class Join:
    """
    Namespace for creating JOIN specifications to be used in :meth:`Table.join`.

    The :class:`Join` class serves as a container for three nested classes:
    :class:`Inner`, :class:`Left`, and :class:`Right`. Each of these classes
    represents a specific type of SQL JOIN and encapsulates the target table
    and the join condition. When instantiated, they produce an object with a
    ``_output`` attribute (a tuple containing the SQL fragment and its
    parameters) that is consumed by :meth:`Table.join`.

    **Nested Classes**
        - :class:`Join.Inner`: Creates an ``INNER JOIN`` clause.
        - :class:`Join.Left`: Creates a ``LEFT JOIN`` clause.
        - :class:`Join.Right`: Creates a ``RIGHT JOIN`` clause.

    Each nested class has the same constructor signature:
        ``__init__(table: Table, match_case_condition: ColumnsOperation)``

    Example:
        Joining two tables using an INNER JOIN::

            from ormophine.Mysql import Join

            # Assume we have table objects: users, orders
            # and column objects: users.id, orders.user_id

            inner_join = Join.Inner(
                orders,
                users.id == orders.user_id
            )

            results = users.join(
                columns=[users.id, users.name, orders.amount],
                joins_list=[inner_join],
                where=users.id > 100
            )

        Using a LEFT JOIN::

            left_join = Join.Left(
                orders,
                users.id == orders.user_id
            )

            results = users.join(
                columns=[users.id, users.name, orders.amount],
                joins_list=[left_join]
            )

        Using a RIGHT JOIN::

            right_join = Join.Right(
                orders,
                users.id == orders.user_id
            )

            results = users.join(
                columns=[users.id, users.name, orders.amount],
                joins_list=[right_join]
            )

    Note:
        The join objects are not meant to be used independently; they are
        designed to be passed as a list to the ``joins_list`` parameter of
        :meth:`Table.join`. The join condition must be a
        :class:`ColumnsOperation` expression, typically created using
        comparison operators (``==``, ``!=``, ``>``, etc.) on :class:`Column`
        objects.
    """    
    class Inner:
        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            """
            Initialize an INNER JOIN clause between the current table and another table.

            This constructor creates an object that represents an ``INNER JOIN`` SQL
            clause. It stores both the SQL string and the associated parameter values
            for the join condition. The resulting object is typically used in a list
            passed to :meth:`Table.join` to perform multi-table queries.

            Args:
                table (Table): The table to join with. This is the right-hand side
                    table in the join.
                match_case_condition (ColumnsOperation): A :class:`ColumnsOperation`
                    expression that defines the join condition (e.g., ``users.id == orders.user_id``).
                    This condition will be used in the ``ON`` clause of the join.

            Returns:
                None: This method does not return a value; it initializes the instance.

            Raises:
                None: This constructor does not perform any validation and does not
                    raise exceptions.

            Example:
                Creating an INNER JOIN between the ``users`` table and the ``orders``
                table::

                    from ormophine.Mysql import Join

                    # Assuming we have table objects: users, orders
                    inner_join = Join.Inner(
                        orders,
                        users.id == orders.user_id
                    )

                    # Then use it in a join query
                    results = users.join(
                        columns=[users.name, orders.amount],
                        joins_list=[inner_join]
                    )
            """
            self._output =  (f'INNER JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])
            
    class Left:
        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            """
            Initialize a LEFT JOIN clause for a SQL query.

            This constructor creates a representation of a LEFT JOIN between the
            current table and the specified ``table``, using the provided condition.
            The resulting object stores a tuple ``_output`` containing the SQL fragment
            (e.g., ``'LEFT JOIN table_name ON condition'``) and the associated parameter
            list for safe parameterized execution. This object is intended to be used
            in the :meth:`Table.join` method.

            Args:
                table (Table): The table to join with.
                match_case_condition (ColumnsOperation): A :class:`ColumnsOperation`
                    expression defining the join condition (e.g., ``users.id == orders.user_id``).

            Returns:
                None: The constructor initializes the instance and stores the SQL
                fragment and parameters in ``self._output``.

            Raises:
                None: This method does not raise any exceptions directly.

            Example:
                Creating a LEFT JOIN between the ``users`` and ``orders`` tables::

                    from ormophine.Mysql import Join

                    join_clause = Join.Left(
                        orders,
                        users.id == orders.user_id
                    )

                    # The join clause can then be passed to Table.join()
                    results = users.join(
                        columns=[users.name, orders.amount],
                        joins_list=[join_clause]
                    )
            """
            self._output =  (f'LEFT JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])

    class Right:
        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            """
            Initialize a RIGHT JOIN clause for a query.

            This constructor creates a RIGHT JOIN specification that can be used
            in a :meth:`Table.join` call. A RIGHT JOIN returns all rows from the
            right table (the table being joined) and the matching rows from the
            left table (the base table). If no match is found on the left side,
            columns from the left table will contain ``NULL``.

            Args:
                table (Table): The table to join on the right side. This is the
                    table from which all rows will be returned (the "right" table).
                match_case_condition (ColumnsOperation): A :class:`ColumnsOperation`
                    expression defining the join condition, typically an equality
                    comparison between columns of the base table and the joined table
                    (e.g., ``users.id == orders.user_id``).

            Returns:
                None: This constructor only initializes the join object. The resulting
                object is meant to be passed to :meth:`Table.join`.

            Raises:
                Exception: If the underlying SQL generation or execution fails
                    (indirectly, when the join object is used in a query).

            Example:
                Performing a RIGHT JOIN between the ``users`` table and an
                ``orders`` table::

                    from ormophine.Mysql import Join

                    # Assume we have table objects: users, orders
                    # and column objects: users.id, orders.user_id, orders.amount

                    right_join = Join.Right(
                        orders,
                        users.id == orders.user_id
                    )

                    results = users.join(
                        columns=[users.id, users.name, orders.amount],
                        joins_list=[right_join],
                        where=users.id > 100
                    )
                    # This will return all orders, even those without a matching user
                    # (user columns will be NULL for unmatched orders).
            """
            self._output = (f'RIGHT JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])

