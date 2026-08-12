Ormophine Documentation
=======================

Ormophine is the simplest Python ORM. It lets you write database queries in plain Python —
no models to define, no DSL to learn, no boilerplate to write.

The design follows one rule: **if it reads like Python, it's right. If you have to look up
how to write it, it's wrong.**

Most Python ORMs were built for enterprise complexity — layers of abstractions, session
lifecycles, model definitions, and migration pipelines. They're powerful, but they make
simple things hard. Ormophine is built on a different premise:

**90% of database work is simple CRUD. The ORM for that work should be simple too.**

With Ormophine, columns behave like native Python values. You call ``.lower()``,
``.startswith()``, and slice with ``[2:5]`` — exactly as you would in Python — and
Ormophine translates them into the correct SQL functions under the hood. Arithmetic,
concatenation, and logical operators work the same way. You never have to think about
how to express your logic in SQL.

.. code-block:: python

   from Ormophine.Sqlite import Driver

   # Connect — one import, one line
   db = Driver('app.db')

   # Tables appear as attributes automatically — no models, no definitions
   users = db.users

   # Query using plain Python syntax
   results = users.get_row(
       which_columns=[users.name, users.age],
       where=(users.name.lower().startswith('a')) & (users.age >= 18),
       order_by=users.age
   )

   # Disconnect gracefully
   db.disconnect()

That's it. Read it like Python, it runs like SQL.

Installation
------------

Install Ormophine via pip:

.. code-block:: bash

   pip install ormophine

What Makes Ormophine Simple
---------------------------

Columns Are Python Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Other ORMs give you column objects that you must wrap in helper functions. Ormophine
columns **behave like native Python values**:

.. code-block:: python

   # String methods — just call them
   users.name.lower()
   users.name.startswith('A')

   # Slicing — just like Python strings
   users.code[:3]          # first 3 characters
   users.lastname[5:-2]    # from index 5, drop last 2

   # Arithmetic — just like Python numbers
   users.price * users.qty - users.discount

   # Concatenation — the + operator works naturally
   users.first_name + ' ' + users.last_name

   # Logic — combine with & and |
   (users.age >= 18) & (users.status == 'active')

All of these are translated to the correct SQL under the hood. All values are
automatically parameterized — **SQL injection is prevented by design, not by discipline.**

No Models, No Boilerplate
^^^^^^^^^^^^^^^^^^^^^^^^^

You don't define classes. You don't declare fields. You don't bind tables to a metadata
registry. You connect, and everything is there:

.. code-block:: python

   db = Driver('my.db')

   users  = db.users     # it just exists
   orders = db.orders    # this too

   # Columns appear as attributes
   users.name    # column object
   users.age     # column object

Auto-Commit by Default
^^^^^^^^^^^^^^^^^^^^^^

Every insert, update, and delete commits automatically. No ``session.commit()``.
No ``with engine.begin()``. For batch operations, use ``.batch()`` — otherwise,
each operation stands on its own.

.. code-block:: python

   # This is a complete, working operation. Nothing else needed.
   users.insert({users.name: 'Alice', users.age: 30})

One API, Three Databases
^^^^^^^^^^^^^^^^^^^^^^^^

Switching databases is a one-line import change. The API stays identical:

.. code-block:: python

   # SQLite
   from Ormophine.Sqlite import Driver
   db = Driver('my.db')

   # MySQL
   from Ormophine.Mysql import Driver
   db = Driver(host='localhost', port=3306, username='root', password='pass', db_name='my_db')

   # PostgreSQL
   from Ormophine.Postgresql import Driver
   db = Driver(host='localhost', port=5432, username='postgres', password='pass', db_name='my_db')

Same ``.insert()``, same ``.get_row()``, same ``.update()``, same ``.batch()``.
Learn once, use anywhere.

Key Features
------------

- **Zero Learning Curve**: If you know Python, you know Ormophine. Columns are variables, methods are methods, slicing is slicing, operators are operators. There is no DSL, no special syntax, nothing to look up.
- **Reads Like English**: ``users.name.lower().startswith('a')`` says exactly what it does. Compare that to ``func.lower(users.c.name).like('a%')``.
- **Dynamic Schema Discovery**: Existing tables are automatically discovered and exposed as attributes on the driver instance (e.g., ``db.users``). No model definitions. No reflection boilerplate.
- **Auto-Commit Simplicity**: Every write operation commits immediately by default. No session management. For atomic multi-step operations, the ``.batch()`` builder is one ``batch.run()`` call.
- **Fast & Thread-Safe**: Built on a dedicated writer queue (SQLite) and robust connection pooling (MySQL/PostgreSQL); parallel reads, serialized writes.
- **Fault-Tolerant Connection Pools**: Automatically detects broken connections (e.g., database restarts) and seamlessly recreates them without crashing your application.
- **Multi-Database**: One unified API across SQLite, MySQL, and PostgreSQL. Switch databases by changing your import.
- **Built-in DB Administration**: Built-in PRAGMA management for SQLite, user/permission management for MySQL/PostgreSQL, and maintenance tasks (like PostgreSQL ``VACUUM``).
- **WAL Mode Support (SQLite)**: Automatic checkpointing for maximum write throughput.

