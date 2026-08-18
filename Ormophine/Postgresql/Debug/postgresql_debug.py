from queue import SimpleQueue, Empty
from psycopg import OperationalError, ProgrammingError, connect
from typing import Any, Literal


class ColumnsOperation():
    def __init__(self, col_obj):
        """Initializes a new ColumnsOperation instance.

        Args:
            col_obj (Column): The column object that this operation is associated with.
        """
        
        self._output = '' # To apply operations in a chained manner
        self.col_obj = col_obj
        self.current_datatype = col_obj.datatype

    def __add__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} {'||' if (self.current_datatype == str) or (other.current_datatype == str) else '+'} {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} {'||' if (self.current_datatype == str) or (other.datatype == str) else '+'} {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} {'||' if (self.current_datatype == str) else '+'} %s)', self._output[1]+[other]) if isinstance(other, int) or isinstance(other , float) else (f'({self._output[0]} || %s)', self._output[1]+[other if isinstance(other, str) else str(other)])
        new_op.current_datatype = str if (isinstance(other, ColumnsOperation) and other.current_datatype == str) or (isinstance(other, Column) and other.datatype == str) or self.current_datatype == str or ( not isinstance(other, ColumnsOperation) and not isinstance(other,Column) and not isinstance(other, int) and not isinstance(other, float)) else self.current_datatype
        return new_op

    def __radd__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} {'||' if (self.current_datatype == str) or (other.current_datatype == str) else '+'} {self._output[0]})', other._output[1]+self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} {'||' if (self.current_datatype == str) or (other.datatype == str) else '+'} {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s {'||' if (self.current_datatype == str) else '+'} {self._output[0]})', [other]+self._output[1]) if isinstance(other, int) or isinstance(other , float) else (f'(%s || {self._output[0]})', [other if isinstance(other, str) else str(other)]+self._output[1])
        new_op.current_datatype = str if (isinstance(other, ColumnsOperation) and other.current_datatype == str) or (isinstance(other, Column) and other.datatype == str) or self.current_datatype == str or ( not isinstance(other, ColumnsOperation) and not isinstance(other,Column) and not isinstance(other, int) and not isinstance(other, float)) else self.current_datatype
        return new_op

    def __sub__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} - {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} - {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} - %s)', self._output[1]+[other])
        return new_op

    def __rsub__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} - {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} - {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s - {self._output[0]})', [other]+self._output[1])
        return new_op

    def __mul__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} * {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} * {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} * %s)', self._output[1]+[other])
        return new_op

    def __rmul__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} * {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} * {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s * {self._output[0]})', [other]+self._output[1])
        return new_op

    def __pow__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(POW({self._output[0]} , {other._output[0]}))', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'(POW({self._output[0]} , {other.name}))', self._output[1]) if isinstance(other, Column) else (f'(POW({self._output[0]} , %s))', self._output[1]+[other])
        return new_op

    def __rpow__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(POW({other._output[0]} , {self._output[0]}))', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'(POW({other.name} , {self._output[0]}))', self._output[1]) if isinstance(other, Column) else (f'(POW(%s , {self._output[0]}))', [other]+self._output[1])
        return new_op

    def __truediv__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} / {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} / {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} / %s)', self._output[1]+[other])
        return new_op

    def __rtruediv__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} / {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} / {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s / {self._output[0]})', [other]+self._output[1])
        return new_op

    def __mod__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} % {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} % {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} % %s)', self._output[1]+[other])
        return new_op

    def __rmod__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} % {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} % {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(%s % {self._output[0]})', [other]+self._output[1])
        return new_op


    def __getitem__(self, key: slice):
        new_op = ColumnsOperation(self.col_obj)
        new_op.current_datatype = str
        if self._output:
            if key.start == None and key.stop ==  None:
                new_op._output = (f'(SUBSTRING({self._output[0]} , 1 , LENGTH({self._output[0]}) + 1))', self._output[1] + self._output[1])   #
            elif key.start == None and key.stop < 0:
                new_op._output = (f'(SUBSTRING({self._output[0]} , 1 , LENGTH({self._output[0]}) - %s))', self._output[1] + self._output[1] + [abs(key.stop)])  #
            elif key.start == None and key.stop >= 0:
                new_op._output = (f'(SUBSTRING({self._output[0]} , 1 , %s))', self._output[1] + [key.stop])  #  
            elif key.start >= 0 and key.stop ==  None:
                new_op._output = (f'(SUBSTRING({self._output[0]} , %s , LENGTH({self._output[0]})))', self._output[1] + [key.start + 1] + self._output[1])  #   
            elif key.start < 0 and key.stop == None:
                new_op._output = (f'(SUBSTRING({self._output[0]} , LENGTH({self._output[0]}) - %s , LENGTH({self._output[0]})))', self._output[1] + self._output[1] + [abs(key.start) - 1] + self._output[1])  #
            elif key.start >= 0 and key.stop < 0:
                new_op._output = (f'(SUBSTRING({self._output[0]} , %s , LENGTH({self._output[0]}) - %s))', self._output[1] +  [key.start + 1] + self._output[1] + [abs(key.stop - key.start)])  #  
            elif key.start >= 0 and key.stop > 0:
                new_op._output = (f'(SUBSTRING({self._output[0]} , %s , %s))', self._output[1] + [key.start + 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop < 0:
                new_op._output = (f'(SUBSTRING({self._output[0]} , LENGTH({self._output[0]}) - %s , %s))', self._output[1] + self._output[1] + [abs(key.start) - 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop > 0:
                new_op._output = (f'(SUBSTRING({self._output[0]} , LENGTH({self._output[0]}) - %s ,  %s - (LENGTH({self._output[0]}) - %s)))', self._output[1] + self._output[1] + [abs(key.start) - 1, key.stop] + self._output[1] + [abs(key.start)])
        else:
            if key.start == None and key.stop ==  None:
                new_op._output = (f'(SUBSTRING({self.col_obj.name} , 1 , LENGTH({self.col_obj.name}) + 1))', [])   #
            elif key.start == None and key.stop < 0:
                new_op._output = (f'(SUBSTRING({self.col_obj.name} , 1 , LENGTH({self.col_obj.name}) - %s))', [abs(key.stop)])  #
            elif key.start == None and key.stop >= 0:
                new_op._output = (f'(SUBSTRING({self.col_obj.name} , 1 , %s))', [key.stop])  #  
            elif key.start >= 0 and key.stop ==  None:
                new_op._output = (f'(SUBSTRING({self.col_obj.name} , %s , LENGTH({self.col_obj.name})))', [key.start + 1])  #   
            elif key.start < 0 and key.stop == None:
                new_op._output = (f'(SUBSTRING({self.col_obj.name} , LENGTH({self.col_obj.name}) - %s , LENGTH({self.col_obj.name})))', [abs(key.start) - 1])  #
            elif key.start >= 0 and key.stop < 0:
                new_op._output = (f'(SUBSTRING({self.col_obj.name} , %s , LENGTH({self.col_obj.name}) - %s))', [key.start + 1, abs(key.stop - key.start)])  #  
            elif key.start >= 0 and key.stop > 0:
                new_op._output = (f'(SUBSTRING({self.col_obj.name} , %s , %s))', [key.start + 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop < 0:
                new_op._output = (f'(SUBSTRING({self.col_obj.name} , LENGTH({self.col_obj.name}) - %s , %s))', [abs(key.start) - 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop > 0:
                new_op._output = (f'(SUBSTRING({self.col_obj.name} , LENGTH({self.col_obj.name}) - %s ,  %s - (LENGTH({self.col_obj.name}) - %s)))', [abs(key.start) - 1, key.stop, abs(key.start)])
        return new_op

    def eq(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} = {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} = {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} = %s)', self._output[1] + [value])
        return new_op

    def __eq__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} = {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} = {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} = %s)', self._output[1] + [value])
        return new_op

    def ne(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} != {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} != {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} != %s)', self._output[1] + [value])
        return new_op

    def __ne__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} != {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} != {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} != %s)', self._output[1] + [value])
        return new_op

    def gt(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} > {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} > {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} > %s)', self._output[1] + [value])
        return new_op

    def __gt__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} > {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} > {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} > %s)', self._output[1] + [value])
        return new_op

    def lt(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} < {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} < {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} < %s)', self._output[1] + [value])
        return new_op

    def __lt__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} < {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} < {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} < %s)', self._output[1] + [value])
        return new_op

    def ge(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} >= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} >= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} >= %s)', self._output[1] + [value])
        return new_op

    def __ge__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} >= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} >= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} >= %s)', self._output[1] + [value])
        return new_op

    def le(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} <= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} <= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} <= %s)', self._output[1] + [value])
        return new_op

    def __le__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} <= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} <= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} <= %s)', self._output[1] + [value])
        return new_op

    def __and__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} AND {value._output[0]})', self._output[1] + value._output[1])
        return new_op

    def __or__(self, value):        
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} OR {value._output[0]})', self._output[1] + value._output[1])
        return new_op

    def like(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"({self._output[0]} like {value._output[0]})", (self._output[1] + value._output[1]) if self._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} like {value.name})', self._output[1]) if isinstance(value , Column) else (f'({self._output[0]} like %s)', self._output[1] + [f'{value}'])
        return new_op

    def startswith(self, prefix):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"({self._output[0]} like {prefix._output[0]} || '%%')", (self._output[1] + prefix._output[1]) if self._output else prefix._output[1]) if isinstance(prefix, ColumnsOperation) else (f"({self._output[0]} like {prefix.name} || '%%')", self._output[1]) if isinstance(prefix , Column) else (f"({self._output[0]} like %s || '%%')", self._output[1] + [f'{prefix}'])
        return new_op

    def endswith(self, suffix):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"({self._output[0]} like '%%' || {suffix._output[0]})", (self._output[1] + suffix._output[1]) if self._output else suffix._output[1]) if isinstance(suffix, ColumnsOperation) else (f"({self._output[0]} like '%%' || {suffix.name})", self._output[1]) if isinstance(suffix , Column) else (f"({self._output[0]} like '%%' || %s)", self._output[1] + [f'{suffix}'])
        return new_op

    def contains(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"({self._output[0]} like '%%' || {value._output[0]} || '%%')", (self._output[1] + value._output[1]) if self._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self._output[0]} like '%%' || {value.name} || '%%')", self._output[1]) if isinstance(value , Column) else (f"({self._output[0]} like '%%' || %s || '%%')", self._output[1] + [f'{value}'])
        return new_op

    def add_end(self, content):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} || {content._output[0]})', self._output[1]+content._output[1] if self._output else content._output[1]) if isinstance(content, ColumnsOperation) else (f'({self._output[0]} || {content.name})', self._output[1] if self._output else []) if isinstance(content, Column) else (f'({self._output[0]} || %s)', self._output[1]+[content] if self._output else [content])
        new_op.current_datatype = str
        return new_op

    def add_first(self, content):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({content._output[0]} || {self._output[0]})', content._output[1]+self._output[1] if self._output else content._output[1]) if isinstance(content, ColumnsOperation) else (f'({content.name} || {self._output[0]})', self._output[1] if self._output else []) if isinstance(content, Column) else (f'(%s || {self._output[0]})', [content]+self._output[1] if self._output else [content])
        new_op.current_datatype = str
        return new_op

    def replace(self, old: str, new: str):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(REPLACE({self._output[0]} , %s , %s))', self._output[1] + [old, new]) if self._output else (f'(REPLACE({self.col_obj.name} , %s , %s))', [old, new])
        new_op.current_datatype = str
        return new_op

    def upper(self):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(UPPER({self._output[0]}))', self._output[1]) if self._output else (f'(UPPER({self.col_obj.name}))', [])
        new_op.current_datatype = str
        return new_op

    def lower(self):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(LOWER({self._output[0]}))', self._output[1]) if self._output else (f'(LOWER({self.col_obj.name}))', [])
        new_op.current_datatype = str
        return new_op

    def strip(self, chars: str = ' '):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"(TRIM(BOTH '{chars}' FROM {self._output[0]}))", self._output[1]) if self._output else (f"(TRIM(BOTH '{chars}' FROM {self.col_obj.name}))", [])
        new_op.current_datatype = str
        return new_op

    def lstrip(self, chars: str = ' '):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"(TRIM(LEADING '{chars}' FROM {self._output[0]}))", self._output[1]) if self._output else (f"(TRIM(LEADING '{chars}' FROM {self.col_obj.name}))", [])
        new_op.current_datatype = str
        return new_op

    def rstrip(self, chars: str = ' '):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"(TRIM(TRAILING '{chars}' FROM {self._output[0]}))", self._output[1]) if self._output else (f"(TRIM(TRAILING '{chars}' FROM {self.col_obj.name}))", [])
        new_op.current_datatype = str
        return new_op

    def In(self, column: Column|ColumnsOperation = None, where: ColumnsOperation = None, data_list: list = None):
        if isinstance(column, list):
            data_list, column = column, None #So user can simply In(['Alice', 'Bob']) with out passing arguments
        if not column and not data_list:
            raise Exception("In() requires either data_list or column")
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} IN ({", ".join(["%s" for _ in data_list])}))', self._output[1] + data_list) if data_list is not None else (f'({self._output[0]} IN (SELECT {column.name if isinstance(column, Column) else column._output[0]} FROM {(column.name if isinstance(column, Column) else column.col_obj.name).split(".")[0]}{f" WHERE {where._output[0]}" if isinstance(where, ColumnsOperation) else f" WHERE {where.name}" if isinstance(where, Column) else ""}))', self._output[1] + ([] if isinstance(column, Column) else column._output[1]) + (where._output[1] if isinstance(where, ColumnsOperation) else [])) if isinstance(column, (Column, ColumnsOperation)) else None
        
        return new_op


