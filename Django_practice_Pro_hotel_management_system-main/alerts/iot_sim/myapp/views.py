import json
from django.http import JsonResponse
from .models import IoTData

def receive_iot_data(request):
    if request.method == "POST":
        data = json.loads(request.body)

        IoTData.objects.create(
            device_id=data.get("device_id"),
            room=data.get("room"),
            temperature=data.get("temperature"),
            gas=data.get("gas"),
            motion=data.get("motion"),
            status=data.get("status")
        )

        return JsonResponse({"message": "stored"})

    return JsonResponse({"error": "Invalid request"}, status=400)


def get_iot_data(request):
    data = IoTData.objects.all().order_by('-timestamp')[:100]

    result = [
        {
            "room": d.room,
            "temperature": d.temperature,
            "gas": d.gas,
            "motion": d.motion,
            "status": d.status,
            "timestamp": d.timestamp.strftime("%H:%M:%S")
        }
        for d in data
    ]

    return JsonResponse(result, safe=False)