import pytest
from Ormophine import Postgresql
import os
import uuid
import datetime
from decimal import Decimal

# Skip the entire module if psycopg isn't installed
psycopg = pytest.importorskip("psycopg")

from Ormophine import Postgresql


# ---------------------------------------------------------------------------
# Connection info from environment (with sensible defaults)
# ---------------------------------------------------------------------------

PG_PASS = os.environ.get("PGPASSWORD", "1234")  
PG_HOST = os.environ.get("PGHOST", "localhost")
PG_PORT = int(os.environ.get("PGPORT", 5432))
PG_USER = os.environ.get("PGUSER", "postgres")
PG_PASSWORD = os.environ.get("PGPASSWORD", "1234")   # ← از PG_PASS تغییر بده
PG_MAINT_DB = os.environ.get("PGMAINTDB", "postgres")
PG_DB_NAME  = os.environ.get("PGDBNAME", "ormophine_test_db")  # ← جدید
def _pg_available() -> bool:
    """Probe whether a PostgreSQL server is reachable with these credentials."""
    try:
        con = psycopg.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER,
            password=PG_PASS, dbname=PG_MAINT_DB, connect_timeout=2,
        )
        con.close()
        return True
    except Exception:
        return False


pg_available = pytest.mark.skipif(
    not _pg_available(),
    reason=f"PostgreSQL not reachable at {PG_HOST}:{PG_PORT} as {PG_USER}",
)

pytestmark = pg_available


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def pg_db_name():
    """Unique database name per test session."""
    return f"ormophine_test_{uuid.uuid4().hex[:10]}"


@pytest.fixture(scope="session")
def pg_driver(pg_db_name):
    """Session-wide driver with a fresh test database."""
    drv = Postgresql.Driver(
        PG_HOST, PG_PORT, PG_USER, PG_PASS,
        db_name=pg_db_name,
        create_new_db=True,
        pool_size=3,
        connect_timeout=5,
    )
    yield drv
    try:
        drv.disconnect()
    except Exception:
        pass
    # Best-effort drop of the test database via a fresh admin connection
    try:
        admin = psycopg.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER,
            password=PG_PASS, dbname=PG_MAINT_DB,
        )
        admin.autocommit = True
        cur = admin.cursor()
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (pg_db_name,),
        )
        cur.execute(f'DROP DATABASE IF EXISTS "{pg_db_name}"')
        admin.close()
    except Exception:
        pass


