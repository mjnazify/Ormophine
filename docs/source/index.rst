Ormophine Documentation
=======================

Ormophine is a lightweight, fast, and highly Pythonic ORM for modern database-driven
applications. It provides a unified programming model for SQLite, MySQL, and PostgreSQL
while keeping SQL generation and database interaction straightforward for Python developers.

The design goal is to feel natural in Python rather than like a separate query DSL. In
practice, this means you work with dynamic table and column objects, build filters with
Python operators, and use expression helpers that behave like familiar Python string APIs.

For example, the project simulates Python string behavior for expressions such as
``"a" + "b"`` together with helpers like ``lower()``, ``upper()``, ``startswith()``,
``endswith()``, ``strip()``, and slice syntax like ``column[2:5]``. The same style is also
used for arithmetic operations, so the query syntax stays close to regular Python code.

.. code-block:: python

   from Ormophine.Sqlite import Driver, TableStructure, DataTypes

   # 1. Connect to the database
   db = Driver('app.db')

   # 2. Access tables dynamically as attributes
   users = db.users

   # 3. Query using Pythonic operators and string methods
   results = users.get_row(
       which_columns=[users.id, users.name],
       where=(users.name.startswith('A')) & (users.age > 18)
   )

   # 4. Disconnect gracefully
   db.disconnect()

Installation
------------

You can install Ormophine via pip:

.. code-block:: bash

   pip install ormophine

Key Features
------------

- **Intuitive Pythonic Syntax**: Overloaded Python operators, string methods (e.g., ``startswith()``, ``column[2:5]``), and arithmetic operations translate directly to parameterized SQL.
- **Fast & Thread-Safe**: Built on a dedicated writer queue (SQLite) and robust connection pooling (MySQL/PostgreSQL); parallel reads, serialized writes.
- **Fault-Tolerant Connection Pools**: Automatically detects broken connections (e.g., database restarts) and seamlessly recreates them without crashing your application.
- **Multi-Database**: One unified API across SQLite, MySQL, and PostgreSQL. Switch databases by changing your import.
- **Dynamic Schema Mapping**: Existing tables are automatically discovered and exposed as attributes on the driver instance (e.g., ``db.users``).
- **Fluent Schema Construction**: Build tables programmatically using ``TableStructure`` and ``DataTypes``.
- **Batch Transactions**: Efficient grouped inserts and updates.
- **Advanced Join Helpers**: Intuitive multi-table querying.
- **Built-in DB Administration**: Built-in PRAGMA management for SQLite, user/permission management for MySQL/PostgreSQL, and maintenance tasks (like PostgreSQL ``VACUUM``).
- **WAL Mode Support (SQLite)**: Automatic checkpointing for maximum write throughput.

AI-Powered Assistance
---------------------

To help you write queries and debug your Ormophine code, we provide reference files that contain the full source code of the ORM for each backend:

* ``Sqlite.AI.Reference.txt``
* ``MySQL.AI.Reference.txt``
* ``PostgreSQL.AI.Reference.txt``

These files are designed to be sent to any capable AI assistant (such as ChatGPT, Claude, or Gemini). Simply attach the appropriate file along with a short instruction prompt and your question. The AI will then answer using the exact API and behaviour of your Ormophine version.

**Where to find the files**

After installing Ormophine via pip (or cloning the repository), the reference files are located in the **root directory** of the package.  
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

To demonstrate Ormophine's raw performance, we benchmarked it against popular Python ORMs (SQLAlchemy, PonyORM, and Peewee) across SQLite, PostgreSQL, and MySQL.

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
   :maxdepth: 2
   :caption: Quick Start Guides

   Ormophine.Sqlite.QuikStart
   Ormophine.Mysql.QuikStart
   Ormophine.Postgresql.QuikStart

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/modules