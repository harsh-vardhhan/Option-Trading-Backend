from channels.consumer import AsyncConsumer


class StockConsumer(AsyncConsumer):
     async def websocket_connect(self, event):
        print("connected", event)
        await self.send({
           "type": "websocket.accept"
        })

     async def websocket_receive(self, event):
        print("receive", event)

     async def websocket_disconnect(self, message):
        print("disconnected", event)