from channels.consumer import AsyncConsumer


class stock_consumer(AsyncConsumer):
     async def websocket_connect(self, event):
        print('Hiiiiii')
        print("connected", event)

     async def websocket_receive(self, event):
        print("receive", event)

     async def websocket_disconnect(self, message):
        print("disconnected", event)