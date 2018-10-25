#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
from pysmi.parser.smi import parserFactory
from pysmi.parser.dialect import smiV1

# compatibility stub
SmiV1Parser = parserFactory(**smiV1)
