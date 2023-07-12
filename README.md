# DHCP Server Helpers Checker

This script checks if a list of ip helper addresses are configured in all vlans of a L3 device.
_ DHCP servers ip addresses are stored in an internal variable dhcp_servers_list[]
_ The script checks all Vlans of each L3 device to verify that ip helpers and ip helpers global are configured including the specific DHCP server ip addresses.
_ If an interface vlan or L3 port doesn't have ip helpers configured, DHCP ip's won't be missing. It only checks in those interfaces where ip helpers and/or ip helpers global where configured.

**Example 1**

DHCP ip to check: 1.1.1.1 & 3.3.3.3

interface Vlan350
 description client-cisco
 ip address 192.168.30.254 255.255.255.0
 ip helper-address 1.1.1.1
 ip helper-address 2.2.2.2
 no ip proxy-arp
!

In this case ip helper-address 3.3.3.3 is missing.

**Example 2**

DHCP ip to check: 1.1.1.1

interface Vlan350
 description client-cisco
 ip address 192.168.30.254 255.255.255.0
 ip helper-address 1.1.1.1
 ip helper-address 2.2.2.2
 ip helper-address global 2.2.2.2
 no ip proxy-arp
!

DHCP server is missing as ip helper-address global 1.1.1.1

**Example 3**

DHCP ip to check: 1.1.1.1

interface Vlan350
 description client-cisco
 ip address 192.168.30.254 255.255.255.0
 no ip proxy-arp
!

DHCP server isn't missing as the vlan doesn't have any ip helper-address configured.

## Files

**hosts.ini**
lists of all the devices to check.
**check_dhcp.py**
Module configured to detect Vlans ip helper configuration for each device. It checks DHCP ip's are configured in each required vlan.
**cmplchk.py**
Main script, with multi-threading capability that scans multiple devices at the same time. This file includes the module check_dhcp.py with its functions.
**devices_compliance.yaml**
It outputs the result of the check

The internal variable dhcp_servers_list[] has the DHCP server ip's needed to be checked.

## Libraries used
netmiko, getpass, pandas, threading, queue, re, os, yaml
