import pytest
from Ormophine import Postgresql
import os
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "1234")
PG_DB_NAME = os.getenv("PG_DB_NAME", "test_orm_db_fixed")
@pytest.fixture(scope="session")
def session_driver():

    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=False
        )
    
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except:
        pass
    yield drv
    drv.disconnect()
@pytest.fixture(scope="function")
def driver(session_driver):
    
    
    try:
        for t in session_driver.get_tables():
            session_driver.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except:
        pass
    
    return session_driver
def test_01_driver_connect_valid_credentials(driver):
    assert driver._connected is True
    assert len(driver.connection_pool_storage) == 5
def test_02_driver_connect_invalid_host():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host="invalid_host_123", port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, connect_timeout=2
        )
def test_03_driver_connect_invalid_port():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=9999, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, connect_timeout=2
        )
def test_04_driver_connect_invalid_username():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username="invalid_user_xyz",
            password=PG_PASSWORD, db_name=PG_DB_NAME, connect_timeout=2
        )
def test_05_driver_connect_invalid_password():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password="wrong_password", db_name=PG_DB_NAME, connect_timeout=2
        )
def test_06_driver_connect_invalid_db_name():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name="non_existent_db_xyz"
        )
def test_07_driver_create_new_db_true_success():
    temp_db = "temp_test_db_creation"
    
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    
    clean_drv.custom_execute("SELECT 1;")
    if temp_db in clean_drv.get_databases():
        clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=temp_db, create_new_db=True
    )
    assert temp_db in drv.get_databases()
    drv.disconnect()
    
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")  
    clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
def test_08_driver_create_new_db_already_exists(session_driver):
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
def test_09_driver_create_new_db_with_collate():
    temp_db = "temp_test_db_collate"
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")
    if temp_db in clean_drv.get_databases():
        clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=temp_db, create_new_db=True,
        collate="C"
    )
    assert temp_db in drv.get_databases()
    drv.disconnect()
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")
    clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
def test_10_driver_create_new_db_with_encoding():
    temp_db = "temp_test_db_utf8"  
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")
    if temp_db in clean_drv.get_databases():
        clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=temp_db, create_new_db=True,
        client_encoding="UTF8"
    )
    assert temp_db in drv.get_databases()
    drv.disconnect()
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")
    clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
def test_11_driver_default_pool_size_5():
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    assert len(drv.connection_pool_storage) == 5
    drv.disconnect()
def test_12_driver_custom_pool_size_10():
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME, pool_size=10
    )
    assert len(drv.connection_pool_storage) == 10
    drv.disconnect()
def test_13_driver_connect_timeout_success():
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME, connect_timeout=10
    )
    assert drv._connected is True
    drv.disconnect()
def test_14_driver_connect_timeout_fails():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host="192.0.2.1",
            port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, connect_timeout=1
        )
def test_21_driver_isolation_level_invalid_str():
    with pytest.raises(Exception):
        Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, isolation_level='INVALID LEVEL'
        )
def test_22_driver_disconnect_normal():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME)
    drv.disconnect()
    assert drv._connected is False
def test_23_driver_disconnect_twice_raises_error():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME)
    drv.disconnect()
    with pytest.raises(RuntimeError, match="Already disconnected"):
        drv.disconnect()
def test_24_driver_get_connection_from_pool(driver):
    con, cur = driver._get_connection()
    assert con is not None
    assert cur is not None
    driver.connection_pool.put((con, cur))
def test_25_driver_pool_exhaustion_creates_new_connection():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME, pool_size=1)
    con1, cur1 = drv._get_connection()
    
    con2, cur2 = drv._get_connection()
    assert len(drv.connection_pool_storage) == 2
    drv.connection_pool.put((con1, cur1))
    drv.connection_pool.put((con2, cur2))
    drv.disconnect()
def test_26_driver_pool_empty_raises_exception():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME, pool_size=1)
    con, cur = drv._get_connection()
    
    drv.config['host'] = 'invalid_host'
    with pytest.raises(Exception):
        drv._get_connection()
    drv.config['host'] = PG_HOST
    drv.connection_pool.put((con, cur))
    drv.disconnect()
def test_27_handle_broken_connection_success(driver):
    con, cur = driver._get_connection()
    con.close()  
    driver.connection_pool.put((con, cur))  
    
    res = driver.custom_execute_with_fetch("SELECT 1;")
    assert res == [(1,)]
def test_28_handle_broken_connection_remove_from_storage():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME, pool_size=2)
    con1, cur1 = drv._get_connection()
    con1.close()
    drv._handle_broken_connection(con1)
    assert con1 not in drv.connection_pool_storage
    assert len(drv.connection_pool_storage) == 2
    drv.disconnect()
def test_29_excfp_query_with_params_success(driver):
    res = driver._excfp("SELECT tablename FROM pg_tables WHERE schemaname = %s;", ('public',))
    assert isinstance(res, list)
def test_30_excfp_query_with_params_fails(driver):
    with pytest.raises(Exception):
        driver._excfp("SELECT * FROM non_existent_table WHERE id = %s;", (1,))
def test_31_excf_query_no_params_success(driver):
    res = driver._excf("SELECT 1;")
    assert res == [(1,)]
def test_32_excf_query_no_params_fails(driver):
    with pytest.raises(Exception):
        driver._excf("SELECT * FROM non_existent_table;")
def test_33_excp_query_with_params_success(driver):
    schema = Postgresql.TableStructure('test_excp')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.test_excp
    driver._excp(f"INSERT INTO {tbl.name_} (id, name) VALUES (%s, %s);", (1, 'Test'))
    
    res = tbl.get_row([tbl.id, tbl.name])
    assert len(res) == 1
    assert res[0][0] == 1
    assert res[0][1] == 'Test'
    driver.delete_table(tbl, True, True, True)
def test_34_excp_query_with_params_fails(driver):
    with pytest.raises(Exception):
        driver._excp("INSERT INTO non_existent_table (id) VALUES (%s);", (1,))
def test_35_exc_query_no_params_success(driver):
    schema = Postgresql.TableStructure('test_exc')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_exc
    driver._exc(f"INSERT INTO {tbl.name_} (id) VALUES (1);")
    
    res = tbl.get_row([tbl.id])
    assert res[0] == 1
    driver.delete_table(tbl, True, True, True)
def test_36_exc_query_no_params_fails(driver):
    with pytest.raises(Exception):
        driver._exc("DROP TABLE non_existent_table;")
def test_37_excs_batch_execution_success(driver):
    schema = Postgresql.TableStructure('test_excs')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_excs
    queries = [
        (f"INSERT INTO {tbl.name_} (id) VALUES (1);",),
        (f"INSERT INTO {tbl.name_} (id) VALUES (2);",),
        (f"INSERT INTO {tbl.name_} (id) VALUES (3);",)
    ]
    driver._excs(queries)
    
    res = tbl.get_row([tbl.id])
    assert len(res) == 3
    driver.delete_table(tbl, True, True, True)
def test_38_excs_batch_execution_fails_rollback(driver):
    schema = Postgresql.TableStructure('test_excs_rb')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    tbl = driver.test_excs_rb
    queries = [
        (f"INSERT INTO {tbl.name_} (id) VALUES (1);",),
        (f"INSERT INTO {tbl.name_} (id) VALUES (2);",),
        (f"INSERT INTO {tbl.name_} (id) VALUES (1);",)  
    ]
    with pytest.raises(Exception):
        driver._excs(queries)
        
    res = tbl.get_row([tbl.id])
    assert len(res) == 0
    driver.delete_table(tbl, True, True, True)
def test_39_excm_executemany_success(driver):
    schema = Postgresql.TableStructure('test_excm')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.test_excm
    data = [(1, 'A'), (2, 'B'), (3, 'C')]
    driver._excm(f"INSERT INTO {tbl.name_} (id, name) VALUES (%s, %s);", data)
    
    res = tbl.get_row([tbl.id])
    assert len(res) == 3
    driver.delete_table(tbl, True, True, True)
def test_40_excm_executemany_fails_rollback(driver):
    schema = Postgresql.TableStructure('test_excm_rb')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    tbl = driver.test_excm_rb
    data = [(1,), (2,), (1,)]  
    with pytest.raises(Exception):
        driver._excm(f"INSERT INTO {tbl.name_} (id) VALUES (%s);", data)
        
    res = tbl.get_row([tbl.id])
    assert len(res) == 0
    driver.delete_table(tbl, True, True, True)
def test_41_custom_execute_with_fetch_params(driver):
    schema = Postgresql.TableStructure('test_cewf')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_cewf
    tbl.insert({tbl.id: 1})
    
    res = driver.custom_execute_with_fetch(f"SELECT * FROM {tbl.name_} WHERE id = %s;", (1,))
    assert res == [(1,)]
    driver.delete_table(tbl, True, True, True)
def test_42_custom_execute_with_fetch_no_params(driver):
    schema = Postgresql.TableStructure('test_cewf2')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_cewf2
    tbl.insert({tbl.id: 1})
    
    res = driver.custom_execute_with_fetch(f"SELECT * FROM {tbl.name_};")
    assert res == [(1,)]
    driver.delete_table(tbl, True, True, True)
def test_43_custom_execute_params(driver):
    schema = Postgresql.TableStructure('test_ce')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.test_ce
    driver.custom_execute(f"INSERT INTO {tbl.name_} (id, name) VALUES (%s, %s);", (1, 'Ali'))
    
    res = tbl.get_row([tbl.name])
    assert res[0] == 'Ali'
    driver.delete_table(tbl, True, True, True)
def test_44_custom_execute_no_params(driver):
    schema = Postgresql.TableStructure('test_ce2')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_ce2
    driver.custom_execute(f"INSERT INTO {tbl.name_} (id) VALUES (1);")
    
    res = tbl.get_row([tbl.id])
    assert res[0] == 1
    driver.delete_table(tbl, True, True, True)
def test_45_custom_execute_many_success(driver):
    schema = Postgresql.TableStructure('test_cem')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.test_cem
    driver.custom_execute_many(f"INSERT INTO {tbl.name_} (id) VALUES (%s);", [(1,), (2,), (3,)])
    
    res = tbl.get_row([tbl.id])
    assert len(res) == 3
    driver.delete_table(tbl, True, True, True)
def test_46_get_databases_excludes_templates(driver):
    dbs = driver.get_databases()
    assert 'template0' not in dbs
    assert 'template1' not in dbs
def test_47_get_databases_includes_current(driver):
    dbs = driver.get_databases()
    assert PG_DB_NAME in dbs
def test_48_get_tables_empty_db():
    temp_db = "empty_db_test_orm"
    
    clean_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    clean_drv.custom_execute("SELECT 1;")
    if temp_db in clean_drv.get_databases():
        clean_drv.delete_database(temp_db, True, True, True)
    clean_drv.disconnect()
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=temp_db, create_new_db=True
    )
    tables = drv.get_tables()
    assert tables == []
    drv.disconnect()
    
    del_drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    del_drv.custom_execute("SELECT 1;")
    del_drv.delete_database(temp_db, True, True, True)
    del_drv.disconnect()
def test_49_get_tables_multiple_tables(driver):
    schema_a = Postgresql.TableStructure('tbl_a')
    schema_a.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema_a)
    schema_b = Postgresql.TableStructure('tbl_b')
    schema_b.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema_b)
    tables = driver.get_tables()
    assert 'tbl_a' in tables
    assert 'tbl_b' in tables
    driver.delete_table(driver.tbl_a, True, True, True)
    driver.delete_table(driver.tbl_b, True, True, True)
