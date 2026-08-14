import os
import pytest
from Ormophine import Postgresql

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "1234")
PG_DB_NAME = os.getenv("PG_DB_NAME", "test_orm_db")

@pytest.fixture(scope="module")
def driver():
    try:
        drv = Postgresql.Driver(
            host=PG_HOST,
            port=PG_PORT,
            username=PG_USER,
            password=PG_PASSWORD,
            db_name=PG_DB_NAME,
            create_new_db=True
        )
    except:
        drv = Postgresql.Driver(
            host=PG_HOST,
            port=PG_PORT,
            username=PG_USER,
            password=PG_PASSWORD,
            db_name=PG_DB_NAME
        )
    
    schema = Postgresql.TableStructure('test_table')
    schema.add_column('name', Postgresql.DataTypes.VARCHAR(100))
    schema.add_column('age', Postgresql.DataTypes.INTEGER())
    schema.add_column('score', Postgresql.DataTypes.REAL())
    
    try:
        drv.custom_execute('DROP TABLE IF EXISTS test_table;')
    except:
        pass
        
    drv.create_table(schema)
    
    yield drv
    
    try:
        drv.custom_execute('DROP TABLE IF EXISTS test_table;')
    except:
        pass
    drv.disconnect()

@pytest.fixture(scope="module")
def table(driver):
    return driver.test_table

@pytest.fixture
def col_str(table):
    return table.name

@pytest.fixture
def col_int(table):
    return table.age

@pytest.fixture
def col_float(table):
    return table.score

@pytest.fixture
def op_str(col_str):
    return col_str + 'op_str_param'

@pytest.fixture
def op_int(col_int):
    return col_int + 1

@pytest.fixture
def op_float(col_float):
    return col_float + 1.5

@pytest.fixture
def lit_str():
    return 'text'

@pytest.fixture
def lit_int():
    return 10

@pytest.fixture
def lit_float():
    return 10.5

# ==========================================
# Tests
# ==========================================

def test_01(col_str):
    res = col_str + col_str
    assert res._output[0] == '("test_table"."name" || "test_table"."name")'
    assert res._output[1] == []

def test_02(col_str, col_int):
    res = col_str + col_int
    assert res._output[0] == '("test_table"."name" || "test_table"."age")'
    assert res._output[1] == []

def test_03(col_str, col_float):
    res = col_str + col_float
    assert res._output[0] == '("test_table"."name" || "test_table"."score")'
    assert res._output[1] == []

def test_04(col_str, op_str):
    res = col_str + op_str
    assert res._output[0] == '("test_table"."name" || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param']

def test_05(col_str, op_int):
    res = col_str + op_int
    assert res._output[0] == '("test_table"."name" || ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_06(col_str, op_float):
    res = col_str + op_float
    assert res._output[0] == '("test_table"."name" || ("test_table"."score" + %s))'
    assert res._output[1] == [1.5]

def test_07(col_str, lit_str):
    res = col_str + lit_str
    assert res._output[0] == '("test_table"."name" || %s)'
    assert res._output[1] == ['text']

def test_08(col_str, lit_int):
    res = col_str + lit_int
    assert res._output[0] == '("test_table"."name" || %s)'
    assert res._output[1] == [10]

def test_09(col_str, lit_float):
    res = col_str + lit_float
    assert res._output[0] == '("test_table"."name" || %s)'
    assert res._output[1] == [10.5]

def test_10(col_str):
    res = col_str - col_str
    assert res._output[0] == '("test_table"."name" - "test_table"."name")'
    assert res._output[1] == []

def test_11(col_str, col_int):
    res = col_str - col_int
    assert res._output[0] == '("test_table"."name" - "test_table"."age")'
    assert res._output[1] == []

def test_12(col_str, col_float):
    res = col_str - col_float
    assert res._output[0] == '("test_table"."name" - "test_table"."score")'
    assert res._output[1] == []

def test_13(col_str, op_str):
    res = col_str - op_str
    assert res._output[0] == '("test_table"."name" - ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param']

def test_14(col_str, op_int):
    res = col_str - op_int
    assert res._output[0] == '("test_table"."name" - ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_15(col_str, op_float):
    res = col_str - op_float
    assert res._output[0] == '("test_table"."name" - ("test_table"."score" + %s))'
    assert res._output[1] == [1.5]

def test_16(col_str, lit_str):
    res = col_str - lit_str
    assert res._output[0] == '("test_table"."name" - %s)'
    assert res._output[1] == ['text']

def test_17(col_str, lit_int):
    res = col_str - lit_int
    assert res._output[0] == '("test_table"."name" - %s)'
    assert res._output[1] == [10]

def test_18(col_str, lit_float):
    res = col_str - lit_float
    assert res._output[0] == '("test_table"."name" - %s)'
    assert res._output[1] == [10.5]

def test_19(lit_str, col_str):
    res = lit_str + col_str
    assert res._output[0] == '(%s || "test_table"."name")'
    assert res._output[1] == ['text']

def test_20(lit_int, col_str):
    res = lit_int + col_str
    assert res._output[0] == '(%s || "test_table"."name")'
    assert res._output[1] == [10]

def test_21(lit_float, col_str):
    res = lit_float + col_str
    assert res._output[0] == '(%s || "test_table"."name")'
    assert res._output[1] == [10.5]

def test_22(lit_str, col_str):
    res = lit_str - col_str
    assert res._output[0] == '(%s - "test_table"."name")'
    assert res._output[1] == ['text']

def test_23(lit_int, col_str):
    res = lit_int - col_str
    assert res._output[0] == '(%s - "test_table"."name")'
    assert res._output[1] == [10]

def test_24(lit_float, col_str):
    res = lit_float - col_str
    assert res._output[0] == '(%s - "test_table"."name")'
    assert res._output[1] == [10.5]

def test_25(col_str):
    res = col_str + (col_str + col_str)
    assert res._output[0] == '("test_table"."name" || ("test_table"."name" || "test_table"."name"))'
    assert res._output[1] == []

def test_26(col_str, col_int):
    res = col_str + (col_int + col_int)
    assert res._output[0] == '("test_table"."name" || ("test_table"."age" + "test_table"."age"))'
    assert res._output[1] == []

def test_27(col_str, col_float):
    res = col_str + (col_float + col_float)
    assert res._output[0] == '("test_table"."name" || ("test_table"."score" + "test_table"."score"))'
    assert res._output[1] == []

def test_28(col_str):
    res = col_str - (col_str - col_str)
    assert res._output[0] == '("test_table"."name" - ("test_table"."name" - "test_table"."name"))'
    assert res._output[1] == []

def test_29(col_str, col_int):
    res = col_str - (col_int - col_int)
    assert res._output[0] == '("test_table"."name" - ("test_table"."age" - "test_table"."age"))'
    assert res._output[1] == []

def test_30(col_str, col_float):
    res = col_str - (col_float - col_float)
    assert res._output[0] == '("test_table"."name" - ("test_table"."score" - "test_table"."score"))'
    assert res._output[1] == []

def test_31(col_str):
    res = (col_str + col_str) + col_str
    assert res._output[0] == '(("test_table"."name" || "test_table"."name") || "test_table"."name")'
    assert res._output[1] == []

def test_32(col_str, lit_str):
    res = (col_str + col_str) + lit_str
    assert res._output[0] == '(("test_table"."name" || "test_table"."name") || %s)'
    assert res._output[1] == ['text']

def test_33(col_str):
    res = (col_str + col_str) - col_str
    assert res._output[0] == '(("test_table"."name" || "test_table"."name") - "test_table"."name")'
    assert res._output[1] == []

def test_34(col_str, lit_str):
    res = (col_str + col_str) - lit_str
    assert res._output[0] == '(("test_table"."name" || "test_table"."name") - %s)'
    assert res._output[1] == ['text']

def test_35(lit_str, col_str):
    res = lit_str + (col_str + col_str)
    assert res._output[0] == '(%s || ("test_table"."name" || "test_table"."name"))'
    assert res._output[1] == ['text']

def test_36(lit_str, col_str):
    res = lit_str - (col_str - col_str)
    assert res._output[0] == '(%s - ("test_table"."name" - "test_table"."name"))'
    assert res._output[1] == ['text']

def test_37(col_str, col_int):
    res = (col_str + col_int) + col_str
    assert res._output[0] == '(("test_table"."name" || "test_table"."age") || "test_table"."name")'
    assert res._output[1] == []

def test_38(col_str, lit_int):
    res = (col_str + lit_int) + col_str
    assert res._output[0] == '(("test_table"."name" || %s) || "test_table"."name")'
    assert res._output[1] == [10]

def test_39(col_str, lit_str):
    res = col_str + (col_str + lit_str)
    assert res._output[0] == '("test_table"."name" || ("test_table"."name" || %s))'
    assert res._output[1] == ['text']

def test_40(col_str, lit_str):
    res = col_str + (lit_str + col_str)
    assert res._output[0] == '("test_table"."name" || (%s || "test_table"."name"))'
    assert res._output[1] == ['text']

def test_41(col_str):
    res = (col_str + col_str) + (col_str + col_str)
    assert res._output[0] == '(("test_table"."name" || "test_table"."name") || ("test_table"."name" || "test_table"."name"))'
    assert res._output[1] == []

def test_42(col_str):
    res = (col_str + col_str) - (col_str - col_str)
    assert res._output[0] == '(("test_table"."name" || "test_table"."name") - ("test_table"."name" - "test_table"."name"))'
    assert res._output[1] == []

def test_43(lit_str, col_str):
    res = lit_str + (col_str + col_str)
    assert res._output[0] == '(%s || ("test_table"."name" || "test_table"."name"))'
    assert res._output[1] == ['text']

def test_44(lit_int, col_str, col_int):
    res = lit_int + (col_str + col_int)
    assert res._output[0] == '(%s || ("test_table"."name" || "test_table"."age"))'
    assert res._output[1] == [10]

def test_45(lit_float, col_str, col_float):
    res = lit_float + (col_str + col_float)
    assert res._output[0] == '(%s || ("test_table"."name" || "test_table"."score"))'
    assert res._output[1] == [10.5]

def test_46(col_str, op_str):
    res = (col_str + col_str) + op_str
    assert res._output[0] == '(("test_table"."name" || "test_table"."name") || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param']

def test_47(col_str, op_int):
    res = (col_str + col_str) + op_int
    assert res._output[0] == '(("test_table"."name" || "test_table"."name") || ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_48(col_str, op_float):
    res = (col_str + col_str) + op_float
    assert res._output[0] == '(("test_table"."name" || "test_table"."name") || ("test_table"."score" + %s))'
    assert res._output[1] == [1.5]

def test_49(op_str, col_str):
    res = op_str + (col_str + col_str)
    assert res._output[0] == '(("test_table"."name" || %s) || ("test_table"."name" || "test_table"."name"))'
    assert res._output[1] == ['op_str_param']

def test_50(op_str, col_str):
    res = op_str - (col_str - col_str)
    assert res._output[0] == '(("test_table"."name" || %s) - ("test_table"."name" - "test_table"."name"))'
    assert res._output[1] == ['op_str_param']

def test_51(col_int, col_str):
    res = col_int + col_str
    assert res._output[0] == '("test_table"."age" || "test_table"."name")'
    assert res._output[1] == []

def test_52(col_int):
    res = col_int + col_int
    assert res._output[0] == '("test_table"."age" + "test_table"."age")'
    assert res._output[1] == []

def test_53(col_int, col_float):
    res = col_int + col_float
    assert res._output[0] == '("test_table"."age" + "test_table"."score")'
    assert res._output[1] == []

def test_54(col_int, op_str):
    res = col_int + op_str
    assert res._output[0] == '("test_table"."age" || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param']

def test_55(col_int, op_int):
    res = col_int + op_int
    assert res._output[0] == '("test_table"."age" + ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_56(col_int, op_float):
    res = col_int + op_float
    assert res._output[0] == '("test_table"."age" + ("test_table"."score" + %s))'
    assert res._output[1] == [1.5]

def test_57(col_int, lit_str):
    res = col_int + lit_str
    assert res._output[0] == '("test_table"."age" || %s)'
    assert res._output[1] == ['text']

def test_58(col_int, lit_int):
    res = col_int + lit_int
    assert res._output[0] == '("test_table"."age" + %s)'
    assert res._output[1] == [10]

def test_59(col_int, lit_float):
    res = col_int + lit_float
    assert res._output[0] == '("test_table"."age" + %s)'
    assert res._output[1] == [10.5]

def test_60(col_int, col_str):
    res = col_int - col_str
    assert res._output[0] == '("test_table"."age" - "test_table"."name")'
    assert res._output[1] == []

def test_61(col_int):
    res = col_int - col_int
    assert res._output[0] == '("test_table"."age" - "test_table"."age")'
    assert res._output[1] == []

def test_62(col_int, col_float):
    res = col_int - col_float
    assert res._output[0] == '("test_table"."age" - "test_table"."score")'
    assert res._output[1] == []

def test_63(col_int, op_str):
    res = col_int - op_str
    assert res._output[0] == '("test_table"."age" - ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param']

def test_64(col_int, op_int):
    res = col_int - op_int
    assert res._output[0] == '("test_table"."age" - ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_65(col_int, op_float):
    res = col_int - op_float
    assert res._output[0] == '("test_table"."age" - ("test_table"."score" + %s))'
    assert res._output[1] == [1.5]

def test_66(col_int, lit_str):
    res = col_int - lit_str
    assert res._output[0] == '("test_table"."age" - %s)'
    assert res._output[1] == ['text']

def test_67(col_int, lit_int):
    res = col_int - lit_int
    assert res._output[0] == '("test_table"."age" - %s)'
    assert res._output[1] == [10]

def test_68(col_int, lit_float):
    res = col_int - lit_float
    assert res._output[0] == '("test_table"."age" - %s)'
    assert res._output[1] == [10.5]

def test_69(lit_str, col_int):
    res = lit_str + col_int
    assert res._output[0] == '(%s || "test_table"."age")'
    assert res._output[1] == ['text']

def test_70(lit_int, col_int):
    res = lit_int + col_int
    assert res._output[0] == '(%s + "test_table"."age")'
    assert res._output[1] == [10]

def test_71(lit_float, col_int):
    res = lit_float + col_int
    assert res._output[0] == '(%s + "test_table"."age")'
    assert res._output[1] == [10.5]

def test_72(lit_str, col_int):
    res = lit_str - col_int
    assert res._output[0] == '(%s - "test_table"."age")'
    assert res._output[1] == ['text']

def test_73(lit_int, col_int):
    res = lit_int - col_int
    assert res._output[0] == '(%s - "test_table"."age")'
    assert res._output[1] == [10]

def test_74(lit_float, col_int):
    res = lit_float - col_int
    assert res._output[0] == '(%s - "test_table"."age")'
    assert res._output[1] == [10.5]

def test_75(col_int):
    res = col_int + (col_int + col_int)
    assert res._output[0] == '("test_table"."age" + ("test_table"."age" + "test_table"."age"))'
    assert res._output[1] == []

def test_76(col_int, col_str):
    res = col_int + (col_str + col_str)
    assert res._output[0] == '("test_table"."age" || ("test_table"."name" || "test_table"."name"))'
    assert res._output[1] == []

def test_77(col_int, col_float):
    res = col_int + (col_float + col_float)
    assert res._output[0] == '("test_table"."age" + ("test_table"."score" + "test_table"."score"))'
    assert res._output[1] == []

def test_78(col_int):
    res = col_int - (col_int - col_int)
    assert res._output[0] == '("test_table"."age" - ("test_table"."age" - "test_table"."age"))'
    assert res._output[1] == []

def test_79(col_int, col_str):
    res = col_int - (col_str - col_str)
    assert res._output[0] == '("test_table"."age" - ("test_table"."name" - "test_table"."name"))'
    assert res._output[1] == []

def test_80(col_int, col_float):
    res = col_int - (col_float - col_float)
    assert res._output[0] == '("test_table"."age" - ("test_table"."score" - "test_table"."score"))'
    assert res._output[1] == []

def test_81(col_int):
    res = (col_int + col_int) + col_int
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") + "test_table"."age")'
    assert res._output[1] == []

def test_82(col_int, lit_int):
    res = (col_int + col_int) + lit_int
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") + %s)'
    assert res._output[1] == [10]

def test_83(col_int):
    res = (col_int + col_int) - col_int
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") - "test_table"."age")'
    assert res._output[1] == []

def test_84(col_int, lit_int):
    res = (col_int + col_int) - lit_int
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") - %s)'
    assert res._output[1] == [10]

def test_85(lit_int, col_int):
    res = lit_int + (col_int + col_int)
    assert res._output[0] == '(%s + ("test_table"."age" + "test_table"."age"))'
    assert res._output[1] == [10]

def test_86(lit_int, col_int):
    res = lit_int - (col_int - col_int)
    assert res._output[0] == '(%s - ("test_table"."age" - "test_table"."age"))'
    assert res._output[1] == [10]

def test_87(col_int, col_str):
    res = (col_int + col_str) + col_int
    assert res._output[0] == '(("test_table"."age" || "test_table"."name") || "test_table"."age")'
    assert res._output[1] == []

def test_88(col_int, lit_str):
    res = (col_int + lit_str) + col_int
    assert res._output[0] == '(("test_table"."age" || %s) || "test_table"."age")'
    assert res._output[1] == ['text']

def test_89(col_int, lit_int):
    res = col_int + (col_int + lit_int)
    assert res._output[0] == '("test_table"."age" + ("test_table"."age" + %s))'
    assert res._output[1] == [10]

def test_90(col_int, lit_int):
    res = col_int + (lit_int + col_int)
    assert res._output[0] == '("test_table"."age" + (%s + "test_table"."age"))'
    assert res._output[1] == [10]

def test_91(col_int):
    res = (col_int + col_int) + (col_int + col_int)
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") + ("test_table"."age" + "test_table"."age"))'
    assert res._output[1] == []

def test_92(col_int):
    res = (col_int + col_int) - (col_int - col_int)
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") - ("test_table"."age" - "test_table"."age"))'
    assert res._output[1] == []

def test_93(lit_int, col_int):
    res = lit_int + (col_int + col_int)
    assert res._output[0] == '(%s + ("test_table"."age" + "test_table"."age"))'
    assert res._output[1] == [10]

def test_94(lit_str, col_int, col_str):
    res = lit_str + (col_int + col_str)
    assert res._output[0] == '(%s || ("test_table"."age" || "test_table"."name"))'
    assert res._output[1] == ['text']

def test_95(lit_float, col_int, col_float):
    res = lit_float + (col_int + col_float)
    assert res._output[0] == '(%s + ("test_table"."age" + "test_table"."score"))'
    assert res._output[1] == [10.5]

def test_96(col_int, op_int):
    res = (col_int + col_int) + op_int
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") + ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_97(col_int, op_str):
    res = (col_int + col_int) + op_str
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param']

def test_98(col_int, op_float):
    res = (col_int + col_int) + op_float
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") + ("test_table"."score" + %s))'
    assert res._output[1] == [1.5]

def test_99(op_int, col_int):
    res = op_int + (col_int + col_int)
    assert res._output[0] == '(("test_table"."age" + %s) + ("test_table"."age" + "test_table"."age"))'
    assert res._output[1] == [1]

def test_100(op_int, col_int):
    res = op_int - (col_int - col_int)
    assert res._output[0] == '(("test_table"."age" + %s) - ("test_table"."age" - "test_table"."age"))'
    assert res._output[1] == [1]

def test_101(col_float, col_str):
    res = col_float + col_str
    assert res._output[0] == '("test_table"."score" || "test_table"."name")'
    assert res._output[1] == []

def test_102(col_float, col_int):
    res = col_float + col_int
    assert res._output[0] == '("test_table"."score" + "test_table"."age")'
    assert res._output[1] == []

def test_103(col_float):
    res = col_float + col_float
    assert res._output[0] == '("test_table"."score" + "test_table"."score")'
    assert res._output[1] == []

def test_104(col_float, op_str):
    res = col_float + op_str
    assert res._output[0] == '("test_table"."score" || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param']

def test_105(col_float, op_int):
    res = col_float + op_int
    assert res._output[0] == '("test_table"."score" + ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_106(col_float, op_float):
    res = col_float + op_float
    assert res._output[0] == '("test_table"."score" + ("test_table"."score" + %s))'
    assert res._output[1] == [1.5]

def test_107(col_float, lit_str):
    res = col_float + lit_str
    assert res._output[0] == '("test_table"."score" || %s)'
    assert res._output[1] == ['text']

def test_108(col_float, lit_int):
    res = col_float + lit_int
    assert res._output[0] == '("test_table"."score" + %s)'
    assert res._output[1] == [10]

def test_109(col_float, lit_float):
    res = col_float + lit_float
    assert res._output[0] == '("test_table"."score" + %s)'
    assert res._output[1] == [10.5]

def test_110(col_float, col_str):
    res = col_float - col_str
    assert res._output[0] == '("test_table"."score" - "test_table"."name")'
    assert res._output[1] == []

def test_111(col_float, col_int):
    res = col_float - col_int
    assert res._output[0] == '("test_table"."score" - "test_table"."age")'
    assert res._output[1] == []

def test_112(col_float):
    res = col_float - col_float
    assert res._output[0] == '("test_table"."score" - "test_table"."score")'
    assert res._output[1] == []

