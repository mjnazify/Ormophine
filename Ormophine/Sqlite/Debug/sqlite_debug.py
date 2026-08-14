from queue import SimpleQueue
from sqlite3 import connect
from threading import Event,Thread
from time import sleep
from traceback import print_exc
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
        new_op._output = (f'({self._output[0]} {'||' if (self.current_datatype == str) or (other.current_datatype == str) else '+'} {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} {'||' if (self.current_datatype == str) or (other.datatype == str) else '+'} {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} {'||' if (self.current_datatype == str) else '+'} ?)', self._output[1]+[other]) if isinstance(other, int) or isinstance(other , float) else (f'({self._output[0]} || ?)', self._output[1]+[other if isinstance(other, str) else str(other)])
        new_op.current_datatype = str if (isinstance(other, ColumnsOperation) and other.current_datatype == str) or (isinstance(other, Column) and other.datatype == str) or self.current_datatype == str or ( not isinstance(other, ColumnsOperation) and not isinstance(other,Column) and not isinstance(other, int) and not isinstance(other, float)) else self.current_datatype
        return new_op

    def __radd__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} {'||' if (self.current_datatype == str) or (other.current_datatype == str) else '+'} {self._output[0]})', other._output[1]+self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} {'||' if (self.current_datatype == str) or (other.datatype == str) else '+'} {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? {'||' if (self.current_datatype == str) else '+'} {self._output[0]})', [other]+self._output[1]) if isinstance(other, int) or isinstance(other , float) else (f'(? || {self._output[0]})', [other if isinstance(other, str) else str(other)]+self._output[1])
        new_op.current_datatype = str if (isinstance(other, ColumnsOperation) and other.current_datatype == str) or (isinstance(other, Column) and other.datatype == str) or self.current_datatype == str or ( not isinstance(other, ColumnsOperation) and not isinstance(other,Column) and not isinstance(other, int) and not isinstance(other, float)) else self.current_datatype
        return new_op

    def __sub__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} - {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} - {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} - ?)', self._output[1]+[other])
        return new_op

    def __rsub__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} - {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} - {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? - {self._output[0]})', [other]+self._output[1])
        return new_op

    def __mul__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} * {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} * {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} * ?)', self._output[1]+[other])
        return new_op

    def __rmul__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} * {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} * {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? * {self._output[0]})', [other]+self._output[1])
        return new_op

    def __pow__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} ** {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} ** {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} ** ?)', self._output[1]+[other])
        return new_op

    def __rpow__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} ** {self._output[0]})', other._output[1]+self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} ** {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? ** {self._output[0]})', [other]+self._output[1])
        return new_op

    def __truediv__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} / {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} / {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} / ?)', self._output[1]+[other])
        return new_op

    def __rtruediv__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} / {self._output[0]})', other._output[1] + self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} / {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? / {self._output[0]})', [other]+self._output[1])
        return new_op

    def __mod__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} % {other._output[0]})', self._output[1] + other._output[1]) if isinstance(other, ColumnsOperation) else (f'({self._output[0]} % {other.name})', self._output[1]) if isinstance(other, Column) else (f'({self._output[0]} % ?)', self._output[1]+[other])
        return new_op

    def __rmod__(self, other):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({other._output[0]} % {self._output[0]})', other._output[1]+self._output[1]) if isinstance(other, ColumnsOperation) else (f'({other.name} % {self._output[0]})', self._output[1]) if isinstance(other, Column) else (f'(? % {self._output[0]})', [other]+self._output[1])
        return new_op

    def __getitem__(self, key: slice):
        new_op = ColumnsOperation(self.col_obj)
        new_op.current_datatype = str
        if self._output:
            if key.start == None and key.stop ==  None:
                new_op._output = (f'(substr({self._output[0]} , 0 , length({self._output[0]}) + 1))', self._output[1] + self._output[1])   #
            elif key.start == None and key.stop < 0:
                new_op._output = (f'(substr({self._output[0]} , 0 , length({self._output[0]}) - ?))', self._output[1] + self._output[1] + [abs(key.stop) - 1])  #
            elif key.start == None and key.stop >= 0:
                new_op._output = (f'(substr({self._output[0]} , 0 , ?))', self._output[1] + [key.stop + 1])  #  
            elif key.start >= 0 and key.stop ==  None:
                new_op._output = (f'(substr({self._output[0]} , ? , length({self._output[0]})))', self._output[1] + [key.start + 1] + self._output[1])  #   
            elif key.start < 0 and key.stop == None:
                new_op._output = (f'(substr({self._output[0]} , length({self._output[0]}) - ? , length({self._output[0]})))', self._output[1] + self._output[1] + [abs(key.start) - 1] + self._output[1])  #
            elif key.start >= 0 and key.stop < 0:
                new_op._output = (f'(substr({self._output[0]} , ? , length({self._output[0]}) - ?))', self._output[1] +  [key.start + 1] + self._output[1] + [abs(key.stop - key.start)])  #  
            elif key.start >= 0 and key.stop > 0:
                new_op._output = (f'(substr({self._output[0]} , ? , ?))', self._output[1] + [key.start + 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop < 0:
                new_op._output = (f'(substr({self._output[0]} , length({self._output[0]}) - ? , ?))', self._output[1] + self._output[1] + [abs(key.start) - 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop > 0:
                new_op._output = (f'(substr({self._output[0]} , length({self._output[0]}) - ? ,  ? - (length({self._output[0]}) - ?)))', self._output[1] + self._output[1] + [abs(key.start) - 1, key.stop] + self._output[1] + [abs(key.start)])
        else:
            if key.start == None and key.stop ==  None:
                new_op._output = (f'(substr({self.col_obj.name} , 0 , length({self.col_obj.name}) + 1))', [])   #
            elif key.start == None and key.stop < 0:
                new_op._output = (f'(substr({self.col_obj.name} , 0 , length({self.col_obj.name}) - ?))', [abs(key.stop) - 1])  #
            elif key.start == None and key.stop >= 0:
                new_op._output = (f'(substr({self.col_obj.name} , 0 , ?))', [key.stop + 1])  #  
            elif key.start >= 0 and key.stop ==  None:
                new_op._output = (f'(substr({self.col_obj.name} , ? , length({self.col_obj.name})))', [key.start + 1])  #   
            elif key.start < 0 and key.stop == None:
                new_op._output = (f'(substr({self.col_obj.name} , length({self.col_obj.name}) - ? , length({self.col_obj.name})))', [abs(key.start) - 1])  #
            elif key.start >= 0 and key.stop < 0:
                new_op._output = (f'(substr({self.col_obj.name} , ? , length({self.col_obj.name}) - ?))', [key.start + 1, abs(key.stop - key.start)])  #  
            elif key.start >= 0 and key.stop > 0:
                new_op._output = (f'(substr({self.col_obj.name} , ? , ?))', [key.start + 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop < 0:
                new_op._output = (f'(substr({self.col_obj.name} , length({self.col_obj.name}) - ? , ?))', [abs(key.start) - 1, key.stop - key.start])  #
            elif key.start < 0 and key.stop > 0:
                new_op._output = (f'(substr({self.col_obj.name} , length({self.col_obj.name}) - ? ,  ? - (length({self.col_obj.name}) - ?)))', [abs(key.start) - 1, key.stop, abs(key.start)])
        return new_op

    def eq(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} = {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} = {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} = ?)', self._output[1] + [value])
        return new_op

    def __eq__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} = {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} = {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} = ?)', self._output[1] + [value])
        return new_op

    def ne(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} != {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} != {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} != ?)', self._output[1] + [value])
        return new_op

    def __ne__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} != {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} != {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} != ?)', self._output[1] + [value])
        return new_op

    def gt(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} > {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} > {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} > ?)', self._output[1] + [value])
        return new_op

    def __gt__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} > {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} > {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} > ?)', self._output[1] + [value])
        return new_op

    def lt(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} < {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} < {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} < ?)', self._output[1] + [value])
        return new_op

    def __lt__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} < {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} < {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} < ?)', self._output[1] + [value])
        return new_op

    def ge(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} >= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} >= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} >= ?)', self._output[1] + [value])
        return new_op

    def __ge__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} >= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} >= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} >= ?)', self._output[1] + [value])
        return new_op

    def le(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} <= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} <= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} <= ?)', self._output[1] + [value])
        return new_op

    def __le__(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} <= {value._output[0]})', self._output[1] + value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} <= {value.name})', self._output[1] if isinstance(self._output[1], list) else [self._output[1]]) if isinstance(value, Column) else (f'({self._output[0]} <= ?)', self._output[1] + [value])
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
        new_op._output = (f"({self._output[0]} like {value._output[0]})", (self._output[1] + value._output[1]) if self._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self._output[0]} like {value.name})', self._output[1]) if isinstance(value , Column) else (f'({self._output[0]} like ?)', self._output[1] + [f'{value}'])
        return new_op

    def startswith(self, prefix):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"({self._output[0]} like {prefix._output[0]} || '%')", (self._output[1] + prefix._output[1]) if self._output else prefix._output[1]) if isinstance(prefix, ColumnsOperation) else (f"({self._output[0]} like {prefix.name} || '%')", self._output[1]) if isinstance(prefix , Column) else (f"({self._output[0]} like ? || '%')", self._output[1] + [f'{prefix}'])
        return new_op

    def endswith(self, suffix):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"({self._output[0]} like '%' || {suffix._output[0]})", (self._output[1] + suffix._output[1]) if self._output else suffix._output[1]) if isinstance(suffix, ColumnsOperation) else (f"({self._output[0]} like '%' || {suffix.name})", self._output[1]) if isinstance(suffix , Column) else (f"({self._output[0]} like '%' || ?)", self._output[1] + [f'{suffix}'])
        return new_op

    def contains(self, value):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f"({self._output[0]} like '%' || {value._output[0]} || '%')", (self._output[1] + value._output[1]) if self._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self._output[0]} like '%' || {value.name} || '%')", self._output[1]) if isinstance(value , Column) else (f"({self._output[0]} like '%' || ? || '%')", self._output[1] + [f'{value}'])
        return new_op

    def add_end(self, content):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} || {content._output[0]})', self._output[1]+content._output[1] if self._output else content._output[1]) if isinstance(content, ColumnsOperation) else (f'({self._output[0]} || {content.name})', self._output[1] if self._output else []) if isinstance(content, Column) else (f'({self._output[0]} || ?)', self._output[1]+[content] if self._output else [content])
        new_op.current_datatype = str
        return new_op

    def add_first(self, content):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({content._output[0]} || {self._output[0]})', content._output[1]+self._output[1] if self._output else content._output[1]) if isinstance(content, ColumnsOperation) else (f'({content.name} || {self._output[0]})', self._output[1] if self._output else []) if isinstance(content, Column) else (f'(? || {self._output[0]})', [content]+self._output[1] if self._output else [content])
        new_op.current_datatype = str
        return new_op

    def replace(self, old: str, new: str):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(replace({self._output[0]} , ? , ?))', self._output[1] + [old, new]) if self._output else (f'(replace({self.col_obj.name} , ? , ?))', [old, new])
        new_op.current_datatype = str
        return new_op

    def upper(self):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(upper({self._output[0]}))', self._output[1]) if self._output else (f'(upper({self.col_obj.name}))', [])
        new_op.current_datatype = str
        return new_op

    def lower(self):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(lower({self._output[0]}))', self._output[1]) if self._output else (f'(lower({self.col_obj.name}))', [])
        new_op.current_datatype = str
        return new_op

    def strip(self, chars: str = ' '):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(trim({self._output[0]},"{chars}"))', self._output[1]) if self._output else (f'(trim({self.col_obj.name},"{chars}"))', [])
        new_op.current_datatype = str
        return new_op

    def lstrip(self, chars: str = ' '):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(ltrim({self._output[0]},"{chars}"))', self._output[1]) if self._output else (f'(ltrim({self.col_obj.name},"{chars}"))', [])
        new_op.current_datatype = str
        return new_op

    def rstrip(self, chars: str = ' '):
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'(rtrim({self._output[0]},"{chars}"))', self._output[1]) if self._output else (f'(rtrim({self.col_obj.name},"{chars}"))', [])
        new_op.current_datatype = str
        return new_op

    def In(self, column: Column|ColumnsOperation = None, where: ColumnsOperation = None, data_list: list = None):
        if isinstance(column, list):
            data_list, column = column, None #So user can simply In(['Alice', 'Bob']) with out passing arguments
        if not column and not data_list:
            raise Exception("In() requires either data_list or column")
        new_op = ColumnsOperation(self.col_obj)
        new_op._output = (f'({self._output[0]} IN ({", ".join(["?" for _ in data_list])}))', self._output[1] + data_list) if data_list is not None else (f'({self._output[0]} IN (SELECT {column.name if isinstance(column, Column) else column._output[0]} FROM {(column.name if isinstance(column, Column) else column.col_obj.name).split('.')[0]}{f' WHERE {where._output[0]}' if isinstance(where, ColumnsOperation) else f' WHERE {where.name}' if isinstance(where, Column) else ''}))', self._output[1] + ([] if isinstance(column, Column) else column._output[1]) + (where._output[1] if isinstance(where, ColumnsOperation) else [])) if isinstance(column, (Column, ColumnsOperation)) else None
        return new_op

    
