:orphan:

.. _quickstart_postgresql:

=======================================================
Ormophine PostgreSQL ORM — Complete Quickstart Guide
=======================================================

Welcome to the comprehensive, step-by-step developer guide for the **Ormophine PostgreSQL ORM**.

Ormophine is a modern, thread-safe, dynamic Python ORM designed specifically for PostgreSQL databases. It eliminates boilerplate model classes through **automatic table and column reflection**, provides full type-safety and Pylance autocomplete via type hinting, and compiles Pythonic expressions directly into optimized PostgreSQL SQL using safe ``%s`` parameterization.

.. contents:: Table of Contents
   :depth: 2
   :local:

--------------------------------------------------------------------------------

.. _pg-real-quickstart:

0. ⚡ 60-Second Real Quickstart: Auto-Discovery & Instant CRUD
==============================================================

When you connect to an existing PostgreSQL database:

1. All existing tables are **automatically discovered** as attributes on the ``db`` driver instance (e.g., ``db.users``).
2. All columns are **automatically available** as attributes (e.g., ``users.username``).
3. You can unpack columns with **type hints** (``username: Column = users.username``) for IDE autocompletion and clean, concise code!

Setup: Creating Sample Database & Table
---------------------------------------

If you have an existing PostgreSQL server, you can connect directly. Here is a quick preview:

.. code-block:: python

    from Ormophine.Postgresql import Driver, Column

    # 1. Connect to PostgreSQL database (with thread-safe connection pooling)
    db_quick = Driver(
        host="localhost",
        port=5432,
        username="postgres",
        password="your_password",
        db_name="quickstart_demo_db",
        pool_size=5
    )

    # 2. Auto-Discovery: Tables and columns are ready automatically!
    users = db_quick.users

    # Pro-Tip: Unpack columns with type hints for IDE autocomplete (Pylance)
    # Now you can use 'username' and 'age' directly instead of 'users.username'!
    id: Column = users.id
    username: Column = users.username
    age: Column = users.age
    balance: Column = users.balance

    # 3. Quick Insert
    users.insert({username: "eva", age: 24, balance: 150.0})

    # 4. Powerful Multi-Feature Query:
    # - String Concat (+): 'VIP: ' + username.upper()
    # - String Slicing: username[0:3]
    # - Column Math: balance * 1.05 (5% bonus)
    # - Inline If/Else: username.If(age >= 25).Else('Junior User')
    # - Combined WHERE (& and |): age >= 20 AND (starts with 'a' OR balance >= 150)
    vip_label = "VIP: " + username.upper() + " [" + username[0:3] + "]"
    bonus_balance = balance * 1.05
    user_tier = username.If(age >= 25).Else("Junior User")

    query_results = users.get_row(
        which_columns=[id, vip_label, bonus_balance, user_tier],
        where=(age >= 20) & (username.startswith("a") | (balance >= 150.0)),
        order_by=age
    )

    print("⚡ Quickstart Query Results:")
    for u_id, label, new_bal, tier in query_results:
        print(f"  ID: {u_id} | {label:<18} | Bonus Bal: ${new_bal:6.2f} | Status: {tier}")

    # 5. Quick Update & Delete
    users.update(update={balance: balance + 50.0}, where=age < 25)
    users.delete_row(where=username == "charlie")

    # Clean shutdown
    db_quick.disconnect()

--------------------------------------------------------------------------------

1. Getting Started & Database Connection
========================================

Importing the Core Classes
--------------------------

All core classes are available from the ``Ormophine.Postgresql`` module:

.. code-block:: python

    from Ormophine.Postgresql import Driver, TableStructure, DataTypes, Builtins, Column

* ``Driver``: Manages connection pooling, transactions, and worker queries.
* ``TableStructure``: Defines table schemas, column types, constraints, and foreign keys.
* ``DataTypes``: Provides PostgreSQL native types (``SERIAL``, ``VARCHAR``, ``INTEGER``, ``NUMERIC``, etc.).
* ``Builtins``: Static namespace for PostgreSQL built-in functions (covered in Section 12).
* ``Column``: Type hint class for IDE autocompletion (VS Code / Pylance).

Initializing the Connection Pool
--------------------------------

Initialize a ``Driver`` instance with your PostgreSQL credentials:

.. code-block:: python

    db = Driver(
        host="localhost",
        port=5432,
        username="postgres",
        password="your_password",
        db_name="tutorial_demo_db",
        create_new_db=True,    # Automatically creates database if missing
        pool_size=5            # Thread-safe pooled connections
    )

    print("Connected to PostgreSQL successfully with connection pool!")

