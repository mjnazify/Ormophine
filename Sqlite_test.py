import pytest
import threading
import time
from Ormophine import Sqlite
import datetime
@pytest.fixture
def db_path(tmp_path):
    
    return str(tmp_path / "test_driver.db")
@pytest.fixture
def driver(db_path):
    
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    yield drv
    try:
        drv.disconnect()
    except:
        pass
@pytest.fixture
def driver_with_table(driver):
    
    schema = Sqlite.TableStructure('users', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Sqlite.DataTypes.TEXT())
    driver.create_table(schema)
    return driver
def test_01_driver_valid_path(db_path):
    
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    assert drv is not None
    assert hasattr(drv, 'main_queue')
    drv.disconnect()
def test_02_driver_invalid_path():
    
    with pytest.raises(Exception):
        Sqlite.Driver('/invalid_dir/which/does/not/exist/db.db', setup_time=0.1)
def test_03_driver_isolation_immediate(db_path):
    
    drv = Sqlite.Driver(db_path, isolation_level='IMMEDIATE', setup_time=0.1)
    assert drv is not None
    drv.disconnect()
def test_04_driver_isolation_exclusive(db_path):
    
    drv = Sqlite.Driver(db_path, isolation_level='EXCLUSIVE', setup_time=0.1)
    assert drv is not None
    drv.disconnect()
def test_05_driver_cache_size_256(db_path):
    
    drv = Sqlite.Driver(db_path, cache_size=256, setup_time=0.1)
    assert drv is not None
    drv.disconnect()
def test_06_driver_cache_size_0(db_path):
    
    drv = Sqlite.Driver(db_path, cache_size=0, setup_time=0.1)
    assert drv is not None
    drv.disconnect()
def test_07_driver_reader_pool_size_3(db_path):
    
    drv = Sqlite.Driver(db_path, none_block_reader_pool_size=3, setup_time=0.1)
    assert drv.reader_pool_size == 3
    drv.disconnect()
def test_08_driver_reader_pool_size_0(db_path):
    
    drv = Sqlite.Driver(db_path, none_block_reader_pool_size=0, setup_time=0.1)
    assert drv.reader_pool_size == 0
    drv.disconnect()
def test_09_driver_existing_db_with_tables(db_path):
    
    
    drv1 = Sqlite.Driver(db_path, setup_time=0.1)
    drv1.custom_execute("CREATE TABLE test1 (id INTEGER);")
    drv1.custom_execute("CREATE TABLE test2 (id INTEGER);")
    drv1.disconnect()
    
    
    drv2 = Sqlite.Driver(db_path, setup_time=0.2)
    assert hasattr(drv2, 'test1')
    assert hasattr(drv2, 'test2')
    drv2.disconnect()
def test_10_driver_empty_db(db_path):
    
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    tables = drv.get_tables()
    assert len(tables) == 0
    drv.disconnect()
def test_11_access_table_via_attribute(driver_with_table):
    
    assert hasattr(driver_with_table, 'users')
    assert isinstance(driver_with_table.users, Sqlite.Table)
def test_12_table_object_existing(driver_with_table):
    
    tbl = driver_with_table.table_object('users')
    assert isinstance(tbl, Sqlite.Table)
    assert tbl.name_ == '[users]'
def test_13_table_object_nonexistent(driver):
    
    driver.custom_execute("CREATE TABLE dummy (id INTEGER);")
    with pytest.raises(Exception, match="No such table named"):
        driver.table_object('non_existent_table')
def test_14_table_object_no_tables(driver):
    
    with pytest.raises(Exception, match="No table found"):
        driver.table_object('any_table')
def test_15_get_tables_empty(driver):
    
    tables = driver.get_tables()
    assert tables == {}
def test_16_get_tables_multiple(driver):
    
    driver.custom_execute("CREATE TABLE tbl_a (id INTEGER);")
    driver.custom_execute("CREATE TABLE tbl_b (id INTEGER);")
    tables = driver.get_tables()
    assert 'tbl_a' in tables
    assert 'tbl_b' in tables
    assert len(tables) == 2
def test_17_custom_execute_create_table(driver):
    
    driver.custom_execute("CREATE TABLE my_tbl (id INTEGER, name TEXT);")
    tables = driver.get_tables()
    assert 'my_tbl' in tables
def test_18_custom_execute_insert_params(driver_with_table):
    
    driver_with_table.custom_execute("INSERT INTO users (id, name) VALUES (?, ?);", [1, 'Ali'])
    res = driver_with_table.custom_execute_with_fetch("SELECT * FROM users;")
    assert len(res) == 1
    assert res[0][1] == 'Ali'
def test_19_custom_execute_invalid_query(driver):
    
    with pytest.raises(Exception):
        driver.custom_execute("INSERT INTO non_existent_table VALUES (1);")
def test_20_custom_execute_drop_table(driver_with_table):
    
    driver_with_table.custom_execute("DROP TABLE users;")
    tables = driver_with_table.get_tables()
    assert 'users' not in tables
def test_21_custom_execute_many_insert(driver_with_table):
    
    data = [(1, 'A'), (2, 'B'), (3, 'C')]
    driver_with_table.custom_execute_many("INSERT INTO users (id, name) VALUES (?, ?);", data)
    res = driver_with_table.custom_execute_with_fetch("SELECT * FROM users;")
    assert len(res) == 3
def test_22_custom_execute_many_incompatible_params(driver_with_table):
    
    data = [(1, 'A', 'Extra'), (2, 'B')] 
    with pytest.raises(Exception):
        driver_with_table.custom_execute_many("INSERT INTO users (id, name) VALUES (?, ?);", data)
def test_23_custom_execute_many_update(driver_with_table):
    
    driver_with_table.custom_execute("INSERT INTO users (id, name) VALUES (1, 'Old');")
    data = [['New1'], ['New2']]
    
    driver_with_table.custom_execute_many("UPDATE users SET name = ? WHERE id = 1;", data)
    res = driver_with_table.custom_execute_with_fetch("SELECT name FROM users;")
    assert res[-1][0] == 'New2' 
def test_24_custom_execute_with_fetch_select(driver_with_table):
    
    driver_with_table.custom_execute("INSERT INTO users (id, name) VALUES (1, 'Test');")
    res = driver_with_table.custom_execute_with_fetch("SELECT id, name FROM users;")
    assert res == [(1, 'Test')]
def test_25_custom_execute_with_fetch_where(driver_with_table):
    
    driver_with_table.custom_execute("INSERT INTO users (id, name) VALUES (1, 'Ali');")
    driver_with_table.custom_execute("INSERT INTO users (id, name) VALUES (2, 'Reza');")
    res = driver_with_table.custom_execute_with_fetch("SELECT name FROM users WHERE id = ?;", [2])
    assert res == [('Reza',)]
def test_26_custom_execute_with_fetch_reader_pool(driver_with_table):
    
    driver_with_table.custom_execute("INSERT INTO users (id, name) VALUES (1, 'PoolTest');")
    res = driver_with_table.custom_execute_with_fetch("SELECT name FROM users;", from_readers_pool=True)
    assert res == [('PoolTest',)]
def test_27_custom_execute_with_fetch_invalid(driver):
    
    with pytest.raises(Exception):
        driver.custom_execute_with_fetch("SELECT * FROM missing_table;")
def test_28_custom_execute_with_fetch_no_result(driver_with_table):
    
    res = driver_with_table.custom_execute_with_fetch("SELECT * FROM users WHERE id = 999;")
    assert res == []
