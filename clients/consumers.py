
## here first i write class Metric Consumer
import json
from channels.generic.websocket import (
    AsyncWebsocketConsumer,
)
from channels.db import database_sync_to_async
# from .models import Metrics
from django.core.serializers.json import DjangoJSONEncoder
import json
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
    async def dispatch(self, message):
        
        try:
            await super().dispatch(message)
        except AttributeError as e:
            print(f"Routing failed for type {message.get('type')}: {e}")
    async def receive(self, text_data = None,bytes_data = None):
        print(f'received text from Client {text_data}')
        json_data = json.loads(text_data)
        last_id = json_data['last_seq_id']

        print(f'id sent from Client {last_id}')
        # received data from client uppon reconnection
        # need to fire ORM to find and send back data from last id - latest id-1
        # kinda of like a loop through from last seq-id
        lost_messages = await self.fetch_missed_alert(last_id)
        # lost_messages = json.dumps(lost_messages)
        print(f'messages that were lost {len(lost_messages)}')
        # lost_messages['time_stamp'] = datetime.now().isoformat(),
        await self.send(text_data = json.dumps({
            "type":"recovery_data",
            "messages":lost_messages

        },cls=DjangoJSONEncoder))
    async def events_normal(self, event):
        data = event.get('content', {})
        print(f'Normal event sent from consumer {data}')
        await self.send(text_data=json.dumps({
            "type": "normal", 
            "message": "new metrics",
            "data": data
        }))
        # await self.send(json.loads())
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


    # @database_sync_to_async
    # def fetch_missed_alert(self, last_id):
    #     from .models import Metrics
    #     return list(
    #         Metrics.objects.filter(id__gt=last_id)
    #         .order_by('id')
    #         .values('id', 'seq_id', 'server', 'cpu','time_stamp') # Explicitly name fields you need
    #     )
    #     # return Metrics.objects.filter(id__gte = last_id).order_by('id')
    #     # return missed_data

    @database_sync_to_async
    def fetch_missed_alert(self, last_seq_id, node_server_id=None):
        from .models import Metrics 
        from django.db.models import Max

        # 1. Base filter for sequences greater than last_seq_id
        base_query = Metrics.objects.filter(seq_id__gt=last_seq_id)
        if node_server_id:
            base_query = base_query.filter(node_server_id=node_server_id)

        # 2. Find the absolute latest primary key ID for each unique seq_id
        latest_ids = (
            base_query.values('seq_id')
            .annotate(latest_id=Max('id'))
            .values_list('latest_id', flat=True)
        )

        # 3. Pull the full records matching only those unique primary keys
        return list(
            Metrics.objects.filter(id__in=latest_ids)
            .order_by('seq_id')
            .values('seq_id', 'node_server_id', 'cpu', 'time_stamp')
        )

