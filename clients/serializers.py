from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from .models import Node,Metrics
import time
from django.utils import timezone
class NodeRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only = True, validators = [validate_password])
    class Meta:
        model = Node
        fields = ['node_name','mac_address','os_version','status','password']

    def create(self, attrs):
        # status = attrs.get('status')
        # status = STATUS_ONLINE
        return Node.objects.create_user(**attrs)



class NodeLoginSerializer(serializers.Serializer):
    node_name = serializers.CharField(max_length = 12)
    password = serializers.CharField(write_only = True)
    def validate(self, attrs):
        node_name = attrs.get('node_name')
        password = attrs.get('password')
        if node_name and password:
            auth_user  = authenticate(username = node_name, password = password)
            if auth_user is None:
                raise serializers.ValidationError("Invalid node/server name or password")
            if not auth_user.is_active:
                raise serializers.ValidationError("This user is disabled")
            attrs['user'] = auth_user
        else:
            raise serializers.ValidationError("Must include both hostname and password")
        return attrs

""" 
{'server_id': 4, 'seq_id': 2, 'time_stamp': '2026-08-01T08:51:31.034287+00:00', 
'metrics': {'cpu': 6, 'memory': 70, 'disk': 47}}
""" 
class MetricsSerializer(serializers.ModelSerializer):
    cpu = serializers.IntegerField(min_value = 0, max_value = 100)
    node_server = serializers.PrimaryKeyRelatedField(queryset = Node.objects.all())

    class Meta:
        model = Metrics
        # fields = ['id','node_server (node-id)','server','cpu','time_stamp']
        fields = '__all__'


    def to_internal_value(self,data):
        metrics = data.get('metrics','')

        # inner data
        node_server = data.get('node_server')
        seq_id = data.get('seq_id')
        
        cpu = metrics.get('cpu',None)
        memory = metrics.get('memory',None)
        disk = metrics.get('disk',None)

        # combined = f"{outer_val}-{inner_val_1}" if outer_val and inner_val_1 else None
        
        flat_data = {
            "seq_id":seq_id,
            "node_server":node_server,
            "cpu":cpu,
            "memory":memory,
            "disk":disk
        }
    

        return super().to_internal_value(flat_data)

    def evaluate_severity(self, cpu):
        if cpu > 90:
            return ['CRITICAL',f"CPU {cpu}% > threshold 90%"]
            
        elif cpu > 70:
            return ['WARNING',f"CPU {cpu}% > threshold 70%"]
            
        else:
            return ['NORMAL',None]


    def create(self,attrs):
        # print(f"attributes pre serialization {attrs}")
        cpu = attrs.get('cpu',None)
        cpu_severity = self.evaluate_severity(cpu)
        attrs['severity'] = cpu_severity[0]
        reason = cpu_severity[1]
        attrs['alert_reason'] = reason if reason else None
        if 'time_stamp' not in attrs or attrs['time_stamp'] is None:
            attrs['time_stamp'] = timezone.now()
        
        return Metrics.objects.create(**attrs)