Python → SQL Reference
-----------------------

This is a small list of Python expressions that Ormophine translates into SQL.
Every value is automatically parameterized — SQL injection is prevented by design,
not by discipline.

==============================  ========================================  =====================
Python Expression                SQL Equivalent                            What it does
==============================  ========================================  =====================
``age > 18``                     ``age > 18``                              Comparison
``(age >= 18) & (age < 65)``    ``age >= 18 AND age < 65``                Logical AND
``age == 18``                    ``age = 18``                              Equality
``name.startswith('A')``        ``name LIKE 'A%'``                        Prefix match
``name.endswith('.com')``       ``name LIKE '%.com'``                     Suffix match
``email.contains('@corp')``     ``email LIKE '%@corp%'``                  Substring match
``code[:3]``                    ``SUBSTR(code, 1, 3)``                    Slice from start
``code[2:5]``                   ``SUBSTR(code, 3, 3)``                    Slice with start/end
``name[-4:]``                   ``SUBSTR(name, -4)``                      Slice from end
``name.lower()``                ``LOWER(name)``                           Lowercase
``name.upper()``                ``UPPER(name)``                           Uppercase
``name.strip()``                ``TRIM(name)``                            Strip whitespace
``name + ' suffix'``            ``name || ' suffix'``                     String concatenation
``price * qty - discount``      ``price * qty - discount``                Arithmetic
``price + 10``                  ``price + 10``                            Arithmetic with literal
==============================  ========================================  =====================

No ``func.``, no ``fn.``, no ``F()``, no ``.annotate()``. Just Python.

AI-Powered Assistance
---------------------

To help you write queries and debug your Ormophine code, we provide reference files that
contain the full source code of the ORM for each backend:

* ``Sqlite.AI.Reference.txt``
* ``MySQL.AI.Reference.txt``
* ``PostgreSQL.AI.Reference.txt``

These files are designed to be sent to any capable AI assistant (such as ChatGPT, Claude,
or Gemini). Simply attach the appropriate file along with a short instruction prompt and
your question. The AI will then answer using the exact API and behaviour of your
Ormophine version.

**Where to find the files**

After installing Ormophine via pip (or cloning the repository), the reference files are
located in the **root directory** of the package.
For example, if you installed the package in a virtual environment, you can find them at:

.. code-block:: text

   path/to/venv/lib/python3.x/site-packages/Ormophine/{Sqlite,MySQL,PostgreSQL}.AI.Reference.txt

**Recommended Prompt**

.. code-block:: text

   You are an expert in the Ormophine ORM for {SQLite/MySQL/PostgreSQL}.
   The attached file contains the complete source code of that library.
   Answer all questions based solely on this code.
   Be concise, practical and include relevant code examples.

⚡ Benchmark Results
--------------------

Ormophine is simple — but it's not slow. We benchmarked it against popular Python ORMs
(SQLAlchemy, PonyORM, and Peewee) across SQLite, PostgreSQL, and MySQL.

Methodology
^^^^^^^^^^^
We evaluate two distinct scenarios to measure both transactional overhead and bulk efficiency:

1. **Single Operations:** Measures the time taken to execute CRUD queries where a ``COMMIT`` is issued immediately after *every single* insert, update, and delete. This tests the ORM's baseline overhead and connection management for isolated transactions.
2. **Batch Operations:** Measures the time taken to execute a block of CUD (Create, Update, Delete) queries where all statements are executed first, and a single ``COMMIT`` is issued at the end. This tests the ORM's efficiency in bulk transactional processing.

.. note::
   Due to natural system fluctuations, each test run can have a variance of up to ±10%. Therefore, performance differences of less than 5% are considered statistically insignificant (margin of error). In the charts, differences under 5% are displayed in gray and marked as "≈ Equal".

Run the Benchmarks Yourself
^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can access the benchmark Jupyter notebooks in the project repository at ``Ormophine/{Sqlite, Postgresql, Mysql}/Benchmark``.

You can also use these Google Colab notebooks to run the tests instantly:

* **SQLite:** https://colab.research.google.com/drive/1KK3sr8H_Crd29fmnq3VmpmE88aLNT3Yr?usp=sharing
* **MySQL:** https://colab.research.google.com/drive/1ndwmN0C9UTZHTNmLh8-fT9rEg-DSrzHQ?usp=sharing
* **PostgreSQL:** https://colab.research.google.com/drive/1XYrC30vUciS1YgY6M5MBoxwO9YTltzkD?usp=sharing

For detailed visual charts and per-operation breakdowns, please refer to the `Benchmark Section in the GitHub README <https://github.com/yourusername/ormophine#-benchmark-results>`_.

Documentation Map
-----------------

.. toctree::
   :maxdepth: 8
   :caption: API Reference

   api/modules