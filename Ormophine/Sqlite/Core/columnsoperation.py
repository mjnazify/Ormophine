from __future__ import annotations
from queue import SimpleQueue

class ColumnsOperation:
    """
    A builder for SQL expressions involving columns and literals.

    Instances of this class represent a SQL expression (e.g., arithmetic
    operations, string concatenations, function calls, or comparison
    conditions) that can be used in ``SELECT``, ``WHERE``, ``UPDATE``,
    or other clauses. The class overloads Python operators (``+``, ``-``,
    ``*``, ``**``, ``/``, ``%``, ``&``, ``|``, comparison operators, and
    subscription) to generate corresponding SQL syntax.

    The expression state is stored in the ``_output`` attribute as a tuple
    ``(sql_string, parameters)``, where ``sql_string`` is the raw SQL
    fragment (with placeholders ``?``) and ``parameters`` is a list of
    parameter values for safe query execution. Most methods mutate the
    instance in‑place and return ``self``, enabling method chaining.

    Typical usage starts from a :class:`Column` instance, which creates a
    new ``ColumnsOperation`` object. Operations can then be chained:

    .. code-block:: python

        name = users.name
        expr = (name + ' (active)').upper().startswith('A')
        # expr._output[0] -> "(upper((users.[name] || ?)) like ? || '%')"
        # expr._output[1] -> [' (active)', 'A']

    The resulting expression can be passed to methods like
    :meth:`Table.get_row` or :meth:`Table.update` as a condition or
    computed value.

    Attributes:
        col_obj (Column): The underlying :class:`Column` object that this
            operation is derived from. This is used to determine datatype
            (e.g., whether ``+`` should be string concatenation or
            arithmetic addition) and to provide context.
        _output (tuple[str, list]): A 2‑tuple containing the SQL string
            with placeholders and the list of parameter values. This is
            the internal representation of the expression.
    """

    def __init__(self, col_obj):
        """Initialize a new ColumnsOperation instance.

        This class is used to build SQL expressions involving column operations
        (arithmetic, string concatenation, function calls, comparisons, etc.)
        in a chainable manner. It is typically created indirectly via the
        :class:`Column` class's operator overloads (e.g., ``col + 5``, ``col * 2``)
        or by calling methods like :meth:`Column.upper()`.

        The instance stores the generated SQL expression and its parameter list
        in the ``_output`` attribute as a tuple ``(sql_string, param_list)``.
        Initially, before any operation is applied, ``_output`` is set to an
        empty string, but most methods will overwrite it.

        Args:
            col_obj (Column): The column object that this operation is associated
                with. This is used to determine the column's data type (which
                influences whether ``+`` is mapped to SQL ``+`` or ``||``) and
                to provide a fallback column name when no operation has been
                applied yet.

        Example:
            This class is not meant to be instantiated directly. Instead, use
            column operators::

                from ormophine.Sqlite import Driver, Table

                db = Driver('my.db')
                users = db.users
                name_col = users.name

                # This creates a ColumnsOperation internally:
                expr = name_col.upper().startswith('A')
                # expr._output -> ("upper(users.[name]) like ? || '%'", ['A'])

            In the example above, ``name_col.upper()`` returns a
            :class:`ColumnsOperation` object, and subsequent chained calls
            modify its ``_output`` accordingly.
        """        
        self._output = '' # To apply operations in a chained manner
        self.col_obj = col_obj
        self.current_datatype = col_obj.datatype

    def __add__(self, other):
        """Add a value or expression to the current column expression.

        This method implements the ``+`` operator for :class:`ColumnsOperation`.
        The behavior depends on the column's datatype:

        * If the column's datatype is ``str``, SQL string concatenation is used (``||``).
        * Otherwise, arithmetic addition (``+``) is used.

        The method supports adding:

        * Another :class:`ColumnsOperation` – both expressions are combined.
        * A :class:`Column` – the column's name is used as the right operand.
        * An ``int`` or ``float`` literal – a parameter placeholder (``?``) is used.
        * A ``str`` literal – a parameter placeholder is used for string concatenation.

        The result is stored in the instance's ``_output`` attribute as a tuple
        ``(sql_string, parameters)``, and the instance is returned to allow
        chaining.

        Args:
            other: The value or expression to add. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - ``int`` or ``float``
                - ``str``

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the addition. This allows method chaining.

        Example:
            Assuming a ``products`` table with columns ``price`` (``REAL``) and
            ``name`` (``TEXT``)::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price
                name = products.name

                # Arithmetic addition for numeric column
                expr1 = price + 10
                # expr1._output[0] -> "(products.[price] + ?)"
                # expr1._output[1] -> [10]

                # String concatenation for text column
                expr2 = name + ' (discounted)'
                # expr2._output[0] -> "(products.[name] || ?)"
                # expr2._output[1] -> [' (discounted)']

                # Combining two expressions
                expr3 = (price + 5) + (price * 2)
                # expr3._output[0] -> "((products.[price] + ?) + (products.[price] * ?))"
                # expr3._output[1] -> [5, 2]
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} {'||' if (self.current_datatype == str) or (other.current_datatype == str) else '+'} {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} {'||' if (self.current_datatype == str) or (other.datatype == str) else '+'} {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} {'||' if (self.current_datatype == str) else '+'} ?)', self._output[1]+[other]) if isinstance(other, int) or isinstance(other , float) else (f'({self._output[0]} || ?)', self._output[1]+[other if isinstance(other, str) else str(other)])
        new_op.current_datatype = str if (isinstance(other, ColumnsOperation) and other.current_datatype == str) or (isinstance(other, Column) and other.datatype == str) or self.current_datatype == str or ( not isinstance(other, ColumnsOperation) and not isinstance(other,Column) and not isinstance(other, int) and not isinstance(other, float)) else self.current_datatype
        return new_op

    def __radd__(self, other):
        """Implement reflected addition for SQL expression generation.

        This method is invoked when the left operand does not support addition
        with a :class:`ColumnsOperation` object, i.e., when evaluating
        ``other + self``. It builds a SQL expression representing the addition
        or concatenation of the right-hand side (this operation) with the
        left-hand side operand.

        The SQL operator used depends on the data type of the associated column:

        * For string columns (:attr:`~Column.datatype` is ``str``), the
        concatenation operator ``||`` is used.
        * For numeric columns (e.g., ``int``, ``float``), the arithmetic
        addition operator ``+`` is used.

        The method supports multiple types for ``other``:

        * A :class:`ColumnsOperation` – the SQL expression from that object is
        combined with this one.
        * A :class:`Column` – the column name is used as the left operand.
        * A literal (``int``, ``float``, ``str``) – the literal is used as a
        parameterised value (``?``) in the final query.

        The method updates the internal ``_output`` attribute of the current
        instance to hold the resulting SQL fragment and its parameter list,
        then returns the instance for chaining.

        Args:
            other: The left-hand operand. Can be one of:
                - :class:`ColumnsOperation`: a pre‑built expression.
                - :class:`Column`: a database column.
                - A literal of type ``int``, ``float``, or ``str``.

        Returns:
            :class:`ColumnsOperation`: The same instance (``self``), with its
            ``_output`` updated to represent the SQL expression
            ``(other + self)`` or ``(other || self)``.

        Example:
            Assuming a ``Product`` table with columns ``name`` (string) and
            ``price`` (numeric)::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                name_col = products.name
                price_col = products.price

                # Right addition with a literal (triggers __radd__)
                expr1 = 'Mr. ' + name_col
                # expr1._output[0] -> "(? || products.[name])"
                # expr1._output[1] -> ['Mr. ']

                # Numeric right addition
                expr2 = 100 + price_col
                # expr2._output[0] -> "(? + products.[price])"
                # expr2._output[1] -> [100]

                # Right addition with another ColumnsOperation
                expr3 = (price_col * 2) + name_col
                # expr3._output[0] -> "((products.[price] * ?) + products.[name])"
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} {'||' if (self.current_datatype == str) or (other.current_datatype == str) else '+'} {self._output[0]})', other._output[1]+self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} {'||' if (self.current_datatype == str) or (other.datatype == str) else '+'} {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? {'||' if (self.current_datatype == str) else '+'} {self._output[0]})', [other]+self._output[1]) if isinstance(other, int) or isinstance(other , float) else (f'(? || {self._output[0]})', [other if isinstance(other, str) else str(other)]+self._output[1])
        new_op.current_datatype = str if (isinstance(other, ColumnsOperation) and other.current_datatype == str) or (isinstance(other, Column) and other.datatype == str) or self.current_datatype == str or ( not isinstance(other, ColumnsOperation) and not isinstance(other,Column) and not isinstance(other, int) and not isinstance(other, float)) else self.current_datatype
        return new_op

    def __sub__(self, other):
        """Subtract a value or expression from the current column expression.

        This method implements the ``-`` operator for :class:`ColumnsOperation`,
        generating a SQL subtraction expression. The method supports subtracting:

        * Another :class:`ColumnsOperation` – both expressions are subtracted.
        * A :class:`Column` – the column's name is used as the right operand.
        * A literal (``int``, ``float``, etc.) – a parameter placeholder (``?``)
        is used.

        The result is stored in the instance's ``_output`` attribute as a tuple
        ``(sql_string, parameters)``, and the instance is returned to allow
        chaining.

        Args:
            other: The value or expression to subtract. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - ``int``, ``float``, or any numeric literal

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the subtraction. This allows method chaining.

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price
                discount = products.discount

                # Subtract a literal
                expr1 = price - 10
                # expr1._output[0] -> "(products.[price] - ?)"
                # expr1._output[1] -> [10]

                # Subtract another column
                expr2 = price - discount
                # expr2._output[0] -> "(products.[price] - products.[discount])"

                # Combine with other expressions
                expr3 = (price - 5) - (discount * 2)
                # expr3._output[0] -> "((products.[price] - ?) - (products.[discount] * ?))"
                # expr3._output[1] -> [5, 2]
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} - {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} - {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} - ?)', self._output[1]+[other])
        return new_op

    def __rsub__(self, other):
        """Implement reverse subtraction for the column expression.

        This method is called when the left operand does not support subtraction
        (e.g., ``int - Column``). It generates a SQL subtraction expression
        where the other value is subtracted from the current column expression.
        The operator used is always ``-``, regardless of the column's datatype
        (subtraction is only meaningful for numeric types).

        The method supports:

        * Another :class:`ColumnsOperation` – the other expression is the left
        operand, and the current expression is the right operand.
        * A :class:`Column` – the other column's value is subtracted from the
        current expression.
        * A literal (``int``, ``float``, etc.) – the literal is used as a
        parameter placeholder.

        The result is stored in the instance's ``_output`` attribute as a tuple
        ``(sql_string, parameters)``, and the instance is returned to allow
        chaining.

        Args:
            other: The value or expression to subtract from. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - ``int``, ``float``, or other numeric literal

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the reverse subtraction. This allows method
            chaining.

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Reverse subtraction: 100 - price
                expr = 100 - price
                # expr._output[0] -> "(? - products.[price])"
                # expr._output[1] -> [100]

                # Using in a query
                condition = (100 - price) > 50
                # condition._output[0] -> "((? - products.[price]) > ?)"
                # condition._output[1] -> [100, 50]
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} - {self._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} - {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? - {self._output[0]})', [other]+self._output[1])
        return new_op

    def __mul__(self, other):
        """Multiply the current column expression by a value or expression.

        This method implements the ``*`` operator for :class:`ColumnsOperation`.
        It generates a SQL multiplication expression using the ``*`` operator.
        The method supports:

        * Another :class:`ColumnsOperation` – both expressions are multiplied.
        * A :class:`Column` – the column's name is used as the right operand.
        * A numeric literal (``int`` or ``float``) – a parameter placeholder
        (``?``) is used for the literal.

        The result is stored in the instance's ``_output`` attribute as a tuple
        ``(sql_string, parameters)``, and the instance is returned to allow
        chaining.

        Args:
            other: The value or expression to multiply by. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - ``int`` or ``float``

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the multiplication. This allows method chaining.

        Example:
            Assuming a ``products`` table with a ``price`` column (``REAL``)::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Multiply by a literal
                expr1 = price * 1.2
                # expr1._output[0] -> "(products.[price] * ?)"
                # expr1._output[1] -> [1.2]

                # Multiply by another column
                tax_rate = products.tax_rate
                expr2 = price * tax_rate
                # expr2._output[0] -> "(products.[price] * products.[tax_rate])"

                # Combine with other operations
                expr3 = (price + 10) * 0.9
                # expr3._output[0] -> "((products.[price] + ?) * ?)"
                # expr3._output[1] -> [10, 0.9]
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} * {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} * {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} * ?)', self._output[1]+[other])
        return new_op

    def __rmul__(self, other):
        """Implement reflected multiplication for the column expression.

        This method handles the case where a numeric value or another expression
        appears on the left side of the ``*`` operator and the
        :class:`ColumnsOperation` appears on the right (e.g., ``3 * expr``).
        It generates a SQL multiplication expression (``*``) with the operands
        in the correct order.

        The method supports:

        * Another :class:`ColumnsOperation` – both expressions are multiplied.
        * A :class:`Column` – the column's name is used as the left operand.
        * An ``int`` or ``float`` literal – a parameter placeholder (``?``) is used.

        The result is stored in the instance's ``_output`` attribute as a tuple
        ``(sql_string, parameters)``, and the instance is returned to allow
        chaining.

        Args:
            other: The value or expression to multiply by. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - ``int`` or ``float``

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the reflected multiplication. This allows
            method chaining.

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Reflected multiplication: numeric literal on the left
                expr1 = 3 * price
                # expr1._output[0] -> "(? * products.[price])"
                # expr1._output[1] -> [3]

                # Reflected multiplication with another expression
                expr2 = (price + 5) * (price * 2)
                # expr2._output[0] -> "((products.[price] + ?) * (products.[price] * ?))"
                # expr2._output[1] -> [5, 2]

                # Use in a query to calculate discounted price
                discounted = 0.9 * price
                # discounted._output[0] -> "(? * products.[price])"
                # discounted._output[1] -> [0.9]
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} * {self._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} * {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? * {self._output[0]})', [other]+self._output[1])
        return new_op

    def __pow__(self, other):
        """Raise the column expression to a power using SQL exponentiation.

        This method implements the ``**`` operator for :class:`ColumnsOperation`.
        It generates a SQL expression using the exponentiation operator ``**``,
        which is supported by SQLite (and other databases) for numeric exponentiation.

        The method supports three types of operands:

        * Another :class:`ColumnsOperation` – both expressions are combined with ``**``.
        * A :class:`Column` – the column's name is used as the exponent.
        * A literal (``int`` or ``float``) – a parameter placeholder (``?``) is used.

        The result is stored in the instance's ``_output`` attribute as a tuple
        ``(sql_string, parameters)``, and the instance is returned to allow
        chaining.

        Args:
            other: The exponent value or expression. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - ``int`` or ``float``

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the exponentiation. This allows method chaining.

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Square the price
                expr1 = price ** 2
                # expr1._output[0] -> "(products.[price] ** ?)"
                # expr1._output[1] -> [2]

                # Use another column as exponent
                exponent_col = products.discount
                expr2 = price ** exponent_col
                # expr2._output[0] -> "(products.[price] ** products.[discount])"

                # Combine two expressions
                expr3 = (price + 5) ** (price * 2)
                # expr3._output[0] -> "((products.[price] + ?) ** (products.[price] * ?))"
                # expr3._output[1] -> [5, 2]
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} ** {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} ** {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} ** ?)', self._output[1]+[other])
        return new_op

    def __rpow__(self, other):
        """Implement the reflected (right‑hand side) power operator for column expressions.

        This method handles the case where a value or expression appears on the left
        of the ``**`` operator and the current :class:`ColumnsOperation` is on the right.
        It generates a SQL exponentiation expression of the form ``left ** right``,
        where ``right`` is this column expression. The result updates the instance's
        ``_output`` attribute and returns ``self`` to support chaining.

        The method supports three types of ``other``:

        * A :class:`ColumnsOperation` – both expressions are combined, and their
        parameter lists are merged.
        * A :class:`Column` – the column's name is used as the left operand.
        * A literal (e.g., ``int``, ``float``) – the literal is bound as a parameter
        using a placeholder (``?``) in the SQL string.

        Args:
            other: The left operand of the power operation. Can be one of:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - A numeric literal (``int`` or ``float``)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent ``other ** self``. The ``_output`` attribute is
            a tuple ``(sql_string, parameters)``.

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Using a literal on the left
                expr = 2 ** price
                # expr._output[0] -> "(? ** products.[price])"
                # expr._output[1] -> [2]

                # Using another column
                discount = products.discount
                expr2 = discount ** price
                # expr2._output[0] -> "(products.[discount] ** products.[price])"

                # Using a complex expression on the left
                expr3 = (price + 10) ** price
                # expr3._output[0] -> "((products.[price] + ?) ** products.[price])"
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} ** {self._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} ** {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? ** {self._output[0]})', [other]+self._output[1])
        return new_op

    def __truediv__(self, other):
        """Divide the column expression by a value or expression.

        This method implements the ``/`` (division) operator for
        :class:`ColumnsOperation`. It generates a SQL division expression
        and supports three types of operands:

        * Another :class:`ColumnsOperation` – both expressions are divided.
        * A :class:`Column` – the column's name is used as the divisor.
        * A numeric literal (``int`` or ``float``) – a parameter placeholder (``?``) is used.

        The result is stored in the instance's ``_output`` attribute as a tuple
        ``(sql_string, parameters)``, and the instance is returned to allow
        chaining.

        Args:
            other: The divisor value or expression. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - ``int`` or ``float``

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the division. This allows method chaining.

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Divide price by 2
                expr1 = price / 2
                # expr1._output[0] -> "(products.[price] / ?)"
                # expr1._output[1] -> [2]

                # Divide by another column
                divisor_col = products.discount
                expr2 = price / divisor_col
                # expr2._output[0] -> "(products.[price] / products.[discount])"

                # Divide two composite expressions
                expr3 = (price + 10) / (price * 2)
                # expr3._output[0] -> "((products.[price] + ?) / (products.[price] * ?))"
                # expr3._output[1] -> [10, 2]
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} / {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} / {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} / ?)', self._output[1]+[other])
        return new_op

    def __rtruediv__(self, other):
        """Divide a value by the column expression (reverse division).

        This method implements the reflected (right-hand) division operator for
        :class:`ColumnsOperation`. It is called when a numeric value or column
        appears on the left side of the division operator and the
        :class:`ColumnsOperation` appears on the right (e.g., ``100 / price_expr``).
        The generated SQL uses the division operator ``/``.

        The method supports three types of operands for the left-hand side:

        * Another :class:`ColumnsOperation` – both expressions are combined with ``/``.
        * A :class:`Column` – the column's name is used as the dividend.
        * A literal (``int`` or ``float``) – a parameter placeholder (``?``) is used.

        The result is stored in the instance's ``_output`` attribute as a tuple
        ``(sql_string, parameters)``, and the instance is returned to allow
        chaining.

        Args:
            other: The left-hand side value or expression. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - ``int`` or ``float``

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the reverse division. This allows method chaining.

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price_expr = products.price + 10

                # Reverse division: 100 / (price + 10)
                expr = 100 / price_expr
                # expr._output[0] -> "(? / (products.[price] + ?))"
                # expr._output[1] -> [100, 10]

                # Using another column as the dividend
                discount_col = products.discount
                expr2 = discount_col / price_expr
                # expr2._output[0] -> "(products.[discount] / (products.[price] + ?))"
                # expr2._output[1] -> [10]
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} / {self._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} / {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? / {self._output[0]})', [other]+self._output[1])
        return new_op

    def __mod__(self, other):
        """Apply the modulo operator to the column expression.

        This method implements the ``%`` operator for :class:`ColumnsOperation`.
        It generates a SQL expression using the modulo operator ``%``, which
        computes the remainder of division between the current expression and
        the provided operand.

        The method supports three types of operands:

        * Another :class:`ColumnsOperation` – both expressions are combined with ``%``.
        * A :class:`Column` – the column's name is used as the divisor.
        * A literal (``int`` or ``float``) – a parameter placeholder (``?``) is used.

        The result is stored in the instance's ``_output`` attribute as a tuple
        ``(sql_string, parameters)``, and the instance is returned to allow
        chaining.

        Args:
            other: The divisor value or expression. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - ``int`` or ``float``

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the modulo operation. This allows method chaining.

        Example:
            Assuming a ``products`` table with a ``stock`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                stock = products.stock

                # Check if stock is odd (stock % 2)
                expr = stock % 2
                # expr._output[0] -> "(products.[stock] % ?)"
                # expr._output[1] -> [2]

                # Use another column as divisor
                divisor_col = products.divisor
                expr2 = stock % divisor_col
                # expr2._output[0] -> "(products.[stock] % products.[divisor])"

                # Combine two expressions
                expr3 = (stock + 10) % (stock - 5)
                # expr3._output[0] -> "((products.[stock] + ?) % (products.[stock] - ?))"
                # expr3._output[1] -> [10, 5]
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} % {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} % {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} % ?)', self._output[1]+[other])
        return new_op

    def __rmod__(self, other):
        """Compute the modulo of a value with the column expression (reverse modulo).

        This method implements the reverse ``%`` operator for :class:`ColumnsOperation`.
        It is called when the left operand is not a :class:`ColumnsOperation` (e.g.,
        a literal or another :class:`Column`) and the right operand is this
        expression. The generated SQL uses the modulo operator ``%``.

        The method supports:
        * Another :class:`ColumnsOperation` – the expressions are combined with ``%``
        (left expression modulo right expression).
        * A :class:`Column` – the column's name is used as the left operand.
        * A literal (``int`` or ``float``) – a parameter placeholder (``?``) is used.

        The result is stored in the instance's ``_output`` attribute as a tuple
        ``(sql_string, parameters)``, and the instance is returned to allow chaining.

        Args:
            other: The left operand (value or expression) to be divided by this
                expression. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - ``int`` or ``float``

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the reverse modulo operation. This allows method
            chaining.

        Example:
            Assuming a ``products`` table with a ``stock`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                stock = products.stock

                # Reverse modulo: 100 % stock
                expr = 100 % stock
                # expr._output[0] -> "(? % products.[stock])"
                # expr._output[1] -> [100]

                # Use another column as left operand
                total_col = products.total
                expr2 = total_col % stock
                # expr2._output[0] -> "(products.[total] % products.[stock])"
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} % {self._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} % {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? % {self._output[0]})', [other]+self._output[1])
        return new_op

    def __getitem__(self, key: slice):
        """Implement string slicing on a column expression using SQLite's ``substr``.

        This method allows Python-style slicing (e.g., ``column[1:5]``) on a
        :class:`ColumnsOperation` object. It generates a SQL ``substr`` expression
        that extracts a substring from the column value or from a previously
        constructed expression. The behavior mimics Python string slicing with
        support for positive/negative indices and omitted start/stop values.

        The generated SQL uses SQLite's ``substr(X, Y, Z)`` function, where:
        - The start position is adjusted for 1‑based indexing.
        - Negative indices are converted to ``length(X) - N``.
        - An omitted start defaults to 0 (beginning).
        - An omitted stop defaults to the end of the string.

        The method updates the instance's ``_output`` attribute with a tuple
        ``(sql_string, parameters)`` and returns the instance itself for chaining.

        Args:
            key (slice): A slice object defining the substring range. The
                ``start`` and ``stop`` attributes can be ``None``, positive,
                or negative integers. Negative values count from the end of
                the string.

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the ``substr`` expression. This allows
            additional operations to be chained.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Extract first 3 characters (Python slice 0:3)
                expr = name_col[:3]
                # expr._output[0] -> "substr(users.[name] , 0 , ?)"
                # expr._output[1] -> [3]  # note: SQLite's substr is 1-based,
                # but this ORM adjusts: stop+1 is used, so for 0:3, we get substr(..., 0, 3)
                # Actually this ORM uses 0-based start with substr, so it's fine.

                # Extract from index 1 to 4 (Python slice 1:5)
                expr2 = name_col[1:5]
                # expr2._output[0] -> "substr(users.[name] , ? , ?)"
                # expr2._output[1] -> [2, 4]  # start adjusted to 1-based: 1+1=2, length = 5-1=4

                # Extract last 3 characters (Python slice -3:)
                expr3 = name_col[-3:]
                # expr3._output[0] -> "substr(users.[name] , length(users.[name]) - ? , length(users.[name]))"
                # expr3._output[1] -> [2]  # -3 becomes abs(-3)-1 = 2

                # Use in a query to get initials (first character)
                initial_expr = name_col[0:1]
                results = users.get_row([initial_expr], where=users.id == 1)
                # retrieves the first character of the name for user with id=1
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op.current_datatype = str
        if self._output:
            if key.start == None and key.stop ==  None:
                new_op._output = (f'(substr({self._output[0]} , 0 , length({self._output[0]}) + 1))', self._output[1] + self._output[1])   #
            elif key.start == None and key.stop < 0:
                new_op._output = (f'(substr({self._output[0]} , 0 , length({self._output[0]}) - ?))', self._output[1] + self._output[1] + [abs(key.stop) - 1])  #
            elif key.start == None and key.stop >= 0:
                new_op._output = (f'(substr({self._output[0]} , 0 , ?))', self._output[1] + [key.stop + 1])  #  
            elif key.start >= 0 and key.stop ==  None:
                new_op._output = (f'(substr({self._output[0]} , ? , length({self._output[0]})))', self._output[1] + [key.start + 1] + self._output[1])  #   
            elif key.start < 0 and key.stop == None:
                new_op._output = (f'(substr({self._output[0]} , length({self._output[0]}) - ? , length({self._output[0]})))', self._output[1] + self._output[1] + [abs(key.start) - 1] + self._output[1])  #
            elif key.start >= 0 and key.stop < 0:
                new_op._output = (f'(substr({self._output[0]} , ? , length({self._output[0]}) - ?))', self._output[1] +  [key.start + 1] + self._output[1] + [abs(key.stop - key.start)])  #  
            elif key.start >= 0 and key.stop > 0:
                new_op._output = (f'(substr({self._output[0]} , ? , ?))', self._output[1] + [key.start + 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop < 0:
                new_op._output = (f'(substr({self._output[0]} , length({self._output[0]}) - ? , ?))', self._output[1] + self._output[1] + [abs(key.start) - 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop > 0:
                new_op._output = (f'(substr({self._output[0]} , length({self._output[0]}) - ? ,  ? - (length({self._output[0]}) - ?)))', self._output[1] + self._output[1] + [abs(key.start) - 1, key.stop] + self._output[1] + [abs(key.start)])
        else:
            if key.start == None and key.stop ==  None:
                new_op._output = (f'(substr({self.col_obj.name} , 0 , length({self.col_obj.name}) + 1))', [])   #
            elif key.start == None and key.stop < 0:
                new_op._output = (f'(substr({self.col_obj.name} , 0 , length({self.col_obj.name}) - ?))', [abs(key.stop) - 1])  #
            elif key.start == None and key.stop >= 0:
                new_op._output = (f'(substr({self.col_obj.name} , 0 , ?))', [key.stop + 1])  #  
            elif key.start >= 0 and key.stop ==  None:
                new_op._output = (f'(substr({self.col_obj.name} , ? , length({self.col_obj.name})))', [key.start + 1])  #   
            elif key.start < 0 and key.stop == None:
                new_op._output = (f'(substr({self.col_obj.name} , length({self.col_obj.name}) - ? , length({self.col_obj.name})))', [abs(key.start) - 1])  #
            elif key.start >= 0 and key.stop < 0:
                new_op._output = (f'(substr({self.col_obj.name} , ? , length({self.col_obj.name}) - ?))', [key.start + 1, abs(key.stop - key.start)])  #  
            elif key.start >= 0 and key.stop > 0:
                new_op._output = (f'(substr({self.col_obj.name} , ? , ?))', [key.start + 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop < 0:
                new_op._output = (f'(substr({self.col_obj.name} , length({self.col_obj.name}) - ? , ?))', [abs(key.start) - 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop > 0:
                new_op._output = (f'(substr({self.col_obj.name} , length({self.col_obj.name}) - ? ,  ? - (length({self.col_obj.name}) - ?)))', [abs(key.start) - 1, key.stop, abs(key.start)])
        return new_op

    def eq(self, value):
        """Create an equality comparison condition for the column expression.

        This method generates a SQL equality expression (``=``) between the current
        expression and the provided value. The result is a :class:`ColumnsOperation`
        object that can be used in ``WHERE`` clauses of queries, updates, or deletes.
        This is the named version of the ``__eq__`` operator, allowing explicit
        usage when operator overloading is not desirable.

        The method supports comparisons with:

        * Another :class:`ColumnsOperation` – combines two expressions.
        * A :class:`Column` – compares the expression to a column.
        * A literal (e.g., ``int``, ``str``, ``float``) – uses a parameter placeholder.

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the equality condition. This allows method chaining
            with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``users`` table with columns ``id`` and ``name``::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Use eq to compare with a literal
                condition = name_col.eq('Alice')
                # condition._output[0] -> "(users.[name] = ?)"
                # condition._output[1] -> ['Alice']

                # Compare two columns
                id_col = users.id
                condition2 = name_col.eq(id_col)
                # condition2._output[0] -> "(users.[name] = users.[id])"

                # Chain with AND
                final_condition = condition & (id_col > 10)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} = {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} = {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} = ?)', self._output[1] + [value])
        return new_op

    def __eq__(self, value):
        """Create an equality comparison condition for the column expression.

        This method implements the ``==`` operator for :class:`ColumnsOperation`.
        It generates a SQL equality expression (``=``) between the current
        expression and the provided value. The result is stored in the instance's
        ``_output`` attribute as a tuple ``(sql_string, parameters)``, and the
        instance is returned to allow chaining.

        The method supports comparisons with:

        * Another :class:`ColumnsOperation` – combines two expressions.
        * A :class:`Column` – compares the expression to a column.
        * A literal (e.g., ``int``, ``str``, ``float``) – uses a parameter placeholder.

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the equality condition. This allows method chaining
            with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Compare with a literal using ==
                condition = name_col == 'Alice'
                # condition._output[0] -> "(users.[name] = ?)"
                # condition._output[1] -> ['Alice']

                # Compare two columns
                id_col = users.id
                condition2 = name_col == id_col
                # condition2._output[0] -> "(users.[name] = users.[id])"

                # Compare with a computed expression
                expr = name_col.upper()
                condition3 = expr == 'ALICE'
                # condition3._output[0] -> "(upper(users.[name]) = ?)"
                # condition3._output[1] -> ['ALICE']
        """
        if value is None:
            new_op = ColumnsOperation(self.col_obj)
            new_op._output = (f'({self._output[0]} IS NULL)', self._output[1])
            return new_op
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} = {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} = {value.name})', self._output[1]) if isinstance(value, Column) else (f'({self._output[0]} = ?)', self._output[1] + [value])
        return new_op
    
    def ne(self, value):
        """Create a not-equal comparison condition for the column expression.

        This method generates a SQL inequality expression (``!=``) between the
        current expression and the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses
        of queries, updates, or deletes. This is the named version of the
        ``__ne__`` operator, allowing explicit usage when operator overloading
        is not desirable.

        The method supports comparisons with:

        * Another :class:`ColumnsOperation` – combines two expressions with ``!=``.
        * A :class:`Column` – compares the expression to a column.
        * A literal (e.g., ``int``, ``str``, ``float``) – uses a parameter placeholder.

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the inequality condition. This allows method
            chaining with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Use ne to exclude a specific name
                condition = name_col.ne('Admin')
                # condition._output[0] -> "(users.[name] != ?)"
                # condition._output[1] -> ['Admin']

                # Compare two columns
                id_col = users.id
                condition2 = name_col.ne(id_col)
                # condition2._output[0] -> "(users.[name] != users.[id])"

                # Chain with AND
                final_condition = condition & (users.age > 18)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} != {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} != {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} != ?)', self._output[1] + [value])
        return new_op

    def __ne__(self, value):
        """Create a not-equal comparison condition for the column expression.

        This method implements the ``!=`` operator for :class:`ColumnsOperation`.
        It generates a SQL inequality expression (``!=``) between the current
        expression and the provided value. The result is a :class:`ColumnsOperation`
        object that can be used in ``WHERE`` clauses of queries, updates, or deletes.

        The method supports comparisons with:

        * Another :class:`ColumnsOperation` – combines two expressions with ``!=``.
        * A :class:`Column` – compares the expression to a column.
        * A literal (e.g., ``int``, ``str``, ``float``) – uses a parameter placeholder.

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the inequality condition. This allows method
            chaining with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Use != with a literal
                condition = price != 100
                # condition._output[0] -> "(products.[price] != ?)"
                # condition._output[1] -> [100]

                # Compare two columns
                discount = products.discount
                condition2 = price != discount
                # condition2._output[0] -> "(products.[price] != products.[discount])"

                # Use in a query
                results = products.get_row([price], where=condition)
                # retrieves rows where price != 100
        """
        if value is None:
            new_op = ColumnsOperation(self.col_obj)
            new_op._output = (f'({self._output[0]} IS NOT NULL)', self._output[1])
            return new_op
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} != {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} != {value.name})', self._output[1]) if isinstance(value, Column) else (f'({self._output[0]} != ?)', self._output[1] + [value])
        return new_op
    
    def gt(self, value):
        """Create a greater-than comparison condition for the column expression.

        This method generates a SQL ``>`` (greater than) expression between the
        current expression and the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses
        of queries, updates, or deletes. This is the named version of the
        ``__gt__`` operator, allowing explicit usage when operator overloading
        is not desirable.

        The method supports comparisons with:

        * Another :class:`ColumnsOperation` – combines two expressions.
        * A :class:`Column` – compares the expression to a column.
        * A literal (e.g., ``int``, ``str``, ``float``) – uses a parameter placeholder.

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the greater-than condition. This allows method
            chaining with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price_col = products.price

                # Use gt to compare with a literal
                condition = price_col.gt(100)
                # condition._output[0] -> "(products.[price] > ?)"
                # condition._output[1] -> [100]

                # Compare two columns
                discount_col = products.discount
                condition2 = price_col.gt(discount_col)
                # condition2._output[0] -> "(products.[price] > products.[discount])"

                # Chain with AND
                final_condition = condition & (price_col < 500)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} > {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} > {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} > ?)', self._output[1] + [value])
        return new_op

    def __gt__(self, value):
        """Create a greater-than comparison condition for the column expression.

        This method implements the ``>`` operator for :class:`ColumnsOperation`.
        It generates a SQL expression using the greater-than operator (``>``) between
        the current expression and the provided value. The result is stored in the
        instance's ``_output`` attribute and can be used in ``WHERE`` clauses.

        The method supports comparisons with:
        * Another :class:`ColumnsOperation` – combines two expressions.
        * A :class:`Column` – compares the expression to a column.
        * A literal (``int``, ``str``, ``float``, etc.) – uses a parameter placeholder.

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the ``>`` condition, allowing method chaining.

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Compare price greater than 100
                condition = price > 100
                # condition._output[0] -> "(products.[price] > ?)"
                # condition._output[1] -> [100]

                # Compare two columns
                discount = products.discount
                condition2 = price > discount
                # condition2._output[0] -> "(products.[price] > products.[discount])"

                # Use in a query
                results = products.get_row([price], where=condition)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} > {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} > {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} > ?)', self._output[1] + [value])
        return new_op

    def lt(self, value):
        """Create a less-than comparison condition for the column expression.

        This method generates a SQL ``<`` (less than) expression between the
        current expression and the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses
        of queries, updates, or deletes. This is the named version of the
        ``__lt__`` operator, allowing explicit usage when operator overloading
        is not desirable.

        The method supports comparisons with:

        * Another :class:`ColumnsOperation` – combines two expressions.
        * A :class:`Column` – compares the expression to a column.
        * A literal (e.g., ``int``, ``str``, ``float``) – uses a parameter placeholder.

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the less-than condition. This allows method
            chaining with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Find products with price less than 100
                condition = price.lt(100)
                # condition._output[0] -> "(products.[price] < ?)"
                # condition._output[1] -> [100]

                # Compare two columns
                discount = products.discount
                condition2 = price.lt(discount)
                # condition2._output[0] -> "(products.[price] < products.[discount])"

                # Use in a query
                results = products.get_row([price], where=condition)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} < {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} < {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} < ?)', self._output[1] + [value])
        return new_op

    def __lt__(self, value):
        """Create a less-than comparison condition for the column expression.

        This method implements the ``<`` operator for :class:`ColumnsOperation`.
        It generates a SQL ``<`` (less than) expression between the current
        expression and the provided value. The result is stored in the instance's
        ``_output`` attribute and the instance is returned, allowing method
        chaining.

        The method supports comparisons with:

        * Another :class:`ColumnsOperation` – combines two expressions.
        * A :class:`Column` – compares the expression to a column.
        * A literal (e.g., ``int``, ``str``, ``float``) – uses a parameter placeholder.

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the less-than condition. This allows method
            chaining with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Find products with price less than 100
                condition = price < 100
                # condition._output[0] -> "(products.[price] < ?)"
                # condition._output[1] -> [100]

                # Compare two columns
                discount = products.discount
                condition2 = price < discount
                # condition2._output[0] -> "(products.[price] < products.[discount])"

                # Use in a query
                results = products.get_row([price], where=condition)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} < {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} < {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} < ?)', self._output[1] + [value])
        return new_op

    def ge(self, value):
        """Create a greater-than-or-equal comparison condition for the column expression.

        This method generates a SQL ``>=`` (greater than or equal) expression
        between the current expression and the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses
        of queries, updates, or deletes. This is the named version of the
        ``__ge__`` operator, allowing explicit usage when operator overloading
        is not desirable.

        The method supports comparisons with:

        * Another :class:`ColumnsOperation` – combines two expressions.
        * A :class:`Column` – compares the expression to a column.
        * A literal (e.g., ``int``, ``str``, ``float``) – uses a parameter placeholder.

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the greater-than-or-equal condition. This allows
            method chaining with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Find products with price >= 100
                condition = price.ge(100)
                # condition._output[0] -> "(products.[price] >= ?)"
                # condition._output[1] -> [100]

                # Compare two columns
                discount = products.discount
                condition2 = price.ge(discount)
                # condition2._output[0] -> "(products.[price] >= products.[discount])"

                # Use in a query
                results = products.get_row([price], where=condition)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} >= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} >= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} >= ?)', self._output[1] + [value])
        return new_op

    def __ge__(self, value):
        """Create a greater-than-or-equal-to comparison condition for the column expression.

        This method implements the ``>=`` operator for :class:`ColumnsOperation`.
        It generates a SQL ``>=`` expression between the current expression and
        the provided value. The result is a :class:`ColumnsOperation` object that
        can be used in ``WHERE`` clauses of queries, updates, or deletes.

        The method supports comparisons with:

        * Another :class:`ColumnsOperation` – combines two expressions.
        * A :class:`Column` – compares the expression to a column.
        * A literal (e.g., ``int``, ``str``, ``float``) – uses a parameter placeholder.

        The instance's ``_output`` attribute is updated with the SQL string and
        parameter list, and the instance itself is returned to allow chaining
        of multiple conditions via logical operators (``&`` and ``|``).

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the ``>=`` condition. This allows method chaining.

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Find products with price >= 100
                condition = price.__ge__(100)
                # Alternatively: price >= 100
                # condition._output[0] -> "(products.[price] >= ?)"
                # condition._output[1] -> [100]

                # Compare two columns
                discount = products.discount
                condition2 = price.__ge__(discount)
                # condition2._output[0] -> "(products.[price] >= products.[discount])"

                # Use in a query
                results = products.get_row([price], where=condition)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} >= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} >= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} >= ?)', self._output[1] + [value])
        return new_op

    def le(self, value):
        """Create a less-than-or-equal-to comparison condition for the column expression.

        This method generates a SQL ``<=`` (less than or equal) expression between
        the current expression and the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses
        of queries, updates, or deletes. This is the named version of the
        ``__le__`` operator, allowing explicit usage when operator overloading
        is not desirable.

        The method supports comparisons with:

        * Another :class:`ColumnsOperation` – combines two expressions.
        * A :class:`Column` – compares the expression to a column.
        * A literal (e.g., ``int``, ``str``, ``float``) – uses a parameter placeholder.

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the less-than-or-equal condition. This allows
            method chaining with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming an ``orders`` table with a ``total`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                orders = db.orders
                total = orders.total

                # Find orders with total <= 100.0
                condition = total.le(100.0)
                # condition._output[0] -> "(orders.[total] <= ?)"
                # condition._output[1] -> [100.0]

                # Compare two columns
                discount = orders.discount
                condition2 = total.le(discount)
                # condition2._output[0] -> "(orders.[total] <= orders.[discount])"

                # Use with AND
                final_condition = condition & (orders.id > 10)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} <= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} <= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} <= ?)', self._output[1] + [value])
        return new_op

    def __le__(self, value):
        """Create a less-than-or-equal comparison condition for the column expression.

        This method implements the ``<=`` operator for :class:`ColumnsOperation`.
        It generates a SQL ``<=`` (less than or equal) expression between the
        current expression and the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses
        of queries, updates, or deletes.

        The method supports comparisons with:

        * Another :class:`ColumnsOperation` – combines two expressions.
        * A :class:`Column` – compares the expression to a column.
        * A literal (e.g., ``int``, ``str``, ``float``) – uses a parameter placeholder.

        Args:
            value: The value or expression to compare against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (``int``, ``str``, ``float``, etc.)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the less-than-or-equal condition. This allows
            method chaining with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Find products with price <= 100
                condition = price <= 100
                # condition._output[0] -> "(products.[price] <= ?)"
                # condition._output[1] -> [100]

                # Compare two columns
                discount = products.discount
                condition2 = price <= discount
                # condition2._output[0] -> "(products.[price] <= products.[discount])"

                # Use in a query
                results = products.get_row([price], where=condition)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} <= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} <= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} <= ?)', self._output[1] + [value])
        return new_op

    def __and__(self, value):
        """Combine two conditions with SQL ``AND``.

        This method implements the ``&`` operator for :class:`ColumnsOperation`.
        It generates a SQL ``AND`` expression combining the current condition
        with another condition. The result is a new condition that can be used
        in ``WHERE`` clauses of queries, updates, or deletes.

        The method expects both operands to be :class:`ColumnsOperation` instances.
        It combines their SQL strings and parameter lists into a single expression.

        Args:
            value (ColumnsOperation): Another condition expression to combine
                with the current one using ``AND``.

        Returns:
            ColumnsOperation: The current instance with its ``_output`` updated
            to represent the combined condition. This allows method chaining.

        Example:
            Assuming a ``users`` table with columns ``age`` and ``active``::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                age = users.age
                active = users.active

                # Build a compound condition
                condition = (age > 18) & (active == 1)
                # condition._output[0] -> "((users.[age] > ?) AND (users.[active] = ?))"
                # condition._output[1] -> [18, 1]

                # Use in a query
                results = users.get_row([users.name], where=condition)
                # retrieves names of active users older than 18
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} AND {value._output[0]})', self._output[1] + value._output[1])
        return new_op

    def __or__(self, value):
        """Combine this condition with another using SQL ``OR``.

        This method implements the bitwise OR operator (``|``) for
        :class:`ColumnsOperation` objects. It generates a SQL expression
        that combines two conditions with the ``OR`` logical operator,
        producing a new condition that is true if either subcondition is true.

        The ``value`` must be another :class:`ColumnsOperation` object
        (e.g., a comparison condition created by ``==``, ``>``, ``&``, etc.).
        The result is stored in the instance's ``_output`` attribute as
        a tuple ``(sql_string, parameters)``, and the instance is returned
        to allow chaining with other conditions.

        Args:
            value (ColumnsOperation): Another condition object to combine
                with ``OR``.

        Returns:
            ColumnsOperation: The current instance with its ``_output``
            updated to represent the combined ``OR`` condition. This allows
            method chaining (e.g., ``(price > 100) | (price < 50)``).

        Example:
            Assuming a ``products`` table with a ``price`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price

                # Create two conditions
                cond1 = price > 100
                cond2 = price < 50

                # Combine with OR
                final_cond = cond1 | cond2
                # final_cond._output[0] -> "((products.[price] > ?) OR (products.[price] < ?))"
                # final_cond._output[1] -> [100, 50]

                # Use in a query
                results = products.get_row([price], where=final_cond)
                # retrieves rows where price > 100 OR price < 50
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} OR {value._output[0]})', self._output[1] + value._output[1])
        return new_op

    def like(self, value):
        """Create a SQL ``LIKE`` condition for pattern matching on the column expression.

        This method generates a ``LIKE`` expression that compares the current
        expression to a pattern. The result is a :class:`ColumnsOperation` object
        that can be used in ``WHERE`` clauses of queries, updates, or deletes.

        The method supports three types of input:

        * Another :class:`ColumnsOperation` – the pattern is a computed expression.
        * A :class:`Column` – the pattern is the value of another column.
        * A literal (``str``, ``int``, etc.) – the pattern is the literal value,
        and a parameter placeholder (``?``) is used.

        The SQL ``LIKE`` operator supports wildcards: ``%`` matches any sequence
        of characters, and ``_`` matches a single character. For literal patterns
        with wildcards, you must include them in the string (e.g., ``'%John%'``).

        Args:
            value: The pattern to match against. Supported types:
                - :class:`ColumnsOperation`
                - :class:`Column`
                - Any literal (typically ``str``)

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the ``LIKE`` condition. This allows method
            chaining with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Find users whose names contain 'smith' (case-sensitive)
                condition = name_col.like('%smith%')
                # condition._output[0] -> "(users.[name] like ?)"
                # condition._output[1] -> ['%smith%']

                # Use with another column as pattern
                pattern_col = users.pattern
                condition2 = name_col.like(pattern_col)
                # condition2._output[0] -> "(users.[name] like users.[pattern])"

                # Use in a query
                results = users.get_row([name_col], where=condition)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"({self._output[0]} like {value._output[0]})", (self._output[1] + value._output[1]) if self._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} like {value.name})', self._output[1]) if isinstance(value , Column) else (f'({self._output[0]} like ?)', self._output[1] + [f'{value}'])
        return new_op

    def startswith(self, prefix):
        """Just like python startswith(), create a SQL ``LIKE`` condition to check if the expression starts with a prefix.

        This method generates a ``LIKE`` expression with the pattern
        ``prefix || '%'``, where ``prefix`` is the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses
        of queries, updates, or deletes.

        The method supports three types of input:

        * A literal (e.g., ``str``, ``int``) – the literal is used as the prefix.
        * A :class:`Column` – the column's value is used as the prefix.
        * A :class:`ColumnsOperation` – the computed expression is used as the prefix.

        The generated SQL uses the ``||`` concatenation operator to append the
        wildcard ``%``.

        Args:
            prefix: The prefix to test against. Can be one of:
                - A literal (e.g., ``'John'``) – the expression value is compared
                to ``'John%'``.
                - A :class:`Column` – compares the expression to the concatenation
                of that column's value and ``'%'``.
                - A :class:`ColumnsOperation` – compares the expression to the
                concatenation of the expression's result and ``'%'``.

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the ``LIKE`` condition. This allows method
            chaining with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Find users whose names start with 'Jo'
                condition = name_col.startswith('Jo')
                # condition._output[0] -> "(users.[name] like ? || '%')"
                # condition._output[1] -> ['Jo']

                # Use in a query
                results = users.get_row([name_col], where=condition)
                # retrieves rows where name LIKE 'Jo%'

                # Using another column as the prefix
                prefix_col = users.prefix
                condition2 = name_col.startswith(prefix_col)
                # condition2._output[0] -> "(users.[name] like users.[prefix] || '%')"
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"({self._output[0]} like {prefix._output[0]} || '%')", (self._output[1] + prefix._output[1]) if self._output else prefix._output[1]) if isinstance(prefix, ColumnsOperation) else (f"({self._output[0]} like {prefix.name} || '%')", self._output[1]) if isinstance(prefix , Column) else (f"({self._output[0]} like ? || '%')", self._output[1] + [f'{prefix}'])
        return new_op

    def endswith(self, suffix):
        """Just like python endswith(), create a SQL ``LIKE`` condition to check if the column expression ends with a suffix.

        This method generates a ``LIKE`` expression with the pattern ``'%' || suffix``,
        where ``suffix`` is the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses.
        The method supports three types of input:

        * A literal (e.g., ``str``, ``int``) – the literal is used as the suffix.
        * A :class:`Column` – the column's value is used as the suffix.
        * A :class:`ColumnsOperation` – the computed expression is used as the suffix.

        The generated SQL uses the ``||`` concatenation operator to prepend the
        wildcard ``'%'``.

        Args:
            suffix: The suffix to test against. Can be one of:
                - A literal (e.g., ``'son'``) – the column value is compared
                to ``'%son'``.
                - A :class:`Column` – compares the column to the concatenation
                of ``'%'`` and that column's value.
                - A :class:`ColumnsOperation` – compares the column to the
                concatenation of ``'%'`` and the expression's result.

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the ``LIKE`` condition. This object can be
            chained with other conditions using logical operators (``&``, ``|``).

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Find users whose names end with 'son'
                condition = name_col.endswith('son')
                # condition._output[0] -> "(users.[name] like '%' || ?)"
                # condition._output[1] -> ['son']

                # Use in a query
                results = users.get_row([name_col], where=condition)
                # retrieves rows where name LIKE '%son'

                # Using another column as the suffix
                suffix_col = users.suffix
                condition2 = name_col.endswith(suffix_col)
                # condition2._output[0] -> "(users.[name] like '%' || users.[suffix])"
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"({self._output[0]} like '%' || {suffix._output[0]})", (self._output[1] + suffix._output[1]) if self._output else suffix._output[1]) if isinstance(suffix, ColumnsOperation) else (f"({self._output[0]} like '%' || {suffix.name})", self._output[1]) if isinstance(suffix , Column) else (f"({self._output[0]} like '%' || ?)", self._output[1] + [f'{suffix}'])
        return new_op

    def contains(self, value):
        """Create a SQL ``LIKE`` condition to check if the column expression contains a substring.

        This method generates a ``LIKE`` expression with the pattern
        ``'%' || substring || '%'``, which tests whether the expression's value
        contains the given substring anywhere. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses.

        The method supports three types of input:

        * Another :class:`ColumnsOperation` – the substring is a computed expression.
        * A :class:`Column` – the substring is the value of another column.
        * A literal (e.g., ``str``, ``int``) – the substring is the literal value.

        The generated SQL uses the ``||`` concatenation operator to build the
        pattern with wildcards.

        Args:
            value: The substring to search for. Can be one of:
                - A literal (e.g., ``'abc'``) – the column value is checked
                for containment of ``'abc'``.
                - A :class:`Column` – the substring is taken from the column's value.
                - A :class:`ColumnsOperation` – the substring is the result of
                a computed expression.

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the containment condition. This allows method
            chaining with other conditions via logical operators (``&``, ``|``).

        Example:
            Assuming a ``products`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                name = products.name

                # Find products whose name contains 'phone'
                condition = name.contains('phone')
                # condition._output[0] -> "(products.[name] like '%' || ? || '%')"
                # condition._output[1] -> ['phone']

                # Use another column as the substring
                keyword_col = products.search_term
                condition2 = name.contains(keyword_col)
                # condition2._output[0] -> "(products.[name] like '%' || products.[search_term] || '%')"

                # Use in a query
                results = products.get_row([name], where=condition)
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"({self._output[0]} like '%' || {value._output[0]} || '%')", (self._output[1] + value._output[1]) if self._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self._output[0]} like '%' || {value.name} || '%')", self._output[1]) if isinstance(value , Column) else (f"({self._output[0]} like '%' || ? || '%')", self._output[1] + [f'{value}'])
        return new_op

    def add_end(self, content):
        """Append content to the end of the column expression using SQL concatenation.

        This method generates a SQL expression that concatenates the current
        expression's value with the given ``content`` using the ``||`` operator,
        placing the content after the current value. The result is a
        :class:`ColumnsOperation` object that can be used in ``SELECT``,
        ``WHERE``, or other SQL clauses.

        The method supports three types of input:

        * Another :class:`ColumnsOperation` – concatenates the two expressions.
        * A :class:`Column` – uses the column's value as the content.
        * A literal (e.g., ``str``, ``int``) – uses the literal as the content.

        If the current expression is empty (i.e., the operation is called directly
        on a :class:`Column` without prior operations), the method uses the
        column's name as the base.

        Args:
            content: The content to append. Can be one of:
                - :class:`ColumnsOperation` – a computed expression.
                - :class:`Column` – a table column.
                - Any literal (``str``, ``int``, ``float``, etc.) – a static value.

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the concatenation. This allows method chaining.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Append a literal suffix
                expr = name_col.add_end(' (active)')
                # expr._output[0] -> "(users.[name] || ?)"
                # expr._output[1] -> [' (active)']

                # Append another column's value
                suffix_col = users.status
                expr2 = name_col.add_end(suffix_col)
                # expr2._output[0] -> "(users.[name] || users.[status])"

                # Use in a query
                result = users.get_row([expr], where=users.id == 1)
                # retrieves the concatenated string for the user with id=1
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} || {content._output[0]})', self._output[1]+content._output[1] if self._output else content._output[1]) if isinstance(content, ColumnsOperation) else (f'({self._output[0]} || {content.name})', self._output[1] if self._output else []) if isinstance(content, Column) else (f'({self._output[0]} || ?)', self._output[1]+[content] if self._output else [content])
        new_op.current_datatype = str
        return new_op

    def add_first(self, content):
        """Prepend content to the beginning of the column expression using SQL concatenation.

        This method generates a SQL expression that concatenates the given ``content``
        before the current expression's value using the ``||`` operator.
        The result is a :class:`ColumnsOperation` object that can be used in
        ``SELECT``, ``WHERE``, or other SQL clauses.

        The method supports three types of input:

        * Another :class:`ColumnsOperation` – concatenates the two expressions.
        * A :class:`Column` – uses the column's value as the prefix.
        * A literal (e.g., ``str``, ``int``) – uses the literal as the prefix.

        If the current expression is empty (i.e., the operation is called directly
        on a :class:`Column` without prior operations), the method uses the
        column's name as the base.

        Args:
            content: The content to prepend. Can be one of:
                - :class:`ColumnsOperation` – a computed expression.
                - :class:`Column` – a table column.
                - Any literal (``str``, ``int``, ``float``, etc.) – a static value.

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the concatenation. This allows method chaining.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Prepend a literal prefix
                expr = name_col.add_first('Mr. ')
                # expr._output[0] -> "(? || users.[name])"
                # expr._output[1] -> ['Mr. ']

                # Prepend another column's value
                prefix_col = users.title
                expr2 = name_col.add_first(prefix_col)
                # expr2._output[0] -> "(users.[title] || users.[name])"

                # Use in a query
                result = users.get_row([expr], where=users.id == 1)
                # retrieves the concatenated string for the user with id=1
        """        
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({content._output[0]} || {self._output[0]})', content._output[1]+self._output[1] if self._output else content._output[1]) if isinstance(content, ColumnsOperation) else (f'({content.name} || {self._output[0]})', self._output[1] if self._output else []) if isinstance(content, Column) else (f'(? || {self._output[0]})', [content]+self._output[1] if self._output else [content])
        new_op.current_datatype = str
        return new_op

    def replace(self, old: str, new: str):
        """Just like python replace(), replace all occurrences of a substring within the column value.

        This method generates a SQL expression using the SQLite ``replace()``
        function, which returns the string with every occurrence of ``old``
        replaced by ``new``. The operation is applied to the current column
        expression (or the base column if no prior operations exist).

        The method modifies the instance's ``_output`` in place and returns
        ``self`` to support method chaining. The resulting ``_output`` is a tuple
        ``(sql_string, parameters)`` where the parameters include the ``old``
        and ``new`` strings as placeholders.

        Args:
            old (str): The substring to be replaced.
            new (str): The replacement string.

        Returns:
            ColumnsOperation: The current instance with its ``_output`` updated
            to represent the ``replace()`` SQL function call.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Replace 'John' with 'Jonathan'
                expr = name_col.replace('John', 'Jonathan')
                # expr._output[0] -> "replace(users.[name] , ? , ?)"
                # expr._output[1] -> ['John', 'Jonathan']

                # Use in a SELECT query
                result = users.get_row([expr], where=users.id == 1)
                # retrieves the name with replacements applied

                # Chain with other operations
                expr2 = name_col.upper().replace('A', 'X')
                # expr2._output[0] -> "replace(upper(users.[name]) , ? , ?)"
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(replace({self._output[0]} , ? , ?))', self._output[1] + [old, new]) if self._output else (f'(replace({self.col_obj.name} , ? , ?))', [old, new])
        new_op.current_datatype = str
        return new_op

    def upper(self):
        """Just like python upper(), convert the column expression to uppercase using SQL's UPPER function.

        This method generates a SQL expression that wraps the current expression
        in the ``UPPER()`` function, which converts all characters to uppercase.
        The result is a :class:`ColumnsOperation` object that can be used in
        ``SELECT``, ``WHERE``, or other SQL clauses.

        The method updates the internal ``_output`` attribute to reflect the
        transformation and returns ``self`` to allow method chaining.

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the ``UPPER()`` expression. This allows method
            chaining.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Convert name to uppercase in SQL
                expr = name_col.upper()
                # expr._output[0] -> "upper(users.[name])"
                # expr._output[1] -> []

                # Use in a query to retrieve uppercase names
                results = users.get_row([expr], where=users.id == 1)
                # retrieves the uppercase version of the user's name

                # Chain with other operations
                expr2 = name_col.upper().strip()
                # expr2._output[0] -> "trim(upper(users.[name]), ' ')"
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(upper({self._output[0]}))', self._output[1]) if self._output else (f'(upper({self.col_obj.name}))', [])
        new_op.current_datatype = str
        return new_op

    def lower(self):
        """Just like python lower(), convert the column expression to lowercase using SQLite's `LOWER` function.

        This method generates a SQL expression that applies the ``LOWER()`` function
        to the current column expression. The result is a :class:`ColumnsOperation`
        object that can be used in ``SELECT``, ``WHERE``, or other SQL clauses.

        If the current expression is empty (i.e., the method is called directly on a
        :class:`Column` without prior operations), the method uses the column's name
        as the base expression.

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the ``LOWER()`` function call. This allows method
            chaining.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Convert the column to lowercase
                expr = name_col.lower()
                # expr._output[0] -> "lower(users.[name])"
                # expr._output[1] -> []

                # Use in a query
                results = users.get_row([expr], where=users.id == 1)
                # retrieves the lowercase name for the user with id=1

                # Chain with another operation
                expr2 = (name_col + ' (test)').lower()
                # expr2._output[0] -> "lower((users.[name] || ?))"
                # expr2._output[1] -> [' (test)']
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(lower({self._output[0]}))', self._output[1]) if self._output else (f'(lower({self.col_obj.name}))', [])
        new_op.current_datatype = str
        return new_op

    def strip(self, chars: str = ' '):
        """Just like python strip(), remove leading and trailing characters from the column expression.

        This method generates a SQL ``trim`` function call that removes all
        occurrences of the specified characters from both ends of the expression's
        string value. By default, it strips whitespace characters.

        The method mutates the instance's ``_output`` attribute to store the SQL
        string and parameters, and returns ``self`` to allow method chaining.

        If the instance already has an accumulated expression (i.e., ``_output`` is
        a tuple), the ``trim`` is applied to that expression. Otherwise, it is
        applied directly to the underlying column name (``self.col_obj.name``).

        Args:
            chars (str, optional): A string of characters to remove from both ends.
                Defaults to a single space (' '). The characters can be specified in
                any order; the SQLite ``trim`` function removes any combination of
                these characters.

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the ``trim`` operation. This allows chaining.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Strip whitespace from both ends of the name
                expr = name_col.strip()
                # expr._output[0] -> 'trim(users.[name]," ")'
                # expr._output[1] -> []

                # Strip specific characters (e.g., '-' and '_')
                expr2 = name_col.strip('-_')
                # expr2._output[0] -> 'trim(users.[name],"-_")'

                # Chain with other operations
                expr3 = name_col.strip().upper()
                # expr3._output[0] -> 'upper(trim(users.[name]," "))'
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(trim({self._output[0]},"{chars}"))', self._output[1]) if self._output else (f'(trim({self.col_obj.name},"{chars}"))', [])
        new_op.current_datatype = str
        return new_op

    def lstrip(self, chars: str = ' '):
        """Just like python lstrip(), trim leading characters from the column expression using SQL LTRIM.

        This method generates a SQL ``LTRIM`` function call that removes all
        occurrences of the specified characters from the beginning (left side)
        of the column or expression's string value. The result is stored in the
        instance's ``_output`` attribute and the instance is returned to allow
        chaining.

        If the current expression already contains operations (i.e., ``_output``
        is not empty), the ``LTRIM`` is applied to that expression. Otherwise,
        it is applied directly to the underlying :class:`Column` object.

        The method supports specifying which characters to strip via the
        ``chars`` parameter. The default is a space character.

        Args:
            chars (str): A string containing the characters to remove from the
                left side. Defaults to a single space (``' '``). The order of
                characters does not matter; SQLite removes all characters in the
                set until a non-matching character is encountered.

        Returns:
            ColumnsOperation: The current instance with its ``_output`` updated
            to represent the SQL ``LTRIM`` expression. This allows method
            chaining.

        Example:
            Assuming a ``users`` table with a ``name`` column that may contain
            leading spaces::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Remove leading spaces
                expr = name_col.lstrip()
                # expr._output[0] -> "ltrim(users.[name],' ')"

                # Remove leading 'x' and 'y'
                expr2 = name_col.lstrip('xy')
                # expr2._output[0] -> "ltrim(users.[name],'xy')"

                # Use in a query to get cleaned names
                result = users.get_row([expr])
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(ltrim({self._output[0]},"{chars}"))', self._output[1]) if self._output else (f'(ltrim({self.col_obj.name},"{chars}"))', [])
        new_op.current_datatype = str
        return new_op

    def rstrip(self, chars: str = ' '):
        """Just like python rstrip(), remove trailing characters from the column expression using SQL rtrim.

        This method generates a SQL ``rtrim`` function call that removes all
        occurrences of the specified characters from the end (right side) of the
        expression's string value. By default, it strips trailing whitespace.

        The method mutates the instance's ``_output`` attribute to store the SQL
        string and parameters, and returns ``self`` to allow method chaining.

        If the instance already has an accumulated expression (i.e., ``_output`` is
        a tuple), the ``rtrim`` is applied to that expression. Otherwise, it is
        applied directly to the underlying column name (``self.col_obj.name``).

        Args:
            chars (str, optional): A string of characters to remove from the right
                end. Defaults to a single space (' '). The characters can be
                specified in any order; the SQLite ``rtrim`` function removes any
                combination of these characters from the end of the string.

        Returns:
            :class:`ColumnsOperation`: The current instance with its ``_output``
            updated to represent the ``rtrim`` operation. This allows chaining.

        Example:
            Assuming a ``products`` table with a ``description`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                desc_col = products.description

                # Strip trailing whitespace
                expr = desc_col.rstrip()
                # expr._output[0] -> 'rtrim(products.[description]," ")'
                # expr._output[1] -> []

                # Strip trailing dashes and underscores
                expr2 = desc_col.rstrip('-_')
                # expr2._output[0] -> 'rtrim(products.[description],"-_")'

                # Chain with other operations
                expr3 = desc_col.rstrip().upper()
                # expr3._output[0] -> 'upper(rtrim(products.[description]," "))'
        """
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(rtrim({self._output[0]},"{chars}"))', self._output[1]) if self._output else (f'(rtrim({self.col_obj.name},"{chars}"))', [])
        new_op.current_datatype = str
        return new_op

    def In(self, column: 'Ormophine.Sqlite.Column|Ormophine.Sqlite.ColumnsOperation' = None, where: 'Ormophine.Sqlite.ColumnsOperation' = None, data_list: list = None):
        """Build an SQL ``IN`` clause for the current column expression.

        This method supports two distinct modes for generating an ``IN`` clause:

        * **Literal list mode**: When ``data_list`` is provided, generates a
          parameterised ``IN (?, ?, ...)`` clause using the literal values.
          For backward compatibility, if a list of plain values is passed as
          the first positional argument (``column``), it is automatically
          treated as ``data_list``.
        * **Subquery mode**: When ``column`` is provided as a single
          :class:`Column` or :class:`Ormophine.Sqlite.ColumnsOperation`, builds an
          ``IN (SELECT ...)`` subquery. The table name is extracted from the
          provided column object, and an optional ``where`` condition can be
          applied inside the subquery — handled identically to
          :meth:`Table.get_row`.

        The result is stored in the instance's ``_output`` attribute as a tuple
        ``(sql_string, parameters)``, and the instance is returned to allow
        chaining.

        Args:
            column: A single :class:`Column` or :class:`Ormophine.Sqlite.ColumnsOperation`
                to use in the ``SELECT`` clause of the subquery. The table name
                is determined from this object. Do not pass a list of columns;
                if you need multiple conditions, chain them using ``&`` or ``|``.
                If a list of literals is passed, it is treated as ``data_list``.
            where: An optional :class:`Ormophine.Sqlite.ColumnsOperation` (or :class:`Column` for
                boolean columns) representing the ``WHERE`` condition for the
                subquery. Defaults to ``None``.
            data_list: A list of literal values for a direct ``IN`` clause.
                When provided, ``column`` and ``where`` are ignored.

        Returns:
            :class:`Ormophine.Sqlite.ColumnsOperation`: The current instance with its ``_output``
            updated to represent the ``IN`` clause. This allows method chaining.

        Raises:
            Exception: If neither ``data_list`` nor a valid ``column``
                is provided.

        Example:
            Assuming ``users`` and ``admins`` tables::

                from ormophine.Sqlite import Driver

                db = Driver('app.db')
                users = db.users
                admins = db.admins

                # Literal list mode (backward compatible)
                expr1 = users.name.In(['Alice', 'Bob'])
                # expr1._output[0] -> "(users.[name] IN (?, ?))"
                # expr1._output[1] -> ['Alice', 'Bob']

                # Literal list mode (using keyword)
                expr2 = users.name.In(data_list=['Alice', 'Bob'])

                # Subquery mode with WHERE
                expr3 = users.name.In(
                    column=admins.username,
                    where=admins.active == True
                )
                # expr3._output[0] -> "(users.[name] IN (SELECT admins.[username] FROM admins WHERE (admins.[active] = ?)))"
                # expr3._output[1] -> [True]

                # Subquery mode without WHERE
                expr4 = users.name.In(column=admins.username)
                # expr4._output[0] -> "(users.[name] IN (SELECT admins.[username] FROM admins))"
        """
        if isinstance(column, list):
            data_list, column = column, None #So user can simply In(['Alice', 'Bob']) with out passing arguments
        if not column and not data_list:
            raise Exception("In() requires either data_list or column")
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} IN ({", ".join(["?" for _ in data_list])}))', self._output[1] + data_list) if data_list is not None else (f'({self._output[0]} IN (SELECT {column.name if isinstance(column, Column) else column._output[0]} FROM {(column.name if isinstance(column, Column) else column.col_obj.name).split('.')[0]}{f' WHERE {where._output[0]}' if isinstance(where, ColumnsOperation) else f' WHERE {where.name}' if isinstance(where, Column) else ''}))', self._output[1] + ([] if isinstance(column, Column) else column._output[1]) + (where._output[1] if isinstance(where, ColumnsOperation) else [])) if isinstance(column, (Column, ColumnsOperation)) else None
            
        return new_op
    
    
class Column:
    """Represents a database column in the SQLite ORM.

    This class acts as a proxy for a specific column in a database table,
    providing a Pythonic interface for building SQL expressions and performing
    schema operations. Columns are typically not instantiated directly but
    are automatically created as attributes of a :class:`Table` object during
    table initialization.

    The class overloads Python operators (``+``, ``-``, ``*``, ``/``, ``%``,
    ``**``, ``&``, ``|``, etc.) to generate corresponding SQL expressions.
    For string columns, ``+`` is translated to the SQL concatenation operator
    ``||``; for numeric columns, it translates to ``+``. Comparison operators
    (``==``, ``!=``, ``<``, ``>``, ``<=``, ``>=``) generate SQL comparison
    conditions. The result of these operations is a :class:`ColumnsOperation`
    object, which can be used in the ``where`` clause of query methods like
    :meth:`Table.get_row`, :meth:`Table.update`, and :meth:`Table.delete_row`.

    Additionally, the class provides string manipulation methods (``lower``,
    ``upper``, ``strip``, ``startswith``, ``endswith``, ``contains``, ``like``,
    ``replace``, slicing via ``__getitem__``) that translate to SQLite's
    built-in functions, as well as methods for renaming (``rename``) and
    deleting (``delete_column``) the column in the database schema.

    Attributes:
        name (str): The fully qualified column name for use in SQL queries,
            formatted as ``[table_name].[column_name]``. This includes the
            table name and brackets to safely handle special characters.
        first_name (str): The column name formatted with brackets only,
            e.g., ``[column_name]``. This is typically used in DDL
            statements like ``ALTER TABLE ... RENAME COLUMN``.
        table_obj (Table): The parent :class:`Table` instance that this
            column belongs to.
        datatype (type): The Python type mapping for the column, derived
            from the SQLite column affinity (e.g., ``int`` for INTEGER,
            ``str`` for TEXT, ``float`` for REAL, ``bytes`` for BLOB).

    Example:
        Accessing columns from a table and building conditions::

            from ormophine.Sqlite import Driver

            # Connect to the database
            db = Driver('myapp.db')
            users = db.users  # creates Table instance

            # Access columns as attributes
            name_col = users.name      # Column instance
            age_col = users.age        # Column instance

            # Build SQL expressions using operators
            condition = (age_col >= 18) & name_col.startswith('A')
            # condition._output[0] -> "([users].[age] >= ? AND [users].[name] like ? || '%')"
            # condition._output[1] -> [18, 'A']

            # Use the condition in a query
            results = users.get_row([name_col, age_col], where=condition)
            # Executes: SELECT [users].[name], [users].[age] FROM [users]
            #           WHERE [users].[age] >= 18 AND [users].[name] LIKE 'A%'

            # Perform a string transformation in SQL
            upper_name = name_col.upper()
            # upper_name._output[0] -> "upper([users].[name])"

            # Rename the column (requires triple confirmation)
            name_col.rename('full_name')
    """

    def __init__(self, table_obj: Table, column_name: str, datatype: type):

        """Initializes a Column instance representing a column in a database table.

        This object holds the column's fully qualified name used in SQL generation
        (e.g., ``[table_name].[column_name]``), a short name without the table
        prefix, a reference to the parent :class:`Table`, and the Python type that
        corresponds to the column's SQL data type.

        Args:
            table_obj (Table): The :class:`Table` instance to which this column belongs.
            column_name (str): The name of the column as it appears in the database
                (without brackets). The name will be automatically wrapped in square
                brackets for safe SQL usage.
            datatype (type): The Python type that represents the column's data. This
                is used to decide between string concatenation (``||``) and arithmetic
                operators (``+``) when building expressions with
                :class:`ColumnsOperation`.

        Example:
            >>> from myorm import Driver, Table, Column
            >>> driver = Driver('example.db') #tables automatically imported to this object, and columns imported to each table
            >>> my_table = driver.my_sample_table #Table object
            >>> users = mytable.users #Column object
        """
        self.name= table_obj.name_+'.['+column_name+']'
        self.first_name= f'[{column_name}]'
        self.table_obj= table_obj
        self.datatype= datatype

    def __hash__(self):

        """Return a hash value for the column, derived from its fully qualified name.

        The column's fully qualified name is composed of the table name and the
        column name enclosed in brackets (e.g., ``[users].[id]``). Hashing
        allows :class:`Column` instances to be used as dictionary keys or in sets,
        ensuring uniqueness based on the column identity across different tables.

        Returns:
            int: The hash of the column's fully qualified name string.

        Example:
            >>> users_table = driver.get_tables()['users']
            >>> col = users_table.id
            >>> col_set = {col}
            >>> col in col_set
            True
        """
        
        return hash(self.name)

    def __add__(self, value):
        """Return a :class:`ColumnsOperation` representing addition or string concatenation with this column.

        This method overloads the ``+`` operator to create a SQL expression that adds or concatenates
        a value to the column. The operation depends on the column's data type:
        
        * For numeric columns (``int``, ``float``), it generates ``{column} + {value}``.
        * For string columns (``str``), it generates ``{column} || {value}`` (SQLite concatenation operator).
        
        The returned :class:`ColumnsOperation` can be used directly in methods like
        :meth:`Table.update`, :meth:`Table.get_row`, :meth:`Table.join`, or combined further with
        other arithmetic/comparison operations.

        Args:
            value: The right-hand operand. It can be a :class:`Column` (to add another column),
                a :class:`ColumnsOperation` (to chain from an existing operation), a numeric literal
                (``int`` or ``float`` for arithmetic), or a string literal for concatenation.

        Returns:
            ColumnsOperation: A chainable operation object whose internal SQL representation
            reflects the addition/concatenation. This object can be used in further operations
            like comparison or string manipulation.

        Raises:
            TypeError: If the operand type is incompatible with the column's data type
                (e.g., adding a number to a text column will still generate ``||``, but the
                type handling is determined by the column's ``datatype`` attribute).

        Example:
            Creating an expression for a SELECT or UPDATE:

            >>> # Assuming 'price' is a Column of type float and 'quantity' is an int Column
            >>> total_expr = table.price + table.quantity  # price + quantity (numeric)
            >>> name_with_prefix = table.name + '_suffix'  # name || '_suffix' (text concatenation)
            >>> combined_expr = (table.price + 10) * table.quantity  # (price + 10) * quantity

            Using the expression in a query:

            >>> result = table.get_row([table.price + table.quantity], where=table.price > 100)
            >>> table.update({table.description: table.description + ' - updated'}, where=table.id == 1)
        """

        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob + value

    def __radd__(self, value):
        """Implements reflected addition for a :class:`Column` instance.

        This method is invoked when the left operand does not support addition
        with a :class:`Column` object (e.g., ``"Hello " + col``). It creates
        a :class:`ColumnsOperation` that encapsulates the SQL addition expression.
        For columns of type :class:`str`, the concatenation operator ``||`` is
        used; for numeric types (``int``, ``float``), the arithmetic ``+`` is used.

        Args:
            value: The left operand in the addition. It can be:
                - A :class:`Column` instance.
                - A :class:`ColumnsOperation` instance.
                - An :class:`int` or :class:`float` (numeric literal).
                - A :class:`str` (text literal, treated as string even if the
                column's datatype is numeric, as SQLite's ``||`` will perform
                implicit conversion, but the generated SQL will use ``||``
                for consistency with the column's declared type).

        Returns:
            :class:`ColumnsOperation`: An expression object whose ``_output``
            attribute is a tuple of (SQL fragment, parameter list). The SQL
            fragment uses ``||`` if the column's datatype is :class:`str`,
            otherwise ``+``. The parameter list contains any literal values
            that were bound into the expression.

        Raises:
            No exceptions are raised by this method itself, but further
            evaluation of the expression may raise database-related errors.

        Example:
            >>> col = my_table.name  # datatype is str
            >>> expr = "Hello " + col
            >>> expr._output
            ('? || [my_table].[name]', ['Hello '])

            >>> col2 = my_table.age  # datatype is int
            >>> expr2 = 10 + col2
            >>> expr2._output
            ('? + [my_table].[age]', [10])
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value + temp_ob

    def __sub__(self, value):
        """Return a :class:`ColumnsOperation` representing subtraction from this column.

        Produces a SQL expression that subtracts *value* from the column.
        The type of *value* determines the exact generated SQL:

        - If *value* is a :class:`ColumnsOperation`, the subtraction expression
        is ``(column_name - <operation expression>)`` and the parameter lists
        are concatenated.
        - If *value* is a :class:`Column`, the expression becomes
        ``(column_name - <other column name>)`` with no extra parameters.
        - Otherwise (a numeric literal), the expression is ``(column_name - ?)``
        and the value is added to the parameter list.

        Args:
            value: The right-hand operand. Can be:
                - :class:`ColumnsOperation` – another operation to subtract.
                - :class:`Column` – another column to subtract.
                - numeric (int or float) – a literal value to subtract.

        Returns:
            :class:`ColumnsOperation`: A new operation object whose ``_output``
            attribute is a tuple ``(sql_fragment, parameter_list)``. The object
            can be further chained with other operators or comparisons.

        Example:
            >>> col = table.salary  # salary is a Column
            >>> op = col - 500      # uses __sub__
            >>> op._output
            ('([salary] - ?)', [500])

            >>> bonus = table.bonus
            >>> op2 = col - bonus   # subtraction of two columns
            >>> op2._output
            ('([salary] - [bonus])', [])

            The result can be used in WHERE clauses, SELECT expressions, etc.
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob - value

    def __rsub__(self, value):
        """Implements reflected subtraction for a :class:`Column` instance.

        This method is invoked when the left operand in a subtraction does not
        support the operation with a :class:`Column` object (e.g.,
        ``100 - my_table.age``). It creates a :class:`ColumnsOperation` that
        represents the SQL subtraction expression. The subtraction is always
        arithmetic (``-``) regardless of the column's :attr:`datatype`.

        Args:
            value: The left operand of the subtraction. Can be:
                - :class:`int` or :class:`float`: a numeric literal, wrapped
                  as a parameterized value.
                - :class:`Column`: another column reference.
                - :class:`ColumnsOperation`: a pre‑existing expression.

        Returns:
            :class:`ColumnsOperation`: An expression object whose
            :attr:`_output` attribute is a tuple of
            ``(SQL_fragment, parameter_list)``. The SQL fragment is of the
            form ``(? - column_name)`` or ``(other - column_name)``, and
            the parameter list contains any bound literal values.

        Raises:
            No exceptions are directly raised; database‑related errors may
            occur when the expression is evaluated later.

        Example:
            >>> col = my_table.age  # integer column
            >>> expr = 100 - col
            >>> expr._output
            ('(? - [my_table].[age])', [100])

            >>> col2 = my_table.name  # string column (subtraction is still arithmetic)
            >>> expr2 = 10 - col2  # likely a mistake, but the SQL will be generated
            >>> expr2._output
            ('(? - [my_table].[name])', [10])
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value - temp_ob
        
    def __mul__(self, value):
        """Implements multiplication for a :class:`Column` instance.

        This method is invoked when a :class:`Column` object is used on the
        left side of the ``*`` operator (e.g., ``col * 2``). It creates a
        :class:`ColumnsOperation` that encapsulates the SQL multiplication
        expression. The expression uses the SQL ``*`` operator regardless
        of the column's declared datatype (SQLite performs implicit numeric
        conversion if needed).

        Args:
            value: The right operand in the multiplication. It can be:
                - A :class:`Column` instance (e.g., ``col1 * col2``).
                - A :class:`ColumnsOperation` instance.
                - An :class:`int` or :class:`float` literal.
                - A :class:`str` literal (will be treated as a numeric
                literal if SQLite can convert it; otherwise an error may
                occur at execution time).

        Returns:
            :class:`ColumnsOperation`: An expression object whose ``_output``
            attribute is a tuple of (SQL fragment, parameter list). For
            example, ``col * 2`` produces ``('([table].[col] * ?)', [2])``.
            The expression can be further combined using other operators or
            used in WHERE clauses, joins, and selections.

        Raises:
            No exceptions are raised by this method itself. SQLite runtime
            errors (e.g., type mismatch) may occur when the query is executed.

        Example:
            Multiply an integer column by a constant:

            >>> col = my_table.price
            >>> discounted = col * 0.9
            >>> discounted._output
            ('([my_table].[price] * ?)', [0.9])

            Multiply two columns:

            >>> total = my_table.quantity * my_table.unit_price
            >>> total._output
            ('([my_table].[quantity] * [my_table].[unit_price])', [])
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob * value

    def __rmul__(self, value):
        """Implements reflected multiplication for a :class:`Column`.

        Called when a literal or expression appears on the left of the ``*``
        operator, e.g. ``3 * my_column``.  A new :class:`ColumnsOperation` is
        created that wraps the column name and then delegates to
        :meth:`ColumnsOperation.__rmul__` to build the actual SQL expression.
        The generated SQL uses the arithmetic ``*`` operator (multiplication).

        Note:
            This method is intended for numeric columns.  Using it with a
            :class:`str` column or non-numeric literal may still produce SQL
            that SQLite will attempt to convert implicitly, but is not
            recommended.

        Args:
            value: The left operand of the multiplication.  Accepts:
                - :class:`int` or :class:`float` literals.
                - Another :class:`Column` instance.
                - A :class:`ColumnsOperation` instance.

        Returns:
            :class:`ColumnsOperation`: An expression object whose internal
            ``_output`` tuple contains ``(sql_fragment, parameters)``, ready
            to be used in WHERE clauses, SELECT lists, or UPDATE assignments.

        Raises:
            No exceptions are raised during construction.  Database errors
            (e.g. type mismatches) may occur only when the query is executed.

        Example:
            >>> age = my_table.age  # numeric column
            >>> expr = 2 * age
            >>> expr._output
            ('? * [my_table].[age]', [2])

            The resulting expression can be used directly with :meth:`Table.get_row`::

                my_table.get_row([expr], where=expr > 0)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value * temp_ob

    def __pow__(self, value):
        """Generate an SQL exponentiation (power) expression for this column.

        This special method is invoked when the ``**`` operator is used with a
        :class:`Column` instance on the left side (e.g., ``col ** 2``). It creates a
        :class:`ColumnsOperation` that will produce an SQL fragment raising the column
        to the given power. The resulting SQL uses the ``**`` operator, which is not
        standard SQLite syntax; it is assumed that the underlying SQL execution
        context either supports this syntax or that a custom SQL function ``power``
        is mapped to ``**``. The generated expression is wrapped in parentheses to
        ensure correct operator precedence.

        Args:
            value: The exponent. It can be:
                - A :class:`ColumnsOperation` instance, in which case its SQL fragment
                and parameters are combined.
                - A :class:`Column` instance (another table column), using its name
                directly in the SQL.
                - A numeric literal (int or float), which will be replaced with a
                parameter placeholder (``?``) and added to the parameter list.

        Returns:
            :class:`ColumnsOperation`: An expression object whose ``_output``
            attribute is a tuple of ``(sql_fragment, param_list)``. The SQL
            fragment contains ``**`` between the column and the exponent, and the
            parameter list holds any bound literal values.

        Example:
            >>> age_col = my_table.age  # Column for integer age
            >>> expr = age_col ** 2
            >>> expr._output
            ('([my_table].[age] ** ?)', [2])

            >>> another_col = my_table.salary
            >>> combined_expr = age_col ** another_col
            >>> combined_expr._output
            ('([my_table].[age] ** [my_table].[salary])', [])
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob ** value

    def __rpow__(self, value):
        """Implements the reflected exponentiation operator for a Column.

        This method is called when the left operand does not support power
        with a Column (e.g., ``2 ** col``). It creates a
        :class:`ColumnsOperation` that generates a SQL exponentiation
        expression using the ``**`` operator. The resulting SQL fragment and
        parameters can be used in :meth:`Table.get_row`, :meth:`Table.update`,
        or other query methods.

        Args:
            value: The left operand in the exponentiation. It can be:
                - An :class:`int` or :class:`float` literal (e.g., 2).
                - A :class:`Column` instance.
                - A :class:`ColumnsOperation` instance.

        Returns:
            :class:`ColumnsOperation`: An expression object whose
            :attr:`_output` attribute is a tuple of the form
            (SQL fragment, parameter list). The SQL fragment represents
            ``(value ** column_name)``, and the parameter list contains
            any bound literal values.

        Raises:
            No exceptions are raised by this method. However, subsequent
            use in a SQL query may raise database errors if the operation
            is invalid (e.g., non‑numeric column).

        Example:
            >>> col = my_table.score  # a numeric Column
            >>> expr = 2 ** col
            >>> expr._output
            ('(? ** [my_table].[score])', [2])
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value ** temp_ob

    def __truediv__(self, value):
        """Implement the division operator (``/``) for a :class:`Column`.

        This method creates a :class:`ColumnsOperation` that represents the SQL
        division of this column by ``value``. The generated SQL uses the standard
        ``/`` operator, and any literal operands are parameterized with ``?`` to
        prevent SQL injection.

        The division is performed by first wrapping the column into a
        :class:`ColumnsOperation` with its initial SQL fragment set to the column's
        fully qualified name and an empty parameter list, then delegating to
        :meth:`ColumnsOperation.__truediv__`.

        Args:
            value: The divisor. It can be:
                - A :class:`Column` instance – division by another column.
                - A :class:`ColumnsOperation` instance – division by a sub‑expression.
                - A numeric literal (:class:`int` or :class:`float`) – division by a
                constant value (parameterized).

        Returns:
            :class:`ColumnsOperation`: An expression object whose ``_output``
            attribute is a tuple ``(sql_fragment, params)``. For example, dividing
            a column named ``price`` by 2 would produce the SQL fragment
            ``([table_name].[price] / ?)`` and a parameter list ``[2]``.

        Raises:
            No exceptions are raised directly by this method. However, subsequent
            use of the returned expression in a query may raise database errors if
            the column types are incompatible or division by zero occurs.

        Example:
            >>> # Assume a Table 'products' with Column 'price' (datatype float)
            >>> half_price = products.price / 2
            >>> half_price._output
            ('([products].[price] / ?)', [2])

            >>> # Use in a query
            >>> products.update(
            ...     {products.price: half_price},
            ...     where=products.id == 42
            ... )
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob / value

    def __rtruediv__(self, value):
        """Implements reflected (right-hand) division for a :class:`Column`.

        This method is called when the left operand in a division operation does
        not support division with a :class:`Column` instance, for example when
        writing ``10 / my_column``. It creates a :class:`ColumnsOperation` that
        wraps the column and then delegates the actual operation to the
        :meth:`ColumnsOperation.__rtruediv__` method, resulting in a SQL expression
        using the standard ``/`` operator with parameterized literal values.

        The generated SQL fragment places the right operand's expression on the
        left side of the division to preserve mathematical correctness: the
        resulting fragment will be ``(value / column_name)``.

        Args:
            value: The numerator in the division. It can be:
                - A :class:`Column` instance – division of another column by this
                column.
                - A :class:`ColumnsOperation` instance – a sub‑expression as
                numerator.
                - A numeric literal (:class:`int` or :class:`float`) – division
                of a constant by this column (parameterized with ``?``).

        Returns:
            :class:`ColumnsOperation`: An expression object whose ``_output``
            attribute is a tuple ``(sql_fragment, params)``. For example,
            ``10 / products.price`` would produce ``'(? / [products].[price])'``
            with a parameter list ``[10]``.

        Raises:
            No exceptions are raised by this method itself. Database‑level errors
            (e.g., type mismatch or division by zero) may occur later when the
            expression is executed.

        Example:
            >>> # Assume a Table 'products' with Column 'price' (datatype float)
            >>> inverted = 100 / products.price
            >>> inverted._output
            ('(? / [products].[price])', [100])

            >>> # Use in a query
            >>> products.get_row(
            ...     [products.price, 100 / products.price],
            ...     where=products.id == 1
            ... )
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value / temp_ob

    def __mod__(self, value):
        """Implements the modulo operator (``%``) for a :class:`Column`.

        Generates a :class:`ColumnsOperation` that represents the SQL modulo
        expression (``%`` in SQLite). The column is wrapped in a new
        :class:`ColumnsOperation` with its fully qualified name and an empty
        parameter list, then the modulo operation is applied via
        :meth:`ColumnsOperation.__mod__`. Literal values are parameterized
        with ``?`` placeholders to prevent SQL injection.

        Args:
            value: The divisor for the modulo operation. Can be a
                :class:`Column` (reference to another column), a
                :class:`ColumnsOperation` (a sub‑expression), or a numeric
                literal (:class:`int` or :class:`float`).

        Returns:
            :class:`ColumnsOperation`: An expression object whose
            :attr:`_output` attribute is a tuple
            ``(sql_fragment, params)``. For example, ``col % 3`` produces
            the SQL fragment ``([table_name].[col] % ?)`` and a parameter
            list ``[3]``.

        Example:
            >>> # Assume a Table 'users' with Column 'id' (datatype int)
            >>> remainder = users.id % 2
            >>> remainder._output
            ('([users].[id] % ?)', [2])

            >>> # Use in a query to find odd IDs
            >>> users.get_row(
            ...     [users.id],
            ...     where=remainder == 1
            ... )
        """

        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob % value

    def __rmod__(self, value):
        """Implements the reflected modulo operator (``%``) for a :class:`Column`.

        This method is invoked when the left operand does not support modulo
        with a :class:`Column` object (e.g., ``3 % col``). It creates a
        :class:`ColumnsOperation` that represents the SQL modulo expression
        with the column on the right. The generated SQL uses the ``%``
        operator, and any literal operands are parameterized with ``?`` to
        prevent SQL injection.

        The column is first wrapped in a :class:`ColumnsOperation` whose
        initial SQL fragment is the column's fully qualified name and an
        empty parameter list. Then the reflected modulo is delegated to
        :meth:`ColumnsOperation.__rmod__`.

        Args:
            value: The dividend (left operand) of the modulo operation.
                Can be a :class:`Column` instance, a
                :class:`ColumnsOperation` instance, or a numeric literal
                (:class:`int` or :class:`float`).

        Returns:
            :class:`ColumnsOperation`: An expression object whose
            :attr:`_output` attribute is a tuple
            ``(sql_fragment, params)``. For example, ``3 % col``
            produces the SQL fragment ``(? % [table_name].[col])``
            and a parameter list ``[3]``.

        Example:
            >>> # Assume a Table 'inventory' with Column 'quantity' (datatype int)
            >>> remainder = 10 % inventory.quantity
            >>> remainder._output
            ('(? % [inventory].[quantity])', [10])

            >>> # Use in a query
            >>> inventory.get_row(
            ...     [inventory.id],
            ...     where=remainder == 0
            ... )
        """
     
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value % temp_ob

    def eq(self, value):
        """
        Create an equality comparison expression for this column.

        This method generates a SQL `=` condition, wrapping the column and the
        provided value in a `ColumnsOperation` object. The resulting object can be
        used in WHERE clauses, joins, or other conditional contexts.

        The method supports three types of `value`:
        - Another `Column`: produces `column1 = column2`.
        - A `ColumnsOperation`: produces `column = (expression)` with its parameters.
        - A literal (e.g., int, str, float): produces `column = ?` with the value
        bound as a parameter.

        The returned `ColumnsOperation` holds the SQL fragment and the list of
        bound parameters, suitable for passing to `Table` methods like
        `update()`, `delete_row()`, or `get_row()`.

        Args:
            value (Any): The right-hand side of the equality.
                Can be a `Column`, a `ColumnsOperation`, or a literal value.

        Returns:
            ColumnsOperation: A new operation object representing the equality
            condition `(self = value)`. The object's `_output` attribute is a
            tuple `(sql_expression, parameters)`.

        Example:
            >>> from your_module import Driver, Table, Column
            >>> db = Driver('example.db')
            >>> users = db.users
            >>> age = users.age  # Column instance
            >>> condition = age.eq(25)
            >>> # condition._output -> ('([users].[age] = ?)', [25])
            >>> # Use in a query:
            >>> rows = users.get_row([users.name], where=condition)
        """
        if value is None:
            temp_ob = ColumnsOperation(self)
            temp_ob._output = (f'({self.name} IS NULL)', [])
            return temp_ob
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} = {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} = {value.name})', []) if isinstance(value, Column) else (f'({self.name} = ?)', [value])
        return temp_ob

    def __eq__(self, value):
        """Create an equality comparison condition for the column.

        This method generates a SQL equality expression (`=`) between the column
        and the provided value. The result is a :class:`ColumnsOperation` object
        that can be used in ``WHERE`` clauses of queries, updates, or deletes.
        The method supports comparisons with literals, other :class:`Column`
        objects, and :class:`ColumnsOperation` expressions.

        Args:
            value: The value to compare against. Can be one of:
                - A literal (e.g., ``int``, ``str``, ``float``) – the column
                is compared to that literal.
                - A :class:`Column` – compares the column to another column.
                - A :class:`ColumnsOperation` – compares the column to a
                computed expression.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute holds the SQL string and parameter list for the
            equality comparison. This object can be chained with other
            conditions using logical operators (``&``, ``|``).

        Example:
            Assuming a ``User`` table with columns ``id`` and ``name``::

                from ormophine.Sqlite import Driver, Table

                db = Driver('database.db')
                users = db.users
                name_col = users.name  # a Column instance

                # Compare column to a literal
                condition = name_col == 'Alice'
                # condition._output[0] -> "(users.[name] = ?)"
                # condition._output[1] -> ['Alice']

                # Compare two columns
                id_col = users.id
                condition2 = id_col == name_col
                # condition2._output[0] -> "(users.[id] = users.[name])"
                # condition2._output[1] -> []

                # Use in a query
                results = users.get_row([id_col], where=condition)
                # retrieves rows where name == 'Alice'
        """
        if value is None:
            temp_ob = ColumnsOperation(self)
            temp_ob._output = (f'({self.name} IS NULL)', [])
            return temp_ob
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} = {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} = {value.name})', []) if isinstance(value, Column) else (f'({self.name} = ?)', [value])
        return temp_ob

    def ne(self, value):
        """
        Create a not-equal comparison condition between this column and a value.

        This method generates a SQL `!=` expression that can be used in WHERE clauses.
        The returned `ColumnsOperation` object holds the SQL fragment and its bound
        parameters. It handles comparisons with literal values, other columns, or
        composite expressions (e.g., arithmetic or function calls).

        Args:
            value: The right-hand side of the comparison. Supported types:
                - A literal (e.g., int, float, str, bool): produces a placeholder `?`.
                - A `Column` object: compares column to column using the column's name.
                - A `ColumnsOperation` object: uses the operation's SQL fragment and
                combines its parameters.

        Returns:
            ColumnsOperation: A new operation object representing the `!=` condition.
            The object's internal `_output` attribute is a tuple `(sql_fragment, params)`,
            where `sql_fragment` contains the comparison expression (e.g., `(table.col != ?)`)
            and `params` is the list of bound parameters.

        Example:
            >>> from your_module import Driver, Table, Column
            >>> db = Driver('example.db')
            >>> users = db.users
            >>> age_col = users.age
            >>> condition = age_col.ne(18)   # age != 18
            >>> # Use condition in a query:
            >>> users.get_row([users.name], where=condition)
        """
        if value is None:
            temp_ob = ColumnsOperation(self)
            temp_ob._output = (f'({self.name} IS NOT NULL)', [])
            return temp_ob
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} != {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} != {value.name})', []) if isinstance(value, Column) else (f'({self.name} != ?)', [value])
        return temp_ob

    def __ne__(self, value):
        """Inequality operator (`!=`) for constructing SQL WHERE conditions.

        Generates a SQL inequality comparison between this column and another expression
        or literal value. The result is a :class:`ColumnsOperation` object that can be
        combined with other conditions or used directly in a query's ``WHERE`` clause.

        Args:
            value (Union[Column, ColumnsOperation, Any]): The right-hand side of the
                comparison. Can be another :class:`Column`, a :class:`ColumnsOperation`
                (e.g., from arithmetic or string operations), or a literal value
                (e.g., ``int``, ``str``, ``float``). If a literal is provided, it will
                be used as a parameterized placeholder (``?``) in the generated SQL.

        Returns:
            ColumnsOperation: A :class:`ColumnsOperation` instance whose internal state
            represents the inequality condition ``this_column != value``. This object
            can be used in :meth:`Table.update`, :meth:`Table.delete_row`,
            :meth:`Table.get_row`, and similar methods that accept a ``where``
            parameter.

        Raises:
            TypeError: If the `value` type is not supported (e.g., not a :class:`Column`,
                :class:`ColumnsOperation`, or a literal). The method may fail when
                accessing ``_output`` or ``name`` attributes of unsupported types.

        Example:
            >>> from myorm import Driver, Table, Column
            >>> db = Driver('test.db')
            >>> users = db.users
            >>> age = users.age  # type: Column
            >>> condition = age != 30  # returns ColumnsOperation
            >>> result = users.get_row([users.name], where=condition)
            # Generated SQL: SELECT [users].[name] FROM [users] WHERE ([users].[age] != ?)
        """
        if value is None:
            temp_ob = ColumnsOperation(self)
            temp_ob._output = (f'({self.name} IS NOT NULL)', [])
            return temp_ob
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} != {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} != {value.name})', []) if isinstance(value, Column) else (f'({self.name} != ?)', [value])
        return temp_ob

    def gt(self, value):
        """Construct a SQL condition comparing this column to a value using the greater-than (>) operator.

        This method returns a :class:`ColumnsOperation` object that can be used in WHERE clauses
        or combined with other conditions using logical operators (``&``, ``|``). The comparison
        is applied to the column's stored value. If the column's datatype is not numeric, the
        comparison follows SQLite's rules for the respective type.

        Args:
            value: The value to compare against. Can be one of:
                - A literal (int, float, str, etc.) – will be parameterized as a placeholder.
                - A :class:`Column` object – compares the current column with another column.
                - A :class:`ColumnsOperation` object – compares with a computed expression.

        Returns:
            ColumnsOperation: A new operation object representing the SQL condition
                ``(column > value)``. The object can be chained with other conditions
                or used directly in :meth:`Table.get_row`, :meth:`Table.update`,
                :meth:`Table.delete_row`, etc.

        Example:
            Assuming a table ``users`` with columns ``age`` (Column) and ``name`` (Column)::

                from your_orm import Driver, Column

                db = Driver('example.db')
                users = db.users
                age_col = users.age

                # Compare with a literal
                condition = age_col.gt(18)  # age > 18

                # Compare with another column
                condition2 = age_col.gt(users.min_age)  # age > min_age

                # Use in a query
                rows = users.get_row([users.name], where=condition)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} > {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} > {value.name})', []) if isinstance(value, Column) else (f'({self.name} > ?)', [value])
        return temp_ob

    def __gt__(self, value):
        """Create a greater-than comparison condition for the column.

        This method generates a SQL ">" expression between the column and the provided
        value. The result is a :class:`ColumnsOperation` object that can be used in
        ``WHERE`` clauses of queries, updates, or deletes. The comparison supports
        literals, other :class:`Column` objects, and :class:`ColumnsOperation`
        expressions.

        Args:
            value: The value to compare against. Can be one of:
                - A literal (e.g., ``int``, ``str``, ``float``) – the column
                is compared to that literal.
                - A :class:`Column` – compares the column to another column.
                - A :class:`ColumnsOperation` – compares the column to a
                computed expression.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute holds the SQL string and parameter list for the
            greater-than comparison. This object can be chained with other
            conditions using logical operators (``&``, ``|``).

        Example:
            Assuming a ``Product`` table with columns ``price`` and ``discount``::

                from ormophine.Sqlite import Driver

                db = Driver('store.db')
                products = db.products
                price_col = products.price

                # Compare column to a literal
                condition = price_col > 100
                # condition._output[0] -> "(products.[price] > ?)"
                # condition._output[1] -> [100]

                # Compare two columns
                discount_col = products.discount
                condition2 = price_col > discount_col
                # condition2._output[0] -> "(products.[price] > products.[discount])"

                # Use in a query
                rows = products.get_row([price_col], where=condition)
                # retrieves rows where price > 100
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} > {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} > {value.name})', []) if isinstance(value, Column) else (f'({self.name} > ?)', [value])
        return temp_ob

    def lt(self, value):
        """Create a less-than comparison condition for the column.

        This method generates a SQL less-than expression (`<`) between the column
        and the provided value. The result is a :class:`ColumnsOperation` object
        that can be used in ``WHERE`` clauses of queries, updates, or deletes.
        The method supports comparisons with literals, other :class:`Column`
        objects, and :class:`ColumnsOperation` expressions.

        Args:
            value: The value to compare against. Can be one of:
                - A literal (e.g., ``int``, ``str``, ``float``) – the column
                is compared to that literal.
                - A :class:`Column` – compares the column to another column.
                - A :class:`ColumnsOperation` – compares the column to a
                computed expression.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute holds the SQL string and parameter list for the
            less-than comparison. This object can be chained with other
            conditions using logical operators (``&``, ``|``).

        Example:
            Assuming a ``Product`` table with columns ``price`` and ``discount``::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price_col = products.price
                discount_col = products.discount

                # Compare column to a literal value
                condition = price_col.lt(100)
                # condition._output[0] -> "(products.[price] < ?)"
                # condition._output[1] -> [100]

                # Compare two columns
                condition2 = price_col.lt(discount_col)
                # condition2._output[0] -> "(products.[price] < products.[discount])"
                # condition2._output[1] -> []

                # Use in a query
                results = products.get_row([price_col], where=condition)
                # retrieves rows where price < 100
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} < {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} < {value.name})', []) if isinstance(value, Column) else (f'({self.name} < ?)', [value])
        return temp_ob

    def __lt__(self, value):
        """Create a less-than comparison condition for the column.

        This method generates a SQL less-than expression (`<`) between the column
        and the provided value. The result is a :class:`ColumnsOperation` object
        that can be used in ``WHERE`` clauses of queries, updates, or deletes.
        The method supports comparisons with literals, other :class:`Column`
        objects, and :class:`ColumnsOperation` expressions.

        Args:
            value: The value to compare against. Can be one of:
                - A literal (e.g., ``int``, ``str``, ``float``) – the column
                is compared to that literal.
                - A :class:`Column` – compares the column to another column.
                - A :class:`ColumnsOperation` – compares the column to a
                computed expression.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute holds the SQL string and parameter list for the
            less-than comparison. This object can be chained with other
            conditions using logical operators (``&``, ``|``).

        Example:
            Assuming a ``Product`` table with a ``price`` column::

                from ormophine.Sqlite import Driver

                db = Driver('shop.db')
                products = db.products
                price_col = products.price

                # Compare column to a literal
                condition = price_col < 100
                # condition._output[0] -> "(products.[price] < ?)"
                # condition._output[1] -> [100]

                # Compare two columns
                cost_col = products.cost
                condition2 = price_col < cost_col
                # condition2._output[0] -> "(products.[price] < products.[cost])"

                # Use in a query
                results = products.get_row([price_col], where=condition)
                # retrieves rows where price < 100
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} < {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} < {value.name})', []) if isinstance(value, Column) else (f'({self.name} < ?)', [value])
        return temp_ob

    def ge(self, value):
        """Create a greater-than-or-equal-to (>=) comparison condition for the column.

        This method generates a SQL ``>=`` expression between the column and the
        provided value. The result is a :class:`ColumnsOperation` object that can
        be used in ``WHERE`` clauses of queries, updates, or deletes. The method
        supports comparisons with literals, other :class:`Column` objects, and
        :class:`ColumnsOperation` expressions.

        Args:
            value: The value to compare against. Can be one of:
                - A literal (e.g., ``int``, ``str``, ``float``) – the column
                is compared to that literal.
                - A :class:`Column` – compares the column to another column.
                - A :class:`ColumnsOperation` – compares the column to a
                computed expression.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute holds the SQL string and parameter list for the
            ``>=`` comparison. This object can be chained with other
            conditions using logical operators (``&``, ``|``).

        Example:
            Assuming a ``User`` table with columns ``id`` and ``age``::

                from ormophine.Sqlite import Driver

                db = Driver('database.db')
                users = db.users
                age_col = users.age  # a Column instance

                # Compare column to a literal
                condition = age_col.ge(18)  # or age_col >= 18
                # condition._output[0] -> "(users.[age] >= ?)"
                # condition._output[1] -> [18]

                # Compare two columns
                id_col = users.id
                condition2 = age_col.ge(id_col)
                # condition2._output[0] -> "(users.[age] >= users.[id])"
                # condition2._output[1] -> []

                # Use in a query
                results = users.get_row([id_col], where=condition)
                # retrieves rows where age >= 18
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} >= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} >= {value.name})', []) if isinstance(value, Column) else (f'({self.name} >= ?)', [value])
        return temp_ob

    def __ge__(self, value):
        """Create a greater-than-or-equal-to comparison condition for the column.

        This method generates a SQL `>=` (greater than or equal) expression
        between the column and the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses
        of queries, updates, or deletes. The method supports comparisons with
        literals, other :class:`Column` objects, and :class:`ColumnsOperation`
        expressions.

        Args:
            value: The value to compare against. Can be one of:
                - A literal (e.g., ``int``, ``str``, ``float``) – the column
                is compared to that literal.
                - A :class:`Column` – compares the column to another column.
                - A :class:`ColumnsOperation` – compares the column to a
                computed expression.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute holds the SQL string and parameter list for the
            ``>=`` comparison. This object can be chained with other
            conditions using logical operators (``&``, ``|``).

        Example:
            Assuming a ``Product`` table with columns ``price`` and
            ``discount``::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price_col = products.price
                discount_col = products.discount

                # Compare column to a literal
                condition1 = price_col >= 100
                # condition1._output[0] -> "(products.[price] >= ?)"
                # condition1._output[1] -> [100]

                # Compare two columns
                condition2 = price_col >= discount_col
                # condition2._output[0] -> "(products.[price] >= products.[discount])"
                # condition2._output[1] -> []

                # Use in a query
                results = products.get_row([price_col, discount_col],
                                        where=condition1)
                # retrieves rows where price >= 100
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} >= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} >= {value.name})', []) if isinstance(value, Column) else (f'({self.name} >= ?)', [value])
        return temp_ob

    def le(self, value):
        """Create a less-than-or-equal-to comparison condition for the column.

        This method generates a SQL ``<=`` (less than or equal) comparison expression
        between the column and the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses of
        queries, updates, or deletes. The method supports comparisons with literals,
        other :class:`Column` objects, and :class:`ColumnsOperation` expressions.

        Args:
            value: The value to compare against. Can be one of:
                - A literal (e.g., ``int``, ``str``, ``float``) – the column is
                compared to that literal.
                - A :class:`Column` – compares the column to another column.
                - A :class:`ColumnsOperation` – compares the column to a computed
                expression.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute holds the SQL string and parameter list for the
            less-than-or-equal comparison. This object can be chained with other
            conditions using logical operators (``&``, ``|``).

        Example:
            Assuming a ``Product`` table with columns ``price`` and ``discount``::

                from ormophine.Sqlite import Driver

                db = Driver('store.db')
                products = db.products
                price_col = products.price

                # Compare column to a literal
                condition = price_col <= 100.0
                # condition._output[0] -> "(products.[price] <= ?)"
                # condition._output[1] -> [100.0]

                # Compare two columns
                discount_col = products.discount
                condition2 = price_col <= discount_col
                # condition2._output[0] -> "(products.[price] <= products.[discount])"
                # condition2._output[1] -> []

                # Use in a query
                results = products.get_row([price_col], where=condition)
                # retrieves products with price <= 100.0
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} <= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} <= {value.name})', []) if isinstance(value, Column) else (f'({self.name} <= ?)', [value])
        return temp_ob

    def __le__(self, value):
        """Create a less-than-or-equal-to comparison condition for the column.

        This method generates a SQL `<=` (less than or equal) expression
        between the column and the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses
        of queries, updates, or deletes. The method supports comparisons with
        literals, other :class:`Column` objects, and :class:`ColumnsOperation`
        expressions.

        Args:
            value: The value to compare against. Can be one of:
                - A literal (e.g., ``int``, ``str``, ``float``) – the column
                is compared to that literal.
                - A :class:`Column` – compares the column to another column.
                - A :class:`ColumnsOperation` – compares the column to a
                computed expression.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute holds the SQL string and parameter list for the
            ``<=`` comparison. This object can be chained with other
            conditions using logical operators (``&``, ``|``).

        Example:
            Assuming a ``Product`` table with columns ``price`` and
            ``discount``::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price_col = products.price
                discount_col = products.discount

                # Compare column to a literal
                condition1 = price_col <= 100
                # condition1._output[0] -> "(products.[price] <= ?)"
                # condition1._output[1] -> [100]

                # Compare two columns
                condition2 = price_col <= discount_col
                # condition2._output[0] -> "(products.[price] <= products.[discount])"
                # condition2._output[1] -> []

                # Use in a query
                results = products.get_row([price_col, discount_col],
                                        where=condition1)
                # retrieves rows where price <= 100
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} <= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} <= {value.name})', []) if isinstance(value, Column) else (f'({self.name} <= ?)', [value])
        return temp_ob

    def __getitem__(self, key: slice):
        """Just like python slicing, generate a SQL substring expression for slicing a text column.

        This method enables Python-style slicing on :class:`Column` objects,
        translating slice operations into SQLite ``substr()`` function calls.
        It supports both positive and negative indices, as well as open-ended
        slices. The resulting :class:`ColumnsOperation` object can be used in
        queries, updates, or as part of larger expressions.

        The slicing behavior mimics Python string slicing with SQL semantics:
        - ``column[0:5]`` → ``substr(column, 1, 5)`` (1‑based indexing)
        - ``column[2:]`` → ``substr(column, 3, length(column))``
        - ``column[:-2]`` → ``substr(column, 1, length(column)-1)`` (excludes last two chars)
        - Negative indices are converted to offsets from the end:
        ``column[-3:]`` → ``substr(column, length(column)-2, length(column))``
        - End index is exclusive: ``column[0:3]`` takes characters at positions 0,1,2.

        The method adjusts indices because SQLite ``substr()`` uses 1‑based
        indexing and inclusive end positions, whereas Python uses 0‑based and
        exclusive end. The implementation handles the conversion transparently.

        Args:
            key (slice): A slice object specifying the start and stop positions.
                Both ``start`` and ``stop`` can be ``None``, positive, or negative
                integers. Step values are ignored (not supported by SQLite).

        Returns:
            :class:`ColumnsOperation`: An operation object whose ``_output``
            attribute contains the SQL substring expression and the list of
            bound parameters (if any). The expression can be chained with
            other operations or used in conditions.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver

                db = Driver('database.db')
                users = db.users
                name_col = users.name

                # Get first 3 characters
                expr = name_col[:3]
                # expr._output[0] -> "substr(users.[name] , 1 , 3)"
                # expr._output[1] -> []

                # Get from position 2 to end
                expr2 = name_col[2:]
                # expr2._output[0] -> "substr(users.[name] , 3 , length(users.[name]))"

                # Get last 4 characters (equivalent to name[-4:])
                expr3 = name_col[-4:]
                # expr3._output[0] -> "substr(users.[name] , length(users.[name]) - 3 , length(users.[name]))"
                # expr3._output[1] -> []

                # Use in a query
                condition = name_col[:3] == 'Joh'
                results = users.get_row([name_col], where=condition)
                # retrieves users whose name starts with 'Joh'
        """

        temp_ob = ColumnsOperation(self)
        if key.start == None and key.stop ==  None:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , 0 , length({temp_ob.col_obj.name}) + 1))', [])   #
        elif key.start == None and key.stop < 0:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , 0 , length({temp_ob.col_obj.name}) - ?))', [abs(key.stop) - 1])  #
        elif key.start == None and key.stop >= 0:
             temp_ob._output = (f'(substr({temp_ob.col_obj.name} , 0 , ?))', [key.stop + 1])  #  
        elif key.start >= 0 and key.stop ==  None:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , ? , length({temp_ob.col_obj.name})))', [key.start + 1])  #   
        elif key.start < 0 and key.stop == None:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , length({temp_ob.col_obj.name}) - ? , length({temp_ob.col_obj.name})))', [abs(key.start) - 1])  #
        elif key.start >= 0 and key.stop < 0:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , ? , length({temp_ob.col_obj.name}) - ?))', [key.start + 1, abs(key.stop - key.start)])  #  
        elif key.start >= 0 and key.stop > 0:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , ? , ?))', [key.start + 1, key.stop - key.start])  #
        elif key.start < 0 and key.stop < 0:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , length({temp_ob.col_obj.name}) - ? , ?))', [abs(key.start) - 1, key.stop - key.start])  #
        elif key.start < 0 and key.stop > 0:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , length({temp_ob.col_obj.name}) - ? ,  ? - (length({temp_ob.col_obj.name}) - ?)))', [abs(key.start) - 1, key.stop, abs(key.start)])
        return temp_ob

    def strip(self, chars: str = ' '):
        """Just like python strip(), return a :class:`ColumnsOperation` that applies SQLite's ``trim()`` function to the column.

        The ``trim()`` function removes all characters specified in ``chars`` from both the
        beginning and end of the column's string value. By default, it strips spaces.

        This method is chainable and returns a :class:`ColumnsOperation` object that can be
        used in queries, updates, or as part of larger expressions.

        Args:
            chars (str, optional): A string of characters to remove from both ends.
                Defaults to a single space.

        Returns:
            :class:`ColumnsOperation`: An operation object representing the ``trim()``
            expression. Its ``_output`` attribute contains the SQL string and parameter list.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver

                db = Driver('my.db')
                users = db.users
                name = users.name

                # Strip spaces from both ends
                trimmed = name.strip()
                # trimmed._output[0] -> "trim(users.[name],' ')"
                # trimmed._output[1] -> []

                # Strip specific characters (e.g., underscores and dashes)
                cleaned = name.strip('_-')
                # cleaned._output[0] -> "trim(users.[name],'_-')"

                # Use in a SELECT query
                result = users.get_row([trimmed], where=name.contains('john'))
                # returns rows where the trimmed name contains 'john'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(trim({temp_ob._output[0]},"{chars}"))', temp_ob._output[1]) if temp_ob._output else (f'(trim({temp_ob.col_obj.name},"{chars}"))', [])
        return temp_ob

    def lstrip(self, chars: str = ' '):
        """Just like python lstrip(), remove leading characters from the column value using SQLite's LTRIM function.

        This method creates a :class:`ColumnsOperation` object that represents
        the SQL ``LTRIM()`` expression applied to the column (or to the current
        expression chain). The ``LTRIM`` function removes all occurrences of the
        specified characters from the beginning of the string. If no characters
        are specified, it removes spaces by default.

        If the column has already been part of an expression (e.g., arithmetic or
        string concatenation), the operation is applied to the existing expression
        output. Otherwise, it is applied directly to the column.

        Args:
            chars (str, optional): A string of characters to remove from the start
                of the string. Defaults to a single space ``' '``. To remove
                multiple different characters, pass them as a single string, e.g.,
                ``'_-'`` will strip underscores and hyphens.

        Returns:
            :class:`ColumnsOperation`: A new operation object representing the
            ``LTRIM`` expression. The object's ``_output`` attribute contains
            the SQL string and parameter list for use in queries.

        Example:
            Assuming a ``users`` table with a column ``username`` that may have
            leading spaces or special characters::

                from ormophine.Sqlite import Driver, Table

                db = Driver('my.db')
                users = db.users
                username = users.username

                # Remove leading spaces (default)
                trimmed = username.lstrip()
                # trimmed._output[0] -> "ltrim(users.[username],' ')"
                # trimmed._output[1] -> []

                # Remove leading underscores and hyphens
                trimmed_custom = username.lstrip('_-')
                # trimmed_custom._output[0] -> "ltrim(users.[username],'_-')"

                # Use in a query to get cleaned usernames
                results = users.get_row([trimmed], where=username != '')
                # retrieves rows with usernames trimmed on the left
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(trim({temp_ob._output[0]},"{chars}"))', temp_ob._output[1]) if temp_ob._output else (f'(trim({temp_ob.col_obj.name},"{chars}"))', [])
        return temp_ob

    def rstrip(self, chars: str = ' '):
        """Just like python rstrip(), remove trailing characters from the column's string value.

        This method generates an SQL `rtrim` expression that strips specified
        characters from the right end of the column's string. The result is a
        :class:`ColumnsOperation` object that can be used in queries, updates,
        or as part of larger expressions.

        Args:
            chars (str, optional): A string containing the characters to remove
                from the right side of the column value. Defaults to a single
                space (``' '``).

        Returns:
            :class:`ColumnsOperation`: An operation object whose ``_output``
            attribute holds the SQL string and parameter list for the
            ``rtrim`` function call. This object can be chained with other
            operations or conditions.

        Example:
            Assuming a ``Product`` table with a ``name`` column::

                from ormophine.Sqlite import Driver

                db = Driver('store.db')
                products = db.products
                name_col = products.name

                # Remove trailing spaces
                clean_expression = name_col.rstrip()
                # clean_expression._output[0] -> "rtrim(products.[name],' ')"

                # Remove trailing hyphens and underscores
                clean_expression2 = name_col.rstrip('-_')
                # clean_expression2._output[0] -> "rtrim(products.[name],'-_')"

                # Use in an update to sanitize data
                products.update({name_col: name_col.rstrip()},
                                where=name_col.like('% '))
                # Updates rows where name ends with a space.
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(rtrim({temp_ob._output[0]},"{chars}"))', temp_ob._output[1]) if temp_ob._output else (f'(rtrim({temp_ob.col_obj.name},"{chars}"))', [])
        return temp_ob

    def add_end(self, content):
        """Append content to the end of the column's value.

        This method generates a SQL string concatenation expression using the
        ``||`` operator, combining the column's value with the provided content
        at the end. The result is a :class:`ColumnsOperation` object that can be
        used in queries, updates, or other expressions. The content can be a
        literal value, another :class:`Column`, or a :class:`ColumnsOperation`
        expression.

        Args:
            content: The content to append. Can be one of:
                - A literal (``str``, ``int``, etc.) – the value is bound as a
                parameter.
                - A :class:`Column` – the column's value is concatenated.
                - A :class:`ColumnsOperation` – the result of that expression
                is concatenated.

        Returns:
            :class:`ColumnsOperation`: An operation object whose ``_output``
            attribute holds the SQL expression string and parameter list for
            the concatenation. This object can be further chained with other
            operations or used in conditions.

        Example:
            Assuming a ``users`` table with a ``full_name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.full_name

                # Append a suffix to the column value
                expr = name_col.add_end(' Jr.')
                # expr._output[0] -> "(users.[full_name] || ?)"
                # expr._output[1] -> [' Jr.']

                # Use in a query to retrieve concatenated value
                results = users.get_row([expr])
                # returns rows with full_name + ' Jr.'
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} || {content._output[0]})', [content._output[1]]) if isinstance(content, ColumnsOperation) else (f'({self.name} || {content.name})', []) if isinstance(content, Column) else (f'({self.name} || ?)', [content])
        return temp_ob

    def add_first(self, content):
        """Prepend content to the column value in a SQL string concatenation.

        This method generates a SQL expression that concatenates the given
        ``content`` before the column's value using the ``||`` operator.
        The result is a :class:`ColumnsOperation` object that can be embedded
        in ``SELECT``, ``WHERE``, or other SQL clauses. The method supports
        various input types:

        * A literal (e.g., ``str``, ``int``) – the literal is used as-is.
        * A :class:`Column` – concatenates the other column's value.
        * A :class:`ColumnsOperation` – concatenates a computed expression.

        The method is useful for building dynamic strings, such as prefixes,
        in SQL queries.

        Args:
            content: The content to prepend to the column's value. Can be one of:
                - A literal (``str``, ``int``, ``float``, etc.)
                - A :class:`Column` object
                - A :class:`ColumnsOperation` expression

        Returns:
            :class:`ColumnsOperation`: An expression object whose ``_output``
            attribute contains the SQL string and parameter list for the
            concatenation. The SQL uses the form ``(? || column)`` for literals,
            or the appropriate column/expression references.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Prepend a literal prefix
                expr = name_col.add_first('Mr. ')
                # expr._output[0] -> "(? || users.[name])"
                # expr._output[1] -> ['Mr. ']

                # Prepend another column's value
                prefix_col = users.title
                expr2 = name_col.add_first(prefix_col)
                # expr2._output[0] -> "(users.[title] || users.[name])"

                # Use in a query
                result = users.get_row([expr], where=users.id == 1)
                # retrieves the concatenated string for the user with id=1
        """

        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({content._output[0]} || {self.name})', [content._output[1]]) if isinstance(content, ColumnsOperation) else (f'({content.name} || {self.name})', []) if isinstance(content, Column) else (f'(? || {self.name})', [content])
        return temp_ob
    
    def lower(self):
        """Just like python lower(), convert the column value to lowercase in SQL.

        This method generates a SQL expression that applies the ``LOWER``
        function to the column's value. The result is a
        :class:`ColumnsOperation` object that can be used in ``SELECT``,
        ``WHERE``, or other SQL clauses to perform case‑insensitive
        comparisons or transformations.

        The returned operation can be chained with other operations (e.g.,
        :meth:`~ColumnsOperation.startswith`, :meth:`~ColumnsOperation.like`)
        or combined with logical operators (``&``, ``|``).

        Returns:
            :class:`ColumnsOperation`: An expression object whose ``_output``
            attribute contains the SQL string for the ``LOWER`` function call
            (e.g., ``lower(users.[name])``) and an empty parameter list.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Create a condition for case‑insensitive equality
                condition = name_col.lower() == 'alice'
                # condition._output[0] -> "(lower(users.[name]) = ?)"
                # condition._output[1] -> ['alice']

                # Retrieve users whose name is 'alice' (case‑insensitive)
                results = users.get_row([name_col], where=condition)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(lower({temp_ob._output[0]}))', temp_ob._output[1]) if temp_ob._output else (f'(lower({temp_ob.col_obj.name}))', [])
        return temp_ob

    def upper(self):
        """Just like python upper(), convert the column value to uppercase in SQL.

        This method generates a SQL `UPPER()` function call on the column's
        value, converting all characters to uppercase. The result is a
        :class:`ColumnsOperation` object that can be used in ``SELECT``,
        ``WHERE``, or other SQL clauses.

        Returns:
            :class:`ColumnsOperation`: An expression object whose ``_output``
            attribute contains the SQL string and parameter list for the
            `UPPER()` function call.

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Create uppercase expression
                expr = name_col.upper()
                # expr._output[0] -> "upper(users.[name])"
                # expr._output[1] -> []

                # Use in a query
                results = users.get_row([expr], where=users.id == 1)
                # retrieves the uppercase name for the user with id=1
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(upper({temp_ob._output[0]}))', temp_ob._output[1]) if temp_ob._output else (f'(upper({temp_ob.col_obj.name}))', [])
        return temp_ob

    def replace(self, old, new):
        """Just like python replace(), replace occurrences of a substring within the column's value.

        This method generates a SQL expression that uses the ``replace()``
        function to substitute all occurrences of ``old`` with ``new``
        in the column's string value. The result is a
        :class:`ColumnsOperation` object that can be used in ``SELECT`` or
        other SQL clauses. The replacement is performed on the database side.

        The method automatically handles both simple column references and
        previously built expressions (e.g., after concatenation or substring
        operations) thanks to the internal state of the
        :class:`ColumnsOperation`.

        Args:
            old (str): The substring to be replaced. This is passed as a
                bound parameter (``?``) in the SQL.
            new (str): The replacement string. Also passed as a bound parameter.

        Returns:
            :class:`ColumnsOperation`: An expression object whose ``_output``
            attribute contains the SQL string and parameter list for the
            ``replace()`` call. The SQL string is either ``replace(column, ?, ?)``
            or ``replace(expression, ?, ?)`` if the operation was chained.
            The parameter list includes the ``old`` and ``new`` values.

        Example:
            Assuming a ``users`` table with a ``bio`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                bio_col = users.bio

                # Replace 'foo' with 'bar' in the bio column
                expr = bio_col.replace('foo', 'bar')
                # expr._output[0] -> "replace(users.[bio] , ? , ?)"
                # expr._output[1] -> ['foo', 'bar']

                # Chain with a substring operation
                expr2 = bio_col[0:10].replace('x', 'y')
                # expr2._output[0] -> "replace(substr(users.[bio] , ? , ?) , ? , ?)"
                # expr2._output[1] -> [1, 10, 'x', 'y']

                # Use in a SELECT query
                result = users.get_row([expr], where=users.id == 1)
                # retrieves the transformed bio for user with id=1
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(replace({temp_ob._output[0]} , ? , ?))', temp_ob._output[1] + [old, new]) if temp_ob._output else (f'(replace({temp_ob.col_obj.name} , ? , ?))', [old, new])
        return temp_ob

    def like(self, value):
        """Create a SQL `LIKE` pattern-matching condition for the column.

        This method generates a SQL expression of the form ``column LIKE pattern``,
        where the pattern can be a literal string, another column, or a computed
        expression. The result is a :class:`ColumnsOperation` object suitable for
        use in ``WHERE`` clauses of queries, updates, or deletes.

        The method supports three types of input:

        * A literal (``str``, ``int``, etc.) – the literal is used as the pattern,
        with appropriate escaping and parameter binding.
        * A :class:`Column` – the pattern is taken from another column's value.
        * A :class:`ColumnsOperation` – the pattern is a computed expression.

        The SQL `LIKE` operator is case-sensitive by default in SQLite; to perform
        case-insensitive matches, use the `upper()` or `lower()` functions on both
        sides.

        Args:
            value: The pattern to match against. Can be one of:
                - A literal (e.g., ``'%john%'``) – the pattern is bound as a
                parameter.
                - A :class:`Column` – the pattern is the value of another column.
                - A :class:`ColumnsOperation` – the pattern is a computed expression.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute holds the SQL string and parameter list for the `LIKE`
            comparison. The SQL is typically of the form
            ``(column LIKE ?)`` or ``(column LIKE other_column)``.

        Example:
            Assuming a ``users`` table with columns ``name`` and ``search_pattern``::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Match names containing 'john' (case-sensitive)
                condition = name_col.like('%john%')
                # condition._output[0] -> "(users.[name] like ?)"
                # condition._output[1] -> ['%john%']

                # Use another column as the pattern
                pattern_col = users.search_pattern
                condition2 = name_col.like(pattern_col)
                # condition2._output[0] -> "(users.[name] like users.[search_pattern])"

                # Combine with other conditions
                full_condition = condition & (users.id >= 100)
                results = users.get_row([name_col], where=full_condition)
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like {value._output[0]})", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} like {value.name})', temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f'({self.name} like ?)', (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def startswith(self, value):
        """Just like python startswith(), create a SQL ``LIKE`` condition to check if the column starts with a prefix.

        This method generates a ``LIKE`` expression with the pattern ``prefix || '%'``,
        where ``prefix`` is the provided value. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses.
        The method supports three types of input:

        * A literal (e.g., ``str``, ``int``) – the literal is used as the prefix.
        * A :class:`Column` – the column's value is used as the prefix.
        * A :class:`ColumnsOperation` – the computed expression is used as the prefix.

        The generated SQL uses the ``||`` concatenation operator to append the
        wildcard ``%``.

        Args:
            value: The prefix to test against. Can be one of:
                - A literal (e.g., ``'John'``) – the column value is compared
                to ``'John%'``.
                - A :class:`Column` – compares the column to the concatenation
                of that column's value and ``'%'``.
                - A :class:`ColumnsOperation` – compares the column to the
                concatenation of the expression's result and ``'%'``.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute contains the SQL string and parameter list for the
            ``LIKE`` comparison. This object can be chained with other
            conditions using logical operators (``&``, ``|``).

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Find users whose names start with 'Jo'
                condition = name_col.startswith('Jo')
                # condition._output[0] -> "(users.[name] like ? || '%')"
                # condition._output[1] -> ['Jo']

                # Use in a query
                results = users.get_row([name_col], where=condition)
                # retrieves rows where name LIKE 'Jo%'

                # Using another column as the prefix
                prefix_col = users.prefix
                condition2 = name_col.startswith(prefix_col)
                # condition2._output[0] -> "(users.[name] like users.[prefix] || '%')"
        """        
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like {value._output[0]} || '%')", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self.name} like {value.name} || '%')", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"({self.name} like ? || '%')", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def endswith(self, value):
        """Create a condition that checks if the column's value ends with a given suffix.

        This method generates a SQL `LIKE` expression that tests whether the column's
        text value ends with the specified suffix. The result is a
        :class:`ColumnsOperation` object that can be used in ``WHERE`` clauses.
        The suffix can be a literal string, another :class:`Column`, or a
        :class:`ColumnsOperation` expression.

        The generated SQL uses the pattern ``'%' || suffix``, which matches any
        string ending with the given suffix.

        Args:
            value: The suffix to match. Can be one of:
                - A literal (``str``, ``int``, etc.) – the suffix is bound as a parameter.
                - A :class:`Column` – the suffix is taken from another column's value.
                - A :class:`ColumnsOperation` – the suffix is computed from an expression.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute holds the SQL string and parameter list for the ``LIKE``
            comparison. This object can be combined with other conditions using
            logical operators.

        Example:
            Assuming a ``users`` table with a ``email`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                email_col = users.email

                # Check if email ends with '@example.com'
                condition = email_col.endswith('@example.com')
                # condition._output[0] -> "users.[email] like '%' || ?"
                # condition._output[1] -> ['@example.com']

                # Use in a query
                results = users.get_row([email_col], where=condition)
                # retrieves rows where email ends with '@example.com'

                # Compare with another column
                suffix_col = users.domain_suffix
                condition2 = email_col.endswith(suffix_col)
                # condition2._output[0] -> "users.[email] like '%' || users.[domain_suffix]"
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like '%' || {value._output[0]})", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self.name} like '%' || {value.name})", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"({self.name} like '%' || ?)", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def In(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"{self.name} IN ({value._output[0]})", value._output[1]) if isinstance(value, ColumnsOperation) else (f"{self.name} IN ({','.join(['?'] * len(value))})", list(value)) if isinstance(value, (list, tuple)) else (f"{self.name} = ?", [value])
        return temp_ob

    def contains(self, value):
        """Create a SQL ``LIKE`` condition to check if the column contains a substring.

        This method generates a ``LIKE`` expression with the pattern
        ``'%' || substring || '%'``, where the substring is the provided value.
        The result is a :class:`ColumnsOperation` object that can be used in
        ``WHERE`` clauses. The method supports three types of input:

        * A literal (e.g., ``str``, ``int``) – the literal is used as the substring.
        * A :class:`Column` – the column's value is used as the substring.
        * A :class:`ColumnsOperation` – the computed expression is used as the substring.

        The generated SQL uses the ``||`` concatenation operator to surround the
        substring with wildcards ``%``.

        Args:
            value: The substring to search for. Can be one of:
                - A literal (e.g., ``'John'``) – the column value must contain
                ``'John'``.
                - A :class:`Column` – compares the column to the concatenation
                of ``'%'``, that column's value, and ``'%'``.
                - A :class:`ColumnsOperation` – compares the column to the
                concatenation of ``'%'``, the expression's result, and ``'%'``.

        Returns:
            :class:`ColumnsOperation`: A condition object whose ``_output``
            attribute contains the SQL string and parameter list for the
            ``LIKE`` comparison. This object can be chained with other
            conditions using logical operators (``&``, ``|``).

        Example:
            Assuming a ``users`` table with a ``name`` column::

                from ormophine.Sqlite import Driver, Table

                db = Driver('app.db')
                users = db.users
                name_col = users.name

                # Find users whose names contain 'son'
                condition = name_col.contains('son')
                # condition._output[0] -> "(users.[name] like '%' || ? || '%')"
                # condition._output[1] -> ['son']

                # Use in a query
                results = users.get_row([name_col], where=condition)
                # retrieves rows where name LIKE '%son%'

                # Using another column as the substring
                substr_col = users.search_term
                condition2 = name_col.contains(substr_col)
                # condition2._output[0] -> "(users.[name] like '%' || users.[search_term] || '%')"
        """
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like '%' || {value._output[0]} || '%')", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self.name} like '%' || {value.name} || '%')", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"({self.name} like '%' || ? || '%')", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def rename(self, new_name: str) -> None:
        """Rename the column in the database schema.

        This method executes an ``ALTER TABLE RENAME COLUMN`` statement to change
        the column's name in the underlying SQLite table. After the schema change,
        the corresponding :class:`Column` attribute on the :class:`Table` object
        is replaced with a new :class:`Column` instance reflecting the updated name,
        preserving the original data type.

        The operation is performed through the thread‑safe queue mechanism of the
        ORM, and any SQL error will raise an exception.

        Args:
            new_name (str): The new name for the column. Must be a valid SQLite
                identifier (e.g., no spaces or special characters unless quoted).

        Raises:
            Exception: If the database operation fails (e.g., due to a duplicate
                column name, constraint violation, or connection error). The
                exception message is propagated from the underlying SQLite driver.

        Example:
            Assuming a ``users`` table with a column named ``user_name``::

                from ormophine.Sqlite import Driver

                db = Driver('app.db')
                users = db.users
                old_col = users.user_name

                # Rename the column from 'user_name' to 'full_name'
                old_col.rename('full_name')

                # The attribute is updated: `users.full_name` now exists
                new_col = users.full_name
                assert new_col.datatype == old_col.datatype

                # The old attribute is removed
                # users.user_name  # raises AttributeError
        """

        query = f'ALTER TABLE {self.table_obj.name_} RENAME COLUMN {self.first_name} TO [{new_name}];'
        queue_call_back = SimpleQueue()
        self.table_obj.main_queue.put(['qcb', (query,), queue_call_back])
        if not (callback := queue_call_back.get(block=True))[0]:
            raise Exception(callback[1])
        self.table_obj.__delattr__(self.first_name[1:-1])
        self.table_obj.__setattr__(new_name, Column(self.table_obj, new_name, self.datatype))

    def delete_column(self, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool) -> None:
        """Permanently delete this column from the database table.

        This method executes an ``ALTER TABLE ... DROP COLUMN`` SQL statement
        to remove the column from the table. Because column deletion is a
        destructive operation that cannot be undone, the method requires three
        explicit confirmation flags to be set to ``True``. If any of them is
        ``False``, the operation is silently skipped.

        After a successful deletion, the column attribute is removed from the
        parent :class:`Table` object to keep the Python representation in sync
        with the database schema.

        Args:
            are_you_sure (bool): First confirmation flag. Must be ``True``.
            are_you_really_sure (bool): Second confirmation flag. Must be ``True``.
            for_sure (bool): Third confirmation flag. Must be ``True``.

        Returns:
            None

        Raises:
            Exception: If the SQL execution fails (e.g., due to a foreign key
                constraint or an invalid column), an exception is raised with
                the underlying database error message.

        Example:
            Assuming a ``users`` table with an ``age`` column::

                from ormophine.Sqlite import Driver

                db = Driver('myapp.db')
                users = db.users
                age_col = users.age

                # Delete the column (requires triple confirmation)
                age_col.delete_column(True, True, True)

                # Now the column is removed from the table and the attribute
                # is gone:
                # hasattr(users, 'age') -> False

                # If any flag is False, nothing happens:
                age_col.delete_column(True, False, True)  # no effect
        """
        if are_you_sure and are_you_really_sure and for_sure:
            query = f'ALTER TABLE {self.table_obj.name_} DROP COLUMN {self.first_name};'
            queue_call_back = SimpleQueue()
            self.table_obj.main_queue.put(['qcb', (query,), queue_call_back])
            if not (callback := queue_call_back.get(block=True))[0]:
                raise Exception(callback[1])
            self.table_obj.__delattr__(self.first_name[1:-1])

    def In(self, column: 'Ormophine.Sqlite.Column|Ormophine.Sqlite.ColumnsOperation' = None, where: 'Ormophine.Sqlite.ColumnsOperation' = None, data_list: list = None):
        """Build an SQL ``IN`` clause for the current column.

        This method serves as an entry point for the :class:`Ormophine.Sqlite.ColumnsOperation`
        ``In`` method. It initialises a :class:`Ormophine.Sqlite.ColumnsOperation` with the
        current column's name and delegates the execution to it, enabling
        seamless method chaining.

        Supports two modes:
        * Passing a list of literal values to ``data_list`` (or as the first
          positional argument for backward compatibility).
        * Passing a single :class:`Column`/:class:`Ormophine.Sqlite.ColumnsOperation` to
          ``column`` to build a ``SELECT`` subquery, with an optional
          ``where`` condition.

        Args:
            column: A single :class:`Column` or
                :class:`Ormophine.Sqlite.ColumnsOperation` to use in the ``SELECT`` clause of
                the subquery. If a list of literals is passed, it is treated
                as ``data_list``.
            where: An optional :class:`Ormophine.Sqlite.ColumnsOperation` (or :class:`Column`)
                representing the ``WHERE`` condition for the subquery.
            data_list: A list of literal values for a direct ``IN`` clause.

        Returns:
            :class:`Ormophine.Sqlite.ColumnsOperation`: A :class:`Ormophine.Sqlite.ColumnsOperation` instance
            representing the ``IN`` clause, allowing further chaining.

        Raises:
            Exception: If neither ``data_list`` nor a valid ``column``
                is provided to the underlying :class:`Ormophine.Sqlite.ColumnsOperation` method.

        Example:
            Assuming ``users`` and ``admins`` tables::

                from ormophine.Sqlite import Driver

                db = Driver('app.db')
                users = db.users
                admins = db.admins

                # Literal list
                cond1 = users.age.In([25, 30, 35])

                # Subquery
                cond2 = users.name.In(
                    column=admins.username,
                    where=admins.active == True
                )

                # Use in a query
                result = users.get_row([users.name], where=cond2)
        """
        op = ColumnsOperation(self)
        op._output = (self.name, [])
        return op.In(column=column, where=where, data_list=data_list)
        

class BatchOperation:
    """
    A builder for atomic batch SQL operations.

    This class accumulates multiple SQL statements (INSERT and UPDATE)
    and executes them together as a single transaction via the
    :meth:`run` method. If any operation fails, the entire batch is
    rolled back, ensuring data consistency.

    Typical usage involves chaining :meth:`update` and :meth:`insert`
    calls, then executing with :meth:`run`. The class maintains an
    internal script list that is sent to the database thread for
    execution.

    Attributes:
        script (list): A list of SQL statement/parameter pairs
            representing the accumulated operations. Each element is a
            list in the form ``[sql_string, parameters]``.
        table_obj (Table): The :class:`Table` instance associated with
            this batch operation. Used to access the main database queue.

    Example:
        Assuming a ``users`` table with columns ``name`` and ``age``::

            from ormophine.Sqlite import Driver, Table

            db = Driver('app.db')
            users = db.users
            name_col = users.name
            age_col = users.age

            # Create a batch operation
            batch = users.batch()

            # Chain multiple operations
            batch.update({age_col: age_col + 1}, age_col >= 18)
            batch.update({name_col: name_col.upper()}, name_col.startswith('a'))
            batch.insert({name_col: 'Alice', age_col: 30})

            # Execute atomically
            batch.run()
            # All operations are committed as one transaction.
    """
    
    def __init__(self, table_object: Table):
        """Initialize a new batch operation builder for a specific table.

        The :class:`BatchOperation` class allows you to group multiple
        ``UPDATE`` and ``INSERT`` statements into a single script that
        is executed atomically in one transaction. This constructor
        creates a new batch builder associated with a given table.

        The batch is stored internally as a list of script items, each
        being a list of ``[sql, parameters]``. You can chain
        :meth:`update` and :meth:`insert` calls to build the script,
        then execute all statements with :meth:`run`.

        Args:
            table_object (Table): The table on which the batch operations
                will be performed. This table is used as the default target
                for operations unless overridden by providing a different
                table to :meth:`update` or :meth:`insert`.

        Example:
            Assuming a ``products`` table with columns ``id``, ``name``,
            and ``price``::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products

                # Create a batch for products
                batch = products.batch()

                # Add multiple operations
                batch.insert({products.name: 'Laptop', products.price: 999})
                batch.update({products.price: 899}, where=products.id == 1)
                batch.insert({products.name: 'Mouse', products.price: 29})

                # Execute all at once
                batch.run()
        """
        self.script = []
        self.table_obj = table_object

    def update(self, update: dict[Column, Any], where: ColumnsOperation, table: Table = None) -> 'BatchOperation':
        """Add an UPDATE statement to the batch script.

        This method appends a parameterized UPDATE SQL statement to the batch
        operation script. The statement updates the specified columns with new
        values for rows that match the given condition.

        The ``update`` dictionary maps :class:`Column` objects to their new values.
        Each value can be:

        * A literal (e.g., ``int``, ``str``, ``float``) – used as a parameter
        placeholder (``?``) in the SQL.
        * A :class:`Column` – the column's value is used as the source (e.g.,
        ``column1 = column2``).
        * A :class:`ColumnsOperation` – a computed expression (e.g., ``price + 5``)
        is embedded in the SQL.

        The ``where`` condition is a :class:`ColumnsOperation` that specifies which
        rows to update. If a different table should be updated (instead of the one
        associated with the batch object), it can be provided via the ``table``
        parameter.

        Args:
            update (dict[Column, Any]): A dictionary mapping columns to their new
                values. The values can be literals, :class:`Column` objects, or
                :class:`ColumnsOperation` expressions.
            where (ColumnsOperation): A condition expression that defines which
                rows should be updated.
            table (Table, optional): The table to update. If ``None``, the table
                associated with this batch operation is used.

        Returns:
            BatchOperation: The current batch operation instance (``self``),
            allowing method chaining for adding more statements.

        Example:
            Assuming a ``products`` table with columns ``price`` and ``stock``::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products
                price = products.price
                stock = products.stock
                category = products.category

                # Create a batch operation
                batch = products.batch()

                # Update price for discounted products
                condition = category == 'clearance'
                batch.update(
                    update={price: price * 0.8, stock: stock - 1},
                    where=condition
                )

                # Add another update for a different table (if needed)
                # batch.update(update={...}, where=..., table=other_table)

                # Execute all statements in the batch
                batch.run()
                # This executes: UPDATE products SET price = price * 0.8, stock = stock - 1
                # WHERE category = 'clearance';
        """
        if not update:
            raise Exception("Update dictionary cannot be empty")
        for v in update.values():
            if isinstance(v, bytes):
                raise Exception("Bytes objects cannot be used as values")
        temp_list= []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        self.script.append([f'UPDATE {table.name_ if table else self.table_obj.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=?' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1]])
        return self

    def insert(self, insert: dict[Column, Any], table: Table = None) -> 'BatchOperation':
        """Add an INSERT statement to the batch operation script.

        This method appends a new SQL INSERT command to the internal script
        of the batch operation. The statement inserts a single row into the
        specified table (or the table associated with this batch operation by
        default). The column–value pairs are provided as a dictionary, where
        each key is a :class:`Column` object and the corresponding value is
        the data to insert.

        The method supports values of any type; they are passed as parameters
        (``?`` placeholders) to prevent SQL injection. The batch operation can
        contain multiple statements (inserts, updates, etc.) that will be
        executed together when :meth:`run` is called.

        Args:
            insert (dict[Column, Any]): A mapping of columns to their values.
                Each key must be a :class:`Column` instance belonging to the
                target table, and the value is the data to be inserted.
            table (Table, optional): The table into which the row should be
                inserted. If not provided, the table associated with this
                :class:`BatchOperation` instance is used.

        Returns:
            BatchOperation: The current instance (``self``), allowing method
            chaining for building a multi‑statement batch.

        Example:
            Assuming a ``users`` table with columns ``name`` and ``age``::

                from ormophine.Sqlite import Driver

                db = Driver('app.db')
                users = db.users
                batch = users.batch()

                # Add an insert statement
                batch.insert({users.name: 'Alice', users.age: 30})

                # You can also specify a different table
                logs = db.logs
                batch.insert({logs.action: 'User created'}, table=logs)

                # Execute all batched statements
                batch.run()
        """
        if not insert:
            raise Exception("Insert dictionary cannot be empty")
        for v in insert.values():
            if isinstance(v, bytes):
                raise Exception("Bytes objects cannot be used as values")
        self.script.append([f'INSERT INTO {table.name_ if table else self.table_obj.name_} ({', '.join(i.first_name for i in list(insert.keys()))}) VALUES ({', '.join(f'?' for k in insert)})' , [v for v in list(insert.values())]])
        return self

    def delete_row(self, where: ColumnsOperation, table: Table = None) -> 'BatchOperation':
        """Add a DELETE statement to the batch operation script.

        This method appends a parameterized DELETE SQL statement to the
        internal script. The statement removes rows from the specified table
        (or the table associated with this batch operation by default) that
        match the given condition.

        The ``where`` condition is a :class:`ColumnsOperation` expression that
        defines which rows to delete. As with other batch methods, you can
        chain multiple calls to build a multi‑statement transaction that is
        executed atomically when :meth:`run` is called.

        Args:
            where (ColumnsOperation): A condition expression that specifies
                which rows should be deleted. For example,
                ``users.age < 18`` or ``products.stock == 0``.
            table (Table, optional): The table from which to delete rows.
                If ``None``, the table associated with this batch operation
                instance is used. This can be used to target a different
                table in the same batch.

        Returns:
            BatchOperation: The current batch operation instance (``self``),
            allowing method chaining for adding more statements or executing
            with :meth:`run`.

        Example:
            Assuming a ``products`` table with columns ``id``, ``stock``, and
            ``discontinued``::

                from ormophine.Sqlite import Driver

                db = Driver('store.db')
                products = db.products

                # Create a batch operation
                batch = products.batch()

                # Delete discontinued products with zero stock
                condition = (products.discontinued == True) & (products.stock == 0)
                batch.delete_row(where=condition)

                # You can also delete from another table
                logs = db.logs
                batch.delete_row(where=logs.timestamp < '2020-01-01', table=logs)

                # Execute all operations together
                batch.run()
                # This deletes matching rows in a single transaction.
        """
        self.script.append([f'DELETE FROM {table.name_ if table else self.table_obj.name_} WHERE {where._output[0]};', where._output[1]])
        return self

    def run(self):
        """Execute all batched operations in a single transaction.

        This method sends the accumulated script (list of SQL statements with
        their parameters) to the database connection thread via the table's
        main queue. The operations are executed as a batch, meaning they are
        committed together if all succeed, or rolled back entirely if any
        fails.

        The method blocks until the execution completes and a callback is
        received. If an error occurs during execution, an exception is raised
        with the underlying database error message.

        Returns:
            None

        Raises:
            Exception: If the batch execution fails. The exception message
                contains the original SQLite error.

        Example:
            Assuming a ``products`` table with columns ``price`` and
            ``discount``::

                from ormophine.Sqlite import Driver, Table

                db = Driver('store.db')
                products = db.products

                # Create a batch operation
                batch = products.batch()

                # Add multiple operations
                price = products.price
                discount = products.discount
                batch.update({price: price * 1.1}, price < 100)
                batch.update({discount: discount + 5}, discount > 50)
                batch.insert({price: 200, discount: 20})

                # Execute all operations atomically
                batch.run()
                # All operations are committed together.
        """
        if not self.script:
            return
        if not self.table_obj.db_obj._connected:
            raise RuntimeError("Driver Disconnected")
        queue_call_back = SimpleQueue()
        self.table_obj.main_queue.put(['qsb', self.script, queue_call_back])
        if not (callback := queue_call_back.get(block=True))[0]:
            raise Exception(callback[1])
