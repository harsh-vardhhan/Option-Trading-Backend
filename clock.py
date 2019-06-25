from apscheduler.schedulers.blocking import BlockingScheduler
import os
import redis
from rq import Queue
import ast
import json

sched = BlockingScheduler()

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

#@sched.scheduled_job('interval', seconds=10)

def timed_job():
    for key in r.scan_iter("nifty*"):
        instrument = ast.literal_eval((r.get(key)).decode("utf-8"))
        symbol = (key).decode("utf-8")
        strike_price = (r.get("s_"+symbol)).decode("utf-8")

timed_job()

#sched.start()