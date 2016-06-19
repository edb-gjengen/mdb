from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mdb.api.serializers import HostPXEValidateSerializer


class HostPXEValidate(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = HostPXEValidateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        serializer.save()  # sets Host.pxe_installable=False

        return Response({'valid_pxe_key': True})
