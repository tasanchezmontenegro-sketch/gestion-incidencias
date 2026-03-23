# Business logic for the tickets app will be placed here.

from django.urls import reverse
from .models import Comentario, CustomUser, Estado, Notificacion

def resolver_incidencia_service(incidencia, tecnico, solucion_aplicada, evidencia=None):
    """
    Lógica de negocio centralizada para resolver incidencias.
    """
    # 1. Obtener el estado 'Resuelto'
    estado_resuelto = Estado.objects.filter(name__iexact='Resuelto').first()
    if not estado_resuelto:
        raise Estado.DoesNotExist("El estado 'Resuelto' no está configurado en el sistema.")

    # 2. Actualizar la incidencia
    incidencia.estado = estado_resuelto
    incidencia.solucion_aplicada = solucion_aplicada
    if evidencia:
        incidencia.evidencia_solucion = evidencia
    incidencia.save()

    # 3. Registrar comentario en el historial
    Comentario.objects.create(
        incidencia=incidencia,
        usuario=tecnico,
        tipo_comentario='confirmacion',
        texto=f'Resolución: {solucion_aplicada}',
        evidencia_adjunta=evidencia  # Guardamos la foto también en el comentario
    )

    # 4. Preparar notificaciones
    link = reverse('detalle_incidencia', args=[incidencia.pk])
    msg_admin = f"✅ Ticket #{incidencia.id:04d} resuelto por {tecnico.get_full_name() or tecnico.username}"

    # 5. Notificar al creador (Trabajador)
    if incidencia.creador != tecnico:
        Notificacion.objects.create(
            usuario_destino=incidencia.creador,
            incidencia=incidencia,
            mensaje="Tu incidencia ha sido resuelta. Por favor, verifica y cierra el ticket.",
            tipo="incidencia_resuelta",
            link=link,
        )

    # 6. Notificar a administradores (Optimizado con bulk_create)
    admins = CustomUser.objects.filter(role='administrador', is_active=True).exclude(id=tecnico.id)
    notificaciones_admin = [
        Notificacion(
            usuario_destino=admin,
            incidencia=incidencia,
            mensaje=msg_admin,
            tipo="incidencia_resuelta",
            link=link,
        ) for admin in admins
    ] # Este corchete debe estar alineado con la 'n' de notificaciones
    
    if notificaciones_admin:
        Notificacion.objects.bulk_create(notificaciones_admin)

    return incidencia

def cerrar_incidencia_service(incidencia, usuario_que_cierra):
    """
    Cambia el estado a 'Cerrado' y registra la conformidad.
    """
    estado_cerrado = Estado.objects.filter(name__iexact='Cerrado').first()
    if not estado_cerrado:
        estado_cerrado = Estado.objects.create(name='Cerrado')

    incidencia.estado = estado_cerrado
    incidencia.save()

    Comentario.objects.create(
        incidencia=incidencia,
        usuario=usuario_que_cierra,
        tipo_comentario='confirmacion',
        texto='El usuario ha confirmado la solución. Ticket cerrado formalmente.'
    )

    # Notificar al técnico
    if incidencia.tecnico_asignado:
        Notificacion.objects.create(
            usuario_destino=incidencia.tecnico_asignado,
            incidencia=incidencia,
            mensaje=f"✅ El usuario cerró el ticket #{incidencia.id:04d}.",
            tipo="estado",
            link=reverse('detalle_incidencia', args=[incidencia.pk])
        )