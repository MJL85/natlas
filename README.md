# mnet
MNet Suite

Michael Laforest `<mjlaforest` *at* `gmail` *dot* `com>`

The MNet Suite is a collection of tools written in Python for network professionals.  
The tools are centrally focused on Cisco devices.

# Support

If you use any of these tools and like them please consider donating.  

My bitcoin address is: **`14J9R95Sru4d489W1B4Mk3hh1bWpBV9Rpb`**

![14J9R95Sru4d489W1B4Mk3hh1bWpBV9Rpb](http://i.imgur.com/DutGv9A.png "14J9R95Sru4d489W1B4Mk3hh1bWpBV9Rpb")

# Suite Tools
1. MNet-Graph

## MNet-Graph

### Summary

MNet-Graph crawls a network and builds a detailed DOT diagram (.png output).

`# mnet-graph.py -r <root IP> <-f <file>> [-d <depth>] [-c <config file>] [-t <diagram title>]`

### Requirements

MNet-Graph requires the following:

|   | Tested With Version |
| --- | --- |
| **Python** | 2.7 |
| **PySNMP** | 4.2.5 |
| **PyDot** | 1.0.28 |
| **PyNetAddr** | 0.7.14 |

### Configuration File

The toolset uses a JSON configuration file for common parameters.

```
{  
	"snmp" : [  
		{ "community":"superpublic",	"ver":2 },  
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
	]  
}```

The **snmp** block defines a list of SNMP credentials.  When connecting to a node, each of these credentials is tried in order until one is successful.  This allows crawling a large network with devices that potentially use different SNMP credentials.  
[mnet-graph only] The **domains** block defines a list of domains that should be stripped off of the device names.  For example, if is switch is found with the name *SW1.company.com*, the above example will only show *SW1* in the output.  
  
[mnet-graph only] The **subnets** block defines a list of nodes that should be allowed to be discovered during the discovery process. If a node is discovered as being a neighbor to a node currently being crawled, the neighbor will only be crawled if it is in one of the CIDR ranges defined here. Therefore this list defines the subnets that are allowed to be included in the discovery process, but does not itself define the range of devices to be discovered.

[mnet-graph only] The **exclude** block defines a list of nodes that should be skipped entirely during the discovery process. Since the node is skipped nothing beyond it will be discovered.


### Details

The script starts at a defined root node and recursively traverses neighboring devices (discovered via CDP) until a defined depth is reached.  The script collects data using SNMP.

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

MNet-Graph attempts to include all of the above information in the diagram in an intuitive way.  The keep the diagram clean, the following are used:
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
