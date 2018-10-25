#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import sys
import re
import ply.lex as lex
from pysmi.lexer.base import AbstractLexer
from pysmi import error
from pysmi import debug

UNSIGNED32_MAX = 4294967295
UNSIGNED64_MAX = 18446744073709551615
LEX_VERSION = [int(x) for x in lex.__version__.split('.')]

# Do not overload single lexer methods - overload all or none of them!
# noinspection PySingleQuotedDocstring,PyMethodMayBeStatic,PyIncorrectDocstring
class SmiV2Lexer(AbstractLexer):
    reserved_words = [
        'ACCESS', 'AGENT-CAPABILITIES', 'APPLICATION', 'AUGMENTS', 'BEGIN', 'BITS',
        'CONTACT-INFO', 'CREATION-REQUIRES', 'Counter', 'Counter32', 'Counter64',
        'DEFINITIONS', 'DEFVAL', 'DESCRIPTION', 'DISPLAY-HINT', 'END', 'ENTERPRISE',
        'EXTENDS', 'FROM', 'GROUP', 'Gauge', 'Gauge32', 'IDENTIFIER', 'IMPLICIT',
        'IMPLIED', 'IMPORTS', 'INCLUDES', 'INDEX', 'INSTALL-ERRORS', 'INTEGER',
        'Integer32', 'IpAddress', 'LAST-UPDATED', 'MANDATORY-GROUPS',
        'MAX-ACCESS', 'MIN-ACCESS', 'MODULE', 'MODULE-COMPLIANCE',
        'MODULE-IDENTITY', 'NOTIFICATION-GROUP', 'NOTIFICATION-TYPE',
        'NOTIFICATIONS', 'OBJECT', 'OBJECT-GROUP', 'OBJECT-IDENTITY', 'OBJECT-TYPE',
        'OBJECTS', 'OCTET', 'OF', 'ORGANIZATION', 'Opaque', 'PIB-ACCESS',
        'PIB-DEFINITIONS', 'PIB-INDEX', 'PIB-MIN-ACCESS', 'PIB-REFERENCES',
        'PIB-TAG', 'POLICY-ACCESS', 'PRODUCT-RELEASE', 'REFERENCE', 'REVISION',
        'SEQUENCE', 'SIZE', 'STATUS', 'STRING', 'SUBJECT-CATEGORIES', 'SUPPORTS',
        'SYNTAX', 'TEXTUAL-CONVENTION', 'TimeTicks', 'TRAP-TYPE', 'UNIQUENESS',
        'UNITS', 'UNIVERSAL', 'Unsigned32', 'VALUE', 'VARIABLES',
        'VARIATION', 'WRITE-SYNTAX'
    ]

    reserved = {}
    for w in reserved_words:
        reserved[w] = w.replace('-', '_').upper()
        # hack to support SMIv1
        if w == 'Counter':
            reserved[w] = 'COUNTER32'
        elif w == 'Gauge':
            reserved[w] = 'GAUGE32'

    forbidden_words = [
        'ABSENT', 'ANY', 'BIT', 'BOOLEAN', 'BY', 'COMPONENT', 'COMPONENTS',
        'DEFAULT', 'DEFINED', 'ENUMERATED', 'EXPLICIT', 'EXTERNAL', 'FALSE', 'MAX',
        'MIN', 'MINUS-INFINITY', 'NULL', 'OPTIONAL', 'PLUS-INFINITY', 'PRESENT',
        'PRIVATE', 'REAL', 'SET', 'TAGS', 'TRUE', 'WITH'
    ]

    # Token names required!
    tokens = list(set([
                          'BIN_STRING',
                          'CHOICE',
                          'COLON_COLON_EQUAL',
                          'DOT_DOT',
                          'EXPORTS',
                          'HEX_STRING',
                          'LOWERCASE_IDENTIFIER',
                          'MACRO',
                          'NEGATIVENUMBER',
                          'NEGATIVENUMBER64',
                          'NUMBER',
                          'NUMBER64',
                          'QUOTED_STRING',
                          'UPPERCASE_IDENTIFIER',
                      ] + list(reserved.values())
                      ))

    states = (
        ('macro', 'exclusive'),
        ('choice', 'exclusive'),
        ('exports', 'exclusive'),
        ('comment', 'exclusive'),
    )

    literals = '[]{}():;,-.|'

    t_DOT_DOT = r'\.\.'
    t_COLON_COLON_EQUAL = r'::='

    t_ignore = ' \t'

    def __init__(self, tempdir=''):
        self._tempdir = tempdir
        self.lexer = None
        self.reset()

    def reset(self):
        if LEX_VERSION < [3, 0]:
            self.lexer = lex.lex(module=self,
                                 reflags=re.DOTALL,
                                 outputdir=self._tempdir,
                                 debug=False)
        else:
            if debug.logger & debug.flagLexer:
                logger = debug.logger.getCurrentLogger()
            else:
                logger = lex.NullLogger()

            if debug.logger & debug.flagGrammar:
                debuglogger = debug.logger.getCurrentLogger()
            else:
                debuglogger = None

            self.lexer = lex.lex(module=self,
                                 reflags=re.DOTALL,
                                 outputdir=self._tempdir,
                                 debuglog=debuglogger,
                                 errorlog=logger)

    def t_newline(self, t):
        r'\r\n|\n|\r'
        t.lexer.lineno += 1

    # Skipping MACRO
    def t_MACRO(self, t):
        r'MACRO'
        t.lexer.begin('macro')
        return t

    def t_macro_newline(self, t):
        r'\r\n|\n|\r'
        t.lexer.lineno += 1

    def t_macro_END(self, t):
        r'END'
        t.lexer.begin('INITIAL')
        return t

    def t_macro_body(self, t):
        r'.+?(?=END)'
        pass

    # Skipping EXPORTS
    def t_EXPORTS(self, t):
        r'EXPORTS'
        t.lexer.begin('exports')
        return t

    def t_exports_newline(self, t):
        r'\r\n|\n|\r'
        t.lexer.lineno += 1

    def t_exports_end(self, t):
        r';'
        t.lexer.begin('INITIAL')

    def t_exports_body(self, t):
        r'[^;]+'
        pass

    # Skipping CHOICE
    def t_CHOICE(self, t):
        r'CHOICE'
        t.lexer.begin('choice')
        return t

    def t_choice_newline(self, t):
        r'\r\n|\n|\r'
        t.lexer.lineno += 1

    def t_choice_end(self, t):
        r'\}'
        t.lexer.begin('INITIAL')

    def t_choice_body(self, t):
        r'[^\}]+'
        pass

    # Comment handling
    def t_begin_comment(self, t):
        r'--'
        t.lexer.begin('comment')

    def t_comment_newline(self, t):
        r'\r\n|\n|\r'
        t.lexer.lineno += 1
        t.lexer.begin('INITIAL')

    #  def t_comment_end(self, t):
    #    r'--'
    #    t.lexer.begin('INITIAL')

    def t_comment_body(self, t):
        r'[^\r\n]+'
        pass

    def t_UPPERCASE_IDENTIFIER(self, t):
        r'[A-Z][-a-zA-z0-9]*'
        if t.value in self.forbidden_words:
            raise error.PySmiLexerError("%s is forbidden" % t.value, lineno=t.lineno)

        if t.value[-1] == '-':
            raise error.PySmiLexerError("Identifier should not end with '-': %s" % t.value, lineno=t.lineno)

        t.type = self.reserved.get(t.value, 'UPPERCASE_IDENTIFIER')

        return t

    def t_LOWERCASE_IDENTIFIER(self, t):
        r'[0-9]*[a-z][-a-zA-z0-9]*'
        if t.value[-1] == '-':
            raise error.PySmiLexerError("Identifier should not end with '-': %s" % t.value, lineno=t.lineno)
        return t

    def t_NUMBER(self, t):
        r'-?[0-9]+'
        t.value = int(t.value)
        neg = 0
        if t.value < 0:
            neg = 1

        val = abs(t.value)

        if val <= UNSIGNED32_MAX:
            if neg:
                t.type = 'NEGATIVENUMBER'

        elif val <= UNSIGNED64_MAX:
            if neg:
                t.type = 'NEGATIVENUMBER64'
            else:
                t.type = 'NUMBER64'

        else:
            raise error.PySmiLexerError("Number %s is too big" % t.value, lineno=t.lineno)

        return t

    def t_BIN_STRING(self, t):
        r'\'[01]*\'[bB]'
        value = t.value[1:-2]
        while value and value[0] == '0' and len(value) % 8:
            value = value[1:]
        # XXX raise in strict mode
        #    if len(value) % 8:
        #      raise error.PySmiLexerError("Number of 0s and 1s have to divide by 8 in binary string %s" % t.value, lineno=t.lineno)
        return t

    def t_HEX_STRING(self, t):
        r'\'[0-9a-fA-F]*\'[hH]'
        value = t.value[1:-2]
        while value and value[0] == '0' and len(value) % 2:
            value = value[1:]
        # XXX raise in strict mode
        #    if len(value) % 2:
        #      raise error.PySmiLexerError("Number of symbols have to be even in hex string %s" % t.value, lineno=t.lineno)
        return t

    def t_QUOTED_STRING(self, t):
        r'\"[^\"]*\"'
        t.lexer.lineno += len(re.findall(r'\r\n|\n|\r', t.value))
        return t

    def t_error(self, t):
        raise error.PySmiLexerError(
            "Illegal character '%s', %s characters left unparsed at this stage" % (t.value[0], len(t.value) - 1),
            lineno=t.lineno)
        # t.lexer.skip(1)