def test_50_disconnect_with_active_pool_connections():
    drv = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=PG_DB_NAME, pool_size=3)
    con, cur = drv._get_connection()
    drv.connection_pool.put((con, cur))
    drv.disconnect()
    assert drv._connected is False
@pytest.fixture(scope="module")
def driver():
    
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    
    
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except:
        pass
        
    yield drv
    
    
    try:
        drv.custom_execute(f'DROP DATABASE IF EXISTS "temp_db_100";')
        drv.drop_user("test_user_100")
    except:
        pass
    drv.disconnect()
def test_51_create_table_basic(driver):
    schema = Postgresql.TableStructure('t51')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    assert 't51' in driver.get_tables()
    assert hasattr(driver, 't51')
def test_52_create_table_if_not_exists_logic(driver):
    
    schema = Postgresql.TableStructure('t51')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    with pytest.raises(Exception):
        driver.create_table(schema)
def test_53_create_table_duplicate_raises_error(driver):
    schema = Postgresql.TableStructure('t51_dup')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    with pytest.raises(Exception):
        driver.create_table(schema)
def test_54_delete_table_triple_true(driver):
    schema = Postgresql.TableStructure('t54_del')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    driver.delete_table(driver.t54_del, are_you_sure=True, are_you_really_sure=True, for_sure=True)
    assert 't54_del' not in driver.get_tables()
    assert not hasattr(driver, 't54_del')
def test_55_delete_table_missing_one_flag(driver):
    schema = Postgresql.TableStructure('t55_del')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    driver.delete_table(driver.t55_del, are_you_sure=True, are_you_really_sure=True, for_sure=False)
    assert 't55_del' in driver.get_tables()
def test_56_delete_table_missing_two_flags(driver):
    schema = Postgresql.TableStructure('t56_del')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    driver.delete_table(driver.t56_del, are_you_sure=True, are_you_really_sure=False, for_sure=False)
    assert 't56_del' in driver.get_tables()
def test_57_delete_table_nonexistent(driver):
    schema = Postgresql.TableStructure('t57_ghost')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    
    ghost_table = Postgresql.Table(driver, 't57_ghost')
    with pytest.raises(Exception):
        driver.delete_table(ghost_table, True, True, True)
def test_58_delete_database_triple_true(driver):
    temp_db = "temp_db_100"
    
    drv_temp = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=temp_db, create_new_db=True)
    drv_temp.disconnect()
    
    driver.delete_database(temp_db, are_you_sure=True, are_you_really_sure=True, for_sure=True)
    assert temp_db not in driver.get_databases()
def test_59_delete_database_missing_flags(driver):
    temp_db = "temp_db_100_2"
    drv_temp = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=temp_db, create_new_db=True)
    drv_temp.disconnect()
    
    driver.delete_database(temp_db, are_you_sure=True, are_you_really_sure=False, for_sure=True)
    assert temp_db in driver.get_databases()
    
    driver.delete_database(temp_db, True, True, True)
def test_60_delete_database_nonexistent(driver):
    with pytest.raises(Exception):
        driver.delete_database("non_existent_db_xyz", True, True, True)
def test_61_create_user_basic(driver):
    try:
        driver.drop_user("test_user_100")
    except:
        pass
    driver.create_user("test_user_100", "secure_pass_123")
    users = driver.custom_execute_with_fetch(
        "SELECT usename FROM pg_user WHERE usename = 'test_user_100';"
    )
    assert len(users) == 1
def test_62_create_user_duplicate(driver):
    with pytest.raises(Exception):
        driver.create_user("test_user_100", "secure_pass_123")
def test_63_create_user_invalid_name(driver):
    with pytest.raises(Exception):
        driver.create_user("invalid-user-name;", "pass")
def test_64_drop_user_basic(driver):
    driver.create_user("temp_user_to_drop", "pass")
    driver.drop_user("temp_user_to_drop")
    users = driver.custom_execute_with_fetch("SELECT usename FROM pg_user WHERE usename = 'temp_user_to_drop';")
    assert len(users) == 0
def test_65_drop_user_nonexistent(driver):
    with pytest.raises(Exception):
        driver.drop_user("ghost_user_123")
def test_66_optimize_empty_db(driver):
    temp_db = "empty_db_opt_100"
    drv_temp = Postgresql.Driver(host=PG_HOST, port=PG_PORT, username=PG_USER, password=PG_PASSWORD, db_name=temp_db, create_new_db=True)
    drv_temp.optimize()  
    drv_temp.disconnect()
    driver.delete_database(temp_db, True, True, True)
def test_67_optimize_with_tables(driver):
    schema = Postgresql.TableStructure('t67_opt')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t67_opt
    tbl.insert({tbl.val: 'A'})
    tbl.insert({tbl.val: 'B'})
    tbl.insert({tbl.val: 'C'})
    driver.optimize()
    res = tbl.get_row([tbl.id])
    assert len(res) == 3
    driver.delete_table(tbl, True, True, True)
def test_68_optimize_after_bulk_insert(driver):
    schema = Postgresql.TableStructure('t68_opt')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.t68_opt
    
    data = [(i,) for i in range(100)]
    driver.custom_execute_many(f"INSERT INTO {tbl.name_} (id) VALUES (%s);", data)
    driver.optimize()
    res = tbl.get_row([tbl.id])
    assert len(res) == 100
    driver.delete_table(tbl, True, True, True)
def test_69_table_object_existing(driver):
    tbl = Postgresql.Table(driver, 't67_opt')
    assert isinstance(tbl, Postgresql.Table)
    assert tbl.name_ == '"t67_opt"'
def test_72_table_attribute_auto_discovery(driver):
    schema = Postgresql.TableStructure('t72_auto')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    assert hasattr(driver, 't72_auto')
    assert isinstance(driver.t72_auto, Postgresql.Table)
def test_73_table_attribute_not_exists(driver):
    assert not hasattr(driver, 't73_ghost')
def test_74_get_columns_name_after_create(driver):
    schema = Postgresql.TableStructure('t74_cols')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    cols = driver.t74_cols.get_columns_name()
    assert 'id' in cols
    assert 'name' in cols
    assert 'age' in cols
def test_75_table_name_quoting(driver):
    schema = Postgresql.TableStructure('Table With Spaces')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    
    assert 'Table With Spaces' in driver.get_tables()
    
    
    tbl = Postgresql.Table(driver, 'Table With Spaces')
    driver.delete_table(tbl, True, True, True)
def test_76_table_name_with_special_chars(driver):
    schema = Postgresql.TableStructure('t$pecial#!')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    
    assert 't$pecial#!'
    
    tbl = Postgresql.Table(driver, 't$pecial#!')
    driver.delete_table(tbl, True, True, True)
def test_78_alter_table_add_column(driver):
    schema = Postgresql.TableStructure('t78')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    driver.t78.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    cols = driver.t78.get_columns_name()
    assert 'name' in cols
    driver.delete_table(driver.t78, True, True, True)
