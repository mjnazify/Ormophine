MySQL API
=========

The MySQL backend follows the same public pattern as the SQLite package. Applications
should import from the package root rather than from internal implementation namespaces.

The backend is designed to feel like native Python: table and column objects become
runtime attributes, comparison expressions use operators directly, and string-style
operations such as ``startswith()``, ``endswith()``, and slicing like ``column[2:5]``
remain natural to read.

.. currentmodule:: Ormophine.Mysql

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