class SupportSmiV1Keywords(object):
    @staticmethod
    def reserved():
        reserved_words = [
            'ACCESS', 'AGENT-CAPABILITIES', 'APPLICATION', 'AUGMENTS', 'BEGIN', 'BITS',
            'CONTACT-INFO', 'CREATION-REQUIRES', 'Counter', 'Counter32', 'Counter64',
            'DEFINITIONS', 'DEFVAL', 'DESCRIPTION', 'DISPLAY-HINT', 'END', 'ENTERPRISE',
            'EXTENDS', 'FROM', 'GROUP', 'Gauge', 'Gauge32', 'IDENTIFIER', 'IMPLICIT',
            'IMPLIED', 'IMPORTS', 'INCLUDES', 'INDEX', 'INSTALL-ERRORS', 'INTEGER',
            'Integer32', 'IpAddress', 'LAST-UPDATED', 'MANDATORY-GROUPS',
            'MAX-ACCESS', 'MIN-ACCESS', 'MODULE', 'MODULE-COMPLIANCE', 'MAX',
            'MODULE-IDENTITY', 'NetworkAddress', 'NOTIFICATION-GROUP',
            'NOTIFICATION-TYPE', 'NOTIFICATIONS', 'OBJECT', 'OBJECT-GROUP',
            'OBJECT-IDENTITY', 'OBJECT-TYPE', 'OBJECTS', 'OCTET', 'OF', 'ORGANIZATION',
            'Opaque', 'PIB-ACCESS', 'PIB-DEFINITIONS', 'PIB-INDEX', 'PIB-MIN-ACCESS',
            'PIB-REFERENCES', 'PIB-TAG', 'POLICY-ACCESS', 'PRODUCT-RELEASE',
            'REFERENCE', 'REVISION', 'SEQUENCE', 'SIZE', 'STATUS', 'STRING',
            'SUBJECT-CATEGORIES', 'SUPPORTS', 'SYNTAX', 'TEXTUAL-CONVENTION',
            'TimeTicks', 'TRAP-TYPE', 'UNIQUENESS', 'UNITS', 'UNIVERSAL', 'Unsigned32',
            'VALUE', 'VARIABLES', 'VARIATION', 'WRITE-SYNTAX'
        ]

        reserved = {}
        for w in reserved_words:
            reserved[w] = w.replace('-', '_').upper()
            # hack to support SMIv1
            if w == 'Counter':
                reserved[w] = 'COUNTER32'
            elif w == 'Gauge':
                reserved[w] = 'GAUGE32'

        return reserved

    @staticmethod
    def forbidden_words():
        return [
            'ABSENT', 'ANY', 'BIT', 'BOOLEAN', 'BY', 'COMPONENT', 'COMPONENTS',
            'DEFAULT', 'DEFINED', 'ENUMERATED', 'EXPLICIT', 'EXTERNAL', 'FALSE',
            'MIN', 'MINUS-INFINITY', 'NULL', 'OPTIONAL', 'PLUS-INFINITY', 'PRESENT',
            'PRIVATE', 'REAL', 'SET', 'TAGS', 'TRUE', 'WITH'
        ]

    @staticmethod
    def tokens():
        # Token names required!
        tokens = [
            'BIN_STRING',
            'CHOICE',
            'COLON_COLON_EQUAL',
            'DOT_DOT',
            'EXPORTS',
            'HEX_STRING',
            'LOWERCASE_IDENTIFIER',
            'MACRO',
            'NEGATIVENUMBER',
            'NEGATIVENUMBER64',
            'NUMBER',
            'NUMBER64',
            'QUOTED_STRING',
            'UPPERCASE_IDENTIFIER',
        ]
        tokens += list(SupportSmiV1Keywords.reserved().values())
        return list(set(tokens))


relaxedGrammar = {
    'supportSmiV1Keywords': [
        SupportSmiV1Keywords.reserved,
        SupportSmiV1Keywords.forbidden_words,
        SupportSmiV1Keywords.tokens
    ],
    'supportIndex': [],
    'commaAtTheEndOfImport': [],
    'commaAtTheEndOfSequence': [],
    'mixOfCommasAndSpaces': [],
    'uppercaseIdentifier': [],
    'lowcaseIdentifier': [],
    'curlyBracesAroundEnterpriseInTrap': [],
    'noCells': []
}


def lexerFactory(**grammarOptions):
    classAttr = {}

    for option in grammarOptions:
        if grammarOptions[option]:
            if option not in relaxedGrammar:
                raise error.PySmiError('Unknown lexer relaxation option: %s' % option)

            for func in relaxedGrammar[option]:
                if sys.version_info[0] > 2:
                    classAttr[func.__name__] = func()
                else:
                    classAttr[func.func_name] = func()

    return type('SmiLexer', (SmiV2Lexer,), classAttr)
