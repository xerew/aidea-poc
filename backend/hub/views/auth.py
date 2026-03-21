from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from hub.serializers import AideaTokenObtainPairSerializer


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = AideaTokenObtainPairSerializer


class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'detail': 'Logged out.'})
