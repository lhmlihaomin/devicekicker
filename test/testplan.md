TEST TOPOLOGY
-------------

    Connector1 (num1)
                       >  TestHost (connector_autoclose.py)
    Connector2 (num2)

    ( num1 < BATCH_SIZE < (num1+num2) )


TEST 01. RUN THRU TEST
----------------------
* add devices to sim connectors;
* run `device_num_monitor.py`;
* run `connector_autoclose.py`;
* collect device number data.


TEST 02. KICK SPEED TEST
------------------------
* deploy fake JMX responder;
* edit URL template in `connector_autoclose.py` to fake responder;
* add devices to sim connectors;
* run `device_num_monitor.py`;
* wait until batch timeout;
* check output.


TEST 03. INTERRUPTION TEST
--------------------------
TBD.
