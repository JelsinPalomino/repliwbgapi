'''Access information about the economies in a database.

Economies can include countries, aggregates, and sub-national regions. The
economy dimension in a World Bank database can go by various concept names,
but the wbgapi module tries to insulate the user from most of these
inconsistencies.

Each database in the World Bank API has its own list of economies. However,
databases that are country-based share a common set of classifications for regions,
income and lending groups. The wbgapi tries to integrate these by including 
classifications in economy records where possible. Obviously these won't apply
to databases that don't adhere to the country-level coding standars.
'''

import wbgapi as w

from .economy_coder import coder, coder_report

import wbgapi as w
from . import economy_metadata as metadata
from . import utils
from .economy_coder import coder, coder_report
from functools import reduce
import builtins
try:
    import numpy as np
    import pandas as pd
except ImportError:
    np = None
    pd = None

_aggs = None
_empty_meta_value = '' # value used to for null string economy metadata

# a dict of ISO2 code equivalents, if we ever need this
_iso2Codes = {}

# a dictionary of region, admin, lendingType and incomeLevel classifications per country. Also lon and lat
_class_data = None

# translated names of regions and cities. This is keyed by language and code
_localized_metadata = {}

def list(id='all', q=None, labels=False, skipAggs=False, db=None):
    '''Return a list of economies in the current database

    Arguments:
        id:             an economy identifier or list-like

        q:              search string (on economy name)

        labels:         return both codes and labels for regions, income and lending groups

        skipAggs:       skip aggregates

        db:             database: pass None to access the global database

    Returns:
        a generator object
    
    Example:
        for elem in wbgapi.economy.list():
            print(elem['id'], elem[' value'])
    '''

    q, _ = utils.qget(q)

    update_caches()
    for row in w.source.features('economy', w.queryParam(id, 'economy', db=db), db=db):
        _build(row, labels)
        if (skipAggs == False or row['aggregate'] == False) and utils.qmatch(q, row['value']):
            yield row



def _build(row, labels=False):
    '''Utility function to build an economy record from API and cached data
    '''

    global _class_data, _localized_metadata

    cd = _class_data.get(row['id'])
    if cd is None:
        cd = _class_data.get('___')
    if cd:
        row.update(cd)
        row['capitalCity'] = _localized_metadata[w.lang].get('capitalCity:'+row['id'])
        if labels:
            for key in ['region', 'adminregion', 'lendingType', 'incomeLevel']:
                row[key] = {'id': row[key], 'value': _localized_metadata[w.lang].get(row[key])}


def aggregate():
    '''Returns a set object with both the 2-character and 3-character codes
    of aggregate econommies. These are obtained from the API and then cached.
    '''

    global _aggs

    update_caches()
    return _aggs

def update_caches():
    '''Update internal metadata caches. This needs to be called prior to
    any fetch from an economy endpoint
    '''

    global _localized_metadata, _iso2Codes, _class_data, _aggs

    if _localized_metadata.get(w.lang):
        # nothing to do
        return
    
    # update translation data here except city names
    db = {}
    for elem in ['region', 'incomelevel', 'lendingtype']:
        for row in w.fetch(elem):
            if 'name' in row:
                db[row['code']] = row['name'].strip()
            else:
                db[row['id']] = row['value'].strip()
            
            _iso2Codes[row['id']] = row['iso2code']

    _localized_metadata[w.lang] = db

    url = 'country/all'
    if type(_class_data) is not dict:
        # Initialize objects
        _class_data = {}
        _aggs = set()

        # Here, we update codes and city translations simultaneously
        for row in w.fetch(url):
            _iso2Codes[row['id']] = row['iso2Code']
            _localized_metadata[w.lang]['capitalCity:'+row['id']] = (row['capitalCity'].strip() or _empty_meta_value)

            db = {'aggregate': row['region']['id'] == 'NA'}
            for key in ['longitude', 'latitude']:
                db[key] = float(row[key]) if len(row[key]) else None

            for key in ['region', 'adminregion', 'lendingType', 'incomeLevel']:
                db[key] = _empty_meta_value if db['aggregate'] else (row[key]['id'] or _empty_meta_value) 

            _class_data[row['id']] = db
            if db['aggregate']:
                _aggs.add(row['id'])
                _aggs.add(row['iso2Code'])

        # add one dummy that we can match to unrecognized economy codes
        db = _class_data['USA']
        _class_data['___'] = {k:None for k in db.keys()}

    else:
        # else, just update city codes
        for row in w.fetch(url):
            _localized_metadata[w.lang]['capitalCity:'+row['id']] = (row['capitalCity'].strip() or _empty_meta_value)