class Column:
    def __init__(self, table_obj: Table, column_name: str, datatype: type):
        self.name= table_obj.name_+'."'+column_name+'"'
        self.first_name= f'"{column_name}"'
        self.table_obj= table_obj
        self.datatype= datatype

    def __hash__(self):
        return hash(self.name)

    def __add__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob + value

    def __radd__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value + temp_ob

    def __sub__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob - value

    def __rsub__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value - temp_ob

    def __mul__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob * value

    def __rmul__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value * temp_ob

    def __pow__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob ** value

    def __rpow__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value ** temp_ob

    def __truediv__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob / value

    def __rtruediv__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value / temp_ob

    def __mod__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob % value

    def __rmod__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return value % temp_ob

    def eq(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} = {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} = {value.name})', []) if isinstance(value, Column) else (f'({self.name} = %s)', [value])
        return temp_ob

    def __eq__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} = {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} = {value.name})', []) if isinstance(value, Column) else (f'({self.name} = %s)', [value])
        return temp_ob

    def ne(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} != {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} != {value.name})', []) if isinstance(value, Column) else (f'({self.name} != %s)', [value])
        return temp_ob

    def __ne__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} != {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} != {value.name})', []) if isinstance(value, Column) else (f'({self.name} != %s)', [value])
        return temp_ob

    def gt(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} > {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} > {value.name})', []) if isinstance(value, Column) else (f'({self.name} > %s)', [value])
        return temp_ob

    def __gt__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} > {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} > {value.name})', []) if isinstance(value, Column) else (f'({self.name} > %s)', [value])
        return temp_ob

    def lt(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} < {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} < {value.name})', []) if isinstance(value, Column) else (f'({self.name} < %s)', [value])
        return temp_ob

    def __lt__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} < {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} < {value.name})', []) if isinstance(value, Column) else (f'({self.name} < %s)', [value])
        return temp_ob

    def ge(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} >= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} >= {value.name})', []) if isinstance(value, Column) else (f'({self.name} >= %s)', [value])
        return temp_ob

    def __ge__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} >= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} >= {value.name})', []) if isinstance(value, Column) else (f'({self.name} >= %s)', [value])
        return temp_ob

    def le(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} <= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} <= {value.name})', []) if isinstance(value, Column) else (f'({self.name} <= %s)', [value])
        return temp_ob

    def __le__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} <= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} <= {value.name})', []) if isinstance(value, Column) else (f'({self.name} <= %s)', [value])
        return temp_ob

    def __getitem__(self, key: slice):
        temp_ob = ColumnsOperation(self)
        if key.start == None and key.stop ==  None:
            temp_ob._output = (f'(SUBSTRING({temp_ob.col_obj.name} , 1 , LENGTH({temp_ob.col_obj.name}) + 1))', [])   #
        elif key.start == None and key.stop < 0:
            temp_ob._output = (f'(SUBSTRING({temp_ob.col_obj.name} , 1 , LENGTH({temp_ob.col_obj.name}) - %s))', [abs(key.stop)])  #
        elif key.start == None and key.stop >= 0:
             temp_ob._output = (f'(SUBSTRING({temp_ob.col_obj.name} , 1 , %s))', [key.stop])  #  
        elif key.start >= 0 and key.stop ==  None:
            temp_ob._output = (f'(SUBSTRING({temp_ob.col_obj.name} , %s , LENGTH({temp_ob.col_obj.name})))', [key.start + 1])  #   
        elif key.start < 0 and key.stop == None:
            temp_ob._output = (f'(SUBSTRING({temp_ob.col_obj.name} , LENGTH({temp_ob.col_obj.name}) - %s , LENGTH({temp_ob.col_obj.name})))', [abs(key.start) - 1])  #
        elif key.start >= 0 and key.stop < 0:
            temp_ob._output = (f'(SUBSTRING({temp_ob.col_obj.name} , %s , LENGTH({temp_ob.col_obj.name}) - %s))', [key.start + 1, abs(key.stop - key.start)])  #  
        elif key.start >= 0 and key.stop > 0:
            temp_ob._output = (f'(SUBSTRING({temp_ob.col_obj.name} , %s , %s))', [key.start + 1, key.stop - key.start])  #
        elif key.start < 0 and key.stop < 0:
            temp_ob._output = (f'(SUBSTRING({temp_ob.col_obj.name} , LENGTH({temp_ob.col_obj.name}) - %s , %s))', [abs(key.start) - 1, key.stop - key.start])  #
        elif key.start < 0 and key.stop > 0:
            temp_ob._output = (f'(SUBSTRING({temp_ob.col_obj.name} , LENGTH({temp_ob.col_obj.name}) - %s ,  %s - (LENGTH({temp_ob.col_obj.name}) - %s)))', [abs(key.start) - 1, key.stop, abs(key.start)])
        return temp_ob

    def strip(self, chars: str = ' '):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"(TRIM(BOTH '{chars}' FROM {temp_ob._output[0]}))", temp_ob._output[1]) if temp_ob._output else (f"(TRIM(BOTH '{chars}' FROM {temp_ob.col_obj.name}))", [])
        return temp_ob

    def lstrip(self, chars: str = ' '):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"(TRIM(LEADING '{chars}' FROM {temp_ob._output[0]}))", temp_ob._output[1]) if temp_ob._output else (f"(TRIM(LEADING '{chars}' FROM {temp_ob.col_obj.name}))", [])
        return temp_ob

    def rstrip(self, chars: str = ' '):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"(TRIM(TRAILING '{chars}' FROM {temp_ob._output[0]}))", temp_ob._output[1]) if temp_ob._output else (f"(TRIM(TRAILING '{chars}' FROM {temp_ob.col_obj.name}))", [])
        return temp_ob

    def add_end(self, content):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} || {content._output[0]})', [content._output[1]]) if isinstance(content, ColumnsOperation) else (f'({self.name} || {content.name})', []) if isinstance(content, Column) else (f'({self.name} || %s)', [content])
        return temp_ob

    def add_first(self, content):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({content._output[0]} || {self.name})', [content._output[1]]) if isinstance(content, ColumnsOperation) else (f'({content.name} || {self.name})', []) if isinstance(content, Column) else (f'(%s || {self.name})', [content])
        return temp_ob
    
    def lower(self):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(LOWER({temp_ob._output[0]}))', temp_ob._output[1]) if temp_ob._output else (f'(LOWER({temp_ob.col_obj.name}))', [])
        return temp_ob

    def upper(self):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(UPPER({temp_ob._output[0]}))', temp_ob._output[1]) if temp_ob._output else (f'(UPPER({temp_ob.col_obj.name}))', [])
        return temp_ob

    def replace(self, old, new):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(REPLACE({temp_ob._output[0]} , %s , %s))', temp_ob._output[1] + [old, new]) if temp_ob._output else (f'(REPLACE({temp_ob.col_obj.name} , %s , %s))', [old, new])
        return temp_ob

    def like(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like {value._output[0]})", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} like {value.name})', temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f'({self.name} like %s)', (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def startswith(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like {value._output[0]} || '%%')", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self.name} like {value.name} || '%%')", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"({self.name} like %s || '%%')", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def endswith(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like '%%' || {value._output[0]})", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self.name} like '%%' || {value.name})", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"({self.name} like '%%' || %s)", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def contains(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like '%%' || {value._output[0]} || '%%')", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self.name} like '%%' || {value.name} || '%%')", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"({self.name} like '%%' || %s || '%%')", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def rename(self, column: 'Column', new_name: str) -> None:
        query = f'ALTER TABLE {self.table_obj.name_} RENAME COLUMN {column.first_name} TO "{new_name}";'
        self.table_obj._exc(query)
        self.table_obj.__delattr__(column.first_name.strip('"'))
        self.table_obj.__setattr__(new_name, Column(self.table_obj, new_name, column.datatype))

    def delete_column(self, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool) -> None:
        if are_you_sure and are_you_really_sure and for_sure:
            query = f'ALTER TABLE {self.table_obj.name_} DROP COLUMN {self.first_name};'
            self.table_obj._exc(query)
            self.table_obj.__delattr__(self.first_name[1:-1])

    def In(self, column: Column|ColumnsOperation = None, where: ColumnsOperation = None, data_list: list = None):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (self.name, [])
        return temp_ob.In(column=column, where=where, data_list=data_list)


