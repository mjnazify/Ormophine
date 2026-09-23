from __future__ import annotations
from .. import Column, ColumnsOperation


class Builtins:
    """
    SQL function helpers that always return a ColumnsOperation.

    current_datatype rule (matches how ColumnsOperation.__add__ picks
    between '||' and '+'):
        - SQL function returns TEXT   -> current_datatype = str
        - SQL function returns NUMBER -> current_datatype = int / float
        - SQL function result depends on input (MIN, MAX, SUM, ABS, Func)
          -> propagate the input's datatype, with a numeric fallback when
             the input is not numeric.
    """

    class _NullCol:
        datatype   = None
        table_obj  = None
        name       = ''
        first_name = ''

    @staticmethod
    def _normalize(value):
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
        op = ColumnsOperation.__new__(ColumnsOperation)
        op._output          = (sql, params)
        op.col_obj          = col_obj if col_obj is not None else Builtins._NullCol
        op.current_datatype = datatype
        return op

    # ------------------------------------------------------------------
    # Numeric-returning functions
    # ------------------------------------------------------------------

    @staticmethod
    def Len(value):
        """LENGTH(x) -> always INTEGER."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(LENGTH({sql}))', p, int, c)

    @staticmethod
    def Sum(value):
        """SUM(x) -> INTEGER for int input, REAL otherwise."""
        sql, p, dt, c = Builtins._normalize(value)
        result_dt = dt if dt in (int, float) else int
        return Builtins._make(f'(SUM({sql}))', p, result_dt, c)

    @staticmethod
    def Avg(value):
        """AVG(x) -> always REAL (SQLite returns a float)."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(AVG({sql}))', p, float, c)

    @staticmethod
    def Min(value):
        """MIN(x) -> same type as input."""
        sql, p, dt, c = Builtins._normalize(value)
        return Builtins._make(f'(MIN({sql}))', p, dt, c)

    @staticmethod
    def Max(value):
        """MAX(x) -> same type as input."""
        sql, p, dt, c = Builtins._normalize(value)
        return Builtins._make(f'(MAX({sql}))', p, dt, c)

    @staticmethod
    def Count(value):
        """COUNT(*) / COUNT(x) -> always INTEGER."""
        if isinstance(value, str) and value == '*':
            return Builtins._make('(COUNT(*))', [], int, Builtins._NullCol)
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(COUNT({sql}))', p, int, c)

    @staticmethod
    def Abs(value):
        """ABS(x) -> INTEGER for int input, REAL otherwise."""
        sql, p, dt, c = Builtins._normalize(value)
        result_dt = dt if dt in (int, float) else float
        return Builtins._make(f'(ABS({sql}))', p, result_dt, c)

    @staticmethod
    def Round(value):
        """ROUND(x) -> always REAL in SQLite."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(ROUND({sql}))', p, float, c)

    @staticmethod
    def Int(value):
        """CAST(x AS INTEGER) -> INTEGER."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS INTEGER))', p, int, c)

    @staticmethod
    def Float(value):
        """CAST(x AS REAL) -> REAL."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS REAL))', p, float, c)

    @staticmethod
    def Str(value):
        """CAST(x AS TEXT) -> TEXT."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS TEXT))', p, str, c)

    @staticmethod
    def Bool(value):
        """CAST(x AS INTEGER) but declared BOOLEAN -> INTEGER."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CAST({sql} AS INTEGER))', p, int, c)

    @staticmethod
    def TypeOf(value):
        """TYPEOF(x) -> 'null' / 'integer' / 'real' / 'text' / 'blob'."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(TYPEOF({sql}))', p, str, c)

    @staticmethod
    def Sign(value):
        """SIGN(x) -> INTEGER (-1, 0, 1). SQLite >= 3.35."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(SIGN({sql}))', p, int, c)

    @staticmethod
    def Floor(value):
        """CAST(x AS INTEGER) when x >= 0, else (CAST(x AS INTEGER) - (x != CAST(x AS INTEGER)))."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(FLOOR({sql}))', p, int, c)   # SQLite >= 3.35

    @staticmethod
    def Ceil(value):
        """CEIL(x) -> INTEGER. SQLite >= 3.35."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(CEIL({sql}))', p, int, c)

    @staticmethod
    def Sqrt(value):
        """SQRT(x) -> REAL. SQLite >= 3.35."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(SQRT({sql}))', p, float, c)

    @staticmethod
    def Pow(base, exp):
        """POW(a, b) -> REAL. Takes two operands (like Python's pow())."""
        s1, p1, dt1, c1 = Builtins._normalize(base)
        s2, p2, _,  _  = Builtins._normalize(exp)
        return Builtins._make(f'(POW({s1}, {s2}))', p1 + p2, float, c1)

    @staticmethod
    def Find(value, sub):
        """INSTR(x, sub) -> 1-based position, or 0 if not found. (Python's str.find is 0-based -1)."""
        s1, p1, _, c = Builtins._normalize(value)
        s2, p2, _, _ = Builtins._normalize(sub)
        return Builtins._make(f'(INSTR({s1}, {s2}))', p1 + p2, int, c)

    @staticmethod
    def Reverse(value):
        """REVERSE(x) -> TEXT. SQLite >= 3.44."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(REVERSE({sql}))', p, str, c)

    @staticmethod
    def Format(fmt, *args):
        """Python-style %-formatting; maps to SQLite PRINTF/FORMAT. Variadic."""
        s0, p0, _, c = Builtins._normalize(fmt)
        parts, params = [s0], list(p0)
        for v in args:
            s, p, _, _ = Builtins._normalize(v)
            parts.append(s); params.extend(p)
        return Builtins._make(f'(PRINTF({", ".join(parts)}))', params, str, c)

    @staticmethod
    def Capitalize(value):
        """UPPER of first char + LOWER of the rest."""
        sql, p, _, c = Builtins._normalize(value)
        # SQLite has no direct equivalent; use a two-step expression.
        inner = f'UPPER(SUBSTR({sql}, 1, 1)) || LOWER(SUBSTR({sql}, 2))'
        return Builtins._make(f'({inner})', p, str, c)

    @staticmethod
    def Total(value):
        """TOTAL(x) -> REAL. Like SUM but returns 0.0 (not NULL) for empty groups."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(TOTAL({sql}))', p, float, c)

    @staticmethod
    def IsNull(value):
        """IS NULL predicate."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(({sql}) IS NULL)', p, int, c)

    @staticmethod
    def IsNotNull(value):
        """IS NOT NULL predicate."""
        sql, p, _, c = Builtins._normalize(value)
        return Builtins._make(f'(({sql}) IS NOT NULL)', p, int, c)

    @staticmethod
    def Between(value, low, high):
        """x BETWEEN low AND high."""
        s,  p,  _,  c  = Builtins._normalize(value)
        lo, lp, _,  _  = Builtins._normalize(low)
        hi, hp, _,  _  = Builtins._normalize(high)
        return Builtins._make(f'(({s}) BETWEEN {lo} AND {hi})', p + lp + hp, int, c)

    @staticmethod
    def IIf(condition, then_value, else_value):
        """IIF(cond, a, b) -> a if cond else b. SQLite >= 3.32."""
        cs, cp, _, c = Builtins._normalize(condition)
        ts, tp, _, _ = Builtins._normalize(then_value)
        es, ep, _, _ = Builtins._normalize(else_value)
        return Builtins._make(f'(IIF({cs}, {ts}, {es}))', cp + tp + ep, None, c)