def test_113(col_float, op_str):
    res = col_float - op_str
    assert res._output[0] == '("test_table"."score" - ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param']

def test_114(col_float, op_int):
    res = col_float - op_int
    assert res._output[0] == '("test_table"."score" - ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_115(col_float, op_float):
    res = col_float - op_float
    assert res._output[0] == '("test_table"."score" - ("test_table"."score" + %s))'
    assert res._output[1] == [1.5]

def test_116(col_float, lit_str):
    res = col_float - lit_str
    assert res._output[0] == '("test_table"."score" - %s)'
    assert res._output[1] == ['text']

def test_117(col_float, lit_int):
    res = col_float - lit_int
    assert res._output[0] == '("test_table"."score" - %s)'
    assert res._output[1] == [10]

def test_118(col_float, lit_float):
    res = col_float - lit_float
    assert res._output[0] == '("test_table"."score" - %s)'
    assert res._output[1] == [10.5]

def test_119(lit_str, col_float):
    res = lit_str + col_float
    assert res._output[0] == '(%s || "test_table"."score")'
    assert res._output[1] == ['text']

def test_120(lit_int, col_float):
    res = lit_int + col_float
    assert res._output[0] == '(%s + "test_table"."score")'
    assert res._output[1] == [10]

def test_121(lit_float, col_float):
    res = lit_float + col_float
    assert res._output[0] == '(%s + "test_table"."score")'
    assert res._output[1] == [10.5]

def test_122(lit_str, col_float):
    res = lit_str - col_float
    assert res._output[0] == '(%s - "test_table"."score")'
    assert res._output[1] == ['text']

def test_123(lit_int, col_float):
    res = lit_int - col_float
    assert res._output[0] == '(%s - "test_table"."score")'
    assert res._output[1] == [10]

def test_124(lit_float, col_float):
    res = lit_float - col_float
    assert res._output[0] == '(%s - "test_table"."score")'
    assert res._output[1] == [10.5]

def test_125(col_float):
    res = col_float + (col_float + col_float)
    assert res._output[0] == '("test_table"."score" + ("test_table"."score" + "test_table"."score"))'
    assert res._output[1] == []

def test_126(col_float, col_int):
    res = col_float + (col_int + col_int)
    assert res._output[0] == '("test_table"."score" + ("test_table"."age" + "test_table"."age"))'
    assert res._output[1] == []

def test_127(col_float, col_str):
    res = col_float + (col_str + col_str)
    assert res._output[0] == '("test_table"."score" || ("test_table"."name" || "test_table"."name"))'
    assert res._output[1] == []

def test_128(col_float):
    res = col_float - (col_float - col_float)
    assert res._output[0] == '("test_table"."score" - ("test_table"."score" - "test_table"."score"))'
    assert res._output[1] == []

def test_129(col_float, col_int):
    res = col_float - (col_int - col_int)
    assert res._output[0] == '("test_table"."score" - ("test_table"."age" - "test_table"."age"))'
    assert res._output[1] == []

def test_130(col_float, col_str):
    res = col_float - (col_str - col_str)
    assert res._output[0] == '("test_table"."score" - ("test_table"."name" - "test_table"."name"))'
    assert res._output[1] == []

def test_131(col_float):
    res = (col_float + col_float) + col_float
    assert res._output[0] == '(("test_table"."score" + "test_table"."score") + "test_table"."score")'
    assert res._output[1] == []

def test_132(col_float, lit_float):
    res = (col_float + col_float) + lit_float
    assert res._output[0] == '(("test_table"."score" + "test_table"."score") + %s)'
    assert res._output[1] == [10.5]

def test_133(col_float):
    res = (col_float + col_float) - col_float
    assert res._output[0] == '(("test_table"."score" + "test_table"."score") - "test_table"."score")'
    assert res._output[1] == []

def test_134(col_float, lit_float):
    res = (col_float + col_float) - lit_float
    assert res._output[0] == '(("test_table"."score" + "test_table"."score") - %s)'
    assert res._output[1] == [10.5]

def test_135(lit_float, col_float):
    res = lit_float + (col_float + col_float)
    assert res._output[0] == '(%s + ("test_table"."score" + "test_table"."score"))'
    assert res._output[1] == [10.5]

def test_136(lit_float, col_float):
    res = lit_float - (col_float - col_float)
    assert res._output[0] == '(%s - ("test_table"."score" - "test_table"."score"))'
    assert res._output[1] == [10.5]

def test_137(col_float, col_int):
    res = (col_float + col_int) + col_float
    assert res._output[0] == '(("test_table"."score" + "test_table"."age") + "test_table"."score")'
    assert res._output[1] == []

def test_138(col_float, lit_str):
    res = (col_float + lit_str) + col_float
    assert res._output[0] == '(("test_table"."score" || %s) || "test_table"."score")'
    assert res._output[1] == ['text']

def test_139(col_float, lit_float):
    res = col_float + (col_float + lit_float)
    assert res._output[0] == '("test_table"."score" + ("test_table"."score" + %s))'
    assert res._output[1] == [10.5]

def test_140(col_float, lit_float):
    res = col_float + (lit_float + col_float)
    assert res._output[0] == '("test_table"."score" + (%s + "test_table"."score"))'
    assert res._output[1] == [10.5]

def test_141(col_float):
    res = (col_float + col_float) + (col_float + col_float)
    assert res._output[0] == '(("test_table"."score" + "test_table"."score") + ("test_table"."score" + "test_table"."score"))'
    assert res._output[1] == []

def test_142(col_float):
    res = (col_float + col_float) - (col_float - col_float)
    assert res._output[0] == '(("test_table"."score" + "test_table"."score") - ("test_table"."score" - "test_table"."score"))'
    assert res._output[1] == []

def test_143(lit_float, col_float):
    res = lit_float + (col_float + col_float)
    assert res._output[0] == '(%s + ("test_table"."score" + "test_table"."score"))'
    assert res._output[1] == [10.5]

def test_144(lit_int, col_float, col_int):
    res = lit_int + (col_float + col_int)
    assert res._output[0] == '(%s + ("test_table"."score" + "test_table"."age"))'
    assert res._output[1] == [10]

def test_145(lit_str, col_float, col_str):
    res = lit_str + (col_float + col_str)
    assert res._output[0] == '(%s || ("test_table"."score" || "test_table"."name"))'
    assert res._output[1] == ['text']

def test_146(col_float, op_float):
    res = (col_float + col_float) + op_float
    assert res._output[0] == '(("test_table"."score" + "test_table"."score") + ("test_table"."score" + %s))'
    assert res._output[1] == [1.5]

def test_147(col_float, op_int):
    res = (col_float + col_float) + op_int
    assert res._output[0] == '(("test_table"."score" + "test_table"."score") + ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_148(col_float, op_str):
    res = (col_float + col_float) + op_str
    assert res._output[0] == '(("test_table"."score" + "test_table"."score") || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param']

def test_149(op_float, col_float):
    res = op_float + (col_float + col_float)
    assert res._output[0] == '(("test_table"."score" + %s) + ("test_table"."score" + "test_table"."score"))'
    assert res._output[1] == [1.5]

def test_150(op_float, col_float):
    res = op_float - (col_float - col_float)
    assert res._output[0] == '(("test_table"."score" + %s) - ("test_table"."score" - "test_table"."score"))'
    assert res._output[1] == [1.5]

def test_151(op_str, col_str):
    res = op_str + col_str
    assert res._output[0] == '(("test_table"."name" || %s) || "test_table"."name")'
    assert res._output[1] == ['op_str_param']

def test_152(op_str, col_int):
    res = op_str + col_int
    assert res._output[0] == '(("test_table"."name" || %s) || "test_table"."age")'
    assert res._output[1] == ['op_str_param']

def test_153(op_str, col_float):
    res = op_str + col_float
    assert res._output[0] == '(("test_table"."name" || %s) || "test_table"."score")'
    assert res._output[1] == ['op_str_param']

def test_154(op_str):
    res = op_str + op_str
    assert res._output[0] == '(("test_table"."name" || %s) || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param', 'op_str_param']

def test_155(op_str, op_int):
    res = op_str + op_int
    assert res._output[0] == '(("test_table"."name" || %s) || ("test_table"."age" + %s))'
    assert res._output[1] == ['op_str_param', 1]

def test_156(op_str, op_float):
    res = op_str + op_float
    assert res._output[0] == '(("test_table"."name" || %s) || ("test_table"."score" + %s))'
    assert res._output[1] == ['op_str_param', 1.5]

def test_157(op_str, lit_str):
    res = op_str + lit_str
    assert res._output[0] == '(("test_table"."name" || %s) || %s)'
    assert res._output[1] == ['op_str_param', 'text']

def test_158(op_str, lit_int):
    res = op_str + lit_int
    assert res._output[0] == '(("test_table"."name" || %s) || %s)'
    assert res._output[1] == ['op_str_param', 10]

def test_159(op_str, lit_float):
    res = op_str + lit_float
    assert res._output[0] == '(("test_table"."name" || %s) || %s)'
    assert res._output[1] == ['op_str_param', 10.5]

def test_160(op_str, col_str):
    res = op_str - col_str
    assert res._output[0] == '(("test_table"."name" || %s) - "test_table"."name")'
    assert res._output[1] == ['op_str_param']

def test_161(op_str, col_int):
    res = op_str - col_int
    assert res._output[0] == '(("test_table"."name" || %s) - "test_table"."age")'
    assert res._output[1] == ['op_str_param']

def test_162(op_str, col_float):
    res = op_str - col_float
    assert res._output[0] == '(("test_table"."name" || %s) - "test_table"."score")'
    assert res._output[1] == ['op_str_param']

def test_163(op_str):
    res = op_str - op_str
    assert res._output[0] == '(("test_table"."name" || %s) - ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param', 'op_str_param']

def test_164(op_str, op_int):
    res = op_str - op_int
    assert res._output[0] == '(("test_table"."name" || %s) - ("test_table"."age" + %s))'
    assert res._output[1] == ['op_str_param', 1]

def test_165(op_str, op_float):
    res = op_str - op_float
    assert res._output[0] == '(("test_table"."name" || %s) - ("test_table"."score" + %s))'
    assert res._output[1] == ['op_str_param', 1.5]

def test_166(op_str, lit_str):
    res = op_str - lit_str
    assert res._output[0] == '(("test_table"."name" || %s) - %s)'
    assert res._output[1] == ['op_str_param', 'text']

def test_167(op_str, lit_int):
    res = op_str - lit_int
    assert res._output[0] == '(("test_table"."name" || %s) - %s)'
    assert res._output[1] == ['op_str_param', 10]

def test_168(op_str, lit_float):
    res = op_str - lit_float
    assert res._output[0] == '(("test_table"."name" || %s) - %s)'
    assert res._output[1] == ['op_str_param', 10.5]

def test_169(lit_str, op_str):
    res = lit_str + op_str
    assert res._output[0] == '(%s || ("test_table"."name" || %s))'
    assert res._output[1] == ['text', 'op_str_param']

def test_170(lit_int, op_str):
    res = lit_int + op_str
    assert res._output[0] == '(%s || ("test_table"."name" || %s))'
    assert res._output[1] == [10, 'op_str_param']

def test_171(lit_float, op_str):
    res = lit_float + op_str
    assert res._output[0] == '(%s || ("test_table"."name" || %s))'
    assert res._output[1] == [10.5, 'op_str_param']

def test_172(lit_str, op_str):
    res = lit_str - op_str
    assert res._output[0] == '(%s - ("test_table"."name" || %s))'
    assert res._output[1] == ['text', 'op_str_param']

def test_173(lit_int, op_str):
    res = lit_int - op_str
    assert res._output[0] == '(%s - ("test_table"."name" || %s))'
    assert res._output[1] == [10, 'op_str_param']

def test_174(lit_float, op_str):
    res = lit_float - op_str
    assert res._output[0] == '(%s - ("test_table"."name" || %s))'
    assert res._output[1] == [10.5, 'op_str_param']

def test_175(op_str):
    res = op_str + (op_str + op_str)
    assert res._output[0] == '(("test_table"."name" || %s) || (("test_table"."name" || %s) || ("test_table"."name" || %s)))'
    assert res._output[1] == ['op_str_param', 'op_str_param', 'op_str_param']

def test_176(op_str, col_str):
    res = op_str + (col_str + col_str)
    assert res._output[0] == '(("test_table"."name" || %s) || ("test_table"."name" || "test_table"."name"))'
    assert res._output[1] == ['op_str_param']

def test_177(op_str, lit_str):
    res = op_str + (lit_str + lit_str)
    assert res._output[0] == '(("test_table"."name" || %s) || %s)'
    assert res._output[1] == ['op_str_param', 'texttext']

def test_178(op_str):
    res = op_str - (op_str - op_str)
    assert res._output[0] == '(("test_table"."name" || %s) - (("test_table"."name" || %s) - ("test_table"."name" || %s)))'
    assert res._output[1] == ['op_str_param', 'op_str_param', 'op_str_param']

def test_179(op_str, col_str):
    res = op_str - (col_str - col_str)
    assert res._output[0] == '(("test_table"."name" || %s) - ("test_table"."name" - "test_table"."name"))'
    assert res._output[1] == ['op_str_param']

def test_180(op_str, lit_str):
    with pytest.raises(TypeError):
        res = op_str - (lit_str - lit_str)

def test_181(op_str):
    res = (op_str + op_str) + op_str
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."name" || %s)) || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param', 'op_str_param', 'op_str_param']

def test_182(op_str, lit_str):
    res = (op_str + op_str) + lit_str
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."name" || %s)) || %s)'
    assert res._output[1] == ['op_str_param', 'op_str_param', 'text']

def test_183(op_str):
    res = (op_str + op_str) - op_str
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."name" || %s)) - ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param', 'op_str_param', 'op_str_param']

def test_184(op_str, lit_str):
    res = (op_str + op_str) - lit_str
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."name" || %s)) - %s)'
    assert res._output[1] == ['op_str_param', 'op_str_param', 'text']

def test_185(lit_str, op_str):
    res = lit_str + (op_str + op_str)
    assert res._output[0] == '(%s || (("test_table"."name" || %s) || ("test_table"."name" || %s)))'
    assert res._output[1] == ['text', 'op_str_param', 'op_str_param']

def test_186(lit_str, op_str):
    res = lit_str - (op_str - op_str)
    assert res._output[0] == '(%s - (("test_table"."name" || %s) - ("test_table"."name" || %s)))'
    assert res._output[1] == ['text', 'op_str_param', 'op_str_param']

def test_187(op_str, col_str):
    res = (op_str + col_str) + op_str
    assert res._output[0] == '((("test_table"."name" || %s) || "test_table"."name") || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param', 'op_str_param']

def test_188(op_str, lit_int):
    res = (op_str + lit_int) + op_str
    assert res._output[0] == '((("test_table"."name" || %s) || %s) || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param', 10, 'op_str_param']

def test_189(op_str, lit_str):
    res = op_str + (op_str + lit_str)
    assert res._output[0] == '(("test_table"."name" || %s) || (("test_table"."name" || %s) || %s))'
    assert res._output[1] == ['op_str_param', 'op_str_param', 'text']

def test_190(op_str, lit_str):
    res = op_str + (lit_str + op_str)
    assert res._output[0] == '(("test_table"."name" || %s) || (%s || ("test_table"."name" || %s)))'
    assert res._output[1] == ['op_str_param', 'text', 'op_str_param']

def test_191(op_str):
    res = (op_str + op_str) + (op_str + op_str)
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."name" || %s)) || (("test_table"."name" || %s) || ("test_table"."name" || %s)))'
    assert res._output[1] == ['op_str_param', 'op_str_param', 'op_str_param', 'op_str_param']

def test_192(op_str):
    res = (op_str + op_str) - (op_str - op_str)
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."name" || %s)) - (("test_table"."name" || %s) - ("test_table"."name" || %s)))'
    assert res._output[1] == ['op_str_param', 'op_str_param', 'op_str_param', 'op_str_param']

def test_193(lit_str, op_str):
    res = lit_str + (op_str + op_str)
    assert res._output[0] == '(%s || (("test_table"."name" || %s) || ("test_table"."name" || %s)))'
    assert res._output[1] == ['text', 'op_str_param', 'op_str_param']

def test_194(lit_int, op_str, op_int):
    res = lit_int + (op_str + op_int)
    assert res._output[0] == '(%s || (("test_table"."name" || %s) || ("test_table"."age" + %s)))'
    assert res._output[1] == [10, 'op_str_param', 1]

def test_195(lit_float, op_str, op_float):
    res = lit_float + (op_str + op_float)
    assert res._output[0] == '(%s || (("test_table"."name" || %s) || ("test_table"."score" + %s)))'
    assert res._output[1] == [10.5, 'op_str_param', 1.5]

def test_196(op_str, col_str):
    res = (op_str + op_str) + col_str
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."name" || %s)) || "test_table"."name")'
    assert res._output[1] == ['op_str_param', 'op_str_param']

def test_197(op_str, col_int):
    res = (op_str + op_str) + col_int
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."name" || %s)) || "test_table"."age")'
    assert res._output[1] == ['op_str_param', 'op_str_param']

def test_198(op_str, col_float):
    res = (op_str + op_str) + col_float
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."name" || %s)) || "test_table"."score")'
    assert res._output[1] == ['op_str_param', 'op_str_param']

def test_199(col_str, op_str):
    res = col_str + (op_str + op_str)
    assert res._output[0] == '("test_table"."name" || (("test_table"."name" || %s) || ("test_table"."name" || %s)))'
    assert res._output[1] == ['op_str_param', 'op_str_param']

def test_200(col_str, op_str):
    res = col_str - (op_str - op_str)
    assert res._output[0] == '("test_table"."name" - (("test_table"."name" || %s) - ("test_table"."name" || %s)))'
    assert res._output[1] == ['op_str_param', 'op_str_param']

def test_201(op_int, col_str):
    res = op_int + col_str
    assert res._output[0] == '(("test_table"."age" + %s) || "test_table"."name")'
    assert res._output[1] == [1]

def test_202(op_int, col_int):
    res = op_int + col_int
    assert res._output[0] == '(("test_table"."age" + %s) + "test_table"."age")'
    assert res._output[1] == [1]

def test_203(op_int, col_float):
    res = op_int + col_float
    assert res._output[0] == '(("test_table"."age" + %s) + "test_table"."score")'
    assert res._output[1] == [1]

def test_204(op_int, op_str):
    res = op_int + op_str
    assert res._output[0] == '(("test_table"."age" + %s) || ("test_table"."name" || %s))'
    assert res._output[1] == [1, 'op_str_param']

def test_205(op_int):
    res = op_int + op_int
    assert res._output[0] == '(("test_table"."age" + %s) + ("test_table"."age" + %s))'
    assert res._output[1] == [1, 1]

def test_206(op_int, op_float):
    res = op_int + op_float
    assert res._output[0] == '(("test_table"."age" + %s) + ("test_table"."score" + %s))'
    assert res._output[1] == [1, 1.5]

def test_207(op_int, lit_str):
    res = op_int + lit_str
    assert res._output[0] == '(("test_table"."age" + %s) || %s)'
    assert res._output[1] == [1, 'text']

def test_208(op_int, lit_int):
    res = op_int + lit_int
    assert res._output[0] == '(("test_table"."age" + %s) + %s)'
    assert res._output[1] == [1, 10]

def test_209(op_int, lit_float):
    res = op_int + lit_float
    assert res._output[0] == '(("test_table"."age" + %s) + %s)'
    assert res._output[1] == [1, 10.5]

def test_210(op_int, col_str):
    res = op_int - col_str
    assert res._output[0] == '(("test_table"."age" + %s) - "test_table"."name")'
    assert res._output[1] == [1]

def test_211(op_int, col_int):
    res = op_int - col_int
    assert res._output[0] == '(("test_table"."age" + %s) - "test_table"."age")'
    assert res._output[1] == [1]

def test_212(op_int, col_float):
    res = op_int - col_float
    assert res._output[0] == '(("test_table"."age" + %s) - "test_table"."score")'
    assert res._output[1] == [1]

def test_213(op_int, op_str):
    res = op_int - op_str
    assert res._output[0] == '(("test_table"."age" + %s) - ("test_table"."name" || %s))'
    assert res._output[1] == [1, 'op_str_param']

def test_214(op_int):
    res = op_int - op_int
    assert res._output[0] == '(("test_table"."age" + %s) - ("test_table"."age" + %s))'
    assert res._output[1] == [1, 1]

def test_215(op_int, op_float):
    res = op_int - op_float
    assert res._output[0] == '(("test_table"."age" + %s) - ("test_table"."score" + %s))'
    assert res._output[1] == [1, 1.5]

def test_216(op_int, lit_str):
    res = op_int - lit_str
    assert res._output[0] == '(("test_table"."age" + %s) - %s)'
    assert res._output[1] == [1, 'text']

def test_217(op_int, lit_int):
    res = op_int - lit_int
    assert res._output[0] == '(("test_table"."age" + %s) - %s)'
    assert res._output[1] == [1, 10]

def test_218(op_int, lit_float):
    res = op_int - lit_float
    assert res._output[0] == '(("test_table"."age" + %s) - %s)'
    assert res._output[1] == [1, 10.5]

def test_219(lit_str, op_int):
    res = lit_str + op_int
    assert res._output[0] == '(%s || ("test_table"."age" + %s))'
    assert res._output[1] == ['text', 1]