class BatchOperation:
    def __init__(self, table_object: Table):
        self.script = []
        self.table_obj = table_object

    def update(self, update: dict[Column, Any], where: ColumnsOperation, table: Table = None) -> 'BatchOperation':
        if not update:
            return self
        temp_list= []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        self.script.append([f'UPDATE {table.name_ if table else self.table_obj.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=%s' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1]])
        return self

    def insert(self, insert: dict[Column, Any], table: Table = None) -> 'BatchOperation':
        if not insert:
            self.script.append([f'INSERT INTO {self.table_obj.name_ if not table else table.name_} DEFAULT VALUES;', []])
            return self
        self.script.append([f'INSERT INTO {table.name_ if table else self.table_obj.name_} ({', '.join(i.first_name for i in list(insert.keys()))}) VALUES ({', '.join(f'%s' for k in insert)})' , [v for v in list(insert.values())]])
        return self

    def delete_row(self, where: ColumnsOperation, table: Table = None) -> 'BatchOperation':
        self.script.append([f'DELETE FROM {table.name_ if table else self.table_obj.name_} WHERE {where._output[0]};', where._output[1]])
        return self
        
    def run(self):
        self.table_obj._excs(self.script)


class Join:
    
    class Inner:
        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            self._output =  (f'INNER JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])
            
    class Left:
        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            self._output =  (f'LEFT JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])

    class Right:
        def __init__(self, table: Table, match_case_condition: ColumnsOperation):
            self._output = (f'RIGHT JOIN {table.name_} ON {match_case_condition._output[0]}', match_case_condition._output[1])


class Table:
    PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
    def __init__(self, obj: Driver, table_name: str):
        self.name_ = f'"{table_name}"'
        self.db_obj = obj
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
        for i in self.get_table_info():
            self.__setattr__(i['name'], Column(self, i['name'], i['datatype']))

    def get_table_info(self):
        query = """
            SELECT
                c.ordinal_position AS cid,
                c.column_name AS name,
                c.data_type AS type,
                CASE WHEN c.is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull,
                c.column_default AS dflt_value,
                CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN 1 ELSE 0 END AS pk,
                c.udt_name AS full_type,
                CASE WHEN c.is_identity = 'YES' THEN 1 ELSE 0 END AS auto_increment,
                c.numeric_precision AS num_precision,
                c.numeric_scale AS num_scale,
                c.datetime_precision AS datetime_precision,
                rc.unique_constraint_name AS fk_name,
                ccu.table_name AS fk_table,
                ccu.column_name AS fk_column,
                rc.update_rule AS fk_on_update,
                rc.delete_rule AS fk_on_delete
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu
                ON c.table_schema = kcu.table_schema
                AND c.table_name = kcu.table_name
                AND c.column_name = kcu.column_name
                AND kcu.position_in_unique_constraint IS NOT NULL
            LEFT JOIN information_schema.referential_constraints rc
                ON kcu.constraint_schema = rc.constraint_schema
                AND kcu.constraint_name = rc.constraint_name
            LEFT JOIN information_schema.constraint_column_usage ccu
                ON rc.constraint_schema = ccu.constraint_schema
                AND rc.constraint_name = ccu.constraint_name
            LEFT JOIN information_schema.table_constraints tc
                ON c.table_schema = tc.table_schema
                AND c.table_name = tc.table_name
                AND tc.constraint_type = 'PRIMARY KEY'
                AND EXISTS (
                    SELECT 1 FROM information_schema.constraint_column_usage ccu2
                    WHERE tc.constraint_name = ccu2.constraint_name
                    AND ccu2.column_name = c.column_name
                )
            WHERE c.table_schema = current_schema()
                AND c.table_name = %s
            ORDER BY c.ordinal_position;
        """
        return [{'cid': row[0],'name': row[1],'type': row[2],'datatype': (int if row[2].lower() in ('smallint', 'integer', 'bigint', 'serial', 'smallserial', 'bigserial') else float) if row[2].lower() in ('smallint', 'integer', 'bigint', 'serial', 'smallserial', 'bigserial', 'bit', 'numeric', 'decimal', 'real', 'double precision', 'money') else bool if row[2].lower() == 'boolean' else object if row[2].lower() in ('date', 'time without time zone', 'time with time zone','timestamp without time zone', 'timestamp with time zone','interval') else bool if row[2].lower() == 'boolean' else bytes if row[2].lower() == 'bytea' else str if row[2].lower() in ('character varying', 'character', 'text', 'json', 'jsonb', 'uuid', 'date', 'time without time zone', 'time with time zone', 'timestamp without time zone', 'timestamp with time zone', 'interval') else bytes if row[2].lower() == 'bytea' else bool if row[2].lower() == 'boolean' else str,'notnull': bool(row[3]),'dflt_value': row[4],'pk': bool(row[5]),'full_type': row[6] if row[6] else row[2],'auto_increment': bool(row[7]),'num_precision': row[8],'num_scale': row[9],'datetime_precision': row[10],'fk_name': row[11],'fk_table': row[12],'fk_column': row[13],'fk_on_update': row[14],'fk_on_delete': row[15]} for row in self._excfp(query, (self.name_.strip('"'),))]
        
    def _exc(self, query):
        self.db_obj._exc(query)

    def _excp(self, query, params):
        self.db_obj._excp(query, params)

    def _excf(self, query):
        return self.db_obj._excf(query)

    def _excfp(self, query, params):
        return self.db_obj._excfp(query, params)

    def _excm(self, query, params):
        self.db_obj._excm(query, params)

    def _excs(self, query_params: list):
        self.db_obj._excs(query_params)

    def get_columns_name(self):
        return [i['name'] for i in self.get_table_info()]  
      
    def batch(self) -> 'BatchOperation':
        return BatchOperation(self)

    def update(self, update: dict[Column, Any], where: 'ColumnsOperation') -> None:
        if not update:
            return
        temp_list = []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        self._excp(f'UPDATE {self.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=%s' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1])
        
    def get_row(self,which_columns: list['Column' | 'ColumnsOperation'],where: 'ColumnsOperation' = None,order_by: 'Column' = None):
        if not which_columns:
            return
        tl = []
        wc = []
        [wc.append(i.first_name) if isinstance(i,Column) else [wc.append(i._output[0]), tl.extend(i._output[1])] for i in which_columns]
        return [row[0] for row in (self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} WHERE {where._output[0]} {f'ORDER BY {order_by.first_name}' if order_by else ''};', tl+where._output[1]) if where else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',tl) if tl else self._excf(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',))] if len(which_columns) == 1 else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} WHERE {where._output[0]} {f'ORDER BY {order_by.first_name}' if order_by else ''};', tl+where._output[1]) if where else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',tl) if tl else self._excf(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',)
        
    def insert(self, insert: dict['Column', Any]) -> None:
        if not insert:
            self._exc(f'INSERT INTO {self.name_} DEFAULT VALUES;')
            return
        self._excp(f'INSERT INTO {self.name_} ({', '.join(i.first_name for i in list(insert.keys()))}) VALUES ({', '.join(f'%s' for k in insert)})', [v for v in list(insert.values())])

    def custom_execute(self, query: str, params: list = None) -> None:
        self._excp(query, params) if params else self._exc(query)
            
    def custom_execute_many(self, query: str, params: list = None) -> None:
        self._excm(query, params)

    def custom_execute_with_fetch(self, query: str, params: list = None) -> Any:
        return self._excfp(query, params) if params else self._excf(query)

    def delete_row(self, where: 'ColumnsOperation') -> None:
        self._excp(f'DELETE FROM {self.name_} WHERE {where._output[0]};', where._output[1])

    def delete_table(self, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool) -> None:
        if are_you_sure and are_you_really_sure and for_sure:
            self._exc(f'DROP TABLE {self.name_};')
            self.db_obj.__delattr__(self.name_[1:-1])

    def delete_column(
        self,
        column: 'Column',
        are_you_sure: bool,
        are_you_really_sure: bool,
        for_sure: bool
        ) -> None:
        if are_you_sure and are_you_really_sure and for_sure:
            self._exc(f'ALTER TABLE {self.name_} DROP COLUMN {column.first_name};')
            self.__delattr__(column.first_name[1:-1])

    def add_column(self,column_name: str,data_type: str,nullable: bool = True,default: Any = None,auto_increment: bool = False,primary_key: bool = False,unique: bool = False,) -> None:
        col_def = f'"{column_name}" {data_type}'
        col_def += ' NOT NULL' if not nullable else ''
        col_def += (f" DEFAULT '{default}'" if isinstance(default, str) else f" DEFAULT {default}") if default is not None else ''
        col_def += " GENERATED BY DEFAULT AS IDENTITY" if auto_increment and data_type not in ("SMALLSERIAL", "SERIAL", "BIGSERIAL") else ''
        col_def += " UNIQUE" if unique else ''
        self._exc(f"ALTER TABLE {self.name_} ADD COLUMN {col_def};")
        self._exc(f'ALTER TABLE {self.name_} ADD PRIMARY KEY ("{column_name}");') if primary_key else None
        type_lower = data_type.lower().split("(")[0].strip()
        self.__setattr__(column_name, Column(self, column_name, int if type_lower in ('smallint', 'integer', 'bigint', 'serial', 'smallserial', 'bigserial') else float) if type_lower in ('smallint', 'integer', 'bigint', 'serial', 'smallserial', 'bigserial', 'bit', 'numeric', 'decimal', 'real', 'double precision', 'money') else bool if type_lower == 'boolean' else object if type_lower in ('date', 'time without time zone', 'time with time zone','timestamp without time zone', 'timestamp with time zone','interval') else bool if type_lower == 'boolean' else bytes if type_lower == 'bytea' else str if type_lower in ('character varying', 'character', 'text', 'json', 'jsonb', 'uuid', 'date', 'time without time zone', 'time with time zone', 'timestamp without time zone', 'timestamp with time zone', 'interval') else bytes if type_lower == 'bytea' else bool if type_lower == 'boolean' else str)

    def rename_table(self, new_name: str) -> None:
        self._exc(f'ALTER TABLE {self.name_} RENAME TO "{new_name}";')
        self.db_obj.__delattr__(self.name_[1:-1])
        self.db_obj.__setattr__(new_name, Table(obj=self.db_obj, table_name=new_name))
        self.name_ = f'"{new_name}"'

    def rename_column(self, column: 'Column', new_name: str) -> None:
        query = f'ALTER TABLE {self.name_} RENAME COLUMN {column.first_name} TO "{new_name}";'
        self._exc(query)
        self.__delattr__(column.first_name.strip('"'))
        self.__setattr__(new_name, Column(self, new_name, column.datatype))

    def create_index(
        self,
        index_name: str,
        columns: list['Column'],
        unique: bool = False,
        where: 'ColumnsOperation' = None
        ) -> None:
        if where:
            wr = f'WHERE {where._output[0]}'
            for i in where._output[1]:
                wr=wr.replace('%s',i if isinstance(i,str) else str(i),1)
        self._excp(f'CREATE {'UNIQUE ' if unique else ''}INDEX {index_name} ON {self.name_} ({','.join(i.first_name for i in columns)}) {wr if where else ''}',[])

    def delete_index(self, index_name: str) -> None:
        self._exc(f'DROP INDEX IF EXISTS "{index_name}";')

    def get_indexes_info(self) -> Any:
        query = """
            SELECT
                i.relname AS index_name,
                am.amname AS index_type,
                pg_get_indexdef(i.oid) AS index_def,
                indisunique::int AS is_unique,
                indisprimary::int AS is_primary
            FROM pg_index x
            JOIN pg_class c ON c.oid = x.indrelid
            JOIN pg_class i ON i.oid = x.indexrelid
            LEFT JOIN pg_am am ON i.relam = am.oid
            WHERE c.relname = %s
              AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = current_schema())
        """
        return [{'idx_name': r[0],'index_type': r[1],'definition': r[2],'unique': bool(r[3]),'primary': bool(r[4])}for r in self._excfp(query, (self.name_.strip('"'),))]

    def bulk_insert(self, columns: list['Column'], data_list: list) -> None:
        self._excm(f'INSERT INTO {self.name_} ({', '.join(i.first_name for i in columns)}) VALUES ({', '.join('%s' for i in columns)});',data_list)

    def bulk_update(self, update: dict['Column', Any], where: 'ColumnsOperation', data_list: list) -> None:
        """use db.PLACE_HOLDER or table.PLACE_HOLDER for parameters you wanna take from data_list
        Like bulk_update({col_1:db.PLACE_HOLDER}, where= col_2*col_3 == db.PLACE_HOLDER , data_list = [[1,2],[3,4],[5,6]])"""
        temp_list = []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        query_splited = f'UPDATE {self.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value, Column) else f'{key.first_name}={self.PLACE_HOLDER}' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0].replace('%s', self.PLACE_HOLDER)}' for key , value in list(update.items()))} WHERE {where._output[0].replace('%s', self.PLACE_HOLDER)};'.split(self.PLACE_HOLDER)
        query= query_splited[0]
        for a,i in enumerate(temp_list+where._output[1]):
            query = query +( f'"{i}"' if isinstance(i,str) and not i == self.PLACE_HOLDER else str(i))+ query_splited[a+1] #All "? || '%'" thing are because of Column.contain() method and .startswith() and .endswith() that have "%" in output value
        try:
            self._excm(query.replace(self.PLACE_HOLDER, '%s'), data_list)
        except Exception as e:
            if "Incorrect number of bindings" in str(e):
                raise Exception(f'number of `PLACE_HOLDERS` must be equals to number of items in each of `data_list` items.\n if it is so, make sure that there is no "{self.PLACE_HOLDER}" literal string in your query because it is reserved for this orm. you can change it on you own need with `mytable.PLACE_HOLDER = "you own idea"`')
            else:
                raise

    def join(
        self,
        columns: list['Column'],
        joins_list: list['Join.Inner | Join.Left | Join.Right'],
        where: 'ColumnsOperation' = None,
        order_by: 'Column' = None
        ) -> Any:
        tl = []
        [tl.extend(i._output[1]) if isinstance(i,ColumnsOperation) else None for i in columns]
        [tl.extend(i._output[1]) for i in joins_list]
        return self._excfp(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}'if isinstance(i,Column)else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")")else i._output[0]} AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'WHERE {where._output[0]}'if where else''} {f'ORDER BY {order_by.name}' if order_by else''}', tl+where._output[1]) if where else self._excfp(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}'if isinstance(i,Column)else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")") else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}'for i in columns)} FROM {self.name_} {' '.join(i._output[0]for i in joins_list)} {f'ORDER BY {order_by.name}' if order_by else''}', tl) if tl else self._excf(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column) else f'{i._output[0][1:-1] if i._output[0].startswith('(') and i._output[0].endswith(')') else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'ORDER BY {order_by.name}'if order_by else''}')
        # The above line is approximately 1381 characters, which is not standard, but it is written this way
        # to improve performance in the Driver class and to avoid checking whether the second item in the query
        # is an empty list for each input.


