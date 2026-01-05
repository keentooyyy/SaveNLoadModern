from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


class VersionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'version': settings.APP_VERSION}, status=status.HTTP_200_OK)
