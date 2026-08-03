from __future__ import annotations

class Join:

    """Factory namespace for creating SQL JOIN clauses.

    This class serves as a container for nested join type classes (`Inner`, `Left`,
    `Right`). Each nested class, when instantiated, produces a join fragment that
    can be passed to the :meth:`Table.join` method to build complex SELECT queries
    with joined tables.

    The nested classes store both the SQL join string and its associated
    parameter list, which are used internally by the ORM.

    Example:
        Basic usage with an INNER JOIN:

        >>> employees = driver.employees
        >>> departments = driver.departments
        >>> join_condition = employees.dept_id == departments.id
        >>> inner = Join.Inner(departments, join_condition)
        >>> results = employees.join(
        ...     [employees.name, departments.name],
        ...     [inner]
        ... )

    Example:
        Using a LEFT JOIN to include all employees even if they have no department:

        >>> left = Join.Left(departments, join_condition)
        >>> results = employees.join(
        ...     [employees.name, departments.name],
        ...     [left],
        ...     where=employees.salary > 50000
        ... )

    Example:
        Using a RIGHT JOIN to include all departments even if they have no employees:

        >>> right = Join.Right(departments, join_condition)
        >>> results = employees.join(
        ...     [employees.name, departments.name],
        ...     [right]
        ... )

    Note:
        Multiple joins can be combined by passing a list of join objects to
        :meth:`Table.join`.
    """
        
    class Inner:
        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            """Initialize an INNER JOIN clause for a query.

            This constructor creates an INNER JOIN fragment that can be used in the
            :meth:`Table.join` method. It stores the SQL representation and its
            associated parameters for later use in building a complete SELECT query.

            Args:
                table (Table): The table to join with.
                match_case_condition (ColumnsOperation): The join condition, typically
                    a comparison between columns from the main table and the joined table.

            Returns:
                None: This method initializes the instance and does not return a value.

            Example:
                >>> employees = driver.employees
                >>> departments = driver.departments
                >>> join_condition = employees.dept_id == departments.id
                >>> inner_join = Join.Inner(departments, join_condition)
                >>> # Then use in a join query:
                >>> results = employees.join(
                ...     [employees.name, departments.name],
                ...     [inner_join]
                ... )
            """
            self._output = (f'INNER JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])
            
    class Left:
        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            """Create a LEFT JOIN clause for use in a :meth:`Table.join` query.

            This class represents a LEFT JOIN between the current table and another
            table, with a specified join condition. It stores the generated SQL
            fragment and its parameters in the `_output` attribute, which is
            consumed by :meth:`Table.join` to build the final query.

            Args:
                table (Table): The table to join with.
                match_case_condition (ColumnsOperation): A condition expression
                    defining how the tables are related (e.g., using equality
                    comparisons). This is used in the `ON` clause of the join.

            Returns:
                None: The constructor initializes the instance and does not return
                a value.

            Example:
                >>> employees = driver.employees
                >>> departments = driver.departments
                >>> join_condition = employees.dept_id == departments.id
                >>> left_join = Join.Left(departments, join_condition)
                >>> results = employees.join(
                ...     [employees.name, departments.name],
                ...     [left_join]
                ... )
                >>> # This generates: SELECT ... FROM "employees"
                >>> # LEFT JOIN "departments" ON ("employees"."dept_id" = "departments"."id")
            """
            self._output = (f'LEFT JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])

    class Right:
        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            """Initialize a RIGHT JOIN clause for a query.

            This constructor creates a RIGHT JOIN fragment that can be used in the
            :meth:`Table.join` method. A RIGHT JOIN returns all rows from the right
            table (the one being joined), and the matching rows from the left table.
            If no match is found, NULL values are returned for the left table's columns.

            Args:
                table (Table): The table to join with (the right side of the join).
                match_case_condition (ColumnsOperation): The join condition, typically
                    a comparison between columns from the main table and the joined table.

            Returns:
                None: This method initializes the instance and does not return a value.

            Example:
                >>> employees = driver.employees
                >>> departments = driver.departments
                >>> join_condition = employees.dept_id == departments.id
                >>> right_join = Join.Right(departments, join_condition)
                >>> # This will include all departments, even those with no employees.
                >>> results = employees.join(
                ...     [employees.name, departments.name],
                ...     [right_join]
                ... )
            """
            self._output = (f'RIGHT JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])
            