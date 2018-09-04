from django.conf.urls import url, include

from onlinedevicenum import views

urlpatterns = [
    url(r'^read/fakeconnector', views.stat),
    url(r'^exec/fakeconnector:name=Controller/closeAll/([0-9]+)/', views.initiate_close_all),
    url(r'^set/([0-9]+)', views.set_device_num),
    url(r'status', views.status),
]
