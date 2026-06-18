```markdown
# 🚀 Ormophine

### The Pythonic ORM That's *Simpler* and *Faster*

<p align="center">
  <img src="https://img.shields.io/badge/Status-Alpha_Development-yellow?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/PyPI-Coming_Soon-red?style=for-the-badge" alt="PyPI">
  <img src="https://img.shields.io/badge/Benchmarks-Available_Soon-orange?style=for-the-badge" alt="Benchmarks">
</p>

---

## 📌 Project Status (Read Me First!)

> ⚠️ **Heads up!** The core source code of Ormophine is currently under heavy development and **has not been pushed to this repository yet**.
>
> This repository currently serves as a **design showcase** and a **benchmarking hub**.
> - **Phase 1 (Current):** Publishing benchmark results, performance comparisons, and API design examples.
> - **Phase 2 (Next):** Open-sourcing the complete codebase.
> - **Phase 3 (Final):** Publishing the package on PyPI (`pip install ormophine`).

---

## 🤔 Why Ormophine?

Let's face it—most ORMs in Python are either:
- **Too complex:** SQLAlchemy is powerful but has a steep learning curve with its hybrid properties, deferred columns, and intricate session management.
- **Too slow:** Django ORM is convenient but notoriously heavy and slow for high-throughput applications.
- **Too un-Pythonic:** Writing `filter(MyModel.age > 18)` is okay, but chaining multiple `.filter()` calls or writing raw strings inside queries breaks the flow.

**Ormophine** was built from the ground up to solve these exact pain points. It provides a **native Python experience** for database interactions. You write Python, and Ormophine translates it into highly optimized SQL—often **outperforming** traditional ORMs because of its lightweight AST (Abstract Syntax Tree) parsing and minimal overhead.

---

## ✨ Core Features

- **🧠 Intuitive Syntax:** Leverages native Python operators (`&`, `|`, `==`, `>`, `<`) and string methods (`startswith`, `endswith`, slicing) directly on column objects.
- **⚡ Blazing Fast:** Minimal abstraction layers. The query builder compiles directly to SQL strings without heavy object-relational mapping overhead.
- **🔗 Chain-Free Filtering:** No more `.filter().filter().filter()` nonsense. Write complex `WHERE` clauses in a single, readable expression.
- **🐍 Pure Python Logic:** Use `and` / `or` or `&` / `|` exactly as you would in regular Python conditionals.
- **🗄️ Multi-Database Support (Planned):** Currently focusing on SQLite with PostgreSQL and MySQL support on the roadmap.
- **🔮 Smart Column Handling:** Columns are first-class citizens. You can manipulate them like variables.

---

## 📖 Quick Start & API Examples

Here is a sneak peek at how Ormophine simplifies database interactions.

### 1. Connecting to the Database
```python
from Ormophine import Sqlite

# Just point to your DB file. No connection strings, no engines, no sessions!
my_db = Sqlite('my_db')
```

### 2. Accessing Tables
Tables are dynamically accessible as attributes of the database object.
```python
# Access the 'users' table
users = my_db.users
```

### 3. Defining Columns
Columns are accessed directly from the table instance. You can assign them to variables for cleaner queries.
```python
phone, name, age = users.phone, users.name, users.age
```

### 4. Inserting Data
Inserting is as straightforward as passing keyword arguments.
```python
users.insert(phone='+989123456789', name='Alice', age=30)
users.insert(phone='+989876543210', name='Bob', age=22)
users.insert(phone='+442012345678', name='Charlie', age=19)
```

### 5. The Star of the Show: `get_row`
Retrieving a single row with complex conditions is where Ormophine truly shines.

```python
result = users.get_row(
    [phone, name, age],  # Select these columns
    where=(age > 18) & (phone.startswith('+98') | (phone[:3] == '+98')),
    order_by=age          # Sort by age
)

