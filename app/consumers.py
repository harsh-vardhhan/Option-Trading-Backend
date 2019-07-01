from channels.generic.websocket import AsyncWebsocketConsumer
from upstox_api.api import Session, Upstox, LiveFeedType
import json
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from app.models import Full_Quote
import time
import itertools as it
from django.core.cache import cache
from rq import Queue
from worker import conn
from app.background_process import instrument_subscribe_queue
import redis
import os
from django.db import connection
import pdb
import threading

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)
api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'


def start_socket():
   list_options = Full_Quote.objects\
                            .all()\
                            .order_by('strike_price')
   connection.close()
   def to_lakh(n):
         return float(round(n/100000, 1))
   
   # r.set("access_token","0ed0271819b5be3bc2c3b762bdec2f93fc5bbc05")
   access_token = r.get("access_token").decode("utf-8")
   q = Queue(connection=conn)
   for a, b in it.combinations(list_options, 2):
      if (a.strike_price == b.strike_price):
         if to_lakh(a.oi) > 0.0 and to_lakh(b.oi) > 0.0:          
            subscribed_key = 'sub_'+a.symbol
            print(r.get(subscribed_key))
            if(r.get(subscribed_key) != None):
               print(r.get(subscribed_key).decode("utf-8"), access_token)
               if (r.get(subscribed_key).decode("utf-8") != access_token):
                  q.enqueue(instrument_subscribe_queue, 
                              access_token,
                              a.exchange, 
                              a.symbol, 
                              b.symbol)
   
   u = Upstox(api_key, r.get("access_token").decode("utf-8"))    
   u.get_master_contract('NSE_FO')
   u.get_master_contract('NSE_EQ')
   u.start_websocket(True)
   def quote_update(message):
      messageData = json.loads(json.dumps(message))
      symbol = (messageData['symbol'])
      r.set(symbol.lower(), json.dumps(message).encode("utf-8"))

   def websocket_stopped(message):
      u.start_websocket(True)

   u.set_on_quote_update(quote_update)
   u.set_on_disconnect (websocket_stopped)


