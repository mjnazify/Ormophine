from __future__ import annotations

class Join:
    """
    A factory namespace for constructing SQL JOIN clauses.

    This class is not meant to be instantiated directly. Instead, it
    serves as a container for the nested classes :class:`Inner`,
    :class:`Left`, and :class:`Right`, each of which builds the
    corresponding SQL join type. Instances of these nested classes
    are passed to the :meth:`Table.join` method to perform multi‑table
    queries.

    The nested classes store their output in an ``_output`` attribute
    as a tuple ``(sql_string, parameters)``, which is consumed by
    :meth:`Table.join`.

    Example:
        Assuming a database with ``orders`` and ``customers`` tables::

            from ormophine.Sqlite import Driver, Table, Join

            db = Driver('store.db')
            orders = db.users
            customers = db.customers

            # Define the join condition
            condition = orders.customer_id == customers.id

            # Build different join types
            inner_join = Join.Inner(customers, condition)
            left_join = Join.Left(customers, condition)
            right_join = Join.Right(customers, condition)

            # Perform a query with a LEFT JOIN
            results = orders.join(
                columns=[orders.order_id, customers.name],
                joins_list=[left_join]
            )
            # Returns all orders with customer names (including orders without a customer).

    Note:
        While SQLite does not natively support ``RIGHT JOIN``, the ORM
        generates the syntax for compatibility with other database
        backends or for use with SQLite extensions.
    """

    class Inner:
        """
        Represents an INNER JOIN clause for a SQL query.

        This class is a nested class of :class:`Join` and is used to build
        the join part of a query. It stores the SQL fragment for an
        ``INNER JOIN`` along with its parameters.

        An ``INNER JOIN`` returns only rows where the join condition matches
        in both tables.

        Attributes:
            _output (tuple[str, list]): A 2‑tuple containing the SQL string
                for the join clause and the list of parameter values (if any).

        Example:
            Using ``Join.Inner`` in a query::

                from ormophine.Sqlite import Driver, Table, Join

                db = Driver('store.db')
                orders = db.users
                customers = db.customers

                # Create join condition
                condition = orders.customer_id == customers.id

                # Build INNER JOIN
                inner_join = Join.Inner(customers, condition)

                # Use in Table.join
                results = orders.join(
                    columns=[orders.order_id, customers.name],
                    joins_list=[inner_join]
                )
        """

        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            """
            Initializes an INNER JOIN clause.

            Args:
                table (Table): The table to join (the right side of the join).
                match_case_condition (ColumnsOperation): The condition
                    expression that defines how the tables are matched.
                    Typically created by comparing :class:`Column` objects.

            Example:
                >>> join_obj = Join.Inner(users, users.id == orders.user_id)
            """
            self._output = (f'INNER JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])


    class Left:
        """
        Represents a LEFT JOIN clause for a SQL query.

        This class is a nested class of :class:`Join` and is used to build
        the join part of a query. It stores the SQL fragment for a
        ``LEFT JOIN`` along with its parameters.

        A ``LEFT JOIN`` returns all rows from the left table, and matching
        rows from the right table. If no match exists, the right‑side columns
        contain ``NULL``.

        Attributes:
            _output (tuple[str, list]): A 2‑tuple containing the SQL string
                for the join clause and the list of parameter values (if any).

        Example:
            Using ``Join.Left`` in a query::

                from ormophine.Sqlite import Driver, Table, Join

                db = Driver('store.db')
                orders = db.users
                customers = db.customers

                condition = orders.customer_id == customers.id
                left_join = Join.Left(customers, condition)

                results = orders.join(
                    columns=[orders.order_id, customers.name],
                    joins_list=[left_join]
                )
        """

        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            """
            Initializes a LEFT JOIN clause.

            Args:
                table (Table): The table to join (the right side of the join).
                match_case_condition (ColumnsOperation): The condition
                    expression that defines how the tables are matched.
                    Typically created by comparing :class:`Column` objects.

            Example:
                >>> join_obj = Join.Left(products, products.category_id == categories.id)
            """
            self._output = (f'LEFT JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])


    class Right:
        """
        Represents a RIGHT JOIN clause for a SQL query.

        This class is a nested class of :class:`Join` and is used to build
        the join part of a query. It stores the SQL fragment for a
        ``RIGHT JOIN`` along with its parameters.

        A ``RIGHT JOIN`` returns all rows from the right table, and matching
        rows from the left table. If no match exists, the left‑side columns
        contain ``NULL``.

        Note that SQLite does not support ``RIGHT JOIN`` natively, but the
        ORM will generate the appropriate SQL syntax, which may be processed
        by other database engines or translated.

        Attributes:
            _output (tuple[str, list]): A 2‑tuple containing the SQL string
                for the join clause and the list of parameter values (if any).

        Example:
            Using ``Join.Right`` in a query::

                from ormophine.Sqlite import Driver, Table, Join

                db = Driver('store.db')
                orders = db.users
                customers = db.customers

                condition = orders.customer_id == customers.id
                right_join = Join.Right(customers, condition)

                results = orders.join(
                    columns=[orders.order_id, customers.name],
                    joins_list=[right_join]
                )
        """

        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            """
            Initializes a RIGHT JOIN clause.

            Args:
                table (Table): The table to join (the right side of the join).
                match_case_condition (ColumnsOperation): The condition
                    expression that defines how the tables are matched.
                    Typically created by comparing :class:`Column` objects.

            Example:
                >>> join_obj = Join.Right(employees, employees.department_id == departments.id)
            """
            self._output = (f'RIGHT JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])
