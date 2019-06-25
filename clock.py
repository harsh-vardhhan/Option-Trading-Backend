from apscheduler.schedulers.blocking import BlockingScheduler
import os
import redis
from rq import Queue
import ast
import json
from upstox_api.api import Session, Upstox, LiveFeedType, OHLCInterval
from datetime import date

sched = BlockingScheduler()

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
master_contract_FO = 'NSE_FO'

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

# NOTE token r.set only in DEV mode
#r.set("access_token", "25b244b45aa36c10205b6cd8898e8df8667b940e")
access_token = r.get("access_token").decode("utf-8")

#@sched.scheduled_job('interval', seconds=10)

def create_session():
        upstox = Upstox(api_key, access_token)
        return upstox

def timed_job():
        #values to be iterated
        symbol = "NIFTY"
        future_date = "19JUL"
        expiry_date = date(2019, 7, 25)

        today = date.today()
        days_to_expiry = expiry_date - today 
        time_to_maturity = (days_to_expiry.days)/365
          
        upstox = create_session()
        upstox.get_master_contract(master_contract_FO)
        future = upstox.get_live_feed(upstox.get_instrument_by_symbol(
            master_contract_FO, symbol+future_date+'FUT'),
            LiveFeedType.Full)
        future_data =  json.loads(json.dumps(future))
        future_price = future_data["ltp"]

        for key in r.scan_iter(symbol.lower()+"*"):
                instrument = ast.literal_eval((r.get(key)).decode("utf-8"))
                symbol = (key).decode("utf-8")
                strike_price = (r.get("s_"+symbol)).decode("utf-8")

timed_job()

#sched.start()