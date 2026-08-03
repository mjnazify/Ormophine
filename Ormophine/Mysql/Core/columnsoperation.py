from __future__ import annotations

class ColumnsOperation:
    """
    Builds SQL expressions for column operations, enabling chainable arithmetic, string manipulation, comparisons, and logical conditions.

    This class is the core of the ORM's expression system. It is not typically
    instantiated directly by user code; instead, instances are returned by
    :class:`Column` objects when operators (``+``, ``-``, ``*``, ``/``, etc.)
    or methods (``.eq()``, ``.like()``, ``.upper()``, etc.) are applied to them.

    The class stores the generated SQL fragment and its associated parameter
    list in the internal ``_output`` attribute, which is a tuple of the form
    ``(sql_fragment, parameters)``. All methods that modify the expression
    update this tuple and return ``self``, allowing for fluent chaining.

    The SQL generation is context‑aware: for numeric columns, arithmetic
    operators produce standard SQL arithmetic (e.g., ``+``, ``-``, ``*``),
    while for string columns, the same operators produce string concatenation
    (``||``) or use appropriate functions like ``SUBSTRING`` and ``TRIM``.

    The class provides:
        - Arithmetic operators: ``+``, ``-``, ``*``, ``/``, ``%``, ``**`` (POW)
        - Comparison methods: ``.eq()``, ``.ne()``, ``.gt()``, ``.lt()``,
          ``.ge()``, ``.le()`` (and their dunder equivalents)
        - String methods: ``.like()``, ``.startswith()``, ``.endswith()``,
          ``.contains()``, ``.upper()``, ``.lower()``, ``.strip()``,
          ``.lstrip()``, ``.rstrip()``, ``.replace()``, ``.add_end()``,
          ``.add_first()``, and slice indexing via ``__getitem__``
        - Logical operators: ``&`` (AND), ``|`` (OR)
        - Set membership: ``.In()``

    Attributes:
        _output (tuple): A two‑element tuple ``(sql_fragment, parameters)``.
            The SQL fragment is a string with optional placeholder markers
            (``%s``) for parameters; the parameters list contains all values
            that will be substituted. Initially, this attribute is set to an
            empty string, but after any operation it becomes a tuple.
        col_obj (Column): The :class:`Column` object that this operation is
            associated with. Used to determine the column's datatype (string
            vs. numeric) when choosing the correct SQL operator.

    Example:
        Chaining operations to build a complex condition::

            from ormophine.Mysql import Table

            # Assume `users` is a Table instance with columns: id, name, age
            condition = (users.age > 18) & users.name.startswith('A')
            # condition._output[0] -> '((users.age > %s) AND (users.name like %s || '%%'))'
            # condition._output[1] -> [18, 'A']

            # Using string manipulation
            full_name = users.first_name.add_end(' ').add_end(users.last_name)
            # full_name._output[0] -> '((users.first_name || %s) || users.last_name)'
            # full_name._output[1] -> [' ']

    Note:
        All methods that modify the expression return the instance itself,
        enabling method chaining. The actual execution of the SQL is handled
        by :class:`Table` methods such as :meth:`~Table.get_row` or
        :meth:`~Table.update`, which accept a :class:`ColumnsOperation` as
        the ``where`` parameter.
    """
    def __init__(self, col_obj):
        """
        Initialize a new ColumnsOperation instance.

        This class represents a chainable operation on a column (or a combination
        of columns) that produces an SQL expression and its associated parameters.
        It is used internally by the :class:`Column` class to build complex
        expressions for queries, updates, and conditions. The :attr:`_output`
        attribute stores a tuple ``(sql_expression, param_list)`` that accumulates
        as operations are applied.

        Args:
            col_obj (Column): The :class:`Column` object that this operation is
                associated with. It provides the column name, table reference,
                and datatype, which influence how operations (e.g., addition,
                concatenation) are rendered in SQL.

        Returns:
            None

        Example:
            This class is typically used indirectly via :class:`Column` operators::

                # Assuming `users.age` is a Column
                expr = users.age + 5
                # `expr` is a ColumnsOperation instance

                # Applying further chained operations
                expr = (users.first_name + ' ' + users.last_name).upper()

            In each case, the internal SQL expression and parameters are built up
            to be used in a query or condition.
        """
        self._output = '' # To apply operations in a chained manner
        self.col_obj = col_obj

    def __add__(self, other):
        """
        Add two values or expressions in a SQL context.

        This operator generates a SQL expression for addition (or string
        concatenation) between the current column/expression and another value.
        The operation performed depends on the column's datatype:

        - If the column datatype is ``str``, the SQL ``||`` concatenation
        operator is used (with appropriate MySQL ``PIPES_AS_CONCAT`` mode
        enabled).
        - Otherwise, the SQL ``+`` operator is used for numeric addition.

        The method supports chaining by mutating the internal ``_output`` tuple
        and returning ``self``.

        Args:
            other (Any): The value, column, or expression to add. Can be an
                instance of :class:`ColumnsOperation`, :class:`Column`, or a
                literal (``int``, ``float``, ``str``). For non-literal types,
                the appropriate SQL representation is generated.

        Returns:
            ColumnsOperation: The current instance with updated internal state,
                allowing method chaining.

        Raises:
            None: This method does not raise exceptions directly; however,
                underlying database errors may occur when the resulting SQL is
                executed.

        Example:
            Assuming a :class:`Column` named ``users.age`` with numeric datatype
            and ``users.first_name`` with string datatype::

                # Numeric addition
                expr = users.age + 5
                # Generates SQL: (`users`.`age` + 5)

                # String concatenation
                expr = users.first_name + ' ' + users.last_name
                # Generates SQL: (`users`.`first_name` || ' ' || `users`.`last_name`)

            The resulting :class:`ColumnsOperation` can be used in WHERE clauses,
            UPDATE assignments, or SELECT expressions.
        """
        self._output = (f'({self._output[0]} {'||' if self.col_obj.datatype == str else '+'} {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} {'||' if self.col_obj.datatype == str else '+'} {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} + %s)', self._output[1]+[other]) if isinstance(other, int) or isinstance(other , float) else (f'({self._output[0]} || %s)', self._output[1]+[other if isinstance(other, str) else str(other)])
        return self

    def __radd__(self, other):
        """
        Implement right-side addition (`other + self`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance appears
        on the right side of a ``+`` operator. It generates a SQL expression
        string and accumulates parameter values. The behavior depends on the
        type of ``other``:

        - If ``other`` is a :class:`ColumnsOperation`, both sides are combined
        using ``||`` (for string columns) or ``+`` (for numeric columns).
        - If ``other`` is a :class:`Column`, its name is used directly, and the
        operator is chosen based on the column's datatype (string vs. numeric).
        - If ``other`` is an ``int`` or ``float``, a placeholder ``%s`` is used
        for the value, and the parameter is collected.
        - If ``other`` is a string, it is treated as a string literal, using
        the ``||`` operator (string concatenation) and a placeholder.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            other (ColumnsOperation, Column, int, float, str): The left operand
                to be added to this operation. Its type determines how the SQL
                expression is constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the new operation. This enables method chaining.

        Example:
            Assuming a string column ``users.full_name`` and a numeric column
            ``users.age``::

                # Right addition with a string literal
                op = users.full_name + ' ' + users.last_name
                # The __radd__ is called for ' ' + users.last_name

                # Resulting SQL: (users.full_name || %s)

            For numeric columns::

                op = 100 + users.age
                # Resulting SQL: (%s + users.age)
        """
        self._output = (f'({other._output[0]} {'||' if self.col_obj.datatype == str else '+'} {self._output[0]})', other._output[1]+self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} {'||' if self.col_obj.datatype == str else '+'} {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s + {self._output[0]})', [other]+self._output[1]) if isinstance(other, int) or isinstance(other , float) else (f'(%s || {self._output[0]})', [other if isinstance(other, str) else str(other)]+self._output[1])
        return self

    def __sub__(self, other):
        """
        Implement subtraction (`self - other`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance is used
        with the subtraction operator. It generates a SQL expression string
        and accumulates parameter values. The behavior depends on the type of
        ``other``:

        - If ``other`` is a :class:`ColumnsOperation`, both SQL fragments are
        combined with a subtraction operator, and the parameter lists are merged.
        - If ``other`` is a :class:`Column`, its name is used directly as the
        right-hand side of the subtraction.
        - If ``other`` is an ``int`` or ``float``, a placeholder ``%s`` is used,
        and the value is added to the parameter list.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            other (ColumnsOperation, Column, int, float): The right operand to
                subtract from this operation. Its type determines how the SQL
                expression is constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the new operation. This enables method chaining.

        Example:
            Assuming a numeric column ``users.age`` and a constant value::

                op = users.age - 5
                # Resulting SQL: (users.age - %s), params: [5]

            For subtraction between two column expressions::

                op = users.salary - users.bonus
                # Resulting SQL: (users.salary - users.bonus), params: []
        """
        self._output = (f'({self._output[0]} - {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} - {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} - %s)', self._output[1]+[other])
        return self

    def __rsub__(self, other):
        """
        Implement right-side subtraction (`other - self`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance appears
        on the right side of a ``-`` operator. It generates a SQL expression
        string and accumulates parameter values. The behavior depends on the
        type of ``other``:

        - If ``other`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``-`` operator, and their parameter lists are merged.
        - If ``other`` is a :class:`Column`, its name is used directly as the
        left operand.
        - If ``other`` is an ``int`` or ``float``, a placeholder ``%s`` is used
        for the value, and the parameter is collected.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            other (ColumnsOperation, Column, int, float): The left operand
                from which this operation will be subtracted. Its type determines
                how the SQL expression is constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the new operation. This enables method chaining.

        Example:
            Assuming a numeric column ``users.age`` and a constant value::

                # Right subtraction: 100 - users.age
                op = 100 - users.age
                # The __rsub__ is called for 100 - users.age

                # Resulting SQL: (%s - users.age)
                # Parameter: [100]

            With another column::

                op = users.max_age - users.age
                # __rsub__ may be called if users.max_age is on the left

            For string columns, subtraction is not typically used, but the
            operator is supported for numeric expressions.
        """
        self._output = (f'({other._output[0]} - {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} - {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s - {self._output[0]})', [other]+self._output[1])
        return self

    def __mul__(self, other):
        """
        Implement multiplication (`self * other`) for column operations.

        This method generates a SQL multiplication expression between the current
        column operation and the provided operand. It is called when a
        :class:`ColumnsOperation` instance is multiplied by another value.
        The behavior depends on the type of ``other``:

        - If ``other`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``*`` operator.
        - If ``other`` is a :class:`Column`, its fully qualified name is used
        directly as the right operand.
        - If ``other`` is an ``int`` or ``float``, a placeholder ``%s`` is used
        for the value, and the parameter is added to the parameter list.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            other (ColumnsOperation, Column, int, float): The right operand to
                multiply with this operation.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to represent the multiplication expression.

        Example:
            Multiplying a numeric column by a constant::

                from ormophine.Mysql import DataTypes, TableStructure, Driver

                # Assume a 'products' table with a 'price' column (numeric)
                # and we want to apply a 10% discount
                discounted = products.price * 0.9
                # discounted._output -> ('(products.price * %s)', [0.9])

            Multiplying two columns::

                total = products.quantity * products.price
                # total._output -> ('(products.quantity * products.price)', [])
        """
        self._output = (f'({self._output[0]} * {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} * {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} * %s)', self._output[1]+[other])
        return self

    def __rmul__(self, other):
        """
        Implement right-side multiplication (`other * self`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance appears
        on the right side of a ``*`` operator. It generates a SQL expression
        string and accumulates parameter values. The behavior depends on the
        type of ``other``:

        - If ``other`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``*`` operator.
        - If ``other`` is a :class:`Column`, its name is used directly.
        - If ``other`` is an ``int`` or ``float``, a placeholder ``%s`` is used
        for the value, and the parameter is collected.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            other (ColumnsOperation, Column, int, float): The left operand
                to be multiplied with this operation. Its type determines how the
                SQL expression is constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the new operation. This enables method chaining.

        Example:
            Assuming a numeric column ``users.age``::

                op = 2 * users.age
                # The __rmul__ is called for 2 * users.age
                # Resulting SQL: (%s * users.age)

            For column expressions::

                op = users.income * 0.1
                # __rmul__ is called for 0.1 * users.income
                # Resulting SQL: (%s * users.income)
        """
        self._output = (f'({other._output[0]} * {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} * {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s * {self._output[0]})', [other]+self._output[1])
        return self

    def __pow__(self, other):
        """
        Implement the exponentiation (power) operator (`self ** other`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance is used
        with the ``**`` operator. It generates a SQL ``POW()`` expression and
        accumulates parameter values. The behavior depends on the type of
        ``other``:

        - If ``other`` is a :class:`ColumnsOperation`, both sides are combined
        as ``POW(left_expression, right_expression)``.
        - If ``other`` is a :class:`Column`, its name is used as the exponent,
        resulting in ``POW(expression, column_name)``.
        - If ``other`` is a numeric value (``int`` or ``float``), a placeholder
        ``%s`` is used for the value, and the parameter is collected.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            other (ColumnsOperation, Column, int, float): The exponent (right
                operand). Its type determines how the SQL expression is constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the exponentiation operation. This enables method
            chaining.

        Example:
            Assuming a numeric column ``users.salary`` and a constant value::

                # Exponentiation with a constant
                op = users.salary ** 2
                # Resulting SQL: POW(users.salary, %s) with param [2]

                # Exponentiation with another column
                op = users.salary ** users.experience_years
                # Resulting SQL: POW(users.salary, users.experience_years)

                # Chaining with other operations
                op = (users.salary ** 2) + users.bonus
                # Resulting SQL: (POW(users.salary, %s) + users.bonus)
        """
        self._output = (f'POW({self._output[0]} , {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'POW({self._output[0]} , {other.name})', self._output[1]) if isinstance(other, Column) else (f'POW({self._output[0]} , %s)', self._output[1]+[other])
        return self

    def __rpow__(self, other):
        """
        Implement right-side exponentiation (`other ** self`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance appears
        on the right side of the ``**`` operator. It generates a SQL expression
        using the ``POW()`` function and accumulates parameter values. The
        behavior depends on the type of ``other``:

        - If ``other`` is a :class:`ColumnsOperation`, both sides are combined
        using ``POW(other_expression, self_expression)``.
        - If ``other`` is a :class:`Column`, its name is used as the base, and
        the exponent is the current operation's expression.
        - If ``other`` is an ``int`` or ``float``, a placeholder ``%s`` is used
        for the base value, and the parameter is collected.
        - Any other type is treated as a literal value (converted to string) and
        used with a placeholder.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            other (ColumnsOperation, Column, int, float, Any): The left operand
                (base) to be raised to the power of this operation (exponent).
                Its type determines how the SQL expression is constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the new operation. This enables method chaining.

        Example:
            Assuming a numeric column ``users.score``::

                # Right exponentiation with a constant
                op = 2 ** users.score
                # Resulting SQL: POW(%s, users.score) with parameter 2

                # With another column operation
                op = (users.age + 1) ** users.score
                # Resulting SQL: POW((users.age + 1), users.score)
        """
        self._output = (f'POW({other._output[0]} , {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'POW({other.name} , {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'POW(%s , {self._output[0]})', [other]+self._output[1])
        return self

    def __truediv__(self, other):
        """
        Implement left-side division (`self / other`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance is divided
        by another value using the ``/`` operator. It generates a SQL expression
        string and accumulates parameter values. The behavior depends on the type
        of ``other``:

        - If ``other`` is a :class:`ColumnsOperation`, both sides are combined
        using ``(left_expression / right_expression)``.
        - If ``other`` is a :class:`Column`, its name is used as the divisor, and
        the expression becomes ``(current_expression / column_name)``.
        - If ``other`` is an ``int`` or ``float``, a placeholder ``%s`` is used
        for the divisor value, and the parameter is collected.
        - Any other type is treated as a literal value (converted to string) and
        used with a placeholder.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            other (ColumnsOperation, Column, int, float, Any): The right operand
                (divisor) to divide this operation by. Its type determines how the
                SQL expression is constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the new operation. This enables method chaining.

        Example:
            Assuming a numeric column ``users.score``::

                # Division by a constant
                op = users.score / 2
                # Resulting SQL: (users.score / %s) with parameter 2

                # Division by another column
                op = users.score / users.max_score
                # Resulting SQL: (users.score / users.max_score)
        """
        self._output = (f'({self._output[0]} / {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} / {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} / %s)', self._output[1]+[other])
        return self

    def __rtruediv__(self, other):
        """
        Implement right-side division (`other / self`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance appears
        on the right side of the ``/`` operator. It generates a SQL expression
        using division and accumulates parameter values. The behavior depends
        on the type of ``other``:

        - If ``other`` is a :class:`ColumnsOperation`, both sides are combined
        as ``(other_expression / self_expression)``.
        - If ``other`` is a :class:`Column`, its name is used as the numerator,
        and the current operation's expression is the denominator.
        - If ``other`` is an ``int`` or ``float``, a placeholder ``%s`` is used
        for the numerator value, and the parameter is collected.
        - Any other type is treated as a literal value and used with a placeholder.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            other (ColumnsOperation, Column, int, float, Any): The left operand
                (numerator) to be divided by this operation (denominator).
                Its type determines how the SQL expression is constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the new operation. This enables method chaining.

        Example:
            Assuming a numeric column ``users.score``::

                # Right division with a constant
                op = 100 / users.score
                # Resulting SQL: (%s / users.score) with parameter 100

                # With another column operation
                op = (users.age + 1) / users.score
                # Resulting SQL: ((users.age + 1) / users.score)
        """
        self._output = (f'({other._output[0]} / {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} / {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s / {self._output[0]})', [other]+self._output[1])
        return self

    def __mod__(self, other):
        """
        Implement the modulo operation (`self % other`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance appears
        on the left side of the ``%`` operator. It generates a SQL expression
        using the modulo operator and accumulates parameter values. The behavior
        depends on the type of ``other``:

        - If ``other`` is a :class:`ColumnsOperation`, both sides are combined
        using the SQL modulo operator ``%``.
        - If ``other`` is a :class:`Column`, its name is used directly as the
        right operand.
        - If ``other`` is an ``int`` or ``float``, a placeholder ``%s`` is used
        for the value, and the parameter is collected.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            other (ColumnsOperation, Column, int, float): The right operand
                for the modulo operation. Its type determines how the SQL
                expression is constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the new operation. This enables method chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Modulo operation with a constant
                op = users.age % 10
                # Resulting SQL: (users.age % %s) with parameter 10

                # With another column operation
                op = users.age % (users.birth_year + 5)
                # Resulting SQL: (users.age % (users.birth_year + 5))
        """
        self._output = (f'({self._output[0]} % {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} % {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} % %s)', self._output[1]+[other])
        return self

    def __rmod__(self, other):
        """
        Implement right-side modulo (`other % self`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance appears
        on the right side of the ``%`` operator. It generates a SQL expression
        using the modulo operator and accumulates parameter values. The behavior
        depends on the type of ``other``:

        - If ``other`` is a :class:`ColumnsOperation`, both sides are combined
        using ``(other_expression % self_expression)``.
        - If ``other`` is a :class:`Column`, its name is used as the left operand,
        and the current operation's expression is the right operand.
        - If ``other`` is an ``int`` or ``float``, a placeholder ``%s`` is used
        for the value, and the parameter is collected.
        - Any other type is treated as a literal value (converted to string) and
        used with a placeholder.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            other (ColumnsOperation, Column, int, float, Any): The left operand
                to be divided by this operation (modulo). Its type determines how
                the SQL expression is constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the new operation. This enables method chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Right modulo with a constant
                op = 10 % users.age
                # Resulting SQL: (%s % users.age) with parameter 10

                # With another column operation
                op = (users.age + 5) % users.age
                # Resulting SQL: ((users.age + 5) % users.age)
        """
        self._output = (f'({other._output[0]} % {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} % {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s % {self._output[0]})', [other]+self._output[1])
        return self

    def __getitem__(self, key: slice):
        """
        Just like python string slicing , implement slicing (`self[start:stop]`) for string column operations.

        This method allows Python-like slicing syntax on :class:`ColumnsOperation`
        instances representing string columns. It generates a SQL ``SUBSTRING()``
        expression that extracts a substring from the column value based on the
        provided slice indices. The behavior mimics Python's string slicing,
        supporting positive and negative indices, as well as ``None`` for start or stop.

        The resulting SQL uses the ``SUBSTRING()`` function with appropriate start
        position and length calculations. For negative indices, the length of the
        string (``LENGTH()``) is used in the SQL expression.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self``, enabling chaining of operations.

        Note:
            This method is intended for use with string columns (``str`` datatype).
            Using it on numeric or other column types will produce invalid SQL.

        Args:
            key (slice): A Python slice object defining the substring range.
                The ``start`` and ``stop`` attributes can be ``None``, positive,
                or negative integers. A step is not supported (only start and stop).

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the substring operation. This enables method chaining.

        Raises:
            None: This method does not raise exceptions directly, but using it
            with non-string columns will result in SQL errors during execution.

        Example:
            Assuming a string column ``users.name``::

                # Get first 5 characters
                op = users.name[:5]
                # SQL: SUBSTRING(users.name, 1, 5)

                # Get from position 3 to the end
                op = users.name[2:]
                # SQL: SUBSTRING(users.name, 3, LENGTH(users.name))

                # Get last 3 characters (negative indexing)
                op = users.name[-3:]
                # SQL: SUBSTRING(users.name, LENGTH(users.name) - 2, LENGTH(users.name))

                # Get substring from 3rd character to 2 before the end
                op = users.name[2:-2]
                # SQL: SUBSTRING(users.name, 3, LENGTH(users.name) - 4)
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
        """
        Create an equality comparison expression.

        This method generates a SQL equality operation between the current
        expression and the provided value. It updates the internal ``_output``
        tuple (SQL fragment and parameter list) and returns ``self`` to enable
        method chaining. The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``=`` operator, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                equality comparison. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the equality comparison. This enables chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Create an equality condition
                condition = users.age.eq(25)
                # condition._output[0] -> '(users.age = %s)'
                # condition._output[1] -> [25]

                # Chain with other operations
                condition = users.age.eq(users.id)  # Compare two columns
                # condition._output[0] -> '(users.age = users.id)'
        """
        self._output = (f'{self._output[0]} = {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} = {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} = %s', self._output[1] + [value])
        return self

    def __eq__(self, value):
        """
        Implement equality comparison (`self == value`) for column operations.

        This magic method is called when a :class:`ColumnsOperation` instance is
        compared with another value using the ``==`` operator. It generates a SQL
        equality expression and updates the internal ``_output`` tuple (SQL
        fragment and parameter list). The method returns ``self`` to enable
        method chaining. The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``=`` operator, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                equality comparison. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the equality comparison. This enables chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Create an equality condition using ==
                condition = users.age == 25
                # condition._output[0] -> '(users.age = %s)'
                # condition._output[1] -> [25]

                # Compare two columns
                condition = users.age == users.id
                # condition._output[0] -> '(users.age = users.id)'
        """
        self._output = (f'{self._output[0]} = {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} = {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} = %s', self._output[1] + [value])
        return self

    def ne(self, value):
        """
        Create a non‑equality (not equal) comparison expression.

        This method generates a SQL inequality operation between the current
        expression and the provided value. It updates the internal ``_output``
        tuple (SQL fragment and parameter list) and returns ``self`` to enable
        method chaining. The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``!=`` operator, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                inequality comparison. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the inequality comparison. This enables chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Create an inequality condition
                condition = users.age.ne(25)
                # condition._output[0] -> '(users.age != %s)'
                # condition._output[1] -> [25]

                # Chain with other operations
                condition = users.age.ne(users.id)  # Compare two columns
                # condition._output[0] -> '(users.age != users.id)'
        """
        self._output = (f'{self._output[0]} != {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} != {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} != %s', self._output[1] + [value])
        return self

    def __ne__(self, value):
        """
        Implement the inequality operator (`!=`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance is compared
        with another value using the ``!=`` operator. It generates a SQL inequality
        expression and accumulates parameter values. The behavior depends on the
        type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``!=`` operator, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                inequality comparison. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the inequality operation. This enables chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Create an inequality condition
                condition = users.age.__ne__(25)
                # Equivalent to: users.age != 25
                # condition._output[0] -> '(users.age != %s)'
                # condition._output[1] -> [25]

                # Compare two columns
                condition = users.age.__ne__(users.id)
                # condition._output[0] -> '(users.age != users.id)'
        """
        self._output = (f'{self._output[0]} != {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} != {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} != %s', self._output[1] + [value])
        return self

    def gt(self, value):
        """
        Create a greater-than comparison expression.

        This method generates a SQL ``>`` operation between the current expression
        and the provided value. It updates the internal ``_output`` tuple (SQL
        fragment and parameter list) and returns ``self`` to enable method
        chaining. The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``>`` operator, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                comparison. Its type determines how the SQL expression and
                parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the greater-than comparison. This enables chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Create a greater-than condition
                condition = users.age.gt(18)
                # condition._output[0] -> '(users.age > %s)'
                # condition._output[1] -> [18]

                # Chain with other operations
                condition = users.age.gt(users.min_age)  # Compare two columns
                # condition._output[0] -> '(users.age > users.min_age)'
        """
        self._output = (f'{self._output[0]} > {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} > {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} > %s', self._output[1] + [value])
        return self

    def __gt__(self, value):
        """
        Implement the greater-than comparison operator (`>`).

        This method is called when a :class:`ColumnsOperation` instance is compared
        with another value using the ``>`` operator. It generates a SQL expression
        string and accumulates parameter values. The behavior depends on the type
        of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``>`` operator, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                greater-than comparison. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the comparison. This enables chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Create a greater-than condition
                condition = users.age > 25
                # condition._output[0] -> '(users.age > %s)'
                # condition._output[1] -> [25]

                # Chain with other comparisons
                condition = (users.age > 18) & (users.age < 65)
                # Generates: ((users.age > %s) AND (users.age < %s))
        """
        self._output = (f'{self._output[0]} > {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} > {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} > %s', self._output[1] + [value])
        return self

    def lt(self, value):
        """
        Create a less-than comparison expression.

        This method generates a SQL less-than operation between the current
        expression and the provided value. It updates the internal ``_output``
        tuple (SQL fragment and parameter list) and returns ``self`` to enable
        method chaining. The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``<`` operator, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                less-than comparison. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the less-than comparison. This enables chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Create a less-than condition
                condition = users.age.lt(25)
                # condition._output[0] -> '(users.age < %s)'
                # condition._output[1] -> [25]

                # Chain with other operations
                condition = users.age.lt(users.max_age)  # Compare two columns
                # condition._output[0] -> '(users.age < users.max_age)'
        """
        self._output = (f'{self._output[0]} < {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} < {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} < %s', self._output[1] + [value])
        return self

    def __lt__(self, value):
        """
        Implement the less-than operator (`<`) for column operations.

        This method is invoked when a :class:`ColumnsOperation` instance is used
        with the ``<`` operator (e.g., ``op < value``). It generates a SQL
        less-than expression and updates the internal ``_output`` tuple (SQL
        fragment and parameter list). The behavior depends on the type of
        ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``<`` operator, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                less-than comparison. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the less-than operation. This enables chaining.

        Example:
            Using the ``<`` operator with a numeric column::

                from ormophine.Mysql import Column

                # Assuming `users.age` is a Column instance
                condition = users.age < 25
                # condition._output[0] -> '(users.age < %s)'
                # condition._output[1] -> [25]

                # Compare two columns
                condition = users.age < users.max_age
                # condition._output[0] -> '(users.age < users.max_age)'
        """
        self._output = (f'{self._output[0]} < {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} < {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} < %s', self._output[1] + [value])
        return self

    def ge(self, value):
        """
        Create a greater-than-or-equal-to comparison expression.

        This method generates a SQL greater-than-or-equal operation between the
        current expression and the provided value. It updates the internal
        ``_output`` tuple (SQL fragment and parameter list) and returns ``self``
        to enable method chaining. The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``>=`` operator, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                greater-than-or-equal comparison. Its type determines how the
                SQL expression and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the comparison. This enables chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Create a greater-than-or-equal condition
                condition = users.age.ge(18)
                # condition._output[0] -> '(users.age >= %s)'
                # condition._output[1] -> [18]

                # Chain with other operations
                condition = users.age.ge(users.min_age)  # Compare two columns
                # condition._output[0] -> '(users.age >= users.min_age)'
        """
        self._output = (f'{self._output[0]} >= {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} >= {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} >= %s', self._output[1] + [value])
        return self

    def __ge__(self, value):
        """
        Implement greater-than-or-equal comparison (`self >= value`) for column operations.

        This method is called when a :class:`ColumnsOperation` instance is compared
        using the ``>=`` operator. It generates a SQL expression string and
        accumulates parameter values. The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``>=`` operator, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                comparison. Its type determines how the SQL expression and
                parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the greater-than-or-equal comparison. This enables
            chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Create a condition using the >= operator
                condition = users.age >= 18
                # condition._output[0] -> '(users.age >= %s)'
                # condition._output[1] -> [18]

                # Compare two columns
                condition = users.age >= users.min_age
                # condition._output[0] -> '(users.age >= users.min_age)'
        """
        self._output = (f'{self._output[0]} >= {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} >= {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} >= %s', self._output[1] + [value])
        return self

    def le(self, value):
        """
        Create a less-than-or-equal-to comparison expression.

        This method generates a SQL ``<=`` operation between the current expression
        and the provided value. It updates the internal ``_output`` tuple (SQL
        fragment and parameter list) and returns ``self`` to enable method chaining.
        The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using the ``<=`` operator, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                less-than-or-equal-to comparison. Its type determines how the SQL
                expression and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the less-than-or-equal-to comparison. This enables
            chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Create a less-than-or-equal-to condition
                condition = users.age.le(25)
                # condition._output[0] -> '(users.age <= %s)'
                # condition._output[1] -> [25]

                # Chain with other operations
                condition = users.age.le(users.max_age)  # Compare two columns
                # condition._output[0] -> '(users.age <= users.max_age)'
        """
        self._output = (f'{self._output[0]} <= {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} <= {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} <= %s', self._output[1] + [value])
        return self

    def __le__(self, value):
        """
        Implement less-than-or-equal comparison (`self <= value`).

        This special method is called when a :class:`ColumnsOperation` instance
        is compared with another value using the ``<=`` operator. It generates a
        SQL expression using the ``<=`` operator and accumulates parameter values.
        The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        using ``<=``, and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to allow chaining.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                less-than-or-equal comparison. Its type determines how the SQL
                expression and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the less-than-or-equal comparison. This enables
            method chaining.

        Example:
            Assuming a numeric column ``users.age``::

                # Create a <= condition using the operator
                condition = users.age <= 25
                # condition._output[0] -> '(users.age <= %s)'
                # condition._output[1] -> [25]

                # Compare two columns
                condition = users.age <= users.max_age
                # condition._output[0] -> '(users.age <= users.max_age)'
        """
        self._output = (f'{self._output[0]} <= {value._output[0]}', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} <= {value.name}', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'{self._output[0]} <= %s', self._output[1] + [value])
        return self

    def __and__(self, value):
        """
        Implement the bitwise AND operator (`&`) as a logical AND for SQL conditions.

        This method is called when a :class:`ColumnsOperation` instance is used with
        the ``&`` operator. It generates a SQL expression combining the current
        operation's SQL fragment and the provided value's SQL fragment with an
        ``AND`` between them. Both parameter lists are merged, and the internal
        ``_output`` tuple is updated accordingly.

        The method returns ``self`` to allow chaining of conditions, making it
        convenient to build complex WHERE clauses.

        Args:
            value (ColumnsOperation): The right-hand side operation to combine
                with the current operation using ``AND``. Must be a
                :class:`ColumnsOperation` instance.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the combined condition. This enables chaining.

        Raises:
            AttributeError: If ``value`` is not a :class:`ColumnsOperation` (though
                the implementation does not explicitly check for this, the intended
                usage is with another operation).

        Example:
            Building a complex WHERE condition using ``&`` to combine conditions::

                from ormophine.Mysql import Column

                # Assume users is a Table instance with columns: id, name, age
                condition = (users.age > 18) & (users.name.startswith('A'))
                # condition._output[0] -> '((users.age > %s) AND (users.name like %s || '%%'))'
                # condition._output[1] -> [18, 'A']

                # Use in a query
                rows = users.get_row(which_columns=[users.id, users.name],
                                    where=condition)
        """
        self._output = (f'({self._output[0]} AND {value._output[0]})', self._output[1] + value._output[1])
        return self

    def __or__(self, value):
        """
        Implement the bitwise OR operator (`|`) as a logical OR for SQL conditions.

        This method is called when a :class:`ColumnsOperation` instance is used with
        the ``|`` operator. It generates a SQL expression combining the current
        operation's SQL fragment and the provided value's SQL fragment with an
        ``OR`` between them. Both parameter lists are merged, and the internal
        ``_output`` tuple is updated accordingly.

        The method returns ``self`` to allow chaining of conditions, making it
        convenient to build complex WHERE clauses.

        Args:
            value (ColumnsOperation): The right-hand side operation to combine
                with the current operation using ``OR``. Must be a
                :class:`ColumnsOperation` instance.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the combined condition. This enables chaining.

        Raises:
            AttributeError: If ``value`` is not a :class:`ColumnsOperation` (though
                the implementation does not explicitly check for this, the intended
                usage is with another operation).

        Example:
            Building a complex WHERE condition using ``|`` to combine conditions::

                from ormophine.Mysql import Column

                # Assume users is a Table instance with columns: id, name, age
                condition = (users.age < 18) | (users.age > 65)
                # condition._output[0] -> '((users.age < %s) OR (users.age > %s))'
                # condition._output[1] -> [18, 65]

                # Use in a query
                rows = users.get_row(which_columns=[users.id, users.name],
                                    where=condition)
        """
        self._output = (f'({self._output[0]} OR {value._output[0]})', self._output[1] + value._output[1])
        return self

    def like(self, value):
        """
        Create a SQL LIKE pattern-matching comparison.

        This method generates a SQL `LIKE` expression between the current column
        operation and a pattern value. The pattern can be a literal string,
        another column, or a complex operation. The method updates the internal
        ``_output`` tuple (SQL fragment and parameter list) and returns ``self``
        to enable method chaining.

        The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined
        with the `LIKE` operator, and their parameter lists are merged.
        - If ``value`` is a :class:`Column`, its name is used directly on the
        right side, and no additional parameters are added.
        - For any other type (typically a string), the value is treated as a
        literal pattern, a placeholder ``%s`` is used, and the value is added
        to the parameter list after converting to a string.

        Note that the `LIKE` operator in MySQL performs pattern matching with
        ``%`` and ``_`` wildcards. For exact string matching, consider using
        :meth:`eq`.

        Args:
            value (ColumnsOperation, Column, str): The pattern to match against.
                If a string, it will be used as a literal pattern with placeholder.
                If a Column, its name is used directly. If another operation,
                the combined SQL expression is used.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the LIKE comparison. This enables chaining.

        Example:
            Using the `like` method to find users whose names start with 'A'::

                # Assuming users is a Table instance with a 'name' Column
                condition = users.name.like('A%')
                # condition._output[0] -> '(users.name like %s)'
                # condition._output[1] -> ['A%']

                # Combining with another condition
                condition = users.name.like(users.pattern_column)
                # condition._output[0] -> '(users.name like users.pattern_column)'

            For more complex patterns, you can use :meth:`startswith`, :meth:`endswith`,
            or :meth:`contains` which build the appropriate LIKE patterns with
            wildcards automatically.
        """
        self._output = (f"{self._output[0]} like {value._output[0]}", (self._output[1] + value._output[1]) if self._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self._output[0]} like {value.name}', self._output[1]) if isinstance(value , Column) else (f'{self._output[0]} like %s', self._output[1] + [f'{value}'])
        return self

    def startswith(self, prefix):
        """
        Just like python startswith(), create a SQL condition that checks if the current expression starts with a given prefix.

        This method generates a ``LIKE`` condition with the prefix followed by a wildcard
        (``'%%'``), effectively testing whether the expression's value begins with the
        specified prefix. It updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to enable method chaining. The behavior
        depends on the type of ``prefix``:

        - If ``prefix`` is a :class:`ColumnsOperation`, both sides are combined using
        the ``LIKE`` operator with string concatenation (``|| '%%'``), and parameters
        are merged.
        - If ``prefix`` is a :class:`Column`, its name is used directly on the right
        side, and the wildcard is concatenated using ``|| '%%'``.
        - For any other type (e.g., a string literal), a placeholder ``%s`` is used
        for the value, and the wildcard is appended in the SQL fragment, with the
        parameter added to the list.

        Args:
            prefix (ColumnsOperation, Column, Any): The prefix to test against. Its
                type determines how the SQL expression and parameters are constructed.
                If a literal value is provided, it is automatically converted to a
                string and used as a parameter.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the ``STARTSWITH`` condition. This enables chaining.

        Example:
            Assuming a string column ``users.name``::

                # Create a condition for names starting with 'A'
                condition = users.name.startswith('A')
                # condition._output[0] -> '(users.name like %s || '%%')'
                # condition._output[1] -> ['A']

                # Use with a Column as prefix
                prefix_col = users.prefix_column
                condition = users.name.startswith(prefix_col)
                # condition._output[0] -> '(users.name like users.prefix_column || '%%')'
        """
        self._output = (f"{self._output[0]} like {prefix._output[0]} || '%%'", (self._output[1] + prefix._output[1]) if self._output else prefix._output[1]) if isinstance(prefix, ColumnsOperation) else (f"{self._output[0]} like {prefix.name} || '%%'", self._output[1]) if isinstance(prefix , Column) else (f"{self._output[0]} like %s || '%%'", self._output[1] + [f'{prefix}'])
        return self

    def endswith(self, suffix):
        """
        Just like python endswith(), create a SQL condition that checks if the current expression ends with a suffix.

        This method generates a SQL ``LIKE`` expression using the pattern
        ``'%%' || suffix``, which matches strings that end with the specified suffix.
        The operator used is ``LIKE`` with concatenation (``||``) to combine the
        wildcard prefix with the suffix. The method updates the internal ``_output``
        tuple (SQL fragment and parameter list) and returns ``self`` to enable
        chaining.

        The behavior depends on the type of ``suffix``:

        - If ``suffix`` is a :class:`ColumnsOperation`, both sides are combined
        using the pattern ``'%%' || suffix_expression``, and parameters are merged.
        - If ``suffix`` is a :class:`Column`, its name is used directly, and no
        additional parameters are added.
        - If ``suffix`` is a literal value (e.g., ``str``), a placeholder ``%s`` is
        used for the suffix, and the value is added to the parameter list.

        Args:
            suffix (ColumnsOperation, Column, str): The suffix to check for at the end
                of the current expression. Its type determines how the SQL pattern
                and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the ``LIKE`` condition. This enables chaining.

        Example:
            Assuming a string column ``users.email``::

                # Check if email ends with '@example.com'
                condition = users.email.endswith('@example.com')
                # condition._output[0] -> "(users.email like '%%' || %s)"
                # condition._output[1] -> ['@example.com']

                # Using a column as the suffix
                condition = users.email.endswith(users.domain)
                # condition._output[0] -> "(users.email like '%%' || users.domain)"

                # Chain with other conditions
                condition = (users.email.endswith('@gmail.com') & users.age >= 18)
                # condition._output[0] -> "((users.email like '%%' || %s) AND (users.age >= %s))"
                # condition._output[1] -> ['@gmail.com', 18]
        """
        self._output = (f"{self._output[0]} like '%%' || {suffix._output[0]}", (self._output[1] + suffix._output[1]) if self._output else suffix._output[1]) if isinstance(suffix, ColumnsOperation) else (f"{self._output[0]} like '%%' || {suffix.name}", self._output[1]) if isinstance(suffix , Column) else (f"{self._output[0]} like '%%' || %s", self._output[1] + [f'{suffix}'])
        return self

    def contains(self, value):
        """
        Create a SQL LIKE condition to check if the expression contains a substring.

        This method generates a SQL ``LIKE`` expression with the pattern ``'%%' || value || '%%'``,
        effectively checking whether the current expression contains the specified substring.
        The method updates the internal ``_output`` tuple (SQL fragment and parameter list)
        and returns ``self`` to enable method chaining. The behavior depends on the type of
        ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, both sides are combined using
        the ``LIKE`` operator with the pattern ``'%%' || value_expression || '%%'``,
        and parameters are merged.
        - If ``value`` is a :class:`Column`, its name is used directly in the pattern,
        and no additional parameters are added.
        - For any other type (e.g., int, float, str), the value is converted to a string
        and used as a parameter with the ``'%%' || %s || '%%'`` pattern.

        Args:
            value (ColumnsOperation, Column, Any): The substring to search for. Its
                type determines how the SQL expression and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the ``LIKE`` condition. This enables chaining.

        Example:
            Assuming a string column ``users.name``::

                # Check if name contains 'smith'
                condition = users.name.contains('smith')
                # condition._output[0] -> '(users.name like '%%' || %s || '%%')'
                # condition._output[1] -> ['smith']

                # Chain with other operations
                condition = users.name.contains(users.partial_name)
                # condition._output[0] -> '(users.name like '%%' || users.partial_name || '%%')'
        """
        self._output = (f"{self._output[0]} like '%%' || {value._output[0]} || '%%'", (self._output[1] + value._output[1]) if self._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self._output[0]} like '%%' || {value.name} || '%%'", self._output[1]) if isinstance(value , Column) else (f"{self._output[0]} like '%%' || %s || '%%'", self._output[1] + [f'{value}'])
        return self

    def add_end(self, content):
        """
        Concatenate content to the end of the current expression.

        This method generates a SQL string concatenation operation using the ``||``
        operator. It appends the provided ``content`` to the right side of the
        current expression. The behavior depends on the type of ``content``:

        - If ``content`` is a :class:`ColumnsOperation`, both SQL fragments are
        combined with ``||``, and their parameter lists are merged.
        - If ``content`` is a :class:`Column`, its name is used directly, and no
        additional parameters are added.
        - For any other type (e.g., str, int), a placeholder ``%s`` is used, and
        the value is added to the parameter list.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to enable method chaining.

        This method is intended for string columns only. Using it on numeric
        columns may result in unintended SQL behavior (the driver's SQL mode
        must have ``PIPES_AS_CONCAT`` enabled for ``||`` to perform concatenation).

        Args:
            content (ColumnsOperation, Column, Any): The content to append to
                the current expression. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the concatenation. This enables chaining.

        Example:
            Assuming a string column ``users.full_name``::

                # Append a space and a last name
                op = users.full_name.add_end(' ').add_end('Smith')
                # op._output[0] -> '((users.full_name || %s) || %s)'
                # op._output[1] -> [' ', 'Smith']

                # Using with another ColumnsOperation
                suffix = users.last_name
                op = users.first_name.add_end(suffix)
                # op._output[0] -> '(users.first_name || users.last_name)'
        """
        self._output = (f'({self._output[0]} || {content._output[0]})', self._output[1]+content._output[1] if self._output else content._output[1]) if isinstance(content, ColumnsOperation) else (f'({self._output[0]} || {content.name})', self._output[1] if self._output else []) if isinstance(content, Column) else (f'({self._output[0]} || %s)', self._output[1]+[content] if self._output else [content])
        return self

    def add_first(self, content):
        """
        Concatenate content to the beginning of the current expression.

        This method generates a SQL string concatenation operation using the ``||``
        operator. It prepends the provided ``content`` to the left side of the
        current expression. The behavior depends on the type of ``content``:

        - If ``content`` is a :class:`ColumnsOperation`, both SQL fragments are
        combined with ``||``, and their parameter lists are merged.
        - If ``content`` is a :class:`Column`, its name is used directly, and no
        additional parameters are added.
        - For any other type (e.g., str, int), a placeholder ``%s`` is used, and
        the value is added to the parameter list.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to enable method chaining.

        This method is intended for string columns only. Using it on numeric
        columns may result in unintended SQL behavior (the driver's SQL mode
        must have ``PIPES_AS_CONCAT`` enabled for ``||`` to perform concatenation).

        Args:
            content (ColumnsOperation, Column, Any): The content to prepend to
                the current expression. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the concatenation. This enables chaining.

        Example:
            Assuming a string column ``users.last_name``::

                # Prepend a first name and a space
                op = users.last_name.add_first('John ').add_first(' ')
                # op._output[0] -> '((%s || users.last_name) || %s)'
                # op._output[1] -> ['John ', ' ']

                # Using with another ColumnsOperation
                prefix = users.title
                op = users.last_name.add_first(prefix)
                # op._output[0] -> '(users.title || users.last_name)'
        """
        self._output = (f'({content._output[0]} || {self._output[0]})', content._output[1]+self._output[1] if self._output else content._output[1]) if isinstance(content, ColumnsOperation) else (f'({content.name} || {self._output[0]})', self._output[1] if self._output else []) if isinstance(content, Column) else (f'(%s || {self._output[0]})', [content]+self._output[1] if self._output else [content])
        return self

    def replace(self, old: str, new: str):
        """
        Generate a SQL REPLACE expression to substitute occurrences of a substring.

        This method creates a SQL expression using the ``REPLACE()`` function, which
        replaces all occurrences of a specified substring with a new substring in
        the current column or operation expression. The replacement is applied to
        the string value represented by the current operation.

        If the current operation already has an expression stored in ``_output``,
        that expression is used as the target. Otherwise, the original column name
        (``col_obj.name``) is used. Two placeholders (``%s``) are added for the
        old and new strings, and the parameters are appended to the parameter list.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to enable method chaining.

        Args:
            old (str): The substring to be replaced.
            new (str): The substring to replace with.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the REPLACE operation. This enables chaining.

        Example:
            Assuming a string column ``users.bio``::

                # Replace 'old' with 'new' in the bio column
                op = users.bio.replace('old', 'new')
                # op._output[0] -> 'REPLACE(users.bio , %s , %s)'
                # op._output[1] -> ['old', 'new']

                # Chain with other operations
                op = users.bio.upper().replace('OLD', 'NEW')
                # op._output[0] -> 'REPLACE(UPPER(users.bio) , %s , %s)'
                # op._output[1] -> ['OLD', 'NEW']
        """
        self._output = (f'REPLACE({self._output[0]} , %s , %s)', self._output[1] + [old, new]) if self._output else (f'REPLACE({self.col_obj.name} , %s , %s)', [old, new])
        return self

    def upper(self):
        """
        Just like python upper(), apply the SQL UPPER function to the current expression.

        This method generates a SQL expression that converts the current column
        or operation result to uppercase. It updates the internal ``_output``
        tuple (SQL fragment and parameter list) and returns ``self`` to enable
        method chaining. If the current expression is already an operation (i.e.,
        ``self._output`` is not empty), the UPPER function is applied to the
        existing SQL fragment; otherwise, it is applied to the original column
        name stored in ``self.col_obj``.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the UPPER transformation. This enables chaining.

        Example:
            Assuming a string column ``users.username``::

                # Convert username to uppercase in a condition
                condition = users.username.upper().eq('ADMIN')
                # condition._output[0] -> 'UPPER(users.username) = %s'
                # condition._output[1] -> ['ADMIN']

                # Chain with other operations
                result = users.username.upper().startswith('A')
                # result._output[0] -> "UPPER(users.username) like %s || '%%'"
                # result._output[1] -> ['A']
        """
        self._output = (f'UPPER({self._output[0]})', self._output[1]) if self._output else (f'UPPER({self.col_obj.name})', [])
        return self

    def lower(self):
        """
        Just like python lower(), convert the current expression to lowercase using the SQL ``LOWER()`` function.

        This method generates a SQL fragment that wraps the current expression
        (or the column name if no operation has been applied yet) with the
        ``LOWER()`` function. It updates the internal ``_output`` tuple (SQL
        fragment and parameter list) and returns ``self`` to enable chaining.

        If the current operation already has an expression (e.g., after arithmetic
        or string operations), that expression is wrapped. Otherwise, the raw
        column name of the associated :class:`Column` is used.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the ``LOWER()`` transformation. This enables chaining.

        Example:
            Assuming a string column ``users.name``::

                # Convert the name to lowercase
                op = users.name.lower()
                # op._output[0] -> 'LOWER(users.name)'
                # op._output[1] -> []

                # Chain with other operations
                op = (users.first_name + ' ' + users.last_name).lower()
                # op._output[0] -> 'LOWER((users.first_name || %s || users.last_name))'
                # op._output[1] -> [' ']
        """
        self._output = (f'LOWER({self._output[0]})', self._output[1]) if self._output else (f'LOWER({self.col_obj.name})', [])
        return self

    def strip(self, chars: str = ' '):
        """
        Just like python strip(), remove leading and trailing characters from the current expression.

        This method generates a SQL ``TRIM(BOTH ... FROM ...)`` expression that
        removes all occurrences of the specified ``chars`` from both ends of the
        current column or operation. If the current operation already contains
        a SQL fragment (i.e., ``_output`` is not empty), the ``TRIM`` is applied
        to that fragment; otherwise, it is applied directly to the associated
        column name.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to enable method chaining.

        Args:
            chars (str, optional): A string containing the characters to remove
                from both ends. Defaults to a single space (``' '``).

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the trimming operation. This enables chaining.

        Example:
            Assuming a string column ``users.full_name``::

                # Remove leading/trailing spaces
                op = users.full_name.strip()
                # op._output[0] -> "TRIM(BOTH ' ' FROM users.full_name)"

                # Remove specific characters
                op = users.full_name.strip('_')
                # op._output[0] -> "TRIM(BOTH '_' FROM users.full_name)"

                # Chain with other operations
                op = (users.first_name + ' ' + users.last_name).strip()
                # op._output[0] -> "TRIM(BOTH ' ' FROM (users.first_name || ' ' || users.last_name))"
        """
        self._output = (f"TRIM(BOTH '{chars}' FROM {self._output[0]})", self._output[1]) if self._output else (f"TRIM(BOTH '{chars}' FROM {self.col_obj.name})", [])
        return self

    def lstrip(self, chars: str = ' '):
        """
        Just like python lstrip(), generate a SQL expression that trims leading characters from a string.

        This method applies the SQL ``TRIM(LEADING ... FROM ...)`` function to the
        current string expression, removing all leading occurrences of the specified
        characters. If the current operation already has a SQL expression (i.e.,
        ``self._output`` is not empty), the trimming is applied to that expression.
        Otherwise, it is applied to the original column name stored in
        ``self.col_obj.name``.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to enable method chaining.

        Args:
            chars (str, optional): A string of characters to remove from the
                leading end of the expression. Defaults to a single space ``' '``.
                If multiple characters are provided, each is treated as a separate
                character to be stripped.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the left‑trim operation. This enables chaining.

        Example:
            Assuming a string column ``users.name`` with leading whitespace::

                # Remove leading spaces from the column
                op = users.name.lstrip()
                # op._output[0] -> "TRIM(LEADING ' ' FROM users.name)"
                # op._output[1] -> []

                # Remove leading '@' characters
                op = users.username.lstrip('@')
                # op._output[0] -> "TRIM(LEADING '@' FROM users.username)"

                # Chain with other operations
                op = users.name.upper().lstrip()
                # op._output[0] -> "TRIM(LEADING ' ' FROM UPPER(users.name))"
        """
        self._output = (f"TRIM(LEADING '{chars}' FROM {self._output[0]})", self._output[1]) if self._output else (f"TRIM(LEADING '{chars}' FROM {self.col_obj.name})", [])
        return self

    def rstrip(self, chars: str = ' '):
        """
        Just like python rstrip(), generate a SQL expression that trims trailing characters from a string.

        This method applies the SQL ``TRIM(TRAILING ... FROM ...)`` function to the
        current string expression, removing all trailing occurrences of the specified
        characters. If the current operation already has a SQL expression (i.e.,
        ``self._output`` is not empty), the trimming is applied to that expression.
        Otherwise, it is applied to the original column name stored in
        ``self.col_obj.name``.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to enable method chaining.

        Args:
            chars (str, optional): A string of characters to remove from the
                trailing end of the expression. Defaults to a single space ``' '``.
                If multiple characters are provided, each is treated as a separate
                character to be stripped.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the right‑trim operation. This enables chaining.

        Example:
            Assuming a string column ``users.name`` with trailing whitespace::

                # Remove trailing spaces from the column
                op = users.name.rstrip()
                # op._output[0] -> "TRIM(TRAILING ' ' FROM users.name)"
                # op._output[1] -> []

                # Remove trailing '@' characters
                op = users.username.rstrip('@')
                # op._output[0] -> "TRIM(TRAILING '@' FROM users.username)"

                # Chain with other operations
                op = users.name.lower().rstrip()
                # op._output[0] -> "TRIM(TRAILING ' ' FROM LOWER(users.name))"
        """
        self._output = (f"TRIM(TRAILING '{chars}' FROM {self._output[0]})", self._output[1]) if self._output else (f"TRIM(TRAILING '{chars}' FROM {self.col_obj.name})", [])
        return self

    def In(self, value):
        """
        Generate an SQL ``IN`` condition or fall back to equality.

        This method creates a SQL fragment that checks whether the current
        expression is contained within a set of values or a subquery. The
        behavior depends on the type of ``value``:

        * If ``value`` is a :class:`ColumnsOperation`, it is treated as a
        subquery (or a set expression), and the SQL fragment becomes
        ``<expression> IN (<subquery>)``.
        * If ``value`` is a ``list`` or ``tuple``, an ``IN`` clause with
        placeholders is generated: ``<expression> IN (%s, %s, ...)``, and
        all items are added as parameters.
        * For any other single value, the method falls back to an equality
        condition: ``<expression> = %s``.

        The method updates the internal ``_output`` tuple (SQL fragment and
        parameter list) and returns ``self`` to enable method chaining.

        Args:
            value (ColumnsOperation, list, tuple, Any): The right-hand side of
                the condition. If a :class:`ColumnsOperation`, it is used as a
                subquery. If a list or tuple, it provides the set of values for
                the ``IN`` clause. Otherwise, the method generates an equality
                condition.

        Returns:
            ColumnsOperation: The same instance, with its ``_output`` attribute
            updated to reflect the ``IN`` or equality condition.

        Example:
            Using the ``In`` method to filter rows based on a list of values::

                from ormophine.Mysql import Table, Column

                # Assume users is a Table instance with a column 'id'
                condition = users.id.In([1, 2, 3])
                # condition._output[0] -> 'users.id IN (%s,%s,%s)'
                # condition._output[1] -> [1, 2, 3]

                # Using a subquery (e.g., select IDs from another table)
                subquery = other_table.id.gt(10)  # this would be a ColumnsOperation
                condition = users.id.In(subquery)
                # condition._output[0] -> 'users.id IN (other_table.id > %s)'
                # condition._output[1] -> [10]
        """
        self._output = (f"{self._output[0]} IN ({value._output[0]})",self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self._output[0]} IN ({','.join(['%s'] * len(value))})",self._output[1] + list(value)) if isinstance(value, (list, tuple)) else (f"{self._output[0]} = %s",self._output[1] + [value])
        return self


class Column:
    """
    Represents a database column and provides an expressive interface for building SQL expressions.

    The :class:`Column` class is the fundamental building block for query construction
    and schema manipulation. Each instance corresponds to a specific column in a
    database table and is typically created automatically by the :class:`Table`
    class when a table is loaded.

    **Expression Building**

    Columns support Python operators and methods that generate SQL expressions.
    These expressions are encapsulated in :class:`ColumnsOperation` objects,
    which can be chained together to build complex queries. The generated SQL
    is context-aware, using appropriate operators based on the column's data type
    (e.g., ``||`` for string concatenation vs. ``+`` for numeric addition).

    Supported operations include:

    - Arithmetic: ``+``, ``-``, ``*``, ``/``, ``%``, ``**`` (POW)
    - Comparisons: ``==``, ``!=``, ``>``, ``<``, ``>=``, ``<=`` (and explicit methods like ``.eq()``)
    - String methods: ``.like()``, ``.startswith()``, ``.endswith()``, ``.contains()``,
      ``.upper()``, ``.lower()``, ``.strip()``, ``.lstrip()``, ``.rstrip()``,
      ``.replace()``, ``.add_end()``, ``.add_first()``, and slice indexing
    - Set membership: ``.In()``
    - Logical combinations via ``&`` (AND) and ``|`` (OR)

    **Schema Modification**

    The class also provides methods for altering the table schema, such as
    :meth:`rename` and :meth:`delete_column`. These operations are destructive
    and require explicit confirmation flags.

    **Attributes**

    The Column instance stores the fully qualified column name (with table name),
    the unqualified name (for use in queries), a reference to its parent :class:`Table`,
    and the Python data type inferred from the database.

    Attributes:
        name (str): The fully qualified column name in the format
            ``'`table_name`.`column_name`'``. This is used in SQL expressions
            when the table needs to be explicitly referenced (e.g., in JOINs).
        first_name (str): The column name wrapped in backticks, e.g., ``'`column_name`'``.
            This is used when the table context is clear.
        table_obj (Table): The parent :class:`Table` instance that owns this column.
        datatype (type): The Python type corresponding to the column's SQL data type
            (e.g., ``int``, ``str``, ``float``, ``bytes``).

    Example:
        Accessing columns from a table instance and building expressions::

            from ormophine.Mysql import Table, Driver

            # Assume `db` is a Driver instance connected to a database
            users = db.users  # Table instance

            # Refer to columns as attributes
            age_col = users.age
            name_col = users.name

            # Build a condition using operators
            condition = (age_col >= 18) & name_col.startswith('A')
            # condition is a ColumnsOperation: ((users.age >= %s) AND (users.name like %s || '%%'))

            # Use string methods
            full_name = users.first_name.add_end(' ').add_end(users.last_name)
            # full_name._output[0] -> '((users.first_name || %s) || users.last_name)'

            # Rename a column (destructive)
            users.age.rename(users.age, 'user_age')

        For more details on available methods, refer to the individual method
        documentation.
    """
    def __init__(self, table_obj: Table, column_name: str, datatype: type):
        """
        Initialize a new Column instance representing a database column.

        This constructor is typically called automatically by the :class:`Table`
        class when it loads table metadata. Users rarely instantiate this class
        directly; instead, they access columns as attributes of a :class:`Table`
        instance (e.g., ``users.id``, ``users.name``).

        The column's fully qualified name (including the table name) is stored in
        :attr:`name`, while the raw column name wrapped in backticks is stored in
        :attr:`first_name` for use in SQL queries. The associated table object
        and the Python datatype (int, str, float, bytes) are also recorded.

        Args:
            table_obj (Table): The :class:`Table` instance that this column
                belongs to.
            column_name (str): The name of the column in the database table.
            datatype (type): The Python type corresponding to the column's SQL
                data type (e.g., ``int`` for INTEGER, ``str`` for VARCHAR, etc.).

        Returns:
            None

        Example:
            Columns are typically accessed via a table object::

                from ormophine.Mysql import Driver

                db = Driver(host='localhost', username='user',
                            password='pass', db_name='mydb')
                users = db.users  # Table instance

                # Accessing a column attribute returns a Column instance
                id_column = users.id
                # id_column.name -> '`users`.`id`'
                # id_column.first_name -> '`id`'
                # id_column.datatype -> int
        """
        self.name= table_obj.name_+'.`'+column_name+'`'
        self.first_name= f'`{column_name}`'
        self.table_obj= table_obj
        self.datatype= datatype

    def __hash__(self):
        """
        Return the hash value of the column.

        This method computes a hash based on the fully qualified column name
        (``table.column``). It enables :class:`Column` instances to be used as
        keys in dictionaries and sets. The hash is derived from the ``name``
        attribute, which uniquely identifies the column within the database.

        Returns:
            int: The hash value of the column's fully qualified name.

        Example:
            Using a :class:`Column` object as a dictionary key::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a column 'id'
                col = users.id
                d = {col: 'primary key'}
                print(d[col])  # 'primary key'
        """
        return hash(self.name)

    def __add__(self, value):
        """
        Implement addition or string concatenation for a column.

        This method is called when a :class:`Column` instance is used on the
        left side of the ``+`` operator. It creates a new :class:`ColumnsOperation`
        instance, initializes its internal SQL fragment with the column's fully
        qualified name, and then delegates the actual addition logic to the
        operation's own ``__add__`` method. The operator used depends on the
        column's datatype:

        - For string columns (``str``), the SQL ``||`` operator is used for
        concatenation.
        - For numeric columns, the SQL ``+`` operator is used for arithmetic
        addition.

        Args:
            value (ColumnsOperation, Column, int, float, str): The right-hand side
                of the addition. The type determines how the SQL is constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance that
            represents the combined expression, allowing further chaining.

        Example:
            Assuming a ``users`` table with string column ``first_name`` and
            numeric column ``age``::

                # String concatenation
                full_name = users.first_name + ' ' + users.last_name
                # Resulting SQL: (users.first_name || %s)

                # Numeric addition
                next_age = users.age + 1
                # Resulting SQL: (users.age + %s)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob + value

    def __radd__(self, value):
        """
        Implement right-side addition (`value + self`) for a Column.

        This method is called when a :class:`Column` instance appears on the right
        side of a ``+`` operator (e.g., ``'prefix' + users.name``). It creates a
        new :class:`ColumnsOperation` instance associated with this column,
        initializes its internal SQL fragment to the column's qualified name, and
        then delegates the addition to the operation's ``__add__`` (or ``__radd__``)
        method, which handles the actual SQL generation based on the left operand's
        type.

        The result is a :class:`ColumnsOperation` that can be used in queries,
        conditions, or further chained operations.

        Args:
            value (Any): The left operand of the addition. Can be a string,
                number, :class:`Column`, or :class:`ColumnsOperation`. The type
                determines how the SQL expression is constructed (string
                concatenation for strings, arithmetic addition for numbers,
                etc.).

        Returns:
            ColumnsOperation: A new operation representing the addition of
                ``value`` and this column. This operation can be used in SQL
                expressions or comparisons.

        Example:
            Using right addition to concatenate a prefix with a column::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a 'username' column
                expr = 'User: ' + users.username
                # expr is a ColumnsOperation representing
                # (%s || users.username) with parameter 'User: '
                # This can be used in a SELECT or WHERE clause.

                # Using with a numeric column:
                expr = 10 + users.age
                # expr is a ColumnsOperation representing
                # (%s + users.age) with parameter 10
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value + temp_ob

    def __sub__(self, value):
        """
        Implement subtraction between a column and another value.

        This method is called when the ``-`` operator is used with a :class:`Column`
        instance on the left side. It creates a new :class:`ColumnsOperation`
        instance initialized with the column's name, then delegates the subtraction
        to that operation's ``__sub__`` method, which generates the appropriate SQL
        expression.

        The result is a :class:`ColumnsOperation` that represents the subtraction
        operation, allowing further chaining of operations.

        Args:
            value (ColumnsOperation, Column, int, float, Any): The right-hand side
                of the subtraction. The type determines how the SQL is generated:

                - If a :class:`ColumnsOperation`, the SQL fragments are combined
                with a minus sign.
                - If a :class:`Column`, the column name is used directly.
                - If an ``int`` or ``float``, a placeholder ``%s`` is used and
                the value is added to the parameters list.
                - Any other type is treated as a literal value.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the subtraction expression. Its ``_output`` attribute contains the
            SQL fragment and parameter list.

        Example:
            Subtracting a constant from a column::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a column `age`
                result = users.age - 5
                # result._output[0] -> '(users.age - %s)'
                # result._output[1] -> [5]

                # Subtracting another column
                result = users.current_age - users.birth_year
                # result._output[0] -> '(users.current_age - users.birth_year)'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob - value

    def __rsub__(self, value):
        """
        Implement right-side subtraction (`other - self`) for a column.

        This method is called when a :class:`Column` instance appears on the right
        side of the ``-`` operator (e.g., ``100 - users.age``). It creates a
        :class:`ColumnsOperation` instance from the column and then performs
        a subtraction operation where the left operand is ``value`` and the
        right operand is the column's expression.

        The returned :class:`ColumnsOperation` object contains the generated
        SQL fragment and the parameter list, which can be used in queries.

        Args:
            value (ColumnsOperation, Column, int, float, Any): The left operand
                of the subtraction. Its type determines how the SQL expression
                is constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the subtraction operation between ``value`` and this column.

        Example:
            Using a column in a right-side subtraction::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                op = 100 - users.age
                # op is a ColumnsOperation representing (100 - users.age)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value - temp_ob

    def __mul__(self, value):
        """
        Implement multiplication (`self * other`) for a column.

        This method is called when a :class:`Column` instance is multiplied by
        another value using the ``*`` operator. It creates a :class:`ColumnsOperation`
        instance from the column and then performs a multiplication operation
        where the column is the left operand and ``value`` is the right operand.

        The returned :class:`ColumnsOperation` object contains the generated
        SQL fragment and the parameter list, which can be used in queries.

        Args:
            value (ColumnsOperation, Column, int, float, Any): The right operand
                of the multiplication. Its type determines how the SQL expression
                is constructed. If it is a :class:`ColumnsOperation` or :class:`Column`,
                its SQL fragment is used directly; otherwise, a placeholder ``%s``
                is used and the value is added to the parameter list.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the multiplication operation between this column and ``value``.

        Example:
            Using a column in a multiplication expression::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `salary` column
                op = users.salary * 1.1
                # op is a ColumnsOperation representing (users.salary * %s)
                # with parameter 1.1
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob * value

    def __rmul__(self, value):
        """
        Implement right-side multiplication (`other * self`) for a column.

        This method is called when a :class:`Column` instance appears on the right
        side of the ``*`` operator (e.g., ``100 * users.age``). It creates a
        :class:`ColumnsOperation` instance from the column and then performs a
        multiplication operation where the left operand is ``value`` and the
        right operand is the column's expression.

        The returned :class:`ColumnsOperation` object contains the generated
        SQL fragment and the parameter list, which can be used in queries.

        Args:
            value (ColumnsOperation, Column, int, float, Any): The left operand
                of the multiplication. Its type determines how the SQL expression
                is constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the multiplication operation between ``value`` and this column.

        Example:
            Using a column in a right-side multiplication::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                op = 2 * users.age
                # op is a ColumnsOperation representing (2 * users.age)
        """ 
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value * temp_ob

    def __pow__(self, value):
        """
        Implement the exponentiation operator (`**`) for a column.

        This method is called when a :class:`Column` instance is used with the
        ``**`` operator (e.g., ``users.age ** 2``). It creates a
        :class:`ColumnsOperation` instance from the column and then invokes
        the corresponding ``__pow__`` method of that operation with the provided
        value. The resulting :class:`ColumnsOperation` object contains the SQL
        fragment using the ``POW()`` function and the associated parameters.

        The exponentiation is performed using the SQL ``POW(base, exponent)``
        function. The base is the column expression, and the exponent is the
        given value (which may be a constant, another column, or a complex
        expression).

        Args:
            value (ColumnsOperation, Column, int, float, Any): The exponent to
                raise the column to. Its type determines how the SQL expression
                is constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the exponentiation operation between this column and the given value.

        Example:
            Using the exponentiation operator on a numeric column::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                op = users.age ** 2
                # op is a ColumnsOperation representing POW(users.age, %s)
                # with parameter [2]

                # Using a column as exponent
                op = users.age ** users.experience
                # op represents POW(users.age, users.experience)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob ** value

    def __rpow__(self, value):
        """
        Implement right-side exponentiation (`value ** self`) for a column.

        This method is called when a :class:`Column` instance appears on the right
        side of the ``**`` operator (e.g., ``2 ** users.age``). It creates a
        :class:`ColumnsOperation` instance from the column and delegates the
        actual SQL generation to the operation's ``__rpow__`` method.

        The returned :class:`ColumnsOperation` object contains the generated
        SQL fragment using the ``POW()`` function and the parameter list,
        which can be used in queries.

        Args:
            value (Any): The left operand (the base) for the exponentiation.
                This can be a constant, another column, or a
                :class:`ColumnsOperation` expression.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing
            the power operation between ``value`` and this column.

        Example:
            Using a column in a right-side exponentiation::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                op = 2 ** users.age
                # op is a ColumnsOperation representing POW(%s, users.age)
                # with parameter 2
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob ** value

    def __truediv__(self, value):
        """
        Implement division (`self / value`) for a column.

        This method is called when a :class:`Column` instance is divided by a value
        using the ``/`` operator. It creates a :class:`ColumnsOperation` instance
        from the column and then performs a division operation where the column's
        expression is the numerator and ``value`` is the denominator.

        The returned :class:`ColumnsOperation` object contains the generated SQL
        fragment (using the ``/`` operator) and the parameter list, which can be
        used in queries.

        Args:
            value (ColumnsOperation, Column, int, float, Any): The right operand
                (denominator) of the division. Its type determines how the SQL
                expression is constructed:
                - If a :class:`ColumnsOperation`, its SQL fragment and parameters
                are merged.
                - If a :class:`Column`, its name is used directly.
                - Otherwise, a placeholder ``%s`` is used and the value is added
                to the parameter list.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the division operation between this column and ``value``.

        Example:
            Using a column in a division::

                from ormophine.Mysql import Table

                # Assume `products` is a Table instance with `price` and `quantity` columns
                # Calculate price per unit
                op = products.price / products.quantity
                # op is a ColumnsOperation representing (products.price / products.quantity)

                # Division by a literal
                op = products.total / 100
                # op._output[0] -> '(products.total / %s)'
                # op._output[1] -> [100]
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob / value

    def __rtruediv__(self, value):
        """
        Implement right-side true division (`other / self`) for a column.

        This method is called when a :class:`Column` instance appears on the right
        side of the ``/`` operator (e.g., ``100 / users.age``). It creates a
        :class:`ColumnsOperation` instance from the column and then performs
        a division operation where the left operand is ``value`` and the right
        operand is the column's expression.

        The returned :class:`ColumnsOperation` object contains the generated
        SQL fragment and the parameter list, which can be used in queries.

        Args:
            value (ColumnsOperation, Column, int, float, Any): The left operand
                of the division. Its type determines how the SQL expression
                is constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the division operation between ``value`` and this column.

        Example:
            Using a column in a right-side division::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                op = 100 / users.age
                # op is a ColumnsOperation representing (100 / users.age)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value / temp_ob

    def __mod__(self, value):
        """
        Implement the modulo operator (`%`) for a column.

        This method is called when a :class:`Column` instance is used with the
        ``%`` operator (e.g., ``users.age % 2``). It creates a
        :class:`ColumnsOperation` instance that represents the SQL modulo
        operation. The resulting expression can be used in queries, WHERE
        clauses, or as part of larger expressions.

        Args:
            value (ColumnsOperation, Column, int, float, Any): The right-hand
                operand of the modulo operation. Its type determines how the
                SQL expression is constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the modulo operation between this column and the provided value.

        Example:
            Using the modulo operator to filter even ages::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                condition = users.age % 2 == 0
                # condition is a ColumnsOperation representing (users.age % 2) = %s
                # with parameter 0

            Using modulo in a column expression::

                op = users.age % 10
                # op is a ColumnsOperation representing (users.age % 10)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob % value

    def __rmod__(self, value):
        """
        Implement right-side modulo (`other % self`) for a column.

        This method is called when a :class:`Column` instance appears on the right
        side of the ``%`` operator (e.g., ``5 % users.age``). It creates a
        :class:`ColumnsOperation` instance from the column and then performs
        a modulo operation where the left operand is ``value`` and the right
        operand is the column's expression.

        The returned :class:`ColumnsOperation` object contains the generated
        SQL fragment and the parameter list, which can be used in queries.

        Args:
            value (ColumnsOperation, Column, int, float, Any): The left operand
                of the modulo operation. Its type determines how the SQL expression
                is constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the modulo operation between ``value`` and this column.

        Example:
            Using a column in a right-side modulo::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                op = 10 % users.age
                # op is a ColumnsOperation representing (10 % users.age)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value % temp_ob

    def eq(self, value):
        """
        Create an equality comparison expression for this column.

        This method generates a SQL equality condition where this column is compared
        to the provided value. It returns a :class:`ColumnsOperation` object that
        contains the SQL fragment and the associated parameters.

        The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, its SQL fragment is used on
        the right side, and its parameters are merged.
        - If ``value`` is a :class:`Column`, its fully qualified name is used directly,
        and no additional parameters are added.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is used,
        and the value is added to the parameter list.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                equality comparison. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the equality condition ``self.name = value``.

        Example:
            Assuming a :class:`Table` instance ``users`` with a column ``id``::

                # Compare with a literal value
                condition = users.id.eq(42)
                # condition._output[0] -> '(users.id = %s)'
                # condition._output[1] -> [42]

                # Compare with another column
                condition = users.id.eq(orders.user_id)
                # condition._output[0] -> '(users.id = orders.user_id)'
                # condition._output[1] -> []

                # Compare with a ColumnsOperation (e.g., subquery or expression)
                subquery = users.id > 100
                condition = users.id.eq(subquery)
                # condition._output[0] -> '(users.id = (users.id > %s))'
                # condition._output[1] -> [100]
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} = {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} = {value.name})', []) if isinstance(value, Column) else (f'({self.name} = %s)', [value])
        return temp_ob

    def __eq__(self, value):
        """
        Implement equality comparison (`self == value`) for a column.

        This method is called when a :class:`Column` instance is used with the
        ``==`` operator. It creates a :class:`ColumnsOperation` instance that
        represents an equality condition between the column and the provided value.
        The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, the condition is
        ``column == operation``, and its SQL fragment and parameters are used.
        - If ``value`` is a :class:`Column`, the condition is
        ``column == other_column``, and both column names are used directly.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        The returned :class:`ColumnsOperation` object contains the generated
        SQL fragment and parameter list, which can be used in queries.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                equality comparison. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the equality condition between this column and ``value``.

        Example:
            Using equality comparison in a query::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `name` column
                condition = users.name == 'Alice'
                # condition is a ColumnsOperation with SQL: '(users.name = %s)'
                # and parameters: ['Alice']

                # Comparing two columns
                condition = users.id == users.manager_id
                # SQL: '(users.id = users.manager_id)'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} = {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} = {value.name})', []) if isinstance(value, Column) else (f'({self.name} = %s)', [value])
        return temp_ob

    def ne(self, value):
        """
        Create a not-equal comparison expression.

        This method generates a SQL inequality operation between the column
        and the provided value. It returns a :class:`ColumnsOperation` instance
        that can be used in WHERE clauses or combined with other conditions.
        The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, the column is compared
        to the SQL expression of that operation, and parameters are merged.
        - If ``value`` is a :class:`Column`, the comparison uses the column
        name directly, with no additional parameters.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added as a parameter.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                not-equal comparison. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the inequality ``self.name != value``.

        Example:
            Comparing a column to a literal value::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                condition = users.age.ne(25)
                # condition._output[0] -> '(users.age != %s)'
                # condition._output[1] -> [25]

            Comparing two columns::

                condition = users.age.ne(users.max_age)
                # condition._output[0] -> '(users.age != users.max_age)'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} != {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} != {value.name})', []) if isinstance(value, Column) else (f'({self.name} != %s)', [value])
        return temp_ob

    def __ne__(self, value):
        """
        Implement the not‑equal comparison operator (`!=`) for a column.

        This method is called when a :class:`Column` instance is used with the
        ``!=`` operator (e.g., ``users.age != 25``). It creates a
        :class:`ColumnsOperation` object that represents the SQL inequality
        condition. The right‑hand side can be a constant value, another column,
        or a more complex expression (e.g., a :class:`ColumnsOperation` instance).

        The returned :class:`ColumnsOperation` contains the generated SQL
        fragment (with placeholders for parameters) and a list of parameter
        values, which can be used in queries like :meth:`Table.get_row` or
        :meth:`Table.update`.

        Args:
            value (ColumnsOperation, Column, Any): The right‑hand side of the
                inequality comparison. Its type determines how the SQL expression
                is constructed:
                - If it is a :class:`ColumnsOperation`, its SQL fragment is used
                directly, and its parameters are merged.
                - If it is a :class:`Column`, the column name is used directly,
                with no additional parameters.
                - For any other type (e.g., int, float, str), a placeholder
                ``%s`` is used, and the value is added to the parameter list.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the inequality condition ``self != value``, ready for use in SQL
            queries.

        Example:
            Using the ``!=`` operator to filter rows::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                condition = users.age != 30
                # condition is a ColumnsOperation representing (users.age != %s)
                # with parameter [30]

                # Comparing two columns
                condition = users.age != users.max_age
                # condition is a ColumnsOperation representing (users.age != users.max_age)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} != {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} != {value.name})', []) if isinstance(value, Column) else (f'({self.name} != %s)', [value])
        return temp_ob

    def gt(self, value):
        """
        Create a greater-than comparison expression for the column.

        This method generates a SQL ``>`` (greater than) operation between the
        column and the provided value. It returns a :class:`ColumnsOperation`
        instance containing the SQL fragment and parameters, which can be used in
        queries (e.g., :meth:`Table.get_row`, :meth:`Table.update`).

        The right-hand side ``value`` can be:
        - A :class:`ColumnsOperation` (complex expression or subquery)
        - A :class:`Column` (another column, for column-to-column comparison)
        - A constant (int, float, str, etc.), which will be parameterized.

        Args:
            value (ColumnsOperation, Column, Any): The right-hand side of the
                greater-than comparison. Its type determines how the SQL
                expression is constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the condition ``self > value``, ready for use in SQL queries.

        Example:
            Comparing a column to a constant::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                condition = users.age.gt(18)
                # condition._output[0] -> '(users.age > %s)'
                # condition._output[1] -> [18]

                # Comparing two columns
                condition = users.age.gt(users.min_age)
                # condition._output[0] -> '(users.age > users.min_age)'

                # Using with a ColumnsOperation
                avg_age = (users.age + users.age2) / 2
                condition = users.age.gt(avg_age)
                # condition._output[0] -> '(users.age > ((users.age + users.age2) / 2))'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} > {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} > {value.name})', []) if isinstance(value, Column) else (f'({self.name} > %s)', [value])
        return temp_ob

    def __gt__(self, value):
        """
        Implement the greater‑than comparison operator (`>`) for a column.

        This method is called when a :class:`Column` instance is used with the
        ``>`` operator (e.g., ``users.age > 25``). It creates a
        :class:`ColumnsOperation` object that represents the SQL greater‑than
        condition. The right‑hand side can be a constant value, another column,
        or a more complex expression (e.g., a :class:`ColumnsOperation` instance).

        The returned :class:`ColumnsOperation` contains the generated SQL
        fragment (with placeholders for parameters) and a list of parameter
        values, which can be used in queries like :meth:`Table.get_row` or
        :meth:`Table.update`.

        Args:
            value (ColumnsOperation, Column, Any): The right‑hand side of the
                greater‑than comparison. Its type determines how the SQL expression
                is constructed:
                - If it is a :class:`ColumnsOperation`, its SQL fragment is used
                directly, and its parameters are merged.
                - If it is a :class:`Column`, the column name is used directly,
                with no additional parameters.
                - For any other type (e.g., int, float, str), a placeholder
                ``%s`` is used, and the value is added to the parameter list.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the condition ``self > value``, ready for use in SQL queries.

        Example:
            Using the ``>`` operator to filter rows::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                condition = users.age > 30
                # condition is a ColumnsOperation representing (users.age > %s)
                # with parameter [30]

                # Comparing two columns
                condition = users.age > users.min_age
                # condition is a ColumnsOperation representing (users.age > users.min_age)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} > {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} > {value.name})', []) if isinstance(value, Column) else (f'({self.name} > %s)', [value])
        return temp_ob

    def lt(self, value):
        """
        Create a less‑than comparison expression for this column.

        This method generates a SQL ``<`` (less‑than) condition between the column
        and the provided value. It creates a :class:`ColumnsOperation` object
        containing the SQL fragment and parameter list, which can be used in
        queries such as :meth:`Table.get_row` or :meth:`Table.update`.

        The right‑hand side can be a constant, another column, or a more complex
        expression. The behavior depends on the type of ``value``:

        - If ``value`` is a :class:`ColumnsOperation`, its SQL fragment is used
        directly, and its parameters are merged with the column's (none).
        - If ``value`` is a :class:`Column`, the column name is used directly,
        with no additional parameters.
        - For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        Args:
            value (ColumnsOperation, Column, Any): The right‑hand side of the
                less‑than comparison. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the condition ``self < value``, ready for use in SQL queries.

        Example:
            Filtering rows where age is less than 30::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                condition = users.age.lt(30)
                # condition represents: users.age < %s with parameter [30]

                # Comparing two columns
                condition = users.age.lt(users.max_age)
                # condition represents: users.age < users.max_age
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} < {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} < {value.name})', []) if isinstance(value, Column) else (f'({self.name} < %s)', [value])
        return temp_ob

    def __lt__(self, value):
        """
        Implement the less‑than comparison operator (`<`) for a column.

        This method is called when a :class:`Column` instance is used with the
        ``<`` operator (e.g., ``users.age < 25``). It creates a
        :class:`ColumnsOperation` object that represents the SQL less‑than
        condition. The right‑hand side can be a constant value, another column,
        or a more complex expression (e.g., a :class:`ColumnsOperation` instance).

        The returned :class:`ColumnsOperation` contains the generated SQL
        fragment (with placeholders for parameters) and a list of parameter
        values, which can be used in queries like :meth:`Table.get_row` or
        :meth:`Table.update`.

        Args:
            value (ColumnsOperation, Column, Any): The right‑hand side of the
                less‑than comparison. Its type determines how the SQL expression
                is constructed:
                - If it is a :class:`ColumnsOperation`, its SQL fragment is used
                directly, and its parameters are merged.
                - If it is a :class:`Column`, the column name is used directly,
                with no additional parameters.
                - For any other type (e.g., int, float, str), a placeholder
                ``%s`` is used, and the value is added to the parameter list.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the less‑than condition ``self < value``, ready for use in SQL queries.

        Example:
            Using the ``<`` operator to filter rows::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                condition = users.age < 30
                # condition is a ColumnsOperation representing (users.age < %s)
                # with parameter [30]

                # Comparing two columns
                condition = users.age < users.max_age
                # condition is a ColumnsOperation representing (users.age < users.max_age)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} < {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} < {value.name})', []) if isinstance(value, Column) else (f'({self.name} < %s)', [value])
        return temp_ob

    def ge(self, value):
        """
        Create a greater‑than‑or‑equal comparison expression.

        This method generates a SQL ``>=`` operation between the column and the
        provided value. It creates a new :class:`ColumnsOperation` instance
        containing the SQL fragment and parameter list. The behavior depends on
        the type of ``value``:

        * If ``value`` is a :class:`ColumnsOperation`, its SQL fragment and
        parameters are used directly.
        * If ``value`` is a :class:`Column`, the column name is used directly,
        and no additional parameters are added.
        * For any other type (e.g., int, float, str), a placeholder ``%s`` is
        used, and the value is added to the parameter list.

        Args:
            value (ColumnsOperation, Column, Any): The right‑hand side of the
                comparison. Its type determines how the SQL expression and
                parameters are constructed.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the condition ``self >= value``, ready for use in queries.

        Example:
            Using the ``ge`` method to filter rows::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                condition = users.age.ge(18)
                # condition is a ColumnsOperation representing (users.age >= %s)
                # with parameter [18]

                # Comparing two columns
                condition = users.age.ge(users.min_age)
                # condition is a ColumnsOperation representing (users.age >= users.min_age)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} >= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} >= {value.name})', []) if isinstance(value, Column) else (f'({self.name} >= %s)', [value])
        return temp_ob

    def __ge__(self, value):
        """
        Implement the greater-than-or-equal comparison operator (`>=`) for a column.

        This method is called when a :class:`Column` instance is used with the
        ``>=`` operator (e.g., ``users.age >= 18``). It creates a
        :class:`ColumnsOperation` object that represents the SQL condition
        ``self >= value``. The right‑hand side can be a constant value,
        another column, or a more complex expression (a :class:`ColumnsOperation`
        instance). The returned object contains the generated SQL fragment and
        the associated parameter list, suitable for use in queries like
        :meth:`Table.get_row` or :meth:`Table.update`.

        Args:
            value (ColumnsOperation, Column, Any): The right‑hand side of the
                comparison. Its type determines how the SQL expression is built:
                - If it is a :class:`ColumnsOperation`, its SQL fragment is used
                directly, and its parameters are merged.
                - If it is a :class:`Column`, the column name is used directly,
                with no additional parameters.
                - For any other type (e.g., int, float, str), a placeholder
                ``%s`` is used, and the value is added to the parameter list.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the condition ``self >= value``, ready for use in SQL queries.

        Example:
            Using the ``>=`` operator to filter rows::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                condition = users.age >= 18
                # condition is a ColumnsOperation representing (users.age >= %s)
                # with parameter [18]

                # Comparing two columns
                condition = users.age >= users.min_age
                # condition is a ColumnsOperation representing (users.age >= users.min_age)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} >= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} >= {value.name})', []) if isinstance(value, Column) else (f'({self.name} >= %s)', [value])
        return temp_ob

    def le(self, value):
        """
        Create a less-than-or-equal comparison expression for the column.

        This method generates a SQL condition representing ``self <= value``.
        It creates a :class:`ColumnsOperation` object that contains the SQL
        fragment (with placeholders as needed) and the associated parameter list.
        The right‑hand side can be a constant, another column, or a complex
        expression (a :class:`ColumnsOperation` instance).

        Args:
            value (ColumnsOperation, Column, Any): The right‑hand side of the
                comparison. The behavior depends on the type:
                - :class:`ColumnsOperation`: its SQL fragment is used directly,
                and its parameters are merged with the current ones.
                - :class:`Column`: the column name is used directly; no additional
                parameters.
                - Other (e.g., int, float, str): a placeholder ``%s`` is inserted,
                and the value is added to the parameter list.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the condition ``self <= value``, ready for use in SQL queries.

        Example:
            Filtering rows where age is at most 30::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                condition = users.age.le(30)
                # condition._output[0] -> '(users.age <= %s)'
                # condition._output[1] -> [30]

                # Comparing two columns
                condition = users.age.le(users.max_age)
                # condition._output[0] -> '(users.age <= users.max_age)'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} <= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} <= {value.name})', []) if isinstance(value, Column) else (f'({self.name} <= %s)', [value])
        return temp_ob

    def __le__(self, value):
        """
        Implement the less-than-or-equal comparison operator (`<=`) for a column.

        This method is called when a :class:`Column` instance is used with the
        ``<=`` operator (e.g., ``users.age <= 30``). It creates a
        :class:`ColumnsOperation` object that represents the SQL condition
        ``self <= value``. The right‑hand side can be a constant value,
        another column, or a more complex expression (a :class:`ColumnsOperation`
        instance). The returned object contains the generated SQL fragment and
        the associated parameter list, suitable for use in queries like
        :meth:`Table.get_row` or :meth:`Table.update`.

        Args:
            value (ColumnsOperation, Column, Any): The right‑hand side of the
                comparison. Its type determines how the SQL expression is built:
                - If it is a :class:`ColumnsOperation`, its SQL fragment is used
                directly, and its parameters are merged (though in this case,
                the left side is the column and the right side is the operation).
                - If it is a :class:`Column`, the column name is used directly,
                with no additional parameters.
                - For any other type (e.g., int, float, str), a placeholder
                ``%s`` is used, and the value is added to the parameter list.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the condition ``self <= value``, ready for use in SQL queries.

        Example:
            Using the ``<=`` operator to filter rows::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `age` column
                condition = users.age <= 30
                # condition is a ColumnsOperation representing (users.age <= %s)
                # with parameter [30]

                # Comparing two columns
                condition = users.age <= users.max_age
                # condition is a ColumnsOperation representing (users.age <= users.max_age)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} <= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} <= {value.name})', []) if isinstance(value, Column) else (f'({self.name} <= %s)', [value])
        return temp_ob

    def __getitem__(self, key: slice):
        """
        Just like python string slicing , implement Python's slice syntax (`column[start:stop]`) to generate SQL substring expressions.

        This method enables string column slicing using Python's bracket notation, converting
        the slice indices into a SQL ``SUBSTRING()`` function call. The behavior mimics Python
        string slicing with support for positive, negative, and omitted indices, but is
        translated to SQL's 1‑based indexing and parameterised placeholders.

        The returned :class:`ColumnsOperation` object contains the generated SQL fragment
        and the associated parameter list, ready for use in queries.

        The mapping from Python slice semantics to SQL is as follows:

        - `col[:]` → ``SUBSTRING(col, 1, LENGTH(col) + 1)`` (returns the whole string,
        though the +1 is a quirk of the implementation)
        - `col[:stop]` with `stop >= 0` → ``SUBSTRING(col, 1, stop)``
        - `col[:stop]` with `stop < 0` → ``SUBSTRING(col, 1, LENGTH(col) - abs(stop))``
        - `col[start:]` with `start >= 0` → ``SUBSTRING(col, start + 1, LENGTH(col))``
        - `col[start:]` with `start < 0` → ``SUBSTRING(col, LENGTH(col) - abs(start) - 1, LENGTH(col))``
        - `col[start:stop]` with `start >= 0, stop > 0` → ``SUBSTRING(col, start + 1, stop - start)``
        - `col[start:stop]` with `start >= 0, stop < 0` → ``SUBSTRING(col, start + 1, LENGTH(col) - abs(stop - start))``
        - Other combinations follow similar logic with adjustments for 1‑based indexing and length computations.

        Args:
            key (slice): A Python slice object with optional ``start``, ``stop``, and
                ``step`` attributes. The ``step`` is ignored (not supported in SQL
                SUBSTRING). The indices are interpreted as character positions.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the substring expression, with its ``_output`` attribute set to
            ``(sql_fragment, parameters)``.

        Raises:
            None: This method does not raise exceptions directly, though invalid
            slice types (non‑slice) would result in an error at runtime.

        Example:
            Slicing a string column to get the first 3 characters::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `name` column
                op = users.name[:3]
                # op._output[0] -> 'SUBSTRING(users.name , 1 , %s)'
                # op._output[1] -> [3]

                # Slicing from the 2nd character to the 5th
                op = users.name[1:5]
                # op._output[0] -> 'SUBSTRING(users.name , %s , %s)'
                # op._output[1] -> [2, 4]  # start=2 (1-based), length=4

                # Negative stop: exclude last 2 characters
                op = users.name[:-2]
                # op._output[0] -> 'SUBSTRING(users.name , 1 , LENGTH(users.name) - %s)'
                # op._output[1] -> [2]  # abs(stop)
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
        """
        Just like python strip(), generate a SQL expression that trims both leading and trailing characters from a column.

        This method applies the SQL ``TRIM(BOTH ... FROM ...)`` function to the
        column, removing all leading and trailing occurrences of the specified
        characters. The result is a :class:`ColumnsOperation` object that can be
        used in queries, updates, or further chained operations.

        Args:
            chars (str, optional): A string of characters to remove from both
                ends of the column value. Defaults to a single space ``' '``.
                If multiple characters are provided, each is treated as a separate
                character to be stripped.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance whose SQL
            fragment represents the trimmed column, and whose parameter list is
            empty (since the character set is embedded in the SQL). This object
            can be used directly in queries or further manipulated.

        Example:
            Removing leading/trailing spaces from a ``username`` column::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `username` column
                trimmed = users.username.strip()
                # trimmed._output[0] -> "TRIM(BOTH ' ' FROM users.username)"
                # trimmed._output[1] -> []

                # Using with a condition
                rows = users.get_row(
                    which_columns=[users.id, users.username],
                    where=users.username.strip() == 'admin'
                )
                # This generates SQL: ... WHERE TRIM(BOTH ' ' FROM users.username) = %s

                # Strip other characters, e.g., underscores
                trimmed_underscore = users.username.strip('_')
                # trimmed_underscore._output[0] -> "TRIM(BOTH '_' FROM users.username)"
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"TRIM(BOTH '{chars}' FROM {temp_ob._output[0]})", temp_ob._output[1]) if temp_ob._output else (f"TRIM(BOTH '{chars}' FROM {temp_ob.col_obj.name})", [])
        return temp_ob

    def lstrip(self, chars: str = ' '):
        """
        Just like python lstrip(), generate a SQL expression that trims leading characters from a column value.

        This method applies the SQL ``TRIM(LEADING ... FROM ...)`` function to the
        column, removing all leading occurrences of the specified characters from
        the column's value. The result is a :class:`ColumnsOperation` object that
        can be used in queries, updates, or combined with other operations.

        The method creates a new :class:`ColumnsOperation` instance wrapping the
        column, then updates its internal ``_output`` with the SQL fragment and
        parameter list. The operation is chainable with other :class:`ColumnsOperation`
        methods.

        Args:
            chars (str, optional): A string of characters to remove from the
                leading end of the column value. If multiple characters are
                provided, each is treated as a separate character to be stripped.
                Defaults to a single space ``' '``.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the left‑trim operation on the column. The operation's SQL fragment
            will be something like ``TRIM(LEADING ' ' FROM column_name)``, and
            its parameter list will be empty (since the character set is inlined
            in the SQL).

        Example:
            Using ``lstrip()`` to remove leading spaces from a name column::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `name` column
                op = users.name.lstrip()
                # op._output[0] -> "TRIM(LEADING ' ' FROM users.name)"
                # op._output[1] -> []

                # Remove leading '@' characters
                op = users.username.lstrip('@')
                # op._output[0] -> "TRIM(LEADING '@' FROM users.username)"

                # Combine with other operations
                op = users.name.upper().lstrip()
                # op._output[0] -> "TRIM(LEADING ' ' FROM UPPER(users.name))"
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"TRIM(LEADING '{chars}' FROM {temp_ob._output[0]})", temp_ob._output[1]) if temp_ob._output else (f"TRIM(LEADING '{chars}' FROM {temp_ob.col_obj.name})", [])
        return temp_ob

    def rstrip(self, chars: str = ' '):
        """
        Just like python rstrip(), generate a SQL expression that trims trailing characters from a string column.

        This method applies the SQL ``TRIM(TRAILING ... FROM ...)`` function to
        the column, removing all trailing occurrences of the specified characters.
        The method returns a new :class:`ColumnsOperation` object that contains
        the generated SQL fragment and the associated parameter list.

        Args:
            chars (str, optional): A string of characters to remove from the
                trailing end of the column value. Defaults to a single space ``' '``.
                If multiple characters are provided, each is treated as a separate
                character to be stripped.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing
            the right‑trim operation, ready to be used in queries or chained
            with other operations.

        Example:
            Using ``rstrip`` to remove trailing spaces from a column::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `name` column
                op = users.name.rstrip()
                # op._output[0] -> "TRIM(TRAILING ' ' FROM users.name)"

                # Removing trailing '@' characters
                op = users.username.rstrip('@')
                # op._output[0] -> "TRIM(TRAILING '@' FROM users.username)"
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"TRIM(TRAILING '{chars}' FROM {temp_ob._output[0]})", temp_ob._output[1]) if temp_ob._output else (f"TRIM(TRAILING '{chars}' FROM {temp_ob.col_obj.name})", [])
        return temp_ob

    def add_end(self, content):
        """
        Generate a SQL expression that concatenates content to the end of this column.

        This method creates a :class:`ColumnsOperation` that represents the SQL
        string concatenation operation ``column || content``. It is intended for
        string columns and requires the MySQL ``PIPES_AS_CONCAT`` SQL mode to be
        enabled (the driver sets this automatically). The behavior depends on the
        type of ``content``:

        - If ``content`` is a :class:`ColumnsOperation`, its SQL fragment is used
        and its parameters are merged.
        - If ``content`` is a :class:`Column`, the column name is used directly,
        with no additional parameters.
        - For any other type (e.g., str, int), a placeholder ``%s`` is used, and
        the value is added to the parameter list.

        Args:
            content (ColumnsOperation, Column, Any): The content to append to the
                column. Its type determines how the SQL expression is built.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the concatenation expression, ready for use in queries.

        Example:
            Concatenating a space and a last name to a first name column::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with `first_name` and `last_name` columns
                full_name = users.first_name.add_end(' ').add_end(users.last_name)
                # full_name._output[0] -> '((users.first_name || %s) || users.last_name)'
                # full_name._output[1] -> [' ']
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} || {content._output[0]})', [content._output[1]]) if isinstance(content, ColumnsOperation) else (f'({self.name} || {content.name})', []) if isinstance(content, Column) else (f'({self.name} || %s)', [content])
        return temp_ob

    def add_first(self, content):
        """
        Generate a SQL expression that prepends content to the column's value.

        This method creates a string concatenation operation using the SQL ``||``
        operator, placing the provided ``content`` before the current column's
        value. The returned :class:`ColumnsOperation` object contains the generated
        SQL fragment and the associated parameter list, suitable for use in queries.

        The behavior depends on the type of ``content``:

        * If ``content`` is a :class:`ColumnsOperation`, its SQL fragment is used
        as the left operand, and its parameters are included.
        * If ``content`` is a :class:`Column`, its name is used directly, and no
        additional parameters are added.
        * For any other type (e.g., str, int), a placeholder ``%s`` is used, and
        the value is added to the parameter list.

        This method is intended for string columns. The SQL mode must have
        ``PIPES_AS_CONCAT`` enabled for ``||`` to perform concatenation.

        Args:
            content (ColumnsOperation, Column, Any): The content to prepend to
                the column's value. Its type determines how the SQL expression
                and parameters are constructed.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing
            the concatenation operation, ready to be used in queries or chained
            with other operations.

        Example:
            Prepending a prefix to a column value::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `name` column
                op = users.name.add_first('Mr. ')
                # op._output[0] -> '(%s || users.name)'
                # op._output[1] -> ['Mr. ']

                # Prepending another column
                op = users.first_name.add_first(users.title)
                # op._output[0] -> '(users.title || users.first_name)'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({content._output[0]} || {self.name})', [content._output[1]]) if isinstance(content, ColumnsOperation) else (f'({content.name} || {self.name})', []) if isinstance(content, Column) else (f'(%s || {self.name})', [content])
        return temp_ob
    
    def lower(self):
        """
        Just like python lower(), generate a SQL expression that converts the column value to lowercase.

        This method applies the SQL ``LOWER()`` function to the column, transforming
        all characters in the string value to lowercase. The method returns a new
        :class:`ColumnsOperation` object that contains the generated SQL fragment
        and the associated parameter list (which is empty for this operation).

        The returned object can be used in queries, conditions, or chained with
        other operations.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing
            the lowercase operation, ready to be used in SQL queries.

        Example:
            Using ``lower()`` to perform a case‑insensitive comparison::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `name` column
                condition = users.name.lower() == 'alice'
                # condition._output[0] -> '(LOWER(users.name) = %s)'
                # condition._output[1] -> ['alice']

                # Using in a query
                rows = users.get_row(
                    which_columns=[users.id, users.name],
                    where=condition
                )
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'LOWER({temp_ob._output[0]})', temp_ob._output[1]) if temp_ob._output else (f'LOWER({temp_ob.col_obj.name})', [])
        return temp_ob

    def upper(self):
        """
        Just like python upper() , generate a SQL expression that converts the column value to uppercase.

        This method applies the SQL ``UPPER()`` function to the column,
        transforming all characters to their uppercase equivalent. It is
        typically used for case‑insensitive comparisons or formatting.

        The method returns a new :class:`ColumnsOperation` object that
        contains the generated SQL fragment and the associated parameter list.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing
            the uppercase transformation, ready to be used in queries or
            chained with other operations.

        Example:
            Using ``upper`` to convert a column to uppercase in a query::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `name` column
                op = users.name.upper()
                # op._output[0] -> 'UPPER(users.name)'

                # Using in a WHERE clause
                condition = users.name.upper() == 'ALICE'
                # condition._output[0] -> '(UPPER(users.name) = %s)'
                # condition._output[1] -> ['ALICE']
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'UPPER({temp_ob._output[0]})', temp_ob._output[1]) if temp_ob._output else (f'UPPER({temp_ob.col_obj.name})', [])
        return temp_ob

    def replace(self, old, new):
        """
        Just like python replace(), generate a SQL REPLACE operation on the column.

        This method creates a :class:`ColumnsOperation` that represents the SQL
        ``REPLACE()`` function, which replaces all occurrences of a substring
        within the column's value with a new substring. The operation is applied
        to the column directly, and the returned object can be used in queries
        or chained with other operations.

        Args:
            old (str): The substring to be replaced.
            new (str): The substring to replace with.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing
            the ``REPLACE()`` function call, e.g.,
            ``REPLACE(column_name, %s, %s)``, with the appropriate parameters.

        Example:
            Replacing all occurrences of 'old' with 'new' in a column::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `bio` column
                op = users.bio.replace('old_text', 'new_text')
                # op._output[0] -> 'REPLACE(users.bio, %s, %s)'
                # op._output[1] -> ['old_text', 'new_text']
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'REPLACE({temp_ob._output[0]} , %s , %s)', temp_ob._output[1] + [old, new]) if temp_ob._output else (f'REPLACE({temp_ob.col_obj.name} , %s , %s)', [old, new])
        return temp_ob

    def like(self, value):
        """
        Generate a SQL ``LIKE`` condition for pattern matching on a string column.

        This method creates a :class:`ColumnsOperation` object that represents a
        SQL ``LIKE`` expression, allowing pattern-based filtering on string columns.
        The right‑hand side can be a constant string pattern, another column, or a
        more complex expression (a :class:`ColumnsOperation` instance). The method
        automatically converts the provided value to a string for safe parameter
        substitution.

        Args:
            value (ColumnsOperation, Column, Any): The pattern to match against
                the column. Its type determines how the SQL expression is built:
                - If it is a :class:`ColumnsOperation`, its SQL fragment is used
                directly, and its parameters are merged.
                - If it is a :class:`Column`, the column name is used directly,
                with no additional parameters.
                - For any other type (e.g., int, float, str), the value is
                converted to a string and a placeholder ``%s`` is used, with
                the value added to the parameter list.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the ``LIKE`` condition ``self LIKE value``, ready for use in SQL
            queries.

        Example:
            Using the ``like`` method to perform pattern matching::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `name` column
                # Find users whose name starts with 'A'
                condition = users.name.like('A%')
                # condition is a ColumnsOperation representing (users.name like %s)
                # with parameter ['A%']

                # Using another column as the pattern
                condition = users.name.like(users.pattern_column)
                # condition is a ColumnsOperation representing (users.name like users.pattern_column)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"{self.name} like {value._output[0]}", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f'{self.name} like {value.name}', temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f'{self.name} like %s', (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def startswith(self, value):
        """
        Just like python startswith(), generate a SQL ``LIKE`` condition that checks if the column starts with a given prefix.

        This method creates a :class:`ColumnsOperation` object that represents a SQL
        expression of the form ``column LIKE 'prefix%'``, which matches rows where
        the column value begins with the specified prefix. The prefix can be a
        constant string, another column, or a complex expression.

        The method automatically constructs the pattern by appending the SQL
        wildcard ``%`` to the provided prefix, ensuring that the condition
        matches any value that starts with the given string.

        Args:
            value (ColumnsOperation, Column, Any): The prefix to match at the start
                of the column's value. Its type determines how the SQL expression
                is built:
                - If it is a :class:`ColumnsOperation`, its SQL fragment is used
                directly, and its parameters are merged.
                - If it is a :class:`Column`, the column name is used directly,
                with no additional parameters.
                - For any other type (e.g., str, int), the value is converted to
                a string and a placeholder ``%s`` is used, with the value added
                to the parameter list. The pattern becomes ``%s || '%%'``.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the ``LIKE`` condition, ready to be used in queries or chained with
            other operations.

        Example:
            Using ``startswith`` to find users whose names begin with 'A'::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `name` column
                condition = users.name.startswith('A')
                # condition._output[0] -> 'users.name like %s || '%%''
                # condition._output[1] -> ['A']

                # Using another column as the prefix
                condition = users.name.startswith(users.prefix_column)
                # condition._output[0] -> 'users.name like users.prefix_column || '%%''
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"{self.name} like {value._output[0]} || '%%'", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self.name} like {value.name} || '%%'", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"{self.name} like %s || '%%'", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def endswith(self, value):
        """
        Just like python endswith(), generate a SQL condition that checks if a string column ends with a given suffix.

        This method creates a :class:`ColumnsOperation` object that represents a
        SQL ``LIKE`` expression with the pattern ``'%%' || value``, which matches
        strings that end with the specified suffix. The right‑hand side can be a
        constant string, another column, or a more complex expression (a
        :class:`ColumnsOperation` instance). The method automatically converts
        the provided value to a string for safe parameter substitution.

        Args:
            value (ColumnsOperation, Column, Any): The suffix to check against
                the column. Its type determines how the SQL expression is built:
                - If it is a :class:`ColumnsOperation`, its SQL fragment is used
                directly, and its parameters are merged.
                - If it is a :class:`Column`, the column name is used directly,
                with no additional parameters.
                - For any other type (e.g., int, float, str), the value is
                converted to a string and a placeholder ``%s`` is used, with
                the value added to the parameter list.

        Returns:
            ColumnsOperation: A new :class:`ColumnsOperation` instance representing
            the condition ``self LIKE '%%' || value``, ready for use in SQL queries.

        Example:
            Using ``endswith`` to filter rows whose column ends with a pattern::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `email` column
                condition = users.email.endswith('@example.com')
                # condition._output[0] -> "users.email like '%%' || %s"
                # condition._output[1] -> ['@example.com']

                # Using another column as the suffix
                condition = users.email.endswith(users.domain)
                # condition._output[0] -> "users.email like '%%' || users.domain"
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"{self.name} like '%%' || {value._output[0]}", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self.name} like '%%' || {value.name}", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"{self.name} like '%%' || %s", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def contains(self, value):
        """
        Generate a SQL condition that checks if a string column contains a substring.

        This method creates a :class:`ColumnsOperation` object representing a
        SQL ``LIKE`` condition with wildcards on both sides of the pattern:
        ``column LIKE '%value%'``. This checks whether the column's value contains
        the specified substring anywhere within it. The right‑hand side can be a
        constant string, another column, or a more complex expression.

        The method automatically handles the wildcard concatenation in the SQL
        expression, so you do not need to add ``%`` characters manually.

        Args:
            value (ColumnsOperation, Column, Any): The substring to search for
                within the column. Its type determines how the SQL expression is
                built:
                - If it is a :class:`ColumnsOperation`, its SQL fragment is used
                directly, and its parameters are merged.
                - If it is a :class:`Column`, the column name is used directly,
                with no additional parameters.
                - For any other type (e.g., int, float, str), the value is
                converted to a string and a placeholder ``%s`` is used, with
                the value added to the parameter list.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing
            the ``LIKE`` condition with wildcards on both sides, ready for use
            in SQL queries.

        Example:
            Using ``contains`` to find rows where a column contains a substring::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with a `name` column
                # Find users whose name contains 'smith'
                condition = users.name.contains('smith')
                # condition._output[0] -> "users.name like '%%' || %s || '%%'"
                # condition._output[1] -> ['smith']

                # Using another column as the pattern
                condition = users.name.contains(users.search_term)
                # condition._output[0] -> "users.name like '%%' || users.search_term || '%%'"
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"{self.name} like '%%' || {value._output[0]} || '%%'", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self.name} like '%%' || {value.name} || '%%'", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"{self.name} like '%%' || %s || '%%'", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def rename(self, column: 'Column', new_name: str) -> None:
        """
        Rename an existing column in the table.

        This method renames a column by executing an ``ALTER TABLE ... CHANGE COLUMN``
        statement. It first retrieves the full data type definition of the column
        (including any attributes like ``NOT NULL``, ``DEFAULT``, etc.) from the
        table's schema using :meth:`~Table.get_table_info`. Then it constructs and
        executes the SQL command to rename the column to the new name while preserving
        its data type and all constraints.

        After the database schema is updated, the method also updates the table
        object's dynamic attributes: it deletes the attribute corresponding to the
        old column name and creates a new attribute with the new name, maintaining
        a consistent Python representation of the table structure.

        Args:
            column (Column): The :class:`Column` object representing the column
                to be renamed. This object must belong to the current table.
            new_name (str): The new name for the column. Must be a valid SQL
                identifier (e.g., no spaces or special characters, unless properly
                quoted).

        Returns:
            None

        Raises:
            Exception: If the underlying SQL execution fails (e.g., the column does
                not exist, the new name conflicts with an existing column,
                insufficient privileges, or a database error). The original error
                and the executed query are included in the exception message.

        Example:
            Renaming a column from ``'old_name'`` to ``'new_name'``::

                # Assume `users` is a Table instance
                old_col = users.old_name
                users.rename(old_col, 'new_name')
                # Now the column is accessible as users.new_name

            Note that after renaming, the old attribute is removed::

                # This would raise AttributeError
                users.old_name
        """
        for col_info in self.table_obj.get_table_info():
            if col_info['name'] == column.first_name[1:-1]:
                full_type = col_info['full_type']  
                break
        query = f'ALTER TABLE {self.table_obj.name_} CHANGE COLUMN {column.first_name} `{new_name}` {full_type};'
        self.table_obj._exc(query)
        self.table_obj.__delattr__(column.first_name[1:-1])
        self.table_obj.__setattr__(new_name, Column(self.table_obj, new_name, column.datatype))

    def delete_column(self, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool) -> None:
        """
        Permanently delete this column from the table.

        This method executes an ``ALTER TABLE ... DROP COLUMN`` statement to remove
        the column from the database. To prevent accidental deletion, three explicit
        confirmation flags are required. All three must be ``True`` for the operation
        to proceed. After successful deletion, the column attribute is also removed
        from the parent :class:`Table` object.

        Args:
            are_you_sure (bool): First-level confirmation flag.
            are_you_really_sure (bool): Second-level confirmation flag.
            for_sure (bool): Final confirmation flag.

        Returns:
            None

        Raises:
            Exception: If the underlying SQL execution fails (e.g., insufficient
                privileges or the column does not exist). The original error and
                query are included in the exception message.

        Example:
            Assuming a :class:`Column` instance named ``users.age`` attached to a
            :class:`Table` instance ``users``::

                # Danger: this deletes the 'age' column
                users.age.delete_column(True, True, True)

            If any flag is ``False``, nothing happens::

                users.age.delete_column(True, True, False)  # No effect
        """
        if are_you_sure and are_you_really_sure and for_sure:
            query = f'ALTER TABLE {self.table_obj.name_} DROP COLUMN {self.first_name};'
            self.table_obj._exc(query)
            self.table_obj.__delattr__(self.first_name[1:-1])

    def In(self, value):
        """
        Generate an SQL ``IN`` condition or fall back to equality for a column.

        This method creates a :class:`ColumnsOperation` object that represents
        either an ``IN`` clause (when a list, tuple, or subquery is provided) or
        an equality comparison (when a single value is given). The behavior
        depends on the type of ``value``:

        * If ``value`` is a :class:`ColumnsOperation`, it is treated as a subquery
        or set expression, and the SQL fragment becomes
        ``<column> IN (<subquery>)``.
        * If ``value`` is a ``list`` or ``tuple``, an ``IN`` clause with
        placeholders is generated: ``<column> IN (%s, %s, ...)``, and all
        items are added as parameters.
        * For any other single value, the method falls back to an equality
        condition: ``<column> = %s``.

        The returned :class:`ColumnsOperation` contains the generated SQL
        fragment and the associated parameter list, ready for use in queries
        like :meth:`Table.get_row` or :meth:`Table.update`.

        Args:
            value (ColumnsOperation, list, tuple, Any): The right‑hand side of
                the condition. If a :class:`ColumnsOperation`, it is used as a
                subquery. If a list or tuple, it provides the set of values for
                the ``IN`` clause. Otherwise, the method generates an equality
                condition.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance representing
            the ``IN`` or equality condition, with its internal ``_output``
            attribute updated accordingly.

        Example:
            Using the ``In`` method to filter rows based on a list of values::

                from ormophine.Mysql import Table

                # Assume `users` is a Table instance with an `id` column
                condition = users.id.In([1, 2, 3])
                # condition._output[0] -> 'users.id IN (%s,%s,%s)'
                # condition._output[1] -> [1, 2, 3]

                # Using a subquery (e.g., select IDs from another table)
                subquery = other_table.id.gt(10)  # this returns a ColumnsOperation
                condition = users.id.In(subquery)
                # condition._output[0] -> 'users.id IN (other_table.id > %s)'
                # condition._output[1] -> [10]
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"{self.name} IN ({value._output[0]})",value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self.name} IN ({','.join(['%s'] * len(value))})",list(value)) if isinstance(value, (list, tuple)) else (f"{self.name} = %s",[value])
        return temp_ob


