from queue import SimpleQueue, Empty
from MySQLdb import connect, OperationalError, ProgrammingError
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
                new_op._output = (f'(SUBSTRING({self.col_obj.name} , LENGTH({self.col_obj.name}) - %s , %s)', [abs(key.start) - 1, key.stop - key.start])  #
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
        new_op._output = (f"({self._output[0]} like {prefix._output[0]} || '%%)'", (self._output[1] + prefix._output[1]) if self._output else prefix._output[1]) if isinstance(prefix, ColumnsOperation) else (f"({self._output[0]} like {prefix.name} || '%%')", self._output[1]) if isinstance(prefix , Column) else (f"({self._output[0]} like %s || '%%')", self._output[1] + [f'{prefix}'])
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
        self.name= table_obj.name_+'.`'+column_name+'`'
        self.first_name= f'`{column_name}`'
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
        for col_info in self.table_obj.get_table_info():
            if col_info['name'] == column.first_name[1:-1]:
                full_type = col_info['full_type']  
                break
        query = f'ALTER TABLE {self.table_obj.name_} CHANGE COLUMN {column.first_name} `{new_name}` {full_type};'
        self.table_obj._exc(query)
        self.table_obj.__delattr__(column.first_name[1:-1])
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
        temp_list= []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        self.script.append([f'UPDATE {table.name_ if table else self.table_obj.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=%s' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1]])
        return self

    def insert(self, insert: dict[Column, Any], table: Table = None) -> 'BatchOperation':
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
        self.name_= '`'+table_name+'`'
        self.db_obj = obj
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
        for i in self.get_table_info():
            self.__setattr__(i['name'], Column(self, i['name'], i['datatype']))

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
        return [i[0] for i in self._excf(f'SHOW COLUMNS FROM {self.name_}')]
    
    def get_table_info(self):
        """
        Get complete information about table columns.
        Returns a list of dictionaries with column info similar to SQLite's PRAGMA table_info.
        """
        
        query = f"""
            SELECT 
                c.ORDINAL_POSITION AS cid,
                c.COLUMN_NAME AS name,
                c.DATA_TYPE AS type,
                CASE WHEN c.IS_NULLABLE = 'NO' THEN 1 ELSE 0 END AS notnull,
                c.COLUMN_DEFAULT AS dflt_value,
                CASE WHEN c.COLUMN_KEY = 'PRI' THEN 1 ELSE 0 END AS pk,
                c.COLUMN_TYPE AS full_type,
                c.EXTRA AS extra,
                c.CHARACTER_SET_NAME AS charset,
                c.COLLATION_NAME AS collation,
                c.NUMERIC_PRECISION AS num_precision,
                c.NUMERIC_SCALE AS num_scale,
                c.DATETIME_PRECISION AS datetime_precision,
                CASE WHEN c.EXTRA LIKE '%%auto_increment%%' THEN 1 ELSE 0 END AS auto_increment,
                kcu.REFERENCED_TABLE_NAME AS fk_table,
                kcu.REFERENCED_COLUMN_NAME AS fk_column,
                rc.UPDATE_RULE AS fk_on_update,
                rc.DELETE_RULE AS fk_on_delete
            FROM INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                ON kcu.TABLE_SCHEMA = c.TABLE_SCHEMA
                AND kcu.TABLE_NAME = c.TABLE_NAME
                AND kcu.COLUMN_NAME = c.COLUMN_NAME
                AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            LEFT JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
                AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                AND rc.TABLE_NAME = c.TABLE_NAME
            WHERE c.TABLE_SCHEMA = DATABASE()
            AND c.TABLE_NAME = %s
            ORDER BY c.ORDINAL_POSITION
        """
        return [{
            'cid': row[0],           # ORDINAL_POSITION
            'name': row[1],          # COLUMN_NAME
            'type': row[2],          # DATA_TYPE (MySQL type name)
            'datatype': int if row[2].lower().split('(')[0] in ('int', 'integer', 'tinyint', 'smallint', 'mediumint', 'bigint', 'serial', 'year', 'bit') else float if row[2].lower().split('(')[0] in ('real', 'float', 'double', 'decimal', 'numeric') else str if row[2].lower().split('(')[0] in ('char', 'varchar', 'text', 'tinytext', 'mediumtext', 'longtext', 'enum', 'set', 'json', 'date', 'time', 'datetime', 'timestamp') else bytes if row[2].lower().split('(')[0] in ('blob', 'tinyblob', 'mediumblob', 'longblob', 'binary', 'varbinary', 'geometry', 'point', 'linestring', 'polygon', 'multipoint', 'multilinestring', 'multipolygon', 'geometrycollection') else str,  # Python type (int, str, float, bytes)
            'notnull': bool(row[3]), # True/False
            'dflt_value': row[4],    # COLUMN_DEFAULT
            'pk': bool(row[5]),      # True/False
            'full_type': row[6],     # COLUMN_TYPE (مثلاً 'int(11)')
            'extra': row[7],         # EXTRA (auto_increment, etc.)
            'charset': row[8],       # CHARACTER_SET_NAME
            'collation': row[9],     # COLLATION_NAME
            'numeric_precision': row[10],  # NUMERIC_PRECISION
            'numeric_scale': row[11],      # NUMERIC_SCALE
            'datetime_precision': row[12], # DATETIME_PRECISION
            'auto_increment': bool(row[13]),  # True/False
            'fk_table': row[14],     # REFERENCED_TABLE_NAME
            'fk_column': row[15],    # REFERENCED_COLUMN_NAME
            'fk_on_update': row[16], # UPDATE_RULE
            'fk_on_delete': row[17]  # DELETE_RULE
        } for row in self._excfp(query, (self.name_[1:-1],))]

    def batch(self) -> 'BatchOperation':
        return BatchOperation(self)

    def update(self, update: dict[Column, Any], where: 'ColumnsOperation') -> None:
        temp_list = []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        self._excp(f'UPDATE {self.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=%s' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1])
        
    def get_row(self,which_columns: list['Column' | 'ColumnsOperation'],where: 'ColumnsOperation' = None,order_by: 'Column' = None):
        tl = []
        wc = []
        [wc.append(i.first_name) if isinstance(i,Column) else [wc.append(i._output[0]), tl.extend(i._output[1])] for i in which_columns]
        return [row[0] for row in (self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} WHERE {where._output[0]} {f'ORDER BY {order_by.first_name}' if order_by else ''};', tl+where._output[1]) if where else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',tl) if tl else self._excf(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',))] if len(which_columns) == 1 else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} WHERE {where._output[0]} {f'ORDER BY {order_by.first_name}' if order_by else ''};', tl+where._output[1]) if where else self._excfp(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',tl) if tl else self._excf(f'SELECT {', '.join(wc)} FROM {self.name_} {f'ORDER BY {order_by.first_name}' if order_by else ''};',)
        
    def insert(self, insert: dict['Column', Any]) -> None:
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

    def add_column(
        self,
        column_name: str,
        data_type: str,          # خروجی از DataTypes (مثلاً DataTypes.INT())
        nullable: bool = True,
        default: Any = None,
        auto_increment: bool = False,
        primary_key: bool = False,
        unique: bool = False,
        comment: str = None,
        after: Column = None,
        first: bool = False
    ) -> None:
        self._exc(f'ALTER TABLE {self.name_} ADD COLUMN {column_name} {data_type} {' NOT NULL' if not nullable else ''}{' AUTO_INCREMENT' if auto_increment else ''}{f" DEFAULT '{default}'" if default is not None and isinstance(default,str) else f' DEFAULT {default}' if default is not None else ''}{' UNIQUE' if unique else ''}{f" COMMENT '{comment}'" if comment else ''}{' FIRST' if first else f" AFTER {after.first_name[1:-1]}" if after else ''};')
        self._exc(f"ALTER TABLE {self.name_} ADD PRIMARY KEY (`{column_name}`);") if primary_key else ''
        self.__setattr__(column_name, Column(self, column_name, int if data_type.lower().split('(')[0] in ('int', 'integer', 'tinyint', 'smallint', 'mediumint', 'bigint', 'serial', 'year', 'bit') else float if data_type.lower().split('(')[0] in ('real', 'float', 'double', 'decimal', 'numeric') else str if data_type.lower().split('(')[0] in ('char', 'varchar', 'text', 'tinytext', 'mediumtext', 'longtext', 'enum', 'set', 'json', 'date', 'time', 'datetime', 'timestamp') else bytes if data_type.lower().split('(')[0] in ('blob', 'tinyblob', 'mediumblob', 'longblob', 'binary', 'varbinary', 'geometry', 'point', 'linestring', 'polygon', 'multipoint', 'multilinestring', 'multipolygon', 'geometrycollection') else str))

    def rename_table(self, new_name: str) -> None:
        self._exc(f'ALTER TABLE {self.name_} RENAME TO `{new_name}`;')
        self.db_obj.__delattr__(self.name_[1:-1])
        self.db_obj.__setattr__(new_name, Table(obj=self.db_obj, table_name=new_name))
        self.name_ = f'`{new_name}`'


    def rename_column(self, column: 'Column', new_name: str) -> None:
        for col_info in self.get_table_info():
            if col_info['name'] == column.first_name[1:-1]:
                full_type = col_info['full_type']  
                break
        query = f'ALTER TABLE {self.name_} CHANGE COLUMN {column.first_name} `{new_name}` {full_type};'
        self._exc(query)
        self.__delattr__(column.first_name[1:-1])
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
        self._exc(f'DROP INDEX {index_name} ON {self.name_};')

    def get_indexes_info(self) -> Any:
        return [{'idx_name':i[2], 'non_unique':bool(i[1]), 'seq_in_idx':i[3], 'Columns_name':i[4],'collation':i[5], 'cardinality':i[6], 'sub_part':i[7], 'packed':i[8], 'nullable':i[9], 'idx_type':i[10], 'comment':i[11]} for i in self._excf(f'SHOW INDEX FROM {self.name_}')]

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
        return self._excfp(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}'if isinstance(i,Column)else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")")else i._output[0]} AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'WHERE {where._output[0]}'if where else ''} {f'ORDER BY {order_by.name}' if order_by else ''}', tl+where._output[1]) if where else self._excfp(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column) else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")") else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'ORDER BY {order_by.name}' if order_by else ''}', tl) if tl else self._excf(f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column) else f'{i._output[0][1:-1] if i._output[0].startswith('(') and i._output[0].endswith(')') else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'ORDER BY {order_by.name}' if order_by else ''}')
        # The above line is approximately 1000 characters, which is not standard, but it is written this way
        # to improve performance in the Driver class and to avoid checking whether the second item in the query
        # is an empty list for each input.