def test_220(lit_int, op_int):
    res = lit_int + op_int
    assert res._output[0] == '(%s + ("test_table"."age" + %s))'
    assert res._output[1] == [10, 1]

def test_221(lit_float, op_int):
    res = lit_float + op_int
    assert res._output[0] == '(%s + ("test_table"."age" + %s))'
    assert res._output[1] == [10.5, 1]

def test_222(lit_str, op_int):
    res = lit_str - op_int
    assert res._output[0] == '(%s - ("test_table"."age" + %s))'
    assert res._output[1] == ['text', 1]

def test_223(lit_int, op_int):
    res = lit_int - op_int
    assert res._output[0] == '(%s - ("test_table"."age" + %s))'
    assert res._output[1] == [10, 1]

def test_224(lit_float, op_int):
    res = lit_float - op_int
    assert res._output[0] == '(%s - ("test_table"."age" + %s))'
    assert res._output[1] == [10.5, 1]

def test_225(op_int):
    res = op_int + (op_int + op_int)
    assert res._output[0] == '(("test_table"."age" + %s) + (("test_table"."age" + %s) + ("test_table"."age" + %s)))'
    assert res._output[1] == [1, 1, 1]

def test_226(op_int, col_int):
    res = op_int + (col_int + col_int)
    assert res._output[0] == '(("test_table"."age" + %s) + ("test_table"."age" + "test_table"."age"))'
    assert res._output[1] == [1]

def test_227(op_int, lit_int):
    res = op_int + (lit_int + lit_int)
    assert res._output[0] == '(("test_table"."age" + %s) + %s)'
    assert res._output[1] == [1, 20] 

def test_228(op_int):
    res = op_int - (op_int - op_int)
    assert res._output[0] == '(("test_table"."age" + %s) - (("test_table"."age" + %s) - ("test_table"."age" + %s)))'
    assert res._output[1] == [1, 1, 1]

def test_229(op_int, col_int):
    res = op_int - (col_int - col_int)
    assert res._output[0] == '(("test_table"."age" + %s) - ("test_table"."age" - "test_table"."age"))'
    assert res._output[1] == [1]

def test_230(op_int, lit_int):
    res = op_int - (lit_int - lit_int)
    assert res._output[0] == '(("test_table"."age" + %s) - %s)'
    assert res._output[1] == [1, 0]  

def test_231(op_int):
    res = (op_int + op_int) + op_int
    assert res._output[0] == '((("test_table"."age" + %s) + ("test_table"."age" + %s)) + ("test_table"."age" + %s))'
    assert res._output[1] == [1, 1, 1]

def test_232(op_int, lit_int):
    res = (op_int + op_int) + lit_int
    assert res._output[0] == '((("test_table"."age" + %s) + ("test_table"."age" + %s)) + %s)'
    assert res._output[1] == [1, 1, 10]

def test_233(op_int):
    res = (op_int + op_int) - op_int
    assert res._output[0] == '((("test_table"."age" + %s) + ("test_table"."age" + %s)) - ("test_table"."age" + %s))'
    assert res._output[1] == [1, 1, 1]

def test_234(op_int, lit_int):
    res = (op_int + op_int) - lit_int
    assert res._output[0] == '((("test_table"."age" + %s) + ("test_table"."age" + %s)) - %s)'
    assert res._output[1] == [1, 1, 10]

def test_235(lit_int, op_int):
    res = lit_int + (op_int + op_int)
    assert res._output[0] == '(%s + (("test_table"."age" + %s) + ("test_table"."age" + %s)))'
    assert res._output[1] == [10, 1, 1]

def test_236(lit_int, op_int):
    res = lit_int - (op_int - op_int)
    assert res._output[0] == '(%s - (("test_table"."age" + %s) - ("test_table"."age" + %s)))'
    assert res._output[1] == [10, 1, 1]

def test_237(op_int, col_int):
    res = (op_int + col_int) + op_int
    assert res._output[0] == '((("test_table"."age" + %s) + "test_table"."age") + ("test_table"."age" + %s))'
    assert res._output[1] == [1, 1]

def test_238(op_int, lit_str):
    res = (op_int + lit_str) + op_int
    assert res._output[0] == '((("test_table"."age" + %s) || %s) || ("test_table"."age" + %s))'
    assert res._output[1] == [1, 'text', 1]

def test_239(op_int, lit_int):
    res = op_int + (op_int + lit_int)
    assert res._output[0] == '(("test_table"."age" + %s) + (("test_table"."age" + %s) + %s))'
    assert res._output[1] == [1, 1, 10]

def test_240(op_int, lit_int):
    res = op_int + (lit_int + op_int)
    assert res._output[0] == '(("test_table"."age" + %s) + (%s + ("test_table"."age" + %s)))'
    assert res._output[1] == [1, 10, 1]

def test_241(op_int):
    res = (op_int + op_int) + (op_int + op_int)
    assert res._output[0] == '((("test_table"."age" + %s) + ("test_table"."age" + %s)) + (("test_table"."age" + %s) + ("test_table"."age" + %s)))'
    assert res._output[1] == [1, 1, 1, 1]

def test_242(op_int):
    res = (op_int + op_int) - (op_int - op_int)
    assert res._output[0] == '((("test_table"."age" + %s) + ("test_table"."age" + %s)) - (("test_table"."age" + %s) - ("test_table"."age" + %s)))'
    assert res._output[1] == [1, 1, 1, 1]

def test_243(lit_int, op_int):
    res = lit_int + (op_int + op_int)
    assert res._output[0] == '(%s + (("test_table"."age" + %s) + ("test_table"."age" + %s)))'
    assert res._output[1] == [10, 1, 1]

def test_244(lit_str, op_int, op_str):
    res = lit_str + (op_int + op_str)
    assert res._output[0] == '(%s || (("test_table"."age" + %s) || ("test_table"."name" || %s)))'
    assert res._output[1] == ['text', 1, 'op_str_param']

def test_245(lit_float, op_int, op_float):
    res = lit_float + (op_int + op_float)
    assert res._output[0] == '(%s + (("test_table"."age" + %s) + ("test_table"."score" + %s)))'
    assert res._output[1] == [10.5, 1, 1.5]

def test_246(op_int, col_int):
    res = (op_int + op_int) + col_int
    assert res._output[0] == '((("test_table"."age" + %s) + ("test_table"."age" + %s)) + "test_table"."age")'
    assert res._output[1] == [1, 1]

def test_247(op_int, col_str):
    res = (op_int + op_int) + col_str
    assert res._output[0] == '((("test_table"."age" + %s) + ("test_table"."age" + %s)) || "test_table"."name")'
    assert res._output[1] == [1, 1]

def test_248(op_int, col_float):
    res = (op_int + op_int) + col_float
    assert res._output[0] == '((("test_table"."age" + %s) + ("test_table"."age" + %s)) + "test_table"."score")'
    assert res._output[1] == [1, 1]

def test_249(col_int, op_int):
    res = col_int + (op_int + op_int)
    assert res._output[0] == '("test_table"."age" + (("test_table"."age" + %s) + ("test_table"."age" + %s)))'
    assert res._output[1] == [1, 1]

def test_250(col_int, op_int):
    res = col_int - (op_int - op_int)
    assert res._output[0] == '("test_table"."age" - (("test_table"."age" + %s) - ("test_table"."age" + %s)))'
    assert res._output[1] == [1, 1]

def test_251(op_float, col_str):
    res = op_float + col_str
    assert res._output[0] == '(("test_table"."score" + %s) || "test_table"."name")'
    assert res._output[1] == [1.5]

def test_252(op_float, col_int):
    res = op_float + col_int
    assert res._output[0] == '(("test_table"."score" + %s) + "test_table"."age")'
    assert res._output[1] == [1.5]

def test_253(op_float, col_float):
    res = op_float + col_float
    assert res._output[0] == '(("test_table"."score" + %s) + "test_table"."score")'
    assert res._output[1] == [1.5]

def test_254(op_float, op_str):
    res = op_float + op_str
    assert res._output[0] == '(("test_table"."score" + %s) || ("test_table"."name" || %s))'
    assert res._output[1] == [1.5, 'op_str_param']

def test_255(op_float, op_int):
    res = op_float + op_int
    assert res._output[0] == '(("test_table"."score" + %s) + ("test_table"."age" + %s))'
    assert res._output[1] == [1.5, 1]

def test_256(op_float):
    res = op_float + op_float
    assert res._output[0] == '(("test_table"."score" + %s) + ("test_table"."score" + %s))'
    assert res._output[1] == [1.5, 1.5]

def test_257(op_float, lit_str):
    res = op_float + lit_str
    assert res._output[0] == '(("test_table"."score" + %s) || %s)'
    assert res._output[1] == [1.5, 'text']

def test_258(op_float, lit_int):
    res = op_float + lit_int
    assert res._output[0] == '(("test_table"."score" + %s) + %s)'
    assert res._output[1] == [1.5, 10]

def test_259(op_float, lit_float):
    res = op_float + lit_float
    assert res._output[0] == '(("test_table"."score" + %s) + %s)'
    assert res._output[1] == [1.5, 10.5]

def test_260(op_float, col_str):
    res = op_float - col_str
    assert res._output[0] == '(("test_table"."score" + %s) - "test_table"."name")'
    assert res._output[1] == [1.5]

def test_261(op_float, col_int):
    res = op_float - col_int
    assert res._output[0] == '(("test_table"."score" + %s) - "test_table"."age")'
    assert res._output[1] == [1.5]

def test_262(op_float, col_float):
    res = op_float - col_float
    assert res._output[0] == '(("test_table"."score" + %s) - "test_table"."score")'
    assert res._output[1] == [1.5]

def test_263(op_float, op_str):
    res = op_float - op_str
    assert res._output[0] == '(("test_table"."score" + %s) - ("test_table"."name" || %s))'
    assert res._output[1] == [1.5, 'op_str_param']

def test_264(op_float, op_int):
    res = op_float - op_int
    assert res._output[0] == '(("test_table"."score" + %s) - ("test_table"."age" + %s))'
    assert res._output[1] == [1.5, 1]

def test_265(op_float):
    res = op_float - op_float
    assert res._output[0] == '(("test_table"."score" + %s) - ("test_table"."score" + %s))'
    assert res._output[1] == [1.5, 1.5]

def test_266(op_float, lit_str):
    res = op_float - lit_str
    assert res._output[0] == '(("test_table"."score" + %s) - %s)'
    assert res._output[1] == [1.5, 'text']

def test_267(op_float, lit_int):
    res = op_float - lit_int
    assert res._output[0] == '(("test_table"."score" + %s) - %s)'
    assert res._output[1] == [1.5, 10]

def test_268(op_float, lit_float):
    res = op_float - lit_float
    assert res._output[0] == '(("test_table"."score" + %s) - %s)'
    assert res._output[1] == [1.5, 10.5]

def test_269(lit_str, op_float):
    res = lit_str + op_float
    assert res._output[0] == '(%s || ("test_table"."score" + %s))'
    assert res._output[1] == ['text', 1.5]

def test_270(lit_int, op_float):
    res = lit_int + op_float
    assert res._output[0] == '(%s + ("test_table"."score" + %s))'
    assert res._output[1] == [10, 1.5]

def test_271(lit_float, op_float):
    res = lit_float + op_float
    assert res._output[0] == '(%s + ("test_table"."score" + %s))'
    assert res._output[1] == [10.5, 1.5]

def test_272(lit_str, op_float):
    res = lit_str - op_float
    assert res._output[0] == '(%s - ("test_table"."score" + %s))'
    assert res._output[1] == ['text', 1.5]

def test_273(lit_int, op_float):
    res = lit_int - op_float
    assert res._output[0] == '(%s - ("test_table"."score" + %s))'
    assert res._output[1] == [10, 1.5]

def test_274(lit_float, op_float):
    res = lit_float - op_float
    assert res._output[0] == '(%s - ("test_table"."score" + %s))'
    assert res._output[1] == [10.5, 1.5]

def test_275(op_float):
    res = op_float + (op_float + op_float)
    assert res._output[0] == '(("test_table"."score" + %s) + (("test_table"."score" + %s) + ("test_table"."score" + %s)))'
    assert res._output[1] == [1.5, 1.5, 1.5]

def test_276(op_float, col_float):
    res = op_float + (col_float + col_float)
    assert res._output[0] == '(("test_table"."score" + %s) + ("test_table"."score" + "test_table"."score"))'
    assert res._output[1] == [1.5]

def test_277(op_float, lit_float):
    res = op_float + (lit_float + lit_float)
    assert res._output[0] == '(("test_table"."score" + %s) + %s)'
    assert res._output[1] == [1.5, 21.0]  

def test_278(op_float):
    res = op_float - (op_float - op_float)
    assert res._output[0] == '(("test_table"."score" + %s) - (("test_table"."score" + %s) - ("test_table"."score" + %s)))'
    assert res._output[1] == [1.5, 1.5, 1.5]

def test_279(op_float, col_float):
    res = op_float - (col_float - col_float)
    assert res._output[0] == '(("test_table"."score" + %s) - ("test_table"."score" - "test_table"."score"))'
    assert res._output[1] == [1.5]

def test_280(op_float, lit_float):
    res = op_float - (lit_float - lit_float)
    assert res._output[0] == '(("test_table"."score" + %s) - %s)'
    assert res._output[1] == [1.5, 0.0]  

def test_281(op_float):
    res = (op_float + op_float) + op_float
    assert res._output[0] == '((("test_table"."score" + %s) + ("test_table"."score" + %s)) + ("test_table"."score" + %s))'
    assert res._output[1] == [1.5, 1.5, 1.5]

def test_282(op_float, lit_float):
    res = (op_float + op_float) + lit_float
    assert res._output[0] == '((("test_table"."score" + %s) + ("test_table"."score" + %s)) + %s)'
    assert res._output[1] == [1.5, 1.5, 10.5]

def test_283(op_float):
    res = (op_float + op_float) - op_float
    assert res._output[0] == '((("test_table"."score" + %s) + ("test_table"."score" + %s)) - ("test_table"."score" + %s))'
    assert res._output[1] == [1.5, 1.5, 1.5]

def test_284(op_float, lit_float):
    res = (op_float + op_float) - lit_float
    assert res._output[0] == '((("test_table"."score" + %s) + ("test_table"."score" + %s)) - %s)'
    assert res._output[1] == [1.5, 1.5, 10.5]

def test_285(lit_float, op_float):
    res = lit_float + (op_float + op_float)
    assert res._output[0] == '(%s + (("test_table"."score" + %s) + ("test_table"."score" + %s)))'
    assert res._output[1] == [10.5, 1.5, 1.5]

def test_286(lit_float, op_float):
    res = lit_float - (op_float - op_float)
    assert res._output[0] == '(%s - (("test_table"."score" + %s) - ("test_table"."score" + %s)))'
    assert res._output[1] == [10.5, 1.5, 1.5]

def test_287(op_float, col_float):
    res = (op_float + col_float) + op_float
    assert res._output[0] == '((("test_table"."score" + %s) + "test_table"."score") + ("test_table"."score" + %s))'
    assert res._output[1] == [1.5, 1.5]

def test_288(op_float, lit_int):
    res = (op_float + lit_int) + op_float
    assert res._output[0] == '((("test_table"."score" + %s) + %s) + ("test_table"."score" + %s))'
    assert res._output[1] == [1.5, 10, 1.5]

def test_289(op_float, lit_float):
    res = op_float + (op_float + lit_float)
    assert res._output[0] == '(("test_table"."score" + %s) + (("test_table"."score" + %s) + %s))'
    assert res._output[1] == [1.5, 1.5, 10.5]

def test_290(op_float, lit_float):
    res = op_float + (lit_float + op_float)
    assert res._output[0] == '(("test_table"."score" + %s) + (%s + ("test_table"."score" + %s)))'
    assert res._output[1] == [1.5, 10.5, 1.5]

def test_291(op_float):
    res = (op_float + op_float) + (op_float + op_float)
    assert res._output[0] == '((("test_table"."score" + %s) + ("test_table"."score" + %s)) + (("test_table"."score" + %s) + ("test_table"."score" + %s)))'
    assert res._output[1] == [1.5, 1.5, 1.5, 1.5]

def test_292(op_float):
    res = (op_float + op_float) - (op_float - op_float)
    assert res._output[0] == '((("test_table"."score" + %s) + ("test_table"."score" + %s)) - (("test_table"."score" + %s) - ("test_table"."score" + %s)))'
    assert res._output[1] == [1.5, 1.5, 1.5, 1.5]

def test_293(lit_float, op_float):
    res = lit_float + (op_float + op_float)
    assert res._output[0] == '(%s + (("test_table"."score" + %s) + ("test_table"."score" + %s)))'
    assert res._output[1] == [10.5, 1.5, 1.5]

def test_294(lit_int, op_float, op_int):
    res = lit_int + (op_float + op_int)
    assert res._output[0] == '(%s + (("test_table"."score" + %s) + ("test_table"."age" + %s)))'
    assert res._output[1] == [10, 1.5, 1]

def test_295(lit_str, op_float, op_str):
    res = lit_str + (op_float + op_str)
    assert res._output[0] == '(%s || (("test_table"."score" + %s) || ("test_table"."name" || %s)))'
    assert res._output[1] == ['text', 1.5, 'op_str_param']

def test_296(op_float, col_float):
    res = (op_float + op_float) + col_float
    assert res._output[0] == '((("test_table"."score" + %s) + ("test_table"."score" + %s)) + "test_table"."score")'
    assert res._output[1] == [1.5, 1.5]

def test_297(op_float, col_int):
    res = (op_float + op_float) + col_int
    assert res._output[0] == '((("test_table"."score" + %s) + ("test_table"."score" + %s)) + "test_table"."age")'
    assert res._output[1] == [1.5, 1.5]

def test_298(op_float, col_str):
    res = (op_float + op_float) + col_str
    assert res._output[0] == '((("test_table"."score" + %s) + ("test_table"."score" + %s)) || "test_table"."name")'
    assert res._output[1] == [1.5, 1.5]

def test_299(col_float, op_float):
    res = col_float + (op_float + op_float)
    assert res._output[0] == '("test_table"."score" + (("test_table"."score" + %s) + ("test_table"."score" + %s)))'
    assert res._output[1] == [1.5, 1.5]

def test_300(col_float, op_float):
    res = col_float - (op_float - op_float)
    assert res._output[0] == '("test_table"."score" - (("test_table"."score" + %s) - ("test_table"."score" + %s)))'
    assert res._output[1] == [1.5, 1.5]

def test_301(col_str, col_int, col_float):
    res = (col_str + col_int) + (col_float + col_str)
    assert res._output[0] == '(("test_table"."name" || "test_table"."age") || ("test_table"."score" || "test_table"."name"))'
    assert res._output[1] == []

def test_302(col_int, col_float, col_str):
    res = (col_int - col_float) - (col_str - col_int)
    assert res._output[0] == '(("test_table"."age" - "test_table"."score") - ("test_table"."name" - "test_table"."age"))'
    assert res._output[1] == []

def test_303(lit_str, col_int, col_float):
    res = lit_str + (col_int + col_float)
    assert res._output[0] == '(%s || ("test_table"."age" + "test_table"."score"))'
    assert res._output[1] == ['text']

def test_304(lit_int, col_int, col_float):
    res = lit_int + (col_float - col_int)
    assert res._output[0] == '(%s + ("test_table"."score" - "test_table"."age"))'
    assert res._output[1] == [10]

def test_305(lit_float, col_int, col_str):
    res = lit_float - (col_int + col_str)
    assert res._output[0] == '(%s - ("test_table"."age" || "test_table"."name"))'
    assert res._output[1] == [10.5]

def test_306(op_str, op_int, op_float):
    res = (op_str + op_int) + (op_float + op_str)
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."age" + %s)) || (("test_table"."score" + %s) || ("test_table"."name" || %s)))'
    assert res._output[1] == ['op_str_param', 1, 1.5, 'op_str_param']

def test_307(op_int, op_float, op_str):
    res = (op_int - op_float) - (op_str - op_int)
    assert res._output[0] == '((("test_table"."age" + %s) - ("test_table"."score" + %s)) - (("test_table"."name" || %s) - ("test_table"."age" + %s)))'
    assert res._output[1] == [1, 1.5, 'op_str_param', 1]

def test_308(lit_str, op_int, op_float):
    res = lit_str + (op_int + op_float)
    assert res._output[0] == '(%s || (("test_table"."age" + %s) + ("test_table"."score" + %s)))'
    assert res._output[1] == ['text', 1, 1.5]

def test_309(lit_int, op_int, op_float):
    res = lit_int + (op_int - op_float)
    assert res._output[0] == '(%s + (("test_table"."age" + %s) - ("test_table"."score" + %s)))'
    assert res._output[1] == [10, 1, 1.5]

def test_310(lit_float, op_int, op_str):
    res = lit_float - (op_int + op_str)
    assert res._output[0] == '(%s - (("test_table"."age" + %s) || ("test_table"."name" || %s)))'
    assert res._output[1] == [10.5, 1, 'op_str_param']

def test_311(col_str, lit_str, col_int, lit_int):
    res = (col_str + lit_str) + (col_int + lit_int)
    assert res._output[0] == '(("test_table"."name" || %s) || ("test_table"."age" + %s))'
    assert res._output[1] == ['text', 10]

