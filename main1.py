import MySQLdb
import argparse


DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "root"
DB_NAME = "prd_deployer"


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




args = parse_args()


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
SELECT * FROM ec2mgr_ec2instance WHERE id IN (
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
            'instance_id': row[2]
        })
    return ret


ret = get_old_module(args)

import json
for elb in ret['load_balancers']:
    instance_ids = []
    for instance in ret['instances']:
        instance_ids.append({'InstanceId': instance['instance_id']})
    s = """
deregister_instances_from_load_balancer(
    LoadBalancerName='{0}',
    Instances={1}
)
"""
    print s.format(elb, json.dumps(instance_ids, indent=4))

