import os
from upstox_api.api import Session, Upstox, LiveFeedType
import json
import redis
from time import sleep

import numpy as np
import scipy.stats as si

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
redis_obj = redis.from_url(redis_url)

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
master_contract_FO = 'NSE_FO'


def full_quotes_queue(accessToken, symbol):
    upstox = Upstox(api_key, accessToken)
    upstox.get_master_contract(master_contract_FO)
    option = upstox.get_live_feed(upstox.get_instrument_by_symbol(
        master_contract_FO, symbol),
        LiveFeedType.Full)
    optionData = json.loads(json.dumps(option))
    redis_obj.set(symbol, optionData)


def instrument_subscribe_queue(access_token, exchange, a_symbol, b_symbol):
    u = Upstox(api_key, access_token)
    u.get_master_contract(master_contract_FO)
    u.subscribe(u.get_instrument_by_symbol(
        str(exchange),
        str(a_symbol)), LiveFeedType.Full)
    redis_obj.set(a_symbol+'_subscribed', access_token)
    u.subscribe(u.get_instrument_by_symbol(
        str(exchange),
        str(b_symbol)), LiveFeedType.Full)


def calcImpliedVol(S, K, T, P, r, sigma, type):
    # S: spot price
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


def cal_iv_queue(symbol ,S, K, T, P, r, sigma=0.25, tolerance=0.0001,type="call"):
    xnew = sigma
    xold = sigma - 1
    while abs(xnew - xold) > tolerance:
        xold = xnew
        xnew = xold - calcImpliedVol(S,K,T,P,r,xold,type=type)
        iv  = round(xnew * 100, 1)
    redis_obj.set(symbol+'_iv', iv)
