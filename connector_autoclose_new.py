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
import sys

import boto3

PORT = 8778
SLEEP_MS = 1000
BATCH_SIZE = 1800000

# CN: stat_url_format = ???
stat_url_format = "http://{IP}:{PORT}/jolokia/read/{MODULE_NAME}:name=StatJmx/stat"

# CN: close_url_format = "http://${IP}:{PORT}/jolokia/exec/${MODULE_NAME}:name=DeviceManager/closeAll/${BATCH_SIZE}"
close_url_format = "http://{IP}:{PORT}/jolokia/exec/{MODULE_NAME}:name=Controller/closeAll/{STEP_SIZE}/1000"


class Connector(object):
    """
    Information about a connector server.
    """
    def __init__(self, instance, module_name):
        self.module_name = module_name
        self.instance_id = instance.id
        self.ip = instance.private_ip_address
        self.device_num = 0
        self.name = ''
        for tag in instance.tags:
            if tag['Key'].lower() == 'name':
                self.name = tag['Value']

    def get_online_device_number(self):
        url = stat_url_format.format(IP=self.ip, PORT=PORT, MODULE_NAME=self.module_name)
        response = requests.get(url)
        result = json.loads(response.text)
        # GLOBAL: self.device_num = result['value']['stat']['onlineDeviceNum']
        # CN: self.device_num = result['value']['stat.onlineDeviceNum']['count']
        self.device_num = result['value']['stat']['onlineDeviceNum']
        return self.device_num


def parse_args():
    """Define arguments"""
    argparser = argparse.ArgumentParser(description="Close connector device connections.")
    argparser.add_argument('-p', '--profile', help="AWSCLi profile")
    argparser.add_argument('-r', '--region', help="Region name")
    argparser.add_argument('-m', '--module', help="Connector module name")
    argparser.add_argument('-v', '--version', help="Module version")
    argparser.add_argument('-e', '--elb', nargs="+", help="Load balancer names")
    argparser.add_argument('-b', '--batch-size', type=int, help="Number of devices to kick in one batch")
    args = argparser.parse_args()
    return args


def get_connectors(profile, region, module_name, version):
    ec2_prefix = "prd-"+module_name+"-"+version
    filters = [
        {'Name': 'tag:Name', 'Values': [ec2_prefix+"*"]},
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]
    session = boto3.Session(profile_name=profile, region_name=region)
    ec2 = session.resource('ec2')
    return ec2.instances.filter(Filters=filters)


def get_connector_addresses(profile, region, module_name, version):
    ec2_prefix = "prd-"+module_name+"-"+version
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
#addresses = get_connector_addresses(args.profile, args.region, args.module_version)
#for instance_id, ip in addresses.items():
#    num = get_online_device_number(ip)
#    print ip
#    print num

connectors = []
for instance in get_connectors(args.profile, args.region, args.module, args.version):
    connector = Connector(instance, args.module)
    #print connector.instance_id
    #print connector.ip
    connector.get_online_device_number()
    print connector.name
    print connector.device_num
    print "--------------------"
    connectors.append(connector)

total_device_num = 0
connector_num = len(connectors)
for connector in connectors:
    total_device_num += connector.device_num


connectors.sort(key=lambda x: x.name)
groups = list()
group = list()
size = 0
for connector in connectors:
    if size + connector.device_num > BATCH_SIZE:
        groups.append(group)
        group = list()
        group.append(connector)
        size = connector.device_num
    else:
        size += connector.device_num
        group.append(connector)
groups.append(group)

print "===================="

for i, g in enumerate(groups):
    with open('connector_close.'+str(i)+".sh", 'w') as fp:
        print "####################"
        print "###    GROUP     ###"
        print "####################"
        sum = 0
        for connector in g:
            print connector.name
            print connector.device_num
            print "--------------------"
            sum += connector.device_num

            step_size = int(connector.device_num / 3000)
            cmd = "curl http://{IP}:{PORT}/jolokia/exec/{MODULE_NAME}:name=Controller/closeAll/{STEP_SIZE}/1000".format(IP=connector.ip, PORT=PORT, MODULE_NAME=args.module, STEP_SIZE=step_size)
            fp.write(cmd)
            fp.write("\n")
            fp.write("echo ''\n")
        print "--------------------"
        print "SUM: "+str(sum)


