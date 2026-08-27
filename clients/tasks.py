# your_app/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Node, Metrics
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def check_offline_servers(self):
    STATUS_OFFLINE = 'OFFLINE' 
    now_local = timezone.localtime(timezone.now())
    threshold_time = now_local - timedelta(seconds=10)
    active_nodes = Node.objects.exclude(status=STATUS_OFFLINE)
    stale_count = 0

    for node in active_nodes:
        latest_metric = Metrics.objects.filter(
            node_server=node
        ).order_by('-time_stamp').first()

        if not latest_metric:
            continue
            
        metric_time_local = timezone.localtime(latest_metric.time_stamp)
        time_diff = now_local - metric_time_local

        if latest_metric.time_stamp < threshold_time:
            stale_count += 1
            node.status = STATUS_OFFLINE
            node.save()
            
            data = {
                "server_mac_address": node.mac_address,
                "server_name": node.node_name,
                "server_status": node.status,
                "server_os": node.os_version,
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
            except Exception as e:
                logger.error(f"Failed to send offline WebSocket frame for {node.node_name}: {e}")

    return f"Checked servers. Marked {stale_count} as offline."