def test_79_alter_table_drop_column(driver):
    schema = Postgresql.TableStructure('t79')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('val', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    driver.t79.delete_column(driver.t79.val, True, True, True)
    cols = driver.t79.get_columns_name()
    assert 'val' not in cols
    driver.delete_table(driver.t79, True, True, True)
def test_80_alter_table_rename_column(driver):
    schema = Postgresql.TableStructure('t80')
    schema.add_column('old_name', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    driver.t80.rename_column(driver.t80.old_name, 'new_name')
    cols = driver.t80.get_columns_name()
    assert 'new_name' in cols and 'old_name' not in cols
    driver.delete_table(driver.t80, True, True, True)
def test_85_create_index_simple(driver):
    schema = Postgresql.TableStructure('t85')
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    driver.t85.create_index('idx_name85', [driver.t85.name])
    indexes = driver.t85.get_indexes_info()
    assert any(idx['idx_name'] == 'idx_name85' for idx in indexes)
    driver.delete_table(driver.t85, True, True, True)
def test_86_create_index_unique(driver):
    schema = Postgresql.TableStructure('t86')
    schema.add_column('email', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    driver.t86.create_index('idx_email86', [driver.t86.email], unique=True)
    
    indexes = driver.t86.get_indexes_info()
    idx = next((i for i in indexes if i['idx_name'] == 'idx_email86'), None)
    assert idx is not None and idx['unique'] is True
    
    driver.t86.insert({driver.t86.email: 'a@b.com'})
    with pytest.raises(Exception):
        driver.t86.insert({driver.t86.email: 'a@b.com'})
    driver.delete_table(driver.t86, True, True, True)
def test_87_create_index_multi_column(driver):
    schema = Postgresql.TableStructure('t87')
    schema.add_column('a', Postgresql.DataTypes.INTEGER())
    schema.add_column('b', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    driver.t87.create_index('idx_ab87', [driver.t87.a, driver.t87.b])
    indexes = driver.t87.get_indexes_info()
    assert any(idx['idx_name'] == 'idx_ab87' for idx in indexes)
    driver.delete_table(driver.t87, True, True, True)
def test_88_drop_index(driver):
    schema = Postgresql.TableStructure('t88')
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    driver.t88.create_index('idx_name88', [driver.t88.name])
    driver.t88.delete_index('idx_name88')
    indexes = driver.t88.get_indexes_info()
    assert not any(idx['idx_name'] == 'idx_name88' for idx in indexes)
    driver.delete_table(driver.t88, True, True, True)
def test_101_data_type_integer():
    schema = Postgresql.TableStructure('t101')
    schema.add_column('col', Postgresql.DataTypes.INTEGER(), primary_key=True)
    sql = schema.get_structure()
    assert 'INTEGER' in sql.upper()
def test_102_data_type_smallint():
    schema = Postgresql.TableStructure('t102')
    schema.add_column('col', Postgresql.DataTypes.SMALLINT(), primary_key=True)
    sql = schema.get_structure()
    assert 'SMALLINT' in sql.upper()
def test_103_data_type_bigint():
    schema = Postgresql.TableStructure('t103')
    schema.add_column('col', Postgresql.DataTypes.BIGINT(), primary_key=True)
    sql = schema.get_structure()
    assert 'BIGINT' in sql.upper()
def test_104_data_type_serial():
    schema = Postgresql.TableStructure('t104')
    schema.add_column('col', Postgresql.DataTypes.SERIAL(), primary_key=True)
    sql = schema.get_structure()
    assert 'SERIAL' in sql.upper()
def test_105_data_type_bigserial():
    schema = Postgresql.TableStructure('t105')
    schema.add_column('col', Postgresql.DataTypes.BIGSERIAL(), primary_key=True)
    sql = schema.get_structure()
    assert 'BIGSERIAL' in sql.upper()
def test_106_data_type_real():
    schema = Postgresql.TableStructure('t106')
    schema.add_column('col', Postgresql.DataTypes.REAL(), primary_key=True)
    sql = schema.get_structure()
    assert 'REAL' in sql.upper()
def test_107_data_type_double_precision():
    schema = Postgresql.TableStructure('t107')
    schema.add_column('col', Postgresql.DataTypes.DOUBLE_PRECISION(), primary_key=True)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'DOUBLE PRECISION' in sql_upper or 'DOUBLE_PRECISION' in sql_upper or 'DOUBLE' in sql_upper
def test_108_data_type_decimal():
    schema = Postgresql.TableStructure('t108')
    schema.add_column('col', Postgresql.DataTypes.DECIMAL(), primary_key=True)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'DECIMAL' in sql_upper or 'NUMERIC' in sql_upper
def test_109_data_type_numeric():
    schema = Postgresql.TableStructure('t109')
    schema.add_column('col', Postgresql.DataTypes.NUMERIC(), primary_key=True)
    sql = schema.get_structure()
    assert 'NUMERIC' in sql.upper()
def test_110_data_type_money():
    schema = Postgresql.TableStructure('t110')
    schema.add_column('col', Postgresql.DataTypes.MONEY(), primary_key=True)
    sql = schema.get_structure()
    assert 'MONEY' in sql.upper()
def test_111_data_type_boolean_true():
    schema = Postgresql.TableStructure('t111')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('flag', Postgresql.DataTypes.BOOLEAN())
    sql = schema.get_structure()
    assert 'BOOLEAN' in sql.upper()
def test_112_data_type_boolean_false():
    schema = Postgresql.TableStructure('t112')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('flag', Postgresql.DataTypes.BOOLEAN(), default_value=False)
    sql = schema.get_structure()
    assert 'BOOLEAN' in sql.upper()
def test_116_data_type_decimal_precision_scale():
    dt = Postgresql.DataTypes.DECIMAL(precision=10, scale=2)
    schema = Postgresql.TableStructure('t116')
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert ('DECIMAL(10, 2)' in sql_upper or
            'NUMERIC(10, 2)' in sql_upper or
            'DECIMAL(10,2)' in sql_upper or
            'NUMERIC(10,2)' in sql_upper)
def test_117_data_type_numeric_precision_scale():
    dt = Postgresql.DataTypes.NUMERIC(precision=15, scale=4)
    schema = Postgresql.TableStructure('t117')
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'NUMERIC(15, 4)' in sql_upper or 'NUMERIC(15,4)' in sql_upper
def test_127_data_type_serial_auto_increment(driver):
    
    schema = Postgresql.TableStructure('t127')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t127
    tbl.insert({tbl.name: 'first'})
    tbl.insert({tbl.name: 'second'})
    res = tbl.get_row([tbl.name])
    assert len(res) == 2
    assert res[0] == 'first'
    assert res[1] == 'second'
    driver.delete_table(tbl, True, True, True)
def test_128_data_type_bigserial_auto_increment(driver):
    
    schema = Postgresql.TableStructure('t128')
    schema.add_column('id', Postgresql.DataTypes.BIGSERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t128
    tbl.insert({tbl.name: 'a'})
    tbl.insert({tbl.name: 'b'})
    res = tbl.get_row([tbl.id])
    assert len(res) == 2
    assert res[0] == 1
    assert res[1] == 2
    driver.delete_table(tbl, True, True, True)
def test_129_data_type_numeric_invalid_precision():
    
    with pytest.raises(Exception):
        Postgresql.DataTypes.NUMERIC(precision=0, scale=0)
def test_130_data_type_decimal_scale_gt_precision():
    with pytest.raises(Exception):
        Postgresql.DataTypes.DECIMAL(precision=3, scale=5)
def test_131_data_type_integer_default_value():
    schema = Postgresql.TableStructure('t131')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('age', Postgresql.DataTypes.INTEGER(), default_value=18)
    sql = schema.get_structure()
    assert 'DEFAULT 18' in sql
def test_132_data_type_numeric_default_value():
    schema = Postgresql.TableStructure('t132')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('price', Postgresql.DataTypes.NUMERIC(10, 2), default_value=0.00)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'DEFAULT' in sql_upper
    assert '0' in sql
def test_133_data_type_boolean_default_true():
    schema = Postgresql.TableStructure('t133')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('active', Postgresql.DataTypes.BOOLEAN(), default_value=True)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'DEFAULT TRUE' in sql_upper or 'DEFAULT true' in sql
def test_134_data_type_boolean_default_false():
    schema = Postgresql.TableStructure('t134')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('deleted', Postgresql.DataTypes.BOOLEAN(), default_value=False)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'DEFAULT FALSE' in sql_upper or 'DEFAULT false' in sql
def test_135_data_type_money_default():
    schema = Postgresql.TableStructure('t135')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('amount', Postgresql.DataTypes.MONEY(), default_value=0)
    sql = schema.get_structure()
    sql_upper = sql.upper()
    assert 'MONEY' in sql_upper
    assert 'DEFAULT' in sql_upper
def test_136_data_type_integer_null_insert(driver):
    
    schema = Postgresql.TableStructure('t136')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t136
    tbl.insert({tbl.val: None})
    res = tbl.get_row([tbl.val])
    assert res[0] is None
    driver.delete_table(tbl, True, True, True)
def test_137_data_type_integer_not_null_violation(driver):
    
    schema = Postgresql.TableStructure('t137')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER(), not_null=True)
    driver.create_table(schema)
    tbl = driver.t137
    with pytest.raises(Exception):
        tbl.insert({tbl.val: None})
    driver.delete_table(tbl, True, True, True)
def test_138_data_type_decimal_negative(driver):
    
    schema = Postgresql.TableStructure('t138')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('balance', Postgresql.DataTypes.DECIMAL(10, 2))
    driver.create_table(schema)
    tbl = driver.t138
    tbl.insert({tbl.balance: -1234.56})
    res = tbl.get_row([tbl.balance])
    assert float(res[0]) == -1234.56
    driver.delete_table(tbl, True, True, True)
def test_139_data_type_real_scientific_notation(driver):
    
    schema = Postgresql.TableStructure('t139')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.REAL())
    driver.create_table(schema)
    tbl = driver.t139
    tbl.insert({tbl.val: 1.5e-10})
    res = tbl.get_row([tbl.val])
    assert abs(float(res[0]) - 1.5e-10) < 1e-15
    driver.delete_table(tbl, True, True, True)
def test_140_data_type_bigint_large_value(driver):
    
    schema = Postgresql.TableStructure('t140')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('big_val', Postgresql.DataTypes.BIGINT())
    driver.create_table(schema)
    tbl = driver.t140
    large_val = 2 ** 62
    tbl.insert({tbl.big_val: large_val})
    res = tbl.get_row([tbl.big_val])
    assert res[0] == large_val
    driver.delete_table(tbl, True, True, True)
def test_141_data_type_numeric_large_precision(driver):
    
    schema = Postgresql.TableStructure('t141')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.NUMERIC(38, 10))
    driver.create_table(schema)
    tbl = driver.t141
    large_num = '1234567890123456789012345678.1234567890'
    tbl.insert({tbl.val: large_num})
    res = tbl.get_row([tbl.val])
    assert str(res[0]).replace(' ', '').startswith('1234567890123456789012345678')
    driver.delete_table(tbl, True, True, True)
def test_142_data_type_smallint_boundary(driver):
    
    schema = Postgresql.TableStructure('t142')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.SMALLINT())
    driver.create_table(schema)
    tbl = driver.t142
    tbl.insert({tbl.val: 32767})
    res = tbl.get_row([tbl.val])
    assert res[0] == 32767
    with pytest.raises(Exception):
        tbl.insert({tbl.val: 32768})
    driver.delete_table(tbl, True, True, True)
def test_143_data_type_integer_boundary(driver):
    
    schema = Postgresql.TableStructure('t143')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t143
    tbl.insert({tbl.val: 2147483647})
    res = tbl.get_row([tbl.val])
    assert res[0] == 2147483647
    driver.delete_table(tbl, True, True, True)
def test_144_data_type_bigint_boundary(driver):
    
    schema = Postgresql.TableStructure('t144')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.BIGINT())
    driver.create_table(schema)
    tbl = driver.t144
    boundary = 2**63 - 1
    tbl.insert({tbl.val: boundary})
    res = tbl.get_row([tbl.val])
    assert res[0] == boundary
    driver.delete_table(tbl, True, True, True)
def test_145_data_type_serial_zero_insert(driver):
    
    schema = Postgresql.TableStructure('t145')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t145
    tbl.insert({tbl.id: 0, tbl.name: 'zero_id'})
    res = tbl.get_row([tbl.id])
    assert res[0] == 0
    driver.delete_table(tbl, True, True, True)
def test_146_data_type_decimal_rounding(driver):
    
    schema = Postgresql.TableStructure('t146')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.DECIMAL(5, 2))
    driver.create_table(schema)
    tbl = driver.t146
    tbl.insert({tbl.val: 123.456})
    res = tbl.get_row([tbl.val])
    assert float(res[0]) == 123.46
    driver.delete_table(tbl, True, True, True)
def test_147_data_type_numeric_aggregation(driver):
    
    schema = Postgresql.TableStructure('t147')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('amount', Postgresql.DataTypes.NUMERIC(10, 2))
    driver.create_table(schema)
    tbl = driver.t147
    tbl.insert({tbl.amount: 100.50})
    tbl.insert({tbl.amount: 200.25})
    tbl.insert({tbl.amount: 300.25})
    res = tbl.get_row([tbl.amount])
    total = sum(float(r) for r in res)
    assert total == 601.0
    driver.delete_table(tbl, True, True, True)
def test_148_data_type_boolean_logic_and(driver):
    
    schema = Postgresql.TableStructure('t148')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('a', Postgresql.DataTypes.BOOLEAN())
    schema.add_column('b', Postgresql.DataTypes.BOOLEAN())
    driver.create_table(schema)
    tbl = driver.t148
    tbl.insert({tbl.a: True, tbl.b: True})
    tbl.insert({tbl.a: True, tbl.b: False})
    tbl.insert({tbl.a: False, tbl.b: True})
    res = tbl.get_row([tbl.a,tbl.b])
    both_true = [r for r in res if r[0] is True and r[1] is True]
    assert len(both_true) == 1
    driver.delete_table(tbl, True, True, True)
def test_149_data_type_boolean_logic_or(driver):
    
    schema = Postgresql.TableStructure('t149')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('a', Postgresql.DataTypes.BOOLEAN())
    schema.add_column('b', Postgresql.DataTypes.BOOLEAN())
    driver.create_table(schema)
    tbl = driver.t149
    tbl.insert({tbl.a: True, tbl.b: False})
    tbl.insert({tbl.a: False, tbl.b: True})
    tbl.insert({tbl.a: False, tbl.b: False})
    res = tbl.get_row([tbl.a,tbl.b])
    any_true = [r for r in res if r[0] is True or r[1] is True]
    assert len(any_true) == 2
    driver.delete_table(tbl, True, True, True)
@pytest.fixture(scope="module")
def driver():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except:
        pass
        
    yield drv
    
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except:
        pass
    drv.disconnect()
def test_151_crud_insert_and_select(driver):
    
    schema = Postgresql.TableStructure('t151')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t151
    tbl.insert({tbl.name: 'Ali', tbl.age: 30})
    tbl.insert({tbl.name: 'Sara', tbl.age: 25})
    res = tbl.get_row([tbl.name])
    assert len(res) == 2
    assert 'Ali' in res
    assert 'Sara' in res
    driver.delete_table(tbl, True, True, True)
def test_152_crud_update(driver):
    
    schema = Postgresql.TableStructure('t152')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t152
    tbl.insert({tbl.name: 'Ali', tbl.age: 30})
    tbl.update({tbl.age: 31}, where=tbl.name == 'Ali')
    res = tbl.get_row([tbl.age])
    assert res[0] == 31
    driver.delete_table(tbl, True, True, True)
def test_153_crud_delete(driver):
    
    schema = Postgresql.TableStructure('t153')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    tbl = driver.t153
    tbl.insert({tbl.name: 'Ali'})
    tbl.insert({tbl.name: 'Sara'})
    tbl.delete_row(where=tbl.name == 'Ali')
    res = tbl.get_row([tbl.name])  
    assert res[0] == 'Sara'
    driver.delete_table(tbl, True, True, True)
