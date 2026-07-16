from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.standups.serializers import StandupSerializer
from apps.standups.services import create_standup
from common.responses import created_response


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
            raise ValidationError(
                {"standup_date": ["A standup for this date has already been submitted."]}
            ) from exc

        return created_response(
            data=StandupSerializer(standup).data,
            message="Standup submitted successfully.",
        )