class Column:
    def __init__(self, table_obj: Table, column_name: str, datatype: type):
        self.name= table_obj.name_+'.['+column_name+']'
        self.first_name= f'[{column_name}]'
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
        temp_ob._output = (f'({self.name} = {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} = {value.name})', []) if isinstance(value, Column) else (f'({self.name} = ?)', [value])
        return temp_ob

    def __eq__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} = {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} = {value.name})', []) if isinstance(value, Column) else (f'({self.name} = ?)', [value])
        return temp_ob

    def ne(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} != {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} != {value.name})', []) if isinstance(value, Column) else (f'({self.name} != ?)', [value])
        return temp_ob

    def __ne__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} != {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} != {value.name})', []) if isinstance(value, Column) else (f'({self.name} != ?)', [value])
        return temp_ob

    def gt(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} > {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} > {value.name})', []) if isinstance(value, Column) else (f'({self.name} > ?)', [value])
        return temp_ob

    def __gt__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} > {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} > {value.name})', []) if isinstance(value, Column) else (f'({self.name} > ?)', [value])
        return temp_ob

    def lt(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} < {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} < {value.name})', []) if isinstance(value, Column) else (f'({self.name} < ?)', [value])
        return temp_ob

    def __lt__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} < {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} < {value.name})', []) if isinstance(value, Column) else (f'({self.name} < ?)', [value])
        return temp_ob

    def ge(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} >= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} >= {value.name})', []) if isinstance(value, Column) else (f'({self.name} >= ?)', [value])
        return temp_ob

    def __ge__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} >= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} >= {value.name})', []) if isinstance(value, Column) else (f'({self.name} >= ?)', [value])
        return temp_ob

    def le(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} <= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} <= {value.name})', []) if isinstance(value, Column) else (f'({self.name} <= ?)', [value])
        return temp_ob

    def __le__(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} <= {value._output[0]})', value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} <= {value.name})', []) if isinstance(value, Column) else (f'({self.name} <= ?)', [value])
        return temp_ob

    def __getitem__(self, key: slice):
        temp_ob = ColumnsOperation(self)
        if key.start == None and key.stop ==  None:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , 0 , length({temp_ob.col_obj.name}) + 1))', [])   #
        elif key.start == None and key.stop < 0:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , 0 , length({temp_ob.col_obj.name}) - ?))', [abs(key.stop) - 1])  #
        elif key.start == None and key.stop >= 0:
             temp_ob._output = (f'(substr({temp_ob.col_obj.name} , 0 , ?))', [key.stop + 1])  #  
        elif key.start >= 0 and key.stop ==  None:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , ? , length({temp_ob.col_obj.name})))', [key.start + 1])  #   
        elif key.start < 0 and key.stop == None:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , length({temp_ob.col_obj.name}) - ? , length({temp_ob.col_obj.name})))', [abs(key.start) - 1])  #
        elif key.start >= 0 and key.stop < 0:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , ? , length({temp_ob.col_obj.name}) - ?))', [key.start + 1, abs(key.stop - key.start)])  #  
        elif key.start >= 0 and key.stop > 0:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , ? , ?))', [key.start + 1, key.stop - key.start])  #
        elif key.start < 0 and key.stop < 0:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , length({temp_ob.col_obj.name}) - ? , ?))', [abs(key.start) - 1, key.stop - key.start])  #
        elif key.start < 0 and key.stop > 0:
            temp_ob._output = (f'(substr({temp_ob.col_obj.name} , length({temp_ob.col_obj.name}) - ? ,  ? - (length({temp_ob.col_obj.name}) - ?)))', [abs(key.start) - 1, key.stop, abs(key.start)])
        return temp_ob

    def strip(self, chars: str = ' '):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(trim({temp_ob._output[0]},"{chars}"))', temp_ob._output[1]) if temp_ob._output else (f'(trim({temp_ob.col_obj.name},"{chars}"))', [])
        return temp_ob

    def lstrip(self, chars: str = ' '):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(ltrim({temp_ob._output[0]},"{chars}"))', temp_ob._output[1]) if temp_ob._output else (f'(ltrim({temp_ob.col_obj.name},"{chars}"))', [])
        return temp_ob

    def rstrip(self, chars: str = ' '):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(rtrim({temp_ob._output[0]},"{chars}"))', temp_ob._output[1]) if temp_ob._output else (f'(rtrim({temp_ob.col_obj.name},"{chars}"))', [])
        return temp_ob

    def add_end(self, content):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({self.name} || {content._output[0]})', [content._output[1]]) if isinstance(content, ColumnsOperation) else (f'({self.name} || {content.name})', []) if isinstance(content, Column) else (f'({self.name} || ?)', [content])
        return temp_ob

    def add_first(self, content):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'({content._output[0]} || {self.name})', [content._output[1]]) if isinstance(content, ColumnsOperation) else (f'({content.name} || {self.name})', []) if isinstance(content, Column) else (f'(? || {self.name})', [content])
        return temp_ob
    
    def lower(self):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(lower({temp_ob._output[0]}))', temp_ob._output[1]) if temp_ob._output else (f'(lower({temp_ob.col_obj.name}))', [])
        return temp_ob

    def upper(self):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(upper({temp_ob._output[0]}))', temp_ob._output[1]) if temp_ob._output else (f'(upper({temp_ob.col_obj.name}))', [])
        return temp_ob

    def replace(self, old, new):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f'(replace({temp_ob._output[0]} , ? , ?))', temp_ob._output[1] + [old, new]) if temp_ob._output else (f'(replace({temp_ob.col_obj.name} , ? , ?))', [old, new])
        return temp_ob

    def like(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like {value._output[0]})", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f'({self.name} like {value.name})', temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f'({self.name} like ?)', (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def startswith(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like {value._output[0]} || '%')", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self.name} like {value.name} || '%')", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"({self.name} like ? || '%')", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def endswith(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like '%' || {value._output[0]})", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self.name} like '%' || {value.name})", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"({self.name} like '%' || ?)", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def In(self, column: Column|ColumnsOperation = None, where: ColumnsOperation = None, data_list: list = None):
        op = ColumnsOperation(self)
        op._output = (self.name, [])
        return op.In(column=column, where=where, data_list=data_list)

    def contains(self, value):
        temp_ob = ColumnsOperation(self)
        temp_ob._output = (f"({self.name} like '%' || {value._output[0]} || '%')", (temp_ob._output[1] + value._output[1]) if temp_ob._output else value._output[1]) if isinstance(value, ColumnsOperation) else (f"({self.name} like '%' || {value.name} || '%')", temp_ob._output[1] if temp_ob._output else []) if isinstance(value , Column) else (f"({self.name} like '%' || ? || '%')", (temp_ob._output[1] + [f'{value}']) if temp_ob._output else [f'{value}'])
        return temp_ob

    def rename(self, new_name: str) -> None:
        query = f'ALTER TABLE {self.table_obj.name_} RENAME COLUMN {self.first_name} TO [{new_name}];'
        queue_call_back = SimpleQueue()
        self.table_obj.main_queue.put(['qcb', (query,), queue_call_back])
        if not (callback := queue_call_back.get(block=True))[0]:
            raise Exception(callback[1])
        self.table_obj.__delattr__(self.first_name[1:-1])
        self.table_obj.__setattr__(new_name, Column(self.table_obj, new_name, self.datatype))

    def delete_column(self, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool) -> None:
        if are_you_sure and are_you_really_sure and for_sure:
            query = f'ALTER TABLE {self.table_obj.name_} DROP COLUMN {self.first_name};'
            queue_call_back = SimpleQueue()
            self.table_obj.main_queue.put(['qcb', (query,), queue_call_back])
            if not (callback := queue_call_back.get(block=True))[0]:
                raise Exception(callback[1])
            self.table_obj.__delattr__(self.first_name[1:-1])


class BatchOperation:
    def __init__(self, table_object: Table):
        self.script = []
        self.table_obj = table_object

    def update(self, update: dict[Column, Any], where: ColumnsOperation, table: Table = None) -> 'BatchOperation':
        temp_list= []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        self.script.append([f'UPDATE {table.name_ if table else self.table_obj.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=?' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1]])
        return self

    def insert(self, insert: dict[Column, Any], table: Table = None) -> 'BatchOperation':
        self.script.append([f'INSERT INTO {table.name_ if table else self.table_obj.name_} ({', '.join(i.first_name for i in list(insert.keys()))}) VALUES ({', '.join(f'?' for k in insert)})' , [v for v in list(insert.values())]])
        return self

    def delete_row(self, where: ColumnsOperation, table: Table = None) -> 'BatchOperation':
        self.script.append([f'DELETE FROM {table.name_ if table else self.table_obj.name_} WHERE {where._output[0]};', where._output[1]])
        return self
    
    def run(self):
        queue_call_back = SimpleQueue()
        self.table_obj.main_queue.put(['qsb', self.script, queue_call_back])
        if not (callback := queue_call_back.get(block=True))[0]:
            raise Exception(callback[1])


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


class SetPragma:

    def __init__(self, connector_obj):
        self.queue = connector_obj.main_queue

    def _exc(self, cmd: str, query: tuple):
        queue_call_back = SimpleQueue()
        self.queue.put((cmd, query, queue_call_back))
        if (callback := queue_call_back.get(block=True))[0]:
            return callback[1]
        else:
            raise Exception(callback[1])

    def journal_mode(self, value: Literal["DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"]):
        self._exc('qcb', (f"PRAGMA journal_mode = {value};",))

    def synchronous(self, value: Literal["OFF", "NORMAL", "FULL", "EXTRA"]):
        self._exc('qcb', (f"PRAGMA synchronous = {value};",))

    def wal_autocheckpoint(self, pages: int):
        if not isinstance(pages, int) or pages < 0:
            raise ValueError("pages must be non-negative integer")
        self._exc('qcb', (f"PRAGMA wal_autocheckpoint = {pages};",))

    def wal_checkpoint(self, mode: Literal["PASSIVE", "FULL", "RESTART", "TRUNCATE"] = "PASSIVE"):
        self._exc('qcb', (f"PRAGMA wal_checkpoint({mode});",))

    def foreign_keys(self, enable: bool | Literal["ON", "OFF"]):
        val = "ON" if enable is True or enable == "ON" else "OFF"
        self._exc('qcb', (f"PRAGMA foreign_keys = {val};",))

    def defer_foreign_keys(self, enable: bool | Literal["ON", "OFF"]):
        val = "ON" if enable is True or enable == "ON" else "OFF"
        self._exc('qcb', (f"PRAGMA defer_foreign_keys = {val};",))

    def cache_size(self, pages_or_kb: int):
        self._exc('qcb', (f"PRAGMA cache_size = {pages_or_kb};",))

    def mmap_size(self, bytes_size: int):
        if bytes_size < 0:
            raise ValueError("mmap_size cannot be negative")
        self._exc('qcb', (f"PRAGMA mmap_size = {bytes_size};",))

    def shrink_memory(self):
        self._exc('qcb', (f"PRAGMA shrink_memory;",))

    def optimize(self, mask: int = 0x10002):
        self._exc('qcb', (f"PRAGMA optimize({mask});",))

    def automatic_index(self, enable: bool | Literal["ON", "OFF"]):
        val = "ON" if enable is True or enable == "ON" else "OFF"
        self._exc('qcb', (f"PRAGMA automatic_index = {val};",))

    def writable_schema(self, value: bool | Literal["ON", "OFF", "RESET"]):
        if value == "RESET":
            v = "RESET"
        else:
            v = "ON" if value is True or value == "ON" else "OFF"
        self._exc('qcb', (f"PRAGMA writable_schema = {v};",))


class Table:
    PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_?_'
    def __init__(self, obj: Driver, table_name: str):
        self.name_= '['+table_name+']'
        self.main_queue: SimpleQueue= obj.main_queue
        self.db_obj= obj
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_?_'
        for i in self.get_table_info():
            self.__setattr__(i['name'], Column(self, i['name'], i['datatype']))
        self.__setattr__('ROWID', Column(self, 'ROWID', int))

    def _exc(self, cmd: str, query: tuple):
        queue_call_back = SimpleQueue()
        self.main_queue.put((cmd, query, queue_call_back))
        if (callback := queue_call_back.get(block=True))[0]:
            return callback[1]
        else:
            raise Exception(callback[1])

    def batch(self) -> 'BatchOperation':
        return BatchOperation(self)

    def update(self, update: dict[Column, Any], where: 'ColumnsOperation') -> None:
        temp_list = []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        query = (f'UPDATE {self.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value , Column) else f'{key.first_name}=?' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0]}' for key , value in list(update.items()))} WHERE {where._output[0]};', temp_list+where._output[1])
        self._exc('qcb', query)

    def get_table_info(self, from_readers_pool: bool = False):
        query = f'PRAGMA table_info({self.name_})'
        if not from_readers_pool:
            columns = self._exc('qf', (query,))
        else:
            queueCallBack = SimpleQueue()
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', (query,), queueCallBack])
            if (callback := queueCallBack.get(block=True))[0]:
                columns = callback[1]
            else:
                raise Exception(callback[1])
            self.db_obj.pool_holder.put(connection_queue)
        
        return [{'id':i[0], 'name':i[1], 'datatype':int if 'INTEGER' in i[2]  else str if 'TEXT' in i[2] else float if 'REAL' in i[2] else bytes if 'BLOB' in i[2] else float if 'NUMERIC' in i[2] else str, 'notnull': i[3], 'default_value':i[4], 'primary_key':i[5]}for i in columns]

    def get_columns_name(self, from_readers_pool: bool = False) -> list[str]:
        query = f'PRAGMA table_info({self.name_})'
        
        if not from_readers_pool:
            columns = self._exc('qf', (query,))
        else:
            queueCallBack = SimpleQueue()
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', (query,), queueCallBack])
            if (callback := queueCallBack.get(block=True))[0]:
                columns = callback[1]
            else:
                raise Exception(callback[1])
            self.db_obj.pool_holder.put(connection_queue)
        return [i[1] for i in columns]

    def get_row(self,which_columns: list['Column' | 'ColumnsOperation'],where: 'ColumnsOperation' = None,order_by: 'Column' = None,from_readers_pool: bool = False):
        tl = []
        wc = []
        [wc.append(i.first_name) if isinstance(i,Column) else [wc.append(i._output[0]), tl.extend(i._output[1])] for i in which_columns]
        
        query = (f'SELECT {', '.join(wc)} FROM {self.name_} WHERE {where._output[0]} ORDER BY {order_by.first_name if order_by else 'ROWID'};', tl+where._output[1]) if where else (f'SELECT {', '.join(wc)} FROM {self.name_} ORDER BY {order_by.first_name if order_by else 'ROWID'};',tl) if tl else (f'SELECT {', '.join(wc)} FROM {self.name_} ORDER BY {order_by.first_name if order_by else 'ROWID'};',)
        if not from_readers_pool:
            return [row[0] for row in self._exc('qf', query)] if len(which_columns) == 1 else self._exc('qf', query)
        else:
            queueCallBack = SimpleQueue()
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', query, queueCallBack])
            self.db_obj.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return [row[0] for row in callback[1]] if len(which_columns) == 1 else callback[1]
            else:
                raise Exception(callback[1])

    def insert(self, insert: dict['Column', Any]) -> None:
        query = (f'INSERT INTO {self.name_} ({', '.join(i.first_name for i in list(insert.keys()))}) VALUES ({', '.join(f'?' for k in insert)})', [v for v in list(insert.values())])
        self._exc('qcb', query)
 
    def custom_execute(self, query: str, params: list = None) -> None:
        self._exc('qcb', (query, params)) if params else self._exc('qcb', (query,))
            
    def custom_execute_many(self, query: str, params: list = None) -> None:
        self._exc('qmb', (query, params)) if params else self._exc('qmb', (query,))

    def custom_execute_with_fetch(self, query: str, params: list = None, from_readers_pool: bool = False) -> Any:
        if not from_readers_pool:
            return self._exc('qf', (query, params)) if params else self._exc('qf', (query,))
        else:
            queueCallBack = SimpleQueue()
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', (query, params), queueCallBack]) if params else connection_queue.put(['qf', (query,), queueCallBack])
            self.db_obj.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return callback[1]
            else:
                raise Exception(callback[1])

    def delete_row(self, where: 'ColumnsOperation') -> None:
        query = (f'DELETE FROM {self.name_} WHERE {where._output[0]};', where._output[1])
        self._exc('qcb', query)

    def delete_table(self, are_you_sure: bool, are_you_really_sure: bool, for_sure: bool) -> None:
        if are_you_sure and are_you_really_sure and for_sure:
            query = f'DROP TABLE {self.name_};'
            self._exc('qcb', (query,))
            self.db_obj.__delattr__(self.name_[1:-1])

    def delete_column(
        self,
        column: 'Column',
        are_you_sure: bool,
        are_you_really_sure: bool,
        for_sure: bool
        ) -> None:
        if are_you_sure and are_you_really_sure and for_sure:
            query = f'ALTER TABLE {self.name_} DROP COLUMN {column.first_name};'
            self._exc('qcb', (query,))
            self.__delattr__(column.first_name)

    def add_column(self, column_name: str, datatype: int|str|float|bytes, default_value=None, not_null: bool=None) -> None:
        query = f'ALTER TABLE {self.name_} ADD COLUMN {datatype.replace('my_saulted_x',column_name)}{' NOT NULL' if not_null else ''}{f' DEFAULT {f"'{default_value}'" if type(default_value) == str else default_value}' if default_value else ''}'
        self._exc('qcb', (query,))
        self.__setattr__(column_name, Column(self, column_name, int if 'INTEGER' in datatype  else str if 'TEXT' in datatype else float if 'REAL' in datatype else bytes if 'BLOB' in datatype else float if 'NUMERIC' in datatype else str))

    def rename_table(self, new_name: str) -> None:
        query = f'ALTER TABLE {self.name_} RENAME TO {new_name};'
        self._exc('qcb', (query,))
        self.db_obj.__delattr__(self.name_[1:-1])
        self.db_obj.__setattr__(new_name, Table(obj=self.db_obj, table_name=new_name))
        self.name_ = f'[{new_name}]'

    def rename_column(self, column: 'Column', new_name: str) -> None:
        query = f'ALTER TABLE {self.name_} RENAME COLUMN {column.first_name} TO {new_name};'
        self._exc('qcb', (query,))
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
                wr=wr.replace('?',i if isinstance(i,str) else str(i),1)
        
        query = (f'CREATE {'UNIQUE ' if unique else ''}INDEX {index_name} ON {self.name_} ({','.join(i.first_name for i in columns)}) {wr if where else ''}',[])
        self._exc('qcb', query)

    def delete_index(self, index_name: str) -> None:
        query = (f'DROP INDEX {index_name}',)
        self._exc('qcb', query)

    def reindex(self, index_name: str) -> None:
        query = (f'REINDEX {index_name}',)
        self._exc('qcb', query)

    def get_indexes(self, from_readers_pool: bool = False) -> Any:
        query = (f'PRAGMA index_list({self.name_});',)
        if not from_readers_pool: 
            return [i[1] for i in  self._exc('qf', query)]
        else:
            queueCallBack= SimpleQueue()  
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', query, queueCallBack])
            self.db_obj.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return [i[1] for i in callback[1]]
            else:
                raise Exception(callback[1])

    def get_index_info(self, index_name: str, from_readers_pool: bool = False) -> Any:
        query = (f'PRAGMA index_info({index_name});',)
        if not from_readers_pool:
            return {'name':index_name, 'indexed_columns':[i[2] for i in self._exc('qf', query)]}
        else:
            queueCallBack= SimpleQueue() 
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', query, queueCallBack])
            self.db_obj.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return {'name':index_name, 'indexed_columns':[i[2] for i in callback[1]]}
            else:
                raise Exception(callback[1])

    def bulk_insert(self, columns: list['Column'], data_list: list) -> None:
        query = f'INSERT INTO {self.name_} ({', '.join(i.first_name for i in columns)}) VALUES ({', '.join('?' for i in columns)});'
        self._exc('qmb', (query, data_list))

    def bulk_update(self, update: dict['Column', Any], where: 'ColumnsOperation', data_list: list) -> None:
        temp_list = []
        [None if isinstance(value , Column) else temp_list.append(value) if not isinstance(value, ColumnsOperation) else temp_list.extend(value._output[1]) for key, value in update.items()]
        query_splited = f'UPDATE {self.name_} SET {', '.join(f'{key.first_name} = {value.first_name}' if isinstance(value, Column) else f'{key.first_name}={self.PLACE_HOLDER}' if not isinstance(value , ColumnsOperation) else f'{key.first_name}={value._output[0].replace('?', self.PLACE_HOLDER)}' for key , value in list(update.items()))} WHERE {where._output[0].replace('?', self.PLACE_HOLDER)};'.split(self.PLACE_HOLDER)
        query= query_splited[0]
        for a,i in enumerate(temp_list+where._output[1]):
            query = query +( f'"{i}"' if isinstance(i,str) and not i == self.PLACE_HOLDER else str(i))+ query_splited[a+1] #All "? || '%'" thing are because of Column.contain() method and .startswith() and .endswith() that have "%" in output value
        try:
            self._exc('qmb', (query.replace(self.PLACE_HOLDER, '?'), data_list))
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
        order_by: 'Column' = None,
        from_readers_pool: bool = False
        ) -> Any:
        tl = []
        [tl.extend(i._output[1]) if isinstance(i,ColumnsOperation) else None for i in columns]
        [tl.extend(i._output[1]) for i in joins_list]
        query= (f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column)  else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")") else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'WHERE {where._output[0]}' if where else ''} {f'ORDER BY {order_by.name}' if order_by else ''}', tl+where._output[1]) if where else (f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column)  else f'{i._output[0][1:-1] if i._output[0].startswith("(") and i._output[0].endswith(")") else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'ORDER BY {order_by.name}' if order_by else ''}', tl) if tl else (f'SELECT {','.join(f'{i.name} AS {i.table_obj.name_[1:-1]}_{i.first_name[1:-1]}' if isinstance(i,Column)  else f'{i._output[0][1:-1] if i._output[0].startswith('(') and i._output[0].endswith(')') else i._output[0] } AS {i.col_obj.table_obj.name_[1:-1]}_{i.col_obj.first_name[1:-1]}' for i in columns)} FROM {self.name_} {' '.join(i._output[0] for i in joins_list)} {f'ORDER BY {order_by.name}' if order_by else ''}',)
        # The above line is approximately 1000 characters, which is not standard, but it is written this way
        # to improve performance in the Driver class and to avoid checking whether the second item in the query
        # is an empty list for each input.
        if not from_readers_pool:
            return self._exc('qf', query)
        else:
            queueCallBack= SimpleQueue()
            connection_queue = self.db_obj.pool_holder.get(block=True)
            connection_queue.put(['qf', query, queueCallBack])
            self.db_obj.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return callback[1]
            else:
                raise Exception(callback[1])