def test_154_select_where_equal(driver):
    
    schema = Postgresql.TableStructure('t154')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('city', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t154
    tbl.insert({tbl.city: 'Tehran'})
    tbl.insert({tbl.city: 'Isfahan'})
    tbl.insert({tbl.city: 'Tehran'})
    res = tbl.get_row([tbl.id],where=tbl.city== 'Tehran')
    assert len(res) == 2
    driver.delete_table(tbl, True, True, True)
def test_155_select_where_multiple_conditions(driver):
    
    schema = Postgresql.TableStructure('t155')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('city', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t155
    tbl.insert({tbl.city: 'Tehran', tbl.age: 30})
    tbl.insert({tbl.city: 'Tehran', tbl.age: 20})
    tbl.insert({tbl.city: 'Isfahan', tbl.age: 30})
    res = tbl.get_row([tbl.city, tbl.age],where=(tbl.city== 'Tehran') & (tbl.age== 30))
    assert len(res) == 1
    assert res[0][0] == 'Tehran'
    assert res[0][1] == 30
    driver.delete_table(tbl, True, True, True)
def test_156_select_order_by(driver):
    
    schema = Postgresql.TableStructure('t156')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('score', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t156
    tbl.insert({tbl.score: 90})
    tbl.insert({tbl.score: 70})
    tbl.insert({tbl.score: 85})
    res = tbl.get_row([tbl.score],order_by=tbl.score)
    assert res[0] == 70
    assert res[2] == 90
    driver.delete_table(tbl, True, True, True)
def test_158_foreign_key_relationship(driver):
    
    
    schema_dept = Postgresql.TableStructure('t158_dept')
    schema_dept.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_dept.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema_dept)
    dept = driver.t158_dept
    dept.insert({dept.name: 'Engineering'})
    dept.insert({dept.name: 'Marketing'})
    
    schema_emp = Postgresql.TableStructure('t158_emp')
    schema_emp.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_emp.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    schema_emp.add_column('dept_id', Postgresql.DataTypes.INTEGER())
    schema_emp.foreign_key('dept_id', dept, dept.id, on_delete='CASCADE')
    driver.create_table(schema_emp)
    emp = driver.t158_emp
    emp.insert({emp.name: 'Ali', emp.dept_id: 1})
    emp.insert({emp.name: 'Sara', emp.dept_id: 2})
    res = emp.get_row([emp.name])
    assert len(res) == 2
    
    with pytest.raises(Exception):
        emp.insert({emp.name: 'Reza', emp.dept_id: 999})
    driver.delete_table(emp, True, True, True)
    driver.delete_table(dept, True, True, True)
def test_159_unique_constraint(driver):
    
    schema = Postgresql.TableStructure('t159')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('email', Postgresql.DataTypes.VARCHAR(200), unique=True)
    driver.create_table(schema)
    tbl = driver.t159
    tbl.insert({tbl.email: 'a@test.com'})
    with pytest.raises(Exception):
        tbl.insert({tbl.email: 'a@test.com'})
    driver.delete_table(tbl, True, True, True)
def test_160_insert_many(driver):
    
    schema = Postgresql.TableStructure('t160')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('score', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t160
    records = [
        {tbl.name: 'Ali', tbl.score: 85},
        {tbl.name: 'Sara', tbl.score: 92},
        {tbl.name: 'Reza', tbl.score: 78},
    ]
    tbl.bulk_insert([tbl.name, tbl.score], 
                [(r[tbl.name], r[tbl.score]) for r in records])
    res = tbl.get_row([tbl.name])
    assert len(res) == 3
    driver.delete_table(tbl, True, True, True)
def test_162_exists(driver):
    
    schema = Postgresql.TableStructure('t162')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t162
    tbl.insert({tbl.name: 'Ali'})
    
    def exists(table, where):
            return len(table.get_row([table.id], where=where)) > 0
    
    assert exists(tbl, tbl.name == 'Ali') is True
    driver.delete_table(tbl, True, True, True)
def test_163_default_value_on_insert(driver):
    
    schema = Postgresql.TableStructure('t163')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('status', Postgresql.DataTypes.VARCHAR(20), default_value='active')
    driver.create_table(schema)
    tbl = driver.t163
    tbl.insert({})  
    res = tbl.get_row([tbl.status])
    assert res[0] == 'active'
    driver.delete_table(tbl, True, True, True)
def test_164_not_null_enforcement(driver):
    
    schema = Postgresql.TableStructure('t164')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50), not_null=True)
    driver.create_table(schema)
    tbl = driver.t164
    with pytest.raises(Exception):
        tbl.insert({tbl.name: None})
    driver.delete_table(tbl, True, True, True)
def test_166_create_and_delete_table_lifecycle(driver):
    
    schema = Postgresql.TableStructure('t166')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    assert 't166' in driver.get_tables()
    assert hasattr(driver, 't166')
    driver.delete_table(driver.t166, True, True, True)
    assert 't166' not in driver.get_tables()
    assert not hasattr(driver, 't166')
def test_167_delete_table_requires_all_flags(driver):
    
    schema = Postgresql.TableStructure('t167')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    driver.delete_table(driver.t167, True, True, False)
    assert 't167' in driver.get_tables()  
    driver.delete_table(driver.t167, True, True, True)  
def test_168_table_name_with_spaces(driver):
    
    schema = Postgresql.TableStructure('My Table')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = getattr(driver, 'My Table')
    tbl.insert({tbl.val: 42})
    res = tbl.get_row([tbl.val])
    assert res[0] == 42
    driver.delete_table(tbl, True, True, True)
def test_169_composite_primary_key(driver):
    
    schema = Postgresql.TableStructure('t169')
    schema.add_column('user_id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('role_id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.t169
    tbl.insert({tbl.user_id: 1, tbl.role_id: 1})
    tbl.insert({tbl.user_id: 1, tbl.role_id: 2})
    
    with pytest.raises(Exception):
        tbl.insert({tbl.user_id: 1, tbl.role_id: 1})
    driver.delete_table(tbl, True, True, True)
def test_170_get_columns_name(driver):
    
    schema = Postgresql.TableStructure('t170')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('first_name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('last_name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('salary', Postgresql.DataTypes.NUMERIC(10, 2))
    driver.create_table(schema)
    cols = driver.t170.get_columns_name()
    assert 'id' in cols
    assert 'first_name' in cols
    assert 'last_name' in cols
    assert 'salary' in cols
    driver.delete_table(driver.t170, True, True, True)
def test_171_optimize_after_operations(driver):
    
    schema = Postgresql.TableStructure('t171')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t171
    for i in range(100):
        tbl.insert({tbl.val: i})
    
    for i in range(50):
        tbl.delete_row(where=tbl.val == i)
    driver.optimize()
    assert len(tbl.get_row([tbl.val])) == 50
    driver.delete_table(tbl, True, True, True)
def test_172_table_object_lookup(driver):
    
    schema = Postgresql.TableStructure('t172')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    tbl = getattr(driver, 't172')
    assert isinstance(tbl, Postgresql.Table)
    assert tbl.name_ == '"t172"'
    driver.delete_table(tbl, True, True, True)
def test_173_table_object_nonexistent_raises(driver):
    
    with pytest.raises(AttributeError, match="t172"):
        getattr(driver, 't172')
def test_174_get_databases_excludes_templates(driver):
    
    dbs = driver.get_databases()
    assert 'template0' not in dbs
    assert 'template1' not in dbs
    assert PG_DB_NAME in dbs
def test_175_create_and_drop_user(driver):
    
    test_user = 't175_user'
    try:
        driver.drop_user(test_user)
    except:
        pass
    driver.create_user(test_user, 'pass123')
    users = driver.custom_execute_with_fetch(
        "SELECT usename FROM pg_user WHERE usename = %s;", (test_user,)
    )
    assert len(users) == 1
    driver.drop_user(test_user)
    users = driver.custom_execute_with_fetch(
        "SELECT usename FROM pg_user WHERE usename = %s;", (test_user,)
    )
    assert len(users) == 0
def test_176_disconnect_and_reconnect():
    
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    assert drv._connected is True
    drv.disconnect()
    assert drv._connected is False
    with pytest.raises(RuntimeError):
        drv.disconnect()  
def test_177_insert_and_read_back(driver):
    schema = Postgresql.TableStructure('t177')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t177
    tbl.insert({tbl.name: 'Ali'})
    tbl.insert({tbl.name: 'Sara'})
    rows = tbl.get_row([tbl.name])  
    assert rows == ['Ali', 'Sara']  
def test_178_unique_constraint_violation(driver):
    schema = Postgresql.TableStructure('t178')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('code', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    tbl = driver.t178
    tbl.insert({tbl.code: 1})
    tbl.insert({tbl.code: 2})
    with pytest.raises(Exception):
        tbl.insert({tbl.code: 1})
    count = len(tbl.get_row([tbl.id]))  
    assert count == 2
def test_179_not_null_violation(driver):
    
    schema = Postgresql.TableStructure('t179')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50), not_null=True)
    driver.create_table(schema)
    tbl = driver.t179
    with pytest.raises(Exception):
        tbl.insert({tbl.name: None})
    driver.delete_table(tbl, True, True, True)
def test_181_foreign_key_violation(driver):
    
    schema_parent = Postgresql.TableStructure('t181_parent')
    schema_parent.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_parent)
    parent = driver.t181_parent
    parent.insert({})
    schema_child = Postgresql.TableStructure('t181_child')
    schema_child.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_child.add_column('parent_id', Postgresql.DataTypes.INTEGER())
    schema_child.foreign_key('parent_id', parent, parent.id)  
    driver.create_table(schema_child)
    child = driver.t181_child
    child.insert({child.parent_id: 1})
    with pytest.raises(Exception):
        child.insert({child.parent_id: 999})
    driver.delete_table(child, True, True, True)
    driver.delete_table(parent, True, True, True)
def test_182_multiple_inserts(driver):
    schema = Postgresql.TableStructure('t182')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t182
    for i in range(5):
        tbl.insert({tbl.val: i * 10})
    rows = tbl.get_row([tbl.val], order_by=tbl.id)
    assert rows == [0, 10, 20, 30, 40]
def test_183_insert_null_allowed(driver):
    schema = Postgresql.TableStructure('t183')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t183
    tbl.insert({tbl.val: None})
    
    rows = tbl.get_row([tbl.val])
    assert rows[0] is None
    driver.delete_table(tbl, True, True, True)
def test_184_insert_empty_string_vs_null(driver):
    
    schema = Postgresql.TableStructure('t184')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema)
    tbl = driver.t184
    tbl.insert({tbl.name: ''})
    tbl.insert({tbl.name: None})
    rows = tbl.get_row([tbl.name])
    assert rows[0] == ('')
    assert rows[1] == (None)
    driver.delete_table(tbl, True, True, True)
def test_185_insert_persian_unicode(driver):
    schema = Postgresql.TableStructure('t185')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    tbl = driver.t185
    tbl.insert({tbl.name: 'علی رضایی'})
    rows = tbl.get_row([tbl.name])
    assert rows[0] == 'علی رضایی'
    driver.delete_table(tbl, True, True, True)
