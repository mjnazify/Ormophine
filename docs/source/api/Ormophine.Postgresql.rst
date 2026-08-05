PostgreSQL API
==============

The PostgreSQL backend exposes the same public ORM style as the other database drivers.
Use the package-level imports for application code so the documentation stays aligned with
how the library is intended to be consumed.

Like the other backends, it is meant to be both fast and Pythonic: the resulting query
expressions are built with normal Python operators and familiar string-style helpers such
as ``startswith()``, ``endswith()``, and slicing such as ``column[2:5]``.

.. currentmodule:: Ormophine.Postgresql

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