def test_312(col_int, lit_int, col_float, lit_float):
    res = (col_int - lit_int) - (col_float - lit_float)
    assert res._output[0] == '(("test_table"."age" - %s) - ("test_table"."score" - %s))'
    assert res._output[1] == [10, 10.5]

def test_313(op_str, col_int, lit_float):
    res = op_str + (col_int + lit_float)
    assert res._output[0] == '(("test_table"."name" || %s) || ("test_table"."age" + %s))'
    assert res._output[1] == ['op_str_param', 10.5]

def test_314(op_int, col_int, lit_int):
    res = op_int + (col_int - lit_int)
    assert res._output[0] == '(("test_table"."age" + %s) + ("test_table"."age" - %s))'
    assert res._output[1] == [1, 10]  

def test_315(op_float, col_int, lit_int):
    res = op_float - (col_int + lit_int)
    assert res._output[0] == '(("test_table"."score" + %s) - ("test_table"."age" + %s))'
    assert res._output[1] == [1.5, 10]

def test_316(col_str, op_str, col_int, op_int):
    res = (col_str + op_str) + (col_int + op_int)
    assert res._output[0] == '(("test_table"."name" || ("test_table"."name" || %s)) || ("test_table"."age" + ("test_table"."age" + %s)))'
    assert res._output[1] == ['op_str_param', 1]

def test_317(col_int, op_int, col_float, op_float):
    res = (col_int - op_int) - (col_float - op_float)
    assert res._output[0] == '(("test_table"."age" - ("test_table"."age" + %s)) - ("test_table"."score" - ("test_table"."score" + %s)))'
    assert res._output[1] == [1, 1.5]

def test_318(lit_str, col_int, op_float):
    res = lit_str + (col_int + op_float)
    assert res._output[0] == '(%s || ("test_table"."age" + ("test_table"."score" + %s)))'
    assert res._output[1] == ['text', 1.5]

def test_319(lit_int, col_str, op_str):
    res = lit_int + (col_str - op_str)
    assert res._output[0] == '(%s || ("test_table"."name" - ("test_table"."name" || %s)))'
    assert res._output[1] == [10, 'op_str_param']

def test_320(lit_float, col_int, op_int):
    res = lit_float - (col_int + op_int)
    assert res._output[0] == '(%s - ("test_table"."age" + ("test_table"."age" + %s)))'
    assert res._output[1] == [10.5, 1]

def test_321(op_str, lit_str, op_int, lit_int):
    res = (op_str + lit_str) + (op_int + lit_int)
    assert res._output[0] == '((("test_table"."name" || %s) || %s) || (("test_table"."age" + %s) + %s))'
    assert res._output[1] == ['op_str_param', 'text', 1, 10]

def test_322(op_int, lit_int, op_float, lit_float):
    res = (op_int - lit_int) - (op_float - lit_float)
    assert res._output[0] == '((("test_table"."age" + %s) - %s) - (("test_table"."score" + %s) - %s))'
    assert res._output[1] == [1, 10, 1.5, 10.5]

def test_323(col_str, op_int, lit_float):
    res = col_str + (op_int + lit_float)
    assert res._output[0] == '("test_table"."name" || (("test_table"."age" + %s) + %s))'
    assert res._output[1] == [1, 10.5]

def test_324(col_int, op_str, lit_str):
    res = col_int + (op_str + lit_str)  
    assert res._output[0] == '("test_table"."age" || (("test_table"."name" || %s) || %s))'
    assert res._output[1] == ['op_str_param', 'text']

def test_325(col_float, op_int, lit_int):
    res = col_float - (op_int + lit_int)
    assert res._output[0] == '("test_table"."score" - (("test_table"."age" + %s) + %s))'
    assert res._output[1] == [1, 10]

def test_326(col_str, op_int):
    res = (col_str + col_str) + op_int
    assert res._output[0] == '(("test_table"."name" || "test_table"."name") || ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_327(col_int, op_str):
    res = (col_int + col_int) - op_str
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") - ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param']

def test_328(col_float, op_float):
    res = (col_float + col_float) + op_float
    assert res._output[0] == '(("test_table"."score" + "test_table"."score") + ("test_table"."score" + %s))'
    assert res._output[1] == [1.5]

def test_329(op_str, col_int):
    res = op_str - (col_int + col_int)
    assert res._output[0] == '(("test_table"."name" || %s) - ("test_table"."age" + "test_table"."age"))'
    assert res._output[1] == ['op_str_param']

def test_330(op_int, col_float):
    res = op_int + (col_float - col_float)
    assert res._output[0] == '(("test_table"."age" + %s) + ("test_table"."score" - "test_table"."score"))'
    assert res._output[1] == [1]

def test_331(lit_str, col_str, op_int):
    res = (lit_str + col_str) + op_int
    assert res._output[0] == '((%s || "test_table"."name") || ("test_table"."age" + %s))'
    assert res._output[1] == ['text', 1]

def test_332(lit_int, col_int, op_str):
    res = (lit_int + col_int) - op_str
    assert res._output[0] == '((%s + "test_table"."age") - ("test_table"."name" || %s))'
    assert res._output[1] == [10, 'op_str_param']

def test_333(lit_float, col_float, op_float):
    res = (lit_float + col_float) + op_float
    assert res._output[0] == '((%s + "test_table"."score") + ("test_table"."score" + %s))'
    assert res._output[1] == [10.5, 1.5]

def test_334(op_str, lit_int, col_int):
    res = op_str - (lit_int + col_int)
    assert res._output[0] == '(("test_table"."name" || %s) - (%s + "test_table"."age"))'
    assert res._output[1] == ['op_str_param', 10]

def test_335(op_int, lit_float, col_float):
    res = op_int + (lit_float - col_float)
    assert res._output[0] == '(("test_table"."age" + %s) + (%s - "test_table"."score"))'
    assert res._output[1] == [1, 10.5]

def test_336(op_str, col_int):
    res = (op_str + op_str) + col_int
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."name" || %s)) || "test_table"."age")'
    assert res._output[1] == ['op_str_param', 'op_str_param']

def test_337(op_int, col_str):
    res = (op_int + op_int) - col_str
    assert res._output[0] == '((("test_table"."age" + %s) + ("test_table"."age" + %s)) - "test_table"."name")'
    assert res._output[1] == [1, 1]

def test_338(op_float, col_float):
    res = (op_float + op_float) + col_float
    assert res._output[0] == '((("test_table"."score" + %s) + ("test_table"."score" + %s)) + "test_table"."score")'
    assert res._output[1] == [1.5, 1.5]

def test_339(col_str, op_int):
    res = col_str - (op_int + op_int)
    assert res._output[0] == '("test_table"."name" - (("test_table"."age" + %s) + ("test_table"."age" + %s)))'
    assert res._output[1] == [1, 1]

def test_340(col_int, op_float):
    res = col_int + (op_float - op_float)
    assert res._output[0] == '("test_table"."age" + (("test_table"."score" + %s) - ("test_table"."score" + %s)))'
    assert res._output[1] == [1.5, 1.5]

def test_341(lit_str, op_str, col_int):
    res = (lit_str + op_str) + col_int
    assert res._output[0] == '((%s || ("test_table"."name" || %s)) || "test_table"."age")'
    assert res._output[1] == ['text', 'op_str_param']

def test_342(lit_int, op_int, col_str):
    res = (lit_int + op_int) - col_str
    assert res._output[0] == '((%s + ("test_table"."age" + %s)) - "test_table"."name")'
    assert res._output[1] == [10, 1]

def test_343(lit_float, op_float, col_float):
    res = (lit_float + op_float) + col_float
    assert res._output[0] == '((%s + ("test_table"."score" + %s)) + "test_table"."score")'
    assert res._output[1] == [10.5, 1.5]

def test_344(col_str, lit_int, op_int):
    res = col_str - (lit_int + op_int)
    assert res._output[0] == '("test_table"."name" - (%s + ("test_table"."age" + %s)))'
    assert res._output[1] == [10, 1]

def test_345(col_int, lit_float, op_float):
    res = col_int + (lit_float - op_float)
    assert res._output[0] == '("test_table"."age" + (%s - ("test_table"."score" + %s)))'
    assert res._output[1] == [10.5, 1.5]

def test_346(col_str, lit_int, op_float):
    res = (col_str + lit_int) + op_float
    assert res._output[0] == '(("test_table"."name" || %s) || ("test_table"."score" + %s))'
    assert res._output[1] == [10, 1.5]

def test_347(col_int, lit_str, op_int):
    res = (col_int - lit_str) - op_int
    assert res._output[0] == '(("test_table"."age" - %s) - ("test_table"."age" + %s))'
    assert res._output[1] == ['text', 1]

def test_348(op_str, col_float, lit_int):
    res = op_str + (col_float - lit_int)
    assert res._output[0] == '(("test_table"."name" || %s) || ("test_table"."score" - %s))'
    assert res._output[1] == ['op_str_param', 10]

def test_349(op_int, col_int, lit_int):
    res = op_int - (col_int - lit_int)
    assert res._output[0] == '(("test_table"."age" + %s) - ("test_table"."age" - %s))'
    assert res._output[1] == [1, 10]

def test_350(op_float, col_int, lit_str):
    res = op_float + (col_int - lit_str)
    assert res._output[0] == '(("test_table"."score" + %s) + ("test_table"."age" - %s))'
    assert res._output[1] == [1.5, 'text']

def test_351(col_str, col_int, col_float, lit_str):
    res = ((col_str + col_int) + col_float) + lit_str
    assert res._output[0] == '((("test_table"."name" || "test_table"."age") || "test_table"."score") || %s)'
    assert res._output[1] == ['text']

def test_352(col_int, col_float, col_str, lit_int):
    res = ((col_int - col_float) - col_str) - lit_int
    assert res._output[0] == '((("test_table"."age" - "test_table"."score") - "test_table"."name") - %s)'
    assert res._output[1] == [10]

def test_353(lit_str, col_str, col_int, col_float):
    res = lit_str + ((col_str + col_int) + col_float)
    assert res._output[0] == '(%s || (("test_table"."name" || "test_table"."age") || "test_table"."score"))'
    assert res._output[1] == ['text']

def test_354(lit_int, col_int, col_float, col_str):
    res = lit_int - ((col_int - col_float) - col_str)
    assert res._output[0] == '(%s - (("test_table"."age" - "test_table"."score") - "test_table"."name"))'
    assert res._output[1] == [10]

def test_355(col_str, col_int, col_float, lit_str):
    res = (col_str + (col_int + col_float)) + lit_str
    assert res._output[0] == '(("test_table"."name" || ("test_table"."age" + "test_table"."score")) || %s)'
    assert res._output[1] == ['text']

def test_356(col_int, col_float, col_str, lit_int):
    res = (col_int - (col_float - col_str)) - lit_int
    assert res._output[0] == '(("test_table"."age" - ("test_table"."score" - "test_table"."name")) - %s)'
    assert res._output[1] == [10]

def test_357(lit_str, col_str, col_int, col_float):
    res = lit_str + (col_str + (col_int + col_float))
    assert res._output[0] == '(%s || ("test_table"."name" || ("test_table"."age" + "test_table"."score")))'
    assert res._output[1] == ['text']

def test_358(lit_int, col_int, col_float, col_str):
    res = lit_int - (col_int - (col_float - col_str))
    assert res._output[0] == '(%s - ("test_table"."age" - ("test_table"."score" - "test_table"."name")))'
    assert res._output[1] == [10]

def test_359(op_str, op_int, op_float, lit_str):
    res = ((op_str + op_int) + op_float) + lit_str
    assert res._output[0] == '(((("test_table"."name" || %s) || ("test_table"."age" + %s)) || ("test_table"."score" + %s)) || %s)'
    assert res._output[1] == ['op_str_param', 1, 1.5, 'text']

def test_360(op_int, op_float, op_str, lit_int):
    res = ((op_int - op_float) - op_str) - lit_int
    assert res._output[0] == '(((("test_table"."age" + %s) - ("test_table"."score" + %s)) - ("test_table"."name" || %s)) - %s)'
    assert res._output[1] == [1, 1.5, 'op_str_param', 10]

def test_361(lit_str, op_str, op_int, op_float):
    res = lit_str + ((op_str + op_int) + op_float)
    assert res._output[0] == '(%s || ((("test_table"."name" || %s) || ("test_table"."age" + %s)) || ("test_table"."score" + %s)))'
    assert res._output[1] == ['text', 'op_str_param', 1, 1.5]

def test_362(lit_int, op_int, op_float, op_str):
    res = lit_int - ((op_int - op_float) - op_str)
    assert res._output[0] == '(%s - ((("test_table"."age" + %s) - ("test_table"."score" + %s)) - ("test_table"."name" || %s)))'
    assert res._output[1] == [10, 1, 1.5, 'op_str_param']

def test_363(op_str, op_int, op_float, lit_str):
    res = (op_str + (op_int + op_float)) + lit_str
    assert res._output[0] == '((("test_table"."name" || %s) || (("test_table"."age" + %s) + ("test_table"."score" + %s))) || %s)'
    assert res._output[1] == ['op_str_param', 1, 1.5, 'text']

def test_364(op_int, op_float, op_str, lit_int):
    res = (op_int - (op_float - op_str)) - lit_int
    assert res._output[0] == '((("test_table"."age" + %s) - (("test_table"."score" + %s) - ("test_table"."name" || %s))) - %s)'
    assert res._output[1] == [1, 1.5, 'op_str_param', 10]

def test_365(lit_str, op_str, op_int, op_float):
    res = lit_str + (op_str + (op_int + op_float))
    assert res._output[0] == '(%s || (("test_table"."name" || %s) || (("test_table"."age" + %s) + ("test_table"."score" + %s))))'
    assert res._output[1] == ['text', 'op_str_param', 1, 1.5]

def test_366(lit_int, op_int, op_float, op_str):
    res = lit_int - (op_int - (op_float - op_str))
    assert res._output[0] == '(%s - (("test_table"."age" + %s) - (("test_table"."score" + %s) - ("test_table"."name" || %s))))'
    assert res._output[1] == [10, 1, 1.5, 'op_str_param']

def test_367(col_str, op_str, lit_int, col_float):
    res = ((col_str + op_str) + lit_int) + col_float
    assert res._output[0] == '((("test_table"."name" || ("test_table"."name" || %s)) || %s) || "test_table"."score")'
    assert res._output[1] == ['op_str_param', 10]

def test_368(col_int, op_int, lit_str, col_float):
    res = ((col_int - op_int) - lit_str) - col_float
    assert res._output[0] == '((("test_table"."age" - ("test_table"."age" + %s)) - %s) - "test_table"."score")'
    assert res._output[1] == [1, 'text']

def test_369(col_str, op_int, col_float, lit_str):
    res = col_str + ((op_int + col_float) + lit_str)
    assert res._output[0] == '("test_table"."name" || ((("test_table"."age" + %s) + "test_table"."score") || %s))'
    assert res._output[1] == [1, 'text']

def test_370(col_int, op_float, col_str, lit_int):
    res = col_int - ((op_float - col_str) - lit_int)
    assert res._output[0] == '("test_table"."age" - ((("test_table"."score" + %s) - "test_table"."name") - %s))'
    assert res._output[1] == [1.5, 10]

def test_371(col_str, op_str, lit_int, col_float):
    res = (col_str + (op_str + lit_int)) + col_float
    assert res._output[0] == '(("test_table"."name" || (("test_table"."name" || %s) || %s)) || "test_table"."score")'
    assert res._output[1] == ['op_str_param', 10]

def test_372(col_int, op_int, lit_str, col_float):
    res = (col_int - (op_int - lit_str)) - col_float
    assert res._output[0] == '(("test_table"."age" - (("test_table"."age" + %s) - %s)) - "test_table"."score")'
    assert res._output[1] == [1, 'text']

def test_373(col_str, op_str, lit_int, col_float):
    res = col_str + (op_str + (lit_int + col_float))
    assert res._output[0] == '("test_table"."name" || (("test_table"."name" || %s) || (%s + "test_table"."score")))'
    assert res._output[1] == ['op_str_param', 10]

def test_374(col_int, op_int, lit_str, col_float):
    res = col_int - (op_int - (lit_str - col_float))
    assert res._output[0] == '("test_table"."age" - (("test_table"."age" + %s) - (%s - "test_table"."score")))'
    assert res._output[1] == [1, 'text']

def test_375(lit_str, col_str, op_int, col_float):
    res = ((lit_str + col_str) + op_int) + col_float
    assert res._output[0] == '(((%s || "test_table"."name") || ("test_table"."age" + %s)) || "test_table"."score")'
    assert res._output[1] == ['text', 1]

def test_376(lit_int, col_int, op_str, col_float):
    res = ((lit_int - col_int) - op_str) - col_float
    assert res._output[0] == '(((%s - "test_table"."age") - ("test_table"."name" || %s)) - "test_table"."score")'
    assert res._output[1] == [10, 'op_str_param']

def test_377(op_str, col_int, col_float, lit_str):
    res = op_str + ((col_int + col_float) + lit_str)
    assert res._output[0] == '(("test_table"."name" || %s) || (("test_table"."age" + "test_table"."score") || %s))'
    assert res._output[1] == ['op_str_param', 'text']

def test_378(op_int, col_float, col_str, lit_int):
    res = op_int - ((col_float - col_str) - lit_int)
    assert res._output[0] == '(("test_table"."age" + %s) - (("test_table"."score" - "test_table"."name") - %s))'
    assert res._output[1] == [1, 10]

def test_379(lit_str, col_str, op_int, col_float):
    res = (lit_str + (col_str + op_int)) + col_float
    assert res._output[0] == '((%s || ("test_table"."name" || ("test_table"."age" + %s))) || "test_table"."score")'
    assert res._output[1] == ['text', 1]

def test_380(lit_int, col_int, op_str, col_float):
    res = (lit_int - (col_int - op_str)) - col_float
    assert res._output[0] == '((%s - ("test_table"."age" - ("test_table"."name" || %s))) - "test_table"."score")'
    assert res._output[1] == [10, 'op_str_param']

def test_381(op_str, col_int, col_float, lit_str):
    res = op_str + (col_int + (col_float + lit_str))
    assert res._output[0] == '(("test_table"."name" || %s) || ("test_table"."age" || ("test_table"."score" || %s)))'
    assert res._output[1] == ['op_str_param', 'text']

def test_382(op_int, col_float, col_str, lit_int):
    res = op_int - (col_float - (col_str - lit_int))
    assert res._output[0] == '(("test_table"."age" + %s) - ("test_table"."score" - ("test_table"."name" - %s)))'
    assert res._output[1] == [1, 10]

def test_383(col_str, lit_str, col_int, op_float):
    res = ((col_str + lit_str) + col_int) + op_float
    assert res._output[0] == '((("test_table"."name" || %s) || "test_table"."age") || ("test_table"."score" + %s))'
    assert res._output[1] == ['text', 1.5]

def test_384(col_int, lit_int, col_float, op_str):
    res = ((col_int - lit_int) - col_float) - op_str
    assert res._output[0] == '((("test_table"."age" - %s) - "test_table"."score") - ("test_table"."name" || %s))'
    assert res._output[1] == [10, 'op_str_param']

def test_385(lit_str, col_int, col_float, op_str):
    res = lit_str + ((col_int + col_float) + op_str)
    assert res._output[0] == '(%s || (("test_table"."age" + "test_table"."score") || ("test_table"."name" || %s)))'
    assert res._output[1] == ['text', 'op_str_param']

def test_386(lit_int, col_float, col_int, op_float):
    res = lit_int - ((col_float - col_int) - op_float)
    assert res._output[0] == '(%s - (("test_table"."score" - "test_table"."age") - ("test_table"."score" + %s)))'
    assert res._output[1] == [10, 1.5]

def test_387(col_str, lit_str, col_int, op_float):
    res = (col_str + (lit_str + col_int)) + op_float
    assert res._output[0] == '(("test_table"."name" || (%s || "test_table"."age")) || ("test_table"."score" + %s))'
    assert res._output[1] == ['text', 1.5]

def test_388(col_int, lit_int, col_float, op_str):
    res = (col_int - (lit_int - col_float)) - op_str
    assert res._output[0] == '(("test_table"."age" - (%s - "test_table"."score")) - ("test_table"."name" || %s))'
    assert res._output[1] == [10, 'op_str_param']

def test_389(lit_str, col_int, col_float, op_str):
    res = lit_str + (col_int + (col_float + op_str))
    assert res._output[0] == '(%s || ("test_table"."age" || ("test_table"."score" || ("test_table"."name" || %s))))'
    assert res._output[1] == ['text', 'op_str_param']

def test_390(lit_int, col_float, col_int, op_float):
    res = lit_int - (col_float - (col_int - op_float))
    assert res._output[0] == '(%s - ("test_table"."score" - ("test_table"."age" - ("test_table"."score" + %s))))'
    assert res._output[1] == [10, 1.5]

def test_391(op_str, lit_str, op_int, col_float):
    res = ((op_str + lit_str) + op_int) + col_float
    assert res._output[0] == '(((("test_table"."name" || %s) || %s) || ("test_table"."age" + %s)) || "test_table"."score")'
    assert res._output[1] == ['op_str_param', 'text', 1]

def test_392(op_int, lit_int, op_float, col_str):
    res = ((op_int - lit_int) - op_float) - col_str
    assert res._output[0] == '(((("test_table"."age" + %s) - %s) - ("test_table"."score" + %s)) - "test_table"."name")'
    assert res._output[1] == [1, 10, 1.5]

