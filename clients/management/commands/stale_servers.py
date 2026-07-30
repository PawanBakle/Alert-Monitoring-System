import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from clients.models import Metrics, Node 
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from clients.models import Node, Metrics 

class Command(BaseCommand):
    help = 'Detects offline servers based on their latest stale metrics'

    def handle(self, *args, **options):
        threshold_time = timezone.now() - timedelta(seconds=20)
        # Online servers
        active_nodes = Node.objects.exclude(status=Node.STATUS_OFFLINE)
        
        channel_layer = get_channel_layer()
        stale_count = 0

        for node in active_nodes:
            
        
            latest_metric = Metrics.objects.filter(
                node_server=node
            ).order_by('-time_stamp').first() # .first() gets the newest row or None

            if not latest_metric:
                continue

            # latest timestamp against the threshold
            if latest_metric.time_stamp < threshold_time:
                stale_count += 1
                
                # Update status
                node.status = Node.STATUS_OFFLINE
                node.save()
                self.stdout.write(f"Marked {node.host_name} as OFFLINE.")
                
             
                data = {
                    "server_host_name": node.host_name,
                    "server_mac_address": node.mac_address,
                    "server_status": node.status,
                    "last_known_server": latest_metric.server,
                    "last_known_cpu": latest_metric.cpu,
                    "timestamp": latest_metric.time_stamp.isoformat()
                }

                try:
                    async_to_sync(channel_layer.group_send)("metrics", {
                        "type": "events.offline", 
                        "content": {"data": data}
                    })
                except Exception as e:
                    self.stderr.write(f"Failed to send WebSocket event: {e}")


        if stale_count > 0:
            self.stdout.write(self.style.SUCCESS(f"Processed {stale_count} stale servers."))
        else:
            self.stdout.write("No stale servers detected. All nodes are reporting normally.")
