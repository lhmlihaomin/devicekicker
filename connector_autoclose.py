#!/usr/bin/python
# coding: utf8
#
# usage: connector_autoclose.py [-h] [-p PROFILE] [-r REGION]
#                               [-m MODULE_VERSION] [-e ELB [ELB ...]]
# 
# Close connector device connections.
# 
# optional arguments:
#   -h, --help            show this help message and exit
#   -p PROFILE, --profile PROFILE
#                         AWSCLi profile
#   -r REGION, --region REGION
#                         Region name
#   -m MODULE_VERSION, --module-version MODULE_VERSION
#                         Connector module version
#   -e ELB [ELB ...], --elb ELB [ELB ...]
#                         Load balancer names


import argparse
import json
import requests

import boto3

PORT = 8778
MODULE_NAME = "connector"
SLEEP_MS = 1000
BATCH_SIZE = 1500000

# CN: stat_url_format = ???
stat_url_format = "http://{IP}:{PORT}/jolokia/read/{MODULE_NAME}:name=StatJmx/stat"
# CN: close_url_format = "http://${IP}:{PORT}/jolokia/exec/${MODULE_NAME}:name=DeviceManager/closeAll/${BATCH_SIZE}"
close_url_format = "http://{IP}:{PORT}/jolokia/exec/{MODULE_NAME}:name=Controller/closeAll/{BATCH_SIZE}/{SLEEP_MS}"


class Connector(object):
    """
    Information about a connector server.
    """
    def __init__(self, instance):
        self.instance_id = instance.id
        self.ip = instance.private_ip_address
        self.device_num = 0
        
    def get_online_device_number(self):
        url = stat_url_format.format(IP=self.ip, PORT=PORT, MODULE_NAME=MODULE_NAME)
        response = requests.get(url)
        result = json.loads(response.text)
        self.device_num = result['value']['stat']['onlineDeviceNum']
        return self.device_num
        

def parse_args():
    """Define arguments"""
    argparser = argparse.ArgumentParser(description="Close connector device connections.")
    argparser.add_argument('-p', '--profile', help="AWSCLi profile")
    argparser.add_argument('-r', '--region', help="Region name")
    argparser.add_argument('-m', '--module-version', help="Connector module version")
    argparser.add_argument('-e', '--elb', nargs="+", help="Load balancer names")
    argparser.add_argument('-b', '--batch-size', type=int, help="Number of devices to kick in one batch")
    args = argparser.parse_args()
    return args


def get_connectors(profile, region, version):
    ec2_prefix = "prd-"+MODULE_NAME+"-"+version
    filters = [
        {'Name': 'tag:Name', 'Values': [ec2_prefix+"*"]},
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]
    session = boto3.Session(profile_name=profile, region_name=region)
    ec2 = session.resource('ec2')
    return ec2.instances.filter(Filters=filters)


def get_connector_addresses(profile, region, version):
    ec2_prefix = "prd-"+MODULE_NAME+"-"+version
    filters = [
        {'Name': 'tag:Name', 'Values': [ec2_prefix+"*"]},
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]
    session = boto3.Session(profile_name=profile, region_name=region)
    ec2 = session.resource('ec2')

    addresses = {}
    for instance in ec2.instances.filter(Filters=filters):
        addresses.update({instance.id: instance.private_ip_address})
    return addresses


# Get connector IPaddr list:


# Read onlineDeviceNum:

# Group connectors to kick:

# For each group:
    # Start timer (45min)

    # Deregister all connectors

    # Send closeAll request to all connectors in group:

    # Watch onlineDeviceNum, and wait for timer:

    # Register back the rest:



args = parse_args()
print args
#addresses = get_connector_addresses(args.profile, args.region, args.module_version)
#for instance_id, ip in addresses.items():
#    num = get_online_device_number(ip)
#    print ip
#    print num

for instance in get_connectors(args.profile, args.region, args.module_version):
    connector = Connector(instance)
    print connector.instance_id
    print connector.ip
    connector.get_online_device_number()
    print connector.device_num
    print "=========="
    