--------------------------------------------------------------------------------

2. Defining Table Structures (DDL)
==================================

Use ``TableStructure`` to define your database schema programmatically.

2.1 Simple Table Example: ``users``
-----------------------------------

.. code-block:: python

    # Define the 'users' schema
    users_schema = TableStructure("users")

    # DataTypes.SERIAL() creates an auto-incrementing primary key in PostgreSQL
    users_schema.add_column("id", DataTypes.SERIAL(), primary_key=True)
    users_schema.add_column("username", DataTypes.VARCHAR(50), unique=True, not_null=True)
    users_schema.add_column("age", DataTypes.INTEGER(), default_value=18)

    # Create the table in PostgreSQL
    users = db.create_table(users_schema)

    # Unpack columns with type hints for clean code & Pylance autocomplete
    id: Column = users.id
    username: Column = users.username
    age: Column = users.age

    print(f"Simple table '{users.name_}' created successfully!")

2.2 Complex Table Example: ``products``
---------------------------------------

.. code-block:: python

    # Define a more complex 'products' schema with exact financial types
    products_schema = TableStructure("products")

    products_schema.add_column("id", DataTypes.SERIAL(), primary_key=True)
    products_schema.add_column("name", DataTypes.VARCHAR(100), not_null=True)
    products_schema.add_column("category", DataTypes.TEXT(), not_null=True)
    products_schema.add_column("price", DataTypes.NUMERIC(10, 2), not_null=True)
    products_schema.add_column("discount", DataTypes.REAL(), default_value=0.0)

    products = db.create_table(products_schema)

    # Unpack products columns with type hints
    p_id: Column = products.id
    name: Column = products.name
    category: Column = products.category
    price: Column = products.price
    discount: Column = products.discount

    print(f"Complex table '{products.name_}' created successfully!")

--------------------------------------------------------------------------------

3. Basic CRUD Operations
========================

3.1 Inserting Data (Single & Bulk)
----------------------------------

* **Single Insert:** Insert one row with ``users.insert()``.
* **Bulk Insert:** Insert multiple rows efficiently with ``users.bulk_insert()``.

.. code-block:: python

    # 1. Single Insert
    users.insert({
        username: "alice",
        age: 25
    })

    # 2. Bulk Insert (fast batch insertion)
    users.bulk_insert(
        columns=[username, age],
        data_list=[
            ("bob", 30),
            ("charlie", 22),
            ("diana", 28),
            ("edward", 35),
        ]
    )

    # Populate products table
    products.bulk_insert(
        columns=[name, category, price, discount],
        data_list=[
            ("Widget-A", "gadgets", 20.00, 0.10),
            ("Gadget Pro", "gadgets", 50.00, 0.20),
            ("SuperTool", "tools", 30.00, 0.00),
            ("MegaWidget", "gadgets", 100.00, 0.25),
            ("HeavyHammer", "tools", 15.00, 0.00),
        ]
    )

3.2 Querying Data (``get_row``)
-------------------------------

.. code-block:: python

    # Simple Query: Get id, username, and age ordered by age
    all_users = users.get_row(
        which_columns=[id, username, age],
        order_by=age
    )

    print("All Users (Ordered by Age):")
    for u_id, u_name, u_age in all_users:
        print(f"  ID: {u_id} | Username: {u_name:<10} | Age: {u_age}")

3.3 Updating Data (``update``)
------------------------------

* **Simple Update:** Assign a fixed value.
* **Complex Update:** Update using a mathematical expression on an existing column (``age + 1``).

.. code-block:: python

    # Simple Update: Set fixed age for 'alice'
    users.update(
        update={age: 26},
        where=username == "alice"
    )

    # Complex Update: Increase age by 1 for all users under 30
    users.update(
        update={age: age + 1},  # Column math expression!
        where=age < 30
    )

3.4 Deleting Data (``delete_row``)
----------------------------------

.. code-block:: python

    # Delete user 'edward'
    users.delete_row(where=username == "edward")

--------------------------------------------------------------------------------

4. Mastering Conditions & Filtering (``WHERE`` Clause)
======================================================

.. warning::

   **Always wrap conditions in parentheses ``()`` when combining with ``&`` (AND) and ``|`` (OR):**
   In Python, bitwise operators have higher priority than comparison operators.
   
   * ❌ **Wrong:** ``age > 20 & username == "alice"``
   *  **Right:** ``(age > 20) & (username == "alice")``

