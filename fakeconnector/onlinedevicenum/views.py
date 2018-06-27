# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
import json

from django.shortcuts import render
from django.http import HttpResponse

from onlinedevicenum.models import DeviceNum

ret_tpl = {
    'value': {
        'stat.onlineDeviceNum': {
            'count': 0
        }
    }
}

def stat(request):
    num = DeviceNum.get_num()
    ret = ret_tpl
    ret['value']['stat.onlineDeviceNum']['count'] = num
    return HttpResponse(json.dumps(ret), content_type='text/plain')


def set_device_num(request, num):
    if num is None or int(num) == 0:
        num = random.randint(0, 200000)
    else:
        num = int(num)
    DeviceNum.set_num(num)
    ret = ret_tpl
    ret['value']['stat.onlineDeviceNum']['count'] = num
    return HttpResponse(json.dumps(ret), content_type='text/plain')


def initiate_close_all(request, batch):
    if batch is None or int(batch) == 0:
        batch = 30
    DeviceNum.initiate_close_all(int(batch))
    return HttpResponse(DeviceNum.status(), content_type='text/plain')


def status(request):
    return HttpResponse(DeviceNum.status(), content_type='text/plain')
