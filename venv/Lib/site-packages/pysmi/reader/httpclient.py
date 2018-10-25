#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import socket
import sys
import time

try:
    # noinspection PyUnresolvedReferences
    from urllib2 import Request, urlopen
except ImportError:
    # noinspection PyUnresolvedReferences
    from urllib.request import Request
    from urllib.request import urlopen

from pysmi.reader.base import AbstractReader
from pysmi.mibinfo import MibInfo
from pysmi.compat import decode
from pysmi import __version__ as pysmi_version
from pysmi import error
from pysmi import debug


class HttpReader(AbstractReader):
    """Fetch ASN.1 MIB text by name from a web site.

    *HttpReader* class instance tries to download ASN.1 MIB files
    by name and return their contents to caller.
    """
    MIB_MAGIC = '@mib@'

    def __init__(self, host, port, locationTemplate, timeout=5, ssl=False):
        """Create an instance of *HttpReader* bound to specific URL.

           Note:
               The `http_proxy` and `https_proxy` environment variables are
               respected by the underlying `urllib` stdlib module.

           Args:
               host (str): domain name or IP address of web server
               port (int): TCP port web server is listening
               locationTemplate (str): location part of the URL optionally containing @mib@
                   magic placeholder to be replaced with MIB name. If @mib@ magic is not present,
                   MIB name is appended to `locationTemplate`

           Keyword Args:
               timeout (int): response timeout
               ssl (bool): access HTTPS web site
        """
        self._url = '%s://%s:%d%s' % (ssl and 'https' or 'http',
                                      host, port, decode(locationTemplate))

        socket.setdefaulttimeout(timeout)
        self._user_agent = 'pysmi-%s; python-%s.%s.%s; %s' % (
            pysmi_version, sys.version_info[0], sys.version_info[1],
            sys.version_info[2], sys.platform
        )

    def __str__(self):
        return self._url

    def getData(self, mibname):
        headers = {
            'Accept': 'text/plain',
            'User-Agent': self._user_agent
        }

        mibname = decode(mibname)

        debug.logger & debug.flagReader and debug.logger('looking for MIB %s' % mibname)

        for mibalias, mibfile in self.getMibVariants(mibname):
            if self.MIB_MAGIC in self._url:
                url = self._url.replace(self.MIB_MAGIC, mibfile)
            else:
                url = self._url + mibfile

            debug.logger & debug.flagReader and debug.logger('trying to fetch MIB from %s' % url)

            try:
                req = Request(url, headers=headers)
                response = urlopen(req)

            except Exception:
                debug.logger & debug.flagReader and debug.logger('failed to fetch MIB from %s: %s' % (url, sys.exc_info()[1]))
                continue

            debug.logger & debug.flagReader and debug.logger('HTTP response %s' % response.code)

            if response.code == 200:
                try:
                    mtime = time.mktime(time.strptime(response.getheader('Last-Modified'), "%a, %d %b %Y %H:%M:%S %Z"))

                except Exception:
                    debug.logger & debug.flagReader and debug.logger('malformed HTTP headers: %s' % sys.exc_info()[1])
                    mtime = time.time()

                debug.logger & debug.flagReader and debug.logger(
                    'fetching source MIB %s, mtime %s' % (url, response.getheader('Last-Modified')))

                return MibInfo(path=url, file=mibfile, name=mibalias, mtime=mtime), decode(response.read(self.maxMibSize))

        raise error.PySmiReaderFileNotFoundError('source MIB %s not found' % mibname, reader=self)
