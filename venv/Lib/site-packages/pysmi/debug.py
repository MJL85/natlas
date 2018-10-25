#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import logging
from pysmi import error
from pysmi import __version__

flagNone = 0x0000
flagSearcher = 0x0001
flagReader = 0x0002
flagLexer = 0x0004
flagParser = 0x0008
flagGrammar = 0x0010
flagCodegen = 0x0020
flagWriter = 0x0040
flagCompiler = 0x0080
flagBorrower = 0x0100
flagAll = 0xffff

flagMap = {
    'searcher': flagSearcher,
    'reader': flagReader,
    'lexer': flagLexer,
    'parser': flagParser,
    'grammar': flagGrammar,
    'codegen': flagCodegen,
    'writer': flagWriter,
    'compiler': flagCompiler,
    'borrower': flagBorrower,
    'all': flagAll
}


class Printer(object):
    def __init__(self, logger=None, handler=None, formatter=None):
        if logger is None:
            logger = logging.getLogger('pysmi')

        logger.setLevel(logging.DEBUG)

        if handler is None:
            handler = logging.StreamHandler()

        if formatter is None:
            formatter = logging.Formatter('%(asctime)s %(name)s: %(message)s')

        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)

        logger.addHandler(handler)

        self.__logger = logger

    def __call__(self, msg):
        self.__logger.debug(msg)

    def __str__(self):
        return '<python built-in logging>'

    def getCurrentLogger(self):
        return self.__logger


if hasattr(logging, 'NullHandler'):
    NullHandler = logging.NullHandler
else:
    # Python 2.6 and older
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass


class Debug(object):
    defaultPrinter = None

    def __init__(self, *flags, **options):
        self._flags = flagNone
        if options.get('printer') is not None:
            self._printer = options.get('printer')

        elif self.defaultPrinter is not None:
            self._printer = self.defaultPrinter

        else:
            if 'loggerName' in options:
                # route our logs to parent logger
                self._printer = Printer(
                    logger=logging.getLogger(options['loggerName']),
                    handler=NullHandler()
                )
            else:
                self._printer = Printer()

        self('running pysmi version %s' % __version__)

        for flag in flags:
            inverse = flag and flag[0] in ('!', '~')

            if inverse:
                flag = flag[1:]

            try:
                if inverse:
                    self._flags &= ~flagMap[flag]
                else:
                    self._flags |= flagMap[flag]

            except KeyError:
                raise error.PySmiError('bad debug flag %s' % flag)

            self('debug category \'%s\' %s' % (flag, inverse and 'disabled' or 'enabled'))

    def __str__(self):
        return 'logger %s, flags %x' % (self._printer, self._flags)

    def __call__(self, msg):
        self._printer(msg)

    def __and__(self, flag):
        return self._flags & flag

    def __rand__(self, flag):
        return flag & self._flags

    def getCurrentPrinter(self):
        return self._printer

    def getCurrentLogger(self):
        return self._printer and self._printer.getCurrentLogger() or None


# This will yield false from bitwise and with a flag, and save
# on unnecessary calls
logger = 0


def setLogger(l):
    global logger
    logger = l
