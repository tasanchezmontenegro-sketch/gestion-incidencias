# 🛠️ Sistema Web de Gestión de Incidencias Técnicas - UGEL Morropón

Este sistema es una solución integral diseñada para optimizar el registro, asignación y seguimiento de incidencias tecnológicas (software, hardware y red) en una entidad pública. El proyecto mejora la comunicación entre los trabajadores administrativos y el área de Tecnologías de la Información, garantizando trazabilidad, control y eficiencia operativa.

---

## 🚀 Características Principales por Rol

### 🔹 Administrador / Ingeniero TI

* **Control Total:** Gestión de usuarios (creación, edición, activación/desactivación).
* **Asignación Dinámica:** Supervisión global de tickets y asignación según carga laboral.
* **Gestión de Infraestructura:** Administración de áreas institucionales y estados.

### 🔹 Técnico Especialista

* **Panel de Trabajo:** Visualización de incidencias asignadas con programación.
* **Resolución:** Registro de soluciones, evidencias fotográficas y actualización de estados.
* **Historial Técnico:** Seguimiento completo para auditoría.

### 🔹 Usuario (Trabajador)

* **Reporte Rápido:** Creación de incidencias con adjuntos.
* **Seguimiento en Tiempo Real:** Estado del ticket y técnico asignado.
* **Conformidad:** Validación de solución del problema.

---

## 🛠️ Arquitectura y Tecnologías

El sistema se basa en el patrón **MVT (Modelo - Vista - Template)** de Django:

* **Backend:** Django 5.x (Python)
* **Base de Datos:** ORM con modelos como `CustomUser`, `Incidencia`, `Area`, `Estado`
* **Frontend Dinámico:** HTMX para interacciones sin recarga
* **Estilos:** CSS personalizado + Bootstrap
* **Seguridad:** Control de acceso con `@login_required` y roles

---

## 📦 Instalación y Configuración

### 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/tasanchezmontenegro-sketch/gestion-incidencias.git
cd gestion-incidencias
```

---

### 2️⃣ Crear entorno virtual

```bash
python -m venv .venv
```

---

### 3️⃣ Activar entorno virtual

📌 En Windows:

```bash
.\.venv\Scripts\activate
```

📌 En Linux / Mac:

```bash
source .venv/bin/activate
```

---

### 4️⃣ Instalar dependencias

```bash
pip install -r requirements.txt
```

---

### 5️⃣ Preparar base de datos

```bash
python manage.py migrate
```

---

### 6️⃣ Cargar datos iniciales (seed)

```bash
python manage.py seed
```

---

### 7️⃣ Ejecutar servidor

```bash
python manage.py runserver
```

---

## 🌐 Acceso al sistema

Abrir en el navegador:

```
http://127.0.0.1:8000/
```

---

## 📄 Funcionalidades destacadas

* Gestión completa de incidencias
* Paneles personalizados por rol
* Generación de reportes en PDF
* Dashboard interactivo
* Sistema de estados y prioridades
* Exportación de datos

---

## 📁 Estructura del Proyecto

```
gestion-incidencias/
├── gestion_incidencias/
├── tickets/
├── static/
├── templates/
├── db.sqlite3
└── manage.py
```

---

## ⚠️ Recomendaciones

* Activar siempre el entorno virtual antes de trabajar
* Verificar dependencias si hay errores de instalación
* Mantener actualizado el archivo `requirements.txt`

---

## 🧑‍💻 Autor

**Alexander Sánchez Montenegro**

---

## 📌 Estado del Proyecto

* ✔ Sistema funcional
* ✔ Implementación de roles completa
* 🚀 Mejoras continuas en interfaz y reportes PDF
* 🔧 Optimización en curso

---
