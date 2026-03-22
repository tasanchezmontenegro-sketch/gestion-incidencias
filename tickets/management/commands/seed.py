from django.core.management.base import BaseCommand
from tickets.models import Area, Estado  # Verifica que estos sean tus nombres de modelos

class Command(BaseCommand):
    help = 'Limpia datos de prueba y carga la configuración inicial'

    def handle(self, *args, **kwargs):
        self.stdout.write('Iniciando carga de datos iniciales...')

        # --- 1. Crear Áreas ---
        # Basado en tus capturas, estas son las principales
        areas_nombres = ['Tesorería', 'Informática', 'Recursos Humanos', 'Mantenimiento', 'Administración']
        
        for nombre in areas_nombres:
            obj, created = Area.objects.get_or_create(name=nombre)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Área creada: {nombre}'))

        # --- 2. Crear Estados ---
        # Definimos nombre y el color que usas en tus badges/dots
        estados_data = [
            {'name': 'Pendiente', 'color': '#f59e0b'},
            {'name': 'En Proceso', 'color': '#2563eb'},
            {'name': 'Resuelto', 'color': '#16a34a'},
            {'name': 'Cerrado', 'color': '#64748b'},
        ]

        for data in estados_data:
            # Usamos get_or_create para no duplicar si ya existen
            obj, created = Estado.objects.get_or_create(name=data['name'])
            # Si tu modelo Estado tiene un campo 'color', descomenta la siguiente línea:
            # obj.color = data['color']; obj.save()
            if created:
                self.stdout.write(self.style.SUCCESS(f'Estado creado: {data["name"]}'))

        self.stdout.write(self.style.SUCCESS('¡Configuración inicial lista para trabajar!'))