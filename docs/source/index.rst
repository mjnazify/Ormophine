AI-Powered Assistance
=======================

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

When working directly from the source repository, they are simply at the top‑level folder.

**Recommended prompt**

.. code-block:: text

   You are an expert in the Ormophine ORM for {SQLite/MySQL/PostgreSQL}.
   The attached file contains the complete source code of that library.
   Answer all questions based solely on this code.
   Be concise, practical and include relevant code examples.

**Example usage**

#. Locate the reference file for your database (e.g., ``Sqlite.AI.Reference.txt``) in the Ormophine installation directory.
#. Open your preferred AI chat.
#. Paste the prompt above, replacing ``{SQLite/MySQL/PostgreSQL}`` with your backend.
#. Attach the ``.txt`` file.
#. Ask your question – for instance, *"How do I perform a bulk update with dynamic values?"*

The AI will then consult the real implementation and provide an accurate, version‑specific answer.

Ormophine Documentation
=======================

Ormophine is a lightweight, fast, and highly Pythonic ORM for modern database-driven
applications. It provides a unified programming model for SQLite, MySQL, and PostgreSQL
while keeping SQL generation and database interaction straightforward for Python developers.

The design goal is to feel natural in Python rather than like a separate query DSL. In
practice this means you work with dynamic table and column objects, build filters with
Python operators, and use expression helpers that behave like familiar Python string APIs.
For example, the project simulates Python string behavior for expressions such as
``"a" + "b"`` together with helpers like ``lower()``, ``upper()``, ``startswith()``,
``endswith()``, ``strip()``, ``lstrip()``, ``rstrip()``, and ``replace()``. The same
style is also used for slice expressions such as ``column[2:5]`` so the query syntax stays
close to regular Python code. Additional Python-style string methods are planned to be
simulated in future releases.

The public API should be imported from the database-specific package root, for example:

.. code-block:: python

   from Ormophine.Sqlite import Driver, Table, TableStructure, DataTypes

This documentation focuses on the supported public classes and helpers that developers
actually use when building applications with Ormophine.

Overview
--------

Ormophine offers a practical set of features for high-performance database work:

- Thread-safe database access through a dedicated writer queue
- Optional reader-pool support for non-blocking read operations
- Fluent schema construction with ``TableStructure`` and ``DataTypes``
- Dynamic table objects exposed directly from the driver instance
- Pythonic column expression building with operator-overloaded conditions
- Built-in-like string helpers such as ``startswith()``, ``endswith()``, and slice syntax
  like ``column[2:5]``
- Batch transaction support for grouped inserts and updates
- Join helpers for multi-table queries
- Direct SQL execution helpers for advanced use cases
- PRAGMA management for SQLite tuning and operational control

The source code and API reference in this guide are organized around the public package
exports rather than the internal ``Core`` module implementation details.

Documentation map
------------------

.. toctree::
   :maxdepth: 2

   api/modules