4.1 Logical AND (``&``) and OR (``|``)
--------------------------------------

.. code-block:: python

    # Simple Filter
    simple_cond = age >= 25
    print("Simple Filter (age >= 25):", users.get_row([username, age], where=simple_cond))

    # Complex Filter: (age < 25 OR age >= 30) AND (username != 'alice')
    complex_cond = ((age < 25) | (age >= 30)) & (username != "alice")
    print("Complex Filter with nested & and |:", users.get_row([username, age], where=complex_cond))

4.2 Pattern Matching & String Filtering
---------------------------------------

.. code-block:: python

    # 1. Starts with prefix
    print("Starts with 'd':", users.get_row([username], where=username.startswith("d")))

    # 2. Case-insensitive substring search combined with price check
    pattern_cond = (name.lower().contains("widget")) & (price > 15.0)
    print("Products containing 'widget' and price > 15:", products.get_row([name, price], where=pattern_cond))

4.3 In-List Filtering (``.In()`` and ``.not_In()``)
---------------------------------------------------

.. code-block:: python

    # 1. Membership check with .In()
    in_cond = username.In(data_list=["alice", "bob"])
    print("Users IN ['alice', 'bob']:", users.get_row([username], where=in_cond))

    # 2. Non-membership check with .not_In() combined with age filter
    not_in_cond = (username.not_In(data_list=["bob", "charlie"])) & (age >= 25)
    print("Users NOT IN ['bob', 'charlie'] with age >= 25:", users.get_row([username, age], where=not_in_cond))

4.4 Subqueries & Combining Multiple Subqueries (``&`` / ``|``)
--------------------------------------------------------------

.. code-block:: python

    # Create 'admins' and 'banned_users' tables
    admins_schema = TableStructure("admins")
    admins_schema.add_column("id", DataTypes.SERIAL(), primary_key=True)
    admins_schema.add_column("username", DataTypes.VARCHAR(50))
    admins = db.create_table(admins_schema)
    admin_username: Column = admins.username
    admins.bulk_insert([admin_username], [("bob",), ("diana",), ("charlie",)])

    banned_schema = TableStructure("banned_users")
    banned_schema.add_column("id", DataTypes.SERIAL(), primary_key=True)
    banned_schema.add_column("user_id", DataTypes.INTEGER(), not_null=True)
    banned_table = db.create_table(banned_schema)
    banned_user_id: Column = banned_table.user_id
    banned_table.insert({banned_user_id: 4})  # Ban user with id=4 (diana)

    # Complex Subquery: User IS in admins table AND IS NOT in banned_users table
    is_admin = username.In(column=admin_username)
    is_not_banned = id.not_In(column=banned_user_id)

    active_admins = users.get_row(
        which_columns=[id, username, age],
        where=(is_admin) & (is_not_banned),
        order_by=id
    )

    print("Active Admins (who are NOT banned):")
    for row in active_admins:
        print(" ", row)

--------------------------------------------------------------------------------

5. Advanced Expressions & ``ColumnsOperation``
==============================================

5.1 String Concatenation with ``+`` Operator (IMPORTANT)
--------------------------------------------------------

In Ormophine, you can concatenate columns and strings naturally using the standard **``+`` operator**.
The ORM automatically converts ``+`` on text columns into PostgreSQL's SQL concatenation (``||``).

.. code-block:: python

    # Simple String Concatenation
    user_greeting = "User: " + username
    for greeting in users.get_row([user_greeting]):
        print(" ", greeting)

    # Complex String Concatenation: Combine multiple columns and static strings
    product_label = name + " (" + category + ")"
    for row in products.get_row([p_id, product_label, price]):
        print(f"  ID: {row[0]} | Label: {row[1]:<25} | Price: ${row[2]:.2f}")

5.2 Arithmetic Calculations & Computed Filters
----------------------------------------------

.. code-block:: python

    # Calculate discounted price + 9% tax
    discounted_price = price * (1 - discount)
    final_price_with_tax = discounted_price * 1.09

    results = products.get_row(
        which_columns=[name, price, discounted_price, final_price_with_tax],
        where=final_price_with_tax > 25.0,
        order_by=final_price_with_tax
    )

    print("Products with Final Price (inc. Tax) > $25:")
    for prod_name, base_p, disc_p, total_p in results:
        print(f"  {prod_name:<12} | Base: ${base_p:.2f} | Discounted: ${disc_p:.2f} | Total (+Tax): ${total_p:.2f}")