class DataTypes:
    """
    Complete PostgreSQL 16 Data Types as static methods.
    Each method returns the corresponding SQL data type string.
    """

    # ========================
    # Numeric Data Types
    # ========================

    @staticmethod
    def BIT(size: int) -> str:
        if size < 1 or size > 64:
            raise ValueError("Size for BIT must be between 1 and 64.")
        return f"BIT({size})"

    @staticmethod
    def SMALLINT() -> str:
        return "SMALLINT"

    @staticmethod
    def INTEGER() -> str:
        return "INTEGER"

    @staticmethod
    def BIGINT() -> str:
        return "BIGINT"

    @staticmethod
    def DECIMAL(precision: int = 10, scale: int = 0) -> str:
        if precision < 1 or scale < 0 or scale > precision:
            raise ValueError("Precision must be >= 1 and scale must be >= 0 and <= precision.")
        return f"DECIMAL({precision}, {scale})"

    @staticmethod
    def NUMERIC(precision: int = 10, scale: int = 0) -> str:
        if precision < 1 or scale < 0 or scale > precision:
            raise ValueError("Precision must be >= 1 and scale must be >= 0 and <= precision.")
        return f"NUMERIC({precision}, {scale})"

    @staticmethod
    def REAL() -> str:
        return "REAL"

    @staticmethod
    def DOUBLE_PRECISION() -> str:
        return "DOUBLE PRECISION"

    @staticmethod
    def MONEY() -> str:
        return "MONEY"

    # ========================
    # Serial (Auto-increment) Types
    # ========================

    @staticmethod
    def SERIAL() -> str:
        return "SERIAL"

    @staticmethod
    def SMALLSERIAL() -> str:
        return "SMALLSERIAL"

    @staticmethod
    def BIGSERIAL() -> str:
        return "BIGSERIAL"

    # ========================
    # String Data Types
    # ========================

    @staticmethod
    def CHAR(length: int = 1) -> str:
        if length < 1:
            raise ValueError("Length for CHAR must be at least 1.")
        return f"CHAR({length})"

    @staticmethod
    def VARCHAR(length: int = 255) -> str:
        if length < 1:
            raise ValueError("Length for VARCHAR must be at least 1.")
        return f"VARCHAR({length})"

    @staticmethod
    def TEXT() -> str:
        return "TEXT"

    # ========================
    # Binary Data Types
    # ========================

    @staticmethod
    def BYTEA() -> str:
        return "BYTEA"

    # ========================
    # Date and Time Data Types
    # ========================

    @staticmethod
    def DATE() -> str:
        return "DATE"

    @staticmethod
    def TIME(precision: int = None) -> str:
        if precision is not None:
            return f"TIME({precision})"
        return "TIME"

    @staticmethod
    def TIMETZ(precision: int = None) -> str:
        if precision is not None:
            return f"TIMETZ({precision})"
        return "TIMETZ"

    @staticmethod
    def TIMESTAMP(precision: int = None) -> str:
        if precision is not None:
            return f"TIMESTAMP({precision})"
        return "TIMESTAMP"

    @staticmethod
    def TIMESTAMPTZ(precision: int = None) -> str:
        if precision is not None:
            return f"TIMESTAMPTZ({precision})"
        return "TIMESTAMPTZ"

    @staticmethod
    def INTERVAL() -> str:
        return "INTERVAL"

    # ========================
    # Boolean Type
    # ========================

    @staticmethod
    def BOOLEAN() -> str:
        return "BOOLEAN"

    # ========================
    # JSON Types
    # ========================

    @staticmethod
    def JSON() -> str:
        return "JSON"

    @staticmethod
    def JSONB() -> str:
        return "JSONB"

    # ========================
    # UUID Type
    # ========================

    @staticmethod
    def UUID() -> str:
        return "UUID"

    # ========================
    # Spatial Data Types (PostGIS)
    # ========================

    @staticmethod
    def GEOMETRY() -> str:
        return "GEOMETRY"

    @staticmethod
    def GEOGRAPHY() -> str:
        return "GEOGRAPHY"

    @staticmethod
    def POINT() -> str:
        return "POINT"

    @staticmethod
    def LINESTRING() -> str:
        return "LINESTRING"

    @staticmethod
    def POLYGON() -> str:
        return "POLYGON"

    @staticmethod
    def MULTIPOINT() -> str:
        return "MULTIPOINT"

    @staticmethod
    def MULTILINESTRING() -> str:
        return "MULTILINESTRING"

    @staticmethod
    def MULTIPOLYGON() -> str:
        return "MULTIPOLYGON"

    @staticmethod
    def GEOMETRYCOLLECTION() -> str:
        return "GEOMETRYCOLLECTION"

    # ========================
    # Array Type
    # ========================

    @staticmethod
    def ARRAY(element_type: str) -> str:
        return f"{element_type}[]"


