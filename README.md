# mnet
MNet Suite

Michael Laforest `<mjlaforest` *at* `gmail` *dot* `com>`

The MNet Suite is a collection of tools written in Python for network professionals.  The tools are centrally focused on Cisco devices.

## About

As a network engineer I needed certain tools but have been largely unable to find anything suitable, so I decided to write my own.  I hope others find these useful too.  If you do I would certainly appreciate a donation!

If you want to donate my bitcoin address is: **`14J9R95Sru4d489W1B4Mk3hh1bWpBV9Rpb`**

![14J9R95Sru4d489W1B4Mk3hh1bWpBV9Rpb](http://i.imgur.com/DutGv9A.png "14J9R95Sru4d489W1B4Mk3hh1bWpBV9Rpb")

# Suite Tools
1. MNet-Graph

## MNet-Graph

MNet-Graph crawls a network and builds a detailed DOT diagram (.png output).

`# mnet-graph.py -r <root IP> [-d <depth>] [-f <file>] [-t <diagram title>]`

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

## Examples

Example 1
![MNet-Graph Ex1](http://i.imgur.com/Mny7PLl.png "MNet-Graph Ex1")

Example 2
![MNet-Graph Ex2](http://i.imgur.com/BuXnzWG.png "MNet-Graph Ex2")

Example 3
![MNet-Graph Ex3](http://i.imgur.com/i1dqM09.png "MNet-Graph Ex3")
