from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone

from common.constants import APPLICATION_NAME, APPLICATION_VERSION


def health_check(request):
    return JsonResponse(
        {
            "status": "ok",
            "application": APPLICATION_NAME,
            "version": APPLICATION_VERSION,
            "environment": settings.ENVIRONMENT,
            "server_time": timezone.now().isoformat(),
        }
    )
