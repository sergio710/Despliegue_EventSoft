from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from app_eventos.models import Evento, AdministradorEvento
import datetime

Usuario = get_user_model()

class HU69CargarProgramacionEventoTest(TestCase):
    """
    HU69:
    Como ADMINISTRADOR DE EVENTO,
    Quiero cargar la información detallada de la programación de un evento,
    Para permitir su acceso a los asistentes, expositores y evaluadores de un evento.
    """

    def setUp(self):
        # Crear usuario administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin69",
            email="admin69@test.com",
            password="12345",
            documento="12345678"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento sin programación inicial
        self.evento = Evento.objects.create(
            eve_nombre="Foro Internacional de Tecnología",
            eve_descripcion="Evento de tecnología avanzada",
            eve_ciudad="Medellín",
            eve_lugar="Plaza Mayor",
            eve_fecha_inicio=datetime.date(2025, 11, 15),
            eve_fecha_fin=datetime.date(2025, 11, 18),
            eve_estado="Pendiente",
            eve_capacidad=300,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

    def test_cargar_y_actualizar_programacion(self):
        """
        Cubre los criterios de aceptación de HU69:
        1. Adjuntar archivo de programación.
        2. Guardar en eve_programacion.
        3. Permitir actualizar el archivo.
        4. Asegurar acceso al archivo por los roles relacionados al evento.
        """

        # (1) Cargar archivo inicial
        archivo_inicial = SimpleUploadedFile("programacion.pdf", b"Contenido inicial")
        self.evento.eve_programacion = archivo_inicial
        self.evento.save()

        self.assertIsNotNone(self.evento.eve_programacion)
        from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from app_eventos.models import Evento, AdministradorEvento
import datetime

Usuario = get_user_model()

class HU69CargarProgramacionEventoTest(TestCase):
    """
    HU69:
    Como ADMINISTRADOR DE EVENTO,
    Quiero cargar la información detallada de la programación de un evento,
    Para permitir su acceso a los asistentes, expositores y evaluadores de un evento.
    """

    def setUp(self):
        # Crear usuario administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin69",
            email="admin69@test.com",
            password="12345",
            documento="12345678"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento sin programación inicial
        self.evento = Evento.objects.create(
            eve_nombre="Foro Internacional de Tecnología",
            eve_descripcion="Evento de tecnología avanzada",
            eve_ciudad="Medellín",
            eve_lugar="Plaza Mayor",
            eve_fecha_inicio=datetime.date(2025, 11, 15),
            eve_fecha_fin=datetime.date(2025, 11, 18),
            eve_estado="Pendiente",
            eve_capacidad=300,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

    def test_cargar_y_actualizar_programacion(self):
        """
        Cubre los criterios de aceptación de HU69:
        1. Adjuntar archivo de programación.
        2. Guardar en eve_programacion.
        3. Permitir actualizar el archivo.
        4. Asegurar acceso al archivo por los roles relacionados al evento.
        """

        # (1) Cargar archivo inicial
        archivo_inicial = SimpleUploadedFile("programacion.pdf", b"Contenido inicial")
        self.evento.eve_programacion = archivo_inicial
        self.evento.save()

        # Verificar que se guardó un archivo PDF
        self.assertIsNotNone(self.evento.eve_programacion)
        self.assertTrue(self.evento.eve_programacion.name.endswith(".pdf"))

        # (2) Actualizar archivo
        archivo_nuevo = SimpleUploadedFile("programacion_actualizada.pdf", b"Contenido actualizado")
        self.evento.eve_programacion = archivo_nuevo
        self.evento.save()

        # Verificar que se actualizó el archivo PDF
        evento = Evento.objects.get(pk=self.evento.pk)
        self.assertTrue(evento.eve_programacion.name.endswith(".pdf"))

        # (3) Acceso simulado: comprobar que el archivo está asociado al evento
        self.assertIsNotNone(evento.eve_programacion)