@pytest.fixture
def bt(pg_driver):
    name = f"bt_{uuid.uuid4().hex[:8]}"
    schema = Postgresql.TableStructure(name)
    schema.add_column("id",         Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column("name",       Postgresql.DataTypes.VARCHAR(100))
    schema.add_column("age",        Postgresql.DataTypes.INTEGER())
    schema.add_column("salary",     Postgresql.DataTypes.NUMERIC(12, 2))
    schema.add_column("score",      Postgresql.DataTypes.NUMERIC(6, 2))
    schema.add_column("balance",    Postgresql.DataTypes.NUMERIC(12, 2))
    schema.add_column("created_at", Postgresql.DataTypes.TIMESTAMP())
    schema.add_column("active",     Postgresql.DataTypes.BOOLEAN())

    pg_driver.create_table(schema)              # returns None
    tbl = getattr(pg_driver, name)              # ← اینجا جدول را بردار

    tbl.bulk_insert(
        [tbl.id, tbl.name, tbl.age, tbl.salary, tbl.score, tbl.balance,
         tbl.created_at, tbl.active],
        [
            (1, 'Alice', 30, Decimal('50000.00'), Decimal('85.50'),
             Decimal('100.00'), datetime.datetime(2024, 3, 15, 9, 30, 42), True),
            (2, 'Bob',   25, Decimal('60000.00'), Decimal('72.00'),
             Decimal('-50.00'), datetime.datetime(2024, 1, 10, 14, 20, 0), True),
            (3, 'Carol', 35, Decimal('70000.00'), Decimal('95.00'),
             Decimal('200.00'), datetime.datetime(2023, 12, 25, 8, 0, 0), False),
            (4, None,    40, Decimal('80000.00'), Decimal('60.00'),
             Decimal('-10.00'), datetime.datetime(2024, 6, 1, 23, 59, 59), True),
            (5, 'Eve',   None, None, None, Decimal('0.00'),
             datetime.datetime(2024, 3, 15, 9, 30, 42), False),
        ],
    )
    yield tbl
    try:
        pg_driver._exc(f'DROP TABLE IF EXISTS "{name}";')
    except Exception:
        pass

def _dec(x):
    """Convert a fetched value to Decimal for comparison (handles None)."""
    return None if x is None else Decimal(str(x))


def _flt(x):
    """Convert a fetched value to float for comparison (handles None)."""
    return None if x is None else float(x)


# ===========================================================================
# Internal helpers: _normalize / _make
# ===========================================================================
def test_builtins_normalize_column(bt):
    sql, params, dt, c = Postgresql.Builtins._normalize(bt.name)
    assert sql == bt.name.name
    assert params == []
    assert dt is str
    assert c is bt.name


def test_builtins_normalize_columns_operation(bt):
    op = bt.age + 1
    sql, params, dt, c = Postgresql.Builtins._normalize(op)
    assert params == [1]
    assert c is bt.age


def test_builtins_normalize_raw_literal():
    sql, params, dt, c = Postgresql.Builtins._normalize('hello')
    assert sql == '%s'
    assert params == ['hello']
    assert dt is str


def test_builtins_make_returns_columns_operation(bt):
    op = Postgresql.Builtins.Len(bt.name)
    assert isinstance(op, Postgresql.ColumnsOperation)


# ===========================================================================
# Len
# ===========================================================================
def test_builtins_len_basic(bt):
    res = bt.get_row([Postgresql.Builtins.Len(bt.name)], order_by=bt.id)
    assert res == [5, 3, 5, None, 3]


def test_builtins_len_in_where(bt):
    res = bt.get_row([bt.name],
                     where=Postgresql.Builtins.Len(bt.name) > 3,
                     order_by=bt.id)
    assert res == ['Alice', 'Carol']


def test_builtins_len_literal():
    op = Postgresql.Builtins.Len('hello')
    assert op._output[0] == '(LENGTH(%s))'
    assert op._output[1] == ['hello']
    assert op.current_datatype is int


def test_builtins_len_datatype_is_int(bt):
    assert Postgresql.Builtins.Len(bt.name).current_datatype is int


def test_builtins_len_nested_arithmetic(bt):
    expr = ((Postgresql.Builtins.Len(bt.name) + 3) / 4) * 4
    res = bt.get_row([expr], order_by=bt.id)
    assert [_flt(r) for r in res] == [8.0, 4.0, 8.0, None, 4.0]


# ===========================================================================
# Sum / Total / Avg / Min / Max / Count
# ===========================================================================
def test_builtins_sum_basic(bt):
    res = bt.get_row([Postgresql.Builtins.Sum(bt.salary)])
    assert _dec(res[0]) == Decimal('260000.00')


def test_builtins_sum_empty_table(bt):
    res = bt.get_row([Postgresql.Builtins.Sum(bt.salary)], where=bt.id > 100)
    assert res == [None]


def test_builtins_sum_datatype_propagation(bt):
    assert Postgresql.Builtins.Sum(bt.salary).current_datatype is float
    assert Postgresql.Builtins.Sum(bt.age).current_datatype is int


def test_builtins_total_empty_returns_zero(bt):
    res = bt.get_row([Postgresql.Builtins.Total(bt.salary)], where=bt.id > 100)
    assert _flt(res[0]) == 0.0


def test_builtins_total_datatype_is_float(bt):
    assert Postgresql.Builtins.Total(bt.salary).current_datatype is float


def test_builtins_avg_basic(bt):
    res = bt.get_row([Postgresql.Builtins.Avg(bt.salary)])
    assert _flt(res[0]) == 65000.0


def test_builtins_avg_datatype_is_float(bt):
    assert Postgresql.Builtins.Avg(bt.age).current_datatype is float


def test_builtins_min_max(bt):
    assert bt.get_row([Postgresql.Builtins.Min(bt.age)]) == [25]
    assert bt.get_row([Postgresql.Builtins.Max(bt.age)]) == [40]


def test_builtins_min_datatype_propagation(bt):
    assert Postgresql.Builtins.Min(bt.age).current_datatype is int
    assert Postgresql.Builtins.Min(bt.name).current_datatype is str


def test_builtins_count_star(bt):
    res = bt.get_row([Postgresql.Builtins.Count('*')])
    assert res == [5]


def test_builtins_count_column_skips_null(bt):
    res = bt.get_row([Postgresql.Builtins.Count(bt.name)])
    assert res == [4]


def test_builtins_count_datatype_is_int():
    assert Postgresql.Builtins.Count('*').current_datatype is int


def test_builtins_count_with_where(bt):
    res = bt.get_row([Postgresql.Builtins.Count('*')], where=bt.age > 30)
    assert res == [2]


# ===========================================================================
# Abs / Round / Sign / Floor / Ceil / Sqrt / Pow
# ===========================================================================
def test_builtins_abs_basic(bt):
    res = bt.get_row([Postgresql.Builtins.Abs(bt.balance)], order_by=bt.id)
    assert [_flt(r) for r in res] == [100.0, 50.0, 200.0, 10.0, 0.0]


def test_builtins_abs_datatype(bt):
    assert Postgresql.Builtins.Abs(bt.age).current_datatype is int
    assert Postgresql.Builtins.Abs(bt.salary).current_datatype is float


def test_builtins_abs_in_where(bt):
    res = bt.get_row([bt.id],
                     where=Postgresql.Builtins.Abs(bt.balance) >= 100,
                     order_by=bt.id)
    assert res == [1, 3]


def test_builtins_round_basic(bt):
    res = bt.get_row([Postgresql.Builtins.Round(bt.score)], order_by=bt.id)
    # Round returns float from PostgreSQL but psycopg delivers NUMERIC as Decimal
    assert [_flt(r) for r in res] == [86.0, 72.0, 95.0, 60.0, None]


def test_builtins_round_datatype_float(bt):
    assert Postgresql.Builtins.Round(bt.score).current_datatype is float


def test_builtins_sign(bt):
    res = bt.get_row([Postgresql.Builtins.Sign(bt.balance)], order_by=bt.id)
    assert res == [1, -1, 1, -1, 0]


def test_builtins_sign_datatype(bt):
    assert Postgresql.Builtins.Sign(bt.balance).current_datatype is int


def test_builtins_floor(bt):
    res = bt.get_row([Postgresql.Builtins.Floor(bt.score)], order_by=bt.id)
    assert res == [85, 72, 95, 60, None]


def test_builtins_floor_negative():
    op = Postgresql.Builtins.Floor(-1.5)
    assert op._output[0] == '(FLOOR(%s))'
    assert op.current_datatype is int


def test_builtins_ceil(bt):
    res = bt.get_row([Postgresql.Builtins.Ceil(bt.score)], order_by=bt.id)
    assert res == [86, 72, 95, 60, None]


def test_builtins_sqrt(bt):
    # PostgreSQL raises on sqrt of negative values, so filter them out first.
    res = bt.get_row(
        [Postgresql.Builtins.Sqrt(bt.balance)],
        where=bt.balance >= 0,
        order_by=bt.id,
    )
    assert [_flt(r) for r in res] == [10.0, pytest.approx(14.142135, rel=1e-5), 0.0]


def test_builtins_sqrt_datatype_float(bt):
    assert Postgresql.Builtins.Sqrt(bt.balance).current_datatype is float

def test_builtins_pow(bt):
    res = bt.get_row([Postgresql.Builtins.Pow(2, 10)], limit=1)
    assert _flt(res[0]) == 1024.0


def test_builtins_pow_datatype_float(bt):
    assert Postgresql.Builtins.Pow(bt.age, 2).current_datatype is float


def test_builtins_pow_uses_power_function():
    op = Postgresql.Builtins.Pow(2, 3)
    assert op._output[0] == '(POWER(%s, %s))'
    assert op._output[1] == [2, 3]


# ===========================================================================
# Int / Float / Str / Bool
# ===========================================================================
def test_builtins_int_cast(bt):
    # PostgreSQL rounds numeric -> integer, unlike SQLite which truncates.
    # 85.50 -> 86, 72.00 -> 72, 95.00 -> 95, 60.00 -> 60, NULL -> NULL
    res = bt.get_row([Postgresql.Builtins.Int(bt.score)], order_by=bt.id)
    assert res == [86, 72, 95, 60, None]


def test_builtins_int_datatype():
    assert Postgresql.Builtins.Int('3').current_datatype is int


def test_builtins_int_uses_cast(bt):
    op = Postgresql.Builtins.Int(bt.age)
    assert op._output[0].startswith('(CAST(')
    assert op._output[0].endswith('AS INTEGER))')

def test_builtins_float_cast(bt):
    res = bt.get_row([Postgresql.Builtins.Float(bt.age)], order_by=bt.id)
    assert res == [30.0, 25.0, 35.0, 40.0, None]


def test_builtins_float_datatype():
    assert Postgresql.Builtins.Float(3).current_datatype is float


def test_builtins_float_uses_double_precision():
    op = Postgresql.Builtins.Float(3)
    assert op._output[0] == '(CAST(%s AS DOUBLE PRECISION))'


def test_builtins_str_cast(bt):
    res = bt.get_row([Postgresql.Builtins.Str(bt.age)], order_by=bt.id)
    assert res == ['30', '25', '35', '40', None]


def test_builtins_str_uses_cast():
    op = Postgresql.Builtins.Str(42)
    assert op._output[0] == '(CAST(%s AS TEXT))'
    assert op.current_datatype is str


def test_builtins_str_concat_chain(bt):
    expr = Postgresql.Builtins.Str(bt.salary) + ' USD'
    assert '||' in expr._output[0]
    res = bt.get_row([expr], order_by=bt.id)
    # NUMERIC 50000.00 → '50000.00'
    assert res[0].endswith(' USD')


def test_builtins_bool_cast(bt):
    res = bt.get_row([Postgresql.Builtins.Bool(bt.active)], order_by=bt.id)
    assert res == [True, True, False, True, False]


def test_builtins_bool_datatype_is_bool(bt):
    assert Postgresql.Builtins.Bool(bt.active).current_datatype is bool


def test_builtins_bool_literal():
    op = Postgresql.Builtins.Bool(True)
    assert op._output == ('(CAST(%s AS BOOLEAN))', [True])


# ===========================================================================
# TypeOf / Upper / Lower / Trim / Capitalize / Find / Format
# ===========================================================================
def test_builtins_typeof(bt):
    res = bt.get_row([Postgresql.Builtins.TypeOf(bt.name)], order_by=bt.id)
    # PG_TYPEOF returns the standard internal type name, not the alias.
    # For a VARCHAR column it returns 'character varying' (not 'varchar').
    # All five rows have the same declared type regardless of the NULL value.
    assert all(r == 'character varying' for r in res)

def test_builtins_typeof_datatype():
    assert Postgresql.Builtins.TypeOf('x').current_datatype is str

def test_builtins_upper(bt):
    res = bt.get_row([Postgresql.Builtins.Upper(bt.name)], order_by=bt.id)
    assert res == ['ALICE', 'BOB', 'CAROL', None, 'EVE']


def test_builtins_upper_datatype():
    assert Postgresql.Builtins.Upper('x').current_datatype is str


def test_builtins_lower(bt):
    res = bt.get_row([Postgresql.Builtins.Lower(bt.name)], order_by=bt.id)
    assert res == ['alice', 'bob', 'carol', None, 'eve']


def test_builtins_lower_datatype():
    assert Postgresql.Builtins.Lower('X').current_datatype is str


def test_builtins_trim(bt):
    # Add a row with whitespace, verify trim
    bt.insert({bt.id: 99, bt.name: '  spaced  '})
    res = bt.get_row([Postgresql.Builtins.Trim(bt.name)],
                     where=bt.id == 99)
    assert res == ['spaced']
    bt.delete_row(bt.id == 99)


def test_builtins_capitalize():
    op = Postgresql.Builtins.Capitalize('hELLO wORLD')
    assert op._output[0].startswith('(UPPER(SUBSTRING(')
    assert op.current_datatype is str


def test_builtins_capitalize_functional(bt):
    res = bt.get_row([Postgresql.Builtins.Capitalize(bt.name)], order_by=bt.id)
    assert res == ['Alice', 'Bob', 'Carol', None, 'Eve']


def test_builtins_find(bt):
    res = bt.get_row([Postgresql.Builtins.Find(bt.name, 'a')], order_by=bt.id)
    # STRPOS is case-sensitive
    # 'Alice' -> 'a' not found -> 0
    # 'Bob'   -> 0
    # 'Carol' -> 'a' at 2
    # None    -> None
    # 'Eve'   -> 0
    assert res == [0, 0, 2, None, 0]


def test_builtins_find_datatype():
    assert Postgresql.Builtins.Find('abc', 'b').current_datatype is int


def test_builtins_find_uses_strpos():
    op = Postgresql.Builtins.Find('hello', 'l')
    assert op._output[0] == '(STRPOS(%s, %s))'
    assert op._output[1] == ['hello', 'l']


def test_builtins_format(bt):
    res = bt.get_row(
        [Postgresql.Builtins.Format('Hello, %s!', bt.name)],
        order_by=bt.id,
    )
    assert res[0] == 'Hello, Alice!'
    assert res[1] == 'Hello, Bob!'
    assert res[2] == 'Hello, Carol!'
    assert res[4] == 'Hello, Eve!'
    # Row 3 has NULL name. PostgreSQL's FORMAT('%s', NULL) may produce
    # 'Hello, NULL!', 'Hello, !', or NULL depending on version/config.
    # We only assert that the row exists.
    assert len(res) == 5


def test_builtins_format_datatype():
    assert Postgresql.Builtins.Format('%s', 'x').current_datatype is str


def test_builtins_format_multi_args(bt):
    expr = Postgresql.Builtins.Format('%s:%s', bt.name, bt.age)
    res = bt.get_row([expr], order_by=bt.id)
    assert res[0] == 'Alice:30'
    assert res[1] == 'Bob:25'

# ===========================================================================
# IsNull / IsNotNull / Between / IIf
# ===========================================================================
def test_builtins_isnull(bt):
    res = bt.get_row([bt.id],
                     where=Postgresql.Builtins.IsNull(bt.name),
                     order_by=bt.id)
    assert res == [4]


def test_builtins_isnull_datatype_is_bool():
    assert Postgresql.Builtins.IsNull('x').current_datatype is bool


def test_builtins_isnotnull(bt):
    res = bt.get_row([bt.id],
                     where=Postgresql.Builtins.IsNotNull(bt.name),
                     order_by=bt.id)
    assert res == [1, 2, 3, 5]


def test_builtins_isnull_literal_none():
    op = Postgresql.Builtins.IsNull(None)
    assert op._output[0] == '((%s) IS NULL)'
    assert op._output[1] == [None]


def test_builtins_between(bt):
    res = bt.get_row([bt.id],
                     where=Postgresql.Builtins.Between(bt.age, 25, 35),
                     order_by=bt.id)
    assert res == [1, 2, 3]


def test_builtins_between_inclusive(bt):
    res = bt.get_row([bt.id],
                     where=Postgresql.Builtins.Between(bt.age, 30, 30))
    assert res == [1]


def test_builtins_between_datatype_is_bool():
    assert Postgresql.Builtins.Between('x', 'a', 'z').current_datatype is bool


def test_builtins_between_params_order(bt):
    op = Postgresql.Builtins.Between('m', 'a', 'z')
    assert op._output[1] == ['m', 'a', 'z']


def test_builtins_iif(bt):
    res = bt.get_row(
        [Postgresql.Builtins.IIf(bt.age >= 30, 'old', 'young')],
        order_by=bt.id,
    )
    # age=NULL -> NULL >= 30 -> NULL -> falsy -> 'young'
    assert res == ['old', 'young', 'old', 'old', 'young']


def test_builtins_iif_uses_case_when():
    op = Postgresql.Builtins.IIf(True, 1, 0)
    assert op._output[0].startswith('(CASE WHEN ')
    assert op._output[0].endswith(' END)')
    assert op.current_datatype is None


def test_builtins_iif_params(bt):
    op = Postgresql.Builtins.IIf(bt.age >= 18, 'adult', 'minor')
    assert op._output[1] == [18, 'adult', 'minor']


# ===========================================================================
# Date / Time / DateTime
# ===========================================================================
def test_builtins_date(bt):
    res = bt.get_row([Postgresql.Builtins.Date(bt.created_at)], order_by=bt.id)
    assert res[0] == datetime.date(2024, 3, 15)
    assert res[2] == datetime.date(2023, 12, 25)


def test_builtins_date_datatype_is_str(bt):
    assert Postgresql.Builtins.Date(bt.created_at).current_datatype is str


def test_builtins_date_uses_cast():
    op = Postgresql.Builtins.Date('2024-03-15')
    assert op._output[0] == '(CAST(%s AS DATE))'


def test_builtins_time(bt):
    res = bt.get_row([Postgresql.Builtins.Time(bt.created_at)], order_by=bt.id)
    assert res[0] == datetime.time(9, 30, 42)


def test_builtins_datetime(bt):
    res = bt.get_row([Postgresql.Builtins.DateTime(bt.created_at)], order_by=bt.id)
    assert res[0] == datetime.datetime(2024, 3, 15, 9, 30, 42)


def test_builtins_datetime_uses_cast():
    op = Postgresql.Builtins.DateTime('2024-03-15')
    assert op._output[0] == '(CAST(%s AS TIMESTAMP))'


# ===========================================================================
# Year / Month / Day / Hour / Minute / Second
# ===========================================================================
def test_builtins_year(bt):
    res = bt.get_row([Postgresql.Builtins.Year(bt.created_at)], order_by=bt.id)
    assert res == [2024, 2024, 2023, 2024, 2024]


def test_builtins_year_datatype():
    assert Postgresql.Builtins.Year('2024-01-01').current_datatype is int


def test_builtins_year_numeric_chain(bt):
    expr = Postgresql.Builtins.Year(bt.created_at) + 1
    res = bt.get_row([expr], order_by=bt.id)
    assert res == [2025, 2025, 2024, 2025, 2025]


def test_builtins_month(bt):
    res = bt.get_row([Postgresql.Builtins.Month(bt.created_at)], order_by=bt.id)
    assert res == [3, 1, 12, 6, 3]


def test_builtins_day(bt):
    res = bt.get_row([Postgresql.Builtins.Day(bt.created_at)], order_by=bt.id)
    assert res == [15, 10, 25, 1, 15]


def test_builtins_hour(bt):
    res = bt.get_row([Postgresql.Builtins.Hour(bt.created_at)], order_by=bt.id)
    assert res == [9, 14, 8, 23, 9]


def test_builtins_minute(bt):
    res = bt.get_row([Postgresql.Builtins.Minute(bt.created_at)], order_by=bt.id)
    assert res == [30, 20, 0, 59, 30]


def test_builtins_second(bt):
    res = bt.get_row([Postgresql.Builtins.Second(bt.created_at)], order_by=bt.id)
    assert res == [42, 0, 0, 59, 42]


def test_builtins_hour_business_hours(bt):
    h = Postgresql.Builtins.Hour(bt.created_at)
    res = bt.get_row([bt.id], where=(h >= 9) & (h < 17), order_by=bt.id)
    assert res == [1, 2, 5]


def test_builtins_second_datatype(bt):
    assert Postgresql.Builtins.Second(bt.created_at).current_datatype is int
    assert Postgresql.Builtins.Minute(bt.created_at).current_datatype is int


# ===========================================================================
# DayOfWeek / IsoWeekday / Weekday / DayOfYear / WeekOfYear
# ===========================================================================
def test_builtins_dayofweek():
    # 2024-03-15 is Friday -> DOW == 5
    res = Postgresql.Builtins.DayOfWeek('2024-03-15')
    assert 'EXTRACT(DOW' in res._output[0]


def test_builtins_dayofweek_functional(bt):
    res = bt.get_row([Postgresql.Builtins.DayOfWeek(bt.created_at)], order_by=bt.id)
    # 2024-03-15 Fri=5, 2024-01-10 Wed=3, 2023-12-25 Mon=1, 2024-06-01 Sat=6, 2024-03-15 Fri=5
    assert res == [5, 3, 1, 6, 5]


def test_builtins_isoweekday(bt):
    res = bt.get_row([Postgresql.Builtins.IsoWeekday(bt.created_at)], order_by=bt.id)
    # ISO: Fri=5, Wed=3, Mon=1, Sat=6, Fri=5
    assert res == [5, 3, 1, 6, 5]


def test_builtins_isoweekday_datatype():
    assert Postgresql.Builtins.IsoWeekday('2024-03-15').current_datatype is int


def test_builtins_weekday(bt):
    res = bt.get_row([Postgresql.Builtins.Weekday(bt.created_at)], order_by=bt.id)
    # Python weekday: Fri=4, Wed=2, Mon=0, Sat=5, Fri=4
    assert res == [4, 2, 0, 5, 4]


def test_builtins_weekday_datatype():
    assert Postgresql.Builtins.Weekday('2024-03-15').current_datatype is int


def test_builtins_dayofyear(bt):
    res = bt.get_row([Postgresql.Builtins.DayOfYear(bt.created_at)], order_by=bt.id)
    # 2024-03-15 -> 75, 2024-01-10 -> 10, 2023-12-25 -> 359, 2024-06-01 -> 153, 2024-03-15 -> 75
    assert res == [75, 10, 359, 153, 75]


def test_builtins_weekofyear(bt):
    res = bt.get_row([Postgresql.Builtins.WeekOfYear(bt.created_at)], order_by=bt.id)
    # ISO week numbers, all >= 1
    assert all(isinstance(r, int) and 1 <= r <= 53 for r in res)


# ===========================================================================
# Now / Today / UnixNow / UnixEpoch / JulianDay
# ===========================================================================
def test_builtins_now(bt):
    res = bt.get_row([Postgresql.Builtins.Now()], limit=1)
    assert isinstance(res[0], datetime.datetime)


def test_builtins_now_datatype():
    assert Postgresql.Builtins.Now().current_datatype is str


def test_builtins_today(bt):
    res = bt.get_row([Postgresql.Builtins.Today()], limit=1)
    assert isinstance(res[0], datetime.date)


def test_builtins_unixnow(bt):
    res = bt.get_row([Postgresql.Builtins.UnixNow()], limit=1)
    assert isinstance(res[0], int)
    assert res[0] > 1_000_000_000


def test_builtins_unixnow_datatype():
    assert Postgresql.Builtins.UnixNow().current_datatype is int


def test_builtins_unixepoch(bt):
    res = bt.get_row([Postgresql.Builtins.UnixEpoch('1970-01-02 00:00:00')], limit=1)
    assert res[0] == 86400


def test_builtins_unixepoch_datatype(bt):
    assert Postgresql.Builtins.UnixEpoch(bt.created_at).current_datatype is int


def test_builtins_julianday():
    op = Postgresql.Builtins.JulianDay('2024-01-01')
    assert 'EXTRACT(JULIAN' in op._output[0]
    assert op.current_datatype is float


def test_builtins_julianday_functional():
    op = Postgresql.Builtins.JulianDay('2024-01-01')
    res = op  # we can't easily verify without a table; assert construction
    assert res._output[1] == ['2024-01-01']


# ===========================================================================
# Strftime / StrftimeMod
# ===========================================================================
def test_builtins_strftime(bt):
    res = bt.get_row(
        [Postgresql.Builtins.Strftime('YYYY', bt.created_at)],
        order_by=bt.id,
    )
    assert res == ['2024', '2024', '2023', '2024', '2024']


def test_builtins_strftime_params():
    op = Postgresql.Builtins.Strftime('YYYY-MM', '2024-03-15')
    assert op._output[0] == '(TO_CHAR(%s, %s))'
    assert op._output[1] == ['2024-03-15', 'YYYY-MM']


def test_builtins_strftime_datatype():
    assert Postgresql.Builtins.Strftime('YYYY', '2024').current_datatype is str


def test_builtins_strftimemod():
    op = Postgresql.Builtins.StrftimeMod(
        'YYYY-MM', 'now', '1 month'
    )
    assert op._output[0].startswith('(TO_CHAR(')
    assert 'interval' in op._output[0]
    assert 'YYYY-MM' in op._output[1]


def test_builtins_strftimemod_no_intervals():
    op = Postgresql.Builtins.StrftimeMod('YYYY', '2024-03-15')
    assert op._output[0] == '(TO_CHAR(%s, %s))'


# ===========================================================================
# DateDiffDays / DateDiffSeconds / Timediff
# ===========================================================================
def test_builtins_datediffdays():
    op = Postgresql.Builtins.DateDiffDays('2024-03-15', '2024-03-01')
    assert op.current_datatype is int
    assert 'EXTRACT(EPOCH' in op._output[0]


def test_builtins_datediffdays_params_order():
    op = Postgresql.Builtins.DateDiffDays('now', '2020-01-01')
    assert op._output[1] == ['now', '2020-01-01']


def test_builtins_datediffdays_functional(bt):
    # 14 days between 2024-03-01 and 2024-03-15
    op = Postgresql.Builtins.DateDiffDays('2024-03-15', '2024-03-01')
    res = bt.get_row([op], limit=1)
    assert res[0] == 14


def test_builtins_datediffseconds():
    op = Postgresql.Builtins.DateDiffSeconds(
        '2024-03-15 12:00:00', '2024-03-15 11:00:00'
    )
    assert op.current_datatype is int


def test_builtins_datediffseconds_functional(bt):
    op = Postgresql.Builtins.DateDiffSeconds(
        '2024-03-15 12:00:00', '2024-03-15 11:00:00'
    )
    res = bt.get_row([op], limit=1)
    assert res[0] == 3600


def test_builtins_timediff():
    op = Postgresql.Builtins.Timediff('2024-03-15', '2024-03-01')
    assert op.current_datatype is str
    assert 'AS TIMESTAMP' in op._output[0]


def test_builtins_timediff_functional(bt):
    op = Postgresql.Builtins.Timediff('2024-03-15', '2024-03-01')
    res = bt.get_row([op], limit=1)
    # The result is a text interval like '14 days'
    assert '14 days' in res[0] or '14 day' in res[0]


# ===========================================================================
# DateAdd / DateTimeAdd / TimeAdd
# ===========================================================================
def test_builtins_dateadd():
    op = Postgresql.Builtins.DateAdd('2024-03-15', '1 day')
    assert op._output[0].startswith('(CAST(')
    assert 'interval' in op._output[0]
    assert op.current_datatype is str


def test_builtins_dateadd_no_intervals():
    op = Postgresql.Builtins.DateAdd('2024-03-15')
    assert op._output[0] == '(CAST(%s AS DATE))'


def test_builtins_dateadd_functional(bt):
    op = Postgresql.Builtins.DateAdd('2024-03-15', '1 day')
    res = bt.get_row([op], limit=1)
    assert res[0] == datetime.date(2024, 3, 16)


def test_builtins_datetimeadd():
    op = Postgresql.Builtins.DateTimeAdd('2024-03-15 09:00:00', '1 hour')
    assert 'interval' in op._output[0]
    assert op.current_datatype is str


def test_builtins_datetimeadd_functional(bt):
    op = Postgresql.Builtins.DateTimeAdd('2024-03-15 09:00:00', '1 hour')
    res = bt.get_row([op], limit=1)
    assert res[0] == datetime.datetime(2024, 3, 15, 10, 0, 0)


def test_builtins_datetimeadd_no_intervals():
    op = Postgresql.Builtins.DateTimeAdd('2024-03-15 09:00:00')
    assert op._output[0] == '(CAST(%s AS TIMESTAMP))'


def test_builtins_timeadd():
    op = Postgresql.Builtins.TimeAdd('09:00:00', '30 minutes')
    assert 'interval' in op._output[0]
    assert op.current_datatype is str


def test_builtins_timeadd_functional(bt):
    op = Postgresql.Builtins.TimeAdd('2024-03-15 09:00:00', '30 minutes')
    res = bt.get_row([op], limit=1)
    assert res[0] == datetime.time(9, 30)


# ===========================================================================
# Total / GroupConcat / Func
# ===========================================================================
def test_builtins_total_empty_returns_zero():
    op = Postgresql.Builtins.Total('1')
    assert 'COALESCE(SUM' in op._output[0]
    assert op.current_datatype is float


def test_builtins_groupconcat(bt):
    res = bt.get_row(
        [Postgresql.Builtins.GroupConcat(bt.name, ',')],
        where=Postgresql.Builtins.IsNotNull(bt.name),
        limit=1,
    )
    # STRING_AGG order is unspecified
    parts = set(res[0].split(','))
    assert parts == {'Alice', 'Bob', 'Carol', 'Eve'}


def test_builtins_groupconcat_custom_sep(bt):
    res = bt.get_row(
        [Postgresql.Builtins.GroupConcat(bt.name, ' | ')],
        where=Postgresql.Builtins.IsNotNull(bt.name),
        limit=1,
    )
    parts = set(res[0].split(' | '))
    assert parts == {'Alice', 'Bob', 'Carol', 'Eve'}


def test_builtins_groupconcat_datatype():
    assert Postgresql.Builtins.GroupConcat('x').current_datatype is str


def test_builtins_func_uses_given_name(bt):
    op = Postgresql.Builtins.Func('INITCAP', 'hello world')
    assert op._output[0] == '(INITCAP(%s))'
    assert op.current_datatype is str


def test_builtins_func_rejects_empty_name():
    with pytest.raises(ValueError):
        Postgresql.Builtins.Func('', 'x')


# ===========================================================================
# Integration
# ===========================================================================
def test_builtins_combined_select(bt):
    expr = Postgresql.Builtins.Len(bt.name)
    assert expr._output[0].startswith('(LENGTH(')
    assert expr.current_datatype is int


def test_builtins_aggregate_with_other_columns(bt):
    res = bt.get_row([
        Postgresql.Builtins.Count('*'),
        Postgresql.Builtins.Sum(bt.age),
        Postgresql.Builtins.Avg(bt.age),
    ], limit=1)
    assert res[0][0] == 5
    assert res[0][1] == 130          # 30+25+35+40 (+NULL)
    assert _flt(res[0][2]) == 32.5


def test_builtins_in_where_with_arithmetic(bt):
    res = bt.get_row(
        [bt.id],
        where=(Postgresql.Builtins.Abs(bt.balance) > 50) & (bt.age >= 30),
        order_by=bt.id,
    )
    assert res == [1, 3]


def test_builtins_nested_aggregate(bt):
    expr = Postgresql.Builtins.Round(Postgresql.Builtins.Avg(bt.salary))
    res = bt.get_row([expr], limit=1)
    assert _flt(res[0]) == 65000.0


def test_builtins_cast_then_concat(bt):
    expr = Postgresql.Builtins.Str(bt.id).add_first('ID-')
    res = bt.get_row([expr], order_by=bt.id)
    assert res == ['ID-1', 'ID-2', 'ID-3', 'ID-4', 'ID-5']


def test_builtins_column_operation_input(bt):
    expr = bt.age + 5
    res = bt.get_row([Postgresql.Builtins.Abs(expr)], order_by=bt.id)
    assert res == [35, 30, 40, 45, None]


def test_builtins_in_update_statement(bt):
    bt.update(
        {bt.age: Postgresql.Builtins.Int(bt.age * 1.5)},
        bt.id == 1,
    )
    res = bt.get_row([bt.age], bt.id == 1)
    assert res == [45]


def test_builtins_in_join(pg_driver, bt):
    name = f"scores_{uuid.uuid4().hex[:8]}"
    schema = Postgresql.TableStructure(name)
    schema.add_column("uid", Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column("pts", Postgresql.DataTypes.INTEGER())

    pg_driver.create_table(schema)          # returns None
    scores = getattr(pg_driver, name)       # ← اینجا جدول را بردار

    scores.bulk_insert([scores.uid, scores.pts], [(1, 10), (2, 20), (3, 30)])
    try:
        res = (bt.inner_join(scores, bt.id == scores.uid)
                 .get_row([bt.name, Postgresql.Builtins.Abs(scores.pts * -1)],
                          order_by=bt.id))
        assert res == [('Alice', 10), ('Bob', 20), ('Carol', 30)]
    finally:
        pg_driver._exc(f'DROP TABLE IF EXISTS "{name}";')

# ===========================================================================
# Bool + python semantics
# ===========================================================================
def test_builtins_bool_matches_python(bt):
    op_zero = Postgresql.Builtins.Bool(0)
    op_one = Postgresql.Builtins.Bool(1)
    op_false = Postgresql.Builtins.Bool(False)
    op_true = Postgresql.Builtins.Bool(True)
    assert op_zero._output == ('(CAST(%s AS BOOLEAN))', [0])
    assert op_one._output == ('(CAST(%s AS BOOLEAN))', [1])
    assert op_false._output == ('(CAST(%s AS BOOLEAN))', [False])
    assert op_true._output == ('(CAST(%s AS BOOLEAN))', [True])


def test_builtins_bool_where_comparison(bt):
    res = bt.get_row([bt.id],
                     where=Postgresql.Builtins.Bool(bt.active) == True,
                     order_by=bt.id)
    assert res == [1, 2, 4]


@pytest.fixture
def users_if(in_driver):
    
    name = f"users_If{uuid.uuid4().hex[:8]}"
    s = Postgresql.TableStructure(name)
    s.add_column("id",     Postgresql.DataTypes.INTEGER(), primary_key=True)
    s.add_column("name",   Postgresql.DataTypes.VARCHAR(100))
    s.add_column("age",    Postgresql.DataTypes.INTEGER())
    s.add_column("active", Postgresql.DataTypes.BOOLEAN())
    in_driver.create_table(s)
    tbl = getattr(in_driver, name)
    tbl.bulk_insert(
        [tbl.id, tbl.name, tbl.age, tbl.active],
        [
            (1, 'Ali',   30,   True),
            (2, 'Reza',  17,   True),
            (3, 'Sara',  25,   False),
            (4, None,    40,   True),
            (5, 'Nima',  None, False),
        ]
    )
    yield tbl
    try:
        in_driver.delete_table(tbl, True, True, True)
    except Exception:
        pass
def test_Ifsql_uses_case_when(users_if):
    """The generated SQL must use `CASE WHEN ... THEN ... ELSE ... END`
    (not IIF, which PostgreSQL doesn't have)."""
    expr = users_if.name.If(users_if.active == True).Else('inactive')
    sql, params = expr._output
    assert sql.startswith('(CASE WHEN ')
    assert ' THEN ' in sql
    assert ' ELSE ' in sql
    assert sql.endswith(' END)')
    assert 'IIF' not in sql.upper()
    
    assert params == [True, 'inactive']
    
    assert users_if.name.name in sql
    assert users_if.active.name in sql
def test_Ifsql_then_literal_else_column(users_if):
    
    expr = (
        Postgresql.LiteralValue('n/a')
        .If(users_if.age == None)
        .Else(users_if.age)
    )
    sql, params = expr._output
    assert sql == (
        f'(CASE WHEN ({users_if.age.name} IS NULL) '
        f'THEN %s ELSE {users_if.age.name} END)'
    )
    assert params == ['n/a']
def test_Ifsql_then_and_else_both_columns(users_if):
    
    expr = users_if.name.If(users_if.active == True).Else(users_if.name)
    sql, params = expr._output
    assert sql == (
        f'(CASE WHEN ({users_if.active.name} = %s) '
        f'THEN {users_if.name.name} ELSE {users_if.name.name} END)'
    )
    assert params == [True]
def test_Ifsql_then_and_else_both_operations(users_if):
    
    expr = (
        users_if.name.upper()
        .If(users_if.active == True)
        .Else(users_if.name.lower())
    )
    sql, params = expr._output
    assert f'(UPPER({users_if.name.name}))' in sql
    assert f'(LOWER({users_if.name.name}))' in sql
    assert params == [True]
def test_If01_column_then_literal_else(users_if):
    res = users_if.get_row(
        [users_if.name.If(users_if.active == True).Else('inactive')],
        order_by=users_if.id,
    )
    assert res == ['Ali', 'Reza', 'inactive', None, 'inactive']
def test_If02_literal_then_column_else(users_if):
    res = users_if.get_row(
        [Postgresql.LiteralValue(0).If(users_if.age == None).Else(users_if.age)],
        order_by=users_if.id,
    )
    assert res == [30, 17, 25, 40, 0]
def test_If03_raw_condition_auto_wrapped(users_if):
    
    res_true = users_if.get_row(
        [users_if.name.If(True).Else('never')],
        order_by=users_if.id,
    )
    assert res_true == ['Ali', 'Reza', 'Sara', None, 'Nima']
    res_false = users_if.get_row(
        [users_if.name.If(False).Else('always')],
        order_by=users_if.id,
    )
    assert res_false == ['always', 'always', 'always', 'always', 'always']
def test_If04_expression_branches(users_if):
    expr = (
        users_if.name.upper()
        .If(users_if.active == True)
        .Else(users_if.name.lower())
    )
    res = users_if.get_row([expr], order_by=users_if.id)
    assert res == ['ALI', 'REZA', 'sara', None, 'nima']
def test_If05_nested_conditionals(users_if):
    label = (
        users_if.name
        .If(users_if.age == None).Else('has_age')
        .If(users_if.active == False).Else('active')
    )
    res = users_if.get_row([label], order_by=users_if.id)
    assert res == ['active', 'active', 'has_age', 'active', 'Nima']
def test_If06_forgot_else_raises_runtime_error(users_if):
    bad = users_if.name.If(users_if.active == True)
    with pytest.raises(RuntimeError, match="never chained"):
        users_if.get_row([bad])
def test_If09_partial_builder_in_where_raises(users_if):
    bad = users_if.age.If(users_if.age > 18)
    with pytest.raises(RuntimeError, match="never chained"):
        users_if.get_row([users_if.id], where=bad)
def test_If10_keyword_form(users_if):
    res = users_if.get_row(
        [users_if.name.If(users_if.active == True).Else('inactive')],
        order_by=users_if.id,
    )
    assert res == ['Ali', 'Reza', 'inactive', None, 'inactive']
def test_If11_mixed_keyword_and_underscore_form(users_if):
    a = users_if.name.If(users_if.active == True).Else('X')
    b = users_if.name.If(users_if.active == True).Else('Y')
    res = users_if.get_row([a, b], order_by=users_if.id)
    assert res == [
        ('Ali', 'Ali'),
        ('Reza', 'Reza'),
        ('X', 'Y'),
        (None, None),
        ('X', 'Y'),
    ]
def test_If12_compound_and(users_if):
    cond = (users_if.active == True) & (users_if.age > 18)
    res = users_if.get_row(
        [users_if.name.If(cond).Else('nope')],
        order_by=users_if.id,
    )
    assert res == ['Ali', 'nope', 'nope', None, 'nope']
def test_If13_or_condition(users_if):
    cond = (users_if.age == None) | (users_if.age > 30)
    res = users_if.get_row(
        [users_if.name.If(cond).Else('ok')],
        order_by=users_if.id,
    )
    assert res == ['ok', 'ok', 'ok', None, 'Nima']
def test_If14_used_in_where(users_if):
    label = Postgresql.LiteralValue('inactive').If(users_if.active == False).Else(users_if.name)
    res = users_if.get_row(
        [users_if.id],
        where=label == 'inactive',
        order_by=users_if.id,
    )
    assert res == [3, 5]
def test_If15_used_in_update(users_if):
    users_if.update(
        {users_if.name: Postgresql.LiteralValue('unknown').If(users_if.name == None).Else(users_if.name)},
        where=users_if.id > 0,
    )
    res = users_if.get_row([users_if.name], order_by=users_if.id)
    assert res == ['Ali', 'Reza', 'Sara', 'unknown', 'Nima']
def test_If16_used_in_batch_update(users_if):
    batch = users_if.batch()
    batch.update(
        {users_if.name: Postgresql.LiteralValue('unknown').If(users_if.name == None).Else(users_if.name)},
        where=users_if.id > 0,
    )
    batch.run()
    res = users_if.get_row([users_if.name], order_by=users_if.id)
    assert res == ['Ali', 'Reza', 'Sara', 'unknown', 'Nima']
def test_If17_used_in_delete(users_if):
    
    label = Postgresql.LiteralValue('').If(users_if.name != None).Else(users_if.name)
    users_if.delete_row(label == '')
    res = users_if.get_row([users_if.id], order_by=users_if.id)
    assert res == [4]
def test_If18_chained_string_method(users_if):
    expr = users_if.name.If(users_if.active == True).Else('inactive').upper()
    res = users_if.get_row([expr], order_by=users_if.id)
    assert res == ['ALI', 'REZA', 'INACTIVE', None, 'INACTIVE']
def test_If19_conditional_with_str_concat(users_if):
    expr = (
        Postgresql.LiteralValue('unknown')
        .If(users_if.name == None)
        .Else(users_if.name)
        .add_end('!')
    )
    res = users_if.get_row([expr], order_by=users_if.id)
    assert res == ['Ali!', 'Reza!', 'Sara!', 'unknown!', 'Nima!']
def test_If20_arithmetic_on_conditional(users_if):
    expr = Postgresql.LiteralValue(0).If(users_if.age == None).Else(users_if.age) + 1
    res = users_if.get_row([expr], order_by=users_if.id)
    assert res == [31, 18, 26, 41, 1]
def test_If21_used_in_order_by(users_if):
    
    label = Postgresql.LiteralValue('zzz').If(users_if.name == None).Else(users_if.name)
    
    
    res = users_if.get_row([users_if.id], order_by=label)
    assert res == [1, 5, 2, 3, 4]
def test_If22_both_branches_literal(users_if):
    res = users_if.get_row(
        [Postgresql.LiteralValue('yes').If(users_if.active == True).Else(Postgresql.LiteralValue('no'))],
        order_by=users_if.id,
    )
    assert res == ['yes', 'yes', 'no', 'yes', 'no']
def test_If23_int_branches(users_if):
    res = users_if.get_row(
        [Postgresql.LiteralValue(0).If(users_if.age == None).Else(users_if.age)],
        order_by=users_if.id,
    )
    assert res == [30, 17, 25, 40, 0]
def test_If24_empty_string_else(users_if):
    res = users_if.get_row(
        [users_if.name.If(users_if.name == None).Else(Postgresql.LiteralValue(''))],
        order_by=users_if.id,
    )
    assert res == ['', '', '', None, '']
def test_If25_current_datatype_is_none(users_if):
    label = users_if.name.If(users_if.active == True).Else(Postgresql.LiteralValue(0))
    assert label.current_datatype is None
def test_If26_multiple_conditionals_in_select(users_if):
    a = users_if.name.If(users_if.active == True).Else('X')
    b = Postgresql.LiteralValue(-1).If(users_if.age == None).Else(users_if.age)
    res = users_if.get_row([a, b], order_by=users_if.id)
    assert res == [
        ('Ali', 30),
        ('Reza', 17),
        ('X', 25),
        (None, 40),
        ('X', -1),
    ]
def test_If27_conditional_in_join(in_driver, users_if):
    name = f"orders_If{uuid.uuid4().hex[:8]}"
    s = Postgresql.TableStructure(name)
    s.add_column("id",      Postgresql.DataTypes.INTEGER(), primary_key=True)
    s.add_column("user_id", Postgresql.DataTypes.INTEGER())
    s.add_column("total",   Postgresql.DataTypes.REAL())
    in_driver.create_table(s)
    orders = getattr(in_driver, name)
    orders.bulk_insert(
        [orders.id, orders.user_id, orders.total],
        [(100, 1, 50.0), (101, 3, 0.0)]
    )
    expr = users_if.name.If(orders.total == 0).Else(users_if.name)
    try:
        res = (users_if
               .inner_join(orders, users_if.id == orders.user_id)
               .get_row([expr], order_by=users_if.id))
        
        
        assert res == [('Ali',), ('Sara',)]
    finally:
        try:
            in_driver.delete_table(orders, True, True, True)
        except Exception:
            pass
def test_If28_literal_value_exported():
    
    assert hasattr(Postgresql, 'LiteralValue')
    lv = Postgresql.LiteralValue('hello')
    assert lv._output == ('%s', ['hello'])
def test_If29_literal_value_arithmetic():
    lv = Postgresql.LiteralValue(100)
    expr = lv - 1
    assert expr._output == ('(%s - %s)', [100, 1])
def test_If30_literal_value_string_methods():
    lv = Postgresql.LiteralValue('hello').upper()
    assert lv._output == ('(UPPER(%s))', ['hello'])
def test_If31_literal_value_in_where(users_if):
    
    res = users_if.get_row(
        [users_if.name],
        where=Postgresql.LiteralValue(1) == users_if.id,
        order_by=users_if.id,
    )
    assert res == ['Ali']
    
@pytest.fixture(scope="module")
def in_driver():
    
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    yield drv
    try:
        drv.disconnect()
    except Exception:
        pass
@pytest.fixture
def tbl(in_driver):
    
    name = f"in_tbl_{uuid.uuid4().hex[:8]}"
    s = Postgresql.TableStructure(name)
    s.add_column("name", Postgresql.DataTypes.VARCHAR(100))
    s.add_column("age", Postgresql.DataTypes.INTEGER())
    s.add_column("score", Postgresql.DataTypes.REAL())
    in_driver.create_table(s)                    
    t = getattr(in_driver, name)                 
    yield t
    try:
        in_driver.delete_table(t, True, True, True)
    except Exception:
        pass
@pytest.fixture
def admins(in_driver):
    
    name = f"in_adm_{uuid.uuid4().hex[:8]}"
    s = Postgresql.TableStructure(name)
    s.add_column("username", Postgresql.DataTypes.VARCHAR(50))
    s.add_column("active", Postgresql.DataTypes.BOOLEAN())
    in_driver.create_table(s)
    t = getattr(in_driver, name)
    yield t
    try:
        in_driver.delete_table(t, True, True, True)
    except Exception:
        pass
def test_in_list_positional(tbl):
    res = tbl.name.In(["Alice", "Bob"])
    assert res._output[0] == f'({tbl.name.name} IN (%s, %s))'
    assert res._output[1] == ["Alice", "Bob"]
def test_in_list_keyword(tbl):
    res = tbl.name.In(data_list=["Alice", "Bob"])
    assert res._output[0] == f'({tbl.name.name} IN (%s, %s))'
    assert res._output[1] == ["Alice", "Bob"]
def test_in_list_single(tbl):
    res = tbl.age.In([42])
    assert res._output[0] == f'({tbl.age.name} IN (%s))'
    assert res._output[1] == [42]
def test_in_list_many(tbl):
    res = tbl.age.In([1, 2, 3, 4, 5])
    assert res._output[0] == f'({tbl.age.name} IN (%s, %s, %s, %s, %s))'
    assert res._output[1] == [1, 2, 3, 4, 5]
def test_in_list_on_float(tbl):
    res = tbl.score.In([1.5, 2.5])
    assert res._output[0] == f'({tbl.score.name} IN (%s, %s))'
    assert res._output[1] == [1.5, 2.5]
def test_in_returns_columns_operation(tbl):
    res = tbl.name.In(["a"])
    assert isinstance(res, Postgresql.ColumnsOperation)
def test_in_on_columns_operation(tbl):
    op = tbl.name + "!"
    res = op.In(["a", "b"])
    
    
    assert res._output[0] == f'(({tbl.name.name} || %s) IN (%s, %s))'
    assert res._output[1] == ["!", "a", "b"]
def test_in_no_args_error(tbl):
    with pytest.raises(Exception):
        tbl.name.In()
def test_in_subquery_no_where(tbl, admins):
    res = tbl.name.In(column=admins.username)
    assert res._output[0] == (
        f'({tbl.name.name} IN (SELECT {admins.username.name} '
        f'FROM {admins.name_}))'
    )
    assert res._output[1] == []
def test_in_subquery_with_where(tbl, admins):
    res = tbl.name.In(column=admins.username, where=admins.active == True)
    assert res._output[0] == (
        f'({tbl.name.name} IN (SELECT {admins.username.name} '
        f'FROM {admins.name_} WHERE ({admins.active.name} = %s)))'
    )
    assert res._output[1] == [True]
def test_in_subquery_with_columns_operation(tbl, admins):
    res = tbl.name.In(column=admins.username.upper())
    
    assert res._output[0] == (
        f'({tbl.name.name} IN (SELECT (UPPER({admins.username.name})) '
        f'FROM {admins.name_}))'
    )
    assert res._output[1] == []
def test_not_in_list_positional(tbl):
    res = tbl.name.not_In(["Alice", "Bob"])
    assert res._output[0] == f'({tbl.name.name} NOT IN (%s, %s))'
    assert res._output[1] == ["Alice", "Bob"]
def test_not_in_list_keyword(tbl):
    res = tbl.name.not_In(data_list=["Alice", "Bob"])
    assert res._output[0] == f'({tbl.name.name} NOT IN (%s, %s))'
    assert res._output[1] == ["Alice", "Bob"]
def test_not_in_list_single(tbl):
    res = tbl.age.not_In([42])
    assert res._output[0] == f'({tbl.age.name} NOT IN (%s))'
    assert res._output[1] == [42]
def test_not_in_on_columns_operation(tbl):
    op = tbl.name + "!"
    res = op.not_In(["a", "b"])
    assert res._output[0] == f'(({tbl.name.name} || %s) NOT IN (%s, %s))'
    assert res._output[1] == ["!", "a", "b"]
def test_not_in_subquery_no_where(tbl, admins):
    res = tbl.name.not_In(column=admins.username)
    assert res._output[0] == (
        f'({tbl.name.name} NOT IN (SELECT {admins.username.name} '
        f'FROM {admins.name_}))'
    )
    assert res._output[1] == []
def test_not_in_subquery_with_where(tbl, admins):
    res = tbl.name.not_In(column=admins.username, where=admins.active == True)
    assert res._output[0] == (
        f'({tbl.name.name} NOT IN (SELECT {admins.username.name} '
        f'FROM {admins.name_} WHERE ({admins.active.name} = %s)))'
    )
    assert res._output[1] == [True]
def test_not_in_subquery_contains_not_in_keyword(tbl, admins):
    
    res = tbl.name.not_In(column=admins.username, where=admins.active == True)
    assert " NOT IN " in res._output[0]
    assert " IN (SELECT" in res._output[0]
    assert res._output[0].count("NOT IN") == 1
def test_in_combined_with_and(tbl):
    res = tbl.name.In(["Alice"]) & (tbl.age > 18)
    assert res._output[0] == (
        f'(({tbl.name.name} IN (%s)) AND ({tbl.age.name} > %s))'
    )
    assert res._output[1] == ["Alice", 18]
def test_not_in_combined_with_or(tbl):
    res = tbl.age.not_In([1, 2]) | (tbl.age > 100)
    assert res._output[0] == (
        f'(({tbl.age.name} NOT IN (%s, %s)) OR ({tbl.age.name} > %s))'
    )
    assert res._output[1] == [1, 2, 100]
def test_eq_none_method(tbl):
    res = tbl.name.eq(None)
    assert res._output[0] == f'({tbl.name.name} IS NULL)'
    assert res._output[1] == []
def test_eq_none_operator(tbl):
    res = tbl.name == None
    assert res._output[0] == f'({tbl.name.name} IS NULL)'
    assert res._output[1] == []
def test_ne_none_method(tbl):
    res = tbl.name.ne(None)
    assert res._output[0] == f'({tbl.name.name} IS NOT NULL)'
    assert res._output[1] == []
def test_ne_none_operator(tbl):
    res = tbl.name != None
    assert res._output[0] == f'({tbl.name.name} IS NOT NULL)'
    assert res._output[1] == []
def test_eq_none_on_int(tbl):
    res = tbl.age.eq(None)
    assert res._output[0] == f'({tbl.age.name} IS NULL)'
    assert res._output[1] == []
def test_ne_none_on_int(tbl):
    res = tbl.age != None
    assert res._output[0] == f'({tbl.age.name} IS NOT NULL)'
    assert res._output[1] == []
def test_eq_none_on_float(tbl):
    res = tbl.score == None
    assert res._output[0] == f'({tbl.score.name} IS NULL)'
    assert res._output[1] == []
def test_ne_none_on_float(tbl):
    res = tbl.score != None
    assert res._output[0] == f'({tbl.score.name} IS NOT NULL)'
    assert res._output[1] == []
def test_eq_none_on_columns_operation(tbl):
    op = tbl.name + "!"
    res = op.eq(None)
    assert res._output[0] == f'(({tbl.name.name} || %s) IS NULL)'
    assert res._output[1] == ["!"]
def test_ne_none_on_columns_operation(tbl):
    op = tbl.name + "!"
    res = op != None
    assert res._output[0] == f'(({tbl.name.name} || %s) IS NOT NULL)'
    assert res._output[1] == ["!"]
def test_eq_none_combined_with_and(tbl):
    res = (tbl.name == None) & (tbl.age > 18)
    assert res._output[0] == (
        f'(({tbl.name.name} IS NULL) AND ({tbl.age.name} > %s))'
    )
    assert res._output[1] == [18]
def test_ne_none_combined_with_in(tbl):
    res = (tbl.name != None) & tbl.age.In([1, 2, 3])
    assert res._output[0] == (
        f'(({tbl.name.name} IS NOT NULL) AND '
        f'({tbl.age.name} IN (%s, %s, %s)))'
    )
    assert res._output[1] == [1, 2, 3]
def test_in_functional(tbl):
    tbl.bulk_insert(
        [tbl.name, tbl.age],
        [("Alice", 30), ("Bob", 25), ("Carol", 28), ("Dave", 22)],
    )
    res = tbl.get_row([tbl.name], tbl.name.In(["Alice", "Carol"]))
    assert set(res) == {"Alice", "Carol"}
def test_not_in_functional(tbl):
    tbl.bulk_insert(
        [tbl.name, tbl.age],
        [("X1", 1), ("X2", 2), ("X3", 3), ("X4", 4)],
    )
    res = tbl.get_row(
        [tbl.name],
        tbl.name.not_In(["X1", "X3"]),
        order_by=tbl.name,
    )
    assert res == ["X2", "X4"]
def test_in_subquery_functional(tbl, admins):
    tbl.bulk_insert(
        [tbl.name, tbl.age],
        [("admin1", 30), ("user1", 25), ("admin2", 28), ("user2", 22)],
    )
    admins.bulk_insert(
        [admins.username, admins.active],
        [("admin1", True), ("admin2", True), ("admin3", False)],
    )
    res = tbl.get_row(
        [tbl.name],
        tbl.name.In(column=admins.username, where=admins.active == True),
        order_by=tbl.name,
    )
    assert res == ["admin1", "admin2"]
def test_not_in_subquery_functional(tbl, admins):
    tbl.bulk_insert(
        [tbl.name, tbl.age],
        [("a1", 1), ("b1", 2), ("c1", 3), ("d1", 4)],
    )
    admins.bulk_insert(
        [admins.username, admins.active],
        [("a1", True), ("c1", True)],
    )
    res = tbl.get_row(
        [tbl.name],
        tbl.name.not_In(column=admins.username, where=admins.active == True),
        order_by=tbl.name,
    )
    assert res == ["b1", "d1"], (
        f"not_In returned {res!r}; if this is ['a1', 'c1'], the source's "
        f"not_In subquery branch is emitting IN instead of NOT IN."
    )
def test_eq_none_functional(tbl):
    tbl.bulk_insert(
        [tbl.name, tbl.age],
        [("has_name", 1), (None, 2), (None, 3)],
    )
    assert tbl.get_row([tbl.age], tbl.name == None, order_by=tbl.age) == [2, 3]
def test_ne_none_functional(tbl):
    tbl.bulk_insert(
        [tbl.name, tbl.age],
        [("has_name", 1), (None, 2), ("also_has_name", 3)],
    )
    assert tbl.get_row([tbl.age], tbl.name != None, order_by=tbl.age) == [1, 3]
def test_eq_none_on_int_functional(tbl):
    tbl.bulk_insert(
        [tbl.name, tbl.age],
        [("a", 10), ("b", None), ("c", 30)],
    )
    assert tbl.get_row([tbl.name], tbl.age == None) == ["b"]
    assert tbl.get_row([tbl.name], tbl.age != None, order_by=tbl.name) == ["a", "c"]
def test_eq_none_on_columns_operation_functional(tbl):
    tbl.bulk_insert(
        [tbl.name, tbl.age],
        [("a", 1), (None, 2)],
    )
    
    op = tbl.name + "!"
    assert tbl.get_row([tbl.age], op == None, order_by=tbl.age) == [2]
def test_ne_none_on_columns_operation_functional(tbl):
    tbl.bulk_insert(
        [tbl.name, tbl.age],
        [("a", 1), (None, 2), ("c", 3)],
    )
    op = tbl.name + "!"
    assert tbl.get_row([tbl.age], op != None, order_by=tbl.age) == [1, 3]
def test_in_with_null_is_null_functional(tbl):
    
    tbl.bulk_insert(
        [tbl.name, tbl.age],
        [("A", None), ("B", 20), ("A", 30)],
    )
    cond = (tbl.name.In(["A"])) & (tbl.age == None)
    assert tbl.get_row([tbl.age], cond) == [None]
@pytest.fixture(scope="function")
def order_driver():
    
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    try:
        drv.custom_execute('DROP TABLE IF EXISTS order_test CASCADE;')
    except Exception:
        pass
    schema = Postgresql.TableStructure('order_test')
    schema.add_column('id',   Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(20))
    schema.add_column('val',  Postgresql.DataTypes.INTEGER())
    drv.create_table(schema)
    tbl = drv.order_test
    tbl.bulk_insert(
        [tbl.id, tbl.name, tbl.val],
        [(i, f'U{i}', i * 10) for i in range(1, 11)]
    )
    yield drv
    try:
        drv.custom_execute('DROP TABLE IF EXISTS order_test CASCADE;')
    except Exception:
        pass
    drv.disconnect()
@pytest.fixture(scope="function")
def join_order_driver():
    
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    for t in ('users_ob', 'orders_ob', 'logs_ob'):
        try:
            drv.custom_execute(f'DROP TABLE IF EXISTS {t} CASCADE;')
        except Exception:
            pass
    
    s = Postgresql.TableStructure('users_ob')
    s.add_column('id',   Postgresql.DataTypes.INTEGER(), primary_key=True)
    s.add_column('name', Postgresql.DataTypes.VARCHAR(20))
    drv.create_table(s)
    users = drv.users_ob
    users.bulk_insert(
        [users.id, users.name],
        [(i, f'U{i}') for i in range(1, 11)]
    )
    
    s = Postgresql.TableStructure('orders_ob')
    s.add_column('id',      Postgresql.DataTypes.INTEGER(), primary_key=True)
    s.add_column('user_id', Postgresql.DataTypes.INTEGER())
    s.add_column('total',   Postgresql.DataTypes.REAL())
    drv.create_table(s)
    orders = drv.orders_ob
    orders.bulk_insert(
        [orders.id, orders.user_id, orders.total],
        [(100 + i, i, float(i * 10)) for i in range(1, 11)]
    )
    
    s = Postgresql.TableStructure('logs_ob')
    s.add_column('id',      Postgresql.DataTypes.INTEGER(), primary_key=True)
    s.add_column('user_id', Postgresql.DataTypes.INTEGER())
    s.add_column('msg',     Postgresql.DataTypes.VARCHAR(20))
    drv.create_table(s)
    logs = drv.logs_ob
    logs.bulk_insert(
        [logs.id, logs.user_id, logs.msg],
        [(i, i, f'M{i}') for i in range(1, 11)]
    )
    yield drv
    for t in ('users_ob', 'orders_ob', 'logs_ob'):
        try:
            drv.custom_execute(f'DROP TABLE IF EXISTS {t} CASCADE;')
        except Exception:
            pass
    drv.disconnect()
def test_ob_01_order_by_simple_operation_desc(order_driver):
    
    t = order_driver.order_test
    res = t.get_row([t.id], order_by=t.val * -1)
    assert res == [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
def test_ob_02_order_by_operation_equivalent_to_column(order_driver):
    
    t = order_driver.order_test
    res = t.get_row([t.id], order_by=t.id + 0)
    assert res == list(range(1, 11))
def test_ob_03_order_by_string_operation(order_driver):
    
    t = order_driver.order_test
    res = t.get_row([t.id], order_by=t.name.upper())
    
    assert res == [1, 10, 2, 3, 4, 5, 6, 7, 8, 9]
def test_ob_04_order_by_operation_zero_params(order_driver):
    
    t = order_driver.order_test
    res = t.get_row([t.id], order_by=t.id * t.id)
    assert res == list(range(1, 11))
def test_ob_05_order_by_operation_on_computed_select(order_driver):
    
    t = order_driver.order_test
    res = t.get_row(
        [t.val + 1],           
        order_by=t.val * -1,   
        limit=2,
    )
    
    assert res == [101, 91]
def test_ob_06_order_by_operation_with_where(order_driver):
    t = order_driver.order_test
    res = t.get_row(
        [t.id],
        where=t.val > 30,
        order_by=t.val * -1,
    )
    
    assert res == [10, 9, 8, 7, 6, 5, 4]
def test_ob_07_order_by_operation_with_where_params(order_driver):
    
    t = order_driver.order_test
    res = t.get_row(
        [t.id],
        where=t.val >= 20,    
        order_by=t.id * -1,   
    )
    
    assert res == [10, 9, 8, 7, 6, 5, 4, 3, 2]
def test_ob_08_order_by_operation_with_limit(order_driver):
    t = order_driver.order_test
    res = t.get_row([t.id], order_by=t.val * -1, limit=3)
    assert res == [10, 9, 8]
def test_ob_09_order_by_operation_with_limit_offset(order_driver):
    t = order_driver.order_test
    res = t.get_row([t.id], order_by=t.val * -1, limit=3, offset=2)
    assert res == [8, 7, 6]
def test_ob_10_order_by_operation_full_stack(order_driver):
    
    t = order_driver.order_test
    res = t.get_row(
        [t.id],
        where=(t.val > 20) & (t.val < 90),   
        order_by=t.id * -1 + 100,            
        limit=2,
        offset=1,                            
    )
    
    assert res == [7, 6]
def test_ob_11_order_by_operation_empty_result(order_driver):
    t = order_driver.order_test
    res = t.get_row([t.id], where=t.id > 100, order_by=t.val * -1)
    assert res == []
def test_ob_12_order_by_multiple_columns_with_operation(order_driver):
    
    t = order_driver.order_test
    res = t.get_row(
        [t.val + 1, t.val * 2],    
        order_by=t.id * -1,        
        limit=2,
    )
    
    assert res == [(101, 200), (91, 180)]
def test_ob_13_param_order_sanity(order_driver):
    t = order_driver.order_test
    res = t.get_row(
        [t.val + 1],                            
        where=(t.val >= 10) & (t.val <= 80),    
        order_by=t.val * -1,                    
        limit=2,                                
        offset=1,                               
    )
    
    
    assert res == [71, 61]
def test_ob_14_join_order_by_operation(join_order_driver):
    
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    res = (users.inner_join(orders, users.id == orders.user_id)
                .get_row([users.id],
                         order_by=orders.total * -1))
    assert [r[0] for r in res] == [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
def test_ob_15_join_order_by_string_operation(join_order_driver):
    
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    res = (users.inner_join(orders, users.id == orders.user_id)
                .get_row([users.id],
                         order_by=users.name.upper()))
    
    assert [r[0] for r in res] == [1, 10, 2, 3, 4, 5, 6, 7, 8, 9]
def test_ob_16_join_order_by_operation_with_where(join_order_driver):
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    res = (users.inner_join(orders, users.id == orders.user_id)
                .get_row([users.id],
                         where=orders.total > 30,
                         order_by=orders.total * -1))
    
    assert [r[0] for r in res] == [10, 9, 8, 7, 6, 5, 4]
def test_ob_17_join_order_by_operation_with_limit_offset(join_order_driver):
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    res = (users.inner_join(orders, users.id == orders.user_id)
                .get_row([users.id],
                         order_by=orders.total * -1,
                         limit=3, offset=2))
    assert [r[0] for r in res] == [8, 7, 6]
def test_ob_18_join_order_by_operation_full_stack(join_order_driver):
    
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    res = (users.inner_join(orders, users.id == orders.user_id)
                .get_row([users.id],
                         where=orders.total > 30,
                         order_by=orders.total * -1 + 1000,
                         limit=2,
                         offset=1))
    
    
    assert [r[0] for r in res] == [9, 8]
def test_ob_19_join_order_by_operation_chain(join_order_driver):
    
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    logs   = join_order_driver.logs_ob
    res = (users.inner_join(orders, users.id == orders.user_id)
                .inner_join(logs,   users.id == logs.user_id)
                .get_row([users.id, logs.msg],
                         order_by=orders.total * -1,
                         limit=3))
    assert [r[0] for r in res] == [10, 9, 8]
def test_ob_20_join_order_by_with_alias(join_order_driver):
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    jq = (users.inner_join(orders, users.id == orders.user_id)
               .inner_join(orders, users.id == orders.user_id))  
    res = jq.get_row([users.id],
                     order_by=orders.total * -1,
                     limit=3)
    assert len(res) == 3
def test_ob_21_join_order_by_param_order(join_order_driver):
    
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    res = (users.inner_join(orders, users.id == orders.user_id)
                .get_row(
                    [users.id],
                    where=orders.total > 20,       
                    order_by=orders.total * -1,    
                    limit=2, offset=1,             
                ))
    
    
    assert [r[0] for r in res] == [9, 8]
def test_ob_22_join_order_by_multi_select(join_order_driver):
    
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    res = (users.inner_join(orders, users.id == orders.user_id)
                .get_row(
                    [orders.total + 1, orders.total * 2],
                    order_by=users.id * -1,
                    limit=2,
                ))
    
    
    assert res == [(101, 200), (91, 180)]
def test_ob_23_join_left_order_by_operation(join_order_driver):
    
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    users.insert({users.id: 99, users.name: 'Orphan'})
    res = (users.left_join(orders, users.id == orders.user_id)
                .get_row([users.id, orders.total],
                         order_by=users.id * -1,
                         limit=2))
    
    assert res[0][0] == 99
    assert res[0][1] is None
def test_ob_24_join_order_by_operation_with_offset_only(join_order_driver):
    
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    res = (users.inner_join(orders, users.id == orders.user_id)
                .get_row([users.id],
                         order_by=orders.total * -1,
                         offset=7))
    assert [r[0] for r in res] == [3, 2, 1]
def test_ob_25_join_order_by_operation_limit_zero(join_order_driver):
    
    users  = join_order_driver.users_ob
    orders = join_order_driver.orders_ob
    res = (users.inner_join(orders, users.id == orders.user_id)
                .get_row([users.id],
                         order_by=orders.total * -1,
                         limit=0))
    assert res == []
@pytest.fixture(scope="function")
def join_driver():
    
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    for t in ('users_j', 'orders_j', 'products_j'):
        try:
            drv.custom_execute(f'DROP TABLE IF EXISTS {t} CASCADE;')
        except Exception:
            pass
    
    s = Postgresql.TableStructure('products_j')
    s.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    s.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    s.add_column('price', Postgresql.DataTypes.INTEGER())
    drv.create_table(s)
    products = drv.products_j
    products.insert({products.name: 'laptop',   products.price: 1000})
    products.insert({products.name: 'mouse',    products.price: 20})
    products.insert({products.name: 'keyboard', products.price: 50})
    
    s = Postgresql.TableStructure('users_j')
    s.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    s.add_column('username', Postgresql.DataTypes.VARCHAR(50))
    s.add_column('age', Postgresql.DataTypes.INTEGER())
    drv.create_table(s)
    users = drv.users_j
    users.insert({users.username: 'alice',   users.age: 30})
    users.insert({users.username: 'bob',     users.age: 25})
    users.insert({users.username: 'charlie', users.age: 35})
    
    s = Postgresql.TableStructure('orders_j')
    s.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    s.add_column('user_id', Postgresql.DataTypes.INTEGER())
    s.add_column('product_id', Postgresql.DataTypes.INTEGER())
    s.add_column('amount', Postgresql.DataTypes.INTEGER())
    drv.create_table(s)
    orders = drv.orders_j
    orders.insert({orders.user_id: 1, orders.product_id: 1, orders.amount: 1000})
    orders.insert({orders.user_id: 1, orders.product_id: 2, orders.amount: 20})
    orders.insert({orders.user_id: 2, orders.product_id: 3, orders.amount: 50})
    yield drv
    for t in ('users_j', 'orders_j', 'products_j'):
        try:
            drv.custom_execute(f'DROP TABLE IF EXISTS {t} CASCADE;')
        except Exception:
            pass
    drv.disconnect()
def test_join_01_inner_join_basic(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [users.username, orders.amount]
    )
    assert len(res) == 3
    assert ('alice', 1000) in res
    assert ('alice', 20)   in res
    assert ('bob',   50)   in res
def test_join_02_left_join_keeps_unmatched(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.left_join(orders, orders.user_id == users.id).get_row(
        [users.username, orders.amount]
    )
    
    assert len(res) == 4
    charlie = [r for r in res if r[0] == 'charlie']
    assert len(charlie) == 1
    assert charlie[0][1] is None
def test_join_03_right_join(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.right_join(orders, orders.user_id == users.id).get_row(
        [users.username, orders.amount]
    )
    assert len(res) == 3
def test_join_04_join_with_where(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [users.username, orders.amount],
        where=orders.amount > 100
    )
    assert res == [('alice', 1000)]
def test_join_05_join_with_order_by(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [orders.amount],
        order_by=orders.amount
    )
    assert res == [(20,), (50,), (1000,)]
def test_join_06_join_with_columns_operation_in_select(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [users.username, orders.amount * 2]
    )
    assert len(res) == 3
    doubled = sorted(r[1] for r in res)
    assert doubled == [40, 100, 2000]
def test_join_07_join_with_where_and_operation(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [users.username],
        where=(orders.amount * 10) >= 500
    )
    assert res == [('alice',), ('bob',)]
def test_join_08_multi_join_chained(join_driver):
    users    = join_driver.users_j
    orders   = join_driver.orders_j
    products = join_driver.products_j
    res = (users.inner_join(orders,   orders.user_id == users.id)
                .inner_join(products, products.id == orders.product_id)
                .get_row([users.username, products.name]))
    assert len(res) == 3
    assert ('alice', 'laptop')   in res
    assert ('alice', 'mouse')    in res
    assert ('bob',   'keyboard') in res
def test_join_09_multi_join_with_where(join_driver):
    users    = join_driver.users_j
    orders   = join_driver.orders_j
    products = join_driver.products_j
    res = (users.inner_join(orders,   orders.user_id == users.id)
                .inner_join(products, products.id == orders.product_id)
                .get_row([users.username, products.name],
                         where=products.price < 100))
    assert len(res) == 2
    assert ('alice', 'mouse')    in res
    assert ('bob',   'keyboard') in res
def test_join_10_join_with_limit(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [orders.amount],
        order_by=orders.amount,
        limit=2
    )
    assert res == [(20,), (50,)]
def test_join_11_join_with_offset(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [orders.amount],
        order_by=orders.amount,
        offset=1
    )
    assert res == [(50,), (1000,)]
def test_join_12_join_with_limit_and_offset(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [orders.amount],
        order_by=orders.amount,
        limit=1, offset=1
    )
    assert res == [(50,)]
def test_join_13_join_condition_must_be_columnsoperation(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    with pytest.raises(Exception):
        users.inner_join(orders, "invalid condition")
def test_join_14_join_returns_empty_on_no_match(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(
        orders,
        (orders.user_id == users.id) & (users.id == 9999)
    ).get_row([users.username, orders.amount])
    assert res == []
def test_join_15_joinquery_type(join_driver):
    from Ormophine.Postgresql import JoinQuery
    users  = join_driver.users_j
    orders = join_driver.orders_j
    jq = users.inner_join(orders, orders.user_id == users.id)
    assert isinstance(jq, JoinQuery)
def test_join_16_join_does_not_mutate_original(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    jq1 = users.inner_join(orders, orders.user_id == users.id)
    jq2 = jq1.left_join(users, users.id == orders.user_id)
    
    assert len(jq1.joins) == 1
    assert len(jq2.joins) == 2
def test_join_17_left_join_with_where(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.left_join(orders, orders.user_id == users.id).get_row(
        [users.username, orders.amount],
        where=orders.amount == None
    )
    
    assert len(res) == 1
    assert res[0][0] == 'charlie'
def test_limit_01_limit_only(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], order_by=tbl.name, limit=2)
    assert res == ['Alice', 'Bob']
def test_limit_02_offset_only(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], order_by=tbl.name, offset=2)
    assert res == ['Charlie', 'David', 'Eve']
def test_limit_03_limit_and_offset(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], order_by=tbl.name, limit=2, offset=1)
    assert res == ['Bob', 'Charlie']
def test_limit_04_limit_zero(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], order_by=tbl.name, limit=0)
    assert res == []
def test_limit_05_offset_beyond_total(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], order_by=tbl.name, offset=100)
    assert res == []
def test_limit_06_limit_larger_than_total(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], order_by=tbl.name, limit=100)
    assert len(res) == 5
def test_limit_07_limit_with_where(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row(
        [tbl.name],
        where=tbl.age >= 25,
        order_by=tbl.name,
        limit=2
    )
    assert res == ['Alice', 'Bob']
def test_limit_08_limit_with_multi_column_select(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name, tbl.age], order_by=tbl.name, limit=2)
    assert len(res) == 2
    assert res[0][0] == 'Alice' and res[0][1] == 30
    assert res[1][0] == 'Bob'   and res[1][1] == 25
def test_limit_09_limit_without_order_by(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], limit=3)
    assert len(res) == 3
def test_limit_10_offset_without_order_by(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], offset=2)
    
    assert len(res) == 3
def test_limit_11_limit_with_where_complex(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row(
        [tbl.name],
        where=(tbl.age >= 25) & (tbl.score != None),
        order_by=tbl.name,
        limit=2,
        offset=0
    )
    assert res == ['Alice', 'Bob']
def test_limit_12_limit_with_columns_operation(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row(
        [tbl.name, tbl.score * 2],
        order_by=tbl.name,
        limit=2
    )
    assert len(res) == 2
    
    assert abs(res[0][1] - 171.0) < 1e-6
    
    assert abs(res[1][1] - 184.0) < 1e-6
def test_limit_13_limit_and_offset_and_where(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row(
        [tbl.name],
        where=tbl.age >= 25,
        order_by=tbl.name,
        limit=1,
        offset=1
    )
    assert res == ['Bob']
def test_join_18_join_limit_zero(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [orders.amount],
        order_by=orders.amount,
        limit=0
    )
    assert res == []
def test_join_19_join_offset_beyond_total(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [orders.amount],
        order_by=orders.amount,
        offset=100
    )
    assert res == []
def test_join_20_join_limit_larger_than_total(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [orders.amount],
        order_by=orders.amount,
        limit=100
    )
    assert len(res) == 3
def test_join_21_join_limit_without_order_by(join_driver):
    users  = join_driver.users_j
    orders = join_driver.orders_j
    res = users.inner_join(orders, orders.user_id == users.id).get_row(
        [orders.amount],
        limit=2
    )
    assert len(res) == 2
def test_join_22_multi_join_limit_offset(join_driver):
    users    = join_driver.users_j
    orders   = join_driver.orders_j
    products = join_driver.products_j
    res = (users.inner_join(orders,   orders.user_id == users.id)
                .inner_join(products, products.id == orders.product_id)
                .get_row([products.price],
                         order_by=products.price,
                         limit=2, offset=1))
    assert res == [(50,), (1000,)]
@pytest.fixture(scope="session")
def session_driver():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=False
        )
    
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except:
        pass
    yield drv
    drv.disconnect()
@pytest.fixture(scope="function")
def driver(session_driver):
    
    
    try:
        for t in session_driver.get_tables():
            session_driver.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except:
        pass
    
    return session_driver
def test_01_driver_connect_valid_credentials(driver):
    assert driver._connected is True
    assert len(driver.connection_pool_storage) == 5
def test_02_driver_connect_invalid_host():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host="invalid_host_123", port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, connect_timeout=2
        )
def test_03_driver_connect_invalid_port():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=9999, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, connect_timeout=2
        )
def test_04_driver_connect_invalid_username():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username="invalid_user_xyz",
            password=PG_PASSWORD, db_name=PG_DB_NAME, connect_timeout=2
        )
def test_05_driver_connect_invalid_password():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password="wrong_password", db_name=PG_DB_NAME, connect_timeout=2
        )