class TableStructure:
    ON_ACTION = Literal['CASCADE', 'SET NULL', 'SET DEFAULT', 'RESTRICT', 'NO ACTION']

    def __init__(self, table_name: str):
        self.table_query = ''
        self.primary_keys = []
        self.items = {}
        self.name = f'"{table_name}"'
        self.foreigns = []

    def _validate_column( self,column_name,datatype,default_value,unique,not_null,primary_key,auto_increment):
        if not isinstance(datatype, str):
            raise TypeError("datatype must be a string returned by DataTypes.")

        if primary_key:
            if unique:
                raise Exception("PRIMARY KEY columns cannot be UNIQUE, as they are inherently unique.")

        if column_name in self.items:
            raise Exception(f"Column {column_name} already exists.")

        if isinstance(default_value, bytes):
            raise Exception("Bytes objects cannot be used as default values.")

        for values in self.items.values():
            if values[5] and auto_increment:
                raise Exception("Only one auto-increment column is allowed.")

        numeric_types = ("SMALLINT","INTEGER","BIGINT","DECIMAL","NUMERIC","REAL","DOUBLE PRECISION","SMALLSERIAL","SERIAL","BIGSERIAL")

        if auto_increment:
            if datatype.split("(")[0].strip() not in numeric_types:
                raise Exception("Auto-increment is only allowed on numeric or serial types.")
            if not (primary_key or unique):
                raise Exception("Auto-increment column must be PRIMARY KEY or UNIQUE.")
            if default_value is not None:
                raise Exception("Auto-increment columns cannot have DEFAULT values.")

        if datatype in ("SMALLSERIAL", "SERIAL", "BIGSERIAL"):
            if not not_null:
                raise Exception("Serial types are inherently NOT NULL, so not_null must be True.")
            if not auto_increment:
                raise Exception("Serial types are inherently auto-increment, so auto_increment must be True.")

    def add_column(self, column_name: str, datatype: DataTypes,default_value=None, unique: bool = None,not_null: bool = None,primary_key: bool = None,auto_increment: bool = False):
        column_name = f'"{column_name.strip()}"'
        primary_key, not_null, auto_increment = (True, True, True) if datatype in ("SMALLSERIAL", "SERIAL", "BIGSERIAL") else (primary_key, not_null, auto_increment)
        self._validate_column(column_name,datatype,default_value,unique,not_null,primary_key,auto_increment)
        if type(default_value) == bytes:
            raise Exception('Cant set bytes object as default value')
        self.primary_keys.append(column_name) if primary_key else None
        self.items[column_name] = [datatype, default_value, unique, not_null, primary_key, auto_increment]
        auto_part = " GENERATED BY DEFAULT AS IDENTITY" if auto_increment and datatype not in ("SMALLSERIAL", "SERIAL", "BIGSERIAL") else ""
        self.table_query += f' {column_name.strip()} {datatype}{auto_part}{' UNIQUE' if unique else ''}{' NOT NULL' if not_null else ''}{f" DEFAULT {('TRUE' if default_value else 'FALSE') if isinstance(default_value,bool) else f"'{default_value}'" if type(default_value) == str else str(default_value)}" if default_value is not None else ""},'
        return self

    def delete_column(self, column_name: str):
        column_name = f'"{column_name.strip()}"'
        self.items.pop(column_name)
        query_list = self.table_query.split(',')
        new_list = []
        for item in query_list:
            if item.strip().startswith(column_name):
                continue
            new_list.append(item)
        self.table_query = ','.join(new_list)
        return self

    def get_columns(self):
        items_list = []
        for item in self.items:
            items_dict = {}
            values = self.items[item]
            items_dict['name'] = item
            items_dict['datatype'] = values[0]
            items_dict['default_value'] = values[1]
            items_dict['unique'] = True if values[2] else False
            items_dict['not_null'] = True if values[3] else False
            items_dict['primari_key'] = True if values[4] else False
            items_list.append(items_dict)
        return items_list

    def foreign_key(self, column: str, refrences_table: 'Table',
                    refrences_column: 'Column', on_delete: ON_ACTION = None,
                    on_update: ON_ACTION = None
                    ):
        self.foreigns.append(f'FOREIGN KEY ({column}) REFERENCES {refrences_table.name_} ({refrences_column.first_name}){f' ON DELETE {on_delete}' if on_delete else ''}{f' ON UPDATE {on_update}' if on_update else ''}')
        return self

    def get_structure(self):
        if not self.get_columns():
            raise Exception('You must add at least one column to create a table')
        primary_key_clause = f', PRIMARY KEY({', '.join(self.primary_keys)})' if self.primary_keys else ''
        foreign_key_clause = f', {', '.join(self.foreigns)}' if self.foreigns else ''
        body = self.table_query[:-1] + primary_key_clause + foreign_key_clause
        return f'CREATE TABLE {self.name} ({body});'

            
