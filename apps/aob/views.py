from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.aob.models import AOBItem
from apps.aob.permissions import IsAOBItemCreator
from apps.aob.serializers import AOBItemSerializer
from apps.aob.services import create_aob_item, delete_aob_item, update_aob_item
from common.responses import created_response, success_response


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


class AOBItemUpdateDeleteView(generics.GenericAPIView):
    # IsAOBItemCreator (IsOwnerOrReadOnly with owner_field="created_by")
    # allows safe methods for anyone and restricts unsafe methods to the
    # creator — matching the same reuse already established for standups.
    permission_classes = [IsAuthenticated, IsAOBItemCreator]
    queryset = AOBItem.objects.all()
    serializer_class = AOBItemSerializer

    def patch(self, request, *args, **kwargs):
        # get_object() 404s for a nonexistent pk and, via
        # check_object_permissions(), 403s for a pk that exists but wasn't
        # created by request.user.
        item = self.get_object()

        serializer = self.get_serializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = update_aob_item(item=item, validated_data=serializer.validated_data)

        return success_response(
            data=AOBItemSerializer(updated).data,
            message="AOB item updated successfully.",
        )

    def delete(self, request, *args, **kwargs):
        item = self.get_object()

        delete_aob_item(item=item)

        return success_response(data=None, message="AOB item deleted successfully.")
