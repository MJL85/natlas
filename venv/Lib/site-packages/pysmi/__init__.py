# http://www.python.org/dev/peps/pep-0396/
__version__ = '0.3.2'

import sys

if sys.version_info[:2] < (2, 4):
    raise RuntimeError('PySMI requires Python 2.4 or later')
