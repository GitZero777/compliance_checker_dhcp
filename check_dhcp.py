from netmiko import SSHDetect, ConnectHandler
from getpass import getpass
import os
import re



#---------------------------------------------------------------------------

def get_vlans_with_helpers(text):
    #This is a regex that returns vlans with helpers configured. Input should be Cisco's 'show running config'
    #There are 2 type of helpers that can be configured -> Global and non-global, depending if vlan is configured in a vrf
    #((.*(\n|\r|\r\n)){2}).+ -> Includes text from 2 carriage return above
    pattern_helper = re.compile(r"(?<=interface )(.+)[\s\S][^!]+ helper-address \d[\s\S]*?!")
    pattern_helper_global = re.compile(r"(?<=interface )(.+)[\s\S][^!]+ helper-address global \d[\s\S]*?!")

    vlans_w_helpers = pattern_helper.findall(text)
    vlans_w_helpers_global = pattern_helper_global.findall(text)

    return vlans_w_helpers, vlans_w_helpers_global


def get_vlans_w_dhcp_configured(text, dhcp_servers_list):
    #This regex verifies if dhcp servers are configured in the vlans. Input should be Cisco's 'show running config'
    vlans_w_dhcp = []
    vlans_w_dhcp_global = []
    vlans_w_dhcp_aux = []

    for dhcp_server in dhcp_servers_list:
        dhcp_server_escaped = dhcp_server.replace('.','\.')
        pattern_dhcp = re.compile(r"(?<=interface )(.+)[\s\S][^!]+ helper-address " + dhcp_server_escaped + r"\s*\n[\s\S]*?!")
        pattern_dhcp_global = re.compile(r"(?<=interface )(.+)[\s\S][^!]+ helper-address global " + dhcp_server_escaped + r"\s*\n[\s\S]*?!")
        
        if len(vlans_w_dhcp) == 0:
            vlans_w_dhcp.extend(pattern_dhcp.findall(text))                 #extend adds a list of objects, append only adds one object
            vlans_w_dhcp = list(set(vlans_w_dhcp))                         #set() is a list to remove duplicates
        elif len(vlans_w_dhcp) > 0:
            vlans_w_dhcp_aux.extend(pattern_dhcp.findall(text))
            vlans_w_dhcp_aux = list(set(vlans_w_dhcp_aux))
            if len(vlans_w_dhcp_aux) < len(vlans_w_dhcp):
                vlans_w_dhcp = []
                vlans_w_dhcp = vlans_w_dhcp_aux                            #The vlan will be added to the list only if both dhcp ip's are present
        vlans_w_dhcp_aux = []                  
        if len(vlans_w_dhcp_global) == 0:
            vlans_w_dhcp_global.extend(pattern_dhcp_global.findall(text))
            vlans_w_dhcp_global = list(set(vlans_w_dhcp_global))           #set() is a list to remove duplicates
        elif len(vlans_w_dhcp_global) > 0:
            vlans_w_dhcp_aux.extend(pattern_dhcp_global.findall(text))
            vlans_w_dhcp_aux = list(set(vlans_w_dhcp_aux))
            if len(vlans_w_dhcp_aux) < len(vlans_w_dhcp_global):
                vlans_w_dhcp_global = []
                vlans_w_dhcp_global = vlans_w_dhcp_aux                     #The vlan will be added to the list only if both dhcp ip's are present        
        vlans_w_dhcp_aux = []

    return vlans_w_dhcp, vlans_w_dhcp_global

#---------------------------------------------------------------------------

def verify_dhcp_servers_device_reg(std_output):
    #Verifies that vlans have the correct helpers applyed from dhcp servers list. Regex only version
    dhcp_servers_list = ["1.1.1.1","2.2.2.2"]           #New DHCP servers to verify
    iphelpersConfigured = False
    iphelpersGlobalConfigured = False
    verification = ""

    vlans_w_helpers, vlans_w_helpers_global = get_vlans_with_helpers(std_output)
    vlans_w_dhcp, vlans_w_dhcp_global = get_vlans_w_dhcp_configured(std_output, dhcp_servers_list)
    
    if ((len(vlans_w_helpers) == 0) and (len(vlans_w_helpers_global) == 0)):
        return "There isn't any DHCP servers configured in device"
    else:
        vlans_w_helpers.sort()
        vlans_w_dhcp.sort()
        vlans_w_helpers_global.sort()
        vlans_w_dhcp_global.sort()
        if (vlans_w_helpers == vlans_w_dhcp) and (len(vlans_w_dhcp) > 0):
            #print("Ip helpers have been applied to all vlans")
            iphelpersConfigured = True
        if (vlans_w_helpers_global == vlans_w_dhcp_global) and (len(vlans_w_dhcp_global) > 0):
            #print("Ip helpers global have been applied to all vlans")
            iphelpersGlobalConfigured = True

        if (iphelpersConfigured == True) and (iphelpersGlobalConfigured == True):
            verification = "DHCP servers configured in all vlans"
        else:
            #Detect missing Vlans to configure helpers
            i = 0
            missing_vlans_str = ""
            for vlan_h in vlans_w_helpers:
                for vlan_d in vlans_w_dhcp:
                    i += 1
                    if vlan_h == vlan_d:
                        i = 0
                        break
                    elif i == len(vlans_w_dhcp):
                        if missing_vlans_str == "":
                            missing_vlans_str = vlan_h
                        else:
                            missing_vlans_str = missing_vlans_str + ", " + vlan_h
                        i = 0
            
            if missing_vlans_str != "":
                verification = "DHCP servers missing in vlans -> " + missing_vlans_str

            #Detect missing Vlans to configure helpers global
            i = 0
            missing_vlans_str = ""
            for vlan_h in vlans_w_helpers_global:
                for vlan_d in vlans_w_dhcp:
                    i += 1
                    if vlan_h == vlan_d:
                        i = 0
                        break
                    elif i == len(vlans_w_dhcp_global):
                        if missing_vlans_str == "":
                            missing_vlans_str = vlan_h
                        else:
                            missing_vlans_str = missing_vlans_str + ", " + vlan_h
                        i = 0    
    
            if missing_vlans_str != "":
                if verification == "":
                    verification = "DHCP servers global missing in vlans -> " + missing_vlans_str
                else:
                    verification = verification + " & DHCP servers global missing in vlans -> " + missing_vlans_str

    return verification