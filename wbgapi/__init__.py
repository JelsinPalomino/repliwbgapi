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
enpoint = 'https://api.worldbank.org/v2'
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