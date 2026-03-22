from django.shortcuts import redirect
from django.urls import reverse

class ForzarCambioPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Si debe cambiar contraseña y no está ya en las páginas permitidas
            if getattr(request.user, 'must_change_password', False):
                
                # Definimos rutas que NO disparan la redirección
                # Añadimos 'password_change_forced' que será nuestra nueva vista limpia
                rutas_permitidas = [
                    reverse('password_change_forced'), 
                    reverse('logout'),
                ]

                if request.path not in rutas_permitidas:
                    return redirect('password_change_forced')

        return self.get_response(request)