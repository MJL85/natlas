# mnet
mnet Suite - Tools for network professionals.  
Michael Laforest `<mjlaforest` *at* `gmail` *dot* `com>`
  
Automated discovery and diagram tools using SNMP, CDP, and LLDP.

# Support

If you use any of these tools or find them useful please consider donating.  

Donation Method | Address | QR Code
--- | --- | ---
Bitcoin (BTC) | 1HY3jPYVfE6YZbuYTYfMpazvSKRXjZDMbS  | ![1HY3jPYVfE6YZbuYTYfMpazvSKRXjZDMbS](https://github.com/MJL85/mnet/blob/master/docs/donate/BTC.png "Bitcoin (BTC)")
Bitcoin Cash (BCH) | 1HSycjR3LAZxuLG34aEBbQdUSayPkh8XsH | ![1HSycjR3LAZxuLG34aEBbQdUSayPkh8XsH](https://github.com/MJL85/mnet/blob/master/docs/donate/BCH.png "Bitcoin Cash (BCH)")

# Suite Tools
| Module | Description |
| --- | --- |
| Diagram | Discovers a network and generates a diagram based on CDP and LLDP neighbor information. |
| TraceMAC | Attempts to locate a specific MAC address by recursively looking it up in switch CAM tables. |
| GetMACS | Collect a list of all MAC addresses on the discovered network and generate a report. |

# Installing mnet

mnet can be installed through Python's pip.  
  
`# pip install mnet`

# Running mnet

### Network Discovery  
  
A network discovery will be performed For the `diagram` and `getmacs` modules.  The discovery process will use SNMP, CDP, and LLDP to discover the network topology and details about each node.  
  
The discovery will begin at the specified root node and perform the following actions:

1. Collect a list of adjacencies through CDP and LLDP.  
2. Evaluate each  adjacent node against the `discover` ACL.
3. If the ACL permits discovery then collect information from that node.
4. If the current discovered depth is less than the user deviced maximum depth, repeat step 1 with this node.
  
The `discover` ACL is defined in the configuration file as:

```
"discover" : [
    ACE,
    ACE,
    ACE
]
```

An ACE is defined as:  
  
```<permit|deny|leaf|include|;> < [host REGEX] | [ip CIDR] >```
  
| Option | Include Node | Collect Node Information | Allow Discovery of Adjacencies |
| --- |:---:|:---:|:---:|
| permit | X | X | X |
| leaf | X | X |  |
| include | X |  |  |
| deny |  |  |  |
  
| Parameter | Description | Example |
| --- | --- | --- |
| host REGEX | The host can be matched against any regular expression string.  The host string is what is reported from CDP or LLDP. | `host Router-.*` |
| ip CIDR | The ip can be matched against and CIDR. | `ip 10.50.31.0/24` |

### Diagram Module

```
mnet.py diagram -r <root IP>
                -o <output file>
               [-d <max depth>]
               [-c <config file>]
               [-t <diagram title>]
               [-C <catalog file>]
```
The above command will discover the network and generate a network diagram.

| Option | Description |
| --- | --- |
| `-r <root IP>` | IP address of the network node to start on. |
| `-o <output file>` | The file that the output will be written to.<br />Common file extensions: `.png`, `.pdf`, `.svg` |
| `-c <config file>` | The JSON configuration file to use. |
| `-d <max depth>` | The maximum hop depth to discover, starting at the root node specified by `-r` |
| `-t <diagram title>` | The title to give your generated network diagram. |
| `-C <catalog file>` | If specified, mnet will generate a comma separated (CSV) catalog file with a list of all devices discovered. |

### TraceMAC Module

```
mnet.py tracemac -r <root IP>
                 -m <MAC Address>
                 [-c <config file>]
```
The above command will run the `TraceMAC` module and trace a MAC address through CAM tables.

| Option | Description |
| --- | --- |
| `-r <root IP>` | IP address of the network node to start on. |
| `-m <MAC Address>` | The MAC address to locate.  Can be in any form.  Ex: `11:22:33:44:55:66` or `112233445566` or `1122.3344.5566` |
| `-c <config file>` | The JSON configuration file to use. |

### GetMACS Module

```
mnet.py getmacs -r <root IP>
                 -o <output CSV file>
                 [-d <mac depth>]
                 [-c <config file>]
```
Discover the network per the `discover` rules in the configuration file, then generate a CSV output file of all MAC addresses.

| Option | Description |
| --- | --- |
| `-r <root IP>` | IP address of the network node to start on. |
| `-o <output CSV file>` | The comma separated value (.csv) file that the output will be written to. |
| `-d <max depth>` | The maximum hop depth to discover, starting at the root node specified by `-r` |
| `-c <config file>` | The JSON configuration file to use. |


### Config Module

```
mnet.py config
```
The above command will run the `config` module and output a standard config to stdout.  
  
Use this module and redirect stdout to a file in order to create a new blank config file.  
`# mnet.py config > mnet.conf`

# Configuration File

The toolset uses a JSON configuration file for common parameters.

```
{
	"snmp" : [
		{ "community":"private",	"ver":2 },
		{ "community":"public",		"ver":2 }
	],
	"domains" : [
		".company.net",
		".company.com"
	],
	"discover" : [
        "permit ip 10.0.0.0/8",
		"permit host Router[1,2]",
		"deny ip any",
	],
 	"diagram" : {
		"node_text_size" : 10,
		"link_text_size" : 9,
		"title_text_size" : 15,
		"get_stack_members" : 0,
		"get_vss_members" : 0,
		"expand_stackwise" : 0,
		"expand_vss" : 0,
        "expand_lag" : 1,
        "group_vpc" : 0
    }
	
}
```

| Block / Variable | Description |
| --- | --- |
| `snmp` | Defines a list of SNMP credentials.  When connecting to a node, each of these credentials is tried in order until one is successful.  This allows crawling a large network with devices that potentially use different SNMP credentials. |
| `discover` | Defines a Cisco-style ACL. See the `Network Discovery` section. |
| `diagram` | Defines specific values used to change diagram attributes.  Detailed below in the *Diagram block* table. |

**Diagram block**

| Variable | Type | Default Value | Description |
| --- | --- | --- | --- |
| `node_text_size` | integer | `10` | Node text size. |
| `link_text_size` | integer | `9` | Link text size. |
| `title_text_size` | integer | `15` |  Diagram title text size. |
| `get_stack_members` | bool | `0` | If set to `1`, nodes will include details about stackwise members. |
| `get_vss_members` | bool | `0` | If set to `1`, nodes will include details about VSS members. |
| `expand_stackwise` | bool | `0` | If set to `1`, nodes belonging to stackwise groups will be expanded to show each member as a node. |
| `expand_vss` | bool | `0` | If set to `1`, nodes belonging to VSS groups will be expanded to show each member as a node. |
| `expand_lag` | bool | `1` | If set to `1`, each link between nodes will be shown.  If set to `0`, links of the same logical link channel will be grouped and only the channel link will be shown. |
| `group_vpc` | bool | `0` | If set to `1`, VPC peers will be grouped together on the diagram, otherwise they will not be clustered. |

# mnet's Diagram Module

### Details

A network discovery will be performed and a network diagram will be generated. 
  
mnet will attempt to collect the following information and include it in the generated diagram:
+ All devices (via CDP and LLDP)
+ Interface names
+ IP addresses
+ VLAN memberships
+ Etherchannel memberships (LACP only)
+ Identify trunk links
+ Identify switched links
+ Identify routed links
+ BGP Local AS
+ OSPF Router ID
+ HSRP Virtual IP
+ HSRP Priority
+ VSS Domain
+ Stackwise membership
+ VPC peerlink information

mnet's Diagram module attempts to include all of the above information in the diagram in an intuitive way.  The keep the diagram clean, the following are used:
+ Nodes
  + Circle nodes represent layer 2 switches.
  + Diamond nodes represent layer 3 switches or routers.
  + If a node has multiple borders then either VSS or StackWise is enabled.
    + VSS - Will always have a double border.
    + StackWise - The number of borders denotes the number of switches in the stack.
  + If the configuration specifies, VSS/VPC/Stackwise nodes will be grouped in larger squares.
+ Links
  + Links are shown with arrowed lines.  The end with no arrow is the *parent* and the end with the arrow is the *child*, such that the arrangement is *parent*->*child*.
  + If a link says *P:gi0/1* , *C:gi1/4* then the parent node's connection is on port gi0/1 and the child node's connection is on port gi1/4.
  + If the link is part of an Etherchannel the etherchannel's interface name will also be shown.  Since an etherchannel interface is locally significiant, a *P:* and *C:* will also be shown if available.

### Examples

Example 1
![MNet-Diagram Ex1](http://i.imgur.com/Mny7PLl.png "MNet-Graph Ex1")

Example 2
![MNet-Diagram Ex2](http://i.imgur.com/BuXnzWG.png "MNet-Graph Ex2")

Example 3
![MNet-Diagram Ex3](http://i.imgur.com/i1dqM09.png "MNet-Graph Ex3")

# mnet's TraceMAC Module

### Examples

The below example shows a trace for MAC address `00:23:68:63:75:70` starting
at node `10.10.0.3`.  The MAC address is found on switch `IDF3_D` on port
`Gi0/11`.

```
# mnet.py tracemac -r 10.10.0.3 -m 0023.6863.7570
MNet Suite v0.7
Written by Michael Laforest <mjlaforest@gmail.com>

     Config file: ./mnet.conf
       Root node: 10.10.0.3
     MAC address: 0023.6863.7570



Start trace.
------------
IDF1_A (10.10.0.3)
          VLAN: 1
          Port: Gi1/3
     Next Node: IDF1_B
  Next Node IP: 10.10.0.2
------------
IDF1_B (10.10.0.2)
          VLAN: 1
          Port: Gi0/24
     Next Node: IDF3_D
  Next Node IP: 10.10.0.6
------------
IDF3_D (10.10.0.6)
          VLAN: 1
          Port: Gi0/11
------------
Trace complete.
```

# FAQ

**Q.** `My diagram is too large.  I only want to diagram part of my network.`

**A.** Try changing the config `discover` ACL to narrow down the scope of your discovery.  You can explicitly deny CIDR's or host name regex patterns if you do not want them included in your diagram.  
  
**Q.** `My diagram is still too wide.  What can I do?`  
  
**A.** Try to use the Graphviz `unflatted` command line program to reformat the generated dot file.  
  
**Q.** `Where is the config file?`  
  
*A.* If you need a config file you can generate a new one with `# mnet.py config > mnet.conf` .

**Q.** `I need a diagram with less proprietary information. Can I get one without IPs or serial numbers?`

*A.* Yes, you can change the text inside each node by editing the config option `diagram\node_text`. Below is an example that would produce a minimal information diagram:

```
"diagram" : {
	node_text = '<font point-size="10"><b>{node.name}</b></font><br />{node.ios}<br />{node.plat}'
}	
```

