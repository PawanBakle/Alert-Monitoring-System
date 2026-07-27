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
        fields = ['host_name','mac_address','os_version','status','password']

    def create(self, attrs):
        # status = attrs.get('status')
        # status = STATUS_ONLINE
        return Node.objects.create_user(**attrs)

class NodeLoginSerializer(serializers.Serializer):
    host_name = serializers.CharField(max_length = 12)
    password = serializers.CharField(write_only = True)
    def validate(self, attrs):
        host_name = attrs.get('host_name')
        password = attrs.get('password')
        if host_name and password:
            auth_user  = authenticate(username = host_name, password = password)
            if auth_user is None:
                raise serializers.ValidationError("Invalid hostname or password")
            if not auth_user.is_active:
                raise serializers.ValidationError("This user is disabled")
            attrs['user'] = auth_user
        else:
            raise serializers.ValidationError("Must include both hostname and password")
        return attrs
class MetricsSerializer(serializers.ModelSerializer):
    cpu = serializers.IntegerField(min_value = 0, max_value = 100)
    node_server = serializers.PrimaryKeyRelatedField(queryset = Node.objects.all())

    class Meta:
        model = Metrics
        fields = ['id','node_server','server','cpu','time_stamp']

        # def validate(self, attrs):
        #     node_server = attrs.get('node_server','')
        
    def create(self,attrs):
        
        time_stamp = attrs.get('time_stamp','')
        time_stamp = timezone.now()
        attrs['time_stamp'] = time_stamp
        return Metrics.objects.create(**attrs)


