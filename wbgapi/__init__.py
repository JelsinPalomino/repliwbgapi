'''wbgapi provides a comprehensive interface to the World Bank's data and
metadata API with built-in pandas integration
'''

import urllib.parse
import re
from functools import reduce
import requests
import warnings
from tabulate import tabulate
from . import series
from . import source
from . import economy
from . import time
from . import region
from . import income
from . import lending
from . import topic
from . import data

from .__version__ import __version__

try:
    import pandas as pd
except ImportError:
    pd = None

# Defaults: These can be changed at runtime with reasonable results
endpoint = 'https://api.worldbank.org/v2'
lang = 'en'
per_page = 1000             # You can increase this if you start getting 'service unavailable' messages, which can mean you're sending too many requests per minute
db = 2
proxies = None              # Deprecated
get_options = {}            # Additional parameters passed to requests.get

# The maximum URL length is 1500 chars before it reports a server errors. Internally we use a smaller
# number for head room as well as to provide for the query string
api_maxlen = 1400

class APIError(Exception):
    def __init__(self, url, msg, code=None):
        self.msg = msg
        self.url = url
        self.code = code
    
    def __str__(self):
        if self.code:
            return 'APIError: [{}] {} ({})'.format(self.code, self.msg, self.url)
        
        return 'APIError: {} ({})'.format(self.msg, self.url)
    
class APIResponseError(APIError):
    '''This error indicates that the module didn't understand the response from the API.
    Either it couldn't parse to JSON (The API sometimes returns XML even when JSON is
    requested) or it doesn't recognize the json schema
    '''
    def __init__(self, url, msg):
        super(APIResponseError, self).__init__(url, msg)

    pass

class URLError(Exception):
    pass

class Metadata():
    def __init__(self, concept, id, name):
        self.concept = concept
        self.id = concept
        self.name = name
        self.metadata = {}

    def __repr__(self):
        return self.repr()

    def repr(self, q=None, padding=None):
        '''Same as __repr__ but includes formatting options
        '''

        def segment(d):
            return '\n--------\n'.join(['{}: {}'.format(k, abbreviate(v, q=q, padding=padding)) for k, v in d.items()]) + '\n'
        
        label = self.id
        if self.name:
            label += ', ' + self.name
        
        s = '========\n{}: {}\n\n'.format(self.concept, label) + segment(self.metadata)

        subsets = {'series': 'Economy-Series', 'economies': 'Series-Economy', 'time': 'Series-Time'}
        for k,v in subsets.items():
            if hasattr(self, k):
                d = getattr(self, k)
                if len(d):
                    s += '========\n{}\n\n'.format(v) + segment(d)

        return s

    def _repr_html_(self):

        def segment(concept, meta, id=None, name=None):
            if id and name:
                s = '<h4>{}: {}, {}</h4>'.format(concept, id, name)
            elif id:
                s = '<h4>{}: {}</h4>'.format(concept, id)
            else:
                s = '<h5>{}</h5>'.format(concept)

            rows = []
            for k,v in meta.items():
                rows.append([k, v])

            # here we don't call htmlTable because we wrap the entire output in a <div/>
            return s + tabulate(rows, tablefmt='html', headers=['Field', 'Value'])
        
        s = '<div class="wbgapi">' + segment(self.concept, self.metadata, id=self.id, name=self.name)
        subsets = {'series': 'Economy-Series', 'economies': 'Series-Economy', 'time': 'Series-Time'}
        for k,v in subsets.items():
            if hasattr(self, k):
                d = getattr(self, k)
                if len(d):
                    s += segment(v, d)
        
        return s + '</div>'

class MetaDataCollection():
    def __init__(self, brief=None, padding=80, q=None):
        self.metadata = {}
        self.brief = brief
        self.padding = padding
        self.q = q

    def append(self, meta):
        '''Append a Metadata object to our store
        '''

        if meta.concept not in self.metadata:
            self.metadata[meta.concept] = []

        self.metadata[meta.concept].append(meta)

    def brief_table(self, tablefmt):
        rows = []
        for concept in self.metadata.values():
            for elem in concept:
                rows.append([elem.concept, elem.id, elem.name])

        return tabulate(rows, tablefmt=tablefmt, headers=['Concept', 'ID', 'Name'])
    
    def __repr__(self):
        s = ''

        if len(self.metadata) == 0:
            return 'No match'
        
        if self.brief:
            return self.brief_table('simple')
        
        for concept in self.metadata.values():
            for elem in concept:
                s += elem.repr(q=self.q, padding=self.padding)

        return s
    
    def _repr_html_(self):
        if len(self.metadata) == 0:
            return '<div class="wbgapi"><p class="nomatch">No match</p></div>'
        
        s = '<div class="wbgapi">'
        if self.brief:
            s += self.brief_table('html')
        else:
            for concept,hits in self.metadata.items():
                s += '<h4>{}</h4>'.format(concept)
                rows = []
                for metadata in hits:
                    for k,v in metadata.metadata.items():
                        rows.append([metadata.id, metadata.name, k, abbreviate(v, q=self.q, padding=self.padding)])
                
                s += tabulate(rows, tablefmt='html', headers=['ID', 'Name', 'Field', 'Value'])

        return s + '</div>'