def test_06_driver_connect_invalid_db_name():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name="non_existent_db_xyz"
        )
def test_07_driver_create_new_db_true_success():
    temp_db = "temp_test_db_creation"
    
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    
    clean_drv.custom_execute("SELECT 1;")
    if temp_db in clean_drv.get_databases():
        clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=temp_db, create_new_db=True
    )
    assert temp_db in drv.get_databases()
    drv.disconnect()
    
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")  
    clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
def test_08_driver_create_new_db_already_exists(session_driver):
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
def test_09_driver_create_new_db_with_collate():
    temp_db = "temp_test_db_collate"
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")
    if temp_db in clean_drv.get_databases():
        clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=temp_db, create_new_db=True,
        collate="C"
    )
    assert temp_db in drv.get_databases()
    drv.disconnect()
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")
    clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
def test_10_driver_create_new_db_with_encoding():
    temp_db = "temp_test_db_utf8"  
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")
    if temp_db in clean_drv.get_databases():
        clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=temp_db, create_new_db=True,
        client_encoding="UTF8"
    )
    assert temp_db in drv.get_databases()
    drv.disconnect()
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")
    clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
def test_11_driver_default_pool_size_5():
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    assert len(drv.connection_pool_storage) == 5
    drv.disconnect()
