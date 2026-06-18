<div align="center">

# Ormophine

**A fast, Pythonic ORM that gets out of your way.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Development-orange)](https://github.com/yourusername/ormophine)
[![PyPI](https://img.shields.io/badge/PyPI-Coming%20Soon-lightgrey?logo=pypi)](https://pypi.org/)

*Write database queries the way you think — in plain Python.*

</div>

---

## The Problem with Other ORMs

Most Python ORMs are either too verbose, too magical, or too slow. Compare fetching filtered rows with a popular ORM versus Ormophine:

**Other ORMs:**
```python
# SQLAlchemy (Core)
with engine.connect() as conn:
    stmt = select(users.c.phone, users.c.name, users.c.age).where(
        and_(
            users.c.age > 18,
            or_(
                users.c.phone.like('+98%'),
                func.substr(users.c.phone, 1, 3) == '+98'
            )
        )
    ).order_by(users.c.age)
    result = conn.execute(stmt).fetchall()
```

**Ormophine:**
```python
my_db = Ormophine.Sqlite('my_db')
users = my_db.users
phone, name, age = users.phone, users.name, users.age

users.get_row(
    [phone, name, age],
    where = (age > 18) & (phone.startswith('+98') | (phone[:3] == '+98')),
    order_by = age
)
```

Same result. No boilerplate. No imports. No ceremony.

---

## Why Ormophine?

- **Intuitive syntax** — columns behave like Python variables with full operator overloading (`>`, `&`, `|`, `+`, `[]`, `.startswith()`, etc.)
- **Fast** — built on a dedicated writer thread + read-only connection pool; no ORM overhead on the hot path
- **Multi-database** — one API across all supported backends
- **Connection pooling built-in** — parallel reads, serialized writes, no configuration needed
- **WAL mode support** (SQLite) — automatic checkpointing for maximum write throughput
- **Blocking and non-blocking** — fire-and-forget writes or wait for commit confirmation

---

## Supported Databases

| Database     | Status              |
|--------------|---------------------|
| SQLite       | ✅ Available         |
| MySQL        | 🔧 In development   |
| MariaDB      | 🔧 In development   |
| PostgreSQL   | 🔧 In development   |

The API is identical across all backends. Switch databases by changing one line.

---

## Benchmark Results

> 📊 **Coming soon** — benchmark results comparing Ormophine against SQLAlchemy, Tortoise ORM, and raw DB-API 2.0 will be published here across INSERT, SELECT, bulk operations, and concurrent read workloads.

---

## Quick Examples

### Connect and access tables

```python
import Ormophine

db = Ormophine.Sqlite('company.db')

# Tables and columns are discovered automatically
users   = db.users
orders  = db.orders
```

### Insert

```python
users.insert({
    users.name:  'Alice',
    users.email: 'alice@example.com',
    users.age:   30
})
```

### Select with conditions

```python
name, email, age = users.name, users.email, users.age

rows = users.get_row(
    [name, email],
    where   = (age >= 18) & name.startswith('A'),
    order_by = age
)
```

### Update

```python
users.update(
    update = {users.age: users.age + 1},
    where  = users.status == 'active'
)
```

### Bulk insert

```python
users.bulk_insert(
    columns   = [users.name, users.age],
    data_list = [['Bob', 25], ['Carol', 32], ['Dave', 28]]
)
```

### Joins

```python
from Ormophine import Join

result = orders.join(
    columns    = [users.name, orders.amount, orders.date],
    joins_list = [Join.Inner(users, users.id == orders.user_id)],
    where      = orders.amount > 100,
    order_by   = [orders.date]
)
```

### Batch operations (single transaction)

```python
(users.batch()
    .insert({users.name: 'Eve', users.age: 28})
    .update({users.age: 29}, where=users.name == 'Eve')
    .run())
```

### Schema management

```python
from Ormophine import TableStructure

schema = TableStructure('products', strict=True)
schema.add_column('id',    int,   primary_key=True)
schema.add_column('title', str,   not_null=True, unique=True)
schema.add_column('price', float, default_value=0.0)

products = db.create_table(schema)

# Add / rename / drop columns
products.add_column('stock', int, default_value=0, not_null=True)
products.rename_column(products.stock, 'inventory')
products.delete_column(products.inventory, True, True, True)
```

### WAL mode and performance tuning

```python
db.set_WAL_mode(True, wal_timer=60)   # automatic checkpoint every 60 s

db.SetPragma.synchronous('NORMAL')
db.SetPragma.cache_size(-4000)        # 4 MiB page cache
db.SetPragma.foreign_keys(True)
```

---

## Operator Reference

Ormophine columns support native Python expressions — all values are automatically parameterized.

| Expression                          | SQL equivalent                          |
|-------------------------------------|-----------------------------------------|
| `age > 18`                          | `age > 18`                              |
| `(age >= 18) & (age < 65)`          | `age >= 18 AND age < 65`               |
| `status == 'active'`                | `status = 'active'`                     |
| `name.startswith('A')`              | `name LIKE 'A%'`                        |
| `email.contains('@corp.com')`       | `email LIKE '%@corp.com%'`             |
| `code[:3]`                          | `SUBSTR(code, 1, 3)`                    |
| `name.upper().strip()`              | `TRIM(UPPER(name))`                     |
| `price * qty - discount`            | `price * qty - discount`               |

---

## Installation

> 🚧 **PyPI release coming soon.**

```bash
# Not yet available — star the repo to get notified
pip install ormophine
```

---

## Roadmap

- [x] SQLite backend with full ORM
- [x] Operator overloading for columns
- [x] Read-only connection pool
- [x] WAL mode + automatic checkpointing
- [x] Batch / bulk operations
- [ ] MySQL / MariaDB backend
- [ ] PostgreSQL backend
- [ ] Async support
- [ ] PyPI release
- [ ] Benchmark suite publication

---

## Contributing

The codebase is currently in active development and not yet public. Once released, contributions, bug reports, and feature requests will be very welcome.

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<div align="center">
  <sub>Built with Python · Designed for developers who value clarity and speed</sub>
</div>
