# mnet

mnet Suite - Tools for network professionals.  
Michael Laforest `<mjlaforest` *at* `gmail` *dot* `com>`
  
Automated discovery and diagram tools using SNMP, CDP, and LLDP.

 ```# ./mnet.py diagram -r 10.75.0.1 -o .\network.svg```<br><br><br>*The above command will generate the diagram to the right.* | ![MNet-Diagram Ex3][diag3]
:--- | --- 
 
# Support

If you use any of these tools or find them useful please consider donating.  

Donation Method | Address | QR Code
--- | --- | ---
Bitcoin (BTC) | 1HY3jPYVfE6YZbuYTYfMpazvSKRXjZDMbS  | ![1HY3jPYVfE6YZbuYTYfMpazvSKRXjZDMbS](https://github.com/MJL85/mnet/blob/master/docs/donate/BTC.png "Bitcoin (BTC)")
Bitcoin Cash (BCH) | 1HSycjR3LAZxuLG34aEBbQdUSayPkh8XsH | ![1HSycjR3LAZxuLG34aEBbQdUSayPkh8XsH](https://github.com/MJL85/mnet/blob/master/docs/donate/BCH.png "Bitcoin Cash (BCH)")

# Tools
| Module | Description |
| --- | --- |
| Diagram | Discovers a network and generates a diagram based on CDP and LLDP neighbor information. |
| TraceMAC | Attempts to locate a specific MAC address by recursively looking it up in switch CAM tables. |
| GetMACS | Collect a list of all MAC addresses on the discovered network and generate a report. |

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
| host REGEX | The host can be matched against any regular expression string.  The host string is what is reported from CDP or LLDP. | `host Router-.*` |
| ip CIDR | The ip can be matched against and CIDR. | `ip 10.50.31.0/24` |

# Command Reference

### Diagram
```
# mnet.py diagram -r <root IP>
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
| `-C <catalog file>` | If specified, mnet will generate a comma separated (CSV) catalog file with a list of all devices discovered. |

### TraceMAC
```
# mnet.py tracemac -r <root IP>
                 -m <MAC Address>
                 [-c <config file>]
```
| Option | Description |
| --- | --- |
| `-r <root IP>` | IP address of the network node to start on. |
| `-m <MAC Address>` | The MAC address to locate.  Can be in any form.  Ex: `11:22:33:44:55:66` or `112233445566` or `1122.3344.5566` |
| `-c <config file>` | The JSON configuration file to use. |

### GetMACS
```
# mnet.py getmacs -r <root IP>
                 -o <output CSV file>
                 [-d <mac depth>]
                 [-c <config file>]
```
| Option | Description |
| --- | --- |
| `-r <root IP>` | IP address of the network node to start on. |
| `-o <output CSV file>` | The comma separated value (.csv) file that the output will be written to. |
| `-d <max depth>` | The maximum hop depth to discover, starting at the root node specified by `-r` |
| `-c <config file>` | The JSON configuration file to use. |


### Config
```
# mnet.py config
```
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

#### Examples

Example 1
![MNet-Diagram Ex1](http://i.imgur.com/Mny7PLl.png "MNet-Graph Ex1")

Example 2
![MNet-Diagram Ex2](http://i.imgur.com/BuXnzWG.png "MNet-Graph Ex2")

Example 3
![MNet-Diagram Ex3](http://i.imgur.com/i1dqM09.png "MNet-Graph Ex3")

# TraceMAC

#### Examples

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

#### Q1 - My diagram is too large.  I only want to diagram part of my network.
Try changing the config `discover` ACL to narrow down the scope of your discovery.  You can explicitly deny CIDR's or host name regex patterns if you do not want them included in your diagram.  
  
#### Q2 - Where is the config file?
Create a new one with
`# mnet.py config > mnet.conf`

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

[diag3]: http://i.imgur.com/i1dqM09.png "MNet-Graph Ex3"
