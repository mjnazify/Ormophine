from __future__ import annotations
from .. import Column, ColumnsOperation


class Builtins:
    """PostgreSQL SQL function helpers that always return a :class:`ColumnsOperation`.

    ``Builtins`` is a stateless namespace of static methods, each of which
    wraps a PostgreSQL function (or, where PostgreSQL lacks a native
    function, a short composition of PostgreSQL functions) into a
    :class:`ColumnsOperation` object. Because every helper returns a
    ``ColumnsOperation``, the result can be used anywhere a column
    expression is accepted: in the ``which_columns`` list of
    :meth:`Table.get_row`, in the ``where`` condition, in the ``update``
    dict of :meth:`Table.update`, inside :meth:`~Table.bulk_update`, and
    so on. Helpers can also be nested freely — e.g.
    ``Builtins.Round(Builtins.Avg(col) * 100) / 100`` compiles into a
    single SQL expression with all parameters collected in order.

    Design
    ------
    The class is deliberately a namespace, not an instance-based helper.
    You never write ``Builtins()``; every entry point is a
    ``@staticmethod`` you call directly::

        from Ormophine.Postgresql import Driver, Builtins

        rows = users.get_row(
            [users.id, Builtins.Len(users.username)],
            where=Builtins.Len(users.username) > 5,
        )

    All three of the standard operand types are accepted by every helper:

    - :class:`Column` — the fully qualified name (`` "table"."col" ``) is
      embedded verbatim; no parameters are consumed.
    - :class:`ColumnsOperation` — the previously-built SQL fragment and
      its parameter list are reused and extended.
    - Any raw Python value (``str``, ``int``, ``float``, ``bytes``,
      ``None``, ``bool``) — bound as a ``%s`` placeholder. Binding rather
      than interpolating means the value never reaches the SQL text, so
      injection is impossible.

    Datatype propagation
    --------------------
    Each helper sets ``current_datatype`` on the returned
    ``ColumnsOperation`` to a Python type (``int``, ``float``, ``str``,
    ``bytes``, ``bool``, or ``None`` when the result's type depends on its
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
    ``Count``, ``Abs``, ``Sign``, ``Floor``,
    ``Ceil``, ``Int``, ``Year``, ``Month``,
    ``Day``, ``Hour``, ``Minute``, ``Second``,
    ``DayOfWeek``, ``IsoWeekday``, ``Weekday``,
    ``DayOfYear``, ``WeekOfYear``, ``UnixNow``,
    ``UnixEpoch``, ``DateDiffDays``,
    ``DateDiffSeconds``                      ``int``
    ``Avg``, ``Round``, ``Sqrt``, ``Pow``,
    ``Float``, ``Total``, ``JulianDay``      ``float``
    ``Reverse``-equivalents, ``Upper``,
    ``Lower``, ``Trim``, ``Capitalize``,
    ``Str``, ``Date``, ``Time``, ``DateTime``,
    ``Now``, ``Today``, ``Strftime``,
    ``StrftimeMod``, ``Timediff``,
    ``DateAdd``, ``DateTimeAdd``,
    ``TimeAdd``, ``Format``, ``GroupConcat``,
    ``TypeOf``                               ``str``
    ``IsNull``, ``IsNotNull``, ``Between``,
    ``Bool``                                 ``bool``
    ``IIf``                                  ``None`` (branches may
                                             disagree)
    ===================================  =========

    Differences from the MySQL backend
    ----------------------------------
    The PostgreSQL helpers are deliberately *not* a mechanical port of the
    MySQL ones; PostgreSQL has different native functions, different type
    coercions, and a richer set of built-ins to expose. The important
    differences:

    **Helpers that exist only in PostgreSQL:**

    - :meth:`Total` — PostgreSQL's ``SUM`` returns ``NULL`` over empty
      groups, so ``Total`` wraps it in ``COALESCE(SUM(...), 0)`` — the
      SQL analogue of SQLite's ``TOTAL``.
    - :meth:`GroupConcat` — wraps ``STRING_AGG`` for
      ``','.join(...)``-style aggregation.
    - :meth:`TypeOf` — wraps ``PG_TYPEOF``, which returns the *actual*
      PostgreSQL type name (``'int4'``, ``'jsonb'``, ``'uuid'``, ...) —
      far more informative than SQLite's five storage classes.
    - :meth:`JulianDay` — wraps ``EXTRACT(JULIAN FROM ...)``, matching
      SQLite's ``julianday()``.
    - :meth:`Func` — a single-operand escape hatch for any PostgreSQL
      function not covered by a dedicated helper.
    - :meth:`Format` — wraps ``FORMAT`` for the ``%s``/``%I``/``%L``
      template language.
    - :meth:`Upper`, :meth:`Lower`, :meth:`Trim` — these are exposed as
      module-level helpers *in addition* to the corresponding ``Column``
      methods, so they can be applied to arbitrary expressions built from
      ``ColumnsOperation``.
    - :meth:`Capitalize` — PostgreSQL has no native ``CAPITALIZE``, so the
      helper composes ``UPPER(SUBSTRING(x,1,1)) || LOWER(SUBSTRING(x,2))``.

    **Helpers with PostgreSQL-specific semantics:**

    - :meth:`Bool` — PostgreSQL has a real ``BOOLEAN`` type, so the
      helper casts to ``BOOLEAN`` (not ``SIGNED`` as in MySQL) and sets
      ``current_datatype = bool``.
    - :meth:`DayOfWeek` — PostgreSQL's ``DOW`` is Sunday=0 through
      Saturday=6, not the ODBC 1–7 convention MySQL uses. Use
      :meth:`Weekday` or :meth:`IsoWeekday` if you want the Python or
      ISO numbering.
    - :meth:`Weekday` — composed as
      ``((EXTRACT(DOW FROM x)::INTEGER + 6) % 7)`` to match Python's
      ``date.weekday()``.
    - :meth:`IsoWeekday` — a direct ``EXTRACT(ISODOW ...)`` (no modulo
      arithmetic needed, unlike the SQLite backend's equivalent).
    - :meth:`WeekOfYear` — a direct ``EXTRACT(WEEK ...)`` with ISO
      semantics (weeks start on Monday, week 1 contains the first
      Thursday).
    - :meth:`DateAdd` / :meth:`DateTimeAdd` / :meth:`TimeAdd` /
      :meth:`StrftimeMod` — the ``*intervals`` argument takes PostgreSQL
      interval strings like ``'1 day'``, ``'-3 hours'``, ``'2 months'``
      — **not** the SQLite-style ``'start of month'`` tokens. Use
      ``DATE_TRUNC`` via :meth:`Func` for period truncation.
    - :meth:`UnixNow` / :meth:`UnixEpoch` — composed as
      ``EXTRACT(EPOCH FROM ...)::BIGINT``, not ``UNIX_TIMESTAMP()``.
    - :meth:`Timediff` — returns the interval cast to ``text``, e.g.
      ``'2 days 05:29:18'``.

    **MySQL helpers deliberately absent here:**

    - ``IfNull`` — use :meth:`Total` for the common ``SUM + 0`` case, or
      :meth:`Func` with ``'COALESCE'`` for the general two-argument form.
    - ``Pow`` — present, but the underlying PostgreSQL function is
      ``POWER`` (not ``POW``); the helper name is kept for API parity.
    - ``UnixNow``'s MySQL form (``UNIX_TIMESTAMP()``) is not used because
      PostgreSQL has no such function.

    SQLite-style modifiers
    ----------------------
    The ``*intervals`` argument accepted by :meth:`DateAdd`,
    :meth:`DateTimeAdd`, :meth:`TimeAdd` and :meth:`StrftimeMod` expects
    PostgreSQL interval strings rather than SQLite modifier tokens. The
    accepted forms include:

    - ``'1 day'``, ``'7 days'``, ``'-1 day'`` — day arithmetic
    - ``'1 month'``, ``'3 months'``, ``'-2 months'`` — month arithmetic
      (PostgreSQL clamps end-of-month correctly)
    - ``'1 year'``, ``'-1 year'`` — year arithmetic
    - ``'2 hours'``, ``'30 minutes'``, ``'15 seconds'`` — time arithmetic
    - ``'1 day 2 hours'`` — compound intervals
    - ``'1-2'`` — SQL standard year-month form
    - ``'3 04:05:06'`` — SQL standard day-time form

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
      SQL fragment, which is the order psycopg expects.

    Example:
        A quick tour of the helper categories::

            from Ormophine.Postgresql import Driver, Builtins

            db    = Driver("localhost", 5432, "user", "pass", "app")
            users = db.users

            # String
            Builtins.Len(users.username)
            Builtins.Upper(users.name)
            Builtins.Lower(users.email)
            Builtins.Trim(users.name)
            Builtins.Capitalize(users.name)
            Builtins.Find(users.email, '@')
            Builtins.Format('Hello %s', users.name)

            # Aggregate
            Builtins.Sum(users.balance)
            Builtins.Avg(users.age)
            Builtins.Min(users.created_at)
            Builtins.Max(users.score)
            Builtins.Count('*')
            Builtins.Total(users.balance)
            Builtins.GroupConcat(users.username)

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
            Builtins.Strftime('YYYY-MM-DD', users.created_at)
            Builtins.Now()
            Builtins.Today()
            Builtins.UnixNow()
            Builtins.UnixEpoch(users.created_at)
            Builtins.JulianDay(users.created_at)
            Builtins.DateAdd(users.created_at, '1 day', '2 hours')
            Builtins.DateTimeAdd(users.created_at, '-1 hour')
            Builtins.TimeAdd(users.created_at, '30 minutes')
            Builtins.StrftimeMod('YYYY-MM', users.created_at, '1 month')
            Builtins.DateDiffDays(Builtins.Now(), users.created_at)
            Builtins.DateDiffSeconds(Builtins.Now(), users.updated_at)
            Builtins.Timediff(Builtins.Now(), users.created_at)

            # Escape hatch
            Builtins.Func('MD5', users.email)
    """

    class _NullCol:
        """Fallback stand-in used when a :class:`ColumnsOperation` has no originating :class:`Column`.

        Several helpers in :class:`Builtins` (e.g. :meth:`Builtins.Count`
        with ``'*'``, :meth:`Builtins.Now`, :meth:`Builtins.Today`,
        :meth:`Builtins.UnixNow`) produce SQL that does not refer to any
        particular table or column. For example ``COUNT(*)`` has no
        column operand, and ``NOW()`` is a server-side constant. But every
        :class:`ColumnsOperation` in this ORM is expected to carry a
        ``col_obj`` attribute pointing at the :class:`Column` that
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
            name (str): Always the empty string. Substituting it into SQL
                would produce invalid SQL, but this path is never taken
                because the helper's own SQL fragment already contains
                the complete expression.
            first_name (str): Always the empty string. Same reasoning as
                ``name``.
            table_obj (type): A *class* (not an instance) whose only
                attribute is ``_PlaceHolder`` set to ``type(None)``. This
                ensures that ``isinstance(value, self.col_obj.table_obj._PlaceHolder)``
                is ``False`` for every real Python value — so the operator
                dispatcher's numeric-vs-string branch in
                :meth:`ColumnsOperation.__add__` never accidentally treats
                a raw literal as a placeholder. The real
                :class:`Table._PlaceHolder` class is used only in the
                ``bulk_update`` context; helpers never participate in bulk
                updates, so ``_NullCol`` supplies a benign stub.

        Example:
            Internal usage within a helper::

                @staticmethod
                def Now(_=None):
                    return Builtins._make('(NOW())', [], str, Builtins._NullCol)

            The ``Builtins._NullCol`` class itself (not an instance) is
            passed because the helpers only need the attribute surface,
            never any per-instance state. Passing the class works because
            attribute lookup falls through to the class-level definitions.
        """
        datatype   = None
        name       = ''
        first_name = ''
        class table_obj:
            _PlaceHolder = type(None)   # Nothing isinstance-matches this

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
          (`` "table"."col" ``); for a :class:`ColumnsOperation` it is the
          previously-built fragment; for a raw value it is the placeholder
          ``'%s'``.
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
                - Any other Python value — wrapped as ``('%s', [value])``
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
                ('"users"."username"', [], str, <Column users.username>)

                >>> op = Builtins.Len(users.username)
                >>> Builtins._normalize(op)
                ('(LENGTH("users"."username"))', [], int, <Column users.username>)

                >>> Builtins._normalize('hello')
                ('%s', ['hello'], str, Builtins._NullCol)

                >>> Builtins._normalize(42)
                ('%s', [42], int, Builtins._NullCol)

                >>> Builtins._normalize(None)
                ('%s', [None], NoneType, Builtins._NullCol)
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
        return '%s', [value], type(value), Builtins._NullCol

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
                add. Must contain ``%s`` placeholders exactly as many times
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

                # Len — PostgreSQL LENGTH()
                return Builtins._make(f'(LENGTH({sql}))', p, int, c)

                # Now — no operands at all
                return Builtins._make('(NOW())', [], str, Builtins._NullCol)

                # IIf — datatype intentionally None because the branches
                # may disagree
                return Builtins._make(
                    f'(CASE WHEN {cs} THEN {ts} ELSE {es} END)',
                    cp + tp + ep,
                    None,
                    c,
                )

                # DateDiffDays — nested CAST/EXTRACT
                return Builtins._make(
                    f'(CAST(EXTRACT(EPOCH FROM '
                    f'(CAST({s1} AS TIMESTAMP) - CAST({s2} AS TIMESTAMP))) '
                    f'/ 86400 AS INTEGER))',
                    p1 + p2, int, c,
                )

            The result composes with the rest of the expression system::

                >>> op = Builtins._make('(NOW())', [], str, Builtins._NullCol)
                >>> op._output
                ('(NOW())', [])
                >>> op.current_datatype
                <class 'str'>
                >>> # Chain arithmetic — the dispatcher sees str, so it
                >>> # would pick || unless overridden by a cast builtin.
                >>> (Builtins.Int(Builtins.UnixNow()) + 60)._output[0]
                '((CAST((EXTRACT(EPOCH FROM NOW())::BIGINT)) AS INTEGER) + %s)'
        """
        op = ColumnsOperation.__new__(ColumnsOperation)
        op._output          = (sql, params)
        op.col_obj          = col_obj if col_obj is not None else Builtins._NullCol
        op.current_datatype = datatype
        return op
    
    @staticmethod
    def Len(value):
        """Compute the length of a value using PostgreSQL's ``LENGTH()`` function.

        Generates a SQL expression that returns the number of characters in a
        string, or the number of bytes in a ``BYTEA``. This is the SQL
        equivalent of Python's built-in ``len()``. The result is always an
        ``INTEGER``, regardless of the input's datatype.

        The returned object is a :class:`ColumnsOperation`, so every operator
        and method of that class remains available on it — comparisons,
        string methods, slicing, ``In``, ``like``, arithmetic, and so on.

        Args:
            value: The expression whose length is computed. Supported types:

                - :class:`ColumnsOperation` — the generated SQL fragment and
                  its parameters are reused.
                - :class:`Column` — the fully qualified column name is used
                  directly in the SQL; no parameters are consumed.
                - Any raw Python value (``str``, ``int``, ``float``,
                  ``bytes``) — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(LENGTH(<expr>))`` and whose ``current_datatype`` is ``int``.

        Example:
            Basic filtering — find users whose username is longer than 5
            characters::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row(
                    [users.username],
                    where=Builtins.Len(users.username) > 5,
                )
                # SELECT "users"."username" FROM "users"
                # WHERE (LENGTH("users"."username") > %s)
                # Parameters: [5]

            As a SELECT column — the length of each username::

                rows = users.get_row([
                    users.username,
                    Builtins.Len(users.username),
                ])
                # SELECT "users"."username", (LENGTH("users"."username"))
                # FROM "users"

            Chained with other operations — the length padded up to the
            nearest multiple of 4, then selected::

                padded_len = ((Builtins.Len(users.username) + 3) / 4) * 4
                rows = users.get_row(
                    [users.username, padded_len],
                    where=Builtins.Len(users.username) > 0,
                )
                # SELECT "users"."username",
                #        ((((LENGTH("users"."username") + %s) / %s) * %s))
                # FROM "users"
                # WHERE (LENGTH("users"."username") > %s)

            Nested inside other builtins — the average username length::

                avg_len = Builtins.Avg(Builtins.Len(users.username))
                rows = users.get_row([avg_len])
                # SELECT (AVG((LENGTH("users"."username")))) FROM "users"

            Applied to a raw literal — the literal is bound as a parameter::

                rows = users.get_row([
                    Builtins.Len('hello'),   # -> (LENGTH(%s)) with param 'hello'
                    Builtins.Len(42),        # -> (LENGTH(%s)) with param 42
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(LENGTH({sql}))', p, int, c)

    @staticmethod
    def Sum(value):
        """Compute the sum of a set of values using PostgreSQL's ``SUM()`` aggregate.

        Generates an SQL ``SUM(<expr>)`` expression. When used in a SELECT
        list without a ``GROUP BY`` clause, it aggregates over all rows
        returned by the query. When used inside a ``WHERE`` clause it has no
        meaning on its own (PostgreSQL will reject it) — ``Sum`` is meant for
        the SELECT side of a query, not for filtering.

        The resulting ``current_datatype`` is propagated from the input:

        - ``int``   → ``int`` (PostgreSQL keeps integer sums as integers
          when the input is a smallint/integer/bigint)
        - ``float`` → ``float`` (numeric and real inputs propagate as float)
        - anything else → ``int`` (conservative default)

        This keeps arithmetic chains (``Builtins.Sum(col) + 1``) compiling
        to ``+`` and not ``||``.

        Args:
            value: The expression to sum. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder
                  (rarely useful as the sole argument of an aggregate, but
                  supported for completeness).

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(SUM(<expr>))`` and whose ``current_datatype`` matches the
            input's numeric type (or ``int`` if the input is not numeric).

        Example:
            Total salary across all employees::

                from Ormophine.Postgresql import Driver, Builtins

                db        = Driver("localhost", 5432, "user", "pass", "company")
                employees = db.employees

                total = Builtins.Sum(employees.salary)
                rows  = employees.get_row([total])
                # SELECT (SUM("employees"."salary")) FROM "employees"
                # -> [(1245000,)] for example

            Sum alongside other aggregates::

                rows = employees.get_row([
                    Builtins.Count('*'),
                    Builtins.Sum(employees.salary),
                    Builtins.Avg(employees.salary),
                ])
                # SELECT (COUNT(*)), (SUM("employees"."salary")),
                #        (AVG("employees"."salary"))
                # FROM "employees"

            Sum combined with arithmetic (stays numeric, not string)::

                with_bonus = Builtins.Sum(employees.salary) + 10000
                rows = employees.get_row([with_bonus])
                # SELECT ((SUM("employees"."salary")) + %s) FROM "employees"
                # Parameters: [10000]

            Sum of a computed expression::

                net_total = Builtins.Sum(employees.salary - employees.tax)
                rows = employees.get_row([net_total])
                # SELECT (SUM(("employees"."salary" - "employees"."tax")))
                # FROM "employees"

            Group totals — fetch each department's total in Python::

                rows = employees.get_row([
                    employees.department,
                    Builtins.Sum(employees.salary),
                ])
                # SELECT "employees"."department",
                #        (SUM("employees"."salary"))
                # FROM "employees"
                # -> [('Engineering', 320000), ('Sales', 180000), ...]
        """
        sql, p, dt, c = Builtins._normalize(value)
        result_dt = dt if dt in (int, float) else int
        return Builtins._make(f'(SUM({sql}))', p, result_dt, c)

    @staticmethod
    def Avg(value):
        """Compute the average of a set of values using PostgreSQL's ``AVG()`` aggregate.

        Generates an SQL ``AVG(<expr>)`` expression. PostgreSQL always returns
        the average as a ``NUMERIC`` (which psycopg delivers to Python as
        ``decimal.Decimal``), but this helper declares the result as
        ``float`` so downstream arithmetic chains stay in the floating-point
        domain — matching SQLite's behaviour and Python's ``statistics.mean``.

        Like :meth:`Sum`, this aggregate is meant for the SELECT side of a
        query. Using it in a ``WHERE`` clause will raise an SQL error unless
        the query contains a ``GROUP BY`` that makes the aggregate legal.

        Args:
            value: The expression to average. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(AVG(<expr>))`` and whose ``current_datatype`` is always
            ``float``.

        Example:
            Average salary across all employees::

                from Ormophine.Postgresql import Driver, Builtins

                db        = Driver("localhost", 5432, "user", "pass", "company")
                employees = db.employees

                rows = employees.get_row([Builtins.Avg(employees.salary)])
                # SELECT (AVG("employees"."salary")) FROM "employees"
                # -> [(78750.0,)] for example

            Average rounded to two decimals::

                rows = employees.get_row([
                    Builtins.Round(Builtins.Avg(employees.salary) * 100) / 100
                ])
                # SELECT ((ROUND(((AVG("employees"."salary")) * %s))) / %s)
                # FROM "employees"
                # Parameters: [100, 100]

            Average of a computed expression::

                rows = employees.get_row([
                    Builtins.Avg(employees.salary + employees.bonus)
                ])
                # SELECT (AVG(("employees"."salary" + "employees"."bonus")))
                # FROM "employees"

            Combined with other aggregates in a single row::

                rows = employees.get_row([
                    Builtins.Count('*'),
                    Builtins.Avg(employees.salary),
                    Builtins.Sum(employees.salary),
                ])
                # SELECT (COUNT(*)), (AVG("employees"."salary")),
                #        (SUM("employees"."salary"))
                # FROM "employees"

            Per-department averages — fetched as (department, avg) pairs::

                rows = employees.get_row([
                    employees.department,
                    Builtins.Avg(employees.salary),
                ])
                # -> [('Engineering', 82000.0), ('Sales', 64500.0), ...]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(AVG({sql}))', p, float, c)

    @staticmethod
    def Min(value):
        """Compute the minimum of a set of values using PostgreSQL's ``MIN()`` aggregate.

        Generates an SQL ``MIN(<expr>)`` expression. When used with a single
        argument in the SELECT list, ``MIN`` acts as an aggregate over all
        rows of the group.

        The resulting ``current_datatype`` is propagated from the input,
        because PostgreSQL returns the same type as the operand:

        - ``int``   → ``int``
        - ``float`` → ``float``
        - ``str``   → ``str`` (lexicographic minimum)
        - ``bytes`` → ``bytes``

        This keeps downstream concatenation (``Builtins.Min(col) + '!'``)
        compiling to ``||`` when the input was text, and keeps arithmetic
        (``Builtins.Min(col) + 1``) numeric when the input was numeric.

        Args:
            value: The expression whose minimum is computed. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(MIN(<expr>))`` and whose ``current_datatype`` matches the
            input's datatype.

        Example:
            Lowest salary in the table::

                from Ormophine.Postgresql import Driver, Builtins

                db        = Driver("localhost", 5432, "user", "pass", "company")
                employees = db.employees

                rows = employees.get_row([Builtins.Min(employees.salary)])
                # SELECT (MIN("employees"."salary")) FROM "employees"
                # -> [(45000,)] for example

            Earliest signup date::

                users = db.users
                rows  = users.get_row([Builtins.Min(users.created_at)])
                # SELECT (MIN("users"."created_at")) FROM "users"
                # -> [('2021-03-04 08:15:42',)]

            Lexicographic minimum of a text column — note that
            ``current_datatype`` is ``str`` here, so chaining with ``+``
            produces ``||``::

                expr = Builtins.Min(employees.name) + ' (first alphabetically)'
                rows = employees.get_row([expr])
                # SELECT ((MIN("employees"."name")) || %s) FROM "employees"
                # Parameters: [' (first alphabetically)']

            Minimum of a computed expression::

                rows = employees.get_row([
                    Builtins.Min(employees.salary - employees.bonus)
                ])
                # SELECT (MIN(("employees"."salary" - "employees"."bonus")))
                # FROM "employees"

            Per-department minimums::

                rows = employees.get_row([
                    employees.department,
                    Builtins.Min(employees.salary),
                ])
                # -> [('Engineering', 45000), ('Sales', 42000), ...]
        """
        sql, p, dt, c = Builtins._normalize(value)
        return Builtins._make(f'(MIN({sql}))', p, dt, c)

    @staticmethod
    def Max(value):
        """Compute the maximum of a set of values using PostgreSQL's ``MAX()`` aggregate.

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
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(MAX(<expr>))`` and whose ``current_datatype`` matches the
            input's datatype.

        Example:
            Highest salary in the table::

                from Ormophine.Postgresql import Driver, Builtins

                db        = Driver("localhost", 5432, "user", "pass", "company")
                employees = db.employees

                rows = employees.get_row([Builtins.Max(employees.salary)])
                # SELECT (MAX("employees"."salary")) FROM "employees"
                # -> [(180000,)] for example

            Latest signup date::

                users = db.users
                rows  = users.get_row([Builtins.Max(users.created_at)])
                # SELECT (MAX("users"."created_at")) FROM "users"
                # -> [('2024-11-22 17:04:11',)]

            The id of the top earner — combine a filter with ORDER BY and
            LIMIT, since SQLite-style ``MAX`` + other columns is not
            portable in PostgreSQL::

                top = employees.get_row(
                    [employees.id, employees.name, employees.salary],
                    order_by=employees.salary * -1,
                    limit=1,
                )
                # SELECT "employees"."id", "employees"."name",
                #        "employees"."salary"
                # FROM "employees"
                # ORDER BY ("employees"."salary" * %s)
                # LIMIT %s
                # Parameters: [-1, 1]

            Maximum of a computed expression::

                rows = employees.get_row([
                    Builtins.Max(employees.salary + employees.bonus)
                ])
                # SELECT (MAX(("employees"."salary" + "employees"."bonus")))
                # FROM "employees"

            Lexicographic maximum of a text column — ``current_datatype``
            is ``str``, so ``add_end`` chains as ``||``::

                expr = Builtins.Max(employees.name).add_end(' wins')
                rows = employees.get_row([expr])
                # SELECT ((MAX("employees"."name")) || %s) FROM "employees"
                # Parameters: [' wins']

            Per-department maximums::

                rows = employees.get_row([
                    employees.department,
                    Builtins.Max(employees.salary),
                ])
                # -> [('Engineering', 180000), ('Sales', 95000), ...]
        """
        sql, p, dt, c = Builtins._normalize(value)
        return Builtins._make(f'(MAX({sql}))', p, dt, c)

    @staticmethod
    def Count(value):
        """Count rows using PostgreSQL's ``COUNT()`` aggregate.

        Two forms are supported, mirroring SQL's own behaviour:

        * **Row count** — when ``value`` is the literal string ``'*'``,
          generates ``COUNT(*)`` which counts every row in the group,
          regardless of NULL values.
        * **Non-null count** — for any other input, generates
          ``COUNT(<expr>)`` which counts only the rows where the expression
          evaluates to a non-NULL value.

        The result is always an ``INTEGER`` (PostgreSQL returns ``BIGINT``
        from ``COUNT``, and psycopg delivers it as a Python ``int``).

        Args:
            value: What to count. Supported types:

                - The string ``'*'`` — produces ``COUNT(*)`` and no
                  parameters.
                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused; produces ``COUNT(<fragment>)``.
                - :class:`Column` — the fully qualified column name is used;
                  produces ``COUNT("table"."column")``.
                - Any other raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is either
            ``(COUNT(*))`` or ``(COUNT(<expr>))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Count all rows in the table::

                from Ormophine.Postgresql import Driver, Builtins

                db        = Driver("localhost", 5432, "user", "pass", "company")
                employees = db.employees

                rows = employees.get_row([Builtins.Count('*')])
                # SELECT (COUNT(*)) FROM "employees"
                # -> [(250,)] for example

            Count rows where a column is non-NULL::

                users = db.users
                rows  = users.get_row([Builtins.Count(users.email)])
                # SELECT (COUNT("users"."email")) FROM "users"
                # -> [(198,)] — 52 users have no email on file

            Count with a filter — combine with ``where=`` in the usual way::

                rows = users.get_row(
                    [Builtins.Count('*')],
                    where=users.is_active == True,
                )
                # SELECT (COUNT(*)) FROM "users"
                # WHERE ("users"."is_active" = %s)
                # Parameters: [True]

            Count of a computed expression::

                rows = users.get_row([
                    Builtins.Count(Builtins.Upper(users.username))
                ])
                # SELECT (COUNT((UPPER("users"."username")))) FROM "users"

            Boolean count via a ``CASE`` — count how many rows satisfy a
            condition inside a single aggregate. The ``IIf`` builder emits
            a ``CASE WHEN ... THEN ... ELSE ... END``::

                adults = Builtins.Sum(
                    Builtins.IIf(users.age >= 18, 1, 0)
                )
                rows = users.get_row([adults])
                # SELECT (SUM((CASE WHEN ("users"."age" >= %s)
                #                    THEN %s ELSE %s END)))
                # FROM "users"
                # Parameters: [18, 1, 0]
        """
        if isinstance(value, str) and value == '*':
            return Builtins._make('(COUNT(*))', [], int, Builtins._NullCol)
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(COUNT({sql}))', p, int, c)

    @staticmethod
    def Abs(value):
        """Compute the absolute value of a number using PostgreSQL's ``ABS()`` function.

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
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(ABS(<expr>))`` and whose ``current_datatype`` matches the
            input's numeric type (or ``float`` if the input is not numeric).

        Example:
            Magnitude of a signed delta::

                from Ormophine.Postgresql import Driver, Builtins

                db        = Driver("localhost", 5432, "user", "pass", "analytics")
                movements = db.movements

                rows = movements.get_row([
                    movements.account_id,
                    Builtins.Abs(movements.delta),
                ])
                # SELECT "movements"."account_id",
                #        (ABS("movements"."delta"))
                # FROM "movements"

            Filter by absolute value::

                rows = movements.get_row(
                    [movements.account_id, movements.delta],
                    where=Builtins.Abs(movements.delta) > 1000,
                )
                # SELECT "movements"."account_id", "movements"."delta"
                # FROM "movements"
                # WHERE ((ABS("movements"."delta")) > %s)
                # Parameters: [1000]

            Absolute value of a computed expression::

                balance_change = movements.credit - movements.debit
                rows = movements.get_row([Builtins.Abs(balance_change)])
                # SELECT (ABS(("movements"."credit" - "movements"."debit")))
                # FROM "movements"

            Chained with arithmetic — stays numeric::

                padded = Builtins.Abs(movements.delta) + 1
                # SELECT ((ABS("movements"."delta")) + %s) FROM "movements"
                # Parameters: [1]

            Applied to a raw literal::

                rows = movements.get_row([
                    Builtins.Abs(-42),     # -> (ABS(%s)) with param -42  ->  42
                    Builtins.Abs(-3.14),   # -> (ABS(%s)) with param -3.14 -> 3.14
                ])
        """
        sql, p, dt, c = Builtins._normalize(value)
        result_dt = dt if dt in (int, float) else float
        return Builtins._make(f'(ABS({sql}))', p, result_dt, c)

    @staticmethod
    def Round(value):
        """Round a number to the nearest integer using PostgreSQL's ``ROUND()`` function.

        Generates an SQL ``ROUND(<expr>)`` expression. When called with a
        single argument, PostgreSQL rounds to zero decimal places and
        returns a ``NUMERIC`` value. This helper declares the result as
        ``float`` so Python-side arithmetic remains in the floating-point
        domain, matching SQLite's behaviour and Python's built-in ``round``.

        To round to a specific number of decimal places, use
        :meth:`Builtins.Func` with a two-argument ``ROUND`` — for example
        ``Builtins.Func('ROUND', users.price)`` handles the one-argument
        form, and the two-argument form can be constructed with a small
        helper or by wrapping the operand in an expression.

        Args:
            value: The expression whose value is rounded. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(ROUND(<expr>))`` and whose ``current_datatype`` is always
            ``float``.

        Example:
            Round a computed price to the nearest integer::

                from Ormophine.Postgresql import Driver, Builtins

                db       = Driver("localhost", 5432, "user", "pass", "store")
                products = db.products

                rows = products.get_row([
                    products.name,
                    Builtins.Round(products.price * 1.07),
                ])
                # SELECT "products"."name",
                #        (ROUND(("products"."price" * %s)))
                # FROM "products"
                # Parameters: [1.07]

            Round then cast to integer — the classic "nearest whole
            number" pattern::

                rows = products.get_row([
                    Builtins.Int(Builtins.Round(products.price)),
                ])
                # SELECT (CAST((ROUND("products"."price")) AS INTEGER))
                # FROM "products"

            Round an aggregate to two decimals — multiply, round, divide::

                rows = products.get_row([
                    Builtins.Round(Builtins.Avg(products.price) * 100) / 100,
                ])
                # SELECT ((ROUND(((AVG("products"."price")) * %s))) / %s)
                # FROM "products"
                # Parameters: [100, 100]

            Filter by rounded value::

                rows = products.get_row(
                    [products.name, products.price],
                    where=Builtins.Round(products.price) > 100,
                )
                # SELECT "products"."name", "products"."price"
                # FROM "products"
                # WHERE ((ROUND("products"."price")) > %s)
                # Parameters: [100]

            Chained with arithmetic — ``current_datatype`` is ``float``, so
            numeric operators stay numeric::

                padded = Builtins.Round(products.price) * 1.1
                # SELECT ((ROUND("products"."price")) * %s) FROM "products"
                # Parameters: [1.1]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(ROUND({sql}))', p, float, c)

    @staticmethod
    def Sign(value):
        """Return the sign of a number using PostgreSQL's ``SIGN()`` function.

        Generates a SQL ``SIGN(<expr>)`` expression. PostgreSQL returns:

        - ``-1`` if the value is negative
        - `` 0`` if the value is zero
        - `` 1`` if the value is positive

        This mirrors Python's ``(x > 0) - (x < 0)`` idiom and is useful for
        bucketing, sorting by direction, or normalising deltas.

        The result is always an ``INTEGER``, so it plays nicely with
        arithmetic, comparisons, and other numeric builtins.

        Args:
            value: The expression whose sign is computed. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(SIGN(<expr>))`` and whose ``current_datatype`` is ``int``.

        Example:
            Bucket movements by direction — up, flat, or down::

                from Ormophine.Postgresql import Driver, Builtins

                db        = Driver("localhost", 5432, "user", "pass", "analytics")
                movements = db.movements

                rows = movements.get_row([
                    movements.account_id,
                    movements.delta,
                    Builtins.Sign(movements.delta),
                ])
                # SELECT "movements"."account_id", "movements"."delta",
                #        (SIGN("movements"."delta"))
                # FROM "movements"
                # -> [(1, 250.0, 1), (1, -80.0, -1), (1, 0.0, 0), ...]

            Filter only the positive movements::

                rows = movements.get_row(
                    [movements.account_id, movements.delta],
                    where=Builtins.Sign(movements.delta) == 1,
                )
                # SELECT "movements"."account_id", "movements"."delta"
                # FROM "movements"
                # WHERE ((SIGN("movements"."delta")) = %s)
                # Parameters: [1]

            Sum signs to count net direction — positive means more ups
            than downs, and vice versa::

                net = Builtins.Sum(Builtins.Sign(movements.delta))
                rows = movements.get_row([movements.account_id, net])
                # SELECT "movements"."account_id",
                #        (SUM((SIGN("movements"."delta"))))
                # FROM "movements"

            Sign of a computed expression::

                range_mid = (movements.high + movements.low) / 2
                rows = movements.get_row([
                    movements.symbol,
                    Builtins.Sign(movements.close - range_mid),
                ])
                # SELECT "movements"."symbol",
                #        (SIGN(("movements"."close"
                #               - (("movements"."high" + "movements"."low") / %s)))))
                # FROM "movements"
                # Parameters: [2]

            Applied to a raw literal::

                rows = movements.get_row([
                    Builtins.Sign(-5),    # -> (SIGN(%s)) with param -5  -> -1
                    Builtins.Sign(0),     # -> (SIGN(%s)) with param 0   ->  0
                    Builtins.Sign(3.14),  # -> (SIGN(%s)) with param 3.14 -> 1
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(SIGN({sql}))', p, int, c)

    @staticmethod
    def Floor(value):
        """Round a number down to the nearest integer using PostgreSQL's ``FLOOR()``.

        Generates a ``FLOOR(<expr>)`` expression. For positive numbers this
        behaves like truncation toward zero; for negative numbers it rounds
        away from zero (``FLOOR(-1.5) = -2``, unlike ``CAST(-1.5 AS
        INTEGER)`` which gives ``-1``).

        The result is always an ``INTEGER`` when the input is a numeric type
        PostgreSQL can safely cast — but be aware that ``FLOOR`` of a
        ``NUMERIC`` value with a large magnitude returns a ``NUMERIC``
        that psycopg may deliver as ``decimal.Decimal``. The
        ``current_datatype`` is set to ``int`` because the value is always
        whole.

        Args:
            value: The expression to floor. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(FLOOR(<expr>))`` and whose ``current_datatype`` is ``int``.

        Example:
            Snap a price down to the whole dollar::

                from Ormophine.Postgresql import Driver, Builtins

                db       = Driver("localhost", 5432, "user", "pass", "store")
                products = db.products

                rows = products.get_row([
                    products.name,
                    products.price,
                    Builtins.Floor(products.price),
                ])
                # SELECT "products"."name", "products"."price",
                #        (FLOOR("products"."price"))
                # FROM "products"
                # -> [('Widget', 19.99, 19), ('Gadget', 24.50, 24), ...]

            Bucket scores into deciles::

                decile = Builtins.Floor(products.score / 10) * 10
                rows = products.get_row([decile, Builtins.Count('*')])
                # SELECT ((FLOOR(("products"."score" / %s))) * %s),
                #        (COUNT(*))
                # FROM "products"
                # Parameters: [10, 10]
                # -> [(0, 12), (10, 45), (20, 38), ...]

            Handle negative values correctly — FLOOR rounds down, not
            toward zero::

                rows = products.get_row([
                    Builtins.Floor(-1.5),   # -> -2
                    Builtins.Int(-1.5),     # -> -1 (truncation, not floor)
                ])

            Filter by floored value::

                rows = products.get_row(
                    [products.name, products.price],
                    where=Builtins.Floor(products.price) >= 20,
                )
                # SELECT "products"."name", "products"."price"
                # FROM "products"
                # WHERE ((FLOOR("products"."price")) >= %s)
                # Parameters: [20]

            Combined with arithmetic — stays numeric::

                discount = Builtins.Floor(products.price * 0.8)
                rows = products.get_row([products.name, discount])
                # SELECT "products"."name",
                #        (FLOOR(("products"."price" * %s)))
                # FROM "products"
                # Parameters: [0.8]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(FLOOR({sql}))', p, int, c)

    @staticmethod
    def Ceil(value):
        """Round a number up to the nearest integer using PostgreSQL's ``CEIL()``.

        Generates a ``CEIL(<expr>)`` expression. For positive numbers this
        rounds away from zero; for negative numbers it rounds toward zero
        (``CEIL(-1.5) = -1``, unlike ``FLOOR(-1.5) = -2``). This is the
        mirror image of :meth:`Floor`.

        The result is always an ``INTEGER`` when the input is a numeric type
        PostgreSQL can safely cast — the same caveat about large ``NUMERIC``
        inputs applies as for :meth:`Floor`. The ``current_datatype`` is
        declared as ``int`` because the value is always whole.

        Args:
            value: The expression to ceil. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CEIL(<expr>))`` and whose ``current_datatype`` is ``int``.

        Example:
            Snap a price up to the whole dollar — the common "don't lose
            money on rounding" pattern::

                from Ormophine.Postgresql import Driver, Builtins

                db       = Driver("localhost", 5432, "user", "pass", "store")
                products = db.products

                rows = products.get_row([
                    products.name,
                    products.price,
                    Builtins.Ceil(products.price),
                ])
                # SELECT "products"."name", "products"."price",
                #        (CEIL("products"."price"))
                # FROM "products"
                # -> [('Widget', 19.01, 20), ('Gadget', 24.00, 24), ...]

            Pagination — compute how many pages of 20 items each::

                page_count = Builtins.Ceil(Builtins.Count('*') / 20)
                rows = products.get_row([page_count])
                # SELECT (CEIL(((COUNT(*)) / %s))) FROM "products"
                # Parameters: [20]
                # -> [(13,)] if there are 250 products

            Bucket scores into the next higher 10::

                next_ten = Builtins.Ceil(products.score / 10) * 10
                rows = products.get_row([products.id, next_ten])
                # SELECT "products"."id",
                #        ((CEIL(("products"."score" / %s))) * %s)
                # FROM "products"
                # Parameters: [10, 10]

            Handle negative values correctly::

                rows = products.get_row([
                    Builtins.Ceil(-1.5),   # -> -1
                    Builtins.Int(-1.5),    # -> -1 (same here)
                ])

            Build a "bracketed price" pair from Floor and Ceil::

                low  = Builtins.Floor(products.price)
                high = Builtins.Ceil(products.price)
                rows = products.get_row([products.price, low, high])
                # SELECT "products"."price",
                #        (FLOOR("products"."price")),
                #        (CEIL("products"."price"))
                # FROM "products"
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CEIL({sql}))', p, int, c)

    @staticmethod
    def Sqrt(value):
        """Compute the square root of a number using PostgreSQL's ``SQRT()`` function.

        Generates a ``SQRT(<expr>)`` expression. The result is always a
        ``DOUBLE PRECISION`` (float) — even ``SQRT(4)`` returns ``2.0``,
        not ``2``. This is consistent with PostgreSQL's decision to keep
        math functions in the floating-point domain.

        Negative inputs raise a database error in PostgreSQL (unlike SQLite
        which silently returns ``NULL``). If your input might be negative,
        guard it — either by clamping with ``GREATEST(x, 0)`` via
        :meth:`Builtins.Func`, or by filtering rows with a plain comparison
        before the expression is evaluated.

        Args:
            value: The expression whose square root is computed. Supported
                types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(SQRT(<expr>))`` and whose ``current_datatype`` is always
            ``float``.

        Example:
            Euclidean distance — the standard ``sqrt(a² + b²)`` pattern::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "geometry")
                points = db.points

                distance_from_origin = Builtins.Sqrt(
                    points.x * points.x + points.y * points.y
                )
                rows = points.get_row([
                    points.id,
                    distance_from_origin,
                ])
                # SELECT "points"."id",
                #        (SQRT((("points"."x" * "points"."x")
                #               + ("points"."y" * "points"."y"))))
                # FROM "points"

            Standard deviation of a small set — square root of the mean
            squared deviation::

                mean   = Builtins.Avg(points.x)
                sq_dev = Builtins.Avg((points.x - mean) * (points.x - mean))
                stddev = Builtins.Sqrt(sq_dev)
                rows = points.get_row([stddev])
                # SELECT (SQRT((AVG((("points"."x" - (AVG("points"."x")))
                #                     * ("points"."x" - (AVG("points"."x"))))))))
                # FROM "points"

            Filter by magnitude — points more than 10 units from the origin::

                rows = points.get_row(
                    [points.id, points.x, points.y],
                    where=Builtins.Sqrt(
                        points.x * points.x + points.y * points.y
                    ) > 10,
                )
                # SELECT "points"."id", "points"."x", "points"."y"
                # FROM "points"
                # WHERE ((SQRT((("points"."x" * "points"."x")
                #               + ("points"."y" * "points"."y")))) > %s)
                # Parameters: [10]

            Combine with Round for display::

                pretty = Builtins.Round(
                    Builtins.Sqrt(points.x * points.x + points.y * points.y) * 100
                ) / 100
                rows = points.get_row([points.id, pretty])
                # SELECT "points"."id",
                #        ((ROUND((SQRT((("points"."x" * "points"."x")
                #                       + ("points"."y" * "points"."y"))))
                #                * %s)) / %s)
                # FROM "points"
                # Parameters: [100, 100]

            Applied to a raw literal::

                rows = points.get_row([
                    Builtins.Sqrt(16),    # -> (SQRT(%s)) with param 16 -> 4.0
                    Builtins.Sqrt(2),     # -> 1.4142135623730951
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(SQRT({sql}))', p, float, c)

    @staticmethod
    def Pow(base, exp):
        """Raise a base value to a power using PostgreSQL's ``POWER(a, b)`` function.

        Generates a ``POWER(<base>, <exp>)`` expression. This is the SQL
        analogue of Python's built-in ``pow(base, exp)`` and the ``**``
        operator. Both operands may be any expression — a column, another
        builtin, a raw literal, or a nested :class:`ColumnsOperation`.

        The result is always a ``DOUBLE PRECISION`` (float) — even
        ``POWER(2, 3)`` returns ``8.0``, not ``8``, because PostgreSQL
        keeps ``POWER`` in the floating-point domain.

        Args:
            base: The base expression. Any of the standard operand types:

                - :class:`ColumnsOperation`
                - :class:`Column`
                - A raw Python number

            exp: The exponent expression. Same accepted types as ``base``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(POWER(<base>, <exp>))`` and whose ``current_datatype`` is
            always ``float``. Parameters are concatenated left-to-right:
            first ``base``'s parameters, then ``exp``'s.

        Example:
            Compound interest — principal times ``(1 + rate)^years``::

                from Ormophine.Postgresql import Driver, Builtins

                db       = Driver("localhost", 5432, "user", "pass", "bank")
                accounts = db.accounts

                future_value = accounts.principal * Builtins.Pow(
                    1 + accounts.rate,
                    accounts.years,
                )
                rows = accounts.get_row([
                    accounts.id,
                    future_value,
                ])
                # SELECT "accounts"."id",
                #        ("accounts"."principal"
                #         * (POWER((%s + "accounts"."rate"),
                #                  "accounts"."years")))
                # FROM "accounts"
                # Parameters: [1]

            Square or cube a value::

                rows = accounts.get_row([
                    Builtins.Pow(accounts.principal, 2),   # square
                    Builtins.Pow(accounts.principal, 3),   # cube
                ])
                # SELECT (POWER("accounts"."principal", %s)),
                #        (POWER("accounts"."principal", %s))
                # FROM "accounts"
                # Parameters: [2, 3]

            Square root via fractional exponent — equivalent to
            :meth:`Sqrt`::

                rows = accounts.get_row([
                    Builtins.Pow(accounts.principal, 0.5),
                ])
                # SELECT (POWER("accounts"."principal", %s))
                # FROM "accounts"
                # Parameters: [0.5]

            Inverse power — ``x⁻¹`` equals ``1/x``::

                rows = accounts.get_row([
                    Builtins.Pow(accounts.principal, -1),
                ])
                # SELECT (POWER("accounts"."principal", %s))
                # FROM "accounts"
                # Parameters: [-1]

            Distance squared without the square root — useful for
            comparisons where you don't need the exact distance::

                rows = accounts.get_row(
                    [accounts.id],
                    where=Builtins.Pow(accounts.x, 2)
                        + Builtins.Pow(accounts.y, 2) > 100,
                )
                # SELECT "accounts"."id" FROM "accounts"
                # WHERE (((POWER("accounts"."x", %s))
                #          + (POWER("accounts"."y", %s))) > %s)
                # Parameters: [2, 2, 100]

            Combine with Round for display::

                pretty = Builtins.Round(
                    Builtins.Pow(accounts.principal, 1.05) * 100
                ) / 100
                rows = accounts.get_row([accounts.id, pretty])
                # SELECT "accounts"."id",
                #        ((ROUND((POWER("accounts"."principal", %s) * %s))) / %s)
                # FROM "accounts"
                # Parameters: [1.05, 100, 100]

            Chained with arithmetic — stays numeric::

                doubled = Builtins.Pow(accounts.principal, 2) * 2
                # SELECT ((POWER("accounts"."principal", %s)) * %s)
                # FROM "accounts"
                # Parameters: [2, 2]
        """
        s1, p1, _, c = Builtins._normalize(base)
        s2, p2, _, _ = Builtins._normalize(exp)
        return Builtins._make(f'(POWER({s1}, {s2}))', p1 + p2, float, c)

    @staticmethod
    def Total(value):
        """Sum a set of values, returning zero instead of NULL for empty groups.

        Generates a ``COALESCE(SUM(<expr>), 0)`` expression. This is the
        PostgreSQL equivalent of SQLite's ``TOTAL()``: it behaves like
        :meth:`Sum` with one critical difference — **empty groups return
        ``0`` instead of ``NULL``**. This makes it the safer choice when
        you need a numeric result even when no rows match, or when the
        aggregated column contains only NULLs:

        .. code-block:: sql

            SUM  of (NULL, NULL) -> NULL
            COALESCE(SUM(...), 0) of (NULL, NULL) -> 0

            SUM  of ()          -> NULL
            COALESCE(SUM(...), 0) of ()          -> 0

        The result is declared as ``float`` so downstream arithmetic stays
        in the numeric domain and Python never has to distinguish between
        ``None`` and ``0`` after the fetch.

        Args:
            value: The expression to sum. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(COALESCE(SUM(<expr>), 0))`` and whose ``current_datatype``
            is always ``float``.

        Example:
            Sum with a guaranteed numeric result — no ``None`` to guard
            against in Python::

                from Ormophine.Postgresql import Driver, Builtins

                db       = Driver("localhost", 5432, "user", "pass", "store")
                products = db.products

                total = Builtins.Total(products.price)
                rows = products.get_row([total])
                # SELECT (COALESCE(SUM("products"."price"), 0))
                # FROM "products"
                # -> [(1234.56,)] even if the table is empty

            Compare with SUM to see the difference::

                rows = products.get_row([
                    Builtins.Sum(products.price),     # -> None when empty
                    Builtins.Total(products.price),   # -> 0.0 when empty
                ])
                # SELECT (SUM("products"."price")),
                #        (COALESCE(SUM("products"."price"), 0))
                # FROM "products"
                # -> [(None, 0.0)] on an empty table

            Sum a nullable column — the SUM ignores NULLs, and if every
            row is NULL, the COALESCE returns 0::

                rows = products.get_row([
                    Builtins.Total(products.discount),   # NULLs -> 0
                ])
                # SELECT (COALESCE(SUM("products"."discount"), 0))
                # FROM "products"

            Safety-check division — Total never produces NULL, so the
            denominator in a ratio is always numeric. Note that SQL still
            raises on division by zero, so guard against that separately::

                ratio = (Builtins.Total(products.revenue)
                         / Builtins.Func('NULLIF', Builtins.Total(products.cost)))
                rows = products.get_row([ratio])
                # SELECT ((COALESCE(SUM("products"."revenue"), 0))
                #         / (NULLIF((COALESCE(SUM("products"."cost"), 0)), %s)))
                # FROM "products"
                # Parameters: [0]

            Conditional aggregate — sum only the paid products::

                paid = Builtins.Total(
                    Builtins.IIf(products.paid == True,
                                 products.price,
                                 0)
                )
                rows = products.get_row([paid])
                # SELECT (COALESCE(SUM((CASE WHEN ("products"."paid" = %s)
                #                              THEN "products"."price"
                #                              ELSE %s END)), 0))
                # FROM "products"
                # Parameters: [True, 0]

            Chained arithmetic — stays numeric::

                padded = Builtins.Total(products.price) + 100
                # SELECT ((COALESCE(SUM("products"."price"), 0)) + %s)
                # FROM "products"
                # Parameters: [100]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(COALESCE(SUM({sql}), 0))', p, float, c)

    @staticmethod
    def GroupConcat(value, sep=','):
        """Concatenate values from multiple rows into a single string.

        Generates a ``STRING_AGG(<expr>, <sep>)`` expression. This is the
        SQL analogue of Python's ``','.join(...)`` applied to a column:
        every non-NULL value in the group is converted to text, joined
        with the separator, and returned as a single TEXT value.

        The separator is bound as a ``%s`` parameter, so it is safe to
        pass user-supplied strings. Values are aggregated in an
        unspecified order by PostgreSQL unless you add an explicit
        ``ORDER BY`` to the ``STRING_AGG`` call, which this helper does
        not do — if deterministic ordering matters, use :meth:`Func` with
        the three-argument form: ``Func('STRING_AGG', col)`` and extend
        the SQL yourself.

        The result is always a ``TEXT`` string, so ``+`` chained after it
        produces concatenation (``||``) rather than arithmetic addition.

        Args:
            value: The expression whose values are concatenated. Supported
                types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder.

            sep (str, optional): The separator string inserted between
                values. Bound as a parameter. Defaults to ``','``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(STRING_AGG(<expr>, %s))`` and whose ``current_datatype`` is
            always ``str``. Parameters are ``value's_parameters + [sep]``.

        Example:
            Comma-separated list of all usernames::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([Builtins.GroupConcat(users.username)])
                # SELECT (STRING_AGG("users"."username", %s)) FROM "users"
                # Parameters: [',']
                # -> [('alice,bob,carol,dave',)]

            Custom separator — a pipe::

                rows = users.get_row([
                    Builtins.GroupConcat(users.username, ' | ')
                ])
                # SELECT (STRING_AGG("users"."username", %s)) FROM "users"
                # Parameters: [' | ']
                # -> [('alice | bob | carol',)]

            Emails for a specific domain — combine with a filter::

                rows = users.get_row(
                    [Builtins.GroupConcat(users.email, '; ')],
                    where=users.email.endswith('@example.com'),
                )
                # SELECT (STRING_AGG("users"."email", %s)) FROM "users"
                # WHERE ("users"."email" LIKE '%%' || %s)
                # Parameters: ['; ', '@example.com']

            Build a display string per group — combine with a grouped
            query by fetching the raw rows and doing the grouping in
            Python, since the ORM has no GROUP BY helper::

                rows = users.get_row([
                    users.department,
                    users.username,
                ])
                from collections import defaultdict
                grouped = defaultdict(list)
                for dept, username in rows:
                    grouped[dept].append(username)
                # {'Engineering': ['alice', 'bob'], 'Sales': ['carol'], ...}
                # then: ', '.join(names) in Python

            Concatenate a transformed column — upper-case usernames joined
            by commas::

                rows = users.get_row([
                    Builtins.GroupConcat(Builtins.Upper(users.username)),
                ])
                # SELECT (STRING_AGG((UPPER("users"."username")), %s))
                # FROM "users"
                # Parameters: [',']
                # -> [('ALICE,BOB,CAROL',)]

            Chained with string methods — the result is TEXT::

                expr = Builtins.GroupConcat(users.username)
                rows = users.get_row([expr.add_first('Users: ')])
                # SELECT (%s || (STRING_AGG("users"."username", %s)))
                # FROM "users"
                # Parameters: ['Users: ', ',']
                # -> [('Users: alice,bob,carol',)]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(STRING_AGG({sql}, %s))', p + [sep], str, c)

    @staticmethod
    def Int(value):
        """Convert a value to an integer using ``CAST(x AS INTEGER)``.

        This is the SQL equivalent of Python's ``int()``. Generates a
        ``CAST(<expr> AS INTEGER)`` expression. PostgreSQL's conversion
        rules apply: text that looks like an integer is parsed, REAL is
        truncated toward zero (not rounded), and NULL stays NULL. If the
        input cannot be coerced, PostgreSQL raises an error rather than
        returning NULL.

        The result is always an ``INTEGER``, so arithmetic chains and
        comparisons behave as expected even when the original column was
        declared as TEXT or a floating-point type.

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS INTEGER))`` and whose ``current_datatype`` is
            always ``int``.

        Example:
            Force a text column to be treated as an integer::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "app")
                events = db.events

                rows = events.get_row([
                    events.id,
                    Builtins.Int(events.payload),
                ])
                # SELECT "events"."id", (CAST("events"."payload" AS INTEGER))
                # FROM "events"

            Compare a text column numerically::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Int(events.amount_text) > 1000,
                )
                # SELECT "events"."id" FROM "events"
                # WHERE ((CAST("events"."amount_text" AS INTEGER)) > %s)
                # Parameters: [1000]

            Truncate a REAL toward zero — note this is *not* rounding::

                rows = events.get_row([
                    Builtins.Int(events.temperature),   # 23.7 -> 23
                    Builtins.Round(events.temperature), # 23.7 -> 24.0
                ])
                # SELECT (CAST("events"."temperature" AS INTEGER)),
                #        (ROUND("events"."temperature"))
                # FROM "events"

            Combine with arithmetic — stays numeric::

                doubled = Builtins.Int(events.count) * 2
                # SELECT ((CAST("events"."count" AS INTEGER)) * %s)
                # FROM "events"
                # Parameters: [2]

            Used inside an aggregate::

                rows = events.get_row([
                    Builtins.Sum(Builtins.Int(events.payload)),
                ])
                # SELECT (SUM((CAST("events"."payload" AS INTEGER))))
                # FROM "events"
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS INTEGER))', p, int, c)

    @staticmethod
    def Float(value):
        """Convert a value to a floating-point number using ``CAST(x AS DOUBLE PRECISION)``.

        This is the SQL equivalent of Python's ``float()``. Generates a
        ``CAST(<expr> AS DOUBLE PRECISION)`` expression. PostgreSQL's
        conversion rules apply: text that looks like a number is parsed,
        INTEGER is widened to DOUBLE PRECISION, and NULL stays NULL.
        Unlike ``CAST AS INTEGER``, this target type handles both integer
        and fractional inputs without truncation.

        The result is always a ``DOUBLE PRECISION`` (Python ``float``), so
        any chained arithmetic naturally stays in the floating-point domain
        — which is important because PostgreSQL's integer division returns
        an integer (``5 / 2 = 2``), while floating-point division returns
        the expected fractional result (``5.0 / 2 = 2.5``).

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS DOUBLE PRECISION))`` and whose
            ``current_datatype`` is always ``float``.

        Example:
            Force integer division to produce a real result::

                from Ormophine.Postgresql import Driver, Builtins

                db         = Driver("localhost", 5432, "user", "pass", "analytics")
                statistics = db.statistics

                ratio = (Builtins.Float(statistics.successes)
                         / statistics.attempts)
                rows = statistics.get_row([ratio])
                # SELECT ((CAST("statistics"."successes" AS DOUBLE PRECISION))
                #         / "statistics"."attempts")
                # FROM "statistics"
                # -> [(0.9732,)]

            Without the cast, integer division silently truncates::

                wrong = statistics.successes / statistics.attempts
                rows = statistics.get_row([wrong])
                # SELECT ("statistics"."successes" / "statistics"."attempts")
                # FROM "statistics"
                # -> [(0,)] for 9732 successes out of 10000 attempts

            Parse a text column as a number and filter on it::

                rows = statistics.get_row(
                    [statistics.id,
                     Builtins.Float(statistics.amount_text)],
                    where=Builtins.Float(statistics.amount_text) >= 99.5,
                )
                # SELECT "statistics"."id",
                #        (CAST("statistics"."amount_text" AS DOUBLE PRECISION))
                # FROM "statistics"
                # WHERE ((CAST("statistics"."amount_text" AS DOUBLE PRECISION)) >= %s)
                # Parameters: [99.5]

            Widen an integer column before averaging — this is what
            :meth:`Avg` already does internally::

                rows = statistics.get_row([
                    Builtins.Avg(Builtins.Float(statistics.count)),
                ])
                # SELECT (AVG((CAST("statistics"."count" AS DOUBLE PRECISION))))
                # FROM "statistics"

            Multiply a converted value by a literal::

                scaled = Builtins.Float(statistics.score) * 1.5
                rows = statistics.get_row([scaled])
                # SELECT ((CAST("statistics"."score" AS DOUBLE PRECISION)) * %s)
                # FROM "statistics"
                # Parameters: [1.5]

            Applied to a raw literal::

                rows = statistics.get_row([
                    Builtins.Float('3.14'),   # -> (CAST(%s AS DOUBLE PRECISION))
                    Builtins.Float(42),       # -> 42.0
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS DOUBLE PRECISION))', p, float, c)

    @staticmethod
    def Str(value):
        """Convert a value to text using ``CAST(x AS TEXT)``.

        This is the SQL equivalent of Python's ``str()``. Generates a
        ``CAST(<expr> AS TEXT)`` expression. PostgreSQL's conversion rules
        apply: numbers are formatted as their decimal representation,
        booleans become ``'t'`` / ``'f'``, dates and timestamps use the
        configured ``DateStyle`` (usually ISO 8601), and NULL stays NULL.

        The result is always a ``TEXT`` (Python ``str``), so chaining with
        ``+`` produces string concatenation (``||``) rather than arithmetic
        addition. This is essential when you need to mix numeric columns
        into text — otherwise PostgreSQL will refuse the operation, since
        it has no implicit int-to-text coercion.

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS TEXT))`` and whose ``current_datatype`` is
            always ``str``.

        Example:
            Safely concatenate a numeric column with text. Without the
            cast, PostgreSQL raises ``operator does not exist: integer
            || unknown``::

                from Ormophine.Postgresql import Driver, Builtins

                db        = Driver("localhost", 5432, "user", "pass", "company")
                employees = db.employees

                label = Builtins.Str(employees.salary) + ' USD'
                rows = employees.get_row([employees.name, label])
                # SELECT "employees"."name",
                #        ((CAST("employees"."salary" AS TEXT)) || %s)
                # FROM "employees"
                # Parameters: [' USD']
                # -> [('Alice', '75000 USD'), ...]

            Without Builtins.Str — this will error at execution time
            because PostgreSQL refuses to concatenate integer and text::

                wrong = employees.salary + ' USD'
                rows = employees.get_row([employees.name, wrong])
                # SELECT "employees"."name",
                #        ("employees"."salary" || %s)
                # FROM "employees"
                # ERROR: operator does not exist: integer || text

            Format an integer id for display::

                rows = employees.get_row([
                    Builtins.Str(employees.id).add_first('EMP-'),
                ])
                # SELECT (%s || (CAST("employees"."id" AS TEXT)))
                # FROM "employees"
                # Parameters: ['EMP-']
                # -> [('EMP-42',), ...]

            Use with string methods — ``add_end`` chains as ``||``::

                rows = employees.get_row([
                    Builtins.Str(employees.salary).add_end(' gross'),
                ])
                # SELECT ((CAST("employees"."salary" AS TEXT)) || %s)
                # FROM "employees"
                # Parameters: [' gross']

            Inside a LIKE pattern — match the leading digit of an integer
            id::

                rows = employees.get_row(
                    [employees.id],
                    where=Builtins.Str(employees.id).startswith('1'),
                )
                # SELECT "employees"."id" FROM "employees"
                # WHERE ((CAST("employees"."id" AS TEXT)) LIKE %s || '%%')
                # Parameters: ['1']

            Applied to a raw literal::

                rows = employees.get_row([
                    Builtins.Str(3.14),    # -> (CAST(%s AS TEXT)) -> '3.14'
                    Builtins.Str(True),    # -> (CAST(%s AS TEXT)) -> 'true'
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS TEXT))', p, str, c)

    @staticmethod
    def Bool(value):
        """Convert a value to a boolean using ``CAST(x AS BOOLEAN)``.

        PostgreSQL has a native ``BOOLEAN`` type, unlike SQLite. This
        helper mirrors Python's ``bool()`` by emitting a
        ``CAST(<expr> AS BOOLEAN)`` expression. PostgreSQL's conversion
        rules apply: text values ``'t'``, ``'true'``, ``'yes'``, ``'on'``,
        ``'1'`` become TRUE; ``'f'``, ``'false'``, ``'no'``, ``'off'``,
        ``'0'`` become FALSE; integers ``0`` become FALSE and any non-zero
        integer becomes TRUE.

        The result is a real Python ``bool`` (``True`` / ``False``), so it
        can be compared directly to Python booleans in the ORM's filter
        expressions.

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value (``True``, ``False``, ``0``, ``1``, or
                  any coercible value) — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS BOOLEAN))`` and whose ``current_datatype``
            is ``bool``.

        Example:
            Normalise a status column that stores mixed values::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                normalised = Builtins.Bool(users.is_active)
                rows = users.get_row([users.id, normalised])
                # SELECT "users"."id",
                #        (CAST("users"."is_active" AS BOOLEAN))
                # FROM "users"
                # -> [(1, True), (2, False), ...]

            Compare a computed condition against a boolean literal::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Bool(users.age >= 18) == True,
                )
                # SELECT "users"."id" FROM "users"
                # WHERE ((CAST(("users"."age" >= %s) AS BOOLEAN)) = %s)
                # Parameters: [18, True]

            Coerce a raw literal — useful when the surrounding API expects
            a ColumnsOperation-shaped object::

                rows = users.get_row([
                    Builtins.Bool(True),    # -> (CAST(%s AS BOOLEAN))
                    Builtins.Bool(False),   # -> (CAST(%s AS BOOLEAN))
                ])

            Use in a CASE expression — a boolean column drives the branch::

                status = Builtins.IIf(
                    Builtins.Bool(users.is_active),
                    'active',
                    'inactive',
                )
                rows = users.get_row([users.name, status])
                # SELECT "users"."name",
                #        (CASE WHEN (CAST("users"."is_active" AS BOOLEAN))
                #              THEN %s ELSE %s END)
                # FROM "users"
                # Parameters: ['active', 'inactive']

            Count active rows via SUM of the boolean cast — PostgreSQL
            promotes boolean to integer in arithmetic::

                active_count = Builtins.Sum(
                    Builtins.IIf(Builtins.Bool(users.is_active), 1, 0)
                )
                rows = users.get_row([active_count])
                # SELECT (SUM((CASE WHEN
                #               (CAST("users"."is_active" AS BOOLEAN))
                #               THEN %s ELSE %s END)))
                # FROM "users"
                # Parameters: [1, 0]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS BOOLEAN))', p, bool, c)

    @staticmethod
    def TypeOf(value):
        """Return the PostgreSQL internal type name of a value using ``PG_TYPEOF()``.

        Generates a ``PG_TYPEOF(<expr>)`` expression. PostgreSQL returns
        the internal type name as a ``TEXT`` string — for example ``'int4'``
        for a regular ``integer``, ``'int8'`` for ``bigint``, ``'float8'``
        for ``double precision``, ``'text'`` for ``text``, ``'varchar'``
        for ``character varying``, ``'bool'`` for ``boolean``, ``'numeric'``
        for ``numeric``, ``'timestamptz'`` for ``timestamp with time zone``,
        ``'date'`` for ``date``, ``'jsonb'`` for ``jsonb``, ``'uuid'`` for
        ``uuid``.

        This is the closest SQL analogue of Python's ``type()`` for
        debugging and introspection. Because PostgreSQL is a strongly typed
        system, the result is *much* more useful than SQLite's ``TYPEOF`` —
        SQLite only returns the five storage classes, whereas PostgreSQL
        returns the actual declared type name.

        The result is always a ``TEXT`` string, so it plays nicely with
        ``.like``, ``.startswith``, ``.In``, and other text-oriented chains.

        Args:
            value: The expression whose storage class is inspected.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(PG_TYPEOF(<expr>))`` and whose ``current_datatype`` is always
            ``str``.

        Example:
            Audit a column that stores mixed types::

                from Ormophine.Postgresql import Driver, Builtins

                db      = Driver("localhost", 5432, "user", "pass", "app")
                records = db.records

                rows = records.get_row([
                    records.id,
                    Builtins.TypeOf(records.payload),
                ])
                # SELECT "records"."id", (PG_TYPEOF("records"."payload"))
                # FROM "records"
                # -> [(1, 'text'), (2, 'int4'), (3, 'jsonb'), ...]

            Filter only the rows that stored real numbers::

                rows = records.get_row(
                    [records.id, records.payload],
                    where=Builtins.TypeOf(records.payload) == 'float8',
                )
                # SELECT "records"."id", "records"."payload"
                # FROM "records"
                # WHERE ((PG_TYPEOF("records"."payload")) = %s)
                # Parameters: ['float8']

            Group records by storage class — count in Python::

                rows = records.get_row([Builtins.TypeOf(records.payload)])
                from collections import Counter
                histogram = Counter(t for (t,) in rows)
                # {'text': 120, 'int4': 45, 'float8': 18, 'jsonb': 3}

            Combine with a text-method chain::

                rows = records.get_row(
                    [records.id],
                    where=Builtins.TypeOf(records.payload).In(
                        ['int4', 'int8', 'float8']
                    ),
                )
                # SELECT "records"."id" FROM "records"
                # WHERE ((PG_TYPEOF("records"."payload")) IN (%s, %s, %s))
                # Parameters: ['int4', 'int8', 'float8']

            Inspect a raw literal — note that literals are typed by
            PostgreSQL's own rules, so ``42`` is ``int4`` and ``3.14`` is
            ``numeric``, not ``float8``::

                rows = records.get_row([
                    Builtins.TypeOf(42),      # -> 'int4'
                    Builtins.TypeOf(3.14),    # -> 'numeric'
                    Builtins.TypeOf('hello'), # -> 'text'
                    Builtins.TypeOf(None),    # -> 'unknown'
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(PG_TYPEOF({sql}))', p, str, c)

    @staticmethod
    def Upper(value):
        """Convert a text value to uppercase using PostgreSQL's ``UPPER()``.

        Generates an ``UPPER(<expr>)`` expression. The conversion is
        locale-sensitive and follows the database's collation rules for
        non-ASCII characters.

        This is the SQL equivalent of Python's ``str.upper()``. The result
        is always a ``TEXT`` string, so ``+`` chained after it produces
        concatenation (``||``) rather than arithmetic addition.

        The returned object is a :class:`ColumnsOperation`, so all string
        methods (``.contains``, ``.startswith``, ``.like``, ``.add_end``,
        slicing) remain available on it.

        Args:
            value: The expression whose text is uppercased. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(UPPER(<expr>))`` and whose ``current_datatype`` is always
            ``str``.

        Example:
            Case-insensitive comparison — the classic ``upper = upper``
            pattern::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row(
                    [users.id, users.name],
                    where=Builtins.Upper(users.name) == 'ALICE',
                )
                # SELECT "users"."id", "users"."name" FROM "users"
                # WHERE ((UPPER("users"."name")) = %s)
                # Parameters: ['ALICE']

            Case-insensitive with a raw literal on the right — same as
            above, written the other way round::

                rows = users.get_row(
                    [users.id],
                    where=users.name.upper() == 'ALICE',
                )
                # SELECT "users"."id" FROM "users"
                # WHERE ((UPPER("users"."name")) = %s)
                # Parameters: ['ALICE']

            As a SELECT column — display the uppercase name alongside the
            original::

                rows = users.get_row([
                    users.name,
                    Builtins.Upper(users.name),
                ])
                # SELECT "users"."name", (UPPER("users"."name")) FROM "users"
                # -> [('Alice', 'ALICE'), ('Bob', 'BOB'), ...]

            Chain with string methods — the result is TEXT::

                expr = Builtins.Upper(users.name).add_end(' (verified)')
                rows = users.get_row([users.name, expr])
                # SELECT "users"."name",
                #        ((UPPER("users"."name")) || %s)
                # FROM "users"
                # Parameters: [' (verified)']

            Case-insensitive sort — order by the uppercase version::

                rows = users.get_row(
                    [users.name],
                    order_by=Builtins.Upper(users.name),
                )
                # SELECT "users"."name" FROM "users"
                # ORDER BY (UPPER("users"."name"))

            Inside a LIKE pattern::

                rows = users.get_row(
                    [users.name],
                    where=Builtins.Upper(users.name).startswith('A'),
                )
                # SELECT "users"."name" FROM "users"
                # WHERE ((UPPER("users"."name")) LIKE %s || '%%')
                # Parameters: ['A']

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Upper('hello'),   # -> (UPPER(%s)) -> 'HELLO'
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(UPPER({sql}))', p, str, c)

    @staticmethod
    def Lower(value):
        """Convert a text value to lowercase using PostgreSQL's ``LOWER()``.

        Generates a ``LOWER(<expr>)`` expression. The conversion is
        locale-sensitive and follows the database's collation rules for
        non-ASCII characters.

        This is the SQL equivalent of Python's ``str.lower()``. The result
        is always a ``TEXT`` string, so ``+`` chained after it produces
        concatenation (``||``) rather than arithmetic addition.

        The returned object is a :class:`ColumnsOperation`, so all string
        methods remain available on it.

        Args:
            value: The expression whose text is lowercased. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(LOWER(<expr>))`` and whose ``current_datatype`` is always
            ``str``.

        Example:
            Case-insensitive email lookup — a very common pattern::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row(
                    [users.id, users.name],
                    where=Builtins.Lower(users.email) == 'alice@example.com',
                )
                # SELECT "users"."id", "users"."name" FROM "users"
                # WHERE ((LOWER("users"."email")) = %s)
                # Parameters: ['alice@example.com']

            Normalise user input before storing — a common update pattern::

                users.update(
                    update={users.email: Builtins.Lower(users.email)},
                    where=users.email != Builtins.Lower(users.email),
                )
                # UPDATE "users" SET "email" = (LOWER("users"."email"))
                # WHERE ("users"."email" != (LOWER("users"."email")));

            As a SELECT column — display the lowercase email alongside the
            original::

                rows = users.get_row([
                    users.email,
                    Builtins.Lower(users.email),
                ])
                # SELECT "users"."email", (LOWER("users"."email"))
                # FROM "users"

            Build a slug — lowercase and replace spaces::

                slug = Builtins.Lower(users.name).replace(' ', '-')
                rows = users.get_row([users.id, slug])
                # SELECT "users"."id",
                #        (REPLACE((LOWER("users"."name")), %s, %s))
                # FROM "users"
                # Parameters: [' ', '-']

            Combine with Upper for a case-folded comparison of two columns::

                same_ignoring_case = (
                    Builtins.Lower(users.first_name)
                    == Builtins.Lower(users.nickname)
                )
                rows = users.get_row([users.id], where=same_ignoring_case)
                # SELECT "users"."id" FROM "users"
                # WHERE ((LOWER("users"."first_name"))
                #        = (LOWER("users"."nickname")))

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Lower('HELLO'),   # -> (LOWER(%s)) -> 'hello'
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(LOWER({sql}))', p, str, c)

    @staticmethod
    def Trim(value):
        """Strip whitespace from both ends of a text value using ``TRIM()``.

        Generates a ``TRIM(<expr>)`` expression. By default, ``TRIM``
        removes spaces only — unlike Python's ``str.strip()`` which also
        removes tabs, newlines, and other whitespace. If you need to strip
        a specific set of characters, use :meth:`Builtins.Func` with the
        two-argument form, or chain the ``Column.strip`` method which
        already supports a ``chars`` argument.

        The result is always a ``TEXT`` string, so ``+`` chained after it
        produces concatenation (``||``) rather than arithmetic addition.

        Args:
            value: The expression whose text is trimmed. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(TRIM(<expr>))`` and whose ``current_datatype`` is always
            ``str``.

        Example:
            Clean up user-supplied input before storing::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                users.insert({
                    users.username: '  alice  ',
                })
                # Stored as-is with the padding

                users.update(
                    update={users.username: Builtins.Trim(users.username)},
                    where=users.username != Builtins.Trim(users.username),
                )
                # UPDATE "users" SET "username" = (TRIM("users"."username"))
                # WHERE ("users"."username" != (TRIM("users"."username")));

            Filter on trimmed values — match against a clean literal::

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.Trim(users.username) == 'alice',
                )
                # SELECT "users"."id", "users"."username" FROM "users"
                # WHERE ((TRIM("users"."username")) = %s)
                # Parameters: ['alice']

            Chain with other string methods — the result is TEXT::

                expr = Builtins.Trim(users.name).add_end('!')
                rows = users.get_row([expr])
                # SELECT ((TRIM("users"."name")) || %s) FROM "users"
                # Parameters: ['!']

            Chain with ``Upper`` for a full normalisation::

                clean = Builtins.Upper(Builtins.Trim(users.username))
                rows = users.get_row([users.id, clean])
                # SELECT "users"."id",
                #        (UPPER((TRIM("users"."username"))))
                # FROM "users"
                # -> [(1, 'ALICE'), (2, 'BOB'), ...]

            Sort ignoring leading/trailing whitespace::

                rows = users.get_row(
                    [users.username],
                    order_by=Builtins.Trim(users.username),
                )
                # SELECT "users"."username" FROM "users"
                # ORDER BY (TRIM("users"."username"))

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Trim('  hello  '),   # -> (TRIM(%s)) -> 'hello'
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(TRIM({sql}))', p, str, c)

    @staticmethod
    def Capitalize(value):
        """Capitalise a text value — first character upper, rest lower.

        PostgreSQL has no native ``INITCAP``-like two-step for this exact
        behaviour when applied to a *single* string (``INITCAP`` capitalises
        every word). Instead, this helper composes the Python-equivalent
        behaviour from two SQL expressions:

        .. code-block:: sql

            UPPER(SUBSTRING(<expr>, 1, 1)) || LOWER(SUBSTRING(<expr>, 2))

        The result is a new string with the first character converted to
        uppercase and every subsequent character converted to lowercase.
        This matches Python's ``str.capitalize()`` behaviour exactly for
        the common case.

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
                - A raw Python string — bound as a ``%s`` placeholder (also
                  duplicated).

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(UPPER(SUBSTRING(<expr>, 1, 1)) || LOWER(SUBSTRING(<expr>, 2)))``
            and whose ``current_datatype`` is always ``str``.

        Example:
            Title-case names for display — even if the stored values are
            all-uppercase or mixed-case::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([
                    users.id,
                    Builtins.Capitalize(users.name),
                ])
                # SELECT "users"."id",
                #        (UPPER(SUBSTRING("users"."name", 1, 1))
                #         || LOWER(SUBSTRING("users"."name", 2)))
                # FROM "users"
                # -> [(1, 'Alice'), (2, 'Bob'), (3, 'Carol'), ...]
                #    even if the stored values were 'ALICE', 'bob', 'cAROL'

            Sort case-insensitively by name::

                rows = users.get_row(
                    [users.name],
                    order_by=Builtins.Capitalize(users.name),
                )
                # SELECT "users"."name" FROM "users"
                # ORDER BY (UPPER(SUBSTRING("users"."name", 1, 1))
                #           || LOWER(SUBSTRING("users"."name", 2)))

            Normalise before display::

                rows = users.get_row([
                    users.id,
                    Builtins.Capitalize(users.first_name).add_end(' ').add_end(
                        Builtins.Capitalize(users.last_name)
                    ),
                ])
                # SELECT "users"."id",
                #        ((UPPER(SUBSTRING("users"."first_name", 1, 1))
                #          || LOWER(SUBSTRING("users"."first_name", 2)))
                #         || %s
                #         || (UPPER(SUBSTRING("users"."last_name", 1, 1))
                #             || LOWER(SUBSTRING("users"."last_name", 2))))
                # FROM "users"
                # Parameters: [' ']

            Chain with other string builtins::

                expr = Builtins.Capitalize(users.name).add_end('!')
                rows = users.get_row([expr])
                # -> 'Alice!', 'Bob!', ...

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Capitalize('hELLO wORLD'),   # -> 'Hello world'
                ])
                # SQL: (UPPER(SUBSTRING(%s, 1, 1))
                #       || LOWER(SUBSTRING(%s, 2)))
                # Parameters: ['hELLO wORLD', 'hELLO wORLD']

            Combine with ``Trim`` to clean up and capitalise in one go::

                clean = Builtins.Capitalize(Builtins.Trim(users.name))
                rows = users.get_row([clean])
                # SELECT (UPPER(SUBSTRING((TRIM("users"."name")), 1, 1))
                #         || LOWER(SUBSTRING((TRIM("users"."name")), 2)))
                # FROM "users"
        """
        sql, p, _, c = Builtins._normalize(value)
        inner = f'UPPER(SUBSTRING({sql}, 1, 1)) || LOWER(SUBSTRING({sql}, 2))'
        return Builtins._make(f'({inner})', p, str, c)

    @staticmethod
    def Find(value, sub):
        """Locate a substring within a value using PostgreSQL's ``STRPOS()`` function.

        Generates a ``STRPOS(<value>, <sub>)`` expression. Returns the
        1-based position of the first occurrence of ``sub`` inside
        ``value``, or ``0`` if ``sub`` is not present.

        .. warning::
            SQLite's ``INSTR`` and PostgreSQL's ``STRPOS`` have the same
            semantics, but both differ from Python's ``str.find`` in two
            ways that routinely trip people up:

            ==================  =========  =========
            Behaviour           Python     SQL
            ==================  =========  =========
            Index of first char    0          1
            "Not found" value     -1          0
            ==================  =========  =========

            If you need strict Python semantics — e.g. so that
            ``Find(col, 'x') >= 0`` means "contains x" — add ``- 1`` to the
            result at the call site::

                py_find = Builtins.Find(users.name, 'x') - 1
                # py_find == -1 when not found, == 0 when found at position 0

            For a plain "does it contain this" check, :meth:`Column.contains`
            is usually the better choice.

        Args:
            value: The haystack. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder.

            sub: The needle. Same accepted types as ``value``. Usually a
                plain string literal, but any expression is allowed.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(STRPOS(<value>, <sub>))`` and whose ``current_datatype`` is
            ``int``. Parameters are concatenated left-to-right: first the
            haystack's parameters, then the needle's.

        Example:
            Find the position of a delimiter inside a text column::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "app")
                emails = db.emails

                at_pos = Builtins.Find(emails.address, '@')
                rows = emails.get_row([
                    emails.id,
                    emails.address,
                    at_pos,
                ])
                # SELECT "emails"."id", "emails"."address",
                #        (STRPOS("emails"."address", %s))
                # FROM "emails"
                # Parameters: ['@']
                # -> [(1, 'alice@example.com', 6),
                #     (2, 'bob@x.io', 4), ...]

            Detect the presence of a substring — use ``> 0`` because
            PostgreSQL returns 0 (not -1) when the needle is missing::

                rows = emails.get_row(
                    [emails.id, emails.address],
                    where=Builtins.Find(emails.address, 'spam') > 0,
                )
                # SELECT "emails"."id", "emails"."address"
                # FROM "emails"
                # WHERE ((STRPOS("emails"."address", %s)) > %s)
                # Parameters: ['spam', 0]

            Python-equivalent "not found" check — add ``- 1`` so -1 means
            "missing"::

                py_find = Builtins.Find(emails.address, 'example') - 1
                rows = emails.get_row(
                    [emails.address],
                    where=py_find == -1,
                )
                # SELECT "emails"."address" FROM "emails"
                # WHERE (((STRPOS("emails"."address", %s)) - %s) = %s)
                # Parameters: ['example', 1, -1]

            Use a column as the needle — find where one column appears
            inside another::

                rows = emails.get_row([
                    emails.id,
                    Builtins.Find(emails.address, emails.username),
                ])
                # SELECT "emails"."id",
                #        (STRPOS("emails"."address", "emails"."username"))
                # FROM "emails"

            Combine with slicing to extract everything before the '@'.
            Note that the ORM slice is start-inclusive, stop-exclusive on
            top of a 0-based expression, so we subtract one extra from the
            1-based STRPO S position::

                at_pos = Builtins.Find(emails.address, '@')
                local_part = emails.address[:at_pos - 1]
                rows = emails.get_row([emails.id, local_part])
                # The generated slice expression handles the -1 internally
                # and produces the substring before the '@'.

            Applied to raw literals::

                rows = emails.get_row([
                    Builtins.Find('hello', 'l'),   # -> 3 (first 'l' at 1-based pos 3)
                    Builtins.Find('hello', 'z'),   # -> 0
                ])
        """
        s1, p1, _, c = Builtins._normalize(value)
        s2, p2, _, _ = Builtins._normalize(sub)
        return Builtins._make(f'(STRPOS({s1}, {s2}))', p1 + p2, int, c)

    @staticmethod
    def Format(fmt, *args):
        """Format a string using PostgreSQL's ``FORMAT()`` function.

        Generates a ``FORMAT(<fmt>, <arg1>, <arg2>, ...)`` expression.
        Unlike SQLite's ``PRINTF`` which supports ``%d``, ``%f``, ``%s``,
        and ``%x``, PostgreSQL's ``FORMAT`` supports only the following
        placeholders:

        - ``%s`` — string substitution (the argument is cast to text)
        - ``%I`` — quoted identifier (useful for dynamic SQL)
        - ``%L`` — quoted literal (null → ``NULL``, others → quoted text)
        - ``%%`` — literal percent sign

        Numeric formatting with padding, decimals, or thousands separators
        is done via ``TO_CHAR`` instead — for example
        ``Builtins.Strftime('999,999.99', col)`` works on numeric inputs
        too, despite the name. See the ORM's ``Strftime`` helper.

        .. warning::
            The format string is bound as a parameter (``%s``), but the
            *format specifier* inside it is interpreted by PostgreSQL at
            execution time. A malformed format string will raise an SQL
            error; a mismatched number of specifiers versus arguments will
            silently substitute the wrong values or raise a runtime error.

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
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(FORMAT(<fmt>, <arg1>, ...))`` and whose ``current_datatype``
            is always ``str``.

        Example:
            Classic greeting — the SQL analogue of ``'Hi, %s' % name``::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                greeting = Builtins.Format('Hello, %s!', users.name)
                rows = users.get_row([greeting])
                # SELECT (FORMAT(%s, "users"."name")) FROM "users"
                # Parameters: ['Hello, %s!']
                # -> [('Hello, Alice!',), ('Hello, Bob!',), ...]

            Build a CSV line from multiple columns::

                row_csv = Builtins.Format(
                    '%s,%s,%s',
                    users.name,
                    users.email,
                    users.age,
                )
                rows = users.get_row([row_csv])
                # SELECT (FORMAT(%s, "users"."name",
                #                "users"."email", "users"."age"))
                # FROM "users"
                # Parameters: ['%s,%s,%s']
                # -> [('Alice,alice@x.com,30',), ...]

            Null-safe literal via ``%L`` — NULL becomes the SQL keyword
            NULL, others are quoted::

                expr = Builtins.Format('SELECT %L', users.name)
                rows = users.get_row([expr])
                # -> [("SELECT 'Alice'",), ("SELECT 'Bob'",), ...]

            Quoted identifier via ``%I`` — for dynamic-SQL generation::

                expr = Builtins.Format('SELECT * FROM %I', users.name)
                rows = users.get_row([expr])
                # -> [('SELECT * FROM "Alice"',), ...]

            Escape a literal percent sign with ``%%``::

                percent = Builtins.Format('%s%% complete', users.progress)
                rows = users.get_row([percent])
                # Parameters: ['%s%% complete']
                # -> [('75% complete',), ('100% complete',), ...]

            Combine with other builtins::

                total = Builtins.Format(
                    'Total: %s USD',
                    Builtins.Sum(users.balance),
                )
                rows = users.get_row([total])
                # SELECT (FORMAT(%s, (SUM("users"."balance"))))
                # FROM "users"
                # Parameters: ['Total: %s USD']

            Numeric formatting is NOT handled by FORMAT — use Strftime
            (which maps to TO_CHAR) for that::

                pretty = Builtins.Strftime('999,999.99', users.balance)
                rows = users.get_row([pretty])
                # SELECT (TO_CHAR("users"."balance", %s)) FROM "users"
                # Parameters: ['999,999.99']
                # -> [('  123,456.78',), ...]
        """
        s0, p0, _, c = Builtins._normalize(fmt)
        parts, params = [s0], list(p0)
        for v in args:
            s, p, _, _ = Builtins._normalize(v)
            parts.append(s)
            params.extend(p)
        return Builtins._make(f'(FORMAT({", ".join(parts)}))', params, str, c)

    @staticmethod
    def IsNull(value):
        """Test whether a value is NULL.

        Generates an ``(<expr> IS NULL)`` predicate. PostgreSQL evaluates
        this to a boolean ``TRUE`` when the expression produces NULL, and
        ``FALSE`` otherwise.

        This is the explicit, always-correct way to check for NULL. Using
        the ordinary comparison operator — ``column == None`` — is also
        supported by this ORM (see :meth:`Column.eq`) but only when the
        right-hand side is literally ``None``. ``IsNull`` works uniformly
        with any expression:

        - A column that may contain NULL
        - A computed expression that may return NULL (e.g. ``Sqrt`` of a
          negative number raises, ``Func('NULLIF', …)`` returns NULL, an
          aggregate over an empty group with ``Sum``)
        - A raw Python ``None`` literal

        The result is a real Python ``bool``, so it can be compared
        directly to Python booleans in the ORM's filter expressions.

        Args:
            value: The expression to test. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder. In
                  particular, ``IsNull(None)`` produces ``(%s IS NULL)``
                  with the ``None`` bound as a parameter, which is always
                  true.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``((<expr>) IS NULL)`` and whose ``current_datatype`` is
            ``bool``.

        Example:
            Select users who have not yet provided an email::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.IsNull(users.email),
                )
                # SELECT "users"."id", "users"."username" FROM "users"
                # WHERE (("users"."email") IS NULL)

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
                # SELECT "users"."id", "users"."username" FROM "users"
                # WHERE ((("users"."email") IS NULL)
                #        AND ("users"."created_at" > %s))
                # Parameters: ['2024-01-01']

            Test a computed expression that might return NULL — for
            example the ``NULLIF`` of a field against itself::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.IsNull(
                        Builtins.Func('NULLIF', users.email)
                    ),
                )
                # SELECT "users"."id" FROM "users"
                # WHERE ((NULLIF("users"."email")) IS NULL)

            Count how many rows have a NULL value in one column. PostgreSQL
            does not allow boolean values to be cast to integer implicitly,
            so this uses a CASE to convert to 0/1::

                missing_emails = Builtins.Sum(
                    Builtins.IIf(Builtins.IsNull(users.email), 1, 0)
                )
                rows = users.get_row([missing_emails])
                # SELECT (SUM((CASE WHEN (("users"."email") IS NULL)
                #                    THEN %s ELSE %s END)))
                # FROM "users"
                # Parameters: [1, 0]
                # -> [(42,)] if 42 users have no email

            Check for a raw literal ``None``::

                rows = users.get_row([
                    Builtins.IsNull(None),   # -> ((%s) IS NULL) -> always TRUE
                ])
                # Parameters: [None]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(({sql}) IS NULL)', p, bool, c)

    @staticmethod
    def IsNotNull(value):
        """Test whether a value is not NULL.

        Generates an ``(<expr> IS NOT NULL)`` predicate. PostgreSQL
        evaluates this to a boolean ``TRUE`` when the expression produces
        any non-NULL value, and ``FALSE`` when it evaluates to NULL.

        The exact logical negation of :meth:`IsNull`. Use whichever reads
        more naturally at the call site — both compile to distinct SQL but
        produce the same set of rows when their results are inverted.

        The result is a real Python ``bool``, so it can be compared
        directly to Python booleans in the ORM's filter expressions.

        Args:
            value: The expression to test. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder. In
                  particular, ``IsNotNull(42)`` produces ``(%s IS NOT NULL)``
                  with the ``42`` bound as a parameter, which is always true;
                  ``IsNotNull(None)`` is always false.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``((<expr>) IS NOT NULL)`` and whose ``current_datatype`` is
            ``bool``.

        Example:
            Select users who have provided an email::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row(
                    [users.id, users.username, users.email],
                    where=Builtins.IsNotNull(users.email),
                )
                # SELECT "users"."id", "users"."username", "users"."email"
                # FROM "users"
                # WHERE (("users"."email") IS NOT NULL)

            Combine with OR to allow either of two identifier columns::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.IsNotNull(users.email)
                        | Builtins.IsNotNull(users.phone),
                )
                # SELECT "users"."id" FROM "users"
                # WHERE ((("users"."email") IS NOT NULL)
                #        OR (("users"."phone") IS NOT NULL))

            Count non-NULL values in a column — the inverse of the
            ``IsNull`` count::

                have_email = Builtins.Sum(
                    Builtins.IIf(Builtins.IsNotNull(users.email), 1, 0)
                )
                rows = users.get_row([have_email])
                # SELECT (SUM((CASE WHEN (("users"."email") IS NOT NULL)
                #                    THEN %s ELSE %s END)))
                # FROM "users"
                # Parameters: [1, 0]
                # -> [(198,)]

            Test a computed expression whose non-NULLness is meaningful —
            the classic "only rows where the ratio is defined"::

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.IsNotNull(
                        Builtins.Func('NULLIF', users.attempts)
                    ),
                )
                # SELECT "users"."id", "users"."username" FROM "users"
                # WHERE ((NULLIF("users"."attempts")) IS NOT NULL)

            "Both or neither" validation — the classic pattern to find
            inconsistent rows::

                both_set = (
                    Builtins.IsNotNull(users.email)
                    & Builtins.IsNotNull(users.verified_at)
                )
                neither_set = (
                    Builtins.IsNull(users.email)
                    & Builtins.IsNull(users.verified_at)
                )
                rows = users.get_row(
                    [users.id],
                    where=(both_set | neither_set) == False,
                )
                # SELECT "users"."id" FROM "users"
                # WHERE ((((("users"."email") IS NOT NULL)
                #          AND (("users"."verified_at") IS NOT NULL))
                #         OR ((("users"."email") IS NULL)
                #             AND (("users"."verified_at") IS NULL))) = %s)
                # Parameters: [False]

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.IsNotNull(42),    # -> ((%s) IS NOT NULL) -> TRUE
                    Builtins.IsNotNull(None),  # -> ((%s) IS NOT NULL) -> FALSE
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(({sql}) IS NOT NULL)', p, bool, c)

    @staticmethod
    def Between(value, low, high):
        """Test whether a value lies within an inclusive range.

        Generates an ``(<expr> BETWEEN <low> AND <high>)`` predicate.
        PostgreSQL evaluates this to a boolean ``TRUE`` when
        ``low <= value <= high`` and ``FALSE`` otherwise. Both bounds are
        inclusive, matching Python's ``low <= x <= high`` idiom exactly.

        .. note::
            SQL's ``BETWEEN`` is equivalent to
            ``(value >= low) AND (value <= high)`` but is a single operator
            with well-defined semantics for all three operand types. When
            any of the three operands is NULL the result is NULL, which the
            surrounding query treats as "false" in a ``WHERE`` clause.

        The result is a real Python ``bool``, so it can be compared
        directly to Python booleans in the ORM's filter expressions.

        Args:
            value: The expression to test. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder.

            low: The lower bound (inclusive). Same accepted types as
                ``value``.

            high: The upper bound (inclusive). Same accepted types as
                ``value``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``((<value>) BETWEEN <low> AND <high>)`` and whose
            ``current_datatype`` is ``bool``. Parameters are concatenated
            left-to-right: first ``value``'s, then ``low``'s, then
            ``high``'s.

        Example:
            Select products in a price band::

                from Ormophine.Postgresql import Driver, Builtins

                db       = Driver("localhost", 5432, "user", "pass", "store")
                products = db.products

                rows = products.get_row(
                    [products.name, products.price],
                    where=Builtins.Between(products.price, 10.0, 50.0),
                )
                # SELECT "products"."name", "products"."price"
                # FROM "products"
                # WHERE (("products"."price") BETWEEN %s AND %s)
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
                # SELECT "users"."id", "users"."created_at" FROM "users"
                # WHERE (("users"."created_at") BETWEEN %s AND %s)
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
                # SELECT "products"."name" FROM "products"
                # WHERE (("products"."price" * %s) BETWEEN %s AND %s)
                # Parameters: [0.9, 5.0, 45.0]

            Boundaries using other columns — margins within 10% of cost::

                rows = products.get_row(
                    [products.name, products.price],
                    where=Builtins.Between(
                        products.price,
                        products.cost,
                        products.cost * 1.1,
                    ),
                )
                # SELECT "products"."name", "products"."price"
                # FROM "products"
                # WHERE (("products"."price")
                #        BETWEEN "products"."cost"
                #            AND ("products"."cost" * %s))
                # Parameters: [1.1]

            Negate the check — rows outside the band. PostgreSQL returns
            boolean, so the ``== False`` comparison is clean::

                in_band = Builtins.Between(products.price, 10.0, 50.0)
                rows = products.get_row(
                    [products.name],
                    where=in_band == False,
                )
                # SELECT "products"."name" FROM "products"
                # WHERE ((("products"."price") BETWEEN %s AND %s) = %s)
                # Parameters: [10.0, 50.0, False]

            NULL handling — a NULL value in any operand makes the whole
            predicate NULL (treated as false). To include NULLs, add an
            explicit OR::

                rows = products.get_row(
                    [products.name],
                    where=Builtins.Between(products.price, 10.0, 50.0)
                        | Builtins.IsNull(products.price),
                )
                # SELECT "products"."name" FROM "products"
                # WHERE ((("products"."price") BETWEEN %s AND %s)
                #        OR (("products"."price") IS NULL))
                # Parameters: [10.0, 50.0]

            Applied to raw literals::

                rows = products.get_row([
                    Builtins.Between(5, 1, 10),     # -> TRUE
                    Builtins.Between(15, 1, 10),    # -> FALSE
                ])
        """
        s, p, _, c = Builtins._normalize(value)
        lo, lp, _, _ = Builtins._normalize(low)
        hi, hp, _, _ = Builtins._normalize(high)
        return Builtins._make(
            f'(({s}) BETWEEN {lo} AND {hi})', p + lp + hp, bool, c)

    @staticmethod
    def IIf(condition, then_value, else_value):
        """One-line conditional — the SQL analogue of Python's ``a if cond else b``.

        Generates a ``CASE WHEN <cond> THEN <then> ELSE <else> END``
        expression. PostgreSQL has no built-in ``IIF`` function (unlike
        SQLite 3.32+ and SQL Server), so this helper emits the standard
        SQL ``CASE`` form directly — which works on every version of
        PostgreSQL and is also more portable across other database engines.

        This is the value-producing sibling of the SQL ``CASE`` statement
        and the direct equivalent of Python's ternary conditional operator::

            Python:   x if cond else y
            SQL:      CASE WHEN cond THEN x ELSE y END
            ORM:      Builtins.IIf(cond, x, y)

        .. note::
            PostgreSQL evaluates both branches before choosing one — same
            as Python's conditional expression. If a branch divides by
            zero, that will raise at execution time even when the condition
            would have skipped that branch. Guard the divisor with a nested
            ``IIf`` or use ``Func('NULLIF', …)`` if this matters.

        Args:
            condition: The test expression. May be any standard operand:

                - :class:`ColumnsOperation` — typically a comparison like
                  ``users.age >= 18``.
                - :class:`Column` — used directly as a boolean.
                - A raw Python value (``True``, ``False``, ``0``, ``1``)
                  — bound as a parameter.

            then_value: What to return when ``condition`` is truthy.
                Same accepted types as ``condition``.

            else_value: What to return when ``condition`` is falsy.
                Same accepted types as ``condition``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CASE WHEN <cond> THEN <then> ELSE <else> END)`` and whose
            ``current_datatype`` is ``None``. The datatype is not
            propagated because the two branches may disagree (e.g. ``str``
            versus ``int``); downstream ``+`` operators will choose
            arithmetic by default, which the caller may override by
            wrapping the result in :meth:`Str`, :meth:`Int`, or
            :meth:`Float`. Parameters are concatenated in the order:
            condition, then, else.

        Example:
            Categorise ages into minor / adult — the classic pattern::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                category = Builtins.IIf(users.age >= 18, 'adult', 'minor')
                rows = users.get_row([
                    users.name,
                    users.age,
                    category,
                ])
                # SELECT "users"."name", "users"."age",
                #        (CASE WHEN ("users"."age" >= %s)
                #              THEN %s ELSE %s END)
                # FROM "users"
                # Parameters: [18, 'adult', 'minor']
                # -> [('Alice', 30, 'adult'), ('Bob', 15, 'minor'), ...]

            Fill NULL with a fallback — equivalent to COALESCE but with
            a boolean test::

                display_email = Builtins.IIf(
                    Builtins.IsNull(users.email),
                    'no email',
                    users.email,
                )
                rows = users.get_row([users.username, display_email])
                # SELECT "users"."username",
                #        (CASE WHEN (("users"."email") IS NULL)
                #              THEN %s ELSE "users"."email" END)
                # FROM "users"
                # Parameters: ['no email']

            Nested conditionals — a two-threshold bucketing. Each nested
            call goes inside the ``else_value`` slot::

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
                # SELECT "users"."name", "users"."score",
                #        (CASE WHEN ("users"."score" >= %s) THEN %s
                #              ELSE (CASE WHEN ("users"."score" >= %s) THEN %s
                #                         ELSE (CASE WHEN ("users"."score" >= %s)
                #                                    THEN %s ELSE %s END) END) END)
                # FROM "users"
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
                # SELECT "users"."name", "users"."salary",
                #        (CASE WHEN ("users"."rating" > %s)
                #              THEN ("users"."salary" * %s)
                #              ELSE "users"."salary" END)
                # FROM "users"
                # Parameters: [4, 1.1]

            Coerce the result to a specific type with a cast builtin::

                label_num = Builtins.Int(
                    Builtins.IIf(users.is_active == True, 100, 0)
                )
                rows = users.get_row([label_num])
                # SELECT (CAST((CASE WHEN ("users"."is_active" = %s)
                #                    THEN %s ELSE %s END) AS INTEGER))
                # FROM "users"
                # Parameters: [True, 100, 0]

            Count matches via SUM of IIF — a common "conditional
            aggregate" idiom::

                active_count = Builtins.Sum(
                    Builtins.IIf(users.is_active == True, 1, 0)
                )
                rows = users.get_row([active_count])
                # SELECT (SUM((CASE WHEN ("users"."is_active" = %s)
                #                   THEN %s ELSE %s END)))
                # FROM "users"
                # Parameters: [True, 1, 0]

            Diverging branches with different datatypes — the reason
            ``current_datatype`` is ``None`` on the result::

                mixed = Builtins.IIf(users.has_phone == True,
                                     users.phone,
                                     0)
                # If has_phone, returns a string; else returns integer 0.
                # Wrap with Builtins.Str if the surrounding context expects
                # a string:
                safe = Builtins.Str(mixed)
                rows = users.get_row([safe])
                # SELECT (CAST((CASE WHEN ("users"."has_phone" = %s)
                #                    THEN "users"."phone"
                #                    ELSE %s END) AS TEXT))
                # FROM "users"
                # Parameters: [True, 0]
        """
        cs, cp, _, c = Builtins._normalize(condition)
        ts, tp, _, _ = Builtins._normalize(then_value)
        es, ep, _, _ = Builtins._normalize(else_value)
        return Builtins._make(
            f'(CASE WHEN {cs} THEN {ts} ELSE {es} END)',
            cp + tp + ep, None, c)
    
    @staticmethod
    def Func(name, value):
        """Apply an arbitrary SQL function to a single operand.

        Generates a ``(<name>(<expr>))`` expression. This is the escape
        hatch for any PostgreSQL function whose return type cannot be
        inferred from the ORM's built-in catalogue — for example
        ``COALESCE``, ``NULLIF``, ``GREATEST``, ``LEAST``, ``INITCAP``,
        ``MD5``, ``ENCODE``, ``DECODE``, ``REGEXP_REPLACE``, or any
        user-defined function.

        The helper is deliberately minimal: it takes exactly two
        arguments — the function name as a Python string, and the single
        operand to feed it. Multi-argument functions need to be built by
        chaining, or by using the ``Column`` methods that already wrap the
        common cases (``.replace`` for ``REPLACE``, ``.like`` for ``LIKE``,
        etc.).

        Because the return type is unknown, ``current_datatype`` is
        propagated from the input as a best-effort heuristic:

        - ``str``   → ``str``   (safe for text functions)
        - ``int``   → ``int``
        - ``float`` → ``float``
        - ``bool``  → ``bool``

        This keeps arithmetic chains (``Func('ABS', col) + 1``) compiling
        to ``+`` when the input was numeric, and keeps concatenation
        (``Func('INITCAP', col) + '!'``) compiling to ``||`` when the input
        was text. If the actual return type differs from the input's type
        — for example ``Func('LENGTH', some_text)`` returns an integer —
        wrap the result in :meth:`Int`, :meth:`Float`, :meth:`Str`, or
        :meth:`Bool` to force the correct ``current_datatype`` before
        chaining further.

        Args:
            name: The PostgreSQL function name. Must be a non-empty string.
                Case is preserved as written, so if the function is defined
                in lowercase (PostgreSQL's default), pass it in lowercase.

            value: The single operand. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(<name>(<expr>))`` and whose ``current_datatype`` is
            propagated from the input.

        Raises:
            ValueError: If ``name`` is not a non-empty string.

        Example:
            ``COALESCE`` — return the first non-NULL argument. Note that
            since the multi-argument form is not supported by ``Func``,
            this example wraps a single column that is *already* known to
            contain NULLs and provides no fallback; use :meth:`Column.If`
            for that pattern instead::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([
                    Builtins.Func('INITCAP', users.name),
                ])
                # SELECT (INITCAP("users"."name")) FROM "users"
                # -> [('Alice Smith',), ('Bob Jones',), ...]

            ``MD5`` — a text function that returns text::

                rows = users.get_row([
                    Builtins.Func('MD5', users.email),
                ])
                # SELECT (MD5("users"."email")) FROM "users"
                # -> [('5d41402abc4b2a76b9719d911017c592',), ...]

            ``LENGTH`` on a text column — the return type is ``int`` but
            the input's ``current_datatype`` is ``str``, so we wrap with
            :meth:`Int` to force the correct chaining semantics::

                length_int = Builtins.Int(Builtins.Func('LENGTH', users.name))
                rows = users.get_row(
                    [users.name, length_int],
                    where=length_int > 5,
                )
                # SELECT "users"."name",
                #        (CAST((LENGTH("users"."name")) AS INTEGER))
                # FROM "users"
                # WHERE ((CAST((LENGTH("users"."name")) AS INTEGER)) > %s)
                # Parameters: [5]

            ``REGEXP_REPLACE`` — strip non-ASCII from a column. The
            pattern and replacement are baked into the function via
            Python-side string composition, since ``Func`` accepts only
            one operand::

                expr = Builtins.Func('REGEXP_REPLACE', users.name)
                rows = users.get_row([expr])
                # SELECT (REGEXP_REPLACE("users"."name")) FROM "users"
                # NOTE: the two-argument REGEXP_REPLACE requires a second
                # argument — this will fail at execution. Use a raw
                # expression or the Column API instead.

            ``GREATEST`` on two columns — again, the multi-argument case.
            Build the SQL manually via ``Column`` operators::

                from Ormophine.Postgresql import ColumnsOperation
                # The built-in way to get the larger of two columns:
                expr = users.updated_at   # placeholder for illustration
                # For "greatest of two columns", use a CASE:
                later = Builtins.IIf(
                    users.updated_at > users.created_at,
                    users.updated_at,
                    users.created_at,
                )
                rows = users.get_row([later])
                # SELECT (CASE WHEN ("users"."updated_at" > "users"."created_at")
                #              THEN "users"."updated_at"
                #              ELSE "users"."created_at" END)
                # FROM "users"

            Chained with arithmetic — ``current_datatype`` propagates
            from the input::

                doubled = Builtins.Func('ABS', users.balance) * 2
                rows = users.get_row([doubled])
                # SELECT ((ABS("users"."balance")) * %s) FROM "users"
                # Parameters: [2]

            Chained with string operations — same idea, text side::

                expr = Builtins.Func('INITCAP', users.name).add_end('!')
                rows = users.get_row([expr])
                # SELECT ((INITCAP("users"."name")) || %s) FROM "users"
                # Parameters: ['!']

            Raises on empty name::

                Builtins.Func('', users.name)
                # ValueError: Func requires a non-empty function name string
        """
        if not isinstance(name, str) or not name:
            raise ValueError('Func requires a non-empty function name string')
        sql, p, dt, c = Builtins._normalize(value)
        return Builtins._make(f'({name}({sql}))', p, dt, c)

    @staticmethod
    def Date(value):
        """Cast a value to a DATE, discarding any time-of-day component.

        Generates a ``CAST(<expr> AS DATE)`` expression. This is the SQL
        equivalent of taking ``datetime.date()`` from a Python
        ``datetime.datetime`` object — it strips the time portion and
        keeps only the calendar date.

        The result is a real Python ``datetime.date`` after fetching (the
        psycopg driver converts PostgreSQL's ``DATE`` type automatically).
        The ``current_datatype`` is set to ``str`` because the ORM's
        datatype dispatch treats dates as text-like values in comparisons
        and concatenation.

        PostgreSQL accepts a wide range of inputs for the cast:

        - A ``TIMESTAMP`` or ``TIMESTAMPTZ`` column (the common case)
        - An ISO 8601 text literal like ``'2024-03-15'``
        - An ISO 8601 timestamp string like ``'2024-03-15 09:30:00'``
        - A ``CURRENT_DATE`` or ``NOW()`` expression

        Args:
            value: The expression whose date component is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS DATE))`` and whose ``current_datatype`` is
            ``str``.

        Example:
            Get the signup date for every user — strip the time component::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([
                    users.id,
                    users.created_at,
                    Builtins.Date(users.created_at),
                ])
                # SELECT "users"."id", "users"."created_at",
                #        (CAST("users"."created_at" AS DATE))
                # FROM "users"
                # -> [(1, datetime(2024, 3, 15, 9, 30, 42), date(2024, 3, 15)), ...]

            Filter by a specific day — everything created on March 15::

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.Date(users.created_at)
                        == Builtins.Date('2024-03-15'),
                )
                # SELECT "users"."id", "users"."username" FROM "users"
                # WHERE ((CAST("users"."created_at" AS DATE))
                #        = (CAST(%s AS DATE)))
                # Parameters: ['2024-03-15']

            Compare against today's date — the ``CURRENT_DATE`` keyword::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Date(users.created_at)
                        == Builtins.Func('CURRENT_DATE', 'dummy'),
                )
                # NOTE: CURRENT_DATE is a keyword, not a function. Use
                # Builtins.Today() for a cleaner equivalent (see below).

            The idiomatic "today" comparison uses :meth:`Today`::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Date(users.created_at) == Builtins.Today(),
                )
                # SELECT "users"."id" FROM "users"
                # WHERE ((CAST("users"."created_at" AS DATE)) = (CURRENT_DATE))

            Group by day and count — do the grouping in Python after
            fetching, since the ORM has no GROUP BY helper::

                rows = users.get_row([Builtins.Date(users.created_at)])
                from collections import Counter
                daily = Counter(d for (d,) in rows)
                # {date(2024, 3, 15): 12, date(2024, 3, 16): 8, ...}

            Chain with date arithmetic via :meth:`DateAdd`::

                next_week = Builtins.DateAdd(users.created_at, '7 days')
                rows = users.get_row([
                    users.id,
                    next_week,
                ])
                # SELECT "users"."id",
                #        (CAST((CAST("users"."created_at" AS TIMESTAMP)
                #               + %s::interval) AS DATE))
                # FROM "users"
                # Parameters: ['7 days']

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Date('2024-03-15 14:30:00'),  # -> date(2024, 3, 15)
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS DATE))', p, str, c)

    @staticmethod
    def Time(value):
        """Cast a value to a TIME, discarding any date component.

        Generates a ``CAST(<expr> AS TIME)`` expression. This is the SQL
        equivalent of taking ``datetime.time()`` from a Python
        ``datetime.datetime`` object — it strips the date portion and keeps
        only the time of day.

        The result is a real Python ``datetime.time`` after fetching (the
        psycopg driver converts PostgreSQL's ``TIME`` type automatically).
        The ``current_datatype`` is set to ``str`` because the ORM's
        datatype dispatch treats times as text-like values in comparisons
        and concatenation.

        Note that ``CAST(<expr> AS TIME)`` produces a ``TIME WITHOUT TIME
        ZONE`` by default. To preserve a time-zone offset, cast to
        ``TIMETZ`` instead — use :meth:`Func` with the target type, or
        rely on the column's declared type.

        PostgreSQL accepts a wide range of inputs for the cast:

        - A ``TIMESTAMP`` or ``TIMESTAMPTZ`` column
        - An ISO 8601 text literal like ``'09:30:00'``
        - An ISO 8601 timestamp string like ``'2024-03-15 09:30:00'``
        - A ``NOW()`` expression

        Args:
            value: The expression whose time component is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS TIME))`` and whose ``current_datatype`` is
            ``str``.

        Example:
            Get the signup time for every user — strip the date component::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([
                    users.id,
                    users.created_at,
                    Builtins.Time(users.created_at),
                ])
                # SELECT "users"."id", "users"."created_at",
                #        (CAST("users"."created_at" AS TIME))
                # FROM "users"
                # -> [(1, datetime(2024, 3, 15, 9, 30, 42), time(9, 30, 42)), ...]

            Filter by time-of-day range — office-hours signups::

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.Time(users.created_at) >= '09:00:00',
                )
                # SELECT "users"."id", "users"."username" FROM "users"
                # WHERE ((CAST("users"."created_at" AS TIME)) >= %s)
                # Parameters: ['09:00:00']

            Half-open range — the BETWEEN helper is inclusive, so use two
            comparisons for a strict upper bound::

                t = Builtins.Time(users.created_at)
                rows = users.get_row(
                    [users.id],
                    where=(t >= '09:00:00') & (t < '17:00:00'),
                )
                # SELECT "users"."id" FROM "users"
                # WHERE (((CAST("users"."created_at" AS TIME)) >= %s)
                #        AND ((CAST("users"."created_at" AS TIME)) < %s))
                # Parameters: ['09:00:00', '17:00:00']

            Extract the hour via :meth:`Hour` instead of slicing in Python::

                rows = users.get_row([
                    users.id,
                    Builtins.Hour(users.created_at),
                ])
                # SELECT "users"."id",
                #        (EXTRACT(HOUR FROM "users"."created_at")::INTEGER)
                # FROM "users"

            Compare against the current time — the ``'now'`` keyword is
            not a thing in PostgreSQL; use :meth:`Now` instead::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Time(users.created_at)
                        < Builtins.Time(Builtins.Now()),
                )
                # SELECT "users"."id" FROM "users"
                # WHERE ((CAST("users"."created_at" AS TIME))
                #        < (CAST((NOW()) AS TIME)))

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Time('2024-03-15 14:30:00'),  # -> time(14, 30)
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS TIME))', p, str, c)

    @staticmethod
    def DateTime(value):
        """Cast a value to a TIMESTAMP (without time zone).

        Generates a ``CAST(<expr> AS TIMESTAMP)`` expression. This is the
        SQL equivalent of Python's ``datetime.datetime`` — a date and time
        together, without any time-zone awareness.

        The result is a real Python ``datetime.datetime`` after fetching
        (the psycopg driver converts PostgreSQL's ``TIMESTAMP`` type
        automatically). The ``current_datatype`` is set to ``str`` because
        the ORM's datatype dispatch treats timestamps as text-like values
        in comparisons and concatenation.

        Common uses:

        - **Normalising** text or mixed-shape inputs into a canonical
          ``TIMESTAMP`` form so they compare consistently.
        - **Stripping the time zone** from a ``TIMESTAMPTZ`` value — for
          example, to compare against a ``TIMESTAMP`` column without
          time-zone conversion.
        - **Upgrading** a ``DATE`` value to a ``TIMESTAMP`` at midnight.

        To preserve a time zone, cast to ``TIMESTAMPTZ`` instead — use
        :meth:`Func` with the target type, or rely on the column's
        declared type.

        Args:
            value: The expression whose full datetime is produced.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS TIMESTAMP))`` and whose ``current_datatype``
            is ``str``.

        Example:
            Normalise mixed-format timestamps for display::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "app")
                events = db.events

                rows = events.get_row([
                    events.id,
                    events.occurred_at,
                    Builtins.DateTime(events.occurred_at),
                ])
                # SELECT "events"."id", "events"."occurred_at",
                #        (CAST("events"."occurred_at" AS TIMESTAMP))
                # FROM "events"
                # -> [(1, datetime(2024, 3, 15, 0, 0), datetime(2024, 3, 15, 0, 0)), ...]

            Strip the time zone from a ``TIMESTAMPTZ`` column for
            comparison against a ``TIMESTAMP`` column::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.DateTime(events.occurred_at)
                        > Builtins.DateTime(events.created_at),
                )
                # SELECT "events"."id" FROM "events"
                # WHERE ((CAST("events"."occurred_at" AS TIMESTAMP))
                #        > (CAST("events"."created_at" AS TIMESTAMP)))

            Get the current timestamp as a SELECT column — see
            :meth:`Now` for a cleaner alternative::

                rows = events.get_row([
                    Builtins.DateTime(Builtins.Now()),
                ])
                # SELECT (CAST((NOW()) AS TIMESTAMP)) FROM "events"
                # -> [(datetime(2024, 3, 15, 14, 30, 42),)]

            "Last 24 hours" filter — combine with :meth:`DateTimeAdd`::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.DateTime(events.occurred_at)
                        >= Builtins.DateTimeAdd(Builtins.Now(), '-1 day'),
                )
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # WHERE ((CAST("events"."occurred_at" AS TIMESTAMP))
                #        >= ((CAST((NOW()) AS TIMESTAMP) + %s::interval)))
                # Parameters: ['-1 day']

            Bucket events into "recent / older" via IIF::

                recent = Builtins.IIf(
                    Builtins.DateTime(events.occurred_at)
                        >= Builtins.DateTimeAdd(Builtins.Now(), '-1 day'),
                    'recent',
                    'older',
                )
                rows = events.get_row([events.id, recent])
                # SELECT "events"."id",
                #        (CASE WHEN ((CAST("events"."occurred_at" AS TIMESTAMP))
                #                    >= ((CAST((NOW()) AS TIMESTAMP)
                #                         + %s::interval)))
                #              THEN %s ELSE %s END)
                # FROM "events"
                # Parameters: ['-1 day', 'recent', 'older']

            Store a computed timestamp during an UPDATE::

                events.update(
                    update={events.last_seen: Builtins.Now()},
                    where=events.id == 42,
                )
                # UPDATE "events" SET "last_seen" = (NOW())
                # WHERE ("events"."id" = %s);
                # Parameters: [42]

            Applied to a raw literal to normalise at the SQL layer::

                rows = events.get_row([
                    Builtins.DateTime('2024-03-15'),           # -> midnight
                    Builtins.DateTime('2024-03-15 09:30:00'),  # unchanged
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS TIMESTAMP))', p, str, c)

    @staticmethod
    def Year(value):
        """Extract the four-digit year from a date/time value.

        Generates an ``EXTRACT(YEAR FROM <expr>)::INTEGER`` expression.
        PostgreSQL's ``EXTRACT`` returns a ``NUMERIC`` by default, so the
        explicit ``::INTEGER`` cast is required to keep the datatype
        honest — otherwise a downstream ``+ 1`` would keep the numeric
        domain but psycopg would deliver a ``decimal.Decimal`` instead of
        a Python ``int``.

        The result is always an ``INTEGER``, so it plays nicely with
        arithmetic, comparisons, and other numeric builtins.

        Args:
            value: The date/time expression whose year is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(YEAR FROM <expr>)::INTEGER)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Filter rows by year::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Year(users.created_at) == 2024,
                )
                # SELECT "users"."id", "users"."created_at" FROM "users"
                # WHERE ((EXTRACT(YEAR FROM "users"."created_at")::INTEGER) = %s)
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
                # SELECT "users"."username",
                #        (EXTRACT(YEAR FROM "users"."created_at")::INTEGER)
                # FROM "users"
                # -> [('Alice', 2024), ('Bob', 2024), ...]

            Range filter across years — combine with :meth:`Between`::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Between(
                        Builtins.Year(users.created_at), 2023, 2024
                    ),
                )
                # SELECT "users"."id" FROM "users"
                # WHERE (((EXTRACT(YEAR FROM "users"."created_at")::INTEGER))
                #        BETWEEN %s AND %s)
                # Parameters: [2023, 2024]

            Compare years with arithmetic — stays numeric because
            ``current_datatype`` is ``int``::

                next_year = Builtins.Year(users.created_at) + 1
                rows = users.get_row([users.id, next_year])
                # SELECT "users"."id",
                #        ((EXTRACT(YEAR FROM "users"."created_at")::INTEGER) + %s)
                # FROM "users"
                # Parameters: [1]

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Year('2024-03-15'),  # -> 2024
                    Builtins.Year(Builtins.Now()),  # -> current year
                ])
                # SELECT (EXTRACT(YEAR FROM %s)::INTEGER),
                #        (EXTRACT(YEAR FROM (NOW()))::INTEGER)
                # Parameters: ['2024-03-15']
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'(EXTRACT(YEAR FROM {sql})::INTEGER)', p, int, c)

    @staticmethod
    def Month(value):
        """Extract the month number (1–12) from a date/time value.

        Generates an ``EXTRACT(MONTH FROM <expr>)::INTEGER`` expression.
        PostgreSQL's ``EXTRACT`` returns a ``NUMERIC`` by default, so the
        explicit ``::INTEGER`` cast is required to produce a plain Python
        ``int`` after fetching.

        The result is always an ``INTEGER`` in the range 1 through 12, so
        it compares correctly with numeric literals (``== 3`` rather than
        ``== '03'``, which is the common pitfall when using ``TO_CHAR``).

        Args:
            value: The date/time expression whose month is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(MONTH FROM <expr>)::INTEGER)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Filter by month — pick a specific month regardless of year::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Month(users.created_at) == 3,
                )
                # SELECT "users"."id", "users"."created_at" FROM "users"
                # WHERE ((EXTRACT(MONTH FROM "users"."created_at")::INTEGER) = %s)
                # Parameters: [3]
                # -> everything created in March, any year

            Seasonal filter — Q1 only (January through March)::

                q1 = Builtins.Between(Builtins.Month(users.created_at), 1, 3)
                rows = users.get_row(
                    [users.username],
                    where=q1,
                )
                # SELECT "users"."username" FROM "users"
                # WHERE (((EXTRACT(MONTH FROM "users"."created_at")::INTEGER))
                #        BETWEEN %s AND %s)
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
                # SELECT "users"."username", "users"."created_at"
                # FROM "users"
                # ORDER BY (EXTRACT(MONTH FROM "users"."created_at")::INTEGER)

            Select with formatted month name — combine with ``IIf`` for
            the common "Jan / Feb / ..." display. Extend the nesting for
            all twelve months in real code::

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

            Same-month filter — users whose signup month matches their
            birth month::

                rows = users.get_row(
                    [users.username],
                    where=Builtins.Month(users.created_at)
                        == Builtins.Month(users.birth_date),
                )
                # SELECT "users"."username" FROM "users"
                # WHERE ((EXTRACT(MONTH FROM "users"."created_at")::INTEGER)
                #        = (EXTRACT(MONTH FROM "users"."birth_date")::INTEGER))

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Month('2024-03-15'),   # -> 3
                    Builtins.Month(Builtins.Now()),  # -> current month
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'(EXTRACT(MONTH FROM {sql})::INTEGER)', p, int, c)

    @staticmethod
    def Day(value):
        """Extract the day of the month (1–31) from a date/time value.

        Generates an ``EXTRACT(DAY FROM <expr>)::INTEGER`` expression.
        PostgreSQL's ``EXTRACT`` returns a ``NUMERIC`` by default, so the
        explicit ``::INTEGER`` cast is required to produce a plain Python
        ``int`` after fetching.

        The result is always an ``INTEGER`` in the range 1 through 31, so
        it compares correctly with numeric literals.

        Args:
            value: The date/time expression whose day of month is
                extracted. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(DAY FROM <expr>)::INTEGER)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Find rows created on the first of the month::

                from Ormophine.Postgresql import Driver, Builtins

                db       = Driver("localhost", 5432, "user", "pass", "app")
                invoices = db.invoices

                rows = invoices.get_row(
                    [invoices.id, invoices.issued_at, invoices.total],
                    where=Builtins.Day(invoices.issued_at) == 1,
                )
                # SELECT "invoices"."id", "invoices"."issued_at",
                #        "invoices"."total"
                # FROM "invoices"
                # WHERE ((EXTRACT(DAY FROM "invoices"."issued_at")::INTEGER) = %s)
                # Parameters: [1]

            Billing-cycle filter — mid-month settlements, days 13 to 15::

                rows = invoices.get_row(
                    [invoices.id],
                    where=Builtins.Between(
                        Builtins.Day(invoices.issued_at), 13, 15
                    ),
                )
                # SELECT "invoices"."id" FROM "invoices"
                # WHERE (((EXTRACT(DAY FROM "invoices"."issued_at")::INTEGER))
                #        BETWEEN %s AND %s)
                # Parameters: [13, 15]

            Detect first-of-month runs — useful for cron job auditing::

                rows = invoices.get_row(
                    [invoices.id, invoices.issued_at],
                    where=Builtins.Day(invoices.issued_at) <= 2,
                )
                # SELECT "invoices"."id", "invoices"."issued_at"
                # FROM "invoices"
                # WHERE ((EXTRACT(DAY FROM "invoices"."issued_at")::INTEGER) <= %s)
                # Parameters: [2]

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
                # -> all invoices issued in the last few days of any month

            Compare day-of-month across two date columns::

                same_day = (Builtins.Day(invoices.issued_at)
                            == Builtins.Day(invoices.due_at))
                rows = invoices.get_row([invoices.id], where=same_day)
                # SELECT "invoices"."id" FROM "invoices"
                # WHERE ((EXTRACT(DAY FROM "invoices"."issued_at")::INTEGER)
                #        = (EXTRACT(DAY FROM "invoices"."due_at")::INTEGER))

            Applied to a raw literal::

                rows = invoices.get_row([
                    Builtins.Day('2024-03-15'),   # -> 15
                    Builtins.Day(Builtins.Now()),  # -> current day
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'(EXTRACT(DAY FROM {sql})::INTEGER)', p, int, c)

    @staticmethod
    def Hour(value):
        """Extract the hour (0–23) from a date/time value.

        Generates an ``EXTRACT(HOUR FROM <expr>)::INTEGER`` expression.
        PostgreSQL's ``EXTRACT`` returns a ``NUMERIC`` by default, so the
        explicit ``::INTEGER`` cast is required to produce a plain Python
        ``int`` after fetching.

        The result is always an ``INTEGER`` in the range 0 through 23,
        using the 24-hour clock. Comparisons and arithmetic work as you
        would expect in Python.

        Args:
            value: The date/time expression whose hour is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(HOUR FROM <expr>)::INTEGER)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Business-hours filter — signups between 9 AM and 5 PM::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                hours = Builtins.Hour(users.created_at)
                rows = users.get_row(
                    [users.id, users.created_at],
                    where=(hours >= 9) & (hours < 17),
                )
                # SELECT "users"."id", "users"."created_at" FROM "users"
                # WHERE (((EXTRACT(HOUR FROM "users"."created_at")::INTEGER) >= %s)
                #        AND ((EXTRACT(HOUR FROM "users"."created_at")::INTEGER) < %s))
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
                # SELECT "users"."id",
                #        (CASE WHEN ((EXTRACT(HOUR FROM "users"."created_at")::INTEGER) < %s)
                #              THEN %s
                #              ELSE (CASE WHEN ((EXTRACT(HOUR FROM "users"."created_at")::INTEGER) < %s)
                #                         THEN %s
                #                         ELSE (CASE WHEN ((EXTRACT(HOUR FROM "users"."created_at")::INTEGER) < %s)
                #                                    THEN %s
                #                                    ELSE %s END) END) END)
                # FROM "users"
                # Parameters: [6, 'night', 12, 'morning', 18, 'afternoon', 'evening']

            Hourly histogram — a 24-bucket count of signups::

                rows = users.get_row([Builtins.Hour(users.created_at)])
                from collections import Counter
                by_hour = Counter(h for (h,) in rows)
                # {0: 3, 1: 1, ..., 9: 45, 10: 52, ..., 23: 8}
                # Great for finding the quietest hour to run maintenance.

            Filter by hour range with a wrap-around — "off-hours" (22:00
            through 05:59)::

                h = Builtins.Hour(users.created_at)
                off_hours = (h >= 22) | (h < 6)
                rows = users.get_row([users.id], where=off_hours)
                # SELECT "users"."id" FROM "users"
                # WHERE (((EXTRACT(HOUR FROM "users"."created_at")::INTEGER) >= %s)
                #        OR ((EXTRACT(HOUR FROM "users"."created_at")::INTEGER) < %s))
                # Parameters: [22, 6]

            Order by hour-of-day — clusters activity by time of day
            regardless of date::

                rows = users.get_row(
                    [users.username, users.created_at],
                    order_by=Builtins.Hour(users.created_at),
                )
                # SELECT "users"."username", "users"."created_at"
                # FROM "users"
                # ORDER BY (EXTRACT(HOUR FROM "users"."created_at")::INTEGER)

            Compare hours across two columns — same-hour activity::

                same_hour = (Builtins.Hour(users.created_at)
                             == Builtins.Hour(users.last_login))
                rows = users.get_row([users.id], where=same_hour)

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Hour('2024-03-15 09:30:42'),  # -> 9
                    Builtins.Hour(Builtins.Now()),          # -> current hour
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'(EXTRACT(HOUR FROM {sql})::INTEGER)', p, int, c)

    @staticmethod
    def Minute(value):
        """Extract the minute (0–59) from a date/time value.

        Generates an ``EXTRACT(MINUTE FROM <expr>)::INTEGER`` expression.
        PostgreSQL's ``EXTRACT`` returns a ``NUMERIC`` by default, so the
        explicit ``::INTEGER`` cast is required to produce a plain Python
        ``int`` after fetching.

        The result is always an ``INTEGER`` in the range 0 through 59.

        Args:
            value: The date/time expression whose minute is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(MINUTE FROM <expr>)::INTEGER)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Extract the minute component of a timestamp::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "analytics")
                events = db.events

                rows = events.get_row([
                    events.id,
                    Builtins.Minute(events.occurred_at),
                ])
                # SELECT "events"."id",
                #        (EXTRACT(MINUTE FROM "events"."occurred_at")::INTEGER)
                # FROM "events"
                # -> [(1, 42), (2, 0), (3, 15), ...]

            Filter events in the last 5 minutes of an hour::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.Minute(events.occurred_at) >= 55,
                )
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # WHERE ((EXTRACT(MINUTE FROM "events"."occurred_at")::INTEGER) >= %s)
                # Parameters: [55]

            Bucket events by 15-minute intervals — combine with
            integer division on the extracted minute::

                minute = Builtins.Minute(events.occurred_at)
                bucket = Builtins.Int(minute / 15) * 15
                rows = events.get_row([events.id, bucket])
                # SELECT "events"."id",
                #        ((CAST(((EXTRACT(MINUTE FROM "events"."occurred_at")::INTEGER) / %s)
                #                AS INTEGER)) * %s)
                # FROM "events"
                # Parameters: [15, 15]
                # -> [(1, 30), (2, 0), (3, 45), ...]

            Detect the top of the hour — a common "cleanup" filter::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Minute(events.occurred_at) == 0,
                )
                # SELECT "events"."id" FROM "events"
                # WHERE ((EXTRACT(MINUTE FROM "events"."occurred_at")::INTEGER) = %s)
                # Parameters: [0]

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
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # ORDER BY (EXTRACT(MINUTE FROM "events"."occurred_at")::INTEGER)

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.Minute('2024-03-15 09:30:42'),  # -> 30
                    Builtins.Minute(Builtins.Now()),          # -> current minute
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'(EXTRACT(MINUTE FROM {sql})::INTEGER)', p, int, c)

    @staticmethod
    def Second(value):
        """Extract the second (0–59) from a date/time value.

        Generates an ``EXTRACT(SECOND FROM <expr>)::INTEGER`` expression.
        PostgreSQL's ``EXTRACT(SECOND ...)`` returns a ``NUMERIC`` that
        includes fractional seconds (e.g. ``42.123456`` for a
        ``TIMESTAMP(6)``). The explicit ``::INTEGER`` cast truncates the
        fractional part, giving a plain Python ``int`` in the range 0
        through 59.

        To retain the fractional seconds, cast the result to ``DOUBLE
        PRECISION`` instead — use :meth:`Builtins.Func` with
        ``'EXTRACT'``, or fetch the raw value and format in Python.

        The result is always an ``INTEGER`` in the range 0 through 59.
        PostgreSQL does not represent leap seconds, so the upper bound is
        strictly 59.

        Args:
            value: The date/time expression whose second is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(SECOND FROM <expr>)::INTEGER)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Extract the second component of a timestamp::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "analytics")
                events = db.events

                rows = events.get_row([
                    events.id,
                    events.occurred_at,
                    Builtins.Second(events.occurred_at),
                ])
                # SELECT "events"."id", "events"."occurred_at",
                #        (EXTRACT(SECOND FROM "events"."occurred_at")::INTEGER)
                # FROM "events"
                # -> [(1, datetime(2024, 3, 15, 9, 30, 42), 42), ...]

            Find events that landed on a round minute — second == 0::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.Second(events.occurred_at) == 0,
                )
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # WHERE ((EXTRACT(SECOND FROM "events"."occurred_at")::INTEGER) = %s)
                # Parameters: [0]

            Detect rapid-fire activity — events within the first 5 seconds
            of each minute::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Second(events.occurred_at) < 5,
                )
                # SELECT "events"."id" FROM "events"
                # WHERE ((EXTRACT(SECOND FROM "events"."occurred_at")::INTEGER) < %s)
                # Parameters: [5]

            Reconstruct a full HH:MM:SS display from components — combine
            with :meth:`Hour`, :meth:`Minute`, and :meth:`Format`::

                hh = Builtins.Hour(events.occurred_at)
                mm = Builtins.Minute(events.occurred_at)
                ss = Builtins.Second(events.occurred_at)
                display = Builtins.Format('%s:%s:%s', hh, mm, ss)
                rows = events.get_row([events.id, display])
                # SELECT "events"."id",
                #        (FORMAT(%s,
                #                (EXTRACT(HOUR FROM "events"."occurred_at")::INTEGER),
                #                (EXTRACT(MINUTE FROM "events"."occurred_at")::INTEGER),
                #                (EXTRACT(SECOND FROM "events"."occurred_at")::INTEGER)))
                # FROM "events"
                # Parameters: ['%s:%s:%s']
                # -> [(1, '9:30:42'), (2, '9:30:43'), ...]

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
                # SELECT "events"."id" FROM "events"
                # WHERE ((EXTRACT(SECOND FROM "events"."started_at")::INTEGER)
                #        = (EXTRACT(SECOND FROM "events"."finished_at")::INTEGER))

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.Second('2024-03-15 09:30:42'),  # -> 42
                    Builtins.Second(Builtins.Now()),          # -> current second
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'(EXTRACT(SECOND FROM {sql})::INTEGER)', p, int, c)

    @staticmethod
    def DayOfWeek(value):
        """Extract the day-of-week number using PostgreSQL's ``DOW`` convention.

        Generates an ``EXTRACT(DOW FROM <expr>)::INTEGER`` expression.
        PostgreSQL's ``EXTRACT(DOW FROM ...)`` returns a number in the
        range 0 through 6 using the following convention:

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
            This is the **PostgreSQL / POSIX** convention, not Python's.
            Python's ``date.weekday()`` returns 0 for Monday, and
            ``date.isoweekday()`` returns 1 for Monday. If you want Python
            semantics, use :meth:`Weekday` instead. If you want ISO 8601
            semantics (1 = Monday, 7 = Sunday), use :meth:`IsoWeekday`.

        The result is always an ``INTEGER`` in the range 0 through 6.

        Args:
            value: The date/time expression whose weekday is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(DOW FROM <expr>)::INTEGER)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Filter for Sundays — in PostgreSQL's convention, Sunday is 0::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "analytics")
                events = db.events

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.DayOfWeek(events.occurred_at) == 0,
                )
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # WHERE ((EXTRACT(DOW FROM "events"."occurred_at")::INTEGER) = %s)
                # Parameters: [0]

            Weekend filter — Saturday (6) or Sunday (0)::

                dow = Builtins.DayOfWeek(events.occurred_at)
                rows = events.get_row(
                    [events.id],
                    where=(dow == 0) | (dow == 6),
                )
                # SELECT "events"."id" FROM "events"
                # WHERE (((EXTRACT(DOW FROM "events"."occurred_at")::INTEGER) = %s)
                #        OR ((EXTRACT(DOW FROM "events"."occurred_at")::INTEGER) = %s))
                # Parameters: [0, 6]

            Weekday-only filter — Monday through Friday (1..5)::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Between(
                        Builtins.DayOfWeek(events.occurred_at), 1, 5
                    ),
                )
                # SELECT "events"."id" FROM "events"
                # WHERE (((EXTRACT(DOW FROM "events"."occurred_at")::INTEGER))
                #        BETWEEN %s AND %s)
                # Parameters: [1, 5]

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
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # ORDER BY (EXTRACT(DOW FROM "events"."occurred_at")::INTEGER)

            Build a readable day name via ``IIf``::

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
                    Builtins.DayOfWeek('2024-03-15'),  # -> 5 (Friday)
                    Builtins.DayOfWeek(Builtins.Now()),  # -> current DOW
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'(EXTRACT(DOW FROM {sql})::INTEGER)', p, int, c)

    @staticmethod
    def IsoWeekday(value):
        """Extract the ISO 8601 weekday (1 = Monday, 7 = Sunday).

        Generates an ``EXTRACT(ISODOW FROM <expr>)::INTEGER`` expression.
        PostgreSQL's ``ISODOW`` field is a native companion to ``DOW`` that
        returns the ISO 8601 weekday number directly:

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

        This matches Python's ``datetime.date.isoweekday()`` method and
        the ISO 8601 standard. Because PostgreSQL provides ``ISODOW`` as a
        first-class field, this helper is a direct extraction — no modulo
        arithmetic is involved, unlike the SQLite backend's equivalent.

        Use this method when you want an unambiguous 1-based weekday
        number. ISO 8601 uses this convention throughout its date and
        duration standards, so it is the "neutral" choice when talking to
        systems that have no Python or PostgreSQL heritage.

        Args:
            value: The date/time expression whose ISO weekday is
                extracted. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(ISODOW FROM <expr>)::INTEGER)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Filter for Mondays — ``== 1`` in ISO convention::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "analytics")
                events = db.events

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.IsoWeekday(events.occurred_at) == 1,
                )
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # WHERE ((EXTRACT(ISODOW FROM "events"."occurred_at")::INTEGER) = %s)
                # Parameters: [1]

            Weekend filter — ISO 6 (Saturday) or 7 (Sunday)::

                dow = Builtins.IsoWeekday(events.occurred_at)
                rows = events.get_row(
                    [events.id],
                    where=(dow == 6) | (dow == 7),
                )
                # SELECT "events"."id" FROM "events"
                # WHERE (((EXTRACT(ISODOW FROM "events"."occurred_at")::INTEGER) = %s)
                #        OR ((EXTRACT(ISODOW FROM "events"."occurred_at")::INTEGER) = %s))
                # Parameters: [6, 7]

            Weekday-only filter — Monday through Friday (1..5)::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Between(
                        Builtins.IsoWeekday(events.occurred_at), 1, 5
                    ),
                )
                # SELECT "events"."id" FROM "events"
                # WHERE (((EXTRACT(ISODOW FROM "events"."occurred_at")::INTEGER))
                #        BETWEEN %s AND %s)
                # Parameters: [1, 5]

            ISO weekday histogram — 1 through 7 in ISO order::

                rows = events.get_row([Builtins.IsoWeekday(events.occurred_at)])
                from collections import Counter
                by_dow = Counter(w for (w,) in rows)
                # {1: 42, 2: 38, 3: 40, 4: 45, 5: 44, 6: 15, 7: 22}
                # Monday through Sunday, 1-based

            Build a readable day name via ``IIf`` — ISO order::

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

            Order by ISO weekday::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    order_by=Builtins.IsoWeekday(events.occurred_at),
                )
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # ORDER BY (EXTRACT(ISODOW FROM "events"."occurred_at")::INTEGER)

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.IsoWeekday('2024-03-15'),  # -> 5 (Friday)
                    Builtins.IsoWeekday(Builtins.Now()),  # -> current ISO DOW
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'(EXTRACT(ISODOW FROM {sql})::INTEGER)', p, int, c)

    @staticmethod
    def Weekday(value):
        """Extract the Python-style weekday (0 = Monday, 6 = Sunday).

        Generates an expression that converts PostgreSQL's Sunday-based
        ``DOW`` convention into Python's Monday-based weekday convention:

        .. code-block:: sql

            (EXTRACT(DOW FROM <expr>)::INTEGER + 6) % 7

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
        same as Python code. Use :meth:`DayOfWeek` when you need
        PostgreSQL's native convention, and :meth:`IsoWeekday` when you
        need ISO 8601 (1 = Monday, 7 = Sunday).

        The result is always an ``INTEGER`` in the range 0 through 6.

        Args:
            value: The date/time expression whose Python-style weekday is
                extracted. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``((EXTRACT(DOW FROM <expr>)::INTEGER + 6) % 7)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Filter for Mondays — ``== 0`` matches Python's convention::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "analytics")
                events = db.events

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.Weekday(events.occurred_at) == 0,
                )
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # WHERE (((EXTRACT(DOW FROM "events"."occurred_at")::INTEGER + %s) % %s) = %s)
                # Parameters: [6, 7, 0]

            Weekend filter — Saturday (5) or Sunday (6):::

                dow = Builtins.Weekday(events.occurred_at)
                rows = events.get_row(
                    [events.id],
                    where=(dow == 5) | (dow == 6),
                )
                # SELECT "events"."id" FROM "events"
                # WHERE ((((EXTRACT(DOW FROM "events"."occurred_at")::INTEGER + %s) % %s) = %s)
                #        OR (((EXTRACT(DOW FROM "events"."occurred_at")::INTEGER + %s) % %s) = %s))
                # Parameters: [6, 7, 5, 6, 7, 6]

            Weekday-only filter — Monday through Friday (0..4)::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Between(
                        Builtins.Weekday(events.occurred_at), 0, 4
                    ),
                )
                # SELECT "events"."id" FROM "events"
                # WHERE ((((EXTRACT(DOW FROM "events"."occurred_at")::INTEGER + %s) % %s))
                #        BETWEEN %s AND %s)
                # Parameters: [6, 7, 0, 4]

            Python-style weekday histogram::

                rows = events.get_row([Builtins.Weekday(events.occurred_at)])
                from collections import Counter
                by_dow = Counter(w for (w,) in rows)
                # {0: 42, 1: 38, 2: 40, 3: 45, 4: 44, 5: 15, 6: 22}
                # Monday through Sunday, matching Python's weekday() order

            Same-weekday filter — events that happened on the same
            weekday as today::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Weekday(events.occurred_at)
                        == Builtins.Weekday(Builtins.Now()),
                )
                # SELECT "events"."id" FROM "events"
                # WHERE (((EXTRACT(DOW FROM "events"."occurred_at")::INTEGER + %s) % %s)
                #        = ((EXTRACT(DOW FROM (NOW()))::INTEGER + %s) % %s))
                # Parameters: [6, 7, 6, 7]

            Build a readable day name via ``IIf`` — the list is now in
            Python order::

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
                    Builtins.Weekday('2024-03-15'),  # -> 4 (Friday)
                    Builtins.Weekday(Builtins.Now()),  # -> current Python DOW
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'((EXTRACT(DOW FROM {sql})::INTEGER + 6) % 7)', p, int, c)

    @staticmethod
    def DayOfYear(value):
        """Extract the day of the year (1–366) from a date/time value.

        Generates an ``EXTRACT(DOY FROM <expr>)::INTEGER`` expression.
        PostgreSQL's ``DOY`` field returns the ordinal day of the year,
        1-based. The explicit ``::INTEGER`` cast is required to produce a
        plain Python ``int`` after fetching.

        The result is always an ``INTEGER`` in the range 1 through 366.
        Leap years produce 366; non-leap years produce at most 365.
        PostgreSQL determines leap-ness from the actual input date, so
        this helper is completely accurate across century boundaries.

        Args:
            value: The date/time expression whose ordinal day is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(DOY FROM <expr>)::INTEGER)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Ordinal day for every row — the day of the year, 1-based::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "analytics")
                events = db.events

                rows = events.get_row([
                    events.id,
                    events.occurred_at,
                    Builtins.DayOfYear(events.occurred_at),
                ])
                # SELECT "events"."id", "events"."occurred_at",
                #        (EXTRACT(DOY FROM "events"."occurred_at")::INTEGER)
                # FROM "events"
                # -> [(1, date(2024, 3, 15), 75), ...]

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
                # SELECT "events"."id",
                #        ((EXTRACT(DOY FROM "events"."occurred_at")::INTEGER) % %s)
                # FROM "events"
                # Parameters: [7]

            Filter for the first quarter (days 1 through 91)::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.Between(
                        Builtins.DayOfYear(events.occurred_at), 1, 91
                    ),
                )
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # WHERE (((EXTRACT(DOY FROM "events"."occurred_at")::INTEGER))
                #        BETWEEN %s AND %s)
                # Parameters: [1, 91]

            Year-relative comparison — find all events on the same
            calendar day across different years::

                rows = events.get_row(
                    [events.occurred_at],
                    where=Builtins.DayOfYear(events.occurred_at) == 75,
                )
                # SELECT "events"."occurred_at" FROM "events"
                # WHERE ((EXTRACT(DOY FROM "events"."occurred_at")::INTEGER) = %s)
                # Parameters: [75]
                # -> every March 15 (or March 14 in leap years) regardless
                #    of the year, since DOY shifts by one after Feb 28 in
                #    leap years.

            Sort by position within the year — combines nicely with
            :meth:`Year`::

                rows = events.get_row(
                    [events.occurred_at],
                    order_by=Builtins.DayOfYear(events.occurred_at),
                )
                # SELECT "events"."occurred_at" FROM "events"
                # ORDER BY (EXTRACT(DOY FROM "events"."occurred_at")::INTEGER)

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.DayOfYear('2024-03-15'),  # -> 75
                    Builtins.DayOfYear('2024-12-31'),  # -> 366 (2024 is leap)
                ])
                # SELECT (EXTRACT(DOY FROM %s)::INTEGER),
                #        (EXTRACT(DOY FROM %s)::INTEGER)
                # Parameters: ['2024-03-15', '2024-12-31']
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'(EXTRACT(DOY FROM {sql})::INTEGER)', p, int, c)

    @staticmethod
    def WeekOfYear(value):
        """Extract the ISO 8601 week number (1–53) from a date/time value.

        Generates an ``EXTRACT(WEEK FROM <expr>)::INTEGER`` expression.
        PostgreSQL's ``WEEK`` field returns the ISO 8601 week number —
        **not** the US-style ``%U`` or ``%W`` conventions that SQLite uses.
        The differences are important:

        - **Weeks start on Monday.**
        - **Week 1 is the week containing the first Thursday of the year**
          (equivalently, the week containing January 4th).
        - **The range is 1 through 53** — never 0.

        This means the first few days of January might belong to week 52
        or 53 of the *previous* year, and the last few days of December
        might belong to week 1 of the *next* year. If you need the year
        that a week belongs to, use ``EXTRACT(ISOYEAR FROM ...)`` — the
        ORM exposes this via :meth:`Builtins.Func`:
        ``Func('EXTRACT', col)`` combined with a manual expression, or by
        chaining the year separately.

        The result is always an ``INTEGER`` in the range 1 through 53.

        Args:
            value: The date/time expression whose week-of-year is
                extracted. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(WEEK FROM <expr>)::INTEGER)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Week number for every row::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "analytics")
                events = db.events

                rows = events.get_row([
                    events.id,
                    events.occurred_at,
                    Builtins.WeekOfYear(events.occurred_at),
                ])
                # SELECT "events"."id", "events"."occurred_at",
                #        (EXTRACT(WEEK FROM "events"."occurred_at")::INTEGER)
                # FROM "events"
                # -> [(1, date(2024, 3, 15), 11), ...]

            Weekly histogram — count events per week::

                rows = events.get_row([Builtins.WeekOfYear(events.occurred_at)])
                from collections import Counter
                by_week = Counter(w for (w,) in rows)
                # {1: 45, 2: 52, ..., 11: 22, ..., 53: 1}

            Filter to a specific week — e.g. week 11 of the year::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.WeekOfYear(events.occurred_at) == 11,
                )
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # WHERE ((EXTRACT(WEEK FROM "events"."occurred_at")::INTEGER) = %s)
                # Parameters: [11]

            Filter to the first quarter — weeks 1 through 13::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Between(
                        Builtins.WeekOfYear(events.occurred_at), 1, 13
                    ),
                )
                # SELECT "events"."id" FROM "events"
                # WHERE (((EXTRACT(WEEK FROM "events"."occurred_at")::INTEGER))
                #        BETWEEN %s AND %s)
                # Parameters: [1, 13]

            Build a year-week key for reporting — the ISO-correct year is
            ``ISOYEAR``, not the calendar year. Because ``ISOYEAR`` is not
            exposed by a dedicated helper, this example uses the calendar
            year, which is correct for most (but not all) dates::

                key = Builtins.Format(
                    '%s-W%s',
                    Builtins.Year(events.occurred_at),
                    Builtins.WeekOfYear(events.occurred_at),
                )
                rows = events.get_row([events.id, key])
                # SELECT "events"."id",
                #        (FORMAT(%s,
                #                (EXTRACT(YEAR FROM "events"."occurred_at")::INTEGER),
                #                (EXTRACT(WEEK FROM "events"."occurred_at")::INTEGER)))
                # FROM "events"
                # Parameters: ['%s-W%s']
                # -> [(1, '2024-W11'), (2, '2024-W11'), (3, '2024-W12'), ...]

            Order by week — chronological grouping within the year::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    order_by=Builtins.WeekOfYear(events.occurred_at),
                )
                # SELECT "events"."id", "events"."occurred_at"
                # FROM "events"
                # ORDER BY (EXTRACT(WEEK FROM "events"."occurred_at")::INTEGER)

            Applied to a raw literal — note that ISO semantics may put
            early January in the previous year's week::

                rows = events.get_row([
                    Builtins.WeekOfYear('2024-01-01'),  # -> 1 (Mon 2024-01-01 starts ISO week 1)
                    Builtins.WeekOfYear('2023-01-01'),  # -> 52 (Sun, belongs to 2022's last week)
                    Builtins.WeekOfYear('2024-03-15'),  # -> 11
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'(EXTRACT(WEEK FROM {sql})::INTEGER)', p, int, c)

    @staticmethod
    def Now(_=None):
        """Return the current moment as a ``TIMESTAMPTZ`` value.

        Generates a ``NOW()`` expression. PostgreSQL's ``NOW()`` returns
        the start time of the current transaction as a ``TIMESTAMP WITH
        TIME ZONE``. This means every call to ``Now()`` within a single
        transaction returns the same value — even if the wall-clock time
        has advanced during the transaction. This is the SQL standard
        behaviour and is usually what you want for consistency.

        To get the actual wall-clock time that changes within a
        transaction, use ``CLOCK_TIMESTAMP()`` via
        :meth:`Builtins.Func`: ``Func('CLOCK_TIMESTAMP', 'x')`` (the
        argument is ignored). The difference matters for long-running
        transactions and audit logs.

        The result is a real Python ``datetime.datetime`` with a
        ``tzinfo`` (usually UTC) after fetching.

        The optional positional argument ``_`` exists only to make the
        signature uniform with the other date/time helpers and to allow
        the callable to be passed to APIs that expect a one-argument
        function. It is ignored.

        Args:
            _: Ignored. Any value passed is discarded; the SQL emitted is
                always ``NOW()``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(NOW())`` and whose ``current_datatype`` is ``str``. The
            parameter list is always empty.

        Example:
            The current timestamp as a SELECT column::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([Builtins.Now()])
                # SELECT (NOW()) FROM "users"
                # -> [(datetime(2024, 3, 15, 14, 30, 42,
                #               tzinfo=datetime.timezone.utc),)]
                # Same value for every row, because PostgreSQL evaluates
                # NOW() once per transaction, not per row.

            Compute account age in days — combine with
            :meth:`DateDiffDays`::

                age = Builtins.DateDiffDays(Builtins.Now(), users.created_at)
                rows = users.get_row([users.username, age])
                # SELECT "users"."username",
                #        (CAST(EXTRACT(EPOCH FROM
                #                       (CAST((NOW()) AS TIMESTAMP)
                #                        - CAST("users"."created_at" AS TIMESTAMP)))
                #              / %s
                #              AS INTEGER))
                # FROM "users"
                # Parameters: [86400]

            Compute account age in a human-readable format — combine with
            :meth:`Timediff`::

                age_str = Builtins.Timediff(Builtins.Now(), users.created_at)
                rows = users.get_row([users.username, age_str])
                # -> [('Alice', '2 days 05:29:18'), ...]

            Filter rows updated in the last hour — combine with
            :meth:`DateDiffSeconds`::

                rows = users.get_row(
                    [users.username, users.updated_at],
                    where=Builtins.DateDiffSeconds(
                        Builtins.Now(), users.updated_at
                    ) < 3600,
                )
                # SELECT "users"."username", "users"."updated_at"
                # FROM "users"
                # WHERE ((CAST(EXTRACT(EPOCH FROM
                #                       (CAST((NOW()) AS TIMESTAMP)
                #                        - CAST("users"."updated_at" AS TIMESTAMP)))
                #              AS BIGINT)) < %s)
                # Parameters: [3600]

            Store the current timestamp during an UPDATE::

                users.update(
                    update={users.last_seen: Builtins.Now()},
                    where=users.id == 42,
                )
                # UPDATE "users" SET "last_seen" = (NOW())
                # WHERE ("users"."id" = %s);
                # Parameters: [42]

            Compare two ``Now()`` calls to see that both evaluate to the
            same moment within a single transaction — useful for
            validating cache keys::

                rows = users.get_row([
                    Builtins.Now(),
                    Builtins.Now(),
                ])
                # SELECT (NOW()), (NOW()) FROM "users"
                # Both columns are identical.

            Local-time variant — pass ``'localtime'`` at the SQL level
            using :meth:`Func` — PostgreSQL does not support the SQLite
            ``'localtime'`` modifier, so this must be done in Python::

                import datetime
                # Fetch as UTC, convert in Python:
                rows = users.get_row([Builtins.Now()])
                local = rows[0][0].astimezone()  # to the local timezone
        """
        return Builtins._make('(NOW())', [], str, Builtins._NullCol)
    
    @staticmethod
    def Today(_=None):
        """Return the current date as a ``DATE`` value (from ``CURRENT_DATE``).

        Generates a ``CURRENT_DATE`` expression, which PostgreSQL returns
        as a ``DATE`` value — the calendar date in the session's time
        zone (usually the server's, unless ``SET TIME ZONE`` was issued).
        This is the date-only counterpart of :meth:`Now`.

        Unlike SQLite, PostgreSQL does not require a string keyword like
        ``'now'`` — ``CURRENT_DATE`` is a true SQL keyword that yields a
        native ``DATE`` type. After fetching, psycopg delivers the value
        as a Python ``datetime.date`` object, ready for direct comparison
        with other ``date`` values or for arithmetic.

        The optional positional argument ``_`` exists only to make the
        signature uniform with the other date/time helpers and to allow
        the callable to be passed to APIs that expect a one-argument
        function. It is ignored.

        Args:
            _: Ignored. Any value passed is discarded; the SQL emitted is
                always ``CURRENT_DATE``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CURRENT_DATE)`` and whose ``current_datatype`` is ``str``.
            The parameter list is always empty.

        Example:
            The current date as a SELECT column::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([Builtins.Today()])
                # SELECT (CURRENT_DATE) FROM "users"
                # -> [(date(2024, 3, 15),)]

            Find users who signed up today — cast the timestamp column
            to DATE and compare to the current date::

                rows = users.get_row(
                    [users.username, users.created_at],
                    where=Builtins.Date(users.created_at) == Builtins.Today(),
                )
                # SELECT "users"."username", "users"."created_at"
                # FROM "users"
                # WHERE ((CAST("users"."created_at" AS DATE)) = (CURRENT_DATE))

            Same-day boolean flag via ``IIf``::

                is_today = Builtins.IIf(
                    Builtins.Date(users.created_at) == Builtins.Today(),
                    'new',
                    'old',
                )
                rows = users.get_row([users.username, is_today])
                # SELECT "users"."username",
                #        (CASE WHEN ((CAST("users"."created_at" AS DATE))
                #                    = (CURRENT_DATE))
                #              THEN %s ELSE %s END)
                # FROM "users"
                # Parameters: ['new', 'old']

            Store today's date in an UPDATE — most useful against a
            column declared as ``DATE``::

                users.update(
                    update={users.last_active_date: Builtins.Today()},
                    where=users.id == 42,
                )
                # UPDATE "users" SET "last_active_date" = (CURRENT_DATE)
                # WHERE ("users"."id" = %s);
                # Parameters: [42]

            Yesterday's date — chain with a modifier via
            :meth:`DateAdd`::

                yesterday = Builtins.DateAdd(Builtins.Today(), '-1 day')
                rows = users.get_row([yesterday])
                # SELECT (CAST((CAST((CURRENT_DATE) AS TIMESTAMP)
                #               + %s::interval) AS DATE))
                # FROM "users"
                # Parameters: ['-1 day']
                # -> [(date(2024, 3, 14),)]

            First day of the current month — useful for month-to-date
            reporting. PostgreSQL has no ``'start of month'`` modifier,
            so this uses ``DATE_TRUNC`` via :meth:`Func`::

                month_start = Builtins.Func('DATE_TRUNC', users.created_at)
                # NOTE: DATE_TRUNC requires a unit argument. Build it
                # manually via Column expressions or a raw query.
                # The idiomatic PostgreSQL form is:
                #   DATE_TRUNC('month', CURRENT_DATE)::DATE
                # which is not expressible through Func alone.

            Count users who signed up today — via a conditional SUM::

                today_count = Builtins.Sum(
                    Builtins.IIf(
                        Builtins.Date(users.created_at) == Builtins.Today(),
                        1,
                        0,
                    )
                )
                rows = users.get_row([today_count])
                # SELECT (SUM((CASE WHEN ((CAST("users"."created_at" AS DATE))
                #                        = (CURRENT_DATE))
                #                   THEN %s ELSE %s END)))
                # FROM "users"
                # Parameters: [1, 0]
                # -> [(8,)] if 8 users signed up today

            Compare against a fixed date literal::

                rows = users.get_row(
                    [users.username],
                    where=Builtins.Today() > Builtins.Date('2024-01-01'),
                )
                # SELECT "users"."username" FROM "users"
                # WHERE ((CURRENT_DATE) > (CAST(%s AS DATE)))
                # Parameters: ['2024-01-01']
        """
        return Builtins._make('(CURRENT_DATE)', [], str, Builtins._NullCol)

    @staticmethod
    def UnixNow(_=None):
        """Return the current moment as an integer Unix timestamp.

        Generates an ``EXTRACT(EPOCH FROM NOW())::BIGINT`` expression.
        The result is an INTEGER equal to the number of whole seconds
        since the Unix epoch (midnight UTC on 1 January 1970), matching
        Python's ``int(time.time())`` — except that PostgreSQL's ``NOW()``
        returns the *transaction start* time rather than the wall-clock
        moment, so the value is consistent across all calls within a
        single transaction.

        This is the numeric counterpart of :meth:`Now`. Because the
        result is a plain integer, it is the best choice for cache keys,
        request IDs, expiry timestamps, and any arithmetic that needs
        sub-day precision without floating-point round-off. It also
        compares directly with `int` values in Python without conversion
        after fetching.

        The optional positional argument ``_`` exists only to make the
        signature uniform with the other date/time helpers; it is
        ignored.

        Args:
            _: Ignored. Any value passed is discarded; the SQL emitted is
                always ``EXTRACT(EPOCH FROM NOW())::BIGINT``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(EPOCH FROM NOW())::BIGINT)`` and whose
            ``current_datatype`` is ``int``. The parameter list is always
            empty.

        Example:
            Current Unix timestamp as a SELECT column::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([Builtins.UnixNow()])
                # SELECT (EXTRACT(EPOCH FROM NOW())::BIGINT) FROM "users"
                # -> [(1710513042,)]

            Compute account age in seconds without any date parsing::

                age_secs = (Builtins.UnixNow()
                            - Builtins.UnixEpoch(users.created_at))
                rows = users.get_row([users.username, age_secs])
                # SELECT "users"."username",
                #        ((EXTRACT(EPOCH FROM NOW())::BIGINT)
                #         - (EXTRACT(EPOCH FROM "users"."created_at")::BIGINT))
                # FROM "users"
                # -> [('Alice', 6394842), ('Bob', 1036800), ...]

            Filter users who signed up in the last 24 hours::

                rows = users.get_row(
                    [users.username, users.created_at],
                    where=Builtins.UnixNow()
                        - Builtins.UnixEpoch(users.created_at) < 86400,
                )
                # SELECT "users"."username", "users"."created_at"
                # FROM "users"
                # WHERE (((EXTRACT(EPOCH FROM NOW())::BIGINT)
                #         - (EXTRACT(EPOCH FROM "users"."created_at")::BIGINT))
                #        < %s)
                # Parameters: [86400]

            Generate a per-request cache key — combine with a user id::

                cache_key = Builtins.Format(
                    'user:%s:%s',
                    users.id,
                    Builtins.UnixNow(),
                )
                rows = users.get_row([cache_key])
                # SELECT (FORMAT(%s, "users"."id",
                #                (EXTRACT(EPOCH FROM NOW())::BIGINT)))
                # FROM "users"
                # Parameters: ['user:%s:%s']
                # -> [('user:42:1710513042',), ...]

            Store the current epoch in an UPDATE — useful for
            portability-friendly integer columns::

                users.update(
                    update={users.last_login_epoch: Builtins.UnixNow()},
                    where=users.id == 42,
                )
                # UPDATE "users"
                # SET "last_login_epoch" = (EXTRACT(EPOCH FROM NOW())::BIGINT)
                # WHERE ("users"."id" = %s);
                # Parameters: [42]

            Compute a future expiry — a session token valid for 1 hour::

                expires_at = Builtins.UnixNow() + 3600
                rows = users.get_row([users.id, expires_at])
                # SELECT "users"."id",
                #        ((EXTRACT(EPOCH FROM NOW())::BIGINT) + %s)
                # FROM "users"
                # Parameters: [3600]
                # -> [(1, 1710516642), ...]

            Set a session expiry during an UPDATE, then check it with a
            plain integer comparison::

                users.update(
                    update={users.token_expires: Builtins.UnixNow() + 3600},
                    where=users.id == 42,
                )

                # Later, filter expired sessions:
                import time
                now_epoch = int(time.time())
                expired = users.get_row(
                    [users.id],
                    where=users.token_expires < now_epoch,
                )
                # SELECT "users"."id" FROM "users"
                # WHERE ("users"."token_expires" < %s)
                # Parameters: [1710516642]
        """
        return Builtins._make(
            '(EXTRACT(EPOCH FROM NOW())::BIGINT)', [], int, Builtins._NullCol)

    @staticmethod
    def UnixEpoch(value):
        """Convert a date/time value to a Unix timestamp.

        Generates an ``EXTRACT(EPOCH FROM <expr>)::BIGINT`` expression.
        The result is an INTEGER equal to the number of whole seconds
        since the Unix epoch (midnight UTC on 1 January 1970). The
        explicit ``::BIGINT`` cast ensures the value arrives in Python as
        a plain ``int`` rather than a ``decimal.Decimal`` (which is what
        ``EXTRACT`` returns by default) and truncates any fractional
        seconds.

        This works against any input PostgreSQL can interpret as a
        timestamp — a ``TIMESTAMP`` column, a ``TIMESTAMPTZ`` column, an
        ISO 8601 text literal, or the result of another builtin like
        :meth:`Now`. For ``TIMESTAMPTZ``, the time zone is normalised to
        UTC automatically; for plain ``TIMESTAMP``, PostgreSQL treats the
        value as UTC, which is usually what you want for storage.

        Args:
            value: The date/time expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(EPOCH FROM <expr>)::BIGINT)`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Display the raw epoch value alongside a timestamp::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([
                    users.created_at,
                    Builtins.UnixEpoch(users.created_at),
                ])
                # SELECT "users"."created_at",
                #        (EXTRACT(EPOCH FROM "users"."created_at")::BIGINT)
                # FROM "users"
                # -> [(datetime(2024, 3, 15, 9, 30, 42), 1710495042), ...]

            Compute elapsed seconds since signup::

                elapsed = (Builtins.UnixNow()
                           - Builtins.UnixEpoch(users.created_at))
                rows = users.get_row([users.username, elapsed])
                # SELECT "users"."username",
                #        ((EXTRACT(EPOCH FROM NOW())::BIGINT)
                #         - (EXTRACT(EPOCH FROM "users"."created_at")::BIGINT))
                # FROM "users"

            Elapsed days — divide by 86400::

                days = ((Builtins.UnixNow()
                         - Builtins.UnixEpoch(users.created_at))
                        / 86400)
                rows = users.get_row([users.username, days])
                # SELECT "users"."username",
                #        (((EXTRACT(EPOCH FROM NOW())::BIGINT)
                #          - (EXTRACT(EPOCH FROM "users"."created_at")::BIGINT))
                #         / %s)
                # FROM "users"
                # Parameters: [86400]
                # Note: integer division in PostgreSQL truncates — for a
                # fractional day count use Builtins.Float on one operand.

            Filter by an absolute cutoff timestamp::

                cutoff = 1704067200   # 2024-01-01 00:00:00 UTC
                rows = users.get_row(
                    [users.username],
                    where=Builtins.UnixEpoch(users.created_at) > cutoff,
                )
                # SELECT "users"."username" FROM "users"
                # WHERE ((EXTRACT(EPOCH FROM "users"."created_at")::BIGINT) > %s)
                # Parameters: [1704067200]

            Store a timestamp as an integer during an UPDATE — useful
            when a column is declared INTEGER for portability::

                users.update(
                    update={users.last_seen_epoch: Builtins.UnixNow()},
                    where=users.id == 42,
                )

            Sort by absolute moment::

                rows = users.get_row(
                    [users.username],
                    order_by=Builtins.UnixEpoch(users.created_at),
                )
                # SELECT "users"."username" FROM "users"
                # ORDER BY (EXTRACT(EPOCH FROM "users"."created_at")::BIGINT)

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.UnixEpoch('2024-03-15 00:00:00'),  # -> 1710460800
                    Builtins.UnixEpoch('1970-01-01 00:00:00'),  # -> 0
                ])
                # SELECT (EXTRACT(EPOCH FROM %s)::BIGINT),
                #        (EXTRACT(EPOCH FROM %s)::BIGINT)
                # Parameters: ['2024-03-15 00:00:00', '1970-01-01 00:00:00']
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(
            f'(EXTRACT(EPOCH FROM {sql})::BIGINT)', p, int, c)

    @staticmethod
    def JulianDay(value):
        """Convert a date/time value to its Julian day number.

        Generates an ``EXTRACT(JULIAN FROM <expr>)`` expression.
        PostgreSQL returns the value as a ``NUMERIC`` representing days
        since noon UTC on 24 November 4714 BC in the proleptic Gregorian
        calendar — the same numbering astronomers use and the same
        convention as SQLite's ``julianday()``.

        Because the result is a plain number, it is ideal for arithmetic
        that spans days, months, or years. Subtracting two Julian day
        numbers yields the number of days between two moments, with a
        fractional part for the hours. The Julian day number changes at
        **noon** UTC, not midnight, so fractional values represent the
        fraction of the day since the last noon boundary.

        Args:
            value: The date/time expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(EXTRACT(JULIAN FROM <expr>))`` and whose
            ``current_datatype`` is always ``float``. PostgreSQL returns
            a NUMERIC, but the ORM declares ``float`` so downstream
            arithmetic stays in the floating-point domain.

        Example:
            Inspect the underlying numeric value of a timestamp::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([
                    users.created_at,
                    Builtins.JulianDay(users.created_at),
                ])
                # SELECT "users"."created_at",
                #        (EXTRACT(JULIAN FROM "users"."created_at"))
                # FROM "users"
                # -> [(datetime(2024, 3, 15, 9, 30, 42), 2460385.89...), ...]

            Day count between two dates — the classic
            ``julianday(b) - julianday(a)`` idiom::

                days_between = (
                    Builtins.JulianDay(users.created_at)
                    - Builtins.JulianDay('2024-01-01')
                )
                rows = users.get_row([
                    users.username,
                    days_between,
                ])
                # SELECT "users"."username",
                #        ((EXTRACT(JULIAN FROM "users"."created_at"))
                #         - (EXTRACT(JULIAN FROM %s)))
                # FROM "users"
                # Parameters: ['2024-01-01']
                # -> [('Alice', 74.396...), ('Bob', 12.184...), ...]

            Whole-day version — cast to INTEGER to drop the fractional
            part. See :meth:`DateDiffDays` for a ready-made helper::

                whole_days = Builtins.Int(
                    Builtins.JulianDay(users.created_at)
                    - Builtins.JulianDay('2024-01-01')
                )
                # -> [('Alice', 74), ('Bob', 12), ...]

            Fractional hours since an event::

                hours_since = (
                    Builtins.JulianDay(Builtins.Now())
                    - Builtins.JulianDay(users.last_seen)
                ) * 24
                rows = users.get_row([users.username, hours_since])
                # SELECT "users"."username",
                #        (((EXTRACT(JULIAN FROM (NOW())))
                #          - (EXTRACT(JULIAN FROM "users"."last_seen"))) * %s)
                # FROM "users"
                # Parameters: [24]

            Sort by actual moment in time — Julian day numbers sort
            identically to the underlying timestamps::

                rows = users.get_row(
                    [users.username, users.created_at],
                    order_by=Builtins.JulianDay(users.created_at),
                )
                # SELECT "users"."username", "users"."created_at"
                # FROM "users"
                # ORDER BY (EXTRACT(JULIAN FROM "users"."created_at"))

            Compare against a threshold expressed in days::

                rows = users.get_row(
                    [users.username],
                    where=Builtins.JulianDay(Builtins.Now())
                        - Builtins.JulianDay(users.created_at) < 7,
                )
                # -> users who signed up in the last week

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.JulianDay('2024-03-15'),   # -> 2460384.5
                    Builtins.JulianDay(Builtins.Now()),  # -> current Julian day
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(EXTRACT(JULIAN FROM {sql}))', p, float, c)

    @staticmethod
    def Strftime(fmt, value):
        """Format a date/time value according to a template string.

        Generates a ``TO_CHAR(<expr>, <fmt>)`` expression. This is the SQL
        analogue of Python's ``datetime.strftime()`` method — but
        PostgreSQL uses its own template syntax, which is **not**
        interchangeable with Python's or SQLite's:

        ==================  =============  =================
        Meaning             Python/SQLite  PostgreSQL
        ==================  =============  =================
        Four-digit year     %Y             YYYY
        Two-digit year      %y             YY
        Month number        %m             MM
        Month name          %B             Month
        Abbreviated month   %b             Mon
        Day of month        %d             DD
        Day name            %A             Day
        Abbreviated day     %a             Dy
        Hour (24-hour)      %H             HH24
        Hour (12-hour)      %I             HH12
        Minute              %M             MI
        Second              %S             SS
        Millisecond         —              MS
        Microsecond         —              US
        AM/PM               %p             AM
        Literal percent     %%             (no escape)
        ==================  =============  =================

        The most common pitfall is that ``MI`` is minutes and ``MM`` is
        months — the reverse of Python where ``%m`` is month and ``%M`` is
        minute. Another pitfall is that literal text in the format string
        must be quoted with double quotes (e.g. ``'YYYY" Q"Q'`` for
        ``2024 Q1``), because unquoted letters are treated as templates.

        The result is always a ``TEXT`` string, so ``+`` chained after it
        produces concatenation (``||``) rather than arithmetic addition.

        Args:
            fmt: The format template. Bound as a ``%s`` parameter, so it
                can be user-supplied safely — though for full safety you
                should validate the template against an allowlist. See
                the table above for the token mapping.

            value: The date/time expression to format. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(TO_CHAR(<expr>, %s))`` and whose ``current_datatype`` is
            ``str``. Parameters are ``value's_parameters + [fmt]``.

        Example:
            Format a timestamp as ``YYYY-MM-DD``::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([
                    users.id,
                    Builtins.Strftime('YYYY-MM-DD', users.created_at),
                ])
                # SELECT "users"."id",
                #        (TO_CHAR("users"."created_at", %s))
                # FROM "users"
                # Parameters: ['YYYY-MM-DD']
                # -> [(1, '2024-03-15'), ...]

            Format a human-readable datetime — hour is ``HH24``, minute
            is ``MI`` (not ``MM``)::

                pretty = Builtins.Strftime(
                    'YYYY-MM-DD HH24:MI:SS',
                    users.created_at,
                )
                rows = users.get_row([users.id, pretty])
                # -> [(1, '2024-03-15 09:30:42'), ...]

            Format only the time portion with AM/PM::

                rows = users.get_row([
                    Builtins.Strftime('HH12:MI AM', users.created_at),
                ])
                # -> [('09:30 AM',), ('02:45 PM',), ...]

            Month-year grouping — useful for reporting::

                month_key = Builtins.Strftime('YYYY-MM', users.created_at)
                rows = users.get_row([month_key])
                from collections import Counter
                monthly = Counter(m for (m,) in rows)
                # {'2024-01': 45, '2024-02': 38, '2024-03': 52, ...}

            Literal text in the format — quoted with double quotes::

                display = Builtins.Strftime(
                    'YYYY" Q"Q',        # -> '2024 Q1'
                    users.created_at,
                )
                rows = users.get_row([display])
                # -> [('2024 Q1',), ...]
                # Note: Q is a template token for the quarter — you must
                # quote it with double quotes when you want a literal.

            Day name and ordinal day — using PostgreSQL's tokens::

                display = Builtins.Strftime(
                    'Day DD of YYYY',    # -> 'Friday 15 of 2024'
                    users.created_at,
                )
                rows = users.get_row([display])

            Filter by formatted year string::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Strftime('YYYY', users.created_at) == '2024',
                )
                # SELECT "users"."id" FROM "users"
                # WHERE ((TO_CHAR("users"."created_at", %s)) = %s)
                # Parameters: ['YYYY', '2024']

            Chain with string methods — ``current_datatype`` is ``str``::

                expr = Builtins.Strftime('YYYY', users.created_at).add_end('-Q1')
                rows = users.get_row([expr])
                # -> '2024-Q1'

            Escape a literal double-quote in the format — a rare need::

                tricky = Builtins.Strftime('YYYY""YY', users.created_at)
                # Produces '2024"24'
                rows = users.get_row([tricky])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(TO_CHAR({sql}, %s))', p + [fmt], str, c)

    @staticmethod
    def Timediff(a, b):
        """Compute the difference between two timestamps as a text interval.

        Generates an expression of the form
        ``(CAST(<a> AS TIMESTAMP) - CAST(<b> AS TIMESTAMP))::text``.
        PostgreSQL's native interval type is fetched by psycopg as a
        ``datetime.timedelta``, which is fine for Python-side arithmetic
        but awkward for direct display. Casting to ``text`` gives a
        human-readable form like ``'2 days 05:29:18'``.

        The result is a ``TEXT`` string describing the elapsed time
        between ``a`` and ``b``. Sign convention: the result is
        ``a - b``. A positive interval means ``a`` occurs after ``b``;
        a negative interval means ``a`` occurs before ``b``. When ``a``
        and ``b`` are within the same day, the day part is omitted.

        PostgreSQL's interval text format:

        .. code-block:: text

            1 year 2 months 3 days 04:05:06
            2 days 05:29:18
            00:00:42
            -1 days -04:05:06

        For numeric differences in days or seconds, use
        :meth:`DateDiffDays` or :meth:`DateDiffSeconds` instead — those
        return plain integers ready for arithmetic.

        Args:
            a: The subtrahend — the "later" side of the difference.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

            b: The minuend — the "earlier" side of the difference. Same
                accepted types as ``a``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``((CAST(<a> AS TIMESTAMP) - CAST(<b> AS TIMESTAMP))::text)``
            and whose ``current_datatype`` is always ``str``. Parameters
            are concatenated left-to-right: first ``a``'s, then ``b``'s.

        Example:
            Human-readable account age for every user::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                age = Builtins.Timediff(Builtins.Now(), users.created_at)
                rows = users.get_row([
                    users.username,
                    age,
                ])
                # SELECT "users"."username",
                #        ((CAST((NOW()) AS TIMESTAMP)
                #          - CAST("users"."created_at" AS TIMESTAMP))::text)
                # FROM "users"
                # -> [('Alice', '2 days 05:29:18'), ...]

            Time since last login::

                elapsed = Builtins.Timediff(
                    Builtins.Now(),
                    users.last_login,
                )
                rows = users.get_row([users.username, elapsed])
                # -> [('Alice', '00:15:42'), ('Bob', '3 days 12:04:11'), ...]

            Compare two timestamp columns — session duration::

                session_len = Builtins.Timediff(
                    users.session_ended,
                    users.session_started,
                )
                rows = users.get_row([users.id, session_len])
                # -> [(1, '01:23:45'), ...]

            Sign convention — the order of arguments matters::

                later_minus_earlier = Builtins.Timediff(
                    users.updated_at,      # a
                    users.created_at,      # b
                )
                rows = users.get_row([users.id, later_minus_earlier])
                # -> [(1, '00:30:00'), ...]   (updated after created)

                earlier_minus_later = Builtins.Timediff(
                    users.created_at,      # a
                    users.updated_at,      # b
                )
                rows = users.get_row([users.id, earlier_minus_later])
                # -> [(1, '-00:30:00'), ...]   (created before updated)

            Combine with :meth:`Format` for a prettier display::

                age_str = Builtins.Timediff(Builtins.Now(), users.created_at)
                display = Builtins.Format('Member for %s', age_str)
                rows = users.get_row([users.username, display])
                # -> [('Alice', 'Member for 2 days 05:29:18'), ...]

            Filter by elapsed time — use the numeric helpers instead,
            because interval text does not sort lexicographically in the
            same order as chronologically::

                # Correct:
                recently = (Builtins.DateDiffDays(
                    Builtins.Now(), users.created_at
                ) < 7)
                rows = users.get_row([users.username], where=recently)

            Applied to raw literals::

                rows = users.get_row([
                    Builtins.Timediff('2024-03-15', '2024-03-01'),
                    # -> '14 days'
                    Builtins.Timediff('2024-03-01', '2024-03-15'),
                    # -> '-14 days'
                ])
        """
        s1, p1, _, c = Builtins._normalize(a)
        s2, p2, _, _ = Builtins._normalize(b)
        return Builtins._make(
            f'((CAST({s1} AS TIMESTAMP) - CAST({s2} AS TIMESTAMP))::text)',
            p1 + p2, str, c)

    @staticmethod
    def DateDiffDays(a, b):
        """Compute the number of whole days between two date/time values.

        Generates a
        ``CAST(EXTRACT(EPOCH FROM (CAST(<a> AS TIMESTAMP) - CAST(<b> AS TIMESTAMP))) / 86400 AS INTEGER)``
        expression. The result is the signed day count from ``b`` to
        ``a``:

        - A positive result means ``a`` occurs *after* ``b``.
        - A negative result means ``a`` occurs *before* ``b``.
        - A zero result means the two timestamps fall within the same
          twenty-four-hour window.

        Because the intermediate epoch-seconds value is divided by 86400
        and then cast to integer, the truncation is toward zero — "one
        and a half days" becomes "1", not "2". The count is a *whole*
        day count, not a rounded one.

        This is the natural SQL analogue of Python's
        ``(date_a - date_b).days`` on two ``date`` objects, and matches
        the SQLite ORM's identical helper.

        Args:
            a: The later date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

            b: The earlier date/time expression. Same accepted types as
                ``a``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(EXTRACT(EPOCH FROM (CAST(<a> AS TIMESTAMP)
            - CAST(<b> AS TIMESTAMP))) / 86400 AS INTEGER))`` and whose
            ``current_datatype`` is always ``int``. Parameters are
            concatenated left-to-right: first ``a``'s parameters, then
            ``b``'s.

        Example:
            Account age in days for every user::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                age_days = Builtins.DateDiffDays(Builtins.Now(), users.created_at)
                rows = users.get_row([
                    users.username,
                    age_days,
                ])
                # SELECT "users"."username",
                #        (CAST(EXTRACT(EPOCH FROM
                #                       (CAST((NOW()) AS TIMESTAMP)
                #                        - CAST("users"."created_at" AS TIMESTAMP)))
                #              / %s AS INTEGER))
                # FROM "users"
                # Parameters: [86400]
                # -> [('Alice', 74), ('Bob', 12), ...]

            Filter users who signed up in the last week::

                rows = users.get_row(
                    [users.username, users.created_at],
                    where=Builtins.DateDiffDays(
                        Builtins.Now(), users.created_at
                    ) < 7,
                )
                # SELECT "users"."username", "users"."created_at"
                # FROM "users"
                # WHERE ((CAST(EXTRACT(EPOCH FROM
                #                      (CAST((NOW()) AS TIMESTAMP)
                #                       - CAST("users"."created_at" AS TIMESTAMP)))
                #             / %s AS INTEGER)) < %s)
                # Parameters: [86400, 7]

            Filter users who signed up more than a year ago::

                rows = users.get_row(
                    [users.username],
                    where=Builtins.DateDiffDays(
                        Builtins.Now(), users.created_at
                    ) > 365,
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
                    order_by=Builtins.DateDiffDays(
                        Builtins.Now(), users.created_at
                    ),
                )
                # Smallest day-count (most recent) appears first.

            Detect users who signed up today::

                same_day = (Builtins.DateDiffDays(
                    Builtins.Now(), users.created_at
                ) == 0)
                rows = users.get_row([users.username], where=same_day)

            Sign convention — order of arguments matters::

                # Positive: a is later than b
                pos = Builtins.DateDiffDays('2024-03-15', '2024-03-01')
                # -> 14

                # Negative: a is earlier than b
                neg = Builtins.DateDiffDays('2024-03-01', '2024-03-15')
                # -> -14

            Compare with the fractional-day form — use :meth:`JulianDay`
            for a fractional day count::

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
            f'(CAST(EXTRACT(EPOCH FROM (CAST({s1} AS TIMESTAMP) - CAST({s2} AS TIMESTAMP))) / 86400 AS INTEGER))',
            p1 + p2, int, c)

    @staticmethod
    def DateDiffSeconds(a, b):
        """Compute the number of whole seconds between two date/time values.

        Generates a
        ``CAST(EXTRACT(EPOCH FROM (CAST(<a> AS TIMESTAMP) - CAST(<b> AS TIMESTAMP))) AS BIGINT)``
        expression. The result is the signed second count from ``b`` to
        ``a``:

        - A positive result means ``a`` occurs *after* ``b``.
        - A negative result means ``a`` occurs *before* ``b``.
        - A zero result means the two moments are within the same second.

        The explicit ``::BIGINT`` cast ensures the value arrives in Python
        as a plain ``int`` (not a ``decimal.Decimal``) and truncates the
        fractional seconds toward zero.

        This is the natural SQL analogue of Python's
        ``(datetime_a - datetime_b).total_seconds()`` for whole-second
        precision.

        Args:
            a: The later date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

            b: The earlier date/time expression. Same accepted types as
                ``a``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(EXTRACT(EPOCH FROM (CAST(<a> AS TIMESTAMP)
            - CAST(<b> AS TIMESTAMP)) AS BIGINT))`` and whose
            ``current_datatype`` is always ``int``. Parameters are
            concatenated left-to-right: first ``a``'s parameters, then
            ``b``'s.

        Example:
            Seconds since last login for every user::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                secs = Builtins.DateDiffSeconds(Builtins.Now(), users.last_login)
                rows = users.get_row([
                    users.username,
                    secs,
                ])
                # SELECT "users"."username",
                #        (CAST(EXTRACT(EPOCH FROM
                #                       (CAST((NOW()) AS TIMESTAMP)
                #                        - CAST("users"."last_login" AS TIMESTAMP)))
                #              AS BIGINT))
                # FROM "users"
                # Parameters: []
                # -> [('Alice', 4809), ('Bob', 172800), ...]

            Filter to sessions active in the last hour::

                rows = users.get_row(
                    [users.username, users.last_seen],
                    where=Builtins.DateDiffSeconds(
                        Builtins.Now(), users.last_seen
                    ) < 3600,
                )
                # SELECT "users"."username", "users"."last_seen"
                # FROM "users"
                # WHERE ((CAST(EXTRACT(EPOCH FROM
                #                      (CAST((NOW()) AS TIMESTAMP)
                #                       - CAST("users"."last_seen" AS TIMESTAMP)))
                #             AS BIGINT)) < %s)
                # Parameters: [3600]

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
                    order_by=Builtins.DateDiffSeconds(
                        Builtins.Now(), users.last_seen
                    ),
                )

            Detect users active within the same second::

                same_second = (Builtins.DateDiffSeconds(
                    Builtins.Now(), users.last_seen
                ) == 0)
                rows = users.get_row([users.username], where=same_second)

            Rate limiting pattern — count events in a rolling window::

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
                pos = Builtins.DateDiffSeconds(
                    '2024-03-15 12:00:00', '2024-03-15 11:00:00'
                )
                # -> 3600

                # Negative: a is earlier than b
                neg = Builtins.DateDiffSeconds(
                    '2024-03-15 11:00:00', '2024-03-15 12:00:00'
                )
                # -> -3600
        """
        s1, p1, _, c = Builtins._normalize(a)
        s2, p2, _, _ = Builtins._normalize(b)
        return Builtins._make(
            f'(CAST(EXTRACT(EPOCH FROM (CAST({s1} AS TIMESTAMP) - CAST({s2} AS TIMESTAMP))) AS BIGINT))',
            p1 + p2, int, c)

    @staticmethod
    def DateAdd(value, *intervals):
        """Add one or more PostgreSQL INTERVAL strings to a date and cast to DATE.

        Generates a chain of ``(CAST(<expr> AS TIMESTAMP) + %s::interval)``
        additions, each wrapping the previous result, and finally casts
        the whole expression to ``DATE``:

        .. code-block:: sql

            CAST((CAST(<expr> AS TIMESTAMP)
                  + %s::interval
                  + %s::interval) AS DATE)

        Each interval is bound as a ``%s`` parameter, so user-supplied
        interval strings are safe from SQL injection — though for full
        safety you should validate the interval against an allowlist
        before passing it.

        PostgreSQL interval syntax differs from SQLite's modifier syntax.
        The following forms are accepted:

        - ``'1 day'``, ``'7 days'`` — add days
        - ``'-1 day'`` — subtract a day
        - ``'1 month'``, ``'3 months'`` — add months (PostgreSQL clamps
          end-of-month correctly — Jan 31 + 1 month → Feb 28/29)
        - ``'1 year'`` — add a year
        - ``'2 hours'``, ``'30 minutes'``, ``'15 seconds'`` — add time
        - ``'1 day 2 hours'`` — compound intervals
        - ``'1-2'`` — SQL standard year-month form
        - ``'3 04:05:06'`` — SQL standard day-time form

        SQLite-style tokens like ``'start of month'`` or
        ``'weekday 1'`` are **not** supported. Use ``DATE_TRUNC`` via
        :meth:`Func` for those cases.

        When called with no intervals, this helper degenerates to
        ``CAST(<expr> AS DATE)`` — the same behaviour as :meth:`Date`.
        The separate name exists for the modifier-aware form, but both
        are valid call patterns.

        Args:
            value: The starting date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

            *intervals: Zero or more interval strings, each bound as a
                ``%s`` parameter. Applied left-to-right. See the list
                above for accepted forms.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> + ?::interval + ?::interval AS DATE))`` and
            whose ``current_datatype`` is always ``str``. Parameters are
            concatenated left-to-right: first ``value``'s parameters,
            then the intervals in order.

        Example:
            Tomorrow's date::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([
                    Builtins.DateAdd(Builtins.Today(), '1 day'),
                ])
                # SELECT (CAST((CAST((CURRENT_DATE) AS TIMESTAMP)
                #               + %s::interval) AS DATE))
                # FROM "users"
                # Parameters: ['1 day']
                # -> [(date(2024, 3, 16),)]

            A week from now::

                rows = users.get_row([
                    Builtins.DateAdd(Builtins.Today(), '7 days'),
                ])
                # -> [(date(2024, 3, 22),)]

            First day of the current month — PostgreSQL has no
            ``'start of month'`` modifier, so this uses ``DATE_TRUNC``
            via a raw Func call combined with a Python f-string::

                # Not directly expressible with DateAdd — use Func:
                month_start = Builtins.Func('DATE_TRUNC', Builtins.Today())
                # Note: DATE_TRUNC requires a unit argument. This is a
                # limitation of the single-argument Func helper. The
                # idiomatic form is:
                #   DATE_TRUNC('month', CURRENT_DATE)::DATE

            Previous week relative to a stored timestamp::

                last_week = Builtins.DateAdd(users.created_at, '-7 days')
                rows = users.get_row([users.username, last_week])
                # SELECT "users"."username",
                #        (CAST((CAST("users"."created_at" AS TIMESTAMP)
                #               + %s::interval) AS DATE))
                # FROM "users"
                # Parameters: ['-7 days']

            Chained intervals — one month and one day::

                next_period = Builtins.DateAdd(
                    users.created_at,
                    '1 month',
                    '1 day',
                )
                rows = users.get_row([users.username, next_period])
                # SELECT "users"."username",
                #        (CAST((CAST("users"."created_at" AS TIMESTAMP)
                #               + %s::interval
                #               + %s::interval) AS DATE))
                # FROM "users"
                # Parameters: ['1 month', '1 day']

            Filter events that occurred in the current month::

                month_start = Builtins.DateAdd(Builtins.Today(), '-30 days')
                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Date(users.created_at) >= month_start,
                )
                # SELECT "users"."id", "users"."created_at" FROM "users"
                # WHERE ((CAST("users"."created_at" AS DATE))
                #        >= (CAST((CAST((CURRENT_DATE) AS TIMESTAMP)
                #                  + %s::interval) AS DATE)))
                # Parameters: ['-30 days']

            Birthday reminder — combine a stored date with an annual
            offset. Note that ``'1 year'`` on Feb 29 lands on Feb 28 in
            non-leap years — PostgreSQL handles this correctly::

                next_birthday = Builtins.DateAdd(users.date_of_birth, '1 year')
                rows = users.get_row([users.username, next_birthday])

            Degenerate form — no intervals, same as :meth:`Date`::

                rows = users.get_row([
                    Builtins.DateAdd(users.created_at),   # (CAST(<expr> AS DATE))
                    Builtins.Date(users.created_at),      # (CAST(<expr> AS DATE))
                ])
                # Both columns produce identical SQL and results.
        """
        sql, p, _, c = Builtins._normalize(value)
        if not intervals:
            return Builtins._make(f'(CAST({sql} AS DATE))', p, str, c)
        expr, params = f'CAST({sql} AS TIMESTAMP)', list(p)
        for iv in intervals:
            expr = f'({expr} + %s::interval)'
            params.append(iv)
        return Builtins._make(f'(CAST({expr} AS DATE))', params, str, c)

    @staticmethod
    def DateTimeAdd(value, *intervals):
        """Add one or more PostgreSQL INTERVAL strings to a datetime.

        Generates a chain of ``(CAST(<expr> AS TIMESTAMP) + %s::interval)``
        additions, each wrapping the previous result. Unlike
        :meth:`DateAdd`, this helper does **not** cast the final result
        to ``DATE`` — the result is a full ``TIMESTAMP`` that preserves
        the time-of-day component.

        This is the datetime-producing counterpart of :meth:`DateAdd`:
        same interval set, same chaining semantics, but the result keeps
        the time portion. Use this method whenever the time-of-day
        matters — for example, when computing "one hour from now", when
        the intervals include a time unit (``'2 hours'``, ``'30
        minutes'``, ``'15 seconds'``), or when the base value is a full
        timestamp and you want to preserve it.

        See :meth:`DateAdd` for the complete list of accepted interval
        strings. They are identical for both helpers.

        When called with no intervals, this helper degenerates to
        ``CAST(<expr> AS TIMESTAMP)`` — the same behaviour as
        :meth:`DateTime`.

        Args:
            value: The starting date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

            *intervals: Zero or more interval strings, each bound as a
                ``%s`` parameter. Applied left-to-right, exactly as in
                :meth:`DateAdd`.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS TIMESTAMP) + ?::interval + ?::interval)``
            and whose ``current_datatype`` is always ``str``. Parameters
            are concatenated left-to-right: first ``value``'s parameters,
            then the intervals in order.

        Example:
            One hour from now — the time portion is preserved::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([
                    Builtins.DateTimeAdd(Builtins.Now(), '1 hour'),
                ])
                # SELECT ((CAST((NOW()) AS TIMESTAMP) + %s::interval))
                # FROM "users"
                # Parameters: ['1 hour']
                # -> [(datetime(2024, 3, 15, 15, 30, 42),)]

            Fifteen minutes from now — good for short-lived tokens::

                expiry = Builtins.DateTimeAdd(Builtins.Now(), '15 minutes')
                rows = users.get_row([users.id, expiry])
                # -> [(1, datetime(2024, 3, 15, 14, 45, 42)), ...]

            Last week relative to a stored timestamp::

                last_week = Builtins.DateTimeAdd(users.created_at, '-7 days')
                rows = users.get_row([users.username, last_week])
                # SELECT "users"."username",
                #        ((CAST("users"."created_at" AS TIMESTAMP)
                #          + %s::interval))
                # FROM "users"
                # Parameters: ['-7 days']
                # -> [('Alice', datetime(2024, 3, 8, 9, 30, 42)), ...]

            Chained intervals — a day and a half::

                later = Builtins.DateTimeAdd(
                    users.created_at,
                    '1 day',
                    '12 hours',
                )
                rows = users.get_row([users.username, later])
                # SELECT "users"."username",
                #        ((CAST("users"."created_at" AS TIMESTAMP)
                #          + %s::interval
                #          + %s::interval))
                # FROM "users"
                # Parameters: ['1 day', '12 hours']

            Filter events in the last hour — compare against a computed
            threshold::

                cutoff = Builtins.DateTimeAdd(Builtins.Now(), '-1 hour')
                rows = users.get_row(
                    [users.id, users.created_at],
                    where=users.created_at >= cutoff,
                )
                # SELECT "users"."id", "users"."created_at" FROM "users"
                # WHERE ("users"."created_at"
                #        >= ((CAST((NOW()) AS TIMESTAMP) + %s::interval)))
                # Parameters: ['-1 hour']

            Rolling window of one day — a common "recent activity"
            filter::

                rows = users.get_row(
                    [users.username, users.last_seen],
                    where=Builtins.DateTime(users.last_seen)
                        >= Builtins.DateTimeAdd(Builtins.Now(), '-1 day'),
                )

            Add months to a stored subscription date::

                plus_three_months = Builtins.DateTimeAdd(
                    users.subscribed_at, '3 months'
                )
                rows = users.get_row([users.username, plus_three_months])

            Store a computed expiry during an UPDATE::

                users.update(
                    update={users.token_expires:
                            Builtins.DateTimeAdd(Builtins.Now(), '1 day')},
                    where=users.id == 42,
                )
                # UPDATE "users"
                # SET "token_expires" = ((CAST((NOW()) AS TIMESTAMP)
                #                         + %s::interval))
                # WHERE ("users"."id" = %s);
                # Parameters: ['1 day', 42]

            Degenerate form — no intervals, same as :meth:`DateTime`::

                rows = users.get_row([
                    Builtins.DateTimeAdd(users.created_at),
                    Builtins.DateTime(users.created_at),
                ])
                # Both columns produce identical SQL and results.
        """
        sql, p, _, c = Builtins._normalize(value)
        if not intervals:
            return Builtins._make(f'(CAST({sql} AS TIMESTAMP))', p, str, c)
        expr, params = f'CAST({sql} AS TIMESTAMP)', list(p)
        for iv in intervals:
            expr = f'({expr} + %s::interval)'
            params.append(iv)
        return Builtins._make(f'({expr})', params, str, c)

    @staticmethod
    def TimeAdd(value, *intervals):
        """Add INTERVAL strings to a time-of-day value and cast back to TIME.

        Generates a chain of ``(CAST(<expr> AS TIMESTAMP) + %s::interval)``
        additions and finally casts the whole expression to ``TIME``:

        .. code-block:: sql

            CAST((CAST(<expr> AS TIMESTAMP)
                  + %s::interval
                  + %s::interval) AS TIME)

        This is the time-only counterpart of :meth:`DateAdd` and
        :meth:`DateTimeAdd`: the interval set is identical, but the
        result is a ``TIME`` value, discarding the date component
        entirely.

        Use this method when you only care about the time of day — for
        example, when a schedule shifts by a fixed number of minutes
        regardless of which day it lands on, or when you want to compare
        two times-of-day without their dates confusing the result.

        Because PostgreSQL's date-time arithmetic always carries a full
        timestamp internally, ``TIME`` casts will silently wrap around
        midnight — ``TIME '23:30' + INTERVAL '1 hour'`` produces
        ``TIME '00:30'``, losing the day boundary information. If you
        need to preserve the day, use :meth:`DateTimeAdd` and extract
        the time in Python.

        See :meth:`DateAdd` for the complete list of accepted interval
        strings. They are identical for all three helpers.

        When called with no intervals, this helper degenerates to
        ``CAST(<expr> AS TIME)`` — the same behaviour as :meth:`Time`.

        Args:
            value: The starting date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

            *intervals: Zero or more interval strings, each bound as a
                ``%s`` parameter. Applied left-to-right.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> + ?::interval + ?::interval AS TIME))`` and
            whose ``current_datatype`` is always ``str``. Parameters
            are concatenated left-to-right: first ``value``'s parameters,
            then the intervals in order.

        Example:
            The current time of day::

                from Ormophine.Postgresql import Driver, Builtins

                db     = Driver("localhost", 5432, "user", "pass", "app")
                events = db.events

                rows = events.get_row([
                    Builtins.TimeAdd(Builtins.Now()),
                ])
                # SELECT (CAST((NOW()) AS TIME)) FROM "events"
                # -> [(time(14, 30, 42),)]

            Shift a stored time by 30 minutes::

                rows = events.get_row([
                    events.id,
                    events.scheduled_at,
                    Builtins.TimeAdd(events.scheduled_at, '30 minutes'),
                ])
                # SELECT "events"."id", "events"."scheduled_at",
                #        (CAST((CAST("events"."scheduled_at" AS TIMESTAMP)
                #               + %s::interval) AS TIME))
                # FROM "events"
                # Parameters: ['30 minutes']
                # -> [(1, datetime(2024, 3, 15, 9, 0), time(9, 30)), ...]

            Compute the "next hour" marker by adding 60 minutes::

                next_hour = Builtins.TimeAdd(events.scheduled_at, '60 minutes')
                rows = events.get_row([events.id, next_hour])
                # -> [(1, time(10, 0)), ...]

            Compare a stored time against a threshold — filter events
            whose scheduled time plus 15 minutes is after 6 PM::

                rows = events.get_row(
                    [events.id, events.scheduled_at],
                    where=Builtins.TimeAdd(
                        events.scheduled_at, '15 minutes'
                    ) > '18:00:00',
                )
                # SELECT "events"."id", "events"."scheduled_at"
                # FROM "events"
                # WHERE ((CAST((CAST("events"."scheduled_at" AS TIMESTAMP)
                #               + %s::interval) AS TIME)) > %s)
                # Parameters: ['15 minutes', '18:00:00']

            Shift a time-of-day backwards by an hour::

                one_hour_earlier = Builtins.TimeAdd(
                    events.scheduled_at, '-1 hour'
                )
                rows = events.get_row([events.id, one_hour_earlier])
                # -> [(1, time(8, 0)), (2, time(7, 30)), ...]

            Cross-midnight wrap-around — the result wraps silently::

                rows = events.get_row([
                    Builtins.TimeAdd('23:30:00', '1 hour'),
                ])
                # -> [(time(0, 30),)] — the day boundary is lost.
                # Use DateTimeAdd if you need to preserve the day.

            Filter office-hours slots — combined with plain :meth:`Time`::

                rows = events.get_row(
                    [events.id, events.scheduled_at],
                    where=(Builtins.Time(events.scheduled_at) >= '09:00:00')
                        & (Builtins.Time(events.scheduled_at) <= '17:00:00'),
                )
                # SELECT "events"."id", "events"."scheduled_at"
                # FROM "events"
                # WHERE (((CAST("events"."scheduled_at" AS TIME)) >= %s)
                #        AND ((CAST("events"."scheduled_at" AS TIME)) <= %s))
                # Parameters: ['09:00:00', '17:00:00']

            Compose with :meth:`Format` for a display string::

                display = Builtins.Format(
                    'Next slot at %s',
                    Builtins.TimeAdd(events.scheduled_at, '45 minutes'),
                )
                rows = events.get_row([events.id, display])
                # -> [('Next slot at 09:45:00',), ...]

            Degenerate form — no intervals, same as :meth:`Time`::

                rows = events.get_row([
                    Builtins.TimeAdd(events.scheduled_at),
                    Builtins.Time(events.scheduled_at),
                ])
                # Both columns produce identical SQL and results.
        """
        sql, p, _, c = Builtins._normalize(value)
        if not intervals:
            return Builtins._make(f'(CAST({sql} AS TIME))', p, str, c)
        expr, params = f'CAST({sql} AS TIMESTAMP)', list(p)
        for iv in intervals:
            expr = f'({expr} + %s::interval)'
            params.append(iv)
        return Builtins._make(f'(CAST({expr} AS TIME))', params, str, c)

    @staticmethod
    def StrftimeMod(fmt, value, *intervals):
        """Format a date/time value with INTERVAL modifiers applied first.

        Generates a ``TO_CHAR(<expr>, <fmt>)`` expression where ``<expr>``
        is the base value with every interval added in sequence:

        .. code-block:: sql

            TO_CHAR((CAST(<value> AS TIMESTAMP)
                     + %s::interval
                     + %s::interval),
                    %s)

        This is the modifier-aware companion of :meth:`Strftime`: it
        applies every interval to ``value`` before feeding the result to
        the format string, which lets you do things like "format the
        timestamp as ``YYYY-MM`` *after* adding one month" in a single
        SQL expression.

        The full interval set documented for :meth:`DateAdd` is
        available. The format string supports the same PostgreSQL
        template tokens as :meth:`Strftime` — see that method for the
        complete mapping.

        When called with no intervals, this helper degenerates to
        ``TO_CHAR(<value>, <fmt>)`` — the same behaviour as
        :meth:`Strftime`. The separate name exists for the modifier-aware
        form, but both patterns are valid.

        The result is always a ``TEXT`` string.

        Args:
            fmt: The format template. Bound as a ``%s`` parameter, so it
                can be user-supplied safely.

            value: The starting date/time expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

            *intervals: Zero or more interval strings, each bound as a
                ``%s`` parameter. Applied left-to-right.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(TO_CHAR(<expr> + ?::interval + ?, %s))`` and whose
            ``current_datatype`` is always ``str``. Parameters are
            ordered: first ``value``'s parameters, then the intervals,
            then ``fmt`` as the final parameter.

        Example:
            Format "one month from now" as ``YYYY-MM``::

                from Ormophine.Postgresql import Driver, Builtins

                db    = Driver("localhost", 5432, "user", "pass", "app")
                users = db.users

                rows = users.get_row([
                    Builtins.StrftimeMod(
                        'YYYY-MM',
                        Builtins.Now(),
                        '1 month',
                    ),
                ])
                # SELECT (TO_CHAR((CAST((NOW()) AS TIMESTAMP)
                #                  + %s::interval), %s))
                # FROM "users"
                # Parameters: ['1 month', 'YYYY-MM']
                # -> [('2024-04',)]

            Report period label from a stored subscription date::

                period = Builtins.StrftimeMod(
                    'YYYY-MM',
                    users.subscribed_at,
                    '3 months',
                )
                rows = users.get_row([users.username, period])
                # SELECT "users"."username",
                #        (TO_CHAR((CAST("users"."subscribed_at" AS TIMESTAMP)
                #                  + %s::interval), %s))
                # FROM "users"
                # Parameters: ['3 months', 'YYYY-MM']
                # -> [('Alice', '2024-06'), ('Bob', '2024-07'), ...]

            "Last seen today" — extract the time after shifting by
            nothing (uses the base datetime)::

                last_seen_local = Builtins.StrftimeMod(
                    'HH24:MI',
                    users.last_seen,
                    '0 seconds',        # no-op interval, cleaner than empty
                )
                rows = users.get_row([users.username, last_seen_local])
                # -> [('Alice', '15:30'), ('Bob', '09:12'), ...]

            "First of next month" as a display string — chain two
            intervals::

                first_next_month = Builtins.StrftimeMod(
                    'YYYY-MM-DD',
                    Builtins.Today(),
                    '1 month',
                )
                rows = users.get_row([first_next_month])
                # -> [('2024-04-15',)]
                # Note: this returns the same day next month, not the
                # first of the month. For "first of month" semantics,
                # use DATE_TRUNC via a raw expression.

            Filter by a formatted, modified value::

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.StrftimeMod(
                        'YYYY',
                        users.created_at,
                        '-6 months',
                    ) == '2023',
                )
                # SELECT "users"."id", "users"."created_at"
                # FROM "users"
                # WHERE ((TO_CHAR((CAST("users"."created_at" AS TIMESTAMP)
                #                  + %s::interval), %s)) = %s)
                # Parameters: ['-6 months', 'YYYY', '2023']
                # Users whose timestamp, shifted back six months, falls
                # in 2023.

            Quarter label via a chained interval::

                q_label = Builtins.StrftimeMod(
                    'YYYY"-Q"Q',
                    users.created_at,
                    '0 days',
                )
                rows = users.get_row([users.username, q_label])
                # -> [('Alice', '2024-Q1'), ('Bob', '2024-Q2'), ...]
                # Q is a PostgreSQL template token for the quarter.

            Degenerate form — no intervals, same as :meth:`Strftime`::

                rows = users.get_row([
                    Builtins.StrftimeMod('YYYY', users.created_at),
                    Builtins.Strftime('YYYY', users.created_at),
                ])
                # Both columns produce identical SQL and results.
        """
        sql, p, _, c = Builtins._normalize(value)
        if not intervals:
            return Builtins._make(
                f'(TO_CHAR({sql}, %s))', p + [fmt], str, c)
        expr, params = f'CAST({sql} AS TIMESTAMP)', list(p)
        for iv in intervals:
            expr = f'({expr} + %s::interval)'
            params.append(iv)
        return Builtins._make(
            f'(TO_CHAR({expr}, %s))', params + [fmt], str, c)
    