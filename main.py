import threading
import time


DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "pass"
DB_NAME = "prd_deployer"

DEVNUM_THRESHOLD = 1000

class Connector(object):
    def __init__(self, device_num=10000):
        self.device_num = device_num

    def get_online_device_number(self):
        self.device_num = int(self.device_num * 0.72)
        print self.device_num
        return self.device_num


class ConnectorHandler(threading.Thread):
    def __init__(self, connector, period):
        threading.Thread.__init__(self)
        self.connector = connector
        self.period = period

    @property
    def device_number(self):
        return self.connector.device_num

    def run(self):
        # Initiate device "closeAll":
        pass
        now = time.time()
        start_time = now
        while True:
            now = time.time()
            # Read online device number:
            self.connector.get_online_device_number()
            # Check current time:
            if now - start_time >= self.period:
                break
            # Sleep 1 minute:
            time.sleep(1.0 - (time.time() - now))


def get_elb_instances():
    """Read ELB instances, group them into old and new."""
    pass


def deregister_old_instances():
    """Deregister old instances from ELB(s), and record time"""
    pass


def register_old_instances():
    """Register remaining instances back to ELB(s)"""
    pass


def main():
    # Remove old instances from ELBs:
    connectors_old, connectors_new = get_elb_instances(elbs)
    deregister_old_instances(elbs, connectors_old)
    start_time = time.time()

    # Send "closeAll" request to servers:
    close_all_connections(connectors_old)

    # check device number and wait for a full cycle:
    while True:
        get_online_device_number()
        now = time.time()
        if now - start_time >= period:
            break
        time.sleep(60.0)

    # if a lot of devices are still online, move servers back into ELBs:
    if sum(device_numbers) > failure_threshold:
        register_old_instances(elbs, connectors_old)


handlers = list()
for i in range(3):
    handlers.append(ConnectorHandler(Connector(), 10.0))

for handler in handlers:
    handler.start()

for handler in handlers:
    handler.join()

total = 0
for handler in handlers:
    total += handler.device_number

print "TOTAL: {0}".format(total)
if total > DEVNUM_THRESHOLD:
    print "Something went seriously wrong!"
else:
    print "OK."

