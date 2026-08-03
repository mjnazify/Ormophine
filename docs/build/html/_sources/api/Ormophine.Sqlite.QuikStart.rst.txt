:orphan:

.. _quickstart:

Sqlite Quickstart
====================

This guide is designed for first‑time users of **Ormophine**. By the end you will be able to connect to a database, define tables, insert, query, update, delete, and use advanced features like ``ColumnsOperation`` and joins.

.. note::

   Ormophine is a **dynamic ORM** – you never write model classes.  
   * Tables and columns become **Python attributes** automatically.  
   * Whether you create a new table or connect to an existing database, everything is discovered and made available at runtime.

Importing the ORM
------------------

All core classes are available from the ``Ormophine.Sqlite`` module:

.. code-block:: python

    from Ormophine.Sqlite import Driver, TableStructure, DataTypes, Join

.. hint::

   ``Driver`` manages the connection.  
   ``TableStructure`` defines a table schema.  
   ``DataTypes`` provides typed column definitions with optional constraints.  
   ``Join`` is used for JOIN queries.

Connecting to a Database
--------------------------

Create a ``Driver`` instance. This immediately opens the database file and **discovers all existing tables and columns**:

.. code-block:: python

    db = Driver("mydatabase.db")
    # All existing tables are now available as attributes of `db`.
    # Example: if a table named 'users' already exists, you can access it via `db.users`.

For a brand‑new database the file is created, but no tables exist yet. You can check existing tables with:

.. code-block:: python

    print(db.get_tables())   # dict of table names -> Table objects

Creating Your First Table
---------------------------

Use ``TableStructure`` to design a table, then call ``db.create_table()``:

.. code-block:: python

    # Define a 'users' table
    users_schema = TableStructure("users", strict=True)

    # Add columns with type and constraints
    users_schema.add_column(
        "id", DataTypes.INTEGER(),
        primary_key=True
    )
    users_schema.add_column(
        "username", DataTypes.TEXT(max_length=50),
        unique=True, not_null=True
    )
    users_schema.add_column(
        "age", DataTypes.INTEGER(min_val=0),
        default_value=18
    )

    # Create the table – it returns a Table object.
    users = db.create_table(users_schema)
    # The table is now also accessible as `db.users`.

.. important::

   After creation (or after connecting to an existing database), every column becomes an **attribute** of the ``Table`` object. For example, you can refer to ``users.username``, ``users.age``, etc. This makes writing queries natural and safe.

Inserting Data
----------------

Single insert using a dictionary where **keys are the column attributes**:

.. code-block:: python

    users.insert({
        users.username: "alice",
        users.age: 25
    })
    # If 'id' is an INTEGER PRIMARY KEY it auto‑increments.

Bulk insert for multiple rows:

.. code-block:: python

    users.bulk_insert(
        columns=[users.username, users.age],
        data_list=[
            ("bob", 30),
            ("charlie", 22),
            ("diana", 28),
        ]
    )

Querying Data – Simple Queries
---------------------------------

The ``get_row()`` method retrieves rows. You can choose which columns to fetch, apply a ``WHERE`` condition, and order the results.

.. code-block:: python

    # Fetch usernames and ages, ordered by age
    all_users = users.get_row(
        which_columns=[users.username, users.age],
        order_by=users.age
    )
    for row in all_users:
        print(row)  # e.g., ('charlie', 22), ('alice', 25), ...

Filtering uses ``ColumnsOperation`` – these are created by using comparison operators on column attributes:

.. code-block:: python

    # Users older than 24
    condition = users.age > 24
    older_users = users.get_row(
        which_columns=[users.username],
        where=condition
    )
    for (username,) in older_users:
        print(username)  # alice, bob, diana

.. tip::

   All column attributes return a ``ColumnsOperation`` when used with operators like ``>``, ``==``, ``+``, ``.like()``, etc. This allows you to build expressive SQL expressions directly in Python.

Updating Data
---------------

Update rows that match a condition. You can assign a constant value or an expression based on the current column value.

.. code-block:: python

    # Increase age by 1 for all users under 30
    condition = users.age < 30
    users.update(
        update={users.age: users.age + 1},   # using ColumnsOperation
        where=condition
    )

Deleting Data
---------------

Delete rows matching a condition:

.. code-block:: python

    # Remove user 'charlie'
    condition = users.username == "charlie"
    users.delete_row(where=condition)

