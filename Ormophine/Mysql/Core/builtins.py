from __future__ import annotations
import re
from .. import Column, ColumnsOperation


class Builtins:
    """MySQL SQL function helpers that always return a :class:`ColumnsOperation`.

    ``Builtins`` is a stateless namespace of static methods, each of which
    wraps a MySQL function (or, where MySQL lacks a native function, a
    short composition of MySQL functions) into a :class:`ColumnsOperation`
    object. Because every helper returns a ``ColumnsOperation``, the result
    can be used anywhere a column expression is accepted: in the
    ``which_columns`` list of :meth:`Table.get_row`, in the ``where``
    condition, in the ``update`` dict of :meth:`Table.update`, inside
    :meth:`~Table.bulk_update`, and so on. Helpers can also be nested
    freely — ``Builtins.Round(Builtins.Avg(col) * 100) / 100`` compiles
    into a single SQL expression with all parameters collected in order.

    Design
    ------
    The class is deliberately a namespace, not an instance-based helper.
    You never write ``Builtins()``; every entry point is a ``@staticmethod``
    you call directly::

        from Ormophine.Mysql import Driver, Builtins

        rows = users.get_row(
            [users.id, Builtins.Len(users.username)],
            where=Builtins.Len(users.username) > 5,
        )

    All three of the standard operand types are accepted by every helper:

    - :class:`Column` — the fully qualified name (`` `table`.`col` ``) is
      embedded verbatim; no parameters are consumed.
    - :class:`ColumnsOperation` — the previously-built SQL fragment and its
      parameter list are reused and extended.
    - Any raw Python value (``str``, ``int``, ``float``, ``bytes``,
      ``None``, ``bool``) — bound as a ``%s`` placeholder. Binding rather
      than interpolating means the value never reaches the SQL text, so
      injection is impossible.

    Datatype propagation
    --------------------
    Each helper sets ``current_datatype`` on the returned
    ``ColumnsOperation`` to a Python type (``int``, ``float``, ``str``,
    ``bytes``, or ``None`` when the result's type depends on its branches,
    as in :meth:`IIf`). The downstream operator dispatcher in
    :class:`ColumnsOperation` uses this attribute to choose between
    arithmetic (``+``) and concatenation (``||``) when the expression is
    chained. Helpers therefore document their result type so that call
    sites can reason about chained expressions without trial and error.

    Coventional result types:

    ===================================  =========
    Helper family                        datatype
    ===================================  =========
    ``Len``, ``Find``, ``Sum``, ``Min``,
    ``Max``, ``Count``, ``Abs``, ``Sign``,
    ``Floor``, ``Ceil``, ``Int``, ``Bool``,
    ``DateDiffDays``, ``DateDiffSeconds``   ``int``
    ``Avg``, ``Round``, ``RoundTo``,
    ``Sqrt``, ``Pow``, ``Float``            ``float``
    ``Reverse``, ``Capitalize``, ``Str``,
    ``Date``, ``Time``, ``DateTime``,
    ``Now``, ``Today``, ``Strftime``,
    ``StrftimeMod``, ``Timediff``,
    ``DateAdd``, ``DateTimeAdd``,
    ``TimeAdd``                              ``str``
    ===================================  =========

    Date/time conventions
    ---------------------
    Date and time helpers return ``str`` in ISO-8601-like formats that
    MySQL produces natively (``'YYYY-MM-DD'``, ``'HH:MM:SS'``,
    ``'YYYY-MM-DD HH:MM:SS'``). They accept an ISO literal, a
    :class:`Column`, a :class:`ColumnsOperation`, or the special string
    ``'now'`` — the last is translated to ``CURDATE()``, ``CURTIME()``,
    ``NOW()``, or ``UNIX_TIMESTAMP()`` depending on the helper. This
    mirrors the calling convention of SQLite's ``date()``, ``time()`` and
    ``datetime()`` functions, so code ported from the SQLite counterpart
    of this ORM keeps working.

    SQLite-style modifiers such as ``'+1 day'``, ``'-3 hours'``,
    ``'start of month'`` are supported by :meth:`DateAdd`,
    :meth:`DateTimeAdd`, :meth:`TimeAdd` and :meth:`StrftimeMod`; they are
    folded into chained ``DATE_ADD``/``DATE_SUB`` calls (and, for the
    anchor modifiers, into ``DATE_FORMAT`` truncations) by the internal
    helper :meth:`_apply_modifiers`.

    Helpers that are intentionally absent
    -------------------------------------
    MySQL lacks a few functions that SQLite provides and that a
    drop-in port would otherwise include:

    - ``TYPEOF`` — MySQL uses ``information_schema`` for column metadata
      instead; see :meth:`Table.get_table_info`.
    - ``PRINTF`` / ``FORMAT`` — MySQL's ``FORMAT()`` only handles numbers;
      for general string formatting use :meth:`Str` combined with
      :meth:`ColumnsOperation.add_first` / :meth:`add_end`, or a raw
      ``custom_execute`` call.
    - ``TOTAL`` — SQLite's ``SUM`` that returns 0 instead of NULL over an
      empty group. In MySQL use :meth:`Sum` wrapped in
      ``Builtins.Func('IFNULL', Builtins.Sum(col), 0)``.
    - ``julianday`` — MySQL has ``TO_DAYS``, but the semantics differ and
      the ORM's date arithmetic helpers cover the same ground.

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
      SQL fragment, which is the order MySQLdb expects.

    Example:
        A quick tour of the helper categories::

            from Ormophine.Mysql import Driver, Builtins

            db    = Driver(host='localhost', port=3306, username='root',
                           password='secret', db_name='app')
            users = db.users

            # String
            Builtins.Len(users.username)
            Builtins.Reverse(users.username)
            Builtins.Find(users.email, '@')
            Builtins.Capitalize(users.name)

            # Aggregate
            Builtins.Sum(users.balance)
            Builtins.Avg(users.age)
            Builtins.Min(users.created_at)
            Builtins.Max(users.score)
            Builtins.Count('*')

            # Math
            Builtins.Abs(users.delta)
            Builtins.Round(users.price)
            Builtins.RoundTo(users.price, 2)
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
        column operand, and ``NOW()`` is a server-side constant. But every
        :class:`ColumnsOperation` in this ORM is expected to carry a
        ``col_obj`` attribute pointing at the :class:`Column` that
        originated the expression — the operator dispatcher reads
        ``col_obj.datatype``, ``col_obj.name``, and
        ``col_obj.table_obj._PlaceHolder`` when deciding how to render a
        chained operation.

        Rather than passing ``None`` and forcing every call site to
        null-check, helpers with no natural column use an instance of
        ``_NullCol``. It supplies the same attribute surface as a real
        :class:`Column` so chained operations such as ``Builtins.Now() + 1``
        or ``Builtins.Count('*') * 2`` do not raise ``AttributeError``.

        Attributes:
            datatype (None): Always ``None``. Signals that the originating
                expression is not tied to a column type, so the operator
                dispatcher falls back to its safe defaults (arithmetic
                rather than concatenation when both sides are ambiguous).
            table_obj (None): Always ``None``. There is no parent table.
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
                    return Builtins._make('(NOW())', [], str, Builtins._NullCol)

            The ``Builtins._NullCol`` class itself (not an instance) is
            passed because the helpers only need the attribute surface,
            never any per-instance state. Passing the class works because
            attribute lookup falls through to the class-level definitions.
        """
        datatype   = None
        table_obj  = None
        name       = ''
        first_name = ''

    # ------------------------------------------------------------------ helpers

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
          (`` `table`.`col` ``); for a :class:`ColumnsOperation` it is the
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
                ('`users`.`username`', [], str, <Column users.username>)

                >>> op = Builtins.Len(users.username)
                >>> Builtins._normalize(op)
                ('(LENGTH(`users`.`username`))', [], int, <Column users.username>)

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

                # Len — MySQL LENGTH()
                return Builtins._make(f'(LENGTH({sql}))', p, int, c)

                # Now — no operands at all
                return Builtins._make('(NOW())', [], str, Builtins._NullCol)

                # IIf — datatype intentionally None because the branches
                # may disagree
                return Builtins._make(
                    f'(IF({cs}, {ts}, {es}))',
                    cp + tp + ep,
                    None,
                    c,
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
                '((CAST((UNIX_TIMESTAMP()) AS SIGNED)) + %s)'
        """
        op = ColumnsOperation.__new__(ColumnsOperation)
        op._output          = (sql, params)
        op.col_obj          = col_obj if col_obj is not None else Builtins._NullCol
        op.current_datatype = datatype
        return op

    @staticmethod
    def _is_now(value):
        """Detect the literal string ``'now'`` used as a date/time keyword.

        SQLite's ``date()``, ``time()`` and ``datetime()`` functions accept
        the literal string ``'now'`` as a keyword meaning "the current
        moment", and the same convention is preserved by the SQLite
        counterpart of this ORM. MySQL has no such keyword, so the
        date/time helpers (:meth:`Date`, :meth:`Time`, :meth:`DateTime`,
        :meth:`DateAdd`, :meth:`DateTimeAdd`, :meth:`TimeAdd`,
        :meth:`StrftimeMod`, :meth:`UnixEpoch`) check for ``'now'`` via
        this method and translate it into the appropriate MySQL
        zero-argument function:

        ===================  ===================
        Helper               MySQL translation
        ===================  ===================
        :meth:`Date`         ``CURDATE()``
        :meth:`Time`         ``CURTIME()``
        :meth:`DateTime`     ``NOW()``
        :meth:`DateAdd`      ``CURDATE()``
        :meth:`DateTimeAdd`  ``NOW()``
        :meth:`TimeAdd`      ``NOW()``
        :meth:`StrftimeMod`  ``NOW()``
        :meth:`UnixEpoch`    ``UNIX_TIMESTAMP()``
        ===================  ===================

        Matching is case-insensitive and ignores surrounding whitespace,
        so ``'NOW'``, ``'now'``, ``' Now '`` all trigger the translation.
        The comparison is only attempted against strings; any other type
        returns ``False`` without raising.

        Args:
            value: The candidate to test. Only a Python ``str`` can match;
                any other type returns ``False`` immediately.

        Returns:
            bool: ``True`` when ``value`` is a string whose stripped,
            lowercased form is exactly ``'now'``. ``False`` otherwise —
            including when ``value`` is ``'nowhere'``, ``'the now'``, or
            a :class:`Column` named ``'now'``.

        Example:
            Behaviour on typical inputs::

                >>> Builtins._is_now('now')
                True
                >>> Builtins._is_now('NOW')
                True
                >>> Builtins._is_now('  Now  ')
                True
                >>> Builtins._is_now('nowhere')
                False
                >>> Builtins._is_now(None)
                False
                >>> Builtins._is_now(42)
                False

            How a helper uses it — :meth:`Date` short-circuits to
            ``CURDATE()`` when the keyword is detected, before falling
            back to the general normalisation path::

                @staticmethod
                def Date(value):
                    if Builtins._is_now(value):
                        return Builtins._make('(CURDATE())', [], str,
                                              Builtins._NullCol)
                    sql, p, _, c = Builtins._normalize(value)
                    return Builtins._make(f'(DATE({sql}))', p, str, c)

            Users can therefore write the SQLite-style call
            ``Builtins.Date('now')`` alongside the MySQL-native
            ``Builtins.Today()`` and get the same result.
        """
        return isinstance(value, str) and value.strip().lower() == 'now'
    
    @staticmethod
    def Len(value):
        """Compute the length of a value using MySQL's ``LENGTH()`` function.

        Generates a SQL expression that returns the number of **bytes** in a
        string or binary value. This is the SQL analogue of Python's ``len()``
        for ASCII data, but MySQL counts bytes not characters — for
        ``utf8mb4`` text with multi-byte characters the result is larger than
        Python's ``len()`` would be.

        If you need character count, use ``CHAR_LENGTH`` via
        ``Builtins.Int(Builtins.Func(...))`` or a raw ``custom_execute``
        call. For pure-ASCII columns the two are equivalent.

        The result is always an ``INTEGER``, so it composes cleanly with
        comparisons and arithmetic.

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

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row(
                    [users.username],
                    where=Builtins.Len(users.username) > 5,
                )
                # SELECT `users`.`username` FROM `users`
                # WHERE ((LENGTH(`users`.`username`)) > %s)
                # Parameters: [5]

            As a SELECT column — the length of each username::

                rows = users.get_row([
                    users.username,
                    Builtins.Len(users.username),
                ])
                # SELECT `users`.`username`, (LENGTH(`users`.`username`))
                # FROM `users`

            Chained with other operations — the length rounded up to a
            multiple of 4::

                padded_len = ((Builtins.Len(users.username) + 3) / 4) * 4
                rows = users.get_row(
                    [users.username, padded_len],
                    where=Builtins.Len(users.username) > 0,
                )
                # SELECT `users`.`username`,
                #        ((((LENGTH(`users`.`username`)) + %s) / %s) * %s)
                # FROM `users`
                # WHERE ((LENGTH(`users`.`username`)) > %s)
                # Parameters: [3, 4, 4, 0]

            Nested inside other builtins::

                avg_len = Builtins.Avg(Builtins.Len(users.username))
                rows = users.get_row([avg_len])
                # SELECT (AVG((LENGTH(`users`.`username`)))) FROM `users`

            Applied to a raw literal — the literal is bound as a parameter::

                rows = users.get_row([
                    Builtins.Len('hello'),    # -> (LENGTH(%s)) with param 'hello'
                    Builtins.Len(42),         # -> (LENGTH(%s)) with param 42
                ])

            Filter inside a compound condition::

                active_short = Builtins.Sum(
                    Builtins.IIf(
                        (Builtins.Len(users.username) < 8)
                        & (users.active == 1),
                        1,
                        0,
                    )
                )
                rows = users.get_row([active_short])
                # SELECT (SUM((IF(
                #   (((LENGTH(`users`.`username`)) < %s)
                #    AND (`users`.`active` = %s)),
                #   %s, %s))))
                # FROM `users`
                # Parameters: [8, 1, 1, 0]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(LENGTH({sql}))', p, int, c)

    @staticmethod
    def Reverse(value):
        """Reverse the characters of a text value using MySQL's ``REVERSE()``.

        Generates a ``REVERSE(<expr>)`` expression. The result is a new
        string with the same characters in the opposite order. This is the
        SQL analogue of Python's ``s[::-1]`` idiom.

        The result is always a ``TEXT`` string, so ``+`` chained after it
        produces concatenation (``||``) rather than arithmetic addition —
        the driver enables ``PIPES_AS_CONCAT`` automatically.

        .. note::
            ``REVERSE()`` is available in MySQL 4.1+ and in all MariaDB
            versions, so it works on every supported backend. It operates
            on bytes, so the reversed form of a multi-byte string may not
            be valid text — this only matters for exotic data.

        Args:
            value: The expression whose characters are reversed. Supported
                types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python string — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(REVERSE(<expr>))`` and whose ``current_datatype`` is always
            ``str``.

        Example:
            Reverse every username as a simple pseudo-hash::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row([
                    users.id,
                    users.username,
                    Builtins.Reverse(users.username),
                ])
                # SELECT `users`.`id`, `users`.`username`,
                #        (REVERSE(`users`.`username`))
                # FROM `users`
                # -> e.g. [(1, 'alice', 'ecila'), (2, 'bob', 'bob'), ...]

            Palindrome check — a string equals its own reverse::

                is_palindrome = users.username == Builtins.Reverse(users.username)
                rows = users.get_row(
                    [users.username],
                    where=is_palindrome,
                )
                # SELECT `users`.`username` FROM `users`
                # WHERE (`users`.`username` = (REVERSE(`users`.`username`)))

            Suffix search turned into prefix search::

                rows = users.get_row(
                    [users.username],
                    where=Builtins.Reverse(users.username).startswith('e'),
                )
                # SELECT `users`.`username` FROM `users`
                # WHERE ((REVERSE(`users`.`username`)) LIKE %s || '%')
                # Parameters: ['e']

            Sort by reversed string — clusters anagrams::

                rows = users.get_row(
                    [users.username],
                    order_by=Builtins.Reverse(users.username),
                )

            Chain with other string builtins::

                expr = Builtins.Reverse(Builtins.Upper(users.username))
                # -> (REVERSE((UPPER(`users`.`username`))))
                rows = users.get_row([expr])

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Reverse('hello'),    # -> (REVERSE(%s)) with param 'hello'
                ])
                # -> [('olleh',)]
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(REVERSE({sql}))', p, str, c)

    @staticmethod
    def Find(value, sub):
        """Locate a substring within a value using MySQL's ``INSTR()`` function.

        Generates an ``INSTR(<value>, <sub>)`` expression. Returns the
        1-based position of the first occurrence of ``sub`` inside
        ``value``, or ``0`` if ``sub`` is not present.

        .. warning::
            MySQL's ``INSTR`` and Python's ``str.find`` differ in two ways
            that routinely trip people up:

            ==================  =========  =========
            Behaviour           Python     MySQL
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

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value — bound as a ``%s`` placeholder.

            sub: The needle. Same accepted types as ``value``. Usually a
                plain string literal, but any expression is allowed.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(INSTR(<value>, <sub>))`` and whose ``current_datatype`` is
            ``int``. Parameters are concatenated left-to-right: first the
            haystack's parameters, then the needle's.

        Example:
            Find the position of a delimiter inside a text column::

                from Ormophine.Mysql import Driver, Builtins

                db     = Driver(host='localhost', port=3306, username='root',
                                password='secret', db_name='app')
                emails = db.emails

                at_pos = Builtins.Find(emails.address, '@')
                rows = emails.get_row([
                    emails.id,
                    emails.address,
                    at_pos,
                ])
                # SELECT `emails`.`id`, `emails`.`address`,
                #        (INSTR(`emails`.`address`, %s))
                # FROM `emails`
                # Parameters: ['@']
                # -> e.g. [(1, 'alice@example.com', 6), (2, 'bob@x.io', 4), ...]

            Detect the presence of a substring — ``> 0`` because MySQL
            returns 0 (not -1) when the needle is missing::

                rows = emails.get_row(
                    [emails.id, emails.address],
                    where=Builtins.Find(emails.address, 'spam') > 0,
                )
                # SELECT ... WHERE ((INSTR(`emails`.`address`, %s)) > %s)
                # Parameters: ['spam', 0]

            Python-equivalent "not found" check — add ``- 1`` so -1 means
            "missing"::

                py_find = Builtins.Find(emails.address, 'example') - 1
                rows = emails.get_row(
                    [emails.address],
                    where=py_find == -1,
                )
                # SELECT `emails`.`address` FROM `emails`
                # WHERE (((INSTR(`emails`.`address`, %s)) - %s) = %s)
                # Parameters: ['example', 1, -1]

            Use a column as the needle — find where one column appears
            inside another::

                rows = emails.get_row([
                    emails.id,
                    Builtins.Find(emails.address, emails.username),
                ])
                # SELECT `emails`.`id`,
                #        (INSTR(`emails`.`address`, `emails`.`username`))
                # FROM `emails`

            Combine with slicing to extract everything before the '@'::

                at_pos = Builtins.Find(emails.address, '@')
                local_part = emails.address[:at_pos - 1]
                rows = emails.get_row([emails.id, local_part])
        """
        s1, p1, _, c = Builtins._normalize(value)
        s2, p2, _, _ = Builtins._normalize(sub)
        return Builtins._make(f'(INSTR({s1}, {s2}))', p1 + p2, int, c)

    @staticmethod
    def Capitalize(value):
        """Capitalise a text value — first character upper, rest lower.

        MySQL has no native ``CAPITALIZE()`` function, so this helper
        composes one from two SQL expressions:

        .. code-block:: sql

            CONCAT(UPPER(SUBSTRING(<expr>, 1, 1)), LOWER(SUBSTRING(<expr>, 2)))

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

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused. The fragment is embedded twice in
                  the output (once for the first char, once for the rest),
                  so any parameters it carries are also duplicated.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python string — bound as a ``%s`` placeholder
                  (also duplicated).

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CONCAT(UPPER(SUBSTRING(<expr>, 1, 1)), LOWER(SUBSTRING(<expr>, 2))))``
            and whose ``current_datatype`` is always ``str``.

        Example:
            Title-case names for display::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row([
                    users.id,
                    Builtins.Capitalize(users.name),
                ])
                # SELECT `users`.`id`,
                #        (CONCAT(UPPER(SUBSTRING(`users`.`name`, 1, 1)),
                #                LOWER(SUBSTRING(`users`.`name`, 2))))
                # FROM `users`
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
                # SQL: (CONCAT(UPPER(SUBSTRING(%s, 1, 1)), LOWER(SUBSTRING(%s, 2))))
                # Parameters: ['hELLO wORLD', 'hELLO wORLD']

            Combine with Trim to clean up and capitalise in one go::

                clean = Builtins.Capitalize(users.name.strip())
                rows = users.get_row([clean])
        """
        sql, p, _, c = Builtins._normalize(value)
        inner = f'CONCAT(UPPER(SUBSTRING({sql}, 1, 1)), LOWER(SUBSTRING({sql}, 2)))'
        return Builtins._make(f'({inner})', p, str, c)

    # ================================================================ aggregate

    @staticmethod
    def Sum(value):
        """Compute the sum of a set of values using MySQL's ``SUM()`` aggregate.

        Generates a SQL ``SUM(<expr>)`` expression. When used in a SELECT
        list without a ``GROUP BY`` clause, it aggregates over all rows
        returned by the query. When used inside a ``WHERE`` clause it has
        no meaning on its own (MySQL will reject it) — ``Sum`` is meant
        for the SELECT side of a query, not for filtering.

        The resulting ``current_datatype`` is propagated from the input:

        - ``int``   → ``int`` (MySQL keeps integer sums as integers unless
          the column is ``UNSIGNED BIGINT``, which is widened to
          ``DECIMAL``)
        - ``float`` → ``float``
        - anything else → ``int`` (conservative default)

        This keeps arithmetic chains (``Builtins.Sum(col) + 1``) compiling
        to ``+`` and not ``||``.

        .. note::
            ``SUM`` returns ``NULL`` over an empty group. If you want 0
            instead, wrap in ``IFNULL`` via
            ``Builtins.IfNull(Builtins.Sum(col), 0)`` or use
            ``Builtins.Func('COALESCE', ...)``.

        Args:
            value: The expression to sum. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(SUM(<expr>))`` and whose ``current_datatype`` matches the
            input's numeric type (or ``int`` if the input is not numeric).

        Example:
            Total salary across all employees::

                from Ormophine.Mysql import Driver, Builtins

                db        = Driver(host='localhost', port=3306, username='root',
                                   password='secret', db_name='company')
                employees = db.employees

                total = Builtins.Sum(employees.salary)
                rows  = employees.get_row([total])
                # SELECT (SUM(`employees`.`salary`)) FROM `employees`
                # -> [(1245000,)] for example

            Sum alongside other aggregates::

                rows = employees.get_row([
                    Builtins.Count(employees.id),
                    Builtins.Sum(employees.salary),
                    Builtins.Avg(employees.salary),
                ])
                # SELECT (COUNT(`employees`.`id`)),
                #        (SUM(`employees`.`salary`)),
                #        (AVG(`employees`.`salary`))
                # FROM `employees`

            Sum combined with arithmetic (stays numeric, not string)::

                with_bonus = Builtins.Sum(employees.salary) + 10000
                rows = employees.get_row([with_bonus])
                # SELECT ((SUM(`employees`.`salary`)) + %s) FROM `employees`
                # Parameters: [10000]

            Sum with a filter — combine with ``where=`` in the usual way::

                rows = employees.get_row(
                    [Builtins.Sum(employees.salary)],
                    where=employees.department == 'Engineering',
                )
                # SELECT (SUM(`employees`.`salary`)) FROM `employees`
                # WHERE (`employees`.`department` = %s)
                # Parameters: ['Engineering']

            Conditional aggregate — count how many rows satisfy a
            condition inside a single SUM::

                adults = Builtins.Sum(
                    Builtins.IIf(employees.age >= 18, 1, 0)
                )
                rows = employees.get_row([adults])
                # SELECT (SUM((IF((`employees`.`age` >= %s), %s, %s))))
                # FROM `employees`
                # Parameters: [18, 1, 0]
        """
        sql, p, dt, c = Builtins._normalize(value)
        result_dt = dt if dt in (int, float) else int
        return Builtins._make(f'(SUM({sql}))', p, result_dt, c)

    @staticmethod
    def Avg(value):
        """Compute the average of a set of values using MySQL's ``AVG()`` aggregate.

        Generates a SQL ``AVG(<expr>)`` expression. MySQL always returns
        the average as a ``DECIMAL`` value, even when every input value is
        an integer; therefore ``current_datatype`` is unconditionally set
        to ``float`` regardless of the input's datatype.

        Like :meth:`Sum`, this aggregate is meant for the SELECT side of a
        query. Using it in a ``WHERE`` clause will raise an SQL error
        unless the query contains a ``GROUP BY`` that makes the aggregate
        legal.

        .. note::
            ``AVG`` returns ``NULL`` over an empty group. Handle the empty
            case in Python (``if avg is None: ...``) or wrap in
            ``Builtins.IfNull(Builtins.Avg(col), 0)``.

        Args:
            value: The expression to average. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(AVG(<expr>))`` and whose ``current_datatype`` is always
            ``float``.

        Example:
            Average salary across all employees::

                from Ormophine.Mysql import Driver, Builtins

                db        = Driver(host='localhost', port=3306, username='root',
                                   password='secret', db_name='company')
                employees = db.employees

                rows = employees.get_row([Builtins.Avg(employees.salary)])
                # SELECT (AVG(`employees`.`salary`)) FROM `employees`
                # -> [(78750.0,)] for example

            Average rounded to two decimals::

                rows = employees.get_row([
                    Builtins.Round(
                        Builtins.Avg(employees.salary) * 100
                    ) / 100
                ])
                # SELECT ((ROUND(((AVG(`employees`.`salary`)) * %s))) / %s)
                # FROM `employees`
                # Parameters: [100, 100]

            Average of a computed expression::

                rows = employees.get_row([
                    Builtins.Avg(employees.salary + employees.bonus)
                ])
                # SELECT (AVG((`employees`.`salary` + `employees`.`bonus`)))
                # FROM `employees`

            Combined with other aggregates in a single row::

                rows = employees.get_row([
                    Builtins.Count(employees.id),
                    Builtins.Avg(employees.salary),
                    Builtins.Sum(employees.salary),
                ])

            Average with a filter — average salary of one department::

                rows = employees.get_row(
                    [Builtins.Avg(employees.salary)],
                    where=employees.department == 'Engineering',
                )
                # SELECT (AVG(`employees`.`salary`)) FROM `employees`
                # WHERE (`employees`.`department` = %s)
                # Parameters: ['Engineering']

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
        """Compute the minimum of a set of values using MySQL's ``MIN()`` aggregate.

        Generates a SQL ``MIN(<expr>)`` expression. When used with a
        single argument in the SELECT list, ``MIN`` acts as an aggregate
        over all rows. (When used with multiple arguments it acts as a
        scalar function, but this method only accepts one argument — for
        the scalar form use ``Builtins.Func('LEAST', a, b, c)`` instead.)

        The resulting ``current_datatype`` is propagated from the input,
        because MySQL returns the same type as the operand:

        - ``int``   → ``int``
        - ``float`` → ``float``
        - ``str``   → ``str`` (lexicographic minimum)
        - ``bytes`` → ``bytes``

        This keeps downstream concatenation (``Builtins.Min(col) + '!'``)
        compiling to ``||`` when the input was text.

        Args:
            value: The expression whose minimum is computed. Supported
                types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(MIN(<expr>))`` and whose ``current_datatype`` matches the
            input's datatype.

        Example:
            Lowest salary in the table::

                from Ormophine.Mysql import Driver, Builtins

                db        = Driver(host='localhost', port=3306, username='root',
                                   password='secret', db_name='company')
                employees = db.employees

                rows = employees.get_row([Builtins.Min(employees.salary)])
                # SELECT (MIN(`employees`.`salary`)) FROM `employees`
                # -> [(45000,)] for example

            Earliest signup date::

                users = db.users
                rows  = users.get_row([Builtins.Min(users.created_at)])
                # SELECT (MIN(`users`.`created_at`)) FROM `users`

            Lexicographic minimum of a text column::

                rows = employees.get_row([Builtins.Min(employees.name)])
                # current_datatype == str, so chaining works:
                expr = Builtins.Min(employees.name) + ' (first alphabetically)'
                # SELECT ((MIN(`employees`.`name`)) || %s) FROM `employees`
                # Parameters: [' (first alphabetically)']

            Minimum of a computed expression::

                rows = employees.get_row([
                    Builtins.Min(employees.salary - employees.bonus)
                ])

            Minimum with a filter::

                rows = employees.get_row(
                    [Builtins.Min(employees.salary)],
                    where=employees.department == 'Sales',
                )
                # SELECT (MIN(`employees`.`salary`)) FROM `employees`
                # WHERE (`employees`.`department` = %s)
                # Parameters: ['Sales']
        """
        sql, p, dt, c = Builtins._normalize(value)
        return Builtins._make(f'(MIN({sql}))', p, dt, c)

    @staticmethod
    def Max(value):
        """Compute the maximum of a set of values using MySQL's ``MAX()`` aggregate.

        Generates a SQL ``MAX(<expr>)`` expression. The mirror image of
        :meth:`Min`: same typing rules, same aggregate semantics, same
        single-argument signature.

        The resulting ``current_datatype`` is propagated from the input so
        that arithmetic and concatenation chains compile to the correct
        SQL operator.

        Args:
            value: The expression whose maximum is computed. Supported
                types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(MAX(<expr>))`` and whose ``current_datatype`` matches the
            input's datatype.

        Example:
            Highest salary in the table::

                from Ormophine.Mysql import Driver, Builtins

                db        = Driver(host='localhost', port=3306, username='root',
                                   password='secret', db_name='company')
                employees = db.employees

                rows = employees.get_row([Builtins.Max(employees.salary)])
                # SELECT (MAX(`employees`.`salary`)) FROM `employees`
                # -> [(180000,)] for example

            Latest signup date::

                users = db.users
                rows  = users.get_row([Builtins.Max(users.created_at)])
                # SELECT (MAX(`users`.`created_at`)) FROM `users`

            Combined with the id of the top earner — get both at once::

                rows = employees.get_row([
                    Builtins.Max(employees.salary),
                    employees.id,
                ])
                # The first value is the max salary; the second is the id
                # of an arbitrary row (MySQL picks one) — for a strict
                # "id of the top earner" use order_by + limit:
                top = employees.get_row(
                    [employees.id, employees.name, employees.salary],
                    order_by=employees.salary * -1,   # descending
                    limit=1,
                )

            Maximum of a computed expression::

                rows = employees.get_row([
                    Builtins.Max(employees.salary + employees.bonus)
                ])

            Maximum with a filter::

                rows = employees.get_row(
                    [Builtins.Max(employees.salary)],
                    where=employees.department == 'Sales',
                )
                # SELECT (MAX(`employees`.`salary`)) FROM `employees`
                # WHERE (`employees`.`department` = %s)
                # Parameters: ['Sales']
        """
        sql, p, dt, c = Builtins._normalize(value)
        return Builtins._make(f'(MAX({sql}))', p, dt, c)

    @staticmethod
    def Count(value):
        """Count rows using MySQL's ``COUNT()`` aggregate.

        Two forms are supported, mirroring MySQL's own behaviour:

        * **Row count** — when ``value`` is the literal string ``'*'``,
          generates ``COUNT(*)`` which counts every row in the group,
          regardless of NULL values.
        * **Non-null count** — for any other input, generates
          ``COUNT(<expr>)`` which counts only the rows where the
          expression evaluates to a non-NULL value.

        The result is always an ``INTEGER``, regardless of the input's
        datatype.

        Args:
            value: What to count. Supported types:

                - The string ``'*'`` — produces ``COUNT(*)`` and no
                  parameters.
                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused; produces ``COUNT(<fragment>)``.
                - :class:`Column` — the fully qualified column name is
                  used; produces ``COUNT(`table`.`column`)``.
                - Any other raw Python value — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is either
            ``(COUNT(*))`` or ``(COUNT(<expr>))`` and whose
            ``current_datatype`` is always ``int``.

        Example:
            Count all rows in the table::

                from Ormophine.Mysql import Driver, Builtins

                db        = Driver(host='localhost', port=3306, username='root',
                                   password='secret', db_name='company')
                employees = db.employees

                rows = employees.get_row([Builtins.Count('*')])
                # SELECT (COUNT(*)) FROM `employees`
                # -> [(250,)] for example

            Count rows where a column is non-NULL::

                users = db.users
                rows  = users.get_row([Builtins.Count(users.email)])
                # SELECT (COUNT(`users`.`email`)) FROM `users`
                # -> [(198,)] — 52 users have no email on file

            Count with a filter — combine with where= in the usual way::

                rows = users.get_row(
                    [Builtins.Count('*')],
                    where=users.is_active == 1,
                )
                # SELECT (COUNT(*)) FROM `users`
                # WHERE (`users`.`is_active` = %s)
                # Parameters: [1]

            Count of a computed expression::

                rows = users.get_row([
                    Builtins.Count(Builtins.Upper(users.username))
                ])
                # SELECT (COUNT((UPPER(`users`.`username`)))) FROM `users`

            Boolean count via IF — count how many rows satisfy a
            condition inside a single aggregate::

                adults = Builtins.Sum(
                    Builtins.IIf(users.age >= 18, 1, 0)
                )
                rows = users.get_row([adults])
                # SELECT (SUM((IF((`users`.`age` >= %s), %s, %s))))
                # FROM `users`
                # Parameters: [18, 1, 0]
        """
        if isinstance(value, str) and value == '*':
            return Builtins._make('(COUNT(*))', [], int, Builtins._NullCol)
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(COUNT({sql}))', p, int, c)

    # ==================================================================== math

    @staticmethod
    def Abs(value):
        """Compute the absolute value of a number using MySQL's ``ABS()`` function.

        Generates a SQL ``ABS(<expr>)`` expression. The return type mirrors
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

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(ABS(<expr>))`` and whose ``current_datatype`` matches the
            input's numeric type (or ``float`` if the input is not
            numeric).

        Example:
            Magnitude of a signed delta::

                from Ormophine.Mysql import Driver, Builtins

                db        = Driver(host='localhost', port=3306, username='root',
                                   password='secret', db_name='analytics')
                movements = db.movements

                rows = movements.get_row([
                    movements.account_id,
                    Builtins.Abs(movements.delta),
                ])
                # SELECT `movements`.`account_id`,
                #        (ABS(`movements`.`delta`))
                # FROM `movements`

            Filter by absolute value::

                rows = movements.get_row(
                    [movements.account_id, movements.delta],
                    where=Builtins.Abs(movements.delta) > 1000,
                )
                # SELECT `movements`.`account_id`, `movements`.`delta`
                # FROM `movements`
                # WHERE ((ABS(`movements`.`delta`)) > %s)
                # Parameters: [1000]

            Absolute value of a computed expression::

                balance_change = movements.credit - movements.debit
                rows = movements.get_row([Builtins.Abs(balance_change)])
                # SELECT (ABS((`movements`.`credit` - `movements`.`debit`)))
                # FROM `movements`

            Chained with arithmetic — stays numeric::

                padded = Builtins.Abs(movements.delta) + 1
                # SELECT ((ABS(`movements`.`delta`)) + %s) FROM `movements`

            Applied to a raw literal::

                rows = movements.get_row([
                    Builtins.Abs(-42),    # -> (ABS(%s)) with param -42
                    Builtins.Abs(-3.14),  # -> (ABS(%s)) with param -3.14
                ])
        """
        sql, p, dt, c = Builtins._normalize(value)
        result_dt = dt if dt in (int, float) else float
        return Builtins._make(f'(ABS({sql}))', p, result_dt, c)

    @staticmethod
    def Round(value):
        """Round a number to the nearest integer using MySQL's ``ROUND()`` function.

        Generates a SQL ``ROUND(<expr>)`` expression. MySQL's single-arg
        ``ROUND`` rounds to zero decimal places. Unlike SQLite, MySQL's
        ``ROUND`` returns the **same type as the input** when possible:
        ``ROUND(INTEGER)`` returns an INTEGER, ``ROUND(DECIMAL)`` returns
        a DECIMAL, ``ROUND(DOUBLE)`` returns a DOUBLE. Because we cannot
        know the underlying type reliably, ``current_datatype`` is set to
        ``float`` — the safest choice for downstream arithmetic.

        To round to a specific number of decimal places, use
        :meth:`RoundTo` or wrap with ``Builtins.Func('ROUND', value, n)``.

        Args:
            value: The expression whose value is rounded. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(ROUND(<expr>))`` and whose ``current_datatype`` is always
            ``float``.

        Example:
            Round a computed price to the nearest integer::

                from Ormophine.Mysql import Driver, Builtins

                db       = Driver(host='localhost', port=3306, username='root',
                                  password='secret', db_name='store')
                products = db.products

                rows = products.get_row([
                    products.name,
                    Builtins.Round(products.price * 1.07),
                ])
                # SELECT `products`.`name`,
                #        (ROUND((`products`.`price` * %s)))
                # FROM `products`
                # Parameters: [1.07]

            Round then cast to integer::

                rows = products.get_row([
                    Builtins.Int(Builtins.Round(products.price)),
                ])
                # SELECT (CAST((ROUND(`products`.`price`)) AS SIGNED))
                # FROM `products`

            Round an aggregate::

                rows = products.get_row([
                    Builtins.Round(Builtins.Avg(products.price) * 100) / 100,
                ])
                # Two-decimal average price:
                # SELECT ((ROUND(((AVG(`products`.`price`)) * %s))) / %s)
                # FROM `products`
                # Parameters: [100, 100]

            Filter by rounded value::

                rows = products.get_row(
                    [products.name, products.price],
                    where=Builtins.Round(products.price) > 100,
                )
                # SELECT ... WHERE ((ROUND(`products`.`price`)) > %s)
                # Parameters: [100]

            Chained with arithmetic — ``current_datatype`` is float, so
            arithmetic stays numeric::

                padded = Builtins.Round(products.price) * 1.1
                # SELECT ((ROUND(`products`.`price`)) * %s) FROM `products`
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(ROUND({sql}))', p, float, c)

    @staticmethod
    def RoundTo(value, decimals):
        """Round a number to a fixed number of decimal places using ``ROUND(x, n)``.

        Generates ``ROUND(<expr>, <n>)``. The second argument is a plain
        integer literal (not a parameterised value) because MySQL requires
        it to be a constant at query-parse time. Rounds half away from
        zero, matching MySQL's default rounding mode.

        Use this instead of composing ``Round(value * 100) / 100`` when
        you want MySQL's native, precise decimal rounding rather than
        floating-point tricks.

        Args:
            value: The expression whose value is rounded. Supported types
                are the same as for :meth:`Round`.
            decimals (int): Number of digits after the decimal point.
                Negative values round to the left of the decimal point
                (``RoundTo(123.45, -1)`` → ``120``).

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(ROUND(<expr>, <n>))`` and whose ``current_datatype`` is
            ``float``.

        Example:
            Two-decimal prices::

                rows = products.get_row([
                    products.name,
                    Builtins.RoundTo(products.price, 2),
                ])
                # SELECT `products`.`name`, (ROUND(`products`.`price`, 2))
                # FROM `products`

            Round to hundreds::

                rows = products.get_row([
                    Builtins.RoundTo(products.revenue, -2),
                ])
                # SELECT (ROUND(`products`.`revenue`, -2)) FROM `products`

            Average with two decimals — a cleaner alternative to
            ``Round(Avg(x) * 100) / 100``::

                rows = products.get_row([
                    Builtins.RoundTo(Builtins.Avg(products.price), 2),
                ])
                # SELECT (ROUND((AVG(`products`.`price`)), 2)) FROM `products`
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(ROUND({sql}, {int(decimals)}))', p, float, c)

    @staticmethod
    def Floor(value):
        """Round a number down to the nearest integer using MySQL's ``FLOOR()``.

        Generates a ``FLOOR(<expr>)`` expression. For positive numbers
        this behaves like truncation toward zero; for negative numbers it
        rounds away from zero (``FLOOR(-1.5) = -2``, unlike
        ``CAST(-1.5 AS SIGNED)`` which gives ``-1``).

        MySQL returns an INTEGER when the input is an INTEGER or DECIMAL;
        the ``current_datatype`` is set to ``int``.

        Args:
            value: The expression to floor. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(FLOOR(<expr>))`` and whose ``current_datatype`` is ``int``.

        Example:
            Snap a price down to the whole dollar::

                from Ormophine.Mysql import Driver, Builtins

                db       = Driver(host='localhost', port=3306, username='root',
                                  password='secret', db_name='store')
                products = db.products

                rows = products.get_row([
                    products.name,
                    products.price,
                    Builtins.Floor(products.price),
                ])
                # SELECT `products`.`name`, `products`.`price`,
                #        (FLOOR(`products`.`price`))
                # FROM `products`
                # -> e.g. [('Widget', 19.99, 19), ('Gadget', 24.50, 24), ...]

            Bucket scores into deciles::

                decile = Builtins.Floor(products.score / 10) * 10
                rows = products.get_row([decile, Builtins.Count('*')])
                # SELECT ((FLOOR((`products`.`score` / %s))) * %s),
                #        (COUNT(*))
                # FROM `products`
                # GROUP BY ... (grouping is done by caller)
                # Parameters: [10, 10]

            Handle negative values correctly (FLOOR rounds down, not
            toward zero)::

                rows = products.get_row([
                    Builtins.Floor(-1.5),   # -> -2.0 in MySQL
                    Builtins.Int(-1.5),     # -> -1 (CAST truncates, not floor)
                ])

            Filter by floored value::

                rows = products.get_row(
                    [products.name, products.price],
                    where=Builtins.Floor(products.price) >= 20,
                )
                # SELECT ... WHERE ((FLOOR(`products`.`price`)) >= %s)
                # Parameters: [20]

            Combined with arithmetic — stays numeric::

                discount = Builtins.Floor(products.price * 0.8)
                rows = products.get_row([products.name, discount])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(FLOOR({sql}))', p, int, c)

    @staticmethod
    def Ceil(value):
        """Round a number up to the nearest integer using MySQL's ``CEIL()``.

        Generates a ``CEIL(<expr>)`` expression. For positive numbers
        this rounds away from zero; for negative numbers it rounds toward
        zero (``CEIL(-1.5) = -1``, unlike ``FLOOR(-1.5) = -2``). This is
        the mirror image of :meth:`Floor`.

        MySQL returns an INTEGER when the input is an INTEGER or DECIMAL;
        the ``current_datatype`` is set to ``int``.

        Args:
            value: The expression to ceil. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CEIL(<expr>))`` and whose ``current_datatype`` is ``int``.

        Example:
            Snap a price up to the whole dollar — a common "don't lose
            money on rounding" pattern::

                from Ormophine.Mysql import Driver, Builtins

                db       = Driver(host='localhost', port=3306, username='root',
                                  password='secret', db_name='store')
                products = db.products

                rows = products.get_row([
                    products.name,
                    products.price,
                    Builtins.Ceil(products.price),
                ])
                # SELECT `products`.`name`, `products`.`price`,
                #        (CEIL(`products`.`price`))
                # FROM `products`
                # -> e.g. [('Widget', 19.01, 20), ('Gadget', 24.00, 24), ...]

            Pagination — compute how many pages of 20 items each::

                page_count = Builtins.Ceil(Builtins.Count('*') / 20)
                rows = products.get_row([page_count])
                # SELECT (CEIL(((COUNT(*)) / %s))) FROM `products`
                # Parameters: [20]

            Bucket scores into the next higher 10::

                next_ten = Builtins.Ceil(products.score / 10) * 10
                rows = products.get_row([products.id, next_ten])

            Handle negatives correctly::

                rows = products.get_row([
                    Builtins.Ceil(-1.5),   # -> -1 in MySQL
                    Builtins.Int(-1.5),    # -> -1 (same here, different reason)
                ])

            Combine with Floor to build a rounded-down/rounded-up pair::

                low  = Builtins.Floor(products.price)
                high = Builtins.Ceil(products.price)
                rows = products.get_row([products.price, low, high])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CEIL({sql}))', p, int, c)

    # =================================================================== type cast

    @staticmethod
    def Int(value):
        """Convert a value to an integer using MySQL's ``CAST(x AS SIGNED)``.

        This is the SQL equivalent of Python's ``int()``. Generates a
        ``CAST(<expr> AS SIGNED)`` expression — MySQL's 64-bit signed
        integer type. MySQL's conversion rules apply: text is parsed as
        a number (leading digits only), REAL is truncated toward zero,
        and NULL stays NULL.

        The result is always an ``INTEGER``, so arithmetic chains and
        comparisons behave as expected even when the original column was
        declared as TEXT or DECIMAL.

        .. note::
            Use ``Builtins.Int`` (SIGNED) rather than a hypothetical
            ``CAST AS INTEGER`` — MySQL rejects ``INTEGER`` in a CAST
            expression; the correct name is ``SIGNED`` (or
            ``UNSIGNED`` for non-negative values).

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS SIGNED))`` and whose ``current_datatype``
            is always ``int``.

        Example:
            Force a text column to be treated as an integer::

                from Ormophine.Mysql import Driver, Builtins

                db     = Driver(host='localhost', port=3306, username='root',
                                password='secret', db_name='app')
                events = db.events

                rows = events.get_row([
                    events.id,
                    Builtins.Int(events.payload),
                ])
                # SELECT `events`.`id`,
                #        (CAST(`events`.`payload` AS SIGNED))
                # FROM `events`

            Compare a text column numerically::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.Int(events.amount_text) > 1000,
                )
                # SELECT `events`.`id` FROM `events`
                # WHERE ((CAST(`events`.`amount_text` AS SIGNED)) > %s)
                # Parameters: [1000]

            Truncate a REAL toward zero::

                rows = events.get_row([
                    Builtins.Int(events.temperature),   # 23.7 -> 23
                ])
                # SELECT (CAST(`events`.`temperature` AS SIGNED))
                # FROM `events`

            Combine with arithmetic — stays numeric::

                doubled = Builtins.Int(events.count) * 2
                # SELECT ((CAST(`events`.`count` AS SIGNED)) * %s)
                # FROM `events`

            Used inside an aggregate::

                rows = events.get_row([
                    Builtins.Sum(Builtins.Int(events.payload)),
                ])
                # SELECT (SUM((CAST(`events`.`payload` AS SIGNED))))
                # FROM `events`
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS SIGNED))', p, int, c)

    @staticmethod
    def Float(value):
        """Convert a value to a floating-point number using ``CAST(x AS DECIMAL)``.

        This is the SQL equivalent of Python's ``float()``. Generates a
        ``CAST(<expr> AS DECIMAL(65,30))`` expression. MySQL uses
        DECIMAL for exact numerics; the ``(65,30)`` precision pair gives
        us a fixed-point type wide enough to hold any IEEE-754 double
        without losing significant digits, effectively emulating a float.

        Use ``Builtins.Func('CAST', value, 'DOUBLE')`` if you specifically
        need the DOUBLE storage class (e.g. for inf/NaN support, though
        MySQL does not support those values in DOUBLE either). For the
        vast majority of numeric conversions DECIMAL is safer and does
        not accumulate floating-point error.

        The result is always a DECIMAL, exposed here as ``float``, so any
        chained arithmetic naturally stays in the floating domain.

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS DECIMAL(65,30)))`` and whose
            ``current_datatype`` is always ``float``.

        Example:
            Force integer division to produce a real result::

                from Ormophine.Mysql import Driver, Builtins

                db         = Driver(host='localhost', port=3306, username='root',
                                    password='secret', db_name='analytics')
                statistics = db.statistics

                ratio = Builtins.Float(statistics.successes) / statistics.attempts
                rows = statistics.get_row([ratio])
                # SELECT ((CAST(`statistics`.`successes` AS DECIMAL(65,30)))
                #         / `statistics`.`attempts`)
                # FROM `statistics`
                # -> e.g. [(0.9732,)]

            Parse a text column as a number::

                rows = statistics.get_row(
                    [statistics.id, Builtins.Float(statistics.amount_text)],
                    where=Builtins.Float(statistics.amount_text) >= 99.5,
                )
                # SELECT `statistics`.`id`,
                #        (CAST(`statistics`.`amount_text` AS DECIMAL(65,30)))
                # FROM `statistics`
                # WHERE ((CAST(`statistics`.`amount_text` AS DECIMAL(65,30))) >= %s)
                # Parameters: [99.5]

            Widen an integer column before averaging::

                rows = statistics.get_row([
                    Builtins.Avg(Builtins.Float(statistics.count)),
                ])

            Multiply a converted value by a literal::

                scaled = Builtins.Float(statistics.score) * 1.5
                rows = statistics.get_row([scaled])
                # SELECT ((CAST(`statistics`.`score` AS DECIMAL(65,30))) * %s)
                # FROM `statistics`
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS DECIMAL(65,30)))', p, float, c)

    @staticmethod
    def Str(value):
        """Convert a value to text using MySQL's ``CAST(x AS CHAR)``.

        This is the SQL equivalent of Python's ``str()``. Generates a
        ``CAST(<expr> AS CHAR)`` expression. MySQL's conversion rules
        apply: numbers are formatted as their decimal representation,
        NULL stays NULL, and BLOB data is interpreted as text.

        The result is always a ``TEXT`` value, so chaining with ``+``
        produces string concatenation (``||``) rather than arithmetic
        addition.

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS CHAR))`` and whose ``current_datatype`` is
            always ``str``.

        Example:
            Safely concatenate a numeric column with text::

                from Ormophine.Mysql import Driver, Builtins

                db        = Driver(host='localhost', port=3306, username='root',
                                   password='secret', db_name='company')
                employees = db.employees

                label = Builtins.Str(employees.salary) + ' USD'
                rows = employees.get_row([employees.name, label])
                # SELECT `employees`.`name`,
                #        ((CAST(`employees`.`salary` AS CHAR)) || %s)
                # FROM `employees`
                # Parameters: [' USD']
                #
                # Without Builtins.Str, `employees.salary + ' USD'` would
                # compile to arithmetic '+' (because salary.datatype is int),
                # which MySQL would coerce the string to 0.

            Format an integer id for display::

                rows = employees.get_row([
                    Builtins.Str(employees.id).add_first('EMP-'),
                ])
                # SELECT (%s || (CAST(`employees`.`id` AS CHAR)))
                # FROM `employees`
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
                # SELECT `employees`.`id` FROM `employees`
                # WHERE ((CAST(`employees`.`id` AS CHAR)) LIKE %s || '%')
                # Parameters: ['1']
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS CHAR))', p, str, c)

    @staticmethod
    def Bool(value):
        """Convert a value to a boolean-like integer using ``CAST(x AS SIGNED)``.

        MySQL has no native boolean type — booleans are stored as
        ``TINYINT(1)`` with the integers ``0`` and ``1``. This helper
        mirrors Python's ``bool()`` by emitting a ``CAST(<expr> AS SIGNED)``
        expression and declaring the result as an ``INTEGER``. The caller
        is responsible for interpreting the returned integer as a truth
        value.

        In practice this is identical to :meth:`Int`; the separate name
        exists so that call sites read as intent (``Builtins.Bool(...)``
        rather than ``Builtins.Int(...)`` when the semantic meaning is a
        truth value).

        Args:
            value: The expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value (``True``, ``False``, ``0``, ``1``,
                  or any coercible value) — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS SIGNED))`` and whose ``current_datatype``
            is ``int``.

        Example:
            Normalise an is_active column that stores mixed values::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                normalised = Builtins.Bool(users.is_active)
                rows = users.get_row([users.id, normalised])
                # SELECT `users`.`id`, (CAST(`users`.`is_active` AS SIGNED))
                # FROM `users`

            Compare a computed condition against a boolean literal::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Bool(users.age >= 18) == 1,
                )
                # SELECT `users`.`id` FROM `users`
                # WHERE ((CAST((`users`.`age` >= %s) AS SIGNED)) = %s)
                # Parameters: [18, 1]

            Coerce a raw literal — useful when the surrounding API
            expects a ColumnsOperation-shaped object::

                rows = users.get_row([
                    Builtins.Bool(True),    # -> (CAST(%s AS SIGNED)) with param True
                    Builtins.Bool(False),   # -> (CAST(%s AS SIGNED)) with param False
                ])

            Use as a numeric value in a SUM::

                active_count = Builtins.Sum(Builtins.Bool(users.is_active))
                rows = users.get_row([active_count])
                # SELECT (SUM((CAST(`users`.`is_active` AS SIGNED))))
                # FROM `users`
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS SIGNED))', p, int, c)

    @staticmethod
    def Sign(value):
        """Return the sign of a number using MySQL's ``SIGN()`` function.

        Generates a ``SIGN(<expr>)`` expression. MySQL returns:

        - ``-1`` if the value is negative
        - `` 0`` if the value is zero
        - `` 1`` if the value is positive

        This mirrors Python's ``(x > 0) - (x < 0)`` idiom and is useful
        for bucketing, sorting by direction, or normalising deltas.

        Args:
            value: The expression whose sign is computed. Supported
                types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(SIGN(<expr>))`` and whose ``current_datatype`` is ``int``.

        Example:
            Bucket movements by direction — up, flat, or down::

                from Ormophine.Mysql import Driver, Builtins

                db        = Driver(host='localhost', port=3306, username='root',
                                   password='secret', db_name='analytics')
                movements = db.movements

                rows = movements.get_row([
                    movements.account_id,
                    movements.delta,
                    Builtins.Sign(movements.delta),
                ])
                # SELECT `movements`.`account_id`, `movements`.`delta`,
                #        (SIGN(`movements`.`delta`))
                # FROM `movements`
                # -> e.g. [(1, 250.0, 1), (1, -80.0, -1), (1, 0.0, 0), ...]

            Filter only the positive movements::

                rows = movements.get_row(
                    [movements.account_id, movements.delta],
                    where=Builtins.Sign(movements.delta) == 1,
                )
                # SELECT ... WHERE ((SIGN(`movements`.`delta`)) = %s)
                # Parameters: [1]

            Sum signs to count net direction — positive means more ups
            than downs, and vice versa::

                net = Builtins.Sum(Builtins.Sign(movements.delta))
                rows = movements.get_row([movements.account_id, net])
                # SELECT `movements`.`account_id`,
                #        (SUM((SIGN(`movements`.`delta`))))
                # FROM `movements`
                # GROUP BY ... (grouping is done by caller)

            Sign of a computed expression::

                range_mid = (movements.high + movements.low) / 2
                rows = movements.get_row([
                    movements.symbol,
                    Builtins.Sign(movements.close - range_mid),
                ])
                # SELECT `movements`.`symbol`,
                #        (SIGN((`movements`.`close` - ((`movements`.`high` + `movements`.`low`) / %s))))
                # FROM `movements`
                # Parameters: [2]

            Chained with arithmetic::

                direction_times_size = Builtins.Sign(movements.delta) * movements.delta
                rows = movements.get_row([
                    movements.account_id,
                    direction_times_size,
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(SIGN({sql}))', p, int, c)

    @staticmethod
    def Sqrt(value):
        """Compute the square root of a number using MySQL's ``SQRT()`` function.

        Generates a ``SQRT(<expr>)`` expression. The result is always a
        REAL (float) — even ``SQRT(4)`` returns ``2.0``, not ``2``.

        Negative inputs produce ``NULL`` in MySQL rather than raising an
        error. If your application needs to distinguish "no result" from
        "zero", wrap the call or add a ``CHECK`` constraint on the column.

        Args:
            value: The expression whose square root is computed. Supported
                types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value (``int``, ``float``) — bound as a
                  ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(SQRT(<expr>))`` and whose ``current_datatype`` is always
            ``float``.

        Example:
            Euclidean distance — the standard ``sqrt(a² + b²)`` pattern::

                from Ormophine.Mysql import Driver, Builtins

                db     = Driver(host='localhost', port=3306, username='root',
                                password='secret', db_name='geometry')
                points = db.points

                distance_from_origin = Builtins.Sqrt(
                    points.x * points.x + points.y * points.y
                )
                rows = points.get_row([
                    points.id,
                    distance_from_origin,
                ])
                # SELECT `points`.`id`,
                #        (SQRT(((`points`.`x` * `points`.`x`)
                #                + (`points`.`y` * `points`.`y`))))
                # FROM `points`

            Standard deviation of a small set — square root of the mean
            squared deviation::

                mean = Builtins.Avg(points.x)
                sq_dev = Builtins.Avg((points.x - mean) * (points.x - mean))
                stddev = Builtins.Sqrt(sq_dev)
                rows = points.get_row([stddev])
                # SELECT (SQRT((AVG(((`points`.`x` - (AVG(`points`.`x`)))
                #                     * (`points`.`x` - (AVG(`points`.`x`))))))))
                # FROM `points`

            Filter by magnitude — points more than 10 units from origin::

                rows = points.get_row(
                    [points.id, points.x, points.y],
                    where=Builtins.Sqrt(
                        points.x * points.x + points.y * points.y
                    ) > 10,
                )

            Combine with Round for display::

                pretty = Builtins.Round(
                    Builtins.Sqrt(points.x * points.x + points.y * points.y) * 100
                ) / 100
                rows = points.get_row([points.id, pretty])

            Applied to a raw literal::

                rows = points.get_row([
                    Builtins.Sqrt(16),    # -> (SQRT(%s)) with param 16 -> 4.0
                    Builtins.Sqrt(2),     # -> 1.41421356...
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(SQRT({sql}))', p, float, c)

    @staticmethod
    def Pow(base, exp):
        """Raise a base value to a power using MySQL's ``POW(a, b)`` function.

        Generates a ``POW(<base>, <exp>)`` expression. This is the SQL
        analogue of Python's built-in ``pow(base, exp)`` and the ``**``
        operator. Both operands may be any expression — a column, another
        builtin, a raw literal, or a nested :class:`ColumnsOperation`.

        The result is always a REAL (float) — even ``POW(2, 3)`` returns
        ``8.0``, not ``8``, because MySQL keeps all math functions in the
        floating-point domain (returning ``DOUBLE``).

        Args:
            base: The base expression. Any of the standard operand types:

                - :class:`ColumnsOperation`
                - :class:`Column`
                - A raw Python number

            exp: The exponent expression. Same accepted types as ``base``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(POW(<base>, <exp>))`` and whose ``current_datatype`` is
            always ``float``.

        Example:
            Compound interest — principal times ``(1 + rate)^years``::

                from Ormophine.Mysql import Driver, Builtins

                db       = Driver(host='localhost', port=3306, username='root',
                                  password='secret', db_name='bank')
                accounts = db.accounts

                future_value = accounts.principal * Builtins.Pow(
                    1 + accounts.rate,
                    accounts.years,
                )
                rows = accounts.get_row([
                    accounts.id,
                    future_value,
                ])
                # SELECT `accounts`.`id`,
                #        (`accounts`.`principal`
                #         * (POW((%s + `accounts`.`rate`), `accounts`.`years`)))
                # FROM `accounts`
                # Parameters: [1]

            Square or cube a value::

                rows = accounts.get_row([
                    Builtins.Pow(accounts.principal, 2),   # square
                    Builtins.Pow(accounts.principal, 3),   # cube
                ])
                # SELECT (POW(`accounts`.`principal`, %s)),
                #        (POW(`accounts`.`principal`, %s))
                # FROM `accounts`

            Square root via fractional exponent — equivalent to
            :meth:`Sqrt`::

                rows = accounts.get_row([
                    Builtins.Pow(accounts.principal, 0.5),
                ])
                # SELECT (POW(`accounts`.`principal`, %s)) FROM `accounts`
                # Parameters: [0.5]

            Inverse power — ``x⁻¹`` equals ``1/x``::

                rows = accounts.get_row([
                    Builtins.Pow(accounts.principal, -1),
                ])

            Distance squared without the square root::

                rows = accounts.get_row(
                    [accounts.id],
                    where=Builtins.Pow(accounts.x, 2)
                        + Builtins.Pow(accounts.y, 2) > 100,
                )

            Combine with Round for display::

                pretty = Builtins.Round(
                    Builtins.Pow(accounts.principal, 1.05) * 100
                ) / 100
                rows = accounts.get_row([accounts.id, pretty])

            Chained with arithmetic — stays numeric::

                doubled = Builtins.Pow(accounts.principal, 2) * 2
                # SELECT ((POW(`accounts`.`principal`, %s)) * %s)
                # FROM `accounts`
        """
        s1, p1, _, c = Builtins._normalize(base)
        s2, p2, _, _ = Builtins._normalize(exp)
        return Builtins._make(f'(POW({s1}, {s2}))', p1 + p2, float, c)

    # ================================================================ condition

    @staticmethod
    def IsNull(value):
        """Test whether a value is NULL.

        Generates an ``(<expr> IS NULL)`` predicate. MySQL evaluates this
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

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value — bound as a ``%s`` placeholder. In
                  particular, ``IsNull(None)`` produces ``(%s IS NULL)``
                  with the ``None`` bound as a parameter, which is always
                  true.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``((<expr>) IS NULL)`` and whose ``current_datatype`` is
            ``int`` — MySQL returns 0 or 1 for boolean predicates.

        Example:
            Select users who have not yet provided an email::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.IsNull(users.email),
                )
                # SELECT `users`.`id`, `users`.`username` FROM `users`
                # WHERE ((`users`.`email`) IS NULL)

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
                # SELECT ... WHERE (((`users`.`email`) IS NULL)
                #                    AND (`users`.`created_at` > %s))
                # Parameters: ['2024-01-01']

            Test a computed expression that might return NULL::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.IsNull(
                        Builtins.Sqrt(users.balance - users.debt)
                    ),
                )
                # -> users whose balance < debt (SQRT returns NULL)
                # SELECT `users`.`id` FROM `users`
                # WHERE ((SQRT((`users`.`balance` - `users`.`debt`))) IS NULL)

            Count how many rows have a NULL value in one column::

                missing_emails = Builtins.Sum(Builtins.IsNull(users.email))
                rows = users.get_row([missing_emails])
                # SELECT (SUM(((`users`.`email`) IS NULL))) FROM `users`
                # -> [(42,)] if 42 users have no email

            Check for a raw literal ``None``::

                rows = users.get_row([
                    Builtins.IsNull(None),   # -> ((%s) IS NULL) -> always 1
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(({sql}) IS NULL)', p, int, c)

    @staticmethod
    def IsNotNull(value):
        """Test whether a value is not NULL.

        Generates an ``(<expr> IS NOT NULL)`` predicate. MySQL evaluates
        this to ``1`` (true) when the expression produces any non-NULL
        value, and ``0`` (false) when it evaluates to NULL.

        The exact logical negation of :meth:`IsNull`. Use whichever reads
        more naturally at the call site — both compile to distinct SQL
        but produce the same set of rows when their results are inverted.

        Args:
            value: The expression to test. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value — bound as a ``%s`` placeholder. In
                  particular, ``IsNotNull(42)`` produces
                  ``(%s IS NOT NULL)`` with the ``42`` bound as a
                  parameter, which is always true; ``IsNotNull(None)`` is
                  always false.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``((<expr>) IS NOT NULL)`` and whose ``current_datatype`` is
            ``int``.

        Example:
            Select users who have provided an email::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row(
                    [users.id, users.username, users.email],
                    where=Builtins.IsNotNull(users.email),
                )
                # SELECT `users`.`id`, `users`.`username`, `users`.`email`
                # FROM `users`
                # WHERE ((`users`.`email`) IS NOT NULL)

            Combine with OR to allow either of two identifier columns::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.IsNotNull(users.email)
                        | Builtins.IsNotNull(users.phone),
                )
                # SELECT `users`.`id` FROM `users`
                # WHERE (((`users`.`email`) IS NOT NULL)
                #        OR ((`users`.`phone`) IS NOT NULL))

            Count non-NULL values in a column — the inverse of the
            ``IsNull`` count::

                have_email = Builtins.Sum(Builtins.IsNotNull(users.email))
                rows = users.get_row([have_email])
                # SELECT (SUM(((`users`.`email`) IS NOT NULL))) FROM `users`

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
        MySQL evaluates this to ``1`` (true) when ``low <= value <= high``
        and ``0`` otherwise. Both bounds are inclusive, matching Python's
        ``low <= x <= high`` idiom exactly.

        .. note::
            MySQL's ``BETWEEN`` is equivalent to
            ``(value >= low) AND (value <= high)`` but is a single
            operator with well-defined semantics for all three operand
            types. When any of the three operands is NULL the result is
            NULL, which the surrounding query treats as "false" in a
            ``WHERE`` clause.

        Args:
            value: The expression to test. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python value — bound as a ``%s`` placeholder.

            low: The lower bound (inclusive). Same accepted types as
                ``value``.

            high: The upper bound (inclusive). Same accepted types as
                ``value``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``((<value>) BETWEEN <low> AND <high>)`` and whose
            ``current_datatype`` is ``int``. Parameters are concatenated
            left-to-right: first ``value``'s, then ``low``'s, then
            ``high``'s.

        Example:
            Select products in a price band::

                from Ormophine.Mysql import Driver, Builtins

                db       = Driver(host='localhost', port=3306, username='root',
                                  password='secret', db_name='store')
                products = db.products

                rows = products.get_row(
                    [products.name, products.price],
                    where=Builtins.Between(products.price, 10.0, 50.0),
                )
                # SELECT `products`.`name`, `products`.`price` FROM `products`
                # WHERE ((`products`.`price`) BETWEEN %s AND %s)
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
                # SELECT ... WHERE ((`users`.`created_at`)
                #                    BETWEEN %s AND %s)
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
                # SELECT `products`.`name` FROM `products`
                # WHERE ((`products`.`price` * %s) BETWEEN %s AND %s)
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
                # SELECT ... WHERE ((`products`.`price`)
                #                    BETWEEN `products`.`cost`
                #                        AND (`products`.`cost` * %s))
                # Parameters: [2]

            Negate the check — rows outside the band::

                in_band = Builtins.Between(products.price, 10.0, 50.0)
                rows = products.get_row(
                    [products.name],
                    where=(in_band == 0),
                )
                # SELECT `products`.`name` FROM `products`
                # WHERE ((((`products`.`price`) BETWEEN %s AND %s)) = %s)
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

        Generates an ``IF(<cond>, <then>, <else>)`` expression. MySQL
        evaluates ``condition`` first; if it is truthy (any non-zero,
        non-NULL value), the expression yields ``then_value``; otherwise
        it yields ``else_value``.

        This is the direct equivalent of Python's ternary conditional
        operator::

            Python:   x if cond else y
            SQL:      IF(cond, x, y)
            ORM:      Builtins.IIf(cond, x, y)

        .. note::
            Unlike Python's ``and`` / ``or``, MySQL's ``IF`` **always
            evaluates both branches** before choosing one. This matters
            for expressions with potential errors — e.g. division by
            zero returns NULL rather than skipping. If both branches
            might divide by zero, guard the divisor with an inner
            ``IIf``.

        Args:
            condition: The test expression. May be any standard operand:

                - :class:`ColumnsOperation` — typically a comparison
                  like ``users.age >= 18``.
                - :class:`Column` — used directly as a boolean.
                - A raw Python value (``True``, ``False``, ``0``, ``1``)
                  — bound as a parameter. MySQL treats ``0`` as false
                  and any other number as true.

            then_value: What to return when ``condition`` is truthy.
                Same accepted types as ``condition``.

            else_value: What to return when ``condition`` is falsy.
                Same accepted types as ``condition``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(IF(<cond>, <then>, <else>))`` and whose
            ``current_datatype`` is ``None``. The datatype is not
            propagated because the two branches may disagree (e.g.
            ``str`` versus ``int``); downstream ``+`` operators will
            choose arithmetic by default, which the caller may override
            by wrapping the result in :meth:`Str`, :meth:`Int`, or
            :meth:`Float`.

        Example:
            Categorise ages into minor / adult — the classic pattern::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                category = Builtins.IIf(users.age >= 18, 'adult', 'minor')
                rows = users.get_row([
                    users.name,
                    users.age,
                    category,
                ])
                # SELECT `users`.`name`, `users`.`age`,
                #        (IF((`users`.`age` >= %s), %s, %s))
                # FROM `users`
                # Parameters: [18, 'adult', 'minor']
                # -> [('Alice', 30, 'adult'), ('Bob', 15, 'minor'), ...]

            Fill NULL with a fallback — equivalent to ``COALESCE`` but
            with a boolean test::

                display_email = Builtins.IIf(
                    Builtins.IsNull(users.email),
                    'no email',
                    users.email,
                )
                rows = users.get_row([users.username, display_email])
                # SELECT `users`.`username`,
                #        (IF(((`users`.`email`) IS NULL), %s, `users`.`email`))
                # FROM `users`
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
                # (IF((`users`.`score` >= %s), ?, (IF((`users`.`score` >= %s),
                #      ?, (IF((`users`.`score` >= %s), ?, ?))))))
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
                # SELECT `users`.`name`, `users`.`salary`,
                #        (IF((`users`.`rating` > %s),
                #             (`users`.`salary` * %s),
                #             `users`.`salary`))
                # FROM `users`
                # Parameters: [4, 1.1]

            Coerce the result to a specific type with a cast builtin::

                label_num = Builtins.Int(
                    Builtins.IIf(users.is_active == 1, 100, 0)
                )
                rows = users.get_row([label_num])

            Count matches via SUM of IF — a common "conditional
            aggregate" idiom::

                active_count = Builtins.Sum(
                    Builtins.IIf(users.is_active == 1, 1, 0)
                )
                rows = users.get_row([active_count])
                # SELECT (SUM((IF((`users`.`is_active` = %s), %s, %s))))
                # FROM `users`
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
        return Builtins._make(f'(IF({cs}, {ts}, {es}))', cp + tp + ep, None, c)

    # ============================================================ date and time

    @staticmethod
    def Date(value):
        """Extract the date portion of a value using MySQL's ``DATE()`` function.

        Generates a ``DATE(<expr>)`` expression. The result is a TEXT
        string in ``'YYYY-MM-DD'`` format. Inputs accepted by MySQL
        include:

        - An ISO date/datetime string: ``'2024-03-15'``,
          ``'2024-03-15 09:30:00'``
        - A ``DATE``/``DATETIME``/``TIMESTAMP`` column
        - A numeric Unix epoch value (converted implicitly)
        - The literal string ``'now'`` — special-cased here to emit
          MySQL's ``CURDATE()``

        This is the SQL equivalent of Python's ``datetime.date()``
        method: it discards the time-of-day component.

        Args:
            value: The expression whose date component is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.
                - The literal string ``'now'`` — special-cased to
                  ``CURDATE()``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(DATE(<expr>))`` (or ``(CURDATE())`` for the ``'now'``
            case) and whose ``current_datatype`` is ``str``.

        Example:
            Get the signup date for every user — strip the time
            component::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row([
                    users.id,
                    users.created_at,
                    Builtins.Date(users.created_at),
                ])
                # SELECT `users`.`id`, `users`.`created_at`,
                #        (DATE(`users`.`created_at`))
                # FROM `users`
                # -> [(1, '2024-03-15 09:30:42', '2024-03-15'), ...]

            Filter by a specific day — everything created on March 15::

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.Date(users.created_at) == '2024-03-15',
                )
                # SELECT `users`.`id`, `users`.`username` FROM `users`
                # WHERE ((DATE(`users`.`created_at`)) = %s)
                # Parameters: ['2024-03-15']

            Group by day and count — do the grouping in Python after
            fetching, since the ORM has no GROUP BY helper::

                rows = users.get_row([Builtins.Date(users.created_at)])
                from collections import Counter
                daily = Counter(d for (d,) in rows)
                # {'2024-03-15': 12, '2024-03-16': 8, ...}

            Compare against the current date — the ``'now'`` keyword
            special case::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Date(users.created_at) == Builtins.Date('now'),
                )
                # SELECT `users`.`id` FROM `users`
                # WHERE ((DATE(`users`.`created_at`)) = (CURDATE()))

            Chain with date modifiers for windows of time::

                first_of_month = Builtins.DateAdd(users.created_at, 'start of month')
                rows = users.get_row([
                    users.id,
                    first_of_month,
                ])
                # SELECT `users`.`id`,
                #        (DATE(DATE_FORMAT(`users`.`created_at`, '%Y-%m-01')))
                # FROM `users`

            Pass a raw literal::

                rows = users.get_row([
                    Builtins.Date('2024-03-15 14:30:00'),   # -> '2024-03-15'
                ])
        """
        if Builtins._is_now(value):
            return Builtins._make('(CURDATE())', [], str, Builtins._NullCol)
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(DATE({sql}))', p, str, c)

    @staticmethod
    def Time(value):
        """Extract the time-of-day portion of a value using MySQL's ``TIME()``.

        Generates a ``TIME(<expr>)`` expression. The result is a TEXT
        string in ``'HH:MM:SS'`` format. Inputs accepted by MySQL mirror
        those of :meth:`Date`:

        - An ISO date/datetime string: ``'2024-03-15 09:30:00'``
        - A ``TIME``/``DATETIME``/``TIMESTAMP`` column
        - The literal string ``'now'`` — special-cased here to emit
          MySQL's ``CURTIME()``

        This is the SQL equivalent of Python's ``datetime.time()``
        method: it discards the date component.

        Args:
            value: The expression whose time component is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.
                - The literal string ``'now'`` — special-cased to
                  ``CURTIME()``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(TIME(<expr>))`` (or ``(CURTIME())`` for the ``'now'``
            case) and whose ``current_datatype`` is ``str``.

        Example:
            Get the signup time for every user::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row([
                    users.id,
                    users.created_at,
                    Builtins.Time(users.created_at),
                ])
                # SELECT `users`.`id`, `users`.`created_at`,
                #        (TIME(`users`.`created_at`))
                # FROM `users`
                # -> [(1, '2024-03-15 09:30:42', '09:30:42'), ...]

            Filter by time-of-day range — office-hours signups::

                rows = users.get_row(
                    [users.id, users.username],
                    where=Builtins.Time(users.created_at) >= '09:00:00'
                        and Builtins.Time(users.created_at) < '17:00:00',
                )
                # Because BETWEEN is inclusive on both ends, use two
                # comparisons for a half-open range.
                # SELECT ... WHERE ((TIME(`users`.`created_at`)) >= %s)
                #               AND ((TIME(`users`.`created_at`)) < %s)
                # Parameters: ['09:00:00', '17:00:00']

            Extract the hour via :meth:`Hour` instead of slicing::

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
                # SELECT `users`.`id` FROM `users`
                # WHERE ((TIME(`users`.`created_at`)) < (CURTIME()))

            Pass a raw literal::

                rows = users.get_row([
                    Builtins.Time('2024-03-15 14:30:00'),   # -> '14:30:00'
                ])

            Build a compact "time ago" bucket with IIf::

                bucket = Builtins.IIf(
                    Builtins.Hour(users.created_at) < 12,
                    'AM',
                    'PM',
                )
                rows = users.get_row([users.id, bucket])
        """
        if Builtins._is_now(value):
            return Builtins._make('(CURTIME())', [], str, Builtins._NullCol)
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(TIME({sql}))', p, str, c)

    @staticmethod
    def DateTime(value):
        """Normalise a value to a full datetime using ``CAST(x AS DATETIME)``.

        MySQL has no ``DATETIME()`` normalizer function like SQLite's
        ``datetime()``; the closest equivalent is a ``CAST`` to the
        ``DATETIME`` storage type. The result is a TEXT string in
        ``'YYYY-MM-DD HH:MM:SS'`` format. Inputs accepted by MySQL
        mirror those of :meth:`Date` and :meth:`Time`:

        - An ISO date or datetime string
        - A numeric Unix epoch value (converted implicitly)
        - The literal string ``'now'`` — special-cased here to emit
          MySQL's ``NOW()``

        Its main uses are:

        - **Normalising** inputs of mixed shape so they all compare
          consistently.
        - **Upgrading** a date-only string (``'2024-03-15'``) to a full
          datetime (``'2024-03-15 00:00:00'``).
        - **Getting the current timestamp** via ``DateTime('now')``.

        Args:
            value: The expression whose full datetime is produced.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.
                - The literal string ``'now'`` — special-cased to
                  ``NOW()``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CAST(<expr> AS DATETIME))`` (or ``(NOW())`` for the
            ``'now'`` case) and whose ``current_datatype`` is ``str``.

        Example:
            Normalise mixed-format timestamps for display::

                from Ormophine.Mysql import Driver, Builtins

                db     = Driver(host='localhost', port=3306, username='root',
                                password='secret', db_name='app')
                events = db.events

                rows = events.get_row([
                    events.id,
                    events.occurred_at,                       # mixed shapes
                    Builtins.DateTime(events.occurred_at),   # all normalised
                ])
                # SELECT `events`.`id`, `events`.`occurred_at`,
                #        (CAST(`events`.`occurred_at` AS DATETIME))
                # FROM `events`
                # -> [(1, '2024-03-15', '2024-03-15 00:00:00'), ...]

            Get the current datetime as a SELECT column::

                rows = events.get_row([
                    Builtins.DateTime('now'),
                ])
                # SELECT (NOW()) FROM `events`
                # -> [('2024-03-15 14:30:42',)]

            Compare against the current datetime for "last 24 hours"::

                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.DateTime(events.occurred_at)
                        >= Builtins.DateTimeAdd('now', '-1 day'),
                )
                # SELECT `events`.`id`, `events`.`occurred_at` FROM `events`
                # WHERE ((CAST(`events`.`occurred_at` AS DATETIME))
                #         >= (DATE_SUB(NOW(), INTERVAL 1 DAY)))

            Compare against the current datetime for "last week"::

                rows = events.get_row(
                    [events.id],
                    where=Builtins.DateTime(events.occurred_at)
                        >= Builtins.DateTimeAdd('now', '-7 days'),
                )

            Combine with IIf to bucket events into "recent / older"::

                recent = Builtins.IIf(
                    Builtins.DateTime(events.occurred_at)
                        >= Builtins.DateTimeAdd('now', '-1 day'),
                    'recent',
                    'older',
                )
                rows = events.get_row([events.id, recent])

            Store into a datetime column during an UPDATE::

                events.update(
                    update={events.last_seen: Builtins.DateTime('now')},
                    where=events.id == 42,
                )
                # UPDATE `events` SET `last_seen`=(NOW())
                # WHERE (`events`.`id` = %s)

            Pass a raw literal to normalise at the SQL layer::

                rows = events.get_row([
                    Builtins.DateTime('2024-03-15'),           # -> '2024-03-15 00:00:00'
                    Builtins.DateTime('2024-03-15 09:30:00'),  # unchanged
                ])
        """
        if Builtins._is_now(value):
            return Builtins._make('(NOW())', [], str, Builtins._NullCol)
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS DATETIME))', p, str, c)

    # ============================================================ now / today

    @staticmethod
    def Now(_=None):
        """Return the current moment as a MySQL ``NOW()`` value.

        Generates a ``NOW()`` expression. The result is a TEXT string in
        ISO 8601 format: ``'YYYY-MM-DD HH:MM:SS'``, in the server's
        session time zone (``@@session.time_zone``), which defaults to
        ``SYSTEM`` (the OS time zone).

        No parameters are consumed. The optional positional argument
        ``_`` exists only to make the signature uniform with the other
        date/time helpers and to allow the callable to be passed to APIs
        that expect a one-argument function. It is ignored.

        For the corresponding date-only form, see :meth:`Today`. For an
        integer Unix timestamp, see :meth:`UnixNow`. For UTC-normalised
        output when the server runs in a non-UTC time zone, chain
        through ``Builtins.Func('CONVERT_TZ', value, '+00:00', ...)`` or
        set ``SET time_zone = '+00:00'`` on the connection.

        Args:
            _: Ignored. Any value passed is discarded; the SQL emitted is
                always ``NOW()``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(NOW())`` and whose ``current_datatype`` is ``str``. The
            parameter list is always empty.

        Example:
            The current timestamp as a SELECT column::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row([Builtins.Now()])
                # SELECT (NOW()) FROM `users`
                # -> [('2024-03-15 14:30:42',)] — same value for every row
                #    in the result set, because MySQL evaluates NOW() once
                #    per query, not per row.

            Compute account age in days::

                age = Builtins.DateDiffDays(Builtins.Now(), users.created_at)
                rows = users.get_row([users.username, age])
                # SELECT `users`.`username`, (DATEDIFF(NOW(), `users`.`created_at`))
                # FROM `users`

            Compute account age in a human-readable format::

                age_str = Builtins.Timediff(Builtins.Now(), users.created_at)
                rows = users.get_row([users.username, age_str])
                # -> [('Alice', '02 05:29:18'), ...]

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
                # UPDATE `users` SET `last_seen`=(NOW())
                # WHERE (`users`.`id` = %s);
                # Parameters: [42]

            Insert with an explicit timestamp — use the raw form for
            inserts when the value must be produced by SQL::

                users.custom_execute(
                    "INSERT INTO `users` (`username`, `created_at`) "
                    "VALUES (%s, NOW())",
                    ['alice'],
                )

            Compare two Now() calls to see that both evaluate to the
            same moment in a single query::

                rows = users.get_row([
                    Builtins.Now(),
                    Builtins.Now(),
                ])
                # -> [('2024-03-15 14:30:42', '2024-03-15 14:30:42')]
                # Both columns are identical.

            Force a specific time zone for the current moment::

                utc_now = Builtins.Func('CONVERT_TZ', Builtins.Now(), '+00:00', '+00:00')
                rows = users.get_row([utc_now])
                # -> [('2024-03-15 14:30:42',)] — no-op if server is UTC
        """
        return Builtins._make('(NOW())', [], str, Builtins._NullCol)

    @staticmethod
    def Today(_=None):
        """Return the current date as a MySQL ``CURDATE()`` value.

        Generates a ``CURDATE()`` expression. The result is a TEXT string
        in ISO 8601 format: ``'YYYY-MM-DD'``, in the server's session
        time zone. No parameters are consumed. This is the date-only
        counterpart of :meth:`Now`.

        The optional positional argument ``_`` exists only to make the
        signature uniform with the other date/time helpers; it is
        ignored.

        For the corresponding datetime, see :meth:`Now`. For an integer
        Unix timestamp, see :meth:`UnixNow`.

        Args:
            _: Ignored. Any value passed is discarded; the SQL emitted is
                always ``CURDATE()``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(CURDATE())`` and whose ``current_datatype`` is ``str``.
            The parameter list is always empty.

        Example:
            The current date as a SELECT column::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row([Builtins.Today()])
                # SELECT (CURDATE()) FROM `users`
                # -> [('2024-03-15',)]

            Find users who signed up today::

                rows = users.get_row(
                    [users.username, users.created_at],
                    where=Builtins.Date(users.created_at) == Builtins.Today(),
                )
                # SELECT `users`.`username`, `users`.`created_at` FROM `users`
                # WHERE ((DATE(`users`.`created_at`)) = (CURDATE()))

            Same-day boolean flag via IIf::

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
                # UPDATE `users` SET `last_active_date`=(CURDATE())
                # WHERE (`users`.`id` = %s);
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
                # SELECT `users`.`username` FROM `users`
                # WHERE ((CURDATE()) > %s)
                # Parameters: ['2024-01-01']
        """
        return Builtins._make('(CURDATE())', [], str, Builtins._NullCol)

    @staticmethod
    def UnixNow(_=None):
        """Return the current moment as an integer Unix timestamp.

        Generates a ``UNIX_TIMESTAMP()`` expression. The result is an
        INTEGER equal to the number of whole seconds since the Unix
        epoch (midnight UTC on 1 January 1970). No parameters are
        consumed.

        This is the numeric counterpart of :meth:`Now` and matches the
        return value of Python's ``time.time()`` (rounded down to an
        integer). Because the result is a plain integer, it is the best
        choice for cache keys, request IDs, expiry timestamps, and any
        arithmetic that needs sub-day precision without floating-point
        round-off.

        Note that MySQL's ``UNIX_TIMESTAMP()`` is time-zone independent
        for the current moment — it always returns the count of seconds
        since the epoch, regardless of ``@@session.time_zone``.

        The optional positional argument ``_`` exists only to make the
        signature uniform with the other date/time helpers; it is
        ignored.

        Args:
            _: Ignored. Any value passed is discarded; the SQL emitted is
                always ``UNIX_TIMESTAMP()``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(UNIX_TIMESTAMP())`` and whose ``current_datatype`` is
            ``int``. The parameter list is always empty.

        Example:
            Current Unix timestamp as a SELECT column::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row([Builtins.UnixNow()])
                # SELECT (UNIX_TIMESTAMP()) FROM `users`
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
                # SELECT `users`.`username`, `users`.`created_at` FROM `users`
                # WHERE (((UNIX_TIMESTAMP()) - (UNIX_TIMESTAMP(`users`.`created_at`))) < %s)
                # Parameters: [86400]

            Generate a per-request cache key — combine with a user id::

                cache_key = Builtins.Concat(
                    'user:',
                    Builtins.Str(users.id),
                    ':',
                    Builtins.Str(Builtins.UnixNow()),
                )
                rows = users.get_row([cache_key])
                # -> [('user:42:1710513042',), ...]

            Store the current epoch in an UPDATE — useful for
            portability-friendly integer columns::

                users.update(
                    update={users.last_login_epoch: Builtins.UnixNow()},
                    where=users.id == 42,
                )
                # UPDATE `users` SET `last_login_epoch`=(UNIX_TIMESTAMP())
                # WHERE (`users`.`id` = %s);
                # Parameters: [42]

            Compute a future expiry — a session token valid for 1 hour::

                expires_at = Builtins.UnixNow() + 3600
                rows = users.get_row([users.id, expires_at])
                # -> [(1, 1710516642), ...]

            Set a session expiry during an UPDATE and later check it
            with a plain integer comparison::

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
        return Builtins._make('(UNIX_TIMESTAMP())', [], int, Builtins._NullCol)

    # ================================================================ UnixEpoch

    @staticmethod
    def UnixEpoch(value):
        """Convert a date/time value to a Unix timestamp using ``UNIX_TIMESTAMP(x)``.

        Generates a ``UNIX_TIMESTAMP(<expr>)`` expression. The result is
        an INTEGER equal to the number of whole seconds since the Unix
        epoch (midnight UTC on 1 January 1970). The input must be a
        valid ``DATE``/``DATETIME``/``TIMESTAMP`` value or an ISO
        formatted string.

        .. note::
            ``UNIX_TIMESTAMP(<expr>)`` interprets the input in the
            server's session time zone by default. If your column stores
            UTC but the server runs in a non-UTC zone, the returned epoch
            will be offset. Normalise the column to UTC first with
            ``CONVERT_TZ`` if this matters.

        The literal string ``'now'`` is special-cased to emit
        ``UNIX_TIMESTAMP()`` — the same value :meth:`UnixNow` produces —
        so the SQLite calling convention still works.

        Args:
            value: The date/time expression to convert. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python string — bound as a ``%s`` placeholder.
                - The literal string ``'now'`` — special-cased to
                  ``UNIX_TIMESTAMP()``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(UNIX_TIMESTAMP(<expr>))`` (or ``(UNIX_TIMESTAMP())`` for
            the ``'now'`` case) and whose ``current_datatype`` is
            ``int``.

        Example:
            Display the raw epoch value alongside a timestamp::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row([
                    users.created_at,
                    Builtins.UnixEpoch(users.created_at),
                ])
                # SELECT `users`.`created_at`,
                #        (UNIX_TIMESTAMP(`users`.`created_at`))
                # FROM `users`
                # -> [('2024-03-15 09:30:42', 1710495042), ...]

            Compute elapsed seconds since signup::

                elapsed = Builtins.UnixNow() - Builtins.UnixEpoch(users.created_at)
                rows = users.get_row([users.username, elapsed])
                # SELECT `users`.`username`,
                #        ((UNIX_TIMESTAMP()) - (UNIX_TIMESTAMP(`users`.`created_at`)))
                # FROM `users`

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
                # SELECT `users`.`username` FROM `users`
                # WHERE ((UNIX_TIMESTAMP(`users`.`created_at`)) > %s)
                # Parameters: [1704067200]

            Store a timestamp as an integer during an UPDATE::

                users.update(
                    update={users.last_seen_epoch: Builtins.UnixNow()},
                    where=users.id == 42,
                )

            Sort by absolute moment::

                rows = users.get_row(
                    [users.username],
                    order_by=Builtins.UnixEpoch(users.created_at),
                )

            The ``'now'`` special case mirrors :meth:`UnixNow`::

                rows = users.get_row([
                    Builtins.UnixEpoch('now'),   # -> (UNIX_TIMESTAMP()) current epoch
                ])
                # -> [(1710513042,)]

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.UnixEpoch('2024-03-15 00:00:00'),
                    # -> (UNIX_TIMESTAMP(%s)) with param '2024-03-15 00:00:00'
                    # -> 1710460800 (if session tz is UTC)
                ])
        """
        if Builtins._is_now(value):
            return Builtins._make('(UNIX_TIMESTAMP())', [], int, Builtins._NullCol)
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(UNIX_TIMESTAMP({sql}))', p, int, c)

    # ============================================================ date extractors

    @staticmethod
    def Year(value):
        """Extract the four-digit year from a date/time value using ``YEAR()``.

        Generates a ``YEAR(<expr>)`` expression. The result is always an
        ``INTEGER`` in the range 1000 through 9999 (MySQL's ``DATE``
        type limit), or 0 for the ``'0000-00-00'`` sentinel when
        ``NO_ZERO_DATE`` is disabled.

        This is the SQL equivalent of ``datetime.date.year`` on a parsed
        Python date.

        Args:
            value: The date/time expression whose year is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(YEAR(<expr>))`` and whose ``current_datatype`` is always
            ``int``.

        Example:
            Filter rows by year::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Year(users.created_at) == 2024,
                )
                # SELECT `users`.`id`, `users`.`created_at` FROM `users`
                # WHERE ((YEAR(`users`.`created_at`)) = %s)
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
                # SELECT `users`.`username`, (YEAR(`users`.`created_at`))
                # FROM `users`

            Range filter across years::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.Between(Builtins.Year(users.created_at), 2023, 2024),
                )
                # SELECT `users`.`id` FROM `users`
                # WHERE (((YEAR(`users`.`created_at`))) BETWEEN %s AND %s)
                # Parameters: [2023, 2024]

            Compare years with arithmetic — stays numeric because
            ``current_datatype`` is ``int``::

                next_year = Builtins.Year(users.created_at) + 1
                rows = users.get_row([users.id, next_year])
                # SELECT `users`.`id`, ((YEAR(`users`.`created_at`)) + %s)
                # FROM `users`
                # Parameters: [1]

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Year('2024-03-15'),   # -> 2024
                    Builtins.Year('now'),          # -> current year
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(YEAR({sql}))', p, int, c)

    @staticmethod
    def Month(value):
        """Extract the month number (1-12) from a date/time value using ``MONTH()``.

        Generates a ``MONTH(<expr>)`` expression. The result is always an
        ``INTEGER`` in the range 1 through 12, so it compares correctly
        with numeric literals (``== 3`` rather than ``== '03'``).

        This is the SQL equivalent of ``datetime.date.month`` on a
        parsed Python date.

        Args:
            value: The date/time expression whose month is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(MONTH(<expr>))`` and whose ``current_datatype`` is always
            ``int``.

        Example:
            Filter by month — pick a specific month regardless of year::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Month(users.created_at) == 3,
                )
                # SELECT `users`.`id`, `users`.`created_at` FROM `users`
                # WHERE ((MONTH(`users`.`created_at`)) = %s)
                # Parameters: [3]
                # -> everything created in March, any year

            Seasonal filter — Q1 only::

                q1 = Builtins.Between(Builtins.Month(users.created_at), 1, 3)
                rows = users.get_row(
                    [users.username],
                    where=q1,
                )
                # SELECT `users`.`username` FROM `users`
                # WHERE (((MONTH(`users`.`created_at`))) BETWEEN %s AND %s)
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

            Select with formatted month name — combine with IIf for the
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

            Filter on a computed month — e.g. users whose signup month
            matches their birth month::

                rows = users.get_row(
                    [users.username],
                    where=Builtins.Month(users.created_at)
                        == Builtins.Month(users.birth_date),
                )
                # SELECT `users`.`username` FROM `users`
                # WHERE ((MONTH(`users`.`created_at`)) = (MONTH(`users`.`birth_date`)))

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Month('2024-03-15'),   # -> 3
                    Builtins.Month('now'),          # -> current month 1..12
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(MONTH({sql}))', p, int, c)

    @staticmethod
    def Day(value):
        """Extract the day of the month (1-31) from a date/time value using ``DAY()``.

        Generates a ``DAY(<expr>)`` expression. The result is always an
        ``INTEGER`` in the range 1 through 31, so it compares correctly
        with numeric literals.

        MySQL also accepts ``DAYOFMONTH()`` as a synonym; this helper
        uses ``DAY()`` for brevity. See :meth:`DayOfYear` for the ordinal
        day within the year.

        Args:
            value: The date/time expression whose day of month is
                extracted. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(DAY(<expr>))`` and whose ``current_datatype`` is always
            ``int``.

        Example:
            Find rows created on the first of the month::

                from Ormophine.Mysql import Driver, Builtins

                db       = Driver(host='localhost', port=3306, username='root',
                                  password='secret', db_name='app')
                invoices = db.invoices

                rows = invoices.get_row(
                    [invoices.id, invoices.issued_at, invoices.total],
                    where=Builtins.Day(invoices.issued_at) == 1,
                )
                # SELECT `invoices`.`id`, `invoices`.`issued_at`,
                #        `invoices`.`total`
                # FROM `invoices`
                # WHERE ((DAY(`invoices`.`issued_at`)) = %s)
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
        return Builtins._make(f'(DAY({sql}))', p, int, c)

    @staticmethod
    def Hour(value):
        """Extract the hour (0-23) from a date/time value using ``HOUR()``.

        Generates a ``HOUR(<expr>)`` expression. The result is always an
        ``INTEGER`` in the range 0 through 23, so it compares correctly
        with numeric literals and works well with range filters.

        MySQL's ``HOUR`` uses a 24-hour clock. Midnight is 0, noon is 12,
        11 PM is 23.

        Args:
            value: The date/time expression whose hour is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and
                  parameters are reused.
                - :class:`Column` — the fully qualified column name is
                  used.
                - A raw Python string or number — bound as a ``%s``
                  placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(HOUR(<expr>))`` and whose ``current_datatype`` is always
            ``int``.

        Example:
            Business-hours filter — signups between 9 AM and 5 PM::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                hours = Builtins.Hour(users.created_at)
                rows = users.get_row(
                    [users.id, users.created_at],
                    where=(hours >= 9) & (hours < 17),
                )
                # SELECT `users`.`id`, `users`.`created_at` FROM `users`
                # WHERE (((HOUR(`users`.`created_at`)) >= %s)
                #        AND ((HOUR(`users`.`created_at`)) < %s))
                # Parameters: [9, 17]

            Time-of-day bucketing — morning / afternoon / evening /
            night::

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
        return Builtins._make(f'(HOUR({sql}))', p, int, c)

    @staticmethod
    def Minute(value):
        """Extract the minute (0-59) from a date/time value using MySQL's ``MINUTE()``.

        Generates a ``MINUTE(<expr>)`` expression. The result is always an
        ``INTEGER`` in the range 0 through 59, so it compares correctly with
        numeric literals and works well with range filters.

        This is the SQL equivalent of ``datetime.datetime.minute`` on a parsed
        Python datetime.

        Args:
            value: The date/time expression whose minute is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(MINUTE(<expr>))`` and whose ``current_datatype`` is always
            ``int``.

        Example:
            Filter rows created in the first fifteen minutes of any hour::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Minute(users.created_at) < 15,
                )
                # SELECT `users`.`id`, `users`.`created_at` FROM `users`
                # WHERE ((MINUTE(`users`.`created_at`)) < %s)
                # Parameters: [15]

            Minute histogram — a 60-bucket distribution::

                rows = users.get_row([Builtins.Minute(users.created_at)])
                from collections import Counter
                by_minute = Counter(m for (m,) in rows)
                # {0: 5, 1: 3, ..., 59: 2}

            Compare minutes across two columns — same minute-of-hour::

                same_minute = (Builtins.Minute(users.created_at)
                               == Builtins.Minute(users.last_login))
                rows = users.get_row([users.id], where=same_minute)

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Minute('2024-03-15 09:30:42'),   # -> 30
                    Builtins.Minute('now'),                    # -> current 0..59
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(MINUTE({sql}))', p, int, c)

    @staticmethod
    def Second(value):
        """Extract the second (0-59) from a date/time value using MySQL's ``SECOND()``.

        Generates a ``SECOND(<expr>)`` expression. The result is always an
        ``INTEGER`` in the range 0 through 59, so it compares correctly with
        numeric literals. Fractional seconds (if the column was declared with
        ``DATETIME(n)``) are truncated — use ``MICROSECOND()`` via
        ``Builtins.Func`` if you need sub-second precision.

        This is the SQL equivalent of ``datetime.datetime.second`` on a parsed
        Python datetime.

        Args:
            value: The date/time expression whose second is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(SECOND(<expr>))`` and whose ``current_datatype`` is always
            ``int``.

        Example:
            Filter rows created in the first 10 seconds of any minute::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Second(users.created_at) <= 10,
                )
                # SELECT `users`.`id`, `users`.`created_at` FROM `users`
                # WHERE ((SECOND(`users`.`created_at`)) <= %s)
                # Parameters: [10]

            Detect round-minute timestamps — a common data-quality check::

                on_the_minute = (Builtins.Second(users.created_at) == 0)
                rows = users.get_row([users.id], where=on_the_minute)

            Second histogram — 60-bucket distribution::

                rows = users.get_row([Builtins.Second(users.created_at)])
                from collections import Counter
                by_second = Counter(s for (s,) in rows)

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Second('2024-03-15 09:30:42'),   # -> 42
                    Builtins.Second('now'),                    # -> current 0..59
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(SECOND({sql}))', p, int, c)

    @staticmethod
    def DayOfWeek(value):
        """Return the day of the week using MySQL's ``DAYOFWEEK()`` — 1=Sunday … 7=Saturday.

        Generates a ``DAYOFWEEK(<expr>)`` expression. The result is always an
        ``INTEGER`` in the range 1 through 7, using MySQL's convention where
        Sunday is 1 and Saturday is 7 (this follows the ODBC standard).

        .. warning::
            The numbering differs from both Python and ISO-8601:

            ===========  ============  ===========  ========
            Day          MySQL (1-7)   Python (0-6) ISO (1-7)
            ===========  ============  ===========  ========
            Sunday       1             6            7
            Monday       2             0            1
            Tuesday      3             1            2
            Wednesday    4             2            3
            Thursday     5             3            4
            Friday       6             4            5
            Saturday     7             5            6
            ===========  ============  ===========  ========

            If you need Python's numbering (0=Monday … 6=Sunday), use
            :meth:`Weekday`. If you need ISO-8601 numbering (1=Monday …
            7=Sunday), use :meth:`IsoWeekday`.

        Args:
            value: The date/time expression whose day-of-week is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(DAYOFWEEK(<expr>))`` and whose ``current_datatype`` is always
            ``int``.

        Example:
            Filter only weekend rows (Saturday=7 or Sunday=1)::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                weekend = (Builtins.DayOfWeek(users.created_at) == 1) | \
                          (Builtins.DayOfWeek(users.created_at) == 7)
                rows = users.get_row([users.id, users.created_at], where=weekend)
                # SELECT ... WHERE (((DAYOFWEEK(`users`.`created_at`)) = %s)
                #                 OR ((DAYOFWEEK(`users`.`created_at`)) = %s))
                # Parameters: [1, 7]

            Group by weekday via IIf — turn numbers into names::

                name = Builtins.IIf(
                    Builtins.DayOfWeek(users.created_at) == 1, 'Sun',
                    Builtins.IIf(
                        Builtins.DayOfWeek(users.created_at) == 2, 'Mon',
                        Builtins.IIf(
                            Builtins.DayOfWeek(users.created_at) == 6, 'Fri',
                            'Other',
                        ),
                    ),
                )
                rows = users.get_row([users.id, name])

            Histogram over the 7 days::

                rows = users.get_row([Builtins.DayOfWeek(users.created_at)])
                from collections import Counter
                by_dow = Counter(d for (d,) in rows)
                # {1: 120, 2: 340, ..., 7: 88}

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.DayOfWeek('2024-03-15'),   # Friday -> 6
                    Builtins.DayOfWeek('now'),          # current 1..7
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(DAYOFWEEK({sql}))', p, int, c)

    @staticmethod
    def DayOfYear(value):
        """Return the ordinal day of the year (1-366) using MySQL's ``DAYOFYEAR()``.

        Generates a ``DAYOFYEAR(<expr>)`` expression. The result is always an
        ``INTEGER`` in the range 1 through 366 (366 only for leap years). This
        is useful for building year-over-year comparisons and seasonal bucketing.

        This is the SQL equivalent of Python's
        ``datetime.date.timetuple().tm_yday``.

        Args:
            value: The date/time expression whose ordinal day is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(DAYOFYEAR(<expr>))`` and whose ``current_datatype`` is always
            ``int``.

        Example:
            Filter the first week of the year::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.DayOfYear(users.created_at) <= 7,
                )
                # SELECT `users`.`id`, `users`.`created_at` FROM `users`
                # WHERE ((DAYOFYEAR(`users`.`created_at`)) <= %s)
                # Parameters: [7]

            Day-of-year histogram for seasonal analysis::

                rows = users.get_row([Builtins.DayOfYear(users.created_at)])
                from collections import Counter
                by_doy = Counter(d for (d,) in rows)

            Leap-year check — a year has a Feb 29 row if some row maps to
            day 60::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.DayOfYear(users.created_at) == 60,
                )

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.DayOfYear('2024-03-15'),   # -> 75
                    Builtins.DayOfYear('now'),          # -> current 1..366
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(DAYOFYEAR({sql}))', p, int, c)

    @staticmethod
    def WeekOfYear(value):
        """Return the ISO-8601 week number (1-53) using MySQL's ``WEEKOFYEAR()``.

        Generates a ``WEEKOFYEAR(<expr>)`` expression. The result is always an
        ``INTEGER`` in the range 1 through 53. Week 1 is the first week that
        contains a Thursday (ISO-8601 rule), and weeks start on Monday.

        This is the SQL equivalent of Python's
        ``datetime.date.isocalendar()[1]``.

        .. note::
            ``WEEKOFYEAR()`` is equivalent to ``WEEK(<expr>, 3)`` — mode 3 is
            the ISO-8601 mode. Do not confuse it with ``WEEK(<expr>)`` whose
            default mode depends on the ``default_week_format`` server
            variable.

        Args:
            value: The date/time expression whose ISO week number is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(WEEKOFYEAR(<expr>))`` and whose ``current_datatype`` is always
            ``int``.

        Example:
            Weekly signup reports::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                rows = users.get_row(
                    [Builtins.WeekOfYear(users.created_at)],
                )
                from collections import Counter
                by_week = Counter(w for (w,) in rows)
                # {1: 45, 2: 38, ..., 52: 12}

            Filter Q1 weeks only::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.WeekOfYear(users.created_at) <= 13,
                )
                # SELECT `users`.`id` FROM `users`
                # WHERE ((WEEKOFYEAR(`users`.`created_at`)) <= %s)
                # Parameters: [13]

            Compare the same ISO week across years — for the same calendar
            alignment::

                rows = users.get_row(
                    [Builtins.WeekOfYear(users.created_at)],
                    where=Builtins.WeekOfYear(users.created_at) == 15,
                )

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.WeekOfYear('2024-03-15'),   # -> 11
                    Builtins.WeekOfYear('now'),          # current 1..53
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(WEEKOFYEAR({sql}))', p, int, c)

    @staticmethod
    def Weekday(value):
        """Return Python's weekday number (0=Monday … 6=Sunday) via MySQL's ``WEEKDAY()``.

        Generates a ``WEEKDAY(<expr>)`` expression. The result is always an
        ``INTEGER`` in the range 0 through 6, matching Python's
        ``datetime.date.weekday()`` convention: Monday is 0, Sunday is 6.

        This is the safest day-of-week helper to pair with Python-side logic
        since the numbering is identical to Python's.

        ===========  =============  ========
        Day          ``Weekday``     Python
        ===========  =============  ========
        Monday       0              0
        Tuesday      1              1
        Wednesday    2              2
        Thursday     3              3
        Friday       4              4
        Saturday     5              5
        Sunday       6              6
        ===========  =============  ========

        Args:
            value: The date/time expression whose weekday is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(WEEKDAY(<expr>))`` and whose ``current_datatype`` is always
            ``int``.

        Example:
            Filter only weekends (Sat=5 or Sun=6)::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                weekend = (Builtins.Weekday(users.created_at) == 5) | \
                          (Builtins.Weekday(users.created_at) == 6)
                rows = users.get_row([users.id], where=weekend)

            Business-day filter — Monday through Friday::

                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Weekday(users.created_at) <= 4,
                )
                # SELECT ... WHERE ((WEEKDAY(`users`.`created_at`)) <= %s)
                # Parameters: [4]

            Histogram — 7 buckets in the same order as Python::

                rows = users.get_row([Builtins.Weekday(users.created_at)])
                from collections import Counter
                by_dow = Counter(d for (d,) in rows)
                # {0: Mon, 1: Tue, ..., 6: Sun}

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Weekday('2024-03-15'),   # Friday -> 4
                    Builtins.Weekday('now'),          # 0..6
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(WEEKDAY({sql}))', p, int, c)

    @staticmethod
    def IsoWeekday(value):
        """Return the ISO-8601 weekday number (1=Monday … 7=Sunday).

        MySQL has no dedicated ``ISODAYOFWEEK()`` function, so this helper
        composes one from ``WEEKDAY()``:

        .. code-block:: sql

            (WEEKDAY(<expr>) + 1)

        ``WEEKDAY()`` returns 0 for Monday through 6 for Sunday; adding 1
        shifts the range to 1 through 7, matching the ISO-8601 standard.

        Use this helper when you need to interoperate with ISO-8601 based
        libraries or when the numbering 1-7 reads more naturally than 0-6.

        Args:
            value: The date/time expression whose ISO weekday is extracted.
                Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``((WEEKDAY(<expr>) + 1))`` and whose ``current_datatype`` is
            always ``int``.

        Example:
            ISO weekday names via nested IIf::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                name = Builtins.IIf(
                    Builtins.IsoWeekday(users.created_at) == 1, 'Mon',
                    Builtins.IIf(
                        Builtins.IsoWeekday(users.created_at) == 7, 'Sun',
                        'Midweek',
                    ),
                )
                rows = users.get_row([users.id, name])

            Filter ISO weekends (Sat=6, Sun=7)::

                weekend = (Builtins.IsoWeekday(users.created_at) == 6) | \
                          (Builtins.IsoWeekday(users.created_at) == 7)
                rows = users.get_row([users.id], where=weekend)
                # SELECT `users`.`id` FROM `users`
                # WHERE ((((WEEKDAY(`users`.`created_at`) + %s)) = %s)
                #     OR (((WEEKDAY(`users`.`created_at`) + %s)) = %s))
                # Parameters: [1, 6, 1, 7]

            Filter the first three days of the ISO week::

                rows = users.get_row(
                    [users.id],
                    where=Builtins.IsoWeekday(users.created_at) <= 3,
                )

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.IsoWeekday('2024-03-15'),   # Friday -> 5
                    Builtins.IsoWeekday('now'),          # 1..7
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'((WEEKDAY({sql}) + 1))', p, int, c)

    @staticmethod
    def Strftime(fmt, value):
        """Format a date/time value using MySQL's ``DATE_FORMAT()``.

        Generates a ``DATE_FORMAT(<expr>, <fmt>)`` expression. The format
        string follows MySQL's percent-style specifiers, which differ from
        Python's ``strftime`` in a few places — most notably ``%i`` for
        minutes (Python uses ``%M``) and ``%s``/``%S`` for seconds.

        Common MySQL specifiers:

        =========  =========================
        Specifier  Meaning
        =========  =========================
        ``%Y``     Four-digit year
        ``%y``     Two-digit year
        ``%m``     Month, zero-padded (01-12)
        ``%c``     Month (1-12)
        ``%M``     Month name (January..December)
        ``%b``     Abbreviated month name
        ``%d``     Day of month, zero-padded
        ``%e``     Day of month
        ``%H``     Hour (00-23)
        ``%h``     Hour (01-12)
        ``%i``     Minutes (00-59)
        ``%s``     Seconds (00-59)
        ``%S``     Seconds (00-59) — synonym for ``%s``
        ``%W``     Weekday name (Sunday..Saturday)
        ``%a``     Abbreviated weekday
        ``%j``     Day of year (001-366)
        ``%T``     Time, 24-hour (hh:mm:ss)
        ``%r``     Time, 12-hour (hh:mm:ss AM/PM)
        =========  =========================

        This is the SQL counterpart of Python's ``strftime``, but with
        MySQL's specifiers. Note that the ``fmt`` argument is bound as a
        parameter (``%s``) — MySQL accepts it as a runtime string, so no
        injection risk is introduced.

        Args:
            fmt (str): The MySQL format string, e.g. ``'%Y-%m-%d'`` or
                ``'%H:%i:%s'``. It is bound as a parameter, so any string
                content is safe.
            value: The date/time expression to format. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(DATE_FORMAT(<expr>, %s))`` with the format string appended to
            the parameter list, and whose ``current_datatype`` is always
            ``str``.

        Example:
            ISO-style date column::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                iso_date = Builtins.Strftime('%Y-%m-%d', users.created_at)
                rows = users.get_row([users.id, iso_date])
                # SELECT `users`.`id`, (DATE_FORMAT(`users`.`created_at`, %s))
                # FROM `users`
                # Parameters: ['%Y-%m-%d']
                # -> [(1, '2024-03-15'), ...]

            Human-readable month-year grouping::

                month = Builtins.Strftime('%M %Y', users.created_at)
                rows = users.get_row([month, Builtins.Count('*')])
                # SELECT (DATE_FORMAT(`users`.`created_at`, %s)), (COUNT(*))
                # FROM `users`
                # Parameters: ['%M %Y']
                # -> [('March 2024', 42), ('April 2024', 55), ...]

            Filename-safe timestamp::

                stamp = Builtins.Strftime('%Y%m%d_%H%i%s', users.created_at)
                rows = users.get_row([stamp])

            Sort by formatted string — useful for month names in calendar
            order (since ``%m`` is zero-padded, lexicographic order matches
            chronological order for the year-month combination)::

                rows = users.get_row(
                    [users.id],
                    order_by=Builtins.Strftime('%Y-%m', users.created_at),
                )

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.Strftime('%Y-%m-%d', '2024-03-15 09:30:42'),
                    # -> '2024-03-15'
                ])
        """
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(DATE_FORMAT({sql}, %s))', p + [fmt], str, c)

    _INTERVAL_RE = re.compile(
        r'^\s*([+-]?\d+)\s*'
        r'(day|days|week|weeks|month|months|year|years|hour|hours|minute|minutes|second|seconds)\s*$',
        re.IGNORECASE,
    )

    @staticmethod
    def _apply_modifiers(base_sql, base_params, modifiers):
        """Fold SQLite-style date modifiers into chained MySQL ``DATE_ADD``/``DATE_SUB`` calls.

        This internal helper takes a base SQL fragment and a sequence of
        modifier strings — the same style accepted by SQLite's ``date()``
        and ``datetime()`` functions — and produces the equivalent MySQL
        date arithmetic expression, along with the accumulated parameter
        list.

        Two kinds of modifiers are supported:

        * **Interval modifiers** — strings like ``'+1 day'``, ``'-3 hours'``,
          ``'+2 months'``, ``'-1 year'``. The integer sign determines whether
          ``DATE_ADD`` or ``DATE_SUB`` is emitted, and the unit is upper-cased
          and singularised (``'days'`` → ``'DAY'``). Each modifier wraps the
          previous SQL fragment, so modifiers apply left-to-right, matching
          SQLite's semantics.
        * **Anchor modifiers** — the special strings ``'start of month'``,
          ``'start of year'``, and ``'start of day'``. These rewrite the
          fragment using ``DATE_FORMAT`` (for month/year) or ``DATE()``
          (for day), truncating the value to the beginning of the period.

        Args:
            base_sql (str): The starting SQL fragment, e.g.
                ``'`users`.`created_at`'`` or ``'NOW()'``.
            base_params (list): The parameters already associated with
                ``base_sql``. Returned values are appended to a copy of this
                list; the input list is never modified.
            modifiers (tuple[str, ...]): One or more modifier strings, in
                the order they should be applied.

        Returns:
            tuple[str, list]: A two-element tuple ``(sql, params)`` where
            ``sql`` is the transformed fragment and ``params`` is the
            accumulated parameter list (a copy of ``base_params`` plus
            any new parameters added along the way — currently, the
            modifiers themselves carry no parameters).

        Raises:
            ValueError: If a modifier does not match the recognised
                interval pattern and is not one of the three anchor
                modifiers. The error message lists the accepted forms.

        Example:
            Internal usage::

                >>> Builtins._apply_modifiers('NOW()', [], ['+1 day'])
                ('DATE_ADD(NOW(), INTERVAL 1 DAY)', [])

                >>> Builtins._apply_modifiers('NOW()', [], ['+1 month', '-2 days'])
                ('DATE_SUB(DATE_ADD(NOW(), INTERVAL 1 MONTH), INTERVAL 2 DAY)', [])

                >>> Builtins._apply_modifiers('NOW()', [], ['start of month'])
                ("DATE_FORMAT(NOW(), '%Y-%m-01')", [])
        """
        params = list(base_params)
        sql    = base_sql
        for mod in modifiers:
            low = mod.strip().lower()
            if low == 'start of month':
                sql = f"DATE_FORMAT({sql}, '%Y-%m-01')"
                continue
            if low == 'start of year':
                sql = f"DATE_FORMAT({sql}, '%Y-01-01')"
                continue
            if low == 'start of day':
                sql = f'DATE({sql})'
                continue
            m = Builtins._INTERVAL_RE.match(mod)
            if not m:
                raise ValueError(
                    f"Unrecognized modifier {mod!r}. Use something like "
                    f"'+1 day', '-2 hours', '+3 months', 'start of month'."
                )
            n    = int(m.group(1))
            unit = m.group(2).upper().rstrip('S')
            fn   = 'DATE_ADD' if n >= 0 else 'DATE_SUB'
            sql  = f'{fn}({sql}, INTERVAL {abs(n)} {unit})'
        return sql, params

    @staticmethod
    def DateAdd(value, *modifiers):
        """Add or subtract intervals from a date value — returns a DATE.

        Generates a MySQL date arithmetic expression that applies one or
        more SQLite-style modifiers to ``value`` and returns the resulting
        date (truncated to day precision) as a TEXT string in
        ``'YYYY-MM-DD'`` format.

        Two kinds of modifiers are supported:

        * **Interval modifiers** — ``'+1 day'``, ``'-3 hours'``, ``'+2 months'``,
          ``'-1 year'``, etc. Positive values use ``DATE_ADD``; negative
          values use ``DATE_SUB``. Modifiers apply left-to-right.
        * **Anchor modifiers** — ``'start of month'``, ``'start of year'``,
          ``'start of day'``. These truncate the value to the beginning of
          the period.

        The literal string ``'now'`` is special-cased to ``CURDATE()`` — the
        current date — so the SQLite calling convention still works.

        The final result is always wrapped in ``DATE(...)``, discarding any
        time-of-day component, matching SQLite's ``date()`` semantics.

        Args:
            value: The starting date/datetime. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.
                - The literal string ``'now'`` — special-cased to ``CURDATE()``.

            *modifiers: Zero or more modifier strings applied in order.
                If no modifiers are given, the value is only normalised to a
                date.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is the
            composed SQL fragment wrapped in ``DATE(...)`` and whose
            ``current_datatype`` is always ``str``.

        Raises:
            ValueError: If any modifier is unrecognised — propagated from
                :meth:`_apply_modifiers`.

        Example:
            Tomorrow's date::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                tomorrow = Builtins.DateAdd('now', '+1 day')
                rows = users.get_row([tomorrow])
                # SELECT (DATE(DATE_ADD(CURDATE(), INTERVAL 1 DAY))) FROM `users`
                # -> [('2024-03-16',)]

            One week after signup::

                after_week = Builtins.DateAdd(users.created_at, '+7 days')
                rows = users.get_row([users.id, after_week])
                # SELECT `users`.`id`,
                #        (DATE(DATE_ADD(`users`.`created_at`, INTERVAL 7 DAY)))
                # FROM `users`

            First day of the current month::

                month_start = Builtins.DateAdd('now', 'start of month')
                rows = users.get_row([month_start])
                # SELECT (DATE(DATE_FORMAT(CURDATE(), '%Y-%m-01'))) FROM `users`
                # -> [('2024-03-01',)]

            Chained modifiers — one month ago, then start of month::

                prev_month_start = Builtins.DateAdd('now', '-1 month', 'start of month')
                rows = users.get_row([prev_month_start])
                # -> [('2024-02-01',)]

            Filter users created in the last 30 days::

                cutoff = Builtins.DateAdd('now', '-30 days')
                rows = users.get_row(
                    [users.id, users.created_at],
                    where=Builtins.Date(users.created_at) >= cutoff,
                )
                # SELECT ... WHERE ((DATE(`users`.`created_at`)) >=
                #   (DATE(DATE_SUB(CURDATE(), INTERVAL 30 DAY))))

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.DateAdd('2024-03-15', '+1 month'),   # -> '2024-04-15'
                ])
        """
        if Builtins._is_now(value):
            sql, p, c = 'CURDATE()', [], Builtins._NullCol
        else:
            sql, p, _, c = Builtins._normalize(value)
        if not modifiers:
            return Builtins._make(f'(DATE({sql}))', p, str, c)
        inner, params = Builtins._apply_modifiers(sql, p, modifiers)
        return Builtins._make(f'(DATE({inner}))', params, str, c)

    @staticmethod
    def DateTimeAdd(value, *modifiers):
        """Add or subtract intervals from a datetime value — returns a DATETIME.

        The datetime counterpart of :meth:`DateAdd`. Applies the same set
        of SQLite-style modifiers to ``value`` but preserves the time-of-day
        component and normalises the result to a DATETIME value as a TEXT
        string in ``'YYYY-MM-DD HH:MM:SS'`` format.

        The literal string ``'now'`` is special-cased to ``NOW()`` — the
        current datetime — so the SQLite calling convention still works.

        When no modifiers are given, the value is only normalised to a
        DATETIME via ``CAST(<expr> AS DATETIME)``.

        Args:
            value: The starting datetime. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.
                - The literal string ``'now'`` — special-cased to ``NOW()``.

            *modifiers: Zero or more modifier strings applied in order.
                Recognised forms are the same as for :meth:`DateAdd`.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is the
            composed SQL fragment (either a bare ``DATE_ADD``/``DATE_SUB``
            chain or a ``CAST(... AS DATETIME)`` when no modifiers are
            given) and whose ``current_datatype`` is always ``str``.

        Raises:
            ValueError: If any modifier is unrecognised — propagated from
                :meth:`_apply_modifiers`.

        Example:
            One hour from now::

                from Ormophine.Mysql import Driver, Builtins

                db     = Driver(host='localhost', port=3306, username='root',
                                password='secret', db_name='app')
                events = db.events

                soon = Builtins.DateTimeAdd('now', '+1 hour')
                rows = events.get_row([soon])
                # SELECT (DATE_ADD(NOW(), INTERVAL 1 HOUR)) FROM `events`
                # -> [('2024-03-15 15:30:42',)]

            Filter events in the last 24 hours::

                cutoff = Builtins.DateTimeAdd('now', '-1 day')
                rows = events.get_row(
                    [events.id, events.occurred_at],
                    where=Builtins.DateTime(events.occurred_at) >= cutoff,
                )

            A token expiring in 30 minutes::

                expires = Builtins.DateTimeAdd('now', '+30 minutes')
                rows = events.get_row([expires])

            Normalise a date-only string to a full datetime::

                normalised = Builtins.DateTimeAdd('2024-03-15')
                rows = events.get_row([normalised])
                # SELECT (CAST(%s AS DATETIME)) FROM `events`
                # Parameters: ['2024-03-15']
                # -> [('2024-03-15 00:00:00',)]

            Chain multiple modifiers — one month ahead, then anchor to
            the first day of that month (with time preserved as 00:00:00)::

                first_of_next_month = Builtins.DateTimeAdd(
                    'now', '+1 month', 'start of month'
                )
                rows = events.get_row([first_of_next_month])
        """
        if Builtins._is_now(value):
            sql, p, c = 'NOW()', [], Builtins._NullCol
        else:
            sql, p, _, c = Builtins._normalize(value)
        if not modifiers:
            return Builtins._make(f'(CAST({sql} AS DATETIME))', p, str, c)
        inner, params = Builtins._apply_modifiers(sql, p, modifiers)
        return Builtins._make(f'({inner})', params, str, c)

    @staticmethod
    def TimeAdd(value, *modifiers):
        """Add or subtract intervals from a datetime value — returns a TIME.

        The time-of-day variant of :meth:`DateAdd` / :meth:`DateTimeAdd`.
        Applies the same modifier grammar but wraps the final result in
        ``TIME(...)``, extracting only the clock portion as a TEXT string
        in ``'HH:MM:SS'`` format.

        The literal string ``'now'`` is special-cased to ``NOW()`` — the
        current datetime — so the SQLite calling convention still works.
        Only the time component of the result is returned.

        When no modifiers are given, the value is only normalised to a
        TIME via ``TIME(<expr>)``.

        Args:
            value: The starting datetime. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.
                - The literal string ``'now'`` — special-cased to ``NOW()``.

            *modifiers: Zero or more modifier strings applied in order.
                Recognised forms are the same as for :meth:`DateAdd`.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is either
            ``(TIME(<expr>))`` when no modifiers are given, or
            ``(TIME(<date_arithmetic_chain>))`` otherwise, and whose
            ``current_datatype`` is always ``str``.

        Raises:
            ValueError: If any modifier is unrecognised — propagated from
                :meth:`_apply_modifiers`.

        Example:
            Time in 2 hours from now, as a clock time only::

                from Ormophine.Mysql import Driver, Builtins

                db     = Driver(host='localhost', port=3306, username='root',
                                password='secret', db_name='app')
                events = db.events

                in_two_hours = Builtins.TimeAdd('now', '+2 hours')
                rows = events.get_row([in_two_hours])
                # SELECT (TIME(DATE_ADD(NOW(), INTERVAL 2 HOUR))) FROM `events`
                # -> [('17:30:42',)]

            30 minutes after a scheduled time::

                later = Builtins.TimeAdd(events.scheduled_at, '+30 minutes')
                rows = events.get_row([events.id, later])
                # SELECT `events`.`id`,
                #        (TIME(DATE_ADD(`events`.`scheduled_at`, INTERVAL 30 MINUTE)))
                # FROM `events`

            Strip the date from a datetime column, leaving only the time::

                time_only = Builtins.TimeAdd(events.occurred_at)
                rows = events.get_row([events.id, time_only])
                # SELECT `events`.`id`, (TIME(`events`.`occurred_at`))
                # FROM `events`

            Applied to a raw literal::

                rows = events.get_row([
                    Builtins.TimeAdd('2024-03-15 14:30:00', '+1 hour'),
                    # -> '15:30:00'
                ])
        """
        if Builtins._is_now(value):
            sql, p, c = 'NOW()', [], Builtins._NullCol
        else:
            sql, p, _, c = Builtins._normalize(value)
        if not modifiers:
            return Builtins._make(f'(TIME({sql}))', p, str, c)
        inner, params = Builtins._apply_modifiers(sql, p, modifiers)
        return Builtins._make(f'(TIME({inner}))', params, str, c)

    @staticmethod
    def StrftimeMod(fmt, value, *modifiers):
        """Format a date/time value after applying modifiers — a modifier-aware ``Strftime``.

        Combines :meth:`_apply_modifiers` with :meth:`Strftime`: applies the
        given SQLite-style modifiers to ``value``, then formats the result
        with the MySQL ``DATE_FORMAT()`` function using ``fmt``.

        This is the right helper when you need both shifting and formatting
        in one expression, e.g. "the month name of the previous month" or
        "the ISO date one week ahead".

        The literal string ``'now'`` is special-cased to ``NOW()`` — the
        current datetime — so the SQLite calling convention still works.

        Args:
            fmt (str): The MySQL ``DATE_FORMAT`` format string, e.g.
                ``'%Y-%m-%d'`` or ``'%H:%i:%s'``. Bound as a parameter.
            value: The starting date/datetime. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.
                - The literal string ``'now'`` — special-cased to ``NOW()``.

            *modifiers: Zero or more modifier strings applied before
                formatting. Recognised forms are the same as for
                :meth:`DateAdd`. When omitted, the method degenerates to
                :meth:`Strftime`.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(DATE_FORMAT(<modified_expr>, %s))`` and whose
            ``current_datatype`` is always ``str``. The format string is
            appended to the parameter list after any parameters carried by
            ``value``.

        Raises:
            ValueError: If any modifier is unrecognised — propagated from
                :meth:`_apply_modifiers`.

        Example:
            The month name of the previous month::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                prev_month = Builtins.StrftimeMod('%M %Y', 'now', '-1 month')
                rows = users.get_row([prev_month])
                # SELECT (DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), %s))
                # FROM `users`
                # Parameters: ['%M %Y']
                # -> [('February 2024',)]

            ISO date one week after each signup::

                due = Builtins.StrftimeMod(
                    '%Y-%m-%d', users.created_at, '+7 days'
                )
                rows = users.get_row([users.id, due])

            Group by month after shifting into the previous month::

                bucket = Builtins.StrftimeMod('%Y-%m', users.created_at, '-1 month')
                rows = users.get_row([bucket, Builtins.Count('*')])

            Normalise a mixed-format column to ISO date via a no-op
            modifier chain — equivalent to :meth:`Strftime`::

                iso = Builtins.StrftimeMod('%Y-%m-%d', users.created_at)
                rows = users.get_row([iso])

            Applied to a raw literal::

                rows = users.get_row([
                    Builtins.StrftimeMod(
                        '%Y-%m-%d', '2024-03-15', '+1 month'
                    ),
                    # -> '2024-04-15'
                ])
        """
        if Builtins._is_now(value):
            sql, p, c = 'NOW()', [], Builtins._NullCol
        else:
            sql, p, _, c = Builtins._normalize(value)
        if modifiers:
            sql, p = Builtins._apply_modifiers(sql, p, modifiers)
        return Builtins._make(f'(DATE_FORMAT({sql}, %s))', p + [fmt], str, c)

    @staticmethod
    def DateDiffDays(a, b):
        """Signed whole-day count between two dates using MySQL's ``DATEDIFF()``.

        Generates a ``DATEDIFF(<a>, <b>)`` expression. MySQL evaluates this
        as ``<a> - <b>`` in days: a positive result means ``a`` is later
        than ``b``, a negative result means ``a`` is earlier. Only the date
        portion of each operand is considered; the time-of-day is ignored,
        so ``DATEDIFF('2024-03-16', '2024-03-15 23:59:59')`` returns ``1``.

        The result is always an ``INTEGER``.

        .. note::
            Because MySQL's ``DATEDIFF`` truncates to the day, it does not
            give a fractional count. If you need sub-day precision, use
            :meth:`DateDiffSeconds` and divide by 86400.

        Args:
            a: The later (minuend) date expression. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.

            b: The earlier (subtrahend) date expression. Same accepted
                types as ``a``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(DATEDIFF(<a>, <b>))`` and whose ``current_datatype`` is
            always ``int``. Parameters are concatenated left-to-right:
            first ``a``'s, then ``b``'s.

        Example:
            Account age in days::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                age_days = Builtins.DateDiffDays(Builtins.Now(), users.created_at)
                rows = users.get_row([users.username, age_days])
                # SELECT `users`.`username`,
                #        (DATEDIFF(NOW(), `users`.`created_at`))
                # FROM `users`
                # -> [('alice', 42), ('bob', 8), ...]

            Filter accounts older than 30 days::

                age_days = Builtins.DateDiffDays(Builtins.Now(), users.created_at)
                rows = users.get_row(
                    [users.id, users.username],
                    where=age_days > 30,
                )
                # SELECT ... WHERE ((DATEDIFF(NOW(), `users`.`created_at`)) > %s)
                # Parameters: [30]

            Signup cohort by weekly buckets::

                age_days = Builtins.DateDiffDays(Builtins.Now(), users.created_at)
                bucket   = Builtins.Floor(age_days / 7)
                rows = users.get_row([bucket, Builtins.Count('*')])

            Order by "newest first" via the reverse diff — the largest
            positive value corresponds to the most recent signup::

                rows = users.get_row(
                    [users.username],
                    order_by=Builtins.DateDiffDays(users.created_at, '1970-01-01') * -1,
                )

            Applied to raw literals::

                rows = users.get_row([
                    Builtins.DateDiffDays('2024-03-15', '2024-03-01'),   # -> 14
                    Builtins.DateDiffDays('2024-03-01', '2024-03-15'),   # -> -14
                ])
        """
        s1, p1, _, c = Builtins._normalize(a)
        s2, p2, _, _ = Builtins._normalize(b)
        return Builtins._make(f'(DATEDIFF({s1}, {s2}))', p1 + p2, int, c)

    @staticmethod
    def DateDiffSeconds(a, b):
        """Signed whole-second count between two moments using ``TIMESTAMPDIFF(SECOND, ...)``.

        Generates a ``TIMESTAMPDIFF(SECOND, <b>, <a>)`` expression. MySQL
        evaluates this as ``<a> - <b>`` in whole seconds: a positive result
        means ``a`` is later than ``b``, a negative result means ``a`` is
        earlier. Unlike :meth:`DateDiffDays`, the full datetime is used,
        including the time-of-day.

        The result is always an ``INTEGER`` — MySQL's ``TIMESTAMPDIFF``
        rounds toward zero for fractional seconds.

        The argument order is chosen so that ``DateDiffSeconds(later, earlier)``
        is positive, matching Python's ``(later - earlier).total_seconds()``
        idiom. Internally the call is emitted as ``TIMESTAMPDIFF(SECOND, b, a)``
        because MySQL's ``TIMESTAMPDIFF`` expects ``(unit, start, end)`` — the
        older timestamp first.

        Args:
            a: The later (end) moment. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.

            b: The earlier (start) moment. Same accepted types as ``a``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(TIMESTAMPDIFF(SECOND, <b>, <a>))`` and whose
            ``current_datatype`` is always ``int``. Parameters are
            concatenated left-to-right: first ``a``'s, then ``b``'s.

        Example:
            Session duration in seconds — a common analytics metric::

                from Ormophine.Mysql import Driver, Builtins

                db       = Driver(host='localhost', port=3306, username='root',
                                  password='secret', db_name='analytics')
                sessions = db.sessions

                duration = Builtins.DateDiffSeconds(
                    sessions.ended_at, sessions.started_at
                )
                rows = sessions.get_row([sessions.id, duration])
                # SELECT `sessions`.`id`,
                #        (TIMESTAMPDIFF(SECOND, `sessions`.`started_at`,
                #                                `sessions`.`ended_at`))
                # FROM `sessions`

            Filter long sessions (> 1 hour)::

                duration = Builtins.DateDiffSeconds(
                    sessions.ended_at, sessions.started_at
                )
                rows = sessions.get_row(
                    [sessions.id],
                    where=duration > 3600,
                )

            Elapsed seconds since signup::

                users = db.users
                elapsed = Builtins.DateDiffSeconds(Builtins.Now(), users.created_at)
                rows = users.get_row([users.username, elapsed])
                # SELECT `users`.`username`,
                #        (TIMESTAMPDIFF(SECOND, `users`.`created_at`, NOW()))
                # FROM `users`

            Convert to fractional days by chaining arithmetic::

                elapsed = Builtins.DateDiffSeconds(Builtins.Now(), users.created_at)
                days = elapsed / 86400
                rows = users.get_row([users.username, days])

            Applied to raw literals::

                rows = sessions.get_row([
                    Builtins.DateDiffSeconds(
                        '2024-03-15 10:00:00', '2024-03-15 09:30:00'
                    ),   # -> 1800
                ])
        """
        s1, p1, _, c = Builtins._normalize(a)
        s2, p2, _, _ = Builtins._normalize(b)
        return Builtins._make(f'(TIMESTAMPDIFF(SECOND, {s2}, {s1}))', p1 + p2, int, c)

    @staticmethod
    def Timediff(a, b):
        """Elapsed time between two moments as an ``HH:MM:SS`` string using ``TIMEDIFF()``.

        Generates a ``TIMEDIFF(<a>, <b>)`` expression. MySQL returns a
        signed ``TIME`` value representing the elapsed time from ``b`` to
        ``a`` — i.e., ``<a> - <b>``. The result is a TEXT string in
        ``'HH:MM:SS'`` format (or ``'-HH:MM:SS'`` for negative results).

        Unlike :meth:`DateDiffSeconds`, which returns an integer count,
        ``TIMEDIFF`` keeps the value in the TIME domain, so it composes
        naturally with the ``TIME`` arithmetic and formatting helpers. It
        is useful for producing human-readable durations.

        .. note::
            MySQL's ``TIMEDIFF`` limits its result to the TIME range
            (``-838:59:59`` to ``838:59:59``). For durations that may
            exceed that range, use :meth:`DateDiffSeconds` and format the
            integer in Python.

        Args:
            a: The later (end) moment. Supported types:

                - :class:`ColumnsOperation` — its SQL fragment and parameters
                  are reused.
                - :class:`Column` — the fully qualified column name is used.
                - A raw Python string or number — bound as a ``%s`` placeholder.

            b: The earlier (start) moment. Same accepted types as ``a``.

        Returns:
            ColumnsOperation: An expression whose ``_output[0]`` is
            ``(TIMEDIFF(<a>, <b>))`` and whose ``current_datatype`` is
            always ``str``. Parameters are concatenated left-to-right:
            first ``a``'s, then ``b``'s.

        Example:
            Human-readable account age::

                from Ormophine.Mysql import Driver, Builtins

                db    = Driver(host='localhost', port=3306, username='root',
                               password='secret', db_name='app')
                users = db.users

                age_str = Builtins.Timediff(Builtins.Now(), users.created_at)
                rows = users.get_row([users.username, age_str])
                # SELECT `users`.`username`,
                #        (TIMEDIFF(NOW(), `users`.`created_at`))
                # FROM `users`
                # -> [('alice', '02 05:29:18'), ...]  # MySQL DAY+HH:MM:SS
                # Note: values exceeding 24h are formatted as `DD HH:MM:SS`

            Session duration in clock notation::

                duration = Builtins.Timediff(
                    sessions.ended_at, sessions.started_at
                )
                rows = sessions.get_row([sessions.id, duration])
                # -> [('01:23:45',), ...]

            Sort by duration — largest first via arithmetic negation::

                duration = Builtins.Timediff(
                    sessions.ended_at, sessions.started_at
                )
                rows = sessions.get_row(
                    [sessions.id],
                    order_by=duration * -1,
                )

            Combine with :meth:`Strftime` to get compact labels::

                duration = Builtins.Timediff(
                    sessions.ended_at, sessions.started_at
                )
                label = Builtins.Strftime('%H:%i', duration)
                rows = sessions.get_row([sessions.id, label])

            Applied to raw literals::

                rows = users.get_row([
                    Builtins.Timediff('2024-03-15 10:00:00',
                                      '2024-03-15 09:30:00'),   # -> '00:30:00'
                ])
        """
        s1, p1, _, c = Builtins._normalize(a)
        s2, p2, _, _ = Builtins._normalize(b)
        return Builtins._make(f'(TIMEDIFF({s1}, {s2}))', p1 + p2, str, c)
    