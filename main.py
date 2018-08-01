import random

import threading
import time
import datetime
import argparse
import json
import requests

import MySQLdb
import boto3

DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "root"
DB_NAME = "prd_deployer"

PORT = 8778

#KICK_TPS = 600
KICK_TPS = 600
# PERIOD = 50
PERIOD = 50
BATCH_SIZE = KICK_TPS * PERIOD * 60
print "[INFO] BATCH_SIZE: {:,}".format(BATCH_SIZE)

#FAILURE_THRESHOLD = 60000
FAILURE_THRESHOLD = 60000


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


class RealConnector(object):
    """
    Information about a connector server.
    """
    def __init__(self, instance, module_name):
        self.stat_url_format = "http://{IP}:{PORT}/jolokia/read/{MODULE_NAME}:name=StatJmx/stat"
        self.close_url_format = "http://{IP}:{PORT}/jolokia/exec/{MODULE_NAME}:name=Controller/closeAll/{STEP_SIZE}/{INTERVAL}"
        self.module_name = module_name
        self.device_num = 0

        if type(instance) is dict:
            self._init_with_dict(instance)
        else:
            self.instance_id = instance.id
            self.ip = instance.private_ip_address
            self.name = ''
            for tag in instance.tags:
                if tag['Key'].lower() == 'name':
                    self.name = tag['Value']

    def _init_with_dict(self, instance):
        self.instance_id = instance['instance_id']
        self.ip = instance['ip']
        self.name = instance['name']

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
        step_size = int( float(self.device_num) / PERIOD / 60.0 + 0.5 )
        url = self.close_url_format.format(IP=self.ip, PORT=PORT, MODULE_NAME=self.module_name, STEP_SIZE=step_size, INTERVAL=1000)
        #----------
        print "Requesting URL: "+url
        #----------
        
        response = requests.get(url)


class FakeConnector(object):
    """
    Fake connector that emulates real behavior.
    """
    def __init__(self, instance, module_name):
        self.module_name = module_name
        self.device_num = random.randint(100000, 150000)

        self.close_start_time = 0
        self.close_flag = False

        if type(instance) is dict:
            self._init_with_dict(instance)
        else:
            self.instance_id = instance.id
            self.ip = instance.private_ip_address
            self.name = ''
            for tag in instance.tags:
                if tag['Key'].lower() == 'name':
                    self.name = tag['Value']

    def _init_with_dict(self, instance):
        self.instance_id = instance['instance_id']
        self.ip = instance['ip']
        self.name = instance['name']

    def get_online_device_number(self):
        if self.close_flag:
            now = time.time()
            self.device_num -= (now - self.last_access_time) * random.randint(50, 60)
            self.last_access_time = now
        if self.device_num < 0:
            self.device_num = 0
        return self.device_num

    def close_all_connections(self):
        self.close_flag = True
        self.close_start_time = time.time()
        self.last_access_time = self.close_start_time
        return True


def get_elb_instances(elb, args):
    # Remove this line:
    return ['i-00251efa09077080c', 'i-00918f726f10c15ab', 'i-0403ec61a2ef37e87', 'i-071228706f1310042', 'i-0a052b564af186fb9', 'i-0f3424c25212b39b9']
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
        print "[INFO] Removing these instances from ELB {0}: ".format(elb)
        for instance in instances:
            print "    {0} ({1})".format(instance.name, instance.ip)


def register_old_instances(elbs, instances):
    """Register remaining instances back to ELB(s)"""
    for elb in elbs:
        print "[INFO] Registering these instances with ELB {0}: ".format(elb)
        for instance in instances:
            print "    {0} ({1})".format(instance.name, instance.ip)


def close_all_connections(instances):
    """JMX exec closeAll multi-thread call"""
    print "[INFO] Calling closeAll on these instances:"
    for instance in instances:
        instance.close_all_connections()
        print "    {0} ({1})".format(instance.ip, instance.name)


def update_online_device_numbers(instances):
    """JMX stat.onlineDeviceNum multi-thread read"""
    for instance in instances:
        instance.get_online_device_number()
    pass


def create_output_file(instances):
    """Create output file and write table headers"""
    fp = open("output.csv", 'w')
    for instance in instances:
        fp.write(",{}".format(instance.name))
    fp.write('\n')
    fp.close()

def write_online_device_numbers(instances):
    """Append online device number data to output file"""
    print "[INFO] Current device numbers:"
    for instance in instances:
        print "    {}: {}".format(instance.name, instance.device_num)
    print "----------"
    fp = open("output.csv", 'a')
    fp.write(datetime.datetime.strftime(datetime.datetime.now(), "%H:%M:%S")+",")
    for instance in instances:
        fp.write("{},".format(instance.device_num))
    fp.write("\n")
    fp.close()


def main():
    pass

args = parse_args()

# Get old version instances registered with ELBs:
result = get_old_module(args)
elbs = result['load_balancers']
instances = result['instances']
elb_instance_ids = get_elb_instances(elbs, args)
instances_old_module = list()
for instance in instances:
    if instance['instance_id'] in elb_instance_ids:
        #instances_old_module.append(FakeConnector(instance, args.module))
        instances_old_module.append(RealConnector(instance, args.module))

# Group instances according to device number:
instances_to_kick = list()
total_device_num = 0
update_online_device_numbers(instances_old_module)
for instance in instances_old_module:
    total_device_num += instance.device_num
    if total_device_num >= BATCH_SIZE:
        print "[INFO] Total device num: {0}".format(total_device_num - instance.device_num)
        break
    else:
        instances_to_kick.append(instance)

create_output_file(instances_to_kick)

# Remove old instances from ELBs:
deregister_old_instances(elbs, instances_to_kick)
start_time = time.time()

# Send "closeAll" request to servers:
close_all_connections(instances_to_kick)

# check device number and wait for a full cycle:
while True:
    loop_start_time = time.time()
    update_online_device_numbers(instances_to_kick)
    write_online_device_numbers(instances_to_kick)
    if time.time() - start_time >= PERIOD * 60.0:
        break
    time.sleep(60.0 - (time.time() - loop_start_time))

# if a lot of devices are still online, move servers back into ELBs:
total_device_num = 0
for instance in instances_to_kick:
    total_device_num += instance.device_num
if total_device_num > FAILURE_THRESHOLD:
    print "[WARN] Too many devices still online: {} > {}".format(total_device_num, FAILURE_THRESHOLD)
    print "[WARN] Registering instances back with ELBs"
    register_old_instances(elbs, instances_to_kick)

if __name__ == "__main__":
    main()
