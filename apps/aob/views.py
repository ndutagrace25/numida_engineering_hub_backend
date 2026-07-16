from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.aob.serializers import AOBItemSerializer
from apps.aob.services import create_aob_item
from common.responses import created_response


class AOBItemCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AOBItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item = create_aob_item(user=request.user, validated_data=serializer.validated_data)

        return created_response(
            data=AOBItemSerializer(item).data,
            message="AOB item created successfully.",
        )