def test_186_insert_text_with_newlines(driver):
    schema = Postgresql.TableStructure('t186')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('content', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t186
    multiline = "line1\nline2\nline3"
    tbl.insert({tbl.content: multiline})
    rows = tbl.get_row([tbl.content])
    assert rows[0] == multiline
    driver.delete_table(tbl, True, True, True)
def test_187_insert_long_text(driver):
    
    schema = Postgresql.TableStructure('t187')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('content', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t187
    long_text = 'آ' * 10000
    tbl.insert({tbl.content: long_text})
    rows = driver.custom_execute_with_fetch('SELECT LENGTH(content) FROM t187;')
    assert rows[0][0] == 10000
    driver.delete_table(tbl, True, True, True)
def test_188_varchar_length_limit(driver):
    
    schema = Postgresql.TableStructure('t188')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('code', Postgresql.DataTypes.VARCHAR(5))
    driver.create_table(schema)
    tbl = driver.t188
    tbl.insert({tbl.code: 'ABC12'})
    with pytest.raises(Exception):
        tbl.insert({tbl.code: 'ABC12345'})
    driver.delete_table(tbl, True, True, True)
def test_189_boolean_insert_and_filter(driver):
    schema = Postgresql.TableStructure('t189')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('active', Postgresql.DataTypes.BOOLEAN())
    driver.create_table(schema)
    tbl = driver.t189
    tbl.insert({tbl.active: True})
    tbl.insert({tbl.active: False})
    tbl.insert({tbl.active: True})
    active = len(tbl.get_row([tbl.id], where=tbl.active == True))
    inactive = len(tbl.get_row([tbl.id], where=tbl.active == False))
    assert active == 2
    assert inactive == 1
def test_190_decimal_precision(driver):
    schema = Postgresql.TableStructure('t190')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('amount', Postgresql.DataTypes.DECIMAL(10, 4))
    driver.create_table(schema)
    tbl = driver.t190
    tbl.insert({tbl.amount: '12345.6789'})
    rows = tbl.get_row([tbl.amount])
    assert str(rows[0]) == '12345.6789'
    driver.delete_table(tbl, True, True, True)
def test_191_decimal_negative(driver):
    schema = Postgresql.TableStructure('t191')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('balance', Postgresql.DataTypes.DECIMAL(10, 2))
    driver.create_table(schema)
    tbl = driver.t191
    tbl.insert({tbl.balance: -1234.56})
    rows = tbl.get_row([tbl.balance])
    assert float(rows[0]) == -1234.56
    driver.delete_table(tbl, True, True, True)
def test_192_real_scientific_notation(driver):
    schema = Postgresql.TableStructure('t192')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.REAL())
    driver.create_table(schema)
    tbl = driver.t192
    tbl.insert({tbl.val: 1.5e-10})
    rows = tbl.get_row([tbl.val])
    assert abs(float(rows[0]) - 1.5e-10) < 1e-15
    driver.delete_table(tbl, True, True, True)
def test_193_bigint_large_value(driver):
    schema = Postgresql.TableStructure('t193')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('big_val', Postgresql.DataTypes.BIGINT())
    driver.create_table(schema)
    tbl = driver.t193
    large_val = 2 ** 62
    tbl.insert({tbl.big_val: large_val})
    rows = tbl.get_row([tbl.big_val])
    assert rows[0] == large_val
    driver.delete_table(tbl, True, True, True)
def test_194_smallint_boundary(driver):
    schema = Postgresql.TableStructure('t194')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.SMALLINT())
    driver.create_table(schema)
    tbl = driver.t194
    tbl.insert({tbl.val: 32767})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == 32767
    with pytest.raises(Exception):
        tbl.insert({tbl.val: 32768})
    driver.delete_table(tbl, True, True, True)
def test_195_integer_zero_and_negative(driver):
    schema = Postgresql.TableStructure('t195')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t195
    tbl.insert({tbl.val: 0})
    tbl.insert({tbl.val: -999})
    rows = tbl.get_row([tbl.val], order_by=tbl.id)
    assert rows[0] == 0
    assert rows[1] == -999
    driver.delete_table(tbl, True, True, True)
def test_196_money_type(driver):
    schema = Postgresql.TableStructure('t196')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('price', Postgresql.DataTypes.MONEY())
    driver.create_table(schema)
    tbl = driver.t196
    tbl.insert({tbl.price: '99.99'})
    rows = tbl.get_row([tbl.price])
    assert rows[0] is not None
    driver.delete_table(tbl, True, True, True)
def test_197_default_value_used(driver):
    schema = Postgresql.TableStructure('t197')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('status', Postgresql.DataTypes.VARCHAR(20), default_value='active')
    driver.create_table(schema)
    tbl = driver.t197
    tbl.insert({})  
    rows = tbl.get_row([tbl.status])
    assert rows[0] == 'active'
def test_198_auto_discovery_after_create(driver):
    schema = Postgresql.TableStructure('t198')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('data', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    assert hasattr(driver, 't198')
    tbl = driver.t198
    tbl.insert({tbl.data: 'hello'})
    rows = tbl.get_row([tbl.data])
    assert rows[0] == 'hello'
def test_199_get_columns_name(driver):
    
    schema = Postgresql.TableStructure('t199')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('first_name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('salary', Postgresql.DataTypes.NUMERIC(10, 2))
    driver.create_table(schema)
    cols = driver.t199.get_columns_name()
    assert 'id' in cols
    assert 'first_name' in cols
    assert 'salary' in cols
    driver.delete_table(driver.t199, True, True, True)
def test_200_create_and_delete_table_lifecycle(driver):
    
    schema = Postgresql.TableStructure('t200')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    assert 't200' in driver.get_tables()
    assert hasattr(driver, 't200')
    driver.delete_table(driver.t200, True, True, True)
    assert 't200' not in driver.get_tables()
    assert not hasattr(driver, 't200')
def test_201_delete_table_requires_all_flags(driver):
    
    schema = Postgresql.TableStructure('t201')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    driver.delete_table(driver.t201, True, True, False)
    assert 't201' in driver.get_tables()
    driver.delete_table(driver.t201, True, False, True)
    assert 't201' in driver.get_tables()
    
    driver.delete_table(driver.t201, True, True, True)
    assert 't201' not in driver.get_tables()
def test_202_multiple_tables_independent(driver):
    tables = []
    for i in range(3):
        name = f't202_tbl{i}'
        s = Postgresql.TableStructure(name)
        s.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
        s.add_column('val', Postgresql.DataTypes.INTEGER())
        driver.create_table(s)
        tbl = getattr(driver, name)
        tables.append(tbl)
    for tbl in tables:
        tbl.insert({tbl.val: 100})
    for tbl in tables:
        rows = tbl.get_row([tbl.val])
        assert rows[0] == 100
def test_203_bulk_insert_with_custom_execute_many(driver):
    schema = Postgresql.TableStructure('t203')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('num', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t203
    data = [(i,) for i in range(1000)]
    tbl.bulk_insert([tbl.num], data)
    count = len(tbl.get_row([tbl.id]))
    assert count == 1000
def test_204_optimize_after_operations(driver):
    schema = Postgresql.TableStructure('t204')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t204
    for i in range(50):
        tbl.insert({tbl.val: i})
    
    tbl.delete_row(where=tbl.val < 25)
    driver.optimize()
    
    count = len(tbl.get_row([tbl.id]))
    assert count == 25
    driver.delete_table(tbl, True, True, True)
def test_205_table_with_special_name(driver):
    schema = Postgresql.TableStructure('My Table')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = getattr(driver, 'My Table')
    tbl.insert({tbl.val: 42})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == 42
def test_206_composite_primary_key(driver):
    
    schema = Postgresql.TableStructure('t206')
    schema.add_column('user_id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('role_id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    tbl = driver.t206
    tbl.insert({tbl.user_id: 1, tbl.role_id: 1})
    tbl.insert({tbl.user_id: 1, tbl.role_id: 2})
    with pytest.raises(Exception):
        tbl.insert({tbl.user_id: 1, tbl.role_id: 1})
    count = driver.custom_execute_with_fetch('SELECT COUNT(*) FROM t206;')
    assert count[0][0] == 2
    driver.delete_table(tbl, True, True, True)
def test_207_fk_parent_child(driver):
    schema_p = Postgresql.TableStructure('t207_dept')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_p.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    driver.create_table(schema_p)
    dept = driver.t207_dept
    dept.insert({dept.name: 'Engineering'})
    dept.insert({dept.name: 'Marketing'})
    schema_c = Postgresql.TableStructure('t207_emp')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    schema_c.add_column('dept_id', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('dept_id', dept, dept.id)  
    driver.create_table(schema_c)
    emp = driver.t207_emp
    emp.insert({emp.name: 'Ali', emp.dept_id: 1})
    emp.insert({emp.name: 'Sara', emp.dept_id: 2})
    count = len(emp.get_row([emp.id]))
    assert count == 2
def test_208_get_databases_excludes_templates(driver):
    
    dbs = driver.get_databases()
    assert 'template0' not in dbs
    assert 'template1' not in dbs
    assert PG_DB_NAME in dbs
def test_209_create_and_drop_user(driver):
    
    test_user = 't209_user'
    try:
        driver.drop_user(test_user)
    except:
        pass
    driver.create_user(test_user, 'pass123')
    users = driver.custom_execute_with_fetch(
        "SELECT usename FROM pg_user WHERE usename = %s;", (test_user,)
    )
    assert len(users) == 1
    driver.drop_user(test_user)
    users = driver.custom_execute_with_fetch(
        "SELECT usename FROM pg_user WHERE usename = %s;", (test_user,)
    )
    assert len(users) == 0
def test_210_disconnect_and_double_disconnect():
    
    drv = Postgresql.Driver(
        host=PG_HOST, port=PG_PORT, username=PG_USER,
        password=PG_PASSWORD, db_name=PG_DB_NAME
    )
    assert drv._connected is True
    drv.disconnect()
    assert drv._connected is False
    with pytest.raises(RuntimeError):
        drv.disconnect()
def test_211_full_lifecycle(driver):
    schema = Postgresql.TableStructure('t211')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50))
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t211
    tbl.insert({tbl.name: 'Ali', tbl.age: 30})
    tbl.insert({tbl.name: 'Sara', tbl.age: 25})
    
    rows = tbl.get_row([tbl.id])
    assert len(rows) == 2
    
    tbl.update({tbl.age: 31}, where=tbl.name == 'Ali')
    rows = tbl.get_row([tbl.age], where=tbl.name == 'Ali')
    assert rows[0] == 31
    
    tbl.delete_row(where=tbl.name == 'Sara')
    rows = tbl.get_row([tbl.id])
    assert len(rows) == 1
    
    driver.delete_table(tbl, True, True, True)
    assert 't211' not in driver.get_tables()
def test_213_data_type_date_invalid_format(driver):
    schema = Postgresql.TableStructure('t213')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.DATE())
    driver.create_table(schema)
    tbl = driver.t213
    with pytest.raises(Exception):
        tbl.insert({tbl.val: 'Not a Date'})
def test_214_data_type_time_invalid_format(driver):
    schema = Postgresql.TableStructure('t214')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.TIME())
    driver.create_table(schema)
    tbl = driver.t214
    with pytest.raises(Exception):
        tbl.insert({tbl.val: '25:99:99'})
def test_215_data_type_timestamp_invalid_format(driver):
    schema = Postgresql.TableStructure('t215')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.TIMESTAMP())
    driver.create_table(schema)
    tbl = driver.t215
    with pytest.raises(Exception):
        tbl.insert({tbl.val: '2023-13-40 99:99:99'})
def test_216_data_type_date_arithmetic_add_interval(driver):
    schema = Postgresql.TableStructure('t216')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('d', Postgresql.DataTypes.DATE())
    schema.add_column('i', Postgresql.DataTypes.INTERVAL())
    driver.create_table(schema)
    tbl = driver.t216
    tbl.insert({tbl.d: '2023-01-01', tbl.i: '1 month'})
    res = tbl.get_row([tbl.d + tbl.i])
    
    
    
    date_str = str(res[0])[:10]  
    assert date_str == '2023-02-01'
