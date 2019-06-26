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

'''
# ws://localhost:8000/ws/access_token/
# Use POST method to get the skeleton and WebSocket to feed independent cells
class stock_consumer(AsyncWebsocketConsumer):
    
   channel_layer = get_channel_layer()

   async def websocket_connect(self, event):
      await self.accept()
      await self.channel_layer.group_add("stock_group", self.channel_name)
      access_token = self.scope['url_route']['kwargs']['id']
      #symbol = self.scope['url_route']['kwargs']['symbol']
      u = Upstox(api_key, access_token)    
      u.get_master_contract('NSE_FO')
      list_options = Full_Quote.objects.all()\
                                       .order_by('strike_price')
      def to_lakh(n):
         return float(round(n/100000, 1))
      for a, b in it.combinations(list_options, 2):
         if (a.strike_price == b.strike_price):
            if to_lakh(a.oi) > 0.0 and to_lakh(b.oi) > 0.0:
               subscribed_key = a.symbol+'_subscribed'
               def get_key():
                  if(r.get(subscribed_key) == None):
                     return ""
                  else:
                     return r.get(subscribed_key).decode("utf-8")
               subscribed_access_token = get_key()

               if(r.exists(subscribed_key) == False):      
                     q = Queue(connection=conn)
                     q.enqueue(instrument_subscribe_queue, 
                               access_token, 
                               a.exchange, a.symbol, b.symbol)
               elif(r.exists(subscribed_key) == True
               and subscribed_access_token != access_token):
                     q = Queue(connection=conn)
                     q.enqueue(instrument_subscribe_queue, 
                               access_token, 
                               a.exchange, a.symbol, b.symbol)

      connection.close()   
      u.start_websocket(True)
      def quote_update(message):
         stock_consumer.send_message(self, message)
         messageData = json.loads(json.dumps(message))
         symbol = (messageData['symbol'])
         r.set(symbol, messageData)
      def websocket_stopped(message):
         u.start_websocket(True)
      u.set_on_disconnect (websocket_stopped)
      u.set_on_quote_update(quote_update)

         
   async def websocket_receive(self, event):
      await self.send(text_data=json.dumps(event))
      
   async def websocket_disconnect(self, message):
      await self.channel_layer.group_discard('stock_group', self.channel_name)

   def send_message(self, message):
      self.send(text_data=json.dumps(message))
      async_to_sync(self.channel_layer.group_send)("stock_group", {
         "type": "websocket_receive",
         "text": (message)    
      })
'''

def start_socket():
   u = Upstox(api_key, r.get("access_token").decode("utf-8"))    
   u.get_master_contract('NSE_FO')
   list_options = Full_Quote.objects\
                            .all()\
                            .order_by('strike_price')
   connection.close()
   def to_lakh(n):
         return float(round(n/100000, 1))

   access_token = r.get("access_token").decode("utf-8")

   for a, b in it.combinations(list_options, 2):
      if (a.strike_price == b.strike_price):
         if to_lakh(a.oi) > 0.0 and to_lakh(b.oi) > 0.0:
            q = Queue(connection=conn)
            q.enqueue(instrument_subscribe_queue, 
                        access_token, 
                        a.exchange, 
                        a.symbol, 
                        b.symbol
                     )

   def quote_update(message):
      messageData = json.loads(json.dumps(message))
      symbol = (messageData['symbol'])
      r.set(symbol, messageData)

   def websocket_stopped(message):
      u.start_websocket(True)

   u.set_on_quote_update(quote_update)
   u.start_websocket(True)
   u.set_on_disconnect (websocket_stopped)


