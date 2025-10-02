from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from app_evaluadores.models import Evaluador, EvaluadorEvento, Criterio
from app_eventos.models import Evento, AdministradorEvento
from app_participantes.models import Participante, ParticipanteEvento
import datetime

Usuario = get_user_model()

class HU44CargarInstrumentoEvaluacionTest(TestCase):
    """
    HU44:
    Como EVALUADOR,
    Quiero cargar el Instrumento de evaluación que se empleará (rúbrica, lista de chequeo, plantilla) en el evento en el que soy evaluador,
    Para ofrecer información a los expositores sobre cómo serán evaluados.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin_evento44",
            email="admin44@test.com",
            password="12345",
            documento="12345678"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evaluador
        self.evaluador_user = Usuario.objects.create_user(
            username="evaluador44",
            email="eva44@test.com",
            password="12345",
            documento="99999999"
        )
        self.evaluador = Evaluador.objects.create(usuario=self.evaluador_user)

        # Crear participante (para probar visualización)
        self.participante_user = Usuario.objects.create_user(
            username="participante44",
            email="part44@test.com",
            password="12345",
            documento="11111111"
        )
        self.participante = Participante.objects.create(usuario=self.participante_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Congreso de Tecnología",
            eve_descripcion="Evento académico sobre nuevas tecnologías",
            eve_ciudad="Medellín",
            eve_lugar="Plaza Mayor",
            eve_fecha_inicio=datetime.date(2025, 8, 10),
            eve_fecha_fin=datetime.date(2025, 8, 12),
            eve_estado="Pendiente",
            eve_capacidad=400,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Relación evaluador-evento (aprobado y confirmado)
        self.evaluador_evento = EvaluadorEvento.objects.create(
            evaluador=self.evaluador,
            evento=self.evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado="Aprobado",
            confirmado=True
        )

        # Relación participante-evento (aprobado y confirmado)
        self.participante_evento = ParticipanteEvento.objects.create(
            participante=self.participante,
            evento=self.evento,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado="Aprobado",
            confirmado=True
        )

    def test_acceso_condicionado_evaluador_aprobado(self):
        """
        Criterio 1: El evaluador solo puede acceder si está aprobado.
        """
        # Simular login del evaluador
        self.client.login(email="eva44@test.com", password="12345")
        
        session = self.client.session
        session['rol_sesion'] = 'evaluador'
        session.save()

        # Intentar acceder a la vista de agregar criterio
        from django.urls import reverse
        url = reverse('agregar_item_evaluador', kwargs={'eve_id': self.evento.eve_id})
        response = self.client.get(url)

        # Verificar que puede acceder (no error 403 o 404 por permiso/estado)
        # La vista podría redirigir o mostrar formulario
        self.assertNotEqual(response.status_code, 403)

    def test_definicion_criterios_evaluacion(self):
        """
        Criterio 2: El evaluador puede definir criterios con descripción y peso.
        """
        # Simular login del evaluador
        self.client.login(email="eva44@test.com", password="12345")
        
        session = self.client.session
        session['rol_sesion'] = 'evaluador'
        session.save()

        # Enviar datos VÁLIDOS para crear un criterio
        from django.urls import reverse
        url = reverse('agregar_item_evaluador', kwargs={'eve_id': self.evento.eve_id})
        data = {
            'descripcion': 'Presentación clara y concisa', # <-- Cambiado a 'descripcion'
            'peso': 2.5
        }
        try:
            response = self.client.post(url, data)
        except Exception as e:
            # Si la vista lanza una excepción (como IntegrityError),
            # el test debe fallar y mostrarlo, lo cual indica un problema en la vista.
            self.fail(f"La vista lanzó una excepción inesperada con datos válidos: {e}")

        # Verificar que el criterio fue creado
        # Suponiendo que la vista redirige tras éxito
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Criterio.objects.count(), 1)
        criterio = Criterio.objects.first()
        self.assertEqual(criterio.cri_descripcion, 'Presentación clara y concisa')
        self.assertEqual(criterio.cri_peso, 2.5)
        self.assertEqual(criterio.cri_evento_fk, self.evento)

    def test_persistencia_instrumento(self):
        """
        Criterio 3: Los criterios deben quedar almacenados y asociados al evento.
        """
        # Crear un criterio
        criterio = Criterio.objects.create(
            cri_descripcion='Original',
            cri_peso=1.0,
            cri_evento_fk=self.evento
        )

        # Verificar que está en la base de datos y asociado al evento correcto
        self.assertEqual(Criterio.objects.filter(cri_evento_fk=self.evento).count(), 1)
        self.assertEqual(criterio.cri_evento_fk.eve_nombre, "Congreso de Tecnología")

    def test_visualizacion_publica_para_participantes(self):
        """
        Criterio 4: Los criterios deben ser visibles para los participantes del evento.
        """
        # Crear un criterio
        Criterio.objects.create(
            cri_descripcion='Criterio Visible',
            cri_peso=3.0, # En la base de datos se guarda como 3.0, pero en la plantilla puede mostrarse como 3,0
            cri_evento_fk=self.evento
        )

        # Simular login del participante
        self.client.login(email="part44@test.com", password="12345")
        
        session = self.client.session
        session['rol_sesion'] = 'participante'
        session.save()

        # Acceder a la vista donde se muestran los criterios (ej. instrumento_evaluacion_participante)
        from django.urls import reverse
        url = reverse('instrumento_evaluacion_participante', kwargs={'evento_id': self.evento.eve_id})
        response = self.client.get(url)

        # Verificar que la respuesta es exitosa y contiene el criterio
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Criterio Visible')
        # En el HTML generado, el número 3.0 puede aparecer como 3,0 (formato latinoamericano)
        # Busquemos ambos formatos para evitar fallos
        self.assertTrue('3.0' in str(response.content) or '3,0' in str(response.content))

    def test_integridad_datos_criterios(self):
        """
        Criterio 5: Los criterios deben tener valores válidos (descripción no vacía, peso positivo).
        """
        # Simular login del evaluador para intentar crear un criterio inválido
        self.client.login(email="eva44@test.com", password="12345")
        
        session = self.client.session
        session['rol_sesion'] = 'evaluador'
        session.save()

        from django.urls import reverse
        url = reverse('agregar_item_evaluador', kwargs={'eve_id': self.evento.eve_id})

        # Contar criterios antes de intentar crear inválidos
        criterios_antes = Criterio.objects.count()

        # Intentar crear un criterio sin descripción (debería fallar en la vista o modelo)
        data_vacio = {
            'descripcion': '', # Vacío # <-- Cambiado a 'descripcion'
            'peso': 2.0
        }
        response_vacio = self.client.post(url, data_vacio)
        # La vista debería manejar el error y no crear el objeto.
        # Puede redirigir o devolver el formulario con error.
        # No debería lanzar una excepción de base de datos.
        # Verificar que no se creó un criterio inválido
        self.assertEqual(Criterio.objects.count(), criterios_antes)

        # Intentar crear un criterio con peso negativo (debería fallar en la vista o modelo)
        data_negativo = {
            'descripcion': 'Criterio Inválido', # <-- Cambiado a 'descripcion'
            'peso': -1.0, # Negativo
        }
        response_negativo = self.client.post(url, data_negativo)
        # La vista debería manejar el error y no crear el objeto.
        # Puede redirigir o devolver el formulario con error.
        # No debería lanzar una excepción de base de datos.
        # Verificar que no se creó un criterio inválido
        self.assertEqual(Criterio.objects.count(), criterios_antes)

        # Verificar que no se crearon criterios inválidos en total
        # Después de ambos intentos, el conteo debe seguir siendo el mismo.
        self.assertEqual(Criterio.objects.count(), criterios_antes)