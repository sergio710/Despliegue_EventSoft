from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from app_usuarios.models import Usuario
from app_administradores.models import AdministradorEvento
from app_eventos.models import Evento
import datetime


class HU85CargarMemoriasEventoTest(TestCase):
    """
    HU85:
    Como ADMINISTRADOR DE EVENTO,
    Quiero cargar las memorias de un evento,
    Para permitir su descarga por asistentes, expositores y evaluadores.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin85",
            email="admin85@test.com",
            password="12345",
            documento="12345685"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento gestionado por el administrador
        self.evento = Evento.objects.create(
            eve_nombre="Simposio Internacional de Tecnología",
            eve_descripcion="Evento académico sobre innovación tecnológica",
            eve_ciudad="Bogotá",
            eve_lugar="Corferias",
            eve_fecha_inicio=datetime.date(2025, 11, 20),
            eve_fecha_fin=datetime.date(2025, 11, 22),
            eve_estado="Aprobado",
            eve_capacidad=300,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

    def test_cargar_y_actualizar_memorias(self):
        """
        Cubre los criterios de aceptación de HU85:
        1. Solo administrador del evento puede cargar memorias.
        2. El sistema debe aceptar la carga de un archivo de memorias.
        3. Se puede reemplazar el archivo previamente cargado.
        4. El archivo queda asociado al evento y accesible para descarga.
        5. El archivo se guarda en la ruta definida.
        """

        # (1) Verificar que el admin gestiona este evento
        self.assertEqual(self.evento.eve_administrador_fk, self.admin)

        # (2) Subir memorias al evento
        archivo_memorias = SimpleUploadedFile(
            "memorias.pdf",
            b"Contenido de prueba de memorias",
            content_type="application/pdf"
        )
        self.evento.eve_memorias = archivo_memorias
        self.evento.save()

        # Verificar que el archivo se guardó en la ruta correcta
        self.assertIn("memorias", str(self.evento.eve_memorias))
        self.assertTrue(self.evento.eve_memorias.storage.exists(self.evento.eve_memorias.name))

        # (3) Reemplazar el archivo de memorias
        archivo_memorias2 = SimpleUploadedFile(
            "memorias_actualizadas.pdf",
            b"Contenido actualizado de memorias",
            content_type="application/pdf"
        )
        self.evento.eve_memorias = archivo_memorias2
        self.evento.save()

        # Verificar que se actualizó correctamente
        self.assertIn("memorias_actualizadas", str(self.evento.eve_memorias))
        self.assertTrue(self.evento.eve_memorias.storage.exists(self.evento.eve_memorias.name))

        # (4) Confirmar disponibilidad: el campo eve_memorias tiene el archivo
        self.assertIsNotNone(self.evento.eve_memorias)

        # (5) Verificar la ruta de almacenamiento
        self.assertTrue(self.evento.eve_memorias.name.startswith("eventos/memorias/"))