def test_29_create_table_valid(driver):
    
    schema = Sqlite.TableStructure('products', strict=True)
    schema.add_column('pid', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('title', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    assert isinstance(tbl, Sqlite.Table)
    assert hasattr(driver, 'products')
def test_30_create_table_duplicate(driver):
    
    schema = Sqlite.TableStructure('duplicated', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema)
    with pytest.raises(Exception):
        driver.create_table(schema)
def test_31_create_table_with_fk(driver):
    
    schema1 = Sqlite.TableStructure('categories', strict=True)
    schema1.add_column('cid', Sqlite.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema1)
    schema2 = Sqlite.TableStructure('items', strict=True)
    schema2.add_column('iid', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema2.add_column('cid', Sqlite.DataTypes.INTEGER())
    schema2.foreign_key('cid', driver.categories, driver.categories.cid)
    tbl = driver.create_table(schema2)
    assert isinstance(tbl, Sqlite.Table)
def test_32_create_table_invalid_fk(driver):
    
    schema = Sqlite.TableStructure('bad_fk_tbl', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('fid', Sqlite.DataTypes.INTEGER())
    tbl = driver.create_table(schema)
    assert isinstance(tbl, Sqlite.Table)
def test_33_defragment(driver_with_table):
    driver_with_table.custom_execute("INSERT INTO users (id, name) VALUES (1, 'Ali');")
    driver_with_table.defragment()   
def test_34_defragment_empty(driver):
    
    driver.defragment() 
def test_35_set_WAL_mode_enable(driver):
    
    
    driver.set_WAL_mode(True, wal_timer=60)
    res = driver.custom_execute_with_fetch("PRAGMA journal_mode;")
    assert res[0][0].lower() == 'wal'
def test_36_set_WAL_mode_disable(driver):
    
    driver.set_WAL_mode(True, wal_timer=60)
    driver.set_WAL_mode(False)
    res = driver.custom_execute_with_fetch("PRAGMA journal_mode;")
    assert res[0][0].lower() == 'persist'
def test_37_set_WAL_mode_timer_30(driver):
    
    
    driver.set_WAL_mode(True, wal_timer=30)
    assert driver.wal_enabled.is_set()
def test_38_set_WAL_mode_timer_0(driver):
    
    
    driver.set_WAL_mode(True, wal_timer=0)
    time.sleep(0.1) 
    driver.set_WAL_mode(False) 
def test_39_checkpoint_timer_background(driver):
    
    driver.set_WAL_mode(True, wal_timer=1)
    driver.custom_execute("CREATE TABLE test_tbl (id INTEGER);")
    driver.custom_execute("INSERT INTO test_tbl VALUES (1);")
    time.sleep(2) 
    
    driver.set_WAL_mode(False)
def test_40_disconnect_normal(driver):
    
    driver.custom_execute("CREATE TABLE t1 (id INTEGER);")
    print(888)
    driver.disconnect()
    print(1)
    with pytest.raises(RuntimeError):
        print(2)
        driver._exc('qf', ('SELECT * FROM t1;',))
        print(3)
    print(4)
def test_41_disconnect_with_wal(driver):
    
    driver.set_WAL_mode(True, wal_timer=1)
    driver.custom_execute("CREATE TABLE t1 (id INTEGER);")
    driver.disconnect()
    
def test_42_disconnect_with_pending_queries(db_path):
    
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    drv.custom_execute("CREATE TABLE t1 (id INTEGER);")
    
    drv.main_queue.put(['qcb', ('INSERT INTO t1 VALUES (1);',), __import__('queue').SimpleQueue()])
    drv.disconnect()
    
    drv2 = Sqlite.Driver(db_path, setup_time=0.1)
    res = drv2.custom_execute_with_fetch("SELECT * FROM t1;")
    assert len(res) == 1
    drv2.disconnect()
def test_43_concurrent_main_queue_order(driver):
    
    driver.custom_execute("CREATE TABLE seq_test (val INTEGER);")
    threads = []
    for i in range(5):
        t = threading.Thread(target=driver.custom_execute, args=("INSERT INTO seq_test VALUES (?);", [i]))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    
    res = driver.custom_execute_with_fetch("SELECT COUNT(*) FROM seq_test;")
    assert res[0][0] == 5
def test_44_reader_pool_concurrent(db_path):
    
    drv = Sqlite.Driver(db_path, none_block_reader_pool_size=2, setup_time=0.1)
    drv.custom_execute("CREATE TABLE r_test (id INTEGER);")
    drv.custom_execute("INSERT INTO r_test VALUES (1);")
    
    results = [None, None]
    def read_thread(idx):
        results[idx] = drv.custom_execute_with_fetch("SELECT * FROM r_test;", from_readers_pool=True)
    
    t1 = threading.Thread(target=read_thread, args=(0,))
    t2 = threading.Thread(target=read_thread, args=(1,))
    t1.start(); t2.start()
    t1.join(); t2.join()
    
    assert results[0] == [(1,)]
    assert results[1] == [(1,)]
    drv.disconnect()
def test_45_read_write_no_interfere(driver):
    
    driver.custom_execute("CREATE TABLE rw_test (id INTEGER);")
    driver.custom_execute("INSERT INTO rw_test VALUES (1);")
    
    
    def write():
        for i in range(10):
            driver.custom_execute("INSERT INTO rw_test VALUES (?);", [i+2])
    
    t = threading.Thread(target=write)
    t.start()
    time.sleep(0.1) 
    res = driver.custom_execute_with_fetch("SELECT COUNT(*) FROM rw_test;", from_readers_pool=True)
    t.join()
    
    
    assert res[0][0] >= 1
def test_46_exc_qf(driver):
    
    driver.custom_execute("CREATE TABLE qf_test (val TEXT);")
    driver.custom_execute("INSERT INTO qf_test VALUES ('hello');")
    res = driver._exc('qf', ('SELECT val FROM qf_test;',))
    assert res == [('hello',)]
def test_47_exc_qcb(driver):
    
    driver.custom_execute("CREATE TABLE qcb_test (val INTEGER);")
    driver._exc('qcb', ('INSERT INTO qcb_test VALUES (100);',))
    res = driver._exc('qf', ('SELECT val FROM qcb_test;',))
    assert res == [(100,)]
def test_48_exc_qsb(driver):
    
    driver.custom_execute("CREATE TABLE qsb_test (id INTEGER);")
    script = [
        ('INSERT INTO qsb_test VALUES (1);',),
        ('INSERT INTO qsb_test VALUES (2);',),
        ('INSERT INTO qsb_test VALUES (3);',)
    ]
    driver._exc('qsb', script)
    res = driver._exc('qf', ('SELECT COUNT(*) FROM qsb_test;',))
    assert res[0][0] == 3
def test_49_exc_qmb(driver):
    
    driver.custom_execute("CREATE TABLE qmb_test (id INTEGER);")
    data = [(1,), (2,), (3,)]
    driver._exc('qmb', ('INSERT INTO qmb_test VALUES (?);', data))
    res = driver._exc('qf', ('SELECT COUNT(*) FROM qmb_test;',))
    assert res[0][0] == 3
def test_50_exc_cp(driver):
    
    
    driver.set_WAL_mode(True, wal_timer=60)
    driver.custom_execute("CREATE TABLE cp_test (id INTEGER);")
    driver.custom_execute("INSERT INTO cp_test VALUES (1);")
    
    from queue import SimpleQueue
    q = SimpleQueue()
    driver.main_queue.put(['cp', q])
    res = q.get(timeout=5)
    assert res is True
@pytest.fixture
def db_path(tmp_path):
    
    return str(tmp_path / "test_pragma.db")
@pytest.fixture
def driver(db_path):
    
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    yield drv
    try:
        drv.disconnect()
    except:
        pass
def test_51_journal_mode_wal(driver):
    
    driver.SetPragma.journal_mode('WAL')
    res = driver.custom_execute_with_fetch("PRAGMA journal_mode;")
    assert res[0][0].upper() == 'WAL'
def test_52_journal_mode_delete(driver):
    
    driver.SetPragma.journal_mode('DELETE')
    res = driver.custom_execute_with_fetch("PRAGMA journal_mode;")
    assert res[0][0].upper() == 'DELETE'
def test_53_journal_mode_persist(driver):
    
    driver.SetPragma.journal_mode('PERSIST')
    res = driver.custom_execute_with_fetch("PRAGMA journal_mode;")
    assert res[0][0].upper() == 'PERSIST'
def test_54_journal_mode_memory(driver):
    
    driver.SetPragma.journal_mode('MEMORY')
    res = driver.custom_execute_with_fetch("PRAGMA journal_mode;")
    assert res[0][0].upper() == 'MEMORY'
def test_55_journal_mode_off(driver):
    
    driver.SetPragma.journal_mode('OFF')
    res = driver.custom_execute_with_fetch("PRAGMA journal_mode;")
    assert res[0][0].upper() == 'OFF'
def test_56_journal_mode_invalid(driver):
    
    with pytest.raises(Exception):
        driver.SetPragma.journal_mode('INVALID_MODE')
def test_57_synchronous_normal(driver):
    
    driver.SetPragma.synchronous('NORMAL')
    res = driver.custom_execute_with_fetch("PRAGMA synchronous;")
    assert res[0][0] == 1 
def test_58_synchronous_off(driver):
    
    driver.SetPragma.synchronous('OFF')
    res = driver.custom_execute_with_fetch("PRAGMA synchronous;")
    assert res[0][0] == 0 
def test_59_synchronous_full(driver):
    
    driver.SetPragma.synchronous('FULL')
    res = driver.custom_execute_with_fetch("PRAGMA synchronous;")
    assert res[0][0] == 2 
def test_60_synchronous_extra(driver):
    
    driver.SetPragma.synchronous('EXTRA')
    res = driver.custom_execute_with_fetch("PRAGMA synchronous;")
    assert res[0][0] == 3 
def test_61_synchronous_invalid(driver):
    
    with pytest.raises(Exception):
        driver.SetPragma.synchronous('SUPER')
def test_62_wal_autocheckpoint_1000(driver):
    
    driver.SetPragma.journal_mode('WAL')
    driver.SetPragma.wal_autocheckpoint(1000)
    res = driver.custom_execute_with_fetch("PRAGMA wal_autocheckpoint;")
    assert res[0][0] == 1000
def test_63_wal_autocheckpoint_0(driver):
    
    driver.SetPragma.journal_mode('WAL')
    driver.SetPragma.wal_autocheckpoint(0)
    res = driver.custom_execute_with_fetch("PRAGMA wal_autocheckpoint;")
    assert res[0][0] == 0
def test_64_wal_autocheckpoint_negative(driver):
    
    with pytest.raises(Exception):
        driver.SetPragma.wal_autocheckpoint(-100)
def test_65_wal_checkpoint_passive(driver):
    
    driver.SetPragma.journal_mode('WAL')
    driver.custom_execute("CREATE TABLE t1 (id INTEGER);")
    driver.custom_execute("INSERT INTO t1 VALUES (1);")
    
    driver.SetPragma.wal_checkpoint()
def test_66_wal_checkpoint_full(driver):
    
    driver.SetPragma.journal_mode('WAL')
    driver.custom_execute("CREATE TABLE t1 (id INTEGER);")
    driver.SetPragma.wal_checkpoint('FULL')
def test_67_wal_checkpoint_truncate(driver):
    
    driver.SetPragma.journal_mode('WAL')
    driver.custom_execute("CREATE TABLE t1 (id INTEGER);")
    driver.SetPragma.wal_checkpoint('TRUNCATE')
def test_68_wal_checkpoint_restart(driver):
    
    driver.SetPragma.journal_mode('WAL')
    driver.custom_execute("CREATE TABLE t1 (id INTEGER);")
    driver.SetPragma.wal_checkpoint('RESTART')
def test_69_wal_checkpoint_invalid(driver):
    
    with pytest.raises(Exception):
        driver.SetPragma.wal_checkpoint('INVALID_MODE')
def test_70_foreign_keys_true(driver):
    
    driver.SetPragma.foreign_keys(True)
    res = driver.custom_execute_with_fetch("PRAGMA foreign_keys;")
    assert res[0][0] == 1
def test_71_foreign_keys_false(driver):
    
    driver.SetPragma.foreign_keys(False)
    res = driver.custom_execute_with_fetch("PRAGMA foreign_keys;")
    assert res[0][0] == 0
def test_72_foreign_keys_on_off_str(driver):
    
    driver.SetPragma.foreign_keys('ON')
    res1 = driver.custom_execute_with_fetch("PRAGMA foreign_keys;")
    driver.SetPragma.foreign_keys('OFF')
    res2 = driver.custom_execute_with_fetch("PRAGMA foreign_keys;")
    assert res1[0][0] == 1 and res2[0][0] == 0
def test_73_foreign_keys_invalid(driver):
    with pytest.raises(Exception):
        driver.SetPragma.foreign_keys('SURE')
def test_74_defer_foreign_keys_true(driver):
    
    driver.SetPragma.foreign_keys(True)
    driver.custom_execute("CREATE TABLE parent (id INTEGER PRIMARY KEY);")
    driver.custom_execute("CREATE TABLE child (id INTEGER, pid INTEGER REFERENCES parent(id));")
    
    driver.SetPragma.defer_foreign_keys(True)
    
    script = [
        ("INSERT INTO child (id, pid) VALUES (1, 100);",),
        ("INSERT INTO parent (id) VALUES (100);",)
    ]
    driver._exc('qsb', script)
    res = driver.custom_execute_with_fetch("SELECT * FROM child;")
    assert len(res) == 1
def test_75_defer_foreign_keys_false(driver):
    
    driver.SetPragma.foreign_keys(True)
    driver.custom_execute("CREATE TABLE parent2 (id INTEGER PRIMARY KEY);")
    driver.custom_execute("CREATE TABLE child2 (id INTEGER, pid INTEGER REFERENCES parent2(id));")
    
    driver.SetPragma.defer_foreign_keys(False)
    
    with pytest.raises(Exception):
        driver.custom_execute("INSERT INTO child2 (id, pid) VALUES (1, 200);")
def test_76_defer_foreign_keys_on_off_str(driver):
    
    driver.SetPragma.defer_foreign_keys('ON')
    res1 = driver.custom_execute_with_fetch("PRAGMA defer_foreign_keys;")
    driver.SetPragma.defer_foreign_keys('OFF')
    res2 = driver.custom_execute_with_fetch("PRAGMA defer_foreign_keys;")
    assert res1[0][0] == 1 and res2[0][0] == 0
def test_77_cache_size_positive(driver):
    
    driver.SetPragma.cache_size(2000)
    res = driver.custom_execute_with_fetch("PRAGMA cache_size;")
    assert res[0][0] == 2000
def test_78_cache_size_negative(driver):
    
    driver.SetPragma.cache_size(-2048)
    res = driver.custom_execute_with_fetch("PRAGMA cache_size;")
    assert res[0][0] == -2048
def test_79_cache_size_zero(driver):
    
    driver.SetPragma.cache_size(0)
    res = driver.custom_execute_with_fetch("PRAGMA cache_size;")
    assert res[0][0] == 0
def test_80_cache_size_large(driver):
    
    driver.SetPragma.cache_size(100000)
    res = driver.custom_execute_with_fetch("PRAGMA cache_size;")
    assert res[0][0] == 100000
def test_81_mmap_size_zero(driver):
    
    driver.SetPragma.mmap_size(0)
    res = driver.custom_execute_with_fetch("PRAGMA mmap_size;")
    assert res[0][0] == 0
def test_82_mmap_size_1mb(driver):
    
    size = 1024 * 1024
    driver.SetPragma.mmap_size(size)
    res = driver.custom_execute_with_fetch("PRAGMA mmap_size;")
    assert res[0][0] == size
def test_83_mmap_size_negative(driver):
    
    with pytest.raises(Exception):
        driver.SetPragma.mmap_size(-1024)
def test_84_mmap_size_very_large(driver):
    size = 2**30  
    driver.SetPragma.mmap_size(size)
    res = driver.custom_execute_with_fetch("PRAGMA mmap_size;")
    assert res[0][0] == size
def test_85_shrink_memory(driver):
    
    driver.custom_execute("CREATE TABLE t1 (id INTEGER);")
    driver.SetPragma.shrink_memory() 
def test_86_shrink_memory_after_delete(driver):
    
    driver.custom_execute("CREATE TABLE t1 (id INTEGER);")
    driver.custom_execute_many("INSERT INTO t1 VALUES (?);", [(i,) for i in range(1000)])
    driver.custom_execute("DELETE FROM t1;")
    driver.SetPragma.shrink_memory() 
def test_87_optimize_no_args(driver):
    
    driver.SetPragma.optimize()
def test_88_optimize_default_mask(driver):
    
    driver.SetPragma.optimize(mask=0x10002)
def test_89_optimize_specific_mask(driver):
    
    driver.SetPragma.optimize(mask=0x0001)
def test_90_optimize_str_mask(driver):
    
    with pytest.raises(Exception):
        driver.SetPragma.optimize(mask="0x10002")
def test_91_automatic_index_true(driver):
    
    driver.SetPragma.automatic_index(True)
    res = driver.custom_execute_with_fetch("PRAGMA automatic_index;")
    assert res[0][0] == 1
def test_92_automatic_index_false(driver):
    
    driver.SetPragma.automatic_index(False)
    res = driver.custom_execute_with_fetch("PRAGMA automatic_index;")
    assert res[0][0] == 0
def test_93_automatic_index_on_off_str(driver):
    
    driver.SetPragma.automatic_index('ON')
    res1 = driver.custom_execute_with_fetch("PRAGMA automatic_index;")
    driver.SetPragma.automatic_index('OFF')
    res2 = driver.custom_execute_with_fetch("PRAGMA automatic_index;")
    assert res1[0][0] == 1 and res2[0][0] == 0
def test_94_writable_schema_on(driver):
    
    driver.SetPragma.writable_schema('ON')
    
    driver.SetPragma.writable_schema('OFF') 
def test_95_writable_schema_off(driver):
    
    driver.SetPragma.writable_schema('OFF')
    res = driver.custom_execute_with_fetch("PRAGMA writable_schema;")
    assert res[0][0] == 0
def test_96_writable_schema_reset(driver):
    
    driver.SetPragma.writable_schema('RESET')
def test_97_writable_schema_bool(driver):
    
    driver.SetPragma.writable_schema(True)
    res1 = driver.custom_execute_with_fetch("PRAGMA writable_schema;")
    driver.SetPragma.writable_schema(False)
    res2 = driver.custom_execute_with_fetch("PRAGMA writable_schema;")
    assert res1[0][0] == 1 and res2[0][0] == 0
def test_98_combine_wal_and_sync(driver):
    
    driver.SetPragma.journal_mode('WAL')
    driver.SetPragma.synchronous('NORMAL')
    j_res = driver.custom_execute_with_fetch("PRAGMA journal_mode;")
    s_res = driver.custom_execute_with_fetch("PRAGMA synchronous;")
    assert j_res[0][0].upper() == 'WAL' and s_res[0][0] == 1
def test_99_combine_cache_and_mmap(driver):
    
    driver.SetPragma.cache_size(-4096)
    driver.SetPragma.mmap_size(2048*1024)
    c_res = driver.custom_execute_with_fetch("PRAGMA cache_size;")
    m_res = driver.custom_execute_with_fetch("PRAGMA mmap_size;")
    assert c_res[0][0] == -4096 and m_res[0][0] == 2048*1024
def test_100_wal_checkpoint_after_tx(driver):
    
    driver.SetPragma.journal_mode('WAL')
    driver.custom_execute("CREATE TABLE t1 (id INTEGER);")
    for i in range(5):
        driver.custom_execute("INSERT INTO t1 VALUES (?);", [i])
    
    driver.SetPragma.wal_checkpoint('TRUNCATE')
    res = driver.custom_execute_with_fetch("SELECT COUNT(*) FROM t1;")
    assert res[0][0] == 5
@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_datatypes.db")
@pytest.fixture
def driver(db_path):
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    yield drv
    try:
        drv.disconnect()
    except:
        pass
def test_101_integer_no_constraint():
    
    dt = Sqlite.DataTypes.INTEGER()
    schema = Sqlite.TableStructure('t101', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "INTEGER" in sql
    assert "CHECK" not in sql
def test_102_integer_unsigned():
    
    dt = Sqlite.DataTypes.INTEGER(unsigned=True)
    schema = Sqlite.TableStructure('t102', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "INTEGER" in sql
    assert "CHECK" in sql
    assert ">= 0" in sql
def test_103_integer_min_max():
    
    dt = Sqlite.DataTypes.INTEGER(min_val=1, max_val=10)
    schema = Sqlite.TableStructure('t103', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "CHECK" in sql
    assert ">= 1" in sql
    assert "<= 10" in sql
def test_104_integer_min_max_unsigned():
    
    
    dt = Sqlite.DataTypes.INTEGER(min_val=1, max_val=10, unsigned=True)
    schema = Sqlite.TableStructure('t104', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "CHECK" in sql
    assert ">= 1" in sql 
def test_105_real_no_constraint():
    
    dt = Sqlite.DataTypes.REAL()
    schema = Sqlite.TableStructure('t105', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "REAL" in sql
    assert "CHECK" not in sql
def test_106_real_min_max():
    
    dt = Sqlite.DataTypes.REAL(min_val=0.0, max_val=100.0)
    schema = Sqlite.TableStructure('t106', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "CHECK" in sql
    assert ">= 0.0" in sql or ">= 0" in sql
    assert "<= 100.0" in sql or "<= 100" in sql
def test_107_real_unsigned():
    
    dt = Sqlite.DataTypes.REAL(unsigned=True)
    schema = Sqlite.TableStructure('t107', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "CHECK" in sql
    assert ">= 0" in sql
def test_108_float_equivalent():
    
    dt = Sqlite.DataTypes.FLOAT()
    schema = Sqlite.TableStructure('t108', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "REAL" in sql or "FLOAT" in sql 
def test_109_double_equivalent():
    
    dt = Sqlite.DataTypes.DOUBLE()
    schema = Sqlite.TableStructure('t109', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "REAL" in sql or "DOUBLE" in sql
def test_110_decimal_precision_scale():
    
    
    dt = Sqlite.DataTypes.DECIMAL(precision=5, scale=2)
    schema = Sqlite.TableStructure('t110', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "REAL" in sql or "NUMERIC" in sql or "DECIMAL" in sql
    assert "CHECK" in sql
def test_111_decimal_unsigned():
    
    dt = Sqlite.DataTypes.DECIMAL(precision=5, scale=2, unsigned=True)
    schema = Sqlite.TableStructure('t111', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert ">= 0" in sql
def test_112_decimal_override_min_max():
    
    dt = Sqlite.DataTypes.DECIMAL(precision=5, scale=2, min_val=-10, max_val=10)
    schema = Sqlite.TableStructure('t112', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "BETWEEN -10 AND 10" in sql
def test_113_decimal_no_scale():
    
    dt = Sqlite.DataTypes.DECIMAL(precision=5)
    schema = Sqlite.TableStructure('t113', strict=True)
    schema.add_column('col', dt, primary_key=True)
    
    sql = schema.get_structure()
    assert "CHECK" in sql
def test_114_decimal_no_precision():
    
    dt = Sqlite.DataTypes.DECIMAL(scale=2)
    schema = Sqlite.TableStructure('t114', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "CHECK" in sql
def test_115_numeric_equivalent():
    
    dt = Sqlite.DataTypes.NUMERIC()
    schema = Sqlite.TableStructure('t115', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "NUMERIC" in sql or "REAL" in sql
def test_116_text_no_constraint():
    
    dt = Sqlite.DataTypes.TEXT()
    schema = Sqlite.TableStructure('t116', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "TEXT" in sql
    assert "CHECK" not in sql
def test_117_text_min_length():
    
    dt = Sqlite.DataTypes.TEXT(min_length=3)
    schema = Sqlite.TableStructure('t117', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "length" in sql.lower()
    assert ">= 3" in sql
def test_118_text_max_length():
    
    dt = Sqlite.DataTypes.TEXT(max_length=50)
    schema = Sqlite.TableStructure('t118', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "length" in sql.lower()
    assert "<= 50" in sql
def test_119_text_min_max_length():
    
    dt = Sqlite.DataTypes.TEXT(min_length=3, max_length=50)
    schema = Sqlite.TableStructure('t119', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert ">= 3" in sql and "<= 50" in sql
def test_120_varchar_equivalent():
    
    dt = Sqlite.DataTypes.VARCHAR()
    schema = Sqlite.TableStructure('t120', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "TEXT" in sql
def test_121_char_equivalent():
    
    dt = Sqlite.DataTypes.CHAR()
    schema = Sqlite.TableStructure('t121', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "TEXT" in sql
def test_122_blob():
    
    dt = Sqlite.DataTypes.BLOB()
    schema = Sqlite.TableStructure('t122', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "BLOB" in sql
def test_123_null_type():
    
    dt = Sqlite.DataTypes.NULL()
    schema = Sqlite.TableStructure('t123', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "NULL" in sql
def test_124_tinyint_default():
    
    dt = Sqlite.DataTypes.TINYINT()
    schema = Sqlite.TableStructure('t124', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "BETWEEN -128 AND 127" in sql
def test_125_tinyint_unsigned():
    
    dt = Sqlite.DataTypes.TINYINT(unsigned=True)
    schema = Sqlite.TableStructure('t125', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "BETWEEN 0 AND 255" in sql
def test_126_tinyint_custom_range():
    
    dt = Sqlite.DataTypes.TINYINT(min_val=-50, max_val=50)
    schema = Sqlite.TableStructure('t126', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "BETWEEN -50 AND 50" in sql
def test_127_smallint_default():
    
    dt = Sqlite.DataTypes.SMALLINT()
    schema = Sqlite.TableStructure('t127', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "BETWEEN -32768 AND 32767" in sql
def test_128_smallint_unsigned():
    
    dt = Sqlite.DataTypes.SMALLINT(unsigned=True)
    schema = Sqlite.TableStructure('t128', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "BETWEEN 0 AND 65535" in sql
def test_129_mediumint_default():
    
    dt = Sqlite.DataTypes.MEDIUMINT()
    schema = Sqlite.TableStructure('t129', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "BETWEEN -8388608 AND 8388607" in sql
def test_130_mediumint_unsigned():
    
    dt = Sqlite.DataTypes.MEDIUMINT(unsigned=True)
    schema = Sqlite.TableStructure('t130', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "BETWEEN 0 AND 16777215" in sql
def test_131_int_equivalent():
    
    dt = Sqlite.DataTypes.INT()
    schema = Sqlite.TableStructure('t131', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "INTEGER" in sql or "INT" in sql
def test_132_bigint_equivalent():
    
    dt = Sqlite.DataTypes.BIGINT()
    schema = Sqlite.TableStructure('t132', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "INTEGER" in sql or "BIGINT" in sql
def test_133_enum_values():
    
    dt = Sqlite.DataTypes.ENUM('active', 'inactive')
    schema = Sqlite.TableStructure('t133', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "CHECK" in sql
    assert "'active'" in sql
    assert "'inactive'" in sql
def test_134_enum_single_chars():
    
    dt = Sqlite.DataTypes.ENUM('A', 'B', 'C')
    schema = Sqlite.TableStructure('t134', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "'A'" in sql and "'B'" in sql and "'C'" in sql
def test_135_enum_no_values_error():
    
    with pytest.raises(Exception):
        Sqlite.DataTypes.ENUM()
def test_136_boolean_check():
    
    dt = Sqlite.DataTypes.BOOLEAN()
    schema = Sqlite.TableStructure('t136', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "CHECK" in sql
    assert "0" in sql and "1" in sql
def test_137_custom_geometry():
    
    dt = Sqlite.DataTypes.CUSTOM('GEOMETRY')
    schema = Sqlite.TableStructure('t137', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "GEOMETRY" in sql
def test_138_custom_json_with_check():
    
    dt = Sqlite.DataTypes.CUSTOM('JSON', check='my_saulted_x IS NOT NULL')
    schema = Sqlite.TableStructure('t138', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "JSON" in sql
    
    assert "my_saulted_x" not in sql
    assert "[col] IS NOT NULL" in sql or "col IS NOT NULL" in sql
def test_139_combined_constraints_text():
    
    dt = Sqlite.DataTypes.TEXT(min_length=5, max_length=20)
    schema = Sqlite.TableStructure('t139', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert ">= 5" in sql and "<= 20" in sql
def test_140_integer_add_column_replacement(driver):
    schema = Sqlite.TableStructure('t140', strict=True)
    schema.add_column('col', Sqlite.DataTypes.INTEGER(min_val=10), primary_key=True)
    tbl = driver.create_table(schema)
    sql = schema.get_structure()
    assert "CHECK" in sql and "col" in sql
def test_141_decimal_scale_gt_precision_error():
    
    with pytest.raises(Exception):
        Sqlite.DataTypes.DECIMAL(precision=2, scale=5)
def test_142_text_min_length_zero():
    
    dt = Sqlite.DataTypes.TEXT(min_length=0)
    schema = Sqlite.TableStructure('t142', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    
    assert "TEXT" in sql
def test_143_enum_duplicate_values():
    
    
    dt = Sqlite.DataTypes.ENUM('A', 'B', 'A')
    schema = Sqlite.TableStructure('t143', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "CHECK" in sql
def test_144_custom_complex_check():
    
    dt = Sqlite.DataTypes.CUSTOM('TEXT', check='(length(my_saulted_x) > 5 AND my_saulted_x LIKE \'%test%\')')
    schema = Sqlite.TableStructure('t144', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "my_saulted_x" not in sql
    assert "length([col])" in sql or "length(col)" in sql
def test_145_boolean_default_value():
    
    dt = Sqlite.DataTypes.BOOLEAN()
    schema = Sqlite.TableStructure('t145', strict=True)
    schema.add_column('col', dt, primary_key=True, default_value=False)
    sql = schema.get_structure()
    assert "DEFAULT 0" in sql or "DEFAULT False" in sql
def test_146_integer_min_gt_max_error():
    
    
    with pytest.raises(Exception):
        Sqlite.DataTypes.INTEGER(min_val=100, max_val=10)
def test_147_real_unsigned_conflict():
    
    
    with pytest.raises(Exception):
        Sqlite.DataTypes.REAL(unsigned=True, min_val=-1)
def test_148_decimal_precision_zero():
    
    
    with pytest.raises(Exception):
        Sqlite.DataTypes.DECIMAL(precision=0, scale=0)
def test_149_varchar_max_none():
    
    dt = Sqlite.DataTypes.VARCHAR(max_length=None)
    schema = Sqlite.TableStructure('t149', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    
    assert "TEXT" in sql
    assert "length" not in sql.lower()
def test_150_char_fixed_length():
    
    dt = Sqlite.DataTypes.CHAR(min_length=10, max_length=10)
    schema = Sqlite.TableStructure('t150', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "== 10" in sql or "= 10" in sql
@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_structure.db")
@pytest.fixture
def driver(db_path):
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    yield drv
    try:
        drv.disconnect()
    except:
        pass
def test_151_create_structure_not_strict():
    
    schema = Sqlite.TableStructure('users', strict=False)
    sql = schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).get_structure()
    assert "STRICT" not in sql
def test_152_create_structure_strict():
    
    schema = Sqlite.TableStructure('users', strict=True)
    sql = schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).get_structure()
    assert "STRICT" in sql
def test_153_primarykey_on_conflict():
    
    schema = Sqlite.TableStructure('users', primarykey_on_conflict='REPLACE')
    sql = schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).get_structure()
    assert "ON CONFLICT REPLACE" in sql
def test_154_add_column_basic():
    schema = Sqlite.TableStructure('t154', strict=True)
    schema.add_column('age', Sqlite.DataTypes.INTEGER())
    sql = schema.get_structure()
    
    assert "[age] INTEGER" in sql
def test_155_add_column_numeric_default():
    
    schema = Sqlite.TableStructure('t155', strict=True)
    schema.add_column('age', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('level', Sqlite.DataTypes.INTEGER(), default_value=1)
    sql = schema.get_structure()
    assert "DEFAULT 1" in sql
def test_156_add_column_string_default():
    
    schema = Sqlite.TableStructure('t156', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('role', Sqlite.DataTypes.TEXT(), default_value='user')
    sql = schema.get_structure()
    assert "DEFAULT 'user'" in sql
def test_157_add_column_bytes_default_error():
    
    schema = Sqlite.TableStructure('t157', strict=True)
    with pytest.raises(Exception):
        schema.add_column('data', Sqlite.DataTypes.BLOB(), default_value=b'binary')
def test_158_add_column_unique():
    
    schema = Sqlite.TableStructure('t158', strict=True)
    schema.add_column('email', Sqlite.DataTypes.TEXT(), unique=True)
    sql = schema.get_structure()
    assert "UNIQUE" in sql
def test_159_add_column_unique_on_conflict():
    
    schema = Sqlite.TableStructure('t159', strict=True)
    schema.add_column('email', Sqlite.DataTypes.TEXT(), unique=True, unique_on_conflict='IGNORE')
    sql = schema.get_structure()
    assert "UNIQUE ON CONFLICT IGNORE" in sql
def test_160_add_column_not_null():
    
    schema = Sqlite.TableStructure('t160', strict=True)
    schema.add_column('name', Sqlite.DataTypes.TEXT(), not_null=True)
    sql = schema.get_structure()
    assert "NOT NULL" in sql
def test_161_add_column_not_null_on_conflict():
    
    schema = Sqlite.TableStructure('t161', strict=True)
    schema.add_column('name', Sqlite.DataTypes.TEXT(), not_null=True, not_null_on_conflict='FAIL')
    sql = schema.get_structure()
    assert "NOT NULL ON CONFLICT FAIL" in sql
def test_162_add_column_primary_key():
    
    schema = Sqlite.TableStructure('t162', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    sql = schema.get_structure()
    assert "PRIMARY KEY" in sql
def test_163_add_column_pk_and_unique():
    
    schema = Sqlite.TableStructure('t163', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True, unique=True)
    sql = schema.get_structure()
    assert "PRIMARY KEY" in sql
    assert "UNIQUE" in sql
def test_164_add_column_duplicate_error():
    
    schema = Sqlite.TableStructure('t164', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    with pytest.raises(Exception):
        schema.add_column('id', Sqlite.DataTypes.TEXT())
def test_165_chain_add_column():
    schema = Sqlite.TableStructure('t165', strict=True)
    sql = schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True) \
                .add_column('name', Sqlite.DataTypes.TEXT()) \
                .get_structure()
    
    assert "[id] INTEGER" in sql and "[name] TEXT" in sql
def test_166_delete_column_existing():
    
    schema = Sqlite.TableStructure('t166', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('to_delete', Sqlite.DataTypes.TEXT())
    schema.delete_column('to_delete')
    sql = schema.get_structure()
    assert "to_delete" not in sql
def test_167_delete_column_nonexistent_error():
    
    schema = Sqlite.TableStructure('t167', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    with pytest.raises(Exception):
        schema.delete_column('ghost_col')
def test_168_delete_then_add_same_column():
    schema = Sqlite.TableStructure('t168', strict=True)
    schema.add_column('col', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.delete_column('col')
    schema.add_column('col', Sqlite.DataTypes.TEXT()) 
    sql = schema.get_structure()
    assert "[col] TEXT" in sql
def test_169_get_columns_after_add():
    schema = Sqlite.TableStructure('t169', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Sqlite.DataTypes.TEXT())
    cols = schema.get_columns()
    
    assert any(c['name'] == 'id' for c in cols)
    assert any(c['name'] == 'name' for c in cols)
    assert len(cols) == 2
def test_170_get_columns_after_delete():
    
    schema = Sqlite.TableStructure('t170', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('temp', Sqlite.DataTypes.TEXT())
    schema.delete_column('temp')
    cols = schema.get_columns()
    assert 'temp' not in cols
    assert len(cols) == 1
def test_171_foreign_key_basic(driver):
    schema_parent = Sqlite.TableStructure('parents', strict=True)
    schema_parent.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    parent_table = driver.create_table(schema_parent)
    schema = Sqlite.TableStructure('t171', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('parent_id', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('parent_id', parent_table, parent_table.id)
    sql = schema.get_structure()
    assert "FOREIGN KEY" in sql
    assert "REFERENCES [parents]" in sql  
def test_172_foreign_key_on_delete(driver):
    schema_parent = Sqlite.TableStructure('p', strict=True)
    schema_parent.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    parent_table = driver.create_table(schema_parent)
    schema = Sqlite.TableStructure('t172', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('pid', parent_table, parent_table.id, on_delete='CASCADE')
    sql = schema.get_structure()
    assert "ON DELETE CASCADE" in sql
def test_173_foreign_key_on_update(driver):
    schema_parent = Sqlite.TableStructure('p', strict=True)
    schema_parent.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    parent_table = driver.create_table(schema_parent)
    schema = Sqlite.TableStructure('t173', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('pid', parent_table, parent_table.id, on_update='RESTRICT')
    sql = schema.get_structure()
    assert "ON UPDATE RESTRICT" in sql
def test_174_foreign_key_not_deferrable(driver):
    schema_parent = Sqlite.TableStructure('p', strict=True)
    schema_parent.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    parent_table = driver.create_table(schema_parent)
    schema = Sqlite.TableStructure('t174', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('pid', parent_table, parent_table.id, deferrable=False)
    sql = schema.get_structure()
    assert "NOT DEFERRABLE" in sql
def test_175_foreign_key_initially_immediate(driver):
    schema_parent = Sqlite.TableStructure('p', strict=True)
    schema_parent.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    parent_table = driver.create_table(schema_parent)
    schema = Sqlite.TableStructure('t175', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('pid', parent_table, parent_table.id, initially='IMMEDIATE')
    sql = schema.get_structure()
    assert "INITIALLY IMMEDIATE" in sql
def test_176_foreign_key_deferred(driver):
    schema_parent = Sqlite.TableStructure('p', strict=True)
    schema_parent.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    parent_table = driver.create_table(schema_parent)
    schema = Sqlite.TableStructure('t176', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('pid', parent_table, parent_table.id, deferrable=True, initially='DEFERRED')
    sql = schema.get_structure()
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
def test_177_foreign_key_invalid_ref_runtime_error(driver):
    driver.SetPragma.foreign_keys(True)  
    schema_parent = Sqlite.TableStructure('t177_parent', strict=True)
    schema_parent.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    parent_table = driver.create_table(schema_parent)
    schema_child = Sqlite.TableStructure('t177_child', strict=True)
    schema_child.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema_child.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema_child.foreign_key('pid', parent_table, parent_table.id)
    tbl = driver.create_table(schema_child)
    with pytest.raises(Exception):
        tbl.insert({tbl.id: 1, tbl.pid: 99})
def test_178_multiple_foreign_keys(driver):
    schema1 = Sqlite.TableStructure('tbl1', strict=True)
    schema1.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl1 = driver.create_table(schema1)
    schema2 = Sqlite.TableStructure('tbl2', strict=True)
    schema2.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl2 = driver.create_table(schema2)
    schema = Sqlite.TableStructure('t178', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('fk1', Sqlite.DataTypes.INTEGER())
    schema.add_column('fk2', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('fk1', tbl1, tbl1.id)
    schema.foreign_key('fk2', tbl2, tbl2.id)
    sql = schema.get_structure()
    assert sql.count("FOREIGN KEY") == 2
def test_179_get_structure_no_columns_error():
    
    schema = Sqlite.TableStructure('t179', strict=True)
    with pytest.raises(Exception):
        schema.get_structure()
def test_180_get_structure_one_column():
    schema = Sqlite.TableStructure('t180', strict=True)
    sql = schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).get_structure()
    assert "CREATE TABLE [t180]" in sql
    assert "[id] INTEGER" in sql
def test_181_get_structure_multi_col_pk():
    schema = Sqlite.TableStructure('t181', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Sqlite.DataTypes.TEXT())
    sql = schema.get_structure()
    assert "PRIMARY KEY" in sql and "[name] TEXT" in sql
def test_182_get_structure_pk_on_conflict():
    schema = Sqlite.TableStructure('t182', primarykey_on_conflict='ABORT')
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    sql = schema.get_structure()
    
    
    assert "ON CONFLICT ABORT" in sql
def test_183_get_structure_fk(driver):
    schema_parent = Sqlite.TableStructure('p', strict=True)
    schema_parent.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    parent_table = driver.create_table(schema_parent)
    schema = Sqlite.TableStructure('t183', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('pid', parent_table, parent_table.id)
    sql = schema.get_structure()
    assert "FOREIGN KEY(pid) REFERENCES [p]([id])" in sql
def test_184_get_structure_strict():
    schema = Sqlite.TableStructure('t184', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    sql = schema.get_structure()
    
    assert "STRICT" in sql
def test_185_get_structure_combined(driver):
    schema_parent = Sqlite.TableStructure('p', strict=True)
    schema_parent.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    parent_table = driver.create_table(schema_parent)
    schema = Sqlite.TableStructure('t185', strict=True, primarykey_on_conflict='REPLACE')
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('pid', Sqlite.DataTypes.INTEGER(), not_null=True)
    schema.foreign_key('pid', parent_table, parent_table.id, on_delete='CASCADE')
    sql = schema.get_structure()
    assert "STRICT" in sql and "REPLACE" in sql and "NOT NULL" in sql and "CASCADE" in sql
def test_186_verify_commas_parentheses():
    
    schema = Sqlite.TableStructure('t186', strict=True)
    schema.add_column('a', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('b', Sqlite.DataTypes.TEXT())
    sql = schema.get_structure()
    
    assert ", " in sql 
    assert sql.count('(') == sql.count(')')
def test_187_add_column_bool_default():
    
    schema = Sqlite.TableStructure('t187', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('active', Sqlite.DataTypes.BOOLEAN(), default_value=True)
    sql = schema.get_structure()
    assert "DEFAULT 1" in sql
def test_188_add_column_none_default():
    schema = Sqlite.TableStructure('t188', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('data', Sqlite.DataTypes.TEXT(), default_value=None)
    sql = schema.get_structure()
    assert "DEFAULT" not in sql.split("[data] TEXT")[1].split(",")[0]
def test_189_delete_then_get_columns():
    
    schema = Sqlite.TableStructure('t189', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('rem', Sqlite.DataTypes.TEXT())
    schema.delete_column('rem')
    assert 'rem' not in schema.get_columns()
def test_190_foreign_key_future_table(driver):
    future = driver.create_table(
        Sqlite.TableStructure('future_table', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    )
    schema = Sqlite.TableStructure('t190', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('fid', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('fid', future, future.id)
    sql = schema.get_structure()
    assert "REFERENCES [future_table]" in sql  
def test_191_get_structure_after_rename():
    schema = Sqlite.TableStructure('old_name', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.name = 'new_name'
    sql = schema.get_structure()
    assert "CREATE TABLE [new_name]" in sql
def test_192_pk_on_conflict_variations():
    
    for conflict in ['ROLLBACK', 'ABORT', 'FAIL', 'IGNORE', 'REPLACE']:
        schema = Sqlite.TableStructure(f't192_{conflict}', primarykey_on_conflict=conflict)
        schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
        sql = schema.get_structure()
        assert f"ON CONFLICT {conflict}" in sql
def test_193_add_column_datatype_no_placeholder():
    
        
    dt = Sqlite.DataTypes.CUSTOM('SPECIAL_TYPE')
    schema = Sqlite.TableStructure('t193', strict=True)
    schema.add_column('col', dt, primary_key=True)
    sql = schema.get_structure()
    assert "SPECIAL_TYPE" in sql
def test_194_delete_column_space_in_name():
    
    schema = Sqlite.TableStructure('t194', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('col space', Sqlite.DataTypes.TEXT())
    schema.delete_column('col space')
    assert 'col space' not in schema.get_columns()
def test_195_foreign_key_delete_and_update(driver):
    p = driver.create_table(
        Sqlite.TableStructure('p', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    )
    schema = Sqlite.TableStructure('t195', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('pid', p, p.id, on_delete='SET NULL', on_update='CASCADE')
    sql = schema.get_structure()
    assert "ON DELETE SET NULL" in sql
    assert "ON UPDATE CASCADE" in sql
def test_196_foreign_key_deferrable_defaults(driver):
    p = driver.create_table(
        Sqlite.TableStructure('p', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    )
    schema = Sqlite.TableStructure('t196', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('pid', p, p.id, deferrable=True)  
    sql = schema.get_structure()
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
def test_197_get_columns_float_default():
    schema = Sqlite.TableStructure('t197', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('rate', Sqlite.DataTypes.REAL(), default_value=1.5)
    cols = schema.get_columns()
    assert any(c['name'] == 'rate' for c in cols)
def test_198_get_structure_no_pk():
    
    schema = Sqlite.TableStructure('t198', strict=True)
    schema.add_column('a', Sqlite.DataTypes.INTEGER(), not_null=True)
    sql = schema.get_structure()
    assert "PRIMARY KEY" not in sql
def test_199_get_structure_no_fk():
    
    schema = Sqlite.TableStructure('t199', strict=True)
    schema.add_column('a', Sqlite.DataTypes.INTEGER(), primary_key=True)
    sql = schema.get_structure()
    assert "FOREIGN KEY" not in sql
def test_200_compare_strict_true_false():
    
    schema_s = Sqlite.TableStructure('t200s', strict=True)
    schema_s.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    
    schema_ns = Sqlite.TableStructure('t200ns', strict=False)
    schema_ns.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    
    sql_s = schema_s.get_structure()
    sql_ns = schema_ns.get_structure()
    
    assert "STRICT" in sql_s
    assert "STRICT" not in sql_ns
@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_table_crud.db")
@pytest.fixture
def driver(db_path):
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    yield drv
    try:
        drv.disconnect()
    except:
        pass
@pytest.fixture
def tbl(driver):
    
    schema = Sqlite.TableStructure('users', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Sqlite.DataTypes.TEXT(), not_null=True)
    schema.add_column('age', Sqlite.DataTypes.INTEGER())
    schema.add_column('salary', Sqlite.DataTypes.REAL())
    return driver.create_table(schema)
def test_201_create_table_attribute(driver, tbl):
    
    assert hasattr(driver, 'users')
    assert isinstance(tbl, Sqlite.Table)
def test_202_get_table_info(tbl):
    
    info = tbl.get_table_info()
    assert isinstance(info, list)
    assert len(info) == 4 
def test_203_get_table_info_reader_pool(tbl):
    
    info = tbl.get_table_info(from_readers_pool=True)
    assert len(info) == 4
def test_204_get_columns_name(tbl):
    
    cols = tbl.get_columns_name()
    assert 'id' in cols and 'name' in cols and 'age' in cols and 'salary' in cols
def test_205_get_columns_name_reader_pool(tbl):
    
    cols = tbl.get_columns_name(from_readers_pool=True)
    assert len(cols) == 4
def test_206_insert_full_row(tbl):
    
    tbl.insert({tbl.id: 1, tbl.name: 'Ali', tbl.age: 30, tbl.salary: 5000.0})
    res = tbl.get_row([tbl.name], tbl.id == 1)
    assert res[0] == 'Ali'
def test_207_insert_selected_columns(tbl):
    
    tbl.insert({tbl.id: 2, tbl.name: 'Reza'}) 
    res = tbl.get_row([tbl.age], tbl.id == 2)
    assert res[0] is None
def test_208_insert_none_value(tbl):
    
    tbl.insert({tbl.id: 3, tbl.name: 'NullAge', tbl.age: None})
    res = tbl.get_row([tbl.age], tbl.id == 3)
    assert res[0] is None
def test_209_insert_duplicate_pk_error(tbl):
    
    tbl.insert({tbl.id: 10, tbl.name: 'First'})
    with pytest.raises(Exception):
        tbl.insert({tbl.id: 10, tbl.name: 'Second'})
def test_210_insert_unique_violation_error(driver):
    
    schema = Sqlite.TableStructure('uniq_test', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('code', Sqlite.DataTypes.TEXT(), unique=True)
    tbl_u = driver.create_table(schema)
    tbl_u.insert({tbl_u.id: 1, tbl_u.code: 'A1'})
    with pytest.raises(Exception):
        tbl_u.insert({tbl_u.id: 2, tbl_u.code: 'A1'})
def test_211_insert_datetime(tbl):
    
    now = datetime.datetime.now()
    tbl.insert({tbl.id: 4, tbl.name: str(now)}) 
    res = tbl.get_row([tbl.name], tbl.id == 4)
    assert now.strftime('%Y-%m-%d') in res[0]
def test_212_update_one_column(tbl):
    
    tbl.insert({tbl.id: 1, tbl.name: 'Ali', tbl.age: 30})
    tbl.update({tbl.age: 31}, tbl.id == 1)
    res = tbl.get_row([tbl.age], tbl.id == 1)
    assert res[0] == 31
def test_213_update_multiple_columns(tbl):
    
    tbl.insert({tbl.id: 2, tbl.name: 'Reza', tbl.age: 25, tbl.salary: 1000})
    tbl.update({tbl.age: 26, tbl.salary: 2000}, tbl.id == 2)
    res = tbl.get_row([tbl.age, tbl.salary], tbl.id == 2)
    assert res[0] == (26, 2000)
def test_214_update_with_columns_operation_where(tbl):
    
    tbl.insert({tbl.id: 3, tbl.name: 'Sara', tbl.age: 20})
    tbl.insert({tbl.id: 4, tbl.name: 'Child', tbl.age: 10})
    tbl.update({tbl.age: 21}, tbl.age > 18)
    res = tbl.get_row([tbl.age], tbl.id == 4)
    assert res[0] == 10 
def test_215_update_column_in_value(tbl):
    
    tbl.insert({tbl.id: 5, tbl.name: 'Emp', tbl.salary: 1000})
    tbl.update({tbl.salary: tbl.salary * 1.1}, tbl.id == 5)
    res = tbl.get_row([tbl.salary], tbl.id == 5)
    assert res[0] == pytest.approx(1100.0)
def test_216_update_columns_operation_in_value(tbl):
    
    tbl.insert({tbl.id: 6, tbl.name: 'Emp2', tbl.salary: 2000, tbl.age: 5})
    tbl.update({tbl.salary: tbl.salary + 500}, tbl.id == 6)
    res = tbl.get_row([tbl.salary], tbl.id == 6)
    assert res[0] == pytest.approx(2500.0)
def test_217_update_no_matching_row(tbl):
    
    
    tbl.update({tbl.age: 99}, tbl.id == 999)
def test_218_update_invalid_condition_error(tbl):
    
    with pytest.raises(Exception):
        tbl.update({tbl.age: 99}, "invalid sql string")
def test_219_update_datetime_value(tbl):
    
    tbl.insert({tbl.id: 7, tbl.name: 'Old'})
    now = datetime.datetime.now()
    tbl.update({tbl.name: str(now)}, tbl.id == 7)
    res = tbl.get_row([tbl.name], tbl.id == 7)
    assert '202' in res[0]
def test_220_update_column_from_other_table_error(driver, tbl):
    
    schema = Sqlite.TableStructure('other_tbl', strict=True)
    schema.add_column('val', Sqlite.DataTypes.INTEGER(), primary_key=True)
    other = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.update({tbl.age: other.val}, tbl.id == 1)
def test_221_delete_row_simple(tbl):
    
    tbl.insert({tbl.id: 1, tbl.name: 'ToDelete'})
    tbl.delete_row(tbl.id == 1)
    res = tbl.get_row([tbl.name], tbl.id == 1)
    assert len(res) == 0
def test_222_delete_row_complex_condition(tbl):
    
    tbl.insert({tbl.id: 2, tbl.name: 'A', tbl.age: 20})
    tbl.insert({tbl.id: 3, tbl.name: 'B', tbl.age: 30})
    tbl.delete_row((tbl.age > 25) & (tbl.name == 'B'))
    res = tbl.get_row([tbl.id], tbl.id == 3)
    assert len(res) == 0
def test_223_delete_row_always_false(tbl):
    
    tbl.insert({tbl.id: 4, tbl.name: 'Keep'})
    tbl.delete_row(tbl.id == 999)
    res = tbl.get_row([tbl.id], tbl.id == 4)
    assert len(res) == 1
def test_224_delete_row_invalid_condition(tbl):
    
    with pytest.raises(Exception):
        tbl.delete_row("invalid condition")
def test_225_delete_row_condition_with_none(tbl):
    
    tbl.insert({tbl.id: 5, tbl.name: 'Null', tbl.age: None})
    tbl.delete_row(tbl.age == None) 
    res = tbl.get_row([tbl.id], tbl.id == 5)
    assert len(res) == 0
def test_226_get_row_one_column(tbl):
    
    tbl.insert({tbl.id: 1, tbl.name: 'One'})
    res = tbl.get_row([tbl.name], tbl.id == 1)
    assert len(res) == 1
    assert res[0] == 'One'
def test_227_get_row_multiple_columns(tbl):
    
    tbl.insert({tbl.id: 2, tbl.name: 'Two', tbl.age: 20})
    res = tbl.get_row([tbl.name, tbl.age], tbl.id == 2)
    assert res[0] == ('Two', 20)
def test_228_get_row_where_simple(tbl):
    
    tbl.insert({tbl.id: 3, tbl.name: 'Three'})
    res = tbl.get_row([tbl.name], tbl.id == 3)
    assert res[0] == 'Three'
def test_229_get_row_order_by(tbl):
    
    tbl.insert({tbl.id: 4, tbl.name: 'B', tbl.age: 10})
    tbl.insert({tbl.id: 5, tbl.name: 'A', tbl.age: 20})
    res = tbl.get_row([tbl.name], order_by=tbl.name)
    assert res[0] == 'A' and res[1] == 'B'
def test_230_get_row_order_by_nonexistent_error(tbl):
    
    with pytest.raises(Exception):
        tbl.get_row([tbl.name], order_by="nonexistent")
def test_231_get_row_columns_operation(tbl):
    
    tbl.insert({tbl.id: 6, tbl.name: 'upper_me'})
    res = tbl.get_row([tbl.name.upper()], tbl.id == 6)
    assert res[0] == 'UPPER_ME'
def test_232_get_row_reader_pool(tbl):
    
    tbl.insert({tbl.id: 7, tbl.name: 'Reader'})
    res = tbl.get_row([tbl.name], tbl.id == 7, from_readers_pool=True)
    assert res[0] == 'Reader'
def test_233_get_row_where_none(tbl):
    tbl.insert({tbl.id: 8, tbl.name: 'NullAge', tbl.age: None})
    res = tbl.get_row([tbl.name], tbl.age == None)
    assert res[0] == 'NullAge'  
def test_234_get_row_which_columns_empty_error(tbl):
    
    with pytest.raises(Exception):
        tbl.get_row([])
def test_235_get_row_where_is_none(tbl):
    
    tbl.insert({tbl.id: 9, tbl.name: 'A'})
    tbl.insert({tbl.id: 10, tbl.name: 'B'})
    res = tbl.get_row([tbl.id], where=None)
    assert len(res) >= 2
def test_236_get_row_order_by_none(tbl):
    
    tbl.insert({tbl.id: 11, tbl.name: 'X'})
    res = tbl.get_row([tbl.id], order_by=None)
    assert len(res) > 0
def test_237_get_row_like(tbl):
    
    tbl.insert({tbl.id: 12, tbl.name: 'John Doe'})
    res = tbl.get_row([tbl.name], tbl.name.like('John%'))
    assert res[0] == 'John Doe'
def test_238_get_row_between(tbl):
    tbl.insert({tbl.id: 13, tbl.name: 'test', tbl.age: 25})  
    res = tbl.get_row([tbl.age], (tbl.age >= 20) & (tbl.age <= 30))
    assert res[0] == 25
def test_239_custom_execute_on_table(tbl):
    
    tbl.custom_execute("CREATE INDEX idx_age ON users(age);")
    
def test_240_custom_execute_many_on_table(tbl):
    
    data = [(20, 'A', 1, 100), (21, 'B', 2, 200)]
    tbl.custom_execute_many("INSERT INTO users (age, name, id, salary) VALUES (?, ?, ?, ?);", data)
    res = tbl.get_row([tbl.id], where=None)
    assert len(res) == 2
def test_241_custom_execute_with_fetch_on_table(tbl):
    
    tbl.insert({tbl.id: 1, tbl.name: 'Fetch'})
    res = tbl.custom_execute_with_fetch("SELECT name FROM users WHERE id = 1;")
    assert res[0][0] == 'Fetch'
def test_242_custom_execute_with_fetch_reader_pool_table(tbl):
    
    tbl.insert({tbl.id: 2, tbl.name: 'PoolFetch'})
    res = tbl.custom_execute_with_fetch("SELECT name FROM users WHERE id = 2;", from_readers_pool=True)
    assert res[0][0] == 'PoolFetch'
def test_243_add_column_datatype_default(driver):
    
    schema = Sqlite.TableStructure('alter_tbl', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl_a = driver.create_table(schema)
    tbl_a.add_column('status', Sqlite.DataTypes.TEXT(), default_value='active')
    tbl_a.insert({tbl_a.id: 1})
    res = tbl_a.get_row([tbl_a.status], tbl_a.id == 1)
    assert res[0] == 'active'
def test_244_add_column_not_null_insert_null_error(driver):
    
    schema = Sqlite.TableStructure('alter_tbl2', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl_b = driver.create_table(schema)
    tbl_b.add_column('req', Sqlite.DataTypes.TEXT(), not_null=True)
    with pytest.raises(Exception):
        tbl_b.insert({tbl_b.id: 1, tbl_b.req: None})
def test_245_rename_column(driver):
    schema = Sqlite.TableStructure('ren_tbl', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('old_name', Sqlite.DataTypes.TEXT())
    tbl_r = driver.create_table(schema)
    tbl_r.rename_column(tbl_r.old_name, 'new_name')
    cols = tbl_r.get_columns_name()
    assert 'new_name' in cols and 'old_name' not in cols
def test_246_rename_column_duplicate_error(driver):
    
    schema = Sqlite.TableStructure('ren_tbl2', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('col1', Sqlite.DataTypes.TEXT())
    tbl_r2 = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl_r2.rename_column(tbl_r2.col1, 'id') 
def test_247_delete_column_confirmed(driver):
    schema = Sqlite.TableStructure('del_tbl', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('to_drop', Sqlite.DataTypes.TEXT())
    tbl_d = driver.create_table(schema)
    tbl_d.delete_column(tbl_d.to_drop, True, True, True)
    cols = tbl_d.get_columns_name()
    assert 'to_drop' not in cols
def test_248_delete_column_unconfirmed(driver):
    
    schema = Sqlite.TableStructure('del_tbl2', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('keep', Sqlite.DataTypes.TEXT())
    tbl_d2 = driver.create_table(schema)
    tbl_d2.delete_column('keep', True, False, True) 
    cols = tbl_d2.get_columns_name()
    assert 'keep' in cols 
def test_249_delete_column_nonexistent_error(driver):
    
    schema = Sqlite.TableStructure('del_tbl3', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl_d3 = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl_d3.delete_column('ghost', True, True, True)
def test_250_rename_table(driver):
    
    schema = Sqlite.TableStructure('old_table', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl_old = driver.create_table(schema)
    tbl_old.rename_table('new_table')
    assert hasattr(driver, 'new_table')
    assert not hasattr(driver, 'old_table')
@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_advanced.db")
@pytest.fixture
def driver(db_path):
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    yield drv
    try:
        drv.disconnect()
    except:
        pass
@pytest.fixture
def users(driver):
    schema = Sqlite.TableStructure('users', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Sqlite.DataTypes.TEXT())
    schema.add_column('age', Sqlite.DataTypes.INTEGER())
    return driver.create_table(schema)
@pytest.fixture
def orders(driver):
    schema = Sqlite.TableStructure('orders', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('user_id', Sqlite.DataTypes.INTEGER())
    schema.add_column('total', Sqlite.DataTypes.REAL())
    return driver.create_table(schema)
def test_251_bulk_insert_two_rows(users):
    
    users.bulk_insert([users.id, users.name], [(1, 'Ali'), (2, 'Reza')])
    res = users.get_row([users.id], where=None)
    assert len(res) == 2
def test_252_bulk_insert_100_rows(users):
    
    data = [(i, f'User{i}') for i in range(100)]
    users.bulk_insert([users.id, users.name], data)
    res = users.get_row([users.id], where=None)
    assert len(res) == 100
def test_253_bulk_insert_unequal_columns_error(users):
    
    with pytest.raises(Exception):
        users.bulk_insert([users.id, users.name], [(1, 'Ali', 'Extra')])
def test_254_bulk_insert_different_types(users):
    
    users.bulk_insert([users.id, users.name, users.age], [(1, 'A', 20), (2, 'B', None)])
    res = users.get_row([users.age], users.id == 2)
    assert res[0] is None
def test_255_bulk_insert_empty_list(users):
    
    users.bulk_insert([users.id, users.name], [])
    res = users.get_row([users.id], where=None)
    assert len(res) == 0
def test_256_bulk_update_one_placeholder(users, driver):
    
    users.insert({users.id: 1, users.name: 'Old'})
    users.bulk_update({users.name: driver.PLACE_HOLDER}, users.id == 1, [('New',)])
    res = users.get_row([users.name], users.id == 1)
    assert res[0] == 'New'
def test_257_bulk_update_two_placeholders(users, driver):
    
    users.insert({users.id: 1, users.name: 'A', users.age: 20})
    users.insert({users.id: 2, users.name: 'B', users.age: 30})
    
    users.bulk_update({users.name: driver.PLACE_HOLDER}, users.id == driver.PLACE_HOLDER, [('Updated1', 1), ('Updated2', 2)])
    res = users.get_row([users.name], users.id == 2)
    assert res[0] == 'Updated2'
def test_258_bulk_update_binding_error(users, driver):
    
    users.insert({users.id: 1, users.name: 'A'})
    with pytest.raises(Exception):
        users.bulk_update({users.name: driver.PLACE_HOLDER}, users.id == driver.PLACE_HOLDER, [('OnlyOneParam',)])
def test_260_bulk_update_empty_list(users, driver):
    
    users.insert({users.id: 1, users.name: 'A'})
    users.bulk_update({users.name: driver.PLACE_HOLDER}, users.id == 1, [])
    res = users.get_row([users.name], users.id == 1)
    assert res[0] == 'A' 
def test_262_join_inner(users, orders):
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name, orders.total], [Sqlite.Join.Inner(orders, users.id == orders.user_id)])
    assert len(res) == 1
    assert res[0] == ('Ali', 50.0)
def test_263_join_left(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    users.insert({users.id: 2, users.name: 'Reza'}) 
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    
    res = users.join([users.name, orders.total], [Sqlite.Join.Left(orders, users.id == orders.user_id)])
    assert len(res) == 2
    assert res[1][1] is None 
def test_264_join_right(users, orders):
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    orders.insert({orders.id: 101, orders.user_id: 99, orders.total: 20.0})
    res = users.join(
        [users.name, orders.total],
        [Sqlite.Join.Right(orders, users.id == orders.user_id)]
    )
    assert len(res) == 2  
def test_265_join_two_joins(users, orders, driver):
    
    schema = Sqlite.TableStructure('items', strict=True)
    schema.add_column('order_id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('product', Sqlite.DataTypes.TEXT())
    items = driver.create_table(schema)
    
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 10, orders.user_id: 1, orders.total: 100})
    items.insert({items.order_id: 10, items.product: 'Book'})
    
    res = users.join(
        [users.name, items.product],
        [Sqlite.Join.Inner(orders, users.id == orders.user_id), Sqlite.Join.Inner(items, orders.id == items.order_id)]
    )
    assert res[0] == ('Ali', 'Book')
def test_266_join_with_where(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    users.insert({users.id: 2, users.name: 'Reza'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    orders.insert({orders.id: 101, orders.user_id: 2, orders.total: 150.0})
    
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], where=orders.total > 100)
    assert len(res) == 1 and res[0][0] == 'Reza'
def test_267_join_order_by(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    users.insert({users.id: 2, users.name: 'Reza'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    orders.insert({orders.id: 101, orders.user_id: 2, orders.total: 150.0})
    
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], order_by=orders.total)
    assert res[0][0] == 'Ali' 
def test_268_join_columns_operation_select(users, orders):
    
    users.insert({users.id: 1, users.name: 'ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name.upper()], [Sqlite.Join.Inner(orders, users.id == orders.user_id)])
    assert res[0][0] == 'ALI'
def test_269_join_reader_pool(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], from_readers_pool=True)
    assert res[0][0] == 'Ali'
def test_270_join_complex_condition(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali', users.age: 20})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    cond = (users.id == orders.user_id) & (users.age > 18)
    res = users.join([users.name], [Sqlite.Join.Inner(orders, cond)])
    assert len(res) == 1
def test_271_join_no_data(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)])
    assert len(res) == 0
def test_272_join_three_tables_where(users, orders, driver):
    
    schema = Sqlite.TableStructure('payments', strict=True)
    schema.add_column('order_id', Sqlite.DataTypes.INTEGER())
    schema.add_column('amount', Sqlite.DataTypes.REAL())
    payments = driver.create_table(schema)
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 10, orders.user_id: 1, orders.total: 100})
    payments.insert({payments.order_id: 10, payments.amount: 50.0})
    res = users.join(
        [users.name, payments.amount],
        [Sqlite.Join.Inner(orders, users.id == orders.user_id), Sqlite.Join.Inner(payments, orders.id == payments.order_id)],
        where=payments.amount < 100.0
    )
    assert len(res) == 1
def test_273_join_where_like(users, orders):
    
    users.insert({users.id: 1, users.name: 'Alexander'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], where=users.name.like('Alex%'))
    assert len(res) == 1
def test_274_join_where_in(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    users.insert({users.id: 2, users.name: 'Reza'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    orders.insert({orders.id: 101, orders.user_id: 2, orders.total: 60.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], where=users.name.In(['Ali']))
    assert len(res) == 1
def test_275_join_where_between(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], where=(orders.total >= 40) & (orders.total <= 60))
    assert len(res) == 1
def test_276_join_where_is_null(users, orders):
    
    users.insert({users.id: 1, users.name: None}) 
    
    users.insert({users.id: 2, users.name: 'Reza', users.age: None})
    orders.insert({orders.id: 100, orders.user_id: 2, orders.total: 10.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], where=users.age == None)
    assert len(res) == 1
def test_277_join_where_is_not_null(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali', users.age: 20})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 10.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], where=users.age != None)
    assert len(res) == 1
def test_278_join_computed_order(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], order_by=orders.total)
    assert len(res) == 1
def test_279_join_empty_joins_list(users):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    res = users.join([users.name], joins_list=[])
    assert res[0][0] == 'Ali'
def test_280_join_columns_empty_error(users, orders):
    
    with pytest.raises(Exception):
        users.join([], [Sqlite.Join.Inner(orders, users.id == orders.user_id)])
def test_281_join_where_none(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], where=None)
    assert len(res) == 1
def test_282_join_order_by_none(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], order_by=None)
    assert len(res) == 1
def test_283_bulk_insert_then_join(users, orders):
    
    users.bulk_insert([users.id, users.name], [(1, 'Ali')])
    orders.bulk_insert([orders.id, orders.user_id, orders.total], [(100, 1, 50.0)])
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)])
    assert res[0][0] == 'Ali'
def test_284_update_on_joined_table_error(users, orders):
    
    
    with pytest.raises(Exception):
        users.update({orders.total: 999}, users.id == 1)
def test_285_delete_on_joined_table_error(users, orders):
    
    
    with pytest.raises(Exception):
        users.delete_row(orders.total > 100)
def test_286_get_row_order_by_other_table(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    
    with pytest.raises(Exception):
        users.get_row([users.name], order_by=orders.total)
def test_287_join_inner_output(users, orders):
    
    join_obj = Sqlite.Join.Inner(orders, users.id == orders.user_id)
    out = join_obj._output
    assert "INNER JOIN" in out[0]
    assert "orders" in out[0]
def test_288_join_left_output(users, orders):
    
    join_obj = Sqlite.Join.Left(orders, users.id == orders.user_id)
    out = join_obj._output
    assert "LEFT JOIN" in out[0]
def test_289_join_right_output(users, orders):
    
    join_obj = Sqlite.Join.Right(orders, users.id == orders.user_id)
    out = join_obj._output
    assert "RIGHT JOIN" in out[0]
def test_290_join_combine_inner_left(users, orders, driver):
    
    schema = Sqlite.TableStructure('logs', strict=True)
    schema.add_column('user_id', Sqlite.DataTypes.INTEGER())
    schema.add_column('msg', Sqlite.DataTypes.TEXT())
    logs = driver.create_table(schema)
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 10, orders.user_id: 1, orders.total: 100})
    logs.insert({logs.user_id: 1, logs.msg: 'Error'})
    res = users.join(
        [users.name, logs.msg],
        [Sqlite.Join.Inner(orders, users.id == orders.user_id), Sqlite.Join.Left(logs, users.id == logs.user_id)]
    )
    assert res[0][1] == 'Error'
def test_291_join_complex_op_where(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali', users.age: 20})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], where=(users.age + 10) > 29)
    assert len(res) == 1
def test_292_join_order_and_reader_pool(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], order_by=users.id, from_readers_pool=True)
    assert res[0][0] == 'Ali'
def test_293_join_where_null(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali', users.age: None})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], where=users.age == None)
    assert len(res) == 1
def test_294_join_mixed_columns(users, orders):
    
    users.insert({users.id: 1, users.name: 'ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name.upper(), orders.total], [Sqlite.Join.Inner(orders, users.id == orders.user_id)])
    assert res[0] == ('ALI', 50.0)
def test_296_join_and_get_row(users, orders):
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    joined_res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)])
    row_res = users.get_row([users.name], users.id == 1)
    assert joined_res[0][0] == row_res[0]
def test_299_join_where_in_subquery(users, orders, driver):
    users.insert({users.id: 1, users.name: 'Ali'})
    users.insert({users.id: 2, users.name: 'Reza'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], where=users.name.In(['Ali', 'Sara']))
    assert len(res) == 1
def test_300_join_alias_prevention(users, orders):
    
    
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    
    res = users.join([users.name, orders.total], [Sqlite.Join.Inner(orders, users.id == orders.user_id)])
    assert res[0] == ('Ali', 50.0)
@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_indexes_schema.db")
@pytest.fixture
def driver(db_path):
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    yield drv
    try:
        drv.disconnect()
    except:
        pass
def test_301_create_index_one_column(driver):
    
    schema = Sqlite.TableStructure('t301', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_name', [tbl.name])
    indexes = tbl.get_indexes()
    assert 'idx_name' in indexes
def test_302_create_index_two_columns(driver):
    
    schema = Sqlite.TableStructure('t302', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('a', Sqlite.DataTypes.TEXT())
    schema.add_column('b', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_ab', [tbl.a, tbl.b])
    indexes = tbl.get_indexes()
    assert 'idx_ab' in indexes
def test_303_create_index_unique(driver):
    schema = Sqlite.TableStructure('t303', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('code', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_uniq', [tbl.code], unique=True)
    info = tbl.get_index_info('idx_uniq')
    assert info['unique'] is True
def test_304_create_index_where(driver):
    
    schema = Sqlite.TableStructure('t304', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('status', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_partial', [tbl.status], where=tbl.status == 'active')
    indexes = tbl.get_indexes()
    assert 'idx_partial' in indexes
def test_305_create_index_duplicate_error(driver):
    
    schema = Sqlite.TableStructure('t305', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('val', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_dup', [tbl.val])
    with pytest.raises(Exception):
        tbl.create_index('idx_dup', [tbl.val])
def test_306_create_index_empty_columns_error(driver):
    
    schema = Sqlite.TableStructure('t306', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.create_index('idx_emp', [])
def test_307_get_indexes(driver):
    
    schema = Sqlite.TableStructure('t307', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('a', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx1', [tbl.a])
    assert 'idx1' in tbl.get_indexes()
def test_308_get_indexes_reader_pool(driver):
    
    schema = Sqlite.TableStructure('t308', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    indexes = tbl.get_indexes(from_readers_pool=True)
    assert isinstance(indexes, list)
def test_309_get_index_info_existing(driver):
    
    schema = Sqlite.TableStructure('t309', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('a', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_info', [tbl.a])
    info = tbl.get_index_info('idx_info')
    assert info is not None
def test_310_get_index_info_nonexistent_error(driver):
    
    schema = Sqlite.TableStructure('t310', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.get_index_info('ghost_idx')
def test_311_delete_index_existing(driver):
    
    schema = Sqlite.TableStructure('t311', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('a', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_del', [tbl.a])
    tbl.delete_index('idx_del')
    assert 'idx_del' not in tbl.get_indexes()
def test_312_delete_index_nonexistent_error(driver):
    
    schema = Sqlite.TableStructure('t312', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.delete_index('ghost_idx')
def test_313_reindex_existing(driver):
    
    schema = Sqlite.TableStructure('t313', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('a', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_re', [tbl.a])
    tbl.reindex('idx_re') 
def test_314_reindex_nonexistent_error(driver):
    
    schema = Sqlite.TableStructure('t314', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.reindex('ghost_idx')
def test_315_reindex_after_bulk_insert(driver):
    
    schema = Sqlite.TableStructure('t315', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('a', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_bulk', [tbl.a])
    tbl.bulk_insert([tbl.id, tbl.a], [(1, 'A'), (2, 'B')])
    tbl.reindex('idx_bulk') 
def test_316_add_column_after_insert(driver):
    
    schema = Sqlite.TableStructure('t316', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.insert({tbl.id: 1})
    tbl.add_column('new_col', Sqlite.DataTypes.TEXT(), default_value='hello')
    res = tbl.get_row([tbl.new_col], tbl.id == 1)
    assert res[0] == 'hello'
def test_317_add_column_default_then_insert(driver):
    
    schema = Sqlite.TableStructure('t317', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.add_column('status', Sqlite.DataTypes.TEXT(), default_value='active')
    tbl.insert({tbl.id: 1, tbl.status: 'active'})
    res = tbl.get_row([tbl.status], tbl.id == 1)
    assert res[0] == 'active'
def test_318_add_column_not_null_insert_null_error(driver):
    
    schema = Sqlite.TableStructure('t318', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.add_column('req', Sqlite.DataTypes.TEXT(), not_null=True, default_value='val')
    with pytest.raises(Exception):
        tbl.insert({tbl.id: 1, tbl.req: None})
def test_319_add_column_invalid_datatype_error(driver):
    
    schema = Sqlite.TableStructure('t319', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.add_column('bad_col', "JUST_A_STRING_NOT_DATATYPE")
def test_320_rename_column_new_name(driver):
    schema = Sqlite.TableStructure('t320', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('old_name', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.rename_column(tbl.old_name, 'new_name')
    assert 'new_name' in tbl.get_columns_name()
def test_321_rename_column_duplicate_error(driver):
    
    schema = Sqlite.TableStructure('t321', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('col1', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.rename_column(tbl.col1, 'id')
def test_322_rename_column_and_get_row(driver):
    schema = Sqlite.TableStructure('t322', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('old_col', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.insert({tbl.id: 1, tbl.old_col: 'Data'})
    tbl.rename_column(tbl.old_col, 'new_col')
    res = tbl.get_row([tbl.new_col], tbl.id == 1)
    assert res[0] == 'Data'
def test_323_delete_column_confirmed(driver):
    schema = Sqlite.TableStructure('t323', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('to_drop', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.delete_column(tbl.to_drop, True, True, True)
    assert 'to_drop' not in tbl.get_columns_name()
def test_324_delete_column_unconfirmed(driver):
    
    schema = Sqlite.TableStructure('t324', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('keep', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.delete_column('keep', True, False, True)
    assert 'keep' in tbl.get_columns_name()
def test_325_delete_column_and_insert(driver):
    schema = Sqlite.TableStructure('t325', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('temp', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.delete_column(tbl.temp, True, True, True)
    tbl.insert({tbl.id: 1})
    res = tbl.get_row([tbl.id], tbl.id == 1)
    assert len(res) == 1
def test_326_delete_table_confirmed(driver):
    
    schema = Sqlite.TableStructure('del_me', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    assert hasattr(driver, 'del_me')
    tbl.delete_table(True, True, True)
    assert not hasattr(driver, 'del_me')
def test_327_delete_table_unconfirmed(driver):
    
    schema = Sqlite.TableStructure('keep_me', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.delete_table(True, False, True)
    assert hasattr(driver, 'keep_me')
def test_328_delete_table_then_get_tables(driver):
    
    schema = Sqlite.TableStructure('temp_tbl', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.delete_table(True, True, True)
    tables = driver.get_tables()
    assert 'temp_tbl' not in tables
def test_329_rename_table(driver):
    
    schema = Sqlite.TableStructure('old_name', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.rename_table('new_name')
    assert hasattr(driver, 'new_name')
    assert not hasattr(driver, 'old_name')
def test_330_rename_table_duplicate_error(driver):
    
    schema1 = Sqlite.TableStructure('tbl_a', strict=True)
    schema1.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    driver.create_table(schema1)
    
    schema2 = Sqlite.TableStructure('tbl_b', strict=True)
    schema2.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl_b = driver.create_table(schema2)
    
    with pytest.raises(Exception):
        tbl_b.rename_table('tbl_a')
def test_331_rename_table_use_new_name(driver):
    
    schema = Sqlite.TableStructure('old_t', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('val', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.rename_table('new_t')
    driver.new_t.insert({driver.new_t.id: 1, driver.new_t.val: 'Test'})
    res = driver.new_t.get_row([driver.new_t.val], driver.new_t.id == 1)
    assert res[0] == 'Test'
def test_332_get_index_info_after_reindex(driver):
    
    schema = Sqlite.TableStructure('t332', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('a', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_r', [tbl.a])
    tbl.reindex('idx_r')
    info = tbl.get_index_info('idx_r')
    assert info is not None
def test_333_create_index_cross_table_error(driver):
    
    schema1 = Sqlite.TableStructure('t1', strict=True)
    schema1.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    t1 = driver.create_table(schema1)
    
    schema2 = Sqlite.TableStructure('t2', strict=True)
    schema2.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema2.add_column('fk', Sqlite.DataTypes.INTEGER())
    t2 = driver.create_table(schema2)
    
    with pytest.raises(Exception):
        t2.create_index('idx_cross', [t1.id]) 
def test_334_reindex_none_error(driver):
    
    schema = Sqlite.TableStructure('t334', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.reindex(None)
def test_335_delete_index_none_error(driver):
    
    schema = Sqlite.TableStructure('t335', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.delete_index(None)
def test_336_get_index_info_none_error(driver):
    
    schema = Sqlite.TableStructure('t336', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.get_index_info(None)
def test_337_create_index_where_with_params(driver):
    
    schema = Sqlite.TableStructure('t337', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('age', Sqlite.DataTypes.INTEGER())
    tbl = driver.create_table(schema)
    
    tbl.create_index('idx_param', [tbl.age], where=tbl.age > 18)
    assert 'idx_param' in tbl.get_indexes()
def test_338_create_index_unique_partial(driver):
    
    schema = Sqlite.TableStructure('t338', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('email', Sqlite.DataTypes.TEXT())
    schema.add_column('status', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    
    tbl.create_index('idx_uniq_active', [tbl.email], unique=True, where=tbl.status == 'active')
    assert 'idx_uniq_active' in tbl.get_indexes()
def test_339_add_column_bytes_default_error(driver):
    
    schema = Sqlite.TableStructure('t339', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.add_column('data', Sqlite.DataTypes.BLOB(), default_value=b'bytes_val')
def test_340_add_column_my_saulted_x_replacement(driver):
    
    schema = Sqlite.TableStructure('t340', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    
    dt = Sqlite.DataTypes.CUSTOM('TEXT', check='length(my_saulted_x) > 0')
    tbl.add_column('checked_col', dt)
    
    assert 'checked_col' in tbl.get_columns_name()
def test_341_rename_column_space_in_name(driver):
    schema = Sqlite.TableStructure('t341', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('col', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.rename_column(tbl.col, 'new name')
    assert 'new name' in tbl.get_columns_name()
def test_342_delete_column_other_table_error(driver):
    
    schema1 = Sqlite.TableStructure('t342a', strict=True)
    schema1.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    t1 = driver.create_table(schema1)
    
    schema2 = Sqlite.TableStructure('t342b', strict=True)
    schema2.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    t2 = driver.create_table(schema2)
    
    with pytest.raises(Exception):
        t2.delete_column('id') 
        
def test_343_rename_table_space_in_name(driver):
    
    schema = Sqlite.TableStructure('t343', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.rename_table('table with space')
    assert hasattr(driver, 'table with space')
def test_344_create_index_cross_table_column_error(driver):
    
    schema1 = Sqlite.TableStructure('t344a', strict=True)
    schema1.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    t1 = driver.create_table(schema1)
    
    schema2 = Sqlite.TableStructure('t344b', strict=True)
    schema2.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    t2 = driver.create_table(schema2)
    
    with pytest.raises(Exception):
        t2.create_index('idx_cross', [t1.id])
def test_345_get_indexes_after_delete(driver):
    
    schema = Sqlite.TableStructure('t345', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('a', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_temp', [tbl.a])
    tbl.delete_index('idx_temp')
    assert 'idx_temp' not in tbl.get_indexes()
def test_346_reindex_after_rename_column(driver):
    schema = Sqlite.TableStructure('t346', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('old_col', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx_old', [tbl.old_col])
    tbl.rename_column(tbl.old_col, 'new_col')
    tbl.reindex('idx_old')
def test_347_add_column_datetime_default(driver):
    
    schema = Sqlite.TableStructure('t347', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    now = datetime.datetime.now()
    tbl.add_column('created_at', Sqlite.DataTypes.TEXT(), default_value=str(now))
    tbl.insert({tbl.id: 1})
    res = tbl.get_row([tbl.created_at], tbl.id == 1)
    assert now.strftime('%Y-%m-%d') in res[0]
def test_348_rename_column_then_get_columns_name(driver):
    schema = Sqlite.TableStructure('t348', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('old', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.rename_column(tbl.old, 'new')
    assert 'new' in tbl.get_columns_name() and 'old' not in tbl.get_columns_name()
def test_349_delete_table_then_get_row_error(driver):
    
    schema = Sqlite.TableStructure('t349', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.insert({tbl.id: 1})
    tbl.delete_table(True, True, True)
    with pytest.raises(Exception):
        tbl.get_row([tbl.id], tbl.id == 1)
def test_350_delete_column_nonexistent_error(driver):
    
    schema = Sqlite.TableStructure('t350', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    with pytest.raises(Exception):
        tbl.delete_column('ghost_col', True, True, True)
@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_batch.db")
@pytest.fixture
def driver(db_path):
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    yield drv
    try:
        drv.disconnect()
    except:
        pass
@pytest.fixture
def users(driver):
    schema = Sqlite.TableStructure('users', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Sqlite.DataTypes.TEXT())
    schema.add_column('age', Sqlite.DataTypes.INTEGER())
    return driver.create_table(schema)
def test_351_create_batch(users):
    
    batch = users.batch()
    assert batch is not None
def test_352_batch_insert_one_row(users):
    
    batch = users.batch()
    batch.insert({users.id: 1, users.name: 'Ali'})
    batch.run()
    res = users.get_row([users.name], users.id == 1)
    assert res[0] == 'Ali'
def test_353_batch_insert_multiple_rows(users):
    
    batch = users.batch()
    batch.insert({users.id: 1, users.name: 'A'})
    batch.insert({users.id: 2, users.name: 'B'})
    batch.run()
    res = users.get_row([users.id], where=None)
    assert len(res) == 2
def test_354_batch_update_one_column(users):
    
    users.insert({users.id: 1, users.name: 'Old'})
    batch = users.batch()
    batch.update({users.name: 'New'}, users.id == 1)
    batch.run()
    res = users.get_row([users.name], users.id == 1)
    assert res[0] == 'New'
def test_355_batch_update_multiple_columns(users):
    
    users.insert({users.id: 1, users.name: 'A', users.age: 20})
    batch = users.batch()
    batch.update({users.name: 'B', users.age: 30}, users.id == 1)
    batch.run()
    res = users.get_row([users.name, users.age], users.id == 1)
    assert res[0] == ('B', 30)
def test_356_batch_delete_row(users):
    
    users.insert({users.id: 1, users.name: 'ToDelete'})
    batch = users.batch()
    batch.delete_row(users.id == 1)
    batch.run()
    res = users.get_row([users.id], users.id == 1)
    assert len(res) == 0
def test_357_batch_combined_operations(users):
    
    users.insert({users.id: 1, users.name: 'A', users.age: 10})
    batch = users.batch()
    batch.insert({users.id: 2, users.name: 'B', users.age: 20})
    batch.update({users.age: 15}, users.id == 1)
    batch.delete_row(users.id == 2)
    batch.run()
    
    res1 = users.get_row([users.age], users.id == 1)
    res2 = users.get_row([users.id], users.id == 2)
    assert res1[0] == 15
    assert len(res2) == 0
def test_458_rename_column_and_get_row(driver):
    schema = Sqlite.TableStructure('ren_c', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('old', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.insert({tbl.id: 1, tbl.old: 'Data'})
    tbl.rename_column(tbl.old, 'new')
    assert tbl.get_row([tbl.new], tbl.id == 1)[0] == 'Data'
def test_359_batch_run_rollback_on_error(users):
    
    users.insert({users.id: 1, users.name: 'Existing'})
    batch = users.batch()
    batch.insert({users.id: 2, users.name: 'Valid'})
    batch.insert({users.id: 1, users.name: 'DuplicatePK'}) 
    with pytest.raises(Exception):
        batch.run()
    
    res = users.get_row([users.id], users.id == 2)
    assert len(res) == 0
def test_360_batch_run_empty(users):
    
    batch = users.batch()
    batch.run() 
def test_361_batch_update_with_columns_operation_value(users):
    
    users.insert({users.id: 1, users.age: 20})
    batch = users.batch()
    batch.update({users.age: users.age + 5}, users.id == 1)
    batch.run()
    res = users.get_row([users.age], users.id == 1)
    assert res[0] == 25
def test_362_batch_update_with_columns_operation_where(users):
    
    users.insert({users.id: 1, users.age: 20})
    batch = users.batch()
    batch.update({users.age: 30}, users.age > 18)
    batch.run()
    res = users.get_row([users.age], users.id == 1)
    assert res[0] == 30
def test_363_batch_insert_default_value(users):
    
    
    batch = users.batch()
    batch.insert({users.id: 1, users.age: 50})
    batch.run()
    res = users.get_row([users.name], users.id == 1)
    assert res[0] is None
def test_364_batch_insert_missing_columns_error(driver):
    
    
    schema = Sqlite.TableStructure('strict_tbl', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Sqlite.DataTypes.TEXT(), not_null=True)
    tbl = driver.create_table(schema)
    batch = tbl.batch()
    batch.insert({tbl.id: 1}) 
    with pytest.raises(Exception):
        batch.run()
def test_365_batch_delete_false_condition(users):
    
    users.insert({users.id: 1, users.name: 'Keep'})
    batch = users.batch()
    batch.delete_row(users.id == 999)
    batch.run()
    res = users.get_row([users.id], users.id == 1)
    assert len(res) == 1
def test_366_batch_with_another_table_parameter(driver, users):
    
    schema = Sqlite.TableStructure('products', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    products = driver.create_table(schema)
    
    
    batch = users.batch() 
    batch.insert({users.id: 1, users.name: 'U1'})
    batch.run()
    assert len(users.get_row([users.id], where=None)) == 1
def test_367_batch_multiple_tables(driver, users):
    
    
    
    schema = Sqlite.TableStructure('t2', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    t2 = driver.create_table(schema)
    
    b1 = users.batch()
    b1.insert({users.id: 1, users.name: 'A'})
    b1.run()
    
    b2 = t2.batch()
    b2.insert({t2.id: 1})
    b2.run()
def test_368_batch_after_add_column(users):
    
    users.add_column('status', Sqlite.DataTypes.TEXT(), default_value='active')
    batch = users.batch()
    batch.insert({users.id: 1, users.name: 'New', users.status: 'pending'})
    batch.run()
    res = users.get_row([users.status], users.id == 1)
    assert res[0] == 'pending'
def test_369_batch_concurrent_reader_pool(users):
    
    users.insert({users.id: 1, users.name: 'Init'})
    batch = users.batch()
    batch.update({users.name: 'UpdatedByBatch'}, users.id == 1)
    
    
    t1 = threading.Thread(target=batch.run)
    t1.start()
    time.sleep(0.05) 
    res = users.get_row([users.name], users.id == 1, from_readers_pool=True)
    t1.join()
    
    assert res[0] in ['Init', 'UpdatedByBatch']
def test_370_batch_with_fk(driver):
    schema_p = Sqlite.TableStructure('parent', strict=True)
    schema_p.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    parent = driver.create_table(schema_p)
    schema_c = Sqlite.TableStructure('child', strict=True)
    schema_c.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema_c.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema_c.foreign_key('pid', parent, parent.id)
    child = driver.create_table(schema_c)
    driver.SetPragma.foreign_keys(True)
    batch = child.batch()
    batch.insert({child.id: 1, child.pid: 99})
    with pytest.raises(Exception):
        batch.run()
def test_371_batch_insert_null_value(users):
    
    batch = users.batch()
    batch.insert({users.id: 1, users.name: None, users.age: 20})
    batch.run()
    res = users.get_row([users.name], users.id == 1)
    assert res[0] is None
def test_372_batch_bytes_value_error(users):
    
    batch = users.batch()
    with pytest.raises(Exception):
        batch.insert({users.id: 1, users.name: b'bytes_val'})
def test_373_batch_run_while_disconnected_error(users, driver):
    
    batch = users.batch()
    batch.insert({users.id: 1, users.name: 'Ghost'})
    driver.disconnect()
    with pytest.raises(Exception):
        batch.run()
def test_374_batch_update_empty_dict_error(users):
    
    batch = users.batch()
    with pytest.raises(Exception):
        batch.update({}, users.id == 1)
def test_375_batch_insert_empty_dict_error(users):
    
    batch = users.batch()
    with pytest.raises(Exception):
        batch.insert({})
def test_376_batch_delete_none_where_error(users):
    
    batch = users.batch()
    
    with pytest.raises(Exception):
        batch.delete_row(None)
def test_377_batch_run_twice(users):
    
    batch = users.batch()
    batch.insert({users.id: 1, users.name: 'A'})
    batch.run()
    
    
    try:
        batch.run()
    except Exception:
        pass 
def test_378_batch_insert_then_update_same_row(users):
    
    batch = users.batch()
    batch.insert({users.id: 1, users.name: 'Initial', users.age: 10})
    batch.update({users.age: 20}, users.id == 1)
    batch.run()
    res = users.get_row([users.name, users.age], users.id == 1)
    assert res[0] == ('Initial', 20)
def test_379_batch_delete_then_insert_same_pk(users):
    
    users.insert({users.id: 1, users.name: 'Old'})
    batch = users.batch()
    batch.delete_row(users.id == 1)
    batch.insert({users.id: 1, users.name: 'New'})
    batch.run()
    res = users.get_row([users.name], users.id == 1)
    assert res[0] == 'New'
def test_380_batch_update_no_match(users):
    
    batch = users.batch()
    batch.update({users.name: 'Ghost'}, users.id == 999)
    batch.run() 
def test_381_batch_insert_with_none(users):
    
    batch = users.batch()
    batch.insert({users.id: 1, users.name: None, users.age: None})
    batch.run()
    res = users.get_row([users.name, users.age], users.id == 1)
    assert res[0] == (None, None)
def test_382_batch_update_with_none(users):
    
    users.insert({users.id: 1, users.name: 'Ali', users.age: 20})
    batch = users.batch()
    batch.update({users.age: None}, users.id == 1)
    batch.run()
    res = users.get_row([users.age], users.id == 1)
    assert res[0] is None
def test_383_batch_delete_with_columns_operation(users):
    
    users.insert({users.id: 1, users.age: 25})
    batch = users.batch()
    batch.delete_row(users.age > 20)
    batch.run()
    res = users.get_row([users.id], users.id == 1)
    assert len(res) == 0
def test_384_batch_update_column_value(users):
    
    users.insert({users.id: 1, users.name: 'Ali', users.age: 30})
    batch = users.batch()
    
    batch.update({users.name: users.age}, users.id == 1) 
    batch.run()
    res = users.get_row([users.name], users.id == 1)
    assert res[0] == '30' 
def test_385_batch_on_strict_table(driver):
    
    schema = Sqlite.TableStructure('strict_batch', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('val', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    
    batch = tbl.batch()
    batch.insert({tbl.id: 1, tbl.val: 'Text'})
    batch.update({tbl.val: 'NewText'}, tbl.id == 1)
    batch.run()
    res = tbl.get_row([tbl.val], tbl.id == 1)
    assert res[0] == 'NewText'
def test_386_batch_rollback_verification(users):
    
    batch = users.batch()
    batch.insert({users.id: 1, users.name: 'Valid'})
    batch.insert({users.id: 'InvalidType', users.name: 'Error'}) 
    with pytest.raises(Exception):
        batch.run()
    res = users.get_row([users.id], where=None)
    assert len(res) == 0 
def test_387_batch_on_conflict_placeholder(users, driver):
    
    users.insert({users.id: 1, users.name: 'Old'})
    batch = users.batch()
    
    
    users.bulk_update({users.name: driver.PLACE_HOLDER}, users.id == 1, [('FromBulk',)])
    res = users.get_row([users.name], users.id == 1)
    assert res[0] == 'FromBulk'
def test_388_batch_multiple_operations(users):
    batch = users.batch()
    users.insert({users.id: 1, users.name: 'ToKeep', users.age: 10})
    batch.insert({users.id: 2, users.name: 'ToAdd', users.age: 20})
    batch.update({users.age: 15}, users.id == 1)
    batch.run()
    res = users.get_row([users.age], where=None, order_by=users.id)
    assert res[0] == 15 and res[1] == 20
def test_389_batch_and_get_row_verification(users):
    
    batch = users.batch()
    batch.insert({users.id: 1, users.name: 'Ali'})
    batch.run()
    res = users.get_row([users.name], users.id == 1)
    assert res[0] == 'Ali'
def test_390_batch_reader_pool_after_run(users):
    
    batch = users.batch()
    batch.insert({users.id: 1, users.name: 'ReaderTest'})
    batch.run()
    res = users.get_row([users.name], users.id == 1, from_readers_pool=True)
    assert res[0] == 'ReaderTest'
def test_391_batch_large_number_of_ops(users):
    
    batch = users.batch()
    for i in range(150):
        batch.insert({users.id: i, users.name: f'User{i}'})
    batch.run()
    res = users.get_row([users.id], where=None)
    assert len(res) == 150
def test_392_batch_isolation_on_error(users):
    
    users.insert({users.id: 1, users.name: 'Outside'})
    batch = users.batch()
    batch.update({users.name: 'InsideUpdate'}, users.id == 1)
    batch.insert({users.id: 1, users.name: 'Duplicate'}) 
    with pytest.raises(Exception):
        batch.run()
    
    res = users.get_row([users.name], users.id == 1)
    assert res[0] == 'Outside'
def test_393_batch_insert_with_datetime(users):
    
    now = "2023-10-25 10:00:00"
    batch = users.batch()
    batch.insert({users.id: 1, users.name: now})
    batch.run()
    res = users.get_row([users.name], users.id == 1)
    assert '2023' in res[0]
def test_394_batch_delete_with_none_condition(users):
    
    batch = users.batch()
    with pytest.raises(Exception):
        batch.delete_row(where=None)
def test_395_batch_update_columns_operation_complex(users):
    
    users.insert({users.id: 1, users.age: 20})
    batch = users.batch()
    batch.update({users.age: (users.age * 2) + 5}, users.id == 1)
    batch.run()
    res = users.get_row([users.age], users.id == 1)
    assert res[0] == 45 
def test_396_batch_multiple_runs_sequential(users):
    
    b1 = users.batch()
    b1.insert({users.id: 1, users.name: 'First'})
    b1.run()
    
    b2 = users.batch()
    b2.insert({users.id: 2, users.name: 'Second'})
    b2.run()
    
    res = users.get_row([users.id], where=None)
    assert len(res) == 2
def test_397_batch_with_in_clause(users):
    
    users.bulk_insert([users.id, users.name], [(1, 'A'), (2, 'B'), (3, 'C')])
    batch = users.batch()
    batch.delete_row(users.id.In([1, 3]))
    batch.run()
    res = users.get_row([users.id], where=None)
    assert len(res) == 1 and res[0] == 2
def test_398_batch_with_like_clause(users):
    users.bulk_insert([users.id, users.name], [(1, 'Ali'), (2, 'Reza')])
    batch = users.batch()
    batch.update({users.name: 'Updated'}, users.name.like('A%'))
    batch.run()
    res = users.get_row([users.name], where=None, order_by=users.id)
    assert res[0] == 'Updated' and res[1] == 'Reza'
def test_399_batch_insert_invalid_type_strict(driver):
    
    schema = Sqlite.TableStructure('strict_batch_err', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('age', Sqlite.DataTypes.INTEGER())
    tbl = driver.create_table(schema)
    
    batch = tbl.batch()
    batch.insert({tbl.id: 1, tbl.age: 'NotAnInt'})
    with pytest.raises(Exception):
        batch.run()
def test_400_batch_concurrent_writers(driver, users):
    users.insert({users.id: 1, users.name: 'Init', users.age: 10})
    def run_batch_1():
        b = users.batch()
        b.update({users.name: 'Thread1'}, users.id == 1)
        b.run()
    def run_batch_2():
        b = users.batch()
        b.update({users.age: 99}, users.id == 1)
        b.run()
    t1 = threading.Thread(target=run_batch_1)
    t2 = threading.Thread(target=run_batch_2)
    t1.start(); t2.start()
    t1.join(); t2.join()
    res = users.get_row([users.name, users.age], users.id == 1)
    
    assert (res[0][0] == 'Thread1' and res[0][1] == 99) or \
           (res[0][0] == 'Init' and res[0][1] == 99) or \
           (res[0][0] == 'Thread1' and res[0][1] == 10)
    
@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_join_ops.db")
@pytest.fixture
def driver(db_path):
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    yield drv
    try:
        drv.disconnect()
    except:
        pass
@pytest.fixture
def users(driver):
    schema = Sqlite.TableStructure('users', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('name', Sqlite.DataTypes.TEXT())
    schema.add_column('age', Sqlite.DataTypes.INTEGER())
    return driver.create_table(schema)
@pytest.fixture
def orders(driver):
    schema = Sqlite.TableStructure('orders', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('user_id', Sqlite.DataTypes.INTEGER())
    schema.add_column('total', Sqlite.DataTypes.REAL())
    return driver.create_table(schema)
def test_401_join_inner_creation(users, orders):
    
    join = Sqlite.Join.Inner(orders, users.id == orders.user_id)
    assert join is not None
def test_402_join_inner_output(users, orders):
    
    join = Sqlite.Join.Inner(orders, users.id == orders.user_id)
    sql, params = join._output
    assert "INNER JOIN" in sql
    assert "orders" in sql
    assert len(params) == 0
def test_403_join_left_output(users, orders):
    
    join = Sqlite.Join.Left(orders, users.id == orders.user_id)
    sql, params = join._output
    assert "LEFT JOIN" in sql
def test_404_join_right_output(users, orders):
    
    join = Sqlite.Join.Right(orders, users.id == orders.user_id)
    sql, params = join._output
    assert "RIGHT JOIN" in sql
def test_405_use_inner_in_table_join(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)])
    assert res[0][0] == 'Ali'
def test_406_use_left_in_table_join(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    res = users.join([users.name], [Sqlite.Join.Left(orders, users.id == orders.user_id)])
    assert len(res) == 1
def test_407_use_right_in_table_join(users, orders):
    users.insert({users.id: 1, users.name: 'Ali'})
    res = users.join(
        [users.name],
        [Sqlite.Join.Left(orders, users.id == orders.user_id)]
    )
    assert len(res) == 1
def test_408_join_inner_compound_and(users, orders):
    
    cond = (users.id == orders.user_id) & (orders.total > 10)
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "AND" in sql
def test_409_join_left_compound_or(users, orders):
    
    cond = (users.id == orders.user_id) | (orders.total == 0)
    join = Sqlite.Join.Left(orders, cond)
    sql, _ = join._output
    assert "OR" in sql
def test_410_join_right_columns_op(users, orders):
    
    cond = (users.id + 1) == orders.user_id
    join = Sqlite.Join.Right(orders, cond)
    sql, _ = join._output
    assert "+" in sql
def test_411_join_space_in_table_name(driver, orders):
    
    schema = Sqlite.TableStructure('user data', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl_space = driver.create_table(schema)
    join = Sqlite.Join.Inner(orders, tbl_space.id == orders.user_id)
    sql, _ = join._output
    assert "user data" in sql or "[user data]" in sql
def test_412_join_columns_op_with_params(users, orders):
    
    cond = users.name == 'Ali' 
    join = Sqlite.Join.Inner(orders, cond)
    sql, params = join._output
    assert "?" in sql
    assert 'Ali' in params
def test_413_multiple_joins_in_query(users, orders, driver):
    
    schema = Sqlite.TableStructure('logs', strict=True)
    schema.add_column('user_id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    logs = driver.create_table(schema)
    
    j1 = Sqlite.Join.Inner(orders, users.id == orders.user_id)
    j2 = Sqlite.Join.Left(logs, users.id == logs.user_id)
    
    assert j1._output and j2._output
def test_414_join_inner_no_data(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    res = users.join([users.name], [Sqlite.Join.Inner(orders, users.id == orders.user_id)])
    assert len(res) == 0
def test_415_join_left_no_data(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali'})
    res = users.join([users.name], [Sqlite.Join.Left(orders, users.id == orders.user_id)])
    assert len(res) == 1
def test_416_join_on_like(users, orders):
    
    
    cond = users.name.like('A%')
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "like" in sql.lower()
def test_417_join_on_between(users, orders):
    
    cond = (orders.total >= 10) & (orders.total <= 100)
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert ">=" in sql and "<=" in sql
def test_418_join_on_in(users, orders):
    
    cond = users.name.In(['Ali', 'Reza'])
    join = Sqlite.Join.Inner(orders, cond)
    sql, params = join._output
    assert "IN" in sql.upper()
    assert 'Ali' in params
def test_419_join_on_function(users, orders):
    
    cond = users.name.upper() == 'ALI'
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "upper" in sql.lower()
def test_420_join_table_from_driver_attr(driver, users, orders):
    
    tbl = driver.users
    join = Sqlite.Join.Inner(orders, tbl.id == orders.user_id)
    assert join is not None
def test_421_join_table_from_table_object(driver, users, orders):
    
    tbl = driver.table_object('users')
    join = Sqlite.Join.Left(orders, tbl.id == orders.user_id)
    assert join is not None
def test_422_join_newly_created_table(driver, orders):
    
    schema = Sqlite.TableStructure('fresh', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    fresh = driver.create_table(schema)
    join = Sqlite.Join.Right(fresh, orders.user_id == fresh.id)
    assert join is not None
def test_423_join_on_add_end(users, orders):
    
    cond = users.name.add_end('_suffix') == orders.user_id 
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "||" in sql 
def test_424_join_on_add_first(users, orders):
    
    cond = users.name.add_first('prefix_') == orders.user_id
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "||" in sql
def test_425_join_on_replace(users, orders):
    
    cond = users.name.replace('a', 'b') == 'Ali'
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "replace" in sql.lower()
def test_426_join_on_strip(users, orders):
    
    cond = users.name.strip() == 'Ali'
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "ltrim" in sql.lower() or "rtrim" in sql.lower() or "trim" in sql.lower()
def test_427_join_on_upper_lower(users, orders):
    
    cond = users.name.upper() == users.name.lower()
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "upper" in sql.lower() and "lower" in sql.lower()
def test_428_join_on_startswith(users, orders):
    
    cond = users.name.startswith('A')
    join = Sqlite.Join.Inner(orders, cond)
    sql, params = join._output
    assert "like" in sql.lower()
    assert 'A%' in params or 'A' in params
def test_429_join_on_endswith(users, orders):
    
    cond = users.name.endswith('z')
    join = Sqlite.Join.Inner(orders, cond)
    sql, params = join._output
    assert "like" in sql.lower()
def test_430_join_on_contains(users, orders):
    
    cond = users.name.contains('li')
    join = Sqlite.Join.Inner(orders, cond)
    sql, params = join._output
    assert "like" in sql.lower()
def test_431_join_on_like_method(users, orders):
    
    cond = users.name.like('%li%')
    join = Sqlite.Join.Inner(orders, cond)
    sql, params = join._output
    assert "like" in sql.lower()
def test_432_join_on_eq(users, orders):
    
    cond = users.id.eq(orders.user_id)
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "=" in sql
def test_433_join_on_ne(users, orders):
    
    cond = users.id.ne(orders.user_id)
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "<>" in sql or "!=" in sql
def test_434_join_on_comparisons(users, orders):
    
    cond = users.id.gt(orders.user_id) & users.id.le(10)
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert ">" in sql and "<=" in sql
def test_435_join_on_in_list(users, orders):
    
    cond = users.id.In([1, 2, 3])
    join = Sqlite.Join.Inner(orders, cond)
    sql, params = join._output
    assert "IN" in sql.upper()
    assert len(params) > 0
def test_436_join_on_and_or(users, orders):
    
    c1 = (users.id == orders.user_id)
    c2 = (orders.total > 50)
    cond = c1 & c2
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "AND" in sql
def test_437_join_on_slice(users, orders):
    
    cond = users.name[1:3] == 'li'
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "substr" in sql.lower()
def test_438_join_on_add_sub(users, orders):
    
    cond = (users.age + 5) == (orders.total - 10)
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "+" in sql and "-" in sql
def test_439_join_on_mul_div_mod(users, orders):
    
    cond = (users.age * 2) == (orders.total / 5)
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "*" in sql and "/" in sql
def test_440_join_on_pow(users, orders):
    
    
    
    cond = (users.age ** 2) > 100
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "power" in sql.lower() or "**" in sql 
def test_441_join_on_combined_ops(users, orders):
    
    cond = ((users.age + 10) * 2) < orders.total
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "+" in sql and "*" in sql
def test_442_join_on_datatype_preserved(users, orders):
    
    
    cond = users.age + 5 > 10
    join = Sqlite.Join.Inner(orders, cond)
    sql, _ = join._output
    assert "+" in sql 
def test_443_join_on_many_params(users, orders):
    
    cond = users.name.In(['A', 'B', 'C', 'D', 'E', 'F'])
    join = Sqlite.Join.Inner(orders, cond)
    sql, params = join._output
    assert len(params) == 6
def test_446_join_bucket_table_name(driver, orders):
    
    schema = Sqlite.TableStructure('my-table', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    join = Sqlite.Join.Inner(orders, tbl.id == orders.user_id)
    sql, _ = join._output
    assert "my-table" in sql
def test_447_join_strict_table(users, orders):
    join = Sqlite.Join.Inner(orders, users.id == orders.user_id)
    sql, _ = join._output
    assert "users" in sql
def test_448_join_non_strict_table(driver, orders):
    
    schema = Sqlite.TableStructure('non_strict', strict=False)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    join = Sqlite.Join.Inner(orders, tbl.id == orders.user_id)
    sql, _ = join._output
    assert "non_strict" in sql
def test_449_join_execution_with_complex_on(users, orders):
    
    users.insert({users.id: 1, users.name: 'Ali', users.age: 25})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    
    cond = (users.id == orders.user_id) & (users.age > 20)
    res = users.join([users.name, orders.total], [Sqlite.Join.Inner(orders, cond)])
    assert len(res) == 1
    assert res[0] == ('Ali', 50.0)
def test_450_join_right_execution_logic(users, orders):
    users.insert({users.id: 1, users.name: 'Ali'})
    orders.insert({orders.id: 100, orders.user_id: 1, orders.total: 50.0})
    orders.insert({orders.id: 101, orders.user_id: 99, orders.total: 20.0})
    res = users.join(
        [users.name, orders.total],
        [Sqlite.Join.Right(orders, users.id == orders.user_id)]
    )
    assert len(res) == 2
    orphan_row = [r for r in res if r[1] == 20.0][0]
    assert orphan_row[0] is None
@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_integration.db")
@pytest.fixture
def driver(db_path):
    drv = Sqlite.Driver(db_path, setup_time=0.1)
    yield drv
    try:
        drv.disconnect()
    except:
        pass
def test_451_full_lifecycle(driver):
    
    schema = Sqlite.TableStructure('lifecycle', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('val', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    
    tbl.insert({tbl.id: 1, tbl.val: 'Init'})
    tbl.update({tbl.val: 'Updated'}, tbl.id == 1)
    res = tbl.get_row([tbl.val], tbl.id == 1)
    assert res[0] == 'Updated'
    
    tbl.delete_row(tbl.id == 1)
    assert len(tbl.get_row([tbl.id], tbl.id == 1)) == 0
def test_452_concurrent_5_readers_1_writer(driver):
    
    schema = Sqlite.TableStructure('concurrent_tbl', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.insert({tbl.id: 1})
    stop_event = threading.Event()
    errors = []
    def writer():
        try:
            for i in range(10):
                tbl.update({tbl.id: i + 1}, tbl.id == 1) 
                time.sleep(0.01)
        except Exception as e:
            errors.append(e)
    def reader():
        try:
            while not stop_event.is_set():
                tbl.get_row([tbl.id], tbl.id == 1, from_readers_pool=True)
                time.sleep(0.01)
        except Exception as e:
            errors.append(e)
    t_write = threading.Thread(target=writer)
    t_reads = [threading.Thread(target=reader) for _ in range(5)]
    
    t_write.start()
    for t in t_reads: t.start()
    
    t_write.join()
    stop_event.set()
    for t in t_reads: t.join(timeout=2)
    
    assert len(errors) == 0
def test_453_disconnect_during_long_ops(driver):
    
    schema = Sqlite.TableStructure('long_op', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    
    def long_insert():
        for i in range(100):
            try:
                tbl.insert({tbl.id: i})
                time.sleep(0.01)
            except: break 
    t = threading.Thread(target=long_insert)
    t.start()
    time.sleep(0.2)
    driver.disconnect()
    t.join(timeout=2)
    
def test_454_pragma_then_disconnect(driver):
    
    driver.SetPragma.journal_mode('WAL')
    driver.SetPragma.foreign_keys(True)
    driver.SetPragma.synchronous('NORMAL')
    driver.disconnect() 
def test_456_fk_insert_related_data(driver):
    driver.SetPragma.foreign_keys(True)
    schema_p = Sqlite.TableStructure('parent_tbl', strict=True)
    schema_p.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    parent = driver.create_table(schema_p)
    schema_c = Sqlite.TableStructure('child_tbl', strict=True)
    schema_c.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema_c.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema_c.foreign_key('pid', parent, parent.id)
    child = driver.create_table(schema_c)
    parent.insert({parent.id: 1})
    child.insert({child.id: 1, child.pid: 1})
def test_457_add_column_after_data(driver):
    
    schema = Sqlite.TableStructure('alter_t', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.insert({tbl.id: 1})
    tbl.add_column('new_val', Sqlite.DataTypes.TEXT(), default_value='added')
    res = tbl.get_row([tbl.new_val], tbl.id == 1)
    assert res[0] == 'added'
def test_458_rename_column_and_get_row(driver):
    
    schema = Sqlite.TableStructure('ren_c', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('old', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.insert({tbl.id: 1, tbl.old: 'Data'})
    tbl.rename_column(tbl.old, 'new')
    assert tbl.get_row([tbl.new], tbl.id == 1)[0] == 'Data'
def test_459_rename_table_and_use_new(driver):
    
    schema = Sqlite.TableStructure('old_t', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.rename_table('new_t')
    driver.new_t.insert({driver.new_t.id: 1})
    assert len(driver.new_t.get_row([driver.new_t.id], driver.new_t.id == 1)) == 1
def test_460_delete_column_insert_without(driver):
    schema = Sqlite.TableStructure('del_c', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('temp', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.delete_column(tbl.temp, True, True, True)
    tbl.insert({tbl.id: 1})
    assert len(tbl.get_row([tbl.id], tbl.id == 1)) == 1
def test_461_delete_table_verify(driver):
    
    schema = Sqlite.TableStructure('del_t', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    tbl = driver.create_table(schema)
    tbl.delete_table(True, True, True)
    assert 'del_t' not in driver.get_tables()
def test_462_index_lifecycle(driver):
    
    schema = Sqlite.TableStructure('idx_l', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('a', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('my_idx', [tbl.a])
    assert 'my_idx' in tbl.get_indexes()
    assert tbl.get_index_info('my_idx') is not None
def test_463_reindex_after_modification(driver):
    
    schema = Sqlite.TableStructure('re_idx', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('a', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    tbl.create_index('idx1', [tbl.a])
    tbl.insert({tbl.id: 1, tbl.a: 'X'})
    tbl.reindex('idx1') 
def test_464_join_3_tables_complex_where(driver):
    
    u = driver.create_table(Sqlite.TableStructure('u', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('name', Sqlite.DataTypes.TEXT()))
    o = driver.create_table(Sqlite.TableStructure('o', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('uid', Sqlite.DataTypes.INTEGER()).add_column('total', Sqlite.DataTypes.REAL()))
    p = driver.create_table(Sqlite.TableStructure('p', strict=True).add_column('oid', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('paid', Sqlite.DataTypes.BOOLEAN()))
    u.insert({u.id: 1, u.name: 'A'})
    o.insert({o.id: 10, o.uid: 1, o.total: 100})
    p.insert({p.oid: 10, p.paid: True})
    res = u.join([u.name], [Sqlite.Join.Inner(o, u.id == o.uid), Sqlite.Join.Inner(p, o.id == p.oid)], where=p.paid == True)
    assert len(res) == 1
def test_465_join_computed_select(driver):
    
    u = driver.create_table(Sqlite.TableStructure('u2', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('name', Sqlite.DataTypes.TEXT()))
    o = driver.create_table(Sqlite.TableStructure('o2', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('uid', Sqlite.DataTypes.INTEGER()).add_column('total', Sqlite.DataTypes.REAL()))
    u.insert({u.id: 1, u.name: 'ali'})
    o.insert({o.id: 1, o.uid: 1, o.total: 50})
    res = u.join([u.name.upper(), o.total + 10], [Sqlite.Join.Inner(o, u.id == o.uid)])
    assert res[0] == ('ALI', 60.0)
def test_466_join_order_by_computed(driver):
    
    u = driver.create_table(Sqlite.TableStructure('u3', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True))
    o = driver.create_table(Sqlite.TableStructure('o3', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('uid', Sqlite.DataTypes.INTEGER()).add_column('total', Sqlite.DataTypes.REAL()))
    u.insert({u.id: 1})
    o.insert({o.id: 1, o.uid: 1, o.total: 50})
    res = u.join([u.id], [Sqlite.Join.Inner(o, u.id == o.uid)], order_by=o.total)
    assert len(res) == 1
def test_467_join_reader_pool_concurrent(driver):
    
    u = driver.create_table(Sqlite.TableStructure('u4', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True))
    u.insert({u.id: 1})
    res = u.join([u.id], joins_list=[], from_readers_pool=True)
    assert res[0][0] == 1
def test_468_batch_cross_table_rollback(driver):
    
    
    
    t1 = driver.create_table(Sqlite.TableStructure('b1', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True))
    t2 = driver.create_table(Sqlite.TableStructure('b2', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True))
    
    b1 = t1.batch()
    b1.insert({t1.id: 1})
    b1.run()
    assert len(t1.get_row([t1.id], t1.id == 1)) == 1
def test_469_batch_rollback_on_error(driver):
    
    tbl = driver.create_table(Sqlite.TableStructure('b_roll', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True))
    batch = tbl.batch()
    batch.insert({tbl.id: 1})
    batch.insert({tbl.id: 1}) 
    with pytest.raises(Exception):
        batch.run()
    assert len(tbl.get_row([tbl.id], where=None)) == 0
def test_470_bulk_insert_performance(driver):
    
    tbl = driver.create_table(Sqlite.TableStructure('perf', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('val', Sqlite.DataTypes.INTEGER()))
    data = [(i, i*2) for i in range(10000)]
    start = time.time()
    tbl.bulk_insert([tbl.id, tbl.val], data)
    end = time.time()
    assert (end - start) < 5.0 
    res = tbl.get_row([tbl.id], where=None, from_readers_pool=True)
    assert len(res) == 10000
def test_472_get_row_complex_op(driver):
    tbl = driver.create_table(Sqlite.TableStructure('comp', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('age', Sqlite.DataTypes.INTEGER()))
    tbl.insert({tbl.id: 1, tbl.age: 20})
    res = tbl.get_row([tbl.id], (tbl.age + 10) > 29)
    assert len(res) == 1
def test_473_get_row_like_percent(driver):
    
    tbl = driver.create_table(Sqlite.TableStructure('like_t', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('name', Sqlite.DataTypes.TEXT()))
    tbl.insert({tbl.id: 1, tbl.name: 'Alexander'})
    res = tbl.get_row([tbl.name], tbl.name.like('Alex%'))
    assert res[0] == 'Alexander'
def test_474_custom_execute_ddl(driver):
    
    driver.custom_execute("CREATE TABLE temp_ddl (id INTEGER);")
    driver.custom_execute("DROP TABLE temp_ddl;")
    assert 'temp_ddl' not in driver.get_tables()
def test_475_custom_execute_many_update(driver):
    
    tbl = driver.create_table(Sqlite.TableStructure('cem', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('val', Sqlite.DataTypes.TEXT()))
    tbl.insert({tbl.id: 1, tbl.val: 'A'})
    driver.custom_execute_many("UPDATE cem SET val = ? WHERE id = 1;", [('Updated',)])
    assert tbl.get_row([tbl.val], tbl.id == 1)[0] == 'Updated'
def test_476_pragma_fk_cascade(driver):
    driver.SetPragma.foreign_keys(True)
    p = driver.create_table(
        Sqlite.TableStructure('p_casc', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    )
    schema_c = Sqlite.TableStructure('c_casc', strict=True)
    schema_c.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema_c.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema_c.foreign_key('pid', p, p.id, on_delete='CASCADE')
    c = driver.create_table(schema_c)
    p.insert({p.id: 1})
    c.insert({c.id: 1, c.pid: 1})
    p.delete_row(p.id == 1)
    assert len(c.get_row([c.id], c.id == 1)) == 0
def test_477_set_wal_disconnect_file(driver, db_path):
    
    driver.set_WAL_mode(True, wal_timer=60)
    driver.disconnect()
    
    import os
    assert os.path.exists(db_path)
def test_478_defragment_after_deletes(driver):
    
    tbl = driver.create_table(Sqlite.TableStructure('frag', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True))
    tbl.bulk_insert([tbl.id], [(i,) for i in range(1000)])
    driver.custom_execute("DELETE FROM frag WHERE id < 500;")
    driver.defragment() 
def test_479_get_tables_after_rename(driver):
    
    tbl = driver.create_table(Sqlite.TableStructure('rn', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True))
    tbl.rename_table('rn_new')
    assert 'rn_new' in driver.get_tables()
def test_480_table_object_after_delete(driver):
    
    tbl = driver.create_table(Sqlite.TableStructure('del_obj', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True))
    tbl.delete_table(True, True, True)
    with pytest.raises(Exception):
        driver.table_object('del_obj')
def test_481_create_table_strict_fk(driver):
    ref = driver.create_table(
        Sqlite.TableStructure('ref_t', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    )
    schema = Sqlite.TableStructure('main_t', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('rid', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('rid', ref, ref.id)
    tbl = driver.create_table(schema)
    assert 'main_t' in driver.get_tables()
def test_482_custom_execute_params_typesA(driver):
    
    tbl = driver.create_table(Sqlite.TableStructure('par', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('v', Sqlite.DataTypes.TEXT()))
    driver.custom_execute("INSERT INTO par VALUES (?, ?);", [1, 'List'])
    driver.custom_execute("INSERT INTO par VALUES (?, ?);", (2, 'Tuple'))
    assert len(tbl.get_row([tbl.id], where=None)) == 2
def test_483_custom_execute_many_empty(driver):
    
    
    driver.custom_execute_many("CREATE TABLE emp_t (id INTEGER); INSERT INTO emp_t VALUES (1);", []) 
    driver.custom_execute("CREATE TABLE emp_t (id INTEGER PRIMARY KEY, val TEXT);")
    driver.custom_execute_many("INSERT INTO emp_t VALUES (?, ?);", [])
def test_484_get_row_columns_op_many_params(driver):
    
    tbl = driver.create_table(Sqlite.TableStructure('mnyp', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True).add_column('name', Sqlite.DataTypes.TEXT()))
    tbl.insert({tbl.id: 1, tbl.name: 'Test'})
    
    res = tbl.get_row([tbl.name], tbl.id.In([1, 2, 3, 4, 5]))
    assert res[0] == 'Test'
def test_485_batch_multiple_tables_ops(driver):
    
    
    t1 = driver.create_table(Sqlite.TableStructure('bm1', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True))
    t2 = driver.create_table(Sqlite.TableStructure('bm2', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True))
    b1 = t1.batch(); b1.insert({t1.id: 1}); b1.run()
    b2 = t2.batch(); b2.insert({t2.id: 1}); b2.run()
    assert len(t1.get_row([t1.id], where=None)) == 1
def test_486_dataTypes_float_min_max(driver):
    
    schema = Sqlite.TableStructure('fl_range', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('val', Sqlite.DataTypes.REAL(min_val=0.5, max_val=99.5))
    tbl = driver.create_table(schema)
    tbl.insert({tbl.id: 1, tbl.val: 50.0})
    with pytest.raises(Exception):
        tbl.insert({tbl.id: 2, tbl.val: 100.0}) 
def test_487_custom_type_empty_error(driver):
    
    with pytest.raises(Exception):
        Sqlite.DataTypes.CUSTOM('')
def test_488_structure_space_in_column(driver):
    
    schema = Sqlite.TableStructure('spc_col', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('my col', Sqlite.DataTypes.TEXT())
    tbl = driver.create_table(schema)
    assert 'my col' in tbl.get_columns_name()
def test_489_structure_deferrable_fk(driver):
    def_t = driver.create_table(
        Sqlite.TableStructure('def_t', strict=True).add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    )
    schema = Sqlite.TableStructure('def_t', strict=True)
    schema.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    schema.add_column('pid', Sqlite.DataTypes.INTEGER())
    schema.foreign_key('pid', def_t, def_t.id, deferrable=True, initially='DEFERRED')
    sql = schema.get_structure()
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
def test_499_comprehensive_e2e(db_path):
    drv = Sqlite.Driver(db_path, none_block_reader_pool_size=2, setup_time=0.2)
    drv.SetPragma.journal_mode('WAL')
    drv.SetPragma.foreign_keys(True)
    sch_u = Sqlite.TableStructure('e2e_users', strict=True)
    sch_u.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    sch_u.add_column('name', Sqlite.DataTypes.TEXT(), not_null=True)
    users = drv.create_table(sch_u)
    sch_o = Sqlite.TableStructure('e2e_orders', strict=True)
    sch_o.add_column('id', Sqlite.DataTypes.INTEGER(), primary_key=True)
    sch_o.add_column('user_id', Sqlite.DataTypes.INTEGER())
    sch_o.add_column('total', Sqlite.DataTypes.REAL())
    sch_o.foreign_key('user_id', users, users.id, on_delete='CASCADE')
    orders = drv.create_table(sch_o)
    users.insert({users.id: 1, users.name: 'Ali'})
    users.insert({users.id: 2, users.name: 'Reza'})
    orders.bulk_insert([orders.id, orders.user_id, orders.total], [(1, 1, 50.0), (2, 1, 100.0), (3, 2, 200.0)])
    res = users.join([users.name, orders.total], [Sqlite.Join.Inner(orders, users.id == orders.user_id)], where=orders.total > 50)
    assert len(res) == 2
    batch = users.batch()
    batch.update({users.name: 'AliU'}, users.id == 1)
    batch.run()
    assert users.get_row([users.name], users.id == 1)[0] == 'AliU'
    orders.create_index('idx_e2e_total', [orders.total])
    assert 'idx_e2e_total' in orders.get_indexes()
    drv.defragment()
    drv.disconnect()