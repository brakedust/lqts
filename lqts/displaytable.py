# -*- coding: utf-8 -*-
"""
displaytable
------------

The displaytable module creates tables that are printable to the screen
or a document (in fixed width font)
and that are compliant with the ReStructured Text format.

Functions :

"""

from sqs.util import sigdigits, isfloat
from copy import copy
import math
from collections import OrderedDict
import textwrap

# pylint: disable=C0103


def tryget(llst, i, j):
    """Try to get a value from a list of lists"""
    try:
        val = llst[i][j]
    except Exception:
        val = ""
    return val


def tablize(listofdicts, include="*"):
    """
    Turns a list of dicts into a list of rows where
    row 0 are the column titles and subsequent rows
    are the column values for that row.

    Inputs:

        listofdicts : list of dicts
            a list of dicts where the keys are the column headers and the
            values are the row values
        include : list of str
            a list of which columns to include in the resulting structure.
            Default is all columns included

    Example:

    >>> from collections import OrderedDict
    >>> rows = []
    >>> rows.append(OrderedDict([('A',1),('B',2),('C',3)]))
    >>> rows.append(OrderedDict([('A',4),('B',5),('C',6)]))
    >>> rows.append(OrderedDict([('A','Hello'),('B',u'Goodbye'),
    ...     ('C','Farewell')]))
    >>> t = dtab.tablize(rows,rows[0].keys())
    >>> from pprint import pprint
    >>> pprint(t)
    [['A    ', 'B      ', 'C       '],
     ['1    ', '2      ', '3       '],
     ['4    ', '5      ', '6       '],
     ['Hello', 'Goodbye', 'Farewell']]

    """

    table = []
    if include == "*":
        # using a set is fast but doesn't preserve order
        # include = set(chain(*[ld.keys() for ld in listofdicts]))

        # this approach is slower but preserves order
        include = list(listofdicts[0].keys())
        for rowdict in listofdicts[1:]:
            for k in rowdict.keys():
                if k not in include:
                    include.append(k)
        # include = list(include)

    # include only specified columns
    table.append(include)
    for i in listofdicts:
        # i2 = dict{k:v for k,v in i.iteritems() if i in include}
        row = []
        for k in include:
            row.append(i.get(k, " "))

        table.append(row)

    return table


def tablize_dataframe(df):
    """
    Turns a DataFrame into a list of row lists

    Parameters
    -------------
    df : DataFrame

    Returns
    --------
    table : list[list]
        The list[list] object ready for make_table

    """
    table = []
    table.append(list(df.columns))
    for index, row in df.iterrows():
        table.append(list(row))

    return table


def tablize_dict_of_dicts(data, include=None, outer_key_name="index"):
    """
    Turns a dict of dicts into a list of row lists

    Parameters
    ------------------
    data : dict[dict]
        The data to turn into a list of list
    include : list[str]
        Which columns to include.  Default is to include all
    outer_key_name : str
        The keys of the outer dict will be in the first column.
        outer_key_name is the title of this column.

    Returns
    --------
    table : list[list]
        The list[list] object ready for make_table

    """

    if include is None:
        # using a set is fast but doesn't preserve order
        # include = set(chain(*[ld.keys() for ld in listofdicts]))

        # this approach is slower but preserves order
        include = []
        for outerkey, rowdict in data.items():
            for k in rowdict.keys():
                if k not in include:
                    include.append(k)

    table = []
    table.append(include)
    for key, innerdict in data.items():
        row = [key]
        for k in include:
            row.append(innerdict.get(k, " "))

        table.append(row)

    table[0].insert(0, outer_key_name)

    return table


def split_table_data(table_data, max_columns, first_col=None):
    """
    Splits a table so that each subtable has a certain maximum
    number of columns.

    Parameters
    -----------
    table_data : list[list]

    max_columns: int
        the maximum number of columns in the subtable
    first_col : str
        Not currently used
    """

    ncol = len(table_data[0])
    if ncol > max_columns:
        ntables = int(math.ceil((ncol - 1) / (max_columns - 1)))

        sub_tables = []
        for i in range(ntables):
            # ncol_sub = max_columns - 1

            sub_table = []
            for row in table_data:
                start = (i * (max_columns - 1)) + 1
                stop = min(start + max_columns - 1, ncol)
                partial_row = [row[0]] + row[start:stop]
                sub_table.append(partial_row)

            sub_tables.append(sub_table)

    return sub_tables


def make_table(
    table,
    minwidths=None,
    maxwidth=None,
    numdecimalplaces=None,
    numsigdigits=None,
    exclude=None,
    include=None,
    header=0,
    colsep="|",
    use_rowsep=True,
    wrap_columns=True,
):
    """
    Creates a printable string from the output of tablize.  The output
    is compliant with the ReSTructured Text table definition.

    Inputs:

    table : list of rows
        A list of rows for the table.  Each row is a list
        of the values for that row.
    minwidths : list of ints
        A minimum column width may be specified for each column.
        Default is no minimum
    maxwidth : int
        A maximum column width may be specified for all columns.
        Default is no limit on maximum
    numdigits : int
        Number of significant digits to print for float numbers

    Example:

    >>> from collections import OrderedDict
    >>> rows = []
    >>> rows.append(OrderedDict([('A',1),('B',2),('C',3)]))
    >>> rows.append(OrderedDict([('A',4),('B',5),('C',6)]))
    >>> rows.append(OrderedDict([('A','Hello'),('B',u'Goodbye'),
    ...     ('C',rows[0])]))
    >>> t = dtab.tablize(rows,rows[0].keys())
    >>> print(dtab.make_table(t,numsigdigits=6))
    +-------+---------+---------------+
    | A     | B       | C             |
    +-------+---------+---------------+
    | 1     | 2       | 3             |
    +-------+---------+---------------+
    | 4     | 5       | 6             |
    +-------+---------+---------------+
    | Hello | Goodbye | +---+---+---+ |
    |       |         | | A | B | C | |
    |       |         | +---+---+---+ |
    |       |         | | 1 | 2 | 3 | |
    |       |         | +---+---+---+ |
    +-------+---------+---------------+


    Rendered the table may look like (depening on the report style being used)

    Grid table

    +-------+---------+---------------+
    | A     | B       | C             |
    +-------+---------+---------------+
    | 1     | 2       | 3             |
    +-------+---------+---------------+
    | 4     | 5       | 6             |
    +-------+---------+---------------+
    | Hello | Goodbye | +---+---+---+ |
    |       |         | | A | B | C | |
    |       |         | +---+---+---+ |
    |       |         | | 1 | 2 | 3 | |
    |       |         | +---+---+---+ |
    +-------+---------+---------------+
"""
    table = copy(table)

    if header is None:
        pass
    elif isinstance(header, int):
        header_row = table[header]
    else:
        header_row = header
        table.insert(0, header_row)

    if include:
        exclude = set(header_row).difference(set(include))
        print(exclude)

    if exclude:
        for c in exclude:
            ind = table[0].index(c)
            if ind == 0:
                table = [row[1:] for row in table]
            elif ind == len(table[0]) - 1:
                table = [row[:-1] for row in table]
            else:
                table = [row[:ind] + row[ind + 1 :] for row in table]

    nrow = len(table)
    ncol = len(table[0])
    # print(table)
    embeddedTableKeys = None
    # perform string conversions
    for irow in range(0, nrow):
        for icol in range(0, ncol):
            val = table[irow][icol]
            # print(val)
            if isinstance(val, (list, tuple)):
                table[irow][icol] = make_table(tablize(val))[:-1]
            elif isinstance(table[irow][icol], (dict, OrderedDict)):
                # print('Embeded',str(val))
                if embeddedTableKeys is None:
                    embeddedTableKeys = list(val.keys())
                # else:
                #    embeddedTableKeys = [key.strip() for key in embeddedTableKeys]
                emtable = tablize([val], include=copy(embeddedTableKeys))
                table[irow][icol] = make_table(emtable)[:-1]
                # table[irow][icol] = make_table(tablize([val]))[:-1]
            elif isfloat(val) and numsigdigits is not None:
                table[irow][icol] = str(sigdigits(val, numsigdigits))
            elif isfloat(val) and numdecimalplaces is not None:
                #                table[irow][icol] = str(round(val, numdecimalplaces))
                fmt = "{0:." + str(numdecimalplaces) + "f}"
                table[irow][icol] = fmt.format(val)
            else:
                # print(type(table[irow][icol]))
                table[irow][icol] = str(table[irow][icol])
                if table[irow][icol].strip() == "":
                    table[irow][icol] = "\\"

    # split entries that have \n in them
    for i in range(2):
        rowsep = "rowsep"
        if i == 0:
            newtable = []
        else:
            newtable = [rowsep]
        for row in table:
            if not row:
                continue

            maxheight = max([col.count("\n") for col in row]) + 1
            if maxheight > 1:
                items = [col.split("\n") for col in row]

                for k in range(0, maxheight):
                    newrow = []
                    for icol in range(0, ncol):
                        newrow.append(tryget(items, icol, k))
                    newtable.append(newrow)

            else:
                newtable.append(row)

            newtable.append(rowsep)

        # compute column widths
        colwidths = []
        for icol in range(0, ncol):
            colwidths.append(0)
            for row in table:
                for ir in row[icol].split("\n"):
                    colwidths[-1] = max(colwidths[-1], len(ir))
            # colwidths[-1] = max([len(row[icol].split('\n')]) for row in table])

        if minwidths is not None:
            for i in range(0, len(minwidths)):
                colwidths[i] = max(colwidths[i], minwidths[i])

        if maxwidth is not None:
            for i in range(0, len(colwidths)):
                colwidths[i] = min(colwidths[i], maxwidth)

        # pad each entry
        for irow in range(0, len(newtable)):
            if type(newtable[irow]) is not str:
                for icol in range(0, ncol):
                    val = newtable[irow][icol]
                    cw = colwidths[icol]
                    len_val = len(val)
                    newtable[irow][icol] = val + (" " * (cw - len_val))

        # trim each entry
        for irow in range(0, len(newtable)):
            if type(newtable[irow]) is not str:
                for icol in range(0, ncol):
                    val = newtable[irow][icol]
                    cw = colwidths[icol]
                    len_val = len(val)
                    if len_val > cw:
                        if val.strip() == "":
                            newtable[irow][icol] = val[:cw]
                        else:
                            if wrap_columns:
                                newtable[irow][icol] = textwrap.fill(val, cw)
                            else:
                                newtable[irow][icol] = textwrap.shorten(val, cw, "...")
        table = newtable

    p = "+"
    c = "-"

    separator = p + p.join([c * (cw + 2) for cw in colwidths]) + p + "\n"
    header_separator = separator.replace("-", "=")

    fragtext = ""

    row_separator_count = 0
    for row in newtable:
        # print row
        if type(row) is str:
            if row == rowsep:
                row_separator_count += 1
                if row_separator_count == 2 and header is not None:
                    fragtext += header_separator
                else:
                    if use_rowsep:
                        fragtext += separator
        else:
            fragtext += (
                colsep + " " + (" " + colsep + " ").join(row) + " " + colsep + "\n"
            )

    return fragtext


def _test():
    keys = list("abcdefg")
    import random

    nrows = 10
    rows = []
    for i in range(nrows):
        # skip = random.randint(0,len(keys))
        row = {}
        for i, key in enumerate(keys):
            if i == len(rows):
                row[key] = {"q": 1, "r": 3}
            elif i == 0:
                row[key] = "Hello"
            else:
                row[key] = random.random()

        rows.append(row)

    # from pprint import pprint
    # pprint(rows)
    t = tablize(rows, keys)
    # print(t)

    print((make_table(t, numsigdigits=6)))

    t_split = split_table_data(t, max_columns=4)
    for subtable in t_split:
        print(make_table(subtable))


if __name__ == "__main__":

    _test()

