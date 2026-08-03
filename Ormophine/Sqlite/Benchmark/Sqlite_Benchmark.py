"""Benchmark utilities for comparing SQLite ORM performance (Full CRUD)."""

from time import time, sleep
from Ormophine.Sqlite import Driver, Table
from pony.orm import *
from statistics import mean, variance, stdev
import sqlite3
from shutil import rmtree
from traceback import print_exc
import os
import gc
import tempfile
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from peewee import SqliteDatabase, Model, IntegerField, FloatField, TextField, AutoField
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np

def _get_benchmark_base_dir() -> str:
    """Return a writable directory that works in both Colab and local runs."""
    candidates = ['/content', os.getcwd(), tempfile.gettempdir()]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            os.makedirs(candidate, exist_ok=True)
            probe_path = os.path.join(candidate, '.ormophine_bench_write_test')
            with open(probe_path, 'w', encoding='utf-8') as handle:
                handle.write('ok')
            os.remove(probe_path)
            return candidate
        except OSError:
            continue
    return os.getcwd()

def _cleanup_benchmark_files(names: list[str], base_dir: str | None = None) -> None:
    """Remove benchmark database files from the previous run."""
    if base_dir is None:
        base_dir = _get_benchmark_base_dir()
    for name in names:
        full_path = os.path.join(base_dir, name)
        for suffix in ('', '-journal', '-wal', '-shm'):
            path = full_path + suffix
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    continue

def sqlalchemy_single_operations(rng, jour, sync):
    """Benchmark single CRUD operations using SQLAlchemy."""
    db_path = os.path.join(_get_benchmark_base_dir(), 'Test_sqlalchemy.db')
    with sqlite3.connect(db_path) as con:
        con.execute(f"PRAGMA journal_mode = {jour};")
        con.execute(f"PRAGMA synchronous = {sync};")
        con.execute("PRAGMA page_size = 65536;")
        con.execute("PRAGMA wal_autocheckpoint = 0;")
        con.execute("PRAGMA journal_size_limit = 10485760;")
        con.execute('''
            CREATE TABLE IF NOT EXISTS "TestTable" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "col_1" INTEGER DEFAULT 5,
                "col_2" TEXT DEFAULT "five",
                "col_3" REAL DEFAULT 5.0
                );
        ''')
        con.commit()

    Base = declarative_base()
    class TestTable(Base):
        __tablename__ = 'TestTable'
        id = Column(Integer, primary_key=True)  
        col_1 = Column(Integer)
        col_2 = Column(String)
        col_3 = Column(Float)

    engine = create_engine(f'sqlite:///{db_path}', echo=False, connect_args={'check_same_thread': False})
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()

    # Create (Insert)
    T0 = time()
    for i in range(rng):
        record = TestTable(col_1=i, col_2=f'str{i}', col_3=0.5 + i)
        session.add(record)
        session.commit()
    elapsed_insert = time() - T0

    # Update
    T0 = time()
    for i in range(rng):
        session.query(TestTable).filter(
            TestTable.col_1 == i, TestTable.col_2 == f'str{i}', TestTable.col_3 == i + 0.5
        ).update({
            'col_1': TestTable.col_1 + (TestTable.col_3 * 2),
            'col_2': 'WRAP_' + TestTable.col_2 + '_PER',
            'col_3': TestTable.col_3 + (TestTable.col_1 * 2)
        }, synchronize_session=False)
        session.commit()
    elapsed_update = time() - T0

    # Read
    T0 = time()
    for i in range(rng):
        rec = session.query(TestTable).filter(TestTable.col_2 == f'WRAP_str{i}_PER').first()
        res = (rec.col_1, rec.col_2, rec.col_3)
    elapsed_read = time() - T0

    # Delete
    T0 = time()
    for i in range(rng):
        session.query(TestTable).filter(TestTable.id == i+1).delete()
        session.commit()
    elapsed_delete = time() - T0

    session.close()
    engine.dispose()
    return elapsed_insert, elapsed_update, elapsed_read, elapsed_delete

def sqlalchemy_batch_operations(rng, jour, sync):
    """Benchmark batch CRUD operations using SQLAlchemy."""
    db_path = os.path.join(_get_benchmark_base_dir(), 'Test_sqlalchemy.db')
    with sqlite3.connect(db_path) as con:
        con.execute(f"PRAGMA journal_mode = {jour};")
        con.execute(f"PRAGMA synchronous = {sync};")
        con.execute("PRAGMA page_size = 65536;")
        con.execute("PRAGMA wal_autocheckpoint = 0;")
        con.execute("PRAGMA journal_size_limit = 10485760;")
        con.execute('''
            CREATE TABLE IF NOT EXISTS "TestTable" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "col_1" INTEGER DEFAULT 5,
                "col_2" TEXT DEFAULT "five",
                "col_3" REAL DEFAULT 5.0
                );
        ''')
        con.commit()

    Base = declarative_base()
    class TestTable(Base):
        __tablename__ = 'TestTable'
        id = Column(Integer, primary_key=True)  
        col_1 = Column(Integer)
        col_2 = Column(String)
        col_3 = Column(Float)

    engine = create_engine(f'sqlite:///{db_path}', echo=False, connect_args={'check_same_thread': False})
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()

    # Batch Create (Insert)
    T0 = time()
    for i in range(rng):
        record = TestTable(col_1=i, col_2=f'str{i}', col_3=0.5 + i)
        session.add(record)
    session.commit()
    elapsed_insert = time() - T0

    # Batch Update
    T0 = time()
    for i in range(rng):
        session.query(TestTable).filter(
            TestTable.id == i+1, TestTable.col_1 == i, TestTable.col_2 == f'str{i}', TestTable.col_3 == i + 0.5
        ).update({
            'col_1': TestTable.col_1 + (TestTable.col_3 * 2),
            'col_2': 'WRAP_' + TestTable.col_2 + '_PER',
            'col_3': TestTable.col_3 + (TestTable.col_1 * 2)
        }, synchronize_session=False)
    session.commit()
    elapsed_update = time() - T0

    # Batch Delete
    T0 = time()
    for i in range(rng):
        session.query(TestTable).filter(TestTable.id == i+1).delete()
    session.commit()
    elapsed_delete = time() - T0

    session.close()
    engine.dispose()
    return elapsed_insert, elapsed_update, elapsed_delete

