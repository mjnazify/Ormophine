MySQL API
=========

The MySQL backend follows the same public pattern as the SQLite package. Applications
should import from the package root rather than from internal implementation namespaces.

It is built to stay lightweight and expressive, with a Pythonic query style that keeps
expression building close to normal Python code. That includes Python-alike condition
syntax and string helpers such as ``startswith()``, ``endswith()``, and slice-style
operations like ``column[2:5]``.

.. currentmodule:: Ormophine.Mysql

Driver
------

.. autoclass:: Driver

TableStructure
--------------

.. autoclass:: TableStructure

DataTypes
---------

.. autoclass:: DataTypes

Table
-----

.. autoclass:: Table

Join
----

.. autoclass:: Join