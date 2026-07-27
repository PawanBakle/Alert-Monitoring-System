import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from clients.models import Metrics, Node 

class Command(BaseCommand):
    help = 'Detects offline servers based on stale metrics'

    def handle(self, *args, **options):
        
        threshold_time = timezone.now() - timedelta(seconds=20)
        
        # Filter stale metrics 
        stale_metrics = Metrics.objects.filter(
            time_stamp__lt=threshold_time
        ).select_related('node_server')

        channel_layer = get_channel_layer()
        
        if stale_metrics.exists():
            self.stdout.write(self.style.SUCCESS(f"Found {stale_metrics.count()} stale metrics."))
            
            # avoid updating the same node multiple times if it has multiple stale metrics
            processed_nodes = set()

            for metric in stale_metrics:
                node = metric.node_server
       
                if node.id in processed_nodes:
                    continue
                
              
                if node.status != Node.STATUS_OFFLINE:
                    node.status = Node.STATUS_OFFLINE
                    node.save()
                    self.stdout.write(f"Marked {node.host_name} as OFFLINE.")
                    
                    # data serialization
                    data = {
                        "server_host_name": node.host_name,
                        "server_mac_address": node.mac_address,
                        "server_status": node.status,
                        "last_known_server": metric.server,
                        "last_known_cpu": metric.cpu,
                        "timestamp": metric.time_stamp.isoformat()
                    }

                    
                    try:
                        async_to_sync(channel_layer.group_send)("metrics", {
                            "type": "events.offline",  # channels converts dots to underscores automatically
                            "content": {"data": data}
                        })
                    except Exception as e:
                        self.stderr.write(f"Failed to send WebSocket event: {e}")
                
                processed_nodes.add(node.id)
        else:
            self.stdout.write("No stale metrics found. All servers appear online.")   