def test_217_data_type_date_arithmetic_sub_date(driver):
    schema = Postgresql.TableStructure('t217')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('d1', Postgresql.DataTypes.DATE())
    schema.add_column('d2', Postgresql.DataTypes.DATE())
    driver.create_table(schema)
    tbl = driver.t217
    tbl.insert({tbl.d1: '2023-01-10', tbl.d2: '2023-01-01'})
    res = tbl.get_row([tbl.d1 - tbl.d2])
    
    assert res[0] == 9
def test_223_data_type_json_basic(driver):
    schema = Postgresql.TableStructure('t223')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.JSON())
    driver.create_table(schema)
    tbl = driver.t223
    tbl.insert({tbl.val: '{"key": "value"}'})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == {"key": "value"} 
def test_234_data_type_uuid_invalid_format(driver):
    schema = Postgresql.TableStructure('t234')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.UUID())
    driver.create_table(schema)
    tbl = driver.t234
    with pytest.raises(Exception):
        tbl.insert({tbl.val: 'not-a-uuid'})
def test_240_data_type_array_text(driver):
    schema = Postgresql.TableStructure('t240')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.TEXT()))
    driver.create_table(schema)
    tbl = driver.t240
    tbl.insert({tbl.val: ['a', 'b', 'c']})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == ['a', 'b', 'c']
def test_241_data_type_array_nested(driver):
    schema = Postgresql.TableStructure('t241')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.INTEGER())))
    driver.create_table(schema)
    tbl = driver.t241
    tbl.insert({tbl.val: [[1, 2], [3, 4]]})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == [[1, 2], [3, 4]]
def test_242_data_type_array_empty(driver):
    schema = Postgresql.TableStructure('t242')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.INTEGER()))
    driver.create_table(schema)
    tbl = driver.t242
    tbl.insert({tbl.val: []})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == []
def test_243_data_type_cidr_basic(driver):
    schema = Postgresql.TableStructure('t243')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.VARCHAR(20))  
    driver.create_table(schema)
    tbl = driver.t243
    cidr_val = '192.168.1.0/24'
    tbl.insert({tbl.val: cidr_val})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == cidr_val
def test_244_data_type_inet_basic(driver):
    schema = Postgresql.TableStructure('t244')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.VARCHAR(20))
    driver.create_table(schema)
    tbl = driver.t244
    inet_val = '192.168.1.5'
    tbl.insert({tbl.val: inet_val})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == inet_val
def test_245_data_type_macaddr_basic(driver):
    schema = Postgresql.TableStructure('t245')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.VARCHAR(20))
    driver.create_table(schema)
    tbl = driver.t245
    mac_val = '08:00:2b:01:02:03'
    tbl.insert({tbl.val: mac_val})
    rows = tbl.get_row([tbl.val])
    assert rows[0] == mac_val
def test_246_data_type_xml_basic(driver):
    schema = Postgresql.TableStructure('t246')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.TEXT())  
    driver.create_table(schema)
    tbl = driver.t246
    xml_val = '<book><title>Manual</title></book>'
    tbl.insert({tbl.val: xml_val})
    rows = tbl.get_row([tbl.val])
    assert '<title>Manual</title>' in rows[0]
@pytest.fixture(scope="module")
def driver():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except Exception:
        pass
    yield drv
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except Exception:
        pass
    drv.disconnect()
def test_251_structure_add_column_basic(driver):
    schema = Postgresql.TableStructure('t251')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    cols = driver.t251.get_columns_name()
    assert 'name' in cols
def test_252_structure_add_column_multiple(driver):
    schema = Postgresql.TableStructure('t252')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('a', Postgresql.DataTypes.INTEGER())
    schema.add_column('b', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    cols = driver.t252.get_columns_name()
    assert len(cols) == 3
def test_253_structure_add_column_chainable(driver):
    schema = Postgresql.TableStructure('t253')
    sql = (schema
           .add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
           .add_column('val', Postgresql.DataTypes.INTEGER())
           .get_structure())
    driver.create_table(schema)
    assert 'id' in sql and 'val' in sql
    assert 't253' in driver.get_tables()
def test_254_structure_delete_column_existing(driver):
    schema = Postgresql.TableStructure('t254')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('to_del', Postgresql.DataTypes.TEXT())
    schema.delete_column('to_del')
    driver.create_table(schema)
    cols = driver.t254.get_columns_name()
    assert 'to_del' not in cols
def test_255_structure_delete_column_nonexistent(driver):
    schema = Postgresql.TableStructure('t255')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    with pytest.raises(Exception):
        schema.delete_column('ghost_col')
def test_256_structure_primary_key_single(driver):
    schema = Postgresql.TableStructure('t256')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    
    assert 't256' in driver.get_tables()
    cols = driver.t256.get_columns_name()
    assert 'id' in cols
def test_257_structure_primary_key_composite(driver):
    schema = Postgresql.TableStructure('t257')
    schema.add_column('id1', Postgresql.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('id2', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    assert 't257' in driver.get_tables()
    cols = driver.t257.get_columns_name()
    assert 'id1' in cols and 'id2' in cols
def test_258_structure_foreign_key_basic(driver):
    schema_p = Postgresql.TableStructure('p258')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p258
    schema_c = Postgresql.TableStructure('t258')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id)
    driver.create_table(schema_c)
    
    tbl_p.insert({})  
    driver.t258.insert({driver.t258.pid: 1})
    res = driver.t258.get_row([driver.t258.pid])
    assert res == [1]
def test_259_structure_foreign_key_on_delete_cascade(driver):
    schema_p = Postgresql.TableStructure('p259')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p259
    schema_c = Postgresql.TableStructure('t259')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id, on_delete='CASCADE')
    driver.create_table(schema_c)
    tbl_p.insert({})
    driver.t259.insert({driver.t259.pid: 1})
    tbl_p.delete_row(tbl_p.id == 1)
    res = driver.t259.get_row([driver.t259.id])
    assert res == []
def test_260_structure_foreign_key_on_delete_restrict(driver):
    schema_p = Postgresql.TableStructure('p260')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p260
    schema_c = Postgresql.TableStructure('t260')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id, on_delete='RESTRICT')
    driver.create_table(schema_c)
    tbl_p.insert({})
    driver.t260.insert({driver.t260.pid: 1})
    with pytest.raises(Exception):
        tbl_p.delete_row(tbl_p.id == 1)
def test_261_structure_foreign_key_on_delete_set_null(driver):
    schema_p = Postgresql.TableStructure('p261')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p261
    schema_c = Postgresql.TableStructure('t261')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id, on_delete='SET NULL')
    driver.create_table(schema_c)
    tbl_p.insert({})
    driver.t261.insert({driver.t261.pid: 1})
    tbl_p.delete_row(tbl_p.id == 1)
    res = driver.t261.get_row([driver.t261.pid])
    assert res == [None]
def test_262_structure_foreign_key_on_delete_set_default(driver):
    schema_p = Postgresql.TableStructure('p262')
    schema_p.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p262
    
    tbl_p.insert({tbl_p.id: 0})
    tbl_p.insert({tbl_p.id: 1})
    schema_c = Postgresql.TableStructure('t262')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER(), default_value=0)
    schema_c.foreign_key('pid', tbl_p, tbl_p.id, on_delete='SET DEFAULT')
    driver.create_table(schema_c)
    driver.t262.insert({driver.t262.pid: 1})
    tbl_p.delete_row(tbl_p.id == 1)
    res = driver.t262.get_row([driver.t262.pid])
    assert res == [0]
def test_263_structure_foreign_key_on_update_cascade(driver):
    schema_p = Postgresql.TableStructure('p263')
    schema_p.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p263
    schema_c = Postgresql.TableStructure('t263')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id, on_update='CASCADE')
    driver.create_table(schema_c)
    tbl_p.insert({tbl_p.id: 1})
    driver.t263.insert({driver.t263.pid: 1})
    tbl_p.update({tbl_p.id: 99}, tbl_p.id == 1)
    res = driver.t263.get_row([driver.t263.pid])
    assert res == [99]
def test_266_structure_unique_single(driver):
    schema = Postgresql.TableStructure('t266')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('email', Postgresql.DataTypes.VARCHAR(100), unique=True)
    driver.create_table(schema)
    driver.t266.insert({driver.t266.email: 'a@b.com'})
    with pytest.raises(Exception):
        driver.t266.insert({driver.t266.email: 'a@b.com'})
def test_270_structure_not_null(driver):
    schema = Postgresql.TableStructure('t270')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT(), not_null=True)
    driver.create_table(schema)
    with pytest.raises(Exception):
        driver.t270.insert({driver.t270.name: None})
def test_271_structure_default_value_integer(driver):
    schema = Postgresql.TableStructure('t271')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('val', Postgresql.DataTypes.INTEGER(), default_value=42)
    driver.create_table(schema)
    driver.t271.insert({})  
    res = driver.t271.get_row([driver.t271.val])
    assert res == [42]
def test_272_structure_default_value_string(driver):
    schema = Postgresql.TableStructure('t272')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50), default_value='guest')
    driver.create_table(schema)
    driver.t272.insert({})
    res = driver.t272.get_row([driver.t272.name])
    assert res == ['guest']
def test_273_structure_default_value_boolean(driver):
    schema = Postgresql.TableStructure('t273')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('is_active', Postgresql.DataTypes.BOOLEAN(), default_value=True)
    driver.create_table(schema)
    driver.t273.insert({})
    res = driver.t273.get_row([driver.t273.is_active])
    assert res == [True]
def test_274_structure_default_value_function(driver):
    schema = Postgresql.TableStructure('t274')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('created_at', Postgresql.DataTypes.TIMESTAMP(), default_value='NOW()')
    driver.create_table(schema)
    driver.t274.insert({})
    res = driver.t274.get_row([driver.t274.created_at])
    assert res[0] is not None
def test_275_structure_auto_increment_serial(driver):
    schema = Postgresql.TableStructure('t275')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    driver.t275.insert({})
    driver.t275.insert({})
    res = driver.t275.get_row([driver.t275.id], order_by=driver.t275.id)
    assert res == [1, 2]
def test_276_structure_auto_increment_bigserial(driver):
    schema = Postgresql.TableStructure('t276')
    schema.add_column('id', Postgresql.DataTypes.BIGSERIAL(), primary_key=True)
    driver.create_table(schema)
    driver.t276.insert({})
    res = driver.t276.get_row([driver.t276.id])
    assert res == [1]
def test_277_structure_get_columns(driver):
    schema = Postgresql.TableStructure('t277')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('a', Postgresql.DataTypes.INTEGER())
    schema.add_column('b', Postgresql.DataTypes.TEXT())
    cols = schema.get_columns()
    assert len(cols) == 3
    assert any(c['name'] == '"a"' or c['name'] == 'a' for c in cols)
def test_278_structure_get_structure_sql(driver):
    schema = Postgresql.TableStructure('t278')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    sql = schema.get_structure()
    assert "CREATE TABLE" in sql
    assert "PRIMARY KEY" in sql
def test_279_structure_no_columns_error(driver):
    schema = Postgresql.TableStructure('t279')
    with pytest.raises(Exception):
        schema.get_structure()
def test_280_structure_duplicate_column_error(driver):
    schema = Postgresql.TableStructure('t280')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    with pytest.raises(Exception):
        schema.add_column('id', Postgresql.DataTypes.TEXT())
def test_281_structure_invalid_column_name(driver):
    schema = Postgresql.TableStructure('t281')
    
    try:
        schema.add_column('invalid name!', Postgresql.DataTypes.INTEGER())
        driver.create_table(schema)
        assert False, "Expected error"
    except Exception:
        pass
