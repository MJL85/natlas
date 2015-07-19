# mnet
MNet Suite

Michael Laforest `<mjlaforest` *at* `gmail` *dot* `com>`

The MNet Suite is a collection of tools written in Python for network professionals.  
The tools are centrally focused on Cisco devices.

# Support

If you use any of these tools or find them useful please consider donating.  

My bitcoin address is: **`14J9R95Sru4d489W1B4Mk3hh1bWpBV9Rpb`**

![14J9R95Sru4d489W1B4Mk3hh1bWpBV9Rpb](http://i.imgur.com/DutGv9A.png "14J9R95Sru4d489W1B4Mk3hh1bWpBV9Rpb")

# Suite Tools
| Module | Description |
| --- | --- |
| Graph | Crawls a network and builds a diagram based on CDP neighbor information. |
| TraceMAC | Attempts to locate a specific MAC address by recursively looking it up in switch CAM tables. |

# Installing MNet

MNet Suite can be installed through Python's pip.  
  
`# pip install mnet`

# Running MNet

### Graph Module

```
mnet.py graph -r <root IP>
              -f <file>
              [-d <max depth>]
              [-c <config file>]
              [-t <diagram title>]
              [-C <catalog file>]
```
The above command will run the `graph` module and generate a network diagram.

| Option | Description |
| --- | --- |
| `-r <root IP>` | IP address of the network node to start on. |
| `-f <file>` | The file that the output will be written to. `network.png` will create a PNG  file. |
| `-d <mac depth>` | The maximum depth to crawl into the network starting at the root node specified by `-r` |
| `-c <config file>` | The JSON configuration file to use. |
| `-t <diagram title>` | The title to give your generated network diagram. |
| `-C <catalog file>` | If specified, MNet will generate a comma separated (CSV) catalog file with a list of all devices discovered. |

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
	"exclude" : [
		"192.168.0.0/16"
	],
	"subnets" : [
		"10.0.0.0/8"
	],
	"graph" : {
		"node_text_size" : 10,
		"link_text_size" : 9
	}
}
```

| Block / Variable | Description |
| --- | --- |
| `snmp` | Defines a list of SNMP credentials.  When connecting to a node, each of these credentials is tried in order until one is successful.  This allows crawling a large network with devices that potentially use different SNMP credentials. |
| `domains` | Defines a list of domains that should be stripped off of the device names.  For example, if is switch is found with the name *SW1.company.com*, the above example will only show *SW1* in the output. |
| `subnets` | Defines a list of nodes that should be allowed to be discovered during the discovery process. If a node is discovered as being a neighbor to a node currently being crawled, the neighbor will only be crawled if it is in one of the CIDR ranges defined here. Therefore this list defines the subnets that are allowed to be included in the discovery process, but does not itself define the range of devices to be discovered. |
| `exclude` | Defines a list of nodes that should be skipped entirely during the discovery process. Since the node is skipped nothing beyond it will be discovered. |
| `graph` | Defines specific values used to change graph attributes.  `node_text_size` and `link_text_size` are supported and are both integers. |

# MNet's Graph Module

### Details

The graph module starts at a defined root node and recursively traverses neighboring devices (discovered via CDP) until a defined depth is reached.  The script collects data using SNMP.

MNet-Graph will attempt to collect the following information and include it in the generated diagram:
+ All devices (via CDP)
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

MNet's Graph module attempts to include all of the above information in the diagram in an intuitive way.  The keep the diagram clean, the following are used:
+ Nodes
  + Circle nodes represent layer 2 switches.
  + Diamond nodes represent layer 3 switches or routers.
  + If a node has multiple borders then either VSS or StackWise is enabled.
    + VSS - Will always have a double border.
    + StackWise - The number of borders denotes the number of switches in the stack.
+ Links
  + Links are shown with arrowed lines.  The end with no arrow is the *parent* and the end with the arrow is the *child*, such that the arrangement is *parent*->*child*.
  + If a link says *P:gi0/1* , *C:gi1/4* then the parent node's connection is on port gi0/1 and the child node's connection is on port gi1/4.
  + If the link is part of an Etherchannel the etherchannel's interface name will also be shown.  Since an etherchannel interface is locally significiant, a *P:* and *C:* will also be shown if available.

### Examples

Example 1
![MNet-Graph Ex1](http://i.imgur.com/Mny7PLl.png "MNet-Graph Ex1")

Example 2
![MNet-Graph Ex2](http://i.imgur.com/BuXnzWG.png "MNet-Graph Ex2")

Example 3
![MNet-Graph Ex3](http://i.imgur.com/i1dqM09.png "MNet-Graph Ex3")

# MNet's TraceMAC Module

### Examples

The below example shows a trace for MAC address `00:23:68:63:75:70` starting
at node `10.10.0.3`.  The MAC address is found on switch `IDF3_D` on port
`Gi0/11`.

```
# mnet-tracemac.py -r 10.10.0.3 -m 0023.6863.7570
MNet-TraceMAC v0.1
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