def peewee_single_operations(rng, jour, sync):
    """Benchmark single CRUD operations using Peewee."""
    db_path = os.path.join(_get_benchmark_base_dir(), 'Test_peewee.db')
    with sqlite3.connect(db_path) as con:
        con.execute(f"PRAGMA journal_mode = {jour};")
        con.execute(f"PRAGMA synchronous = {sync};")
        con.execute("PRAGMA page_size = 65536;")
        con.execute("PRAGMA journal_size_limit = 10485760;")
        con.execute("PRAGMA wal_autocheckpoint = 0;")
        con.execute('''
            CREATE TABLE IF NOT EXISTS "TestTable" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "col_1" INTEGER DEFAULT 5,
                "col_2" TEXT DEFAULT "five",
                "col_3" REAL DEFAULT 5.0
            );
        ''')
        con.commit()
        
    db = SqliteDatabase(db_path, autocommit=False)
    class TestTable(Model):
        id = AutoField()  
        col_1 = IntegerField()
        col_2 = TextField()
        col_3 = FloatField()
        class Meta:
            database = db
            table_name = 'TestTable'
    db.connect()
    
    # Create
    T0 = time()
    for i in range(rng):
        TestTable.insert(col_1=i, col_2=f'str{i}', col_3=i+0.5).execute()
        db.manual_commit()
    elapsed_insert = time() - T0

    # Update
    T0 = time()
    for i in range(rng):
        TestTable.update(
                col_1=TestTable.col_1 + (TestTable.col_3 * 2),
                col_2='WRAP_' + TestTable.col_2 + '_PER',
                col_3=TestTable.col_3 + (TestTable.col_1 * 2)
            ).where(
                (TestTable.col_1 == i) & (TestTable.col_2 == f'str{i}') & (TestTable.col_3 == i+0.5)
            ).execute()
        db.manual_commit() 
    elapsed_update = time() - T0

    # Read
    T0 = time()
    for i in range(rng):
        record = TestTable.select(TestTable.col_1, TestTable.col_2, TestTable.col_3).where(TestTable.col_2 == f'WRAP_str{i}_PER').get()
        read_result = (record.col_1, record.col_2, record.col_3)
    elapsed_read = time() - T0

    # Delete
    T0 = time()
    for i in range(rng):
        TestTable.delete().where(TestTable.id == i+1).execute()
        db.manual_commit()
    elapsed_delete = time() - T0

    db.close()
    return elapsed_insert, elapsed_update, elapsed_read, elapsed_delete

def peewee_batch_operations(rng, jour, sync):
    """Benchmark batch CRUD operations using Peewee."""
    db_path = os.path.join(_get_benchmark_base_dir(), 'Test_peewee.db')
    with sqlite3.connect(db_path) as con:
        con.execute(f"PRAGMA journal_mode = {jour};")
        con.execute(f"PRAGMA synchronous = {sync};")
        con.execute("PRAGMA page_size = 65536;")
        con.execute("PRAGMA journal_size_limit = 10485760;")
        con.execute("PRAGMA wal_autocheckpoint = 0;")
        con.execute('''
            CREATE TABLE IF NOT EXISTS "TestTable" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "col_1" INTEGER DEFAULT 5,
                "col_2" TEXT DEFAULT "five",
                "col_3" REAL DEFAULT 5.0
            );
        ''')
        con.commit()
        
    db = SqliteDatabase(db_path, autocommit=False)
    class TestTable(Model):
        id = AutoField()  
        col_1 = IntegerField()
        col_2 = TextField()
        col_3 = FloatField()
        class Meta:
            database = db
            table_name = 'TestTable'
    db.connect()

    # Batch Create
    T0 = time()
    with db.atomic():
        for i in range(rng):
            TestTable.insert(col_1=i, col_2=f'str{i}', col_3=i+0.5).execute()
    elapsed_insert = time() - T0

    # Batch Update
    T0 = time()
    with db.atomic():
        for i in range(rng):
            TestTable.update(
                    col_1=TestTable.col_1 + (TestTable.col_3 * 2),
                    col_2='WRAP_' + TestTable.col_2 + '_PER',
                    col_3=TestTable.col_3 + (TestTable.col_1 * 2)
                ).where(
                    (TestTable.id == i+1) & (TestTable.col_1 == i) & (TestTable.col_2 == f'str{i}') & (TestTable.col_3 == i+0.5)
                ).execute()
    elapsed_update = time() - T0

    # Batch Delete
    T0 = time()
    with db.atomic():
        for i in range(rng):
            TestTable.delete().where(TestTable.id == i+1).execute()
    elapsed_delete = time() - T0

    db.close()
    return elapsed_insert, elapsed_update, elapsed_delete