class DataTypes:
    """
    Complete MySQL 8.0 Data Types as static methods.
    Each method returns the corresponding SQL data type string.
    """
    TEXT_SIZE = Literal['TINYTEXT', 'TEXT', 'MEDIUMTEXT', 'LONGTEXT']
    # ========================
    # Numeric Data Types
    # ========================

    @staticmethod
    def BIT(size: int) -> str:
        """
        Bit-value type. Size from 1 to 64 bits.
        Example: BIT(8)
        """
        if size:
            if size < 1 or size > 64:
                raise ValueError("Size for BIT must be between 1 and 64.")
        return f"BIT({size})"

    @staticmethod
    def TINYINT(size: int = None, unsigned: bool = False, zerofill: bool = False) -> str:
        """
        Very small integer. Range: -128 to 127 signed, 0 to 255 unsigned.
        Example: TINYINT(3) UNSIGNED
        """
        if size is not None:
            if (size < -128 or size > 127) and not unsigned or (size < 0 or size > 255) and unsigned:
                raise ValueError("Size for TINYINT must be between -128 and 127 for signed or 0 to 255 for unsigned.")
        result = "TINYINT"
        if size:
            result += f"({size})"
        if unsigned:
            result += " UNSIGNED"
        if zerofill:
            result += " ZEROFILL"
        return result

    @staticmethod
    def SMALLINT(size: int = None, unsigned: bool = False, zerofill: bool = False) -> str:
        """
        Small integer. Range: -32768 to 32767 signed, 0 to 65535 unsigned.
        """
        if size is not None:
            if (size < -32768 or size > 32767) and not unsigned or (size < 0 or size > 65535) and unsigned:
                raise ValueError("Size for SMALLINT must be between -32768 and 32767 for signed or 0 to 65535 for unsigned.")
        result = "SMALLINT"
        if size:
            result += f"({size})"
        if unsigned:
            result += " UNSIGNED"
        if zerofill:
            result += " ZEROFILL"
        return result

    @staticmethod
    def MEDIUMINT(size: int = None, unsigned: bool = False, zerofill: bool = False) -> str:
        """
        Medium integer. Range: -8388608 to 8388607 signed, 0 to 16777215 unsigned.
        """
        if size is not None:
            if (size < -8388608 or size > 8388607) and not unsigned or (size < 0 or size > 16777215) and unsigned:
                raise ValueError("Size for MEDIUMINT must be between -8388608 and 8388607 for signed or 0 to 16777215 for unsigned.")
        result = "MEDIUMINT"
        if size:
            result += f"({size})"
        if unsigned:
            result += " UNSIGNED"
        if zerofill:
            result += " ZEROFILL"
        return result

    @staticmethod
    def INT(size: int = None, unsigned: bool = False, zerofill: bool = False) -> str:
        """
        Standard integer. Range: -2147483648 to 2147483647 signed, 0 to 4294967295 unsigned.
        """
        if size is not None:
            if (size < -2147483648 or size > 2147483647) and not unsigned or (size < 0 or size > 4294967295) and unsigned:
                raise ValueError("Size for INT must be between -2147483648 and 2147483647 for signed or 0 to 4294967295 for unsigned.")
        result = "INT"
        if size:
            result += f"({size})"
        if unsigned:
            result += " UNSIGNED"
        if zerofill:
            result += " ZEROFILL"
        return result

    @staticmethod
    def BIGINT(size: int = None, unsigned: bool = False, zerofill: bool = False) -> str:
        """
        Large integer. Range: -2^63 to 2^63-1 signed, 0 to 2^64-1 unsigned.
        """
        if size is not None:
            if (size < -9223372036854775808 or size > 9223372036854775807) and not unsigned or (size < 0 or size > 18446744073709551615) and unsigned:
                raise ValueError("Size for BIGINT must be between -9223372036854775808 and 9223372036854775807 for signed or 0 to 18446744073709551615 for unsigned.")
        result = "BIGINT"
        if size:
            result += f"({size})"
        if unsigned:
            result += " UNSIGNED"
        if zerofill:
            result += " ZEROFILL"
        return result

    @staticmethod
    def DECIMAL(precision: int = 10, scale: int = 0) -> str:
        """
        Exact fixed-point number.
        Example: DECIMAL(10,2)
        """
        return f"DECIMAL({precision}, {scale})"

    @staticmethod
    def NUMERIC(precision: int = 10, scale: int = 0) -> str:
        """
        Synonym for DECIMAL.
        """
        if precision < 1 or scale < 0 or scale > precision:
            raise ValueError("Precision must be >= 1 and scale must be >= 0 and <= precision.")
        return f"NUMERIC({precision}, {scale})"

    @staticmethod
    def FLOAT(size: int = None, decimals: int = None) -> str:
        """
        Single-precision floating-point number.
        Example: FLOAT(7,4) or just FLOAT
        """
        if size is not None and decimals is not None:
            return f"FLOAT({size}, {decimals})"
        return "FLOAT"

    @staticmethod
    def DOUBLE(size: int = None, decimals: int = None) -> str:
        """
        Double-precision floating-point number.
        Example: DOUBLE(10,4) or just DOUBLE
        """
        if size is not None and decimals is not None:
            return f"DOUBLE({size}, {decimals})"
        return "DOUBLE"

    @staticmethod
    def REAL() -> str:
        """
        Synonym for DOUBLE (or FLOAT depending on SQL mode).
        """
        return "REAL"

    # ========================
    # String Data Types
    # ========================

    @staticmethod
    def CHAR(length: int = 255) -> str:
        """
        Fixed-length character string. Max 255 characters.
        Example: CHAR(50)
        """
        if length < 1 or length > 255:
            raise ValueError("Length for CHAR must be between 1 and 255.")
        return f"CHAR({length})"

    @staticmethod
    def VARCHAR(length: int = 255) -> str:
        """
        Variable-length character string. Max 65535 bytes.
        Example: VARCHAR(255)
        """
        if length < 1 or length > 65535:
            raise ValueError("Length for VARCHAR must be between 1 and 65535.")
        return f"VARCHAR({length})"

    @staticmethod
    def TINYTEXT() -> str:
        """
        Very small text. Max 255 characters.
        """
        return "TINYTEXT"

    @staticmethod
    def TEXT(size: TEXT_SIZE = None) -> str:
        """
        Standard text. Max 65535 characters.
        Use 'TINYTEXT', 'TEXT', 'MEDIUMTEXT', or 'LONGTEXT' as size.
        """
        if size:
            valid = {"TINYTEXT", "TEXT", "MEDIUMTEXT", "LONGTEXT"}
            if size.upper() in valid:
                return size.upper()
            raise ValueError(f"Invalid TEXT size. Choose from {valid}")
        return "TEXT"

    @staticmethod
    def MEDIUMTEXT() -> str:
        """
        Medium-length text. Max 16,777,215 characters.
        """
        return "MEDIUMTEXT"

    @staticmethod
    def LONGTEXT() -> str:
        """
        Very large text. Max 4,294,967,295 characters.
        """
        return "LONGTEXT"

    @staticmethod
    def BINARY(length: int = 1) -> str:
        """
        Fixed-length binary string. Max 255 bytes.
        Example: BINARY(16)
        """
        return f"BINARY({length})"

    @staticmethod
    def VARBINARY(length: int = 255) -> str:
        """
        Variable-length binary string. Max 65535 bytes.
        Example: VARBINARY(255)
        """
        return f"VARBINARY({length})"

    @staticmethod
    def TINYBLOB() -> str:
        """
        Very small binary object. Max 255 bytes.
        """
        return "TINYBLOB"

    @staticmethod
    def BLOB(size: str = None) -> str:
        """
        Standard binary object. Max 65535 bytes.
        Use 'TINYBLOB', 'BLOB', 'MEDIUMBLOB', or 'LONGBLOB'.
        """
        if size:
            valid = {"TINYBLOB", "BLOB", "MEDIUMBLOB", "LONGBLOB"}
            if size.upper() in valid:
                return size.upper()
            raise ValueError(f"Invalid BLOB size. Choose from {valid}")
        return "BLOB"

    @staticmethod
    def MEDIUMBLOB() -> str:
        """
        Medium binary object. Max 16,777,215 bytes.
        """
        return "MEDIUMBLOB"

    @staticmethod
    def LONGBLOB() -> str:
        """
        Very large binary object. Max 4,294,967,295 bytes.
        """
        return "LONGBLOB"

    @staticmethod
    def ENUM(*values: str) -> str:
        """
        Enumeration: choose one value from a predefined list.
        Example: ENUM('small', 'medium', 'large')
        """
        quoted = ", ".join(f"'{v}'" for v in values)
        return f"ENUM({quoted})"

    @staticmethod
    def SET(*values: str) -> str:
        """
        Set: can store zero or more values from a predefined list.
        Example: SET('red', 'green', 'blue')
        """
        quoted = ", ".join(f"'{v}'" for v in values)
        return f"SET({quoted})"

    # ========================
    # Date and Time Data Types
    # ========================

    @staticmethod
    def DATE() -> str:
        """
        Date value (YYYY-MM-DD).
        """
        return "DATE"

    @staticmethod
    def TIME(precision: int = None) -> str:
        """
        Time value (HH:MM:SS). Optional microsecond precision (0-6).
        Example: TIME(3)
        """
        if precision is not None:
            return f"TIME({precision})"
        return "TIME"

    @staticmethod
    def DATETIME(precision: int = None) -> str:
        """
        Date and time combination (YYYY-MM-DD HH:MM:SS). Optional microsecond precision.
        Example: DATETIME(3)
        """
        if precision is not None:
            return f"DATETIME({precision})"
        return "DATETIME"

    @staticmethod
    def TIMESTAMP(precision: int = None) -> str:
        """
        Timestamp (YYYY-MM-DD HH:MM:SS). Range 1970-01-01 to 2038-01-19.
        Optional microsecond precision.
        Example: TIMESTAMP(6)
        """
        if precision is not None:
            return f"TIMESTAMP({precision})"
        return "TIMESTAMP"

    @staticmethod
    def YEAR() -> str:
        """
        Year value (1901 to 2155, or 0000).
        """
        return "YEAR"

    # ========================
    # Spatial Data Types
    # ========================

    @staticmethod
    def GEOMETRY() -> str:
        """
        Any spatial (geometry) type.
        """
        return "GEOMETRY"

    @staticmethod
    def POINT() -> str:
        """
        Point in 2D space.
        """
        return "POINT"

    @staticmethod
    def LINESTRING() -> str:
        """
        LineString (curve with linear interpolated points).
        """
        return "LINESTRING"

    @staticmethod
    def POLYGON() -> str:
        """
        Polygon (closed shape).
        """
        return "POLYGON"

    @staticmethod
    def MULTIPOINT() -> str:
        """
        Collection of points.
        """
        return "MULTIPOINT"

    @staticmethod
    def MULTILINESTRING() -> str:
        """
        Collection of LineStrings.
        """
        return "MULTILINESTRING"

    @staticmethod
    def MULTIPOLYGON() -> str:
        """
        Collection of Polygons.
        """
        return "MULTIPOLYGON"

    @staticmethod
    def GEOMETRYCOLLECTION() -> str:
        """
        Collection of mixed geometry types.
        """
        return "GEOMETRYCOLLECTION"

    # ========================
    # JSON Data Type
    # ========================

    @staticmethod
    def JSON() -> str:
        """
        Native JSON data type (MySQL 5.7+).
        """
        return "JSON"

    # ========================
    # Special / Other
    # ========================

    @staticmethod
    def SERIAL() -> str:
        """
        Alias for BIGINT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE.
        Convenience for auto-increment primary key.
        """
        return "SERIAL"
        

