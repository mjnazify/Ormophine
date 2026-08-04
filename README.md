<div align="center">

# Ormophine

**A fast, Pythonic ORM that gets out of your way.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Development-orange)](https://github.com/yourusername/ormophine)
[![PyPI](https://img.shields.io/badge/PyPI-Latest-blue?logo=pypi)](https://pypi.org/project/Ormophine/)

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
from Ormophine.Sqlite import Driver

db = Driver('my_db.db')
users = db.users
phone, name, age = users.phone, users.name, users.age

users.get_row(
    [phone, name, age],
    where = (age > 18) & (phone.startswith('+98') | (phone[:3] == '+98')),
    order_by = age
)
```

Same result. No boilerplate. No imports for every logical operator. No ceremony.

---

## Why Ormophine?

- **Intuitive syntax** — columns behave like Python variables with full operator overloading (`>`, `&`, `|`, `+`, `[]`, `.startswith()`, etc.)
- **Fast & Thread-Safe** — built on a dedicated writer queue (SQLite) and robust connection pooling (MySQL/PostgreSQL); parallel reads, serialized writes.
- **Multi-database** — one unified API across SQLite, MySQL, and PostgreSQL. Switch databases by changing your import.
- **Dynamic Schema Mapping** — tables and columns are discovered automatically and attached to the driver instance.
- **WAL mode support** (SQLite) — automatic checkpointing for maximum write throughput.
- **AI-Ready** — includes backend-specific source code reference files to feed to LLMs like ChatGPT or Claude for instant, accurate ORM assistance.

---

## Supported Databases

| Database     | Status              |
|--------------|---------------------|
| SQLite       | ✅ Available         |
| MySQL        | ✅ Available         |
| PostgreSQL   | ✅ Available         |
| MariaDB      | ✅ Available (via MySQL driver) |

The API is identical across all backends. Switch databases by changing one line.

---

## Video Tutorials

> 🎥 **Coming Soon!** 
> We are preparing a comprehensive video series to help you get started with Ormophine, from basic connections to advanced concurrent read/write pooling and schema management. 
> 
> *Stay tuned—links will be posted here soon.*

---

## Benchmark Results

> 📊 **Coming Soon!** 
> Benchmark results comparing Ormophine against SQLAlchemy, Tortoise ORM, and raw DB-API 2.0 will be published here. We are testing INSERT throughput, SELECT latency, bulk operations, and concurrent read workloads across all three backends.

---

## Quick Examples

### Connect and access tables

```python
from Ormophine.Sqlite import Driver

db = Driver('company.db')

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
from Ormophine.Sqlite import Join

result = orders.join(
    columns    = [users.name, orders.amount, orders.date],
    joins_list = [Join.Inner(users, users.id == orders.user_id)],
    where      = orders.amount > 100,
    order_by   = [orders.date]
)
```

### Schema management

```python
from Ormophine.Sqlite import TableStructure, DataTypes

schema = TableStructure('products', strict=True)
schema.add_column('id',    DataTypes.INTEGER(), primary_key=True)
schema.add_column('title', DataTypes.TEXT(max_length=100), not_null=True, unique=True)
schema.add_column('price', DataTypes.REAL(), default_value=0.0)

products = db.create_table(schema)

# Add / rename / drop columns dynamically
products.add_column('stock', DataTypes.INTEGER(), default_value=0, not_null=True)
products.rename_column(products.stock, 'inventory')
products.delete_column(products.inventory, True, True, True)
```

### WAL mode and performance tuning (SQLite)

```python
db.set_WAL_mode(True, wal_timer=60)   # automatic checkpoint every 60 s

db.SetPragma.synchronous('NORMAL')
db.SetPragma.cache_size(-4000)        # 4 MiB page cache
db.SetPragma.foreign_keys(True)
```

---

## Operator Reference

Ormophine columns support native Python expressions — all values are automatically parameterized to prevent SQL injection.

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

## AI-Powered Assistance

To help you write queries and debug your code, Ormophine ships with AI reference files (`Sqlite.AI.Reference.txt`, `MySQL.AI.Reference.txt`, `PostgreSQL.AI.Reference.txt`). 

You can attach these files to ChatGPT, Claude, or Gemini, ask your question, and the AI will respond using the exact API and behavior of your Ormophine version.

---

## Installation

```bash
pip install Ormophine
```

---

## Roadmap

- [x] SQLite backend with full ORM
- [x] MySQL backend with connection pooling
- [x] PostgreSQL backend with connection pooling
- [x] Operator overloading for columns
- [x] Read-only connection pool / Non-blocking reads
- [x] WAL mode + automatic checkpointing
- [x] Batch / bulk operations
- [x] AI Reference files for LLM assistance
- [ ] Video Tutorials
- [ ] Benchmark suite publication
- [ ] Async support

---

## Contributing

The codebase is currently in active development. Contributions, bug reports, and feature requests are very welcome! Please feel free to open an issue or submit a pull request.

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<div align="center">
  <sub>Built with Python · Designed for developers who value clarity and speed</sub>
</div>
