
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
from django.db.models import Q,Max

class MetricsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
            query_string = self.scope['query_string'].decode()
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            token_str = params.get('token')
            if not token_str:
                logger.warning("WebSocket connection rejected: Missing auth token.")
                await self.close(code=4001)  # Custom close code for unauthorized
                return
            user = await self.get_user_from_token(token_str)
            if not user:
                logger.warning("WebSocket connection rejected: Invalid or expired token.")
                await self.close(code=4003)
                return
            self.scope['user'] = user
            
            self.group_name = 'metrics'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info(f"WebSocket connected for user: {user.node_name if hasattr(user, 'node_name') else user}")
    @database_sync_to_async
    def get_user_from_token(self, token_str):
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Decode and verify the JWT access token
            access_token = AccessToken(token_str)
            user_id = access_token['user_id']
            return User.objects.get(id=user_id)
        except (InvalidToken, TokenError, Exception) as e:
            logger.error(f"Token validation error during WS connection: {e}")
            return None
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
        except (ConnectionResetError, BrokenPipeError):
            # Client network socket dropped unexpectedly
            print("Info: Client socket connection reset or broken pipe.")
        except StopConsumer:
            # let consumer handle it
            raise
        except Exception as e:
            # unexpected runtime exceptions
            print(f"Consumer dispatch error: {type(e).__name__}: {e}")
            raise
    async def receive(self, text_data=None, bytes_data=None):
        
            try:
                json_data = json.loads(text_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Malformed JSON received over WebSocket: {e}")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format payload."
                }))
                return
            if 'last_seen' not in json_data:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Missing 'last_seen' payload key."
                }))
                return

            lost_messages = await self.fetch_missed_alert(json_data["last_seen"])
            await self.send(text_data=json.dumps({
                "type": "recovery_data",
                "messages": lost_messages
            }, cls=DjangoJSONEncoder))

    
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
    def fetch_missed_alert(self, payload, node_server_id=None):
        from .models import Metrics, Node
        mac_addresses = list(payload.keys())
        nodes = Node.objects.filter(mac_address__in=mac_addresses).values('id', 'mac_address')
        node_map = {str(n['mac_address']): n['id'] for n in nodes}
        
        results = {}

        for mac, last_seq_id in payload.items():
            if mac not in node_map:
                continue
                
            node_id = node_map[mac]
            
            # filter greater than the last known IDss
            missed_data = list(
                Metrics.objects.filter(
                    node_server_id=node_id, 
                    seq_id__gt=last_seq_id
                ).order_by('seq_id').values('seq_id', 'cpu', 'time_stamp').exclude(severity='NORMAL')
            )
            
            results[mac] = missed_data
# {'mac_address': [list_of_metrics], mac_address2 : [lom]..}
        print(f'data sent back for missed ids {results}')
        return results
