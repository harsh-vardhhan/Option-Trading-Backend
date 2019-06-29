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
    optionData = json.dumps(option).encode('utf-8')
    redis_obj.set(symbol, optionData)


def instrument_subscribe_queue(access_token, exchange, a_symbol, b_symbol):
    u = Upstox(api_key, access_token)
    u.get_master_contract(master_contract_FO)
    u.subscribe(u.get_instrument_by_symbol(
        str(exchange),
        str(a_symbol)), LiveFeedType.Full)
    redis_obj.set('sub_'+a_symbol, access_token)
    u.subscribe(u.get_instrument_by_symbol(
        str(exchange),
        str(b_symbol)), LiveFeedType.Full)