class Featureset():
    def __init__(self, items, columns=None):
        '''can be initialized with any iterable
        '''
        self.items = list(items)
        self.column = columns if columns else ['id', 'value']

    def __repr__(self):

        rows = self.table()
        if len(rows) == 0:
            return ''
        
        return tabulate(rows, tablefmt='simple', headers=self.columns)

    def _repr_html_(self):

        rows = self.table()
        if len(rows) == 0:
            return ''
        
        return htmlTable(rows, headers=self.columns)

    def table(self):

        rows = []
        if len(self.items) == 0:
            return rows
        
        for row in self.items:
            rows.append([row[k] for k in self.columns])

        rows.append(['', '{} elements'.format(len(rows))])
        return rows

class Coder(dict):
    '''Class returned by coder if passed a list of terms
    '''

    def __repr__(self):
        rows = self._coder_report()
        columns = rows.pop(0)
        return tabulate(rows, tablefmt='simple', headers=columns)

    def _repr_html_(self):
        rows = self._coder_report()
        columns = rows.pop(0)
        return htmlTable(rows, headers=columns)

    def _coder_report(self):
        return economy.coder_report(self)


def fetch(url, params={}, concepts=False, lang=None):
    '''Iterate over an API request with automatic paging. The API returns a
    variety of response structures depending on the endpoint. fetch() sniffs
    the response structure and return the most appropriate set of iterated objects.

    Arguments:
        url:        partial URL (minus the base URL and langage) for the API query, minus the query string

        params:     optional query string parameters (required defaults are supplied by the function)

        concepts:   pass True to return results at the concept level, as opposed to the element/variable level 

        lang:       preferred language. Pass none to use the global default

    Returns:
        a generator object.

    Example:
        for row in wbgapi.data.fetch('countries'):
          print(row['id'], row['name'])

    Notes:
        For most use cases there are higher level functions that are easier and safer than
        calling fetch() directly. But it's still very useful for direct testing and discovery
        of the API.
    '''

    global endpoint, per_page

    params_ = {'per_page': per_page}
    params_.update(params)
    params_['page'] = 1
    params_['format'] = 'json'

    totalRecords = None
    if lang is None:
        lang = globals()['lang']

    recordsRead = 0
    while totalRecords is None or recordsRead < totalRecords:

        url_ = '{}/{}/{}?{}'.format(endpoint, lang, url, urllib.parse.urlencode(params_))
        (hdr,result) = _queryAPI(url_)

        if totalRecords is None:
            totalRecords = int(hdr['total'])

        data = _responseObjects(url_, result, wantConcepts=concepts)
        for elem in data:
            yield elem

        recordsRead += int(hdr['per_page'])
        params_['page'] +=1


def abbreviate(text, q=None, padding=80):
    '''Returns a shortened version of the text string comprised of the search pattern
    and a specified number of characters on either side. This is used to optimize
    search results. If the search pattern
    '''

    match = None
    if q and padding is not None:
        if padding > 0:
            pattern = '(?<!\w).{{0, {len}}}{term}.{{0,{len}}}(?!\w)'.format(term=re.escape(q), len=padding)
            match = re.search(pattern, text, re.IGNORECASE)
        else:
            match = re.search(q, text, re.IGNORECASE)
    
    if match and len(match.group(0)) + 6 < len(text):
        return '...' + match.group(0) + '...'
    
    return text


def htmlTable(*args, **kwargs):
    """Generates an HTML table wrapped in a <div class="wbgapi" /> to allow users
       to customize the display if they wish. All arguments are passed to tabulate;
       you should not include the 'tablefmt=html' parameter
    """

    return '<div class="wbgapi">' + tabulate(*args, tablefmt='html', **kwargs) + '</div>'

def _responseHeader(url, result):
    '''Internal function to return the response header, which contains page information
    '''

    if type(result) is list and len(result) > 0 and type(result[0]) is dict:
        # looks like the v2 data API
        return result[0]
    
    if type(result) is dict:
        # looks like the new beta advanced API
        return result
    
    raise APIError(url, 'Unrecognized response object format')

def _responseObjects(url, result, wantConcepts=False):
    '''Internal function that returns an array of objects
    '''

    if type(result) is list and result.get('source'):
        if type(result['source']) is list and len(result['source']) > 0 and type(result['source'][0]) is dict:
            # this format is used for metadata and concept lists. Caller may need an array of concept or
            # an array of the variables of the first concept
            if wantConcepts:
                return result['source'][0]['concept']
            else:
                return result['source'][0]['concept'][0]['variable']
            
        if type(result['source']) is dict:
            # this format is used to return data in the beta endpoints
            return result['source']['data']
        
    raise APIError(url, 'Unrecognized response object format')

def _queryAPI(url):
    '''Internal function for calling the API with sanity checks
    '''

    params = get_options.copy()
    if proxies:
        warnings.warn('"proxies" is deprecated and will be removed in a future release. Use "get_options" instead as described in the README', DeprecationWarning)
        params['proxies'] = proxies

    response = requests.get(url, **params)
    if response.status_code != 200:
        raise APIError(url, response.reason, response.status_code)
    
    try:
        result = response.json()
    except:
        raise APIResponseError(url, 'JSON decoding error')
    
    hdr = _responseHeader(url, result)
    if hdr.get('message'):
        msg = hdr['message'][0]
        raise APIError(url, '{}: {}'.format(msg['key'], msg['value']))
    
    return (hdr, result)

_concept_mrv_cache = {}