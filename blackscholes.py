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
import math
import itertools as it
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.cron import CronTrigger
import pytz

sched = BlockingScheduler()

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
master_contract_FO = 'NSE_FO'

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

# NOTE token r.set only in DEV mode
# r.set("access_token", "0ed0271819b5be3bc2c3b762bdec2f93fc5bbc05")
access_token = r.get("access_token").decode("utf-8")

from datetime import datetime, time

def is_time_between(begin_time, end_time, check_time=None):
    # If check time is not given, default to current UTC time
    tz = pytz.timezone('Asia/Kolkata')
    check_time = check_time or datetime.now(tz).time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else: # crosses midnight
        return check_time >= begin_time or check_time <= end_time


def Greeks_call (S, X, T, r, sigma):
    d1 = (math.log (S/X) + (r + (sigma * sigma) / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt (T)
    Delta_call = si.norm.cdf(d1)
    Gamma = si.norm.pdf(d1) / (S * sigma * math.sqrt(T))
    Vega = (S * math.sqrt(T) * si.norm.pdf(d1))/100
    Theta_call = (-(S * sigma * si.norm.pdf(d1)) / (2 * math.sqrt(T)) - r * X * math.exp(-r * T) * si.norm.cdf(d2))/365
    return (Delta_call, Gamma, Vega, Theta_call)

def Greeks_put (S, X, T, r, sigma):
        d1 = (math.log (S/X) + (r + (sigma * sigma) / 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt (T)
        Delta_put = si.norm.cdf(d1) - 1
        Gamma = si.norm.pdf(d1) / (S * sigma * math.sqrt(T))
        Vega = (S * math.sqrt(T) * si.norm.pdf(d1))/100
        Theta_put = (-(S * sigma * si.norm.pdf(d1)) / (2 * math.sqrt(T)) + r * X * math.exp(-r * T) * si.norm.cdf(-d2))/365
        return (Delta_put, Theta_put)

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





@sched.scheduled_job('interval', seconds=10)
def timed_job():
                def create_session():
                        upstox = Upstox(api_key, r.get("access_token").decode("utf-8"))
                        return upstox
                print("****Running Black Scholes")
                if is_time_between(time(9,15),time(15,30)):
                        upstox = create_session()
                        #values to be iterated
                        symbol_1 = "NIFTY"
                        indices_1= "NIFTY_50"
                        
                        symbol_2 = "BANKNIFTY"
                        indices_2= "NIFTY_BANK"
                        
                        nse_index = 'NSE_INDEX'
                        future_date = "19JUL"
                        expiry_date = date(2019, 7, 25)

                        symbols = []
                        symbol_indices_2 = (symbol_2, indices_2)
                        symbol_indices_1 = (symbol_1, indices_1)
                        symbols.append(symbol_indices_1)
                        symbols.append(symbol_indices_2)

                        for symbol in symbols:
                                today = date.today()
                                days_to_expiry = expiry_date - today
                                r.set("days_to_expiry", days_to_expiry.days)
                                time_to_maturity = (days_to_expiry.days)/365
                                
                                
                                upstox.get_master_contract(master_contract_FO)
                                future = upstox.get_live_feed(upstox.get_instrument_by_symbol(
                                        master_contract_FO, symbol[0]+future_date+'FUT'),
                                        LiveFeedType.Full)
                                future_data = json.loads(json.dumps(future))
                                future_price = future_data["ltp"]
                                r.set("future_price"+symbol[0], future_price)

                                upstox.get_master_contract(nse_index)
                                equity = upstox.get_live_feed(upstox.get_instrument_by_symbol(
                                        nse_index, symbol[1]),
                                        LiveFeedType.Full)
                                equity_data = json.loads(json.dumps(equity))
                                equity_price = equity_data["ltp"]
                                equity_symbol = equity_data["symbol"]
                                r.set("stock_symbol"+symbol[0], equity_symbol)
                                r.set("stock_price"+symbol[0], equity_price)

                                call_OI = 0.0
                                put_OI = 0.0
                                biggest_OI = 0.0
                                iv = 0
                                def to_lakh(n):
                                        return float(round(n/100000, 1))
                                closest_strike = 10000000
                                closest_option = ""
                        
                                for key in r.scan_iter((symbol[0]).lower()+"*"):
                                        #print(key)
                                        instrument_symbol = key.decode('utf-8')
                                        instrument = json.loads(r.get(key).decode('utf-8'))


                                        if(to_lakh(instrument.get("oi")) > 0.0):
                                                instrument_symbol = (key).decode("utf-8")

                                                if r.get("s_"+instrument_symbol) != None:    
                          
                                                        strike_price = float(r.get("s_"+instrument_symbol).decode('utf-8'))
                                                        diff = abs(float(r.get("stock_price"+symbol[0])) - strike_price)

                                                        if(diff < closest_strike):
                                                                closest_strike = diff
                                                                closest_option = strike_price

                                                        if(to_lakh(instrument.get("oi")) > biggest_OI):
                                                                biggest_OI = to_lakh(instrument.get("oi"))

                                                        if (instrument_symbol[-2:] == "ce"):
                                                                call_OI = call_OI + to_lakh(instrument["oi"])
                                                                if (strike_price > equity_price):
                                                                        iv = cal_iv(
                                                                                future_price,
                                                                                strike_price,
                                                                                time_to_maturity,
                                                                                instrument["ltp"], 
                                                                                0.1, 
                                                                                0.25,
                                                                                0.0001, 
                                                                                "call"
                                                                                )
 
                                                                        r.set("iv_"+instrument_symbol, iv)
                                        
                                                        elif(instrument_symbol[-2:] =="pe"):
                                                                put_OI = put_OI + to_lakh(instrument["oi"])
                                                                if (strike_price < equity_price):
                                                                        iv = cal_iv(
                                                                                future_price,
                                                                                strike_price,
                                                                                time_to_maturity,
                                                                                instrument["ltp"], 
                                                                                0.1, 
                                                                                0.25,
                                                                                0.0001, 
                                                                                "put"
                                                                                )
                                                                        r.set("iv_"+instrument_symbol, iv)

                                                        if iv == 0:
                                                                iv = 10
                                                        elif iv < 0:
                                                                iv = abs(iv)

                                                        Delta_call, Gamma, Vega, Theta_call = Greeks_call( 
                                                                future_price,
                                                                strike_price,
                                                                time_to_maturity,
                                                                0.1,
                                                                iv
                                                                )
                                                        Delta_put, Theta_put = Greeks_put( 
                                                                future_price,
                                                                strike_price,
                                                                time_to_maturity,
                                                                0.1,
                                                                iv
                                                                )
                                                        Gamma_val = round(Gamma, 3)
                                                        Vega_val = round(Vega, 2)
                                                        Delta_call_val = round(Delta_call, 2) 
                                                        Theta_call_val = round(Theta_call, 2) 
                                                        Delta_put_val = round(Delta_put, 2)
                                                        Theta_put_val = round(Theta_put, 2) 
                                                        r.set("g_"+instrument_symbol[:-2],Gamma_val)
                                                        r.set("v_"+instrument_symbol[:-2],Vega_val)
                                                        r.set("dc_"+instrument_symbol[:-2],Delta_call_val)
                                                        r.set("tc_"+instrument_symbol[:-2],Theta_call_val)
                                                        r.set("dp_"+instrument_symbol[:-2],Delta_put_val)
                                                        r.set("tp_"+instrument_symbol[:-2],Theta_put_val)
                                                
                                                
                                
                                if call_OI == 0.0:
                                        call_OI = 1.0
                                pcr = round(put_OI/call_OI, 2)
                                r.set("biggest_OI" + symbol[0],biggest_OI)
                                r.set("closest_strike" + symbol[0]+future_date,closest_option)
                                r.set("PCR"+symbol[0] + future_date,pcr)

sched.start()
# timed_job()