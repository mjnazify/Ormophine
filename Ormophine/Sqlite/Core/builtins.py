from __future__ import annotations
from .. import Column, ColumnsOperation


class Builtins:
    """SQLite SQL function helpers that always return a :class:`ColumnsOperation`.

    ``Builtins`` is a stateless namespace of static methods, each of which
    wraps a SQLite function (or, where SQLite lacks a native function, a
    short composition of SQLite functions) into a :class:`ColumnsOperation`
    object. Because every helper returns a ``ColumnsOperation``, the result
    can be used anywhere a column expression is accepted: in the
    ``which_columns`` list of :meth:`Table.get_row`, in the ``where``
    condition, in the ``update`` dict of :meth:`Table.update`, inside
    :meth:`~Table.bulk_update`, and so on. Helpers can also be nested
    freely — e.g. ``Builtins.Round(Builtins.Avg(col) * 100) / 100``
    compiles into a single SQL expression with all parameters collected
    in order.

    Design
    ------
    The class is deliberately a namespace, not an instance-based helper.
    You never write ``Builtins()``; every entry point is a
    ``@staticmethod`` you call directly::

        from Ormophine.Sqlite import Driver, Builtins

        rows = users.get_row(
            [users.id, Builtins.Len(users.username)],
            where=Builtins.Len(users.username) > 5,
        )

    All three of the standard operand types are accepted by every helper:

    - :class:`Column` — the fully qualified name (`` [table].[col] ``) is
      embedded verbatim; no parameters are consumed.
    - :class:`ColumnsOperation` — the previously-built SQL fragment and
      its parameter list are reused and extended.
    - Any raw Python value (``str``, ``int``, ``float``, ``bytes``,
      ``None``, ``bool``) — bound as a ``?`` placeholder. Binding rather
      than interpolating means the value never reaches the SQL text, so
      injection is impossible.

    Datatype propagation
    --------------------
    Each helper sets ``current_datatype`` on the returned
    ``ColumnsOperation`` to a Python type (``int``, ``float``, ``str``,
    ``bytes``, or ``None`` when the result's type depends on its
    branches, as in :meth:`IIf`). The downstream operator dispatcher in
    :class:`ColumnsOperation` uses this attribute to choose between
    arithmetic (``+``) and concatenation (``||``) when the expression is
    chained. Helpers therefore document their result type so that call
    sites can reason about chained expressions without trial and error.

    Conventional result types:

    ===================================  =========
    Helper family                        datatype
    ===================================  =========
    ``Len``, ``Sum``, ``Min``, ``Max``,
    ``Count``, ``Abs``, ``Sign``,
    ``Floor``, ``Ceil``, ``Int``, ``Bool``,
    ``Year``, ``Month``, ``Day``, ``Hour``,
    ``Minute``, ``Second``, ``DayOfWeek``,
    ``DayOfYear``, ``WeekOfYear``,
    ``Weekday``, ``IsoWeekday``,
    ``UnixEpoch``, ``UnixNow``,
    ``DateDiffDays``, ``DateDiffSeconds``    ``int``
    ``Avg``, ``Round``, ``Sqrt``, ``Pow``,
    ``Float``, ``Total``, ``JulianDay``     ``float``
    ``Reverse``, ``Capitalize``, ``Str``,
    ``Format``, ``TypeOf``, ``Date``,
    ``Time``, ``DateTime``, ``Strftime``,
    ``StrftimeMod``, ``Timediff``,
    ``DateAdd``, ``DateTimeAdd``,
    ``TimeAdd``, ``Now``, ``Today``         ``str``
    ``Find``                                 ``int``
    ``IsNull``, ``IsNotNull``, ``Between``   ``int`` (0/1 — SQLite has
                                             no native bool)
    ``IIf``                                  ``None`` (branches may
                                             disagree)
    ===================================  =========

    SQLite version caveats
    ----------------------
    SQLite has been adding SQL functions over time, and this backend
    surfaces them through dedicated helpers. When the functions are not
    available in the SQLite library that ships with the interpreter, the
    generated SQL will fail at execution time. The minimum SQLite
    versions per helper are:

    - **SQLite >= 3.35** (2021-03-12): :meth:`Sign`, :meth:`Floor`,
      :meth:`Ceil`, :meth:`Sqrt`, :meth:`Pow`.
    - **SQLite >= 3.38** (2022-02-22): :meth:`UnixEpoch`, :meth:`UnixNow`.
    - **SQLite >= 3.43** (2023-08-24): :meth:`Timediff`.
    - **SQLite >= 3.44** (2023-11-01): :meth:`Reverse`.

    For every one of these helpers the docstring documents a portable
    fallback (usually a composition of older primitives). If you need to
    support an older SQLite, either upgrade or wrap the expression
    manually.

    Helpers that exist only in SQLite
    ---------------------------------
    Some helpers are unique to this backend because they wrap functions
    that other databases either lack or implement differently:

    - :meth:`IIf` — wraps SQLite's ``IIF`` (SQLite >= 3.32). Other
      backends emit ``IF`` (MySQL) or ``CASE WHEN`` (PostgreSQL).
    - :meth:`TOTAL` (via :meth:`Total`) — SQLite's ``TOTAL`` aggregate
      returns ``0.0`` over empty groups, unlike ``SUM`` which returns
      ``NULL``. This is a SQLite-only function name.
    - :meth:`TypeOf` — wraps ``TYPEOF``, which returns one of SQLite's
      five storage classes (``'null'``, ``'integer'``, ``'real'``,
      ``'text'``, ``'blob'``).
    - :meth:`Format` — wraps SQLite's ``PRINTF`` (the ``printf`` function
      exposed to SQL as ``PRINTF``).
    - :meth:`JulianDay` — wraps ``julianday``, SQLite's built-in
      Julian-day converter.
    - :meth:`UnixEpoch` — wraps ``unixepoch`` (SQLite >= 3.38).
    - :meth:`Timediff` — wraps ``timediff`` (SQLite >= 3.43), which
      returns an interval-formatted text string.
    - :meth:`DateAdd`, :meth:`DateTimeAdd`, :meth:`TimeAdd`,
      :meth:`StrftimeMod` — modifier-aware date functions that accept
      SQLite's *modifier strings* (``'start of month'``, ``'+1 day'``,
      ``'-2 hours'``, ``'localtime'``, ``'weekday 1'``, ...). These are
      not portable to other backends without rewriting the modifiers.

    Date/time conventions
    ---------------------
    Date and time helpers return ``str`` in ISO-8601-like formats that
    SQLite produces natively (``'YYYY-MM-DD'``, ``'HH:MM:SS'``,
    ``'YYYY-MM-DD HH:MM:SS'``). They accept an ISO literal, a
    :class:`Column`, a :class:`ColumnsOperation`, or the special string
    ``'now'``. All dates are UTC unless a ``'localtime'`` modifier is
    supplied.

    Unlike the MySQL and PostgreSQL backends, SQLite has **no native
    date type**; every date function accepts and returns text. That means
    every helper here works transparently with text columns without any
    casting.

    Notes
    -----
    - The helpers do not cache or memoize; every call builds a fresh
      ``ColumnsOperation``. This is deliberate — the operations are cheap
      to construct and the alternative (mutating shared state) would break
      thread-safety.
    - The class is not instantiable for use; it exists only to group the
      static methods. Attempting ``Builtins()`` succeeds but produces an
      object with no useful behaviour.
    - All parameters collected by the helpers are appended to the
      ``_output[1]`` list in the order their placeholders appear in the
      SQL fragment, which is the order sqlite3 expects.
    - SQLite returns ``0`` and ``1`` for boolean predicates, not the
      Python ``True`` / ``False``. Predicates exposed here (:meth:`IsNull`,
      :meth:`IsNotNull`, :meth:`Between`) therefore declare
      ``current_datatype = int``. If you need a real Python boolean after
      fetching, compare the value in Python (``if row[0] == 1``).

    Example:
        A quick tour of the helper categories::

            from Ormophine.Sqlite import Driver, Builtins

            db    = Driver('app.db')
            users = db.users

            # String
            Builtins.Len(users.username)
            Builtins.Reverse(users.username)
            Builtins.Find(users.email, '@')
            Builtins.Capitalize(users.name)
            Builtins.Format('Hello %s', users.name)

            # Aggregate
            Builtins.Sum(users.balance)
            Builtins.Avg(users.age)
            Builtins.Min(users.created_at)
            Builtins.Max(users.score)
            Builtins.Count('*')
            Builtins.Total(users.balance)

            # Math
            Builtins.Abs(users.delta)
            Builtins.Round(users.price)
            Builtins.Floor(users.score)
            Builtins.Ceil(users.score)
            Builtins.Sign(users.delta)
            Builtins.Sqrt(users.x * users.x + users.y * users.y)
            Builtins.Pow(users.base, users.exp)

            # Type cast
            Builtins.Int(users.text_id)
            Builtins.Float(users.text_price)
            Builtins.Str(users.numeric_code)
            Builtins.Bool(users.flag)
            Builtins.TypeOf(users.payload)

            # Condition
            Builtins.IsNull(users.email)
            Builtins.IsNotNull(users.phone)
            Builtins.Between(users.age, 18, 65)
            Builtins.IIf(users.age >= 18, 'adult', 'minor')

            # Date and time
            Builtins.Year(users.created_at)
            Builtins.Month(users.created_at)
            Builtins.Day(users.created_at)
            Builtins.Hour(users.created_at)
            Builtins.Minute(users.created_at)
            Builtins.Second(users.created_at)
            Builtins.DayOfWeek(users.created_at)
            Builtins.DayOfYear(users.created_at)
            Builtins.WeekOfYear(users.created_at)
            Builtins.Weekday(users.created_at)
            Builtins.IsoWeekday(users.created_at)
            Builtins.Strftime('%Y-%m-%d', users.created_at)
            Builtins.Now()
            Builtins.Today()
            Builtins.UnixNow()
            Builtins.UnixEpoch(users.created_at)
            Builtins.JulianDay(users.created_at)
            Builtins.DateAdd('now', '+1 day')
            Builtins.DateTimeAdd('now', '-1 hour')
            Builtins.TimeAdd('now', '+30 minutes')
            Builtins.StrftimeMod('%Y-%m', 'now', '-1 month')
            Builtins.DateDiffDays(Builtins.Now(), users.created_at)
            Builtins.DateDiffSeconds(Builtins.Now(), users.updated_at)
            Builtins.Timediff(Builtins.Now(), users.created_at)
    """

    class _NullCol:
        """Fallback stand-in used when a :class:`ColumnsOperation` has no originating :class:`Column`.

        Several helpers in :class:`Builtins` (e.g. :meth:`Builtins.Count`
        with ``'*'``, :meth:`Builtins.Now`, :meth:`Builtins.Today`,
        :meth:`Builtins.UnixNow`) produce SQL that does not refer to any
        particular table or column. For example ``COUNT(*)`` has no
        column operand, and ``datetime('now')`` is a server-side constant.
        But every :class:`ColumnsOperation` in this ORM is expected to
        carry a ``col_obj`` attribute pointing at the :class:`Column` that
        originated the expression — the operator dispatcher reads
        ``col_obj.datatype``, ``col_obj.name``, and
        ``col_obj.table_obj._PlaceHolder`` when deciding how to render a
        chained operation.

        Rather than passing ``None`` and forcing every call site to
        null-check, helpers with no natural column use this class. It
        supplies the same attribute surface as a real :class:`Column` so
        chained operations such as ``Builtins.Now() + 1`` or
        ``Builtins.Count('*') * 2`` do not raise ``AttributeError``.

        Attributes:
            datatype (None): Always ``None``. Signals that the originating
                expression is not tied to a column type, so the operator
                dispatcher falls back to its safe defaults (arithmetic
                rather than concatenation when both sides are ambiguous).
            table_obj (None): Always ``None``. Unlike the MySQL and
                PostgreSQL backends — which define ``table_obj`` as a
                tiny inner class exposing a harmless ``_PlaceHolder``
                stub — the SQLite backend simply sets it to ``None``.
                The SQLite operator dispatcher only reaches
                ``self.col_obj.table_obj._PlaceHolder`` when
                ``col_obj`` is a real :class:`Column`, so a ``None``
                here is safe for the helpers' use case.
            name (str): Always the empty string. Substituting it into SQL
                would produce invalid SQL, but this path is never taken
                because the helper's own SQL fragment already contains
                the complete expression.
            first_name (str): Always the empty string. Same reasoning as
                ``name``.

        Example:
            Internal usage within a helper::

                @staticmethod
                def Now(_=None):
                    return Builtins._make("(datetime('now'))", [], str,
                                          Builtins._NullCol)

            The ``Builtins._NullCol`` class itself (not an instance) is
            passed because the helpers only need the attribute surface,
            never any per-instance state. Passing the class works because
            attribute lookup falls through to the class-level definitions.
        """
        datatype   = None
        table_obj  = None
        name       = ''
        first_name = ''

    @staticmethod
    def _normalize(value):
        """Coerce an operand into a uniform ``(sql, params, datatype, col_obj)`` tuple.

        This is the single point through which every :class:`Builtins`
        helper inspects its arguments. Because the three accepted operand
        types — :class:`Column`, :class:`ColumnsOperation`, and raw Python
        values — carry their SQL information in different shapes, the
        helpers cannot consume them directly; ``_normalize`` flattens each
        shape into a common four-element tuple so the helper body only
        ever deals with one representation.

        The returned tuple has the following layout:

        - ``sql`` (str): The SQL fragment representing the operand. For a
          :class:`Column` this is the fully qualified name
          (`` [table].[col] ``); for a :class:`ColumnsOperation` it is the
          previously-built fragment; for a raw value it is the placeholder
          ``'?'``.
        - ``params`` (list): The parameters that must be bound to the
          placeholders in ``sql``. Always a fresh list — mutating it does
          not affect the source operand.
        - ``datatype`` (type | None): The Python type that the operand
          evaluates to on the server side, used by the helper to set
          ``current_datatype`` on its result. ``None`` for a raw literal
          whose type is unknown (e.g. when ``value is None``).
        - ``col_obj`` (Column | type[_NullCol]): The originating column,
          or the :class:`_NullCol` class when there is none. Never
          ``None`` — helpers can rely on the attribute surface being
          present.

        Args:
            value: The operand to normalize. Accepted types:

                - :class:`ColumnsOperation` — its ``_output`` tuple is
                  unpacked; the parameter list is copied so the caller
                  cannot accidentally mutate the source operation.
                - :class:`Column` — the fully qualified name is used and
                  no parameters are produced. ``col_obj`` is the column
                  itself.
                - Any other Python value — wrapped as ``('?', [value])``
                  with ``type(value)`` as the datatype and ``_NullCol``
                  as the column stand-in.

        Returns:
            tuple[str, list, type | None, Column | type[_NullCol]]: A
            four-element tuple ``(sql, params, datatype, col_obj)`` as
            described above. The ``params`` list is always freshly
            allocated.

        Example:
            Internal usage inside a helper — :meth:`Len` delegates the
            inspection to ``_normalize`` and then builds its own SQL::

                sql, p, _, c = Builtins._normalize(value)
                return Builtins._make(f'(LENGTH({sql}))', p, int, c)

            Behaviour on each operand type::

                >>> Builtins._normalize(users.username)
                ('[users].[username]', [], str, <Column users.username>)

                >>> op = Builtins.Len(users.username)
                >>> Builtins._normalize(op)
                ('(LENGTH([users].[username]))', [], int, <Column users.username>)

                >>> Builtins._normalize('hello')
                ('?', ['hello'], str, Builtins._NullCol)

                >>> Builtins._normalize(42)
                ('?', [42], int, Builtins._NullCol)

                >>> Builtins._normalize(None)
                ('?', [None], NoneType, Builtins._NullCol)
        """
        if isinstance(value, ColumnsOperation):
            raw    = value._output[1]
            params = list(raw) if isinstance(raw, list) else [raw]
            return (
                value._output[0],
                params,
                value.current_datatype,
                value.col_obj if value.col_obj is not None else Builtins._NullCol,
            )
        if isinstance(value, Column):
            return value.name, [], value.datatype, value
        return '?', [value], type(value), Builtins._NullCol

    @staticmethod
    def _make(sql, params, datatype, col_obj):
        """Assemble a :class:`ColumnsOperation` from a raw SQL fragment and its metadata.

        Helpers build their SQL fragment by string concatenation (or by
        composing the fragments returned from :meth:`_normalize` of their
        operands), then hand the result to ``_make`` for packaging. The
        method creates a fresh ``ColumnsOperation`` **without** calling its
        ``__init__`` — it uses ``__new__`` instead — because the
        constructor initialises ``_output`` to ``('', [])`` and would
        overwrite the fragment we want to store. This is a deliberate
        optimisation: helpers are called far more often than the
        constructor, and skipping ``__init__`` avoids four attribute
        assignments per call.

        The returned object behaves exactly like any other
        ``ColumnsOperation``: it supports arithmetic, comparison, string
        methods, ``In``/``not_In``, ``If``, and so on. Its ``_output``
        tuple is the one passed in, and its ``current_datatype`` reflects
        the helper's declared result type.

        Args:
            sql (str): The complete SQL fragment for the expression,
                including any surrounding parentheses the helper chose to
                add. Must contain ``?`` placeholders exactly as many times
                as ``params`` has elements.
            params (list): The parameter values to bind, in the order
                their placeholders appear in ``sql``. The list is stored
                by reference on the returned operation, so the caller
                should not retain and later mutate it.
            datatype (type | None): The Python type the expression
                evaluates to on the server. Used by the operator dispatcher
                when the operation is chained. Pass ``None`` when the type
                depends on runtime branches (e.g. :meth:`IIf`).
            col_obj (Column | type[_NullCol]): The originating column, or
                the :class:`_NullCol` class when there is none. Passing
                ``None`` is tolerated and treated as ``_NullCol``, but
                helpers should pass ``_NullCol`` explicitly for clarity.

        Returns:
            ColumnsOperation: A new operation whose ``_output`` is
            ``(sql, params)``, whose ``current_datatype`` is ``datatype``,
            and whose ``col_obj`` is ``col_obj`` (or ``_NullCol`` when
            ``col_obj is None``).

        Example:
            Internal usage inside a helper::

                # Len — SQLite LENGTH()
                return Builtins._make(f'(LENGTH({sql}))', p, int, c)

                # Now — no operands at all
                return Builtins._make("(datetime('now'))", [], str,
                                      Builtins._NullCol)

                # IIf — datatype intentionally None because the branches
                # may disagree
                return Builtins._make(
                    f'(IIF({cs}, {ts}, {es}))',
                    cp + tp + ep,
                    None,
                    c,
                )

                # DateDiffDays — nested julianday + CAST
                return Builtins._make(
                    f'(CAST(julianday({s1}) - julianday({s2}) AS INTEGER))',
                    p1 + p2, int, c,
                )

            The result composes with the rest of the expression system::

                >>> op = Builtins._make("(datetime('now'))", [], str,
                ...                     Builtins._NullCol)
                >>> op._output
                ("(datetime('now'))", [])
                >>> op.current_datatype
                <class 'str'>
                >>> # Chain arithmetic — the dispatcher sees str, so it
                >>> # would pick || unless overridden by a cast builtin.
                >>> (Builtins.Int(Builtins.UnixNow()) + 60)._output[0]
                '((CAST((unixepoch(?)) AS INTEGER)) + ?)'
        """
        op = ColumnsOperation.__new__(ColumnsOperation)
        op._output          = (sql, params)
        op.col_obj          = col_obj if col_obj is not None else Builtins._NullCol
        op.current_datatype = datatype
        return op
    
    @staticmethod
    def Len(value):
        """Compute the length of a value using SQLite's ``LENGTH()`` function.

        Generates a SQL expression that returns the number of characters in
        a string, or the number of bytes in a BLOB. This is the SQL equivalent
        of Python's built-in ``len()``. The result is always an ``INTEGER``,
        regardless of the input's datatype.

        The result is a :class:`ColumnsOperation`, so every operator and
        method of that class remains available on it — comparisons, string
        methods, slicing, ``In``, ``like``, arithmetic, and so on.

        Args:
            value: The expression whose length is computed. Supported types:

                - :class:`ColumnsOperation` — the generated SQL fragment and
                  its parameters are reused.
                - :class:`Column` — the fully qualified column name is used
                  directly in the SQL; no parameters are consumed.
                - Any raw Python value (``str``, ``int``, ``float``,
                  ``bytes``) — bound as a ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(LENGTH(<expr>))`` and whose ``current_datatype`` is ``int``.

        Example:
            Basic filtering — find users whose username is longer than 5
            characters::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row(
                    [users.username],
                    where=Builtins.Len(users.username) > 5,
                )
                # SELECT [users].[username] FROM [users] WHERE (LENGTH([users].[username]) > ?)
                # Parameters: [5]

            As a SELECT column — the length of each username::

                rows = users.get_row([
                    users.username,
                    Builtins.Len(users.username),
                ])
                # SELECT [users].[username], (LENGTH([users].[username])) FROM [users]

            Chained with other operations — the length rounded up to a
            multiple of 4, then compared::

                padded_len = ((Builtins.Len(users.username) + 3) / 4) * 4
                rows = users.get_row(
                    [users.username, padded_len],
                    where=Builtins.Len(users.username) > 0,
                )

            Nested inside other builtins::

                avg_len = Builtins.Avg(Builtins.Len(users.username))
                rows = users.get_row([avg_len])
                # SELECT (AVG((LENGTH([users].[username])))) FROM [users]

            Applied to a raw literal — the literal is bound as a parameter::

                rows = users.get_row([
                    Builtins.Len('hello'),    # -> (LENGTH(?)) with param 'hello'
                    Builtins.Len(42),         # -> (LENGTH(?)) with param 42
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(LENGTH({sql}))', p, int, c)

    @staticmethod
    def Sum(value):
        """Compute the sum of a set of values using SQLite's ``SUM()`` aggregate.

        Generates an SQL ``SUM(<expr>)`` expression. When used in a SELECT
        list without a ``GROUP BY`` clause, it aggregates over all rows
        returned by the query. When used inside a ``WHERE`` clause it has no
        meaning on its own (SQLite will reject it) — ``Sum`` is meant for
        the SELECT side of a query, not for filtering.

        The resulting ``current_datatype`` is propagated from the input:

        - ``int``   → ``int`` (SQLite keeps integer sums as integers)
        - ``float`` → ``float``
        - anything else → ``int`` (conservative default)

        This keeps arithmetic chains (``Builtins.Sum(col) + 1``) compiling
        to ``+`` and not ``||``.

        Args:
            value: The expression to sum. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder (rarely
                  useful as the sole argument of an aggregate, but supported
                  for completeness).

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(SUM(<expr>))`` and whose ``current_datatype`` matches the
            input's numeric type (or ``int`` if the input is not numeric).

        Example:
            Total salary across all employees::

                from Ormophine.Sqlite import Driver, Builtins

                db        = Driver('company.db')
                employees = db.employees

                total = Builtins.Sum(employees.salary)
                rows  = employees.get_row([total])
                # SELECT (SUM([employees].[salary])) FROM [employees]
                # -> [(1245000,)] for example

            Sum alongside other aggregates::

                rows = employees.get_row([
                    Builtins.Count(employees.id),
                    Builtins.Sum(employees.salary),
                    Builtins.Avg(employees.salary),
                ])

            Sum combined with arithmetic (stays numeric, not string)::

                with_bonus = Builtins.Sum(employees.salary) + 10000
                rows = employees.get_row([with_bonus])
                # SELECT ((SUM([employees].[salary])) + ?) FROM [employees]
                # Parameters: [10000]

            Sum inside a subquery-style comparison — e.g. find departments
            whose total salary exceeds a threshold. Since SQLite does not
            allow aggregates in ``WHERE``, use ``HAVING``-style filtering
            by grouping::

                rows = employees.get_row(
                    [employees.department, Builtins.Sum(employees.salary)],
                    # In this ORM, group filtering is done via the raw API:
                )
                # Then filter in Python:
                high_paid = [d for d, total in rows if total > 500000]
        """
        sql, p, dt, c = Builtins._normalize(value)
        result_dt = dt if dt in (int, float) else int
        return Builtins._make(f'(SUM({sql}))', p, result_dt, c)

    @staticmethod
    def Avg(value):
        """Compute the average of a set of values using SQLite's ``AVG()`` aggregate.

        Generates an SQL ``AVG(<expr>)`` expression. SQLite always returns
        the average as a floating-point number, even when every input value
        is an integer; therefore ``current_datatype`` is unconditionally set
        to ``float`` regardless of the input's datatype.

        Like :meth:`Sum`, this aggregate is meant for the SELECT side of a
        query. Using it in a ``WHERE`` clause will raise an SQL error unless
        the query contains a ``GROUP BY`` that makes the aggregate legal.

        Args:
            value: The expression to average. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(AVG(<expr>))`` and whose ``current_datatype`` is always
            ``float``.

        Example:
            Average salary across all employees::

                from Ormophine.Sqlite import Driver, Builtins

                db        = Driver('company.db')
                employees = db.employees

                rows = employees.get_row([Builtins.Avg(employees.salary)])
                # SELECT (AVG([employees].[salary])) FROM [employees]
                # -> [(78750.0,)] for example

            Average rounded to two decimals::

                rows = employees.get_row([
                    Builtins.Round(Builtins.Avg(employees.salary) * 100) / 100
                ])

            Average of a computed expression::

                rows = employees.get_row([
                    Builtins.Avg(employees.salary + employees.bonus)
                ])
                # SELECT (AVG(([employees].[salary] + [employees].[bonus]))) FROM [employees]

            Combined with other aggregates in a single row::

                rows = employees.get_row([
                    Builtins.Count(employees.id),
                    Builtins.Avg(employees.salary),
                    Builtins.Sum(employees.salary),
                ])

            Comparing an AVG result in Python after fetching::

                rows = employees.get_row(
                    [employees.department, Builtins.Avg(employees.salary)],
                )
                above_average = [d for d, avg in rows if avg > 60000]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(AVG({sql}))', p, float, c)

    @staticmethod
    def Min(value):
        """Compute the minimum of a set of values using SQLite's ``MIN()`` aggregate.

        Generates an SQL ``MIN(<expr>)`` expression. When used with a single
        argument in the SELECT list, ``MIN`` acts as an aggregate over all
        rows. (When used with multiple arguments it acts as a scalar
        function, but this method only accepts one argument — for the
        scalar form, use :meth:`Builtins.Func` with ``'MIN'`` or chain
        with the ``Column`` API.)

        The resulting ``current_datatype`` is propagated from the input,
        because SQLite returns the same type as the operand:

        - ``int``   → ``int``
        - ``float`` → ``float``
        - ``str``   → ``str`` (lexicographic minimum)
        - ``bytes`` → ``bytes``

        This keeps downstream concatenation (``Builtins.Min(col) + '!'``)
        compiling to ``||`` when the input was text.

        Args:
            value: The expression whose minimum is computed. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(MIN(<expr>))`` and whose ``current_datatype`` matches the
            input's datatype.

        Example:
            Lowest salary in the table::

                from Ormophine.Sqlite import Driver, Builtins

                db        = Driver('company.db')
                employees = db.employees

                rows = employees.get_row([Builtins.Min(employees.salary)])
                # SELECT (MIN([employees].[salary])) FROM [employees]
                # -> [(45000,)] for example

            Earliest signup date::

                users = db.users
                rows  = users.get_row([Builtins.Min(users.created_at)])
                # SELECT (MIN([users].[created_at])) FROM [users]

            Lexicographic minimum of a text column::

                rows = employees.get_row([Builtins.Min(employees.name)])
                # current_datatype == str, so chaining works:
                expr = Builtins.Min(employees.name) + ' (first alphabetically)'
                # SELECT ((MIN([employees].[name])) || ?) FROM [employees]

            Minimum of a computed expression::

                rows = employees.get_row([
                    Builtins.Min(employees.salary - employees.bonus)
                ])
        """
        sql, p, dt, c = Builtins._normalize(value)
        return Builtins._make(f'(MIN({sql}))', p, dt, c)

    @staticmethod
    def Max(value):
        """Compute the maximum of a set of values using SQLite's ``MAX()`` aggregate.

        Generates an SQL ``MAX(<expr>)`` expression. The mirror image of
        :meth:`Min`: same typing rules, same aggregate semantics, same
        single-argument signature.

        The resulting ``current_datatype`` is propagated from the input
        so that arithmetic and concatenation chains compile to the correct
        SQL operator.

        Args:
            value: The expression whose maximum is computed. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(MAX(<expr>))`` and whose ``current_datatype`` matches the
            input's datatype.

        Example:
            Highest salary in the table::

                from Ormophine.Sqlite import Driver, Builtins

                db        = Driver('company.db')
                employees = db.employees

                rows = employees.get_row([Builtins.Max(employees.salary)])
                # SELECT (MAX([employees].[salary])) FROM [employees]
                # -> [(180000,)] for example

            Latest signup date::

                users = db.users
                rows  = users.get_row([Builtins.Max(users.created_at)])
                # SELECT (MAX([users].[created_at])) FROM [users]

            Combined with the id of the top earner — get both at once::

                rows = employees.get_row([
                    Builtins.Max(employees.salary),
                    employees.id,
                ])
                # The first value is the max salary; the second is the id
                # of an arbitrary row (SQLite picks one) — for a strict
                # "id of the top earner" use order_by + limit:
                top = employees.get_row(
                    [employees.id, employees.name, employees.salary],
                    order_by=employees.salary,
                    limit=1,
                )

            Maximum of a computed expression::

                rows = employees.get_row([
                    Builtins.Max(employees.salary + employees.bonus)
                ])
        """
        sql, p, dt, c = Builtins._normalize(value)
        return Builtins._make(f'(MAX({sql}))', p, dt, c)

    @staticmethod
    def Count(value):
        """Count rows using SQLite's ``COUNT()`` aggregate.

        Two forms are supported, mirroring SQLite's own behaviour:

        * **Row count** — when ``value`` is the literal string ``'*'``,
          generates ``COUNT(*)`` which counts every row in the group,
          regardless of NULL values.
        * **Non-null count** — for any other input, generates
          ``COUNT(<expr>)`` which counts only the rows where the expression
          evaluates to a non-NULL value.

        The result is always an ``INTEGER``, regardless of the input's
        datatype.

        Args:
            value: What to count. Supported types:

                - The string ``'*'`` — produces ``COUNT(*)`` and no
                  parameters.
                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused; produces ``COUNT(<fragment>)``.
                - :class:`Column` — the fully qualified column name is used;
                  produces ``COUNT([table].[column])``.
                - Any other raw Python value — bound as a ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            either ``(COUNT(*))`` or ``(COUNT(<expr>))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Count all rows in the table::

                from Ormophine.Sqlite import Driver, Builtins

                db        = Driver('company.db')
                employees = db.employees

                rows = employees.get_row([Builtins.Count('*')])
                # SELECT (COUNT(*)) FROM [employees]
                # -> [(250,)] for example

            Count rows where a column is non-NULL::

                users = db.users
                rows  = users.get_row([Builtins.Count(users.email)])
                # SELECT (COUNT([users].[email])) FROM [users]
                # -> [(198,)] — 52 users have no email on file

            Count with a filter — combine with where= in the usual way::

                rows = users.get_row(
                    [Builtins.Count('*')],
                    where=users.is_active == 1,
                )
                # SELECT (COUNT(*)) FROM [users] WHERE ([users].[is_active] = ?)
                # Parameters: [1]

            Count of a computed expression::

                rows = users.get_row([
                    Builtins.Count(Builtins.Upper(users.username))
                ])
                # SELECT (COUNT((UPPER([users].[username])))) FROM [users]

            Boolean count via IIF — count how many rows satisfy a condition
            inside a single aggregate::

                adults = Builtins.Sum(
                    Builtins.IIf(users.age >= 18, 1, 0)
                )
                rows = users.get_row([adults])
                # SELECT (SUM((IIF(([users].[age] >= ?), ?, ?)))) FROM [users]
        """
        if isinstance(value, str) and value == '*':
            return Builtins._make('(COUNT(*))', [], int, Builtins._NullCol)
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(COUNT({sql}))', p, int, c)

    @staticmethod
    def Abs(value):
        """Compute the absolute value of a number using SQLite's ``ABS()`` function.

        Generates an SQL ``ABS(<expr>)`` expression. The return type mirrors
        the input's numeric type:

        - ``int``   → ``int``
        - ``float`` → ``float``
        - anything else → ``float`` (conservative default, since ``ABS``
          only makes sense for numeric inputs)

        This keeps arithmetic chains (``Builtins.Abs(col) + 1``) compiling
        to ``+`` rather than ``||``.

        Args:
            value: The expression whose absolute value is computed.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(ABS(<expr>))`` and whose ``current_datatype`` matches the
            input's numeric type (or ``float`` if the input is not numeric).

        Example:
            Magnitude of a signed delta::

                from Ormophine.Sqlite import Driver, Builtins

                db         = Driver('analytics.db')
                movements  = db.movements

                rows = movements.get_row([
                    movements.account_id,
                    Builtins.Abs(movements.delta),
                ])
                # SELECT [movements].[account_id], (ABS([movements].[delta])) FROM [movements]

            Filter by absolute value::

                rows = movements.get_row(
                    [movements.account_id, movements.delta],
                    where=Builtins.Abs(movements.delta) > 1000,
                )
                # SELECT [movements].[account_id], [movements].[delta]
                # FROM [movements]
                # WHERE ((ABS([movements].[delta])) > ?)
                # Parameters: [1000]

            Absolute value of a computed expression::

                balance_change = movements.credit - movements.debit
                rows = movements.get_row([Builtins.Abs(balance_change)])

            Chained with arithmetic — stays numeric::

                padded = Builtins.Abs(movements.delta) + 1
                # SELECT ((ABS([movements].[delta])) + ?) FROM [movements]

            Applied to a raw literal::

                rows = movements.get_row([
                    Builtins.Abs(-42),    # -> (ABS(?)) with param -42
                    Builtins.Abs(-3.14),  # -> (ABS(?)) with param -3.14
                ])
        """
        sql, p, dt, c = Builtins._normalize(value)
        result_dt = dt if dt in (int, float) else float
        return Builtins._make(f'(ABS({sql}))', p, result_dt, c)

    @staticmethod
    def Round(value):
        """Round a number to the nearest integer using SQLite's ``ROUND()`` function.

        Generates an SQL ``ROUND(<expr>)`` expression. SQLite's ``ROUND``
        with a single argument rounds to zero decimal places and returns a
        REAL (float), not an INTEGER, even when the input is an integer.
        Therefore ``current_datatype`` is unconditionally set to ``float``.

        To round to a specific number of decimal places or to cast to an
        integer, chain with :meth:`Int` or use :meth:`Builtins.Func` with
        the two-argument form::

            Builtins.Func('ROUND', users.price)       # single arg -> integer rounding
            users.price * 0.9                          # ... then wrap for 2 decimals:
            # currently no 2-arg helper exists; use Func if needed.

        Args:
            value: The expression whose value is rounded. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(ROUND(<expr>))`` and whose ``current_datatype`` is always
            ``float``.

        Example:
            Round a computed price to the nearest integer::

                from Ormophine.Sqlite import Driver, Builtins

                db       = Driver('store.db')
                products = db.products

                rows = products.get_row([
                    products.name,
                    Builtins.Round(products.price * 1.07),
                ])
                # SELECT [products].[name], (ROUND(([products].[price] * ?))) FROM [products]
                # Parameters: [1.07]

            Round then cast to integer::

                rows = products.get_row([
                    Builtins.Int(Builtins.Round(products.price)),
                ])
                # SELECT (CAST((ROUND([products].[price])) AS INTEGER)) FROM [products]

            Round an aggregate::

                rows = products.get_row([
                    Builtins.Round(Builtins.Avg(products.price) * 100) / 100,
                ])
                # Two-decimal average price:
                # SELECT ((ROUND(((AVG([products].[price])) * ?))) / ?) FROM [products]
                # Parameters: [100, 100]

            Filter by rounded value::

                rows = products.get_row(
                    [products.name, products.price],
                    where=Builtins.Round(products.price) > 100,
                )
                # SELECT ... WHERE ((ROUND([products].[price])) > ?)
                # Parameters: [100]

            Chained with string operations — current_datatype is float, so
            arithmetic stays numeric::

                padded = Builtins.Round(products.price) * 1.1
                # SELECT ((ROUND([products].[price])) * ?) FROM [products]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(ROUND({sql}))', p, float, c)

    @staticmethod
    def Int(value):
        """Convert a value to an integer using SQLite's ``CAST(x AS INTEGER)``.

        This is the SQL equivalent of Python's ``int()``. Generates a
        ``CAST(<expr> AS INTEGER)`` expression. SQLite's conversion rules
        apply: text is parsed as a number (leading digits only), REAL is
        truncated toward zero, and NULL stays NULL.

        The result is always an ``INTEGER``, so arithmetic chains and
        comparisons behave as expected even when the original column was
        declared as TEXT or REAL.

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS INTEGER))`` and whose ``current_datatype`` is
            always ``int``.

        Example:
            Force a text column to be treated as an integer::

                from Ormophine.Sqlite import Driver, Builtins

                db     = Driver('app.db')
                events = db.events

                rows = events.get_row([
                    events.id,
                    Builtins.Int(events.payload),
                ])
                # SELECT [events].[id], (CAST([events].[payload] AS INTEGER))
                # FROM [events]

            Compare a text column numerically::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Int(events.amount_text) > 1000,
                )
                # SELECT [events].[id] FROM [events]
                # WHERE ((CAST([events].[amount_text] AS INTEGER)) > ?)
                # Parameters: [1000]

            Truncate a REAL toward zero::

                rows = events.get_row([
                    Builtins.Int(events.temperature),   # 23.7 -> 23
                ])
                # SELECT (CAST([events].[temperature] AS INTEGER)) FROM [events]

            Combine with arithmetic — stays numeric::

                doubled = Builtins.Int(events.count) * 2
                # SELECT ((CAST([events].[count] AS INTEGER)) * ?) FROM [events]

            Used inside an aggregate::

                rows = events.get_row([
                    Builtins.Sum(Builtins.Int(events.payload)),
                ])
                # SELECT (SUM((CAST([events].[payload] AS INTEGER)))) FROM [events]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS INTEGER))', p, int, c)

    @staticmethod
    def Float(value):
        """Convert a value to a floating-point number using ``CAST(x AS REAL)``.

        This is the SQL equivalent of Python's ``float()``. Generates a
        ``CAST(<expr> AS REAL)`` expression. SQLite's conversion rules
        apply: text is parsed as a number, INTEGER is widened to REAL, and
        NULL stays NULL.

        The result is always a ``REAL`` (Python ``float``), so any chained
        arithmetic naturally stays in the floating-point domain.

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS REAL))`` and whose ``current_datatype`` is
            always ``float``.

        Example:
            Force integer division to produce a real result::

                from Ormophine.Sqlite import Driver, Builtins

                db         = Driver('analytics.db')
                statistics = db.statistics

                ratio = Builtins.Float(statistics.successes) / statistics.attempts
                rows = statistics.get_row([ratio])
                # SELECT ((CAST([statistics].[successes] AS REAL)) / [statistics].[attempts])
                # FROM [statistics]
                # -> e.g. [(0.9732,)]

            Parse a text column as a number::

                rows = statistics.get_row(
                    [statistics.id, Builtins.Float(statistics.amount_text)],
                    where=Builtins.Float(statistics.amount_text) >= 99.5,
                )

            Widen an integer column before averaging::

                rows = statistics.get_row([
                    Builtins.Avg(Builtins.Float(statistics.count)),
                ])

            Multiply a converted value by a literal::

                scaled = Builtins.Float(statistics.score) * 1.5
                rows = statistics.get_row([scaled])
                # SELECT ((CAST([statistics].[score] AS REAL)) * ?) FROM [statistics]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS REAL))', p, float, c)

    @staticmethod
    def Str(value):
        """Convert a value to text using SQLite's ``CAST(x AS TEXT)``.

        This is the SQL equivalent of Python's ``str()``. Generates a
        ``CAST(<expr> AS TEXT)`` expression. SQLite's conversion rules
        apply: numbers are formatted as their decimal representation, NULL
        stays NULL, and BLOBs are interpreted as text.

        The result is always a ``TEXT`` (Python ``str``), so chaining with
        ``+`` produces string concatenation (``||``) rather than arithmetic
        addition.

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS TEXT))`` and whose ``current_datatype`` is
            always ``str``.

        Example:
            Safely concatenate a numeric column with text::

                from Ormophine.Sqlite import Driver, Builtins

                db        = Driver('company.db')
                employees = db.employees

                label = Builtins.Str(employees.salary) + ' USD'
                rows = employees.get_row([employees.name, label])
                # SELECT [employees].[name], ((CAST([employees].[salary] AS TEXT)) || ?)
                # FROM [employees]
                # Parameters: [' USD']
                #
                # Without Builtins.Str, `employees.salary + ' USD'` would
                # compile to arithmetic '+' (because salary.datatype is int),
                # which SQLite would silently turn into a wrong numeric result.

            Format an integer id for display::

                rows = employees.get_row([
                    Builtins.Str(employees.id).add_first('EMP-'),
                ])
                # SELECT (? || (CAST([employees].[id] AS TEXT))) FROM [employees]
                # Parameters: ['EMP-']

            Use with string methods::

                rows = employees.get_row([
                    Builtins.Str(employees.salary).strip(),
                ])

            Inside a LIKE pattern::

                rows = employees.get_row(
                    [employees.id],
                    where=Builtins.Str(employees.id).startswith('1'),
                )
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS TEXT))', p, str, c)

    @staticmethod
    def Bool(value):
        """Convert a value to a boolean-like integer using ``CAST(x AS INTEGER)``.

        SQLite has no native boolean type — booleans are stored as the
        integers ``0`` and ``1``. This helper mirrors Python's ``bool()``
        by emitting a ``CAST(<expr> AS INTEGER)`` expression and declaring
        the result as an ``INTEGER``. The caller is responsible for
        interpreting the returned integer as a truth value.

        In practice this is identical to :meth:`Int`; the separate name
        exists so that call sites read as intent (``Builtins.Bool(...)``
        rather than ``Builtins.Int(...)`` when the semantic meaning is a
        truth value).

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``True``, ``False``, ``0``, ``1``, or
                  any coercible value) — bound as a ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS INTEGER))`` and whose ``current_datatype`` is
            ``int``.

        Example:
            Normalise an is_active column that stores mixed values::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                normalised = Builtins.Bool(users.is_active)
                rows = users.get_row([users.id, normalised])

            Compare a computed condition against a boolean literal::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Bool(users.age >= 18) == 1,
                )
                # SELECT [users].[id] FROM [users]
                # WHERE ((CAST(([users].[age] >= ?) AS INTEGER)) = ?)
                # Parameters: [18, 1]

            Coerce a raw literal — useful when the surrounding API expects
            a ColumnsOperation-shaped object::

                rows = users.get_row([
                    Builtins.Bool(True),    # -> (CAST(? AS INTEGER)) with param True
                    Builtins.Bool(False),   # -> (CAST(? AS INTEGER)) with param False
                ])

            Use as a numeric value in a SUM::

                active_count = Builtins.Sum(Builtins.Bool(users.is_active))
                rows = users.get_row([active_count])
                # SELECT (SUM((CAST([users].[is_active] AS INTEGER)))) FROM [users]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CASE WHEN {sql} THEN 1 ELSE 0 END)',p, int, c,)
    
    @staticmethod
    def TypeOf(value):
        """Return the SQLite storage class of a value using ``TYPEOF()``.

        Generates a ``TYPEOF(<expr>)`` expression. SQLite returns one of the
        following text values:

        - ``'null'``    — SQL NULL
        - ``'integer'`` — signed 64-bit integer
        - ``'real'``    — 8-byte IEEE floating point
        - ``'text'``    — UTF-8 / UTF-16 string
        - ``'blob'``    — binary data

        This is the closest SQL analogue of Python's ``type()``. The result
        is always a ``TEXT`` string, so it plays nicely with ``.like``,
        ``.startswith``, ``.In``, and other text-oriented chains.

        Args:
            value: The expression whose storage class is inspected. Supported
                types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(TYPEOF(<expr>))`` and whose ``current_datatype`` is always
            ``str``.

        Example:
            Audit a column that stores mixed types::

                from Ormophine.Sqlite import Driver, Builtins

                db      = Driver('app.db')
                records = db.records

                rows = records.get_row([
                    records.id,
                    Builtins.TypeOf(records.payload),
                ])
                # SELECT [records].[id], (TYPEOF([records].[payload])) FROM [records]
                # -> e.g. [(1, 'text'), (2, 'integer'), (3, 'blob'), ...]

            Filter only the rows that stored real numbers::

                rows = records.get_row(
                    [records.id, records.payload],
                    where=Builtins.TypeOf(records.payload) == 'real',
                )
                # SELECT ... WHERE ((TYPEOF([records].[payload])) = ?)
                # Parameters: ['real']

            Group records by storage class — fetch and count in Python::

                rows = records.get_row([Builtins.TypeOf(records.payload)])
                from collections import Counter
                histogram = Counter(t for (t,) in rows)
                # {'text': 120, 'integer': 45, 'real': 18, 'blob': 3, 'null': 7}

            Combine with a text-method chain::

                rows = records.get_row(
                    [records.id],
                    where=Builtins.TypeOf(records.payload).In(
                        ['integer', 'real']
                    ),
                )

            Inspect a raw literal::

                rows = records.get_row([
                    Builtins.TypeOf(42),      # -> 'integer'
                    Builtins.TypeOf(3.14),    # -> 'real'
                    Builtins.TypeOf('hello'), # -> 'text'
                    Builtins.TypeOf(None),    # -> 'null'
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(TYPEOF({sql}))', p, str, c)

    @staticmethod
    def Sign(value):
        """Return the sign of a number using SQLite's ``SIGN()`` function.

        Generates a ``SIGN(<expr>)`` expression. SQLite returns:

        - ``-1`` if the value is negative
        - `` 0`` if the value is zero
        - `` 1`` if the value is positive

        This mirrors Python's ``(x > 0) - (x < 0)`` idiom and is useful for
        bucketing, sorting by direction, or normalising deltas.

        .. note::
            ``SIGN()`` requires SQLite >= 3.35 (released 2021-03-12). On
            older libraries the generated SQL will fail at execution time.
            If you need a portable version, build it manually with
            ``Builtins.IIf(value > 0, 1, Builtins.IIf(value < 0, -1, 0))``.

        Args:
            value: The expression whose sign is computed. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(SIGN(<expr>))`` and whose ``current_datatype`` is ``int``.

        Example:
            Bucket movements by direction — up, flat, or down::

                from Ormophine.Sqlite import Driver, Builtins

                db        = Driver('analytics.db')
                movements = db.movements

                rows = movements.get_row([
                    movements.account_id,
                    movements.delta,
                    Builtins.Sign(movements.delta),
                ])
                # SELECT [movements].[account_id], [movements].[delta],
                #        (SIGN([movements].[delta]))
                # FROM [movements]
                # -> e.g. [(1, 250.0, 1), (1, -80.0, -1), (1, 0.0, 0), ...]

            Filter only the positive movements::

                rows = movements.get_row(
                    [movements.account_id, movements.delta],
                    where=Builtins.Sign(movements.delta) == 1,
                )
                # SELECT ... WHERE ((SIGN([movements].[delta])) = ?)
                # Parameters: [1]

            Sum signs to count net direction — positive means more ups
            than downs, and vice versa::

                net = Builtins.Sum(Builtins.Sign(movements.delta))
                rows = movements.get_row([movements.account_id, net])

            Sign of a computed expression::

                range_mid = (movements.high + movements.low) / 2
                rows = movements.get_row([
                    movements.symbol,
                    Builtins.Sign(movements.close - range_mid),
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} > 0 AS INTEGER) - CAST({sql} < 0 AS INTEGER))',p + p, int, c,)

    @staticmethod
    def Floor(value):
        """Round a number down to the nearest integer using SQLite's ``FLOOR()``.

        Generates a ``FLOOR(<expr>)`` expression. For positive numbers this
        behaves like truncation toward zero; for negative numbers it rounds
        away from zero (``FLOOR(-1.5) = -2``, unlike ``CAST(-1.5 AS INTEGER)``
        which gives ``-1``).

        .. note::
            ``FLOOR()`` requires SQLite >= 3.35. On older libraries, use
            the portable fallback::

                Builtins.IIf(
                    value >= 0,
                    Builtins.Int(value),
                    Builtins.Int(value) - 1,
                )

        Args:
            value: The expression to floor. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(FLOOR(<expr>))`` and whose ``current_datatype`` is ``int``.

        Example:
            Snap a price down to the whole dollar::

                from Ormophine.Sqlite import Driver, Builtins

                db       = Driver('store.db')
                products = db.products

                rows = products.get_row([
                    products.name,
                    products.price,
                    Builtins.Floor(products.price),
                ])
                # SELECT [products].[name], [products].[price],
                #        (FLOOR([products].[price]))
                # FROM [products]
                # -> e.g. [('Widget', 19.99, 19.0), ('Gadget', 24.50, 24.0), ...]

            Bucket scores into deciles::

                decile = Builtins.Floor(products.score / 10) * 10
                rows = products.get_row([decile, Builtins.Count('*')])
                # -> [0, 12], [10, 45], [20, 38], ...

            Handle negative values correctly (FLOOR rounds down, not
            toward zero)::

                rows = products.get_row([
                    Builtins.Floor(-1.5),   # -> -2.0
                    Builtins.Int(-1.5),     # -> -1   (truncation, not floor)
                ])

            Filter by floored value::

                rows = products.get_row(
                    [products.name, products.price],
                    where=Builtins.Floor(products.price) >= 20,
                )
                # SELECT ... WHERE ((FLOOR([products].[price])) >= ?)
                # Parameters: [20]

            Combined with arithmetic — stays numeric::

                discount = Builtins.Floor(products.price * 0.8)
                rows = products.get_row([products.name, discount])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS INTEGER) - ({sql} < CAST({sql} AS INTEGER)))',p + p + p, int, c,)
    
    @staticmethod
    def Ceil(value):
        """Round a number up to the nearest integer using SQLite's ``CEIL()``.

        Generates a ``CEIL(<expr>)`` expression. For positive numbers this
        rounds away from zero; for negative numbers it rounds toward zero
        (``CEIL(-1.5) = -1``, unlike ``FLOOR(-1.5) = -2``). This is the
        mirror image of :meth:`Floor`.

        .. note::
            ``CEIL()`` requires SQLite >= 3.35. On older libraries, use the
            portable fallback::

                Builtins.IIf(
                    value >= 0,
                    Builtins.Int(value) + 1,
                    Builtins.Int(value),
                )

        Args:
            value: The expression to ceil. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CEIL(<expr>))`` and whose ``current_datatype`` is ``int``.

        Example:
            Snap a price up to the whole dollar — a common "don't lose
            money on rounding" pattern::

                from Ormophine.Sqlite import Driver, Builtins

                db       = Driver('store.db')
                products = db.products

                rows = products.get_row([
                    products.name,
                    products.price,
                    Builtins.Ceil(products.price),
                ])
                # SELECT [products].[name], [products].[price],
                #        (CEIL([products].[price]))
                # FROM [products]
                # -> e.g. [('Widget', 19.01, 20.0), ('Gadget', 24.00, 24.0), ...]

            Pagination — compute how many pages of 20 items each::

                page_count = Builtins.Ceil(Builtins.Count('*') / 20)
                rows = products.get_row([page_count])
                # SELECT (CEIL(((COUNT(*)) / ?))) FROM [products]
                # Parameters: [20]

            Bucket scores into the next higher 10::

                next_ten = Builtins.Ceil(products.score / 10) * 10
                rows = products.get_row([products.id, next_ten])

            Handle negatives correctly::

                rows = products.get_row([
                    Builtins.Ceil(-1.5),   # -> -1.0
                    Builtins.Int(-1.5),    # -> -1   (same here, but for other reasons)
                ])

            Combine with Floor to build a rounded-down/rounded-up pair::

                low  = Builtins.Floor(products.price)
                high = Builtins.Ceil(products.price)
                rows = products.get_row([products.price, low, high])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS INTEGER) + ({sql} > CAST({sql} AS INTEGER)))',p + p + p, int, c,)

    @staticmethod
    def Find(value, sub):
        """Locate a substring within a value using SQLite's ``INSTR()`` function.

        Generates an ``INSTR(<value>, <sub>)`` expression. Returns the
        1-based position of the first occurrence of ``sub`` inside
        ``value``, or ``0`` if ``sub`` is not present.

        .. warning::
            SQLite's ``INSTR`` and Python's ``str.find`` differ in two ways
            that routinely trip people up:

            ==================  =========  =========
            Behaviour           Python     SQLite
            ==================  =========  =========
            Index of first char    0          1
            "Not found" value     -1          0
            ==================  =========  =========

            If you need strict Python semantics — e.g. so that
            ``Find(col, 'x') >= 0`` means "contains x" — add ``- 1`` to the
            result at the call site::

                py_find = Builtins.Find(users.name, 'x') - 1
                # py_find == -1 when not found, == 0 when found at position 0

            For a plain "does it contain this" check, :meth:`contains` on
            :class:`ColumnsOperation` is usually the better choice.

        Args:
            value: The haystack. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder.

            sub: The needle. Same accepted types as ``value``. Usually a
                plain string literal, but any expression is allowed.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(INSTR(<value>, <sub>))`` and whose ``current_datatype`` is
            ``int``. Parameters are concatenated left-to-right: first the
            haystack's parameters, then the needle's.

        Example:
            Find the position of a delimiter inside a text column::

                from Ormophine.Sqlite import Driver, Builtins

                db     = Driver('app.db')
                emails = db.emails

                at_pos = Builtins.Find(emails.address, '@')
                rows = emails.get_row([
                    emails.id,
                    emails.address,
                    at_pos,
                ])
                # SELECT [emails].[id], [emails].[address],
                #        (INSTR([emails].[address], ?))
                # FROM [emails]
                # Parameters: ['@']
                # -> e.g. [(1, 'alice@example.com', 6), (2, 'bob@x.io', 4), ...]

            Detect the presence of a substring — ``> 0`` because SQLite
            returns 0 (not -1) when the needle is missing::

                rows = emails.get_row(
                    [emails.id, emails.address],
                    where=Builtins.Find(emails.address, 'spam') > 0,
                )
                # SELECT ... WHERE ((INSTR([emails].[address], ?)) > ?)
                # Parameters: ['spam', 0]

            Python-equivalent "not found" check — add ``- 1`` so -1 means
            "missing"::

                py_find = Builtins.Find(emails.address, 'example') - 1
                rows = emails.get_row(
                    [emails.address],
                    where=py_find == -1,
                )
                # SELECT [emails].[address] FROM [emails]
                # WHERE (((INSTR([emails].[address], ?)) - ?) = ?)
                # Parameters: ['example', 1, -1]

            Use a column as the needle — find where one column appears
            inside another::

                rows = emails.get_row([
                    emails.id,
                    Builtins.Find(emails.address, emails.username),
                ])
                # SELECT [emails].[id],
                #        (INSTR([emails].[address], [emails].[username]))
                # FROM [emails]

            Combine with slicing to extract everything before the '@'::

                at_pos = Builtins.Find(emails.address, '@')
                local_part = emails.address[:at_pos - 1]
                rows = emails.get_row([emails.id, local_part])
        """
        s1, p1, _, c = Builtins._normalize(value)
        s2, p2, _, _ = Builtins._normalize(sub)
        return Builtins._make(f'(INSTR({s1}, {s2}))', p1 + p2, int, c)


    @staticmethod
    def Format(fmt, *args):
        """Format a string using SQLite's ``PRINTF()`` function.

        Generates a ``PRINTF(<fmt>, <arg1>, <arg2>, ...)`` expression.
        SQLite's ``PRINTF`` supports a subset of C's ``printf`` format
        specifiers:

        - ``%d`` — integer
        - ``%f`` — floating point
        - ``%s`` — string
        - ``%x`` / ``%X`` — hexadecimal
        - ``%%`` — literal percent sign

        Width, precision, and flags are supported (e.g. ``%5.2f``,
        ``%-10s``, ``%08d``), which makes this the SQL analogue of Python's
        ``%``-style string formatting (``'Hello, %s' % name``). For
        ``str.format()``-style ``{}`` placeholders, use
        :meth:`Builtins.Func` with ``'FORMAT'`` on SQLite >= 3.38.

        .. warning::
            The format string is bound as a parameter (``?``), but the
            *format specifier* inside it is interpreted by SQLite at
            execution time. A malformed format string will raise an SQL
            error; a mismatched number of specifiers versus arguments will
            silently substitute the wrong values or ``NULL``.

        Args:
            fmt: The format string. Usually a Python ``str`` literal, but
                any expression is allowed. It is bound as a parameter, so
                user-supplied format strings are safe from SQL injection —
                though you should still validate them against an allowlist
                if security matters.

            *args: Zero or more arguments to substitute into ``fmt``.
                Each may be a :class:`ColumnsOperation`, a :class:`Column`,
                or a raw Python value. They are concatenated left-to-right
                and their parameters appended in the same order.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(PRINTF(<fmt>, <arg1>, ...))`` and whose ``current_datatype``
            is always ``str``.

        Example:
            Classic greeting — the SQL analogue of ``'Hi, %s' % name``::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                greeting = Builtins.Format('Hello, %s!', users.name)
                rows = users.get_row([greeting])
                # SELECT (PRINTF(?, [users].[name])) FROM [users]
                # Parameters: ['Hello, %s!']
                # -> e.g. [('Hello, Alice!',), ('Hello, Bob!',), ...]

            Format a currency value::

                price = Builtins.Format('$%5.2f', users.balance)
                rows = users.get_row([
                    users.name,
                    price,
                ])
                # SELECT [users].[name], (PRINTF(?, [users].[balance]))
                # FROM [users]
                # Parameters: ['$%5.2f']
                # -> [('Alice', '$  123.45'), ('Bob', '$ 1234.56'), ...]

            Pad an integer with leading zeros — a common id-formatting
            pattern::

                padded_id = Builtins.Format('EMP-%05d', users.id)
                rows = users.get_row([padded_id])
                # -> [('EMP-00001',), ('EMP-00042',), ...]

            Build a CSV line from multiple columns::

                row_csv = Builtins.Format(
                    '%s,%s,%s',
                    users.name,
                    users.email,
                    users.age,
                )
                rows = users.get_row([row_csv])
                # SELECT (PRINTF(?, [users].[name], [users].[email], [users].[age]))
                # FROM [users]
                # Parameters: ['%s,%s,%s']

            Combine with other builtins::

                total = Builtins.Format(
                    'Total: %.2f USD',
                    Builtins.Sum(users.balance),
                )
                rows = users.get_row([total])
                # SELECT (PRINTF(?, (SUM([users].[balance])))) FROM [users]
                # Parameters: ['Total: %.2f USD']

            Escape a literal percent sign::

                percent = Builtins.Format('%d%% complete', users.progress)
                rows = users.get_row([percent])
                # Parameters: ['%d%% complete']
                # -> e.g. [('75% complete',), ('100% complete',), ...]
        """
        s0, p0, _, c = Builtins._normalize(fmt)
        parts, params = [s0], list(p0)
        for v in args:
            s, p, _, _ = Builtins._normalize(v)
            parts.append(s); params.extend(p)
        return Builtins._make(f'(PRINTF({", ".join(parts)}))', params, str, c)

    @staticmethod
    def Capitalize(value):
        """Capitalise a text value — first character upper, rest lower.

        SQLite has no native ``CAPITALIZE()`` function, so this helper
        composes one from two SQL expressions:

        .. code-block:: sql

            UPPER(SUBSTR(<expr>, 1, 1)) || LOWER(SUBSTR(<expr>, 2))

        The result is a new string with the first character converted to
        uppercase and every subsequent character converted to lowercase.
        This matches Python's ``str.capitalize()`` behaviour for the
        common case of an all-alphabetic ASCII input. Edge cases differ:
        Python treats non-ASCII letters specially, and both Python and
        this helper leave digits and punctuation unchanged.

        The result is always a ``TEXT`` string, so ``+`` chained after it
        produces concatenation (``||``) rather than arithmetic addition.

        Args:
            value: The expression whose first character is capitalised.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused. The fragment is embedded twice in the output
                  (once for the first char, once for the rest), so any
                  parameters it carries are also duplicated.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string — bound as a ``?`` placeholder (also
                  duplicated).

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(UPPER(SUBSTR(<expr>, 1, 1)) || LOWER(SUBSTR(<expr>, 2)))``
            and whose ``current_datatype`` is always ``str``.

        Example:
            Title-case names for display::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([
                    users.id,
                    Builtins.Capitalize(users.name),
                ])
                # SELECT [users].[id],
                #        (UPPER(SUBSTR([users].[name], 1, 1))
                #         || LOWER(SUBSTR([users].[name], 2)))
                # FROM [users]
                # -> e.g. [(1, 'Alice'), (2, 'Bob'), (3, 'Carol'), ...]
                #    even if the stored values were 'ALICE', 'bob', 'cAROL'

            Sort case-insensitively by name::

                rows = users.get_row(
                    [users.name],
                    order_by=Builtins.Capitalize(users.name),
                )

            Normalise before grouping::

                initial = Builtins.Capitalize(users.name)
                rows = users.get_row(
                    [initial],
                )
                from collections import Counter
                # Counter on the fetched values shows how many names start
                # with each capital letter.

            Chain with other string builtins::

                expr = Builtins.Capitalize(users.name).add_end('!')
                rows = users.get_row([expr])
                # -> 'Alice!', 'Bob!', ...

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Capitalize('hELLO wORLD'),   # -> 'Hello world'
                ])
                # SQL: (UPPER(SUBSTR(?, 1, 1)) || LOWER(SUBSTR(?, 2)))
                # Parameters: ['hELLO wORLD', 'hELLO wORLD']

            Combine with Trim to clean up and capitalise in one go::

                clean = Builtins.Capitalize(users.name.strip())
                rows = users.get_row([clean])
        """
        sql, p, _, c = Builtins._normalize(value)
        inner = f'UPPER(SUBSTR({sql}, 1, 1)) || LOWER(SUBSTR({sql}, 2))'
        return Builtins._make(f'({inner})', p, str, c)

    @staticmethod
    def Total(value):
        """Sum a set of values using SQLite's ``TOTAL()`` aggregate.

        Generates a ``TOTAL(<expr>)`` expression. ``TOTAL`` behaves like
        :meth:`Sum` with one critical difference: **empty groups return
        ``0.0`` instead of ``NULL``**. This makes it the safer choice when
        you need a numeric result even when no rows match, or when the
        aggregated column contains NULLs:

        .. code-block:: sql

            SUM  of (NULL, NULL) -> NULL
            TOTAL of (NULL, NULL) -> 0.0

            SUM  of ()          -> NULL
            TOTAL of ()         -> 0.0

        The result is always a REAL (float) — even when every input is an
        integer — because SQLite defines ``TOTAL`` in terms of
        floating-point arithmetic.

        Args:
            value: The expression to sum. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(TOTAL(<expr>))`` and whose ``current_datatype`` is always
            ``float``.

        Example:
            Sum with a guaranteed numeric result — no ``None`` to guard
            against in Python::

                from Ormophine.Sqlite import Driver, Builtins

                db       = Driver('store.db')
                products = db.products

                total = Builtins.Total(products.price)
                rows = products.get_row([total])
                # SELECT (TOTAL([products].[price])) FROM [products]
                # -> [(1234.56,)] even if the table is empty

            Compare with SUM to see the difference::

                rows = products.get_row([
                    Builtins.Sum(products.price),     # -> None when empty
                    Builtins.Total(products.price),   # -> 0.0 when empty
                ])
                # -> [(None, 0.0)] on an empty table

            Sum a nullable column — TOTAL treats NULLs as 0::

                rows = products.get_row([
                    Builtins.Total(products.discount),   # NULLs -> 0
                ])
                # SELECT (TOTAL([products].[discount])) FROM [products]

            Safety-check division — Total never produces NULL, so the
            denominator in a ratio is always numeric::

                ratio = Builtins.Total(products.revenue) / Builtins.Total(products.cost)
                rows = products.get_row([ratio])
                # SQLite returns NULL when dividing by 0.0 — check in Python if
                # the denominator can actually be zero:
                # -> [(None,)] if TOTAL(cost) == 0.0, else [(2.34,)]

            Conditional aggregate — count of matching rows via a computed
            IIF::

                paid = Builtins.Total(
                    Builtins.IIf(products.paid == 1, products.price, 0)
                )
                rows = products.get_row([paid])
                # SELECT (TOTAL((IIF(([products].[paid] = ?),
                #                    [products].[price], ?))))
                # FROM [products]
                # Parameters: [1, 0]

            Chained arithmetic — stays numeric::

                padded = Builtins.Total(products.price) + 100
                # SELECT ((TOTAL([products].[price])) + ?) FROM [products]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(TOTAL({sql}))', p, float, c)

    @staticmethod
    def IsNull(value):
        """Test whether a value is NULL.

        Generates an ``(<expr> IS NULL)`` predicate. SQLite evaluates this
        to ``1`` (true) when the expression evaluates to NULL, and ``0``
        (false) otherwise.

        This is the explicit, always-correct way to check for NULL. Using
        the ordinary comparison operator — ``column == None`` — is also
        supported by this ORM (see :meth:`Column.eq`) but only when the
        right-hand side is literally ``None``. ``IsNull`` works uniformly
        with any expression:

        - A column that may contain NULL
        - A computed expression that may return NULL (e.g. ``Sqrt`` of a
          negative number, ``Find`` returning no match, aggregate over an
          empty group with ``Sum``)
        - A raw Python ``None`` literal

        Args:
            value: The expression to test. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder. In
                  particular, ``IsNull(None)`` produces ``(? IS NULL)`` with
                  the ``None`` bound as a parameter, which is always true.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``((<expr>) IS NULL)`` and whose ``current_datatype`` is
            ``int`` — SQLite returns 0 or 1 for boolean predicates.

        Example:
            Select users who have not yet provided an email::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.IsNull(users.email),
                )
                # SELECT [users].[id], [users].[username] FROM [users]
                # WHERE (([users].[email]) IS NULL)

            Negate the check — see :meth:`IsNotNull`::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.IsNotNull(users.email),
                )

            Combine with AND to build richer filters::

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.IsNull(users.email)
                        & (users.created_at > '2024-01-01'),
                )
                # SELECT ... WHERE ((([users].[email]) IS NULL)
                #                    AND ([users].[created_at] > ?))
                # Parameters: ['2024-01-01']

            Test a computed expression that might return NULL — the Sqrt
            of a negative number::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.IsNull(
                        Builtins.Sqrt(users.balance - users.debt)
                    ),
                )
                # -> users whose balance < debt (Sqrt returns NULL)
                # SELECT [users].[id] FROM [users]
                # WHERE ((SQRT(([users].[balance] - [users].[debt]))) IS NULL)

            Count how many rows have a NULL value in one column::

                missing_emails = Builtins.Sum(Builtins.IsNull(users.email))
                rows = users.get_row([missing_emails])
                # SELECT (SUM((([users].[email]) IS NULL))) FROM [users]
                # -> [(42,)] if 42 users have no email

            Check for a raw literal ``None``::

                rows = users.get_row([
                    Builtins.IsNull(None),   # -> ((?) IS NULL) -> always 1
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(({sql}) IS NULL)', p, int, c)

    @staticmethod
    def IsNotNull(value):
        """Test whether a value is not NULL.

        Generates an ``(<expr> IS NOT NULL)`` predicate. SQLite evaluates
        this to ``1`` (true) when the expression produces any non-NULL
        value, and ``0`` (false) when it evaluates to NULL.

        The exact logical negation of :meth:`IsNull`. Use whichever reads
        more naturally at the call site — both compile to distinct SQL but
        produce the same set of rows when their results are inverted.

        Args:
            value: The expression to test. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder. In
                  particular, ``IsNotNull(42)`` produces ``(? IS NOT NULL)``
                  with the ``42`` bound as a parameter, which is always true;
                  ``IsNotNull(None)`` is always false.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``((<expr>) IS NOT NULL)`` and whose ``current_datatype`` is
            ``int`` — SQLite returns 0 or 1 for boolean predicates.

        Example:
            Select users who have provided an email::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row(
                    [users.id, users.username, users.email],
                    where=Builtins.IsNotNull(users.email),
                )
                # SELECT [users].[id], [users].[username], [users].[email]
                # FROM [users]
                # WHERE (([users].[email]) IS NOT NULL)

            Combine with OR to allow either of two identifier columns::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.IsNotNull(users.email)
                        | Builtins.IsNotNull(users.phone),
                )
                # SELECT [users].[id] FROM [users]
                # WHERE ((([users].[email]) IS NOT NULL)
                #        OR (([users].[phone]) IS NOT NULL))

            Count non-NULL values in a column — the inverse of the
            ``IsNull`` count::

                have_email = Builtins.Sum(Builtins.IsNotNull(users.email))
                rows = users.get_row([have_email])
                # SELECT (SUM((([users].[email]) IS NOT NULL))) FROM [users]

            Test a computed expression whose non-NULLness is meaningful::

                valid_ratio = Builtins.Floor(
                    users.successes / users.attempts
                )
                rows = users.get_row(
                    [users.id],
                    where=Builtins.IsNotNull(valid_ratio),
                )
                # -> users whose attempts > 0 (division by zero yields NULL)

            Chained with a case check — the classic "both or neither"
            validation pattern::

                rows = users.get_row(
                    [users.id],
                    where=(Builtins.IsNotNull(users.email)
                            & Builtins.IsNotNull(users.verified_at))
                        | (Builtins.IsNull(users.email)
                            & Builtins.IsNull(users.verified_at)),
                )
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(({sql}) IS NOT NULL)', p, int, c)

    @staticmethod
    def Between(value, low, high):
        """Test whether a value lies within an inclusive range.

        Generates an ``(<expr> BETWEEN <low> AND <high>)`` predicate.
        SQLite evaluates this to ``1`` (true) when ``low <= value <= high``
        and ``0`` otherwise. Both bounds are inclusive, matching Python's
        ``low <= x <= high`` idiom exactly.

        .. note::
            SQLite's ``BETWEEN`` is equivalent to
            ``(value >= low) AND (value <= high)`` but is a single operator
            with well-defined semantics for all three operand types. When
            any of the three operands is NULL the result is NULL, which the
            surrounding query treats as "false" in a ``WHERE`` clause.

        Args:
            value: The expression to test. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``?`` placeholder.

            low: The lower bound (inclusive). Same accepted types as
                ``value``.

            high: The upper bound (inclusive). Same accepted types as
                ``value``.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``((<value>) BETWEEN <low> AND <high>)`` and whose
            ``current_datatype`` is ``int``. Parameters are concatenated
            left-to-right: first ``value``'s, then ``low``'s, then
            ``high``'s.

        Example:
            Select products in a price band::

                from Ormophine.Sqlite import Driver, Builtins

                db       = Driver('store.db')
                products = db.products

                rows = products.get_row(
                    [products.name, products.price],
                    where=Builtins.Between(products.price, 10.0, 50.0),
                )
                # SELECT [products].[name], [products].[price] FROM [products]
                # WHERE (([products].[price]) BETWEEN ? AND ?)
                # Parameters: [10.0, 50.0]

            Date-range filter — the most common real-world use::

                users = db.users
                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Between(
                        users.created_at,
                        '2024-01-01',
                        '2024-12-31',
                    ),
                )
                # SELECT ... WHERE (([users].[created_at])
                #                    BETWEEN ? AND ?)
                # Parameters: ['2024-01-01', '2024-12-31']

            Filter on a computed expression::

                rows = products.get_row(
                    [products.name],
                    where=Builtins.Between(
                        products.price * 0.9,      # discounted price
                        5.0,
                        45.0,
                    ),
                )
                # SELECT [products].[name] FROM [products]
                # WHERE (([products].[price] * ?) BETWEEN ? AND ?)
                # Parameters: [0.9, 5.0, 45.0]

            Boundaries using other columns::

                rows = products.get_row(
                    [products.name, products.price],
                    where=Builtins.Between(
                        products.price,
                        products.cost,
                        products.cost * 2,
                    ),
                )
                # SELECT ... WHERE (([products].[price])
                #                    BETWEEN [products].[cost]
                #                        AND ([products].[cost] * ?))
                # Parameters: [2]

            Negate the check — rows outside the band::

                # "not between" is expressed by combining Between with
                # the ~ operator, or simply by negating at the Python level:
                in_band = Builtins.Between(products.price, 10.0, 50.0)
                rows = products.get_row(
                    [products.name],
                    where=(in_band == 0),
                )
                # SELECT [products].[name] FROM [products]
                # WHERE (((([products].[price]) BETWEEN ? AND ?)) = ?)
                # Parameters: [10.0, 50.0, 0]

            NULL handling — a NULL value in any operand makes the whole
            predicate NULL (treated as false). To include NULLs, add an
            explicit OR::

                rows = products.get_row(
                    [products.name],
                    where=Builtins.Between(products.price, 10.0, 50.0)
                        | Builtins.IsNull(products.price),
                )
        """
        s,  p,  _,  c  = Builtins._normalize(value)
        lo, lp, _,  _  = Builtins._normalize(low)
        hi, hp, _,  _  = Builtins._normalize(high)
        return Builtins._make(f'(({s}) BETWEEN {lo} AND {hi})', p + lp + hp, int, c)

    @staticmethod
    def IIf(condition, then_value, else_value):
        """One-line conditional — the SQL analogue of Python's ``a if cond else b``.

        Generates an ``IIF(<cond>, <then>, <else>)`` expression. SQLite
        evaluates ``condition`` first; if it is truthy (any non-zero,
        non-NULL value), the expression yields ``then_value``; otherwise it
        yields ``else_value``.

        This is the value-producing sibling of the SQL ``CASE`` statement
        and the direct equivalent of Python's ternary conditional operator::

            Python:   x if cond else y
            SQL:      IIF(cond, x, y)
            ORM:      Builtins.IIf(cond, x, y)

        .. note::
            ``IIF()`` requires SQLite >= 3.32 (released 2020-05-22). On
            older libraries, use ``Builtins.Func`` to write a ``CASE``
            expression manually, or upgrade SQLite. The keyword ``CASE``
            with identical semantics works on every version.

            Unlike Python's ``and`` / ``or``, SQLite's ``IIF`` **always
            evaluates both branches** before choosing one. This matters
            for expressions with side effects (there are none in SQL) or
            with potential errors — e.g. division by zero returns NULL
            rather than skipping. If both branches might divide by zero,
            guard the divisor with an inner ``IIF``.

        Args:
            condition: The test expression. May be any standard operand:

                - :class:`ColumnsOperation` — typically a comparison like
                  ``users.age >= 18``.
                - :class:`Column` — used directly as a boolean.
                - A raw Python value (``True``, ``False``, ``0``, ``1``)
                  — bound as a parameter. SQLite treats ``0`` as false
                  and any other number as true.

            then_value: What to return when ``condition`` is truthy.
                Same accepted types as ``condition``.

            else_value: What to return when ``condition`` is falsy.
                Same accepted types as ``condition``.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(IIF(<cond>, <then>, <else>))`` and whose ``current_datatype``
            is ``None``. The datatype is not propagated because the two
            branches may disagree (e.g. ``str`` versus ``int``); downstream
            ``+`` operators will choose arithmetic by default, which the
            caller may override by wrapping the result in :meth:`Str`,
            :meth:`Int`, or :meth:`Float`.

        Example:
            Categorise ages into minor / adult — the classic pattern::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                category = Builtins.IIf(users.age >= 18, 'adult', 'minor')
                rows = users.get_row([
                    users.name,
                    users.age,
                    category,
                ])
                # SELECT [users].[name], [users].[age],
                #        (IIF(([users].[age] >= ?), ?, ?))
                # FROM [users]
                # Parameters: [18, 'adult', 'minor']
                # -> [('Alice', 30, 'adult'), ('Bob', 15, 'minor'), ...]

            Fill NULL with a fallback — equivalent to ``COALESCE`` but
            with a boolean test::

                display_email = Builtins.IIF(
                    Builtins.IsNull(users.email),
                    'no email',
                    users.email,
                )
                rows = users.get_row([users.username, display_email])
                # SELECT [users].[username],
                #        (IIF((([users].[email]) IS NULL), ?, [users].[email]))
                # FROM [users]
                # Parameters: ['no email']

            Nested conditionals — a two-threshold bucketing::

                label = Builtins.IIf(
                    users.score >= 90,
                    'A',
                    Builtins.IIf(
                        users.score >= 80,
                        'B',
                        Builtins.IIf(
                            users.score >= 70,
                            'C',
                            'F',
                        ),
                    ),
                )
                rows = users.get_row([users.name, users.score, label])
                # The nesting produces deeply parenthesised SQL:
                # (IIF(([users].[score] >= ?), ?, (IIF(([users].[score] >= ?),
                #      ?, (IIF(([users].[score] >= ?), ?, ?))))))
                # Parameters: [90, 'A', 80, 'B', 70, 'C', 'F']

            Conditional arithmetic — bonus only for top performers::

                adjusted_salary = Builtins.IIf(
                    users.rating > 4,
                    users.salary * 1.1,
                    users.salary,
                )
                rows = users.get_row([
                    users.name,
                    users.salary,
                    adjusted_salary,
                ])
                # SELECT [users].[name], [users].[salary],
                #        (IIF(([users].[rating] > ?),
                #             ([users].[salary] * ?),
                #             [users].[salary]))
                # FROM [users]
                # Parameters: [4, 1.1]

            Coerce the result to a specific type with a cast builtin::

                label_num = Builtins.Int(
                    Builtins.IIf(users.is_active == 1, 100, 0)
                )
                rows = users.get_row([label_num])

            Count matches via SUM of IIF — a common "conditional aggregate"
            idiom::

                active_count = Builtins.Sum(
                    Builtins.IIf(users.is_active == 1, 1, 0)
                )
                rows = users.get_row([active_count])
                # SELECT (SUM((IIF(([users].[is_active] = ?), ?, ?))))
                # FROM [users]
                # Parameters: [1, 1, 0]

            Diverging branches with different datatypes — the reason
            ``current_datatype`` is ``None`` on the result::

                mixed = Builtins.IIf(users.has_phone == 1, users.phone, 0)
                # If has_phone, returns a string; else returns integer 0.
                # Wrap with Builtins.Str if the surrounding context expects
                # a string:
                safe = Builtins.Str(mixed)
        """
        cs, cp, _, c = Builtins._normalize(condition)
        ts, tp, _, _ = Builtins._normalize(then_value)
        es, ep, _, _ = Builtins._normalize(else_value)
        return Builtins._make(f'(IIF({cs}, {ts}, {es}))', cp + tp + ep, None, c)

    @staticmethod
    def Date(value):
        """Extract the date portion of a value using SQLite's ``date()`` function.

        Generates a ``date(<expr>)`` expression. The result is a TEXT
        string in ISO 8601 format: ``'YYYY-MM-DD'``. Inputs accepted by
        SQLite include:

        - An ISO date/datetime string: ``'2024-03-15'``, ``'2024-03-15 09:30:00'``
        - A Julian day number (REAL)
        - A Unix epoch value (INTEGER) — implicitly converted
        - The keyword ``'now'`` for the current UTC date

        This is the SQL equivalent of ``datetime.date()`` from Python's
        ``datetime`` module — it discards the time-of-day component.

        Args:
            value: The expression whose date component is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(date(<expr>))`` and whose ``current_datatype`` is ``str``.

        Example:
            Get the signup date for every user — strip the time component::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([
                    users.id,
                    users.created_at,
                    Builtins.Date(users.created_at),
                ])
                # SELECT [users].[id], [users].[created_at],
                #        (date([users].[created_at]))
                # FROM [users]
                # -> [(1, '2024-03-15 09:30:42', '2024-03-15'), ...]

            Filter by a specific day — everything created on March 15::

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.Date(users.created_at) == '2024-03-15',
                )
                # SELECT [users].[id], [users].[username] FROM [users]
                # WHERE ((date([users].[created_at])) = ?)
                # Parameters: ['2024-03-15']

            Group by day and count — do the grouping in Python after
            fetching, since the ORM has no GROUP BY helper::

                rows = users.get_row([Builtins.Date(users.created_at)])
                from collections import Counter
                daily = Counter(d for (d,) in rows)
                # {'2024-03-15': 12, '2024-03-16': 8, ...}

            Compare against the current date — the ``'now'`` keyword::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Date(users.created_at) == Builtins.Date('now'),
                )
                # SELECT [users].[id] FROM [users]
                # WHERE ((date([users].[created_at])) = (date(?)))
                # Parameters: ['now']

            Chain with date modifiers for windows of time::

                first_of_month = Builtins.DateAdd(users.created_at, 'start of month')
                rows = users.get_row([
                    users.id,
                    first_of_month,
                ])
                # SELECT [users].[id],
                #        (date([users].[created_at], ?))
                # FROM [users]
                # Parameters: ['start of month']

            Pass a raw literal::

                rows = users.get_row([
                    Builtins.Date('2024-03-15 14:30:00'),   # -> '2024-03-15'
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f"(date({sql}))", p, str, c)

    @staticmethod
    def Time(value):
        """Extract the time-of-day portion of a value using SQLite's ``time()``.

        Generates a ``time(<expr>)`` expression. The result is a TEXT
        string in ISO 8601 format: ``'HH:MM:SS'``. Inputs accepted by
        SQLite mirror those of :meth:`Date`:

        - An ISO date/datetime string: ``'2024-03-15 09:30:00'``
        - A Julian day number (REAL)
        - A Unix epoch value (INTEGER)
        - The keyword ``'now'`` for the current UTC time

        This is the SQL equivalent of ``datetime.time()`` from Python's
        ``datetime`` module — it discards the date component.

        Args:
            value: The expression whose time component is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(time(<expr>))`` and whose ``current_datatype`` is ``str``.

        Example:
            Get the signup time for every user::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([
                    users.id,
                    users.created_at,
                    Builtins.Time(users.created_at),
                ])
                # SELECT [users].[id], [users].[created_at],
                #        (time([users].[created_at]))
                # FROM [users]
                # -> [(1, '2024-03-15 09:30:42', '09:30:42'), ...]

            Filter by time-of-day range — office-hours signups::

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.Time(users.created_at) >= '09:00:00'
                        and Builtins.Time(users.created_at) < '17:00:00',
                )
                # Because BETWEEN is inclusive on both ends, use two
                # comparisons for a half-open range.
                # SELECT ... WHERE ((time([users].[created_at])) >= ?)
                #               AND ((time([users].[created_at])) < ?)
                # Parameters: ['09:00:00', '17:00:00']

            Extract the hour via :meth:`Hour` instead of slicing in Python::

                rows = users.get_row([
                    users.id,
                    Builtins.Hour(users.created_at),
                ])

            Compare against the current time::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Time(users.created_at)
                        < Builtins.Time('now'),
                )
                # SELECT [users].[id] FROM [users]
                # WHERE ((time([users].[created_at])) < (time(?)))
                # Parameters: ['now']

            Pass a raw literal::

                rows = users.get_row([
                    Builtins.Time('2024-03-15 14:30:00'),   # -> '14:30:00'
                ])

            Build a compact "time ago" bucket with IIF::

                bucket = Builtins.IIf(
                    Builtins.Hour(users.created_at) < 12,
                    'AM',
                    'PM',
                )
                rows = users.get_row([users.id, bucket])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f"(time({sql}))", p, str, c)

    @staticmethod
    def DateTime(value):
        """Normalise a value to a full datetime using SQLite's ``datetime()``.

        Generates a ``datetime(<expr>)`` expression. The result is a TEXT
        string in ISO 8601 format: ``'YYYY-MM-DD HH:MM:SS'`` (UTC unless
        the input carries a timezone or a ``'localtime'`` modifier is
        applied). Inputs accepted by SQLite mirror those of :meth:`Date`
        and :meth:`Time`:

        - An ISO date or datetime string
        - A Julian day number (REAL)
        - A Unix epoch value (INTEGER)
        - The keyword ``'now'`` for the current UTC datetime

        This is the SQL equivalent of Python's ``datetime.datetime``
        constructor on a normalised value. Its main uses are:

        - **Normalising** inputs of mixed shape so they all compare
          consistently.
        - **Upgrading** a date-only string (``'2024-03-15'``) to a full
          datetime (``'2024-03-15 00:00:00'``).
        - **Getting the current timestamp** via ``DateTime('now')``.

        Args:
            value: The expression whose full datetime is produced.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(datetime(<expr>))`` and whose ``current_datatype`` is
            ``str``.

        Example:
            Normalise mixed-format timestamps for display::

                from Ormophine.Sqlite import Driver, Builtins

                db     = Driver('app.db')
                events = db.events

                rows = events.get_row([
                    events.id,
                    events.occurred_at,                       # mixed shapes
                    Builtins.DateTime(events.occurred_at),   # all normalised
                ])
                # SELECT [events].[id], [events].[occurred_at],
                #        (datetime([events].[occurred_at]))
                # FROM [events]
                # -> [(1, '2024-03-15', '2024-03-15 00:00:00'), ...]

            Get the current UTC datetime as a SELECT column::

                rows = events.get_row([
                    Builtins.DateTime('now'),
                ])
                # SELECT (datetime(?)) FROM [events]
                # Parameters: ['now']
                # -> [('2024-03-15 14:30:42',)]

            Compare against the current datetime for "last 24 hours"::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.DateTime(events.occurred_at)
                        >= Builtins.DateTimeAdd('now', '-1 day'),
                )
                # SELECT [events].[id], [events].[occurred_at] FROM [events]
                # WHERE ((datetime([events].[occurred_at]))
                #         >= (datetime(?, ?)))
                # Parameters: ['now', '-1 day']

            Compare against the current datetime for "last week"::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.DateTime(events.occurred_at)
                        >= Builtins.DateTimeAdd('now', '-7 days'),
                )

            Combine with IIF to bucket events into "recent / older"::

                recent = Builtins.IIf(
                    Builtins.DateTime(events.occurred_at)
                        >= Builtins.DateTimeAdd('now', '-1 day'),
                    'recent',
                    'older',
                )
                rows = events.get_row([events.id, recent])
                # Parameters: ['now', '-1 day', 'recent', 'older']

            Store into a datetime column during an UPDATE — SQLite
            accepts the emitted string directly::

                events.update(
                    update={events.last_seen: Builtins.DateTime('now')},
                    where=events.id == 42,
                )

            Pass a raw literal to normalise at the SQL layer::

                rows = events.get_row([
                    Builtins.DateTime('2024-03-15'),           # -> '2024-03-15 00:00:00'
                    Builtins.DateTime('2024-03-15 09:30:00'),  # unchanged
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f"(datetime({sql}))", p, str, c)
    
    @staticmethod
    def Strftime(fmt, value):
        """Format a date/time value according to a strftime-style format string.

        Generates a ``strftime(<fmt>, <expr>)`` expression. This is the SQL
        analogue of Python's ``datetime.strftime()`` method, using the same
        format specifier syntax. SQLite supports the standard POSIX
        ``strftime`` specifiers:

        - ``%Y`` — four-digit year (``2024``)
        - ``%m`` — two-digit month (``01``–``12``)
        - ``%d`` — two-digit day of month (``01``–``31``)
        - ``%H`` — two-digit hour, 24-hour clock (``00``–``23``)
        - ``%M`` — two-digit minute (``00``–``59``)
        - ``%S`` — two-digit second (``00``–``59``)
        - ``%w`` — day of week (``0`` = Sunday, ``6`` = Saturday)
        - ``%j`` — day of year (``001``–``366``)
        - ``%W`` — week of year, Monday-based (``00``–``53``)
        - ``%%`` — literal percent sign

        The result is always a TEXT string, so ``+`` chained after it
        produces concatenation (``||``) rather than arithmetic addition.

        Args:
            fmt: The format string. Typically a Python ``str`` literal
                like ``'%Y-%m-%d'``. It is bound as a parameter, so it
                can be user-supplied safely — though for full safety you
                should validate the specifiers against an allowlist.

            value: The date/time expression to format. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(strftime(?, <expr>))`` and whose ``current_datatype`` is
            ``str``. The parameters are ``[fmt] + value's_parameters``.

        Example:
            Format a timestamp as ``YYYY-MM-DD``::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([
                    users.id,
                    Builtins.Strftime('%Y-%m-%d', users.created_at),
                ])
                # SELECT [users].[id], (strftime(?, [users].[created_at]))
                # FROM [users]
                # Parameters: ['%Y-%m-%d']
                # -> [(1, '2024-03-15'), ...]

            Format a human-readable datetime — note the space, colon, etc.::

                pretty = Builtins.Strftime(
                    '%Y-%m-%d %H:%M:%S',
                    users.created_at,
                )
                rows = users.get_row([users.id, pretty])
                # -> [(1, '2024-03-15 09:30:42'), ...]

            Format only the time portion::

                rows = users.get_row([
                    Builtins.Strftime('%H:%M', users.created_at),
                ])
                # -> [('09:30',), ('14:45',), ...]

            Month-year grouping — useful for reporting::

                month_key = Builtins.Strftime('%Y-%m', users.created_at)
                rows = users.get_row([month_key])
                from collections import Counter
                monthly = Counter(m for (m,) in rows)
                # {'2024-01': 45, '2024-02': 38, '2024-03': 52, ...}

            Custom display format — day name and ordinal day::

                display = Builtins.Strftime(
                    'Day %j of %Y (%A)',
                    users.created_at,
                )
                # Note: %A is NOT supported by SQLite (only by C strftime).
                # The correct SQLite specifier is %w for numeric weekday.
                # SQLite silently returns the format string unchanged for
                # unknown specifiers, so prefer the numeric forms:
                safe_display = Builtins.Strftime(
                    'Day %j of %Y',
                    users.created_at,
                )
                # -> 'Day 075 of 2024'

            Filter by formatted string::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Strftime('%Y', users.created_at) == '2024',
                )
                # SELECT [users].[id] FROM [users]
                # WHERE ((strftime(?, [users].[created_at])) = ?)
                # Parameters: ['%Y', '2024']

            Chain with string methods — current_datatype is str::

                expr = Builtins.Strftime('%Y', users.created_at).add_end('-Q1')
                rows = users.get_row([expr])
                # -> '2024-Q1'

            Literal percent sign via ``%%``::

                rows = users.get_row([
                    Builtins.Strftime('%Y%%', users.created_at),
                ])
                # -> [('2024%',), ...]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f"(strftime(?, {sql}))", [fmt] + p, str, c)

    @staticmethod
    def JulianDay(value):
        """Convert a date/time value to its Julian day number.

        Generates a ``julianday(<expr>)`` expression. SQLite returns the
        value as a REAL (float) representing days since noon UTC on
        24 November 4714 BC in the proleptic Gregorian calendar. This is
        the same numbering used by astronomers and by Julian Date systems
        in general.

        Because the result is a plain number, it is ideal for arithmetic
        that spans days, months, or years — especially date differences.
        Subtracting two Julian day numbers yields the number of days
        between two moments, with a fractional part for the hours.

        Args:
            value: The date/time expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(julianday(<expr>))`` and whose ``current_datatype`` is always
            ``float``.

        Example:
            Inspect the underlying numeric value of a timestamp::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([
                    users.created_at,
                    Builtins.JulianDay(users.created_at),
                ])
                # SELECT [users].[created_at], (julianday([users].[created_at]))
                # FROM [users]
                # -> [('2024-03-15 09:30:42', 2460385.396...), ...]

            Day count between two dates — the classic ``julianday(b) - julianday(a)``
            idiom::

                days_between = (
                    Builtins.JulianDay(users.created_at)
                    - Builtins.JulianDay('2024-01-01')
                )
                rows = users.get_row([
                    users.username,
                    days_between,
                ])
                # SELECT [users].[username],
                #        ((julianday([users].[created_at])) - (julianday(?)))
                # FROM [users]
                # Parameters: ['2024-01-01']
                # -> [('Alice', 74.396...), ('Bob', 12.184...), ...]

            Whole-day version — cast to INTEGER to drop the fractional part.
            See :meth:`DateDiffDays` for a ready-made helper::

                whole_days = Builtins.Int(
                    Builtins.JulianDay(users.created_at)
                    - Builtins.JulianDay('2024-01-01')
                )
                # -> [('Alice', 74), ('Bob', 12), ...]

            Fractional hours since an event::

                hours_since = (
                    Builtins.JulianDay('now')
                    - Builtins.JulianDay(users.last_seen)
                ) * 24
                rows = users.get_row([users.username, hours_since])
                # SELECT [users].[username],
                #        (((julianday(?)) - (julianday([users].[last_seen]))) * ?)
                # FROM [users]
                # Parameters: ['now', 24]

            Sort by actual moment in time — Julian day numbers sort
            identically to the underlying timestamps::

                rows = users.get_row(
                    [users.username, users.created_at],
                    order_by=Builtins.JulianDay(users.created_at),
                )

            Compare against a threshold expressed in days::

                rows = users.get_row(
                    [users.username],
                    where=Builtins.JulianDay('now')
                        - Builtins.JulianDay(users.created_at) < 7,
                )
                # Users who signed up in the last week.

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.JulianDay('2024-03-15'),   # -> 2460384.5
                    Builtins.JulianDay('now'),          # -> current Julian day
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f"(julianday({sql}))", p, float, c)

    @staticmethod
    def UnixEpoch(value):
        """Convert a date/time value to a Unix timestamp (seconds since 1970-01-01 UTC).

        Generates a ``unixepoch(<expr>)`` expression. SQLite returns the
        value as an INTEGER representing the number of whole seconds since
        the Unix epoch (midnight UTC on 1 January 1970). This is the same
        numbering used by Python's ``time.time()`` and by most modern
        systems.

        .. note::
            ``unixepoch()`` requires SQLite >= 3.38 (released 2022-02-22).
            On older libraries, the portable equivalent is
            ``Builtins.Int((Builtins.JulianDay(x) - 2440587.5) * 86400)``.

        The result is always an ``INTEGER``, so it plays nicely with
        arithmetic, comparisons, and other numeric builtins.

        Args:
            value: The date/time expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder. The special string ``'now'`` returns the
                  current epoch — see :meth:`UnixNow` for a shortcut.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(unixepoch(<expr>))`` and whose ``current_datatype`` is always
            ``int``.

        Example:
            Display the raw epoch value alongside a timestamp::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([
                    users.created_at,
                    Builtins.UnixEpoch(users.created_at),
                ])
                # SELECT [users].[created_at],
                #        (unixepoch([users].[created_at]))
                # FROM [users]
                # -> [('2024-03-15 09:30:42', 1710495042), ...]

            Compute elapsed seconds since signup::

                elapsed = Builtins.UnixNow() - Builtins.UnixEpoch(users.created_at)
                rows = users.get_row([users.username, elapsed])
                # SELECT [users].[username],
                #        ((unixepoch(?)) - (unixepoch([users].[created_at])))
                # FROM [users]
                # Parameters: ['now']

            Elapsed days — divide by 86400::

                days = (Builtins.UnixNow()
                        - Builtins.UnixEpoch(users.created_at)) / 86400
                rows = users.get_row([users.username, days])

            Filter by an absolute cutoff timestamp::

                cutoff = 1704067200   # 2024-01-01 00:00:00 UTC
                rows = users.get_row(
                    [users.username],
                    where=Builtins.UnixEpoch(users.created_at) > cutoff,
                )
                # SELECT [users].[username] FROM [users]
                # WHERE ((unixepoch([users].[created_at])) > ?)
                # Parameters: [1704067200]

            Store a timestamp as an integer during an UPDATE — useful when
            a column is declared INTEGER for portability::

                users.update(
                    update={users.last_seen_epoch: Builtins.UnixNow()},
                    where=users.id == 42,
                )

            Sort by absolute moment::

                rows = users.get_row(
                    [users.username],
                    order_by=Builtins.UnixEpoch(users.created_at),
                )

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.UnixEpoch('2024-03-15 00:00:00'),   # -> 1710460800
                    Builtins.UnixEpoch('now'),                    # -> current epoch
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST((julianday({sql}) - 2440587.5) * 86400 AS INTEGER))',p, int, c,)

    @staticmethod
    def Year(value):
        """Extract the four-digit year from a date/time value.

        Generates ``CAST(strftime('%Y', <expr>) AS INTEGER)``. The result is
        always an ``INTEGER``. SQLite's ``strftime`` returns a string for
        this specifier, so the explicit ``CAST`` is required to keep the
        datatype honest — otherwise a downstream ``+ 1`` would concatenate
        instead of adding.

        Args:
            value: The date/time expression whose year is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(strftime('%Y', <expr>) AS INTEGER))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Filter rows by year::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Year(users.created_at) == 2024,
                )
                # SELECT [users].[id], [users].[created_at] FROM [users]
                # WHERE ((CAST(strftime('%Y', [users].[created_at]) AS INTEGER)) = ?)
                # Parameters: [2024]

            Year-over-year reporting — group in Python after fetching::

                rows = users.get_row([Builtins.Year(users.created_at)])
                from collections import Counter
                by_year = Counter(y for (y,) in rows)
                # {2022: 120, 2023: 340, 2024: 88}

            Extract the year as a SELECT column::

                rows = users.get_row([
                    users.username,
                    Builtins.Year(users.created_at),
                ])
                # SELECT [users].[username],
                #        (CAST(strftime('%Y', [users].[created_at]) AS INTEGER))
                # FROM [users]

            Range filter across years::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Between(Builtins.Year(users.created_at), 2023, 2024),
                )
                # SELECT [users].[id] FROM [users]
                # WHERE (((CAST(strftime('%Y', [users].[created_at]) AS INTEGER)))
                #         BETWEEN ? AND ?)
                # Parameters: [2023, 2024]

            Compare years with arithmetic — stays numeric because
            ``current_datatype`` is ``int``::

                next_year = Builtins.Year(users.created_at) + 1
                rows = users.get_row([users.id, next_year])
                # SELECT [users].[id],
                #        ((CAST(strftime('%Y', [users].[created_at]) AS INTEGER)) + ?)
                # FROM [users]
                # Parameters: [1]

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Year('2024-03-15'),   # -> 2024
                    Builtins.Year('now'),          # -> current year
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f"(CAST(strftime('%Y', {sql}) AS INTEGER))", p, int, c)

    @staticmethod
    def Month(value):
        """Extract the month number (1–12) from a date/time value.

        Generates ``CAST(strftime('%m', <expr>) AS INTEGER)``. SQLite's
        ``strftime('%m', ...)`` returns a zero-padded string like ``'03'``;
        the explicit ``CAST`` converts it to an integer and drops the
        leading zero.

        The result is always an ``INTEGER`` in the range 1 through 12, so
        it compares correctly with numeric literals (``== 3`` rather than
        ``== '03'``).

        Args:
            value: The date/time expression whose month is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(strftime('%m', <expr>) AS INTEGER))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Filter by month — pick a specific month regardless of year::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Month(users.created_at) == 3,
                )
                # SELECT [users].[id], [users].[created_at] FROM [users]
                # WHERE ((CAST(strftime('%m', [users].[created_at]) AS INTEGER)) = ?)
                # Parameters: [3]
                # -> everything created in March, any year

            Seasonal filter — Q1 only::

                q1 = Builtins.Between(Builtins.Month(users.created_at), 1, 3)
                rows = users.get_row(
                    [users.username],
                    where=q1,
                )
                # SELECT [users].[username] FROM [users]
                # WHERE (((CAST(strftime('%m', [users].[created_at]) AS INTEGER)))
                #         BETWEEN ? AND ?)
                # Parameters: [1, 3]

            Monthly histogram — compute in Python after fetching::

                rows = users.get_row([Builtins.Month(users.created_at)])
                from collections import Counter
                by_month = Counter(m for (m,) in rows)
                # {1: 45, 2: 38, 3: 52, ...} — a 12-bucket histogram

            Order by month — chronological within the year::

                rows = users.get_row(
                    [users.username, users.created_at],
                    order_by=Builtins.Month(users.created_at),
                )

            Select with formatted month name — combine with IIF for the
            common "Jan / Feb / ..." display::

                name = Builtins.IIf(
                    Builtins.Month(users.created_at) == 1, 'Jan',
                    Builtins.IIf(
                        Builtins.Month(users.created_at) == 2, 'Feb',
                        Builtins.IIf(
                            Builtins.Month(users.created_at) == 3, 'Mar',
                            'other',
                        ),
                    ),
                )
                rows = users.get_row([users.id, name])

            Filter on a computed month — e.g. only users whose signup
            month matches their birth month (compare two extractions)::

                rows = users.get_row(
                    [users.username],
                    where=Builtins.Month(users.created_at)
                        == Builtins.Month(users.birth_date),
                )

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Month('2024-03-15'),   # -> 3
                    Builtins.Month('now'),          # -> current month 1..12
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f"(CAST(strftime('%m', {sql}) AS INTEGER))", p, int, c)

    @staticmethod
    def Day(value):
        """Extract the day of the month (1–31) from a date/time value.

        Generates ``CAST(strftime('%d', <expr>) AS INTEGER)``. SQLite's
        ``strftime('%d', ...)`` returns a zero-padded string like ``'05'``;
        the explicit ``CAST`` converts it to an integer.

        The result is always an ``INTEGER`` in the range 1 through 31, so
        it compares correctly with numeric literals.

        Args:
            value: The date/time expression whose day of month is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(strftime('%d', <expr>) AS INTEGER))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Find rows created on the first of the month::

                from Ormophine.Sqlite import Driver, Builtins

                db      = Driver('app.db')
                invoices = db.invoices

                rows = invoices.get_row(
                    [invoices.id, invoices.issued_at, invoices.total],
                    where=Builtins.Day(invoices.issued_at) == 1,
                )
                # SELECT [invoices].[id], [invoices].[issued_at],
                #        [invoices].[total]
                # FROM [invoices]
                # WHERE ((CAST(strftime('%d', [invoices].[issued_at]) AS INTEGER)) = ?)
                # Parameters: [1]

            Billing-cycle filter — mid-month settlements, days 13 to 15::

                rows = invoices.get_row(
                    [invoices.id],
                    where=Builtins.Between(
                        Builtins.Day(invoices.issued_at), 13, 15
                    ),
                )

            Detect weekend-adjacent days — days 1 or 2 of any month::

                rows = invoices.get_row(
                    [invoices.id, invoices.issued_at],
                    where=Builtins.Day(invoices.issued_at) <= 2,
                )

            Day-of-month histogram::

                rows = invoices.get_row([Builtins.Day(invoices.issued_at)])
                from collections import Counter
                by_day = Counter(d for (d,) in rows)
                # {1: 45, 2: 12, ..., 31: 3}

            End-of-month filter — days 28 through 31::

                rows = invoices.get_row(
                    [invoices.id],
                    where=Builtins.Between(
                        Builtins.Day(invoices.issued_at), 28, 31
                    ),
                )

            Compare day-of-month across two date columns::

                same_day = (Builtins.Day(invoices.issued_at)
                            == Builtins.Day(invoices.due_at))
                rows = invoices.get_row([invoices.id], where=same_day)

            Applied to a raw literal::

                rows = invoices.get_row([
                    Builtins.Day('2024-03-15'),   # -> 15
                    Builtins.Day('now'),          # -> current day 1..31
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f"(CAST(strftime('%d', {sql}) AS INTEGER))", p, int, c)

    @staticmethod
    def Hour(value):
        """Extract the hour (0–23) from a date/time value.

        Generates ``CAST(strftime('%H', <expr>) AS INTEGER)``. SQLite's
        ``strftime('%H', ...)`` returns a zero-padded 24-hour string like
        ``'09'``; the explicit ``CAST`` converts it to an integer.

        The result is always an ``INTEGER`` in the range 0 through 23, so
        it compares correctly with numeric literals and works well with
        range filters.

        Args:
            value: The date/time expression whose hour is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(strftime('%H', <expr>) AS INTEGER))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Business-hours filter — signups between 9 AM and 5 PM::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                hours = Builtins.Hour(users.created_at)
                rows = users.get_row(
                    [users.id, users.created_at],
                    where=(hours >= 9) & (hours < 17),
                )
                # SELECT [users].[id], [users].[created_at] FROM [users]
                # WHERE (((CAST(strftime('%H', [users].[created_at]) AS INTEGER)) >= ?)
                #        AND ((CAST(strftime('%H', [users].[created_at]) AS INTEGER)) < ?))
                # Parameters: [9, 17]

            Time-of-day bucketing — morning / afternoon / evening / night::

                bucket = Builtins.IIf(
                    Builtins.Hour(users.created_at) < 6, 'night',
                    Builtins.IIf(
                        Builtins.Hour(users.created_at) < 12, 'morning',
                        Builtins.IIf(
                            Builtins.Hour(users.created_at) < 18, 'afternoon',
                            'evening',
                        ),
                    ),
                )
                rows = users.get_row([users.id, bucket])

            Hourly histogram — a 24-bucket count of signups::

                rows = users.get_row([Builtins.Hour(users.created_at)])
                from collections import Counter
                by_hour = Counter(h for (h,) in rows)
                # {0: 3, 1: 1, ..., 9: 45, 10: 52, ..., 23: 8}
                # Great for finding the quietest hour to run maintenance.

            Filter by hour range with a wrap-around — e.g. "off-hours"
            (22:00 through 05:59)::

                h = Builtins.Hour(users.created_at)
                off_hours = (h >= 22) | (h < 6)
                rows = users.get_row([users.id], where=off_hours)

            Order by hour-of-day — clusters activity by time of day
            regardless of date::

                rows = users.get_row(
                    [users.username, users.created_at],
                    order_by=Builtins.Hour(users.created_at),
                )

            Compare hours across two columns — same-hour activity::

                same_hour = (Builtins.Hour(users.created_at)
                             == Builtins.Hour(users.last_login))
                rows = users.get_row([users.id], where=same_hour)

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Hour('2024-03-15 09:30:42'),   # -> 9
                    Builtins.Hour('now'),                    # -> current hour 0..23
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f"(CAST(strftime('%H', {sql}) AS INTEGER))", p, int, c)

    @staticmethod
    def Minute(value):
        """Extract the minute (0–59) from a date/time value.

        Generates ``CAST(strftime('%M', <expr>) AS INTEGER)``. SQLite's
        ``strftime('%M', ...)`` returns a zero-padded string like ``'05'``;
        the explicit ``CAST`` converts it to an integer.

        Note that SQLite uses ``%M`` for minutes and ``%m`` for months —
        the case matters. This helper uses the uppercase ``%M`` for
        minutes; see :meth:`Month` for the lowercase variant.

        The result is always an ``INTEGER`` in the range 0 through 59.

        Args:
            value: The date/time expression whose minute is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(strftime('%M', <expr>) AS INTEGER))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Round down to the top of the hour — subtract the minute count::

                from Ormophine.Sqlite import Driver, Builtins

                db     = Driver('analytics.db')
                events = db.events

                rows = events.get_row([
                    events.id,
                    Builtins.Minute(events.occurred_at),
                ])
                # SELECT [events].[id],
                #        (CAST(strftime('%M', [events].[occurred_at]) AS INTEGER))
                # FROM [events]
                # -> [(1, 42), (2, 0), (3, 15), ...]

            Filter events in the last 5 minutes of an hour::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.Minute(events.occurred_at) >= 55,
                )
                # SELECT [events].[id], [events].[occurred_at] FROM [events]
                # WHERE ((CAST(strftime('%M', [events].[occurred_at]) AS INTEGER)) >= ?)
                # Parameters: [55]

            Bucket events by 15-minute intervals — combine with integer
            division in Python after fetching, or via `Int` arithmetic::

                bucket = Builtins.Int(
                    Builtins.Minute(events.occurred_at) / 15
                ) * 15
                rows = events.get_row([events.id, bucket])
                # -> 0, 15, 30, 45 — a 4-bucket split of each hour

            Detect the top of the hour — a common "cleanup" filter::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Minute(events.occurred_at) == 0,
                )

            Minute histogram across the hour::

                rows = events.get_row([Builtins.Minute(events.occurred_at)])
                from collections import Counter
                by_minute = Counter(m for (m,) in rows)
                # {0: 8, 1: 3, ..., 30: 22, ..., 59: 5}

            Order by minute-of-hour — groups events with the same minute
            regardless of which hour they occurred in::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    order_by=Builtins.Minute(events.occurred_at),
                )

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.Minute('2024-03-15 09:30:42'),   # -> 30
                    Builtins.Minute('now'),                    # -> current minute 0..59
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f"(CAST(strftime('%M', {sql}) AS INTEGER))", p, int, c)

    @staticmethod
    def Second(value):
        """Extract the second (0–59) from a date/time value.

        Generates ``CAST(strftime('%S', <expr>) AS INTEGER)``. SQLite's
        ``strftime('%S', ...)`` returns a zero-padded string like ``'05'``;
        the explicit ``CAST`` converts it to an integer.

        The result is always an ``INTEGER`` in the range 0 through 59.
        SQLite does not represent leap seconds, so the upper bound is
        strictly 59.

        Args:
            value: The date/time expression whose second is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(strftime('%S', <expr>) AS INTEGER))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Extract the second component of a timestamp::

                from Ormophine.Sqlite import Driver, Builtins

                db     = Driver('analytics.db')
                events = db.events

                rows = events.get_row([
                    events.id,
                    events.occurred_at,
                    Builtins.Second(events.occurred_at),
                ])
                # SELECT [events].[id], [events].[occurred_at],
                #        (CAST(strftime('%S', [events].[occurred_at]) AS INTEGER))
                # FROM [events]
                # -> [(1, '2024-03-15 09:30:42', 42), ...]

            Find events that landed on a round minute — second == 0::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.Second(events.occurred_at) == 0,
                )
                # SELECT [events].[id], [events].[occurred_at] FROM [events]
                # WHERE ((CAST(strftime('%S', [events].[occurred_at]) AS INTEGER)) = ?)
                # Parameters: [0]

            Detect rapid-fire activity — events within the first 5 seconds
            of each minute::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Second(events.occurred_at) < 5,
                )

            Reconstruct a full HH:MM:SS display from components — often
            combined with Hour and Minute::

                hh = Builtins.Hour(events.occurred_at)
                mm = Builtins.Minute(events.occurred_at)
                ss = Builtins.Second(events.occurred_at)
                display = Builtins.Format('%02d:%02d:%02d', hh, mm, ss)
                rows = events.get_row([events.id, display])
                # -> [('09:30:42',), ('09:30:43',), ...]

            Second-of-minute histogram — useful for spotting scheduling
            jitter::

                rows = events.get_row([Builtins.Second(events.occurred_at)])
                from collections import Counter
                by_second = Counter(s for (s,) in rows)
                # {0: 45, 1: 2, 2: 1, ..., 42: 3, ...}

            Compare seconds across two columns — same-second events::

                same_second = (
                    Builtins.Second(events.started_at)
                    == Builtins.Second(events.finished_at)
                )
                rows = events.get_row([events.id], where=same_second)

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.Second('2024-03-15 09:30:42'),   # -> 42
                    Builtins.Second('now'),                    # -> current second 0..59
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f"(CAST(strftime('%S', {sql}) AS INTEGER))", p, int, c)

    @staticmethod
    def DayOfWeek(value):
        """Extract the day-of-week number using SQLite's ``%w`` convention.

        Generates ``CAST(strftime('%w', <expr>) AS INTEGER)``. SQLite's
        ``strftime('%w', ...)`` returns a number in the range 0 through 6
        using the following convention:

        =====  ==========
        Value  Day
        =====  ==========
        0      Sunday
        1      Monday
        2      Tuesday
        3      Wednesday
        4      Thursday
        5      Friday
        6      Saturday
        =====  ==========

        .. warning::
            This is the **SQLite / POSIX** convention, not Python's.
            Python's ``date.weekday()`` returns 0 for Monday, and
            ``date.isoweekday()`` returns 1 for Monday. If you want Python
            semantics, use :meth:`Weekday` or :meth:`IsoWeekday` instead.

        The result is always an ``INTEGER`` in the range 0 through 6.

        Args:
            value: The date/time expression whose weekday is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(strftime('%w', <expr>) AS INTEGER))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Filter for Sundays — in SQLite's convention, Sunday is 0::

                from Ormophine.Sqlite import Driver, Builtins

                db     = Driver('analytics.db')
                events = db.events

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.DayOfWeek(events.occurred_at) == 0,
                )
                # SELECT [events].[id], [events].[occurred_at] FROM [events]
                # WHERE ((CAST(strftime('%w', [events].[occurred_at]) AS INTEGER)) = ?)
                # Parameters: [0]

            Weekend filter — Saturday (6) or Sunday (0)::

                dow = Builtins.DayOfWeek(events.occurred_at)
                rows = events.get_row(
                    [events.id],
                    where=(dow == 0) | (dow == 6),
                )
                # -> rows on Saturday or Sunday

            Weekday-only filter — Monday through Friday (1..5)::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Between(
                        Builtins.DayOfWeek(events.occurred_at), 1, 5
                    ),
                )

            Day-of-week histogram — how activity spreads across the week::

                rows = events.get_row([Builtins.DayOfWeek(events.occurred_at)])
                from collections import Counter
                by_dow = Counter(w for (w,) in rows)
                # {0: 15, 1: 42, 2: 38, ..., 6: 22}

            Order by day-of-week — groups rows by weekday, Sunday first::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    order_by=Builtins.DayOfWeek(events.occurred_at),
                )

            Build a readable day name via IIF::

                name = Builtins.IIf(
                    Builtins.DayOfWeek(events.occurred_at) == 0, 'Sun',
                    Builtins.IIf(
                        Builtins.DayOfWeek(events.occurred_at) == 1, 'Mon',
                        Builtins.IIf(
                            Builtins.DayOfWeek(events.occurred_at) == 2, 'Tue',
                            Builtins.IIf(
                                Builtins.DayOfWeek(events.occurred_at) == 3, 'Wed',
                                Builtins.IIf(
                                    Builtins.DayOfWeek(events.occurred_at) == 4, 'Thu',
                                    Builtins.IIf(
                                        Builtins.DayOfWeek(events.occurred_at) == 5, 'Fri',
                                        'Sat',
                                    ),
                                ),
                            ),
                        ),
                    ),
                )
                rows = events.get_row([events.id, name])

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.DayOfWeek('2024-03-15'),   # -> 5 (Friday)
                    Builtins.DayOfWeek('now'),          # -> current day-of-week
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f"(CAST(strftime('%w', {sql}) AS INTEGER))", p, int, c)

    @staticmethod
    def DayOfYear(value):
        """Extract the day of the year (1–366) from a date/time value.

        Generates ``CAST(strftime('%j', <expr>) AS INTEGER)``. SQLite's
        ``strftime('%j', ...)`` returns a zero-padded three-digit string
        like ``'075'``; the explicit ``CAST`` converts it to an integer.

        The result is always an ``INTEGER`` in the range 1 through 366.
        Leap years produce 366; non-leap years produce at most 365. SQLite
        determines leap-ness from the actual input date, so this helper
        is completely accurate across century boundaries.

        Args:
            value: The date/time expression whose ordinal day is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(strftime('%j', <expr>) AS INTEGER))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Ordinal day for every row — the day of the year, 1-based::

                from Ormophine.Sqlite import Driver, Builtins

                db     = Driver('analytics.db')
                events = db.events

                rows = events.get_row([
                    events.id,
                    events.occurred_at,
                    Builtins.DayOfYear(events.occurred_at),
                ])
                # SELECT [events].[id], [events].[occurred_at],
                #        (CAST(strftime('%j', [events].[occurred_at]) AS INTEGER))
                # FROM [events]
                # -> [(1, '2024-03-15', 75), ...]

            Day-of-year histogram — a true 365-bucket distribution of
            activity::

                rows = events.get_row([Builtins.DayOfYear(events.occurred_at)])
                from collections import Counter
                by_doy = Counter(j for (j,) in rows)
                # {1: 12, 2: 8, ..., 75: 22, ..., 366: 4}

            Same-weekday-anywhere comparison — day-of-year modulo 7 groups
            rows into the same weekday::

                same_weekday = Builtins.DayOfYear(events.occurred_at) % 7
                rows = events.get_row([events.id, same_weekday])

            Filter for the first quarter (days 1 through 91)::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.Between(
                        Builtins.DayOfYear(events.occurred_at), 1, 91
                    ),
                )

            Year-relative comparison — find all events on the same calendar
            day across different years::

                rows = events.get_row(
                    [events.occurred_at],
                    where=Builtins.DayOfYear(events.occurred_at) == 75,
                )
                # -> every March 15 regardless of year

            Sort by position within the year — combines nicely with
            :meth:`Year`::

                rows = events.get_row(
                    [events.occurred_at],
                    order_by=Builtins.DayOfYear(events.occurred_at),
                )

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.DayOfYear('2024-03-15'),   # -> 75
                    Builtins.DayOfYear('2024-12-31'),   # -> 366 (2024 is a leap year)
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f"(CAST(strftime('%j', {sql}) AS INTEGER))", p, int, c)

    @staticmethod
    def WeekOfYear(value):
        """Extract the week of the year (0–53) from a date/time value.

        Generates ``CAST(strftime('%W', <expr>) AS INTEGER)``. SQLite's
        ``strftime('%W', ...)`` returns a zero-padded two-digit string
        like ``'11'``; the explicit ``CAST`` converts it to an integer.

        SQLite's ``%W`` convention has two important properties:

        - **Weeks start on Monday**, unlike the US-style ``%U`` which
          starts on Sunday.
        - **The first Monday starts week 1.** Days before the first
          Monday of the year belong to week 0. Therefore the range is
          0 through 53, not 1 through 52.

        This matches ISO week numbering in spirit but not exactly. For
        strict ISO 8601 (Monday weeks, week 1 contains the first Thursday),
        SQLite offers no built-in specifier — you must compute it yourself
        or use a custom SQL function.

        Args:
            value: The date/time expression whose week-of-year is
                extracted. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(strftime('%W', <expr>) AS INTEGER))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Week number for every row::

                from Ormophine.Sqlite import Driver, Builtins

                db     = Driver('analytics.db')
                events = db.events

                rows = events.get_row([
                    events.id,
                    events.occurred_at,
                    Builtins.WeekOfYear(events.occurred_at),
                ])
                # SELECT [events].[id], [events].[occurred_at],
                #        (CAST(strftime('%W', [events].[occurred_at]) AS INTEGER))
                # FROM [events]
                # -> [(1, '2024-03-15', 11), ...]

            Weekly histogram — count events per week::

                rows = events.get_row([Builtins.WeekOfYear(events.occurred_at)])
                from collections import Counter
                by_week = Counter(w for (w,) in rows)
                # {0: 3, 1: 45, 2: 52, ..., 11: 22, ..., 53: 1}

            Filter to a specific week — e.g. week 11 of the year::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.WeekOfYear(events.occurred_at) == 11,
                )
                # SELECT [events].[id], [events].[occurred_at] FROM [events]
                # WHERE ((CAST(strftime('%W', [events].[occurred_at]) AS INTEGER)) = ?)
                # Parameters: [11]

            Filter to the first quarter — weeks 0 through 12::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Between(
                        Builtins.WeekOfYear(events.occurred_at), 0, 12
                    ),
                )

            Combine with Year for a "year-week" key — useful for
            reporting::

                key = Builtins.Format(
                    '%d-W%02d',
                    Builtins.Year(events.occurred_at),
                    Builtins.WeekOfYear(events.occurred_at),
                )
                rows = events.get_row([events.id, key])
                # -> [('2024-W11',), ('2024-W11',), ('2024-W12',), ...]

            Order by week — chronological grouping within the year::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    order_by=Builtins.WeekOfYear(events.occurred_at),
                )

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.WeekOfYear('2024-01-01'),   # -> 0 (before first Monday)
                    Builtins.WeekOfYear('2024-01-08'),   # -> 1 (first Monday week)
                    Builtins.WeekOfYear('2024-03-15'),   # -> 11
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f"(CAST(strftime('%W', {sql}) AS INTEGER))", p, int, c)

    @staticmethod
    def Weekday(value):
        """Extract the Python-style weekday (0 = Monday, 6 = Sunday).

        Generates a two-step expression to convert SQLite's Sunday-based
        ``%w`` convention into Python's Monday-based weekday convention:

        .. code-block:: sql

            (CAST(strftime('%w', <expr>) AS INTEGER) + 6) % 7

        This matches Python's ``datetime.date.weekday()`` method exactly:

        =====  ==========
        Value  Day
        =====  ==========
        0      Monday
        1      Tuesday
        2      Wednesday
        3      Thursday
        4      Friday
        5      Saturday
        6      Sunday
        =====  ==========

        Use this method when you want to write conditions that read the
        same as Python code. Use :meth:`DayOfWeek` when you need SQLite's
        native convention, and :meth:`IsoWeekday` when you need the ISO
        8601 convention (1 = Monday, 7 = Sunday).

        Args:
            value: The date/time expression whose Python-style weekday is
                extracted. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``((CAST(strftime('%w', <expr>) AS INTEGER) + 6) % 7)`` and
            whose ``current_datatype`` is always ``int``.

        Example:
            Filter for Mondays — ``== 0`` matches Python's convention::

                from Ormophine.Sqlite import Driver, Builtins

                db     = Driver('analytics.db')
                events = db.events

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.Weekday(events.occurred_at) == 0,
                )
                # SELECT [events].[id], [events].[occurred_at] FROM [events]
                # WHERE (((CAST(strftime('%w', [events].[occurred_at]) AS INTEGER) + 6) % 7) = ?)
                # Parameters: [0]

            Weekend filter — Saturday (5) or Sunday (6)::

                dow = Builtins.Weekday(events.occurred_at)
                rows = events.get_row(
                    [events.id],
                    where=(dow == 5) | (dow == 6),
                )
                # -> rows on Saturday or Sunday

            Weekday-only filter — Monday through Friday (0..4)::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Between(
                        Builtins.Weekday(events.occurred_at), 0, 4
                    ),
                )

            Python-style weekday histogram::

                rows = events.get_row([Builtins.Weekday(events.occurred_at)])
                from collections import Counter
                by_dow = Counter(w for (w,) in rows)
                # {0: 42, 1: 38, 2: 40, 3: 45, 4: 44, 5: 15, 6: 22}
                # Monday through Sunday, matching Python's weekday() order

            Same-weekday filter — events that happened on the same weekday
            as today::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Weekday(events.occurred_at)
                        == Builtins.Weekday('now'),
                )

            Build a readable day name via IIF — the list is now in Python
            order::

                name = Builtins.IIf(
                    Builtins.Weekday(events.occurred_at) == 0, 'Mon',
                    Builtins.IIf(
                        Builtins.Weekday(events.occurred_at) == 1, 'Tue',
                        Builtins.IIf(
                            Builtins.Weekday(events.occurred_at) == 2, 'Wed',
                            Builtins.IIf(
                                Builtins.Weekday(events.occurred_at) == 3, 'Thu',
                                Builtins.IIf(
                                    Builtins.Weekday(events.occurred_at) == 4, 'Fri',
                                    Builtins.IIf(
                                        Builtins.Weekday(events.occurred_at) == 5, 'Sat',
                                        'Sun',
                                    ),
                                ),
                            ),
                        ),
                    ),
                )
                rows = events.get_row([events.id, name])

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.Weekday('2024-03-15'),   # -> 4 (Friday)
                    Builtins.Weekday('now'),          # -> current weekday 0..6
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f"((CAST(strftime('%w', {sql}) AS INTEGER) + 6) % 7)",
            p, int, c)

    @staticmethod
    def IsoWeekday(value):
        """Extract the ISO 8601 weekday (1 = Monday, 7 = Sunday).

        Generates a two-step expression to convert SQLite's Sunday-based
        ``%w`` convention into the ISO 8601 convention:

        .. code-block:: sql

            ((CAST(strftime('%w', <expr>) AS INTEGER) + 6) % 7) + 1

        This matches Python's ``datetime.date.isoweekday()`` method and
        the ISO 8601 standard:

        =====  ==========
        Value  Day
        =====  ==========
        1      Monday
        2      Tuesday
        3      Wednesday
        4      Thursday
        5      Friday
        6      Saturday
        7      Sunday
        =====  ==========

        Use this method when you want an unambiguous 1-based weekday
        number. ISO 8601 uses this convention throughout its date and
        duration standards, so it is the "neutral" choice when talking
        to systems that have no Python or SQLite heritage.

        Args:
            value: The date/time expression whose ISO weekday is
                extracted. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(((CAST(strftime('%w', <expr>) AS INTEGER) + 6) % 7) + 1)``
            and whose ``current_datatype`` is always ``int``.

        Example:
            Filter for Mondays — ``== 1`` in ISO convention::

                from Ormophine.Sqlite import Driver, Builtins

                db     = Driver('analytics.db')
                events = db.events

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.IsoWeekday(events.occurred_at) == 1,
                )
                # SELECT [events].[id], [events].[occurred_at] FROM [events]
                # WHERE ((((CAST(strftime('%w', [events].[occurred_at]) AS INTEGER) + 6) % 7) + 1) = ?)
                # Parameters: [1]

            Weekend filter — ISO 6 (Saturday) or 7 (Sunday)::

                dow = Builtins.IsoWeekday(events.occurred_at)
                rows = events.get_row(
                    [events.id],
                    where=(dow == 6) | (dow == 7),
                )

            Weekday-only filter — Monday through Friday (1..5)::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Between(
                        Builtins.IsoWeekday(events.occurred_at), 1, 5
                    ),
                )

            ISO weekday histogram — 1 through 7 in ISO order::

                rows = events.get_row([Builtins.IsoWeekday(events.occurred_at)])
                from collections import Counter
                by_dow = Counter(w for (w,) in rows)
                # {1: 42, 2: 38, 3: 40, 4: 45, 5: 44, 6: 15, 7: 22}
                # Monday through Sunday, 1-based

            ISO-weekday range filter for business days, expressed with
            BETWEEN and 1..5::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.Between(
                        Builtins.IsoWeekday(events.occurred_at), 1, 5
                    ),
                )

            Build a readable day name via IIF — ISO order::

                name = Builtins.IIf(
                    Builtins.IsoWeekday(events.occurred_at) == 1, 'Mon',
                    Builtins.IIf(
                        Builtins.IsoWeekday(events.occurred_at) == 2, 'Tue',
                        Builtins.IIf(
                            Builtins.IsoWeekday(events.occurred_at) == 3, 'Wed',
                            Builtins.IIf(
                                Builtins.IsoWeekday(events.occurred_at) == 4, 'Thu',
                                Builtins.IIf(
                                    Builtins.IsoWeekday(events.occurred_at) == 5, 'Fri',
                                    Builtins.IIf(
                                        Builtins.IsoWeekday(events.occurred_at) == 6, 'Sat',
                                        'Sun',
                                    ),
                                ),
                            ),
                        ),
                    ),
                )
                rows = events.get_row([events.id, name])

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.IsoWeekday('2024-03-15'),   # -> 5 (Friday)
                    Builtins.IsoWeekday('now'),          # -> current weekday 1..7
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f"(((CAST(strftime('%w', {sql}) AS INTEGER) + 6) % 7) + 1)",
            p, int, c)
    
    @staticmethod
    def DateDiffDays(a, b):
        """Compute the number of whole days between two date/time values.

        Generates a ``CAST(julianday(<a>) - julianday(<b>) AS INTEGER)``
        expression. The result is the signed day count from ``b`` to ``a``:

        - A positive result means ``a`` occurs *after* ``b``.
        - A negative result means ``a`` occurs *before* ``b``.
        - A zero result means the two dates fall on the same day.

        Because ``julianday`` returns a fractional value (the fractional
        part encodes the time of day), the subtraction produces a real
        number and the ``CAST(... AS INTEGER)`` truncates toward zero.
        This means "one and a half days" becomes "1", not "2" — the count
        is a *whole* day count, not a rounded one. For a fractional day
        count, use :meth:`JulianDay` directly and subtract without the cast.

        This is the natural SQL analogue of Python's
        ``(date_a - date_b).days`` on two ``date`` objects.

        Args:
            a: The later date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder. The special string ``'now'`` produces the
                  current moment.

            b: The earlier date/time expression. Same accepted types as
                ``a``.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST(julianday(<a>) - julianday(<b>) AS INTEGER))`` and whose
            ``current_datatype`` is always ``int``. Parameters are
            concatenated left-to-right: first ``a``'s parameters, then
            ``b``'s.

        Example:
            Account age in days for every user::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                age_days = Builtins.DateDiffDays(Builtins.Now(), users.created_at)
                rows = users.get_row([
                    users.username,
                    age_days,
                ])
                # SELECT [users].[username],
                #        (CAST(julianday((datetime(?))) - julianday([users].[created_at]) AS INTEGER))
                # FROM [users]
                # Parameters: ['now']
                # -> [('Alice', 74), ('Bob', 12), ...]

            Filter users who signed up in the last week::

                rows = users.get_row(
                    [users.username, users.created_at],
                    where=Builtins.DateDiffDays(Builtins.Now(), users.created_at) < 7,
                )
                # SELECT [users].[username], [users].[created_at] FROM [users]
                # WHERE ((CAST(julianday((datetime(?))) - julianday([users].[created_at]) AS INTEGER)) < ?)
                # Parameters: ['now', 7]

            Filter users who signed up more than a year ago::

                rows = users.get_row(
                    [users.username],
                    where=Builtins.DateDiffDays(Builtins.Now(), users.created_at) > 365,
                )

            Session duration in days — compare two columns::

                duration = Builtins.DateDiffDays(
                    users.session_ended,
                    users.session_started,
                )
                rows = users.get_row([users.id, duration])
                # -> [(1, 2), (2, 0), (3, 5), ...]

            Order users by account age — most recent first::

                rows = users.get_row(
                    [users.username, users.created_at],
                    order_by=Builtins.DateDiffDays(Builtins.Now(), users.created_at),
                )
                # Smallest day-count (most recent) appears first.

            Detect users who signed up today::

                same_day = Builtins.DateDiffDays(Builtins.Now(), users.created_at) == 0
                rows = users.get_row([users.username], where=same_day)

            Sign convention — order of arguments matters::

                # Positive: a is later than b
                pos = Builtins.DateDiffDays('2024-03-15', '2024-03-01')
                # -> 14

                # Negative: a is earlier than b
                neg = Builtins.DateDiffDays('2024-03-01', '2024-03-15')
                # -> -14

            Compare with :meth:`JulianDay` for a fractional day count::

                # Truncated:   14  (whole days)
                whole = Builtins.DateDiffDays(
                    '2024-03-15 12:00:00', '2024-03-01 06:00:00'
                )
                # Fractional:  14.25  (days with hours preserved)
                fraction = (
                    Builtins.JulianDay('2024-03-15 12:00:00')
                    - Builtins.JulianDay('2024-03-01 06:00:00')
                )
        """
        s1, p1, _, c = Builtins._normalize(a)
        s2, p2, _, _ = Builtins._normalize(b)
        return Builtins._make(
            f"(CAST(julianday({s1}) - julianday({s2}) AS INTEGER))",
            p1 + p2, int, c)

    @staticmethod
    def DateDiffSeconds(a, b):
        """Compute the number of whole seconds between two date/time values.

        Generates a
        ``CAST((julianday(<a>) - julianday(<b>)) * 86400.0 AS INTEGER)``
        expression. The result is the signed second count from ``b`` to
        ``a``:

        - A positive result means ``a`` occurs *after* ``b``.
        - A negative result means ``a`` occurs *before* ``b``.
        - A zero result means the two moments are within the same second.

        Because Julian day numbers are counted in days and there are
        exactly 86 400 seconds in a day, multiplying the day-difference by
        ``86400.0`` gives the second count. The ``CAST(... AS INTEGER)``
        truncates toward zero.

        This is the natural SQL analogue of Python's
        ``(datetime_a - datetime_b).total_seconds()``.

        Args:
            a: The later date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder. The special string ``'now'`` produces the
                  current moment.

            b: The earlier date/time expression. Same accepted types as
                ``a``.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(CAST((julianday(<a>) - julianday(<b>)) * 86400.0 AS INTEGER))``
            and whose ``current_datatype`` is always ``int``. Parameters
            are concatenated left-to-right: first ``a``'s parameters, then
            ``b``'s.

        Example:
            Seconds since last login for every user::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                secs = Builtins.DateDiffSeconds(Builtins.Now(), users.last_login)
                rows = users.get_row([
                    users.username,
                    secs,
                ])
                # SELECT [users].[username],
                #        (CAST((julianday((datetime(?))) - julianday([users].[last_login])) * 86400.0 AS INTEGER))
                # FROM [users]
                # Parameters: ['now']
                # -> [('Alice', 4809), ('Bob', 172800), ...]

            Filter to sessions active in the last hour::

                rows = users.get_row(
                    [users.username, users.last_seen],
                    where=Builtins.DateDiffSeconds(Builtins.Now(), users.last_seen) < 3600,
                )
                # SELECT [users].[username], [users].[last_seen] FROM [users]
                # WHERE ((CAST((julianday((datetime(?))) - julianday([users].[last_seen])) * 86400.0 AS INTEGER)) < ?)
                # Parameters: ['now', 3600]

            Convert to minutes in Python after fetching::

                rows = users.get_row([
                    users.username,
                    Builtins.DateDiffSeconds(Builtins.Now(), users.last_seen),
                ])
                minutes = [(u, s // 60) for u, s in rows]

            Session duration in seconds — compare two columns::

                duration = Builtins.DateDiffSeconds(
                    users.session_ended,
                    users.session_started,
                )
                rows = users.get_row([users.id, duration])
                # -> [(1, 5025), (2, 12), (3, 432000), ...]

            Order by recency — most recently active first::

                rows = users.get_row(
                    [users.username],
                    order_by=Builtins.DateDiffSeconds(Builtins.Now(), users.last_seen),
                )

            Detect users active within the same second::

                same_second = Builtins.DateDiffSeconds(
                    Builtins.Now(), users.last_seen
                ) == 0
                rows = users.get_row([users.username], where=same_second)

            Rate limiting pattern — count events in a rolling window::

                # Combine with SUM(Builtins.IIf(...)) to count events
                # inside a 60-second window:
                events = db.events
                recent_count = Builtins.Sum(
                    Builtins.IIf(
                        Builtins.DateDiffSeconds(
                            Builtins.Now(), events.occurred_at
                        ) < 60,
                        1,
                        0,
                    )
                )
                rows = events.get_row([recent_count])
                # -> [(7,)] if 7 events happened in the last minute

            Sign convention — order of arguments matters::

                # Positive: a is later than b
                pos = Builtins.DateDiffSeconds('2024-03-15 12:00:00', '2024-03-15 11:00:00')
                # -> 3600

                # Negative: a is earlier than b
                neg = Builtins.DateDiffSeconds('2024-03-15 11:00:00', '2024-03-15 12:00:00')
                # -> -3600
        """
        s1, p1, _, c = Builtins._normalize(a)
        s2, p2, _, _ = Builtins._normalize(b)
        return Builtins._make(
            f"(CAST((julianday({s1}) - julianday({s2})) * 86400.0 AS INTEGER))",
            p1 + p2, int, c)

    @staticmethod
    def Now(_=None):
        """Return the current moment as a ``datetime()`` string (UTC).

        Generates a ``datetime('now')`` expression. The result is a TEXT
        string in ISO 8601 format: ``'YYYY-MM-DD HH:MM:SS'``, in UTC
        (Coordinated Universal Time). No parameters are consumed.

        The optional positional argument ``_`` exists only to make the
        signature uniform with the other date/time helpers and to allow
        the callable to be passed to APIs that expect a one-argument
        function. It is ignored.

        For the corresponding date-only form, see :meth:`Today`. For an
        integer Unix timestamp, see :meth:`UnixNow`. For a timezone-aware
        value in the server's local time, chain through :meth:`DateTimeAdd`
        with the ``'localtime'`` modifier::

            Builtins.DateTimeAdd('now', 'localtime')

        Args:
            _: Ignored. Any value passed is discarded; the SQL emitted is
                always ``datetime('now')``.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(datetime('now'))`` and whose ``current_datatype`` is
            ``str``. The parameter list is always empty.

        Example:
            The current timestamp as a SELECT column::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([Builtins.Now()])
                # SELECT (datetime('now')) FROM [users]
                # -> [('2024-03-15 14:30:42',)] — same value for every row
                #    in the result set, because SQLite evaluates 'now' once
                #    per query, not per row.

            Compute account age in days::

                age = Builtins.DateDiffDays(Builtins.Now(), users.created_at)
                rows = users.get_row([users.username, age])

            Compute account age in a human-readable format::

                age_str = Builtins.Timediff(Builtins.Now(), users.created_at)
                rows = users.get_row([users.username, age_str])
                # -> [('Alice', '+0000-00-02 05:29:18.000'), ...]

            Filter rows updated in the last hour::

                rows = users.get_row(
                    [users.username, users.updated_at],
                    where=Builtins.DateDiffSeconds(
                        Builtins.Now(), users.updated_at
                    ) < 3600,
                )

            Store the current timestamp during an UPDATE::

                users.update(
                    update={users.last_seen: Builtins.Now()},
                    where=users.id == 42,
                )
                # UPDATE [users] SET [last_seen]=(datetime('now'))
                # WHERE ([users].[id] = ?);
                # Parameters: [42]

            Insert with an explicit timestamp — the ORM binds the value
            as-is; passing a ColumnsOperation on the right-hand side of
            an insert is not supported by ``Table.insert``, so use the
            raw form for inserts::

                # For a direct INSERT, the current time can be written
                # either via a DEFAULT clause on the schema or via
                # Table.custom_execute:
                users.custom_execute(
                    "INSERT INTO [users] ([username], [created_at]) "
                    "VALUES (?, datetime('now'))",
                    ['alice'],
                )

            Compare two Now() calls to see that both evaluate to the same
            moment in a single query — useful for validating cache keys::

                rows = users.get_row([
                    Builtins.Now(),
                    Builtins.Now(),
                ])
                # -> [('2024-03-15 14:30:42', '2024-03-15 14:30:42')]
                # Both columns are identical.

            Local-time variant — pass ``'localtime'`` as a modifier via
            ``DateTimeAdd``::

                local_now = Builtins.DateTimeAdd('now', 'localtime')
                rows = users.get_row([local_now])
                # -> [('2024-03-15 15:30:42',)] if the server is UTC+1
        """
        return Builtins._make("(datetime('now'))", [], str, Builtins._NullCol)

    @staticmethod
    def Today(_=None):
        """Return the current date as a ``date()`` string (UTC).

        Generates a ``date('now')`` expression. The result is a TEXT
        string in ISO 8601 format: ``'YYYY-MM-DD'``, in UTC. No parameters
        are consumed. This is the date-only counterpart of :meth:`Now`.

        The optional positional argument ``_`` exists only to make the
        signature uniform with the other date/time helpers; it is ignored.

        For the corresponding UTC datetime, see :meth:`Now`. For an
        integer Unix timestamp, see :meth:`UnixNow`.

        Args:
            _: Ignored. Any value passed is discarded; the SQL emitted is
                always ``date('now')``.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(date('now'))`` and whose ``current_datatype`` is ``str``.
            The parameter list is always empty.

        Example:
            The current date as a SELECT column::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([Builtins.Today()])
                # SELECT (date('now')) FROM [users]
                # -> [('2024-03-15',)]

            Find users who signed up today::

                rows = users.get_row(
                    [users.username, users.created_at],
                    where=Builtins.Date(users.created_at) == Builtins.Today(),
                )
                # SELECT [users].[username], [users].[created_at] FROM [users]
                # WHERE ((date([users].[created_at])) = (date(?)))
                # Parameters: ['now']

            Same-day boolean flag via IIF::

                is_today = Builtins.IIf(
                    Builtins.Date(users.created_at) == Builtins.Today(),
                    'new',
                    'old',
                )
                rows = users.get_row([users.username, is_today])

            Store today's date in an UPDATE::

                users.update(
                    update={users.last_active_date: Builtins.Today()},
                    where=users.id == 42,
                )
                # UPDATE [users] SET [last_active_date]=(date('now'))
                # WHERE ([users].[id] = ?);
                # Parameters: [42]

            Yesterday's date — chain with a modifier::

                yesterday = Builtins.DateAdd('now', '-1 day')
                rows = users.get_row([yesterday])
                # -> [('2024-03-14',)]

            First day of the current month — useful for month-to-date
            reporting::

                month_start = Builtins.DateAdd('now', 'start of month')
                rows = users.get_row([month_start])
                # -> [('2024-03-01',)]

            Count users who signed up today::

                today_count = Builtins.Sum(
                    Builtins.IIf(
                        Builtins.Date(users.created_at) == Builtins.Today(),
                        1,
                        0,
                    )
                )
                rows = users.get_row([today_count])
                # -> [(8,)] if 8 users signed up today

            Compare against a fixed date literal::

                rows = users.get_row(
                    [users.username],
                    where=Builtins.Today() > '2024-01-01',
                )
                # SELECT [users].[username] FROM [users]
                # WHERE ((date(?)) > ?)
                # Parameters: ['now', '2024-01-01']
        """
        return Builtins._make("(date('now'))", [], str, Builtins._NullCol)

    @staticmethod
    def UnixNow(_=None):
        """Return the current moment as an integer Unix timestamp (UTC).

        Generates a ``unixepoch('now')`` expression. The result is an
        INTEGER equal to the number of whole seconds since the Unix epoch
        (midnight UTC on 1 January 1970). No parameters are consumed.

        This is the numeric counterpart of :meth:`Now` and matches the
        return value of Python's ``time.time()`` (rounded down to an
        integer). Because the result is a plain integer, it is the best
        choice for cache keys, request IDs, expiry timestamps, and any
        arithmetic that needs sub-day precision without floating-point
        round-off.

        The optional positional argument ``_`` exists only to make the
        signature uniform with the other date/time helpers; it is ignored.

        .. note::
            ``unixepoch()`` requires SQLite >= 3.38. On older libraries,
            the portable equivalent is
            ``Builtins.Int((Builtins.JulianDay('now') - 2440587.5) * 86400)``,
            or you can use :meth:`JulianDay` directly and multiply.

        Args:
            _: Ignored. Any value passed is discarded; the SQL emitted is
                always ``unixepoch('now')``.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(unixepoch('now'))`` and whose ``current_datatype`` is
            ``int``. The parameter list is always empty.

        Example:
            Current Unix timestamp as a SELECT column::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([Builtins.UnixNow()])
                # SELECT (unixepoch('now')) FROM [users]
                # -> [(1710513042,)]

            Compute account age in seconds without any date parsing::

                age_secs = Builtins.UnixNow() - Builtins.UnixEpoch(users.created_at)
                rows = users.get_row([users.username, age_secs])
                # -> [('Alice', 6394842), ('Bob', 1036800), ...]

            Filter users who signed up in the last 24 hours::

                rows = users.get_row(
                    [users.username, users.created_at],
                    where=Builtins.UnixNow()
                        - Builtins.UnixEpoch(users.created_at) < 86400,
                )
                # SELECT [users].[username], [users].[created_at] FROM [users]
                # WHERE (((unixepoch(?)) - (unixepoch([users].[created_at]))) < ?)
                # Parameters: ['now', 86400]

            Generate a per-request cache key — combine with a user id::

                cache_key = Builtins.Format(
                    'user:%d:%d',
                    users.id,
                    Builtins.UnixNow(),
                )
                rows = users.get_row([cache_key])
                # -> [('user:42:1710513042',), ...]

            Store the current epoch in an UPDATE — useful for
            portability-friendly integer columns::

                users.update(
                    update={users.last_login_epoch: Builtins.UnixNow()},
                    where=users.id == 42,
                )
                # UPDATE [users] SET [last_login_epoch]=(unixepoch('now'))
                # WHERE ([users].[id] = ?);
                # Parameters: [42]

            Compute a future expiry — a session token valid for 1 hour::

                expires_at = Builtins.UnixNow() + 3600
                rows = users.get_row([users.id, expires_at])
                # -> [(1, 1710516642), ...]

            Set a session expiry during an UPDATE and later check it with
            a plain integer comparison::

                users.update(
                    update={users.token_expires: Builtins.UnixNow() + 3600},
                    where=users.id == 42,
                )

                # Later, filter expired sessions using a Python-side
                # timestamp — the comparison is a plain integer one:
                import time
                now_epoch = int(time.time())
                expired = users.get_row(
                    [users.id],
                    where=users.token_expires < now_epoch,
                )
        """
        return Builtins._make("(CAST((julianday('now') - 2440587.5) * 86400 AS INTEGER))",[], int, Builtins._NullCol,)

    @staticmethod
    def DateAdd(value, *modifiers):
        """Apply one or more date modifiers to a value and return a date string.

        Generates a ``date(<expr>, <m1>, <m2>, ...)`` expression. SQLite's
        date functions accept any number of modifier strings after the
        value; each modifier transforms the running result. This helper
        forwards every modifier as a bound parameter, so user-supplied
        modifier strings are safe from SQL injection.

        SQLite supports the following modifiers:

        - ``'+N days'`` / ``'-N days'`` — shift by days
        - ``'+N months'`` / ``'-N months'`` — shift by months
        - ``'+N years'`` / ``'-N years'`` — shift by years
        - ``'+N hours'`` / ``'-N hours'`` — shift by hours
        - ``'+N minutes'`` / ``'-N minutes'`` — shift by minutes
        - ``'+N seconds'`` / ``'-N seconds'`` — shift by seconds
        - ``'start of month'`` — first day of the current month
        - ``'start of year'`` — 1 January of the current year
        - ``'start of day'`` — midnight of the current day
        - ``'weekday N'`` — next day-of-week N (0 = Sunday, 6 = Saturday)
        - ``'unixepoch'`` — treat the value as a Unix timestamp
        - ``'julianday'`` — treat the value as a Julian day number
        - ``'auto'`` — detect the input format automatically
        - ``'localtime'`` — convert to the server's local time
        - ``'utc'`` — convert to UTC

        When called with no modifiers, this helper degenerates to
        ``date(<expr>)`` — the same behaviour as :meth:`Date`. The
        separate name exists for the modifier-aware form, but both are
        valid call patterns.

        The result is always a TEXT string in ``'YYYY-MM-DD'`` format.
        For a datetime result, see :meth:`DateTimeAdd`; for a time-only
        result, see :meth:`TimeAdd`.

        Args:
            value: The starting date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder. The special string ``'now'`` produces the
                  current moment.

            *modifiers: Zero or more modifier strings. Each is bound as a
                ``?`` parameter, so dynamic modifier construction (e.g.
                ``f'+{n} days'``) is safe. Modifiers are applied in the
                order given, so ``('start of month', '+1 month')`` means
                "first day of next month" and ``('+1 month', 'start of month')``
                means "first day of the month that follows the original
                date plus one month" — which is usually the same result,
                but not always for edge cases like the 31st of a month.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(date(<expr>, ?, ?, ...))`` and whose ``current_datatype`` is
            always ``str``. Parameters are concatenated left-to-right:
            first ``value``'s parameters, then the modifiers in order.

        Example:
            Tomorrow's date::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([
                    Builtins.DateAdd('now', '+1 day'),
                ])
                # SELECT (date(?, ?)) FROM [users]
                # Parameters: ['now', '+1 day']
                # -> [('2024-03-16',)]

            A week from now::

                rows = users.get_row([
                    Builtins.DateAdd('now', '+7 days'),
                ])
                # -> [('2024-03-22',)]

            First day of the current month — a common reporting anchor::

                month_start = Builtins.DateAdd('now', 'start of month')
                rows = users.get_row([month_start])
                # -> [('2024-03-01',)]

            First day of next month — chain two modifiers::

                next_month_start = Builtins.DateAdd(
                    'now', '+1 month', 'start of month'
                )
                rows = users.get_row([next_month_start])
                # -> [('2024-04-01',)]

            Previous Monday relative to a stored timestamp::

                last_monday = Builtins.DateAdd(
                    users.created_at,
                    'weekday 1',
                )
                rows = users.get_row([users.username, last_monday])

            Normalise a UTC timestamp to local time before extracting
            the date::

                local_date = Builtins.DateAdd(
                    users.created_at,
                    'localtime',
                )
                rows = users.get_row([users.username, local_date])
                # -> [('Alice', '2024-03-15'), ...]

            "End of month" computation — start of next month minus one day::

                eom = Builtins.DateAdd(
                    users.created_at,
                    'start of month',
                    '+1 month',
                    '-1 day',
                )
                rows = users.get_row([users.username, eom])
                # -> [('Alice', '2024-03-31'), ...]

            Filter events that occurred in the current month::

                month_start = Builtins.DateAdd('now', 'start of month')
                next_month  = Builtins.DateAdd('now', '+1 month', 'start of month')
                rows = users.get_row(
                    [users.id, users.created_at],
                    where=(Builtins.Date(users.created_at) >= month_start)
                        & (Builtins.Date(users.created_at) < next_month),
                )

            Birthday reminder — a fixed annual shift::

                # For a stored date of birth, get this year's birthday:
                birthday_this_year = Builtins.DateAdd(
                    users.date_of_birth,
                    '+0 years',
                )
                # (Kept short here; in practice you compute the year
                #  offset dynamically in Python before passing it.)
                rows = users.get_row([users.username, birthday_this_year])

            Degenerate form — no modifiers, same as :meth:`Date`::

                rows = users.get_row([
                    Builtins.DateAdd(users.created_at),   # (date(<expr>))
                    Builtins.Date(users.created_at),      # (date(<expr>))
                ])
                # Both columns produce identical SQL and results.
        """
        sql, p, _, c = Builtins._normalize(value)
        if not modifiers:
            return Builtins._make(f"(date({sql}))", p, str, c)
        ph = ", ".join("?" for _ in modifiers)
        return Builtins._make(
            f"(date({sql}, {ph}))", p + list(modifiers), str, c)

    @staticmethod
    def DateTimeAdd(value, *modifiers):
        """Apply one or more date modifiers to a value and return a datetime string.

        Generates a ``datetime(<expr>, <m1>, <m2>, ...)`` expression. This
        is the datetime-producing counterpart of :meth:`DateAdd`: same
        modifier set, same chaining semantics, but the result is a TEXT
        string in ``'YYYY-MM-DD HH:MM:SS'`` format instead of a bare
        ``'YYYY-MM-DD'``.

        Use this method whenever the time-of-day component matters — for
        example, when computing "one hour from now", when the modifiers
        include a time unit (``'+N hours'``, ``'+N minutes'``,
        ``'+N seconds'``), or when the base value is a full timestamp and
        you want to preserve the time portion.

        See :meth:`DateAdd` for the complete list of accepted modifier
        strings. They are identical for both helpers.

        When called with no modifiers, this helper degenerates to
        ``datetime(<expr>)`` — the same behaviour as :meth:`DateTime`.

        Args:
            value: The starting date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder. The special string ``'now'`` produces the
                  current moment.

            *modifiers: Zero or more modifier strings, each bound as a
                ``?`` parameter. Applied left-to-right, exactly as in
                :meth:`DateAdd`.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(datetime(<expr>, ?, ?, ...))`` and whose ``current_datatype``
            is always ``str``. Parameters are concatenated left-to-right:
            first ``value``'s parameters, then the modifiers in order.

        Example:
            One hour from now — the time portion is preserved::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([
                    Builtins.DateTimeAdd('now', '+1 hour'),
                ])
                # SELECT (datetime(?, ?)) FROM [users]
                # Parameters: ['now', '+1 hour']
                # -> [('2024-03-15 15:30:42',)]

            Fifteen minutes from now — good for short-lived tokens::

                expiry = Builtins.DateTimeAdd('now', '+15 minutes')
                rows = users.get_row([users.id, expiry])

            Unix-time style "now" converted to a datetime in local time::

                local_now = Builtins.DateTimeAdd('now', 'localtime')
                rows = users.get_row([local_now])
                # -> [('2024-03-15 15:30:42',)] if the server is UTC+1

            Last week relative to a stored timestamp::

                last_week = Builtins.DateTimeAdd(users.created_at, '-7 days')
                rows = users.get_row([users.username, last_week])
                # -> [('Alice', '2024-03-08 09:30:42'), ...]

            Beginning of the current hour — combine two modifiers::

                top_of_hour = Builtins.DateTimeAdd(
                    'now',
                    'start of day',
                    '+9 hours',
                )
                rows = users.get_row([top_of_hour])
                # -> [('2024-03-15 09:00:00',)]

            Filter events in the last hour — compare against a computed
            threshold::

                cutoff = Builtins.DateTimeAdd('now', '-1 hour')
                rows = users.get_row(
                    [users.id, users.created_at],
                    where=users.created_at >= cutoff,
                )
                # SELECT [users].[id], [users].[created_at] FROM [users]
                # WHERE ([users].[created_at] >= (datetime(?, ?)))
                # Parameters: ['now', '-1 hour']

            Rolling window of one day — a common "recent activity" filter::

                rows = users.get_row(
                    [users.username, users.last_seen],
                    where=Builtins.DateTime(users.last_seen)
                        >= Builtins.DateTimeAdd('now', '-1 day'),
                )

            Explicitly add "months" — the datetime form is safer because
            the day-of-month overflow rules are the same as ``date()``::

                plus_three_months = Builtins.DateTimeAdd(
                    users.subscribed_at, '+3 months'
                )
                rows = users.get_row([users.username, plus_three_months])

            Two-modifier ordering — "start of month" then "+1 month" gives
            the beginning of the *next* month::

                next_month_start = Builtins.DateTimeAdd(
                    'now', 'start of month', '+1 month'
                )
                rows = users.get_row([next_month_start])
                # -> [('2024-04-01 00:00:00',)]

            Store a computed expiry during an UPDATE::

                users.update(
                    update={users.token_expires: Builtins.DateTimeAdd('now', '+1 day')},
                    where=users.id == 42,
                )
                # UPDATE [users]
                # SET [token_expires]=(datetime(?, ?))
                # WHERE ([users].[id] = ?);
                # Parameters: ['now', '+1 day', 42]

            Degenerate form — no modifiers, same as :meth:`DateTime`::

                rows = users.get_row([
                    Builtins.DateTimeAdd(users.created_at),   # (datetime(<expr>))
                    Builtins.DateTime(users.created_at),      # (datetime(<expr>))
                ])
                # Both columns produce identical SQL and results.
        """
        sql, p, _, c = Builtins._normalize(value)
        if not modifiers:
            return Builtins._make(f"(datetime({sql}))", p, str, c)
        ph = ", ".join("?" for _ in modifiers)
        return Builtins._make(
            f"(datetime({sql}, {ph}))", p + list(modifiers), str, c)

    @staticmethod
    def TimeAdd(value, *modifiers):
        """Apply one or more date modifiers to a value and return a time-of-day string.

        Generates a ``time(<expr>, <m1>, <m2>, ...)`` expression. This is
        the time-only counterpart of :meth:`DateAdd` and
        :meth:`DateTimeAdd`: the modifier set is identical, but the result
        is a TEXT string in ``'HH:MM:SS'`` format, discarding the date
        component entirely.

        Use this method when you only care about the time of day — for
        example, when a schedule shifts by a fixed number of minutes
        regardless of which day it lands on, or when you want to compare
        two times-of-day without their dates confusing the result.

        Because SQLite's date functions always carry a full date
        internally, ``time()`` internally applies the modifiers to a
        complete date and then throws away the date portion. That means
        modifiers like ``'+1 day'`` produce a *different* result in
        ``time()`` than ``'+24 hours'`` would — the former crosses into
        the next day and back to 00:00:00, while the latter just adds 24
        hours and wraps the clock. For schedules that should not depend on
        day boundaries, prefer minute-based modifiers.

        See :meth:`DateAdd` for the complete list of accepted modifier
        strings. They are identical for all three helpers.

        When called with no modifiers, this helper degenerates to
        ``time(<expr>)`` — the same behaviour as :meth:`Time`.

        Args:
            value: The starting date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder. The special string ``'now'`` produces the
                  current moment.

            *modifiers: Zero or more modifier strings, each bound as a
                ``?`` parameter. Applied left-to-right, exactly as in
                :meth:`DateAdd`.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(time(<expr>, ?, ?, ...))`` and whose ``current_datatype``
            is always ``str``. Parameters are concatenated left-to-right:
            first ``value``'s parameters, then the modifiers in order.

        Example:
            The current time of day::

                from Ormophine.Sqlite import Driver, Builtins

                db     = Driver('scheduler.db')
                events = db.events

                rows = events.get_row([Builtins.TimeAdd('now')])
                # SELECT (time(?)) FROM [events]
                # Parameters: ['now']
                # -> [('14:30:42',)]

            Shift a stored time by 30 minutes::

                rows = events.get_row([
                    events.id,
                    events.scheduled_at,
                    Builtins.TimeAdd(events.scheduled_at, '+30 minutes'),
                ])
                # SELECT [events].[id], [events].[scheduled_at],
                #        (time([events].[scheduled_at], ?))
                # FROM [events]
                # Parameters: ['+30 minutes']
                # -> [(1, '2024-03-15 09:00:00', '09:30:00'), ...]

            Compute the "next hour" marker — strip minutes and seconds::

                # Note: "start of hour" is not a SQLite modifier.
                # The closest approach is to extract the hour and rebuild:
                hh = Builtins.Hour(events.scheduled_at)
                top_of_hour = Builtins.Format('%02d:00:00', hh)
                rows = events.get_row([events.id, top_of_hour])

            Compare a stored time against a threshold::

                rows = events.get_row(
                    [events.id, events.scheduled_at],
                    where=Builtins.TimeAdd(events.scheduled_at, '+15 minutes') > '18:00:00',
                )
                # -> events whose scheduled time + 15 min is after 6 PM

            Shift a time-of-day backwards by an hour::

                one_hour_earlier = Builtins.TimeAdd(
                    events.scheduled_at, '-1 hour'
                )
                rows = events.get_row([events.id, one_hour_earlier])
                # -> [(1, '08:00:00'), (2, '07:30:00'), ...]

            Cross-day stability — using minutes rather than days avoids
            the wrap-around surprise::

                # These two produce different results:
                by_day   = Builtins.TimeAdd('12:00:00', '+1 day')     # -> '12:00:00' (same)
                by_minutes = Builtins.TimeAdd('12:00:00', '+60 minutes')  # -> '13:00:00'
                # Prefer minutes when the intent is a duration.

            Local time conversion for display::

                local_time = Builtins.TimeAdd(events.scheduled_at, 'localtime')
                rows = events.get_row([events.id, local_time])
                # -> [('09:00:00',), ...] if the server is UTC+1 and the
                #    stored value was 08:00:00 UTC

            Filter office-hours slots — times between 09:00 and 17:00::

                rows = events.get_row(
                    [events.id, events.scheduled_at],
                    where=(Builtins.Time(events.scheduled_at) >= '09:00:00')
                        & (Builtins.Time(events.scheduled_at) <= '17:00:00'),
                )

            Compose with :meth:`Format` for a display string::

                display = Builtins.Format(
                    'Next slot at %s',
                    Builtins.TimeAdd(events.scheduled_at, '+45 minutes'),
                )
                rows = events.get_row([events.id, display])
                # -> [('Next slot at 09:45:00',), ...]

            Degenerate form — no modifiers, same as :meth:`Time`::

                rows = events.get_row([
                    Builtins.TimeAdd(events.scheduled_at),   # (time(<expr>))
                    Builtins.Time(events.scheduled_at),      # (time(<expr>))
                ])
                # Both columns produce identical SQL and results.
        """
        sql, p, _, c = Builtins._normalize(value)
        if not modifiers:
            return Builtins._make(f"(time({sql}))", p, str, c)
        ph = ", ".join("?" for _ in modifiers)
        return Builtins._make(
            f"(time({sql}, {ph}))", p + list(modifiers), str, c)

    @staticmethod
    def StrftimeMod(fmt, value, *modifiers):
        """Format a date/time value with modifiers applied first.

        Generates a ``strftime(<fmt>, <expr>, <m1>, <m2>, ...)``
        expression. This is the modifier-aware companion of
        :meth:`Strftime`: it applies every modifier to ``value`` before
        feeding the result to the format string, which lets you do things
        like "format the timestamp as ``YYYY-MM`` *after* adding one month"
        in a single SQL expression.

        The full set of modifiers documented for :meth:`DateAdd` is
        available. The format string supports the same specifiers as
        :meth:`Strftime` (``%Y``, ``%m``, ``%d``, ``%H``, ``%M``, ``%S``,
        ``%w``, ``%j``, ``%W``, ``%%``).

        When called with no modifiers, this helper degenerates to
        ``strftime(<fmt>, <expr>)`` — the same behaviour as
        :meth:`Strftime`. The separate name exists for the modifier-aware
        form, but both patterns are valid.

        The result is always a TEXT string.

        Args:
            fmt: The format string. Bound as a ``?`` parameter, so it can
                be user-supplied safely.

            value: The starting date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``?``
                  placeholder. The special string ``'now'`` produces the
                  current moment.

            *modifiers: Zero or more modifier strings, each bound as a
                ``?`` parameter. Applied left-to-right.

        Returns:
            :class:`ColumnsOperation`: An expression whose ``_output[0]`` is
            ``(strftime(?, <expr>, ?, ?, ...))`` and whose
            ``current_datatype`` is always ``str``. Parameters are ordered:
            first ``fmt``, then ``value``'s parameters, then the modifiers
            in order.

        Example:
            Format "one month from now" as ``YYYY-MM``::

                from Ormophine.Sqlite import Driver, Builtins

                db    = Driver('app.db')
                users = db.users

                rows = users.get_row([
                    Builtins.StrftimeMod(
                        '%Y-%m',
                        'now',
                        '+1 month',
                    ),
                ])
                # SELECT (strftime(?, ?, ?)) FROM [users]
                # Parameters: ['%Y-%m', 'now', '+1 month']
                # -> [('2024-04',)]

            Report period label from a stored subscription date::

                period = Builtins.StrftimeMod(
                    '%Y-%m',
                    users.subscribed_at,
                    '+3 months',
                )
                rows = users.get_row([users.username, period])
                # -> [('Alice', '2024-06'), ('Bob', '2024-07'), ...]

            "Last seen today" — extract the time after converting to
            local time::

                last_seen_local = Builtins.StrftimeMod(
                    '%H:%M',
                    users.last_seen,
                    'localtime',
                )
                rows = users.get_row([users.username, last_seen_local])
                # -> [('Alice', '15:30'), ('Bob', '09:12'), ...]

            Month bucket with a shift — one row per user showing the
            quarter that starts *after* their signup month::

                quarter_label = Builtins.StrftimeMod(
                    '%Y-Q%m',
                    users.created_at,
                    '+1 month',
                    'start of month',
                )
                # Note: '%m' is the month; to bucket into quarters, use
                # integer arithmetic on Month() in a separate expression.
                # The output here is a "YYYY-MM" style label with the year
                # followed by a Q and the numeric month — handy for
                # sorting, less so for display.

            Cleaner quarter label — chain with Python-side post-processing::

                rows = users.get_row([
                    users.username,
                    Builtins.StrftimeMod('%Y', users.created_at),
                    Builtins.Month(users.created_at),
                ])
                # In Python: quarter = (month - 1) // 3 + 1

            "First of next month" as a display string::

                first_next_month = Builtins.StrftimeMod(
                    '%Y-%m-%d',
                    'now',
                    '+1 month',
                    'start of month',
                )
                rows = users.get_row([first_next_month])
                # -> [('2024-04-01',)]

            Filter by a formatted, modified value::

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.StrftimeMod(
                        '%Y',
                        users.created_at,
                        '-6 months',
                    ) == '2023',
                )
                # Users whose timestamp, shifted back six months, falls in 2023.

            Degenerate form — no modifiers, same as :meth:`Strftime`::

                rows = users.get_row([
                    Builtins.StrftimeMod('%Y', users.created_at),
                    Builtins.Strftime('%Y', users.created_at),
                ])
                # Both columns produce identical SQL and results.
        """
        sql, p, _, c = Builtins._normalize(value)
        ph = ", ".join("?" for _ in modifiers)
        args = f"?, {sql}" + (f", {ph}" if modifiers else "")
        return Builtins._make(
            f"(strftime({args}))",
            [fmt] + p + list(modifiers), str, c)
    