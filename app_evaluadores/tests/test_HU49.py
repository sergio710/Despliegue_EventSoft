from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from app_evaluadores.models import Evaluador, EvaluadorEvento
from app_eventos.models import Evento, AdministradorEvento
from app_usuarios.models import Usuario, Rol, RolUsuario
import datetime
import os

Usuario = get_user_model()

class HU49DescargarMemoriasEvaluadorTest(TestCase):
    """
    HU49:
    Como EVALUADOR,
    Quiero descargar las memorias del evento (presentaciones, documentos, etc),
    Para guardarlas y poder acceder a ellas posteriormente como material de estudio.
    """

    def setUp(self):
        # Crear roles
        rol_admin_evento, created = Rol.objects.get_or_create(nombre='administrador_evento', defaults={'descripcion': 'Rol de administrador de evento'})
        rol_evaluador, created = Rol.objects.get_or_create(nombre='evaluador', defaults={'descripcion': 'Rol de evaluador'})

        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin_evento49",
            email="admin49@test.com",
            password="12345",
            documento="12345678"
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=rol_admin_evento)
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear archivo de memorias simulado y guardarlo en el sistema de archivos
        contenido_original = b"Contenido del archivo de memorias del evento"
        # Usar default_storage para guardar el archivo en la ubicación de medios temporal del test
        archivo_nombre = "memorias_evento_test.pdf"
        archivo_path = default_storage.save(archivo_nombre, ContentFile(contenido_original))

        # Crear evento con memorias
        self.evento = Evento.objects.create(
            eve_nombre="Congreso de Tecnología",
            eve_descripcion="Evento académico sobre nuevas tecnologias",
            eve_ciudad="Medellín",
            eve_lugar="Plaza Mayor",
            eve_fecha_inicio=datetime.date(2025, 8, 10),
            eve_fecha_fin=datetime.date(2025, 8, 12),
            eve_estado="Pendiente",
            eve_capacidad=400,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin,
            # Asignar el path relativo donde se guardó el archivo
            eve_memorias=archivo_path # <-- Archivo de memorias asociado
        )

        # Guardar el contenido original para usarlo en el test
        self.contenido_original = contenido_original

        # Crear evaluador
        self.evaluador_user = Usuario.objects.create_user(
            username="evaluador49",
            email="eva49@correo.com",
            password="12345",
            documento="99999999",
            first_name="Eval",
            last_name="Uador49"
        )
        RolUsuario.objects.create(usuario=self.evaluador_user, rol=rol_evaluador)
        self.evaluador = Evaluador.objects.create(usuario=self.evaluador_user)

        # Relación evaluador-evento (aprobado y confirmado)
        self.evaluador_evento = EvaluadorEvento.objects.create(
            evaluador=self.evaluador,
            evento=self.evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado="Aprobado", # <-- Importante para el acceso
            confirmado=True
        )

    def tearDown(self):
        # Limpiar el archivo temporal creado en setUp
        if self.evento.eve_memorias:
            if default_storage.exists(self.evento.eve_memorias.name):
                default_storage.delete(self.evento.eve_memorias.name)


    def test_evento_tiene_archivo_memorias(self):
        """
        CA1: El evento debe tener un archivo de memorias asociado (campo eve_memorias en el modelo Evento) para que el enlace de descarga esté disponible.
        """
        # Verificar que el evento tiene un archivo de memorias asociado
        self.assertIsNotNone(self.evento.eve_memorias, "El evento debe tener un archivo de memorias asociado.")
        self.assertTrue(self.evento.eve_memorias.name.endswith('.pdf'), "El archivo de memorias debe ser un PDF.")
        # Verificar que el archivo existe físicamente
        self.assertTrue(default_storage.exists(self.evento.eve_memorias.name), "El archivo de memorias debe existir físicamente.")


    def test_descarga_archivo_memorias_evaluador_aprobado(self):
        """
        CA2: Al hacer clic en el enlace o botón de descarga, el archivo de memorias debe comenzar a descargarse en el navegador del evaluador.
        CA3: El archivo descargado debe ser idéntico al archivo originalmente subido como memorias del evento.
        """
        # Simular login del evaluador
        self.client.login(email="eva49@correo.com", password="12345")
        session = self.client.session
        session['rol_sesion'] = 'evaluador'
        session.save()

        # Acceder a la vista de descarga
        url_descarga = reverse('descargar_memorias_evaluador', kwargs={'evento_id': self.evento.eve_id})
        response = self.client.get(url_descarga)

        # Verificar que la respuesta sea un archivo adjunto (download)
        self.assertEqual(response.status_code, 200, "La vista debería devolver el archivo.")
        content_disposition = response.get('Content-Disposition')
        self.assertTrue(content_disposition and 'attachment' in content_disposition, "La respuesta debe indicar que es un archivo adjunto para descargar.")
        # El nombre en la descarga puede ser el último segmento del path
        self.assertIn('memorias_evento_test.pdf', content_disposition, "El nombre del archivo en la descarga debe coincidir con el original.")

        # Verificar que el contenido del archivo descargado sea idéntico al original
        contenido_descargado = b''.join(response.streaming_content)
        # Usar el contenido original guardado en setUp
        self.assertEqual(contenido_descargado, self.contenido_original, "El archivo descargado debe ser idéntico al original subido.")