def test_282_structure_invalid_data_type(driver):
    schema = Postgresql.TableStructure('t282')
    with pytest.raises(Exception):
        schema.add_column('val', 123456)
def test_283_structure_add_index(driver):
    schema = Postgresql.TableStructure('t283')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    driver.create_table(schema)
    tbl = driver.t283
    tbl.create_index('idx_t283_name', [tbl.name])
    res = driver.custom_execute_with_fetch(
        "SELECT indexname FROM pg_indexes WHERE tablename='t283';"
    )
    assert any('name' in i[0] for i in res)
def test_284_structure_add_foreign_key_invalid_ref(driver):
    schema_p = Postgresql.TableStructure('p284')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p284
    schema_c = Postgresql.TableStructure('t284')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    with pytest.raises(Exception):
        schema_c.foreign_key('pid', tbl_p, getattr(tbl_p, 'non_existent_col', None))
def test_285_structure_table_name_quoting(driver):
    schema = Postgresql.TableStructure('Table With Spaces')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    driver.create_table(schema)
    assert 'Table With Spaces' in driver.get_tables()
def test_300_structure_unique_null_distinct(driver):
    schema = Postgresql.TableStructure('t300')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('val', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    driver.t300.insert({driver.t300.id: 1, driver.t300.val: None})
    driver.t300.insert({driver.t300.id: 2, driver.t300.val: None})
    res = driver.t300.get_row([driver.t300.id])
    assert len(res) == 2
@pytest.fixture(scope="module")
def driver():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except Exception:
        pass
    yield drv
    try:
        for t in drv.get_tables():
            drv.custom_execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    except Exception:
        pass
    drv.disconnect()
def test_301_insert_single_row(driver):
    schema = Postgresql.TableStructure('t301')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t301
    tbl.insert({tbl.id: 1, tbl.name: 'Ali'})
    res = tbl.get_row([tbl.id, tbl.name])
    assert res == [(1, 'Ali')]
def test_302_insert_multiple_rows(driver):
    schema = Postgresql.TableStructure('t302')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t302
    tbl.insert({tbl.id: 1, tbl.name: 'A'})
    tbl.insert({tbl.id: 2, tbl.name: 'B'})
    tbl.insert({tbl.id: 3, tbl.name: 'C'})
    res = tbl.get_row([tbl.id])
    assert len(res) == 3
def test_303_insert_with_all_columns(driver):
    schema = Postgresql.TableStructure('t303')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t303
    tbl.insert({tbl.id: 1, tbl.name: 'Reza', tbl.age: 25})
    res = tbl.get_row([tbl.id, tbl.name, tbl.age])
    assert res == [(1, 'Reza', 25)]
def test_304_insert_with_partial_columns(driver):
    schema = Postgresql.TableStructure('t304')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t304
    tbl.insert({tbl.id: 1, tbl.name: 'Sara'})
    res = tbl.get_row([tbl.id, tbl.name, tbl.age])
    assert res == [(1, 'Sara', None)]
def test_305_insert_missing_required_column(driver):
    schema = Postgresql.TableStructure('t305')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT(), not_null=True)
    driver.create_table(schema)
    tbl = driver.t305
    with pytest.raises(Exception):
        tbl.insert({tbl.id: 1})
def test_306_insert_invalid_data_type(driver):
    schema = Postgresql.TableStructure('t306')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('val', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = driver.t306
    with pytest.raises(Exception):
        tbl.insert({tbl.id: 1, tbl.val: 'not_an_int'})
def test_307_insert_violates_unique_constraint(driver):
    schema = Postgresql.TableStructure('t307')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    tbl = driver.t307
    tbl.insert({tbl.id: 1})
    with pytest.raises(Exception):
        tbl.insert({tbl.id: 1})
def test_309_insert_violates_foreign_key(driver):
    schema_p = Postgresql.TableStructure('p309')
    schema_p.add_column('id', Postgresql.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema_p)
    tbl_p = driver.p309
    schema_c = Postgresql.TableStructure('t309')
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', tbl_p, tbl_p.id)
    driver.create_table(schema_c)
    with pytest.raises(Exception):
        driver.t309.insert({driver.t309.pid: 99})
def test_310_insert_violates_not_null(driver):
    schema = Postgresql.TableStructure('t310')
    schema.add_column('val', Postgresql.DataTypes.TEXT(), not_null=True)
    driver.create_table(schema)
    tbl = driver.t310
    with pytest.raises(Exception):
        tbl.insert({tbl.val: None})
def test_314_insert_with_serial_id_omitted(driver):
    schema = Postgresql.TableStructure('t314')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t314
    tbl.insert({tbl.name: 'A'})
    tbl.insert({tbl.name: 'B'})
    res = tbl.get_row([tbl.id], order_by=tbl.id)
    assert res == [1, 2]
def test_315_insert_with_explicit_serial_id(driver):
    schema = Postgresql.TableStructure('t315')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t315
    tbl.insert({tbl.id: 100, tbl.name: 'Explicit'})
    res = tbl.get_row([tbl.id])
    assert res == [100]
def test_316_insert_with_default_values(driver):
    schema = Postgresql.TableStructure('t316')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('status', Postgresql.DataTypes.TEXT(), default_value='active')
    driver.create_table(schema)
    tbl = driver.t316
    tbl.insert({})  
    res = tbl.get_row([tbl.status])
    assert res == ['active']
def test_317_insert_with_null_values(driver):
    schema = Postgresql.TableStructure('t317')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('val', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t317
    tbl.insert({tbl.id: 1, tbl.val: None})
    res = tbl.get_row([tbl.val])
    assert res == [None]
def test_318_insert_with_special_chars_string(driver):
    schema = Postgresql.TableStructure('t318')
    schema.add_column('val', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    val = "O'Connor\nNewLine\tTab"
    tbl = driver.t318
    tbl.insert({tbl.val: val})
    res = tbl.get_row([tbl.val])
    assert res == [val]
def test_319_insert_with_unicode_string(driver):
    schema = Postgresql.TableStructure('t319')
    schema.add_column('val', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    val = "日本語 ελληνικά"
    tbl = driver.t319
    tbl.insert({tbl.val: val})
    res = tbl.get_row([tbl.val])
    assert res == [val]
def test_321_insert_with_array(driver):
    schema = Postgresql.TableStructure('t321')
    schema.add_column('val', Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.INTEGER()))
    driver.create_table(schema)
    tbl = driver.t321
    tbl.insert({tbl.val: [1, 2, 3]})
    res = tbl.get_row([tbl.val])
    assert res == [[1, 2, 3]]
def test_322_insert_bulk_execute_many(driver):
    schema = Postgresql.TableStructure('t322')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    data = [(1, 'A'), (2, 'B'), (3, 'C')]
    driver.t322.bulk_insert([driver.t322.id, driver.t322.name], data)
    
    res = driver.t322.get_row([driver.t322.id])
    assert len(res) == 3
def test_323_insert_bulk_partial_failure_rollback(driver):
    schema = Postgresql.TableStructure('t323')
    schema.add_column('id', Postgresql.DataTypes.INTEGER(), unique=True)
    driver.create_table(schema)
    data = [(1,), (2,), (1,)]
    with pytest.raises(Exception):
        driver.t323.bulk_insert([driver.t323.id], data)
        
    res = driver.t323.get_row([driver.t323.id])
    assert len(res) == 0
def test_332_insert_timestamp_auto_now(driver):
    schema = Postgresql.TableStructure('t332')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    schema.add_column('created_at', Postgresql.DataTypes.TIMESTAMP(), default_value='NOW()')
    driver.create_table(schema)
    tbl = driver.t332
    tbl.insert({tbl.id: 1})
    res = tbl.get_row([tbl.created_at])
    assert res[0] is not None
def test_333_insert_uuid_auto_generate(driver):
    
    import uuid
    schema = Postgresql.TableStructure('t333')
    schema.add_column('id', Postgresql.DataTypes.UUID(), default_value=f"{uuid.uuid1()}")
    driver.create_table(schema)
    tbl = driver.t333
    tbl.insert({})
    res = tbl.get_row([tbl.id])
    assert len(str(res[0])) == 36
def test_334_insert_bytea_binary(driver):
    schema = Postgresql.TableStructure('t334')
    schema.add_column('val', Postgresql.DataTypes.BYTEA())
    driver.create_table(schema)
    binary_data = b'\x00\xFF\x10\x20'
    tbl = driver.t334
    tbl.insert({tbl.val: binary_data})
    res = tbl.get_row([tbl.val])
    assert res == [binary_data]
def test_335_insert_large_object(driver):
    schema = Postgresql.TableStructure('t335')
    schema.add_column('val', Postgresql.DataTypes.BYTEA())
    driver.create_table(schema)
    large_data = os.urandom(2 * 1024 * 1024)
    tbl = driver.t335
    tbl.insert({tbl.val: large_data})
    res = driver.custom_execute_with_fetch("SELECT length(val) FROM t335;")
    assert res[0][0] == 2097152
def test_345_insert_case_sensitivity(driver):
    schema = Postgresql.TableStructure('T345_Case')
    schema.add_column('ID', Postgresql.DataTypes.INTEGER())
    schema.add_column('Name', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    
    tbl = getattr(driver, 'T345_Case')
    tbl.insert({tbl.ID: 1, tbl.Name: 'Test'})
    res = tbl.get_row([tbl.ID, tbl.Name])
    assert res == [(1, 'Test')]
def test_346_insert_reserved_keyword_column(driver):
    schema = Postgresql.TableStructure('t346')
    schema.add_column('select', Postgresql.DataTypes.INTEGER())
    schema.add_column('from', Postgresql.DataTypes.TEXT())
    driver.create_table(schema)
    tbl = driver.t346
    tbl.insert({getattr(tbl, 'select'): 1, getattr(tbl, 'from'): 'A'})
    res = tbl.get_row([getattr(tbl, 'select'), getattr(tbl, 'from')])
    assert res == [(1, 'A')]
def test_347_insert_reserved_keyword_table(driver):
    schema = Postgresql.TableStructure('table')
    schema.add_column('id', Postgresql.DataTypes.INTEGER())
    driver.create_table(schema)
    tbl = getattr(driver, 'table')
    tbl.insert({tbl.id: 1})
    res = tbl.get_row([tbl.id])
    assert res == [1]
@pytest.fixture(scope="function")
def select_driver():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    try:
        drv.custom_execute('DROP TABLE IF EXISTS select_test;')
    except Exception:
        pass
    schema = Postgresql.TableStructure('select_test')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50), not_null=True)
    schema.add_column('age', Postgresql.DataTypes.INTEGER(), not_null=True)
    schema.add_column('score', Postgresql.DataTypes.REAL())
    schema.add_column('grade', Postgresql.DataTypes.VARCHAR(2))
    drv.create_table(schema)
    tbl = drv.select_test
    for name, age, score, grade in [
        ('Alice', 30, 85.5, 'A'),
        ('Bob', 25, 92.0, 'A'),
        ('Charlie', 35, 45.0, 'C'),
        ('David', 25, 75.5, 'B'),
        ('Eve', 30, None, None),
    ]:
        tbl.insert({tbl.name: name, tbl.age: age, tbl.score: score, tbl.grade: grade})
    yield drv
    try:
        drv.custom_execute('DROP TABLE IF EXISTS select_test;')
    except Exception:
        pass
    drv.disconnect()
def test_351_select_all_rows(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id, tbl.name, tbl.age, tbl.score, tbl.grade])
    assert len(res) == 5
def test_352_select_specific_columns(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name, tbl.age])
    assert len(res) == 5
    assert len(res[0]) == 2