class TableStructure:
    ON_ACTION= Literal['CASCADE', 'SET NULL', 'SET DEFAULT', 'RESTRICT', 'NO ACTION']
    CHARSET = Literal[
    "armscii8",
    "ascii",
    "big5",
    "binary",
    "cp1250",
    "cp1251",
    "cp1256",
    "cp1257",
    "cp850",
    "cp852",
    "cp866",
    "cp932",
    "dec8",
    "eucjpms",
    "euckr",
    "gb18030",
    "gb2312",
    "gbk",
    "geostd8",
    "greek",
    "hebrew",
    "hp8",
    "keybcs2",
    "koi8r",
    "koi8u",
    "latin1",
    "latin2",
    "latin5",
    "latin7",
    "macce",
    "macroman",
    "sjis",
    "swe7",
    "tis620",
    "ucs2",
    "ujis",
    "utf16",
    "utf16le",
    "utf32",
    "utf8mb3",
    "utf8mb4"
    ]
    COLLATE = Literal[
    "utf8mb4_0900_ai_ci",
    "utf8mb4_0900_as_cs",
    "utf8mb4_0900_bin",
    "utf8mb4_general_ci",
    "utf8mb4_unicode_ci",
    "utf8mb4_unicode_520_ci",
    "utf8mb4_bin",
    "utf8mb4_persian_ci",
    "utf8mb4_ar_0900_ai_ci",
    "utf8mb4_da_0900_ai_ci",
    "utf8mb4_de_pb_0900_ai_ci",
    "utf8mb4_en_0900_ai_ci",
    "utf8mb4_es_0900_ai_ci",
    "utf8mb4_es_trad_0900_ai_ci",
    "utf8mb4_fr_0900_ai_ci",
    "utf8mb4_it_0900_ai_ci",
    "utf8mb4_nl_0900_ai_ci",
    "utf8mb4_pt_0900_ai_ci",
    "utf8mb4_cs_0900_ai_ci",
    "utf8mb4_hr_0900_ai_ci",
    "utf8mb4_hu_0900_ai_ci",
    "utf8mb4_pl_0900_ai_ci",
    "utf8mb4_ro_0900_ai_ci",
    "utf8mb4_sk_0900_ai_ci",
    "utf8mb4_sl_0900_ai_ci",
    "utf8mb4_sv_0900_ai_ci",
    "utf8mb4_nb_0900_ai_ci",
    "utf8mb4_nn_0900_ai_ci",
    "utf8mb4_is_0900_ai_ci",
    "utf8mb4_lt_0900_ai_ci",
    "utf8mb4_lv_0900_ai_ci",
    "utf8mb4_et_0900_ai_ci",
    "utf8mb4_bg_0900_ai_ci",
    "utf8mb4_sr_latn_0900_ai_ci",
    "utf8mb4_bs_0900_ai_ci",
    "utf8mb4_mk_0900_ai_ci",
    "utf8mb4_ja_0900_as_cs",
    "utf8mb4_ko_0900_as_cs",
    "utf8mb4_zh_0900_as_cs",
    "utf8mb4_tr_0900_ai_ci",
    "utf8mb4_vi_0900_ai_ci",
    "utf8mb4_0900_as_cs",
    "utf8mb4_da_0900_as_cs",
    "utf8mb4_es_0900_as_cs",
    "utf8mb4_fr_0900_as_cs",
    "utf8mb4_it_0900_as_cs",
    "utf8mb4_ja_0900_as_cs",
    "utf8mb4_ko_0900_as_cs",
    "utf8mb4_zh_0900_as_cs",
    "utf8mb4_croatian_ci",
    "utf8mb4_czech_ci",
    "utf8mb4_danish_ci",
    "utf8mb4_esperanto_ci",
    "utf8mb4_estonian_ci",
    "utf8mb4_german2_ci",
    "utf8mb4_hungarian_ci",
    "utf8mb4_icelandic_ci",
    "utf8mb4_latvian_ci",
    "utf8mb4_lithuanian_ci",
    "utf8mb4_polish_ci",
    "utf8mb4_romanian_ci",
    "utf8mb4_slovak_ci",
    "utf8mb4_slovenian_ci",
    "utf8mb4_swedish_ci",
    "utf8mb4_turkish_ci"
    ]
    def __init__(self, table_name: str, charset: CHARSET = "utf8mb4", collate: COLLATE = "utf8mb4_bin" ):
        self.table_query= ''
        self.primary_keys= []
        self.items= {}
        self.name= f'`{table_name}`'
        self.foreigns= []
        self.charset = charset
        self.collate = collate

    def _validate_column(
        self,
        column_name,
        datatype,
        default_value,
        unique,
        not_null,
        primary_key,
        auto_increment
    ):
        if not isinstance(datatype, str):
            raise TypeError("datatype must be a string returned by DataTypes.")

        if primary_key:
            if not not_null:
                raise Exception("PRIMARY KEY columns must also be NOT NULL.")
            if unique:
                raise Exception("PRIMARY KEY columns cannot be UNIQUE, as they are inherently unique.")
                
        if column_name in self.items:
            raise Exception(f"Column {column_name} already exists.")
                
        if isinstance(default_value, bytes):
            raise Exception("Bytes objects cannot be used as default values.")
                
        for values in self.items.values():
            if values[5] and auto_increment:
                raise Exception("Only one AUTO_INCREMENT column is allowed.")

        numeric = (
            "BIT",
            "TINYINT",
            "SMALLINT",
            "MEDIUMINT",
            "INT",
            "BIGINT",
            "DECIMAL",
            "NUMERIC",
            "FLOAT",
            "DOUBLE",
            "REAL",
            "SERIAL"
        )

        if auto_increment:
            if datatype.split("(")[0].split()[0] not in numeric:
                raise Exception("AUTO_INCREMENT is only allowed on numeric columns.")
            if not (primary_key or unique):
                raise Exception("AUTO_INCREMENT column must be PRIMARY KEY or UNIQUE.")
            if default_value is not None:
                raise Exception("AUTO_INCREMENT columns cannot have DEFAULT values.")
            
        if 'TEXT' in datatype or 'BLOB' in datatype:
            if default_value is not None:
                raise Exception("TEXT and BLOB columns cannot have default values.")

        if 'SERIAL' in datatype:
            if not primary_key or not auto_increment or not not_null:
                raise Exception("SERIAL implies PRIMARY KEY, AUTO_INCREMENT, and NOT NULL.")
            
    def add_column(self, column_name: str, datatype: DataTypes,
                default_value=None, unique: bool = None,
                not_null: bool = None,
                primary_key: bool = None,
                auto_increment: bool = False):
        column_name = f'`{column_name.strip()}`'
        primary_key, not_null, auto_increment = (True, True, True) if datatype == 'SERIAL' else (primary_key, not_null, auto_increment)
        self._validate_column(
        column_name,
        datatype,
        default_value,
        unique,
        not_null,
        primary_key,
        auto_increment
        )

        for item in self.table_query.split(','):
            if item and (column_name in item) and item.split(' ')[1] == column_name:
                raise Exception('You have added this column befor\nif you wanna modify this column , delete this column and then add a new one with desired options')
        if type(default_value) == bytes:
            raise Exception('Cant set bytes object as default value')
        self.primary_keys.append(column_name) if primary_key else None
        self.items[column_name] = [datatype, default_value, unique, not_null, primary_key, auto_increment]
        self.table_query = self.table_query + f' {column_name.strip()} {datatype}{' AUTO_INCREMENT' if auto_increment else ''}{' UNIQUE' if unique else ''}{' NOT NULL' if not_null else ''}{f' DEFAULT {f"'{default_value}'" if type(default_value) == str else default_value}' if default_value else ''},'
        return self

    def delete_column(self, column_name: str):
        column_name = f'`{column_name.strip()}`'
        query_list = self.table_query.split(',')
        self.items.pop(column_name)
        for item in query_list:
            if item.strip().startswith(column_name):
                query_list.remove(item)
                self.table_query = ','.join(query_list)
                return self
        raise Exception(f'No column found with name ({column_name})')

    def get_columns(self):
        items_list = []
        for item in self.items:
            items_dict = {}
            values = self.items[item]
            items_dict['name']= item
            items_dict['datatype']= values[0]
            items_dict['default_value']= values[1]
            items_dict['unique']= True if values[2] else False
            items_dict['not_null']= True if values[3] else False
            items_dict['primari_key']= True if values[4] else False
            items_list.append(items_dict)
        return items_list

    def foreign_key(self, column: str, refrences_table: 'Table',
                    refrences_column: 'Column', on_delete: ON_ACTION = None,
                    on_update: ON_ACTION = None
                    ):
        self.foreigns.append(f'FOREIGN KEY ({column}) REFERENCES {refrences_table.name_} ({refrences_column.first_name}){f' ON DELETE {on_delete}' if on_delete else ''}{f' ON UPDATE {on_update}' if on_update else ''}')
        return self

    def get_structure(self):
        if self.get_columns():
            return f'CREATE TABLE {self.name} ({self.table_query[:-1]}{f', PRIMARY KEY({', '.join(self.primary_keys)})' if self.primary_keys else ''}{f', {','.join(self.foreigns)}' if self.foreigns else ''})  ENGINE=InnoDB DEFAULT CHARSET={self.charset} COLLATE={self.collate};' 
        else :
            raise Exception('You must add at least one column to create a table')


