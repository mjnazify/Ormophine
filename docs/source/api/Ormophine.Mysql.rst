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

.. autoclass:: Ormophine.Mysql.driver.Driver
   :members:
   :undoc-members:
   :show-inheritance:

TableStructure
--------------

.. autoclass:: Ormophine.Mysql.Core.tablestructure.TableStructure
   :members:
   :undoc-members:
   :show-inheritance:

DataTypes
---------

.. autoclass:: Ormophine.Mysql.Core.tablestructure.DataTypes
   :members:
   :undoc-members:
   :show-inheritance:

Table
-----

.. autoclass:: Ormophine.Mysql.Core.table.Table
   :members:
   :undoc-members:
   :show-inheritance:

Join
----

.. autoclass:: Ormophine.Mysql.Core.join.Join
   :members:
   :undoc-members:
   :show-inheritance: