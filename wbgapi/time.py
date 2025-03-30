
'''Access information about the database's time dimension

The temporal concepts in most World Bank databases are named 'time' but in
some cases are named 'year' or something else. Keys for time elements are
not always consistent across databases. The wbgapi module tries to insulate
the user from most of these inconsistencies. The module will also generally
accept both numeric values and element keys as parameters where this is possible, 
e.g., 'YR2015,' '2015' and 2015 are acceptable.
'''

import wbgapi as w 
from . import utils
import builtins

# This is an array of reverse value lookup tables
_time_values = {}


def periods(db=None):
    '''Returns a dict of time features keyed by value for the current database. This is
    primarily used internally to recognize both values and keys as equivalent
    '''
    global _time_values

    if db is None:
        db = w.db

    v = _time_values.get(db)
    if v is None:
        v = {}
        for row in w.source.features('time', 'all', db=db):
            v[row['value']] = row['id']

        _time_values[db] = v

    return v