Complex Example with ColumnsOperation
----------------------------------------

Now let’s see a more advanced scenario with a ``products`` table. We’ll use arithmetic, string manipulations, and combine conditions.

1. **Create the products table**

   .. code-block:: python

        products_schema = TableStructure("products", strict=True)
        products_schema.add_column("id", DataTypes.INTEGER(), primary_key=True)
        products_schema.add_column("name", DataTypes.TEXT())
        products_schema.add_column("price", DataTypes.REAL(min_val=0.0))
        products_schema.add_column("discount", DataTypes.REAL(min_val=0.0, max_val=1.0))
        products_schema.add_column("category", DataTypes.TEXT())

        products = db.create_table(products_schema)

2. **Insert sample data**

   .. code-block:: python

        products.bulk_insert(
            columns=[products.name, products.price, products.discount, products.category],
            data_list=[
                ("Widget", 19.99, 0.1, "gadgets"),
                ("Gadget Pro", 49.99, 0.2, "gadgets"),
                ("SuperTool", 29.99, 0.0, "tools"),
                ("MegaWidget", 99.99, 0.25, "gadgets"),
            ]
        )

3. **Arithmetic expression** – compute final price and filter

   .. code-block:: python

        # final_price = price * (1 - discount)
        final_price = products.price * (1 - products.discount)
        condition = final_price > 30

        result = products.get_row(
            which_columns=[products.name, final_price],
            where=condition,
            order_by=final_price
        )

        for name, price in result:
            print(f"{name}: ${price:.2f}")
        # Output: Gadget Pro: $39.99, MegaWidget: $74.99

4. **String operations** – case‑insensitive search

   .. code-block:: python

        # Gadgets whose name contains "widget" (case‑insensitive)
        condition = (products.category == "gadgets") & (products.name.lower().contains("widget"))

        gadget_widgets = products.get_row(
            which_columns=[products.name, products.price],
            where=condition
        )
        for name, price in gadget_widgets:
            print(f"{name}: ${price}")
        # Widget: $19.99, MegaWidget: $99.99

5. **Update using a calculation** – apply extra discount

   .. code-block:: python

        # Increase discount by 5 percentage points where discount < 20%
        new_discount = products.discount + 0.05
        products.update(
            update={products.discount: new_discount},
            where=products.discount < 0.2
        )

6. **Deleting with a string condition**

   .. code-block:: python

        # Remove all tools
        products.delete_row(where=products.category == "tools")

Batch Operations – Transactions
--------------------------------

For multiple statements that must run atomically, use ``batch()``:

.. code-block:: python

    batch = products.batch()
    batch.insert({products.name: "Hammer", products.price: 12.50, products.discount: 0.0, products.category: "tools"})
    batch.update(
        update={products.price: products.price * 1.1},  # 10% price increase
        where=products.discount == 0.0
    )
    batch.run()   # both operations execute in a single transaction

Joining Tables
----------------

Assume we have an ``orders`` table referencing ``products``.

.. code-block:: python

    orders_schema = TableStructure("orders")
    orders_schema.add_column("id", DataTypes.INTEGER(), primary_key=True)
    orders_schema.add_column("product_id", DataTypes.INTEGER())
    orders_schema.add_column("quantity", DataTypes.INTEGER(min_val=1))
    orders = db.create_table(orders_schema)

    orders.insert({orders.product_id: 1, orders.quantity: 3})
    orders.insert({orders.product_id: 2, orders.quantity: 1})
    orders.insert({orders.product_id: 4, orders.quantity: 5})

Now join ``orders`` with ``products``:

.. code-block:: python

    from Ormophine.Sqlite import Join  # if not already imported

    join_condition = orders.product_id == products.id

    columns = [
        orders.id,
        products.name,
        orders.quantity,
        products.price * orders.quantity   # total cost
    ]

    result = orders.join(
        columns=columns,
        joins_list=[Join.Inner(products, join_condition)],
        order_by=orders.id
    )

    for row in result:
        print(row)  # (order_id, product_name, quantity, total_cost)

.. seealso::

   The API Reference covers all available methods for ``Driver``, ``Table``, ``ColumnsOperation``, ``DataTypes``, and ``Join``. Explore it to discover even more functionality like string slicing (``column[1:5]``), regex‑like patterns (``.startswith()``, ``.endswith()``), and bulk operations with placeholders.