:orphan:

.. _quickstart-mysql:

MySQL Quickstart
========================

This guide will walk you through the basics of using **Ormophine** with a MySQL database. You'll learn how to connect, define tables, perform CRUD operations, and leverage ``ColumnsOperation`` for complex queries.

.. note::

   Ormophine is a **dynamic ORM** – you never write model classes.
   * Tables and columns become Python **attributes** at runtime.
   * Connecting to an existing database automatically discovers all tables and columns; newly created tables are instantly available as attributes.

Importing the ORM
------------------

All core classes are available from the ``Ormophine.MySQL`` module:

.. code-block:: python

    from Ormophine.MySQL import Driver, TableStructure, DataTypes, Join

.. hint::

   ``Driver`` manages the connection pool.  
   ``TableStructure`` defines a table schema.  
   ``DataTypes`` provides MySQL data type strings (e.g., ``INT()``, ``VARCHAR()``).  
   ``Join`` is used for JOIN queries.

Connecting to a MySQL Database
------------------------------

Create a ``Driver`` instance with your MySQL credentials. The driver immediately connects and **discovers all existing tables**:

.. code-block:: python

    db = Driver(
        host="localhost",
        port=3306,
        username="root",
        password="your_password",
        db_name="mydatabase"
        # charset="utf8mb4",          # optional
        # pool_size=5                 # connection pool size
    )

    # All existing tables are now available as attributes of `db`.
    # Example: if a table named 'users' already exists, you can access it via `db.users`.

If the database does not exist yet, you can create it on connection by setting ``create_new_db=True``:

.. code-block:: python

    db = Driver(..., create_new_db=True)

You can list existing tables with:

.. code-block:: python

    print(db.get_tables())   # list of table names

Creating Your First Table
-------------------------

Use ``TableStructure`` to design a table, then call ``db.create_table()``:

.. code-block:: python

    # Define a 'users' table
    users_schema = TableStructure("users")

    # Add columns using MySQL data types from the DataTypes class
    users_schema.add_column(
        "id", DataTypes.INT(unsigned=True),
        primary_key=True,
        auto_increment=True
    )
    users_schema.add_column(
        "username", DataTypes.VARCHAR(50),
        unique=True, not_null=True
    )
    users_schema.add_column(
        "age", DataTypes.TINYINT(),
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
    # 'id' auto‑increments because it's an auto_increment primary key.

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

        products_schema = TableStructure("products")
        products_schema.add_column("id", DataTypes.INT(unsigned=True), primary_key=True, auto_increment=True)
        products_schema.add_column("name", DataTypes.VARCHAR(100))
        products_schema.add_column("price", DataTypes.DECIMAL(10, 2))
        products_schema.add_column("discount", DataTypes.DECIMAL(4, 3))  # e.g., 0.100
        products_schema.add_column("category", DataTypes.VARCHAR(50))

        products = db.create_table(products_schema)

2. **Insert sample data**

   .. code-block:: python

        products.bulk_insert(
            columns=[products.name, products.price, products.discount, products.category],
            data_list=[
                ("Widget", 19.99, 0.100, "gadgets"),
                ("Gadget Pro", 49.99, 0.200, "gadgets"),
                ("SuperTool", 29.99, 0.000, "tools"),
                ("MegaWidget", 99.99, 0.250, "gadgets"),
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
            print(f"{name}: ${float(price):.2f}")
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
            print(f"{name}: ${float(price)}")
        # Widget: $19.99, MegaWidget: $99.99

5. **Update using a calculation** – apply extra discount

   .. code-block:: python

        # Increase discount by 5 percentage points where discount < 20%
        new_discount = products.discount + 0.050
        products.update(
            update={products.discount: new_discount},
            where=products.discount < 0.200
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
    batch.insert({products.name: "Hammer", products.price: 12.50, products.discount: 0.000, products.category: "tools"})
    batch.update(
        update={products.price: products.price * 1.1},  # 10% price increase
        where=products.discount == 0.000
    )
    batch.run()   # both operations execute in a single transaction

Joining Tables
----------------

Assume we have an ``orders`` table referencing ``products``.

.. code-block:: python

    orders_schema = TableStructure("orders")
    orders_schema.add_column("id", DataTypes.INT(unsigned=True), primary_key=True, auto_increment=True)
    orders_schema.add_column("product_id", DataTypes.INT(unsigned=True))
    orders_schema.add_column("quantity", DataTypes.INT(unsigned=True))
    orders = db.create_table(orders_schema)

    orders.insert({orders.product_id: 1, orders.quantity: 3})
    orders.insert({orders.product_id: 2, orders.quantity: 1})
    orders.insert({orders.product_id: 4, orders.quantity: 5})

Now join ``orders`` with ``products``:

.. code-block:: python

    from Ormophine.MySQL import Join  # if not already imported

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

   The API Reference covers all available methods for ``Driver``, ``Table``, ``ColumnsOperation``, ``DataTypes``, and ``Join``. Explore it to discover even more functionality like string slicing (``column[1:5]``), pattern matching (``.startswith()``, ``.endswith()``), and bulk operations with placeholders.