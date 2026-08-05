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
.. autoclass:: Driver
   :no-index:
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:
   :member-order: bysource

Table
-----
.. autoclass:: Table
   :no-index:
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:
   :member-order: bysource

BatchOperation
--------------
.. autoclass:: BatchOperation
   :no-index:
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:
   :member-order: bysource

ColumnsOperation
----------------
.. autoclass:: ColumnsOperation
   :no-index:
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:
   :member-order: bysource

Column
------
.. autoclass:: Column
   :no-index:
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:
   :member-order: bysource

Join
----
.. autoclass:: Join
   :no-index:
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:
   :member-order: bysource

TableStructure
--------------
.. autoclass:: TableStructure
   :no-index:
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:
   :member-order: bysource

DataTypes
---------
.. autoclass:: DataTypes
   :no-index:
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:
   :member-order: bysource

SetPragma
---------
.. autoclass:: SetPragma
   :no-index:
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:
   :member-order: bysource