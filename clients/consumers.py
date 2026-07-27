
## here first i write class Metric Consumer
import json
from channels.generic.websocket import (
    AsyncWebsocketConsumer,
)
'''
- here first i write class Metric Consumer for all the clients connected to FD 
- first clients connect in def connect
- then consumer receive the data from clients via def receive (although client here is dashboad)
and not sending any data just receiving
- yeah another listener is for group channel layer so it listens for any updates from the channel layer
to push it to the client with def send
- there is no ORM as of now. 
'''
class MetricsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # here client's instances connect to consumer and stay in memory
        self.group_name = 'metrics'
        # add to the group when they join
        await self.channel_layer.group_add(self.group_name,self.channel_name) # are they both different?
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def events_normal(self, event):
        data = event.get('content', {})
        await self.send(text_data=json.dumps({
            "type": "normal", 
            "message": "new metrics",
            "data": data
        }))
    async def events_alert(self, event):
        data = event.get('content',{})
        await self.send(text_data = json.dumps({
            "type": "alert", 
            "message":"high CPU alert for server",
            "data":data
        }))
    async def events_offline(self, event):
        data = event.get('content',{})
        await self.send(text_data = json.dumps({
            "type": "offline", 
            "message":"OFFLINE server detected",
            "data":data
        }))