def test_393(col_str, op_int, op_float, lit_str):
    res = col_str + ((op_int + op_float) + lit_str)
    assert res._output[0] == '("test_table"."name" || ((("test_table"."age" + %s) + ("test_table"."score" + %s)) || %s))'
    assert res._output[1] == [1, 1.5, 'text']

def test_394(col_int, op_float, op_str, lit_int):
    res = col_int - ((op_float - op_str) - lit_int)
    assert res._output[0] == '("test_table"."age" - ((("test_table"."score" + %s) - ("test_table"."name" || %s)) - %s))'
    assert res._output[1] == [1.5, 'op_str_param', 10]

def test_395(op_str, lit_str, op_int, col_float):
    res = (op_str + (lit_str + op_int)) + col_float
    assert res._output[0] == '((("test_table"."name" || %s) || (%s || ("test_table"."age" + %s))) || "test_table"."score")'
    assert res._output[1] == ['op_str_param', 'text', 1]

def test_396(op_int, lit_int, op_float, col_str):
    res = (op_int - (lit_int - op_float)) - col_str
    assert res._output[0] == '((("test_table"."age" + %s) - (%s - ("test_table"."score" + %s))) - "test_table"."name")'
    assert res._output[1] == [1, 10, 1.5]

def test_397(col_str, op_int, op_float, lit_str):
    res = col_str + (op_int + (op_float + lit_str))
    assert res._output[0] == '("test_table"."name" || (("test_table"."age" + %s) || (("test_table"."score" + %s) || %s)))'
    assert res._output[1] == [1, 1.5, 'text']

def test_398(col_int, op_float, op_str, lit_int):
    res = col_int - (op_float - (op_str - lit_int))
    assert res._output[0] == '("test_table"."age" - (("test_table"."score" + %s) - (("test_table"."name" || %s) - %s)))'
    assert res._output[1] == [1.5, 'op_str_param', 10]

def test_399(col_str, col_int, lit_str, op_float):
    res = ((col_str + col_int) + lit_str) + (op_float + col_str)
    assert res._output[0] == '((("test_table"."name" || "test_table"."age") || %s) || (("test_table"."score" + %s) || "test_table"."name"))'
    assert res._output[1] == ['text', 1.5]

def test_400(col_int, col_float, lit_int, op_str):
    res = ((col_int - col_float) - lit_int) - (op_str - col_float)
    assert res._output[0] == '((("test_table"."age" - "test_table"."score") - %s) - (("test_table"."name" || %s) - "test_table"."score"))'
    assert res._output[1] == [10, 'op_str_param']

def test_401(col_str, col_int, col_float, lit_int):
    res = (col_str + col_int) + (col_float + (col_str + lit_int))
    assert res._output[0] == '(("test_table"."name" || "test_table"."age") || ("test_table"."score" || ("test_table"."name" || %s)))'
    assert res._output[1] == [10]

def test_402(col_int, col_float, col_str, lit_float):
    res = (col_int - col_float) - (col_str - (col_int - lit_float))
    assert res._output[0] == '(("test_table"."age" - "test_table"."score") - ("test_table"."name" - ("test_table"."age" - %s)))'
    assert res._output[1] == [10.5]

def test_403(lit_str, col_int, col_float, col_str, lit_int):
    res = lit_str + ((col_int + col_float) + (col_str + lit_int))
    assert res._output[0] == '(%s || (("test_table"."age" + "test_table"."score") || ("test_table"."name" || %s)))'
    assert res._output[1] == ['text', 10]

def test_404(lit_int, col_str, col_float, col_int, lit_str):
    res = lit_int - ((col_str - col_float) - (col_int - lit_str))
    assert res._output[0] == '(%s - (("test_table"."name" - "test_table"."score") - ("test_table"."age" - %s)))'
    assert res._output[1] == [10, 'text']

def test_405(col_str, col_int, col_float, lit_str):
    res = ((col_str + (col_int + col_float)) + lit_str) + col_int
    assert res._output[0] == '((("test_table"."name" || ("test_table"."age" + "test_table"."score")) || %s) || "test_table"."age")'
    assert res._output[1] == ['text']

def test_406(col_int, col_float, col_str, lit_int):
    res = ((col_int - (col_float - col_str)) - lit_int) - col_float
    assert res._output[0] == '((("test_table"."age" - ("test_table"."score" - "test_table"."name")) - %s) - "test_table"."score")'
    assert res._output[1] == [10]

def test_407(col_str, col_int, col_float, lit_str):
    res = (col_str + ((col_int + col_float) + lit_str)) + col_int
    assert res._output[0] == '(("test_table"."name" || (("test_table"."age" + "test_table"."score") || %s)) || "test_table"."age")'
    assert res._output[1] == ['text']

def test_408(col_int, col_float, col_str, lit_int):
    res = (col_int - ((col_float - col_str) - lit_int)) - col_float
    assert res._output[0] == '(("test_table"."age" - (("test_table"."score" - "test_table"."name") - %s)) - "test_table"."score")'
    assert res._output[1] == [10]

def test_409(col_str, col_int, col_float, lit_str):
    res = (((col_str + col_int) + col_float) + lit_str) + col_int
    assert res._output[0] == '(((("test_table"."name" || "test_table"."age") || "test_table"."score") || %s) || "test_table"."age")'
    assert res._output[1] == ['text']

def test_410(col_int, col_float, col_str, lit_int):
    res = (((col_int - col_float) - col_str) - lit_int) - col_float
    assert res._output[0] == '(((("test_table"."age" - "test_table"."score") - "test_table"."name") - %s) - "test_table"."score")'
    assert res._output[1] == [10]

def test_411(op_str, op_int, op_float, lit_int):
    res = (op_str + op_int) + (op_float + (op_str + lit_int))
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."age" + %s)) || (("test_table"."score" + %s) || (("test_table"."name" || %s) || %s)))'
    assert res._output[1] == ['op_str_param', 1, 1.5, 'op_str_param', 10]

def test_412(op_int, op_float, op_str, lit_float):
    res = (op_int - op_float) - (op_str - (op_int - lit_float))
    assert res._output[0] == '((("test_table"."age" + %s) - ("test_table"."score" + %s)) - (("test_table"."name" || %s) - (("test_table"."age" + %s) - %s)))'
    assert res._output[1] == [1, 1.5, 'op_str_param', 1, 10.5]

def test_413(lit_str, op_int, op_float, op_str, lit_int):
    res = lit_str + ((op_int + op_float) + (op_str + lit_int))
    assert res._output[0] == '(%s || ((("test_table"."age" + %s) + ("test_table"."score" + %s)) || (("test_table"."name" || %s) || %s)))'
    assert res._output[1] == ['text', 1, 1.5, 'op_str_param', 10]

def test_414(lit_int, op_str, op_float, op_int, lit_str):
    res = lit_int - ((op_str - op_float) - (op_int - lit_str))
    assert res._output[0] == '(%s - ((("test_table"."name" || %s) - ("test_table"."score" + %s)) - (("test_table"."age" + %s) - %s)))'
    assert res._output[1] == [10, 'op_str_param', 1.5, 1, 'text']

def test_415(op_str, op_int, op_float, lit_str):
    res = ((op_str + (op_int + op_float)) + lit_str) + op_int
    assert res._output[0] == '(((("test_table"."name" || %s) || (("test_table"."age" + %s) + ("test_table"."score" + %s))) || %s) || ("test_table"."age" + %s))'
    assert res._output[1] == ['op_str_param', 1, 1.5, 'text', 1]

def test_416(op_int, op_float, op_str, lit_int):
    res = ((op_int - (op_float - op_str)) - lit_int) - op_float
    assert res._output[0] == '(((("test_table"."age" + %s) - (("test_table"."score" + %s) - ("test_table"."name" || %s))) - %s) - ("test_table"."score" + %s))'
    assert res._output[1] == [1, 1.5, 'op_str_param', 10, 1.5]

def test_417(op_str, op_int, op_float, lit_str):
    res = (op_str + ((op_int + op_float) + lit_str)) + op_int
    assert res._output[0] == '((("test_table"."name" || %s) || ((("test_table"."age" + %s) + ("test_table"."score" + %s)) || %s)) || ("test_table"."age" + %s))'
    assert res._output[1] == ['op_str_param', 1, 1.5, 'text', 1]

def test_418(op_int, op_float, op_str, lit_int):
    res = (op_int - ((op_float - op_str) - lit_int)) - op_float
    assert res._output[0] == '((("test_table"."age" + %s) - ((("test_table"."score" + %s) - ("test_table"."name" || %s)) - %s)) - ("test_table"."score" + %s))'
    assert res._output[1] == [1, 1.5, 'op_str_param', 10, 1.5]

def test_419(op_str, op_int, op_float, lit_str):
    res = (((op_str + op_int) + op_float) + lit_str) + op_int
    assert res._output[0] == '((((("test_table"."name" || %s) || ("test_table"."age" + %s)) || ("test_table"."score" + %s)) || %s) || ("test_table"."age" + %s))'
    assert res._output[1] == ['op_str_param', 1, 1.5, 'text', 1]

def test_420(op_int, op_float, op_str, lit_int):
    res = (((op_int - op_float) - op_str) - lit_int) - op_float
    assert res._output[0] == '((((("test_table"."age" + %s) - ("test_table"."score" + %s)) - ("test_table"."name" || %s)) - %s) - ("test_table"."score" + %s))'
    assert res._output[1] == [1, 1.5, 'op_str_param', 10, 1.5]

def test_421(col_str, op_str, col_int, op_float, lit_str):
    res = (col_str + op_str) + (col_int + (op_float + lit_str))
    assert res._output[0] == '(("test_table"."name" || ("test_table"."name" || %s)) || ("test_table"."age" || (("test_table"."score" + %s) || %s)))'
    assert res._output[1] == ['op_str_param', 1.5, 'text']

def test_422(col_int, op_int, col_float, op_str, lit_int):
    res = (col_int - op_int) - (col_float - (op_str - lit_int))
    assert res._output[0] == '(("test_table"."age" - ("test_table"."age" + %s)) - ("test_table"."score" - (("test_table"."name" || %s) - %s)))'
    assert res._output[1] == [1, 'op_str_param', 10]

def test_423(lit_float, col_int, op_float, col_str, op_int):
    res = lit_float + ((col_int + op_float) + (col_str + op_int))
    assert res._output[0] == '(%s || (("test_table"."age" + ("test_table"."score" + %s)) || ("test_table"."name" || ("test_table"."age" + %s))))'
    assert res._output[1] == [10.5, 1.5, 1]

def test_424(lit_str, col_str, op_int, col_int, op_float):
    res = lit_str - ((col_str - op_int) - (col_int - op_float))
    assert res._output[0] == '(%s - (("test_table"."name" - ("test_table"."age" + %s)) - ("test_table"."age" - ("test_table"."score" + %s))))'
    assert res._output[1] == ['text', 1, 1.5]

def test_425(col_str, op_int, col_float, lit_str):
    res = ((col_str + (op_int + col_float)) + lit_str) + op_int
    assert res._output[0] == '((("test_table"."name" || (("test_table"."age" + %s) + "test_table"."score")) || %s) || ("test_table"."age" + %s))'
    assert res._output[1] == [1, 'text', 1]

def test_426(col_int, op_float, col_str, lit_int, op_str):
    res = ((col_int - (op_float - col_str)) - lit_int) - op_str
    assert res._output[0] == '((("test_table"."age" - (("test_table"."score" + %s) - "test_table"."name")) - %s) - ("test_table"."name" || %s))'
    assert res._output[1] == [1.5, 10, 'op_str_param']

def test_427(col_str, op_int, col_float, lit_str):
    res = (col_str + ((op_int + col_float) + lit_str)) + op_int
    assert res._output[0] == '(("test_table"."name" || ((("test_table"."age" + %s) + "test_table"."score") || %s)) || ("test_table"."age" + %s))'
    assert res._output[1] == [1, 'text', 1]

def test_428(col_int, op_float, col_str, lit_int, op_str):
    res = (col_int - ((op_float - col_str) - lit_int)) - op_str
    assert res._output[0] == '(("test_table"."age" - ((("test_table"."score" + %s) - "test_table"."name") - %s)) - ("test_table"."name" || %s))'
    assert res._output[1] == [1.5, 10, 'op_str_param']

def test_429(col_str, op_int, col_float, lit_str):
    res = (((col_str + op_int) + col_float) + lit_str) + op_int
    assert res._output[0] == '(((("test_table"."name" || ("test_table"."age" + %s)) || "test_table"."score") || %s) || ("test_table"."age" + %s))'
    assert res._output[1] == [1, 'text', 1]

def test_430(col_int, op_float, col_str, lit_int, op_str):
    res = (((col_int - op_float) - col_str) - lit_int) - op_str
    assert res._output[0] == '(((("test_table"."age" - ("test_table"."score" + %s)) - "test_table"."name") - %s) - ("test_table"."name" || %s))'
    assert res._output[1] == [1.5, 10, 'op_str_param']

def test_431(lit_str, col_str, op_int, col_float, lit_int):
    res = (lit_str + col_str) + (op_int + (col_float + lit_int))
    assert res._output[0] == '((%s || "test_table"."name") || (("test_table"."age" + %s) + ("test_table"."score" + %s)))'
    assert res._output[1] == ['text', 1, 10]

def test_432(lit_int, col_int, op_float, col_str, lit_float):
    res = (lit_int - col_int) - (op_float - (col_str - lit_float))
    assert res._output[0] == '((%s - "test_table"."age") - (("test_table"."score" + %s) - ("test_table"."name" - %s)))'
    assert res._output[1] == [10, 1.5, 10.5]

def test_433(op_str, lit_int, col_float, col_int):
    res = op_str + ((lit_int + col_float) + (op_str + col_int))
    assert res._output[0] == '(("test_table"."name" || %s) || ((%s + "test_table"."score") || (("test_table"."name" || %s) || "test_table"."age")))'
    assert res._output[1] == ['op_str_param', 10, 'op_str_param']

def test_434(op_int, lit_str, op_float, col_int, op_str):
    res = op_int - ((lit_str - op_float) - (col_int - op_str))
    assert res._output[0] == '(("test_table"."age" + %s) - ((%s - ("test_table"."score" + %s)) - ("test_table"."age" - ("test_table"."name" || %s))))'
    assert res._output[1] == [1, 'text', 1.5, 'op_str_param']

def test_435(lit_str, col_int, op_float, lit_int, col_str):
    res = ((lit_str + (col_int + op_float)) + lit_int) + col_str
    assert res._output[0] == '(((%s || ("test_table"."age" + ("test_table"."score" + %s))) || %s) || "test_table"."name")'
    assert res._output[1] == ['text', 1.5, 10]

def test_436(lit_int, op_float, col_str, lit_str, col_int):
    res = ((lit_int - (op_float - col_str)) - lit_str) - col_int
    assert res._output[0] == '(((%s - (("test_table"."score" + %s) - "test_table"."name")) - %s) - "test_table"."age")'
    assert res._output[1] == [10, 1.5, 'text']

def test_437(lit_str, col_int, op_float, lit_int, col_str):
    res = (lit_str + ((col_int + op_float) + lit_int)) + col_str
    assert res._output[0] == '((%s || (("test_table"."age" + ("test_table"."score" + %s)) + %s)) || "test_table"."name")'
    assert res._output[1] == ['text', 1.5, 10]

def test_438(lit_int, op_float, col_str, lit_str, col_int):
    res = (lit_int - ((op_float - col_str) - lit_str)) - col_int
    assert res._output[0] == '((%s - ((("test_table"."score" + %s) - "test_table"."name") - %s)) - "test_table"."age")'
    assert res._output[1] == [10, 1.5, 'text']

def test_439(lit_str, col_int, op_float, lit_int, col_str):
    res = (((lit_str + col_int) + op_float) + lit_int) + col_str
    assert res._output[0] == '((((%s || "test_table"."age") || ("test_table"."score" + %s)) || %s) || "test_table"."name")'
    assert res._output[1] == ['text', 1.5, 10]

def test_440(lit_int, op_float, col_str, lit_str, col_int):
    res = (((lit_int - op_float) - col_str) - lit_str) - col_int
    assert res._output[0] == '((((%s - ("test_table"."score" + %s)) - "test_table"."name") - %s) - "test_table"."age")'
    assert res._output[1] == [10, 1.5, 'text']

def test_441(col_str, lit_str, op_int, col_float, op_str):
    res = (col_str + lit_str) + (op_int + (col_float + op_str))
    assert res._output[0] == '(("test_table"."name" || %s) || (("test_table"."age" + %s) || ("test_table"."score" || ("test_table"."name" || %s))))'
    assert res._output[1] == ['text', 1, 'op_str_param']

def test_442(col_int, lit_int, op_float, col_str, op_int):
    res = (col_int - lit_int) - (op_float - (col_str - op_int))
    assert res._output[0] == '(("test_table"."age" - %s) - (("test_table"."score" + %s) - ("test_table"."name" - ("test_table"."age" + %s))))'
    assert res._output[1] == [10, 1.5, 1]

def test_443(op_str, col_int, lit_float):
    res = op_str + ((col_int + lit_float) + (op_str + col_int))
    assert res._output[0] == '(("test_table"."name" || %s) || (("test_table"."age" + %s) || (("test_table"."name" || %s) || "test_table"."age")))'
    assert res._output[1] == ['op_str_param', 10.5, 'op_str_param']

def test_444(op_int, col_str, lit_float, col_int, op_str):
    res = op_int - ((col_str - lit_float) - (col_int - op_str))
    assert res._output[0] == '(("test_table"."age" + %s) - (("test_table"."name" - %s) - ("test_table"."age" - ("test_table"."name" || %s))))'
    assert res._output[1] == [1, 10.5, 'op_str_param']

def test_445(col_str, lit_int, op_float, op_str, col_int):
    res = ((col_str + (lit_int + op_float)) + op_str) + col_int
    assert res._output[0] == '((("test_table"."name" || (%s + ("test_table"."score" + %s))) || ("test_table"."name" || %s)) || "test_table"."age")'
    assert res._output[1] == [10, 1.5, 'op_str_param']

def test_446(col_int, lit_float, col_str, op_int, col_float):
    res = ((col_int - (lit_float - col_str)) - op_int) - col_float
    assert res._output[0] == '((("test_table"."age" - (%s - "test_table"."name")) - ("test_table"."age" + %s)) - "test_table"."score")'
    assert res._output[1] == [10.5, 1]

def test_447(col_str, lit_int, op_float, op_str, col_int):
    res = (col_str + ((lit_int + op_float) + op_str)) + col_int
    assert res._output[0] == '(("test_table"."name" || ((%s + ("test_table"."score" + %s)) || ("test_table"."name" || %s))) || "test_table"."age")'
    assert res._output[1] == [10, 1.5, 'op_str_param']

def test_448(col_int, lit_float, col_str, op_int, col_float):
    res = (col_int - ((lit_float - col_str) - op_int)) - col_float
    assert res._output[0] == '(("test_table"."age" - ((%s - "test_table"."name") - ("test_table"."age" + %s))) - "test_table"."score")'
    assert res._output[1] == [10.5, 1]

def test_449(col_str, lit_int, op_float, op_str, col_int):
    res = (((col_str + lit_int) + op_float) + op_str) + col_int
    assert res._output[0] == '(((("test_table"."name" || %s) || ("test_table"."score" + %s)) || ("test_table"."name" || %s)) || "test_table"."age")'
    assert res._output[1] == [10, 1.5, 'op_str_param']

def test_450(col_int, lit_float, col_str, op_int, col_float):
    res = (((col_int - lit_float) - col_str) - op_int) - col_float
    assert res._output[0] == '(((("test_table"."age" - %s) - "test_table"."name") - ("test_table"."age" + %s)) - "test_table"."score")'
    assert res._output[1] == [10.5, 1]

def test_451(col_str, lit_str):
    res = col_str + (col_str + (col_str + (col_str + lit_str)))
    assert res._output[0] == '("test_table"."name" || ("test_table"."name" || ("test_table"."name" || ("test_table"."name" || %s))))'
    assert res._output[1] == ['text']

def test_452(col_int, lit_int):
    res = col_int - (col_int - (col_int - (col_int - lit_int)))
    assert res._output[0] == '("test_table"."age" - ("test_table"."age" - ("test_table"."age" - ("test_table"."age" - %s))))'
    assert res._output[1] == [10]

def test_453(lit_str, col_str):
    res = lit_str + (lit_str + (lit_str + (lit_str + col_str)))
    assert res._output[0] == '(%s || (%s || (%s || (%s || "test_table"."name"))))'
    assert res._output[1] == ['text', 'text', 'text', 'text']

def test_454(lit_int, col_int):
    res = lit_int - (lit_int - (lit_int - (lit_int - col_int)))
    assert res._output[0] == '(%s - (%s - (%s - (%s - "test_table"."age"))))'
    assert res._output[1] == [10, 10, 10, 10]

def test_455(col_str):
    res = ((((col_str + col_str) + col_str) + col_str) + col_str)
    assert res._output[0] == '(((("test_table"."name" || "test_table"."name") || "test_table"."name") || "test_table"."name") || "test_table"."name")'
    assert res._output[1] == []

