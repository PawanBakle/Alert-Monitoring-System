import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from asgiref.sync import async_to_sync
from clients.models import Metrics, Node 
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import async_to_sync
from clients.models import Node, Metrics 
from channels.layers import get_channel_layer


class Command(BaseCommand):
    help = 'Detects offline servers based on their latest stale metrics..'
    def handle(self, *args, **options):

        now_local = timezone.localtime(timezone.now())
        threshold_time = now_local - timedelta(seconds=10)
        active_nodes = Node.objects.exclude(status='Offline')
        # channel_layer = get_channel_layer()
        stale_count = 0

        for node in active_nodes:
            latest_metric = Metrics.objects.filter(
                node_server=node
            ).order_by('-time_stamp').first()

            if not latest_metric:
                self.stdout.write(f"Node '{node.node_name}': No metrics found in database.")
                continue
            metric_time_local = timezone.localtime(latest_metric.time_stamp)
            
  
            time_diff = now_local - metric_time_local
            
            self.stdout.write(f"Checking Server:       {node.node_name}")
            self.stdout.write(f"-> Last Metric Recv:   {metric_time_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            self.stdout.write(f"-> Age of Last Metric: {time_diff.total_seconds():.2f} seconds old")

            # Final evaluation check
            if latest_metric.time_stamp < threshold_time:
                stale_count += 1
                node.status = 'Offline'
                node.save()
                
                self.stdout.write(self.style.WARNING(f"!! MARKING OFFLINE -> {node.node_name} !!"))
             
            # data = {
            #     "seq_id":saved_data["seq_id"],
            #     "server_mac_address":serializer.validated_data['node_server'].mac_address,
            #     "server_name":node_name,
            #     "server_status":node_status,
            #     "server_os":serializer.validated_data['node_server'].os_version,
            #     # "server":saved_data['server'],
            #     "cpu":saved_data['cpu'],
            #     "time": saved_data['time_stamp'],
            # }
                data = {
                    "server_mac_address": node.mac_address,
                    "server_name": node.node_name,
                    "server_status": node.status,
                    "server_os":node.os_version,
                    "cpu": latest_metric.cpu,
                    "timestamp": metric_time_local.isoformat()
                }
                layer = get_channel_layer()
                try:

                    async_to_sync(layer.group_send)(
                        'metrics', 
                        {
                            'type': 'events.offline', 
                            'content': data
                        }
                    )
                    
                    async_to_sync(layer.group_send)(
                        'metrics', 
                        {
                            'type': 'events_offline', 
                            'content': data
                        }
                    )
                    self.stdout.write(f"-> Sent WebSocket frame for {node.node_name}")
                except Exception as e:
                    self.stderr.write(f"-> Failed to send: {e}")
            else:
                self.stdout.write(self.style.SUCCESS(f"-> Server {node.node_name} is healthy."))
            self.stdout.write("-" * 48)

        self.stdout.write(f"\nProcessed {stale_count} stale servers.\n")
