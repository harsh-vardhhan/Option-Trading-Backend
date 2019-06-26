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
import itertools as it

sched = BlockingScheduler()

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
master_contract_FO = 'NSE_FO'

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

# NOTE token r.set only in DEV mode
#r.set("access_token", "a76f263585d1d9500fa4af77f7c966cfc1daaf84")
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

'''
TODO move closest strike and PCR on worker
'''
def timed_job():
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
                
                upstox = create_session()
                upstox.get_master_contract(master_contract_FO)
                future = upstox.get_live_feed(upstox.get_instrument_by_symbol(
                master_contract_FO, symbol[0]+future_date+'FUT'),
                LiveFeedType.Full)
                future_data =  json.loads(json.dumps(future))
                future_price = future_data["ltp"]
                r.set(symbol[0]+"future_price", future_price)

                upstox.get_master_contract(nse_index)
                equity = upstox.get_live_feed(upstox.get_instrument_by_symbol(
                nse_index, symbol[1]),
                LiveFeedType.Full)
                equity_data = json.loads(json.dumps(equity))
                equity_price = equity_data["ltp"]
                equity_symbol = equity_data["symbol"]
                r.set(symbol[0]+"stock_symbol", equity_symbol)
                r.set(symbol[0]+"stock_price", equity_price)

                '''
                for a, b in it.combinations(r.scan_iter((symbol[0]).lower()+"*"), 2):
                        instrument_a = ast.literal_eval((r.get(a)).decode("utf-8"))
                        instrument_b = ast.literal_eval((r.get(b)).decode("utf-8"))
                        instrument_symbol_a = (a).decode("utf-8")
                        instrument_symbol_b = (b).decode("utf-8")
                        strike_price_a = float((r.get("s_"+instrument_symbol_a).decode("utf-8")))
                        strike_price_b = float((r.get("s_"+instrument_symbol_b).decode("utf-8")))
                        
                        symbol_call = ""
                        symbol_put = ""                   


                        if (instrument_symbol_a[-2:] == "ce"):
                                symbol_call = instrument_symbol_a
                        else:
                                symbol_put = instrument_symbol_a

                        if (instrument_symbol_b[-2:] == "ce"):
                                symbol_call = instrument_symbol_b
                        else:
                                symbol_put = instrument_symbol_b

                        if (strike_price_a == strike_price_b):
                                print(symbol_call, symbol_put)
                '''

                call_OI = 0.0
                put_OI = 0.0
                def to_lakh(n):
                        return float(round(n/100000, 1))
                closest_strike = 10000000
                closest_option = ""
         
                for key in r.scan_iter((symbol[0]).lower()+"*"):
                        instrument = ast.literal_eval((r.get(key)).decode("utf-8"))
                        instrument_symbol = (key).decode("utf-8")
                        strike_price = float((r.get("s_"+instrument_symbol).decode("utf-8")))
                        diff = abs(float(r.get(symbol[0]+"stock_price")) - strike_price)
                
                        if(to_lakh(instrument["oi"]) > 0.0):

                                if(diff < closest_strike):
                                        closest_strike = diff
                                        closest_option = strike_price

                                if (instrument_symbol[-2:] =="ce"):
                                        call_OI = call_OI + to_lakh(instrument["oi"])
                                        if (strike_price > equity_price):                               
                                                r.set("iv_"+instrument_symbol,cal_iv(
                                                        future_price,
                                                        strike_price,
                                                        time_to_maturity,
                                                        instrument["ltp"], 
                                                        0.1, 
                                                        0.25,
                                                        0.0001, 
                                                        "call"
                                                        ))
                     
                                elif(instrument_symbol[-2:] =="pe"):
                                        put_OI = put_OI + to_lakh(instrument["oi"])
                                        if (strike_price < equity_price):
                                                r.set("iv_"+instrument_symbol,cal_iv(
                                                        future_price,
                                                        strike_price,
                                                        time_to_maturity,
                                                        instrument["ltp"],
                                                        0.1,
                                                        0.25,
                                                        0.0001, 
                                                        "put"
                                                        ))
                
                if call_OI == 0.0:
                        call_OI = 1.0 
                pcr = round(put_OI/call_OI, 2)
                r.set(symbol[0]+future_date+"closest_strike",closest_option)
                r.set(symbol[0]+future_date+"PCR",pcr)

timed_job()

#sched.start()