def pony_single_operations(rng, jour, sync):
    """Benchmark single CRUD operations using PonyORM."""
    db_path = os.path.join(_get_benchmark_base_dir(), 'Test_pony.db')
    with sqlite3.connect(db_path) as con:
        con.execute(f"PRAGMA journal_mode = {jour};")
        con.execute(f"PRAGMA synchronous = {sync};")
        con.execute("PRAGMA page_size = 65536;")
        con.execute("PRAGMA journal_size_limit = 10485760;")
        con.execute("PRAGMA wal_autocheckpoint = 0;")
        con.execute('''
            CREATE TABLE IF NOT EXISTS "TestTable" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "col_1" INTEGER DEFAULT 5,
                "col_2" TEXT DEFAULT "five",
                "col_3" REAL DEFAULT 5.0
            );
        ''')
        con.commit()
        
    db = Database()
    class TestTable(db.Entity):
        _table_ = 'TestTable'
        id = PrimaryKey(int, auto=True)  
        col_1 = Required(int)
        col_2 = Required(str)
        col_3 = Required(float)
    db.bind(provider='sqlite', filename=db_path, create_db=True)
    db.generate_mapping(create_tables=False)

    @db_session()
    def pony_insert():
        T0 = time()
        for i in range(rng):
            TestTable(col_1=i, col_2=f'str{i}', col_3=i+0.5)
            commit()
        return time() - T0

    @db_session()
    def pony_update():
        T0 = time()
        for i in range(rng):
            record = TestTable.get(col_1=i, col_2=f'str{i}', col_3=i + 0.5)
            record.col_1 = record.col_1 + int(record.col_3 * 2)
            record.col_2 = 'WRAP_' + record.col_2 + '_PER'
            record.col_3 = record.col_3 + (record.col_1 * 2)
            commit()
        return time() - T0

    @db_session()
    def pony_read():
        T0 = time()
        for i in range(rng):
            record = TestTable.get(id=i + 1)
            a,b,c = record.col_1 , record.col_2 , record.col_3
        return time() - T0

    @db_session()
    def pony_delete():
        T0 = time()
        for i in range(rng):
            TestTable[i+1].delete()
            commit()
        return time() - T0
    
    elapsed_insert = pony_insert()
    elapsed_update = pony_update()
    elapsed_read = pony_read()
    elapsed_delete = pony_delete()

    db.disconnect()
    return elapsed_insert, elapsed_update, elapsed_read, elapsed_delete

def pony_batch_operations(rng, jour, sync):
    """Benchmark batch CRUD operations using PonyORM."""
    db_path = os.path.join(_get_benchmark_base_dir(), 'Test_pony.db')
    with sqlite3.connect(db_path) as con:
        con.execute(f"PRAGMA journal_mode = {jour};")
        con.execute(f"PRAGMA synchronous = {sync};")
        con.execute("PRAGMA page_size = 65536;")
        con.execute("PRAGMA journal_size_limit = 10485760;")
        con.execute("PRAGMA wal_autocheckpoint = 0;")
        con.execute('''
            CREATE TABLE IF NOT EXISTS "TestTable" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "col_1" INTEGER DEFAULT 5,
                "col_2" TEXT DEFAULT "five",
                "col_3" REAL DEFAULT 5.0
            );
        ''')
        con.commit()

    db = Database()
    class TestTable(db.Entity):
        _table_ = 'TestTable'
        id = PrimaryKey(int, auto=True)  
        col_1 = Required(int)
        col_2 = Required(str)
        col_3 = Required(float)
    db.bind(provider='sqlite', filename=db_path, create_db=True)
    db.generate_mapping(create_tables=False)

    @db_session()
    def pony_insert():
        T0 = time()
        for i in range(rng):
            TestTable(col_1=i, col_2=f'str{i}', col_3=i+0.5)
        commit()
        return time() - T0

    @db_session()
    def pony_update():
        T0 = time()
        for i in range(rng):
            record = TestTable.get(id=i+1, col_1=i, col_2=f'str{i}', col_3=i + 0.5)
            record.col_1 = record.col_1 + int(record.col_3 * 2)
            record.col_2 = 'WRAP_' + record.col_2 + '_PER'
            record.col_3 = record.col_3 + (record.col_1 * 2)
        db.commit()
        return time() - T0

    @db_session()
    def pony_delete():
        T0 = time()
        for i in range(rng):
            TestTable[i+1].delete()
        db.commit()
        return time() - T0
    
    elapsed_insert = pony_insert()
    elapsed_update = pony_update()
    elapsed_delete = pony_delete()

    db.disconnect()
    return elapsed_insert, elapsed_update, elapsed_delete

