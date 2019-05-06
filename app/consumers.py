from channels.consumer import AsyncConsumer
from channels.layers import get_channel_layer
from app.fn_views import live_feed
from upstox_api.api import Session, Upstox, LiveFeedType
import json

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
channel_layer = get_channel_layer()
# ws://localhost:8000/ws/access_token/

class stock_consumer(AsyncConsumer):
   
   def event_handler_quote_update(message):
      print(message)

   async def websocket_connect(self, event):
      access_token = self.scope['url_route']['kwargs']['id']
      u = Upstox(api_key, access_token)
      u.set_on_quote_update(stock_consumer.event_handler_quote_update)
      u.get_master_contract('NSE_EQ')
      u.subscribe(u.get_instrument_by_symbol('NSE_EQ', 'RELIANCE'), LiveFeedType.LTP)
      u.subscribe(u.get_instrument_by_symbol('NSE_EQ', 'YESBANK'), LiveFeedType.LTP)
      u.start_websocket(False)

   async def websocket_receive(self, event):
      print(event)
      
   async def websocket_disconnect(self, message):
      pass