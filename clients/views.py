from django.http import HttpResponse,JsonResponse
from rest_framework import status
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import NodeRegisterSerializer,NodeLoginSerializer,MetricsSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.views import APIView
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Node,Metrics
# Create your views here.


def dashboard(request):
    return render(request, 'clients/index.html')

class NodeRegister(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = NodeRegisterSerializer(data = request.data)
        # do i need to assign user to host-name here? 
        # well user is authenticated automatically here
        # better to write a flow here 
        if serializer.is_valid():
            node = serializer.save()
            return Response(
                    {"message": f"Node {node.node_name} registered successfully."}, 
                    status=status.HTTP_201_CREATED
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NodeLogin(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = NodeLoginSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)

        # basically first authenticate with username and password
        # where does token come here? likely here 
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        # last_seq_id = Metrics.objects.filter(node_server = user).order_by('-time_stamp').first()
        last_seq_id = Metrics.objects.filter(node_server = user).order_by('-seq_id').first() # since new seq id is sent every time
        if last_seq_id == None:
            last_sent_id = 0
        else:
            last_sent_id = last_seq_id.seq_id
        print(f'last data saved {last_seq_id}')
        return Response({
            "access": str(refresh.access_token),
            "refresh" = str(refresh),
            "user_id": user.id,
            "node_name": user.node_name,
            "id":user.id,
            "last_sent_seq_id":last_sent_id
        }, status=status.HTTP_200_OK)


class MetricsData(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        # print(f'Data -before serialization {request.data}, sent by {request.user}') # dict but has not be validated
        request.user.status = 'ONLINE'
        request.user.save()
        print(f'server {request.user} and its status {request.user.status}')
        serializer = MetricsSerializer(data = request.data)
        if serializer.is_valid():
            instance = serializer.save() # creates a row in metrics Table
            node = instance.node_server
            saved_data = serializer.data
            data = {
                "seq_id":instance.seq_id,
                "server_name":node.node_name,
                "server_mac_address":node.mac_address,
                "server_status":request.user.status,
                "server_os":node.os_version,
                "severity":instance.severity,
                "cpu":instance.cpu,
                "time": instance.time_stamp.isoformat(),
            }
            print(f'data payload to Redis -> {data}')
            layer = get_channel_layer()
            if instance.severity == 'NORMAL':
                event_type = 'events.normal'
            else:
                event_type = 'events.alert'
            
            async_to_sync(layer.group_send)('metrics',{
                    'type':event_type,
                    'content':data
                })
            return Response({"status": "metrics received"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    '''
    just push the data to the channel layer 
    where is it created? it's something like channel_layer.send = data(dict)
    but where do i set up the channel layer (redis) where it gets the data
    write consumer to consume that data
    '''

     