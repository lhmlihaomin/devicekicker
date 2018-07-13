import threading
import time
import argparse
import json
import requests

import MySQLdb
import boto3

DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "root"
DB_NAME = "prd_deployer"

KICK_TPS = 600
PERIOD = 50
BATCH_SIZE = KICK_TPS * PERIOD * 60

DEVNUM_THRESHOLD = 1000


def parse_args():
    """Define arguments"""
    argparser = argparse.ArgumentParser(description="Close connector device connections.")
    argparser.add_argument('-p', '--profile', help="AWSCLi profile")
    argparser.add_argument('-r', '--region', help="Region name")
    argparser.add_argument('-m', '--module', help="Connector module name")
    argparser.add_argument('-v', '--version', help="Module version")
    argparser.add_argument('-e', '--elbs', nargs="+", help="Load balancer names")
    argparser.add_argument('-b', '--batch-size', type=int, help="Number of devices to kick in one batch")
    args = argparser.parse_args()
    return args


def get_old_module(args):
    conn = MySQLdb.connect(DB_HOST, DB_USER, DB_PASS)
    conn.select_db(DB_NAME)
    c = conn.cursor()

    sql = """
SELECT id, load_balancer_names FROM updateplanmgr_module WHERE 
name='{0}' AND 
current_version='{1}' AND 
profile_id=(
  SELECT id FROM awscredentialmgr_awsprofile WHERE name='{2}'
) AND 
region_id=(
  SELECT id FROM awscredentialmgr_awsregion WHERE name='{3}'
)"""
    sql = sql.format(args.module, args.version, args.profile, args.region)
    c.execute(sql)
    row = c.fetchone()
    module_id = row[0]
    elbs = row[1].split(',')
    elbs = [elb.strip() for elb in elbs]

    sql = """
SELECT id, name, instance_id, private_ip_address FROM ec2mgr_ec2instance WHERE id IN (
  SELECT ec2instance_id FROM updateplanmgr_module_instances WHERE module_id={0}
)
""".format(module_id)
    c.execute(sql)
    rows = c.fetchall()
    ret = {
        'load_balancers': elbs,
        'instances': []
    }
    for row in rows:
        ret['instances'].append({
            'name': row[1],
            'instance_id': row[2],
            'ip': row[3]
        })
    return ret


class Connector(object):
    """
    Information about a connector server.
    """
    def __init__(self, instance, module_name):
        self.stat_url_format = "http://{IP}:{PORT}/jolokia/read/{MODULE_NAME}:name=StatJmx/stat"
        self.close_url_format = "http://{IP}:{PORT}/jolokia/exec/{MODULE_NAME}:name=Controller/closeAll/{STEP_SIZE}/{INTERVAL}"
        self.module_name = module_name
        self.instance_id = instance.id
        self.ip = instance.private_ip_address
        self.device_num = 0
        self.name = ''
        for tag in instance.tags:
            if tag['Key'].lower() == 'name':
                self.name = tag['Value']

    def get_online_device_number(self):
        """Call JMX 'stat' to get onlineDeviceNum"""
        url = self.stat_url_format.format(IP=self.ip, PORT=PORT, MODULE_NAME=self.module_name)
        response = requests.get(url)
        result = json.loads(response.text)
        # GLOBAL: self.device_num = result['value']['stat']['onlineDeviceNum']
        # CN: self.device_num = result['value']['stat.onlineDeviceNum']['count']
        self.device_num = result['value']['stat']['onlineDeviceNum']
        return self.device_num

    def close_all_connections(self):
        """Call JMX 'exec/closeAll' to kick all connected devices"""
        pass


def get_elb_instances(elb, args):
    """Get instance ids registered with this ELB"""
    s = boto3.Session(profile_name=args.profile, region_name=args.region)
    elb = s.client('elb')
    result = elb.describe_load_balancers(
        LoadBalancerNames=['prd-elb-connectorNC-aps1-0']
    )
    result = result['LoadBalancerDescriptions'][0]
    elb_instance_ids = [x['InstanceId'] for x in result['Instances']]
    return elb_instance_ids

 

def deregister_old_instances(elbs, instances):
    """Deregister old instances from ELB(s), and record time"""
    for elb in elbs:
        print "Removing these instances from ELB {0}: ".format(elb)
        print "    {0}".format(", ".join([x['name'] for x in instances]))


def register_old_instances(elbs, instances):
    """Register remaining instances back to ELB(s)"""
    for elb in elbs:
        print "Registering these instances with ELB {0}: ".format(elb)
        print "    {0}".format(", ".join([x['name'] for x in instances]))


def close_all_connections(instances):
    """JMX exec closeAll multi-thread call"""
    print "Calling closeAll on these instances:"
    for instance in instances:
        print "    {0} ({1})".format(instance['ip'], instance['name'])


def get_online_device_numbers(connectors):
    """JMX stat.onlineDeviceNum multi-thread read"""
    pass


def write_online_device_numbers(connectors):
    """Append online device number data to output file"""
    pass

def main():
    pass

args = parse_args()
# Remove old instances from ELBs:
#connectors_old, connectors_new = get_elb_instances(elbs)
result = get_old_module(args)
elbs = result['load_balancers']
instances = result['instances']
elb_instance_ids = get_elb_instances(args.elbs[0], args)
instances_old_module = list()
for instance in instances:
    if instance['instance_id'] in elb_instance_ids:
        instances_old_module.append(instance)
print instances_old_module

# Group instances according to device number:
instances_to_kick = list()
total_device_num = 0
for instance in instances:
    total_device_num += instance.device_num
    if total_device_num >= BATCH_SIZE:
        break
    else:
        instances_to_kick.append(instance)
        

deregister_old_instances(elbs, instances_to_kick)
start_time = time.time()

# Send "closeAll" request to servers:
close_all_connections(instances_to_kick)

# check device number and wait for a full cycle:
while True:
    loop_start_time = time.time()
    get_online_device_numbers()
    write_online_device_numbers()
    if time.time() - start_time >= period:
        break
    time.sleep(60.0 - (time.time() - loop_start_time))

# if a lot of devices are still online, move servers back into ELBs:
if sum(device_numbers) > failure_threshold:
    register_old_instances(elbs, instances_to_kick)

if __name__ == "__main__":
    main()
