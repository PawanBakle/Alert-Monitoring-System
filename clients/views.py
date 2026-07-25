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
            "host_name": user.host_name
        }, status=status.HTTP_200_OK)


class Metrics(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        # first serialize the request
        # server sends metrics. 
        # it gets serialized and validated
        # it is sent to web socket
        # server gets the response that the metrics has been saved
        # but here are we saving the metrics?? everytime it's been sent?? 
        # or checking if metrics is already of particular host is already there if just update relevant data? 
        print(request.data)
        serializer = MetricsSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save() # creates a row in metrics Table

            print(serializer.data)
            
            layer = get_channel_layer()
            async_to_sync(layer.group_send)('metrics', {
    'type': 'events.alarm',
    'content': {"data":serializer.data}
    })
            return Response({"status": "metrics received"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    '''
    just push the data to the channel layer 
    where is it created? it's something like channel_layer.send = data(dict)
    but where do i set up the channel layer (redis) where it gets the data
    write consumer to consume that data
    '''

     