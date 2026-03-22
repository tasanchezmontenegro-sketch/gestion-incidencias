# Business logic for the tickets app will be placed here.

from django.urls import reverse
from .models import Comentario, CustomUser, Estado, Notificacion


def resolver_incidencia_service(incidencia, tecnico, solucion_aplicada):
    """
    Marca una incidencia como 'Resuelta', crea el comentario de confirmación
    y envía notificaciones al creador y a todos los administradores activos.

    Args:
        incidencia: instancia de Incidencia ya guardada con la solución.
        tecnico:    usuario (CustomUser) que resuelve la incidencia.
        solucion_aplicada: texto con la solución aplicada.

    Raises:
        Estado.DoesNotExist: si el estado 'Resuelto' no existe en la BD.
                             Capturar en la vista y mostrar mensaje de error.
    """

    # ── 1. Obtener el estado "Resuelto" de forma segura ──────────────────────
    estado_resuelto = Estado.objects.filter(name='Resuelto').first()
    if estado_resuelto is None:
        raise Estado.DoesNotExist(
            "El estado 'Resuelto' no existe en la base de datos. "
            "Verifique las fixtures o migraciones iniciales."
        )

    # ── 2. Actualizar el estado de la incidencia ─────────────────────────────
    incidencia.estado = estado_resuelto
    incidencia.save()

    # ── 3. Registrar comentario automático de resolución ─────────────────────
    Comentario.objects.create(
        incidencia=incidencia,
        usuario=tecnico,
        tipo_comentario='confirmacion',
        texto=f'Incidencia resuelta. Solución: {solucion_aplicada}',
    )

    # ── 4. Construir mensaje y link para notificaciones ──────────────────────
    link = reverse('detalle_incidencia', args=[incidencia.pk])
    msg = (
        f"✅ Ticket #{incidencia.id:04d} resuelto por "
        f"{tecnico.get_full_name() or tecnico.username}"
    )

    # ── 5. Notificar al creador (si no es el mismo técnico) ──────────────────
    if incidencia.creador != tecnico:
        Notificacion.objects.create(
            usuario_destino=incidencia.creador,
            incidencia=incidencia,
            mensaje="Tu incidencia ha sido resuelta.",
            tipo="incidencia_resuelta",
            link=link,
        )

    # ── 6. Notificar a todos los administradores activos ─────────────────────
    admins = CustomUser.objects.filter(role='administrador', is_active=True)
    notificaciones_admin = [
        Notificacion(
            usuario_destino=admin,
            incidencia=incidencia,
            mensaje=msg,
            tipo="incidencia_resuelta",
            link=link,
        )
        for admin in admins
        if admin != tecnico
    ]
    if notificaciones_admin:
        Notificacion.objects.bulk_create(notificaciones_admin)


def cerrar_incidencia_service(incidencia, usuario_que_cierra):
    """
    Cambia el estado a 'Cerrado' y registra la conformidad del usuario.
    """
    estado_cerrado = Estado.objects.filter(name='Cerrado').first()
    if not estado_cerrado:
        # Si no existe, lo creamos para evitar errores
        estado_cerrado = Estado.objects.create(name='Cerrado')

    incidencia.estado = estado_cerrado
    incidencia.save()

    # Registrar comentario de cierre
    Comentario.objects.create(
        incidencia=incidencia,
        usuario=usuario_que_cierra,
        tipo_comentario='confirmacion',
        texto='El usuario ha confirmado la solución. Ticket cerrado formalmente.'
    )

    # Notificar al técnico que su incidencia fue cerrada satisfactoriamente
    if incidencia.tecnico_asignado:
        Notificacion.objects.create(
            usuario_destino=incidencia.tecnico_asignado,
            incidencia=incidencia,
            mensaje=f"✅ El usuario cerró el ticket #{incidencia.id:04d}.",
            tipo="estado",
            link=reverse('detalle_incidencia', args=[incidencia.pk])
        )