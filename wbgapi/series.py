'''Access information about series in a database
'''

import wbgapi as w
from . import series_metadata as metadata
from . import utils

def list(id='all', q=None, topic=None, db=None):
    '''Return a list of series elements in the current database

    Arguments:
        id:                 a series identifier (i.e., CETS code) or list-like

        q:                  search string (on series name)

        topic:              topic ID or list-like

        db:                 database; pass None to access the global database

    Returns:
        a generator object

    Example:
        for elem in wbgapi.series.list():
            print(elem['id'], elem['value'])
    '''
    if (topic):
        topics = w.topic.members(topic)
        if type(id) is str and id != 'all':
            # if id is also specified, then calculate the intersection of that and the series from topics
            id = set(w.queryParam(id, 'series', db=db).split(';'))
            id &= topics
        else:
            id = topics
    
    q,fullSearch = utils.qget(q)

    for row in w.source.features('series', w.queryParam(id, 'series', db=db), db=db):
        if utils.qmatch(q, row['value'], fullSearch):
            yield row
