#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import sys
import time
import ftplib
from pysmi.reader.base import AbstractReader
from pysmi.mibinfo import MibInfo
from pysmi.compat import decode
from pysmi import error
from pysmi import debug


class FtpReader(AbstractReader):
    """Fetch ASN.1 MIB text by name from FTP server.
       *FtpReader* class instance tries to download ASN.1 MIB files
       by name and return their contents to caller.
    """

    def __init__(self, host, locationTemplate, timeout=5, ssl=False, port=21,
                 user='anonymous', password='anonymous@'):
        """Create an instance of *FtpReader* bound to specific FTP server
           directory.

           Args:
               host (str): domain name or IP address of web server
               locationTemplate (str): location part of the directory containing @mib@ magic placeholder to be
                   replaced with MIB name fetch.

           Keyword Args:
               timeout (int): response timeout
               ssl (bool): access HTTPS web site
               port (int): TCP port web server is listening
               user (str): username at FTP server
               password (str): password for *username* at FTP server
        """
        self._host = host
        self._locationTemplate = locationTemplate
        self._timeout = timeout
        self._ssl = ssl
        self._port = port
        self._user = user
        self._password = password
        if '@mib@' not in locationTemplate:
            raise error.PySmiError('@mib@ placeholder not specified in location at %s' % self)

    def __str__(self):
        return '%s{"ftp://%s%s"}' % (self.__class__.__name__, self._host, self._locationTemplate)

    def getData(self, mibname):
        if self._ssl:
            conn = ftplib.FTP_TLS()
        else:
            conn = ftplib.FTP()

        try:
            conn.connect(self._host, self._port, self._timeout)

        except ftplib.all_errors:
            raise error.PySmiReaderFileNotFoundError(
                'failed to connect to FTP server %s:%s: %s' % (self._host, self._port, sys.exc_info()[1]), reader=self)

        try:
            conn.login(self._user, self._password)

        except ftplib.all_errors:
            conn.close()
            raise error.PySmiReaderFileNotFoundError('failed to log in to FTP server %s:%s as %s/%s: %s' % (self._host, self._port, self._user, self._password, sys.exc_info()[1]), reader=self)

        mibname = decode(mibname)

        debug.logger & debug.flagReader and debug.logger('looking for MIB %s' % mibname)

        for mibalias, mibfile in self.getMibVariants(mibname):
            location = self._locationTemplate.replace('@mib@', mibfile)

            mtime = time.time()

            debug.logger & debug.flagReader and debug.logger(
                'trying to fetch MIB %s from %s:%s' % (location, self._host, self._port))

            data = []

            try:
                try:
                    response = conn.sendcmd('MDTM %s' % location)

                except ftplib.all_errors:
                    debug.logger & debug.flagReader and debug.logger(
                        'server %s:%s does not support MDTM command, fetching file %s' % (
                        self._host, self._port, location))

                else:
                    debug.logger & debug.flagReader and debug.logger(
                        'server %s:%s MDTM response is %s' % (self._host, self._port, response))

                    if response[:3] == 213:
                        mtime = time.mktime(time.strptime(response[4:], "%Y%m%d%H%M%S"))

                debug.logger & debug.flagReader and debug.logger('fetching source MIB %s, mtime %s' % (location, time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(mtime))))

                conn.retrlines('RETR %s' % location, lambda x, y=data: y.append(x))

            except ftplib.all_errors:
                debug.logger & debug.flagReader and debug.logger(
                    'failed to fetch MIB %s from %s:%s: %s' % (location, self._host, self._port, sys.exc_info()[1]))
                continue

            data = decode('\n'.join(data))

            debug.logger & debug.flagReader and debug.logger('fetched %s bytes in %s' % (len(data), location))

            conn.close()

            return MibInfo(path='ftp://%s%s' % (self._host, location), file=mibfile, name=mibalias, mtime=mtime), data

        conn.close()

        raise error.PySmiReaderFileNotFoundError('source MIB %s not found' % mibname, reader=self)
