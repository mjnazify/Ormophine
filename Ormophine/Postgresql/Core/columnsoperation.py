from __future__ import annotations

class ColumnsOperation:
    """
    A chainable builder for SQL column expressions and operations.

    This class provides a fluent interface for constructing SQL expressions
    involving columns, literals, and operations like arithmetic, comparisons,
    string functions, and pattern matching. It is used internally by the
    :class:`Column` class and is returned by most column operators and methods.

    The core of the class is the `_output` attribute, which stores a tuple
    `(sql_expression, parameters_list)`. As operations are chained, the SQL
    string is gradually built and the parameter list is accumulated. This
    allows the final expression to be safely used in parameterized queries,
    preventing SQL injection.

    The class supports:
    - Arithmetic operations (+, -, *, /, %, **) with automatic detection of
      string concatenation vs. numeric addition based on the column's datatype.
    - Comparison operations (==, !=, <, <=, >, >=) via both operator overloading
      and explicit methods (eq, ne, lt, le, gt, ge).
    - Logical operations (AND, OR) for combining conditions.
    - String operations: LIKE, STARTSWITH, ENDSWITH, CONTAINS, UPPER, LOWER,
      REPLACE, TRIM (strip, lstrip, rstrip), and SUBSTRING via slice notation.
    - Collection operations: IN with lists, tuples, or subqueries.
    - Concatenation methods: add_end, add_first for string columns.

    All methods return the instance itself, enabling method chaining:

    Example:
        >>> from ormophine.Postgresql import Driver, Table
        >>> driver = Driver(...)
        >>> employees = driver.employees
        >>> # Build a complex condition
        >>> cond = (employees.salary >= 50000) & (employees.name.upper().contains('SMITH'))
        >>> # Use it in a query
        >>> results = employees.get_row([employees.name, employees.salary], where=cond)
        >>>
        >>> # String slicing (SUBSTRING)
        >>> first_three = employees.name[0:3]
        >>> # Arithmetic operations
        >>> bonus = employees.salary * 0.1
    """
    def __init__(self, col_obj):
        """Initialize a new ColumnsOperation instance.

        This class is a builder for SQL expressions involving column operations.
        It stores the column object and maintains an internal state ``_output``
        that accumulates the SQL fragment and parameter list as operations are
        chained. Typically, instances are created indirectly via :class:`Column`
        operators rather than directly.

        Args:
            col_obj (Column): The column object that this operation is associated
                with. The column's datatype determines whether string concatenation
                (``||``) or numeric addition (``+``) is used in arithmetic operations.

        Returns:
            None: This method only initializes the instance.

        Example:
            >>> # Usually created through Column operators:
            >>> from ormophine.Postgresql import Column, Table
            >>> table = driver.employees
            >>> col_op = table.salary + 1000  # Creates a ColumnsOperation
            >>> # Or explicitly:
            >>> from ormophine.Postgresql import ColumnsOperation
            >>> op = ColumnsOperation(table.salary)
            >>> op._output  # Initially empty, but will be set when operations are applied
            ''
        """
        self._output = '' # To apply operations in a chained manner
        self.col_obj = col_obj

    def __add__(self, other):
        """Add two column expressions or a column and a value.

        This method implements the `+` operator for :class:`ColumnsOperation`.
        It generates a SQL expression that represents either numeric addition
        (for numeric column types) or string concatenation (for string column
        types) using PostgreSQL's `||` operator. The result is stored in the
        internal `_output` tuple, allowing method chaining.

        Args:
            other (Union[ColumnsOperation, Column, int, float, str]): The right-hand
                operand. Can be another :class:`ColumnsOperation`, a :class:`Column`,
                or a literal value (int, float, or str).

        Returns:
            ColumnsOperation: The current instance, with `_output` updated to
                contain the new SQL expression and its parameters. This enables
                fluent chaining of operations.

        Example:
            Simple numeric addition:

            >>> employees = driver.employees
            >>> # Add 10% bonus to salary
            >>> expr = employees.salary * 1.1 + 1000
            >>> # This generates: (("salary" * 1.1) + %s) with params [1000]

        Example:
            String concatenation with a column and a literal:

            >>> # Assuming 'first_name' and 'last_name' are string columns
            >>> full_name = employees.first_name + " " + employees.last_name
            >>> # Generates: (("first_name" || %s) || "last_name") with params [' ']

        Note:
            The operation uses `+` for numeric types and `||` for strings,
            determined by the `col_obj.datatype` attribute. For literals, the
            method automatically chooses the appropriate operator based on
            the column's datatype.
        """
        self._output = (f'({self._output[0]} {'||' if self.col_obj.datatype == str else '+'} {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} {'||' if self.col_obj.datatype == str else '+'} {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} + %s)', self._output[1]+[other]) if isinstance(other, int) or isinstance(other , float) else (f'({self._output[0]} || %s)', self._output[1]+[other if isinstance(other, str) else str(other)])
        return self

    def __radd__(self, other):
        """Implement reflected addition (right-hand side addition) for column operations.

        This method is called when a :class:`ColumnsOperation` object appears on the
        right side of a `+` operator (e.g., `value + column_operation`). It generates
        the appropriate SQL expression fragment, handling different types of `other`:

        - If `other` is another :class:`ColumnsOperation`, it combines both SQL
        expressions with the appropriate operator (`||` for strings, `+` for numerics).
        - If `other` is a :class:`Column`, it uses the column's name.
        - If `other` is an integer or float, it uses a parameterized placeholder `%s`.
        - If `other` is a string, it uses `||` concatenation with a placeholder.
        - For other types, it converts to string and uses `||`.

        The method updates the internal `_output` tuple (SQL string and parameter list)
        and returns `self` to allow method chaining.

        Args:
            other (Any): The value to add to the left side of the operation. Can be
                a :class:`ColumnsOperation`, :class:`Column`, numeric type, string,
                or any other value.

        Returns:
            ColumnsOperation: The current instance with updated `_output`, allowing
                chaining of further operations.

        Example:
            >>> from ormophine.Postgresql import Column, ColumnsOperation, Table
            >>> employees = driver.employees
            >>> # Create a column operation: employees.first_name
            >>> op = employees.first_name
            >>> # Right addition: "Mr. " + first_name
            >>> new_op = "Mr. " + op
            >>> # new_op now represents SQL: ('Mr. ' || "first_name")
            >>> # For numeric columns:
            >>> salary_op = employees.salary
            >>> bonus_op = 1000 + salary_op  # SQL: (1000 + "salary")
        """
        self._output = (f'({other._output[0]} {'||' if self.col_obj.datatype == str else '+'} {self._output[0]})', other._output[1]+self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} {'||' if self.col_obj.datatype == str else '+'} {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s + {self._output[0]})', [other]+self._output[1]) if isinstance(other, int) or isinstance(other , float) else (f'(%s || {self._output[0]})', [other if isinstance(other, str) else str(other)]+self._output[1])
        return self

    def __sub__(self, other):
        """Implement subtraction operator for column expressions.

        This method overloads the `-` operator to generate SQL subtraction expressions
        between column values, column operations, or literal values. It handles
        different operand types:

        * If `other` is a `ColumnsOperation`, both sides are combined.
        * If `other` is a `Column`, it references the column name.
        * Otherwise, it treats `other` as a literal value and uses a parameter placeholder.

        The method mutates the current instance by updating its internal `_output` tuple
        (SQL string and parameter list) and returns `self` to allow method chaining.

        Args:
            other (ColumnsOperation | Column | int | float | Any): The right-hand side
                operand for subtraction.

        Returns:
            ColumnsOperation: The current instance with the updated SQL expression.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> employees = driver.employees
            >>> # Column - literal
            >>> expr = employees.salary - 1000
            >>> # Column - Column
            >>> expr2 = employees.salary - employees.bonus
            >>> # ColumnOperation - ColumnOperation
            >>> expr3 = (employees.salary * 2) - (employees.bonus + 500)
        """
        self._output = (f'({self._output[0]} - {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} - {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} - %s)', self._output[1]+[other])
        return self

    def __rsub__(self, other):
        """Implement reflected subtraction (right-hand side subtraction) for SQL expressions.

        This method is called when a :class:`ColumnsOperation` appears on the right
        side of a subtraction operator, e.g., `5 - column_operation`. It constructs
        the SQL expression for subtracting the current operation from `other` and
        stores the result internally, allowing method chaining.

        The generated SQL expression will use the appropriate operator:
        - If `other` is a :class:`Column`, the expression uses the column name.
        - If `other` is a :class:`ColumnsOperation`, the expression combines both
        operations.
        - If `other` is a literal value, the expression uses a parameter placeholder
        (`%s`) and adds the value to the parameters list.

        Args:
            other (Any): The left-hand operand. Can be a :class:`Column`,
                :class:`ColumnsOperation`, or a literal value (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # This will generate SQL: (1000 - "salary")
            >>> op = 1000 - employees.salary
            >>> print(op._output[0])
            '(1000 - "employees"."salary")'
            >>> print(op._output[1])  # parameters list
            []
        """
        self._output = (f'({other._output[0]} - {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} - {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s - {self._output[0]})', [other]+self._output[1])
        return self

    def __mul__(self, other):
        """Implement multiplication for SQL expressions.

        This method is called when the `*` operator is used between a
        :class:`ColumnsOperation` and another operand. It constructs the SQL
        expression for multiplying the current operation by `other` and stores
        the result internally, allowing method chaining.

        The generated SQL expression uses the `*` operator for numeric types.
        If `other` is a :class:`Column`, a :class:`ColumnsOperation`, or a literal
        value, the appropriate SQL representation is generated with parameter
        placeholders (`%s`) as needed.

        Args:
            other (Any): The right-hand operand. Can be a :class:`Column`,
                :class:`ColumnsOperation`, or a literal value (int, float, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Calculate bonus as salary * 1.1
            >>> bonus = employees.salary * 1.1
            >>> print(bonus._output[0])
            '("employees"."salary" * %s)'
            >>> print(bonus._output[1])  # parameters list
            [1.1]
            >>> # Multiply two columns: salary * hours
            >>> total = employees.salary * employees.hours
            >>> print(total._output[0])
            '("employees"."salary" * "employees"."hours")'
        """
        self._output = (f'({self._output[0]} * {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} * {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} * %s)', self._output[1]+[other])
        return self

    def __rmul__(self, other):
        """Implement reflected multiplication (right-hand side multiplication) for SQL expressions.

        This method is invoked when a :class:`ColumnsOperation` appears on the right side of a
        multiplication operator, e.g., `5 * column_operation`. It constructs the SQL expression
        for multiplying `other` by the current operation and stores the result internally,
        enabling method chaining.

        The generated SQL uses the `*` operator. Depending on the type of `other`:
        - If `other` is a :class:`ColumnsOperation`, the expression combines both operations.
        - If `other` is a :class:`Column`, the expression uses the column name.
        - If `other` is a literal value, the expression uses a parameter placeholder (`%s`)
        and adds the value to the parameters list.

        Args:
            other (Any): The left-hand operand. Can be a :class:`Column`,
                :class:`ColumnsOperation`, or a literal value (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output` state,
            allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # This will generate SQL: (2.5 * "salary")
            >>> op = 2.5 * employees.salary
            >>> print(op._output[0])
            '(2.5 * "employees"."salary")'
            >>> print(op._output[1])  # parameters list
            []
        """
        self._output = (f'({other._output[0]} * {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} * {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s * {self._output[0]})', [other]+self._output[1])
        return self

    def __pow__(self, other):
        """Implement the exponentiation (power) operator for SQL expressions.

        This method is called when the `**` operator is used with a
        :class:`ColumnsOperation` on the left side. It generates a SQL `POW()`
        function call with the current expression as the base and `other` as the
        exponent. The resulting SQL fragment and its parameters are stored internally,
        allowing method chaining.

        Args:
            other (Any): The exponent. Can be a :class:`ColumnsOperation`,
                :class:`Column`, or a literal value (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            Simple exponentiation with a literal:

            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: POW("employees"."salary", 2)
            >>> op = employees.salary ** 2
            >>> print(op._output[0])
            'POW("employees"."salary" , %s)'
            >>> print(op._output[1])  # parameters: [2]
            [2]

        Example:
            Exponentiation with another Column:

            >>> # Generate SQL: POW("employees"."salary", "employees"."years")
            >>> op = employees.salary ** employees.years

        Example:
            Chaining with other operations:

            >>> # Generate SQL: POW(("salary" + 1000), 2)
            >>> op = (employees.salary + 1000) ** 2
        """
        self._output = (f'POW({self._output[0]} , {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'POW({self._output[0]} , {other.name})', self._output[1]) if isinstance(other, Column) else (f'POW({self._output[0]} , %s)', self._output[1]+[other])
        return self

    def __rpow__(self, other):
        """Implement reflected exponentiation (right-hand side power) for SQL expressions.

        This method is called when a :class:`ColumnsOperation` appears on the right
        side of the exponentiation operator (`**`), e.g., `5 ** column_operation`.
        It constructs the SQL `POW()` function expression with the left operand as
        the base and the current operation as the exponent, and stores the result
        internally, allowing method chaining.

        The generated SQL expression depends on the type of `other`:
        - If `other` is a :class:`Column`, the expression uses the column name as base.
        - If `other` is a :class:`ColumnsOperation`, the expression combines both
        operations.
        - If `other` is a literal value, the expression uses a parameter placeholder
        (`%s`) and adds the value to the parameters list.

        Args:
            other (Any): The left-hand operand. Can be a :class:`Column`,
                :class:`ColumnsOperation`, or a literal value (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # This will generate SQL: POW(2, "salary")
            >>> op = 2 ** employees.salary
            >>> print(op._output[0])
            'POW(%s , "employees"."salary")'
            >>> print(op._output[1])  # parameters list
            [2]
        """
        self._output = (f'POW({other._output[0]} , {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'POW({other.name} , {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'POW(%s , {self._output[0]})', [other]+self._output[1])
        return self

    def __truediv__(self, other):
        """Implement division (/) for SQL expressions.

        This method constructs a SQL division expression where the current
        :class:`ColumnsOperation` is divided by `other`. It handles various operand
        types:
        - If `other` is a :class:`ColumnsOperation`, the expression combines both
        operations with `/`.
        - If `other` is a :class:`Column`, the expression uses the column name.
        - If `other` is a literal value, the expression uses a parameter placeholder
        (`%s`) and adds the value to the parameters list.

        The result is stored internally, allowing method chaining.

        Args:
            other (Any): The right-hand operand. Can be a :class:`Column`,
                :class:`ColumnsOperation`, or a literal value (int, float, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, enabling further chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # This will generate SQL: ("salary" / 1000)
            >>> op = employees.salary / 1000
            >>> print(op._output[0])
            '("employees"."salary" / %s)'
            >>> print(op._output[1])  # parameters list
            [1000]

            >>> # Combining two operations
            >>> total_hours = employees.hours_worked
            >>> avg_hours = total_hours / employees.employee_count
            >>> # SQL: ("hours_worked" / "employee_count")
        """
        self._output = (f'({self._output[0]} / {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} / {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} / %s)', self._output[1]+[other])
        return self

    def __rtruediv__(self, other):
        """Implement reflected division (right-hand side division) for SQL expressions.

        This method is called when a :class:`ColumnsOperation` appears on the right
        side of a division operator, e.g., `10 / column_operation`. It constructs
        the SQL expression for dividing `other` by the current operation and stores
        the result internally, allowing method chaining.

        The generated SQL expression will use the appropriate operator:
        - If `other` is a :class:`Column`, the expression uses the column name.
        - If `other` is a :class:`ColumnsOperation`, the expression combines both
        operations.
        - If `other` is a literal value, the expression uses a parameter placeholder
        (`%s`) and adds the value to the parameters list.

        Args:
            other (Any): The left-hand operand (the numerator). Can be a
                :class:`Column`, :class:`ColumnsOperation`, or a literal value
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: (1000 / "salary")
            >>> op = 1000 / employees.salary
            >>> print(op._output[0])
            '(1000 / "employees"."salary")'
            >>> print(op._output[1])  # parameters list
            []
        """
        self._output = (f'({other._output[0]} / {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} / {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s / {self._output[0]})', [other]+self._output[1])
        return self

    def __mod__(self, other):
        """Implement the modulo (remainder) operation for SQL expressions.

        This method is called when the `%` operator is used with a
        :class:`ColumnsOperation` on the left side, e.g.,
        `column_operation % 10`. It constructs the SQL expression for taking the
        modulus of the current operation by `other` and stores the result
        internally, allowing method chaining.

        The generated SQL expression will use the appropriate representation:
        - If `other` is a :class:`Column`, the expression uses the column name.
        - If `other` is a :class:`ColumnsOperation`, the expression combines both
        operations.
        - If `other` is a literal value, the expression uses a parameter placeholder
        (`%s`) and adds the value to the parameters list.

        Args:
            other (Any): The right-hand operand (the divisor). Can be a
                :class:`Column`, :class:`ColumnsOperation`, or a literal value
                (int, float, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: ("salary" % 1000)
            >>> op = employees.salary % 1000
            >>> print(op._output[0])
            '("employees"."salary" % %s)'
            >>> print(op._output[1])
            [1000]
        """
        self._output = (f'({self._output[0]} % {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} % {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} % %s)', self._output[1]+[other])
        return self

    def __rmod__(self, other):
        """Implement reflected modulo (right-hand side modulo) for SQL expressions.

        This method is called when a :class:`ColumnsOperation` appears on the right
        side of a modulo operator, e.g., `10 % column_operation`. It constructs the
        SQL expression for computing the remainder when `other` is divided by the
        current operation and stores the result internally, allowing method chaining.

        The generated SQL expression will use the appropriate representation:
        - If `other` is a :class:`Column`, the expression uses the column name.
        - If `other` is a :class:`ColumnsOperation`, the expression combines both
        operations.
        - If `other` is a literal value, the expression uses a parameter placeholder
        (`%s`) and adds the value to the parameters list.

        Args:
            other (Any): The left-hand operand (the dividend). Can be a
                :class:`Column`, :class:`ColumnsOperation`, or a literal value
                (int, float, str, etc.). Note that modulo with strings is not
                typical; the operator is primarily intended for numeric types.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: (10 % "salary")
            >>> op = 10 % employees.salary
            >>> print(op._output[0])
            '(10 % "employees"."salary")'
            >>> print(op._output[1])  # parameters list
            []
        """
        self._output = (f'({other._output[0]} % {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} % {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s % {self._output[0]})', [other]+self._output[1])
        return self


    def __getitem__(self, key: slice):
        """Generate a SQL SUBSTRING expression from a slice operation on a string column.

        This method implements Python's subscript syntax (square brackets) for
        :class:`ColumnsOperation` objects when the associated column is of a string
        type. It translates slice indices into a PostgreSQL `SUBSTRING` function
        that extracts a portion of the column value. The method handles various
        slice configurations including positive, negative, and `None` start/stop
        values, adapting the SQL parameters accordingly.

        The generated SQL and its parameter list are stored in `self._output`,
        allowing this operation to be chained with other column operations or used
        in `WHERE` clauses and `SELECT` expressions.

        Args:
            key (slice): A Python slice object specifying the start and stop
                positions for substring extraction. Both `start` and `stop` can
                be `None`, positive, or negative integers, following Python's
                indexing semantics (0-based). However, PostgreSQL's `SUBSTRING`
                uses 1-based indexing, so the method adjusts indices accordingly.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing method chaining.

        Raises:
            TypeError: If `key` is not a slice object.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Extract first 3 characters of the "name" column
            >>> op = employees.name[:3]
            >>> print(op._output[0])
            'SUBSTRING("employees"."name" , 1 , %s)'
            >>> print(op._output[1])  # parameters
            [3]

            >>> # Extract from index 2 to the end (Python 0-based, SQL 1-based)
            >>> op = employees.name[2:]
            >>> print(op._output[0])
            'SUBSTRING("employees"."name" , %s , LENGTH("employees"."name"))'
            >>> print(op._output[1])
            [3]  # because 2+1

            >>> # Negative slicing: last 5 characters
            >>> op = employees.name[-5:]
            >>> print(op._output[0])
            'SUBSTRING("employees"."name" , LENGTH("employees"."name") - %s , LENGTH("employees"."name"))'
            >>> print(op._output[1])
            [4]  # abs(-5) - 1 = 4

            >>> # Combined with other operations
            >>> op = employees.name[1:5].upper()
            >>> print(op._output[0])
            'UPPER(SUBSTRING("employees"."name" , %s , %s))'
            >>> print(op._output[1])
            [2, 4]  # start=1 -> 2, stop=5 -> length=4
        """
        if self._output:
            if key.start == None and key.stop ==  None:
                self._output = (f'SUBSTRING({self._output[0]} , 1 , LENGTH({self._output[0]}) + 1)', self._output[1] + self._output[1])   #
            elif key.start == None and key.stop < 0:
                self._output = (f'SUBSTRING({self._output[0]} , 1 , LENGTH({self._output[0]}) - %s)', self._output[1] + self._output[1] + [abs(key.stop)])  #
            elif key.start == None and key.stop >= 0:
                self._output = (f'SUBSTRING({self._output[0]} , 1 , %s)', self._output[1] + [key.stop])  #  
            elif key.start >= 0 and key.stop ==  None:
                self._output = (f'SUBSTRING({self._output[0]} , %s , LENGTH({self._output[0]}))', self._output[1] + [key.start + 1] + self._output[1])  #   
            elif key.start < 0 and key.stop == None:
                self._output = (f'SUBSTRING({self._output[0]} , LENGTH({self._output[0]}) - %s , LENGTH({self._output[0]}))', self._output[1] + self._output[1] + [abs(key.start) - 1] + self._output[1])  #
            elif key.start >= 0 and key.stop < 0:
                self._output = (f'SUBSTRING({self._output[0]} , %s , LENGTH({self._output[0]}) - %s)', self._output[1] +  [key.start + 1] + self._output[1] + [abs(key.stop - key.start)])  #  
            elif key.start >= 0 and key.stop > 0:
                self._output = (f'SUBSTRING({self._output[0]} , %s , %s)', self._output[1] + [key.start + 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop < 0:
                self._output = (f'SUBSTRING({self._output[0]} , LENGTH({self._output[0]}) - %s , %s)', self._output[1] + self._output[1] + [abs(key.start) - 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop > 0:
                self._output = (f'SUBSTRING({self._output[0]} , LENGTH({self._output[0]}) - %s ,  %s - (LENGTH({self._output[0]}) - %s))', self._output[1] + self._output[1] + [abs(key.start) - 1, key.stop] + self._output[1] + [abs(key.start)])
        else:
            if key.start == None and key.stop ==  None:
                self._output = (f'SUBSTRING({self.col_obj.name} , 1 , LENGTH({self.col_obj.name}) + 1)', [])   #
            elif key.start == None and key.stop < 0:
                self._output = (f'SUBSTRING({self.col_obj.name} , 1 , LENGTH({self.col_obj.name}) - %s)', [abs(key.stop)])  #
            elif key.start == None and key.stop >= 0:
                self._output = (f'SUBSTRING({self.col_obj.name} , 1 , %s)', [key.stop])  #  
            elif key.start >= 0 and key.stop ==  None:
                self._output = (f'SUBSTRING({self.col_obj.name} , %s , LENGTH({self.col_obj.name}))', [key.start + 1])  #   
            elif key.start < 0 and key.stop == None:
                self._output = (f'SUBSTRING({self.col_obj.name} , LENGTH({self.col_obj.name}) - %s , LENGTH({self.col_obj.name}))', [abs(key.start) - 1])  #
            elif key.start >= 0 and key.stop < 0:
                self._output = (f'SUBSTRING({self.col_obj.name} , %s , LENGTH({self.col_obj.name}) - %s)', [key.start + 1, abs(key.stop - key.start)])  #  
            elif key.start >= 0 and key.stop > 0:
                self._output = (f'SUBSTRING({self.col_obj.name} , %s , %s)', [key.start + 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop < 0:
                self._output = (f'SUBSTRING({self.col_obj.name} , LENGTH({self.col_obj.name}) - %s , %s)', [abs(key.start) - 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop > 0:
                self._output = (f'SUBSTRING({self.col_obj.name} , LENGTH({self.col_obj.name}) - %s ,  %s - (LENGTH({self.col_obj.name}) - %s))', [abs(key.start) - 1, key.stop, abs(key.start)])
        return self

    def eq(self, value):
        """Create an equality comparison SQL expression.

        This method generates a SQL equality condition between the current
        column/expression and the provided value. It is equivalent to using the
        `==` operator but provided as an explicit method for clarity in complex
        conditions. The operation mutates the internal `_output` state and returns
        `self` for method chaining.

        Args:
            value (Any): The right-hand side of the equality comparison. Can be a
                :class:`Column` object, a :class:`ColumnsOperation` (for comparing
                two expressions), or a literal value (str, int, float, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Simple equality with literal value
            >>> condition = employees.department.eq("Engineering")
            >>> print(condition._output[0])
            '("employees"."department" = %s)'
            >>> print(condition._output[1])  # parameters
            ['Engineering']
            >>>
            >>> # Equality between two columns
            >>> condition = employees.manager_id.eq(employees.id)
            >>> print(condition._output[0])
            '("employees"."manager_id" = "employees"."id")'
        """
        self._output = (f'{self._output[0]} = {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} = {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} = %s', self._output[1] + [value])
        return self

    def __eq__(self, value):
        """Implement equality comparison for SQL expressions.

        This special method is called when a :class:`ColumnsOperation` instance is
        compared with another value using the `==` operator. It constructs the SQL
        expression for equality (`=`) and stores the result internally, allowing
        method chaining.

        The generated SQL expression will use the appropriate syntax:
        - If `value` is a :class:`Column`, the expression uses the column name.
        - If `value` is a :class:`ColumnsOperation`, the expression combines both
        operations.
        - If `value` is a literal, the expression uses a parameter placeholder
        (`%s`) and adds the value to the parameters list.

        Args:
            value (Any): The right-hand operand. Can be a :class:`Column`,
                :class:`ColumnsOperation`, or a literal value.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: ("salary" = 50000)
            >>> condition = employees.salary == 50000
            >>> print(condition._output[0])
            '("employees"."salary" = %s)'
            >>> print(condition._output[1])  # parameters list
            [50000]
            >>>
            >>> # Combining with AND
            >>> condition2 = (employees.department == "Engineering") & (employees.salary > 60000)
            >>> print(condition2._output[0])
            '(("employees"."department" = %s) AND ("employees"."salary" > %s))'
            >>> print(condition2._output[1])
            ['Engineering', 60000]
        """
        self._output = (f'{self._output[0]} = {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} = {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} = %s', self._output[1] + [value])
        return self

    def ne(self, value):
        """Create a SQL inequality comparison (`!=`) for this column operation.

        This method generates a SQL `!=` expression comparing the current operation
        with the provided value. It is the explicit (non-operator) version of
        `__ne__`, useful when the inequality operator cannot be used directly (e.g.,
        in contexts where operator overloading is not supported). The result is
        stored internally, allowing method chaining.

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - A :class:`Column` (using the column's name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameter list).

        Args:
            value (Any): The right-hand side of the inequality. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Explicit inequality: salary != 50000
            >>> op = employees.salary.ne(50000)
            >>> print(op._output[0])
            '("employees"."salary" != %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Chaining with logical operators
            >>> cond = employees.salary.ne(0) & employees.department.ne("IT")
        """
        self._output = (f'{self._output[0]} != {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} != {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} != %s', self._output[1] + [value])
        return self

    def __ne__(self, value):
        """Implement the inequality operator (`!=`) for SQL expressions.

        This special method is called when the `!=` operator is used between a
        :class:`ColumnsOperation` and another operand. It constructs a SQL `!=`
        expression comparing the current operation with the provided value and
        stores the result internally, allowing method chaining.

        The generated SQL expression adapts to the type of `value`:
        - If `value` is a :class:`ColumnsOperation`, both operations are combined.
        - If `value` is a :class:`Column`, the column name is used directly.
        - If `value` is a literal, a parameter placeholder (`%s`) is used, and the
        value is appended to the parameters list.

        Args:
            value (Any): The right-hand side of the inequality. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: ("salary" != 50000)
            >>> cond = employees.salary != 50000
            >>> print(cond._output[0])
            '("employees"."salary" != %s)'
            >>> print(cond._output[1])
            [50000]
            >>> # Combine with another condition
            >>> cond2 = (employees.salary != 0) & (employees.department != "IT")
        """
        self._output = (f'{self._output[0]} != {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} != {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} != %s', self._output[1] + [value])
        return self

    def gt(self, value):
        """Create a SQL greater-than comparison (`>`) for this column operation.

        This method generates a SQL `>` expression comparing the current operation
        with the provided value. It is the explicit (non-operator) version of
        `__gt__`, useful when the greater-than operator cannot be used directly (e.g.,
        in contexts where operator overloading is not supported). The result is
        stored internally, allowing method chaining.

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - A :class:`Column` (using the column's name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameter list).

        Args:
            value (Any): The right-hand side of the comparison. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Explicit greater-than: salary > 50000
            >>> op = employees.salary.gt(50000)
            >>> print(op._output[0])
            '("employees"."salary" > %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Chaining with logical operators
            >>> cond = employees.salary.gt(0) & employees.department.gt("IT")
        """
        self._output = (f'{self._output[0]} > {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} > {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} > %s', self._output[1] + [value])
        return self

    def __gt__(self, value):
        """Create a SQL greater-than comparison (`>`) for this column operation.

        This method is called when the `>` operator is used with a
        :class:`ColumnsOperation` instance on the left-hand side. It generates the
        SQL expression `operation > other` and stores it internally, allowing
        method chaining. The comparison supports:

        - Another :class:`ColumnsOperation`: combines both SQL expressions.
        - A :class:`Column`: uses the column's fully qualified name.
        - A literal value: uses a parameter placeholder (`%s`) and appends the
        value to the parameter list.

        Args:
            value (Any): The right-hand side of the comparison. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: ("salary" > 50000)
            >>> cond = employees.salary > 50000
            >>> print(cond._output[0])
            '("employees"."salary" > %s)'
            >>> print(cond._output[1])
            [50000]
            >>> # Chaining with another column:
            >>> cond2 = employees.bonus > employees.salary * 0.1
        """
        self._output = (f'{self._output[0]} > {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} > {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} > %s', self._output[1] + [value])
        return self

    def lt(self, value):
        """Create a SQL less-than comparison (`<`) for this column operation.

        This method generates a SQL `<` expression comparing the current operation
        with the provided value. It is the explicit (non-operator) version of
        `__lt__`, useful when the comparison operator cannot be used directly (e.g.,
        in contexts where operator overloading is not supported). The result is
        stored internally, allowing method chaining.

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - A :class:`Column` (using the column's name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameter list).

        Args:
            value (Any): The right-hand side of the comparison. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Explicit less-than: salary < 50000
            >>> op = employees.salary.lt(50000)
            >>> print(op._output[0])
            '("employees"."salary" < %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Chaining with logical operators
            >>> cond = employees.salary.lt(100000) & employees.department.lt("ZZZ")
        """
        self._output = (f'{self._output[0]} < {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} < {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} < %s', self._output[1] + [value])
        return self

    def __lt__(self, value):
        """Implement the less-than comparison operator (`<`) for SQL expressions.

        This method is called when a :class:`ColumnsOperation` is compared with
        another value using the `<` operator, e.g., `column_operation < 100`.
        It generates the corresponding SQL `LESS THAN` expression and stores
        the result internally, enabling method chaining and composition with
        logical operators like `&` (AND) and `|` (OR).

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - A :class:`Column` (using the column's name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameter list).

        Args:
            value (Any): The right-hand side of the comparison. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: ("salary" < 50000)
            >>> cond = employees.salary < 50000
            >>> print(cond._output[0])
            '("employees"."salary" < %s)'
            >>> print(cond._output[1])
            [50000]
            >>> # Combined condition: salary < 50000 AND department != 'IT'
            >>> final_cond = (employees.salary < 50000) & (employees.department != 'IT')
        """
        self._output = (f'{self._output[0]} < {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} < {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} < %s', self._output[1] + [value])
        return self

    def ge(self, value):
        """Create a SQL 'greater than or equal to' comparison (`>=`) for this column operation.

        This method generates a SQL `>=` expression comparing the current operation
        with the provided value. It is the explicit (non-operator) version of
        `__ge__`, useful when the comparison operator cannot be used directly (e.g.,
        in contexts where operator overloading is not supported). The result is
        stored internally, allowing method chaining.

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - A :class:`Column` (using the column's name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameter list).

        Args:
            value (Any): The right-hand side of the comparison. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Explicit greater-or-equal: salary >= 50000
            >>> op = employees.salary.ge(50000)
            >>> print(op._output[0])
            '("employees"."salary" >= %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Chaining with logical operators
            >>> cond = employees.salary.ge(30000) & employees.age.ge(25)
        """
        self._output = (f'{self._output[0]} >= {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} >= {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} >= %s', self._output[1] + [value])
        return self

    def __ge__(self, value):
        """Implement the greater-than-or-equal-to comparison operator (`>=`) for SQL expressions.

        This method is called when the `>=` operator is used between a
        :class:`ColumnsOperation` and another value (e.g., `op >= other`). It
        constructs a SQL `>=` expression and stores it internally, allowing
        method chaining.

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - A :class:`Column` (using the column's name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameters list).

        Args:
            value (Any): The right-hand side of the comparison. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: ("salary" >= 50000)
            >>> condition = employees.salary >= 50000
            >>> print(condition._output[0])
            '("employees"."salary" >= %s)'
            >>> print(condition._output[1])
            [50000]
            >>> # Chaining with logical operators
            >>> cond = (employees.salary >= 30000) & (employees.age >= 25)
        """
        self._output = (f'{self._output[0]} >= {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} >= {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} >= %s', self._output[1] + [value])
        return self

    def le(self, value):
        """Create a SQL 'less than or equal to' comparison (`<=`) for this column operation.

        This method generates a SQL `<=` expression comparing the current operation
        with the provided value. It is the explicit (non-operator) version of
        `__le__`, useful when the comparison operator cannot be used directly (e.g.,
        in contexts where operator overloading is not supported). The result is
        stored internally, allowing method chaining.

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - A :class:`Column` (using the column's name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameter list).

        Args:
            value (Any): The right-hand side of the comparison. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Explicit less-or-equal: salary <= 50000
            >>> op = employees.salary.le(50000)
            >>> print(op._output[0])
            '("employees"."salary" <= %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Chaining with logical operators
            >>> cond = employees.salary.le(100000) & employees.age.le(65)
        """
        self._output = (f'{self._output[0]} <= {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} <= {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} <= %s', self._output[1] + [value])
        return self

    def __le__(self, value):
        """Implement the 'less than or equal to' comparison (`<=`) for SQL expressions.

        This special method is called when the `<=` operator is used between a
        :class:`ColumnsOperation` and another value. It generates a SQL `<=`
        expression comparing the current operation with the provided value and
        stores the result internally, allowing method chaining.

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - A :class:`Column` (using the column's name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameter list).

        Args:
            value (Any): The right-hand side of the comparison. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: salary <= 50000
            >>> op = employees.salary <= 50000
            >>> print(op._output[0])
            '("employees"."salary" <= %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Compound condition using logical AND
            >>> cond = (employees.salary <= 50000) & (employees.age <= 30)
        """
        self._output = (f'{self._output[0]} <= {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} <= {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} <= %s', self._output[1] + [value])
        return self

    def __and__(self, value):
        """Combine two conditions with a SQL `AND` operator.

        This method implements the bitwise AND operator (`&`) for
        :class:`ColumnsOperation` objects. When used with another
        :class:`ColumnsOperation`, it generates a SQL expression that combines
        both conditions with `AND`. The resulting expression can be used as a
        `WHERE` clause in queries.

        The operation is performed on the internal `_output` state, which is
        updated to contain the new SQL fragment and its parameters.

        Args:
            value (ColumnsOperation): The right-hand side condition to combine
                with the current condition.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations (e.g., `(col1 == 1) & (col2 == 2)`).

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Build a compound condition: salary >= 50000 AND department = 'Engineering'
            >>> cond = (employees.salary >= 50000) & (employees.department == "Engineering")
            >>> # Use the condition in a query
            >>> employees.get_row([employees.name], where=cond)
            # This generates SQL: ... WHERE (("salary" >= %s) AND ("department" = %s))
        """
        self._output = (f'({self._output[0]} AND {value._output[0]})', self._output[1] + value._output[1])
        return self

    def __or__(self, value):
        """Implement logical OR for SQL conditions.

        This method is called when the `|` operator is used between two
        :class:`ColumnsOperation` instances. It generates a SQL expression
        combining the left and right conditions with an `OR` operator, allowing
        complex boolean logic in WHERE clauses.

        The result is stored internally as a tuple `(sql_string, parameters_list)`,
        enabling method chaining for further logical combinations or comparisons.

        Args:
            value (ColumnsOperation): The right-hand side operation to combine
                with the current operation using logical OR.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
                state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Find employees who are either managers or have salary > 100000
            >>> cond = (employees.title == "Manager") | (employees.salary > 100000)
            >>> print(cond._output[0])
            '(("employees"."title" = %s) OR ("employees"."salary" > %s))'
            >>> print(cond._output[1])  # parameters: ["Manager", 100000]
            ['Manager', 100000]

        Note:
            The method assumes `value` is another `ColumnsOperation`. Combining
            with other types is not supported for `__or__`; use explicit method
            calls or wrap literals appropriately.
        """
        self._output = (f'({self._output[0]} OR {value._output[0]})', self._output[1] + value._output[1])
        return self

    def like(self, value):
        """Create a SQL `LIKE` pattern matching expression for this column operation.

        This method generates a SQL `LIKE` expression that compares the current
        column operation against a pattern. It supports patterns from:
            - Another :class:`ColumnsOperation` (e.g., concatenated strings).
            - A :class:`Column` (using the column's name).
            - A literal string value (using a parameter placeholder `%s`).

        The result is stored internally, allowing the expression to be used in
        `WHERE` clauses or combined with other conditions. The method is chainable.

        Args:
            value (Any): The pattern to match against. Can be a :class:`ColumnsOperation`,
                :class:`Column`, or a literal string.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Find employees whose names start with 'A'
            >>> cond = employees.name.like('A%')
            >>> # Using a ColumnsOperation for more complex patterns
            >>> prefix = employees.name.upper() + '%'
            >>> cond = employees.name.like(prefix)
            >>> # Combining with other conditions
            >>> final_cond = cond & (employees.salary > 50000)
        """
        self._output = (f"{self._output[0]} like {value._output[0]}", (self._output[1] + value._output[1]) if self._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} like {value.name}', self._output[1]) if isinstance(value , Column) else (f'{self._output[0]} like %s', self._output[1] + [f'{value}'])
        return self

    def startswith(self, prefix):
        """Just like python startswith(), create a SQL `LIKE` expression that checks if the column starts with a given prefix.

        This method generates a `LIKE` pattern that matches strings beginning with the
        specified prefix. It appends `'%'` to the prefix to match any trailing characters.
        The result is stored internally, allowing the expression to be used in `WHERE`
        clauses or combined with other conditions.

        The prefix can be:
            - Another :class:`ColumnsOperation` (e.g., concatenated expressions).
            - A :class:`Column` (using the column's value).
            - A literal string (using a parameter placeholder `%s`).

        Args:
            prefix (Any): The prefix to match. Can be a :class:`ColumnsOperation`,
                :class:`Column`, or a literal string.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Find employees whose names start with 'A'
            >>> cond = employees.name.startswith('A')
            >>> # Using a ColumnsOperation for a dynamic prefix
            >>> prefix_col = employees.name.upper()
            >>> cond = employees.name.startswith(prefix_col)
            >>> # Combine with other conditions
            >>> final = cond & (employees.salary > 50000)
            >>> # The generated SQL will be like: "employees"."name" LIKE 'A%'
        """
        self._output = (f"{self._output[0]} like {prefix._output[0]} || '%%'", (self._output[1] + prefix._output[1]) if self._output else prefix._output[1]) if isinstance(prefix, ColumnsOperation) else (f"{self._output[0]} like {prefix.name} || '%%'", self._output[1]) if isinstance(prefix , Column) else (f"{self._output[0]} like %s || '%%'", self._output[1] + [f'{prefix}'])
        return self

    def endswith(self, suffix):
        """Just like python endswith(), create a SQL LIKE pattern matching expression for strings ending with a given suffix.

        This method generates a SQL `LIKE` expression that checks whether the current
        column operation's value ends with the specified suffix. The generated SQL
        uses `LIKE '%%' || suffix` to match strings that end with the suffix. The
        suffix can be a literal string, a :class:`Column`, or a :class:`ColumnsOperation`
        for dynamic values.

        The result is stored internally and can be chained with other operations.

        Args:
            suffix (Any): The suffix to match. Can be a :class:`ColumnsOperation`,
                :class:`Column`, or a literal string value.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Find employees whose names end with 'son'
            >>> cond = employees.name.endswith('son')
            >>> # Using a column as suffix
            >>> cond = employees.name.endswith(employees.suffix_column)
            >>> # Combine with other conditions
            >>> final = cond & (employees.salary > 50000)
        """
        self._output = (f"{self._output[0]} like '%%' || {suffix._output[0]}", (self._output[1] + suffix._output[1]) if self._output else suffix._output[1]) if isinstance(suffix, ColumnsOperation) else (f"{self._output[0]} like '%%' || {suffix.name}", self._output[1]) if isinstance(suffix , Column) else (f"{self._output[0]} like '%%' || %s", self._output[1] + [f'{suffix}'])
        return self

    def contains(self, value):
        """Create a SQL `LIKE` pattern matching expression that checks if the current
        column operation contains the given value as a substring.

        This method generates a SQL `LIKE` expression with wildcards on both sides of
        the value: `'%%' || value || '%%'`. This is equivalent to checking if the
        column value contains the specified substring anywhere within it.

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - A :class:`Column` (using the column's name).
            - A literal string value (using a parameter placeholder `%s`).

        The result is stored internally, allowing method chaining.

        Args:
            value (Any): The substring to search for. Can be a :class:`ColumnsOperation`,
                :class:`Column`, or a literal string.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Find employees whose names contain 'Smith'
            >>> cond = employees.name.contains("Smith")
            >>> # Using a column for the pattern (case-insensitive)
            >>> pattern = employees.last_name.lower()
            >>> cond = employees.first_name.contains(pattern)
            >>> # Combine with other conditions
            >>> final_cond = cond & (employees.department == "Sales")
        """
        self._output = (f"{self._output[0]} like '%%' || {value._output[0]} || '%%'", (self._output[1] + value._output[1]) if self._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self._output[0]} like '%%' || {value.name} || '%%'", self._output[1]) if isinstance(value , Column) else (f"{self._output[0]} like '%%' || %s || '%%'", self._output[1] + [f'{value}'])
        return self

    def add_end(self, content):
        """Concatenate additional content to the end of the current SQL expression.

        This method generates a SQL concatenation expression using the `||` operator
        (string concatenation). It appends the provided `content` to the end of the
        current column operation. This is useful for building dynamic SQL strings
        such as constructing full names, adding suffixes, or assembling text values.

        The `content` can be:
            - Another :class:`ColumnsOperation` (the two expressions are concatenated).
            - A :class:`Column` (the column's name is used as the right operand).
            - A literal value (inserted as a parameter placeholder `%s`).

        The method modifies the internal `_output` state and returns `self` for
        method chaining.

        Args:
            content (Any): The content to append to the current expression.
                Can be a :class:`ColumnsOperation`, :class:`Column`, or a literal
                (str, int, etc.). For non-string literals, the value is converted
                to a string for concatenation.

        Returns:
            ColumnsOperation: The current instance with updated SQL expression and
            parameters, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Add a suffix to names
            >>> op = employees.name.add_end(" (Retired)")
            >>> print(op._output[0])
            '("employees"."name" || %s)'
            >>> print(op._output[1])
            [' (Retired)']
            >>> # Chain with another column
            >>> full_name = employees.first_name.add_end(" ").add_end(employees.last_name)
            >>> # Generates: (("first_name" || ' ') || "last_name")
        """
        self._output = (f'({self._output[0]} || {content._output[0]})', self._output[1]+content._output[1] if self._output else content._output[1]) if isinstance(content, ColumnsOperation) else (f'({self._output[0]} || {content.name})', self._output[1] if self._output else []) if isinstance(content, Column) else (f'({self._output[0]} || %s)', self._output[1]+[content] if self._output else [content])
        return self

    def add_first(self, content):
        """Prepend content to the current string expression (SQL concatenation).

        This method generates a SQL string concatenation expression where the
        provided `content` is placed before the current column operation. The
        result is stored internally and the instance is returned for chaining.

        The `content` can be:
            - Another :class:`ColumnsOperation` (the expression is concatenated).
            - A :class:`Column` (the column name is used).
            - A literal value (a parameter placeholder `%s` is used and the value
            is added to the parameter list).

        The SQL operator used is `||`, which is the standard string concatenation
        operator in PostgreSQL.

        Args:
            content (Any): The content to prepend. Can be a :class:`ColumnsOperation`,
                :class:`Column`, or a literal value (str, int, etc.).

        Returns:
            ColumnsOperation: The current instance with updated `_output`,
            allowing method chaining.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Prepend a prefix to the name column: 'Mr. ' || name
            >>> op = employees.name.add_first("Mr. ")
            >>> print(op._output[0])
            '(%s || "employees"."name")'
            >>> print(op._output[1])
            ['Mr. ']
            >>> # Chain with other operations
            >>> op = employees.name.lower().add_first("Prefix: ")
            >>> # Generates SQL: (%s || LOWER("employees"."name"))
        """
        self._output = (f'({content._output[0]} || {self._output[0]})', content._output[1]+self._output[1] if self._output else content._output[1]) if isinstance(content, ColumnsOperation) else (f'({content.name} || {self._output[0]})', self._output[1] if self._output else []) if isinstance(content, Column) else (f'(%s || {self._output[0]})', [content]+self._output[1] if self._output else [content])
        return self

    def replace(self, old: str, new: str):
        """Just like python replace(), generate a SQL `REPLACE` function call for string substitution.

        This method constructs a SQL `REPLACE` expression that substitutes all
        occurrences of `old` with `new` in the current column or operation.
        The result is stored internally, allowing chained operations.

        If the current `_output` is already set (i.e., this is a chained operation),
        the REPLACE is applied to the existing expression. If not, it is applied
        directly to the underlying column.

        Args:
            old (str): The substring to be replaced.
            new (str): The substring to replace with.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Replace 'old' with 'new' in the name column
            >>> op = employees.name.replace('old', 'new')
            >>> print(op._output[0])
            'REPLACE("employees"."name" , %s , %s)'
            >>> print(op._output[1])
            ['old', 'new']
            >>> # Chain with other operations
            >>> op2 = employees.name.upper().replace('A', 'B')
        """
        self._output = (f'REPLACE({self._output[0]} , %s , %s)', self._output[1] + [old, new]) if self._output else (f'REPLACE({self.col_obj.name} , %s , %s)', [old, new])
        return self

    def upper(self):
        """Generate a SQL `UPPER` function call to convert the expression to uppercase.

        This method constructs a SQL `UPPER` expression that converts the current
        column or operation to uppercase. The result is stored internally, allowing
        chained operations. If the current `_output` is already set (i.e., this is a
        chained operation), the UPPER is applied to the existing expression.
        Otherwise, it is applied directly to the underlying column.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Convert name to uppercase for case-insensitive comparison
            >>> op = employees.name.upper() == 'JOHN'
            >>> print(op._output[0])
            '(UPPER("employees"."name") = %s)'
            >>> print(op._output[1])
            ['JOHN']
            >>> # Chain with other string operations
            >>> op2 = employees.name.strip().upper()
        """
        self._output = (f'UPPER({self._output[0]})', self._output[1]) if self._output else (f'UPPER({self.col_obj.name})', [])
        return self

    def lower(self):
        """just like python lower(), generate a SQL `LOWER` function call to convert text to lowercase.

        This method constructs a SQL `LOWER` expression that transforms the current
        column or operation result to lowercase. The result is stored internally,
        allowing chained operations.

        If the current `_output` is already set (i.e., this is a chained operation),
        the `LOWER` is applied to the existing expression. If not, it is applied
        directly to the underlying column.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Convert name to lowercase
            >>> op = employees.name.lower()
            >>> print(op._output[0])
            'LOWER("employees"."name")'
            >>> # Chain with other operations
            >>> op2 = employees.name.upper().lower()  # upper then lower
            >>> print(op2._output[0])
            'LOWER(UPPER("employees"."name"))'
        """
        self._output = (f'LOWER({self._output[0]})', self._output[1]) if self._output else (f'LOWER({self.col_obj.name})', [])
        return self

    def strip(self, chars: str = ' '):
        """just like python strip(), generate a SQL `TRIM` function call to remove characters from both ends.

        This method creates a SQL `TRIM(BOTH ... FROM ...)` expression that strips
        the specified characters from the start and end of the current column or
        operation. If the `_output` is already set (chained operation), the TRIM is
        applied to that expression; otherwise, it is applied to the underlying column.
        The result is stored internally, allowing further method chaining.

        Args:
            chars (str, optional): The characters to remove. Defaults to a single space.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Remove leading/trailing spaces from the name column
            >>> op = employees.name.strip()
            >>> print(op._output[0])
            "TRIM(BOTH ' ' FROM \"employees\".\"name\")"
            >>> # Remove specific characters after an upper() operation
            >>> op = employees.name.upper().strip('_')
            >>> print(op._output[0])
            "TRIM(BOTH '_' FROM UPPER(\"employees\".\"name\"))"
        """
        self._output = (f"TRIM(BOTH '{chars}' FROM {self._output[0]})", self._output[1]) if self._output else (f"TRIM(BOTH '{chars}' FROM {self.col_obj.name})", [])
        return self

    def lstrip(self, chars: str = ' '):
        """just like python's lstrip method, generate a SQL `TRIM(LEADING ...)` expression to remove leading characters.

        This method constructs a SQL `TRIM` function call that strips the specified
        leading characters from the current column or operation. The result is stored
        internally, allowing chained operations.

        If the current `_output` is already set (i.e., this is a chained operation),
        the trimming is applied to the existing expression. Otherwise, it is applied
        directly to the underlying column. The default character to strip is a space.

        Args:
            chars (str, optional): The character(s) to strip from the left side of
                the string. Defaults to a single space (`' '`).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Remove leading spaces from the name column
            >>> op = employees.name.lstrip()
            >>> print(op._output[0])
            "TRIM(LEADING ' ' FROM \"employees\".\"name\")"
            >>> # Remove leading '#' characters from a computed expression
            >>> op = (employees.code + employees.suffix).lstrip('#')
            >>> print(op._output[0])
            "TRIM(LEADING '#' FROM (\"employees\".\"code\" || \"employees\".\"suffix\"))"
        """
        self._output = (f"TRIM(LEADING '{chars}' FROM {self._output[0]})", self._output[1]) if self._output else (f"TRIM(LEADING '{chars}' FROM {self.col_obj.name})", [])
        return self

    def rstrip(self, chars: str = ' '):
        """just like python's rstrip method, generate a SQL `TRIM` expression to remove trailing characters from a string.

        This method constructs a SQL `TRIM(TRAILING ... FROM ...)` expression that
        removes all occurrences of the specified characters from the end (right side)
        of the current column or operation. The result is stored internally, allowing
        chained operations.

        If the current `_output` is already set (i.e., this is a chained operation),
        the `TRIM` is applied to the existing expression. If not, it is applied
        directly to the underlying column.

        Args:
            chars (str, optional): The characters to remove from the trailing end.
                Defaults to a single space (`' '`).

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Remove trailing spaces from the name column
            >>> op = employees.name.rstrip()
            >>> print(op._output[0])
            "TRIM(TRAILING ' ' FROM \"employees\".\"name\")"
            >>> print(op._output[1])
            []
            >>> # Remove trailing underscores and chain with upper()
            >>> op2 = employees.name.rstrip('_').upper()
            >>> print(op2._output[0])
            "UPPER(TRIM(TRAILING '_' FROM \"employees\".\"name\"))"
            >>> print(op2._output[1])
            []
        """
        self._output = (f"TRIM(TRAILING '{chars}' FROM {self._output[0]})", self._output[1]) if self._output else (f"TRIM(TRAILING '{chars}' FROM {self.col_obj.name})", [])
        return self

    def In(self, value):
        """Generate a SQL `IN` clause or equality for this column operation.

        This method constructs a SQL `IN` expression that checks whether the current
        column operation's value matches any value in a given set or subquery.
        The behavior depends on the type of `value`:

        - If `value` is a :class:`ColumnsOperation`, it generates a subquery IN clause
        (e.g., `column IN (subquery)`).
        - If `value` is a list or tuple, it generates `IN (?, ?, ...)` with one
        placeholder per item, and adds all items as parameters.
        - If `value` is a scalar (single value), it generates an equality condition
        `= ?` instead of `IN`, which is equivalent and more efficient.

        The result is stored internally, allowing chained operations.

        Args:
            value (Any): The set of values or subquery to check against.
                Can be a :class:`ColumnsOperation`, :class:`Column` (though this
                would be unusual), `list`, `tuple`, or a scalar value.

        Returns:
            ColumnsOperation: The current instance with updated internal `_output`
            state, allowing chained operations.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Using a list of values
            >>> cond = employees.department.In(['Engineering', 'Sales', 'Marketing'])
            >>> print(cond._output[0])
            '("employees"."department" IN (%s,%s,%s))'
            >>> print(cond._output[1])
            ['Engineering', 'Sales', 'Marketing']
            >>>
            >>> # Using a subquery (ColumnsOperation)
            >>> subquery = driver.departments.id  # assuming a column
            >>> cond2 = employees.dept_id.In(subquery)
            >>> # The generated SQL will be something like:
            >>> # ("employees"."dept_id" IN ("departments"."id"))
            >>>
            >>> # Scalar value produces equality
            >>> cond3 = employees.id.In(100)
            >>> print(cond3._output[0])
            '("employees"."id" = %s)'
            >>> print(cond3._output[1])
            [100]
        """
        self._output = (f"{self._output[0]} IN ({value._output[0]})", self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self._output[0]} IN ({','.join(['%s'] * len(value))})",self._output[1] + list(value)) if isinstance(value, (list, tuple)) else (f"{self._output[0]} = %s",self._output[1] + [value])
        return self


class Column:
    """
    A database column representation with expression-building capabilities.

    This class represents a column in a database table. It stores the column's
    fully qualified name, its Python datatype, and a reference to its parent
    :class:`Table`. The primary purpose of a `Column` object is to serve as a
    starting point for building SQL expressions using operator overloading and
    method chaining. When you perform operations like `employees.salary + 100`,
    the `Column` object delegates to a :class:`ColumnsOperation` to build the
    corresponding SQL fragment, which can then be used in `WHERE` clauses,
    `SELECT` lists, `UPDATE` assignments, and more.

    The class supports:
    - Arithmetic operations (+, -, *, /, %, **) with automatic selection of
      string concatenation (`||`) vs. numeric addition (`+`) based on datatype.
    - Comparison operators (==, !=, <, <=, >, >=) via operator overloading.
    - String methods: `like()`, `startswith()`, `endswith()`, `contains()`,
      `upper()`, `lower()`, `replace()`, `strip()`, `lstrip()`, `rstrip()`,
      and slice notation for `SUBSTRING`.
    - Collection methods: `In()` for `IN` clauses.
    - Concatenation helpers: `add_end()`, `add_first()`.
    - DDL operations: `rename()` and `delete_column()` (with safety flags).

    Instances of `Column` are automatically created by the :class:`Table` class
    when it initializes, and are attached as attributes to the `Table` object
    (e.g., `employees.name`). You typically do not instantiate `Column` directly.

    Attributes:
        name (str): The fully qualified column name, including the table name
            and quoted identifier (e.g., `"employees"."salary"`). Used in SQL
            generation.
        first_name (str): The quoted column name without the table prefix
            (e.g., `"salary"`). Used in DDL statements and in contexts where the
            table is already specified.
        table_obj (Table): The parent :class:`Table` object that this column
            belongs to.
        datatype (type): The Python type that corresponds to the column's SQL
            data type (e.g., `int`, `str`, `float`, `bool`, `bytes`). Used to
            choose the correct SQL operator for addition (`+` for numeric,
            `||` for string concatenation).

    Example:
        >>> from ormophine.Postgresql import Driver, Table
        >>> driver = Driver(...)
        >>> employees = driver.employees
        >>> # Access a column (automatically created)
        >>> salary_col = employees.salary
        >>> print(salary_col.name)
        '"employees"."salary"'
        >>>
        >>> # Build an expression
        >>> cond = employees.salary > 50000
        >>> print(cond._output[0])
        '("employees"."salary" > %s)'
        >>> # Use in a query
        >>> results = employees.get_row([employees.name], where=cond)
        >>>
        >>> # String operations
        >>> upper_name = employees.name.upper()
        >>> starts_with_a = employees.name.startswith('A')
        >>>
        >>> # DDL: rename a column (requires confirmation flags on Table)
        >>> # employees.rename_column(employees.salary, "base_salary")
    """
    def __init__(self, table_obj: Table, column_name: str, datatype: type):
        """Initialize a Column instance representing a database column.

        This constructor creates a column object that references a specific table
        and column in the database. It stores the column's fully qualified name
        (including the table name), a simplified quoted name for use in SQL
        statements, and its Python datatype. Column objects are typically created
        automatically when a :class:`Table` is instantiated and are accessible as
        attributes of the table object.

        The `name` attribute is used in generated SQL to qualify the column with
        its table, ensuring unambiguous references in JOINs and complex queries.
        The `first_name` attribute provides the column name alone, quoted, which is
        used in contexts where the table is already specified (e.g., SET clauses).

        Args:
            table_obj (Table): The Table object that this column belongs to.
            column_name (str): The name of the column in the database.
            datatype (type): The Python type corresponding to the column's SQL data
                type (e.g., int, str, float, bool, bytes).

        Returns:
            None: This method initializes the instance and does not return a value.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Columns are automatically created as attributes:
            >>> print(employees.name)  # Column object
            >>> # Manual creation (typically not needed):
            >>> from ormophine.Postgresql import Column
            >>> col = Column(employees, "salary", int)
            >>> print(col.name)
            '"employees"."salary"'
            >>> print(col.first_name)
            '"salary"'
            >>> print(col.datatype)
            <class 'int'>
        """
        self.name = table_obj.name_ + '."' + column_name + '"'
        self.first_name = f'"{column_name}"'
        self.table_obj = table_obj
        self.datatype = datatype

    def __hash__(self):
        """Compute the hash value for this column object.

        This method enables :class:`Column` objects to be used as keys in
        dictionaries and sets. The hash is based on the column's fully qualified
        name (including the table name), which uniquely identifies a column
        within a database session.

        Returns:
            int: The hash value of the column's full name.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> col = employees.id
            >>> hash(col)  # Returns a hash based on '"employees"."id"'
            >>> # Columns can be used in sets:
            >>> {employees.id, employees.name}
        """
        return hash(self.name)

    def __add__(self, value):
        """Implement column addition or string concatenation.

        This method overloads the `+` operator for :class:`Column` objects.
        It creates a :class:`ColumnsOperation` instance initialized with this column,
        then delegates to the operation's `__add__` method to combine it with `value`.
        The resulting expression will use `+` for numeric columns or `||` for
        string/text columns (based on the column's datatype) when generating SQL.

        Args:
            value (Any): The right-hand operand. Can be a :class:`Column`,
                a :class:`ColumnsOperation`, a numeric value, a string, etc.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` representing the
            SQL expression for the addition or concatenation.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Numeric addition: salary + bonus
            >>> expr = employees.salary + employees.bonus
            >>> # String concatenation: first_name + ' ' + last_name
            >>> full_name = employees.first_name + ' ' + employees.last_name
            >>> # Use the expression in a query
            >>> results = employees.get_row([expr], where=employees.id == 1)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob + value

    def __radd__(self, value):
        """Implement reflected addition (right-hand side addition) for a column.

        This method is called when a :class:`Column` appears on the right side of an
        addition operator, e.g., `100 + employees.salary` or `'prefix ' + employees.name`.
        It creates a :class:`ColumnsOperation` object for the column and then performs
        the addition with the given value.

        The operator used depends on the column's datatype:
        - If the column is a string (`str`), the SQL `||` concatenation operator is used.
        - Otherwise, the SQL `+` addition operator is used.

        The result is a :class:`ColumnsOperation` that can be used in queries or
        further chained operations.

        Args:
            value (Any): The left-hand operand of the addition. Can be a literal
                (int, float, str, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` representing the
            addition expression.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Numeric addition
            >>> op = 1000 + employees.salary
            >>> print(op._output[0])  # SQL expression
            '(1000 + "employees"."salary")'
            >>> print(op._output[1])  # parameters
            []
            >>>
            >>> # String concatenation
            >>> op = 'Name: ' + employees.name
            >>> print(op._output[0])
            '(%s || "employees"."name")'
            >>> print(op._output[1])
            ['Name: ']
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value + temp_ob

    def __sub__(self, value):
        """Implement subtraction of a value from this column.

        This method overloads the `-` operator for :class:`Column` objects.
        It creates a :class:`ColumnsOperation` that represents the SQL expression
        `column - value`. The operation is chainable and can be used in `WHERE`
        clauses, `SET` expressions, or as part of larger computations.

        The subtraction is always numeric (using the `-` operator in SQL), regardless
        of the column's datatype. If the column is of a string type and you intend
        to remove a suffix, consider using string functions instead.

        Args:
            value (Any): The right-hand side of the subtraction. Can be a
                :class:`Column`, :class:`ColumnsOperation`, or a literal value
                (int, float, etc.).

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the subtraction expression, with the SQL fragment and parameters
            stored internally.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Subtract a constant from a column
            >>> expr = employees.salary - 5000
            >>> # Use in update: decrease salary by 5000 for all employees
            >>> employees.update({employees.salary: employees.salary - 5000}, where=...)
            >>>
            >>> # Subtract one column from another
            >>> expr = employees.max_salary - employees.min_salary
            >>> # Use in SELECT: get salary range
            >>> rows = employees.get_row([expr], where=...)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob - value

    def __rsub__(self, value):
        """Implement reflected subtraction (right-hand side subtraction) for a column.

        This method is called when a :class:`Column` appears on the right side of a
        subtraction operator, e.g., `5 - employees.salary`. It creates a
        :class:`ColumnsOperation` that represents the subtraction expression and
        delegates the actual operation to the `__sub__` method of the operation builder.

        The generated SQL expression will have the form `(value - column)` where
        `value` can be a literal, another :class:`Column`, or a
        :class:`ColumnsOperation`.

        Args:
            value (Any): The left-hand operand (the subtrahend). Can be a literal
                (int, float, str, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            subtraction expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: (1000 - "salary")
            >>> op = 1000 - employees.salary
            >>> print(op._output[0])
            '(1000 - "employees"."salary")'
            >>> print(op._output[1])
            []
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value - temp_ob

    def __mul__(self, value):
        """Implement multiplication (`*`) of a column by a value.

        This method is called when a :class:`Column` is multiplied, e.g.,
        `employees.salary * 1.1`. It creates a :class:`ColumnsOperation` that
        represents the multiplication expression and delegates the actual operation
        to the `__mul__` method of the operation builder.

        The generated SQL expression will have the form `(column * value)` where
        `value` can be a literal, another :class:`Column`, or a
        :class:`ColumnsOperation`. For string columns, multiplication is not
        typically used; this is intended for numeric operations.

        Args:
            value (Any): The right-hand operand (the multiplier). Can be a literal
                (int, float, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            multiplication expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: (salary * 1.1) to calculate a 10% raise
            >>> op = employees.salary * 1.1
            >>> print(op._output[0])
            '("employees"."salary" * %s)'
            >>> print(op._output[1])
            [1.1]
            >>> # Chain with other operations
            >>> bonus = employees.salary * 0.05 + employees.bonus
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob * value

    def __rmul__(self, value):
        """Implement reflected multiplication (right-hand side multiplication) for a column.

        This method is called when a :class:`Column` appears on the right side of a
        multiplication operator, e.g., `5 * employees.salary`. It creates a
        :class:`ColumnsOperation` that represents the multiplication expression and
        delegates the actual operation to the appropriate operator.

        The generated SQL expression will have the form `(value * column)` where
        `value` can be a literal, another :class:`Column`, or a
        :class:`ColumnsOperation`.

        Args:
            value (Any): The left-hand operand (the multiplier). Can be a literal
                (int, float, str, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            multiplication expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: (1000 * "salary")
            >>> op = 1000 * employees.salary
            >>> print(op._output[0])
            '(1000 * "employees"."salary")'
            >>> print(op._output[1])
            []
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value * temp_ob

    def __pow__(self, value):
        """Implement the power/exponentiation operator (`**`) for a column.

        This method is called when a :class:`Column` is raised to a power, e.g.,
        `employees.salary ** 2`. It creates a :class:`ColumnsOperation` that
        represents the exponentiation expression and delegates the actual operation
        to the `__pow__` method of the operation builder, which generates a SQL
        `POW(column, value)` expression.

        The resulting SQL expression will be parameterized appropriately:
        - If `value` is a literal, it will be parameterized as `%s`.
        - If `value` is another :class:`Column` or :class:`ColumnsOperation`,
        the expression will combine them.

        Args:
            value (Any): The exponent. Can be a literal (int, float, etc.),
                a :class:`Column`, or a :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            exponentiation expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: POW("salary", 2)
            >>> op = employees.salary ** 2
            >>> print(op._output[0])
            'POW("employees"."salary" , %s)'
            >>> print(op._output[1])
            [2]
            >>> # Chain with other operations
            >>> op2 = (employees.salary ** 2) + employees.bonus
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob ** value

    def __rpow__(self, value):
        """Implement reflected exponentiation (right-hand side power) for a column.

        This method is called when a :class:`Column` appears on the right side of the
        exponentiation operator, e.g., `2 ** employees.salary`. It creates a
        :class:`ColumnsOperation` that represents the exponentiation expression and
        delegates the actual operation to the `__pow__` method of the operation builder.

        The generated SQL expression will use the `POW` function with the form
        `POW(value, column)` where `value` can be a literal, another :class:`Column`,
        or a :class:`ColumnsOperation`.

        Args:
            value (Any): The left-hand operand (the base). Can be a literal
                (int, float, etc.), a :class:`Column`, or a :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            exponentiation expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: POW(2, "salary")
            >>> op = 2 ** employees.salary
            >>> print(op._output[0])
            'POW(%s , "employees"."salary")'
            >>> print(op._output[1])
            [2]
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob ** value

    def __truediv__(self, value):
        """Implement division for a column.

        This method is called when a :class:`Column` is divided by a value using the
        `/` operator. It creates a :class:`ColumnsOperation` that represents the
        division expression and delegates the actual operation to the operation
        builder.

        Args:
            value (Any): The right-hand operand (the divisor). Can be a literal
                (int, float, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            division expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: ("salary" / 2)
            >>> op = employees.salary / 2
            >>> print(op._output[0])
            '("employees"."salary" / %s)'
            >>> print(op._output[1])
            [2]
            >>> # Division by another column
            >>> op2 = employees.salary / employees.bonus
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob / value

    def __rtruediv__(self, value):
        """Implement reflected division (right‑hand side division) for a column.

        This method is called when a :class:`Column` appears on the right side of a
        division operator, e.g., `100 / employees.salary`. It creates a
        :class:`ColumnsOperation` that represents the division expression and
        delegates the actual operation to the `__truediv__` method of the operation
        builder, with the column as the right operand.

        The generated SQL expression will have the form `(value / column)` where
        `value` can be a literal, another :class:`Column`, or a
        :class:`ColumnsOperation`.

        Args:
            value (Any): The left‑hand operand (the numerator). Can be a literal
                (int, float, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            division expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: (1000 / "salary")
            >>> op = 1000 / employees.salary
            >>> print(op._output[0])
            '(1000 / "employees"."salary")'
            >>> print(op._output[1])
            []
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value / temp_ob

    def __mod__(self, value):
        """Implement the modulo (`%`) operator for a column expression.

        This method is called when the modulo operator is used with a :class:`Column`
        on the left side, e.g., `employees.salary % 10`. It creates a
        :class:`ColumnsOperation` that represents the modulo expression and
        delegates the actual operation to the `__mod__` method of the operation
        builder.

        The generated SQL expression will have the form `(column % value)` where
        `value` can be a literal, another :class:`Column`, or a
        :class:`ColumnsOperation`. The modulo operator is typically used with
        numeric columns.

        Args:
            value (Any): The right‑hand operand. Can be a literal (int, float, etc.),
                a :class:`Column`, or a :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            modulo expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: ("salary" % 10)
            >>> op = employees.salary % 10
            >>> print(op._output[0])
            '("employees"."salary" % %s)'
            >>> print(op._output[1])
            [10]
            >>> # Chaining with other operations
            >>> op2 = (employees.salary % 5) == 0
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob % value

    def __rmod__(self, value):
        """Implement reflected modulo (right-hand side modulo) for a column.

        This method is called when a :class:`Column` appears on the right side of a
        modulo operator, e.g., `10 % employees.salary`. It creates a
        :class:`ColumnsOperation` that represents the modulo expression and delegates
        the actual operation to the `__mod__` method of the operation builder.

        The generated SQL expression will have the form `(value % column)` where
        `value` can be a literal, another :class:`Column`, or a
        :class:`ColumnsOperation`.

        Args:
            value (Any): The left-hand operand (the dividend). Can be a literal
                (int, float, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            modulo expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: (10 % "salary")
            >>> op = 10 % employees.salary
            >>> print(op._output[0])
            '(10 % "employees"."salary")'
            >>> print(op._output[1])
            []
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value % temp_ob

    def eq(self, value):
        """Create a SQL equality comparison (`=`) for this column.

        This method generates a SQL `=` expression with the column on the left
        and the provided value on the right. It is the explicit (non-operator)
        version of `__eq__`, useful when the equality operator cannot be used
        directly (e.g., in contexts where operator overloading is not supported).
        The result is returned as a :class:`ColumnsOperation`, allowing further
        chaining or combination with other conditions.

        The right-hand side can be:
            - Another :class:`ColumnsOperation` (e.g., a computed expression).
            - A :class:`Column` (using its fully qualified name).
            - A literal value (int, float, str, etc.), which will be added to
            the parameters list as a placeholder.

        Args:
            value (Any): The right‑hand side of the equality. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or any literal
                value (str, int, float, etc.).

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing
            the equality condition, ready for use in WHERE clauses or
            further chaining.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>>
            >>> # Equality with a literal
            >>> cond = employees.id.eq(100)
            >>> print(cond._output[0])
            '("employees"."id" = %s)'
            >>> print(cond._output[1])
            [100]
            >>>
            >>> # Equality with another column
            >>> cond2 = employees.manager_id.eq(employees.id)
            >>> print(cond2._output[0])
            '("employees"."manager_id" = "employees"."id")'
            >>>
            >>> # Equality with a ColumnsOperation (e.g., computed)
            >>> from ormophine.Postgresql import ColumnsOperation
            >>> bonus = employees.salary * 0.1
            >>> cond3 = employees.bonus.eq(bonus)
            >>> # This generates: ("employees"."bonus" = ("salary" * 0.1))
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} = {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} = {value.name})', []) if isinstance(value, Column) else (f'({self.name} = %s)', [value])
        return temp_ob

    def __eq__(self, value):
        """Create a SQL equality comparison (`=`) for this column.

        This method is called when the `==` operator is used between a
        :class:`Column` and another value. It creates a :class:`ColumnsOperation`
        that represents the equality expression `column = value`, where `value` can
        be a literal, another :class:`Column`, or a :class:`ColumnsOperation`.

        The generated SQL expression will be parameterized when `value` is a literal,
        using a placeholder (`%s`) to prevent SQL injection.

        Args:
            value (Any): The right-hand side of the equality comparison. Can be a
                literal (int, float, str, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            equality expression, ready for use in `WHERE` clauses or chaining with
            logical operators.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Equality with literal
            >>> cond = employees.name == "Alice"
            >>> print(cond._output[0])
            '("employees"."name" = %s)'
            >>> print(cond._output[1])
            ['Alice']
            >>>
            >>> # Equality with another column
            >>> cond2 = employees.manager_id == employees.id
            >>> print(cond2._output[0])
            '("employees"."manager_id" = "employees"."id")'
            >>>
            >>> # Chaining with AND
            >>> final_cond = (employees.salary == 50000) & (employees.department == "Engineering")
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} = {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} = {value.name})', []) if isinstance(value, Column) else (f'({self.name} = %s)', [value])
        return temp_ob

    def ne(self, value):
        """Create a SQL inequality comparison (`!=`) for this column.

        This method generates a `!=` expression comparing the column to a value,
        subquery, or another column. It is the explicit (non-operator) version of
        `__ne__`, useful when the inequality operator cannot be used directly
        (e.g., in contexts where operator overloading is not supported).

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (embedding its SQL and params).
            - A :class:`Column` (using the column's fully qualified name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameter list).

        Args:
            value (Any): The right‑hand side of the inequality. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            inequality expression, ready for use in WHERE clauses or further chaining.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Explicit inequality: salary != 50000
            >>> cond = employees.salary.ne(50000)
            >>> print(cond._output[0])
            '("employees"."salary" != %s)'
            >>> print(cond._output[1])
            [50000]
            >>>
            >>> # Chain with logical operations
            >>> final = employees.salary.ne(0) & employees.department.ne('IT')
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} != {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} != {value.name})', []) if isinstance(value, Column) else (f'({self.name} != %s)', [value])
        return temp_ob

    def __ne__(self, value):
        """Implement the inequality operator (`!=`) for a column.

        This method is called when a :class:`Column` is compared for inequality with
        another value using the `!=` operator. It creates a :class:`ColumnsOperation`
        that represents the SQL expression `column != value`, where `value` can be
        a literal, another :class:`Column`, or a :class:`ColumnsOperation`.

        The generated SQL expression will be parameterized appropriately to prevent
        SQL injection:
        - If `value` is a `ColumnsOperation`, the expression combines both.
        - If `value` is a `Column`, the expression uses the column name.
        - If `value` is a literal, a placeholder `%s` is used and the value is
            added to the parameters list.

        Args:
            value (Any): The right‑hand side of the inequality. Can be a literal
                (int, float, str, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            inequality expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: "salary" != 50000
            >>> op = employees.salary != 50000
            >>> print(op._output[0])
            '("employees"."salary" != %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Compare with another column: "salary" != "bonus"
            >>> op2 = employees.salary != employees.bonus
            >>> print(op2._output[0])
            '("employees"."salary" != "employees"."bonus")'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} != {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} != {value.name})', []) if isinstance(value, Column) else (f'({self.name} != %s)', [value])
        return temp_ob

    def gt(self, value):
        """Create a SQL 'greater than' comparison (`>`) for this column.

        This method generates a SQL `>` expression comparing the column with the
        provided value. It is the explicit (non-operator) version of `__gt__`,
        useful when the comparison operator cannot be used directly (e.g., in
        contexts where operator overloading is not supported or when building
        dynamic queries). The result is a :class:`ColumnsOperation` instance that
        can be chained or used in `WHERE` clauses.

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - Another :class:`Column` (using the column's name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameter list).

        Args:
            value (Any): The right‑hand side of the comparison. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `>` comparison expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Find employees with salary greater than 50000
            >>> cond = employees.salary.gt(50000)
            >>> print(cond._output[0])
            '("employees"."salary" > %s)'
            >>> print(cond._output[1])
            [50000]
            >>>
            >>> # Compare two columns: salary > bonus
            >>> cond2 = employees.salary.gt(employees.bonus)
            >>> print(cond2._output[0])
            '("employees"."salary" > "employees"."bonus")'
            >>>
            >>> # Using with a ColumnsOperation (e.g., salary > (bonus + 1000))
            >>> bonus_plus = employees.bonus + 1000
            >>> cond3 = employees.salary.gt(bonus_plus)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} > {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} > {value.name})', []) if isinstance(value, Column) else (f'({self.name} > %s)', [value])
        return temp_ob

    def __gt__(self, value):
        """Implement the greater-than operator (`>`) for a column.

        This method is called when a :class:`Column` is compared with another value
        using the `>` operator. It creates a :class:`ColumnsOperation` that
        represents the SQL expression `column > value`, where `value` can be a
        literal, another :class:`Column`, or a :class:`ColumnsOperation`.

        The generated SQL expression will be parameterized appropriately to prevent
        SQL injection:
        - If `value` is a `ColumnsOperation`, the expression combines both.
        - If `value` is a `Column`, the expression uses the column name.
        - If `value` is a literal, a placeholder `%s` is used and the value is
            added to the parameters list.

        Args:
            value (Any): The right‑hand side of the comparison. Can be a literal
                (int, float, str, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            greater‑than expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: "salary" > 50000
            >>> op = employees.salary > 50000
            >>> print(op._output[0])
            '("employees"."salary" > %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Compare with another column: "salary" > "bonus"
            >>> op2 = employees.salary > employees.bonus
            >>> print(op2._output[0])
            '("employees"."salary" > "employees"."bonus")'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} > {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} > {value.name})', []) if isinstance(value, Column) else (f'({self.name} > %s)', [value])
        return temp_ob

    def lt(self, value):
        """Create a SQL 'less than' comparison (`<`) for this column.

        This method generates a SQL `<` expression comparing the column with the
        provided value. It is the explicit (non‑operator) version of `__lt__`,
        useful when the comparison operator cannot be used directly (e.g., in
        contexts where operator overloading is not supported). The result is a
        :class:`ColumnsOperation` that can be used in `WHERE` clauses or combined
        with other conditions.

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - A :class:`Column` (using the column's name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameter list).

        Args:
            value (Any): The right‑hand side of the comparison. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            less‑than expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Explicit less-than: salary < 50000
            >>> cond = employees.salary.lt(50000)
            >>> print(cond._output[0])
            '("employees"."salary" < %s)'
            >>> print(cond._output[1])
            [50000]
            >>> # Compare with another column: salary < bonus
            >>> cond2 = employees.salary.lt(employees.bonus)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} < {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} < {value.name})', []) if isinstance(value, Column) else (f'({self.name} < %s)', [value])
        return temp_ob

    def __lt__(self, value):
        """Implement the less‑than operator (`<`) for a column.

        This method is called when a :class:`Column` is compared with another value
        using the `<` operator. It creates a :class:`ColumnsOperation` that represents
        the SQL expression `column < value`, where `value` can be a literal, another
        :class:`Column`, or a :class:`ColumnsOperation`.

        The generated SQL expression will be parameterized appropriately to prevent
        SQL injection:
        - If `value` is a `ColumnsOperation`, the expression combines both.
        - If `value` is a `Column`, the expression uses the column name.
        - If `value` is a literal, a placeholder `%s` is used and the value is
            added to the parameters list.

        Args:
            value (Any): The right‑hand side of the comparison. Can be a literal
                (int, float, str, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            less‑than expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: "salary" < 50000
            >>> op = employees.salary < 50000
            >>> print(op._output[0])
            '("employees"."salary" < %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Compare with another column: "salary" < "bonus"
            >>> op2 = employees.salary < employees.bonus
            >>> print(op2._output[0])
            '("employees"."salary" < "employees"."bonus")'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} < {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} < {value.name})', []) if isinstance(value, Column) else (f'({self.name} < %s)', [value])
        return temp_ob

    def ge(self, value):
        """Create a SQL 'greater than or equal to' comparison (`>=`) for this column.

        This method is called when a :class:`Column` is compared using the `ge()`
        method (explicit comparison) or via the `>=` operator (delegated to `__ge__`).
        It creates a :class:`ColumnsOperation` that represents the SQL expression
        `column >= value`, where `value` can be a literal, another :class:`Column`,
        or a :class:`ColumnsOperation`.

        The generated SQL expression will be parameterized appropriately:
        - If `value` is a `ColumnsOperation`, the expression combines both operations.
        - If `value` is a `Column`, the expression uses the column name.
        - If `value` is a literal, a placeholder `%s` is used and the value is
        added to the parameters list.

        Args:
            value (Any): The right‑hand side of the comparison. Can be a literal
                (int, float, str, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `>=` comparison expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: "salary" >= 50000
            >>> op = employees.salary.ge(50000)
            >>> print(op._output[0])
            '("employees"."salary" >= %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Compare with another column: "salary" >= "bonus"
            >>> op2 = employees.salary.ge(employees.bonus)
            >>> print(op2._output[0])
            '("employees"."salary" >= "employees"."bonus")'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} >= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} >= {value.name})', []) if isinstance(value, Column) else (f'({self.name} >= %s)', [value])
        return temp_ob

    def __ge__(self, value):
        """Implement the greater‑than‑or‑equal comparison operator (`>=`) for a column.

        This method is called when a :class:`Column` is compared with another value
        using the `>=` operator. It creates a :class:`ColumnsOperation` that
        represents the SQL expression `column >= value`, where `value` can be a
        literal, another :class:`Column`, or a :class:`ColumnsOperation`.

        The generated SQL expression is parameterized to prevent SQL injection:
        - If `value` is a `ColumnsOperation`, the expression combines both.
        - If `value` is a `Column`, the expression uses the column name.
        - If `value` is a literal, a placeholder `%s` is used and the value is
            added to the parameters list.

        Args:
            value (Any): The right‑hand side of the comparison. Can be a literal
                (int, float, str, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            comparison expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: "salary" >= 50000
            >>> op = employees.salary >= 50000
            >>> print(op._output[0])
            '("employees"."salary" >= %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Compare with another column: "salary" >= "bonus"
            >>> op2 = employees.salary >= employees.bonus
            >>> print(op2._output[0])
            '("employees"."salary" >= "employees"."bonus")'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} >= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} >= {value.name})', []) if isinstance(value, Column) else (f'({self.name} >= %s)', [value])
        return temp_ob

    def le(self, value):
        """Create a SQL 'less than or equal to' comparison (`<=`) for this column.

        This method generates a SQL `<=` expression comparing the column with the
        provided value. It is the explicit (non-operator) version of `__le__`,
        useful when the comparison operator cannot be used directly (e.g., in
        contexts where operator overloading is not supported). The result is a
        :class:`ColumnsOperation` that can be used in `WHERE` clauses or combined
        with other conditions.

        The comparison can be made against:
            - Another :class:`ColumnsOperation` (combining both expressions).
            - A :class:`Column` (using the column's name).
            - A literal value (using a parameter placeholder `%s` and adding the
            value to the parameter list).

        Args:
            value (Any): The right‑hand side of the comparison. Can be a
                :class:`ColumnsOperation`, :class:`Column`, or a literal
                (int, float, str, etc.).

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            comparison expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Explicit less‑or‑equal: salary <= 50000
            >>> op = employees.salary.le(50000)
            >>> print(op._output[0])
            '("employees"."salary" <= %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Chaining with another condition
            >>> cond = employees.salary.le(70000) & employees.name.startswith('A')
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} <= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} <= {value.name})', []) if isinstance(value, Column) else (f'({self.name} <= %s)', [value])
        return temp_ob

    def __le__(self, value):
        """Implement the less‑than‑or‑equal comparison operator (`<=`) for a column.

        This method is called when a :class:`Column` is compared with another value
        using the `<=` operator. It creates a :class:`ColumnsOperation` that
        represents the SQL expression `column <= value`, where `value` can be a
        literal, another :class:`Column`, or a :class:`ColumnsOperation`.

        The generated SQL expression is parameterized to prevent SQL injection:
        - If `value` is a `ColumnsOperation`, the expression combines both.
        - If `value` is a `Column`, the expression uses the column name.
        - If `value` is a literal, a placeholder `%s` is used and the value is
            added to the parameters list.

        Args:
            value (Any): The right‑hand side of the comparison. Can be a literal
                (int, float, str, etc.), a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            comparison expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Generate SQL: "salary" <= 50000
            >>> op = employees.salary <= 50000
            >>> print(op._output[0])
            '("employees"."salary" <= %s)'
            >>> print(op._output[1])
            [50000]
            >>> # Compare with another column: "salary" <= "bonus"
            >>> op2 = employees.salary <= employees.bonus
            >>> print(op2._output[0])
            '("employees"."salary" <= "employees"."bonus")'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} <= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} <= {value.name})', []) if isinstance(value, Column) else (f'({self.name} <= %s)', [value])
        return temp_ob

    def __getitem__(self, key: slice):
        """Implement substring extraction using slice notation.

        This method enables Python's slicing syntax (e.g., `column[start:stop]`)
        on a :class:`Column` object. It generates a SQL `SUBSTRING` expression
        that extracts a portion of the column's string value.

        The behavior mimics Python string slicing with support for positive and
        negative indices, as well as `None` for start or stop. The generated SQL
        uses the PostgreSQL `SUBSTRING` function with `LENGTH` for negative
        indexing.

        The method is chainable: it returns a :class:`ColumnsOperation` that can
        be further combined with other operations.

        Args:
            key (slice): A slice object specifying the start and stop positions.
                - `start` (int or None): The starting position (0‑based, inclusive).
                If `None`, the extraction begins at position 1 (SQL 1‑based).
                - `stop` (int or None): The ending position (0‑based, exclusive).
                If `None`, the extraction continues to the end of the string.
                Both `start` and `stop` can be negative, indicating positions
                counted from the end of the string.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance whose `_output`
            contains the SQL `SUBSTRING` expression and associated parameters.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Extract first three characters of the name
            >>> op = employees.name[0:3]
            >>> print(op._output[0])
            'SUBSTRING("employees"."name" , %s , %s)'
            >>> print(op._output[1])
            [1, 3]  # note SQL uses 1-based indexing
            >>>
            >>> # Extract from position 2 to the end
            >>> op2 = employees.name[1:]
            >>> print(op2._output[0])
            'SUBSTRING("employees"."name" , %s , LENGTH("employees"."name"))'
            >>> print(op2._output[1])
            [2]
            >>>
            >>> # Negative indices (last 3 characters)
            >>> op3 = employees.name[-3:]
            >>> print(op3._output[0])
            'SUBSTRING("employees"."name" , LENGTH("employees"."name") - %s , LENGTH("employees"."name"))'
            >>> print(op3._output[1])
            [2]  # LENGTH - 2 gives the start position for last 3 chars
        """
        temp_ob = ColumnsOperation(self)
        if key.start == None and key.stop ==  None:
            temp_ob._output = (f'SUBSTRING({temp_ob.col_obj.name} , 1 , LENGTH({temp_ob.col_obj.name}) + 1)', [])   #
        elif key.start == None and key.stop < 0:
            temp_ob._output = (f'SUBSTRING({temp_ob.col_obj.name} , 1 , LENGTH({temp_ob.col_obj.name}) - %s)', [abs(key.stop)])  #
        elif key.start == None and key.stop >= 0:
            temp_ob._output = (f'SUBSTRING({temp_ob.col_obj.name} , 1 , %s)', [key.stop])  #  
        elif key.start >= 0 and key.stop ==  None:
            temp_ob._output = (f'SUBSTRING({temp_ob.col_obj.name} , %s , LENGTH({temp_ob.col_obj.name}))', [key.start + 1])  #   
        elif key.start < 0 and key.stop == None:
            temp_ob._output = (f'SUBSTRING({temp_ob.col_obj.name} , LENGTH({temp_ob.col_obj.name}) - %s , LENGTH({temp_ob.col_obj.name}))', [abs(key.start) - 1])  #
        elif key.start >= 0 and key.stop < 0:
            temp_ob._output = (f'SUBSTRING({temp_ob.col_obj.name} , %s , LENGTH({temp_ob.col_obj.name}) - %s)', [key.start + 1, abs(key.stop - key.start)])  #  
        elif key.start >= 0 and key.stop > 0:
            temp_ob._output = (f'SUBSTRING({temp_ob.col_obj.name} , %s , %s)', [key.start + 1, key.stop - key.start])  #
        elif key.start < 0 and key.stop < 0:
            temp_ob._output = (f'SUBSTRING({temp_ob.col_obj.name} , LENGTH({temp_ob.col_obj.name}) - %s , %s)', [abs(key.start) - 1, key.stop - key.start])  #
        elif key.start < 0 and key.stop > 0:
            temp_ob._output = (f'SUBSTRING({temp_ob.col_obj.name} , LENGTH({temp_ob.col_obj.name}) - %s ,  %s - (LENGTH({temp_ob.col_obj.name}) - %s))', [abs(key.start) - 1, key.stop, abs(key.start)])
        return temp_ob

    def strip(self, chars: str = ' '):
        """just like python strip(), create a SQL `TRIM` expression to strip leading and trailing characters.

        This method generates a PostgreSQL `TRIM` function call that removes the
        specified characters (default space) from both ends of the column's value.
        It returns a :class:`ColumnsOperation` that can be used in queries or
        chained with other operations.

        Args:
            chars (str, optional): The characters to remove. Defaults to a space.
                The characters are treated as a set; any occurrence at the beginning
                or end of the string is removed.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `TRIM` expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Trim spaces from the 'name' column
            >>> op = employees.name.strip()
            >>> print(op._output[0])
            "TRIM(BOTH ' ' FROM \"employees\".\"name\")"
            >>> # Trim underscores from both ends
            >>> op2 = employees.code.strip('_')
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"TRIM(BOTH '{chars}' FROM {temp_ob._output[0]})", temp_ob._output[1]) if temp_ob._output else (f"TRIM(BOTH '{chars}' FROM {temp_ob.col_obj.name})", [])
        return temp_ob

    def lstrip(self, chars: str = ' '):
        """Just like python lstrip(), remove leading characters from a string column or expression.

        This method generates a SQL `TRIM(LEADING ... FROM ...)` expression that
        strips the specified characters from the start of the column value or
        existing operation. If no `chars` are provided, leading spaces are removed.

        The operation is chainable and returns a :class:`ColumnsOperation` that
        can be used in queries, updates, or combined with other expressions.

        Args:
            chars (str, optional): The characters to remove from the left side.
                Defaults to a single space.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `TRIM(LEADING ...)` expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Remove leading spaces from the 'name' column
            >>> trimmed = employees.name.lstrip()
            >>> # Generate SQL: TRIM(LEADING ' ' FROM "employees"."name")
            >>> # Remove leading dashes from the 'code' column
            >>> trimmed2 = employees.code.lstrip('-')
            >>> # Chain with other operations
            >>> cond = employees.name.lstrip().upper().contains('SMITH')
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"TRIM(LEADING '{chars}' FROM {temp_ob._output[0]})", temp_ob._output[1]) if temp_ob._output else (f"TRIM(LEADING '{chars}' FROM {temp_ob.col_obj.name})", [])
        return temp_ob

    def rstrip(self, chars: str = ' '):
        """Just like python rstrip(), generate a SQL `TRIM` expression that removes trailing characters from the column.

        This method creates a :class:`ColumnsOperation` that, when used in a query,
        strips the specified characters from the end (right side) of the column's
        string value. The default is to strip spaces. The result is a SQL
        `TRIM(TRAILING ... FROM ...)` expression.

        Args:
            chars (str, optional): The characters to remove from the right end of
                the string. Defaults to a single space (`' '`).

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `TRIM` expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Strip trailing spaces from the name column
            >>> op = employees.name.rstrip()
            >>> print(op._output[0])
            "TRIM(TRAILING ' ' FROM \"employees\".\"name\")"
            >>> # Strip trailing 'x' characters
            >>> op2 = employees.name.rstrip('x')
            >>> print(op2._output[0])
            "TRIM(TRAILING 'x' FROM \"employees\".\"name\")"
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"TRIM(TRAILING '{chars}' FROM {temp_ob._output[0]})", temp_ob._output[1]) if temp_ob._output else (f"TRIM(TRAILING '{chars}' FROM {temp_ob.col_obj.name})", [])
        return temp_ob

    def add_end(self, content):
        """Concatenate content to the end of the column's string value.

        This method creates a :class:`ColumnsOperation` that represents the SQL
        expression `column || content`, which appends the given content to the
        end of the column's string value. The content can be a literal, another
        :class:`Column`, or a :class:`ColumnsOperation` (e.g., an expression).

        The result is a :class:`ColumnsOperation` instance that can be used in
        queries, updates, or further chained operations.

        Args:
            content (Any): The value or expression to append. Can be:
                - A :class:`ColumnsOperation` (e.g., an existing expression).
                - A :class:`Column` (another column).
                - A literal (str, int, etc.) that will be converted to a string
                parameter.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` representing the
            concatenation expression, ready for chaining.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Append " (Inc.)" to the company name
            >>> op = employees.company.add_end(" (Inc.)")
            >>> print(op._output[0])
            '("employees"."company" || %s)'
            >>> print(op._output[1])
            [' (Inc.)']
            >>>
            >>> # Append another column (e.g., suffix column)
            >>> op2 = employees.first_name.add_end(employees.last_name)
            >>> print(op2._output[0])
            '("employees"."first_name" || "employees"."last_name")'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} || {content._output[0]})', [content._output[1]]) if isinstance(content, ColumnsOperation) else (f'({self.name} || {content.name})', []) if isinstance(content, Column) else (f'({self.name} || %s)', [content])
        return temp_ob

    def add_first(self, content):
        """Generate a SQL expression that prepends content to the column's value.

        This method creates a :class:`ColumnsOperation` that represents the SQL
        concatenation of `content` before the column's current value. For string
        columns, this is equivalent to `content || column` in PostgreSQL. The
        result can be used in SELECT, UPDATE, or WHERE clauses.

        The `content` parameter can be:
        - Another :class:`ColumnsOperation` (e.g., a concatenated expression).
        - A :class:`Column` from the same or another table.
        - A literal string value (which will be parameterized).

        Args:
            content (Any): The value to prepend. Can be a :class:`ColumnsOperation`,
                :class:`Column`, or a literal string.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            concatenation expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Prepend 'EMP-' to the employee code
            >>> op = employees.code.add_first('EMP-')
            >>> print(op._output[0])
            '(%s || "employees"."code")'
            >>> print(op._output[1])
            ['EMP-']
            >>> # Prepend the value of another column
            >>> op2 = employees.code.add_first(employees.department_code)
            >>> print(op2._output[0])
            '("employees"."department_code" || "employees"."code")'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({content._output[0]} || {self.name})', [content._output[1]]) if isinstance(content, ColumnsOperation) else (f'({content.name} || {self.name})', []) if isinstance(content, Column) else (f'(%s || {self.name})', [content])
        return temp_ob
    
    def lower(self):
        """Just like python lower(), generate a SQL `LOWER` expression to convert the column value to lowercase.

        This method creates a :class:`ColumnsOperation` that, when used in a query,
        applies the PostgreSQL `LOWER` function to the column's string value,
        converting all characters to lowercase. The result is a SQL expression
        that can be used in `SELECT`, `WHERE`, or other clauses.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `LOWER` expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Compare names case-insensitively
            >>> cond = employees.name.lower() == 'john'
            >>> print(cond._output[0])
            '(LOWER("employees"."name") = %s)'
            >>> print(cond._output[1])
            ['john']
            >>> # Use in a query
            >>> results = employees.get_row([employees.name], where=cond)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'LOWER({temp_ob._output[0]})', temp_ob._output[1]) if temp_ob._output else (f'LOWER({temp_ob.col_obj.name})', [])
        return temp_ob

    def upper(self):
        """Just like python upper(), generate a SQL `UPPER` expression that converts the column value to uppercase.

        This method creates a :class:`ColumnsOperation` that, when used in a query,
        applies the SQL `UPPER()` function to the column, transforming all characters
        to uppercase. The result can be used in `SELECT`, `WHERE`, or other clauses.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `UPPER` expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Convert names to uppercase for case‑insensitive comparison
            >>> op = employees.name.upper()
            >>> print(op._output[0])
            'UPPER("employees"."name")'
            >>> # Use in a WHERE clause
            >>> cond = employees.name.upper() == 'JOHN DOE'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'UPPER({temp_ob._output[0]})', temp_ob._output[1]) if temp_ob._output else (f'UPPER({temp_ob.col_obj.name})', [])
        return temp_ob

    def replace(self, old, new):
        """Just like python replace(), generate a SQL `REPLACE` expression to substitute substrings in the column.

        This method creates a :class:`ColumnsOperation` that, when used in a query,
        replaces all occurrences of a specified substring (`old`) with another
        substring (`new`) in the column's string value. The result is a SQL
        `REPLACE(column, old, new)` expression with parameterized placeholders to
        prevent SQL injection.

        Args:
            old (str): The substring to be replaced.
            new (str): The substring to replace with.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `REPLACE` expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Replace 'old' with 'new' in the name column
            >>> op = employees.name.replace('old', 'new')
            >>> print(op._output[0])
            'REPLACE("employees"."name" , %s , %s)'
            >>> print(op._output[1])
            ['old', 'new']
            >>> # Chain with other string functions
            >>> op2 = employees.name.upper().replace('A', 'X')
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'REPLACE({temp_ob._output[0]} , %s , %s)', temp_ob._output[1] + [old, new]) if temp_ob._output else (f'REPLACE({temp_ob.col_obj.name} , %s , %s)', [old, new])
        return temp_ob

    def like(self, value):
        """Generate a SQL `LIKE` pattern matching expression for this column.

        This method creates a :class:`ColumnsOperation` that represents a SQL `LIKE`
        comparison between the column and the provided pattern. The pattern can be
        a literal string, another :class:`Column`, or a :class:`ColumnsOperation`
        (e.g., for concatenated patterns). The result can be used directly in
        `WHERE` clauses or combined with other conditions using logical operators.

        The generated SQL expression is parameterized to prevent injection:
        - If `value` is a `ColumnsOperation`, the expression uses the operation's
            SQL and parameter list.
        - If `value` is a `Column`, the expression uses the column name.
        - If `value` is a literal string, a placeholder `%s` is used and the
            string is added to the parameters list.

        Args:
            value (Any): The pattern to match against. Can be a literal string,
                a :class:`Column`, or a :class:`ColumnsOperation`. For literal
                strings, use `%` as a wildcard (e.g., `'A%'` for values starting
                with 'A').

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `LIKE` expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Find employees whose names start with 'A'
            >>> cond = employees.name.like('A%')
            >>> # Combine with another condition
            >>> final_cond = cond & (employees.salary > 50000)
            >>> # Use a ColumnsOperation for a more complex pattern
            >>> pattern = employees.name.upper() + '%'
            >>> cond2 = employees.name.like(pattern)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"{self.name} like {value._output[0]}", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self.name} like {value.name}', temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f'{self.name} like %s', (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def startswith(self, value):
        """Just like python startswith(), generate a SQL `LIKE` expression that checks if the column starts with a given prefix.

        This method creates a :class:`ColumnsOperation` representing a condition
        that is true when the column's value begins with the specified prefix.
        The generated SQL uses the `LIKE` operator with the prefix followed by a
        wildcard (`%`), e.g., `column LIKE 'prefix%'`. The prefix can be provided
        as a literal string, another :class:`Column`, or a :class:`ColumnsOperation`
        (e.g., for a computed prefix).

        The result is a parameterized SQL expression to prevent injection. When used
        in a query, this condition can be combined with other conditions using
        logical operators (`&`, `|`).

        Args:
            value (Any): The prefix to match at the start of the column's value.
                Can be a literal string, a :class:`Column`, or a
                :class:`ColumnsOperation`. If a literal is provided, it will be
                treated as a string and escaped appropriately.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `LIKE` expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Find employees whose names start with 'A'
            >>> cond = employees.name.startswith('A')
            >>> print(cond._output[0])
            '"employees"."name" like %s || \'%%\''
            >>> print(cond._output[1])
            ['A']
            >>> # Using another column as prefix
            >>> cond2 = employees.name.startswith(employees.prefix_column)
            >>> # Using a ColumnsOperation (e.g., upper-cased prefix)
            >>> prefix_op = employees.name.upper()
            >>> cond3 = employees.name.startswith(prefix_op)
            >>> # Combine with other conditions
            >>> final_cond = cond & (employees.salary > 50000)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"{self.name} like {value._output[0]} || '%%'", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self.name} like {value.name} || '%%'", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"{self.name} like %s || '%%'", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob
    
    def endswith(self, value):
        """Generate a SQL `LIKE` expression that matches strings ending with a suffix.

        This method creates a :class:`ColumnsOperation` that, when used in a query,
        filters rows where the column's string value ends with the specified suffix.
        The generated SQL uses `LIKE '%%' || value` (with the wildcard before the
        value) to perform the pattern match.

        The suffix can be provided as:
            - A literal string (e.g., `'son'`).
            - Another :class:`Column` (e.g., `employees.suffix_column`).
            - A :class:`ColumnsOperation` (e.g., for computed suffixes).

        The result is parameterized to prevent SQL injection; literal values are
        added to the parameters list and bound safely.

        Args:
            value (Any): The suffix to match at the end of the column's string.
                Can be a literal string, a :class:`Column`, or a
                :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `LIKE` expression, ready for chaining or use in `WHERE` clauses.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Find employees whose last names end with 'son'
            >>> cond = employees.last_name.endswith('son')
            >>> # Use in a query
            >>> results = employees.get_row([employees.last_name], where=cond)
            >>>
            >>> # Using a Column as the suffix
            >>> suffix_col = Table(driver, "suffixes").suffix
            >>> cond2 = employees.last_name.endswith(suffix_col)
            >>>
            >>> # Using a ColumnsOperation (e.g., uppercase suffix)
            >>> op = employees.suffix_column.upper()
            >>> cond3 = employees.last_name.endswith(op)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"{self.name} like '%%' || {value._output[0]}", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self.name} like '%%' || {value.name}", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"{self.name} like '%%' || %s", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def contains(self, value):
        """Generate a SQL `LIKE` expression to check if the column contains a substring.

        This method creates a :class:`ColumnsOperation` that represents a SQL
        `LIKE` condition with wildcards on both sides: `column LIKE '%' || value || '%'`.
        The result can be used in `WHERE` clauses to filter rows where the column's
        string value contains the specified substring.

        The behavior depends on the type of `value`:
        - If `value` is a :class:`ColumnsOperation`, its SQL expression and
        parameters are used, and the `LIKE` pattern becomes `'%' || expr || '%'`.
        - If `value` is a :class:`Column`, its name is used directly.
        - If `value` is a literal string, a parameter placeholder `%s` is used,
        and the value is added to the parameter list with `%` wildcards appended.

        Args:
            value (Any): The substring to search for. Can be a literal string,
                a :class:`Column`, or a :class:`ColumnsOperation`.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `LIKE` expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Find employees whose name contains 'Smith'
            >>> cond = employees.name.contains('Smith')
            >>> # Equivalent SQL: "name" LIKE '%' || %s || '%'
            >>> # With parameter: 'Smith'
            >>>
            >>> # Using a ColumnsOperation (e.g., concatenated columns)
            >>> full_name = employees.first_name + ' ' + employees.last_name
            >>> cond2 = full_name.contains('John')
            >>> # Generated SQL: (("first_name" || ' ') || "last_name") LIKE '%' || %s || '%'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"{self.name} like '%%' || {value._output[0]} || '%%'", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self.name} like '%%' || {value.name} || '%%'", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"{self.name} like '%%' || %s || '%%'", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def rename(self, column: 'Column', new_name: str) -> None:
        """Rename an existing column in the table.

        This method executes an `ALTER TABLE ... RENAME COLUMN` SQL statement to
        change the name of the specified column. After the database operation, it
        updates the corresponding :class:`Table` object by removing the attribute
        with the old column name and adding a new attribute with the new name,
        preserving the column's datatype.

        Args:
            column (Column): The :class:`Column` object representing the column to
                rename. This is typically a reference to a column attribute of the
                table.
            new_name (str): The new name for the column. This will be quoted
                appropriately.

        Returns:
            None: This method performs an in-place modification and does not
            return a value.

        Raises:
            Exception: Propagates any database errors from the `ALTER TABLE`
                statement, such as permission issues or if the column does not
                exist.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Assume the table has a column named 'last_name'
            >>> employees.last_name.rename(employees.last_name, "surname")
            >>> # After this, the column is renamed to 'surname', and the
            >>> # employees object now has an attribute 'surname'.
            >>> print(employees.surname)  # Works
        """
        query = f'ALTER TABLE {self.table_obj.name_} RENAME COLUMN {column.first_name} TO "{new_name}";'
        self.table_obj._exc(query)
        self.table_obj.__delattr__(column.first_name.strip('"'))
        self.table_obj.__setattr__(new_name, Column(self.table_obj, new_name, column.datatype))

    def delete_column(self, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool) -> None:
        """Permanently remove this column from its table.

        This method executes a SQL `ALTER TABLE ... DROP COLUMN` statement to
        delete the column from the database schema. It also removes the column
        attribute from the parent :class:`Table` object to keep the ORM in sync.
        To prevent accidental data loss, three separate confirmation flags must
        all be `True`.

        Args:
            are_you_sure (bool): First confirmation flag.
            are_you_really_sure (bool): Second confirmation flag.
            for_sure (bool): Third confirmation flag.

        Returns:
            None: This method does not return a value.

        Raises:
            Exception: Propagates any database errors raised during the execution
                of the DROP COLUMN statement (e.g., permission issues or if the
                column does not exist).

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Assume there is a column 'temp_column'
            >>> # Permanently delete it from the table
            >>> employees.temp_column.delete_column(True, True, True)
            >>> # The attribute is no longer available on the table object
        """
        if are_you_sure and are_you_really_sure and for_sure:
            query = f'ALTER TABLE {self.table_obj.name_} DROP COLUMN {self.first_name};'
            self.table_obj._exc(query)
            self.table_obj.__delattr__(self.first_name[1:-1])

    def In(self, value):
        """Generate a SQL `IN` clause or equality condition for this column.

        This method creates a :class:`ColumnsOperation` that represents a SQL `IN`
        expression, checking whether the column's value matches any value in a set
        or subquery. The behavior depends on the type of `value`:

        - If `value` is a :class:`ColumnsOperation`, it generates an `IN` clause with
        a subquery (e.g., `column IN (subquery)`).
        - If `value` is a list or tuple, it generates `IN (?, ?, ...)` with one
        placeholder per item, and adds all items to the parameter list.
        - If `value` is a scalar (single value), it generates an equality condition
        `= ?` instead of `IN`, which is equivalent and more efficient.

        The result is a :class:`ColumnsOperation` that can be used directly in
        `WHERE` clauses or combined with other conditions using logical operators.

        Args:
            value (Any): The set of values or subquery to check against. Can be a
                :class:`ColumnsOperation` (subquery), a list or tuple of values,
                or a scalar (int, float, str, etc.).

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing the
            `IN` or equality expression, ready for chaining or use in queries.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> departments = driver.departments
            >>>
            >>> # Using a list of values
            >>> cond = employees.department.In(['Engineering', 'Sales', 'Marketing'])
            >>> print(cond._output[0])
            '("employees"."department" IN (%s,%s,%s))'
            >>> print(cond._output[1])
            ['Engineering', 'Sales', 'Marketing']
            >>>
            >>> # Using a subquery (ColumnsOperation)
            >>> # Assuming we have a column from another table
            >>> subquery = departments.id  # Column object, which will be wrapped
            >>> cond2 = employees.dept_id.In(subquery)
            >>> # This generates: ("employees"."dept_id" IN ("departments"."id"))
            >>>
            >>> # Scalar value produces equality
            >>> cond3 = employees.id.In(100)
            >>> print(cond3._output[0])
            '("employees"."id" = %s)'
            >>> print(cond3._output[1])
            [100]
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"{self.name} IN ({value._output[0]})",value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self.name} IN ({','.join(['%s'] * len(value))})",list(value)) if isinstance(value, (list, tuple)) else (f"{self.name} = %s",[value])
        return temp_ob


class BatchOperation:
    """A builder for batch executing multiple SQL operations in a single transaction.

    This class provides a fluent interface for accumulating INSERT and UPDATE
    statements and then executing them together as a single atomic transaction.
    It is useful for bulk data modifications where you want to ensure that all
    operations succeed or fail together, and to reduce network round‑trips by
    sending multiple statements at once.

    Operations are added via the :meth:`insert` and :meth:`update` methods, each
    of which returns the instance itself to allow method chaining. The actual
    execution is triggered by calling :meth:`run`.

    The internal script stores each operation as a list of `[sql_string, params_list]`
    (or `[sql_string]` for no parameters). When `run()` is called, the underlying
    :class:`Table` executes the script using its `_excs` method, which commits
    all changes in one transaction.

    Attributes:
        script (list): A list where each element is either `[sql_string]` or
            `[sql_string, params_list]`, representing the operations to be executed.
        table_obj (Table): The table object that this batch is associated with;
            used to execute the script.

    Example:
        >>> employees = driver.employees
        >>> batch = BatchOperation(employees)
        >>> batch.insert({employees.name: "Alice", employees.salary: 60000})
        >>> batch.insert({employees.name: "Bob", employees.salary: 70000})
        >>> batch.update(
        ...     {employees.salary: employees.salary * 1.05},
        ...     employees.department == "Engineering"
        ... )
        >>> batch.run()
        # All three operations execute in a single transaction.

    Note:
        After `run()`, the script is not cleared automatically. To reuse the
        batch object, you would need to manually clear `script`, but it is
        recommended to create a new `BatchOperation` instance for each batch.
    """
    def __init__(self, table_object: Table):
        """Initialize a new batch operation builder for a specific table.

        A `BatchOperation` instance allows you to collect multiple SQL statements
        (INSERT and UPDATE) and execute them together in a single transaction,
        which improves performance for bulk operations. This constructor is
        typically not called directly; instead, use :meth:`Table.batch` to obtain
        a batch builder for a table.

        Args:
            table_object (Table): The :class:`Table` object on which the batched
                operations will be performed. All operations added to this batch
                will target this table unless overridden in individual operation calls.

        Returns:
            None: This method initializes the instance and does not return a value.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> # Using Table.batch() is the recommended way:
            >>> batch = employees.batch()
            >>> batch.insert({employees.name: "Alice", employees.salary: 60000})
            >>> batch.insert({employees.name: "Bob", employees.salary: 65000})
            >>> batch.update({employees.salary: employees.salary * 1.05}, employees.department == "Engineering")
            >>> batch.run()
            # All statements are executed in a single transaction.
        """
        self.script = []
        self.table_obj = table_object

    def update(self, update: dict[Column, Any], where: ColumnsOperation, table: Table = None) -> 'BatchOperation':
        """Add an UPDATE statement to the batch operation script.

        This method appends an UPDATE SQL statement to the batch script, which will
        be executed when :meth:`run` is called. The update modifies rows in the
        specified table (or the batch's table if no `table` is provided) that match
        the given `where` condition. The method handles various types of values in
        the `update` dictionary, including literals, :class:`Column` objects (for
        column-to-column assignments), and :class:`ColumnsOperation` objects (for
        computed expressions). All literal values are parameterized to prevent SQL
        injection.

        The method is chainable, returning the `BatchOperation` instance.

        Args:
            update (dict[Column, Any]): A dictionary mapping :class:`Column` objects
                to new values. Values can be:
                - Literals (int, str, float, etc.): will be parameterized as `%s`.
                - :class:`Column` objects: for setting one column to another's value.
                - :class:`ColumnsOperation` objects: for computed expressions
                (e.g., `employees.salary + 1000`).
            where (ColumnsOperation): A :class:`ColumnsOperation` representing the
                condition that determines which rows to update.
            table (Table, optional): An optional :class:`Table` object specifying
                which table to update. If `None`, the batch's original table is used.

        Returns:
            BatchOperation: The current instance, allowing method chaining.

        Raises:
            Exception: This method does not immediately raise exceptions, but errors
                may be raised when :meth:`run` is called if the SQL is malformed or
                parameters are invalid.

        Example:
            Simple batch update with literal values:

            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> batch = employees.batch()
            >>> # Update all employees in 'Engineering' to have salary 60000
            >>> batch.update({employees.salary: 60000}, employees.department == 'Engineering')
            >>> batch.run()

        Example:
            Complex update using ColumnsOperation for computed values and
            a compound condition with a different table:

            >>> from ormophine.Postgresql import ColumnsOperation
            >>> # Increase salary by 10% for managers with >5 years experience,
            >>> # and update the title.
            >>> batch = employees.batch()
            >>> batch.update(
            ...     {
            ...         employees.salary: employees.salary * 1.10,
            ...         employees.title: employees.title + ' (Senior)'
            ...     },
            ...     (employees.title == 'Manager') & (employees.years > 5),
            ...     table=employees  # table parameter is optional
            ... )
            >>> batch.run()
        """
        temp_list= []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        self.script.append([f'UPDATE {table.name_ if table else self.table_obj.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=%s' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1]])
        return self

    def insert(self, insert: dict[Column, Any], table: Table = None) -> 'BatchOperation':
        """Add an INSERT operation to the batch script.

        This method appends an INSERT statement to the internal batch script list.
        The statement will insert a new row with the given column-value pairs into
        the specified table (or the batch's default table if none is provided).
        When :meth:`run` is called, all batch operations are executed in order
        within a single transaction.

        Args:
            insert (dict[Column, Any]): A dictionary mapping :class:`Column` objects
                to the values to insert. The values can be Python literals (e.g.,
                `str`, `int`, `float`, etc.) that will be passed as parameters to
                the query.
            table (Table, optional): The table to insert into. If not provided,
                the batch's default table (the one used when creating the
                `BatchOperation` instance) will be used. Defaults to `None`.

        Returns:
            BatchOperation: The current instance, allowing method chaining.

        Example:
            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> batch = employees.batch()
            >>> # Insert a single employee
            >>> batch.insert({employees.name: "Alice", employees.salary: 60000})
            >>> # Insert another employee into a different table
            >>> departments = driver.departments
            >>> batch.insert({departments.name: "Engineering"}, table=departments)
            >>> # Execute all inserts
            >>> batch.run()
        """
        self.script.append([f'INSERT INTO {table.name_ if table else self.table_obj.name_} ({', '.join(i.first_name for i in list(insert.keys()))}) VALUES ({', '.join(f'%s' for k in insert)})' , [v for v in list(insert.values())]])
        return self

    def delete_row(self, where: ColumnsOperation, table: Table = None) -> 'BatchOperation':
        """Add a DELETE statement to the batch operation script.

        This method appends a DELETE SQL statement to the batch script, which will
        be executed when :meth:`run` is called. The deletion removes rows from the
        specified table (or the batch's default table if no `table` is provided)
        that satisfy the given `where` condition. Parameter values from the
        condition are safely parameterized to prevent SQL injection.

        The method is chainable, returning the `BatchOperation` instance itself.

        Args:
            where (ColumnsOperation): A :class:`ColumnsOperation` representing the
                condition that selects which rows to delete.
            table (Table, optional): An optional :class:`Table` object specifying
                from which table to delete. If `None`, the batch's original table
                is used. Defaults to `None`.

        Returns:
            BatchOperation: The current instance, allowing method chaining.

        Raises:
            Exception: This method does not immediately raise exceptions, but errors
                may be raised when :meth:`run` is called if the SQL is malformed or
                parameters are invalid.

        Example:
            Simple batch deletion of all employees in a specific department:

            >>> from ormophine.Postgresql import Driver, Table
            >>> driver = Driver(...)
            >>> employees = driver.employees
            >>> batch = employees.batch()
            >>> batch.delete_row(employees.department == 'Temp')
            >>> batch.run()

        Example:
            Deleting from a different table with a complex condition:

            >>> departments = driver.departments
            >>> batch = employees.batch()
            >>> batch.delete_row(
            ...     (departments.budget < 10000) & (departments.name != 'Core'),
            ...     table=departments
            ... )
            >>> batch.insert(...)  # can chain with other operations
            >>> batch.run()
        """
        self.script.append([f'DELETE FROM {table.name_ if table else self.table_obj.name_} WHERE {where._output[0]};', where._output[1]])
        return self

    def run(self):
        """Execute all batched operations as a single transaction.

        This method sends all accumulated SQL statements (from previous `update()` and
        `insert()` calls) to the database for execution. The operations are performed
        in the order they were added, and the entire batch is executed as a single
        transaction: if any statement fails, all changes are rolled back.

        After execution, the internal script list is not automatically cleared, so
        subsequent calls to `run()` would re‑execute the same statements. Typically,
        a new :class:`BatchOperation` instance should be created for each batch.

        Returns:
            None: This method does not return a value.

        Raises:
            Exception: Propagates any database errors (OperationalError,
                ProgrammingError, etc.) raised during execution of the batch.
                If an error occurs, the transaction is rolled back.

        Example:
            >>> employees = driver.employees
            >>> batch = employees.batch()
            >>> batch.insert({employees.name: "Alice", employees.salary: 60000})
            >>> batch.update({employees.salary: 55000}, employees.department == "Marketing")
            >>> batch.run()
            # Both operations are executed in a single transaction.

        Note:
            The `BatchOperation` instance retains the script after execution. To
            avoid re‑executing the same operations, create a new batch instance
            for each set of operations.
        """
        self.table_obj._excs(self.script)

