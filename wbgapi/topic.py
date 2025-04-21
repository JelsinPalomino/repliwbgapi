'''Access information about World Bank topics. This works best with the WDI (source=2)
but should also work okay with other databases
'''

import wbgapi as w
from . import utils
import builtins

def members(id):
    '''Return a set of series identifiers that are members of the specified topic

    Arguments:
        id:         a topic identifier

    Returns:
        a set object of series identifiers
    '''

    e = set()
    for row in w.fetch('topic/{}/indicator'.format(w.queryParam(id)), {'source': w.db}):
        e.add(row['id'])

    return e