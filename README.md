Despliegue en línea (PythonAnywhere)

EventSoft – Gestión de eventos de divulgación SENA.

EventSoft es una aplicación web desarrollada con Django para gestionar eventos de divulgación del SENA, cubriendo todo el ciclo de vida de un evento: creación, publicación, inscripciones, evaluación y certificación.​
La plataforma maneja varios roles: Visitante Web, Asistente, Participante/Expositor, Evaluador, Administrador de Evento y Super Admin, cada uno con vistas y permisos específicos para registrar eventos, inscribirse, cargar documentación, evaluar proyectos y emitir certificados en PDF.​

Roles y funcionalidades principales.

Visitante Web: consulta eventos disponibles, filtra por criterios y se inscribe a eventos de interés.​

Asistente: gestiona su inscripción, soportes de pago y descarga certificados de asistencia.​

Participante/Expositor: registra proyectos, sube documentación y recibe calificaciones y certificados de participación o premiación.​

Evaluador: gestiona instrumentos de evaluación, califica proyectos y consulta resultados y reportes.​

Administrador de Evento: crea y configura eventos, administra inscripciones de asistentes, expositores y evaluadores, valida pagos, envía notificaciones y genera certificados.​

Super Admin: gestiona códigos de invitación para administradores de evento, supervisa eventos activos y estadísticas generales.​

Integrantes del equipo
- Sergio Castaño Sánchez
- Daniel Dávila
- Jhonatan Escobar
- Jenny Ríos

La aplicación está desplegada en PythonAnywhere y accesible en:
https://correosdjango073.pythonanywhere.com/

Uso en línea.
1. Abrir la URL anterior en un navegador web.​

2. Desde la página principal se puede:

- Ver el listado de eventos públicos como Visitante Web.​

- Usar el enlace de inicio de sesión para acceder como Super Admin, Administrador de Evento u otros roles (credenciales suministradas por el equipo).​


Resumen del proceso de despliegue en PythonAnywhere

1. Registrarse en PythonAnywhere

- Crear cuenta gratuita (“Create a Beginner account”) e iniciar sesión.​

2. Crear la Web App

- Ir a la pestaña Web → Add a new web app.

- Elegir Manual configuration y seleccionar la versión de Python (por ejemplo, 3.10).​

3. Clonar el repositorio en una consola de PythonAnywhere

- Abrir una consola Bash desde PythonAnywhere (pestaña Consoles).

- Ejecutar:
git clone <URL_DEL_REPOSITORIO>
cd <carpeta_del_proyecto>

4. Crear y configurar el entorno virtual en PythonAnywhere

- En esa misma consola Bash:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

5. Configurar Django para producción en PythonAnywhere

Editar settings.py dentro del proyecto:

- Dominio permitido:
ALLOWED_HOSTS = ["correosdjango073.pythonanywhere.com"]

- Base de datos MySQL (usar datos del panel “Databases” de PythonAnywhere):

python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "USUARIO$default",
        "USER": "USUARIO",
        "PASSWORD": "PASSWORD_DB",
        "HOST": "USUARIO.mysql.pythonanywhere-services.com",
        "PORT": "3306",
    }
}

- Archivos estáticos y media:

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

- Configuración de correo (SMTP Gmail o proveedor externo):

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"  # o el host SMTP de tu proveedor
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "tu_correo@example.com"
EMAIL_HOST_PASSWORD = "tu_password_o_app_password"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

6. Aplicar migraciones y crear superusuario (en consola Bash de PythonAnywhere)

Con el entorno virtual activo y situado en la carpeta del proyecto:

python manage.py migrate
python manage.py createsuperuser

7. Configurar WSGI y archivos estáticos en el panel “Web”

- En la pestaña Web, seleccionar la web app creada.

- En Virtualenv, indicar la ruta al entorno virtual (/home/USUARIO/<carpeta_del_proyecto>/venv).​

- En Code → WSGI configuration file, editar para que apunte al wsgi.py del proyecto, por ejemplo:

import os
import sys

path = "/home/USUARIO/<carpeta_del_proyecto>"
if path not in sys.path:
    sys.path.append(path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "preventsoft.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

- En la sección Static files del panel “Web”, añadir:

    - URL: /static/ → Directory: /home/USUARIO/<carpeta_del_proyecto>/staticfiles

    - URL: /media/ → Directory: /home/USUARIO/<carpeta_del_proyecto>/media

- Hacer clic en Reload para reiniciar la web app.​

Con estos pasos, EventSoft queda disponible en la URL pública indicada, usando la base de datos MySQL de PythonAnywhere, almacenamiento de archivos media y envío de correos SMTP desde el servidor.


Clonación y ejecución en entorno de desarrollo (vía PythonAnywhere)
En este proyecto, el entorno de “desarrollo remoto” también se gestiona desde las consolas de PythonAnywhere, usando el mismo código y entorno virtual que la aplicación desplegada.​

1. Abrir consola Bash en PythonAnywhere

Ir a la pestaña Consoles → Start a new console → Bash.​

2. Clonar el repositorio (si aún no existe)

git clone <URL_DEL_REPOSITORIO>
cd <carpeta_del_proyecto>

3. Crear y activar entorno virtual en PythonAnywhere

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

4. Configurar variables de entorno / settings locales (opcional)

- Puedes definir variables de entorno en la pestaña Web → Environment variables o en la Bash antes de ejecutar comandos, para valores sensibles como:

    - SECRET_KEY

    - Credenciales de base de datos (si usas otra BD distinta a la de producción).

    - Credenciales de correo (EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, etc.).​

- Asegúrate de que estos datos y archivos específicos (por ejemplo, settings_local.py) estén incluidos en .gitignore para no publicarlos en el repositorio.​

5. Aplicar migraciones y crear superusuario (si hace falta)

python manage.py migrate
python manage.py createsuperuser

6. Probar la aplicación (modo desarrollo en consola de PythonAnywhere)

Si quieres ejecutar el servidor de desarrollo dentro de PythonAnywhere (para pruebas internas), puedes usar:

python manage.py runserver 0.0.0.0:8000
Luego usarás la consola web de PythonAnywhere solo para verificar logs; el acceso público normal se hace a través de la URL de la web app configurada (no directamente al puerto 8000).​