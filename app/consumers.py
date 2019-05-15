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


api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
# ws://localhost:8000/ws/access_token/
# Use POST method to get the skeleton and WebSocket to feed independent cells
class stock_consumer(AsyncWebsocketConsumer):
    
   channel_layer = get_channel_layer()

   async def websocket_connect(self, event):
      await self.accept()
      await self.channel_layer.group_add("stock_group", self.channel_name)
      access_token = self.scope['url_route']['kwargs']['id']
      u = Upstox(api_key, access_token)    
      u.get_master_contract('NSE_FO')
      list_options = Full_Quote.objects.all().order_by('strike_price')
      for a, b in it.combinations(list_options, 2):
         if (a.strike_price == b.strike_price):
            if int(a.oi) > 0 and int(b.oi) > 0:
               q = Queue(connection=conn)
               q.enqueue(instrument_subscribe_queue, access_token, a.exchange, a.symbol, b.symbol)
      u.start_websocket(True)
      def quote_update(message):
         stock_consumer.send_message(self, message)
      u.set_on_quote_update(quote_update)
   
   async def websocket_receive(self, event):
      await self.send(text_data=json.dumps(event))
      
   async def websocket_disconnect(self, message):
      await self.channel_layer.group_discard('stock_grogup', self.channel_name)
      await self.close()

   def send_message(self, message):
      async_to_sync(self.channel_layer.group_send)("stock_group", {
         "type": "websocket_receive",
         "text": (message)    
      })