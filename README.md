# natlas

natlas - Network Atlas  
Michael Laforest `<mjlaforest` *at* `gmail` *dot* `com>`

Automated discovery and diagram tools using SNMP, CDP, and LLDP.

 ```# ./natlas-cli.py diagram -r 10.75.0.1 -o .\network.svg```<br><br><br>*The above command will generate the diagram to the right.* | ![natlas-Diagram Main][diag-main]
:--- | --- 
 
# Support

If you use any of these tools or find them useful please consider donating.  

Donation Method | Address | QR Code
--- | --- | ---
Bitcoin Cash (BCH) | 1HSycjR3LAZxuLG34aEBbQdUSayPkh8XsH | ![1HSycjR3LAZxuLG34aEBbQdUSayPkh8XsH](https://raw.github.com/MJL85/natlas/master/docs/donate/BCH.png "Bitcoin Cash (BCH)")
Bitcoin (BTC) | 1HY3jPYVfE6YZbuYTYfMpazvSKRXjZDMbS  | ![1HY3jPYVfE6YZbuYTYfMpazvSKRXjZDMbS](https://raw.github.com/MJL85/natlas/master/docs/donate/BTC.png "Bitcoin (BTC)")

# About

natlas is a python application framework which includes a discovery engine, an API, and a front-end cli for running available modules.

##### For Users
The `natlas-cli.py` program allows you to browse and execute any natlas module, including, among others, the network discovery and diagram module.

##### For Developers

Copy `docs/template_module.py` to a new file in the `modules/` directory.
Edit the function `mod_load()` to set the name and help properties for your module.
The entry function for any module is `mod_entry()`.
When creating a new module, natlas will create a new object and pass it to mod_entry().  From there the natlas API is available and includes functions such as:
- discover_network()
- query_node()
- get_switch_vlans()

Once saved, your module will automatically be listed in `natlas-cli.py list` and runnable.

# Modules
| Module | Description |
| --- | --- |
| diagram | Discovers a network and generates a diagram based on CDP and LLDP neighbor information. |
| get-mac-table | Collect a list of all MAC addresses on the discovered network and generate a report. |
| get-arp-table | Collect a list of all ARP entries. |
| get-hosts | Determine all hosts connected to one or all switches in the network. Includes MAC, IP, DNS name of each host, along with what switch and port it was found on. Can be exported to CSV. |
| tracemac | Trace a MAC address through a layer 2 network. |
| newconfig, showconfig, checkconfig | Modules to create, display, and validate natlas configuration files. |

# Network Discovery  
  
The discovery process uses SNMP, CDP, and LLDP to discover the network topology and details about each node.  Each discovered node will be evaluated against the `discover` ACL (defined in the config file) to determine how to proceed; the ACL may allow discovery, stop discovery here, or include it as a leaf in the diagram.

<table>
	<tr>
	<td valign=top rowspan=2>
		The <i>discover</i> ACL is defined as
	<pre><code>"discover" : [
	ACE1,
	ACE2,
	...
	ACEn,
]</code></pre>
	</td>
	<td valign=top>
		An <i>ACE</i> is defined as  
	<pre><code>&lt;permit|deny|leaf|include|;&gt; &lt; [host REGEX] | [ip CIDR] &gt;</code></pre>
	</td>
	</tr>
	<tr>
	<td>
Example
	<pre><code>"discover" : [
	"deny ip 10.50.12.55",
	"deny host ^SEP.*",
	"permit ip 10.50.12.0/24",
	"leaf host ^Switch2$",
	"permit ip any"
]</code>	</td>
	</tr>
</table>

---

| ACE Match Type| Include Node | Collect Node Information | Allow Discovery of Adjacencies |
| --- |:---:|:---:|:---:|
| **permit** | yes | yes | yes |
| **leaf** | yes | yes |  |
| **include** | yes |  |  |
| **deny** |  |  |  |

  ---
 
| ACE Parameter | Description | Example |
| --- | --- | --- |
| host REGEX | The host can match any regular expression string.  The host string is what is reported from CDP or LLDP. | `host Router-.*` |
| ip CIDR | The ip can be matched against and CIDR. | `ip 10\\.50\\.31\\.0/24` |
| platform REGEX | The system platform or hardware model. | `platform .*3850.*` |
| software REGEX | The system software version or IOS. | `software ^15\\.3` |

# Command Reference

### Diagram
```
# natlas-cli.py diagram -r <root IP>
                -o <output file>
               [-d <max depth>]
               [-c <config file>]
               [-t <diagram title>]
               [-C <catalog file>]
```
| Option | Description |
| --- | --- |
| `-r <root IP>` | IP address of the network node to start on. |
| `-o <output file>` | The file that the output will be written to.<br />Common file extensions: `.png`, `.pdf`, `.svg` |
| `-c <config file>` | The JSON configuration file to use. |
| `-d <max depth>` | The maximum hop depth to discover, starting at the root node specified by `-r` |
| `-t <diagram title>` | The title to give your generated network diagram. |
| `-C <catalog file>` | If specified, natlas will generate a comma separated (CSV) catalog file with a list of all devices discovered. |

### get-mac-table
```
# natlas-cli.py get-mac-table -n <node IP> -c <snmp v2 community> [-m <mac regex>] [-p <port regex>] [-v <vlan>]
```
| Option | Description |
| --- | --- |
| `-n <node IP>` | IP address of the network node to get MAC addresses from. |
| `-c <community>` | SNMPv2 community string. |
| `-m <regex>` | Filter MAC addresses by this regex string. |
| `-p <regex>` | Filter MAC addresses to only those on ports matching this regex string. |
| `-v <regex>` | Filter MAC addresses to only those on VLANs matching this regex string. |

### get-arp-table
```
# natlas-cli.py get-arp-table -n <node IP> -c <snmp v2 community> [-s | -d] [-i <IP regex>] [-v <vlan regex>] [-m <mac regex>]
```
| Option | Description |
| --- | --- |
| `-n <node IP>` | IP address of the network node to get ARP entries from. |
| `-c <community>` | SNMPv2 community string. |
| `-s` | Include static entries only |
| `-d` | Include dyntamic entries only |
| `-i <regex>` | Include entries with IP addresses that match regex pattern |
| `-v <regex>` | Include entries with VLANs that match regex pattern |
| `-m <regex>` | Include entries with MAC addreses that match regex pattern |

### get-hosts

get-hosts can either collect information from a single node or can do a network discovery and collect information from all discovered nodes.
```
# natlas-cli.py get-hosts -r <root IP> -c <config file> [-o <csv file>] [-d <discovery depth>]

# natlas-cli.py get-hosts -n <node IP> [-r <router IP>] -C <snmp v2 community> [-v <vlan regex>] [-p <port regex>] [-o <csv file>]
```
| Option | Description |
| --- | --- |
| `-r <root IP>` | IP address to begin a network discovery. |
| `-c <config file>` | natlas configuration file to use. |
| `-o <csv file>` | Output CSV file path. |
| `-d <depth>` | Maximum network discovery depth. |
| --- | --- |
| `-n <node IP>` | IP address of single layer2 or layer3 node to collect information from. |
| `-r <router IP>` | IP address of the layer3 device to collect ARP entries from. If this is omitted then the IP from -n will be used. |
| `-C <community>` | SNMPv2 community string. |
| `-v <regex>` | Include entries with VLANs that match regex pattern |
| `-p <regex>` | Include entries on ports that match regex pattern |
| `-o <csv file>` | Output CSV file path. |

### tracemac

```
# natlas-cli.py tracemac -n <starting node IP> -m <MAC address>
```
| Option | Description |
| --- | --- |
| `-n <starting node IP>` | IP address of node to begin layer 2 MAC trace. |
| `-m <MAC address>` | MAC address to locate in the network. |

### Config
| | |
| --- | --- |
| `# natlas-cli.py newconfig` | Generate a new config file |
| `# natlas-cli.py showconfig [-c <config file>]` | Display the config file |
| `# natlas-cli.py checkconfig [-c <config file>]` | Validate the contents of the config file |

# Configuration File
The configuration file defines common parameters in a JSON format.
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
| `snmp` | Defines a list of SNMP credentials.  When connecting to a node, each of these credentials is tried in order until one is successful. |
| `discover` | Defines a Cisco-style ACL. See the `Network Discovery` section. |
| `diagram` | Defines values used by the diagram module.  Detailed below in the *Diagram block* table. |

### Diagram block
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

# Diagram
natlas will attempt to collect the following information and include it in the generated diagram:
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

#### Diagram Formatting
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

# Examples

#### Diagram Example 1
![natlas-Diagram Ex1][diag-ex1]

#### Diagram Example 2
![natlas-Diagram Ex2][diag-ex2]

#### Diagram Example 3
![natlas-Diagram Ex3][diag-ex3]

#### get-hosts Example 1
![natlas-get-hosts Ex1][get-hosts-ex1]

#### tracemac Example 1
![natlas-tracemac Ex1][tracemac-ex1]

# FAQ

#### Q1 - My diagram is too large.  I only want to diagram part of my network.
Try changing the config `discover` ACL to narrow down the scope of your discovery.  You can explicitly deny CIDR's or host name regex patterns if you do not want them included in your diagram.  
  
#### Q2 - Where is the config file?
Create a new one with
`# natlas-cli.py newconfig > natlas.conf`

#### Q3 - I need a diagram with less proprietary information. Can I get one without IPs or serial numbers?
You can change the text inside each node by editing the config option `diagram\node_text`. Below is an example that would produce a minimal information diagram:

```
"diagram" : {
	node_text = '<font point-size="10"><b>{node.name}</b></font><br />{node.ios}<br />{node.plat}'
}	
``` 
#### Q4 - How can I remove Cisco VoIP phones from my diagram?
```
"discover" : [
	"deny host ^SEP.*$"
]
``` 

[diag-main]: https://raw.github.com/MJL85/natlas/master/docs/images/diagram_example.png "Diagram Main"
[diag-ex1]: https://raw.github.com/MJL85/natlas/master/docs/images/diagram_example1.png "Diagram Example 1"
[diag-ex2]: https://raw.github.com/MJL85/natlas/master/docs/images/diagram_example2.png "Diagram Example 2"
[diag-ex3]: https://raw.github.com/MJL85/natlas/master/docs/images/diagram_example3.png "Diagram Example 3"
[get-hosts-ex1]: https://raw.github.com/MJL85/natlas/master/docs/images/get-hosts_example1.png "get-hosts Example 1"
[tracemac-ex1]: https://raw.github.com/MJL85/natlas/master/docs/images/tracemac_example1.png "tracemac Example 1"


