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

- **Thread-safe database access**: Dedicated writer queue for SQLite and connection pooling for MySQL/PostgreSQL.
- **Optional reader-pool support**: Non-blocking read operations for high-performance workloads.
- **Pythonic Expressions**: Overloaded Python operators and string methods (e.g., ``startswith()``, ``column[2:5]``) translate directly to SQL.
- **Fluent Schema Construction**: Build tables programmatically using ``TableStructure`` and ``DataTypes``.
- **Dynamic Table Objects**: Existing tables are automatically discovered and exposed as attributes on the driver instance (e.g., ``db.users``).
- **Batch Transactions**: Efficient grouped inserts and updates.
- **Advanced Join Helpers**: Intuitive multi-table querying.
- **Database Administration**: Built-in PRAGMA management for SQLite, and user/permission management for MySQL/PostgreSQL.

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