class Driver():
    PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
    CHARSET = Literal[
    "armscii8",
    "ascii",
    "big5",
    "binary",
    "cp1250",
    "cp1251",
    "cp1256",
    "cp1257",
    "cp850",
    "cp852",
    "cp866",
    "cp932",
    "dec8",
    "eucjpms",
    "euckr",
    "gb18030",
    "gb2312",
    "gbk",
    "geostd8",
    "greek",
    "hebrew",
    "hp8",
    "keybcs2",
    "koi8r",
    "koi8u",
    "latin1",
    "latin2",
    "latin5",
    "latin7",
    "macce",
    "macroman",
    "sjis",
    "swe7",
    "tis620",
    "ucs2",
    "ujis",
    "utf16",
    "utf16le",
    "utf32",
    "utf8mb3",
    "utf8mb4"
    ]
    COLLATE = Literal[
    "utf8mb4_0900_ai_ci",
    "utf8mb4_0900_as_cs",
    "utf8mb4_0900_bin",
    "utf8mb4_general_ci",
    "utf8mb4_unicode_ci",
    "utf8mb4_unicode_520_ci",
    "utf8mb4_bin",
    "utf8mb4_persian_ci",
    "utf8mb4_ar_0900_ai_ci",
    "utf8mb4_da_0900_ai_ci",
    "utf8mb4_de_pb_0900_ai_ci",
    "utf8mb4_en_0900_ai_ci",
    "utf8mb4_es_0900_ai_ci",
    "utf8mb4_es_trad_0900_ai_ci",
    "utf8mb4_fr_0900_ai_ci",
    "utf8mb4_it_0900_ai_ci",
    "utf8mb4_nl_0900_ai_ci",
    "utf8mb4_pt_0900_ai_ci",
    "utf8mb4_cs_0900_ai_ci",
    "utf8mb4_hr_0900_ai_ci",
    "utf8mb4_hu_0900_ai_ci",
    "utf8mb4_pl_0900_ai_ci",
    "utf8mb4_ro_0900_ai_ci",
    "utf8mb4_sk_0900_ai_ci",
    "utf8mb4_sl_0900_ai_ci",
    "utf8mb4_sv_0900_ai_ci",
    "utf8mb4_nb_0900_ai_ci",
    "utf8mb4_nn_0900_ai_ci",
    "utf8mb4_is_0900_ai_ci",
    "utf8mb4_lt_0900_ai_ci",
    "utf8mb4_lv_0900_ai_ci",
    "utf8mb4_et_0900_ai_ci",
    "utf8mb4_bg_0900_ai_ci",
    "utf8mb4_sr_latn_0900_ai_ci",
    "utf8mb4_bs_0900_ai_ci",
    "utf8mb4_mk_0900_ai_ci",
    "utf8mb4_ja_0900_as_cs",
    "utf8mb4_ko_0900_as_cs",
    "utf8mb4_zh_0900_as_cs",
    "utf8mb4_tr_0900_ai_ci",
    "utf8mb4_vi_0900_ai_ci",
    "utf8mb4_0900_as_cs",
    "utf8mb4_da_0900_as_cs",
    "utf8mb4_es_0900_as_cs",
    "utf8mb4_fr_0900_as_cs",
    "utf8mb4_it_0900_as_cs",
    "utf8mb4_ja_0900_as_cs",
    "utf8mb4_ko_0900_as_cs",
    "utf8mb4_zh_0900_as_cs",
    "utf8mb4_croatian_ci",
    "utf8mb4_czech_ci",
    "utf8mb4_danish_ci",
    "utf8mb4_esperanto_ci",
    "utf8mb4_estonian_ci",
    "utf8mb4_german2_ci",
    "utf8mb4_hungarian_ci",
    "utf8mb4_icelandic_ci",
    "utf8mb4_latvian_ci",
    "utf8mb4_lithuanian_ci",
    "utf8mb4_polish_ci",
    "utf8mb4_romanian_ci",
    "utf8mb4_slovak_ci",
    "utf8mb4_slovenian_ci",
    "utf8mb4_swedish_ci",
    "utf8mb4_turkish_ci"
    ]
    ISOLATION_LEVEL = Literal['READ UNCOMMITTED', 'READ COMMITTED', 'REPEATABLE READ', 'SERIALIZABLE']
    INNODB_FLUSH_LOG = Literal[0,1,2]
    PRIVILEGES = Literal['ALL PRIVILEGES', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'INDEX', 'REFERENCES', 'EXECUTE', 'GRANT OPTION', 'TRIGGER']
    def __init__(self, host: str, port: int, username: str, password: str, db_name: str, create_new_db: bool = False, pool_size: int = 5, connect_timeout: int = 10, charset: CHARSET = "utf8mb4", collate: COLLATE = "utf8mb4_bin", sql_modes: list = None, isolation_level: ISOLATION_LEVEL = 'REPEATABLE READ'):
        self.CONNECTION_ERRORS = (2002, 2003, 2005, 2006, 2012, 2013, 2026, 2049, 2055, 2000)
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_%s_'
        self.host = host
        self.port = port
        self._connected = True
        self.username = username
        self.password = password
        self.db_name = db_name
        self.charset = charset
        self.collate = collate
        self.connect_timeout = connect_timeout
        self.sql_modes = [] if sql_modes is None else sql_modes
        self.config = {
            "host":self.host,
            "port":self.port,
            "user":self.username,
            "password":self.password,
            "db":self.db_name,
            "charset":self.charset,
            "connect_timeout":self.connect_timeout,
            "init_command": f'SET SESSION TRANSACTION ISOLATION LEVEL {isolation_level};'
        }
        self.connection_pool = SimpleQueue()
        self.connection_pool_storage = []
        
        #To make sure inputs are valid
        conf = {
        "host":self.host,
        "port":self.port,
        "user":self.username,
        "password":self.password,
        "charset":self.charset,
        "connect_timeout":self.connect_timeout
        }
        connection = connect(**conf)
        if not create_new_db:
            try:
                connection.select_db(self.db_name)
                connection.close()
            except Exception:
                connection.close()
                raise
        else:
            try:
                cur = connection.cursor()
                query = f"CREATE DATABASE {self.db_name} CHARACTER SET {self.charset} COLLATE {self.collate};"
                cur.execute(query)
                connection.close()
            except Exception:
                connection.close()
                print(query)
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
            self.connection_pool.put((con, cur))
            self.connection_pool_storage.append(con)
            cur.execute("SET SESSION sql_mode = 'PIPES_AS_CONCAT';")
            for i in self.sql_modes:
                cur.execute(f"SET SESSION sql_mode = CONCAT(@@sql_mode, ',{i}');")
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:  
                con = connect(**self.config)
                cur = con.cursor()
                self.connection_pool.put((con, cur))
                self.connection_pool_storage.append(con)
                cur.execute("SET SESSION sql_mode = 'PIPES_AS_CONCAT';")
                for i in self.sql_modes:
                    cur.execute(f"SET SESSION sql_mode = CONCAT(@@sql_mode, ',{i}');")
            else:
                raise

    def _get_connection(self):
        try:
            return self.connection_pool.get(block=True, timeout=0.5)
        except Empty:
            self._create_connection()
            try:
                return self.connection_pool.get(block=True, timeout=0.5)
            except Empty as e:
                raise Exception(f'{e}\n\nEmpty connection pool, you better increase `pool_size`')

    def _excfp(self, query, params):
        """to fetch queries"""
        con, cur = self._get_connection()
        try:
            cur.execute(query, params)
            res = cur.fetchall()
            con.commit()
            self.connection_pool.put((con, cur))
            return res
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:
                self._handle_broken_connection(con)
                con, cur = self._get_connection()
                try:
                    cur.execute(query, params)
                    res = cur.fetchall()
                    con.commit()
                    self.connection_pool.put((con, cur))
                    return res
                except OperationalError as e2:
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

    def _excf(self, query):
        """to fetch queries"""
        con, cur = self._get_connection()
        try:
            cur.execute(query)
            res = cur.fetchall()
            con.commit()
            self.connection_pool.put((con, cur))
            return res
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:
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

    def _excp(self, query, params):
        """to execute with parameters"""
        con, cur = self._get_connection()
        try:
            cur.execute(query, params)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:
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

    def _exc(self, query):
        """to execute without parameters"""
        con, cur = self._get_connection()
        try:
            cur.execute(query)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:
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

    def _excs(self, query_params: list):
        """to execute script with parameters"""
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
            if e.args[0] in self.CONNECTION_ERRORS:
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

    def _excm(self, query, params):
        """to execute many with parameters"""
        con, cur = self._get_connection()
        try:
            cur.executemany(query, params)
            con.commit()
            self.connection_pool.put((con, cur))
        except OperationalError as e:
            if e.args[0] in self.CONNECTION_ERRORS:
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
        try:
            con.close()
        except:
            pass
        # حذف از storage اگر وجود دارد
        if con in self.connection_pool_storage:
            self.connection_pool_storage.remove(con)
        # ایجاد اتصال جدید برای جایگزینی
        self._create_connection()
    def delete_table(self, table: Table, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool):
        if are_you_sure and are_you_really_sure and for_sure:
            self._exc(f'DROP TABLE {table.name_};')
            self.__delattr__(table.name_[1:-1])

    def delete_database(self, database_name: str, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool):
        if are_you_sure and are_you_really_sure and for_sure:
            self._exc(f'DROP DATABASE {database_name};')

    def custom_execute_with_fetch(self, query, params = None):
        return self._excfp(query, params) if params else self._excf(query)
    
    def custom_execute(self, query, params = None):
        return self._excp(query, params) if params else self._exc(query)
    
    def custom_execute_many(self, query, params):
        return self._excm(query, params)
    
    def get_databases(self):
        return [i[0] for i in self._excf('SHOW DATABASES;')]
    
    def get_tables(self):
        return [i[0] for i in self._excf('SHOW TABLES;')]
    
    def create_table(self, table_structure: TableStructure):
        self._exc(table_structure.get_structure())
        self.__setattr__(table_structure.name.strip('`'), Table(self, table_structure.name.strip('`')))

    def optimize(self):
        for i in self.get_tables():
            self._exc(f"OPTIMIZE TABLE {i};")
            self._exc(f"ANALYZE TABLE {i}")

    def create_user(self, username: str, password: str, host: str = 'localhost'):
        query = f"CREATE USER '{username.replace("'", "''")}'@'{host.replace("'", "''")}' IDENTIFIED BY %s;"
        self._excp(query, (password,))

    def drop_user(self, username: str, host: str = 'localhost'):
        query = f"DROP USER '{username.replace("'", "''")}'@'{host.replace("'", "''")}';"
        self._exc(query)

    def change_password(self, username: str, new_password: str, host: str = 'localhost'):
        query = f"ALTER USER '{username.replace("'", "''")}'@'{host.replace("'", "''")}' IDENTIFIED BY %s;"
        self._excp(query, (new_password,))

    def rename_user(self, old_username: str, old_host: str, new_username: str, new_host: str):
        query = f"RENAME USER '{old_username.replace("'", "''")}'@'{old_host.replace("'", "''")}' TO '{new_username.replace("'", "''")}'@'{new_host.replace("'", "''")}';"
        self._exc(query)

    def grant_privileges(self, username: str, host: str, privileges: PRIVILEGES, database: str, table: str = '*'):
        query = f"GRANT {privileges} ON {database.replace("'", "''")}.{table.replace("'", "''")} TO '{username.replace("'", "''")}'@'{host.replace("'", "''")}';"
        self._exc(query)

    def revoke_privileges(self, username: str, host: str, privileges: PRIVILEGES, database: str, table: str = '*'):
        query = f"REVOKE {privileges} ON {database.replace("'", "''")}.{table.replace("'", "''")} FROM '{username.replace("'", "''")}'@'{host.replace("'", "''")}';"
        self._exc(query)

    def flush_privileges(self):
        self._exc("FLUSH PRIVILEGES;")

    def disconnect(self):
        self._connected = False
        for i in self.connection_pool_storage:
            try:
                i.close()
            except:
                pass
        while not self.connection_pool.empty():
            self.connection_pool.get_nowait()


#TODO Create get_schema() from table and db and column 
#TODO Add Sum() 
#TODO Update
#TODO SELECT output most be object with attributes of column names and slice able with [:] to get rows.