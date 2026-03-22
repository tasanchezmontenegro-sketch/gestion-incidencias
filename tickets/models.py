from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from PIL import Image
import os

# --- FUNCIÓN AUXILIAR DE OPTIMIZACIÓN ---
def resize_image(image_field, size=(800, 800)):
    if not image_field:
        return
    
    img_path = image_field.path
    if os.path.exists(img_path):
        img = Image.open(img_path)
        # Solo redimensiona si es más grande que el límite
        if img.height > size[1] or img.width > size[0]:
            img.thumbnail(size)
            # Calidad 70 es el punto dulce entre peso y nitidez
            img.save(img_path, quality=70, optimize=True)

# --- FUNCIÓN DE OPTIMIZACIÓN ---
def optimizar_imagen(imagen_campo, size=(1024, 1024)):
    if not imagen_campo:
        return
    
    # Obtenemos la ruta física del archivo
    path = imagen_campo.path
    if os.path.exists(path):
        img = Image.open(path)
        
        # Redimensionar si es necesario
        if img.height > size[1] or img.width > size[0]:
            img.thumbnail(size)
            # Guardamos con calidad optimizada para reducir los MB a KB
            img.save(path, quality=75, optimize=True)

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("usuario", "Usuario (Trabajador)"),
        ("tecnico", "Técnico"),
        ("administrador", "Administrador/Ingeniero TI"),
    )
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default="usuario")
    telefono = models.CharField(max_length=15, null=True, blank=True) 
    area = models.ForeignKey("Area", on_delete=models.SET_NULL, null=True, blank=True)
    foto = models.ImageField(upload_to="perfiles/", null=True, blank=True)
    last_password_change = models.DateTimeField(default=timezone.now)
    must_change_password = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.foto:
            # Foto de perfil pequeña (300x300)
            resize_image(self.foto, size=(300, 300))

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class Area(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Estado(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

def get_default_estado():
    # Busca el objeto "Pendiente" por nombre. Si no existe, lo crea.
    estado, _ = Estado.objects.get_or_create(name="Pendiente")
    return estado.id

class Incidencia(models.Model):
    CATEGORIA_CHOICES = (
        ("hardware", "Hardware"),
        ("software", "Software"),
        ("red", "Red"),
        ("sistema", "Sistema"),
    )

    PRIORIDAD_CHOICES = (
        ("baja", "Baja"),
        ("media", "Media"),
        ("alta", "Alta"),
        ("critica", "Crítica"),
    )

    # [Campos originales que ya tienes definidos...]
    creador = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name="incidencias_creadas")
    area = models.ForeignKey("Area", on_delete=models.CASCADE)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES)
    descripcion = models.TextField()
    imagen_adjunta = models.ImageField(upload_to="incidencias_imagenes/", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # CAMBIO AQUÍ: Usamos PROTECT para que no borren los estados y la función default
    estado = models.ForeignKey("Estado", on_delete=models.PROTECT, default=get_default_estado)
    
    # Campos de gestión
    tecnico_asignado = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_asignadas")
    fecha_programada_atencion = models.DateField(null=True, blank=True)
    hora_programada_atencion = models.TimeField(null=True, blank=True)
    observaciones_internas = models.TextField(null=True, blank=True)
    
    # Campos de cierre
    solucion_aplicada = models.TextField(null=True, blank=True)
    evidencia_solucion = models.ImageField(upload_to="soluciones_evidencias/", null=True, blank=True)

    # --- PROPIEDADES DE LÓGICA DE NEGOCIO ---
    # Estas sirven para usarlas en el HTML como {% if incidencia.puede_cerrar %}

    @property
    def puede_cerrar(self):
        """Solo el creador puede cerrar si el técnico ya lo marcó como Resuelto."""
        return self.estado.name == "Resuelto"

    @property
    def esta_asignada(self):
        """Verifica si ya tiene técnico."""
        return self.tecnico_asignado is not None

    @property
    def puede_reabrir(self):
        """Si el usuario no está satisfecho con la solución."""
        return self.estado.name == "Resuelto"

    def save(self, *args, **kwargs):
        # 1. Guardamos primero para que el archivo exista en el disco
        super().save(*args, **kwargs)
        
        # 2. Verificamos y optimizamos la imagen del reporte
        if self.imagen_adjunta:
            optimizar_imagen(self.imagen_adjunta)
            
        # 3. Verificamos y optimizamos la imagen de la solución
        if self.evidencia_solucion:
            optimizar_imagen(self.evidencia_solucion)

    def __str__(self):
        return f"Incidencia #{self.id} - {self.descripcion[:50]}"

class Notificacion(models.Model):
    TIPO_CHOICES = (
        ("asignacion", "Asignación"),
        ("estado", "Cambio de Estado"),
        ("comentario", "Nuevo Comentario"),
        ("nueva_incidencia", "Nueva Incidencia"), # Para administradores
        ("incidencia_resuelta", "Incidencia Resuelta"), # Para administradores
    )

    usuario_destino = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="notificaciones")
    incidencia = models.ForeignKey(Incidencia, on_delete=models.CASCADE, null=True, blank=True)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    leido = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    link = models.URLField(max_length=500, null=True, blank=True)

    def __str__(self):
        return f"Notificación para {self.usuario_destino.username} - {self.tipo} ({'Leído' if self.leido else 'No leído'})"

    class Meta:
        ordering = ["-fecha_creacion"]

class Comentario(models.Model):
    TIPO_COMENTARIO_CHOICES = (
        ("tecnico", "Comentario Técnico"),
        ("confirmacion", "Confirmación de Solución"),
        ("persiste", "Problema Persiste"),
        ("observacion", "Observación Interna"),
    )

    incidencia = models.ForeignKey(Incidencia, on_delete=models.CASCADE, related_name="comentarios")
    usuario = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    tipo_comentario = models.CharField(max_length=20, choices=TIPO_COMENTARIO_CHOICES, default="observacion")
    texto = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    evidencia_adjunta = models.ImageField(upload_to="comentarios_evidencias/", null=True, blank=True)

    def __str__(self):
        return f"Comentario en Incidencia #{self.incidencia.id} por {self.usuario.username}"