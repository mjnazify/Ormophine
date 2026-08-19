
# Ormophine

**The simplest Python ORM. Read like Python, run like SQL.**

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Development-orange)](https://github.com/yourusername/ormophine)
[![PyPI](https://img.shields.io/badge/PyPI-Latest-blue?logo=pypi)](https://pypi.org/project/Ormophine/)

*No models to define. No DSL to learn. No boilerplate to write.*

</div>

---

## Philosophy

Most Python ORMs were built for enterprise complexity — layers of abstractions, session lifecycles, model definitions, and migration pipelines. They're powerful, but they make **simple things hard**.

Ormophine is built on a different premise:

> **90% of database work is simple CRUD. The ORM for that work should be simple too.**

Ormophine gives you one thing no other ORM does: **you write plain Python, and it becomes SQL**. No new syntax. No function wrappers. No lambda queries. If you know Python, you already know Ormophine.

```python
# This is Python. But it's also a SQL query.
rows = users.get_row(
    which_columns = [users.name, users.age],
    where = (users.age >= 18) & users.name.lower().startswith('a'),
    order_by = users.age
)
```

That's it. Read it like Python, it runs like SQL. Under the hood, Ormophine translates your expressions into optimized, parameterized SQL — you never see a `?` or a `%s`.

---

## Documentation & AI Assistance

📖 **Full Documentation**
Comprehensive guides, API references, and examples are available at:
👉 [https://ormophine.readthedocs.io/en/latest/index.html](https://ormophine.readthedocs.io/en/latest/index.html)

🤖 **AI-Powered Assistance**
To help you write queries and debug your code, Ormophine ships with AI reference files (`Sqlite.AI.Reference.txt`, `MySQL.AI.Reference.txt`, `PostgreSQL.AI.Reference.txt`).

You can find these files in the root directory of the installed package. Simply attach the appropriate file to ChatGPT, Claude, or Gemini, ask your question, and the AI will respond using the exact API and behavior of your Ormophine version. It's like having an Ormophine expert on standby!


---

## Simplicity in Action — Side by Side

The best way to understand Ormophine's advantage is to see the same everyday tasks written in different ORMs. Notice what's missing in the Ormophine column: no models, no sessions, no `.execute()`, no `func.` wrappers, no lambdas.

### Connecting to the Database

**SQLAlchemy:**
```python
from sqlalchemy import create_engine
engine = create_engine('sqlite:///my_db.db')
```

**PonyORM:**
```python
from pony.orm import Database
db = Database()
db.bind(provider='sqlite', filename='my_db.db', create_db=True)
```

**Peewee:**
```python
from peewee import SqliteDatabase
db = SqliteDatabase('my_db.db')
```

**Ormophine:**
```python
from Ormophine.Sqlite import Driver

db = Driver('my_db.db')
```

---

### Accessing Tables

**SQLAlchemy:**
*Requires manual reflection or pre-defined models*
```python
from sqlalchemy import Table, MetaData
metadata = MetaData()
users = Table('users', metadata, autoload_with=engine)
```

**PonyORM:**
*Requires defining entities and generating mappings*
```python
from pony.orm import Required
class User(db.Entity):
    name = Required(str)
    age = Required(int)
db.generate_mapping(create_tables=True)
```

**Peewee:**
*Requires defining models and explicitly linking them to the database*
```python
from peewee import Model, CharField, IntegerField
class User(Model):
    name = CharField()
    age = IntegerField()
    class Meta:
        database = db
```

**Ormophine:**
```python
# No models. No definitions. Tables appear as attributes automatically.
users = db.users
```

Your database already knows its schema. Why should you redeclare it in Python?

---

### Inserting Data

**SQLAlchemy:**
*Requires explicit connection context and commit*
```python
with engine.connect() as conn:
    conn.execute(users.insert().values(
        name='Alice', 
        email='alice@example.com', 
        age=30
    ))
    conn.commit()
```

**PonyORM:**
*Requires explicit db_session context*
```python
from pony.orm import db_session
with db_session:
    User(name='Alice', email='alice@example.com', age=30)
```

**Peewee:**
*Requires calling .execute() on the query construct*
```python
User.insert(
    name='Alice', 
    email='alice@example.com', 
    age=30
).execute()
```

**Ormophine:**
```python
# Auto-committed. Column objects as keys — readable and safe.
users.insert({
    users.name:  'Alice',
    users.email: 'alice@example.com',
    users.age:   30
})
```

A dictionary. Column on the left, value on the right. You can read it at a glance.

---

### Fetching Data with Complex Conditions

Let's try to fetch rows where the lowercased name starts with `'ab'`, AND a specific slice of the lastname equals `'connor'`, ordered by age.

**SQLAlchemy:**
*Verbose function calls and manual string manipulation for slicing*
```python
from sqlalchemy import select, func
stmt = select(users.c.name, users.c.age).where(
    func.lower(users.c.name).like('ab%'),
    func.substr(users.c.lastname, 6, func.length(users.c.lastname) - 7) == 'connor'
).order_by(users.c.age)
with engine.connect() as conn:
    results = conn.execute(stmt).fetchall()
```

**PonyORM:**
*Requires lambda functions and lacks intuitive slicing*
```python
from pony.orm import db_session, select
with db_session:
    query = select(u for u in User if u.name.lower().startswith('ab'))
    # String slicing like [5:-2] is not natively supported in PonyORM queries
    query = query.order_by(lambda u: u.age)
    results = [(u.name, u.age) for u in query]
```

**Peewee:**
*Uses SQL function wrappers and lacks native Python slicing*
```python
from peewee import fn
# Peewee lacks native string slicing in ORM queries
query = User.select(User.name, User.age).where(
    fn.LOWER(User.name).startswith('ab')
    # User.lastname[5:-2] == 'connor' is not possible natively
).order_by(User.age)
results = list(query.dicts())
```

**Ormophine:**
```python
# Pure Python. Slicing, string methods — they just work.
rows = users.get_row(
    [users.name, users.age],
    where=(users.name.lower().startswith('ab')) & (users.lastname[5:-2] == 'connor'),
    order_by=users.age
)
```

`users.name.lower().startswith('ab')` — that's Python. `users.lastname[5:-2]` — that's Python. Ormophine translates them into the correct SQL functions automatically. **You never have to think about how to express your logic in SQL.**

---

### Atomic / Batch Transactions

Performing multiple write operations in a single, atomic transaction is crucial for data integrity and speed. Let's insert 2 users, update 1, and delete 1.

**SQLAlchemy:**
*Requires explicit connection block and manual execution for each statement*
```python
with engine.begin() as conn:
    conn.execute(users.insert().values(name='Dave', email='dave@example.com', age=40))
    conn.execute(users.insert().values(name='Eve', email='eve@example.com', age=28))
    conn.execute(users.update().where(users.c.name == 'Alice').values(age=31))
    conn.execute(users.delete().where(users.c.name == 'Bob'))
```

**PonyORM:**
*Requires db_session context and imperative object manipulation for updates/deletes*
```python
from pony.orm import db_session
with db_session:
    User(name='Dave', email='dave@example.com', age=40)
    User(name='Eve', email='eve@example.com', age=28)
    alice = User.get(name='Alice')
    if alice: alice.age = 31
    bob = User.get(name='Bob')
    if bob: bob.delete()
```

**Peewee:**
*Requires atomic context and explicit .execute() on every query construct*
```python
with db.atomic():
    User.insert(name='Dave', email='dave@example.com', age=40).execute()
    User.insert(name='Eve', email='dave@example.com', age=28).execute()
    User.update(age=31).where(User.name == 'Alice').execute()
    User.delete().where(User.name == 'Bob').execute()
```

**Ormophine:**
```python
# Queue your operations. Run once. All or nothing.
batch = users.batch()
batch.insert({users.name: 'Dave', users.email: 'dave@example.com', users.age: 40})
batch.insert({users.name: 'Eve', users.email: 'eve@example.com', users.age: 28})
batch.update({users.age: 31}, where=users.name == 'Alice')
batch.delete_row(where=users.name == 'Bob')
batch.run() # Executes all and commits in one transaction
```

No context managers. No `.execute()` on every line. Just stack your operations and run.

---

## What Makes Ormophine Simple

Ormophine's simplicity isn't about having fewer features — it's about **expressing more with less syntax**. Every design decision follows one rule:

> **If it reads like Python, it's right. If you have to look up how to write it, it's wrong.**

### Columns Are Python Variables

Other ORMs give you column objects that you must wrap in helper functions. Ormophine columns **behave like native Python values**:

```python
# String methods — just call them
users.name.lower()
users.name.upper()
users.name.strip()
users.name.startswith('A')
users.name.endswith('.com')

# Slicing — just like Python strings and lists
users.code[:3]        # first 3 characters
users.lastname[5:-2]  # from index 5, drop last 2

# Arithmetic — just like Python numbers
users.price * users.qty - users.discount

# Concatenation — the + operator works naturally
users.first_name + ' ' + users.last_name

# Logic — combine with & and |
(users.age >= 18) & (users.status == 'active')
```

All of these are translated to the correct SQL under the hood. All values are automatically parameterized — **SQL injection is prevented by design**.

### No Models, No Boilerplate

You don't define classes. You don't declare fields. You don't bind tables to a metadata registry. You connect, and everything is there:

```python
db = Driver('my.db')

users  = db.users     # it just exists
orders = db.orders    # this too

# Columns appear as attributes
users.name    # column object
users.age     # column object
users.email   # column object
```

### Auto-Commit by Default

Every insert, update, and delete commits automatically. No `session.commit()`. No `with engine.begin()`. For batch operations, use `.batch()` — otherwise, each operation stands on its own.

```python
# This is a complete, working operation. Nothing else needed.
users.insert({users.name: 'Alice', users.age: 30})
```

### One API, Three Databases

Switching databases is a one-line import change. The API stays identical:

```python
# SQLite
from Ormophine.Sqlite import Driver
db = Driver('my.db')

# MySQL
from Ormophine.Mysql import Driver
db = Driver(host='localhost', port=3306, username='root', password='pass', db_name='my_db')

# PostgreSQL
from Ormophine.Postgresql import Driver
db = Driver(host='localhost', port=5432, username='postgres', password='pass', db_name='my_db')
```

Same `.insert()`, same `.get_row()`, same `.update()`, same `.batch()`. Learn once, use anywhere.

---

## Why Ormophine?

- **Zero Learning Curve** — if you know Python, you know Ormophine. Columns are variables, methods are methods, slicing is slicing, operators are operators. There is no DSL, no special syntax, nothing to look up.
- **Reads Like English** — `users.name.lower().startswith('a')` says exactly what it does. Compare that to `func.lower(users.c.name).like('a%')`.
- **Dynamic Schema Discovery** — tables and columns appear as attributes automatically. No model definitions. No reflection boilerplate. Connect and start writing queries.
- **Auto-Commit Simplicity** — every write operation commits immediately by default. No session management. For atomic multi-step operations, the `.batch()` builder is one `batch.run()` call.
- **Fast & Thread-Safe** — built on a dedicated writer queue (SQLite) and robust connection pooling (MySQL/PostgreSQL); parallel reads, serialized writes.
- **Fault-Tolerant Connections** — automatically detects broken connections (e.g., database restarts) and seamlessly recreates them without crashing your application.
- **Multi-Database** — one unified API across SQLite, MySQL, and PostgreSQL. Switch databases by changing your import.
- **Built-in DB Administration** — manage users, permissions, create/drop databases, and run maintenance tasks (like PostgreSQL `VACUUM` or SQLite `PRAGMA`) directly from the driver.
- **WAL Mode Support** (SQLite) — automatic checkpointing for maximum write throughput.

---

## ⚡ Benchmark Results

Ormophine is simple — but it's not slow. We benchmarked it against popular Python ORMs (SQLAlchemy, PonyORM, and Peewee) across SQLite, PostgreSQL, and MySQL — measuring throughput instead of raw execution time.

### Methodology
We evaluate two distinct scenarios to measure both transactional overhead and bulk efficiency:

1. **Single Operations:** Measures how many CRUD queries per second each ORM can execute when a COMMIT is issued immediately after every single insert, update, and delete. This tests the ORM's baseline overhead and connection management for isolated transactions.

2. **Batch Operations:** Measures how many CUD (Create, Update, Delete) queries per second each ORM can execute when all statements are executed first, and a single COMMIT is issued at the end. This tests the ORM's efficiency in bulk transactional processing.

**Metric — Queries Per Second (QPS):** each test run executes a fixed number of queries per operation; throughput is computed as QPS = queries / elapsed_seconds for every run, and the mean across all repeats is reported. QPS is a normalized metric, so results remain directly comparable across chunk sizes and database backends — and it reads naturally: how many queries can each ORM execute in one second?

**How to read the charts:** every chart shows Mean Throughput in Queries Per Second (QPS) — a taller bar is better. Below each chart, the percentage indicates how much faster Ormophine is compared to that ORM.

> **Note on Variance & Equivalence:** Due to natural system fluctuations, each test run can have a variance of up to ±10%. Therefore, throughput differences of less than 5% are considered statistically insignificant (margin of error). In the charts below, differences under 5% are displayed in gray and marked as "≈ Equal", rather than claiming a marginal advantage.

You can access the benchmark Jupyter notebooks in the project repository at `Ormophine/{Sqlite, Postgresql, Mysql}/Benchmark` to run the tests on your own hardware.

You can also use this Google Colab notebooks:

**Sqlite:**
https://colab.research.google.com/drive/1KK3sr8H_Crd29fmnq3VmpmE88aLNT3Yr?usp=sharing

**MySQL:**
https://colab.research.google.com/drive/1ndwmN0C9UTZHTNmLh8-fT9rEg-DSrzHQ?usp=sharing

**PostgeSQL:**
https://colab.research.google.com/drive/1XYrC30vUciS1YgY6M5MBoxwO9YTltzkD?usp=sharing


---

### PostgreSQL Results

**Single Operations Test**
*(Executed 10,000 queries total — 200 repeats × 50 chunk size — for each CRUD operation per ORM)*

**Inserts:**

<img width="400" height="400" alt="Postgre-SingleOp-Insert" src="https://github.com/user-attachments/assets/e2e08264-e1ff-4eb4-85a7-033d8ca2e28e" />

**Updates:**

<img width="400" height="400" alt="Postgre-SingleOp-Update" src="https://github.com/user-attachments/assets/c124dc1f-dbd6-47a3-bcd3-cefa30cb20f2" />

**Reads:**

<img width="400" height="400" alt="Postgre-SingleOp-Read" src="https://github.com/user-attachments/assets/6ff5a1c7-fc34-4d95-a8db-fa4e091830c5" />

**Deletes:**

<img width="400" height="400" alt="Postgre-SingleOp-Delete" src="https://github.com/user-attachments/assets/e95e1cbf-a0d7-4873-9fac-da0517319ffc" />

---

**Batch Operation Test**
*(Executed 500 queries total — 5 repeats × 100 statements per chunk — for each CUD operation per ORM)*

**Inserts:**

<img width="400" height="400" alt="Postgre-BatchOp-Insert" src="https://github.com/user-attachments/assets/de37f0a0-0bbf-40a2-9446-d5929b82b417" />

**Updates:**

<img width="400" height="400" alt="Postgre-BatchOp-Update" src="https://github.com/user-attachments/assets/029eb1d1-7a1b-4820-84bb-d21a53d0e64a" />

**Deletes:**

<img width="400" height="400" alt="Postgre-BatchOp-Delete" src="https://github.com/user-attachments/assets/4cec72b7-4c38-4305-8175-be67562be4ee" />

---

### Sqlite Results

**Single Operations Test**
*(Executed 10,000 queries total — 200 repeats × 50 chunk size — for each CRUD operation per ORM)*

**Inserts:**

<img width="400" height="400" alt="Sqlite-SingleOp-Insert" src="https://github.com/user-attachments/assets/00d9b75b-6ac2-421a-a633-2024143b6c25" />

**Updates:**

<img width="400" height="400" alt="Sqlite-SingleOp-Update" src="https://github.com/user-attachments/assets/803050b7-cf23-48c9-9cd5-e9ebeaa448c9" />

**Reads:**

<img width="400" height="400" alt="Sqlite-SingleOp-Read" src="https://github.com/user-attachments/assets/257fdc41-1c56-47d7-a9a5-a23d2fb1764b" />

**Deletes:**

<img width="400" height="400" alt="Sqlite-SingleOp-Delete" src="https://github.com/user-attachments/assets/d1efb031-068f-41d2-a671-155e31e623c2" />

---

**Batch Operation Test**
*(Executed 500 queries total — 5 repeats × 100 statements per chunk — for each CUD operation per ORM)*

**Inserts:**

<img width="400" height="400" alt="Sqlite-BatchOp-Insert" src="https://github.com/user-attachments/assets/89572529-3859-4b34-9c69-b6eb8c566bc6" />

**Updates:**

<img width="400" height="400" alt="Sqlite-BatchOp-Update" src="https://github.com/user-attachments/assets/25ce020d-92d4-4dac-8876-08780657b624" />

**Deletes:**

<img width="400" height="400" alt="Sqlite-BatchOp-Delete" src="https://github.com/user-attachments/assets/35fcee8e-2c5f-4761-adce-84ddc40b4ccf" />

---

### MySQL Results

**Single Operations Test**
*(Executed 10,000 queries total — 200 repeats × 50 chunk size — for each CRUD operation per ORM)*

**Inserts:**

<img width="400" height="400" alt="MySQL-SingleOp-Insert" src="https://github.com/user-attachments/assets/89061de4-8888-45a2-b264-c1c4b1e7d619" />

**Updates:**

<img width="400" height="400" alt="MySQL-SingleOp-Update" src="https://github.com/user-attachments/assets/cd605592-c333-4107-9996-f77a6be63b99" />

**Reads:**

<img width="400" height="400" alt="MySQL-SingleOp-Read" src="https://github.com/user-attachments/assets/f45642db-0f7c-47e4-a4d9-a61bc179e780" />

**Deletes:**

<img width="400" height="400" alt="MySQL-SingleOp-Delete" src="https://github.com/user-attachments/assets/3e781d61-b548-4499-80b9-be90ad39ed05" />

---


**Batch Operation Test**
*(Executed 500 queries total — 5 repeats × 100 statements per chunk — for each CUD operation per ORM)*

**Inserts:**

<img width="400" height="400" alt="MySQL-BatchOp-Insert" src="https://github.com/user-attachments/assets/894c9774-8ba0-47c5-889c-be09b2854c23" />

**Updates:**

<img width="400" height="400" alt="MySQL-BatchOp-Update" src="https://github.com/user-attachments/assets/087109b6-3d6e-480a-816d-8abc0a110bd1" />

**Deletes:**

<img width="400" height="400" alt="MySQL-BatchOp-Delete" src="https://github.com/user-attachments/assets/9cdd1b75-ad44-4ac1-bbd9-9881140fc748" />

---

## Quick Examples

### Connect and access tables

```python
from Ormophine.Sqlite import Driver

db = Driver('company.db')

# Tables and columns are discovered automatically — no models needed
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
    which_columns = [name, email],
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

### Safe Deletion & Administration

```python
# Triple-confirmation flags prevent catastrophic accidental drops
db.delete_table(db.users, are_you_sure=True, are_you_really_sure=True, for_sure=True)

# Create a new database on the fly during connection (MySQL/PostgreSQL)
# from Ormophine.Mysql import Driver
# db = Driver(host='localhost', port=3306, username='root', password='pass', db_name='new_db', create_new_db=True)
```

### WAL mode and performance tuning (SQLite)

```python
db.set_WAL_mode(True, wal_timer=60)   # automatic checkpoint every 60 s

db.SetPragma.synchronous('NORMAL')
db.SetPragma.cache_size(-4000)        # 4 MiB page cache
db.SetPragma.foreign_keys(True)
```

---

## Python → SQL Reference

This is a small list of Python expressions that Ormophine translates into SQL. Every value is automatically parameterized — SQL injection is prevented by design, not by discipline.

| Python Expression                   | SQL Equivalent                          | What it does                         |
|-------------------------------------|-----------------------------------------|--------------------------------------|
| `age > 18`                          | `age > 18`                              | Comparison                           |
| `(age >= 18) & (age < 65)`          | `age >= 18 AND age < 65`               | Logical AND                          |
| `age == 18`                         | `age = 18`                              | Equality                             |
| `name.startswith('A')`              | `name LIKE 'A%'`                        | Prefix match                         |
| `name.endswith('.com')`             | `name LIKE '%.com'`                     | Suffix match                         |
| `email.contains('@corp')`           | `email LIKE '%@corp%'`                  | Substring match                      |
| `code[:3]`                          | `SUBSTR(code, 1, 3)`                    | Slice from start                     |
| `code[2:5]`                         | `SUBSTR(code, 3, 3)`                    | Slice with start and end             |
| `name[-4:]`                         | `SUBSTR(name, -4)`                      | Slice from end                       |
| `name.lower()`                      | `LOWER(name)`                           | Lowercase                            |
| `name.upper()`                      | `UPPER(name)`                           | Uppercase                            |
| `name.strip()`                      | `TRIM(name)`                            | Strip whitespace                     |
| `name + ' suffix'`                  | `name \|\| ' suffix'`                   | String concatenation                 |
| `price * qty - discount`            | `price * qty - discount`                | Arithmetic                           |
| `price + 10`                        | `price + 10`                            | Arithmetic with literal              |

No `func.`, no `fn.`, no `F()`, no `.annotate()`. Just Python.

---

## Installation

```bash
pip install Ormophine
```

---

## Project Status & Roadmap

Ormophine is intentionally lightweight. We don't aim to match the feature count of enterprise ORMs — we aim to make simple CRUD as simple as it can possibly be.

> ⚠️ **Work in Progress**
>
> Ormophine is currently in active development. While it is highly functional and fast, it is not yet as feature-complete as legacy ORMs like SQLAlchemy or Django ORM.
>
> Our philosophy is to keep the core simple and fast. In future releases, we plan to simulate even more Python string and list methods to make the query syntax even closer to pure Python.

### Current Roadmap
- [x] SQLite backend with full ORM
- [x] MySQL backend with connection pooling
- [x] PostgreSQL backend with connection pooling
- [x] Operator overloading and slicing (`[]`) for columns
- [x] String methods simulation (`lower`, `upper`, `strip`, `startswith`, etc.)
- [x] Read-only connection pool / Non-blocking reads
- [x] WAL mode + automatic checkpointing
- [x] Batch / bulk operations
- [x] AI Reference files for LLM assistance
- [ ] Expanding simulated Python methods (`.replace()`, `.find()`, etc.)
- [ ] Video Tutorials
- [ ] Benchmark suite publication

---

## Video Tutorials

> 🎥 **Coming Soon!**
> We are preparing a comprehensive video series to help you get started with Ormophine, from basic connections to advanced concurrent read/write pooling and schema management.
>
> *Stay tuned—links will be posted here soon.*

---

## Contributing

The codebase is currently in active development. Contributions, bug reports, and feature requests are very welcome! Please feel free to open an issue or submit a pull request.

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<div align="center">
  <sub>Built with Python · Designed for developers who value simplicity</sub>
</div>