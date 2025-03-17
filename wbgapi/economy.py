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