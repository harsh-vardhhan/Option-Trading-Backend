from channels.generic.websocket import AsyncWebsocketConsumer
from app.fn_views import live_feed
from upstox_api.api import Session, Upstox, LiveFeedType
import json
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
# ws://localhost:8000/ws/access_token/

class stock_consumer(AsyncWebsocketConsumer):
    
   channel_layer = get_channel_layer()

   async def websocket_connect(self, event):
      await self.accept()
      await self.channel_layer.group_add("stock_group", self.channel_name)
      access_token = self.scope['url_route']['kwargs']['id']
      u = Upstox(api_key, access_token)    
      u.get_master_contract('NSE_EQ')
      u.subscribe(u.get_instrument_by_symbol('NSE_EQ', 'RELIANCE'), LiveFeedType.LTP)
      u.subscribe(u.get_instrument_by_symbol('NSE_EQ', 'YESBANK'), LiveFeedType.LTP)
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
      print("before")
      async_to_sync(self.channel_layer.group_send)("stock_group", {
         "type": "websocket_receive",
         "text": (message)    
      })
      print("after")