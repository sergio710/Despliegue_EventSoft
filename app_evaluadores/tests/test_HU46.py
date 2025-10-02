from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from app_evaluadores.models import Evaluador, EvaluadorEvento, Criterio, Calificacion
from app_eventos.models import Evento, AdministradorEvento
from app_participantes.models import Participante, ParticipanteEvento, Proyecto
from app_usuarios.models import Usuario, Rol, RolUsuario
import datetime

Usuario = get_user_model()

class HU46VisualizarTablaPosicionesTest(TestCase):
    """
    HU46:
    Como EVALUADOR,
    Quiero visualizar la tabla de posiciones con los puntajes obtenidos por todos los expositores del evento en el que soy evaluador,
    Para identificar a los ganadores y el desempeño general de los participantes.
    """

    def setUp(self):
        # Crear roles (todos los roles que se usarán deben crearse aquí)
        rol_admin_evento, created = Rol.objects.get_or_create(nombre='administrador_evento', defaults={'descripcion': 'Rol de administrador de evento'})
        rol_evaluador, created = Rol.objects.get_or_create(nombre='evaluador', defaults={'descripcion': 'Rol de evaluador'})
        rol_participante, created = Rol.objects.get_or_create(nombre='participante', defaults={'descripcion': 'Rol de participante'})

        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin_evento46",
            email="admin46@test.com",
            password="12345",
            documento="12345678"
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=rol_admin_evento) # <-- Usar la variable 'rol_admin_evento'
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evaluador
        self.evaluador_user = Usuario.objects.create_user(
            username="evaluador46",
            email="eva46@test.com",
            password="12345",
            documento="99999999",
            first_name="Eval",
            last_name="Uador"
        )
        RolUsuario.objects.create(usuario=self.evaluador_user, rol=rol_evaluador)
        self.evaluador = Evaluador.objects.create(usuario=self.evaluador_user)

        # Crear evento
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

        # Crear participantes
        self.participante1_user = Usuario.objects.create_user(
            username="part1",
            email="part1@test.com",
            password="12345",
            documento="11111111",
            first_name="Participante",
            last_name="Uno"
        )
        RolUsuario.objects.create(usuario=self.participante1_user, rol=rol_participante)
        self.participante1 = Participante.objects.create(usuario=self.participante1_user)

        self.participante2_user = Usuario.objects.create_user(
            username="part2",
            email="part2@test.com",
            password="12345",
            documento="22222222",
            first_name="Participante",
            last_name="Dos"
        )
        RolUsuario.objects.create(usuario=self.participante2_user, rol=rol_participante)
        self.participante2 = Participante.objects.create(usuario=self.participante2_user)

        self.participante3_user = Usuario.objects.create_user(
            username="part3",
            email="part3@test.com",
            password="12345",
            documento="33333333",
            first_name="Participante",
            last_name="Tres"
        )
        RolUsuario.objects.create(usuario=self.participante3_user, rol=rol_participante)
        self.participante3 = Participante.objects.create(usuario=self.participante3_user)

        # Crear proyecto grupal
        self.proyecto_grupal = Proyecto.objects.create(
            evento=self.evento,
            titulo="Proyecto Grupal",
            descripcion="Un proyecto grupal de prueba"
        )

        # Crear participantes en el evento
        self.participante1_evento = ParticipanteEvento.objects.create(
            participante=self.participante1,
            evento=self.evento,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado="Aprobado",
            confirmado=True,
            proyecto=self.proyecto_grupal # Grupal
        )
        self.participante2_evento = ParticipanteEvento.objects.create(
            participante=self.participante2,
            evento=self.evento,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado="Aprobado",
            confirmado=True,
            proyecto=None # Individual
        )
        self.participante3_evento = ParticipanteEvento.objects.create(
            participante=self.participante3,
            evento=self.evento,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado="Aprobado",
            confirmado=True,
            proyecto=None # Individual
        )

        # Crear criterios
        self.criterio1 = Criterio.objects.create(
            cri_descripcion="Dominio del Tema",
            cri_peso=50.0,
            cri_evento_fk=self.evento
        )
        self.criterio2 = Criterio.objects.create(
            cri_descripcion="Innovación",
            cri_peso=50.0,
            cri_evento_fk=self.evento
        )

        # Simular calificaciones para tener puntajes
        # Participante 1: 4 y 5 -> (4*0.5 + 5*0.5) = 4.5
        Calificacion.objects.create(evaluador=self.evaluador, participante=self.participante1, criterio=self.criterio1, cal_valor=4)
        Calificacion.objects.create(evaluador=self.evaluador, participante=self.participante1, criterio=self.criterio2, cal_valor=5)
        self.participante1_evento.par_eve_valor = 4.5
        self.participante1_evento.save()

        # Participante 2: 5 y 4 -> (5*0.5 + 4*0.5) = 4.5
        Calificacion.objects.create(evaluador=self.evaluador, participante=self.participante2, criterio=self.criterio1, cal_valor=5)
        Calificacion.objects.create(evaluador=self.evaluador, participante=self.participante2, criterio=self.criterio2, cal_valor=4)
        self.participante2_evento.par_eve_valor = 4.5
        self.participante2_evento.save()

        # Participante 3: 3 y 3 -> (3*0.5 + 3*0.5) = 3.0
        Calificacion.objects.create(evaluador=self.evaluador, participante=self.participante3, criterio=self.criterio1, cal_valor=3)
        Calificacion.objects.create(evaluador=self.evaluador, participante=self.participante3, criterio=self.criterio2, cal_valor=3)
        self.participante3_evento.par_eve_valor = 3.0
        self.participante3_evento.save()


    def test_acceso_condicionado_evaluador_aprobado(self):
        """
        CA1: El evaluador solo puede acceder a la tabla de posiciones de un evento si está registrado y aprobado como evaluador en ese evento específico.
        """
        # Simular login del evaluador
        self.client.login(email="eva46@test.com", password="12345")
        session = self.client.session
        session['rol_sesion'] = 'evaluador'
        session.save()

        # Intentar acceder a la tabla de posiciones
        url = reverse('tabla_posiciones_evaluador', kwargs={'eve_id': self.evento.eve_id})
        response = self.client.get(url)

        # Verificar que puede acceder (200 OK)
        self.assertEqual(response.status_code, 200)


    def test_visualizacion_participantes_ordenados(self):
        """
        CA2: La tabla debe mostrar a todos los participantes/expositores aprobados del evento, ordenados por su puntaje total de forma descendente.
        """
        # Simular login del evaluador
        self.client.login(email="eva46@test.com", password="12345")
        session = self.client.session
        session['rol_sesion'] = 'evaluador'
        session.save()

        # Acceder a la tabla de posiciones
        url = reverse('tabla_posiciones_evaluador', kwargs={'eve_id': self.evento.eve_id})
        response = self.client.get(url)

        # Verificar que la respuesta es exitosa
        self.assertEqual(response.status_code, 200)

        # Verificar que los participantes están en el contexto y ordenados por puntaje descendente
        posiciones = response.context['posiciones']
        puntajes = [p['puntaje'] for p in posiciones]
        self.assertEqual(puntajes, sorted(puntajes, reverse=True), "Los participantes deben estar ordenados por puntaje descendente")


    def test_datos_participante_tabla(self):
        """
        CA3: La tabla debe incluir, al menos, el nombre completo, correo electrónico, tipo de proyecto (grupal o individual) y el puntaje total calculado.
        """
        # Simular login del evaluador
        self.client.login(email="eva46@test.com", password="12345")
        session = self.client.session
        session['rol_sesion'] = 'evaluador'
        session.save()

        # Acceder a la tabla de posiciones
        url = reverse('tabla_posiciones_evaluador', kwargs={'eve_id': self.evento.eve_id})
        response = self.client.get(url)

        # Verificar que la respuesta es exitosa
        self.assertEqual(response.status_code, 200)

        # Verificar que los datos requeridos estén en la respuesta HTML
        # Nombre completo
        self.assertContains(response, "Participante Uno")
        self.assertContains(response, "Participante Dos")
        self.assertContains(response, "Participante Tres")
        # Correo
        self.assertContains(response, "part1@test.com")
        self.assertContains(response, "part2@test.com")
        self.assertContains(response, "part3@test.com")
        # Tipo de proyecto (Grupal / Individual)
        self.assertContains(response, "Proyecto Grupal") # Uno es grupal
        self.assertContains(response, "Individual") # Dos y Tres son individuales
        # Puntaje
        # En el HTML, el puntaje puede estar formateado como 4,5 o 4.5
        response_content = response.content.decode('utf-8')
        self.assertTrue("4,5" in response_content or "4.5" in response_content)
        self.assertTrue("3,0" in response_content or "3.0" in response_content)


    def test_puntaje_total_actualizado(self):
        """
        CA4: Los puntajes mostrados deben reflejar las calificaciones más recientes registradas por los evaluadores del evento.
        """
        # Simular login del evaluador
        self.client.login(email="eva46@test.com", password="12345")
        session = self.client.session
        session['rol_sesion'] = 'evaluador'
        session.save()

        # Acceder a la tabla de posiciones
        url = reverse('tabla_posiciones_evaluador', kwargs={'eve_id': self.evento.eve_id})
        response = self.client.get(url)

        # Verificar que la respuesta es exitosa
        self.assertEqual(response.status_code, 200)

        # Verificar que los puntajes mostrados coincidan con los guardados en la base de datos
        # para los participantes relevantes.
        # Este test asume que la vista calcula y guarda correctamente el par_eve_valor
        # en el modelo ParticipanteEvento. El test verifica que el valor guardado
        # esté en la respuesta HTML.
        response_content = response.content.decode('utf-8')
        # Verificamos que los puntajes esperados estén presentes
        # Si hay más evaluadores, el cálculo puede cambiar. Este test es simple.
        self.assertTrue("4,5" in response_content or "4.5" in response_content)
        self.assertTrue("3,0" in response_content or "3.0" in response_content)


    def test_identificacion_ganadores(self):
        """
        CA5: Debe existir una forma clara de identificar al primer, segundo y tercer lugar (por ejemplo, con iconos o resaltados).
        """
        # Simular login del evaluador
        self.client.login(email="eva46@test.com", password="12345")
        session = self.client.session
        session['rol_sesion'] = 'evaluador'
        session.save()

        # Acceder a la tabla de posiciones
        url = reverse('tabla_posiciones_evaluador', kwargs={'eve_id': self.evento.eve_id})
        response = self.client.get(url)

        # Verificar que la respuesta es exitosa
        self.assertEqual(response.status_code, 200)

        # Verificar que hay elementos en la tabla que indiquen el puesto
        # El HTML muestra posiciones únicas consecutivas, incluso si hay puntajes iguales.
        # Por ejemplo, si dos participantes tienen 4.5, uno puede ser #1 y el otro #2 según su ID u orden de inserción.
        # El HTML real muestra:
        # <tr>...<td><strong>#1</strong> 🥇 ...</td>...</tr>
        # <tr>...<td><strong>#2</strong> 🥈 ...</td>...</tr>
        # <tr>...<td><strong>#3</strong> 🥉 ...</td>...</tr>
        # Verificamos que aparezcan las etiquetas de puesto esperadas, asumiendo el comportamiento real.
        # No asumimos empatados, sino posiciones únicas consecutivas.
        self.assertContains(response, "<strong>#1</strong>", count=1, html=True) # Un primer lugar
        self.assertContains(response, "<strong>#2</strong>", count=1, html=True) # Un segundo lugar
        self.assertContains(response, "<strong>#3</strong>", count=1, html=True) # Un tercer lugar
        # O también:
        # self.assertContains(response, "🥇")
        # self.assertContains(response, "🥈")
        # self.assertContains(response, "🥉")


    def test_disponibilidad_exportacion_pdf(self):
        """
        CA6: El sistema debe ofrecer la opción de descargar la tabla de posiciones en formato PDF.
        """
        # Simular login del evaluador
        self.client.login(email="eva46@test.com", password="12345")
        session = self.client.session
        session['rol_sesion'] = 'evaluador'
        session.save()

        # Acceder a la tabla de posiciones
        url = reverse('tabla_posiciones_evaluador', kwargs={'eve_id': self.evento.eve_id})
        response = self.client.get(url)

        # Verificar que la respuesta es exitosa
        self.assertEqual(response.status_code, 200)

        # Verificar que hay un enlace para descargar el PDF
        # El HTML de ejemplo mostraba: <a href="/evaluador/descargar-tabla-posiciones-pdf/6/" class="btn btn-primary">...</a>
        url_pdf = reverse('descargar_tabla_posiciones_pdf', kwargs={'eve_id': self.evento.eve_id})
        self.assertContains(response, url_pdf)
        # O buscar el texto del botón
        self.assertContains(response, "Ver o Descargar Tabla de Posiciones (PDF)")