class Driver():
    PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
    CHARSET = Literal[
    "UTF8",
    "LATIN1",
    "SQL_ASCII",
    "WIN1252",
    "WIN1256",
    "KOI8R",
    "ISO_8859_5",
    "ISO_8859_6",
    "ISO_8859_7",
    "ISO_8859_8",
    "EUC_JP",
    "EUC_KR",
    "EUC_CN",
    "EUC_TW",
    "GB18030",
    "GBK",
    "BIG5",
    "SHIFT_JIS_2004",
    "UHC",
    "JOHAB"
    ]
    COLLATE = Literal[
    "en_US.UTF-8",
    "de_DE.UTF-8",
    "fr_FR.UTF-8",
    "fa_IR.UTF-8",
    "C",
    "POSIX"
    ]
    ISOLATION_LEVEL = Literal['READ UNCOMMITTED', 'READ COMMITTED', 'REPEATABLE READ', 'SERIALIZABLE']
    PRIVILEGES = Literal['ALL PRIVILEGES', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER', 'CREATE', 'CONNECT', 'TEMPORARY', 'EXECUTE', 'USAGE']

    def __init__(self, host: str, port: int, username: str, password: str, db_name: str, create_new_db: bool = False, pool_size: int = 5, connect_timeout: int = 10, client_encoding: CHARSET = "UTF8", collate: COLLATE = None, isolation_level: ISOLATION_LEVEL = 'READ COMMITTED'):
        self.CONNECTION_ERRORS = ('08003', '08006', '08001', '57P01', '57P02', '57P03', '53300', '53000')
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
        self.host = host
        self.port = port
        self._connected = True
        self.username = username
        self.password = password
        self.db_name = db_name
        self.client_encoding = client_encoding
        self.collate = collate
        self.connect_timeout = connect_timeout
        self.isolation_level = isolation_level
        self.config = {
            "host": self.host,
            "port": self.port,
            "user": self.username,
            "password": self.password,
            "dbname": self.db_name,
            "client_encoding": self.client_encoding,
            "connect_timeout": self.connect_timeout
        }
        self.connection_pool = SimpleQueue()
        self.connection_pool_storage = []
        conf = {
            "host": self.host,
            "port": self.port,
            "user": self.username,
            "password": self.password,
            "client_encoding": self.client_encoding,
            "connect_timeout": self.connect_timeout
        }
        if not create_new_db:
            try:
                connection = connect(**self.config)
                connection.close()
            except Exception as e:
                if 'connection' in locals():
                    connection.close()
                raise            
        else:
            try:
                connection = connect(**conf, dbname='postgres')
                connection.autocommit = True
                cur = connection.cursor()
                query = f"CREATE DATABASE {self.db_name} ENCODING '{self.client_encoding}' TEMPLATE template0"
                if self.collate:
                    query += f" LC_COLLATE = '{self.collate}' LC_CTYPE = '{self.collate}'"
                cur.execute(query)
                connection.close()
            except Exception:
                connection.close()
                raise                

        [self._create_connection() for _ in range(pool_size)]

        for i in self.get_tables():
            self.__setattr__(i, Table(self, i))

    def _create_connection(self):
        if not self._connected:
            raise RuntimeError('You have closed the connection, you can not create new connections')
        try:
            con = connect(**self.config)
            cur = con.cursor()
            cur.execute(f"SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL {self.isolation_level};")
            con.commit()
            self.connection_pool.put((con, cur))
            self.connection_pool_storage.append(con)
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                con = connect(**self.config)
                cur = con.cursor()
                cur.execute(f"SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL {self.isolation_level};")
                con.commit()
                self.connection_pool.put((con, cur))
                self.connection_pool_storage.append(con)
            else:
                raise

    def _get_connection(self):
        if not self._connected:
            raise RuntimeError("Driver disconnected")
        try:
            return self.connection_pool.get(block=True, timeout=0.5)
        except Empty:
            self._create_connection()
            try:
                return self.connection_pool.get(block=True, timeout=0.5)
            except Empty as e:
                raise Exception(f'{e}\n\nEmpty connection pool, you better increase `pool_size`')#TODO Create get_schema() from table and db and column 

    def _excfp(self, query, params):
        if not self._connected:
            raise RuntimeError("Driver disconnected")
        con, cur = self._get_connection()
        try:
            cur.execute(query, params)
            res = cur.fetchall()
            con.commit()
            self.connection_pool.put((con, cur))
            return res
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.execute(query, params)
                    res = cur.fetchall()
                    con.commit()
                    self.connection_pool.put((con, cur))
                    return res
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')
        except Exception as e:   # <--- اضافه کنید
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')

    def _excf(self, query):
        if not self._connected:
            raise RuntimeError("Driver disconnected")
        con, cur = self._get_connection()
        try:
            cur.execute(query)
            res = cur.fetchall()
            con.commit()
            self.connection_pool.put((con, cur))
            return res
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.execute(query)
                    res = cur.fetchall()
                    con.commit()
                    self.connection_pool.put((con, cur))
                    return res
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                raise Exception(f'{e}\nQuery:\n\t{query}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}')
        except Exception as e:   # <--- اضافه کنید
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}')
    
    def _excp(self, query, params):
        if not self._connected:
            raise RuntimeError("Driver disconnected")
        con, cur = self._get_connection()
        try:
            cur.execute(query, params)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.execute(query, params)
                    con.commit()
                    self.connection_pool.put((con, cur))
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')
        except Exception as e:   # <--- اضافه کنید
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')
    
    def _exc(self, query):
        if not self._connected:
            raise RuntimeError("Driver disconnected")
        con, cur = self._get_connection()
        try:
            cur.execute(query)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.execute(query)
                    con.commit()
                    self.connection_pool.put((con, cur))
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                raise Exception(f'{e}\nQuery:\n\t{query}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}')
        except Exception as e:   # <--- اضافه کنید
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}')

    def _excs(self, query_params: list):
        if not self._connected:
            raise RuntimeError("Driver disconnected")
        con, cur = self._get_connection()
        try:
            for q in query_params:
                if len(q) == 2:
                    cur.execute(q[0], q[1])
                else:
                    cur.execute(q[0])
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    for q in query_params:
                        if len(q) == 2:
                            cur.execute(q[0], q[1])
                        else:
                            cur.execute(q[0])
                    con.commit()
                    self.connection_pool.put((con, cur))
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                queries_str = '\n'.join([f'Query: {q[0]}\nParams: {q[1] if len(q)>1 else ""}' for q in query_params])
                raise Exception(f'{e}\n{queries_str}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            queries_str = '\n'.join([f'Query: {q[0]}\nParams: {q[1] if len(q)>1 else ""}' for q in query_params])
            raise Exception(f'{e}\n{queries_str}')
        except Exception as e:   # <--- اضافه کنید
            con.rollback()
            self.connection_pool.put((con, cur))
            queries_str = '\n'.join([f'Query: {q[0]}\nParams: {q[1] if len(q)>1 else ""}' for q in query_params])
            raise Exception(f'{e}\n{queries_str}')

    def _excm(self, query, params):
        if not self._connected:
            raise RuntimeError("Driver disconnected")
        con, cur = self._get_connection()
        
        try:
            cur.executemany(query, params)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.sqlstate in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.executemany(query, params)
                    con.commit()
                    self.connection_pool.put((con, cur))
                except OperationalError:
                    self._handle_broken_connection(con)
                    raise
            else:
                con.rollback()
                self.connection_pool.put((con, cur))
                raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')
        except ProgrammingError as e:
            con.rollback()
            self.connection_pool.put((con, cur))
            raise Exception(f'{e}\nQuery:\n\t{query}\nParams:\n\t{params}')

    def _handle_broken_connection(self, con):
        if not self._connected:
            raise RuntimeError("Driver disconnected")
        try:
            con.close()
        except:
            pass
        if con in self.connection_pool_storage:
            self.connection_pool_storage.remove(con)
        self._create_connection()

    def delete_table(self, table: Table, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool):
        if are_you_sure and are_you_really_sure and for_sure:
            self._exc(f'DROP TABLE {table.name_};')
            self.__delattr__(table.name_.strip('"'))

    def delete_database(self, database_name: str, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool):
        if are_you_sure and are_you_really_sure and for_sure:
            con, cur = self._get_connection()
            try:
                con.rollback()
                con.autocommit = True
                cur.execute(f'DROP DATABASE "{database_name}";')
                con.autocommit = False
                self.connection_pool.put((con, cur))
            except Exception:
                try:
                    con.autocommit = False
                except:
                    pass
                self.connection_pool.put((con, cur))
                raise
            
    def custom_execute_with_fetch(self, query, params=None):
        return self._excfp(query, params) if params else self._excf(query)

    def custom_execute(self, query, params=None):
        return self._excp(query, params) if params else self._exc(query)

    def custom_execute_many(self, query, params):
        return self._excm(query, params)

    def get_databases(self):
        return [i[0] for i in self._excf('SELECT datname FROM pg_database WHERE datistemplate = false;')]

    def get_tables(self):
        return [i[0] for i in self._excf("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = current_schema();")]
    
    def create_table(self, table_structure: TableStructure):
        self._exc(table_structure.get_structure())
        self.__setattr__(table_structure.name.strip('"'), Table(self, table_structure.name.strip('"')))

    def optimize(self):
        tables = self.get_tables()
        con, cur = self._get_connection()
        try:
            con.rollback()
            con.autocommit = True
            for i in tables:
                cur.execute(f'VACUUM (ANALYZE) "{i}";')
            con.autocommit = False
            self.connection_pool.put((con, cur))
        except Exception:
            try:
                con.autocommit = False
            except:
                pass
            self.connection_pool.put((con, cur))
            raise

    def create_user(self, username: str, password: str):
        forbidden = (';', '--', '\0', "'")
        for ch in forbidden:
            if ch in username:
                raise Exception(
                    f"Invalid username: '{username}' contains forbidden character '{ch}'"
                )
        safe_username = username.replace('"', '""')
        self._exc(f'CREATE USER "{safe_username}" WITH PASSWORD \'{password}\';')

    def drop_user(self, username: str):
        query = f'DROP USER "{username.replace('"', '""')}";'
        self._exc(query)

    def change_password(self, username: str, new_password: str):
        query = f"ALTER USER \"{username.replace('\"', '\"\"')}\" WITH PASSWORD '{new_password}';"
        self._exc(query)

    def rename_user(self, old_username: str, new_username: str):
        query = f'ALTER USER "{old_username.replace('"', '""')}" RENAME TO "{new_username.replace('"', '""')}";'
        self._exc(query)

    def grant_privileges(self, username: str, privileges: PRIVILEGES, database: str, table: str = '*'):
        if table == '*':
            query = f'GRANT {privileges} ON DATABASE "{database}" TO "{username}";'
        else:
            query = f'GRANT {privileges} ON TABLE "{database}"."{table}" TO "{username}";'
        self._exc(query)

    def revoke_privileges(self, username: str, privileges: PRIVILEGES, database: str, table: str = '*'):
        if table == '*':
            query = f'REVOKE {privileges} ON DATABASE "{database}" FROM "{username}";'
        else:
            query = f'REVOKE {privileges} ON TABLE "{database}"."{table}" FROM "{username}";'
        self._exc(query)

    def disconnect(self):
        if not self._connected:
            raise RuntimeError("Already disconnected")
        self._connected = False
        for i in self.connection_pool_storage:
            try:
                i.close()
            except:
                pass
        while not self.connection_pool.empty():
            self.connection_pool.get_nowait()


#TODO Add Sum()
#TODO SELECT output most be object with attributes of column names and slice able with [:] to get rows.