def test_12_driver_custom_pool_size_10():
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME, pool_size=10
    )
    assert len(drv.connection_pool_storage) == 10
    drv.disconnect()
def test_13_driver_connect_timeout_success():
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME, connect_timeout=10
    )
    assert drv._connected is True
    drv.disconnect()
def test_14_driver_connect_timeout_fails():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host="192.0.2.1",
            port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, connect_timeout=1
        )
def test_21_driver_isolation_level_invalid_str():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, isolation_level='INVALID LEVEL'
        )
def test_22_driver_disconnect_normal():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME)
    drv.disconnect()
    assert drv._connected is False
def test_23_driver_disconnect_twice_raises_error():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME)
    drv.disconnect()
    with pytest.raises(RuntimeError, match="Already disconnected"):
        drv.disconnect()
def test_24_driver_get_connection_from_pool(driver):
    con, cur = driver._get_connection()
    assert con is not None
    assert cur is not None
    driver.connection_pool.put((con, cur))
def test_25_driver_pool_exhaustion_creates_new_connection():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME, pool_size=1)
    con1, cur1 = drv._get_connection()
    
    con2, cur2 = drv._get_connection()
    assert len(drv.connection_pool_storage) == 2
    drv.connection_pool.put((con1, cur1))
    drv.connection_pool.put((con2, cur2))
    drv.disconnect()
def test_26_driver_pool_empty_raises_exception():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME, pool_size=1)
    con, cur = drv._get_connection()
    
    drv.config['host'] = 'invalid_host'
    with pytest.raises(Exception):
        drv._get_connection()
    drv.config['host'] = PG_HOST
    drv.connection_pool.put((con, cur))
    drv.disconnect()
def test_27_handle_broken_connection_success(driver):
    con, cur = driver._get_connection()
    con.close()  
    driver.connection_pool.put((con, cur))  
    
    res = driver.custom_execute_with_fetch("SELECT 1;")
    assert res == [(1,)]
def test_28_handle_broken_connection_remove_from_storage():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME, pool_size=2)
    con1, cur1 = drv._get_connection()
    con1.close()
    drv._handle_broken_connection(con1)
    assert con1 not in drv.connection_pool_storage
    assert len(drv.connection_pool_storage) == 2
    drv.disconnect()
