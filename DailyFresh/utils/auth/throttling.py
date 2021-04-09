import sys
import time

import redis

"""限制用户段时间内登录次数的问题"""
r = redis.StrictRedis(host='127.0.0.1', port=6379, db=1)
try:
    id = sys.argv[1]
except:
    sys.exit(0)
# 将每次登录的时间存入redis的名为login_item列表中,判断列表元素的个数是否已达到5,并且和第一次登录时间比较是否在一小时以内
if r.llen('login_item') >= 5 and (time.time() - float(r.lindex('login_item', 4)) <= 3600):
    print('you are forbidden logining')
else:
    r.lpush('login_item', time.time())
