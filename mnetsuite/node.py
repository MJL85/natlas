#!/usr/bin/python

'''
        MNet Suite
        node.py

        Michael Laforest
        mjlaforest@gmail.com

        Copyright (C) 2015-2018 Michael Laforest

        This program is free software; you can redistribute it and/or
        modify it under the terms of the GNU General Public License
        as published by the Free Software Foundation; either version 2
        of the License, or (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program; if not, write to the Free Software
        Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

import sys

from .snmp import *
from .util import *
from .node_stack import mnet_node_stack, mnet_node_stack_member
from .node_vss   import mnet_node_vss,   mnet_node_vss_member

class mnet_node_link:
    '''
    Generic link to another node.
    CDP and LLDP neighbors are discovered
    and returned as mnet_node_link objects.
    '''

    def __init__(self):
        # the linked node
        self.node                       = None

        # details about the link
        self.link_type                  = None
        self.remote_ip                  = None
        self.remote_name                = None
        self.vlan                       = None
        self.local_native_vlan          = None
        self.local_allowed_vlans        = None
        self.remote_native_vlan         = None
        self.remote_allowed_vlans       = None
        self.local_port                 = None
        self.remote_port                = None
        self.local_lag                  = None
        self.remote_lag                 = None
        self.local_lag_ips              = None
        self.remote_lag_ips             = None
        self.local_if_ip                = None
        self.remote_if_ip               = None
        self.remote_platform            = None
        self.remote_ios                 = None
        self.remote_mac                 = None
        self.discovered_proto           = None

    def __str__(self):
        return ('<local_port=%s,node.name=%s,remote_port=%s>' % (self.local_port, self.node.name, self.remote_port))
    def __repr__(self):
        return self.__str__()


class mnet_node_svi:
    def __init__(self, vlan):
        self.vlan   = vlan
        self.ip     = []
    def __str__(self):
        return ('<vlan=%s,ip=%s>' % (self.vlan, self.ip))
    def __repr__(self):
        return self.__str__()


class mnet_node_lo:
    def __init__(self, name, ips):
        self.name = name.replace('Loopback', 'lo')
        self.ips = ips
    def __str__(self):
        return ('<name=%s,ips=%s>' % (self.name, self.ips))
    def __repr__(self):
        return self.__str__()


class mnet_node:

    class _node_opts:

        def __init__(self):
            self.reset()

        def reset(self):
            self.get_name           = False
            self.get_ip             = False
            self.get_plat           = False
            self.get_ios            = False
            self.get_router         = False
            self.get_ospf_id        = False
            self.get_bgp_las        = False
            self.get_hsrp_pri       = False
            self.get_hsrp_vip       = False
            self.get_serial         = False
            self.get_stack          = False
            self.get_stack_details  = False
            self.get_vss            = False
            self.get_vss_details    = False
            self.get_svi            = False
            self.get_lo             = False
            self.get_bootf          = False
            self.get_chassis_info   = False
            self.get_vpc            = False

    def __init__(self):
        self.opts               = mnet_node._node_opts()
        self.snmpobj            = mnet_snmp()
        self.links              = []
        self.discovered         = 0
        self.name               = None
        self.ip                 = None
        self.plat               = None
        self.ios                = None
        self.router             = None
        self.ospf_id            = None
        self.bgp_las            = None
        self.hsrp_pri           = None
        self.hsrp_vip           = None
        self.serial             = None
        self.bootfile           = None
        self.svis               = []
        self.loopbacks          = []
        self.vpc_peerlink_if    = None
        self.vpc_peerlink_node  = None
        self.vpc_domain         = None
        self.stack              = mnet_node_stack()
        self.vss                = mnet_node_vss()
        self.cdp_vbtbl          = None
        self.ldp_vbtbl          = None
        self.link_type_vbtbl    = None
        self.lag_vbtbl          = None
        self.vlan_vbtbl         = None
        self.ifname_vbtbl       = None
        self.ifip_vbtbl         = None
        self.svi_vbtbl          = None
        self.ethif_vbtbl        = None
        self.trk_allowed_vbtbl  = None
        self.trk_native_vbtbl   = None


    def __str__(self):
        return ('<name=%s, ip=%s, plat=%s, ios=%s, serial=%s, router=%s, vss=%s, stack=%s>' %
                (self.name, self.ip, self.plat, self.ios, self.serial, self.router, self.vss, self.stack))
    def __repr__(self):
        return self.__str__()


    def add_link(self, link):
        self.links.append(link)


    # find valid credentials for this node.
    # try each known IP until one works
    def try_snmp_creds(self, snmp_creds):
        if (self.snmpobj.success == 0):
            for ipaddr in self.ip:
                if ((ipaddr == '0.0.0.0') | (ipaddr == 'UNKNOWN') | (ipaddr == '')):
                    continue
                self.snmpobj._ip = ipaddr
                if (self.snmpobj.get_cred(snmp_creds) == 1):
                    return 1
        return 0


    # Query this node.
    # Set .opts and .snmp_creds before calling.
    def query_node(self):
        if (self.snmpobj.ver == 0):
            # call try_snmp_creds() first or it failed to find good creds
            return 0

        snmpobj = self.snmpobj

        # router
        if (self.opts.get_router == True):
            if (self.router == None):
                self.router = 1 if (snmpobj.get_val(OID_IP_ROUTING) == '1') else 0

            if (self.router == 1):
                # OSPF
                if (self.opts.get_ospf_id == True):
                    self.ospf_id = snmpobj.get_val(OID_OSPF)
                    if (self.ospf_id != None):
                        self.ospf_id = snmpobj.get_val(OID_OSPF_ID)

                # BGP
                if (self.opts.get_bgp_las == True):
                    self.bgp_las = snmpobj.get_val(OID_BGP_LAS)
                    if (self.bgp_las == '0'):       # 4500x is reporting 0 with disabled
                        self.bgp_las = None

                # HSRP
                if (self.opts.get_hsrp_pri == True):
                    self.hsrp_pri = snmpobj.get_val(OID_HSRP_PRI)
                    if (self.hsrp_pri != None):
                        self.hsrp_vip = snmpobj.get_val(OID_HSRP_VIP)

        # stack
        if (self.opts.get_stack):
            self.stack = mnet_node_stack(snmpobj, self.opts)

        # vss
        if (self.opts.get_vss):
            self.vss = mnet_node_vss(snmpobj, self.opts)

        # serial
        if ((self.opts.get_serial == 1) & (self.stack.count == 0) & (self.vss.enabled == 0)):
            self.serial = snmpobj.get_val(OID_SYS_SERIAL)

        # SVI
        if (self.opts.get_svi == True):
            if (self.svi_vbtbl == None):
                self.svi_vbtbl          = snmpobj.get_bulk(OID_SVI_VLANIF)

            if (self.ifip_vbtbl == None):
                self.ifip_vbtbl         = snmpobj.get_bulk(OID_IF_IP)

            for row in self.svi_vbtbl:
                for n, v in row:
                    n = str(n)
                    vlan = n.split('.')[14]
                    svi = mnet_node_svi(vlan)
                    svi_ips = self.__get_cidrs_from_ifidx(v)
                    svi.ip.extend(svi_ips)
                    self.svis.append(svi)

        # loopback
        if (self.opts.get_lo == True):
            self.ethif_vbtbl = snmpobj.get_bulk(OID_ETH_IF)

            if (self.ifip_vbtbl == None):
                self.ifip_vbtbl = snmpobj.get_bulk(OID_IF_IP)

            for row in self.ethif_vbtbl:
                for n, v in row:
                    n = str(n)
                    if (n.startswith(OID_ETH_IF_TYPE) & (v == 24)):
                        ifidx = n.split('.')[10]
                        lo_name = snmpobj.cache_lookup(self.ethif_vbtbl, OID_ETH_IF_DESC + '.' + ifidx)
                        lo_ips = self.__get_cidrs_from_ifidx(ifidx)
                        lo = mnet_node_lo(lo_name, lo_ips)
                        self.loopbacks.append(lo)

        # bootfile
        if (self.opts.get_bootf):
            self.bootfile = snmpobj.get_val(OID_SYS_BOOT)

        # chassis info (serial, IOS, platform)
        if (self.opts.get_chassis_info):
            self.__get_chassis_info()

        # VPC peerlink
        if (self.opts.get_vpc):
            self.vpc_domain, self.vpc_peerlink_if = self.__get_vpc_info(self.ethif_vbtbl)
            
        # reset the get options
        self.opts.reset()
        return 1


    def __get_cidrs_from_ifidx(self, ifidx):
        ips = []

        for ifrow in self.ifip_vbtbl:
            for ifn, ifv in ifrow:
                ifn = str(ifn)
                if (ifn.startswith(OID_IF_IP_ADDR)):
                    if (str(ifv) == str(ifidx)):
                        t = ifn.split('.')
                        ip = ".".join(t[10:])
                        mask = self.snmpobj.cache_lookup(self.ifip_vbtbl, OID_IF_IP_NETM + ip)
                        nbits = util.get_net_bits_from_mask(mask)
                        cidr = '%s/%i' % (ip, nbits)
                        ips.append(cidr)
        return ips


    def __cache_common_mibs(self):
        if (self.link_type_vbtbl == None):
            self.link_type_vbtbl = self.snmpobj.get_bulk(OID_TRUNK_VTP)

        if (self.lag_vbtbl == None):
            self.lag_vbtbl = self.snmpobj.get_bulk(OID_LAG_LACP)

        if (self.vlan_vbtbl == None):
            self.vlan_vbtbl = self.snmpobj.get_bulk(OID_IF_VLAN)

        if (self.ifname_vbtbl == None):
            self.ifname_vbtbl = self.snmpobj.get_bulk(OID_IFNAME)

        if (self.trk_allowed_vbtbl == None):
            self.trk_allowed_vbtbl = self.snmpobj.get_bulk(OID_TRUNK_ALLOW)

        if (self.trk_native_vbtbl == None):
            self.trk_native_vbtbl = self.snmpobj.get_bulk(OID_TRUNK_NATIVE)

        if (self.ifip_vbtbl == None):
            self.ifip_vbtbl = self.snmpobj.get_bulk(OID_IF_IP)


    #
    # Get a list of CDP neighbors.
    # Returns a list of mnet_node_link's
    #
    def get_cdp_neighbors(self):
        neighbors = []
        snmpobj = self.snmpobj

        # get list of CDP neighbors
        self.cdp_vbtbl = snmpobj.get_bulk(OID_CDP)
        if (self.cdp_vbtbl == None):
            print('No CDP Neighbors Found.')
            return None

        # cache some common MIB trees
        self.__cache_common_mibs()

        for row in self.cdp_vbtbl:
            for name, val in row:
                name = str(name)
                # process only if this row is a CDP_DEVID
                if (name.startswith(OID_CDP_DEVID) == 0):
                    continue

                t = name.split('.')
                ifidx = t[14]
                ifidx2 = t[15]

                # get remote IP
                rip = snmpobj.cache_lookup(self.cdp_vbtbl, OID_CDP_IPADDR + '.' + ifidx + '.' + ifidx2)
                rip = util.convert_ip_int_str(rip)

                # get local port
                lport = self.__get_ifname(ifidx)

                # get remote port
                rport = snmpobj.cache_lookup(self.cdp_vbtbl, OID_CDP_DEVPORT + '.' + ifidx + '.' + ifidx2)
                rport = util.shorten_port_name(rport)

                # get remote platform
                rplat = snmpobj.cache_lookup(self.cdp_vbtbl, OID_CDP_DEVPLAT + '.' + ifidx + '.' + ifidx2)

                # get IOS version
                rios = snmpobj.cache_lookup(self.cdp_vbtbl, OID_CDP_IOS + '.' + ifidx + '.' + ifidx2)
                if (rios != None):
                    try:
                        rios = binascii.unhexlify(rios[2:])
                    except:
                        pass
                    rios = self.__format_ios_ver(rios)

                link                  = self.__get_node_link_info(ifidx, ifidx2)
                link.remote_name      = val.prettyPrint()
                link.remote_ip        = rip
                link.discovered_proto = 'cdp'
                link.local_port       = lport
                link.remote_port      = rport
                link.remote_plat      = rplat
                link.remote_ios       = rios

                neighbors.append(link)

        return neighbors


    #
    # Get a list of LLDP neighbors.
    # Returns a list of mnet_node_link's
    #
    def get_lldp_neighbors(self):
        neighbors = []
        snmpobj = self.snmpobj

        self.lldp_vbtbl = snmpobj.get_bulk(OID_LLDP)
        if (self.lldp_vbtbl == None):
            print('No LLDP Neighbors Found.')
            return None

        self.__cache_common_mibs()

        for row in self.lldp_vbtbl:
            for name, val in row:
                name = str(name)
                if (name.startswith(OID_LLDP_TYPE) == 0):
                    continue

                t = name.split('.')
                ifidx = t[12]
                ifidx2 = t[13]

                rip = ''
                for r in self.lldp_vbtbl:
                    for     n, v in r:
                        n = str(n)
                        if (n.startswith(OID_LLDP_DEVADDR + '.' + ifidx + '.' + ifidx2)):
                            t2 = n.split('.')
                            rip = '.'.join(t2[16:])


                lport = self.__get_ifname(ifidx)

                rport = snmpobj.cache_lookup(self.lldp_vbtbl, OID_LLDP_DEVPORT + '.' + ifidx + '.' + ifidx2)
                rport = util.shorten_port_name(rport)

                devid = snmpobj.cache_lookup(self.lldp_vbtbl, OID_LLDP_DEVID + '.' + ifidx + '.' + ifidx2)
                try:
                    mac_seg = [devid[x:x+4] for x in xrange(2, len(devid), 4)]
                    devid = '.'.join(mac_seg)
                except:
                    pass

                rimg = snmpobj.cache_lookup(self.lldp_vbtbl, OID_LLDP_DEVDESC + '.' + ifidx + '.' + ifidx2)
                if (rimg != None):
                    try:
                        rimg = binascii.unhexlify(rimg[2:])
                    except:
                        pass
                    rimg = self.__format_ios_ver(rimg)

                name = snmpobj.cache_lookup(self.lldp_vbtbl, OID_LLDP_DEVNAME + '.' + ifidx + '.' + ifidx2)
                if ((name == None) | (name == '')):
                    name = devid

                link                  = self.__get_node_link_info(ifidx, ifidx2)
                link.remote_ip        = rip
                link.remote_name      = name
                link.discovered_proto = 'lldp'
                link.local_port       = lport
                link.remote_port      = rport
                link.remote_plat      = None
                link.remote_ios       = rimg
                link.remote_mac       = devid

                neighbors.append(link)

        return neighbors


    def __get_node_link_info(self, ifidx, ifidx2):
        snmpobj = self.snmpobj

        # get link type (trunk ?)
        link_type = snmpobj.cache_lookup(self.link_type_vbtbl, OID_TRUNK_VTP + '.' + ifidx)

        native_vlan = None
        allowed_vlans = 'All'
        if (link_type == '1'):
            native_vlan = snmpobj.cache_lookup(self.trk_native_vbtbl, OID_TRUNK_NATIVE + '.' + ifidx)

            allowed_vlans = snmpobj.cache_lookup(self.trk_allowed_vbtbl, OID_TRUNK_ALLOW + '.' + ifidx)
            allowed_vlans = self.__parse_allowed_vlans(allowed_vlans)

        # get LAG membership
        lag = snmpobj.cache_lookup(self.lag_vbtbl, OID_LAG_LACP + '.' + ifidx)
        lag_ifname = self.__get_ifname(lag)
        lag_ips = self.__get_cidrs_from_ifidx(lag)

        # get VLAN info
        vlan = snmpobj.cache_lookup(self.vlan_vbtbl, OID_IF_VLAN + '.' + ifidx)

        # get IP address
        lifips = self.__get_cidrs_from_ifidx(ifidx)

        link                        = mnet_node_link()
        link.link_type              = link_type
        link.vlan                   = vlan
        link.local_native_vlan      = native_vlan
        link.local_allowed_vlans    = allowed_vlans
        link.local_lag              = lag_ifname
        link.local_lag_ips          = lag_ips
        link.remote_lag_ips         = []
        link.local_if_ip            = lifips[0] if len(lifips) else None

        return link


    def __parse_allowed_vlans(self, allowed_vlans):
        if (allowed_vlans.startswith('0x') == False):
            return 'All'

        ret = ''
        group = 0
        op = 0

        for i in range(2, len(allowed_vlans)):
            v = int(allowed_vlans[i], 16)
            for b in range(0, 4):
                a = v & (0x1 << (3 - b))
                vlan = ((i-2)*4)+b

                if (a):
                    if (op == 1):
                        group += 1
                    else:
                        if (len(ret)):
                            if (group > 1):
                                ret += '-'
                                ret += str(vlan - 1) if vlan else '1'
                            else:
                                ret += ',%i' % vlan
                        else:
                            ret += str(vlan)
                        group = 0
                        op = 1
                else:
                    if (op == 1):
                        if (len(ret)):
                            if (group > 1):
                                ret += '-%i' % (vlan - 1)
                        op = 0
                    group = 0

        if (op):
            if (ret == '1'):
                return 'All'
            if (group):
                ret += '-1001'
            else:
                ret += ',1001'

        return ret if len(ret) else 'All'


    def __get_chassis_info(self):
        # Get:
        #    Serial number
        #    Platform
        #    IOS
        # Slow but reliable method by using SNMP directly.
        # Usually we will get this via CDP.
        snmpobj = self.snmpobj

        if ((self.stack.count > 0) | (self.vss.enabled == 1)):
            # Use opts.get_stack_details
            # or  opts.get_vss_details
            # for this.
            return

        class_vbtbl  = snmpobj.get_bulk(OID_ENTPHYENTRY_CLASS)

        if (self.opts.get_serial):  serial_vbtbl = snmpobj.get_bulk(OID_ENTPHYENTRY_SERIAL)
        if (self.opts.get_plat):    platf_vbtbl  = snmpobj.get_bulk(OID_ENTPHYENTRY_PLAT)
        if (self.opts.get_ios):     ios_vbtbl    = snmpobj.get_bulk(OID_ENTPHYENTRY_SOFTWARE)

        if (class_vbtbl == None):
            return

        for row in class_vbtbl:
            for n, v in row:
                n = str(n)
                if (v != ENTPHYCLASS_CHASSIS):
                    continue

                t = n.split('.')
                idx = t[12]

                if (self.opts.get_serial):  self.serial = snmpobj.cache_lookup(serial_vbtbl, OID_ENTPHYENTRY_SERIAL + '.' + idx)
                if (self.opts.get_plat):    self.plat   = snmpobj.cache_lookup(platf_vbtbl, OID_ENTPHYENTRY_PLAT + '.' + idx)
                if (self.opts.get_ios):     self.ios    = snmpobj.cache_lookup(ios_vbtbl, OID_ENTPHYENTRY_SOFTWARE + '.' + idx)

        if (self.opts.get_ios):
            # modular switches might have IOS on a module rather than chassis
            if (self.ios == ''):
                for row in class_vbtbl:
                    for n, v in row:
                        n = str(n)
                        if (v != ENTPHYCLASS_MODULE):
                            continue
                        t = n.split('.')
                        idx = t[12]
                        self.ios = snmpobj.cache_lookup(ios_vbtbl, OID_ENTPHYENTRY_SOFTWARE + '.' + idx)
                        if (self.ios != ''):
                            break
                    if (self.ios != ''):
                        break
            self.ios = self.__format_ios_ver(self.ios)

        return

    #
    # Lookup and format an interface name from a cache table of indexes.
    #
    def __get_ifname(self, ifidx):
        if ((ifidx == None) | (ifidx == OID_ERR)):
            return 'UNKNOWN'

        str = self.snmpobj.cache_lookup(self.ifname_vbtbl, OID_IFNAME + '.' + ifidx)
        str = util.shorten_port_name(str)

        return str or 'UNKNOWN'


    def get_system_name(self, domains):
        return util.shorten_host_name(self.snmpobj.get_val(OID_SYSNAME), domains)


    #
    # Normalize a reporeted software vesion string.
    #
    def __format_ios_ver(self, img):
        x = img
        if (type(img) == bytes):
            x = img.decode("utf-8")

        try:
            img_s = re.search('(Version:? |CCM:)([^ ,$]*)', x)
        except:
            return img

        if (img_s):
            if (img_s.group(1) == 'CCM:'):
                return 'CCM %s' % img_s.group(2)
            return img_s.group(2)

        return img


    def get_ipaddr(self):
        '''
        Return the best IP address for this device.
        Returns the first matching IP:
            - Lowest Loopback interface
            - Lowest SVI address/known IP
        '''
        # Loopbacks - first interface
        if (len(self.loopbacks)):
            ips = self.loopbacks[0].ips
            ips.sort()
            return util.strip_slash_masklen(ips[0])

        # SVIs + all known - lowest address
        ips = []
        for svi in self.svis:
            ips.extend(svi.ip)
        ips.extend(self.ip)
        ips.sort()
        if (len(ips)):
            return util.strip_slash_masklen(ips[0])

        return ''


    def __get_vpc_info(self, ifarr):
        '''
        If VPC is enabled,
        Return the VPC domain and interface name of the VPC peerlink.
        '''
        tbl = self.snmpobj.get_bulk(OID_VPC_PEERLINK_IF)
        if ((tbl == None) | (len(tbl) == 0)):
            return (None, None)
        domain = mnet_snmp.get_last_oid_token(tbl[0][0][0])
        ifidx  = str(tbl[0][0][1])
        ifname = self.snmpobj.cache_lookup(ifarr, OID_ETH_IF_DESC + '.' + ifidx)
        ifname = util.shorten_port_name(ifname)
        return (domain, ifname)