def test_456(col_int):
    res = ((((col_int - col_int) - col_int) - col_int) - col_int)
    assert res._output[0] == '(((("test_table"."age" - "test_table"."age") - "test_table"."age") - "test_table"."age") - "test_table"."age")'
    assert res._output[1] == []

def test_457(op_str):
    res = ((((op_str + op_str) + op_str) + op_str) + op_str)
    assert res._output[0] == '((((("test_table"."name" || %s) || ("test_table"."name" || %s)) || ("test_table"."name" || %s)) || ("test_table"."name" || %s)) || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param', 'op_str_param', 'op_str_param', 'op_str_param', 'op_str_param']

def test_458(op_int):
    res = ((((op_int - op_int) - op_int) - op_int) - op_int)
    assert res._output[0] == '((((("test_table"."age" + %s) - ("test_table"."age" + %s)) - ("test_table"."age" + %s)) - ("test_table"."age" + %s)) - ("test_table"."age" + %s))'
    assert res._output[1] == [1, 1, 1, 1, 1]

def test_459(col_str):
    res = col_str + col_str + col_str + col_str + col_str
    assert res._output[0] == '(((("test_table"."name" || "test_table"."name") || "test_table"."name") || "test_table"."name") || "test_table"."name")'
    assert res._output[1] == []

def test_460(col_int):
    res = col_int - col_int - col_int - col_int - col_int
    assert res._output[0] == '(((("test_table"."age" - "test_table"."age") - "test_table"."age") - "test_table"."age") - "test_table"."age")'
    assert res._output[1] == []

def test_461(op_str):
    res = op_str + op_str + op_str + op_str + op_str
    assert res._output[0] == '((((("test_table"."name" || %s) || ("test_table"."name" || %s)) || ("test_table"."name" || %s)) || ("test_table"."name" || %s)) || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param', 'op_str_param', 'op_str_param', 'op_str_param', 'op_str_param']

def test_462(op_int):
    res = op_int - op_int - op_int - op_int - op_int
    assert res._output[0] == '((((("test_table"."age" + %s) - ("test_table"."age" + %s)) - ("test_table"."age" + %s)) - ("test_table"."age" + %s)) - ("test_table"."age" + %s))'
    assert res._output[1] == [1, 1, 1, 1, 1]

def test_463(lit_str, col_str):
    res = lit_str + col_str + lit_str + col_str + lit_str
    assert res._output[0] == '((((%s || "test_table"."name") || %s) || "test_table"."name") || %s)'
    assert res._output[1] == ['text', 'text', 'text']

def test_464(lit_int, col_int):
    res = lit_int + col_int + lit_int + col_int + lit_int
    assert res._output[0] == '((((%s + "test_table"."age") + %s) + "test_table"."age") + %s)'
    assert res._output[1] == [10, 10, 10]

def test_465(col_str, lit_str):
    res = col_str + lit_str + col_str + lit_str + col_str
    assert res._output[0] == '(((("test_table"."name" || %s) || "test_table"."name") || %s) || "test_table"."name")'
    assert res._output[1] == ['text', 'text']

def test_466(col_int, lit_int):
    res = col_int + lit_int + col_int + lit_int + col_int
    assert res._output[0] == '(((("test_table"."age" + %s) + "test_table"."age") + %s) + "test_table"."age")'
    assert res._output[1] == [10, 10]

def test_467(op_str, lit_str):
    res = op_str + lit_str + op_str + lit_str + op_str
    assert res._output[0] == '((((("test_table"."name" || %s) || %s) || ("test_table"."name" || %s)) || %s) || ("test_table"."name" || %s))'
    assert res._output[1] == ['op_str_param', 'text', 'op_str_param', 'text', 'op_str_param']

def test_468(op_int, lit_int):
    res = op_int + lit_int + op_int + lit_int + op_int
    assert res._output[0] == '((((("test_table"."age" + %s) + %s) + ("test_table"."age" + %s)) + %s) + ("test_table"."age" + %s))'
    assert res._output[1] == [1, 10, 1, 10, 1]

def test_469(col_str, lit_int, col_int, lit_str, col_float):
    res = (col_str + lit_int) + (col_int + lit_str) + (col_float + lit_int)
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."age" || %s)) || ("test_table"."score" + %s))'
    assert res._output[1] == [10, 'text', 10]

def test_470(col_int, lit_str, col_float, lit_int, col_str, lit_float):
    res = (col_int - lit_str) - (col_float - lit_int) - (col_str - lit_float)
    assert res._output[0] == '((("test_table"."age" - %s) - ("test_table"."score" - %s)) - ("test_table"."name" - %s))'
    assert res._output[1] == ['text', 10, 10.5]

def test_471(op_str, col_int, op_int, col_str, op_float):
    res = (op_str + col_int) + (op_int + col_str) + (op_float + col_int)
    assert res._output[0] == '(((("test_table"."name" || %s) || "test_table"."age") || (("test_table"."age" + %s) || "test_table"."name")) || (("test_table"."score" + %s) + "test_table"."age"))'
    assert res._output[1] == ['op_str_param', 1, 1.5]

def test_472(op_int, col_str, op_float, col_int, op_str, col_float):
    res = (op_int - col_str) - (op_float - col_int) - (op_str - col_float)
    assert res._output[0] == '(((("test_table"."age" + %s) - "test_table"."name") - (("test_table"."score" + %s) - "test_table"."age")) - (("test_table"."name" || %s) - "test_table"."score"))'
    assert res._output[1] == [1, 1.5, 'op_str_param']

def test_473(col_str, op_int, lit_str, op_float, col_int, op_str):
    res = (col_str + op_int) + (lit_str + op_float) + (col_int + op_str)
    assert res._output[0] == '((("test_table"."name" || ("test_table"."age" + %s)) || (%s || ("test_table"."score" + %s))) || ("test_table"."age" || ("test_table"."name" || %s)))'
    assert res._output[1] == [1, 'text', 1.5, 'op_str_param']

def test_474(col_int, op_str, lit_int, op_float, col_float, op_int):
    res = (col_int - op_str) - (lit_int - op_float) - (col_float - op_int)
    assert res._output[0] == '((("test_table"."age" - ("test_table"."name" || %s)) - (%s - ("test_table"."score" + %s))) - ("test_table"."score" - ("test_table"."age" + %s)))'
    assert res._output[1] == ['op_str_param', 10, 1.5, 1]

def test_475(lit_str, col_int, op_str, col_float, lit_int, col_str):
    res = (lit_str + col_int) + (op_str + col_float) + (lit_int + col_str)
    assert res._output[0] == '(((%s || "test_table"."age") || (("test_table"."name" || %s) || "test_table"."score")) || (%s || "test_table"."name"))'
    assert res._output[1] == ['text', 'op_str_param', 10]

def test_476(lit_int, col_str, op_int, col_float, lit_float, col_int):
    res = (lit_int - col_str) - (op_int - col_float) - (lit_float - col_int)
    assert res._output[0] == '(((%s - "test_table"."name") - (("test_table"."age" + %s) - "test_table"."score")) - (%s - "test_table"."age"))'
    assert res._output[1] == [10, 1, 10.5]

def test_477(col_str, col_int, col_float, op_str, op_int, op_float):
    res = col_str + (col_int + (col_float + (op_str + (op_int + op_float))))
    assert res._output[0] == '("test_table"."name" || ("test_table"."age" || ("test_table"."score" || (("test_table"."name" || %s) || (("test_table"."age" + %s) + ("test_table"."score" + %s))))))'
    assert res._output[1] == ['op_str_param', 1, 1.5]

def test_478(col_int, col_float, col_str, op_int, op_float, op_str):
    res = col_int - (col_float - (col_str - (op_int - (op_float - op_str))))
    assert res._output[0] == '("test_table"."age" - ("test_table"."score" - ("test_table"."name" - (("test_table"."age" + %s) - (("test_table"."score" + %s) - ("test_table"."name" || %s))))))'
    assert res._output[1] == [1, 1.5, 'op_str_param']

def test_479(op_str, op_int, op_float, col_str, col_int, col_float):
    res = op_str + (op_int + (op_float + (col_str + (col_int + col_float))))
    assert res._output[0] == '(("test_table"."name" || %s) || (("test_table"."age" + %s) || (("test_table"."score" + %s) || ("test_table"."name" || ("test_table"."age" + "test_table"."score")))))'
    assert res._output[1] == ['op_str_param', 1, 1.5]

def test_480(op_int, op_float, op_str, col_int, col_float, col_str):
    res = op_int - (op_float - (op_str - (col_int - (col_float - col_str))))
    assert res._output[0] == '(("test_table"."age" + %s) - (("test_table"."score" + %s) - (("test_table"."name" || %s) - ("test_table"."age" - ("test_table"."score" - "test_table"."name")))))'
    assert res._output[1] == [1, 1.5, 'op_str_param']

def test_481(lit_str, col_int, op_float, col_str, op_int, lit_float):
    res = lit_str + (col_int + (op_float + (col_str + (op_int + lit_float))))
    assert res._output[0] == '(%s || ("test_table"."age" || (("test_table"."score" + %s) || ("test_table"."name" || (("test_table"."age" + %s) + %s)))))'
    assert res._output[1] == ['text', 1.5, 1, 10.5]

def test_482(lit_int, col_float, op_str, col_int, op_float, lit_str):
    res = lit_int - (col_float - (op_str - (col_int - (op_float - lit_str))))
    assert res._output[0] == '(%s - ("test_table"."score" - (("test_table"."name" || %s) - ("test_table"."age" - (("test_table"."score" + %s) - %s)))))'
    assert res._output[1] == [10, 'op_str_param', 1.5, 'text']

def test_483(col_str, lit_int, col_int, lit_str, col_float, lit_float):
    res = ((col_str + lit_int) + (col_int + lit_str)) + ((col_float + lit_int) + (col_str + lit_float))
    assert res._output[0] == '((("test_table"."name" || %s) || ("test_table"."age" || %s)) || (("test_table"."score" + %s) || ("test_table"."name" || %s)))'
    assert res._output[1] == [10, 'text', 10, 10.5]

def test_484(col_int, lit_str, col_float, lit_int, col_str, lit_float):
    res = ((col_int - lit_str) - (col_float - lit_int)) - ((col_str - lit_float) - (col_int - lit_str))
    assert res._output[0] == '((("test_table"."age" - %s) - ("test_table"."score" - %s)) - (("test_table"."name" - %s) - ("test_table"."age" - %s)))'
    assert res._output[1] == ['text', 10, 10.5, 'text']

def test_485(op_str, col_int, op_int, col_str, op_float, col_float):
    res = ((op_str + col_int) + (op_int + col_str)) + ((op_float + col_int) + (op_str + col_float))
    assert res._output[0] == '(((("test_table"."name" || %s) || "test_table"."age") || (("test_table"."age" + %s) || "test_table"."name")) || ((("test_table"."score" + %s) + "test_table"."age") || (("test_table"."name" || %s) || "test_table"."score")))'
    assert res._output[1] == ['op_str_param', 1, 1.5, 'op_str_param']

def test_486(op_int, col_str, op_float, col_int, op_str, col_float):
    res = ((op_int - col_str) - (op_float - col_int)) - ((op_str - col_float) - (op_int - col_str))
    assert res._output[0] == '(((("test_table"."age" + %s) - "test_table"."name") - (("test_table"."score" + %s) - "test_table"."age")) - ((("test_table"."name" || %s) - "test_table"."score") - (("test_table"."age" + %s) - "test_table"."name")))'
    assert res._output[1] == [1, 1.5, 'op_str_param', 1]

def test_487(col_str, op_int, lit_str, op_float, col_int, op_str, lit_int):
    res = ((col_str + op_int) + (lit_str + op_float)) + ((col_int + op_str) + (lit_int + op_int))
    assert res._output[0] == '((("test_table"."name" || ("test_table"."age" + %s)) || (%s || ("test_table"."score" + %s))) || (("test_table"."age" || ("test_table"."name" || %s)) || (%s + ("test_table"."age" + %s))))'
    assert res._output[1] == [1, 'text', 1.5, 'op_str_param', 10, 1]

def test_488(col_int, op_str, lit_int, op_float, col_float, op_int, lit_float):
    res = ((col_int - op_str) - (lit_int - op_float)) - ((col_float - op_int) - (lit_float - op_str))
    assert res._output[0] == '((("test_table"."age" - ("test_table"."name" || %s)) - (%s - ("test_table"."score" + %s))) - (("test_table"."score" - ("test_table"."age" + %s)) - (%s - ("test_table"."name" || %s))))'
    assert res._output[1] == ['op_str_param', 10, 1.5, 1, 10.5, 'op_str_param']

def test_489(lit_str, col_int, op_str, col_float, lit_int, col_str, op_int):
    res = ((lit_str + col_int) + (op_str + col_float)) + ((lit_int + col_str) + (op_int + col_float))
    assert res._output[0] == '(((%s || "test_table"."age") || (("test_table"."name" || %s) || "test_table"."score")) || ((%s || "test_table"."name") || (("test_table"."age" + %s) + "test_table"."score")))'
    assert res._output[1] == ['text', 'op_str_param', 10, 1]

def test_490(lit_int, col_str, op_int, col_float, lit_float, col_int, op_str):
    res = ((lit_int - col_str) - (op_int - col_float)) - ((lit_float - col_int) - (op_str - col_int))
    assert res._output[0] == '(((%s - "test_table"."name") - (("test_table"."age" + %s) - "test_table"."score")) - ((%s - "test_table"."age") - (("test_table"."name" || %s) - "test_table"."age")))'
    assert res._output[1] == [10, 1, 10.5, 'op_str_param']

def test_491(col_str, col_int, col_float, op_str, op_int, op_float, lit_int):
    res = (((col_str + col_int) + col_float) + op_str) + (((op_int + op_float) + col_str) + lit_int)
    assert res._output[0] == '(((("test_table"."name" || "test_table"."age") || "test_table"."score") || ("test_table"."name" || %s)) || (((("test_table"."age" + %s) + ("test_table"."score" + %s)) || "test_table"."name") || %s))'
    assert res._output[1] == ['op_str_param', 1, 1.5, 10]

def test_492(col_int, col_float, col_str, op_int, op_float, op_str, lit_str):
    res = (((col_int - col_float) - col_str) - op_int) - (((op_float - op_str) - col_int) - lit_str)
    assert res._output[0] == '(((("test_table"."age" - "test_table"."score") - "test_table"."name") - ("test_table"."age" + %s)) - (((("test_table"."score" + %s) - ("test_table"."name" || %s)) - "test_table"."age") - %s))'
    assert res._output[1] == [1, 1.5, 'op_str_param', 'text']

def test_493(lit_str, col_int, col_float, op_str, op_int, op_float, col_str, lit_int):
    res = lit_str + (((col_int + col_float) + op_str) + (((op_int + op_float) + col_str) + lit_int))
    assert res._output[0] == '(%s || ((("test_table"."age" + "test_table"."score") || ("test_table"."name" || %s)) || (((("test_table"."age" + %s) + ("test_table"."score" + %s)) || "test_table"."name") || %s)))'
    assert res._output[1] == ['text', 'op_str_param', 1, 1.5, 10]

def test_494(lit_int, col_float, col_str, op_int, op_float, op_str, col_int, lit_str):
    res = lit_int - (((col_float - col_str) - op_int) - (((op_float - op_str) - col_int) - lit_str))
    assert res._output[0] == '(%s - ((("test_table"."score" - "test_table"."name") - ("test_table"."age" + %s)) - (((("test_table"."score" + %s) - ("test_table"."name" || %s)) - "test_table"."age") - %s)))'
    assert res._output[1] == [10, 1, 1.5, 'op_str_param', 'text']

def test_495(col_str, col_int, col_float, op_str, lit_int, col_float_2=col_float):
    res = ((((col_str + col_int) + col_float) + op_str) + lit_int) + col_float
    assert res._output[0] == '((((("test_table"."name" || "test_table"."age") || "test_table"."score") || ("test_table"."name" || %s)) || %s) || "test_table"."score")'
    assert res._output[1] == ['op_str_param', 10]

def test_496(col_int, col_float, col_str, op_int, lit_str, col_float_2=col_float):
    res = ((((col_int - col_float) - col_str) - op_int) - lit_str) - col_float
    assert res._output[0] == '((((("test_table"."age" - "test_table"."score") - "test_table"."name") - ("test_table"."age" + %s)) - %s) - "test_table"."score")'
    assert res._output[1] == [1, 'text']

def test_497(col_str, col_int, col_float, op_str, lit_int, op_float):
    res = col_str + ((((col_int + col_float) + op_str) + lit_int) + op_float)
    assert res._output[0] == '("test_table"."name" || (((("test_table"."age" + "test_table"."score") || ("test_table"."name" || %s)) || %s) || ("test_table"."score" + %s)))'
    assert res._output[1] == ['op_str_param', 10, 1.5]

def test_498(col_int, col_float, col_str, op_int, lit_str, op_float):
    res = col_int - ((((col_float - col_str) - op_int) - lit_str) - op_float)
    assert res._output[0] == '("test_table"."age" - (((("test_table"."score" - "test_table"."name") - ("test_table"."age" + %s)) - %s) - ("test_table"."score" + %s)))'
    assert res._output[1] == [1, 'text', 1.5]

def test_499(col_str, col_int, col_float, op_str, op_int, op_float, lit_str, lit_int, lit_float):
    res = (col_str + col_int + col_float + op_str + op_int + op_float + lit_str + lit_int + lit_float)
    assert res._output[0] == '(((((((("test_table"."name" || "test_table"."age") || "test_table"."score") || ("test_table"."name" || %s)) || ("test_table"."age" + %s)) || ("test_table"."score" + %s)) || %s) || %s) || %s)'
    assert res._output[1] == ['op_str_param', 1, 1.5, 'text', 10, 10.5]

def test_500(col_str, col_int, col_float, op_str, op_int, op_float, lit_str, lit_int, lit_float):
    res = (col_str - col_int - col_float - op_str - op_int - op_float - lit_str - lit_int - lit_float)
    assert res._output[0] == '(((((((("test_table"."name" - "test_table"."age") - "test_table"."score") - ("test_table"."name" || %s)) - ("test_table"."age" + %s)) - ("test_table"."score" + %s)) - %s) - %s) - %s)'
    assert res._output[1] == ['op_str_param', 1, 1.5, 'text', 10, 10.5]

def test_501(col_int):
    res = col_int * col_int
    assert res._output[0] == '("test_table"."age" * "test_table"."age")'
    assert res._output[1] == []

def test_502(col_int, col_float):
    res = col_int * col_float
    assert res._output[0] == '("test_table"."age" * "test_table"."score")'
    assert res._output[1] == []

def test_503(col_int, lit_int):
    res = col_int * lit_int
    assert res._output[0] == '("test_table"."age" * %s)'
    assert res._output[1] == [10]

def test_504(col_int, lit_float):
    res = col_int * lit_float
    assert res._output[0] == '("test_table"."age" * %s)'
    assert res._output[1] == [10.5]

def test_505(col_float, col_int):
    res = col_float * col_int
    assert res._output[0] == '("test_table"."score" * "test_table"."age")'
    assert res._output[1] == []

def test_506(col_float, lit_float):
    res = col_float * lit_float
    assert res._output[0] == '("test_table"."score" * %s)'
    assert res._output[1] == [10.5]

def test_507(lit_int, col_int):
    res = lit_int * col_int
    assert res._output[0] == '(%s * "test_table"."age")'
    assert res._output[1] == [10]

def test_508(lit_float, col_float):
    res = lit_float * col_float
    assert res._output[0] == '(%s * "test_table"."score")'
    assert res._output[1] == [10.5]

def test_509(col_int, op_int):
    res = col_int * op_int
    assert res._output[0] == '("test_table"."age" * ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_510(lit_int, op_int):
    res = lit_int * op_int
    assert res._output[0] == '(%s * ("test_table"."age" + %s))'
    assert res._output[1] == [10, 1]  

def test_511(op_int, col_int):
    res = op_int * col_int
    assert res._output[0] == '(("test_table"."age" + %s) * "test_table"."age")'
    assert res._output[1] == [1]

def test_512(col_int):
    res = (col_int + col_int) * col_int
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") * "test_table"."age")'
    assert res._output[1] == []

def test_513(col_int):
    res = col_int * (col_int + col_int)
    assert res._output[0] == '("test_table"."age" * ("test_table"."age" + "test_table"."age"))'
    assert res._output[1] == []

def test_514(lit_int, col_int):
    res = lit_int * (col_int + col_int)
    assert res._output[0] == '(%s * ("test_table"."age" + "test_table"."age"))'
    assert res._output[1] == [10]

def test_515(col_int, lit_int):
    res = (col_int + col_int) * lit_int
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") * %s)'
    assert res._output[1] == [10]

def test_516(col_int):
    res = col_int / col_int
    assert res._output[0] == '("test_table"."age" / "test_table"."age")'
    assert res._output[1] == []

def test_517(col_int, col_float):
    res = col_int / col_float
    assert res._output[0] == '("test_table"."age" / "test_table"."score")'
    assert res._output[1] == []

def test_518(col_int, lit_int):
    res = col_int / lit_int
    assert res._output[0] == '("test_table"."age" / %s)'
    assert res._output[1] == [10]

def test_519(col_int, lit_float):
    res = col_int / lit_float
    assert res._output[0] == '("test_table"."age" / %s)'
    assert res._output[1] == [10.5]