def Ormophine_single_operations(rng, jour, sync):
    """Benchmark single CRUD operations using Ormophine ORM."""
    db_path = os.path.join(_get_benchmark_base_dir(), 'Test_Ormophine.db')
    with sqlite3.connect(db_path) as con:
        con.execute(f"PRAGMA journal_mode = {jour};")
        con.execute(f"PRAGMA synchronous = {sync};")
        con.execute("PRAGMA journal_size_limit = 10485760;")
        con.execute("PRAGMA page_size = 65536;")
        con.execute('''
            CREATE TABLE IF NOT EXISTS "TestTable" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "col_1" INTEGER DEFAULT 5,
                "col_2" TEXT DEFAULT "five",
                "col_3" REAL DEFAULT 5.0
            );
        ''')
        con.commit()
        
    db = Driver(db_path)
    tb = db.TestTable

    # Create
    T0 = time()
    for i in range(rng):
        tb.insert({tb.col_1 : i , tb.col_2 : f'str{i}' , tb.col_3 : i+0.5})
    tb.get_row([tb.col_2], where=(tb.col_2 == f'str{i-1}'))
    elapsed_inserts = time() - T0

    # Update
    T0 = time()
    for i in range(rng):
        tb.update(
            {tb.col_1: tb.col_1 + (tb.col_3 * 2), tb.col_2: 'WRAP_' + tb.col_2 + '_PER', tb.col_3: tb.col_3 + (tb.col_1 * 2)},
            where=((tb.col_1 == i) & (tb.col_2 == f'str{i}') & (tb.col_3 == i + 0.5))
        )
    tb.get_row([tb.col_2], where=(tb.col_2 == f'WRAP_str{i-1}_PER'))
    elapsed_updates = time() - T0

    # Read
    T0 = time()
    for i in range(rng):
        tb.get_row([tb.col_1, tb.col_2, tb.col_3], where=(tb.col_2 == f'WRAP_str{i}_PER'))
    elapsed_gets = time() - T0

    # Delete
    T0 = time()
    for i in range(rng):
        tb.delete_row(where=(tb.id == i+1))
    # To ensure queue is empty, we check for a non-existent row which forces sync
    tb.get_row([tb.id], where=(tb.id == rng + 1))
    elapsed_deletes = time() - T0
    
    db.disconnect()
    return elapsed_inserts, elapsed_updates, elapsed_gets, elapsed_deletes

def Ormophine_batch_operations(rng, jour, sync):
    """Benchmark batch CRUD operations using Ormophine ORM."""
    db_path = os.path.join(_get_benchmark_base_dir(), 'Test_Ormophine.db')
    con = sqlite3.connect(db_path)
    con.execute(f"PRAGMA journal_mode = {jour};")
    con.execute(f"PRAGMA synchronous = {sync};")
    con.execute("PRAGMA journal_size_limit = 10485760;")
    con.execute("PRAGMA page_size = 65536;")
    con.execute("PRAGMA wal_autocheckpoint = 0;")
    con.execute('''
        CREATE TABLE IF NOT EXISTS "TestTable" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "col_1" INTEGER DEFAULT 5,
            "col_2" TEXT DEFAULT "five",
            "col_3" REAL DEFAULT 5.0
        );
    ''')
    con.commit()
    con.close()
    
    db = Driver(db_path)
    tb : Table = db.TestTable

    # Batch Create
    T0 = time()
    batch = tb.batch()
    for i in range(rng):
        batch.insert({tb.col_1 : i , tb.col_2 : f'str{i}' , tb.col_3 : i+0.5})
    batch.run()
    tb.get_row([tb.col_2], where=(tb.col_2 == f'str{i-1}'))
    elapsed_inserts = time() - T0

    # Batch Update
    T0 = time()
    batch = tb.batch()
    for i in range(rng):
        batch.update({tb.col_1 : tb.col_1+(tb.col_3*2) , tb.col_2 : 'WRAP_'+tb.col_2+'_PER' , tb.col_3 : tb.col_3 + (tb.col_1*2)} , (tb.col_1 == i) & (tb.col_2 == f'str{i}') & (tb.col_3 == i+0.5))
    batch.run()
    tb.get_row([tb.col_2], where=(tb.col_2 == f'WRAP_str{i-1}_PER'))
    elapsed_updates = time() - T0

    # Batch Delete
    T0 = time()
    batch = tb.batch()
    for i in range(rng):
        batch.delete_row(where=(tb.id == i+1))
    batch.run()
    # Force sync to ensure all deletes are completed before stopping timer
    tb.get_row([tb.id], where=(tb.id == rng + 1))
    elapsed_deletes = time() - T0
    
    db.disconnect()
    return elapsed_inserts, elapsed_updates, elapsed_deletes

