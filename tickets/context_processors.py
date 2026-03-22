from .models import Notificacion

def unread_notifications_count(request):
    if request.user.is_authenticated:
        count = Notificacion.objects.filter(usuario_destino=request.user, leido=False).count()
        return {"unread_notifications_count": count}
    return {"unread_notifications_count": 0}
