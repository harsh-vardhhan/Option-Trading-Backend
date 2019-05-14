import os
from upstox_api.api import Session, Upstox, LiveFeedType
import json
import redis

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
master_contract_FO = 'NSE_FO'

def full_quotes_queue(accessToken, symbol):
    print("*********** WORKER ***********")
    upstox = Upstox(api_key, accessToken)
    upstox.get_master_contract(master_contract_FO)
    option = upstox.get_live_feed(upstox.get_instrument_by_symbol(
        master_contract_FO, symbol),
        LiveFeedType.Full)
    optionData = json.loads(json.dumps(option))
    r.set(symbol, optionData)