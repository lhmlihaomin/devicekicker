# coding=utf-8

def get_instances_to_close():
    # Read "old" module EC2Instances:
    # Read instances registered with ELBs:
    # Get instances not only "old" and also registered:
    # Request device numbers:
    # How many instances to kick without exceeding limit:
    pass


def deregister():
    for elb in elbs:
        # Deregister instances:
        # Check if all instances have been removed:
        pass


def register():
    for elb in elbs:
        # Register instances:
        # Check if all instances have been registered
        pass


def get_device_numbers():
    pass


def create_output_file():
    pass


def write_device_numbers():
    pass


# main
def main():
    pass

instances = get_instances_to_close()
connectors = list()
for instance in instances:
    connectors.append(Connector(instance))

create_output_file()
time_start = time.time()
result = deregister()
if not result:
    register()
    raise Exception("")

while True:
    get_device_numbers()
    write_device_numbers()
    