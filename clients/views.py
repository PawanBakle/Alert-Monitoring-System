from django.http import HttpResponse,JsonResponse
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .serializers import NodeRegisterSerializer,NodeLoginSerializer,MetricsSerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.views import APIView
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
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
                    {"message": f"Node {node.host_name} registered successfully."}, 
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
        token, created = Token.objects.get_or_create(user = user)
        return Response({
            "token": token.key,
            "user_id": user.id,
            "host_name": user.host_name,
            "id":user.id
        }, status=status.HTTP_200_OK)


class Metrics(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def check_high_metric(self,data): # type- dict
        cpu_data = data.get('cpu',None)
        if cpu_data and cpu_data > 70:
            return True
        return False
    
    def post(self,request):
        # first serialize the request
        # server sends metrics. 
        # it gets serialized and validated
        # it is sent to web socket
        # server gets the response that the metrics has been saved
        # but here are we saving the metrics?? everytime it's been sent?? 
        # or checking if metrics is already of particular host is already there if just update relevant data? 
        print(f'Data - {request.data}, sent by {request.user} and server {request.data}') # dict but has not be validated
        node_server = request.data.get('node_server','')
        print(node_server)
        serializer = MetricsSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save() # creates a row in metrics Table
            validate = self.check_high_metric(serializer.validated_data)
            print(f'serialized data - {serializer.validated_data}')
            saved_data = serializer.data
            data = {
                "server_mac_address":serializer.validated_data['node_server'].mac_address,
                "server_status":serializer.validated_data['node_server'].status,
                "server_os":serializer.validated_data['node_server'].os_version,
                "server":serializer.validated_data['server'],
                "cpu":serializer.validated_data['cpu'],
                "time": saved_data['time_stamp'],
            }
            print(f'data payload{data}')
            layer = get_channel_layer()
            if validate:
        
                async_to_sync(layer.group_send)('metrics',{
                    'type':'events.alert',
                    # 'content':{"data":serializer.validated_data}
                    'content':{"data":data}
                })
                print(serializer.validated_data)
                return Response({"status": "metrics received"}, status=status.HTTP_201_CREATED)
                # print(type(serializer.validated_data))
            else: 
                
                async_to_sync(layer.group_send)('metrics', {
                'type': 'events.normal',
                'content': {"data":data} # vs serializer.data (need to figure what i pass to the client)
                })
                
                return Response({"status": "metrics received"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    '''
    just push the data to the channel layer 
    where is it created? it's something like channel_layer.send = data(dict)
    but where do i set up the channel layer (redis) where it gets the data
    write consumer to consume that data
    '''

     