#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
from pysmi.parser.smi import parserFactory
from pysmi.parser.dialect import smiV1Relaxed

# compatibility stub
SmiV1CompatParser = parserFactory(**smiV1Relaxed)
SmiStarParser = SmiV1CompatParser
