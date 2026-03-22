from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from .models import Incidencia, Comentario, CustomUser, Notificacion

# ============================================================
# HELPER
# ============================================================
def _link(view_name, pk):
    try:
        return reverse(view_name, args=[pk])
    except Exception:
        return None

# ============================================================
# SEÑALES DE INCIDENCIA
# ============================================================

@receiver(pre_save, sender=Incidencia)
def incidencia_pre_save(sender, instance, **kwargs):
    """Captura estado y técnico anterior ANTES de guardar cambios."""
    if instance.pk:
        try:
            anterior = sender.objects.get(pk=instance.pk)
            instance._estado_anterior = anterior.estado
            instance._tecnico_anterior = anterior.tecnico_asignado
        except sender.DoesNotExist:
            instance._estado_anterior = None
            instance._tecnico_anterior = None
    else:
        instance._estado_anterior = None
        instance._tecnico_anterior = None


@receiver(post_save, sender=Incidencia)
def incidencia_post_save(sender, instance, created, **kwargs):
    link = _link("detalle_incidencia", instance.pk)

    if created:
        # 1. Notificar a administradores (si el creador no es admin)
        if instance.creador and instance.creador.role != 'administrador':
            admins = CustomUser.objects.filter(role='administrador', is_active=True)
            for admin in admins:
                Notificacion.objects.create(
                    usuario_destino=admin,
                    incidencia=instance,
                    mensaje=f"🚩 Nuevo reporte de {instance.creador.get_full_name() or instance.creador.username} (#{instance.id:04d})",
                    tipo="nueva_incidencia",
                    link=link
                )

        # 2. Notificar al técnico si se asigna desde el inicio
        if instance.tecnico_asignado:
            Notificacion.objects.create(
                usuario_destino=instance.tecnico_asignado,
                incidencia=instance,
                mensaje=f"🆕 Se te asignó el ticket #{instance.id:04d}",
                tipo="asignacion",
                link=link
            )

    else:
        # LÓGICA DE EDICIÓN
        tecnico_anterior = getattr(instance, '_tecnico_anterior', None)
        id_anterior = tecnico_anterior.id if tecnico_anterior else None
        id_actual = instance.tecnico_asignado.id if instance.tecnico_asignado else None

        # --- CAMBIO DE TÉCNICO (Reasignación o Desasignación) ---
        if id_actual != id_anterior:
            # Notificar al técnico que sale
            if id_anterior:
                Notificacion.objects.create(
                    usuario_destino=tecnico_anterior,
                    incidencia=instance,
                    mensaje=f"🚫 Se te ha retirado la asignación del ticket #{instance.id:04d}",
                    tipo="desasignacion",
                    link=link
                )
            
            # Notificar al técnico que entra
            if id_actual:
                Notificacion.objects.create(
                    usuario_destino=instance.tecnico_asignado,
                    incidencia=instance,
                    mensaje=f"🆕 Reasignación: Se te ha asignado el ticket #{instance.id:04d}",
                    tipo="asignacion",
                    link=link
                )

        # --- CAMBIO DE ESTADO ---
        estado_anterior = getattr(instance, '_estado_anterior', None)
        if estado_anterior and estado_anterior != instance.estado:
            msg = f"🔄 Ticket #{instance.id:04d} cambió a: {instance.estado.name}"
            
            # Al creador
            if instance.creador:
                Notificacion.objects.create(usuario_destino=instance.creador, incidencia=instance, mensaje=msg, tipo="estado", link=link)
            
            # Al técnico (solo si no cambió de técnico en este mismo guardado)
            if id_actual and id_actual == id_anterior:
                Notificacion.objects.create(usuario_destino=instance.tecnico_asignado, incidencia=instance, mensaje=msg, tipo="estado", link=link)

# ============================================================
# SEÑALES DE COMENTARIO
# ============================================================

@receiver(post_save, sender=Comentario)
def comentario_post_save(sender, instance, created, **kwargs):
    if not created: return

    incidencia = instance.incidencia
    autor = instance.usuario
    link = _link("detalle_incidencia", incidencia.pk)
    msg = f"💬 {autor.get_full_name() or autor.username} comentó en #{incidencia.id:04d}"

    destinatarios = set()
    if incidencia.creador and incidencia.creador != autor:
        destinatarios.add(incidencia.creador)
    if incidencia.tecnico_asignado and incidencia.tecnico_asignado != autor:
        destinatarios.add(incidencia.tecnico_asignado)
    
    # Notificar a admins si el autor no es admin
    if autor.role != 'administrador':
        admins = CustomUser.objects.filter(role='administrador', is_active=True)
        for admin in admins:
            if admin != autor: destinatarios.add(admin)

    for usuario in destinatarios:
        Notificacion.objects.create(
            usuario_destino=usuario, incidencia=incidencia, mensaje=msg, tipo="comentario", link=link
        )