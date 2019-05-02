from channels.generic.websocket import WebsocketConsumer

class stock_consumer(WebsocketConsumer):
   def websocket_connect(self, event):
      print('Websocket Connected :-)')
      self.accept()

   def websocket_receive(self, event):
      text_data_json = json.loads(event)
      message = text_data_json['message']

      self.send(event=json.dumps({
         'message': message
      }))
   
   def websocket_disconnect(self, message):
      pass