5.3 String Transformations & Slicing
------------------------------------

.. code-block:: python

    # Python slicing compiles to PostgreSQL SUBSTRING()
    prefix = name[0:6]
    upper_name = name.upper()
    replaced_name = name.replace("-", "_")

    results = products.get_row([name, prefix, upper_name, replaced_name])
    for orig, pre, up, rep in results:
        print(f"  Orig: {orig:<12} | Slice[0:6]: {pre:<8} | Upper: {up:<12} | Replaced: {rep}")

5.4 Inline & Nested Conditional Expressions (``.If().Else()``)
--------------------------------------------------------------

.. code-block:: python

    # Simple 2-Tier Condition
    simple_tier = name.If(price >= 30.0).Else("Budget Item")

    # Complex Nested 3-Tier Condition (Premium > Mid-Range > Budget)
    # Compiles to PostgreSQL: CASE WHEN ... THEN ... ELSE (CASE WHEN ...) END
    nested_tier = (
        (name + " [Premium]").If(price >= 80.0)
        .Else(
            (name + " [Mid-Range]").If(price >= 30.0)
            .Else(name + " [Budget]")
        )
    )

    print("Complex Nested 3-Tier Classification:")
    for prod_name, prod_price, tier_label in products.get_row([name, price, nested_tier], order_by=price):
        print(f"  {prod_name:<12} (${prod_price:6.2f}) -> {tier_label}")

--------------------------------------------------------------------------------

6. Query Pagination & Connection Pool
=====================================

.. code-block:: python

    # Simple Limit: Top 2 items
    top_2 = products.get_row([name, price], limit=2, order_by=price)

    # Complex Pagination: Page 2 (Limit 2, Offset 2)
    page_2 = products.get_row(
        which_columns=[p_id, name, price],
        order_by=price,
        limit=2,
        offset=2
    )

--------------------------------------------------------------------------------

7. Batch Operations & Atomic Transactions
=========================================

Use ``table.batch()`` to group multiple statements into a single atomic transaction.

.. code-block:: python

    # Start an atomic batch transaction
    batch = products.batch()

    # 1. Queue an Insert
    batch.insert({
        name: "PowerDrill",
        category: "tools",
        price: 60.00,
        discount: 0.05
    })

    # 2. Queue an Update (increase tools price by 10%)
    batch.update(
        update={price: price * 1.10},
        where=category == "tools"
    )

    # 3. Execute all queued operations atomically
    batch.run()
    print("Batch transaction executed successfully!")

--------------------------------------------------------------------------------

8. Table Joins (``INNER JOIN``, ``LEFT JOIN``)
==============================================

.. code-block:: python

    # 1. Create 'orders' table referencing 'products'
    orders_schema = TableStructure("orders")
    orders_schema.add_column("id", DataTypes.SERIAL(), primary_key=True)
    orders_schema.add_column("product_id", DataTypes.INTEGER(), not_null=True)
    orders_schema.add_column("quantity", DataTypes.INTEGER(), default_value=1)

    # Define Foreign Key constraint
    orders_schema.foreign_key(
        column="product_id",
        refrences_table=products,
        refrences_column=p_id,
        on_delete="CASCADE"
    )
    orders = db.create_table(orders_schema)

    order_id: Column = orders.id
    order_product_id: Column = orders.product_id
    quantity: Column = orders.quantity

    # 2. Insert sample orders
    orders.bulk_insert(
        columns=[order_product_id, quantity],
        data_list=[(1, 3), (2, 1), (4, 5)]
    )

    # 3. Join orders with products and calculate line totals
    total_cost = price * quantity
    joined_orders = (
        orders
        .inner_join(products, order_product_id == p_id)
        .get_row(
            which_columns=[
                order_id,
                name,
                quantity,
                price,
                total_cost
            ],
            order_by=order_id
        )
    )

    print("Order Details (INNER JOIN with Line Totals):")
    for o_id, prod_name, qty, unit_p, total in joined_orders:
        print(f"  Order #{o_id} | Product: {prod_name:<12} | Qty: {qty} | Unit: ${unit_p:.2f} | Total: ${total:.2f}")

--------------------------------------------------------------------------------

9. Schema Alterations & Table Management (DDL)
==============================================