def test_520(col_float, col_int):
    res = col_float / col_int
    assert res._output[0] == '("test_table"."score" / "test_table"."age")'
    assert res._output[1] == []

def test_521(lit_int, col_int):
    res = lit_int / col_int
    assert res._output[0] == '(%s / "test_table"."age")'
    assert res._output[1] == [10]

def test_522(lit_float, col_float):
    res = lit_float / col_float
    assert res._output[0] == '(%s / "test_table"."score")'
    assert res._output[1] == [10.5]

def test_523(col_float, op_float):
    res = col_float / op_float
    assert res._output[0] == '("test_table"."score" / ("test_table"."score" + %s))'
    assert res._output[1] == [1.5]

def test_524(lit_float, op_float):
    res = lit_float / op_float
    assert res._output[0] == '(%s / ("test_table"."score" + %s))'
    assert res._output[1] == [10.5, 1.5]  

def test_525(op_float, col_float):
    res = op_float / col_float
    assert res._output[0] == '(("test_table"."score" + %s) / "test_table"."score")'
    assert res._output[1] == [1.5]

def test_526(col_int):
    res = col_int % col_int
    assert res._output[0] == '("test_table"."age" % "test_table"."age")'
    assert res._output[1] == []

def test_527(col_int, lit_int):
    res = col_int % lit_int
    assert res._output[0] == '("test_table"."age" % %s)'
    assert res._output[1] == [10]

def test_528(col_int, lit_float):
    res = col_int % lit_float
    assert res._output[0] == '("test_table"."age" % %s)'
    assert res._output[1] == [10.5]

def test_529(lit_int, col_int):
    res = lit_int % col_int
    assert res._output[0] == '(%s % "test_table"."age")'
    assert res._output[1] == [10]

def test_530(lit_float, col_int):
    res = lit_float % col_int
    assert res._output[0] == '(%s % "test_table"."age")'
    assert res._output[1] == [10.5]

def test_531(col_int, op_int):
    res = col_int % op_int
    assert res._output[0] == '("test_table"."age" % ("test_table"."age" + %s))'
    assert res._output[1] == [1]

def test_532(lit_int, op_int):
    res = lit_int % op_int
    assert res._output[0] == '(%s % ("test_table"."age" + %s))'
    assert res._output[1] == [10, 1]  

def test_533(op_int, col_int):
    res = op_int % col_int
    assert res._output[0] == '(("test_table"."age" + %s) % "test_table"."age")'
    assert res._output[1] == [1]

def test_534(col_int):
    res = col_int ** col_int
    assert res._output[0] == '(POW("test_table"."age" , "test_table"."age"))'
    assert res._output[1] == []

def test_535(col_int, lit_int):
    res = col_int ** lit_int
    assert res._output[0] == '(POW("test_table"."age" , %s))'
    assert res._output[1] == [10]

def test_536(col_int, lit_float):
    res = col_int ** lit_float
    assert res._output[0] == '(POW("test_table"."age" , %s))'
    assert res._output[1] == [10.5]

def test_537(lit_int, col_int):
    res = lit_int ** col_int
    assert res._output[0] == '(POW(%s , "test_table"."age"))'
    assert res._output[1] == [10]

def test_538(lit_float, col_int):
    res = lit_float ** col_int
    assert res._output[0] == '(POW(%s , "test_table"."age"))'
    assert res._output[1] == [10.5]

def test_539(col_float, op_float):
    res = col_float ** op_float
    assert res._output[0] == '(POW("test_table"."score" , ("test_table"."score" + %s)))'
    assert res._output[1] == [1.5]

def test_540(lit_float, op_float):
    res = lit_float ** op_float
    assert res._output[0] == '(POW(%s , ("test_table"."score" + %s)))'
    assert res._output[1] == [10.5, 1.5]  
    
def test_541(op_float, col_float):
    res = op_float ** col_float
    assert res._output[0] == '(POW(("test_table"."score" + %s) , "test_table"."score"))'
    assert res._output[1] == [1.5]

def test_542(col_int, col_float, lit_int):
    res = (col_int * col_float) / lit_int
    assert res._output[0] == '(("test_table"."age" * "test_table"."score") / %s)'
    assert res._output[1] == [10]

def test_543(col_int, lit_int, col_float):
    res = (col_int + lit_int) * col_float
    assert res._output[0] == '(("test_table"."age" + %s) * "test_table"."score")'
    assert res._output[1] == [10]

def test_544(col_int, col_float, lit_float):
    res = col_int * (col_float - lit_float)
    assert res._output[0] == '("test_table"."age" * ("test_table"."score" - %s))'
    assert res._output[1] == [10.5]

def test_545(lit_int, col_int):
    res = lit_int * (col_int % col_int)
    assert res._output[0] == '(%s * ("test_table"."age" % "test_table"."age"))'
    assert res._output[1] == [10]

def test_546(col_int, lit_int):
    res = (col_int ** lit_int) - col_int
    assert res._output[0] == '((POW("test_table"."age" , %s)) - "test_table"."age")'
    assert res._output[1] == [10]

def test_547(col_float, col_int, lit_int):
    res = col_float / (col_int * lit_int)
    assert res._output[0] == '("test_table"."score" / ("test_table"."age" * %s))'
    assert res._output[1] == [10]

def test_548(lit_int, col_float, col_int):
    res = lit_int / (col_float + col_int)
    assert res._output[0] == '(%s / ("test_table"."score" + "test_table"."age"))'
    assert res._output[1] == [10]

def test_549(col_int, lit_int):
    res = ((col_int * col_int) % lit_int) + col_int
    assert res._output[0] == '((("test_table"."age" * "test_table"."age") % %s) + "test_table"."age")'
    assert res._output[1] == [10]

def test_550(col_int, col_float):
    res = (col_int + col_int) * (col_float + col_float)
    assert res._output[0] == '(("test_table"."age" + "test_table"."age") * ("test_table"."score" + "test_table"."score"))'
    assert res._output[1] == []

def test_551(col_str):
    res = col_str.upper()
    assert res._output[0] == '(UPPER("test_table"."name"))'
    assert res._output[1] == []

def test_552(col_str):
    res = col_str.lower()
    assert res._output[0] == '(LOWER("test_table"."name"))'
    assert res._output[1] == []

def test_553(col_str, lit_str):
    res = (col_str + lit_str).upper()
    assert res._output[0] == '(UPPER(("test_table"."name" || %s)))'
    assert res._output[1] == ['text']

def test_554(col_str, lit_str):
    res = (col_str + lit_str).lower()
    assert res._output[0] == '(LOWER(("test_table"."name" || %s)))'
    assert res._output[1] == ['text']

def test_555(lit_str, col_str):
    res = (lit_str + col_str).upper()
    assert res._output[0] == '(UPPER((%s || "test_table"."name")))'
    assert res._output[1] == ['text']

def test_556(col_str):
    res = col_str.startswith('A')
    assert res._output[0] == '("test_table"."name" like %s || \'%%\')'
    assert res._output[1] == ['A']

def test_557(col_str):
    res = col_str.endswith('Z')
    assert res._output[0] == '("test_table"."name" like \'%%\' || %s)'
    assert res._output[1] == ['Z']

def test_558(col_str):
    res = col_str.like('%test%')
    assert res._output[0] == '("test_table"."name" like %s)'
    assert res._output[1] == ['%test%']

def test_559(col_str):
    res = col_str.upper().startswith('A')
    assert res._output[0] == '((UPPER("test_table"."name")) like %s || \'%%\')'
    assert res._output[1] == ['A']

def test_560(col_str):
    res = col_str.lower().endswith('z')
    assert res._output[0] == '((LOWER("test_table"."name")) like \'%%\' || %s)'
    assert res._output[1] == ['z']

def test_561(col_str, lit_str):
    res = (col_str + lit_str).upper().startswith('A')
    assert res._output[0] == '((UPPER(("test_table"."name" || %s))) like %s || \'%%\')'
    assert res._output[1] == ['text', 'A']

def test_562(col_str, lit_str):
    res = (col_str + lit_str).lower().endswith('z')
    assert res._output[0] == '((LOWER(("test_table"."name" || %s))) like \'%%\' || %s)'
    assert res._output[1] == ['text', 'z']

def test_563(op_str):
    res = op_str.upper()
    assert res._output[0] == '(UPPER(("test_table"."name" || %s)))'
    assert res._output[1] == ['op_str_param']

def test_564(op_str):
    res = op_str.lower()
    assert res._output[0] == '(LOWER(("test_table"."name" || %s)))'
    assert res._output[1] == ['op_str_param']

def test_565(op_str):
    res = op_str.startswith('A')
    assert res._output[0] == '(("test_table"."name" || %s) like %s || \'%%\')'
    assert res._output[1] == ['op_str_param', 'A']

def test_566(op_str):
    res = op_str.endswith('Z')
    assert res._output[0] == '(("test_table"."name" || %s) like \'%%\' || %s)'
    assert res._output[1] == ['op_str_param', 'Z']

def test_567(op_str):
    res = op_str.like('%test%')
    assert res._output[0] == '(("test_table"."name" || %s) like %s)'
    assert res._output[1] == ['op_str_param', '%test%']

def test_568(op_str):
    res = op_str.upper().startswith('A')
    assert res._output[0] == '((UPPER(("test_table"."name" || %s))) like %s || \'%%\')'
    assert res._output[1] == ['op_str_param', 'A']

def test_569(op_str):
    res = op_str.lower().endswith('z')
    assert res._output[0] == '((LOWER(("test_table"."name" || %s))) like \'%%\' || %s)'
    assert res._output[1] == ['op_str_param', 'z']

def test_570(col_str, op_str):
    res = (col_str + op_str).upper()
    assert res._output[0] == '(UPPER(("test_table"."name" || ("test_table"."name" || %s))))'
    assert res._output[1] == ['op_str_param']

def test_571(col_str, op_str):
    res = (col_str + op_str).startswith('A')
    assert res._output[0] == '(("test_table"."name" || ("test_table"."name" || %s)) like %s || \'%%\')'
    assert res._output[1] == ['op_str_param', 'A']

def test_572(col_str, op_str):
    res = (col_str + op_str).upper().startswith('A')
    assert res._output[0] == '((UPPER(("test_table"."name" || ("test_table"."name" || %s)))) like %s || \'%%\')'
    assert res._output[1] == ['op_str_param', 'A']

def test_573(op_str, col_str):
    res = (op_str + col_str).lower().endswith('z')
    assert res._output[0] == '((LOWER((("test_table"."name" || %s) || "test_table"."name"))) like \'%%\' || %s)'
    assert res._output[1] == ['op_str_param', 'z']

def test_574(col_str, lit_str):
    res = (col_str + lit_str).like('test')
    assert res._output[0] == '(("test_table"."name" || %s) like %s)'
    assert res._output[1] == ['text', 'test']

def test_575(col_str):
    res = col_str.upper().like('TEST')
    assert res._output[0] == '((UPPER("test_table"."name")) like %s)'
    assert res._output[1] == ['TEST']

def test_576(col_str, col_int):
    res = (col_str + col_int).upper()
    assert res._output[0] == '(UPPER(("test_table"."name" || "test_table"."age")))'
    assert res._output[1] == []

def test_577(col_str, col_int):
    res = (col_str + col_int).startswith('A')
    assert res._output[0] == '(("test_table"."name" || "test_table"."age") like %s || \'%%\')'
    assert res._output[1] == ['A']

def test_578(col_str, lit_int):
    res = (col_str + lit_int).upper().startswith('A')
    assert res._output[0] == '((UPPER(("test_table"."name" || %s))) like %s || \'%%\')'
    assert res._output[1] == [10, 'A']

def test_579(col_int, col_str):
    res = (col_int + col_str).lower()
    assert res._output[0] == '(LOWER(("test_table"."age" || "test_table"."name")))'
    assert res._output[1] == []

def test_580(lit_str, col_str):
    res = (lit_str + col_str).startswith('A')
    assert res._output[0] == '((%s || "test_table"."name") like %s || \'%%\')'
    assert res._output[1] == ['text', 'A']

def test_581(lit_str, col_str):
    res = (lit_str + col_str).upper().endswith('Z')
    assert res._output[0] == '((UPPER((%s || "test_table"."name"))) like \'%%\' || %s)'
    assert res._output[1] == ['text', 'Z']

def test_582(col_str, op_str):
    res = col_str.upper() + op_str.lower()
    assert res._output[0] == '((UPPER("test_table"."name")) || (LOWER(("test_table"."name" || %s))))'
    assert res._output[1] == ['op_str_param']

def test_583(col_str, op_str):
    res = col_str.startswith('A') + op_str.endswith('Z')
    assert res._output[0] == '(("test_table"."name" like %s || \'%%\') || (("test_table"."name" || %s) like \'%%\' || %s))'
    assert res._output[1] == ['A', 'op_str_param', 'Z']

def test_584(op_str, lit_str):
    res = (op_str + lit_str).upper().startswith('prefix')
    assert res._output[0] == '((UPPER((("test_table"."name" || %s) || %s))) like %s || \'%%\')'
    assert res._output[1] == ['op_str_param', 'text', 'prefix']

def test_585(col_str, lit_str):
    res = (col_str + lit_str).lower().like('%pattern%')
    assert res._output[0] == '((LOWER(("test_table"."name" || %s))) like %s)'
    assert res._output[1] == ['text', '%pattern%']

def test_586(col_str, op_str):
    res = (col_str + op_str).upper().like('test')
    assert res._output[0] == '((UPPER(("test_table"."name" || ("test_table"."name" || %s)))) like %s)'
    assert res._output[1] == ['op_str_param', 'test']

def test_587(col_str):
    res = col_str.upper().upper()
    assert res._output[0] == '(UPPER((UPPER("test_table"."name"))))'
    assert res._output[1] == []

def test_588(col_str):
    res = col_str.lower().upper()
    assert res._output[0] == '(UPPER((LOWER("test_table"."name"))))'
    assert res._output[1] == []

def test_589(col_str):
    res = col_str.upper().lower()
    assert res._output[0] == '(LOWER((UPPER("test_table"."name"))))'
    assert res._output[1] == []

def test_590(col_str):
    res = col_str.startswith('A').startswith('B')
    assert res._output[0] == '(("test_table"."name" like %s || \'%%\') like %s || \'%%\')'
    assert res._output[1] == ['A', 'B']

def test_591(col_str):
    res = col_str.endswith('Z').endswith('Y')
    assert res._output[0] == '(("test_table"."name" like \'%%\' || %s) like \'%%\' || %s)'
    assert res._output[1] == ['Z', 'Y']

def test_592(col_str, lit_str):
    res = (lit_str + col_str).upper().lower().startswith('a')
    assert res._output[0] == '((LOWER((UPPER((%s || "test_table"."name"))))) like %s || \'%%\')'
    assert res._output[1] == ['text', 'a']

def test_593(op_str, col_str):
    res = (op_str + col_str).upper().endswith('Z')
    assert res._output[0] == '((UPPER((("test_table"."name" || %s) || "test_table"."name"))) like \'%%\' || %s)'
    assert res._output[1] == ['op_str_param', 'Z']

def test_594(col_str, col_int, lit_str):
    res = (col_str + col_int + lit_str).upper()
    assert res._output[0] == '(UPPER((("test_table"."name" || "test_table"."age") || %s)))'
    assert res._output[1] == ['text']

def test_595(col_str, col_int, lit_str):
    res = (col_str + col_int + lit_str).startswith('A')
    assert res._output[0] == '((("test_table"."name" || "test_table"."age") || %s) like %s || \'%%\')'
    assert res._output[1] == ['text', 'A']

def test_596(col_str, op_int):
    res = (col_str + op_int).upper()
    assert res._output[0] == '(UPPER(("test_table"."name" || ("test_table"."age" + %s))))'
    assert res._output[1] == [1]

def test_597(col_str, op_int):
    res = (col_str + op_int).startswith('A')
    assert res._output[0] == '(("test_table"."name" || ("test_table"."age" + %s)) like %s || \'%%\')'
    assert res._output[1] == [1, 'A']

def test_598(op_str, op_int):
    res = (op_str + op_int).upper().endswith('Z')
    assert res._output[0] == '((UPPER((("test_table"."name" || %s) || ("test_table"."age" + %s)))) like \'%%\' || %s)'
    assert res._output[1] == ['op_str_param', 1, 'Z']

def test_599(col_str, op_float):
    res = (col_str + op_float).lower().like('test')
    assert res._output[0] == '((LOWER(("test_table"."name" || ("test_table"."score" + %s)))) like %s)'
    assert res._output[1] == [1.5, 'test']

def test_600(col_str, lit_str, lit_int):
    res = (lit_str + col_str + lit_int).upper()
    assert res._output[0] == '(UPPER(((%s || "test_table"."name") || %s)))'
    assert res._output[1] == ['text', 10]

def test_601(col_str, lit_str, lit_int):
    res = (lit_str + col_str + lit_int).startswith('A')
    assert res._output[0] == '(((%s || "test_table"."name") || %s) like %s || \'%%\')'
    assert res._output[1] == ['text', 10, 'A']

def test_602(col_str, op_str, lit_str):
    res = (col_str + op_str + lit_str).upper()
    assert res._output[0] == '(UPPER((("test_table"."name" || ("test_table"."name" || %s)) || %s)))'
    assert res._output[1] == ['op_str_param', 'text']

def test_603(col_str, op_str, lit_str):
    res = (col_str + op_str + lit_str).startswith('A')
    assert res._output[0] == '((("test_table"."name" || ("test_table"."name" || %s)) || %s) like %s || \'%%\')'
    assert res._output[1] == ['op_str_param', 'text', 'A']

def test_604(col_str, op_str):
    res = col_str.upper() + op_str.upper()
    assert res._output[0] == '((UPPER("test_table"."name")) || (UPPER(("test_table"."name" || %s))))'
    assert res._output[1] == ['op_str_param']

def test_605(col_str, lit_str):
    res = col_str.startswith(lit_str)
    assert res._output[0] == '("test_table"."name" like %s || \'%%\')'
    assert res._output[1] == ['text']

def test_606(col_str, lit_str):
    res = col_str.endswith(lit_str)
    assert res._output[0] == '("test_table"."name" like \'%%\' || %s)'
    assert res._output[1] == ['text']

def test_607(col_str, lit_str):
    res = col_str.upper().startswith(lit_str)
    assert res._output[0] == '((UPPER("test_table"."name")) like %s || \'%%\')'
    assert res._output[1] == ['text']

def test_608(col_str, lit_str):
    res = col_str.lower().endswith(lit_str)
    assert res._output[0] == '((LOWER("test_table"."name")) like \'%%\' || %s)'
    assert res._output[1] == ['text']

def test_609(col_str, lit_str, lit_int):
    res = (col_str + lit_str).startswith(lit_int)
    assert res._output[0] == '(("test_table"."name" || %s) like %s || \'%%\')'
    assert res._output[1] == ['text', '10'] 

def test_610(col_str, lit_str, lit_int):
    res = (col_str + lit_str).endswith(lit_int)
    assert res._output[0] == '(("test_table"."name" || %s) like \'%%\' || %s)'
    assert res._output[1] == ['text', '10']

def test_611(col_str):
    res = col_str.upper().like(col_str)
    assert res._output[0] == '((UPPER("test_table"."name")) like "test_table"."name")'
    assert res._output[1] == []

def test_612(col_str, col_int):
    res = col_str.startswith(col_int)
    assert res._output[0] == '("test_table"."name" like "test_table"."age" || \'%%\')'
    assert res._output[1] == []

def test_613(col_str, op_str):
    res = op_str.upper().startswith(col_str)
    assert res._output[0] == '((UPPER(("test_table"."name" || %s))) like "test_table"."name" || \'%%\')'
    assert res._output[1] == ['op_str_param']

def test_614(col_str, lit_str):
    res = (col_str - lit_str).upper()
    assert res._output[0] == '(UPPER(("test_table"."name" - %s)))'
    assert res._output[1] == ['text']

def test_615(col_str, lit_str):
    res = (col_str - lit_str).startswith('A')
    assert res._output[0] == '(("test_table"."name" - %s) like %s || \'%%\')'
    assert res._output[1] == ['text', 'A']

def test_616(col_str, op_str):
    res = (col_str - op_str).upper().endswith('Z')
    assert res._output[0] == '((UPPER(("test_table"."name" - ("test_table"."name" || %s)))) like \'%%\' || %s)'
    assert res._output[1] == ['op_str_param', 'Z']

def test_617(lit_str, col_str):
    res = (lit_str - col_str).lower().like('test')
    assert res._output[0] == '((LOWER((%s - "test_table"."name"))) like %s)'
    assert res._output[1] == ['text', 'test']

def test_618(col_str, op_str, lit_str):
    res = (col_str - op_str + lit_str).upper()
    assert res._output[0] == '(UPPER((("test_table"."name" - ("test_table"."name" || %s)) || %s)))'
    assert res._output[1] == ['op_str_param', 'text']

def test_619(col_str, op_str, lit_str):
    res = (col_str - op_str + lit_str).startswith('A')
    assert res._output[0] == '((("test_table"."name" - ("test_table"."name" || %s)) || %s) like %s || \'%%\')'
    assert res._output[1] == ['op_str_param', 'text', 'A']

def test_620(col_str, op_str, lit_str):
    res = (col_str - op_str + lit_str).lower().endswith('z')
    assert res._output[0] == '((LOWER((("test_table"."name" - ("test_table"."name" || %s)) || %s))) like \'%%\' || %s)'
    assert res._output[1] == ['op_str_param', 'text', 'z']

