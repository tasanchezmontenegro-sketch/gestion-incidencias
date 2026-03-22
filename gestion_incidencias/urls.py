from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

handler404 = 'tickets.views.error_404_view'
handler500 = 'tickets.views.error_500_view'

urlpatterns = [
    path('admin/', admin.site.admin_url if hasattr(admin.site, 'admin_url') else admin.site.urls),
    path('', include('tickets.urls')),  # Las URLs de tu app tickets
]

# ESTA ES LA PARTE CLAVE PARA LAS IMÁGENES
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
