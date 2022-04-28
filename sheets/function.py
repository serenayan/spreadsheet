
from typing import Any, Callable, Optional
from sheets.cell_error import CellError, CellErrorType
from sheets.formula import formula_parse
from .utils import convert_to_bool, convert_to_decimal, convert_to_str, cell_range_to_list
from .version import version

def _and(args) -> Any:
    if len(args) == 0:
        return CellError(CellErrorType.TYPE_ERROR, "AND requires at least one argument")
    args = [convert_to_bool(arg()) for arg in args]
    res = True
    for arg in args:
        if isinstance(arg, CellError):
            return arg
        res = res and arg
    return res

def _or(args) -> Any:
    if len(args) == 0:
        return CellError(CellErrorType.TYPE_ERROR, "OR requires at least one argument")
    args = [convert_to_bool(arg()) for arg in args]
    res = False
    for arg in args:
        if isinstance(arg, CellError):
            return arg
        res = res or arg
    return res

def _not(args) -> Any:
    if len(args) != 1:
        return CellError(CellErrorType.TYPE_ERROR, "NOT requires exactly one argument")
    args = [convert_to_bool(arg()) for arg in args]
    return args[0]

def _xor(args) -> Any:
    if len(args) == 0:
        return CellError(CellErrorType.TYPE_ERROR, "XOR requires at least one argument")
    args = [convert_to_bool(arg()) for arg in args]
    res = False
    for arg in args:
        if isinstance(arg, CellError):
            return arg
        res = res != arg
    return res

def _exact(args) -> Any:
    if len(args) != 2:
        return CellError(CellErrorType.TYPE_ERROR, "EXACT requires exactly two arguments")
    args = [convert_to_str(arg()) for arg in args]
    for arg in args:
        if isinstance(arg, CellError):
            return arg
    return args[0] == args[1]

def _if(args) -> Any:
    if len(args) not in [2, 3]:
        return CellError(CellErrorType.TYPE_ERROR, "IF requires 2 or 3 arguments")
    condition = convert_to_bool(args[0]())
    if isinstance(condition, CellError):
        return condition
    if condition:
        return args[1]()
    if len(args) == 2:
        return False
    return args[2]()

def _iferror(args) -> Any:
    if len(args) not in [1, 2]:
        return CellError(CellErrorType.TYPE_ERROR, "IFERROR requires 1 or 2 arguments")
    value1 = convert_to_bool(args[0]())
    if not isinstance(value1, CellError):
        return value1
    if len(args) == 2:
        return args[2]()
    return ""

def _choose(args) -> Any:
    if len(args) < 2:
        return CellError(CellErrorType.TYPE_ERROR, "CHOOSE requires at least 2 arguments")
    index = convert_to_decimal(args[0]())
    if isinstance(index, CellError):
        return index
    ratio = index.as_integer_ratio()
    if ratio[1] != 1:
        return CellError(CellErrorType.TYPE_ERROR, "CHOOSE requires an integer index")
    index = ratio[0]
    if index < 1 or index >= len(args):
        return CellError(CellErrorType.TYPE_ERROR, "index out of bounds")
    return args[index]()

def _isblank(args) -> Any:
    if len(args) != 1:
        return CellError(CellErrorType.TYPE_ERROR, "ISBLANK requires 1 argument")
    value = args[0]()
    return value is None

def _iserror(args) -> Any:
    if len(args) != 1:
        return CellError(CellErrorType.TYPE_ERROR, "ISERROR requires exactly one arguments")
    value = args[0]()
    return isinstance(value, CellError)

def _version(args) -> Any:
    if len(args) != 0:
        return CellError(CellErrorType.TYPE_ERROR, "VERSION requires exactly 0 arguments")
    return version

def _indirect(args) -> Any:
    if len(args) != 1:
        return CellError(CellErrorType.TYPE_ERROR, "INDIRECT requires exactly 1 argument")
    value = convert_to_str(args[0]())
    if isinstance(value, CellError):
        return value
    tree = formula_parse("=" + value)
    if str(tree.data) != 'cell':
        return CellError(CellErrorType.TYPE_ERROR, "invalid cell reference")
    return tree

def _min(args) -> Any:
    if len(args) < 1:
        return CellError(CellErrorType.TYPE_ERROR, "MIN requires at least 1 argument")
    value = convert_to_decimal(args[0]())
    if isinstance(value, CellError):
        return value
    
    minimum = min(args)
    return minimum

def _max(args) -> Any:
    if len(args) < 1:
        return CellError(CellErrorType.TYPE_ERROR, "MAX requires at least 1 argument")
    value = convert_to_decimal(args[0]())
    if isinstance(value, CellError):
        return value
    
    maximum = max(args)
    return maximum

def _sum(args) -> Any:
    if len(args) < 1:
        return CellError(CellErrorType.TYPE_ERROR, "SUM requires at least 1 argument")
    value = convert_to_decimal(args[0]())
    if isinstance(value, CellError):
        return value
    
    summation = sum(args)
    return summation

def _average(args) -> Any:
    if len(args) < 1:
        return CellError(CellErrorType.TYPE_ERROR, "AVERAGE requires at least 1 argument")
    value = convert_to_decimal(args[0]())
    if isinstance(value, CellError):
        return value
    
    avg = sum(args) / len(args)
    return avg



class FunctionRegistry():
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FunctionRegistry, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.funcs = {
            'and': _and,
            'or': _or,
            'not': _not,
            'xor': _xor,
            'exact': _exact,
            'if': _if,
            'iferror': _iferror,
            'choose': _choose,
            'iserror': _iserror,
            'isblank': _isblank,
            'version': _version,
            'indirect': _indirect,
            'min': _min,
            'max': _max,
            'sum': _sum,
            'average': _average,
        }

    def find(self, name: str) -> Optional[Callable]:
        if name.lower() not in self.funcs:
            return None
        return self.funcs[name.lower()]