def test_621(col_str, lit_str):
    res = col_str == lit_str
    assert res._output[0] == '("test_table"."name" = %s)'
    assert res._output[1] == ['text']

def test_622(col_str, lit_str):
    res = col_str != lit_str
    assert res._output[0] == '("test_table"."name" != %s)'
    assert res._output[1] == ['text']

def test_623(col_str, lit_str):
    res = col_str > lit_str
    assert res._output[0] == '("test_table"."name" > %s)'
    assert res._output[1] == ['text']

def test_624(col_str, lit_str):
    res = col_str < lit_str
    assert res._output[0] == '("test_table"."name" < %s)'
    assert res._output[1] == ['text']

def test_625(col_str, lit_str):
    res = col_str >= lit_str
    assert res._output[0] == '("test_table"."name" >= %s)'
    assert res._output[1] == ['text']

def test_626(col_str, lit_str):
    res = col_str <= lit_str
    assert res._output[0] == '("test_table"."name" <= %s)'
    assert res._output[1] == ['text']

def test_627(col_str, lit_str):
    res = col_str.eq(lit_str)
    assert res._output[0] == '("test_table"."name" = %s)'
    assert res._output[1] == ['text']

def test_628(col_str, lit_str):
    res = col_str.ne(lit_str)
    assert res._output[0] == '("test_table"."name" != %s)'
    assert res._output[1] == ['text']

def test_629(col_str, lit_str):
    res = col_str.gt(lit_str)
    assert res._output[0] == '("test_table"."name" > %s)'
    assert res._output[1] == ['text']

def test_630(col_str, lit_str):
    res = col_str.lt(lit_str)
    assert res._output[0] == '("test_table"."name" < %s)'
    assert res._output[1] == ['text']

def test_631(col_str, lit_str):
    res = col_str.ge(lit_str)
    assert res._output[0] == '("test_table"."name" >= %s)'
    assert res._output[1] == ['text']

def test_632(col_str, lit_str):
    res = col_str.le(lit_str)
    assert res._output[0] == '("test_table"."name" <= %s)'
    assert res._output[1] == ['text']

def test_633(col_int, lit_int):
    res = col_int == lit_int
    assert res._output[0] == '("test_table"."age" = %s)'
    assert res._output[1] == [10]

def test_634(col_int, lit_int):
    res = col_int != lit_int
    assert res._output[0] == '("test_table"."age" != %s)'
    assert res._output[1] == [10]

def test_635(col_int, lit_int):
    res = col_int > lit_int
    assert res._output[0] == '("test_table"."age" > %s)'
    assert res._output[1] == [10]

def test_636(col_int, lit_int):
    res = col_int < lit_int
    assert res._output[0] == '("test_table"."age" < %s)'
    assert res._output[1] == [10]

def test_637(col_int, lit_int):
    res = col_int >= lit_int
    assert res._output[0] == '("test_table"."age" >= %s)'
    assert res._output[1] == [10]

def test_638(col_int, lit_int):
    res = col_int <= lit_int
    assert res._output[0] == '("test_table"."age" <= %s)'
    assert res._output[1] == [10]

def test_639(col_float, lit_float):
    res = col_float == lit_float
    assert res._output[0] == '("test_table"."score" = %s)'
    assert res._output[1] == [10.5]

def test_640(col_float, lit_float):
    res = col_float != lit_float
    assert res._output[0] == '("test_table"."score" != %s)'
    assert res._output[1] == [10.5]

def test_641(col_float, lit_float):
    res = col_float > lit_float
    assert res._output[0] == '("test_table"."score" > %s)'
    assert res._output[1] == [10.5]

def test_642(col_float, lit_float):
    res = col_float < lit_float
    assert res._output[0] == '("test_table"."score" < %s)'
    assert res._output[1] == [10.5]

def test_643(col_str, col_int):
    res = col_str == col_int
    assert res._output[0] == '("test_table"."name" = "test_table"."age")'
    assert res._output[1] == []

def test_644(col_str, col_int):
    res = col_str != col_int
    assert res._output[0] == '("test_table"."name" != "test_table"."age")'
    assert res._output[1] == []

def test_645(col_str, col_float):
    res = col_str > col_float
    assert res._output[0] == '("test_table"."name" > "test_table"."score")'
    assert res._output[1] == []

def test_646(col_str, col_float):
    res = col_str < col_float
    assert res._output[0] == '("test_table"."name" < "test_table"."score")'
    assert res._output[1] == []

def test_647(col_int, col_float):
    res = col_int >= col_float
    assert res._output[0] == '("test_table"."age" >= "test_table"."score")'
    assert res._output[1] == []

def test_648(col_int, col_float):
    res = col_int <= col_float
    assert res._output[0] == '("test_table"."age" <= "test_table"."score")'
    assert res._output[1] == []

def test_649(op_str, lit_str):
    res = op_str == lit_str
    assert res._output[0] == '(("test_table"."name" || %s) = %s)'
    assert res._output[1] == ['op_str_param', 'text']

def test_650(op_str, lit_str):
    res = op_str != lit_str
    assert res._output[0] == '(("test_table"."name" || %s) != %s)'
    assert res._output[1] == ['op_str_param', 'text']

def test_651(op_str, lit_str):
    res = op_str > lit_str
    assert res._output[0] == '(("test_table"."name" || %s) > %s)'
    assert res._output[1] == ['op_str_param', 'text']

def test_652(op_str, lit_str):
    res = op_str < lit_str
    assert res._output[0] == '(("test_table"."name" || %s) < %s)'
    assert res._output[1] == ['op_str_param', 'text']

def test_653(op_int, lit_int):
    res = op_int == lit_int
    assert res._output[0] == '(("test_table"."age" + %s) = %s)'
    assert res._output[1] == [1, 10]

def test_654(op_int, lit_int):
    res = op_int != lit_int
    assert res._output[0] == '(("test_table"."age" + %s) != %s)'
    assert res._output[1] == [1, 10]

def test_655(op_float, lit_float):
    res = op_float > lit_float
    assert res._output[0] == '(("test_table"."score" + %s) > %s)'
    assert res._output[1] == [1.5, 10.5]

def test_656(op_float, lit_float):
    res = op_float < lit_float
    assert res._output[0] == '(("test_table"."score" + %s) < %s)'
    assert res._output[1] == [1.5, 10.5]

def test_657(op_str, col_int):
    res = op_str == col_int
    assert res._output[0] == '(("test_table"."name" || %s) = "test_table"."age")'
    assert res._output[1] == ['op_str_param']

def test_658(op_str, col_int):
    res = op_str != col_int
    assert res._output[0] == '(("test_table"."name" || %s) != "test_table"."age")'
    assert res._output[1] == ['op_str_param']

def test_659(op_int, col_float):
    res = op_int > col_float
    assert res._output[0] == '(("test_table"."age" + %s) > "test_table"."score")'
    assert res._output[1] == [1]

def test_660(op_int, col_float):
    res = op_int < col_float
    assert res._output[0] == '(("test_table"."age" + %s) < "test_table"."score")'
    assert res._output[1] == [1]

def test_661(op_float, col_int):
    res = op_float >= col_int
    assert res._output[0] == '(("test_table"."score" + %s) >= "test_table"."age")'
    assert res._output[1] == [1.5]

def test_662(op_float, col_int):
    res = op_float <= col_int
    assert res._output[0] == '(("test_table"."score" + %s) <= "test_table"."age")'
    assert res._output[1] == [1.5]

def test_663(op_str, op_int):
    res = op_str == op_int
    assert res._output[0] == '(("test_table"."name" || %s) = ("test_table"."age" + %s))'
    assert res._output[1] == ['op_str_param', 1]

def test_664(op_str, op_int):
    res = op_str != op_int
    assert res._output[0] == '(("test_table"."name" || %s) != ("test_table"."age" + %s))'
    assert res._output[1] == ['op_str_param', 1]

def test_665(op_int, op_float):
    res = op_int > op_float
    assert res._output[0] == '(("test_table"."age" + %s) > ("test_table"."score" + %s))'
    assert res._output[1] == [1, 1.5]

def test_666(op_int, op_float):
    res = op_int < op_float
    assert res._output[0] == '(("test_table"."age" + %s) < ("test_table"."score" + %s))'
    assert res._output[1] == [1, 1.5]

def test_667(col_int, lit_int):
    res = (col_int > lit_int) & (col_int < 20)
    assert res._output[0] == '(("test_table"."age" > %s) AND ("test_table"."age" < %s))'
    assert res._output[1] == [10, 20]

def test_668(col_int, lit_int):
    res = (col_int >= 5) & (col_int <= lit_int)
    assert res._output[0] == '(("test_table"."age" >= %s) AND ("test_table"."age" <= %s))'
    assert res._output[1] == [5, 10]

def test_669(col_str, lit_str):
    res = (col_str == lit_str) & (col_str != 'other')
    assert res._output[0] == '(("test_table"."name" = %s) AND ("test_table"."name" != %s))'
    assert res._output[1] == ['text', 'other']

def test_670(col_str, lit_str):
    res = (col_str.startswith('A')) & (col_str.endswith('Z'))
    assert res._output[0] == '(("test_table"."name" like %s || \'%%\') AND ("test_table"."name" like \'%%\' || %s))'
    assert res._output[1] == ['A', 'Z']

def test_671(col_int, col_float):
    res = (col_int > 5) & (col_float < 10.0)
    assert res._output[0] == '(("test_table"."age" > %s) AND ("test_table"."score" < %s))'
    assert res._output[1] == [5, 10.0]

def test_672(col_int, col_str, lit_str, lit_int):
    res = (col_int != lit_int) & (col_str == lit_str)
    assert res._output[0] == '(("test_table"."age" != %s) AND ("test_table"."name" = %s))'
    assert res._output[1] == [10, 'text']

def test_673(col_int, lit_int):
    res = (col_int < lit_int) | (col_int > 20)
    assert res._output[0] == '(("test_table"."age" < %s) OR ("test_table"."age" > %s))'
    assert res._output[1] == [10, 20]

def test_674(col_int, lit_int):
    res = (col_int == 5) | (col_int == lit_int)
    assert res._output[0] == '(("test_table"."age" = %s) OR ("test_table"."age" = %s))'
    assert res._output[1] == [5, 10]

def test_675(col_str, lit_str):
    res = (col_str == lit_str) | (col_str == 'other')
    assert res._output[0] == '(("test_table"."name" = %s) OR ("test_table"."name" = %s))'
    assert res._output[1] == ['text', 'other']

def test_676(col_str, lit_str):
    res = (col_str.contains('A')) | (col_str.startswith('B'))
    assert res._output[0] == '(("test_table"."name" like \'%%\' || %s || \'%%\') OR ("test_table"."name" like %s || \'%%\'))'
    assert res._output[1] == ['A', 'B']

def test_677(col_int, col_float):
    res = (col_int > 5) | (col_float < 10.0)
    assert res._output[0] == '(("test_table"."age" > %s) OR ("test_table"."score" < %s))'
    assert res._output[1] == [5, 10.0]

def test_678(col_int, col_str, lit_str, lit_int):
    res = (col_int == lit_int) | (col_str == lit_str)
    assert res._output[0] == '(("test_table"."age" = %s) OR ("test_table"."name" = %s))'
    assert res._output[1] == [10, 'text']

def test_679(col_int, col_str, lit_int, lit_str):
    res = ((col_int > lit_int) & (col_str == lit_str)) | (col_int == 0)
    assert res._output[0] == '((("test_table"."age" > %s) AND ("test_table"."name" = %s)) OR ("test_table"."age" = %s))'
    assert res._output[1] == [10, 'text', 0]

def test_680(col_int, col_float):
    res = (col_int > 5) & ((col_float < 10.0) | (col_float > 20.0))
    assert res._output[0] == '(("test_table"."age" > %s) AND (("test_table"."score" < %s) OR ("test_table"."score" > %s)))'
    assert res._output[1] == [5, 10.0, 20.0]

def test_681(col_str, col_int):
    res = (col_str == 'A') | ((col_int > 5) & (col_int < 20))
    assert res._output[0] == '(("test_table"."name" = %s) OR (("test_table"."age" > %s) AND ("test_table"."age" < %s)))'
    assert res._output[1] == ['A', 5, 20]

def test_682(col_str, col_int, lit_int, lit_str):
    res = ((col_str == lit_str) | (col_int == lit_int)) & (col_int > 0)
    assert res._output[0] == '((("test_table"."name" = %s) OR ("test_table"."age" = %s)) AND ("test_table"."age" > %s))'
    assert res._output[1] == ['text', 10, 0]

def test_683(col_str, lit_str):
    res = col_str.eq(lit_str).ne('other')
    assert res._output[0] == '(("test_table"."name" = %s) != %s)'
    assert res._output[1] == ['text', 'other']

def test_684(col_int, lit_int):
    res = col_int.ge(lit_int).lt(20)
    assert res._output[0] == '(("test_table"."age" >= %s) < %s)'
    assert res._output[1] == [10, 20]

def test_685(col_float, lit_float):
    res = col_float.le(lit_float).gt(5.0)
    assert res._output[0] == '(("test_table"."score" <= %s) > %s)'
    assert res._output[1] == [10.5, 5.0]

def test_686(op_str, lit_str):
    res = op_str.eq(lit_str)
    assert res._output[0] == '(("test_table"."name" || %s) = %s)'
    assert res._output[1] == ['op_str_param', 'text']

def test_687(op_int, lit_int):
    res = op_int.ne(lit_int)
    assert res._output[0] == '(("test_table"."age" + %s) != %s)'
    assert res._output[1] == [1, 10]

def test_688(op_float, lit_float):
    res = op_float.gt(lit_float)
    assert res._output[0] == '(("test_table"."score" + %s) > %s)'
    assert res._output[1] == [1.5, 10.5]

def test_689(op_str, op_int):
    res = op_str.eq(op_int)
    assert res._output[0] == '(("test_table"."name" || %s) = ("test_table"."age" + %s))'
    assert res._output[1] == ['op_str_param', 1]

def test_690(col_int, lit_int):
    res = (col_int.gt(lit_int)) & (col_int.lt(20))
    assert res._output[0] == '(("test_table"."age" > %s) AND ("test_table"."age" < %s))'
    assert res._output[1] == [10, 20]

def test_691(col_str, lit_str):
    res = (col_str.eq(lit_str)) | (col_str.eq('other'))
    assert res._output[0] == '(("test_table"."name" = %s) OR ("test_table"."name" = %s))'
    assert res._output[1] == ['text', 'other']

def test_692(col_int, col_float):
    res = (col_int.ge(5)) & ((col_float.le(10.0)) | (col_float.ge(20.0)))
    assert res._output[0] == '(("test_table"."age" >= %s) AND (("test_table"."score" <= %s) OR ("test_table"."score" >= %s)))'
    assert res._output[1] == [5, 10.0, 20.0]

def test_693(col_int, lit_int):
    res = (col_int + lit_int) > 20
    assert res._output[0] == '(("test_table"."age" + %s) > %s)'
    assert res._output[1] == [10, 20]

def test_694(col_str, lit_str):
    res = (col_str + lit_str) == 'texttext'
    assert res._output[0] == '(("test_table"."name" || %s) = %s)'
    assert res._output[1] == ['text', 'texttext']

def test_695(col_int, lit_int):
    res = (col_int * 2) < lit_int
    assert res._output[0] == '(("test_table"."age" * %s) < %s)'
    assert res._output[1] == [2, 10]

def test_696(col_float, lit_float):
    res = (col_float - 5.0) >= lit_float
    assert res._output[0] == '(("test_table"."score" - %s) >= %s)'
    assert res._output[1] == [5.0, 10.5]

def test_697(col_str, lit_str):
    res = col_str.upper() == lit_str.upper()
    assert res._output[0] == '((UPPER("test_table"."name")) = %s)'
    assert res._output[1] == ['TEXT'] 

def test_698(col_str, lit_str):
    res = col_str.lower() != lit_str.lower()
    assert res._output[0] == '((LOWER("test_table"."name")) != %s)'
    assert res._output[1] == ['text']

def test_699(col_str, lit_str):
    res = col_str.startswith('A') == lit_str
    assert res._output[0] == '(("test_table"."name" like %s || \'%%\') = %s)'
    assert res._output[1] == ['A', 'text']

def test_700(col_str, lit_str):
    res = col_str.endswith('Z') != lit_str
    assert res._output[0] == '(("test_table"."name" like \'%%\' || %s) != %s)'
    assert res._output[1] == ['Z', 'text']

def test_701(col_str):
    res = col_str[:3] == 'abc'
    assert res._output[0] == '((SUBSTRING("test_table"."name" , 1 , %s)) = %s)'
    assert res._output[1] == [3, 'abc'] 

def test_702(col_str):
    res = col_str[1:4] != 'def'
    assert res._output[0] == '((SUBSTRING("test_table"."name" , %s , %s)) != %s)'
    assert res._output[1] == [2, 3, 'def'] 

def test_703(col_str):
    res = col_str.replace('a', 'b') == 'xyz'
    assert res._output[0] == '((REPLACE("test_table"."name" , %s , %s)) = %s)'
    assert res._output[1] == ['a', 'b', 'xyz']

def test_704(col_str):
    res = col_str.strip() == 'text'
    assert res._output[0] == '((TRIM(BOTH \' \' FROM "test_table"."name")) = %s)'
    assert res._output[1] == ['text']

def test_705(col_int, col_str):
    res = ((col_int > 5) & (col_int < 20)) | (col_str == 'admin')
    assert res._output[0] == '((("test_table"."age" > %s) AND ("test_table"."age" < %s)) OR ("test_table"."name" = %s))'
    assert res._output[1] == [5, 20, 'admin']

def test_706(col_int, col_float):
    res = (col_int >= 10) & ((col_float < 5.0) | (col_float > 15.0))
    assert res._output[0] == '(("test_table"."age" >= %s) AND (("test_table"."score" < %s) OR ("test_table"."score" > %s)))'
    assert res._output[1] == [10, 5.0, 15.0]

def test_707(op_str, op_int):
    res = (op_str == 'test') & (op_int > 5)
    assert res._output[0] == '((("test_table"."name" || %s) = %s) AND (("test_table"."age" + %s) > %s))'
    assert res._output[1] == ['op_str_param', 'test', 1, 5]

def test_708(op_float, op_int):
    res = (op_float < 10.0) | (op_int == 1)
    assert res._output[0] == '((("test_table"."score" + %s) < %s) OR (("test_table"."age" + %s) = %s))'
    assert res._output[1] == [1.5, 10.0, 1, 1]

def test_709(col_str, lit_int):
    res = col_str.startswith(lit_int)
    assert res._output[0] == '("test_table"."name" like %s || \'%%\')'
    assert res._output[1] == ['10'] 

def test_710(col_str, lit_int):
    res = col_str.endswith(lit_int)
    assert res._output[0] == '("test_table"."name" like \'%%\' || %s)'
    assert res._output[1] == ['10']

def test_711(col_str, lit_str):
    res = (col_str.like('%test%')) & (col_str != '')
    assert res._output[0] == '(("test_table"."name" like %s) AND ("test_table"."name" != %s))'
    assert res._output[1] == ['%test%', '']

def test_712(col_str, lit_str):
    res = (col_str.contains('A')) | (col_str == lit_str)
    assert res._output[0] == '(("test_table"."name" like \'%%\' || %s || \'%%\') OR ("test_table"."name" = %s))'
    assert res._output[1] == ['A', 'text']

def test_713(col_int, col_float):
    res = (col_int > 5) & (col_float < 10.0) | (col_int == 0)
    assert res._output[0] == '((("test_table"."age" > %s) AND ("test_table"."score" < %s)) OR ("test_table"."age" = %s))'
    assert res._output[1] == [5, 10.0, 0]

def test_714(col_int, col_float):
    res = (col_int > 5) & ((col_float < 10.0) | (col_int == 0))
    assert res._output[0] == '(("test_table"."age" > %s) AND (("test_table"."score" < %s) OR ("test_table"."age" = %s)))'
    assert res._output[1] == [5, 10.0, 0]

def test_715(op_str, lit_str):
    res = op_str.eq(lit_str)
    assert res._output[0] == '(("test_table"."name" || %s) = %s)'
    assert res._output[1] == ['op_str_param', 'text']

def test_716(op_int, lit_int):
    res = op_int.ne(lit_int)
    assert res._output[0] == '(("test_table"."age" + %s) != %s)'
    assert res._output[1] == [1, 10]

def test_717(op_float, lit_float):
    res = op_float.gt(lit_float)
    assert res._output[0] == '(("test_table"."score" + %s) > %s)'
    assert res._output[1] == [1.5, 10.5]

def test_718(op_int, lit_int):
    res = op_int.lt(lit_int)
    assert res._output[0] == '(("test_table"."age" + %s) < %s)'
    assert res._output[1] == [1, 10]

def test_719(op_float, lit_float):
    res = op_float.ge(lit_float)
    assert res._output[0] == '(("test_table"."score" + %s) >= %s)'
    assert res._output[1] == [1.5, 10.5]

def test_720(op_int, lit_int):
    res = op_int.le(lit_int)
    assert res._output[0] == '(("test_table"."age" + %s) <= %s)'
    assert res._output[1] == [1, 10]