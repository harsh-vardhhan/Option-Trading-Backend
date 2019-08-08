from rq import Queue
from worker import conn
from app.background_process import live_feed_queue, update_option_queue
import redis
import os

symbols = ['nifty', 'banknifty', 'reliance']
redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)
api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'


def start_subscription():
    q = Queue(connection=conn)
    for symbol in symbols:
        for key in r.scan_iter(symbol+"*"):
            access_token = r.get("access_token").decode("utf-8")
            instrument = key.decode('utf-8')
            q.enqueue(live_feed_queue, access_token, 'NSE_FO', instrument)


def start_update_option():
    q = Queue(connection=conn)
    for symbol in symbols:
        for key in r.scan_iter(symbol+"*"):
            access_token = r.get("access_token").decode("utf-8")
            instrument = key.decode('utf-8')
            q.enqueue(update_option_queue, access_token, 'NSE_FO', instrument)
