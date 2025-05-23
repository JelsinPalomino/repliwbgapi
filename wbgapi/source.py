'''
Access information about World Bank Databases

World Bank databases are multi-dimensional databases that at a minimun
have series, economy, and time dimensions. Concept names are not consistent
across databases, but the wbgapi module tries to insulate the user from 
these inconsistencies. Use the concepts() function to access the low-level
concept names.
'''

import wbgapi as w
from . import utils
import urllib.parse
import builtins
import re

# Concepts cached per database
_concepts = {}
_metadata_flags = {}

def get(db=None):
    '''Retrieve the record for a single database

    Arguments:
        db:         the database ID (e.g., 2=WDI). Default to the global db

    Returns:
        a database object

    Example:
        print wbgapi.source.get(2)['name']
    '''

    return w.get(_sourceurl(db), {'dataid': 'y'})

def concepts(db=None):
    '''Retrieve the concepts for the specified database. This functions also implements
    support for alternate dimension names for the 3 primary dimensions

    Arguments:
        db:         the databases ID (e.g., 2=WDI). Default to the global database

    Returns:
        a dictionary of concepts: keys are URL friendly
    
    Example:
        for k,v in wbgapi.source.concepts(2).items():
            print(k, v['key'], v['value'])
    '''

    global _concepts

    if db is None:
        db = w.db

    db = int(db)
    c = _concepts.get(db)
    if c is not None:
        return c
    
    url = 'sources/{}/concepts'.format(db)
    c = {}
    for row in w.fetch(url, concepts=True):
        key = urllib.parse.quote(row['id']).lower()
        # there's currently an extra space at the end of "receiving countries" - we support a trimmed version
        # in the event this gets quietly fixed someday
        if key in ['country', 'admin%20region', 'states', 'provinces', 'receiving%20countries%20', 'receiving%20countries']:
            id = 'economy'
        elif key in ['year']:
            id =  'time'
        elif key in ['indicator']:
            id = 'series'
        else:
            id = key

        id = re.sub(r'[\-\.,:!]', '_', id) # neutralize special characters
        c[id] = {'key': key, 'value': row['value']}

    _concepts[db] = c
    return c

def features(concept, id="all", db=None):
    '''Retrieve features for the specified database. This is an internal function
    called by list() in other modules.

    Arguments:
        concept:    the concept to retrieve (e.g., 'series')

        id:         object identifiers to retrieve; must be a well-formed string

        db:         the database to access (e.g., 2=WDI). Default uses the global database

    Returns:
        a generator object

    Example:
        for elem in wbgapi.source.features('time'):
            print(elem['id'], elem['value'])
    '''

    if db is None:
        db = w.db

    if not id:
        # e.g., '' or []
        return []

    return w.refetch('source/{source}/{concept}/{id}', ['id'], source=db, concept=concepts(db)[concept]['key'], id=id)

def has_metadata(db=None):
    '''Test whether the specified database is expected to have metadata, as determined 
    by the database record returned from the API.

    Arguments:
        db:         the database to query. Pass None to reference the global database

    Returns:
        Boolean
    '''

    if db is None:
        db = w.db

    global _metadata_flags
    m = _metadata_flags.get(db)
    if m is None:
        src = get(db)
        m = src.get('metadataavailability', '').upper() == 'Y'
        _metadata_flags[db] = m

    return m

def _sourceurl(db):
    '''Internal function: returns the URL for fetching database objects
    '''

    if db is None:
        db = w.db

    return 'sources/{}'.format(db)