def plot_benchmark_results(title, labels, insert_means, update_means, read_means=None, delete_means=None):
    """Generate a bar chart to compare ORM means (values in milliseconds)."""
    x = np.arange(len(labels))
    width = 0.2

    # تبدیل ثانیه به میلی‌ثانیه
    insert_means_ms = [v * 1000 for v in insert_means]
    update_means_ms = [v * 1000 for v in update_means]
    if delete_means is not None:
        delete_means_ms = [v * 1000 for v in delete_means]
    if read_means is not None:
        read_means_ms = [v * 1000 for v in read_means]

    fig, ax = plt.subplots(figsize=(12, 7))

    # تعیین رنگ‌های ثابت برای هر عملیات
    color_insert = 'blue'
    color_update = 'orange'
    color_read = 'green'
    color_delete = 'red'

    if read_means is not None and delete_means is not None:
        # 4 میله: CRUD
        rects1 = ax.bar(x - 1.5*width, insert_means_ms, width, label='Inserts', color=color_insert)
        rects2 = ax.bar(x - 0.5*width, update_means_ms, width, label='Updates', color=color_update)
        rects3 = ax.bar(x + 0.5*width, read_means_ms, width, label='Reads', color=color_read)
        rects4 = ax.bar(x + 1.5*width, delete_means_ms, width, label='Deletes', color=color_delete)
        rects = [rects1, rects2, rects3, rects4]
    elif delete_means is not None:
        # 3 میله: CUD (مخصوص Batch)
        rects1 = ax.bar(x - width, insert_means_ms, width, label='Inserts', color=color_insert)
        rects2 = ax.bar(x, update_means_ms, width, label='Updates', color=color_update)
        rects3 = ax.bar(x + width, delete_means_ms, width, label='Deletes', color=color_delete)
        rects = [rects1, rects2, rects3]
    else:
        # 2 میله: CU
        rects1 = ax.bar(x - width/2, insert_means_ms, width, label='Inserts', color=color_insert)
        rects2 = ax.bar(x + width/2, update_means_ms, width, label='Updates', color=color_update)
        rects = [rects1, rects2]

    ax.set_ylabel('Time (milliseconds) - Lower is Better')
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.3f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)

    for r in rects:
        autolabel(r)

    fig.tight_layout()
    plt.show()

