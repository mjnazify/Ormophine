API Reference
=============

The public API of Ormophine is exposed from its database-specific packages. In practice,
application code uses imports such as:

.. code-block:: python

   from Ormophine.Sqlite import Driver, Table, TableStructure, DataTypes
   from Ormophine.Mysql import Driver as MySqlDriver
   from Ormophine.Postgresql import Driver as PostgresDriver

Ormophine is intentionally designed to stay close to Python itself. Instead of forcing a
separate query language, the library lets you express conditions and value transforms with
Python operators and built-in-like helpers such as ``startswith()``, ``endswith()``, and
slice notation like ``column[2:5]``.

.. toctree::
   :maxdepth: 1
   :titlesonly:

   Ormophine.Sqlite.QuickStart
   Ormophine.Sqlite
   Ormophine.Mysql.QuickStart
   Ormophine.Mysql
   Ormophine.Postgresql.QuickStart
   Ormophine.Postgresql