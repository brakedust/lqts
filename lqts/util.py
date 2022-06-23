# -*- coding: utf-8 -*-
import os
import fnmatch
from collections import OrderedDict
from math import floor, log10


FLOAT_TYPES = [float]
INT_TYPES = [int]

try:
    import numpy

    FLOAT_TYPES.extend([numpy.float32, numpy.float64])

    INT_TYPES.extend(
        [numpy.int0, numpy.int16, numpy.int32, numpy.int64, numpy.int8]
    )
except ImportError:
    pass

NUMERIC_TYPES = tuple(FLOAT_TYPES + INT_TYPES)
FLOAT_TYPES = tuple(FLOAT_TYPES)
INT_TYPES = tuple(INT_TYPES)


def strtype(obj):
    """
    Returns the string name of the type of object obj
    <type 'mytype'> becomes mytype
    """
    # return str(type(obj)).split("'")[1]
    return type(obj).__name__


def sigdigits(x, n, format_code="g"):
    """
    Rounds a number to the specified number of significant digits
    """
    try:
        fstring = "{0:1." + str(n) + format_code + "}"
        return float(fstring.format(x))
    except (ValueError, TypeError):
        return x


def sigdigits2(x, n=1):
    """
    Rounds a number to the specified number of significant digits
    """
    try:
        if x < 0:
            return -round(-x, -int(floor(log10(-x))) + n - 1)
        else:
            return round(x, -int(floor(log10(x))) + n - 1)
    except (ValueError, TypeError):
        return x


def str_sigdigits(x, n, format_code="g"):
    """
    Formats a number with the specified number of significant digits
    """
    if isnumeric(x):
        fstring = "{0:1." + str(n) + format_code + "}"
        return fstring.format(x)
    else:
        return x


def isnumeric(x):
    """
    Tells if an object is a numeric type
    """
    return isinstance(x, NUMERIC_TYPES)


def isfloat(x):
    """
    Tells if an object is some version of a float (could be a numpy of some flavor)
    """
    return isinstance(x, FLOAT_TYPES)


def isint(x):
    """
    Tells if an object is some version of a int (could be a numpy int of some flavor)
    """
    return isinstance(x, INT_TYPES)


def isNoneOrEmpty(obj):
    """
    Tells is a object
    """

    if obj is None:
        return True
    elif isinstance(obj, str):
        return len(obj) == 0
    elif hasattr(obj, "__len__"):
        return len(obj) == 0

    return False


def merge_ordered_dicts(*d):

    result = OrderedDict()

    for di in d:
        for key in di:
            result[key] = di[key]

    return result


def recursive_glob(path, pattern):
    """
    Returns files matching the pattern in any direcotory under the given path
    :param path:
    :param pattern:
    :return:
    """
    matching_files = []
    dirs = []
    for root, dirnames, filenames in os.walk(path):
        for filename in fnmatch.filter(filenames, pattern):
            matching_files.append(os.path.join(root, filename))
            dirs.append(root)
    dirs = list(set(dirs))
    return matching_files, dirs


def parse_bool(val):

    if str(val).lower() in ("true", "t", "1", "yes", "y"):
        return True
    elif str(val).lower() in ("false", "f", "0", "no", "n"):
        return False
    else:
        raise ValueError("Could not parse {0} to bool".format(val))


def try_cast(value, types):
    """
    Attempts to cast value into one of *types*.  It tries in order.
    It returns on the first successful cast.
    :param value:
    :param types:
    :return:
    """
    for ty in types:
        try:
            return ty(value)
        except:  # nopep8
            pass
    return value


def enum(obj):
    """
    A decorator to turn a class into a readonly Enum
    """

    def __setattr__(obj, name, value):
        """
        Controls/Prohibits the setting of class attribute values
        """
        if hasattr(obj, name):
            raise AttributeError(
                "Attempt to set the value of an Enum.  Class = '{0}', Field = '{1}'".format(
                    obj.__class__, name
                )
            )
        else:
            raise AttributeError(
                "'{0}' object has no attribute '{1}'".format(obj.__class__, name)
            )

    def parse(obj, value):
        """
        Get the field that goes this value
        """
        for name in dir(obj):
            if not name.startswith("__") and not hasattr(
                getattr(obj, name), "__call__"
            ):
                # print(name,getattr(obj,name))
                if getattr(obj, name) == value:
                    return name

    def values(obj):
        """
        gets a list of the enums values
        """
        return [
            n
            for n in dir(obj)
            if ((not n.startswith("__")) and (not hasattr(getattr(obj, n), "__call__")))
        ]

    def dict_(obj):
        return {
            n: getattr(obj, n)
            for n in dir(obj)
            if ((not n.startswith("__")) and (not hasattr(getattr(obj, n), "__call__")))
        }

    setattr(obj, "parse", parse)
    setattr(obj, "values", values)
    setattr(obj, "dict", dict_)

    setattr(obj, "__setattr__", __setattr__)

    obj = obj()

    return obj


def _multirange_next(value_counts, counters):
    """
    Increments the counters for the multirange function.  This raises a StopIteration when
     the mutlirange iterator is exhausted
    :param value_counts:
    :param counters:
    :return:
    """
    i = len(value_counts) - 1
    while i > -1:

        if counters[i] < value_counts[i] - 1:
            counters[i] += 1

            return counters
        else:
            counters[i] = 0
            i -= 1

    raise StopIteration


def multirange(*value_counts):
    """
    An generator that yields nested range values.  Values always start from 0 and
    increment by 1.

    Example:
        >>> for i,j in multirange(2,3):
        >>> print(i,j)
        0 0
        0 1
        0 2
        1 0
        1 1
        1 2
    """
    if len(value_counts) == 0:
        raise StopIteration

    counters = [0] * len(value_counts)
    while True:
        yield counters
        counters = _multirange_next(value_counts, counters)