.. code-block:: python

    # 1. Add a new column
    users.add_column("email", DataTypes.VARCHAR(100), default="user@example.com")
    email: Column = users.email
    print("Columns after adding 'email':", users.get_columns_name())

    # 2. Rename column 'age' to 'user_age'
    users.rename_column(age, "user_age")
    user_age: Column = users.user_age
    print("Columns after renaming 'age' -> 'user_age':", users.get_columns_name())

    # 3. Safely delete column (requires explicit 3 confirmations)
    users.delete_column(
        email,
        are_you_sure=True,
        are_you_really_sure=True,
        for_sure=True
    )
    print("Columns after deleting 'email':", users.get_columns_name())

--------------------------------------------------------------------------------

10. Index Management (Standard & Partial Indexes)
=================================================

PostgreSQL supports both standard indexes and **Conditional (Partial) Indexes** with a ``where`` clause.

.. code-block:: python

    # 1. Simple Index on category column
    products.create_index("idx_products_cat", columns=[category])

    # 2. Complex Partial Index: Only indexes high-value products (price > 40)
    products.create_index(
        "idx_expensive_items",
        columns=[name],
        where=price > 40.0
    )

    # 3. View existing index details
    print("Index info on 'products':", products.get_indexes_info())

    # 4. Drop an index
    products.delete_index("idx_products_cat")
    print("Dropped index idx_products_cat successfully!")

--------------------------------------------------------------------------------

11. Database Maintenance & Administration
=========================================

.. code-block:: python

    # Optimize database tables (VACUUM ANALYZE)
    db.optimize()
    print("Database optimized and statistics updated successfully!")

--------------------------------------------------------------------------------

12. SQL Built-in Functions (``Builtins``)
=========================================

The ``Builtins`` class gives you direct access to PostgreSQL native SQL functions.
Every function in ``Builtins`` returns a ``ColumnsOperation`` so you can use it anywhere (in ``get_row``, ``where``, ``update``, etc.).

12.1 Aggregate Functions (``Count``, ``Sum``, ``Avg``, ``Min``, ``Max``)
-------------------------------------------------------------------------

.. code-block:: python

    # Compute multiple summary statistics in a single query
    stats = products.get_row([
        Builtins.Count(p_id),
        Builtins.Avg(price),
        Builtins.Min(price),
        Builtins.Max(price),
        Builtins.Sum(price)
    ])[0]

    print("--- Product Summary Statistics ---")
    print(f"  Count        : {stats[0]}")
    print(f"  Average Price: ${stats[1]:.2f}")
    print(f"  Min Price    : ${stats[2]:.2f}")
    print(f"  Max Price    : ${stats[3]:.2f}")
    print(f"  Total Sum    : ${stats[4]:.2f}")

12.2 Mathematical & String Functions (``Round``, ``Abs``, ``Len``)
------------------------------------------------------------------

.. code-block:: python

    results = products.get_row([
        name,
        Builtins.Len(name),
        Builtins.Round(price),
        Builtins.Abs(price - 50.0),
    ])

    for prod_name, length, rounded_p, diff in results:
        print(f"  {prod_name:<12} | Len: {length:<2} | Round: ${rounded_p:<5} | Diff from $50: ${diff:.2f}")

12.3 Range & Null Checks (``Between``, ``!= None``, ``== None``)
----------------------------------------------------------------

In Ormophine, checking for NULL values uses standard Python comparison:
* ``col != None`` compiles automatically to SQL **``IS NOT NULL``**
* ``col == None`` compiles automatically to SQL **``IS NULL``**

.. code-block:: python

    # Simple Null Check using '!= None' (compiles to SQL IS NOT NULL)
    valid_products = products.get_row([name], where=category != None)

    # Complex Range Filter: Price between $20 and $70 AND category == 'gadgets'
    between_filter = Builtins.Between(price, 20.0, 70.0) & (category == "gadgets")
    range_results = products.get_row([name, price, category], where=between_filter)

    print("Gadgets priced between $20 and $70 (Builtins.Between):")
    for row in range_results:
        print(" ", row)

12.4 Date & Time Functions (``Now``, ``Today``)
-----------------------------------------------

.. code-block:: python

    date_info = products.get_row([
        name,
        Builtins.Now(),            # Current Timestamp (NOW())
        Builtins.Today(),          # Current Date (CURRENT_DATE)
    ], limit=2)

    print("Current PostgreSQL Date and Time Helpers:")
    for row in date_info:
        print(" ", row)

12.5 Graceful Shutdown
----------------------

.. code-block:: python

    # Disconnect driver and close connection pool
    db.disconnect()
    print("Driver disconnected cleanly. PostgreSQL quickstart tutorial complete!")
