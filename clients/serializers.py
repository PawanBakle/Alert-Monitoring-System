from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from .models import Node,NodeSimulator
class NodeRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only = True, validators = [validate_password])
    class Meta:
        model = Node
        fields = ['host_name', 'mac_address','os_version','password']

    def create(self, attrs):
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

    class Meta:
        model = NodeSimulator
        fields = ['server','cpu']

    def create(self,attrs):
        return NodeSimulator.objects.create(**attrs)