def test_353_select_where_simple_eq(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age == 30)
    assert len(res) == 2
def test_354_select_where_simple_neq(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age != 30)
    assert len(res) == 3
def test_355_select_where_gt(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age > 30)
    assert len(res) == 1
def test_356_select_where_lt(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age < 25)
    assert len(res) == 0
def test_357_select_where_gte(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age >= 30)
    assert len(res) == 3
def test_358_select_where_lte(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age <= 25)
    assert len(res) == 2
def test_359_select_where_like(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], where=tbl.name.like('A%'))
    assert len(res) == 1
    assert res[0] == 'Alice'
def test_361_select_where_in(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age.In(data_list=[25, 35]))
    assert len(res) == 3
def test_366_select_where_and(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row(
        [tbl.name],
        where=(tbl.age == 30) & (tbl.score > 80)
    )
    assert len(res) == 1
    assert res[0] == 'Alice'
def test_367_select_where_or(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row(
        [tbl.id],
        where=(tbl.age == 25) | (tbl.age == 35)
    )
    assert len(res) == 3
def test_368_select_where_not(select_driver):
    
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.id], where=tbl.age != 30)
    assert len(res) == 3
def test_369_select_where_complex_nested(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row(
        [tbl.id],
        where=((tbl.age == 30) & (tbl.score > 80)) | ((tbl.age == 25) & (tbl.grade == 'A'))
    )
    assert len(res) == 2
def test_370_select_order_by_asc(select_driver):
    tbl = select_driver.select_test
    res = tbl.get_row([tbl.name], order_by=tbl.name)
    assert res[0] == 'Alice'
    assert res[4] == 'Eve'
def test_393_select_subquery_in(select_driver):
    tbl = select_driver.select_test
    
    res = tbl.get_row(
        [tbl.name],
        where=tbl.id.In(column=tbl.id, where=tbl.score > 80),
        order_by=tbl.name
    )
    assert len(res) == 2
    assert res[0] == 'Alice'
    assert res[1] == 'Bob'
@pytest.fixture(scope="module")
def driver_upd():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME, create_new_db=True
        )
    except Exception:
        drv = Postgresql.Driver(
            host=PG_HOST, port=PG_PORT, username=PG_USER,
            password=PG_PASSWORD, db_name=PG_DB_NAME
        )
    for t in ('upd_del_test', 'fk_child', 'fk_parent'):
        try:
            drv.custom_execute(f'DROP TABLE IF EXISTS {t} CASCADE;')
        except Exception:
            pass
    schema = Postgresql.TableStructure('upd_del_test')
    schema.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(50), not_null=True, unique=True)
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    schema.add_column('data', Postgresql.DataTypes.JSONB())
    schema.add_column('tags', Postgresql.DataTypes.ARRAY(Postgresql.DataTypes.TEXT()))
    schema.add_column('created_at', Postgresql.DataTypes.TIMESTAMP())
    drv.create_table(schema)
    drv.custom_execute(
        'ALTER TABLE upd_del_test ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;'
    )
    drv.custom_execute(
        'ALTER TABLE upd_del_test ADD CONSTRAINT chk_age CHECK (age >= 18);'
    )
    schema_p = Postgresql.TableStructure('fk_parent')
    schema_p.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    drv.create_table(schema_p)
    schema_c = Postgresql.TableStructure('fk_child')
    schema_c.add_column('id', Postgresql.DataTypes.SERIAL(), primary_key=True)
    schema_c.add_column('pid', Postgresql.DataTypes.INTEGER())
    schema_c.foreign_key('pid', drv.fk_parent, drv.fk_parent.id, on_delete='CASCADE')
    drv.create_table(schema_c)
    yield drv
    for t in ('upd_del_test', 'fk_child', 'fk_parent'):
        try:
            drv.custom_execute(f'DROP TABLE IF EXISTS {t} CASCADE;')
        except Exception:
            pass
    drv.disconnect()
def test_401_update_single_column(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Alice', tbl.age: 25})
    tbl.update({tbl.age: 26}, where=tbl.name == 'Alice')
    res = tbl.get_row([tbl.age], where=tbl.name == 'Alice')
    assert res == [26]
    tbl.delete_row(where=tbl.name == 'Alice')
def test_402_update_multiple_columns(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Bob', tbl.age: 30})
    tbl.update({tbl.age: 31, tbl.name: 'Robert'}, where=tbl.name == 'Bob')
    res = tbl.get_row([tbl.name, tbl.age], where=tbl.name == 'Robert')
    assert res == [('Robert', 31)]
    tbl.delete_row(where=tbl.name == 'Robert')
def test_404_update_where_simple(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Charlie', tbl.age: 22})
    tbl.update({tbl.age: 23}, where=tbl.name == 'Charlie')
    res = tbl.get_row([tbl.age], where=tbl.name == 'Charlie')
    assert res == [23]
    tbl.delete_row(where=tbl.name == 'Charlie')
def test_405_update_where_complex(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'X', tbl.age: 20})
    tbl.insert({tbl.name: 'Y', tbl.age: 25})
    tbl.update({tbl.age: 50}, where=(tbl.name == 'X') & (tbl.age < 25))
    res = tbl.get_row([tbl.age], where=tbl.name == 'X')
    assert res == [50]
    tbl.delete_row(where=tbl.name.In(data_list=['X', 'Y']))
def test_408_update_violates_check(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Frank', tbl.age: 20})
    with pytest.raises(Exception):
        tbl.update({tbl.age: 17}, where=tbl.name == 'Frank')
    tbl.delete_row(where=tbl.name == 'Frank')
def test_409_update_violates_unique(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Unique1', tbl.age: 20})
    tbl.insert({tbl.name: 'Unique2', tbl.age: 20})
    with pytest.raises(Exception):
        tbl.update({tbl.name: 'Unique1'}, where=tbl.name == 'Unique2')
    tbl.delete_row(where=tbl.name.In(data_list=['Unique1', 'Unique2']))
def test_410_update_violates_foreign_key(driver_upd):
    parent = driver_upd.fk_parent
    child = driver_upd.fk_child
    parent.insert({parent.id: 1})
    child.insert({child.pid: 1})
    with pytest.raises(Exception):
        child.update({child.pid: 999}, where=child.pid == 1)
    child.delete_row(where=child.pid == 1)
    parent.delete_row(where=parent.id == 1)
def test_411_update_violates_not_null(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'NullTest', tbl.age: 20})
    with pytest.raises(Exception):
        tbl.update({tbl.name: None}, where=tbl.name == 'NullTest')
    tbl.delete_row(where=tbl.name == 'NullTest')
def test_412_update_with_subquery(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'SubT', tbl.age: 20})
    tbl.insert({tbl.name: 'SubT2', tbl.age: 30})
    
    tbl.update(
        {tbl.age: 99},
        where=tbl.id.In(column=tbl.id, where=tbl.name == 'SubT')
    )
    res = tbl.get_row([tbl.age], where=tbl.name == 'SubT')
    assert res == [99]
    tbl.delete_row(where=tbl.name.In(data_list=['SubT', 'SubT2']))
def test_419_update_increment(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'IncT', tbl.age: 20})
    tbl.update({tbl.age: tbl.age + 1}, where=tbl.name == 'IncT')
    res = tbl.get_row([tbl.age], where=tbl.name == 'IncT')
    assert res == [21]
    tbl.delete_row(where=tbl.name == 'IncT')
def test_420_update_decrement(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'DecT', tbl.age: 25})
    tbl.update({tbl.age: tbl.age - 5}, where=tbl.name == 'DecT')  
    res = tbl.get_row([tbl.age], where=tbl.name == 'DecT')
    assert res == [20]
    tbl.delete_row(where=tbl.name == 'DecT')
def test_421_update_string_concat(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Str', tbl.age: 20})
    tbl.update({tbl.name: tbl.name + '_suffix'}, where=tbl.name == 'Str')
    res = tbl.get_row([tbl.name], where=tbl.name.like('Str%'))
    assert res == ['Str_suffix']
    tbl.delete_row(where=tbl.name == 'Str_suffix')
def test_423_update_invalid_data_type(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'InvT', tbl.age: 20})
    with pytest.raises(Exception):
        tbl.update({tbl.age: 'not_an_int'}, where=tbl.name == 'InvT')
    tbl.delete_row(where=tbl.name == 'InvT')
def test_424_update_no_matching_rows(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.update({tbl.age: 100}, where=tbl.name == 'DoesNotExist')
    res = tbl.get_row([tbl.id], where=tbl.age == 100)
    assert len(res) == 0
def test_425_update_deadlock_handling(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'DeadT', tbl.age: 20})
    tbl.update({tbl.age: 19}, where=tbl.name == 'DeadT')  
    res = tbl.get_row([tbl.age], where=tbl.name == 'DeadT')
    assert res == [19]
    tbl.delete_row(where=tbl.name == 'DeadT')
def test_427_delete_single_row(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Del1', tbl.age: 20})
    tbl.delete_row(where=tbl.name == 'Del1')
    res = tbl.get_row([tbl.id], where=tbl.name == 'Del1')
    assert len(res) == 0
def test_428_delete_multiple_rows(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'Del2', tbl.age: 20})
    tbl.insert({tbl.name: 'Del3', tbl.age: 20})
    tbl.delete_row(where=tbl.age == 20)
    res = tbl.get_row([tbl.id], where=tbl.name.In(data_list=['Del2', 'Del3']))
    assert len(res) == 0
def test_430_delete_where_simple(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'SimpleDel', tbl.age: 20})
    tbl.delete_row(where=tbl.name == 'SimpleDel')
    res = tbl.get_row([tbl.id], where=tbl.name == 'SimpleDel')
    assert len(res) == 0
def test_431_delete_where_complex(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'CDel1', tbl.age: 20})
    tbl.insert({tbl.name: 'CDel2', tbl.age: 25})
    tbl.delete_row(where=(tbl.age < 25) & tbl.name.like('C%'))
    res = tbl.get_row([tbl.id], where=tbl.name == 'CDel2')
    assert len(res) == 1
    tbl.delete_row(where=tbl.name == 'CDel2')
def test_434_delete_with_subquery(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.insert({tbl.name: 'SubDel', tbl.age: 20})
    
    tbl.delete_row(
        where=tbl.id.In(column=tbl.id, where=tbl.name == 'SubDel')
    )
    res = tbl.get_row([tbl.id], where=tbl.name == 'SubDel')
    assert len(res) == 0
def test_437_delete_violates_foreign_key(driver_upd):
    
    
    
    
    
    
    parent = driver_upd.fk_parent
    child = driver_upd.fk_child
    parent.insert({parent.id: 100})
    child.insert({child.pid: 100})
    
    parent.delete_row(where=parent.id == 100)
    res = child.get_row([child.id], where=child.pid == 100)
    assert len(res) == 0
def test_438_delete_cascade_foreign_key(driver_upd):
    parent = driver_upd.fk_parent
    child = driver_upd.fk_child
    parent.insert({parent.id: 200})
    child.insert({child.pid: 200})
    parent.delete_row(where=parent.id == 200)
    res = child.get_row([child.id], where=child.pid == 200)
    assert len(res) == 0
def test_439_delete_no_matching_rows(driver_upd):
    tbl = driver_upd.upd_del_test
    tbl.delete_row(where=tbl.name == 'NonExistent')
    res = tbl.get_row([tbl.id], where=tbl.name == 'NonExistent')
    assert len(res) == 0