def run_single_operation_benchmark(repeats: int, journal_mode: str, synchronous: str, warmup_repeats: int= 3, chunk_size: int= 10):
    """Run the single-operation CRUD benchmark for all ORMs.

    This test measures the overhead of the ORM and the database connection
    when executing queries one by one. To ensure the benchmark is fair:
    - Standard ORMs (SQLAlchemy, Peewee, PonyORM) execute a commit() after every single query.
    - PonyORM inherently uses a Unit of Work pattern (Identity Map). For updates, it performs a 
      SELECT followed by an UPDATE, which is its standard behavior.
    - Ormophine utilizes an auto-commit/queue mechanism. A `get_row` sync is called at the end 
      to ensure all queued operations are fully executed before the timer stops, making it 
      directly comparable to immediate commits.
    """
    names = ['Test_pony.db', "Test_Ormophine.db", 'Test_sqlalchemy.db', 'Test_peewee.db']

    pony_inserts, esq_inserts, sqlalchemy_inserts, peewee_inserts = [], [], [], []
    pony_updates, esq_updates, sqlalchemy_updates, peewee_updates = [], [], [], []
    pony_reads, esq_reads, sqlalchemy_reads, peewee_reads = [], [], [], []
    pony_deletes, esq_deletes, sqlalchemy_deletes, peewee_deletes = [], [], [], []

    print('\n--- Starting Single Operation Benchmark ---')

    for _ in tqdm(range(warmup_repeats), desc="Warmup Phase (Single Ops)", unit="run", leave=False):
        gc.collect(); sleep(0.1); _cleanup_benchmark_files(names)
        pony_single_operations(chunk_size, journal_mode, synchronous)
        Ormophine_single_operations(chunk_size, journal_mode, synchronous)
        sqlalchemy_single_operations(chunk_size, journal_mode, synchronous)
        peewee_single_operations(chunk_size, journal_mode, synchronous)

    print('################## RUNNING BENCHMARK ##################')

    for _ in tqdm(range(repeats), desc="Benchmarking Single Ops", unit="run"):
        gc.collect(); sleep(0.1); _cleanup_benchmark_files(names)

        pon_ins, pon_upd, pon_rd, pon_del = pony_single_operations(chunk_size, journal_mode, synchronous)
        sq_ins, sq_upd, sq_rd, sq_del = Ormophine_single_operations(chunk_size, journal_mode, synchronous)
        alch_ins, alch_upd, alch_rd, alch_del = sqlalchemy_single_operations(chunk_size, journal_mode, synchronous)
        pee_ins, pee_upd, pee_rd, pee_del = peewee_single_operations(chunk_size, journal_mode, synchronous)

        pony_inserts.append(pon_ins); esq_inserts.append(sq_ins); sqlalchemy_inserts.append(alch_ins); peewee_inserts.append(pee_ins)
        pony_updates.append(pon_upd); esq_updates.append(sq_upd); sqlalchemy_updates.append(alch_upd); peewee_updates.append(pee_upd)
        pony_reads.append(pon_rd); esq_reads.append(sq_rd); sqlalchemy_reads.append(alch_rd); peewee_reads.append(pee_rd)
        pony_deletes.append(pon_del); esq_deletes.append(sq_del); sqlalchemy_deletes.append(alch_del); peewee_deletes.append(pee_del)

    pony_ins_mean = mean(pony_inserts); pony_upd_mean = mean(pony_updates); pony_rd_mean = mean(pony_reads); pony_del_mean = mean(pony_deletes)
    esq_ins_mean = mean(esq_inserts); esq_upd_mean = mean(esq_updates); esq_rd_mean = mean(esq_reads); esq_del_mean = mean(esq_deletes)
    sal_ins_mean = mean(sqlalchemy_inserts); sal_upd_mean = mean(sqlalchemy_updates); sal_rd_mean = mean(sqlalchemy_reads); sal_del_mean = mean(sqlalchemy_deletes)
    pee_ins_mean = mean(peewee_inserts); pee_upd_mean = mean(peewee_updates); pee_rd_mean = mean(peewee_reads); pee_del_mean = mean(peewee_deletes)

    print(f"\n--- Performance Statistics (N={repeats}, {chunk_size} records each) ---")
    print(f'------------- Journal_mode = {journal_mode} % synchronous = {synchronous}------------')

    print( '\n-------------------------   INSERTS   ------------------------------')
    print(f"Pony ORM: Mean={pony_ins_mean:.4f}s, Variance={variance(pony_inserts):.4f}, StdDev={stdev(pony_inserts):.4f}")
    print(f"Ormophine: Mean={esq_ins_mean:.4f}s, Variance={variance(esq_inserts):.4f}, StdDev={stdev(esq_inserts):.4f}")
    print(f"SQLAlchemy: Mean={sal_ins_mean:.4f}s, Variance={variance(sqlalchemy_inserts):.4f}, StdDev={stdev(sqlalchemy_inserts):.4f}")
    print(f"Peewee: Mean={pee_ins_mean:.4f}s, Variance={variance(peewee_inserts):.4f}, StdDev={stdev(peewee_inserts):.4f}")

    print( '\n-------------------------   UPDATES   ------------------------------')
    print(f"Pony ORM: Mean={pony_upd_mean:.4f}s, Variance={variance(pony_updates):.4f}, StdDev={stdev(pony_updates):.4f}")
    print(f"Ormophine: Mean={esq_upd_mean:.4f}s, Variance={variance(esq_updates):.4f}, StdDev={stdev(esq_updates):.4f}")
    print(f"SQLAlchemy: Mean={sal_upd_mean:.4f}s, Variance={variance(sqlalchemy_updates):.4f}, StdDev={stdev(sqlalchemy_updates):.4f}")
    print(f"Peewee: Mean={pee_upd_mean:.4f}s, Variance={variance(peewee_updates):.4f}, StdDev={stdev(peewee_updates):.4f}")

    print( '\n-------------------------   READS   ------------------------------')
    print(f"Pony ORM: Mean={pony_rd_mean:.4f}s, Variance={variance(pony_reads):.4f}, StdDev={stdev(pony_reads):.4f}")
    print(f"Ormophine: Mean={esq_rd_mean:.4f}s, Variance={variance(esq_reads):.4f}, StdDev={stdev(esq_reads):.4f}")
    print(f"SQLAlchemy: Mean={sal_rd_mean:.4f}s, Variance={variance(sqlalchemy_reads):.4f}, StdDev={stdev(sqlalchemy_reads):.4f}")
    print(f"Peewee: Mean={pee_rd_mean:.4f}s, Variance={variance(peewee_reads):.4f}, StdDev={stdev(peewee_reads):.4f}")

    print( '\n-------------------------   DELETES   ------------------------------')
    print(f"Pony ORM: Mean={pony_del_mean:.4f}s, Variance={variance(pony_deletes):.4f}, StdDev={stdev(pony_deletes):.4f}")
    print(f"Ormophine: Mean={esq_del_mean:.4f}s, Variance={variance(esq_deletes):.4f}, StdDev={stdev(esq_deletes):.4f}")
    print(f"SQLAlchemy: Mean={sal_del_mean:.4f}s, Variance={variance(sqlalchemy_deletes):.4f}, StdDev={stdev(sqlalchemy_deletes):.4f}")
    print(f"Peewee: Mean={pee_del_mean:.4f}s, Variance={variance(peewee_deletes):.4f}, StdDev={stdev(peewee_deletes):.4f}")

    def calculate_percentage_diff(base_time, other_time):
        return ((other_time - base_time) / base_time) * 100

    print(f"\n--- Percentage Differences In Inserts ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_ins_mean, pony_ins_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_ins_mean, sal_ins_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_ins_mean, pee_ins_mean):.2f}%")

    print(f"\n--- Percentage Differences In Updates ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_upd_mean, pony_upd_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_upd_mean, sal_upd_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_upd_mean, pee_upd_mean):.2f}%")

    print(f"\n--- Percentage Differences In Reads ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_rd_mean, pony_rd_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_rd_mean, sal_rd_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_rd_mean, pee_rd_mean):.2f}%")

    print(f"\n--- Percentage Differences In Deletes ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_del_mean, pony_del_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_del_mean, sal_del_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_del_mean, pee_del_mean):.2f}%")

    labels = ['Ormophine', 'Pony ORM', 'SQLAlchemy', 'Peewee']
    plot_benchmark_results('Single Operation Benchmark Results (CRUD)', labels, 
                           [esq_ins_mean, pony_ins_mean, sal_ins_mean, pee_ins_mean],
                           [esq_upd_mean, pony_upd_mean, sal_upd_mean, pee_upd_mean],
                           read_means=[esq_rd_mean, pony_rd_mean, sal_rd_mean, pee_rd_mean],
                           delete_means=[esq_del_mean, pony_del_mean, sal_del_mean, pee_del_mean])
    
    # --- Execution Report ---
    total_queries = repeats * chunk_size
    print("\n" + "="*60)
    print("📊 BENCHMARK EXECUTION REPORT")
    print("="*60)
    print(f"This benchmark evaluates the performance of 4 Python ORMs (Ormophine, Pony ORM, SQLAlchemy, Peewee) on a SQLite database.")
    print(f"\n- Test Type: Single Operations (Commit executed after EVERY query)")
    print(f"- Operations Tested: Full CRUD (Inserts, Updates, Reads, Deletes)")
    print(f"- Total Queries per Operation: {total_queries} queries ({chunk_size} queries/repeat * {repeats} repeats)")
    print(f"- SQLite Configuration: Journal Mode = {journal_mode.upper()}, Synchronous = {synchronous.upper()}")
    print(f"\n📈 HOW TO READ THE CHART:")
    print("The bar chart displays the Mean Execution Time in milliseconds (ms) for each ORM.")
    print("A LOWER bar indicates BETTER performance (the ORM took less time to execute the queries).")
    print("Variance and Standard Deviation (shown in the text output above) indicate the stability of the results;")
    print("lower numbers mean the ORM performed consistently across all repetitions.")
    print("\nⓘ NOTE ON METHODOLOGY:")
    print("- PonyORM inherently uses a Unit of Work pattern (Identity Map) for updates, meaning it performs a SELECT")
    print("  followed by an UPDATE inside the loop, unlike direct bulk-update queries used by other ORMs.")
    print("- Ormophine utilizes an auto-commit mechanism and a queue sync to ensure operations are fully executed.")
    print("="*60 + "\n")

