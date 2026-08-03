SQLite API
==========

The SQLite backend is the primary public surface of Ormophine. It exposes a
high-level driver object together with schema helpers and table-level query APIs,
while keeping the overall style fast and deliberately Pythonic.

The backend is designed to feel like native Python: table and column objects become
runtime attributes, comparison expressions use operators directly, and string-style
operations such as ``startswith()``, ``endswith()``, and slicing like ``column[2:5]``
remain natural to read.

.. currentmodule:: Ormophine.Sqlite

Driver
------

.. autoclass:: Ormophine.Sqlite.driver.Driver
   :members:
   :undoc-members:
   :show-inheritance:

TableStructure
--------------

.. autoclass:: Ormophine.Sqlite.Core.tablestructure.TableStructure
   :members:
   :undoc-members:
   :show-inheritance:

DataTypes
---------

.. autoclass:: Ormophine.Sqlite.Core.tablestructure.DataTypes
   :members:
   :undoc-members:
   :show-inheritance:

Table
-----

.. autoclass:: Ormophine.Sqlite.Core.table.Table
   :members:
   :undoc-members:
   :show-inheritance:

Join
----

.. autoclass:: Ormophine.Sqlite.Core.join.Join
   :members:
   :undoc-members:
   :show-inheritance:

SetPragma
---------

.. autoclass:: Ormophine.Sqlite.Core.setpragma.SetPragma
   :members:
   :undoc-members:
   :show-inheritance: