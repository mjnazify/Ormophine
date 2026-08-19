"""Benchmark utilities for comparing MySQL ORM performance (Full CRUD)."""

from time import time, sleep
from Ormophine.Mysql import Driver
from pony.orm import *
from statistics import mean, variance, stdev
import MySQLdb
from gc import collect
from sqlalchemy import create_engine, Column, Integer, String, Float, func
from sqlalchemy.orm import sessionmaker, declarative_base
from peewee import MySQLDatabase, Model, IntegerField, FloatField, TextField, AutoField, fn
from urllib.parse import quote_plus
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.transforms import blended_transform_factory

# MySQL connection configuration
MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'test'
}

def format_qps(value: float) -> str:
    """Format a QPS value into a compact human-readable string (e.g. 12.3k, 1.2M)."""
    if value >= 1_000_000:
        return f'{value / 1_000_000:.2f}M'
    if value >= 1_000:
        return f'{value / 1_000:.1f}k'
    return f'{value:.1f}'


def times_to_qps(times: list[float], num_queries: int) -> list[float]:
    """Convert per-repeat elapsed times (seconds) into per-repeat throughput (queries/second)."""
    return [num_queries / t for t in times if t > 0]


def print_qps_summary(title: str, labels: list[str], operations_data: dict) -> None:
    """Print a compact table of mean QPS per ORM for every operation."""
    print(f"\n--- {title} | Mean Throughput (Queries Per Second) ---")
    header = f"{'Operation':<15}" + "".join(f"{name:>14}" for name in labels)
    print(header)
    print('-' * len(header))
    for op_name, means in operations_data.items():
        print(f"{op_name:<15}" + "".join(f"{format_qps(m):>14}" for m in means))

def sqlalchemy_single_operations(rng):
    """Benchmark single CRUD operations using SQLAlchemy."""
    con = MySQLdb.connect(**MYSQL_CONFIG)
    cursor = con.cursor()
    cursor.execute("DROP TABLE IF EXISTS `TestTable_alchemy`;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS `TestTable_alchemy` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `col_1` INT DEFAULT 5,
            `col_2` VARCHAR(255) DEFAULT 'five',
            `col_3` DOUBLE DEFAULT 5.0
        );
    ''')
    con.commit()
    cursor.close()
    con.close()

    Base = declarative_base()
    class TestTable(Base):
        __tablename__ = 'TestTable_alchemy'
        id = Column(Integer, primary_key=True)  
        col_1 = Column(Integer)
        col_2 = Column(String(255))
        col_3 = Column(Float)

    engine = create_engine(
        f"mysql+mysqldb://{quote_plus(MYSQL_CONFIG['user'])}:{quote_plus(MYSQL_CONFIG['password'])}@{MYSQL_CONFIG['host']}/{MYSQL_CONFIG['database']}",
        echo=False
    )
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
            TestTable.col_1 == i,
            TestTable.col_2 == f'str{i}',
            TestTable.col_3 == i + 0.5
        ).update({
            'col_1': TestTable.col_1 + (TestTable.col_3 * 2),
            'col_2': func.concat('WRAP_', TestTable.col_2, '_PER'),
            'col_3': TestTable.col_3 + (TestTable.col_1 * 2)
        }, synchronize_session=False)
        session.commit()
    elapsed_update = time() - T0

    # Read
    T0 = time()
    for i in range(rng):
        rec = session.query(TestTable).filter(
            TestTable.col_2 == f'WRAP_str{i}_PER'
        ).first()
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

def sqlalchemy_batch_operations(rng):
    """Benchmark batch CRUD operations using SQLAlchemy."""
    con = MySQLdb.connect(**MYSQL_CONFIG)
    cursor = con.cursor()
    cursor.execute("DROP TABLE IF EXISTS `TestTable_alchemy`;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS `TestTable_alchemy` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `col_1` INT DEFAULT 5,
            `col_2` VARCHAR(255) DEFAULT 'five',
            `col_3` DOUBLE DEFAULT 5.0
        );
    ''')
    con.commit()
    cursor.close()
    con.close()

    Base = declarative_base()
    class TestTable(Base):
        __tablename__ = 'TestTable_alchemy'
        id = Column(Integer, primary_key=True)  
        col_1 = Column(Integer)
        col_2 = Column(String(255))
        col_3 = Column(Float)

    engine = create_engine(
        f"mysql+mysqldb://{quote_plus(MYSQL_CONFIG['user'])}:{quote_plus(MYSQL_CONFIG['password'])}@{MYSQL_CONFIG['host']}/{MYSQL_CONFIG['database']}",
        echo=False
    )
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()

    # Batch Create
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
            TestTable.id == i+1,
            TestTable.col_1 == i,
            TestTable.col_2 == f'str{i}',
            TestTable.col_3 == i + 0.5
        ).update({
            'col_1': TestTable.col_1 + (TestTable.col_3 * 2),
            'col_2': func.concat('WRAP_', TestTable.col_2, '_PER'),
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

def peewee_single_operations(rng):
    """Benchmark single CRUD operations using Peewee."""
    con = MySQLdb.connect(**MYSQL_CONFIG)
    cursor = con.cursor()
    cursor.execute("DROP TABLE IF EXISTS `TestTable_peewee`;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS `TestTable_peewee` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `col_1` INT DEFAULT 5,
            `col_2` VARCHAR(255) DEFAULT 'five',
            `col_3` DOUBLE DEFAULT 5.0
        );
    ''')
    con.commit()
    cursor.close()
    con.close()

    db = MySQLDatabase(MYSQL_CONFIG['database'], host=MYSQL_CONFIG['host'], user=MYSQL_CONFIG['user'], password=MYSQL_CONFIG['password'])
    class TestTable(Model):
        id = AutoField()  
        col_1 = IntegerField()
        col_2 = TextField()
        col_3 = FloatField()
        class Meta:
            database = db
            table_name = 'TestTable_peewee'
    db.connect()
    
    # Create
    T0 = time()
    for i in range(rng):
        TestTable.insert(col_1=i, col_2=f'str{i}', col_3=i+0.5).execute()
        db.commit()
    elapsed_insert = time() - T0

    # Update
    T0 = time()
    for i in range(rng):
        TestTable.update(
                col_1=TestTable.col_1 + (TestTable.col_3 * 2),
                col_2=fn.CONCAT('WRAP_', TestTable.col_2, '_PER'),
                col_3=TestTable.col_3 + (TestTable.col_1 * 2)
            ).where(
                (TestTable.col_1 == i) &
                (TestTable.col_2 == f'str{i}') &
                (TestTable.col_3 == i+0.5)
            ).execute()
        db.commit() 
    elapsed_update = time() - T0

    # Read
    T0 = time()
    for i in range(rng):
        record = TestTable.select(
                        TestTable.col_1,
                        TestTable.col_2,
                        TestTable.col_3
                    ).where(
                        TestTable.col_2 == f'WRAP_str{i}_PER' 
                    ).get()
        read_result = (record.col_1, record.col_2, record.col_3)
    elapsed_read = time() - T0

    # Delete
    T0 = time()
    for i in range(rng):
        TestTable.delete().where(TestTable.id == i+1).execute()
        db.commit()
    elapsed_delete = time() - T0

    db.close()
    return elapsed_insert, elapsed_update, elapsed_read, elapsed_delete

def peewee_batch_operations(rng):
    """Benchmark batch CRUD operations using Peewee."""
    con = MySQLdb.connect(**MYSQL_CONFIG)
    cursor = con.cursor()
    cursor.execute("DROP TABLE IF EXISTS `TestTable_peewee`;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS `TestTable_peewee` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `col_1` INT DEFAULT 5,
            `col_2` VARCHAR(255) DEFAULT 'five',
            `col_3` DOUBLE DEFAULT 5.0
        );
    ''')
    con.commit()
    cursor.close()
    con.close()

    db = MySQLDatabase(MYSQL_CONFIG['database'], host=MYSQL_CONFIG['host'], user=MYSQL_CONFIG['user'], password=MYSQL_CONFIG['password'])
    class TestTable(Model):
        id = AutoField()  
        col_1 = IntegerField()
        col_2 = TextField()
        col_3 = FloatField()
        class Meta:
            database = db
            table_name = 'TestTable_peewee'
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
                    col_2=fn.CONCAT('WRAP_', TestTable.col_2, '_PER'),
                    col_3=TestTable.col_3 + (TestTable.col_1 * 2)
                ).where(
                    (TestTable.id == i+1) &
                    (TestTable.col_1 == i) &
                    (TestTable.col_2 == f'str{i}') &
                    (TestTable.col_3 == i+0.5)
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

def pony_single_operations(rng):
    """Benchmark single CRUD operations using PonyORM."""
    con = MySQLdb.connect(**MYSQL_CONFIG)
    cursor = con.cursor()
    cursor.execute("DROP TABLE IF EXISTS `TestTable_pony`;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS `TestTable_pony` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `col_1` INT DEFAULT 5,
            `col_2` VARCHAR(255) DEFAULT 'five',
            `col_3` DOUBLE DEFAULT 5.0
        );
    ''')
    con.commit()
    cursor.close()
    con.close()

    db = Database()
    class TestTable(db.Entity):
        _table_ = 'TestTable_pony'
        id = PrimaryKey(int, auto=True)  
        col_1 = Required(int)
        col_2 = Required(str)
        col_3 = Required(float)
    db.bind(provider='mysql', host=MYSQL_CONFIG['host'], user=MYSQL_CONFIG['user'], passwd=MYSQL_CONFIG['password'], db=MYSQL_CONFIG['database'])
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

def pony_batch_operations(rng):
    """Benchmark batch CRUD operations using PonyORM."""
    con = MySQLdb.connect(**MYSQL_CONFIG)
    cursor = con.cursor()
    cursor.execute("DROP TABLE IF EXISTS `TestTable_pony`;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS `TestTable_pony` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `col_1` INT DEFAULT 5,
            `col_2` VARCHAR(255) DEFAULT 'five',
            `col_3` DOUBLE DEFAULT 5.0
        );
    ''')
    con.commit()
    cursor.close()
    con.close()

    db = Database()
    class TestTable(db.Entity):
        _table_ = 'TestTable_pony'
        id = PrimaryKey(int, auto=True)  
        col_1 = Required(int)
        col_2 = Required(str)
        col_3 = Required(float)
    db.bind(provider='mysql', host=MYSQL_CONFIG['host'], user=MYSQL_CONFIG['user'], passwd=MYSQL_CONFIG['password'], db=MYSQL_CONFIG['database'])
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

def Ormophine_single_operations(rng):
    """Benchmark single CRUD operations using Ormophine ORM."""
    con = MySQLdb.connect(**MYSQL_CONFIG)
    cursor = con.cursor()
    cursor.execute("DROP TABLE IF EXISTS `TestTable_Ormophine`;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS `TestTable_Ormophine` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `col_1` INT DEFAULT 5,
            `col_2` VARCHAR(255) DEFAULT 'five',
            `col_3` DOUBLE DEFAULT 5.0
        );
    ''')
    con.commit()
    cursor.close()
    con.close()

    db = Driver(host=MYSQL_CONFIG['host'], username=MYSQL_CONFIG['user'], password=MYSQL_CONFIG['password'], db_name=MYSQL_CONFIG['database'], port=3306)
    tb = db.TestTable_Ormophine

    # Create
    T0 = time()
    for i in range(rng):
        tb.insert({tb.col_1 : i , tb.col_2 : f'str{i}' , tb.col_3 : i+0.5})
    elapsed_inserts = time() - T0

    # Update
    T0 = time()
    for i in range(rng):
        tb.update(
            {tb.col_1: tb.col_1 + (tb.col_3 * 2), tb.col_2: 'WRAP_' + tb.col_2 + '_PER', tb.col_3: tb.col_3 + (tb.col_1 * 2)},
            where=((tb.col_1 == i) & (tb.col_2 == f'str{i}') & (tb.col_3 == i + 0.5))
        )
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
    elapsed_deletes = time() - T0
    
    db.disconnect()
    return elapsed_inserts, elapsed_updates, elapsed_gets, elapsed_deletes

def Ormophine_batch_operations(rng):
    """Benchmark batch CRUD operations using Ormophine ORM."""
    con = MySQLdb.connect(**MYSQL_CONFIG)
    cursor = con.cursor()
    cursor.execute("DROP TABLE IF EXISTS `TestTable_Ormophine`;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS `TestTable_Ormophine` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `col_1` INT DEFAULT 5,
            `col_2` VARCHAR(255) DEFAULT 'five',
            `col_3` DOUBLE DEFAULT 5.0
        );
    ''')
    con.commit()
    cursor.close()
    con.close()

    db = Driver(host=MYSQL_CONFIG['host'], username=MYSQL_CONFIG['user'], password=MYSQL_CONFIG['password'], db_name=MYSQL_CONFIG['database'], port=3306)
    tb = db.TestTable_Ormophine

    # Batch Create
    T0 = time()
    batch = tb.batch()
    for i in range(rng):
        batch.insert({tb.col_1 : i , tb.col_2 : f'str{i}' , tb.col_3 : i+0.5})
    batch.run()
    elapsed_inserts = time() - T0

    # Batch Update
    T0 = time()
    batch = tb.batch()
    for i in range(rng):
        batch.update({tb.col_1 : tb.col_1+(tb.col_3*2) , tb.col_2 : 'WRAP_'+tb.col_2+'_PER' , tb.col_3 : tb.col_3 + (tb.col_1*2)} , (tb.col_1 == i) & (tb.col_2 == f'str{i}') & (tb.col_3 == i+0.5))
    batch.run()
    elapsed_updates = time() - T0

    # Batch Delete
    T0 = time()
    batch = tb.batch()
    for i in range(rng):
        batch.delete_row(where=(tb.id == i+1))
    batch.run()
    elapsed_deletes = time() - T0
    
    db.disconnect()
    return elapsed_inserts, elapsed_updates, elapsed_deletes

def plot_benchmark_results(title_prefix, labels, operations_data, queries_per_repeat: int):
    """Generate separate bar charts comparing ORM throughput (queries per second)."""
    base_index = 0  # Ormophine is the first label
    colors = ['#4CAF50', '#FF9800', '#2196F3', '#F44336']  # Green, Orange, Blue, Red

    for op_name, qps_means in operations_data.items():
        # Create a new figure for each operation
        fig, ax = plt.subplots(figsize=(8, 7))

        bars = ax.bar(labels, qps_means, color=colors[:len(labels)], width=0.5)
        ax.set_ylabel('Queries Per Second (QPS) - Higher is Better', fontsize=12)
        ax.set_title(f'{title_prefix} - {op_name}\n({queries_per_repeat:,} queries per repeat)',
                     fontsize=14, fontweight='bold')
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        # Set y-axis limit to make room for labels on top
        max_val = max(qps_means) if qps_means else 0
        ax.set_ylim(0, max_val * 1.2)

        # Annotate exact QPS values on top of bars
        for bar in bars:
            height = bar.get_height()
            ax.annotate(format_qps(height),
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 5),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=11, fontweight='bold')

        # Annotate percentage difference below x-axis
        trans = blended_transform_factory(ax.transData, ax.transAxes)
        base_qps = qps_means[base_index]

        for i, label in enumerate(labels):
            if i == base_index:
                ax.text(i, -0.15, "Ormophine\n(Baseline)", ha='center', va='top',
                        transform=trans, fontsize=10, fontweight='bold', color='#4CAF50')
            else:
                other_qps = qps_means[i]
                if other_qps > 0:
                    # Positive diff -> Ormophine has higher throughput -> faster
                    diff = ((base_qps - other_qps) / other_qps) * 100

                    if abs(diff) < 5:
                        text, color = f"{diff:.1f}%\nalmost the same\nas {label}", '#808080'
                    elif diff > 0:
                        text, color = f"{diff:.1f}% faster\nthan {label}", '#2E7D32'
                    else:
                        text, color = f"{abs(diff):.1f}% slower\nthan {label}", '#C62828'

                    ax.text(i, -0.15, text, ha='center', va='top',
                            transform=trans, fontsize=10, fontweight='bold', color=color)

        plt.subplots_adjust(bottom=0.25)  # Make room for two lines of text below
        plt.show()

def run_single_operation_benchmark(repeats: int, warmup_repeats: int = 3, chunk_size: int = 10):
    """Run the single-operation CRUD benchmark for all ORMs (reported as QPS)."""
    pony_inserts, esq_inserts, sqlalchemy_inserts, peewee_inserts = [], [], [], []
    pony_updates, esq_updates, sqlalchemy_updates, peewee_updates = [], [], [], []
    pony_reads, esq_reads, sqlalchemy_reads, peewee_reads = [], [], [], []
    pony_deletes, esq_deletes, sqlalchemy_deletes, peewee_deletes = [], [], [], []

    print('\n--- Starting Single Operation Benchmark ---')

    for _ in tqdm(range(warmup_repeats), desc="Warmup Phase (Single Ops)", unit="run", leave=False):
        collect(); sleep(0.1)
        pony_single_operations(chunk_size)
        Ormophine_single_operations(chunk_size)
        sqlalchemy_single_operations(chunk_size)
        peewee_single_operations(chunk_size)

    print('################## RUNNING BENCHMARK ##################')

    for _ in tqdm(range(repeats), desc="Benchmarking Single Ops", unit="run"):
        collect(); sleep(0.1)

        pon_ins, pon_upd, pon_rd, pon_del = pony_single_operations(chunk_size)
        sq_ins, sq_upd, sq_rd, sq_del = Ormophine_single_operations(chunk_size)
        alch_ins, alch_upd, alch_rd, alch_del = sqlalchemy_single_operations(chunk_size)
        pee_ins, pee_upd, pee_rd, pee_del = peewee_single_operations(chunk_size)

        pony_inserts.append(pon_ins); esq_inserts.append(sq_ins); sqlalchemy_inserts.append(alch_ins); peewee_inserts.append(pee_ins)
        pony_updates.append(pon_upd); esq_updates.append(sq_upd); sqlalchemy_updates.append(alch_upd); peewee_updates.append(pee_upd)
        pony_reads.append(pon_rd); esq_reads.append(sq_rd); sqlalchemy_reads.append(alch_rd); peewee_reads.append(pee_rd)
        pony_deletes.append(pon_del); esq_deletes.append(sq_del); sqlalchemy_deletes.append(alch_del); peewee_deletes.append(pee_del)

    # ---------- Convert elapsed times (s) to throughput (queries/second) ----------
    pony_ins_qps = times_to_qps(pony_inserts, chunk_size); pony_upd_qps = times_to_qps(pony_updates, chunk_size)
    pony_rd_qps  = times_to_qps(pony_reads, chunk_size);   pony_del_qps = times_to_qps(pony_deletes, chunk_size)
    esq_ins_qps  = times_to_qps(esq_inserts, chunk_size);  esq_upd_qps  = times_to_qps(esq_updates, chunk_size)
    esq_rd_qps   = times_to_qps(esq_reads, chunk_size);    esq_del_qps  = times_to_qps(esq_deletes, chunk_size)
    sal_ins_qps  = times_to_qps(sqlalchemy_inserts, chunk_size); sal_upd_qps = times_to_qps(sqlalchemy_updates, chunk_size)
    sal_rd_qps   = times_to_qps(sqlalchemy_reads, chunk_size);    sal_del_qps = times_to_qps(sqlalchemy_deletes, chunk_size)
    pee_ins_qps  = times_to_qps(peewee_inserts, chunk_size);     pee_upd_qps = times_to_qps(peewee_updates, chunk_size)
    pee_rd_qps   = times_to_qps(peewee_reads, chunk_size);       pee_del_qps = times_to_qps(peewee_deletes, chunk_size)

    pony_ins_mean = mean(pony_ins_qps); pony_upd_mean = mean(pony_upd_qps); pony_rd_mean = mean(pony_rd_qps); pony_del_mean = mean(pony_del_qps)
    esq_ins_mean  = mean(esq_ins_qps);  esq_upd_mean  = mean(esq_upd_qps);  esq_rd_mean  = mean(esq_rd_qps);  esq_del_mean  = mean(esq_del_qps)
    sal_ins_mean  = mean(sal_ins_qps);  sal_upd_mean  = mean(sal_upd_qps);  sal_rd_mean  = mean(sal_rd_qps);  sal_del_mean  = mean(sal_del_qps)
    pee_ins_mean  = mean(pee_ins_qps);  pee_upd_mean  = mean(pee_upd_qps);  pee_rd_mean  = mean(pee_rd_qps);  pee_del_mean  = mean(pee_del_qps)

    print(f"\n--- Throughput Statistics (N={repeats}, {chunk_size} queries per repeat) ---")

    print('\n-------------------------   INSERTS   ------------------------------')
    print(f"Pony ORM: Mean={pony_ins_mean:.2f} QPS, Variance={variance(pony_ins_qps):.2f}, StdDev={stdev(pony_ins_qps):.2f}")
    print(f"Ormophine: Mean={esq_ins_mean:.2f} QPS, Variance={variance(esq_ins_qps):.2f}, StdDev={stdev(esq_ins_qps):.2f}")
    print(f"SQLAlchemy: Mean={sal_ins_mean:.2f} QPS, Variance={variance(sal_ins_qps):.2f}, StdDev={stdev(sal_ins_qps):.2f}")
    print(f"Peewee: Mean={pee_ins_mean:.2f} QPS, Variance={variance(pee_ins_qps):.2f}, StdDev={stdev(pee_ins_qps):.2f}")

    print('\n-------------------------   UPDATES   ------------------------------')
    print(f"Pony ORM: Mean={pony_upd_mean:.2f} QPS, Variance={variance(pony_upd_qps):.2f}, StdDev={stdev(pony_upd_qps):.2f}")
    print(f"Ormophine: Mean={esq_upd_mean:.2f} QPS, Variance={variance(esq_upd_qps):.2f}, StdDev={stdev(esq_upd_qps):.2f}")
    print(f"SQLAlchemy: Mean={sal_upd_mean:.2f} QPS, Variance={variance(sal_upd_qps):.2f}, StdDev={stdev(sal_upd_qps):.2f}")
    print(f"Peewee: Mean={pee_upd_mean:.2f} QPS, Variance={variance(pee_upd_qps):.2f}, StdDev={stdev(pee_upd_qps):.2f}")

    print('\n-------------------------   READS   ------------------------------')
    print(f"Pony ORM: Mean={pony_rd_mean:.2f} QPS, Variance={variance(pony_rd_qps):.2f}, StdDev={stdev(pony_rd_qps):.2f}")
    print(f"Ormophine: Mean={esq_rd_mean:.2f} QPS, Variance={variance(esq_rd_qps):.2f}, StdDev={stdev(esq_rd_qps):.2f}")
    print(f"SQLAlchemy: Mean={sal_rd_mean:.2f} QPS, Variance={variance(sal_rd_qps):.2f}, StdDev={stdev(sal_rd_qps):.2f}")
    print(f"Peewee: Mean={pee_rd_mean:.2f} QPS, Variance={variance(pee_rd_qps):.2f}, StdDev={stdev(pee_rd_qps):.2f}")

    print('\n-------------------------   DELETES   ------------------------------')
    print(f"Pony ORM: Mean={pony_del_mean:.2f} QPS, Variance={variance(pony_del_qps):.2f}, StdDev={stdev(pony_del_qps):.2f}")
    print(f"Ormophine: Mean={esq_del_mean:.2f} QPS, Variance={variance(esq_del_qps):.2f}, StdDev={stdev(esq_del_qps):.2f}")
    print(f"SQLAlchemy: Mean={sal_del_mean:.2f} QPS, Variance={variance(sal_del_qps):.2f}, StdDev={stdev(sal_del_qps):.2f}")
    print(f"Peewee: Mean={pee_del_mean:.2f} QPS, Variance={variance(pee_del_qps):.2f}, StdDev={stdev(pee_del_qps):.2f}")

    def calculate_percentage_diff(base_qps: float, other_qps: float) -> float:
        """Positive -> Ormophine executes more queries per second -> faster."""
        return ((base_qps - other_qps) / other_qps) * 100

    print("\n--- Percentage Differences In Inserts (throughput) ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_ins_mean, pony_ins_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_ins_mean, sal_ins_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_ins_mean, pee_ins_mean):.2f}%")

    print("\n--- Percentage Differences In Updates (throughput) ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_upd_mean, pony_upd_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_upd_mean, sal_upd_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_upd_mean, pee_upd_mean):.2f}%")

    print("\n--- Percentage Differences In Reads (throughput) ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_rd_mean, pony_rd_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_rd_mean, sal_rd_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_rd_mean, pee_rd_mean):.2f}%")

    print("\n--- Percentage Differences In Deletes (throughput) ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_del_mean, pony_del_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_del_mean, sal_del_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_del_mean, pee_del_mean):.2f}%")

    labels = ['Ormophine', 'Pony ORM', 'SQLAlchemy', 'Peewee']
    operations_data = {
        'Inserts': [esq_ins_mean, pony_ins_mean, sal_ins_mean, pee_ins_mean],
        'Updates': [esq_upd_mean, pony_upd_mean, sal_upd_mean, pee_upd_mean],
        'Reads':   [esq_rd_mean, pony_rd_mean, sal_rd_mean, pee_rd_mean],
        'Deletes': [esq_del_mean, pony_del_mean, sal_del_mean, pee_del_mean]
    }
    print_qps_summary('MySQL Single Operation Benchmark', labels, operations_data)
    plot_benchmark_results('MySQL Single Operation Benchmark', labels, operations_data, queries_per_repeat=chunk_size)

    # --- Execution Report ---
    total_queries = repeats * chunk_size
    print("\n" + "="*60)
    print("📊 BENCHMARK EXECUTION REPORT (THROUGHPUT / QPS)")
    print("="*60)
    print("This benchmark evaluates the performance of 4 Python ORMs (Ormophine, Pony ORM, SQLAlchemy, Peewee) on a MySQL database.")
    print(f"\n- Test Type: Single Operations (Commit executed after EVERY query)")
    print(f"- Operations Tested: Full CRUD (Inserts, Updates, Reads, Deletes)")
    print(f"- Queries per Operation per Repeat: {chunk_size:,}")
    print(f"- Total Queries per Operation: {total_queries:,} ({chunk_size:,} queries/repeat x {repeats} repeats)")
    print(f"- Metric: QPS = queries / elapsed_seconds (mean of per-repeat QPS)")
    print(f"- MySQL Server: {MYSQL_CONFIG['host']} | Database: {MYSQL_CONFIG['database']}")
    print(f"\n📈 HOW TO READ THE CHARTS:")
    print("Each chart displays the Mean Throughput in Queries Per Second (QPS) for a specific operation.")
    print("A HIGHER bar indicates BETTER performance (the ORM executed more queries per second).")
    print("Below each chart, the percentage difference shows how much faster Ormophine is compared to the other ORMs.")
    print("="*60 + "\n")

def run_batch_operation_benchmark(repeats: int, warmup_repeats: int = 3, chunk_size: int = 10000):
    """Run the batch-operation CUD benchmark for all ORMs (reported as QPS)."""
    pony_inserts, esq_inserts, sqlalchemy_inserts, peewee_inserts = [], [], [], []
    pony_updates, esq_updates, sqlalchemy_updates, peewee_updates = [], [], [], []
    pony_deletes, esq_deletes, sqlalchemy_deletes, peewee_deletes = [], [], [], []

    print('\n--- Starting Batch Operation Benchmark ---')

    for _ in tqdm(range(warmup_repeats), desc="Warmup Phase (Batch Ops)", unit="run", leave=False):
        collect(); sleep(0.1)
        pony_batch_operations(chunk_size)
        Ormophine_batch_operations(chunk_size)
        sqlalchemy_batch_operations(chunk_size)
        peewee_batch_operations(chunk_size)

    print('################## RUNNING BENCHMARK ##################')

    for _ in tqdm(range(repeats), desc="Benchmarking Batch Ops", unit="run"):
        collect(); sleep(0.1)

        pon_ins, pon_upd, pon_del = pony_batch_operations(chunk_size)
        sq_ins, sq_upd, sq_del = Ormophine_batch_operations(chunk_size)
        alch_ins, alch_upd, alch_del = sqlalchemy_batch_operations(chunk_size)
        pee_ins, pee_upd, pee_del = peewee_batch_operations(chunk_size)

        pony_inserts.append(pon_ins); esq_inserts.append(sq_ins); sqlalchemy_inserts.append(alch_ins); peewee_inserts.append(pee_ins)
        pony_updates.append(pon_upd); esq_updates.append(sq_upd); sqlalchemy_updates.append(alch_upd); peewee_updates.append(pee_upd)
        pony_deletes.append(pon_del); esq_deletes.append(sq_del); sqlalchemy_deletes.append(alch_del); peewee_deletes.append(pee_del)

    # ---------- Convert elapsed times (s) to throughput (queries/second) ----------
    pony_ins_qps = times_to_qps(pony_inserts, chunk_size); pony_upd_qps = times_to_qps(pony_updates, chunk_size); pony_del_qps = times_to_qps(pony_deletes, chunk_size)
    esq_ins_qps  = times_to_qps(esq_inserts, chunk_size);  esq_upd_qps  = times_to_qps(esq_updates, chunk_size);  esq_del_qps  = times_to_qps(esq_deletes, chunk_size)
    sal_ins_qps  = times_to_qps(sqlalchemy_inserts, chunk_size); sal_upd_qps = times_to_qps(sqlalchemy_updates, chunk_size); sal_del_qps = times_to_qps(sqlalchemy_deletes, chunk_size)
    pee_ins_qps  = times_to_qps(peewee_inserts, chunk_size);     pee_upd_qps = times_to_qps(peewee_updates, chunk_size);     pee_del_qps = times_to_qps(peewee_deletes, chunk_size)

    pony_ins_mean = mean(pony_ins_qps); pony_upd_mean = mean(pony_upd_qps); pony_del_mean = mean(pony_del_qps)
    esq_ins_mean  = mean(esq_ins_qps);  esq_upd_mean  = mean(esq_upd_qps);  esq_del_mean  = mean(esq_del_qps)
    sal_ins_mean  = mean(sal_ins_qps);  sal_upd_mean  = mean(sal_upd_qps);  sal_del_mean  = mean(sal_del_qps)
    pee_ins_mean  = mean(pee_ins_qps);  pee_upd_mean  = mean(pee_upd_qps);  pee_del_mean  = mean(pee_del_qps)

    print(f"\n--- Throughput Statistics (N={repeats}, {chunk_size} queries per repeat) ---")

    print('\n-------------------------   INSERTS   ------------------------------')
    print(f"Pony ORM: Mean={pony_ins_mean:.2f} QPS, Variance={variance(pony_ins_qps):.2f}, StdDev={stdev(pony_ins_qps):.2f}")
    print(f"Ormophine: Mean={esq_ins_mean:.2f} QPS, Variance={variance(esq_ins_qps):.2f}, StdDev={stdev(esq_ins_qps):.2f}")
    print(f"SQLAlchemy: Mean={sal_ins_mean:.2f} QPS, Variance={variance(sal_ins_qps):.2f}, StdDev={stdev(sal_ins_qps):.2f}")
    print(f"Peewee: Mean={pee_ins_mean:.2f} QPS, Variance={variance(pee_ins_qps):.2f}, StdDev={stdev(pee_ins_qps):.2f}")

    print('\n-------------------------   UPDATES   ------------------------------')
    print(f"Pony ORM: Mean={pony_upd_mean:.2f} QPS, Variance={variance(pony_upd_qps):.2f}, StdDev={stdev(pony_upd_qps):.2f}")
    print(f"Ormophine: Mean={esq_upd_mean:.2f} QPS, Variance={variance(esq_upd_qps):.2f}, StdDev={stdev(esq_upd_qps):.2f}")
    print(f"SQLAlchemy: Mean={sal_upd_mean:.2f} QPS, Variance={variance(sal_upd_qps):.2f}, StdDev={stdev(sal_upd_qps):.2f}")
    print(f"Peewee: Mean={pee_upd_mean:.2f} QPS, Variance={variance(pee_upd_qps):.2f}, StdDev={stdev(pee_upd_qps):.2f}")

    print('\n-------------------------   DELETES   ------------------------------')
    print(f"Pony ORM: Mean={pony_del_mean:.2f} QPS, Variance={variance(pony_del_qps):.2f}, StdDev={stdev(pony_del_qps):.2f}")
    print(f"Ormophine: Mean={esq_del_mean:.2f} QPS, Variance={variance(esq_del_qps):.2f}, StdDev={stdev(esq_del_qps):.2f}")
    print(f"SQLAlchemy: Mean={sal_del_mean:.2f} QPS, Variance={variance(sal_del_qps):.2f}, StdDev={stdev(sal_del_qps):.2f}")
    print(f"Peewee: Mean={pee_del_mean:.2f} QPS, Variance={variance(pee_del_qps):.2f}, StdDev={stdev(pee_del_qps):.2f}")

    def calculate_percentage_diff(base_qps: float, other_qps: float) -> float:
        """Positive -> Ormophine executes more queries per second -> faster."""
        return ((base_qps - other_qps) / other_qps) * 100

    print("\n--- Percentage Differences In Inserts (throughput) ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_ins_mean, pony_ins_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_ins_mean, sal_ins_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_ins_mean, pee_ins_mean):.2f}%")

    print("\n--- Percentage Differences In Updates (throughput) ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_upd_mean, pony_upd_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_upd_mean, sal_upd_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_upd_mean, pee_upd_mean):.2f}%")

    print("\n--- Percentage Differences In Deletes (throughput) ---")
    print(f"Ormophine vs Pony ORM: {calculate_percentage_diff(esq_del_mean, pony_del_mean):.2f}%")
    print(f"Ormophine vs SQLAlchemy: {calculate_percentage_diff(esq_del_mean, sal_del_mean):.2f}%")
    print(f"Ormophine vs Peewee: {calculate_percentage_diff(esq_del_mean, pee_del_mean):.2f}%")

    labels = ['Ormophine', 'Pony ORM', 'SQLAlchemy', 'Peewee']
    operations_data = {
        'Batch Inserts': [esq_ins_mean, pony_ins_mean, sal_ins_mean, pee_ins_mean],
        'Batch Updates': [esq_upd_mean, pony_upd_mean, sal_upd_mean, pee_upd_mean],
        'Batch Deletes': [esq_del_mean, pony_del_mean, sal_del_mean, pee_del_mean]
    }
    print_qps_summary('MySQL Batch Operation Benchmark', labels, operations_data)
    plot_benchmark_results('MySQL Batch Operation Benchmark', labels, operations_data, queries_per_repeat=chunk_size)

    # --- Execution Report ---
    total_queries = repeats * chunk_size
    print("\n" + "="*60)
    print("📊 BENCHMARK EXECUTION REPORT (THROUGHPUT / QPS)")
    print("="*60)
    print("This benchmark evaluates the performance of 4 Python ORMs (Ormophine, Pony ORM, SQLAlchemy, Peewee) on a MySQL database.")
    print(f"\n- Test Type: Batch Operations (Commit executed ONCE at the end of the chunk)")
    print(f"- Operations Tested: CUD (Inserts, Updates, Deletes)")
    print(f"- Queries per Operation per Repeat: {chunk_size:,}")
    print(f"- Total Queries per Operation: {total_queries:,} ({chunk_size:,} queries/repeat x {repeats} repeats)")
    print(f"- Metric: QPS = queries / elapsed_seconds (mean of per-repeat QPS)")
    print(f"- MySQL Server: {MYSQL_CONFIG['host']} | Database: {MYSQL_CONFIG['database']}")
    print(f"\n📈 HOW TO READ THE CHARTS:")
    print("Each chart displays the Mean Throughput in Queries Per Second (QPS) for processing the batch of queries.")
    print("A HIGHER bar indicates BETTER performance (the ORM executed more queries per second).")
    print("Below each chart, the percentage difference shows how much faster Ormophine is compared to the other ORMs.")
    print("="*60 + "\n")
    
print('Benchmark functions defined successfully!')