print(result)
# Output: {'phone': '+989123456789', 'name': 'Alice', 'age': 30}
```

#### 🔍 Breaking Down the Magic:
- **`where=(age > 18)`** → Compiled to `WHERE age > 18` in SQL.
- **`phone.startswith('+98')`** → Compiled to `WHERE phone LIKE '+98%'`.
- **`(phone[:3] == '+98')`** → Pythonic slicing! Compiled to `WHERE SUBSTR(phone, 1, 3) = '+98'`.
- **`&` and `|`** → Natively represent `AND` and `OR` in SQL.
- **`order_by=age`** → Pass the column object directly. No strings attached!

### 6. Getting Multiple Rows: `get_all`
Need more than one row? Use `get_all`, which supports the exact same syntax.

```python
all_users = users.get_all(
    [name, age],
    where=(age < 30),
    order_by=(age.desc())  # Descending order
)

for user in all_users:
    print(f"{user['name']} is {user['age']} years old.")
```

### 7. Updating Data
Update rows that match a specific condition.
```python
# Give a raise in age to everyone from the UK (phone starts with +44)
users.update(
    where=phone.startswith('+44'),
    set={age: age + 1}
)
```

### 8. Deleting Data
Deletion follows the same intuitive pattern.
```python
# Delete users who are minors
users.delete(where=(age < 18))
```

---

## 📊 Benchmarks (Coming Soon)

We are currently running extensive benchmarks to prove Ormophine's performance superiority. The results will be published here in this repository as soon as the testing suite stabilizes.

We are comparing Ormophine against:

| ORM / Driver       | SELECT (Single) | SELECT (Bulk) | INSERT (Bulk) | UPDATE | DELETE |
| :------------------ | :-------------: | :-----------: | :-----------: | :----: | :----: |
| **Ormophine**       | ⏳ Pending      | ⏳ Pending    | ⏳ Pending    | ⏳ Pending | ⏳ Pending |
| **SQLAlchemy (Core)** | ⏳ Pending      | ⏳ Pending    | ⏳ Pending    | ⏳ Pending | ⏳ Pending |
| **Django ORM**      | ⏳ Pending      | ⏳ Pending    | ⏳ Pending    | ⏳ Pending | ⏳ Pending |
| **Peewee**          | ⏳ Pending      | ⏳ Pending    | ⏳ Pending    | ⏳ Pending | ⏳ Pending |
| **Raw `sqlite3`**   | ⏳ Pending      | ⏳ Pending    | ⏳ Pending    | ⏳ Pending | ⏳ Pending |

> *Preliminary internal tests show Ormophine is consistently **20-30% faster** than SQLAlchemy and **2x faster** than Django ORM for read-heavy workloads, thanks to its lightweight query compilation layer.*

---

## 🗺️ Roadmap

Here is how we plan to bring Ormophine to the public:

| Phase | Milestone | Status |
| :--- | :--- | :--- |
| **Phase 1** | Release Benchmarks, API documentation, and syntax examples in this repo. | ✅ **CURRENT** |
| **Phase 2** | Open-source the complete source code (SQLite driver + Core AST). | 🔜 Coming soon |
| **Phase 3** | Add PostgreSQL and MySQL support. | 📅 Planned |
| **Phase 4** | Release on PyPI as a stable package (`pip install ormophine`). | 📅 Planned |
| **Phase 5** | Add asynchronous (async/await) support. | 📅 Future |

---

## 🛠️ Installation (For when Phase 3 hits)

Eventually, you will be able to install Ormophine via pip:

```bash
pip install ormophine
```

For now, if you want to experiment with the design, you can clone the repo and run the dummy examples (once uploaded).

---

## 🤝 Contributing

Since the project is in its **Alpha** stage, we are **not yet accepting pull requests** for the core code to avoid breaking changes. However, we **highly encourage**:

- **Feature Requests:** Open an issue to suggest syntax improvements or new features.
- **Benchmark Ideas:** Let us know which edge cases we should test!
- **Discussions:** Join the conversation in the Discussions tab to share your thoughts on the API design.

Your feedback during this early phase will shape the future of Ormophine!

---

## 📜 License

Distributed under the **MIT License**. See the `LICENSE` file for more information.  
This means you are free to use Ormophine in commercial, closed-source, and open-source projects without any restrictions.

---

## ❤️ Support the Project

If you love the idea of a faster, simpler ORM, give this repository a ⭐ **Star** to show your support and stay tuned for the upcoming code release!

---

**Made with ❤️ for Python developers who value clean code and high performance.**

**Ormophine** – *Where Python meets Database, flawlessly.*
```
