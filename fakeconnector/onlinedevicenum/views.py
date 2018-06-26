# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random

from django.shortcuts import render
from django.http import HttpResponse

from onlinedevicenum.models import DeviceNum


def stat(request):
    num = DeviceNum.get_num()
    return HttpResponse(str(num), content_type='text/plain')


def set_device_num(request, num):
    if num is None or int(num) == 0:
        num = random.randint(0, 200000)
    else:
        num = int(num)
    DeviceNum.set_num(num)
    return HttpResponse(str(num), content_type='text/plain')


def initiate_close_all(request):
    DeviceNum.initiate_close_all()
    return HttpResponse("OK", content_type='text/plain')


def status(request):
    return HttpResponse(DeviceNum.status(), content_type='text/plain')
