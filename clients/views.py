from django.shortcuts import render

# Create your views here.


class Metrics(APIView):
    permission_classes = [isAuthenticated]
    def post(request):
        # first serialize the request
        serializer = MetricsSerializer(data = request.data)
        if serializer.is_valid(errors = True):
            serialzer.save() # creates a row in metrics Table
        return Response(serializer.data)

     