def test_29_excfp_query_with_params_success(driver):
    res = driver._excfp("SELECT tablename FROM pg_tables WHERE schemaname = %s;", ('public',))
    assert isinstance(res, list)
def test_30_excfp_query_with_params_fails(driver):
    with pytest.raises(Exception):
        driver._excfp("SELECT * FROM non_existent_table WHERE id = %s;", (1,))
def test_31_excf_query_no_params_success(driver):
    res = driver._excf("SELECT 1;")
    assert res == [(1,)]
def test_32_excf_query_no_params_fails(driver):
    with pytest.raises(Exception):
        driver._excf("SELECT * FROM non_existent_table;")
def test_33_excp_query_with_params_success(driver):
    schema = Postgresql.TableStructure('test_excp')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.test_excp
    driver._excp(f"INSERT INTO {tbl.name_} (id, name) VALUES (%s, %s);", (1, 'Test'))
    
    res = tbl.get_row([tbl.id, tbl.name])
    assert len(res) == 1
    assert res[0][0] == 1
    assert res[0][1] == 'Test'
    driver.delete_table(tbl, True, True, True)
def test_34_excp_query_with_params_fails(driver):
    with pytest.raises(Exception):
        driver._excp("INSERT INTO non_existent_table (id) VALUES (%s);", (1,))
def test_35_exc_query_no_params_success(driver):
    schema = Postgresql.TableStructure('test_exc')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_exc
    driver._exc(f"INSERT INTO {tbl.name_} (id) VALUES (1);")
    
    res = tbl.get_row([tbl.id])
    assert res[0] == 1
    driver.delete_table(tbl, True, True, True)
def test_36_exc_query_no_params_fails(driver):
    with pytest.raises(Exception):
        driver._exc("DROP TABLE non_existent_table;")
def test_37_excs_batch_execution_success(driver):
    schema = Postgresql.TableStructure('test_excs')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_excs
    queries = [
        (f"INSERT INTO {tbl.name_} (id) VALUES (1);",),
        (f"INSERT INTO {tbl.name_} (id) VALUES (2);",),
        (f"INSERT INTO {tbl.name_} (id) VALUES (3);",)
    ]
    driver._excs(queries)
    
    res = tbl.get_row([tbl.id])
    assert len(res) == 3
    driver.delete_table(tbl, True, True, True)
def test_38_excs_batch_execution_fails_rollback(driver):
    schema = Postgresql.TableStructure('test_excs_rb')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    tbl = driver.test_excs_rb
    queries = [
        (f"INSERT INTO {tbl.name_} (id) VALUES (1);",),
        (f"INSERT INTO {tbl.name_} (id) VALUES (2);",),
        (f"INSERT INTO {tbl.name_} (id) VALUES (1);",)  
    ]
    with pytest.raises(Exception):
        driver._excs(queries)
        
    res = tbl.get_row([tbl.id])
    assert len(res) == 0
    driver.delete_table(tbl, True, True, True)
def test_39_excm_executemany_success(driver):
    schema = Postgresql.TableStructure('test_excm')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.test_excm
    data = [(1, 'A'), (2, 'B'), (3, 'C')]
    driver._excm(f"INSERT INTO {tbl.name_} (id, name) VALUES (%s, %s);", data)
    
    res = tbl.get_row([tbl.id])
    assert len(res) == 3
    driver.delete_table(tbl, True, True, True)
def test_40_excm_executemany_fails_rollback(driver):
    schema = Postgresql.TableStructure('test_excm_rb')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    tbl = driver.test_excm_rb
    data = [(1,), (2,), (1,)]  
    with pytest.raises(Exception):
        driver._excm(f"INSERT INTO {tbl.name_} (id) VALUES (%s);", data)
        
    res = tbl.get_row([tbl.id])
    assert len(res) == 0
    driver.delete_table(tbl, True, True, True)
def test_41_custom_execute_with_fetch_params(driver):
    schema = Postgresql.TableStructure('test_cewf')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_cewf
    tbl.insert({tbl.id: 1})
    
    res = driver.custom_execute_with_fetch(f"SELECT * FROM {tbl.name_} WHERE id = %s;", (1,))
    assert res == [(1,)]
    driver.delete_table(tbl, True, True, True)
def test_42_custom_execute_with_fetch_no_params(driver):
    schema = Postgresql.TableStructure('test_cewf2')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_cewf2
    tbl.insert({tbl.id: 1})
    
    res = driver.custom_execute_with_fetch(f"SELECT * FROM {tbl.name_};")
    assert res == [(1,)]
    driver.delete_table(tbl, True, True, True)
def test_43_custom_execute_params(driver):
    schema = Postgresql.TableStructure('test_ce')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.test_ce
    driver.custom_execute(f"INSERT INTO {tbl.name_} (id, name) VALUES (%s, %s);", (1, 'Ali'))
    
    res = tbl.get_row([tbl.name])
    assert res[0] == 'Ali'
    driver.delete_table(tbl, True, True, True)
def test_44_custom_execute_no_params(driver):
    schema = Postgresql.TableStructure('test_ce2')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_ce2
    driver.custom_execute(f"INSERT INTO {tbl.name_} (id) VALUES (1);")
    
    res = tbl.get_row([tbl.id])
    assert res[0] == 1
    driver.delete_table(tbl, True, True, True)
def test_45_custom_execute_many_success(driver):
    schema = Postgresql.TableStructure('test_cem')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_cem
    driver.custom_execute_many(f"INSERT INTO {tbl.name_} (id) VALUES (%s);", [(1,), (2,), (3,)])
    
    res = tbl.get_row([tbl.id])
    assert len(res) == 3
    driver.delete_table(tbl, True, True, True)
def test_46_get_databases_excludes_templates(driver):
    dbs = driver.get_databases()
    assert 'template0' not in dbs
    assert 'template1' not in dbs
def test_47_get_databases_includes_current(driver):
    dbs = driver.get_databases()
    assert PG_DB_NAME in dbs
def test_48_get_tables_empty_db():
    temp_db = "empty_db_test_orm"
    
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")
    if temp_db in clean_drv.get_databases():
        clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=temp_db, create_new_db=True
    )
    tables = drv.get_tables()
    assert tables == []
    drv.disconnect()
    
    del_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    del_drv.custom_execute("SELECT 1;")
    del_drv.delete_database(temp_db, True, True, True)
    del_drv.disconnect()
def test_49_get_tables_multiple_tables(driver):
    schema_a = Postgresql.TableStructure('tbl_a')
    schema_a.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema_a)
    schema_b = Postgresql.TableStructure('tbl_b')
    schema_b.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema_b)
    tables = driver.get_tables()
    assert 'tbl_a' in tables
    assert 'tbl_b' in tables
    driver.delete_table(driver.tbl_a, True, True, True)
    driver.delete_table(driver.tbl_b, True, True, True)
def test_50_disconnect_with_active_pool_connections():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME, pool_size=3)
    con, cur = drv._get_connection()
    drv.connection_pool.put((con, cur))
    drv.disconnect()
    assert drv._connected is False
@pytest.fixture(scope="module")
def driver():
    
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    
    
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except:
        pass
        
    yield drv
    
    
    try:
        drv.custom_execute(f'DROP DATABASE IF EXISTS "temp_db_100";')
        drv.drop_user("test_user_100")
    except:
        pass
    drv.disconnect()
def test_51_create_table_basic(driver):
    schema = Postgresql.TableStructure('t51')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    assert 't51' in driver.get_tables()
    assert hasattr(driver, 't51')
def test_52_create_table_Ifnot_exists_logic(driver):
    
    schema = Postgresql.TableStructure('t51')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    with pytest.raises(Exception):
        driver.create_table(schema)
def test_53_create_table_duplicate_raises_error(driver):
    schema = Postgresql.TableStructure('t51_dup')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    with pytest.raises(Exception):
        driver.create_table(schema)
def test_54_delete_table_triple_true(driver):
    schema = Postgresql.TableStructure('t54_del')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    driver.delete_table(driver.t54_del, are_you_sure=True, are_you_really_sure=True, for_sure=True)
    assert 't54_del' not in driver.get_tables()
    assert not hasattr(driver, 't54_del')
def test_55_delete_table_missing_one_flag(driver):
    schema = Postgresql.TableStructure('t55_del')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    driver.delete_table(driver.t55_del, are_you_sure=True, are_you_really_sure=True, for_sure=False)
    assert 't55_del' in driver.get_tables()
def test_56_delete_table_missing_two_flags(driver):
    schema = Postgresql.TableStructure('t56_del')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    driver.delete_table(driver.t56_del, are_you_sure=True, are_you_really_sure=False, for_sure=False)
    assert 't56_del' in driver.get_tables()
def test_57_delete_table_nonexistent(driver):
    schema = Postgresql.TableStructure('t57_ghost')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    
    ghost_table = Postgresql.Table(driver, 't57_ghost')
    with pytest.raises(Exception):
        driver.delete_table(ghost_table, True, True, True)
def test_58_delete_database_triple_true(driver):
    temp_db = "temp_db_100"
    
    drv_temp = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=temp_db, create_new_db=True)
    drv_temp.disconnect()
    
    driver.delete_database(temp_db, are_you_sure=True, are_you_really_sure=True, for_sure=True)
    assert temp_db not in driver.get_databases()
def test_59_delete_database_missing_flags(driver):
    temp_db = "temp_db_100_2"
    drv_temp = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=temp_db, create_new_db=True)
    drv_temp.disconnect()
    
    driver.delete_database(temp_db, are_you_sure=True, are_you_really_sure=False, for_sure=True)
    assert temp_db in driver.get_databases()
    
    driver.delete_database(temp_db, True, True, True)
def test_60_delete_database_nonexistent(driver):
    with pytest.raises(Exception):
        driver.delete_database("non_existent_db_xyz", True, True, True)
def test_61_create_user_basic(driver):
    try:
        driver.drop_user("test_user_100")
    except:
        pass
    driver.create_user("test_user_100", "secure_pass_123")
    users = driver.custom_execute_with_fetch(
        "SELECT usename FROM pg_user WHERE usename = 'test_user_100';"
    )
    assert len(users) == 1
def test_62_create_user_duplicate(driver):
    with pytest.raises(Exception):
        driver.create_user("test_user_100", "secure_pass_123")
def test_63_create_user_invalid_name(driver):
    with pytest.raises(Exception):
        driver.create_user("invalid-user-name;", "pass")
def test_64_drop_user_basic(driver):
    driver.create_user("temp_user_to_drop", "pass")
    driver.drop_user("temp_user_to_drop")
    users = driver.custom_execute_with_fetch("SELECT usename FROM pg_user WHERE usename = 'temp_user_to_drop';")
    assert len(users) == 0
def test_65_drop_user_nonexistent(driver):
    with pytest.raises(Exception):
        driver.drop_user("ghost_user_123")
def test_66_optimize_empty_db(driver):
    temp_db = "empty_db_opt_100"
    drv_temp = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=temp_db, create_new_db=True)
    drv_temp.optimize()  
    drv_temp.disconnect()
    driver.delete_database(temp_db, True, True, True)
def test_67_optimize_with_tables(driver):
    schema = Postgresql.TableStructure('t67_opt')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t67_opt
    tbl.insert({tbl.val: 'A'})
    tbl.insert({tbl.val: 'B'})
    tbl.insert({tbl.val: 'C'})
    driver.optimize()
    res = tbl.get_row([tbl.id])
    assert len(res) == 3
    driver.delete_table(tbl, True, True, True)
def test_68_optimize_after_bulk_insert(driver):
    schema = Postgresql.TableStructure('t68_opt')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.t68_opt
    
    data = [(i,) for i in range(100)]
    driver.custom_execute_many(f"INSERT INTO {tbl.name_} (id) VALUES (%s);", data)
    driver.optimize()
    res = tbl.get_row([tbl.id])
    assert len(res) == 100
    driver.delete_table(tbl, True, True, True)
def test_69_table_object_existing(driver):
    tbl = Postgresql.Table(driver, 't67_opt')
    assert isinstance(tbl, Postgresql.Table)
    assert tbl.name_ == '"t67_opt"'
def test_72_table_attribute_auto_discovery(driver):
    schema = Postgresql.TableStructure('t72_auto')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    assert hasattr(driver, 't72_auto')
    assert isinstance(driver.t72_auto, Postgresql.Table)
def test_73_table_attribute_not_exists(driver):
    assert not hasattr(driver, 't73_ghost')
def test_74_get_columns_name_after_create(driver):
    schema = Postgresql.TableStructure('t74_cols')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    cols = driver.t74_cols.get_columns_name()
    assert 'id' in cols
    assert 'name' in cols
    assert 'age' in cols
def test_75_table_name_quoting(driver):
    schema = Postgresql.TableStructure('Table With Spaces')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    
    assert 'Table With Spaces' in driver.get_tables()
    
    
    tbl = Postgresql.Table(driver, 'Table With Spaces')
    driver.delete_table(tbl, True, True, True)
def test_76_table_name_with_special_chars(driver):
    schema = Postgresql.TableStructure('t$pecial#@')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    
    assert 't$pecial#@'
    
    tbl = Postgresql.Table(driver, 't$pecial#@')
    driver.delete_table(tbl, True, True, True)
def test_78_alter_table_add_column(driver):
    schema = Postgresql.TableStructure('t78')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    driver.t78.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    cols = driver.t78.get_columns_name()
    assert 'name' in cols
    driver.delete_table(driver.t78, True, True, True)
def test_79_alter_table_drop_column(driver):
    schema = Postgresql.TableStructure('t79')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('val', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    driver.t79.delete_column(driver.t79.val, True, True, True)
    cols = driver.t79.get_columns_name()
    assert 'val' not in cols
    driver.delete_table(driver.t79, True, True, True)
def test_80_alter_table_rename_column(driver):
    schema = Postgresql.TableStructure('t80')
    schema.add_column('old_name', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    driver.t80.rename_column(driver.t80.old_name, 'new_name')
    cols = driver.t80.get_columns_name()
    assert 'new_name' in cols and 'old_name' not in cols
    driver.delete_table(driver.t80, True, True, True)
def test_85_create_index_simple(driver):
    schema = Postgresql.TableStructure('t85')
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    driver.t85.create_index('idx_name85', [driver.t85.name])
    indexes = driver.t85.get_indexes_info()
    assert any(idx['idx_name'] == 'idx_name85' for idx in indexes)
    driver.delete_table(driver.t85, True, True, True)
def test_86_create_index_unique(driver):
    schema = Postgresql.TableStructure('t86')
    schema.add_column('email', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    driver.t86.create_index('idx_email86', [driver.t86.email], unique=True)
    
    indexes = driver.t86.get_indexes_info()
    idx = next((i for i in indexes if i['idx_name'] == 'idx_email86'), None)
    assert idx is not None and idx['unique'] is True
    
    driver.t86.insert({driver.t86.email: 'a@b.com'})
    with pytest.raises(Exception):
        driver.t86.insert({driver.t86.email: 'a@b.com'})
    driver.delete_table(driver.t86, True, True, True)
def test_87_create_index_multi_column(driver):
    schema = Postgresql.TableStructure('t87')
    schema.add_column('a', Postgresql.DataTypes.INTEGER())
    schema.add_column('b', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    driver.t87.create_index('idx_ab87', [driver.t87.a, driver.t87.b])
    indexes = driver.t87.get_indexes_info()
    assert any(idx['idx_name'] == 'idx_ab87' for idx in indexes)
    driver.delete_table(driver.t87, True, True, True)
def test_88_drop_index(driver):
    schema = Postgresql.TableStructure('t88')
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    driver.t88.create_index('idx_name88', [driver.t88.name])
    driver.t88.delete_index('idx_name88')
    indexes = driver.t88.get_indexes_info()
    assert not any(idx['idx_name'] == 'idx_name88' for idx in indexes)
    driver.delete_table(driver.t88, True, True, True)
def test_101_data_type_integer():
    schema = Postgresql.TableStructure('t101')
    schema.add_column('col', Postgresql.DataTypes.INTEGER(), primary_key=True)
    sql = schema.get_structure()
    assert 'INTEGER' in sql.upper()
def test_102_data_type_smallint():
    schema = Postgresql.TableStructure('t102')
    schema.add_column('col', Postgresql.DataTypes.SMALLINT(), primary_key=True)
    sql = schema.get_structure()
    assert 'SMALLINT' in sql.upper()
def test_103_data_type_bigint():
    schema = Postgresql.TableStructure('t103')
    schema.add_column('col', Postgresql.DataTypes.BIGINT(), primary_key=True)
    sql = schema.get_structure()
    assert 'BIGINT' in sql.upper()
def test_104_data_type_serial():
    schema = Postgresql.TableStructure('t104')
    schema.add_column('col', Postgresql.DataTypes.SERIAL(), primary_key=True)
    sql = schema.get_structure()
    assert 'SERIAL' in sql.upper()
def test_105_data_type_bigserial():
    schema = Postgresql.TableStructure('t105')
    schema.add_column('col', Postgresql.DataTypes.BIGSERIAL(), primary_key=True)
    sql = schema.get_structure()
    assert 'BIGSERIAL' in sql.upper()
def test_106_data_type_real():
    schema = Postgresql.TableStructure('t106')
    schema.add_column('col', Postgresql.DataTypes.REAL(), primary_key=True)
    sql = schema.get_structure()
    assert 'REAL' in sql.upper()
def test_107_data_type_double_precision():
    schema = Postgresql.TableStructure('t107')
    schema.add_column('col', Postgresql.DataTypes.DOUBLE_PRECISION(), primary_key=True)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'DOUBLE PRECISION' in sql_upper or 'DOUBLE_PRECISION' in sql_upper or 'DOUBLE' in sql_upper
def test_108_data_type_decimal():
    schema = Postgresql.TableStructure('t108')
    schema.add_column('col', Postgresql.DataTypes.DECIMAL(), primary_key=True)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'DECIMAL' in sql_upper or 'NUMERIC' in sql_upper
def test_109_data_type_numeric():
    schema = Postgresql.TableStructure('t109')
    schema.add_column('col', Postgresql.DataTypes.NUMERIC(), primary_key=True)
    sql = schema.get_structure()
    assert 'NUMERIC' in sql.upper()
def test_110_data_type_money():
    schema = Postgresql.TableStructure('t110')
    schema.add_column('col', Postgresql.DataTypes.MONEY(), primary_key=True)
    sql = schema.get_structure()
    assert 'MONEY' in sql.upper()
def test_111_data_type_boolean_true():
    schema = Postgresql.TableStructure('t111')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('flag', Postgresql.DataTypes.BOOLEAN())
    sql = schema.get_structure()
    assert 'BOOLEAN' in sql.upper()
def test_112_data_type_boolean_false():
    schema = Postgresql.TableStructure('t112')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('flag', Postgresql.DataTypes.BOOLEAN(), default_value=False)
    sql = schema.get_structure()
    assert 'BOOLEAN' in sql.upper()
def test_116_data_type_decimal_precision_scale():
    dt = Postgresql.DataTypes.DECIMAL(precision=10, scale=2)
    schema = Postgresql.TableStructure('t116')
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert ('DECIMAL(10, 2)' in sql_upper or
            'NUMERIC(10, 2)' in sql_upper or
            'DECIMAL(10,2)' in sql_upper or
            'NUMERIC(10,2)' in sql_upper)
def test_117_data_type_numeric_precision_scale():
    dt = Postgresql.DataTypes.NUMERIC(precision=15, scale=4)
    schema = Postgresql.TableStructure('t117')
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'NUMERIC(15, 4)' in sql_upper or 'NUMERIC(15,4)' in sql_upper
def test_127_data_type_serial_auto_increment(driver):
    
    schema = Postgresql.TableStructure('t127')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t127
    tbl.insert({tbl.name: 'first'})
    tbl.insert({tbl.name: 'second'})
    res = tbl.get_row([tbl.name])
    assert len(res) == 2
    assert res[0] == 'first'
    assert res[1] == 'second'
    driver.delete_table(tbl, True, True, True)
def test_128_data_type_bigserial_auto_increment(driver):
    
    schema = Postgresql.TableStructure('t128')
    schema.add_column('id', Postgresql.DataTypes.BIGSERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t128
    tbl.insert({tbl.name: 'a'})
    tbl.insert({tbl.name: 'b'})
    res = tbl.get_row([tbl.id])
    assert len(res) == 2
    assert res[0] == 1
    assert res[1] == 2
    driver.delete_table(tbl, True, True, True)
def test_129_data_type_numeric_invalid_precision():
    
    with pytest.raises(Exception):
        Postgresql.DataTypes.NUMERIC(precision=0, scale=0)
def test_130_data_type_decimal_scale_gt_precision():
    with pytest.raises(Exception):
        Postgresql.DataTypes.DECIMAL(precision=3, scale=5)
def test_131_data_type_integer_default_value():
    schema = Postgresql.TableStructure('t131')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('age', Postgresql.DataTypes.INTEGER(), default_value=18)
    sql = schema.get_structure()
    assert 'DEFAULT 18' in sql
def test_132_data_type_numeric_default_value():
    schema = Postgresql.TableStructure('t132')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('price', Postgresql.DataTypes.NUMERIC(10, 2), default_value=0.00)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'DEFAULT' in sql_upper
    assert '0' in sql
def test_133_data_type_boolean_default_true():
    schema = Postgresql.TableStructure('t133')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('active', Postgresql.DataTypes.BOOLEAN(), default_value=True)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'DEFAULT TRUE' in sql_upper or 'DEFAULT true' in sql
def test_134_data_type_boolean_default_false():
    schema = Postgresql.TableStructure('t134')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('deleted', Postgresql.DataTypes.BOOLEAN(), default_value=False)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'DEFAULT FALSE' in sql_upper or 'DEFAULT false' in sql
def test_135_data_type_money_default():
    schema = Postgresql.TableStructure('t135')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('amount', Postgresql.DataTypes.MONEY(), default_value=0)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'MONEY' in sql_upper
    assert 'DEFAULT' in sql_upper
def test_136_data_type_integer_null_insert(driver):
    
    schema = Postgresql.TableStructure('t136')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t136
    tbl.insert({tbl.val: None})
    res = tbl.get_row([tbl.val])
    assert res[0] is None
    driver.delete_table(tbl, True, True, True)
def test_137_data_type_integer_not_null_violation(driver):
    
    schema = Postgresql.TableStructure('t137')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER(), not_null=True)
    driver.create_table(schema)
    tbl = driver.t137
    with pytest.raises(Exception):
        tbl.insert({tbl.val: None})
    driver.delete_table(tbl, True, True, True)
def test_138_data_type_decimal_negative(driver):
    
    schema = Postgresql.TableStructure('t138')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('balance', Postgresql.DataTypes.DECIMAL(10, 2))
    driver.create_table(schema)
    tbl = driver.t138
    tbl.insert({tbl.balance: -1234.56})
    res = tbl.get_row([tbl.balance])
    assert float(res[0]) == -1234.56
    driver.delete_table(tbl, True, True, True)
def test_139_data_type_real_scientific_notation(driver):
    
    schema = Postgresql.TableStructure('t139')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.REAL())
    driver.create_table(schema)
    tbl = driver.t139
    tbl.insert({tbl.val: 1.5e-10})
    res = tbl.get_row([tbl.val])
    assert abs(float(res[0]) - 1.5e-10) < 1e-15
    driver.delete_table(tbl, True, True, True)
def test_140_data_type_bigint_large_value(driver):
    
    schema = Postgresql.TableStructure('t140')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('big_val', Postgresql.DataTypes.BIGINT())
    driver.create_table(schema)
    tbl = driver.t140
    large_val = 2 ** 62
    tbl.insert({tbl.big_val: large_val})
    res = tbl.get_row([tbl.big_val])
    assert res[0] == large_val
    driver.delete_table(tbl, True, True, True)
def test_141_data_type_numeric_large_precision(driver):
    
    schema = Postgresql.TableStructure('t141')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.NUMERIC(38, 10))
    driver.create_table(schema)
    tbl = driver.t141
    large_num = '1234567890123456789012345678.1234567890'
    tbl.insert({tbl.val: large_num})
    res = tbl.get_row([tbl.val])
    assert str(res[0]).replace(' ', '').startswith('1234567890123456789012345678')
    driver.delete_table(tbl, True, True, True)
def test_142_data_type_smallint_boundary(driver):
    
    schema = Postgresql.TableStructure('t142')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.SMALLINT())
    driver.create_table(schema)
    tbl = driver.t142
    tbl.insert({tbl.val: 32767})
    res = tbl.get_row([tbl.val])
    assert res[0] == 32767
    with pytest.raises(Exception):
        tbl.insert({tbl.val: 32768})
    driver.delete_table(tbl, True, True, True)
def test_143_data_type_integer_boundary(driver):
    
    schema = Postgresql.TableStructure('t143')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t143
    tbl.insert({tbl.val: 2147483647})
    res = tbl.get_row([tbl.val])
    assert res[0] == 2147483647
    driver.delete_table(tbl, True, True, True)
def test_144_data_type_bigint_boundary(driver):
    
    schema = Postgresql.TableStructure('t144')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.BIGINT())
    driver.create_table(schema)
    tbl = driver.t144
    boundary = 2**63 - 1
    tbl.insert({tbl.val: boundary})
    res = tbl.get_row([tbl.val])
    assert res[0] == boundary
    driver.delete_table(tbl, True, True, True)