class BatchOperation:
    """
    Accumulate multiple SQL INSERT and UPDATE statements for batch execution.

    This class provides a mechanism to collect several database operations
    (inserts and updates) and execute them together in a single transaction.
    This is useful for improving performance by reducing round‑trips to the
    database and ensuring atomicity (all operations succeed or fail as a group).

    The class maintains an internal script list of queries and their associated
    parameters. Queries are added using the :meth:`update` and :meth:`insert`
    methods, and then executed with the :meth:`run` method. Each operation can
    involve complex :class:`ColumnsOperation` expressions, making it suitable
    for dynamic SQL generation.

    Attributes:
        script (list): A list where each element is a list or tuple representing
            a query and its parameters. For parameterized queries, the entry is
            ``[query_string, parameter_list]``. For queries without parameters,
            it is simply ``[query_string]``.
        table_obj (Table): The :class:`Table` instance associated with this
            batch operation. This is used to execute the queries via the
            underlying driver's ``_excs`` method.

    Example:
        Creating a batch operation with a mix of insert and update statements::

            from ormophine.Mysql import Table, Driver

            # Assume `db` is a Driver instance connected to a database
            users = db.users

            # Create a batch object
            batch = users.batch()

            # Add an update: increase age by 1 for users whose name starts with 'A'
            condition = users.name.startswith('A')
            batch.update(
                update={users.age: users.age + 1},
                where=condition
            )

            # Add an insert: create a new user
            batch.insert(
                insert={users.name: 'BatchUser', users.age: 25}
            )

            # Add another update using a ColumnsOperation (e.g., set email to full_name + '@domain.com')
            batch.update(
                update={users.email: users.first_name.add_end('@domain.com')},
                where=users.id > 100
            )

            # Execute all batched statements atomically
            batch.run()

        This ensures that either all three operations are applied to the
        database, or none are applied if an error occurs.
    """
    def __init__(self, table_object: Table):
        """
        Initialize a new BatchOperation instance.

        This constructor sets up a batch operation builder for the given table.
        The batch operation allows multiple SQL statements (e.g., updates and
        inserts) to be collected into a single script and executed together
        via the :meth:`run` method. The internal ``script`` list stores the
        queued operations.

        Args:
            table_object (Table): The :class:`Table` instance on which the
                batch operations will be performed. This table is used as
                the default target for operations unless overridden in the
                individual methods.

        Returns:
            None

        Example:
            Creating a batch operation for a table and adding updates::

                from ormophine.Mysql import Table, BatchOperation

                # Assume `users` is a Table instance
                batch = BatchOperation(users)
                batch.update({'age': users.age + 1}, where=users.id == 1)
                batch.insert({'name': 'Bob', 'age': 30})
                batch.run()  # Executes both statements in a single transaction
        """
        self.script = []
        self.table_obj = table_object

    def update(self, update: dict[Column, Any], where: ColumnsOperation, table: Table = None) -> 'BatchOperation':
        """
        Add an UPDATE operation to the batch script.

        This method appends an UPDATE statement to the internal batch script,
        which will be executed when :meth:`run` is called. The update can set
        column values to constants, other columns, or SQL expressions (via
        :class:`ColumnsOperation`). The WHERE clause is mandatory and must be
        a :class:`ColumnsOperation` expression.

        The method supports complex update expressions, such as arithmetic
        operations, string concatenations, and function calls, by accepting
        :class:`ColumnsOperation` objects as values in the ``update`` dict.

        Args:
            update (dict[Column, Any]): A dictionary mapping :class:`Column`
                objects to new values. Each value can be:
                - A constant (e.g., int, str, float) → uses a placeholder.
                - A :class:`Column` object → uses the column name directly.
                - A :class:`ColumnsOperation` object → uses its SQL fragment
                and merges its parameters.
            where (ColumnsOperation): A condition expression (e.g., using
                comparisons and logical operators) that determines which rows
                are updated.
            table (Table, optional): An alternative table to update. If not
                provided, the table associated with this :class:`BatchOperation`
                instance is used.

        Returns:
            BatchOperation: The same instance, allowing method chaining.

        Raises:
            Exception: If the generated SQL is invalid or the database operation
                fails during :meth:`run`. The error message includes the offending
                query and parameters.

        Example:
            Batch update with complex expressions::

                from ormophine.Mysql import BatchOperation, Table, Column

                # Assume `users` is a Table instance with columns: id, name, age, score
                batch = users.batch()

                # Update age to age + 1 and score to score * 2 for users older than 18
                condition = users.age > 18
                batch.update(
                    update={
                        users.age: users.age + 1,  # Arithmetic expression
                        users.score: users.score * 2,
                        users.name: users.name.add_end(' (updated)')  # String concatenation
                    },
                    where=condition
                )

                # Also update another table in the same batch
                # batch.update(..., table=another_table)

                batch.run()  # Execute all batched operations
        """
        temp_list= []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        self.script.append([f'UPDATE {table.name_ if table else self.table_obj.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=%s' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1]])
        return self

    def insert(self, insert: dict[Column, Any], table: Table = None) -> 'BatchOperation':
        """
        Add an INSERT operation to the batch script.

        This method appends an INSERT statement to the internal batch script,
        which can later be executed as a single transaction using :meth:`run`.
        The operation will insert a single row into the target table. The columns
        and their corresponding values are provided as a dictionary mapping
        :class:`Column` objects to values. The table to insert into can be
        specified explicitly; if omitted, the table associated with this
        :class:`BatchOperation` instance is used.

        Args:
            insert (dict[Column, Any]): A dictionary where keys are :class:`Column`
                objects representing the columns to insert, and values are the
                corresponding values to insert. Values are added to the parameter
                list for safe SQL execution.
            table (Table, optional): The target :class:`Table` to insert into.
                If not provided, the table that was passed to the
                :class:`BatchOperation` constructor is used. Defaults to ``None``.

        Returns:
            BatchOperation: The same instance, with the INSERT operation appended
            to its internal script. This enables method chaining for building
            complex batch operations.

        Example:
            Building a batch insert for multiple rows::

                from ormophine.Mysql import BatchOperation

                # Assume `users` is a Table instance with columns: id, name, age
                batch = users.batch()

                # Insert a single row
                batch.insert({users.name: 'Alice', users.age: 30})

                # Insert another row, specifying a different table
                batch.insert({logs.message: 'User created'}, table=logs)

                # Execute all batched operations
                batch.run()
        """
        self.script.append([f'INSERT INTO {table.name_ if table else self.table_obj.name_} ({', '.join(i.first_name for i in list(insert.keys()))}) VALUES ({', '.join(f'%s' for k in insert)})' , [v for v in list(insert.values())]])
        return self

    def delete_row(self, where: ColumnsOperation, table: Table = None) -> 'BatchOperation':
        """
        Add a DELETE operation to the batch script.

        This method appends a DELETE statement to the internal batch script,
        which will be executed when :meth:`run` is called. The WHERE clause is
        mandatory and must be a :class:`ColumnsOperation` expression. Optionally,
        a different table can be specified as the target.

        Args:
            where (ColumnsOperation): A condition expression (e.g., using
                comparisons and logical operators) that determines which rows
                are deleted.
            table (Table, optional): An alternative table to delete from. If not
                provided, the table associated with this :class:`BatchOperation`
                instance is used.

        Returns:
            BatchOperation: The same instance, allowing method chaining.

        Raises:
            Exception: If the generated SQL is invalid or the database operation
                fails during :meth:`run`. The error message includes the offending
                query and parameters.

        Example:
            Batch delete with a condition::

                from ormophine.Mysql import BatchOperation

                batch = users.batch()

                # Delete users older than 60
                condition = users.age > 60
                batch.delete(where=condition)

                # Delete from another table in the same batch
                batch.delete(where=logs.timestamp < '2020-01-01', table=logs)

                batch.run()
        """
        self.script.append([f'DELETE FROM {table.name_ if table else self.table_obj.name_} WHERE {where._output[0]};', where._output[1]])
        return self

    def run(self):
        """
        Execute all batched SQL statements in the current batch operation.

        This method submits all accumulated queries (added via :meth:`update` and
        :meth:`insert`) to the database as a single transaction. The statements are
        executed sequentially, and if any statement fails, the entire transaction
        is rolled back. After execution, the internal script list is cleared.

        This method is typically the final step after building a batch with multiple
        :meth:`update` and :meth:`insert` calls. It is useful for reducing round‑trips
        to the database when performing multiple operations that should succeed or
        fail together.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If any SQL statement in the batch fails. The exception message
                includes the original error and the list of failed queries and their
                parameters for debugging. The transaction is rolled back on failure.

        Example:
            Performing a batch operation with an update that uses a complex
            :class:`ColumnsOperation` condition and multiple insertions::

                from ormophine.Mysql import Table, Driver, BatchOperation

                # Assume db is a Driver instance and users is a Table instance
                users = db.users

                # Build a batch operation
                batch = users.batch()

                # Add an update: set age = age + 1 for users whose name starts with 'A'
                condition = users.name.startswith('A')
                batch.update(
                    update={users.age: users.age + 1},
                    where=condition
                )

                # Add an insert: add a new user
                batch.insert(
                    insert={users.name: 'NewUser', users.age: 30}
                )

                # Add another update using a ColumnsOperation value (e.g., set email to full_name + '@domain.com')
                batch.update(
                    update={users.email: users.first_name.add_end('@domain.com')},
                    where=users.id > 100
                )

                # Execute all batched statements
                batch.run()
        """
        self.table_obj._excs(self.script)

