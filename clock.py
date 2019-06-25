from apscheduler.schedulers.blocking import BlockingScheduler
import os
import redis
from rq import Queue
import ast
import json
from upstox_api.api import Session, Upstox, LiveFeedType, OHLCInterval
from datetime import date
import numpy as np
import scipy.stats as si

sched = BlockingScheduler()

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
master_contract_FO = 'NSE_FO'

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

# NOTE token r.set only in DEV mode
#r.set("access_token", "25b244b45aa36c10205b6cd8898e8df8667b940e")
access_token = r.get("access_token").decode("utf-8")

#@sched.scheduled_job('interval', seconds=10)


def calcImpliedVol(S, K, T, P, r, sigma, type):
    # S: future spot price
    # K: strike price
    # T: time to maturity
    # C: Call value
    # r: interest rate
    # sigma: volatility of underlying asset
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    vega = (1 / np.sqrt(2 * np.pi)) * S * np.sqrt(T) * np.exp(-(si.norm.cdf(d1, 0.0, 1.0) ** 2) * 0.5)
    if type == "call":
        fx = S * si.norm.cdf(d1, 0.0, 1.0) - K * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0) - P
    elif type == "put":
        fx = K * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0) - S * si.norm.cdf(-d1, 0.0, 1.0) - P
    return fx / vega


def cal_iv(S, K, T, P, r, sigma=0.25, tolerance=0.0001,type="call"):
    xnew = sigma
    xold = sigma - 1
    while abs(xnew - xold) > tolerance:
        xold = xnew
        xnew = xold - calcImpliedVol(S,K,T,P,r,xold,type=type)
        iv  = round(xnew * 100, 1)
        return iv

def create_session():
        upstox = Upstox(api_key, access_token)
        return upstox

def timed_job():
        #values to be iterated
        symbol = "NIFTY"
        nse_index = 'NSE_INDEX'
        indices= "NIFTY_50"
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

        upstox.get_master_contract(nse_index)
        equity = upstox.get_live_feed(upstox.get_instrument_by_symbol(
            nse_index, indices),
            LiveFeedType.Full)
        equity_data = json.loads(json.dumps(equity))
        equity_price = equity_data["ltp"]

        for key in r.scan_iter(symbol.lower()+"*"):
                instrument = ast.literal_eval((r.get(key)).decode("utf-8"))
                symbol = (key).decode("utf-8")
                strike_price = float((r.get("s_"+symbol)).decode("utf-8"))
                
                if (symbol[-2:] =="ce" 
                        and strike_price > equity_price 
                        and instrument["oi"] > 0):                                      
                        r.set("iv_"+symbol,cal_iv(
                                future_price,
                                strike_price,
                                time_to_maturity,
                                instrument["ltp"], 
                                0.1, 
                                0.25,
                                0.0001, 
                                "call"
                                ))
                elif(symbol[-2:] =="pe" 
                        and strike_price < equity_price 
                        and instrument["oi"] > 0):
                        r.set("iv_"+symbol,cal_iv(
                                future_price,
                                strike_price,
                                time_to_maturity,
                                instrument["ltp"],
                                0.1,
                                0.25,
                                0.0001, 
                                "put"
                                ))

timed_job()

#sched.start()