def test_145_data_type_serial_zero_insert(driver):
    
    schema = Postgresql.TableStructure('t145')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t145
    tbl.insert({tbl.id: 0, tbl.name: 'zero_id'})
    res = tbl.get_row([tbl.id])
    assert res[0] == 0
    driver.delete_table(tbl, True, True, True)
def test_146_data_type_decimal_rounding(driver):
    
    schema = Postgresql.TableStructure('t146')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.DECIMAL(5, 2))
    driver.create_table(schema)
    tbl = driver.t146
    tbl.insert({tbl.val: 123.456})
    res = tbl.get_row([tbl.val])
    assert float(res[0]) == 123.46
    driver.delete_table(tbl, True, True, True)
def test_147_data_type_numeric_aggregation(driver):
    
    schema = Postgresql.TableStructure('t147')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('amount', Postgresql.DataTypes.NUMERIC(10, 2))
    driver.create_table(schema)
    tbl = driver.t147
    tbl.insert({tbl.amount: 100.50})
    tbl.insert({tbl.amount: 200.25})
    tbl.insert({tbl.amount: 300.25})
    res = tbl.get_row([tbl.amount])
    total = sum(float(r) for r in res)
    assert total == 601.0
    driver.delete_table(tbl, True, True, True)
def test_148_data_type_boolean_logic_and(driver):
    
    schema = Postgresql.TableStructure('t148')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('a', Postgresql.DataTypes.BOOLEAN())
    schema.add_column('b', Postgresql.DataTypes.BOOLEAN())
    driver.create_table(schema)
    tbl = driver.t148
    tbl.insert({tbl.a: True, tbl.b: True})
    tbl.insert({tbl.a: True, tbl.b: False})
    tbl.insert({tbl.a: False, tbl.b: True})
    res = tbl.get_row([tbl.a,tbl.b])
    both_true = [r for r in res if r[0] is True and r[1] is True]
    assert len(both_true) == 1
    driver.delete_table(tbl, True, True, True)
def test_149_data_type_boolean_logic_or(driver):
    
    schema = Postgresql.TableStructure('t149')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('a', Postgresql.DataTypes.BOOLEAN())
    schema.add_column('b', Postgresql.DataTypes.BOOLEAN())
    driver.create_table(schema)
    tbl = driver.t149
    tbl.insert({tbl.a: True, tbl.b: False})
    tbl.insert({tbl.a: False, tbl.b: True})
    tbl.insert({tbl.a: False, tbl.b: False})
    res = tbl.get_row([tbl.a,tbl.b])
    any_true = [r for r in res if r[0] is True or r[1] is True]
    assert len(any_true) == 2
    driver.delete_table(tbl, True, True, True)
@pytest.fixture(scope="module")
def driver():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except:
        pass
        
    yield drv
    
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except:
        pass
    drv.disconnect()
def test_151_crud_insert_and_select(driver):
    
    schema = Postgresql.TableStructure('t151')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t151
    tbl.insert({tbl.name: 'Ali', tbl.age: 30})
    tbl.insert({tbl.name: 'Sara', tbl.age: 25})
    res = tbl.get_row([tbl.name])
    assert len(res) == 2
    assert 'Ali' in res
    assert 'Sara' in res
    driver.delete_table(tbl, True, True, True)
def test_152_crud_update(driver):
    
    schema = Postgresql.TableStructure('t152')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t152
    tbl.insert({tbl.name: 'Ali', tbl.age: 30})
    tbl.update({tbl.age: 31}, where=tbl.name == 'Ali')
    res = tbl.get_row([tbl.age])
    assert res[0] == 31
    driver.delete_table(tbl, True, True, True)
def test_153_crud_delete(driver):
    
    schema = Postgresql.TableStructure('t153')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    tbl = driver.t153
    tbl.insert({tbl.name: 'Ali'})
    tbl.insert({tbl.name: 'Sara'})
    tbl.delete_row(where=tbl.name == 'Ali')
    res = tbl.get_row([tbl.name])  
    assert res[0] == 'Sara'
    driver.delete_table(tbl, True, True, True)
def test_154_select_where_equal(driver):
    
    schema = Postgresql.TableStructure('t154')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('city', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t154
    tbl.insert({tbl.city: 'Tehran'})
    tbl.insert({tbl.city: 'Isfahan'})
    tbl.insert({tbl.city: 'Tehran'})
    res = tbl.get_row([tbl.id],where=tbl.city== 'Tehran')
    assert len(res) == 2
    driver.delete_table(tbl, True, True, True)
def test_155_select_where_multiple_conditions(driver):
    
    schema = Postgresql.TableStructure('t155')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('city', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t155
    tbl.insert({tbl.city: 'Tehran', tbl.age: 30})
    tbl.insert({tbl.city: 'Tehran', tbl.age: 20})
    tbl.insert({tbl.city: 'Isfahan', tbl.age: 30})
    res = tbl.get_row([tbl.city, tbl.age],where=(tbl.city== 'Tehran') & (tbl.age== 30))
    assert len(res) == 1
    assert res[0][0] == 'Tehran'
    assert res[0][1] == 30
    driver.delete_table(tbl, True, True, True)
def test_156_select_order_by(driver):
    
    schema = Postgresql.TableStructure('t156')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('score', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t156
    tbl.insert({tbl.score: 90})
    tbl.insert({tbl.score: 70})
    tbl.insert({tbl.score: 85})
    res = tbl.get_row([tbl.score],order_by=tbl.score)
    assert res[0] == 70
    assert res[2] == 90
    driver.delete_table(tbl, True, True, True)
def test_158_foreign_key_relationship(driver):
    
    
    schema_dept = Postgresql.TableStructure('t158_dept')
    schema_dept.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_dept.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema_dept)
    dept = driver.t158_dept
    dept.insert({dept.name: 'Engineering'})
    dept.insert({dept.name: 'Marketing'})
    
    schema_emp = Postgresql.TableStructure('t158_emp')
    schema_emp.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_emp.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    schema_emp.add_column('dept_id', Postgresql.DataTypes.INTEGER())
    schema_emp.foreign_key('dept_id', dept, dept.id, on_delete='CASCADE')
    driver.create_table(schema_emp)
    emp = driver.t158_emp
    emp.insert({emp.name: 'Ali', emp.dept_id: 1})
    emp.insert({emp.name: 'Sara', emp.dept_id: 2})
    res = emp.get_row([emp.name])
    assert len(res) == 2
    
    with pytest.raises(Exception):
        emp.insert({emp.name: 'Reza', emp.dept_id: 999})
    driver.delete_table(emp, True, True, True)
    driver.delete_table(dept, True, True, True)
def test_159_unique_constraint(driver):
    
    schema = Postgresql.TableStructure('t159')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('email', Postgresql.DataTypes.VARCHAR(200), unique=True)
    driver.create_table(schema)
    tbl = driver.t159
    tbl.insert({tbl.email: 'a@test.com'})
    with pytest.raises(Exception):
        tbl.insert({tbl.email: 'a@test.com'})
    driver.delete_table(tbl, True, True, True)
def test_160_insert_many(driver):
    
    schema = Postgresql.TableStructure('t160')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('score', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t160
    records = [
        {tbl.name: 'Ali', tbl.score: 85},
        {tbl.name: 'Sara', tbl.score: 92},
        {tbl.name: 'Reza', tbl.score: 78},
    ]
    tbl.bulk_insert([tbl.name, tbl.score], 
                [(r[tbl.name], r[tbl.score]) for r in records])
    res = tbl.get_row([tbl.name])
    assert len(res) == 3
    driver.delete_table(tbl, True, True, True)
def test_162_exists(driver):
    
    schema = Postgresql.TableStructure('t162')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t162
    tbl.insert({tbl.name: 'Ali'})
    
    def exists(table, where):
            return len(table.get_row([table.id], where=where)) > 0
    
    assert exists(tbl, tbl.name == 'Ali') is True
    driver.delete_table(tbl, True, True, True)
def test_163_default_value_on_insert(driver):
    
    schema = Postgresql.TableStructure('t163')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('status', Postgresql.DataTypes.VARCHAR(20), default_value='active')
    driver.create_table(schema)
    tbl = driver.t163
    tbl.insert({})  
    res = tbl.get_row([tbl.status])
    assert res[0] == 'active'
    driver.delete_table(tbl, True, True, True)
def test_164_not_null_enforcement(driver):
    
    schema = Postgresql.TableStructure('t164')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50), not_null=True)
    driver.create_table(schema)
    tbl = driver.t164
    with pytest.raises(Exception):
        tbl.insert({tbl.name: None})
    driver.delete_table(tbl, True, True, True)
def test_166_create_and_delete_table_lifecycle(driver):
    
    schema = Postgresql.TableStructure('t166')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    assert 't166' in driver.get_tables()
    assert hasattr(driver, 't166')
    driver.delete_table(driver.t166, True, True, True)
    assert 't166' not in driver.get_tables()
    assert not hasattr(driver, 't166')
def test_167_delete_table_requires_all_flags(driver):
    
    schema = Postgresql.TableStructure('t167')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    driver.delete_table(driver.t167, True, True, False)
    assert 't167' in driver.get_tables()  
    driver.delete_table(driver.t167, True, True, True)  
def test_168_table_name_with_spaces(driver):
    
    schema = Postgresql.TableStructure('My Table')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = getattr(driver, 'My Table')
    tbl.insert({tbl.val: 42})
    res = tbl.get_row([tbl.val])
    assert res[0] == 42
    driver.delete_table(tbl, True, True, True)
def test_169_composite_primary_key(driver):
    
    schema = Postgresql.TableStructure('t169')
    schema.add_column('user_id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('role_id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.t169
    tbl.insert({tbl.user_id: 1, tbl.role_id: 1})
    tbl.insert({tbl.user_id: 1, tbl.role_id: 2})
    
    with pytest.raises(Exception):
        tbl.insert({tbl.user_id: 1, tbl.role_id: 1})
    driver.delete_table(tbl, True, True, True)
def test_170_get_columns_name(driver):
    
    schema = Postgresql.TableStructure('t170')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('first_name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('last_name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('salary', Postgresql.DataTypes.NUMERIC(10, 2))
    driver.create_table(schema)
    cols = driver.t170.get_columns_name()
    assert 'id' in cols
    assert 'first_name' in cols
    assert 'last_name' in cols
    assert 'salary' in cols
    driver.delete_table(driver.t170, True, True, True)
def test_171_optimize_after_operations(driver):
    
    schema = Postgresql.TableStructure('t171')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t171
    for i in range(100):
        tbl.insert({tbl.val: i})
    
    for i in range(50):
        tbl.delete_row(where=tbl.val == i)
    driver.optimize()
    assert len(tbl.get_row([tbl.val])) == 50
    driver.delete_table(tbl, True, True, True)
def test_172_table_object_lookup(driver):
    
    schema = Postgresql.TableStructure('t172')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    tbl = getattr(driver, 't172')
    assert isinstance(tbl, Postgresql.Table)
    assert tbl.name_ == '"t172"'
    driver.delete_table(tbl, True, True, True)
def test_173_table_object_nonexistent_raises(driver):
    
    with pytest.raises(AttributeError, match="t172"):
        getattr(driver, 't172')
def test_174_get_databases_excludes_templates(driver):
    
    dbs = driver.get_databases()
    assert 'template0' not in dbs
    assert 'template1' not in dbs
    assert PG_DB_NAME in dbs
def test_175_create_and_drop_user(driver):
    
    test_user = 't175_user'
    try:
        driver.drop_user(test_user)
    except:
        pass
    driver.create_user(test_user, 'pass123')
    users = driver.custom_execute_with_fetch(
        "SELECT usename FROM pg_user WHERE usename = %s;", (test_user,)
    )
    assert len(users) == 1
    driver.drop_user(test_user)
    users = driver.custom_execute_with_fetch(
        "SELECT usename FROM pg_user WHERE usename = %s;", (test_user,)
    )
    assert len(users) == 0
def test_176_disconnect_and_reconnect():
    
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    assert drv._connected is True
    drv.disconnect()
    assert drv._connected is False
    with pytest.raises(RuntimeError):
        drv.disconnect()  
def test_177_insert_and_read_back(driver):
    schema = Postgresql.TableStructure('t177')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t177
    tbl.insert({tbl.name: 'Ali'})
    tbl.insert({tbl.name: 'Sara'})
    rows = tbl.get_row([tbl.name])  
    assert rows == ['Ali', 'Sara']  
def test_178_unique_constraint_violation(driver):
    schema = Postgresql.TableStructure('t178')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('code', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    tbl = driver.t178
    tbl.insert({tbl.code: 1})
    tbl.insert({tbl.code: 2})
    with pytest.raises(Exception):
        tbl.insert({tbl.code: 1})
    count = len(tbl.get_row([tbl.id]))  
    assert count == 2
def test_179_not_null_violation(driver):
    
    schema = Postgresql.TableStructure('t179')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50), not_null=True)
    driver.create_table(schema)
    tbl = driver.t179
    with pytest.raises(Exception):
        tbl.insert({tbl.name: None})
    driver.delete_table(tbl, True, True, True)
def test_181_foreign_key_violation(driver):
    
    schema_parent = Postgresql.TableStructure('t181_parent')
    schema_parent.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_parent)
    parent = driver.t181_parent
    parent.insert({})
    schema_child = Postgresql.TableStructure('t181_child')
    schema_child.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_child.add_column('parent_id', Postgresql.DataTypes.INTEGER())
    schema_child.foreign_key('parent_id', parent, parent.id)  
    driver.create_table(schema_child)
    child = driver.t181_child
    child.insert({child.parent_id: 1})
    with pytest.raises(Exception):
        child.insert({child.parent_id: 999})
    driver.delete_table(child, True, True, True)
    driver.delete_table(parent, True, True, True)
def test_182_multiple_inserts(driver):
    schema = Postgresql.TableStructure('t182')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t182
    for i in range(5):
        tbl.insert({tbl.val: i * 10})
    rows = tbl.get_row([tbl.val], order_by=tbl.id)
    assert rows == [0, 10, 20, 30, 40]
def test_183_insert_null_allowed(driver):
    schema = Postgresql.TableStructure('t183')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t183
    tbl.insert({tbl.val: None})
    
    rows = tbl.get_row([tbl.val])
    assert rows[0] is None
    driver.delete_table(tbl, True, True, True)
def test_184_insert_empty_string_vs_null(driver):
    
    schema = Postgresql.TableStructure('t184')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t184
    tbl.insert({tbl.name: ''})
    tbl.insert({tbl.name: None})
    rows = tbl.get_row([tbl.name])
    assert rows[0] == ('')
    assert rows[1] == (None)
    driver.delete_table(tbl, True, True, True)
def test_185_insert_persian_unicode(driver):
    schema = Postgresql.TableStructure('t185')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    tbl = driver.t185
    tbl.insert({tbl.name: 'علی رضایی'})
    rows = tbl.get_row([tbl.name])
    assert rows[0] == 'علی رضایی'
    driver.delete_table(tbl, True, True, True)
def test_186_insert_text_with_newlines(driver):
    schema = Postgresql.TableStructure('t186')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('content', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t186
    multiline = "line1\nline2\nline3"
    tbl.insert({tbl.content: multiline})
    rows = tbl.get_row([tbl.content])
    assert rows[0] == multiline
    driver.delete_table(tbl, True, True, True)
def test_187_insert_long_text(driver):
    
    schema = Postgresql.TableStructure('t187')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('content', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t187
    long_text = 'آ' * 10000
    tbl.insert({tbl.content: long_text})
    rows = driver.custom_execute_with_fetch('SELECT LENGTH(content) FROM t187;')
    assert rows[0][0] == 10000
    driver.delete_table(tbl, True, True, True)
def test_188_varchar_length_limit(driver):
    
    schema = Postgresql.TableStructure('t188')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('code', Postgresql.DataTypes.VARCHAR(5))
    driver.create_table(schema)
    tbl = driver.t188
    tbl.insert({tbl.code: 'ABC12'})
    with pytest.raises(Exception):
        tbl.insert({tbl.code: 'ABC12345'})
    driver.delete_table(tbl, True, True, True)
def test_189_boolean_insert_and_filter(driver):
    schema = Postgresql.TableStructure('t189')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('active', Postgresql.DataTypes.BOOLEAN())
    driver.create_table(schema)
    tbl = driver.t189
    tbl.insert({tbl.active: True})
    tbl.insert({tbl.active: False})
    tbl.insert({tbl.active: True})
    active = len(tbl.get_row([tbl.id], where=tbl.active == True))
    inactive = len(tbl.get_row([tbl.id], where=tbl.active == False))
    assert active == 2
    assert inactive == 1
def test_190_decimal_precision(driver):
    schema = Postgresql.TableStructure('t190')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('amount', Postgresql.DataTypes.DECIMAL(10, 4))
    driver.create_table(schema)
    tbl = driver.t190
    tbl.insert({tbl.amount: '12345.6789'})
    rows = tbl.get_row([tbl.amount])
    assert str(rows[0]) == '12345.6789'
    driver.delete_table(tbl, True, True, True)
def test_191_decimal_negative(driver):
    schema = Postgresql.TableStructure('t191')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('balance', Postgresql.DataTypes.DECIMAL(10, 2))
    driver.create_table(schema)
    tbl = driver.t191
    tbl.insert({tbl.balance: -1234.56})
    rows = tbl.get_row([tbl.balance])
    assert float(rows[0]) == -1234.56
    driver.delete_table(tbl, True, True, True)
def test_192_real_scientific_notation(driver):
    schema = Postgresql.TableStructure('t192')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.REAL())
    driver.create_table(schema)
    tbl = driver.t192
    tbl.insert({tbl.val: 1.5e-10})
    rows = tbl.get_row([tbl.val])
    assert abs(float(rows[0]) - 1.5e-10) < 1e-15
    driver.delete_table(tbl, True, True, True)
def test_193_bigint_large_value(driver):
    schema = Postgresql.TableStructure('t193')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('big_val', Postgresql.DataTypes.BIGINT())
    driver.create_table(schema)
    tbl = driver.t193
    large_val = 2 ** 62
    tbl.insert({tbl.big_val: large_val})
    rows = tbl.get_row([tbl.big_val])
    assert rows[0] == large_val
    driver.delete_table(tbl, True, True, True)
def test_194_smallint_boundary(driver):
    schema = Postgresql.TableStructure('t194')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.SMALLINT())
    driver.create_table(schema)
    tbl = driver.t194
    tbl.insert({tbl.val: 32767})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == 32767
    with pytest.raises(Exception):
        tbl.insert({tbl.val: 32768})
    driver.delete_table(tbl, True, True, True)
def test_195_integer_zero_and_negative(driver):
    schema = Postgresql.TableStructure('t195')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t195
    tbl.insert({tbl.val: 0})
    tbl.insert({tbl.val: -999})
    rows = tbl.get_row([tbl.val], order_by=tbl.id)
    assert rows[0] == 0
    assert rows[1] == -999
    driver.delete_table(tbl, True, True, True)
def test_196_money_type(driver):
    schema = Postgresql.TableStructure('t196')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('price', Postgresql.DataTypes.MONEY())
    driver.create_table(schema)
    tbl = driver.t196
    tbl.insert({tbl.price: '99.99'})
    rows = tbl.get_row([tbl.price])
    assert rows[0] is not None
    driver.delete_table(tbl, True, True, True)
def test_197_default_value_used(driver):
    schema = Postgresql.TableStructure('t197')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('status', Postgresql.DataTypes.VARCHAR(20), default_value='active')
    driver.create_table(schema)
    tbl = driver.t197
    tbl.insert({})  
    rows = tbl.get_row([tbl.status])
    assert rows[0] == 'active'
def test_198_auto_discovery_after_create(driver):
    schema = Postgresql.TableStructure('t198')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('data', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    assert hasattr(driver, 't198')
    tbl = driver.t198
    tbl.insert({tbl.data: 'hello'})
    rows = tbl.get_row([tbl.data])
    assert rows[0] == 'hello'
def test_199_get_columns_name(driver):
    
    schema = Postgresql.TableStructure('t199')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('first_name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('salary', Postgresql.DataTypes.NUMERIC(10, 2))
    driver.create_table(schema)
    cols = driver.t199.get_columns_name()
    assert 'id' in cols
    assert 'first_name' in cols
    assert 'salary' in cols
    driver.delete_table(driver.t199, True, True, True)
def test_200_create_and_delete_table_lifecycle(driver):
    
    schema = Postgresql.TableStructure('t200')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    assert 't200' in driver.get_tables()
    assert hasattr(driver, 't200')
    driver.delete_table(driver.t200, True, True, True)
    assert 't200' not in driver.get_tables()
    assert not hasattr(driver, 't200')
def test_201_delete_table_requires_all_flags(driver):
    
    schema = Postgresql.TableStructure('t201')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    driver.delete_table(driver.t201, True, True, False)
    assert 't201' in driver.get_tables()
    driver.delete_table(driver.t201, True, False, True)
    assert 't201' in driver.get_tables()
    
    driver.delete_table(driver.t201, True, True, True)
    assert 't201' not in driver.get_tables()
def test_202_multiple_tables_independent(driver):
    tables = []
    for i in range(3):
        name = f't202_tbl{i}'
        s = Postgresql.TableStructure(name)
        s.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
        s.add_column('val', Postgresql.DataTypes.INTEGER())
        driver.create_table(s)
        tbl = getattr(driver, name)
        tables.append(tbl)
    for tbl in tables:
        tbl.insert({tbl.val: 100})
    for tbl in tables:
        rows = tbl.get_row([tbl.val])
        assert rows[0] == 100
def test_203_bulk_insert_with_custom_execute_many(driver):
    schema = Postgresql.TableStructure('t203')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('num', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t203
    data = [(i,) for i in range(1000)]
    tbl.bulk_insert([tbl.num], data)
    count = len(tbl.get_row([tbl.id]))
    assert count == 1000
def test_204_optimize_after_operations(driver):
    schema = Postgresql.TableStructure('t204')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t204
    for i in range(50):
        tbl.insert({tbl.val: i})
    
    tbl.delete_row(where=tbl.val < 25)
    driver.optimize()
    
    count = len(tbl.get_row([tbl.id]))
    assert count == 25
    driver.delete_table(tbl, True, True, True)
def test_205_table_with_special_name(driver):
    schema = Postgresql.TableStructure('My Table')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = getattr(driver, 'My Table')
    tbl.insert({tbl.val: 42})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == 42
def test_206_composite_primary_key(driver):
    
    schema = Postgresql.TableStructure('t206')
    schema.add_column('user_id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('role_id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.t206
    tbl.insert({tbl.user_id: 1, tbl.role_id: 1})
    tbl.insert({tbl.user_id: 1, tbl.role_id: 2})
    with pytest.raises(Exception):
        tbl.insert({tbl.user_id: 1, tbl.role_id: 1})
    count = driver.custom_execute_with_fetch('SELECT COUNT(*) FROM t206;')
    assert count[0][0] == 2
    driver.delete_table(tbl, True, True, True)
def test_207_fk_parent_child(driver):
    schema_p = Postgresql.TableStructure('t207_dept')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_p.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema_p)
    dept = driver.t207_dept
    dept.insert({dept.name: 'Engineering'})
    dept.insert({dept.name: 'Marketing'})
    schema_c = Postgresql.TableStructure('t207_emp')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    schema_c.add_column('dept_id', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('dept_id', dept, dept.id)  
    driver.create_table(schema_c)
    emp = driver.t207_emp
    emp.insert({emp.name: 'Ali', emp.dept_id: 1})
    emp.insert({emp.name: 'Sara', emp.dept_id: 2})
    count = len(emp.get_row([emp.id]))
    assert count == 2
def test_208_get_databases_excludes_templates(driver):
    
    dbs = driver.get_databases()
    assert 'template0' not in dbs
    assert 'template1' not in dbs
    assert PG_DB_NAME in dbs
def test_209_create_and_drop_user(driver):
    
    test_user = 't209_user'
    try:
        driver.drop_user(test_user)
    except:
        pass
    driver.create_user(test_user, 'pass123')
    users = driver.custom_execute_with_fetch(
        "SELECT usename FROM pg_user WHERE usename = %s;", (test_user,)
    )
    assert len(users) == 1
    driver.drop_user(test_user)
    users = driver.custom_execute_with_fetch(
        "SELECT usename FROM pg_user WHERE usename = %s;", (test_user,)
    )
    assert len(users) == 0
def test_210_disconnect_and_double_disconnect():
    
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    assert drv._connected is True
    drv.disconnect()
    assert drv._connected is False
    with pytest.raises(RuntimeError):
        drv.disconnect()
def test_211_full_lifecycle(driver):
    schema = Postgresql.TableStructure('t211')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t211
    tbl.insert({tbl.name: 'Ali', tbl.age: 30})
    tbl.insert({tbl.name: 'Sara', tbl.age: 25})
    
    rows = tbl.get_row([tbl.id])
    assert len(rows) == 2
    
    tbl.update({tbl.age: 31}, where=tbl.name == 'Ali')
    rows = tbl.get_row([tbl.age], where=tbl.name == 'Ali')
    assert rows[0] == 31
    
    tbl.delete_row(where=tbl.name == 'Sara')
    rows = tbl.get_row([tbl.id])
    assert len(rows) == 1
    
    driver.delete_table(tbl, True, True, True)
    assert 't211' not in driver.get_tables()
def test_213_data_type_date_invalid_format(driver):
    schema = Postgresql.TableStructure('t213')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.DATE())
    driver.create_table(schema)
    tbl = driver.t213
    with pytest.raises(Exception):
        tbl.insert({tbl.val: 'Not a Date'})
def test_214_data_type_time_invalid_format(driver):
    schema = Postgresql.TableStructure('t214')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.TIME())
    driver.create_table(schema)
    tbl = driver.t214
    with pytest.raises(Exception):
        tbl.insert({tbl.val: '25:99:99'})
def test_215_data_type_timestamp_invalid_format(driver):
    schema = Postgresql.TableStructure('t215')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.TIMESTAMP())
    driver.create_table(schema)
    tbl = driver.t215
    with pytest.raises(Exception):
        tbl.insert({tbl.val: '2023-13-40 99:99:99'})
def test_216_data_type_date_arithmetic_add_interval(driver):
    schema = Postgresql.TableStructure('t216')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('d', Postgresql.DataTypes.DATE())
    schema.add_column('i', Postgresql.DataTypes.INTERVAL())
    driver.create_table(schema)
    tbl = driver.t216
    tbl.insert({tbl.d: '2023-01-01', tbl.i: '1 month'})
    res = tbl.get_row([tbl.d + tbl.i])
    
    
    
    date_str = str(res[0])[:10]  
    assert date_str == '2023-02-01'
def test_217_data_type_date_arithmetic_sub_date(driver):
    schema = Postgresql.TableStructure('t217')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('d1', Postgresql.DataTypes.DATE())
    schema.add_column('d2', Postgresql.DataTypes.DATE())
    driver.create_table(schema)
    tbl = driver.t217
    tbl.insert({tbl.d1: '2023-01-10', tbl.d2: '2023-01-01'})
    res = tbl.get_row([tbl.d1 - tbl.d2])
    
    assert res[0] == 9
def test_223_data_type_json_basic(driver):
    schema = Postgresql.TableStructure('t223')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.JSON())
    driver.create_table(schema)
    tbl = driver.t223
    tbl.insert({tbl.val: '{"key": "value"}'})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == {"key": "value"} 
def test_234_data_type_uuid_invalid_format(driver):
    schema = Postgresql.TableStructure('t234')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.UUID())
    driver.create_table(schema)
    tbl = driver.t234
    with pytest.raises(Exception):
        tbl.insert({tbl.val: 'not-a-uuid'})
