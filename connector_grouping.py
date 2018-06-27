#!/usr/bin/python
# coding:utf8

with open('devicenum.txt', 'r') as fp:
    txt = fp.readlines()

nums = []
for t in txt:
    nums.append(int(float(t)))
print nums

BATCH = 800000

groups = list()
group = list()
size = 0
for num in nums:
    print size + num
    if size + num > BATCH:
        groups.append(group)
        group = list()
        group.append(num)
        size = num
    else:
        size += num
        group.append(num)
    print group
groups.append(group)


