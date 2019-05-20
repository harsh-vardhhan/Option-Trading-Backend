import os
from upstox_api.api import Session, Upstox, LiveFeedType
import json
import redis
from time import sleep

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
master_contract_FO = 'NSE_FO'


def full_quotes_queue(accessToken, symbol):
    upstox = Upstox(api_key, accessToken)
    upstox.get_master_contract(master_contract_FO)
    option = upstox.get_live_feed(upstox.get_instrument_by_symbol(
        master_contract_FO, symbol),
        LiveFeedType.Full)
    optionData = json.loads(json.dumps(option))
    r.set(symbol, optionData)

def instrument_subscribe_queue(access_token, exchange, a_symbol, b_symbol):
    u = Upstox(api_key, access_token)
    u.get_master_contract(master_contract_FO)
    u.subscribe(u.get_instrument_by_symbol(
        str(exchange),
        str(a_symbol)), LiveFeedType.Full)
    r.set(a_symbol+'_subscribed', access_token)
    u.subscribe(u.get_instrument_by_symbol(
        str(exchange),
        str(b_symbol)), LiveFeedType.Full)

