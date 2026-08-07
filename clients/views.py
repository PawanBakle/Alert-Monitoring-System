from django.http import HttpResponse,JsonResponse
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
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

    def check_high_metric(self,data): # type- dict
        cpu_data = data.get('cpu',None)
        if cpu_data and cpu_data > 70:
            return True
        return False
    
    def post(self,request):
        # print(f'Data -before serialization {request.data}, sent by {request.user}') # dict but has not be validated
        request.user.status = 'Online'
        request.user.save()
        print(f'server {request.user} and its status {request.user.status}')
        # print(f'server Id sent {node_id}')
        serializer = MetricsSerializer(data = request.data)
        # print(f'Just called serializer on this {serializer.initial_data}')
        if serializer.is_valid():
            serializer.save() # creates a row in metrics Table
            validate = self.check_high_metric(serializer.validated_data)
            # print(f'serialized data - {serializer.validated_data}')
            node_name = serializer.validated_data['node_server'].node_name
            node_status = serializer.validated_data['node_server'].status
            
            # node_status = serializer.validated_data['node_server']
            # node_status.status = 'ONLINE'
            # node_status.save()
            # serializer.validated_data['node_server'] = node_status
            saved_data = serializer.data
            # print(f"saved data post serialization {saved_data}")

            data = {
                "seq_id":saved_data["seq_id"],
                "server_name":node_name,
                "server_mac_address":serializer.validated_data['node_server'].mac_address,
                "server_status":node_status,
                "server_os":serializer.validated_data['node_server'].os_version,
                # "server":saved_data['server'],
                "cpu":saved_data['cpu'],
                "time": saved_data['time_stamp'],
            }
            print(f'data payload to Redis -> {data}')
            layer = get_channel_layer()
            if validate:
        
                async_to_sync(layer.group_send)('metrics',{
                    'type':'events.alert',
                    # 'content':{"data":serializer.validated_data}
                    'content':data
                    # 'content':{"data":data}
                })
                # print(serializer.validated_data)
                return Response({"status": "metrics received"}, status=status.HTTP_201_CREATED)
                # print(type(serializer.validated_data))
            else: 
                
                async_to_sync(layer.group_send)('metrics', {
                'type': 'events.normal',
                'content': data # vs serializer.data (need to figure what i pass to the client)
                # 'content': {"data":data} # vs serializer.data (need to figure what i pass to the client)
                })
                
                return Response({"status": "metrics received"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    '''
    just push the data to the channel layer 
    where is it created? it's something like channel_layer.send = data(dict)
    but where do i set up the channel layer (redis) where it gets the data
    write consumer to consume that data
    '''

     