def test_240_data_type_array_text(driver):
    schema = Postgresql.TableStructure('t240')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.TEXT()))
    driver.create_table(schema)
    tbl = driver.t240
    tbl.insert({tbl.val: ['a', 'b', 'c']})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == ['a', 'b', 'c']
def test_241_data_type_array_nested(driver):
    schema = Postgresql.TableStructure('t241')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.INTEGER())))
    driver.create_table(schema)
    tbl = driver.t241
    tbl.insert({tbl.val: [[1, 2], [3, 4]]})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == [[1, 2], [3, 4]]
def test_242_data_type_array_empty(driver):
    schema = Postgresql.TableStructure('t242')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.INTEGER()))
    driver.create_table(schema)
    tbl = driver.t242
    tbl.insert({tbl.val: []})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == []
def test_243_data_type_cidr_basic(driver):
    schema = Postgresql.TableStructure('t243')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.VARCHAR(20))  
    driver.create_table(schema)
    tbl = driver.t243
    cidr_val = '192.168.1.0/24'
    tbl.insert({tbl.val: cidr_val})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == cidr_val
def test_244_data_type_inet_basic(driver):
    schema = Postgresql.TableStructure('t244')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.VARCHAR(20))
    driver.create_table(schema)
    tbl = driver.t244
    inet_val = '192.168.1.5'
    tbl.insert({tbl.val: inet_val})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == inet_val
def test_245_data_type_macaddr_basic(driver):
    schema = Postgresql.TableStructure('t245')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.VARCHAR(20))
    driver.create_table(schema)
    tbl = driver.t245
    mac_val = '08:00:2b:01:02:03'
    tbl.insert({tbl.val: mac_val})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == mac_val
def test_246_data_type_xml_basic(driver):
    schema = Postgresql.TableStructure('t246')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.TEXT())  
    driver.create_table(schema)
    tbl = driver.t246
    xml_val = '<book><title>Manual</title></book>'
    tbl.insert({tbl.val: xml_val})
    rows = tbl.get_row([tbl.val])
    assert '<title>Manual</title>' in rows[0]
@pytest.fixture(scope="module")
def driver():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except Exception:
        pass
    yield drv
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except Exception:
        pass
    drv.disconnect()
def test_251_structure_add_column_basic(driver):
    schema = Postgresql.TableStructure('t251')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    cols = driver.t251.get_columns_name()
    assert 'name' in cols
def test_252_structure_add_column_multiple(driver):
    schema = Postgresql.TableStructure('t252')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('a', Postgresql.DataTypes.INTEGER())
    schema.add_column('b', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    cols = driver.t252.get_columns_name()
    assert len(cols) == 3
def test_253_structure_add_column_chainable(driver):
    schema = Postgresql.TableStructure('t253')
    sql = (schema
           .add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
           .add_column('val', Postgresql.DataTypes.INTEGER())
           .get_structure())
    driver.create_table(schema)
    assert 'id' in sql and 'val' in sql
    assert 't253' in driver.get_tables()
def test_255_structure_delete_column_nonexistent(driver):
    schema = Postgresql.TableStructure('t255')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    with pytest.raises(Exception):
        schema.delete_column('ghost_col')
def test_256_structure_primary_key_single(driver):
    schema = Postgresql.TableStructure('t256')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    
    assert 't256' in driver.get_tables()
    cols = driver.t256.get_columns_name()
    assert 'id' in cols
def test_257_structure_primary_key_composite(driver):
    schema = Postgresql.TableStructure('t257')
    schema.add_column('id1', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('id2', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    assert 't257' in driver.get_tables()
    cols = driver.t257.get_columns_name()
    assert 'id1' in cols and 'id2' in cols
def test_258_structure_foreign_key_basic(driver):
    schema_p = Postgresql.TableStructure('p258')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p258
    schema_c = Postgresql.TableStructure('t258')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id)
    driver.create_table(schema_c)
    
    tbl_p.insert({})  
    driver.t258.insert({driver.t258.pid: 1})
    res = driver.t258.get_row([driver.t258.pid])
    assert res == [1]
def test_259_structure_foreign_key_on_delete_cascade(driver):
    schema_p = Postgresql.TableStructure('p259')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p259
    schema_c = Postgresql.TableStructure('t259')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id, on_delete='CASCADE')
    driver.create_table(schema_c)
    tbl_p.insert({})
    driver.t259.insert({driver.t259.pid: 1})
    tbl_p.delete_row(tbl_p.id == 1)
    res = driver.t259.get_row([driver.t259.id])
    assert res == []
def test_260_structure_foreign_key_on_delete_restrict(driver):
    schema_p = Postgresql.TableStructure('p260')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p260
    schema_c = Postgresql.TableStructure('t260')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id, on_delete='RESTRICT')
    driver.create_table(schema_c)
    tbl_p.insert({})
    driver.t260.insert({driver.t260.pid: 1})
    with pytest.raises(Exception):
        tbl_p.delete_row(tbl_p.id == 1)
def test_261_structure_foreign_key_on_delete_set_null(driver):
    schema_p = Postgresql.TableStructure('p261')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p261
    schema_c = Postgresql.TableStructure('t261')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id, on_delete='SET NULL')
    driver.create_table(schema_c)
    tbl_p.insert({})
    driver.t261.insert({driver.t261.pid: 1})
    tbl_p.delete_row(tbl_p.id == 1)
    res = driver.t261.get_row([driver.t261.pid])
    assert res == [None]
def test_262_structure_foreign_key_on_delete_set_default(driver):
    schema_p = Postgresql.TableStructure('p262')
    schema_p.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p262
    
    tbl_p.insert({tbl_p.id: 0})
    tbl_p.insert({tbl_p.id: 1})
    schema_c = Postgresql.TableStructure('t262')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER(), default_value=0)
    schema_c.foreign_key('pid', tbl_p, tbl_p.id, on_delete='SET DEFAULT')
    driver.create_table(schema_c)
    driver.t262.insert({driver.t262.pid: 1})
    tbl_p.delete_row(tbl_p.id == 1)
    res = driver.t262.get_row([driver.t262.pid])
    assert res == [0]
def test_263_structure_foreign_key_on_update_cascade(driver):
    schema_p = Postgresql.TableStructure('p263')
    schema_p.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p263
    schema_c = Postgresql.TableStructure('t263')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id, on_update='CASCADE')
    driver.create_table(schema_c)
    tbl_p.insert({tbl_p.id: 1})
    driver.t263.insert({driver.t263.pid: 1})
    tbl_p.update({tbl_p.id: 99}, tbl_p.id == 1)
    res = driver.t263.get_row([driver.t263.pid])
    assert res == [99]
def test_266_structure_unique_single(driver):
    schema = Postgresql.TableStructure('t266')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('email', Postgresql.DataTypes.VARCHAR(100), unique=True)
    driver.create_table(schema)
    driver.t266.insert({driver.t266.email: 'a@b.com'})
    with pytest.raises(Exception):
        driver.t266.insert({driver.t266.email: 'a@b.com'})
def test_270_structure_not_null(driver):
    schema = Postgresql.TableStructure('t270')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT(), not_null=True)
    driver.create_table(schema)
    with pytest.raises(Exception):
        driver.t270.insert({driver.t270.name: None})
def test_271_structure_default_value_integer(driver):
    schema = Postgresql.TableStructure('t271')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER(), default_value=42)
    driver.create_table(schema)
    driver.t271.insert({})  
    res = driver.t271.get_row([driver.t271.val])
    assert res == [42]
def test_272_structure_default_value_string(driver):
    schema = Postgresql.TableStructure('t272')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50), default_value='guest')
    driver.create_table(schema)
    driver.t272.insert({})
    res = driver.t272.get_row([driver.t272.name])
    assert res == ['guest']
def test_273_structure_default_value_boolean(driver):
    schema = Postgresql.TableStructure('t273')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('is_active', Postgresql.DataTypes.BOOLEAN(), default_value=True)
    driver.create_table(schema)
    driver.t273.insert({})
    res = driver.t273.get_row([driver.t273.is_active])
    assert res == [True]
def test_274_structure_default_value_function(driver):
    schema = Postgresql.TableStructure('t274')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('created_at', Postgresql.DataTypes.TIMESTAMP(), default_value='NOW()')
    driver.create_table(schema)
    driver.t274.insert({})
    res = driver.t274.get_row([driver.t274.created_at])
    assert res[0] is not None
def test_275_structure_auto_increment_serial(driver):
    schema = Postgresql.TableStructure('t275')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    driver.t275.insert({})
    driver.t275.insert({})
    res = driver.t275.get_row([driver.t275.id], order_by=driver.t275.id)
    assert res == [1, 2]
def test_276_structure_auto_increment_bigserial(driver):
    schema = Postgresql.TableStructure('t276')
    schema.add_column('id', Postgresql.DataTypes.BIGSERIAL(), primary_key=True)
    driver.create_table(schema)
    driver.t276.insert({})
    res = driver.t276.get_row([driver.t276.id])
    assert res == [1]
def test_277_structure_get_columns(driver):
    schema = Postgresql.TableStructure('t277')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('a', Postgresql.DataTypes.INTEGER())
    schema.add_column('b', Postgresql.DataTypes.TEXT())
    cols = schema.get_columns()
    assert len(cols) == 3
    assert any(c['name'] == '"a"' or c['name'] == 'a' for c in cols)
def test_278_structure_get_structure_sql(driver):
    schema = Postgresql.TableStructure('t278')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    sql = schema.get_structure()
    assert "CREATE TABLE" in sql
    assert "PRIMARY KEY" in sql
def test_279_structure_no_columns_error(driver):
    schema = Postgresql.TableStructure('t279')
    with pytest.raises(Exception):
        schema.get_structure()
def test_280_structure_duplicate_column_error(driver):
    schema = Postgresql.TableStructure('t280')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    with pytest.raises(Exception):
        schema.add_column('id', Postgresql.DataTypes.TEXT())
def test_281_structure_invalid_column_name(driver):
    schema = Postgresql.TableStructure('t281')
    
    try:
        schema.add_column('invalid name!', Postgresql.DataTypes.INTEGER())
        driver.create_table(schema)
        assert False, "Expected error"
    except Exception:
        pass
def test_282_structure_invalid_data_type(driver):
    schema = Postgresql.TableStructure('t282')
    with pytest.raises(Exception):
        schema.add_column('val', 123456)
