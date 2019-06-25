from apscheduler.schedulers.blocking import BlockingScheduler
import os
import redis
from rq import Queue
import ast

sched = BlockingScheduler()

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

#@sched.scheduled_job('interval', seconds=10)

def timed_job():
    for key in r.scan_iter("nifty*"):
        symbol_key =(r.get(key))
        symbol_decoded = symbol_key.decode("utf-8")
        option = ast.literal_eval(symbol_decoded)
        print(option["symbol"])

timed_job()

#sched.start()