<div align="center">

# Ormophine

**The most Pythonic ORM. Fast, intuitive, and gets out of your way.**

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Development-orange)](https://github.com/yourusername/ormophine)
[![PyPI](https://img.shields.io/badge/PyPI-Latest-blue?logo=pypi)](https://pypi.org/project/Ormophine/)

*Write database queries the way you think — in plain Python.*

</div>

---

## Documentation & AI Assistance

📖 **Full Documentation**  
Comprehensive guides, API references, and examples are available at:  
👉 [https://ormophine.readthedocs.io/en/latest/index.html](https://ormophine.readthedocs.io/en/latest/index.html)

🤖 **AI-Powered Assistance**  
To help you write queries and debug your code, Ormophine ships with AI reference files (`Sqlite.AI.Reference.txt`, `MySQL.AI.Reference.txt`, `PostgreSQL.AI.Reference.txt`). 

You can find these files in the root directory of the installed package. Simply attach the appropriate file to ChatGPT, Claude, or Gemini, ask your question, and the AI will respond using the exact API and behavior of your Ormophine version. It's like having an Ormophine expert on standby!

---

## The Problem with Other ORMs

Most Python ORMs are either too verbose, too magical, or require too much boilerplate. Compare the everyday workflow of connecting, accessing tables, inserting data, and querying using popular ORMs versus Ormophine.

### 1. Connecting to the Database

**Other ORMs:**

```python
# Django ORM (Requires project setup, settings.py configuration, and no direct script execution)
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'my_db.db',
    }
}

# SQLAlchemy
from sqlalchemy import create_engine
engine = create_engine('sqlite:///my_db.db')

# PonyORM
from pony.orm import Database
db = Database()
db.bind(provider='sqlite', filename='my_db.db', create_db=True)
```

**Ormophine:**

```python
from Ormophine.Sqlite import Driver

# Direct, clean instantiation. No settings files, no bind calls.
db = Driver('my_db.db')
```

### 2. Accessing Tables

**Other ORMs:**

```python
# Django ORM (Requires defining models in models.py and running migrations)
# models.py
class User(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
# Then in your code:
from .models import User

# SQLAlchemy (Requires manual reflection or pre-defined models)
from sqlalchemy import Table, MetaData
metadata = MetaData()
users = Table('users', metadata, autoload_with=engine)

# PonyORM (Requires defining entities)
from pony.orm import Required
class User(db.Entity):
    name = Required(str)
    age = Required(int)
db.generate_mapping(create_tables=True)
```

**Ormophine:**

```python
# Tables and columns are discovered and mapped dynamically as attributes
users = db.users
```

### 3. Inserting Data

**Other ORMs:**

```python
# Django ORM
User.objects.create(name='Alice', email='alice@example.com', age=30)

# SQLAlchemy (Requires explicit connection and commit)
with engine.connect() as conn:
    conn.execute(users.insert().values(
        name='Alice', 
        email='alice@example.com', 
        age=30
    ))
    conn.commit()

# PonyORM (Requires explicit db_session context)
from pony.orm import db_session
with db_session:
    User(name='Alice', email='alice@example.com', age=30)
```

**Ormophine:**

```python
# Auto-committed, uses Pythonic dictionary mapping with actual column objects
users.insert({
    users.name:  'Alice',
    users.email: 'alice@example.com',
    users.age:   30
})
```

### 4. Fetching Data with Complex Conditions

Let's try to fetch rows where the lowercased name starts with 'ab', AND a specific slice of the lastname equals 'connor', ordered by age.

**Other ORMs:**

```python
# Django ORM (Lacks native string slicing; requires complex Regex or raw SQL)
from django.db.models import F
results = User.objects.filter(
    name__istartswith='ab'
    #lastname[5:-2] == 'connor' is notoriously difficult without RawSQL or Regex
).order_by('age').values('name', 'age')

# SQLAlchemy (Verbose function calls and string manipulation)
from sqlalchemy import select, func, or_
stmt = select(users.c.name, users.c.age).where(
    func.lower(users.c.name).like('ab%'),
    func.substr(users.c.lastname, 6, func.length(users.c.lastname) - 7) == 'connor'
).order_by(users.c.age)
with engine.connect() as conn:
    results = conn.execute(stmt).fetchall()

# PonyORM (Requires lambda functions and lacks intuitive slicing)
from pony.orm import db_session, select
with db_session:
    query = select(u for u in User if u.name.lower().startswith('ab'))
    # Again, string slicing like [5:-2] is not natively supported in PonyORM queries
    query = query.order_by(lambda u: u.age)
    results = [(u.name, u.age) for u in query]
```

**Ormophine:**

```python
# Pure Python syntax! Slicing and string methods translate directly to SQL under the hood.
rows = users.get_row(
    [users.name, users.age],
    where=(users.name.lower().startswith('ab')) & (users.lastname[5:-2] == 'connor'),
    order_by=users.age
)
```

Same results. No boilerplate. No complex function mapping. Just Python.

---

## Why Ormophine?

- **Intuitive Pythonic Syntax** — columns behave like native Python variables. We designed Ormophine to simulate standard Python string and sequence behaviors directly in SQL. Instead of learning a new DSL or using verbose SQL functions, you just write Python, and Ormophine translates it into optimized, parameterized SQL under the hood:
  - **String Concatenation:** Use the standard Python `+` operator to concatenate string columns and literals seamlessly.
  - **Native String Methods:** Chain Python string methods like `lower()`, `upper()`, `strip()`, `lstrip()`, `rstrip()`, `replace()`, `startswith()`, and `endswith()` directly on column objects.
  - **Sequence Slicing:** Use Python's native slice syntax (e.g., `column[2:5]` or `column[-4:]`) to extract substrings, which automatically translates to native SQL substring functions.
  - **Logical & Arithmetic Operators:** Combine conditions using Python's bitwise operators (`&`, `|`) and perform arithmetic (`+`, `-`, `*`, `/`) just like regular Python variables.
- **Fast & Thread-Safe** — built on a dedicated writer queue (SQLite) and robust connection pooling (MySQL/PostgreSQL); parallel reads, serialized writes.
- **Fault-Tolerant Connection Pools** — automatically detects broken connections (e.g., database restarts) and seamlessly recreates them without crashing your application.
- **Multi-database** — one unified API across SQLite, MySQL, and PostgreSQL. Switch databases by changing your import.
- **Dynamic Schema Mapping** — tables and columns are discovered automatically and attached to the driver instance.
- **Built-in DB Administration** — manage users, permissions, create/drop databases, and run maintenance tasks (like PostgreSQL `VACUUM` or SQLite `PRAGMA`) directly from the driver.
- **WAL mode support** (SQLite) — automatic checkpointing for maximum write throughput.

---

## Benchmark Results

> 📊 **Coming Soon!** 
> Ormophine is not just about clean syntax—it is engineered for extreme performance. Early internal tests show it is **significantly faster** than other popular Python ORMs. 
> 
> Detailed benchmark results comparing Ormophine against SQLAlchemy, Django ORM, Tortoise ORM, and raw DB-API 2.0 will be published here soon. We are testing INSERT throughput, SELECT latency, bulk operations, and concurrent read workloads across all three backends.

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

## Installation

```bash
pip install Ormophine
```

---

## Project Status & Roadmap

> ⚠️ **Work in Progress**
> 
> Ormophine is currently in active development. While it is highly functional and fast, it is not yet as feature-complete or massive in size as legacy ORMs like SQLAlchemy or Django ORM. 
> 
> Our philosophy is to keep the core lightweight and fast. In future releases, we plan to simulate even more Python string and list methods to make the query syntax even closer to pure Python.

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
- [ ] Async support

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
  <sub>Built with Python · Designed for developers who value clarity and speed</sub>
</div>
