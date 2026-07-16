from django.db import IntegrityError
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.standups.models import Standup
from apps.standups.permissions import IsStandupOwner
from apps.standups.serializers import StandupSerializer
from apps.standups.services import create_standup, update_standup
from common.responses import created_response, success_response

DUPLICATE_STANDUP_DATE_ERROR = {
    "standup_date": ["A standup for this date has already been submitted."]
}


class StandupCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StandupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            standup = create_standup(user=request.user, validated_data=serializer.validated_data)
        except IntegrityError as exc:
            # The model's UniqueConstraint(user, standup_date) is the source
            # of truth for this rule; translate it into the standard error
            # format instead of letting it surface as an unhandled 500.
            raise ValidationError(DUPLICATE_STANDUP_DATE_ERROR) from exc

        return created_response(
            data=StandupSerializer(standup).data,
            message="Standup submitted successfully.",
        )


class StandupUpdateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsStandupOwner]
    queryset = Standup.objects.all()
    serializer_class = StandupSerializer

    def patch(self, request, *args, **kwargs):
        # get_object() 404s for a nonexistent pk and, via
        # check_object_permissions(), 403s for a pk that exists but isn't
        # owned by request.user.
        standup = self.get_object()

        serializer = self.get_serializer(standup, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            updated = update_standup(standup=standup, validated_data=serializer.validated_data)
        except IntegrityError as exc:
            raise ValidationError(DUPLICATE_STANDUP_DATE_ERROR) from exc

        return success_response(
            data=StandupSerializer(updated).data,
            message="Standup updated successfully.",
        )
