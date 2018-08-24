# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
import threading
import time
import json
import random


class DeviceNum(models.Model):
    _total = 0
    _num = 0
    _timestamp = 0.0
    _closing = False
    _lock = threading.Lock()
    _batch = 0

    @classmethod
    def set_num(cls, num):
        with cls._lock:
            cls._closing = False
            cls._num = num
            cls._total = num
            
    @classmethod
    def initiate_close_all(cls, batch):
        with cls._lock:
            cls._closing = True
            cls._timestamp = time.time()
            cls._batch = batch

    @classmethod
    def get_num(cls):

        #return [cls._num, cls._closing, cls._timestamp]

        if not cls._closing:
            return cls._num
        else:
            period = time.time() - cls._timestamp
            num = cls._total - int(period) * cls._batch
            if num < 0:
                cls._num = 0
                cls._closing = False
                return cls._num
            else:
                cls._num = num
                return num

    @classmethod
    def status(cls):
        d = {
            'num': cls._num,
            'timestamp': cls._timestamp,
            'closing': cls._closing,
            'batch': cls._batch,
        }
        return json.dumps(d, indent=4)
