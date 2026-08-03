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
   :members:
   :undoc-members:
   :show-inheritance:

TableStructure
--------------

.. autoclass:: TableStructure
   :members:
   :undoc-members:
   :show-inheritance:

DataTypes
---------

.. autoclass:: DataTypes
   :members:
   :undoc-members:
   :show-inheritance:

Table
-----

.. autoclass:: Table
   :members:
   :undoc-members:
   :show-inheritance:

Join
----

.. autoclass:: Join
   :members:
   :undoc-members:
   :show-inheritance:
