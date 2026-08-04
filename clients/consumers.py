
## here first i write class Metric Consumer
import json
from channels.generic.websocket import (
    AsyncWebsocketConsumer,
)
from channels.db import database_sync_to_async
# from .models import Metrics
from django.core.serializers.json import DjangoJSONEncoder
from channels.exceptions import StopConsumer
import redis
import asyncio   
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
        # async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            "metrics",
            self.channel_name
        )
    async def dispatch(self, message):
        #overriding dispatch to gracefully catch Redis drops instead of crashing daphne or uvicorn
            try:
                await super().dispatch(message)
            except (redis.exceptions.TimeoutError, asyncio.TimeoutError):
                # Log the transient drop internally without killing the socket worker
                print("Warning: Transient Redis read timeout caught in consumer dispatch.")
            except (StopConsumer, ConnectionResetError, BrokenPipeError):
                # Client disconnected unexpectedly
                print("Info: Client disconnected abruptly.")
                # Do NOT raise e; let the consumer stop naturally
            except Exception as e:
                # Only log and raise if it's a genuine unexpected error
                if str(e):
                    print(f"Consumer dispatch error: {e}")
                else:
                    print(f"Consumer dispatch error: {type(e).__name__} (Empty message)")
                raise e

    async def receive(self, text_data = None,bytes_data = None):
        # print(f'received text from Client {text_data}')
        json_data = json.loads(text_data) 
        print(f'Received JSON from CLIENT {json_data}')
        # {'type': 'sync', 'last_seen': {'12:31:13:197': 16, '12:31:13:195': 17, '5d:7d:81:e2:55:dc': 12}}
        # need to fire ORM to find and send back data from last id - latest id-1
        # kinda of like a loop through from last seq-id
        payload = json_data['last_seen']
        lost_messages = await self.fetch_missed_alert(json_data["last_seen"])
        # lost_messages = json.dumps(lost_messages)
        # print(f'messages that were lost {len(lost_messages)}')
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

    @database_sync_to_async
    def fetch_missed_alert(self, last_seq_id, node_server_id=None):
        from .models import Metrics 
        from django.db.models import Max

# to get and remove de duplicates
        # base_query = Metrics.objects.filter(seq_id__gt=last_seq_id)
        for each_key in payload.keys():
            # get the value and perform the same query
            # base_query = Metrics.objects.filter(seq_id__gt=last_seq_id)
            if node_server_id:
                base_query = base_query.filter(node_server_id=node_server_id)

            latest_ids = (
                base_query.values('seq_id')
                .annotate(latest_id=Max('id'))
                .values_list('latest_id', flat=True)
            )
        print(f"Lost data received and sent {list((Metrics.objects.filter(id__in=latest_ids).order_by('seq_id').values('seq_id', 'node_server_id', 'cpu', 'time_stamp')))}")

        return list(
            Metrics.objects.filter(id__in=latest_ids)
            .order_by('seq_id')
            .values('seq_id', 'node_server_id', 'cpu', 'time_stamp')
        )