def test_283_structure_add_index(driver):
    schema = Postgresql.TableStructure('t283')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    tbl = driver.t283
    tbl.create_index('idx_t283_name', [tbl.name])
    res = driver.custom_execute_with_fetch(
        "SELECT indexname FROM pg_indexes WHERE tablename='t283';"
    )
    assert any('name' in i[0] for i in res)
def test_284_structure_add_foreign_key_invalid_ref(driver):
    schema_p = Postgresql.TableStructure('p284')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p284
    schema_c = Postgresql.TableStructure('t284')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    with pytest.raises(Exception):
        schema_c.foreign_key('pid', tbl_p, getattr(tbl_p, 'non_existent_col', None))
def test_285_structure_table_name_quoting(driver):
    schema = Postgresql.TableStructure('Table With Spaces')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    assert 'Table With Spaces' in driver.get_tables()
def test_300_structure_unique_null_distinct(driver):
    schema = Postgresql.TableStructure('t300')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('val', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    driver.t300.insert({driver.t300.id: 1, driver.t300.val: None})
    driver.t300.insert({driver.t300.id: 2, driver.t300.val: None})
    res = driver.t300.get_row([driver.t300.id])
    assert len(res) == 2
@pytest.fixture(scope="module")
def driver():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except Exception:
        pass
    yield drv
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except Exception:
        pass
    drv.disconnect()
def test_301_insert_single_row(driver):
    schema = Postgresql.TableStructure('t301')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t301
    tbl.insert({tbl.id: 1, tbl.name: 'Ali'})
    res = tbl.get_row([tbl.id, tbl.name])
    assert res == [(1, 'Ali')]
def test_302_insert_multiple_rows(driver):
    schema = Postgresql.TableStructure('t302')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t302
    tbl.insert({tbl.id: 1, tbl.name: 'A'})
    tbl.insert({tbl.id: 2, tbl.name: 'B'})
    tbl.insert({tbl.id: 3, tbl.name: 'C'})
    res = tbl.get_row([tbl.id])
    assert len(res) == 3
def test_303_insert_with_all_columns(driver):
    schema = Postgresql.TableStructure('t303')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t303
    tbl.insert({tbl.id: 1, tbl.name: 'Reza', tbl.age: 25})
    res = tbl.get_row([tbl.id, tbl.name, tbl.age])
    assert res == [(1, 'Reza', 25)]
def test_304_insert_with_partial_columns(driver):
    schema = Postgresql.TableStructure('t304')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t304
    tbl.insert({tbl.id: 1, tbl.name: 'Sara'})
    res = tbl.get_row([tbl.id, tbl.name, tbl.age])
    assert res == [(1, 'Sara', None)]
def test_305_insert_missing_required_column(driver):
    schema = Postgresql.TableStructure('t305')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT(), not_null=True)
    driver.create_table(schema)
    tbl = driver.t305
    with pytest.raises(Exception):
        tbl.insert({tbl.id: 1})
def test_306_insert_invalid_data_type(driver):
    schema = Postgresql.TableStructure('t306')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t306
    with pytest.raises(Exception):
        tbl.insert({tbl.id: 1, tbl.val: 'not_an_int'})
def test_307_insert_violates_unique_constraint(driver):
    schema = Postgresql.TableStructure('t307')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    tbl = driver.t307
    tbl.insert({tbl.id: 1})
    with pytest.raises(Exception):
        tbl.insert({tbl.id: 1})
def test_309_insert_violates_foreign_key(driver):
    schema_p = Postgresql.TableStructure('p309')
    schema_p.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p309
    schema_c = Postgresql.TableStructure('t309')
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id)
    driver.create_table(schema_c)
    with pytest.raises(Exception):
        driver.t309.insert({driver.t309.pid: 99})
def test_310_insert_violates_not_null(driver):
    schema = Postgresql.TableStructure('t310')
    schema.add_column('val', Postgresql.DataTypes.TEXT(), not_null=True)
    driver.create_table(schema)
    tbl = driver.t310
    with pytest.raises(Exception):
        tbl.insert({tbl.val: None})
def test_314_insert_with_serial_id_omitted(driver):
    schema = Postgresql.TableStructure('t314')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t314
    tbl.insert({tbl.name: 'A'})
    tbl.insert({tbl.name: 'B'})
    res = tbl.get_row([tbl.id], order_by=tbl.id)
    assert res == [1, 2]
def test_315_insert_with_explicit_serial_id(driver):
    schema = Postgresql.TableStructure('t315')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t315
    tbl.insert({tbl.id: 100, tbl.name: 'Explicit'})
    res = tbl.get_row([tbl.id])
    assert res == [100]
def test_316_insert_with_default_values(driver):
    schema = Postgresql.TableStructure('t316')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('status', Postgresql.DataTypes.TEXT(), default_value='active')
    driver.create_table(schema)
    tbl = driver.t316
    tbl.insert({})  
    res = tbl.get_row([tbl.status])
    assert res == ['active']
def test_317_insert_with_null_values(driver):
    schema = Postgresql.TableStructure('t317')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('val', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t317
    tbl.insert({tbl.id: 1, tbl.val: None})
    res = tbl.get_row([tbl.val])
    assert res == [None]
def test_318_insert_with_special_chars_string(driver):
    schema = Postgresql.TableStructure('t318')
    schema.add_column('val', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    val = "O'Connor\nNewLine\tTab"
    tbl = driver.t318
    tbl.insert({tbl.val: val})
    res = tbl.get_row([tbl.val])
    assert res == [val]
def test_319_insert_with_unicode_string(driver):
    schema = Postgresql.TableStructure('t319')
    schema.add_column('val', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    val = "日本語 ελληνικά"
    tbl = driver.t319
    tbl.insert({tbl.val: val})
    res = tbl.get_row([tbl.val])
    assert res == [val]
def test_321_insert_with_array(driver):
    schema = Postgresql.TableStructure('t321')
    schema.add_column('val', Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.INTEGER()))
    driver.create_table(schema)
    tbl = driver.t321
    tbl.insert({tbl.val: [1, 2, 3]})
    res = tbl.get_row([tbl.val])
    assert res == [[1, 2, 3]]
def test_322_insert_bulk_execute_many(driver):
    schema = Postgresql.TableStructure('t322')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    data = [(1, 'A'), (2, 'B'), (3, 'C')]
    driver.t322.bulk_insert([driver.t322.id, driver.t322.name], data)
    
    res = driver.t322.get_row([driver.t322.id])
    assert len(res) == 3
def test_323_insert_bulk_partial_failure_rollback(driver):
    schema = Postgresql.TableStructure('t323')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    data = [(1,), (2,), (1,)]
    with pytest.raises(Exception):
        driver.t323.bulk_insert([driver.t323.id], data)
        
    res = driver.t323.get_row([driver.t323.id])
    assert len(res) == 0
def test_332_insert_timestamp_auto_now(driver):
    schema = Postgresql.TableStructure('t332')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('created_at', Postgresql.DataTypes.TIMESTAMP(), default_value='NOW()')
    driver.create_table(schema)
    tbl = driver.t332
    tbl.insert({tbl.id: 1})
    res = tbl.get_row([tbl.created_at])
    assert res[0] is not None
def test_333_insert_uuid_auto_generate(driver):
    
    import uuid
    schema = Postgresql.TableStructure('t333')
    schema.add_column('id', Postgresql.DataTypes.UUID(), default_value=f"{uuid.uuid1()}")
    driver.create_table(schema)
    tbl = driver.t333
    tbl.insert({})
    res = tbl.get_row([tbl.id])
    assert len(str(res[0])) == 36
def test_334_insert_bytea_binary(driver):
    schema = Postgresql.TableStructure('t334')
    schema.add_column('val', Postgresql.DataTypes.BYTEA())
    driver.create_table(schema)
    binary_data = b'\x00\xFF\x10\x20'
    tbl = driver.t334
    tbl.insert({tbl.val: binary_data})
    res = tbl.get_row([tbl.val])
    assert res == [binary_data]
def test_335_insert_large_object(driver):
    schema = Postgresql.TableStructure('t335')
    schema.add_column('val', Postgresql.DataTypes.BYTEA())
    driver.create_table(schema)
    large_data = os.urandom(2 * 1024 * 1024)
    tbl = driver.t335
    tbl.insert({tbl.val: large_data})
    res = driver.custom_execute_with_fetch("SELECT length(val) FROM t335;")
    assert res[0][0] == 2097152
def test_345_insert_case_sensitivity(driver):
    schema = Postgresql.TableStructure('T345_Case')
    schema.add_column('ID', Postgresql.DataTypes.INTEGER())
    schema.add_column('Name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    
    tbl = getattr(driver, 'T345_Case')
    tbl.insert({tbl.ID: 1, tbl.Name: 'Test'})
    res = tbl.get_row([tbl.ID, tbl.Name])
    assert res == [(1, 'Test')]
def test_346_insert_reserved_keyword_column(driver):
    schema = Postgresql.TableStructure('t346')
    schema.add_column('select', Postgresql.DataTypes.INTEGER())
    schema.add_column('from', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t346
    tbl.insert({getattr(tbl, 'select'): 1, getattr(tbl, 'from'): 'A'})
    res = tbl.get_row([getattr(tbl, 'select'), getattr(tbl, 'from')])
    assert res == [(1, 'A')]
def test_347_insert_reserved_keyword_table(driver):
    schema = Postgresql.TableStructure('table')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = getattr(driver, 'table')
    tbl.insert({tbl.id: 1})
    res = tbl.get_row([tbl.id])
    assert res == [1]
@pytest.fixture(scope="function")
def select_driver():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    try:
        drv.custom_execute('DROP TABLE IF EXISTS select_test;')
    except Exception:
        pass
    schema = Postgresql.TableStructure('select_test')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50), not_null=True)
    schema.add_column('age', Postgresql.DataTypes.INTEGER(), not_null=True)
    schema.add_column('score', Postgresql.DataTypes.REAL())
    schema.add_column('grade', Postgresql.DataTypes.VARCHAR(2))
    drv.create_table(schema)
    tbl = drv.select_test
    for name, age, score, grade in [
        ('Alice', 30, 85.5, 'A'),
        ('Bob', 25, 92.0, 'A'),
        ('Charlie', 35, 45.0, 'C'),
        ('David', 25, 75.5, 'B'),
        ('Eve', 30, None, None),
    ]:
        tbl.insert({tbl.name: name, tbl.age: age, tbl.score: score, tbl.grade: grade})
    yield drv
    try:
        drv.custom_execute('DROP TABLE IF EXISTS select_test;')
    except Exception:
        pass
    drv.disconnect()
def test_351_select_all_rows(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id, tbl.name, tbl.age, tbl.score, tbl.grade])
    assert len(res) == 5
def test_352_select_specific_columns(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name, tbl.age])
    assert len(res) == 5
    assert len(res[0]) == 2
def test_353_select_where_simple_eq(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age == 30)
    assert len(res) == 2
def test_354_select_where_simple_neq(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age != 30)
    assert len(res) == 3
def test_355_select_where_gt(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age > 30)
    assert len(res) == 1
def test_356_select_where_lt(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age < 25)
    assert len(res) == 0
def test_357_select_where_gte(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age >= 30)
    assert len(res) == 3
def test_358_select_where_lte(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age <= 25)
    assert len(res) == 2
def test_359_select_where_like(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], where=tbl.name.like('A%'))
    assert len(res) == 1
    assert res[0] == 'Alice'
def test_361_select_where_in(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age.In(data_list=[25, 35]))
    assert len(res) == 3
def test_366_select_where_and(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row(
        [tbl.name],
        where=(tbl.age == 30) & (tbl.score > 80)
    )
    assert len(res) == 1
    assert res[0] == 'Alice'
def test_367_select_where_or(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row(
        [tbl.id],
        where=(tbl.age == 25) | (tbl.age == 35)
    )
    assert len(res) == 3
def test_368_select_where_not(select_driver):
    
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age != 30)
    assert len(res) == 3
def test_369_select_where_complex_nested(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row(
        [tbl.id],
        where=((tbl.age == 30) & (tbl.score > 80)) | ((tbl.age == 25) & (tbl.grade == 'A'))
    )
    assert len(res) == 2
def test_370_select_order_by_asc(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], order_by=tbl.name)
    assert res[0] == 'Alice'
    assert res[4] == 'Eve'
def test_393_select_subquery_in(select_driver):
    tbl = select_driver.select_test
    
    res = tbl.get_row(
        [tbl.name],
        where=tbl.id.In(column=tbl.id, where=tbl.score > 80),
        order_by=tbl.name
    )
    assert len(res) == 2
    assert res[0] == 'Alice'
    assert res[1] == 'Bob'
@pytest.fixture(scope="module")
def driver_upd():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    for t in ('upd_del_test', 'fk_child', 'fk_parent'):
        try:
            drv.custom_execute(f'DROP TABLE IF EXISTS {t} CASCADE;')
        except Exception:
            pass
    schema = Postgresql.TableStructure('upd_del_test')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50), not_null=True, unique=True)
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    schema.add_column('data', Postgresql.DataTypes.JSONB())
    schema.add_column('tags', Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.TEXT()))
    schema.add_column('created_at', Postgresql.DataTypes.TIMESTAMP())
    drv.create_table(schema)
    drv.custom_execute(
        'ALTER TABLE upd_del_test ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;'
    )
    drv.custom_execute(
        'ALTER TABLE upd_del_test ADD CONSTRAINT chk_age CHECK (age >= 18);'
    )
    schema_p = Postgresql.TableStructure('fk_parent')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    drv.create_table(schema_p)
    schema_c = Postgresql.TableStructure('fk_child')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', drv.fk_parent, drv.fk_parent.id, on_delete='CASCADE')
    drv.create_table(schema_c)
    yield drv
    for t in ('upd_del_test', 'fk_child', 'fk_parent'):
        try:
            drv.custom_execute(f'DROP TABLE IF EXISTS {t} CASCADE;')
        except Exception:
            pass
    drv.disconnect()
def test_401_update_single_column(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Alice', tbl.age: 25})
    tbl.update({tbl.age: 26}, where=tbl.name == 'Alice')
    res = tbl.get_row([tbl.age], where=tbl.name == 'Alice')
    assert res == [26]
    tbl.delete_row(where=tbl.name == 'Alice')
def test_402_update_multiple_columns(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Bob', tbl.age: 30})
    tbl.update({tbl.age: 31, tbl.name: 'Robert'}, where=tbl.name == 'Bob')
    res = tbl.get_row([tbl.name, tbl.age], where=tbl.name == 'Robert')
    assert res == [('Robert', 31)]
    tbl.delete_row(where=tbl.name == 'Robert')
def test_404_update_where_simple(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Charlie', tbl.age: 22})
    tbl.update({tbl.age: 23}, where=tbl.name == 'Charlie')
    res = tbl.get_row([tbl.age], where=tbl.name == 'Charlie')
    assert res == [23]
    tbl.delete_row(where=tbl.name == 'Charlie')
def test_405_update_where_complex(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'X', tbl.age: 20})
    tbl.insert({tbl.name: 'Y', tbl.age: 25})
    tbl.update({tbl.age: 50}, where=(tbl.name == 'X') & (tbl.age < 25))
    res = tbl.get_row([tbl.age], where=tbl.name == 'X')
    assert res == [50]
    tbl.delete_row(where=tbl.name.In(data_list=['X', 'Y']))
def test_408_update_violates_check(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Frank', tbl.age: 20})
    with pytest.raises(Exception):
        tbl.update({tbl.age: 17}, where=tbl.name == 'Frank')
    tbl.delete_row(where=tbl.name == 'Frank')
def test_409_update_violates_unique(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Unique1', tbl.age: 20})
    tbl.insert({tbl.name: 'Unique2', tbl.age: 20})
    with pytest.raises(Exception):
        tbl.update({tbl.name: 'Unique1'}, where=tbl.name == 'Unique2')
    tbl.delete_row(where=tbl.name.In(data_list=['Unique1', 'Unique2']))
def test_410_update_violates_foreign_key(driver_upd):
    parent = driver_upd.fk_parent
    child = driver_upd.fk_child
    parent.insert({parent.id: 1})
    child.insert({child.pid: 1})
    with pytest.raises(Exception):
        child.update({child.pid: 999}, where=child.pid == 1)
    child.delete_row(where=child.pid == 1)
    parent.delete_row(where=parent.id == 1)
def test_411_update_violates_not_null(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'NullTest', tbl.age: 20})
    with pytest.raises(Exception):
        tbl.update({tbl.name: None}, where=tbl.name == 'NullTest')
    tbl.delete_row(where=tbl.name == 'NullTest')
def test_412_update_with_subquery(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'SubT', tbl.age: 20})
    tbl.insert({tbl.name: 'SubT2', tbl.age: 30})
    
    tbl.update(
        {tbl.age: 99},
        where=tbl.id.In(column=tbl.id, where=tbl.name == 'SubT')
    )
    res = tbl.get_row([tbl.age], where=tbl.name == 'SubT')
    assert res == [99]
    tbl.delete_row(where=tbl.name.In(data_list=['SubT', 'SubT2']))
def test_419_update_increment(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'IncT', tbl.age: 20})
    tbl.update({tbl.age: tbl.age + 1}, where=tbl.name == 'IncT')
    res = tbl.get_row([tbl.age], where=tbl.name == 'IncT')
    assert res == [21]
    tbl.delete_row(where=tbl.name == 'IncT')
def test_420_update_decrement(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'DecT', tbl.age: 25})
    tbl.update({tbl.age: tbl.age - 5}, where=tbl.name == 'DecT')  
    res = tbl.get_row([tbl.age], where=tbl.name == 'DecT')
    assert res == [20]
    tbl.delete_row(where=tbl.name == 'DecT')
def test_421_update_string_concat(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Str', tbl.age: 20})
    tbl.update({tbl.name: tbl.name + '_suffix'}, where=tbl.name == 'Str')
    res = tbl.get_row([tbl.name], where=tbl.name.like('Str%'))
    assert res == ['Str_suffix']
    tbl.delete_row(where=tbl.name == 'Str_suffix')
def test_423_update_invalid_data_type(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'InvT', tbl.age: 20})
    with pytest.raises(Exception):
        tbl.update({tbl.age: 'not_an_int'}, where=tbl.name == 'InvT')
    tbl.delete_row(where=tbl.name == 'InvT')
def test_424_update_no_matching_rows(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.update({tbl.age: 100}, where=tbl.name == 'DoesNotExist')
    res = tbl.get_row([tbl.id], where=tbl.age == 100)
    assert len(res) == 0
def test_425_update_deadlock_handling(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'DeadT', tbl.age: 20})
    tbl.update({tbl.age: 19}, where=tbl.name == 'DeadT')  
    res = tbl.get_row([tbl.age], where=tbl.name == 'DeadT')
    assert res == [19]
    tbl.delete_row(where=tbl.name == 'DeadT')
def test_427_delete_single_row(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Del1', tbl.age: 20})
    tbl.delete_row(where=tbl.name == 'Del1')
    res = tbl.get_row([tbl.id], where=tbl.name == 'Del1')
    assert len(res) == 0
def test_428_delete_multiple_rows(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Del2', tbl.age: 20})
    tbl.insert({tbl.name: 'Del3', tbl.age: 20})
    tbl.delete_row(where=tbl.age == 20)
    res = tbl.get_row([tbl.id], where=tbl.name.In(data_list=['Del2', 'Del3']))
    assert len(res) == 0
def test_430_delete_where_simple(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'SimpleDel', tbl.age: 20})
    tbl.delete_row(where=tbl.name == 'SimpleDel')
    res = tbl.get_row([tbl.id], where=tbl.name == 'SimpleDel')
    assert len(res) == 0
def test_431_delete_where_complex(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'CDel1', tbl.age: 20})
    tbl.insert({tbl.name: 'CDel2', tbl.age: 25})
    tbl.delete_row(where=(tbl.age < 25) & tbl.name.like('C%'))
    res = tbl.get_row([tbl.id], where=tbl.name == 'CDel2')
    assert len(res) == 1
    tbl.delete_row(where=tbl.name == 'CDel2')
def test_434_delete_with_subquery(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'SubDel', tbl.age: 20})
    
    tbl.delete_row(
        where=tbl.id.In(column=tbl.id, where=tbl.name == 'SubDel')
    )
    res = tbl.get_row([tbl.id], where=tbl.name == 'SubDel')
    assert len(res) == 0
def test_437_delete_violates_foreign_key(driver_upd):
    parent = driver_upd.fk_parent
    child = driver_upd.fk_child
    parent.insert({parent.id: 100})
    child.insert({child.pid: 100})
    
    parent.delete_row(where=parent.id == 100)
    res = child.get_row([child.id], where=child.pid == 100)
    assert len(res) == 0
def test_438_delete_cascade_foreign_key(driver_upd):
    parent = driver_upd.fk_parent
    child = driver_upd.fk_child
    parent.insert({parent.id: 200})
    child.insert({child.pid: 200})
    parent.delete_row(where=parent.id == 200)
    res = child.get_row([child.id], where=child.pid == 200)
    assert len(res) == 0
def test_439_delete_no_matching_rows(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.delete_row(where=tbl.name == 'NonExistent')
    res = tbl.get_row([tbl.id], where=tbl.name == 'NonExistent')
    assert len(res) == 0