class DataTypes:
    """
    SQLite Data Types with CHECK constraint generation.
    Each method returns a complete column definition string including CHECK
    for length limits, enum values, etc.
    The placeholder 'my_saulted_x' will be replaced by the actual column name.
    """

    @staticmethod
    def INTEGER(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """Standard integer. Unsigned adds CHECK(my_saulted_x >= 0)."""
        checks = []
        if unsigned and min_val is None:
            checks.append("my_saulted_x >= 0")
        if min_val is not None:
            checks.append(f"my_saulted_x >= {min_val}")
        if max_val is not None:
            checks.append(f"my_saulted_x <= {max_val}")
        if checks:
            return f"my_saulted_x INTEGER CHECK({' AND '.join(checks)})"
        return f"my_saulted_x INTEGER"

    @staticmethod
    def REAL(min_val: float = None, max_val: float = None, unsigned: bool = False) -> str:
        """
        Floating-point number (8 bytes).
        If unsigned=True, adds CHECK(my_saulted_x >= 0).
        If min_val/max_val provided, adds range CHECK.
        """
        checks = []
        if unsigned:
            checks.append("my_saulted_x >= 0")
        if min_val is not None:
            checks.append(f"my_saulted_x >= {min_val}")
        if max_val is not None:
            checks.append(f"my_saulted_x <= {max_val}")
        if checks:
            return f"my_saulted_x REAL CHECK({' AND '.join(checks)})"
        return f"my_saulted_x REAL"

    @staticmethod
    def FLOAT(min_val: float = None, max_val: float = None, unsigned: bool = False) -> str:
        """Synonym for REAL."""
        return DataTypes.REAL(min_val, max_val, unsigned)

    @staticmethod
    def DOUBLE(min_val: float = None, max_val: float = None, unsigned: bool = False) -> str:
        """Synonym for REAL."""
        return DataTypes.REAL(min_val, max_val, unsigned)

    @staticmethod
    def DECIMAL(precision: int = None, scale: int = None,
                min_val: float = None, max_val: float = None,
                unsigned: bool = False) -> str:
        """
        Fixed-point decimal stored as REAL with optional range CHECK based on precision/scale.
        If precision/scale given, infers default range (max = 10^(precision-scale) - 10^-scale).
        Custom min_val/max_val override defaults.
        """
        checks = []
        if unsigned:
            checks.append("my_saulted_x >= 0")
        # Compute default range from precision/scale if provided and no custom bounds
        if precision is not None and scale is not None:
            default_max = 10 ** (precision - scale) - 10 ** (-scale)
            default_min = 0 if unsigned else -default_max
            actual_min = min_val if min_val is not None else default_min
            actual_max = max_val if max_val is not None else default_max
            checks.append(f"my_saulted_x BETWEEN {actual_min} AND {actual_max}")
        elif precision is not None and scale is None:
            default_max = 10 ** precision - 1
            default_min = 0 if unsigned else -default_max
            actual_min = min_val if min_val is not None else default_min
            actual_max = max_val if max_val is not None else default_max
            checks.append(f"my_saulted_x BETWEEN {actual_min} AND {actual_max}")
        else:
            # No precision/scale: apply custom min/max if given
            if min_val is not None:
                checks.append(f"my_saulted_x >= {min_val}")
            if max_val is not None:
                checks.append(f"my_saulted_x <= {max_val}")
        if checks:
            return f"my_saulted_x REAL CHECK({' AND '.join(checks)})"
        return f"my_saulted_x REAL"

    @staticmethod
    def NUMERIC(precision: int = None, scale: int = None,
                min_val: float = None, max_val: float = None,
                unsigned: bool = False) -> str:
        """Synonym for DECIMAL."""
        return DataTypes.DECIMAL(precision, scale, min_val, max_val, unsigned)

    @staticmethod
    def TEXT(min_length: int = None, max_length: int = None) -> str:
        """
        Text type with optional length constraints.
        """
        checks = []
        if min_length is not None:
            checks.append(f"LENGTH(my_saulted_x) >= {min_length}")
        if max_length is not None:
            checks.append(f"LENGTH(my_saulted_x) <= {max_length}")
        if checks:
            return f"my_saulted_x TEXT CHECK({' AND '.join(checks)})"
        return f"my_saulted_x TEXT"

    @staticmethod
    def BLOB() -> str:
        """Binary type."""
        return f"my_saulted_x BLOB"

    @staticmethod
    def NULL() -> str:
        """NULL type (rarely used)."""
        return f"my_saulted_x NULL"

    @staticmethod
    def VARCHAR(min_length: int = None, max_length: int = None) -> str:
        """
        Variable-length string with maximum length.
        If length is given, sets max_length = length.
        """
        return DataTypes.TEXT(min_length, max_length)

    @staticmethod
    def TINYINT(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """
        Signed: -128..127, Unsigned: 0..255.
        Custom min/max override the default range.
        """
        if unsigned:
            default_min, default_max = 0, 255
        else:
            default_min, default_max = -128, 127
        actual_min = min_val if min_val is not None else default_min
        actual_max = max_val if max_val is not None else default_max
        if actual_min is not None or actual_max is not None:
            return f"my_saulted_x INTEGER CHECK(my_saulted_x BETWEEN {actual_min} AND {actual_max})"
        return f"my_saulted_x INTEGER"

    @staticmethod
    def SMALLINT(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """Signed: -32768..32767, Unsigned: 0..65535."""
        if unsigned:
            default_min, default_max = 0, 65535
        else:
            default_min, default_max = -32768, 32767
        actual_min = min_val if min_val is not None else default_min
        actual_max = max_val if max_val is not None else default_max
        if actual_min is not None or actual_max is not None:
            return f"my_saulted_x INTEGER CHECK(my_saulted_x BETWEEN {actual_min} AND {actual_max})"
        return f"my_saulted_x INTEGER"

    @staticmethod
    def MEDIUMINT(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """Signed: -8388608..8388607, Unsigned: 0..16777215."""
        if unsigned:
            default_min, default_max = 0, 16777215
        else:
            default_min, default_max = -8388608, 8388607
        actual_min = min_val if min_val is not None else default_min
        actual_max = max_val if max_val is not None else default_max
        if actual_min is not None or actual_max is not None:
            return f"my_saulted_x INTEGER CHECK(my_saulted_x BETWEEN {actual_min} AND {actual_max})"
        return f"my_saulted_x INTEGER"

    @staticmethod
    def INT(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """Standard integer. Unsigned adds CHECK(my_saulted_x >= 0)."""
        checks = []
        if unsigned and min_val is None:
            checks.append("my_saulted_x >= 0")
        if min_val is not None:
            checks.append(f"my_saulted_x >= {min_val}")
        if max_val is not None:
            checks.append(f"my_saulted_x <= {max_val}")
        if checks:
            return f"my_saulted_x INTEGER CHECK({' AND '.join(checks)})"
        return f"my_saulted_x INTEGER"

    @staticmethod
    def BIGINT(min_val: int = None, max_val: int = None, unsigned: bool = False) -> str:
        """Same as INT (SQLite INTEGER is 64-bit)."""
        return DataTypes.INT(min_val, max_val, unsigned)

    @staticmethod
    def CHAR(min_length: int = None, max_length: int = None) -> str:
        """Fixed-length character. If length given, sets min_length = max_length = length."""
        return DataTypes.TEXT(min_length, max_length)

    @staticmethod
    def ENUM(*values: str) -> str:
        """Enumeration: allowed values list."""
        quoted = ", ".join(f"'{v}'" for v in values)
        return f"my_saulted_x TEXT CHECK(my_saulted_x IN ({quoted}))"

    @staticmethod
    def BOOLEAN() -> str:
        """Boolean stored as INTEGER 0/1."""
        return f"my_saulted_x INTEGER CHECK(my_saulted_x IN (0, 1))"

    @staticmethod
    def CUSTOM(type_name: str, check: str = None) -> str:
        """
        Custom data type name (when strict mode OFF). Optionally add a CHECK constraint.
        Example: CUSTOM('GEOMETRY', 'my_saulted_x IS NOT NULL')
        """
        if check:
            return f"my_saulted_x {type_name} CHECK({check})"
        return f"my_saulted_x {type_name}"


class TableStructure:
    ON_CONFLICT= Literal['ABORT', 'ROLLBACK', 'FAIL', 'IGNORE', 'REPLACE']
    ON_ACTION= Literal['CASCADE', 'SET NULL', 'SET DEFAULT', 'RESTRICT', 'NO ACTION']
    ON_INIT= Literal['DEFERRED', 'IMMEDIATE']

    def __init__(self, table_name: str, strict: bool = False, primarykey_on_conflict: ON_CONFLICT = 'ABORT'):
        self.strict= strict
        self.table_query= ''
        self.primary_keys= []
        self.items= {}
        self.name= table_name
        self.foreigns= []
        self.pkonc = primarykey_on_conflict

    def add_column(self, column_name: str, datatype: DataTypes,
                default_value=None, unique: bool = None,
                unique_on_conflict: ON_CONFLICT = 'ABORT',
                not_null: bool = None,
                not_null_on_conflict: ON_CONFLICT = 'ABORT',
                primary_key: bool = None):
        for item in self.table_query.split(','):
            if column_name in item:
                raise Exception('You have added this column befor\nif you wanna modify this column , delete this column and then add a new one with desired options') if item.split(' ')[0] == column_name else None
        if type(default_value) == bytes:
            raise Exception('Cant set bytes object as default value')
        self.primary_keys.append(column_name) if primary_key else None
        self.items[column_name] = [datatype, default_value, unique, unique_on_conflict, not_null, not_null_on_conflict, primary_key]
        self.table_query = self.table_query + f' {datatype.replace('my_saulted_x' , f'[{column_name.strip()}]')}{f' UNIQUE ON CONFLICT {unique_on_conflict}' if unique else ''}{f' NOT NULL ON CONFLICT {not_null_on_conflict}' if not_null else ''}{f' DEFAULT {f"'{default_value}'" if type(default_value) == str else default_value}' if default_value else ''},'
        return self

    def delete_column(self, column_name: str):
        query_list = self.table_query.split(',')
        self.items.pop(column_name)
        for item in query_list:
            if item.startswith(column_name):
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
            items_dict['unique_on_conflict']= values[3]
            items_dict['not_null']= True if values[4] else False
            items_dict['not_null_on_conflict']= values[5]
            items_dict['primari_key']= True if values[6] else False
            items_list.append(items_dict)
        return items_list

    def foreign_key(self, column: str, refrences_table: 'Table',
                    refrences_column: 'Column', on_delete: ON_ACTION = None,
                    on_update: ON_ACTION = None, deferrable: bool = True,
                    initially: ON_INIT = 'DEFERRED'):
        self.foreigns.append(f'FOREIGN KEY ({column}) REFERENCES {refrences_table.name_} ({refrences_column.first_name}){f' ON DELETE {on_delete}' if on_delete else ''}{f' ON UPDATE {on_update}' if on_update else ''}{' DEFERRABLE' if deferrable else ' NOT DEFERRABLE'}{f' INITIALLY {initially}' if initially else ''}')
        return self

    def get_structure(self):
        return f'CREATE TABLE [{self.name}] ({self.table_query[:-1]}{',' if self.primary_keys else ''}{f'PRIMARY KEY({', '.join(self.primary_keys)}) ON CONFLICT {self.pkonc}' if self.primary_keys else ''}{',' if self.foreigns else ''}{','.join(self.foreigns) if self.foreigns else ''}) {'STRICT' if self.strict else ''};'


class Driver:
    PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_?_'
    ISOLATION_LEVEL= Literal['DEFERRED', 'IMMEDIATE', 'EXCLUSIVE']
    def __init__(self, db_path: str, isolation_level: ISOLATION_LEVEL = 'DEFERRED',
                cache_size: int = 128, none_block_reader_pool_size: int = 1,
                setup_time: float = 0.5):

        try:
            connector = connect(db_path , isolation_level=isolation_level , cached_statements=cache_size)
            connector.close()
        except Exception as e:
            raise Exception(e)
        self.PLACE_HOLDER = '_MY_S4ULT3D_PL4C3_H0LD3R_?_'
        self.db_path= db_path
        self.main_queue= SimpleQueue()
        self.wal_stop= Event()
        self.wal_enabled= Event()
        self.SetPragma= SetPragma(self)
        self.reader_pool_size = none_block_reader_pool_size
        self.pool_holder = SimpleQueue()
        for i in range(self.reader_pool_size):
            connection_queue = SimpleQueue()
            Thread(target=Driver.reader_driver, args=(connection_queue, self.db_path, isolation_level, cache_size)).start()
            self.pool_holder.put(connection_queue)
        Thread(target=Driver.simple_driver, args=(self.main_queue, self.db_path, isolation_level, cache_size)).start()
        QueueCallBack=SimpleQueue()
        self.main_queue.put(['qf', ('SELECT * FROM SQLITE_MASTER;',), QueueCallBack])
        if (callback:= QueueCallBack.get(block=True))[0]:
            [self.__setattr__(i[1], Table(self, i[1])) if i[0] == 'table' and i[1] != 'sqlite_sequence' else None for i in callback[1]]
            sleep(setup_time) #give Table objects some time to fetch from database and do __setattr__ 
        else:
            raise Exception(callback[1])
        
    def _exc(self, cmd: str, query: tuple):
        queue_call_back = SimpleQueue()
        self.main_queue.put((cmd, query, queue_call_back))
        if (callback := queue_call_back.get(block=True))[0]:
            return callback[1]
        else:
            raise Exception(callback[1])

    @staticmethod
    def reader_driver(receiver: SimpleQueue, db_path: str, isolation_level: str, cache_size: int):
        while True:
            try:
                connector = connect(db_path , isolation_level=isolation_level , cached_statements=cache_size)
                cursor = connector.cursor()
                break
            except:
                pass
        while True:
            try:
                query = receiver.get(block=True, timeout=0.05)
                print(query)
                if query[0] == 'dc':
                    break
            except:
                continue
            try:
                query[2].put((True, cursor.execute(query[1][0]).fetchall())) if len(query[1]) == 1 else query[2].put((True, cursor.execute(query[1][0], query[1][1]).fetchall()))
            except Exception as e:
                query[2].put((False, e))

    @staticmethod
    def simple_driver(receiver: SimpleQueue, db_path: str, isolation_level: str, cache_size: int):

        connector = connect(db_path , isolation_level=isolation_level , cached_statements=cache_size)
        cursor = connector.cursor()
        while True:
            try:
                try:
                    query = receiver.get(block=True, timeout=0.05)
                    cmd = query[0]
                    print(query)
                except:
                    continue
                match cmd:
                    case 'qf':
                        try:
                            query[2].put((True, cursor.execute(query[1][0]).fetchall())) if len(query[1]) == 1 else query[2].put((True,cursor.execute(query[1][0], query[1][1]).fetchall()))
                        except Exception as e:
                            query[2].put((False, e))
                    case 'qcb':
                        try:
                            cursor.execute(query[1][0]) if len(query[1]) == 1 else cursor.execute(query[1][0], query[1][1])
                            connector.commit()
                            query[2].put((True, None))
                        except Exception as e:
                            connector.rollback()
                            query[2].put((False, e))
                    case 'qsb':
                        try:
                            [cursor.execute(i[0]) if len(i) == 1 else cursor.execute(i[0], i[1]) for i in query[1]]
                            connector.commit()
                            query[2].put((True, None))
                        except Exception as e:
                            connector.rollback()
                            query[2].put((False, e))
                    case 'qmb':
                        try:
                            cursor.executemany(query[1][0]) if len(query[1]) == 1 else cursor.executemany(query[1][0], query[1][1])
                            connector.commit()
                            query[2].put((True, None))
                        except Exception as e:
                            connector.rollback()
                            query[2].put((False, e))
                    case 'cp':
                        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                        query[1].put(True)
                    case 'dc':
                        try:
                            connector.commit()
                            query[1].put((True, None))
                        except Exception as e:
                            connector.rollback()
                            query[1].put((False, e))
                        break
            except Exception as e:
                print_exc()

    @staticmethod
    def checkpoint_timer(main_commit_queue: SimpleQueue, timer: int, stop: Event):
        while True:
            if stop.is_set():
                print('checkpoint stopped')
                break
            sleep(timer)
            call_back_queue = SimpleQueue()
            main_commit_queue.put(['cp', call_back_queue])
            try:
                call_back_queue.get(timeout=5.0)
            except:
                pass

    def table_object(self, table_name: str) -> 'Table':
        tables = self.get_tables()
        if not table_name in tables:
            if len(tables) == 0:
                raise Exception(f'No table found')
            raise Exception(f'No such table named {table_name} in this db')
        return Table(self, table_name)

    def custom_execute(self, query: str, params: list = None) -> None:
        return self._exc('qcb', (query, params)) if params else self._exc('qcb', (query,))
        
    def custom_execute_many(self, query: str, params: list = None) -> None:
        return self._exc('qmb', (query, params)) if params else self._exc('qmb', (query,))

    def custom_execute_with_fetch(self, query: str, params: list = None,from_readers_pool: bool = False) -> Any:
        if not from_readers_pool:
            return self._exc('qf', (query,params)) if params else self._exc('qf', (query,))
        else:
            queueCallBack = SimpleQueue()
            connection_queue = self.pool_holder.get(block=True)
            connection_queue.put(['qf', (query,params), queueCallBack]) if params else connection_queue.put(['qf', (query,), queueCallBack])
            self.pool_holder.put(connection_queue)
            if (callback := queueCallBack.get(block=True))[0]:
                return callback[1]
            else:
                raise Exception(callback[1])

    def get_tables(self) -> dict[str, 'Table']:
        tables_list = self.custom_execute_with_fetch('SELECT * FROM SQLITE_MASTER;')
        tables_dict = {}
        for item in tables_list:
            if item[0] == 'table' and not item[1] == 'sqlite_sequence':
                tables_dict[item[1]] = Table(self, item[1])
        return tables_dict

    def create_table(self, table_structure: 'TableStructure') -> 'Table':
        self._exc('qcb', (table_structure.get_structure(),))
        self.__setattr__(table_structure.name, Table(self,table_structure.name))
        return Table(self, table_structure.name)

    def defragment(self) -> None:
        self._exc('qcb', ("VACUUM;PRAGMA optimize;",))

    def set_WAL_mode(self, is_set: bool, wal_timer: int = 60) -> None:
        if is_set:
            self.wal_enabled.set()
            self.wal_stop.clear()
            self._exc('qcb', ("PRAGMA journal_mode=WAL;",))
            Thread(target=Driver.checkpoint_timer, args=(self.main_queue, wal_timer, self.wal_stop)).start()
        else:
            self.wal_stop.set()
            self._exc('qcb', ("PRAGMA journal_mode=PERSIST;",))
        call_back_queue = SimpleQueue()
        self.main_queue.put(['cp', call_back_queue])
        call_back_queue.get(block=True)

    def disconnect(self) -> None:
        self.wal_stop.set()
        callback_dc = SimpleQueue()
        if self.wal_enabled.is_set():
            call_back_queue = SimpleQueue()
            self.main_queue.put(['cp', call_back_queue])
            self.main_queue.put(['dc' , callback_dc])
            call_back_queue.get(block=True)
        else:
            self.main_queue.put(['dc' , callback_dc])
        callback_dc.get(block=True)
        for i in range(self.reader_pool_size):
            connection_queue = self.pool_holder.get(block=True)
            connection_queue.put(['dc'])


#TODO Update 