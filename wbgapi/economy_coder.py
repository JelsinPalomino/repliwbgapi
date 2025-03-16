
'''Translates country names into country codes, based on common
spellings and conventions.
'''

import wbgapi as w
import yaml
import os
import re

try:
    import pandas as pd
except ImportError:
    pd = None

_lookup_data = None
_coder_names = None

def coder(name, summary=False, debug=None):
    '''Return the country code for a given country name, based on common spellings and convertions.
    This function is intended to make it easier to convert country names to ISO3 codes.

    This feature is English-only and still in development. You can extend the matching algorithm
    by editing the `lookup-data.yaml` file.

    Arguments:

        name: a country name as a string, or an iterable object of name strings

        summary: just return anomalies (name that couldn't be matched or that don't match the WBG name).

        debug: a list of ISO codes of which to print debug output
    
    Returns:
        If `name` is a string then the function returns the corresponding ISO3 code, or None if the code
        can't be ascertained.

        If `name` is a pandas Series, the function returns a pandas Series with the same index. Note that
        if the summary is True then the function always returns a Coder object.

        If `name` is any other iterable object, the function returns a Coder object. Coder is a dict subclass
        with some sugar to produce a nice command line (or jupyter notebook) report. Country names that
        cannot be coded have a value of None.

        Note that if summary is True then the function ALWAYS returns a Coder object.

    Examples:
        print(wbgapi.economy_coder.lookup('Eswatini')) # prints 'SWZ'

        print(wbgapi.economy_coder.lookup('Swaziland')) # prints 'SWZ'

        print(wbgapi.economy_coder.lookup(['Canada', 'Toronto'])) # prints {'Canada'}
    '''
    global _lookup_data, _coder_names

    def prepare(s, clean=False, magicRegex=False):

        s = s.lower()
        if clean:
            # Should be False if the string is regex-capable

            # this next trick is strips the container parentheses from "... (US|UK)"
            # and leaves the inner part. Need this for the Virgin Islands since,
            # before we remove parenthetical text entirely
            s = re.sub(r'\((u\.?s\.?|u\.?k\.?)\)', lambda t: t.group(1).replace('.',''), s)

            s = re.sub(r'\s*\(.*\)', '', s)         # remove parenthetical text
            s = s.replace("'", '')                  # remove apostrophes
            s = re.sub(r'[^\w&]', ' ', s)           # remove remaining superflous chars to spaces

        s = s.strip()

        if magicRegex:
            # converts 'and' to (and|&), 'st' to (st|saint)
            s = re.sub(r'\band\b', r'(and|\&)', s)
            s = re.sub(r'\bst\b', r'(st|saint)', s)
            s = re.sub(r'\s+', r'\\s+', s)

        return s
    
    if _lookup_data is None:
        _lookup_data = []
        _coder_names = {}
        user_data = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), 'lookup-data.yaml'), 'r'))
        