def run_batch_operation_benchmark(repeats: int, journal_mode: str, synchronous: str, warmup_repeats: int= 3, chunk_size: int= 10000):
    """Run the batch-operation CUD benchmark for all ORMs.

    This test measures the throughput of ORMs when processing large amounts of data.
    To ensure the benchmark is fair:
    - Standard ORMs (SQLAlchemy, Peewee, PonyORM) execute a commit() only ONCE at the end 
      of the loop (or within a single transaction).
    - Ormophine utilizes a batch queue and runs a sync check (`get_row`) at the end to 
      ensure all operations are flushed to the database before the timer stops.
    - A heavy workload (chunk_size=10000) is used to minimize the impact of connection 
      overhead and emphasize actual ORM processing and I/O efficiency.
    """
    names = ['Test_pony.db', "Test_Ormophine.db", 'Test_sqlalchemy.db', 'Test_peewee.db']

    pony_inserts, esq_inserts, sqlalchemy_inserts, peewee_inserts = [], [], [], []
    pony_updates, esq_updates, sqlalchemy_updates, peewee_updates = [], [], [], []
    pony_deletes, esq_deletes, sqlalchemy_deletes, peewee_deletes = [], [], [], []

    print('\n--- Starting Batch Operation Benchmark ---')

    for _ in tqdm(range(warmup_repeats), desc="Warmup Phase (Batch Ops)", unit="run", leave=False):
        gc.collect(); sleep(0.1); _cleanup_benchmark_files(names)
        pony_batch_operations(chunk_size, journal_mode, synchronous)
        Ormophine_batch_operations(chunk_size, journal_mode, synchronous)
        sqlalchemy_batch_operations(chunk_size, journal_mode, synchronous)
        peewee_batch_operations(chunk_size, journal_mode, synchronous)

    print('################## RUNNING BENCHMARK ##################')

    for _ in tqdm(range(repeats), desc="Benchmarking Batch Ops", unit="run"):
        gc.collect(); sleep(0.1); _cleanup_benchmark_files(names)

        pon_ins, pon_upd, pon_del = pony_batch_operations(chunk_size, journal_mode, synchronous)
        sq_ins, sq_upd, sq_del = Ormophine_batch_operations(chunk_size, journal_mode, synchronous)
        alch_ins, alch_upd, alch_del = sqlalchemy_batch_operations(chunk_size, journal_mode, synchronous)
        pee_ins, pee_upd, pee_del = peewee_batch_operations(chunk_size, journal_mode, synchronous)

        pony_inserts.append(pon_ins); esq_inserts.append(sq_ins); sqlalchemy_inserts.append(alch_ins); peewee_inserts.append(pee_ins)
        pony_updates.append(pon_upd); esq_updates.append(sq_upd); sqlalchemy_updates.append(alch_upd); peewee_updates.append(pee_upd)
        pony_deletes.append(pon_del); esq_deletes.append(sq_del); sqlalchemy_deletes.append(alch_del); peewee_deletes.append(pee_del)

    pony_ins_mean = mean(pony_inserts); pony_upd_mean = mean(pony_updates); pony_del_mean = mean(pony_deletes)
    esq_ins_mean = mean(esq_inserts); esq_upd_mean = mean(esq_updates); esq_del_mean = mean(esq_deletes)
    sal_ins_mean = mean(sqlalchemy_inserts); sal_upd_mean = mean(sqlalchemy_updates); sal_del_mean = mean(sqlalchemy_deletes)
    pee_ins_mean = mean(peewee_inserts); pee_upd_mean = mean(peewee_updates); pee_del_mean = mean(peewee_deletes)

    print(f"\n--- Performance Statistics (N={repeats}, {chunk_size} records each) ---")
    print(f'------------- Journal_mode = {journal_mode} % synchronous = {synchronous}------------')

    print( '\n-------------------------   INSERTS   ------------------------------')
    print(f"Pony ORM: Mean={pony_ins_mean:.4f}s, Variance={variance(pony_inserts):.4f}, StdDev={stdev(pony_inserts):.4f}")
    print(f"Ormophine: Mean={esq_ins_mean:.4f}s, Variance={variance(esq_inserts):.4f}, StdDev={stdev(esq_inserts):.4f}")
    print(f"SQLAlchemy: Mean={sal_ins_mean:.4f}s, Variance={variance(sqlalchemy_inserts):.4f}, StdDev={stdev(sqlalchemy_inserts):.4f}")
    print(f"Peewee: Mean={pee_ins_mean:.4f}s, Variance={variance(peewee_inserts):.4f}, StdDev={stdev(peewee_inserts):.4f}")

    print( '\n-------------------------   UPDATES   ------------------------------')
    print(f"Pony ORM: Mean={pony_upd_mean:.4f}s, Variance={variance(pony_updates):.4f}, StdDev={stdev(pony_updates):.4f}")
    print(f"Ormophine: Mean={esq_upd_mean:.4f}s, Variance={variance(esq_updates):.4f}, StdDev={stdev(esq_updates):.4f}")
    print(f"SQLAlchemy: Mean={sal_upd_mean:.4f}s, Variance={variance(sqlalchemy_updates):.4f}, StdDev={stdev(sqlalchemy_updates):.4f}")
    print(f"Peewee: Mean={pee_upd_mean:.4f}s, Variance={variance(peewee_updates):.4f}, StdDev={stdev(peewee_updates):.4f}")

    print( '\n-------------------------   DELETES   ------------------------------')
    print(f"Pony ORM: Mean={pony_del_mean:.4f}s, Variance={variance(pony_deletes):.4f}, StdDev={stdev(pony_deletes):.4f}")
    print(f"Ormophine: Mean={esq_del_mean:.4f}s, Variance={variance(esq_deletes):.4f}, StdDev={stdev(esq_deletes):.4f}")
    print(f"SQLAlchemy: Mean={sal_del_mean:.4f}s, Variance={variance(sqlalchemy_deletes):.4f}, StdDev={stdev(sqlalchemy_deletes):.4f}")
    print(f"Peewee: Mean={pee_del_mean:.4f}s, Variance={variance(peewee_deletes):.4f}, StdDev={stdev(peewee_deletes):.4f}")

    def calculate_percentage_diff(base_time, other_time):
        return ((other_time - base_time) / base_time) * 100

    print(f"\n--- Percentage Differences In Inserts ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_ins_mean, pony_ins_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_ins_mean, sal_ins_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_ins_mean, pee_ins_mean):.2f}%")

    print(f"\n--- Percentage Differences In Updates ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_upd_mean, pony_upd_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_upd_mean, sal_upd_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_upd_mean, pee_upd_mean):.2f}%")

    print(f"\n--- Percentage Differences In Deletes ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_del_mean, pony_del_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_del_mean, sal_del_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_del_mean, pee_del_mean):.2f}%")

    labels = ['Ormophine', 'Pony ORM', 'SQLAlchemy', 'Peewee']
    plot_benchmark_results('Batch Operation Benchmark Results (CUD)', labels, 
                           [esq_ins_mean, pony_ins_mean, sal_ins_mean, pee_ins_mean],
                           [esq_upd_mean, pony_upd_mean, sal_upd_mean, pee_upd_mean],
                           delete_means=[esq_del_mean, pony_del_mean, sal_del_mean, pee_del_mean])
    
    # --- Execution Report ---
    total_queries = repeats * chunk_size
    print("\n" + "="*60)
    print("📊 BENCHMARK EXECUTION REPORT")
    print("="*60)
    print(f"This benchmark evaluates the performance of 4 Python ORMs (Ormophine, Pony ORM, SQLAlchemy, Peewee) on a SQLite database.")
    print(f"\n- Test Type: Batch Operations (Commit executed ONCE at the end of the chunk)")
    print(f"- Operations Tested: CUD (Inserts, Updates, Deletes)")
    print(f"- Total Queries per Operation: {total_queries} queries ({chunk_size} queries/repeat * {repeats} repeats)")
    print(f"- SQLite Configuration: Journal Mode = {journal_mode.upper()}, Synchronous = {synchronous.upper()}")
    print(f"\n📈 HOW TO READ THE CHART:")
    print("The bar chart displays the Mean Execution Time in milliseconds (ms) for processing the batch of queries.")
    print("A LOWER bar indicates BETTER performance (the ORM took less time to process the entire batch).")
    print("Batch operations are significantly faster than single operations because they minimize disk I/O operations.")
    print("Variance and Standard Deviation (shown in the text output above) indicate the stability of the results;")
    print("lower numbers mean the ORM performed consistently across all repetitions.")
    print("\nⓘ NOTE ON METHODOLOGY:")
    print("- PonyORM inherently uses a Unit of Work pattern (Identity Map) for updates, meaning it performs a SELECT")
    print("  followed by an UPDATE inside the loop, unlike direct bulk-update queries used by other ORMs.")
    print("- Ormophine utilizes a batch queue and runs a sync check at the end to ensure operations are fully executed.")
    print("="*60 + "\n")

print('Benchmark functions defined successfully!')