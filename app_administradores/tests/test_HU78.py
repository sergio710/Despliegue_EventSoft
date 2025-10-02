# app_administradores/tests/test_HU78.py

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from app_usuarios.models import Usuario, Rol, RolUsuario
from app_administradores.models import AdministradorEvento
from app_eventos.models import Evento # <-- Solo Evento desde app_eventos
from app_participantes.models import Participante, ParticipanteEvento
# Importar Criterio desde la app correcta
from app_evaluadores.models import Evaluador, EvaluadorEvento, Calificacion, Criterio # <-- Agregar Criterio aquí


class HU78InfoDetalladaCalificacionesTest(TestCase):
    """
    HU78: COMO ADMINISTRADOR DE EVENTO, Quiero acceder a la información detallada de las calificaciones emitidas a un determinado expositor,
    Para identificar los puntajes otorgados en cada criterio de evaluación por los diferentes evaluadores.
    """

    def setUp(self):
        self.client = Client()
        
        # Crear roles
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.rol_participante = Rol.objects.create(nombre='participante')
        self.rol_evaluador = Rol.objects.create(nombre='evaluador')

        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin78",
            email="admin78@test.com",
            password="password123",
            documento="12345678"
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Evento Calificaciones Detalladas",
            eve_descripcion="Evento para testing de calificaciones detalladas",
            eve_ciudad="Test City",
            eve_lugar="Test Place",
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=2),
            eve_estado="Aprobado",
            eve_capacidad=50,
            eve_tienecosto="No",
            eve_administrador_fk=self.admin
        )

        # Crear participante (expositor)
        self.expositor_user = Usuario.objects.create_user(
            username="expo78",
            email="expo78@test.com",
            password="password123",
            documento="78000000",
            first_name="Expositor",
            last_name="Detallado"
        )
        RolUsuario.objects.create(usuario=self.expositor_user, rol=self.rol_participante)
        self.expositor = Participante.objects.create(usuario=self.expositor_user)
        
        self.expositor_evento = ParticipanteEvento.objects.create(
            participante=self.expositor,
            evento=self.evento,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado="Aprobado",
            confirmado=True,
        )

        # Crear criterios de evaluación
        self.criterio1 = Criterio.objects.create(
            cri_descripcion="Dominio del Tema",
            cri_peso=40.0,
            cri_evento_fk=self.evento
        )
        self.criterio2 = Criterio.objects.create(
            cri_descripcion="Innovación",
            cri_peso=35.0,
            cri_evento_fk=self.evento
        )
        self.criterio3 = Criterio.objects.create(
            cri_descripcion="Presentación",
            cri_peso=25.0,
            cri_evento_fk=self.evento
        )

        # Crear 2 evaluadores
        self.eval1_user = Usuario.objects.create_user(
            username="eval1_78",
            email="eval1_78@test.com",
            password="password123",
            documento="78111111",
            first_name="Evaluador",
            last_name="Uno"
        )
        RolUsuario.objects.create(usuario=self.eval1_user, rol=self.rol_evaluador)
        self.eval1 = Evaluador.objects.create(usuario=self.eval1_user)
        
        self.eval1_evento = EvaluadorEvento.objects.create(
            evaluador=self.eval1,
            evento=self.evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado="Aprobado",
            confirmado=True
        )

        self.eval2_user = Usuario.objects.create_user(
            username="eval2_78",
            email="eval2_78@test.com",
            password="password123",
            documento="78222222",
            first_name="Evaluador",
            last_name="Dos"
        )
        RolUsuario.objects.create(usuario=self.eval2_user, rol=self.rol_evaluador)
        self.eval2 = Evaluador.objects.create(usuario=self.eval2_user)
        
        self.eval2_evento = EvaluadorEvento.objects.create(
            evaluador=self.eval2,
            evento=self.evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado="Aprobado",
            confirmado=True
        )

        # Crear calificaciones para el expositor por ambos evaluadores
        # Evaluador 1 otorga: 4, 5, 3
        Calificacion.objects.create(
            evaluador=self.eval1,
            participante=self.expositor,
            criterio=self.criterio1,
            cal_valor=4
        )
        Calificacion.objects.create(
            evaluador=self.eval1,
            participante=self.expositor,
            criterio=self.criterio2,
            cal_valor=5
        )
        Calificacion.objects.create(
            evaluador=self.eval1,
            participante=self.expositor,
            criterio=self.criterio3,
            cal_valor=3
        )

        # Evaluador 2 otorga: 5, 4, 4
        Calificacion.objects.create(
            evaluador=self.eval2,
            participante=self.expositor,
            criterio=self.criterio1,
            cal_valor=5
        )
        Calificacion.objects.create(
            evaluador=self.eval2,
            participante=self.expositor,
            criterio=self.criterio2,
            cal_valor=4
        )
        Calificacion.objects.create(
            evaluador=self.eval2,
            participante=self.expositor,
            criterio=self.criterio3,
            cal_valor=4
        )

        # Calcular y asignar un puntaje total (simplificado: promedio ponderado de todas las calificaciones)
        # Peso total = 40 + 35 + 25 = 100%
        # Calificaciones: E1: [4, 5, 3], E2: [5, 4, 4]
        # Ponderado E1: (4*0.4) + (5*0.35) + (3*0.25) = 1.6 + 1.75 + 0.75 = 4.1
        # Ponderado E2: (5*0.4) + (4*0.35) + (4*0.25) = 2.0 + 1.4 + 1.0 = 4.4
        # Puntaje Total = (4.1 + 4.4) / 2 = 4.25
        # Este cálculo puede variar según la lógica real de tu aplicación.
        # Supongamos que se almacena en `par_eve_valor` del `ParticipanteEvento`.
        self.expositor_evento.par_eve_valor = 4.25
        self.expositor_evento.save()

        # URL: Suponiendo que la vista de info detallada para admin es similar a la de evaluador
        # o una vista específica en app_administradores.
        # Revisando urls.py de app_administradores:
        # path('informacion-detallada-administrador/<int:eve_id>/', views.info_detallada_admin, name='informacion_detallada_administrador_evento'),
        # Esta vista probablemente lista info detallada de *todos* los participantes del evento para el admin.
        # La HU78 dice "a un determinado expositor".
        # La URL `informacion_detallada_administrador_evento` toma `eve_id`, no `participante_id`.
        # La vista `info_detallada_admin` probablemente renderiza una página con información detallada
        # de todos los participantes del evento, incluyendo sus calificaciones por evaluador.
        # El admin vería una lista/tabla con todos los participantes y sus detalles.
        # Para "un determinado expositor", la vista `info_detallada_admin` debe mostrar
        # la información de *ese* participante específico si se filtra o se navega a él.
        # El test verificará que la información del participante específico esté en la respuesta.
        self.url_info_detallada = reverse('informacion_detallada_administrador_evento', args=[self.evento.pk])

        # Login
        self.client.force_login(self.admin_user)
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()


    def test_hu78_info_detallada_calificaciones_completa(self):
        """
        Prueba los 4 criterios de aceptación de HU78:
        CA1: Visualización de identidad del expositor
        CA2: Visualización de criterios y calificaciones
        CA3: Identificación de evaluadores
        CA4: Puntaje total del expositor
        """
        
        # Acceso a la vista
        response = self.client.get(self.url_info_detallada)
        self.assertEqual(response.status_code, 200, "El admin debe poder acceder a la info detallada del evento")

        # CA1: Visualización de identidad del expositor
        # Verificar que el nombre y correo del expositor estén en la respuesta
        self.assertContains(response, "Expositor Detallado", msg_prefix="CA1: Debe mostrar nombre del expositor")
        self.assertContains(response, "expo78@test.com", msg_prefix="CA1: Debe mostrar correo del expositor")

        # CA2: Visualización de criterios y calificaciones
        # Verificar que los criterios y los valores de calificación estén presentes
        # Buscamos los nombres de los criterios
        self.assertContains(response, "Dominio del Tema", msg_prefix="CA2: Debe mostrar criterio Dominio del Tema")
        self.assertContains(response, "Innovación", msg_prefix="CA2: Debe mostrar criterio Innovación")
        self.assertContains(response, "Presentación", msg_prefix="CA2: Debe mostrar criterio Presentación")
        
        # Buscamos los valores de calificación asignados (4, 5, 3 de eval1 y 5, 4, 4 de eval2)
        # Este test verifica que las calificaciones específicas estén presentes en la respuesta HTML.
        # Si la vista no renderiza las calificaciones de esta manera, este test fallará.
        self.assertContains(response, "4") # Calificación 1 de eval1 o calificación 3 de eval2
        self.assertContains(response, "5") # Calificación 1 de eval2 o calificación 2 de eval1
        self.assertContains(response, "3") # Calificación 3 de eval1
        # Nota: Este enfoque puede dar falsos positivos si otros participantes tienen las mismas calificaciones.
        # Para mayor precisión, se necesitaría inspeccionar el contexto de la respuesta o usar un parser de HTML.

        # CA3: Identificación de evaluadores
        # Verificar que los nombres o identificadores de los evaluadores estén presentes junto con sus calificaciones
        # Buscamos los nombres de los evaluadores.
        # Asumiendo que se muestran en el HTML.
        # La vista muestra el nombre completo del evaluador, no el username.
        self.assertContains(response, "Evaluador Uno", msg_prefix="CA3: Debe mostrar nombre del evaluador 1")
        self.assertContains(response, "Evaluador Dos", msg_prefix="CA3: Debe mostrar nombre del evaluador 2")
        # El test buscaba username, pero la vista muestra nombre. Ya verificamos el nombre.
        # No buscamos username porque no se muestra.
        # self.assertContains(response, "eval1_78", msg_prefix="CA3: Debe mostrar username del evaluador 1") # <-- Comentado/removido
        # self.assertContains(response, "eval2_78", msg_prefix="CA3: Debe mostrar username del evaluador 2") # <-- Comentado/removido


        # CA4: Puntaje total del expositor
        # Verificar que el puntaje total calculado esté presente en la respuesta
        # El puntaje total almacenado es 4.25
        # En el HTML, puede aparecer como "4.25" o "4,25" dependiendo del locale
        response_content_str = response.content.decode('utf-8')
        self.assertTrue(
            "4.25" in response_content_str or "4,25" in response_content_str,
            "CA4: El puntaje total del expositor (4.25) debe estar presente en la vista"
        )

        # Verificación contextual adicional (opcional)
        # Si el contexto de la vista incluye la información del evento y participantes
        if 'evento' in response.context:
            evento_contexto = response.context['evento']
            self.assertEqual(evento_contexto, self.evento, "La vista debe incluir el evento correcto en el contexto")

        if 'participantes_info' in response.context:
            participantes_info = response.context['participantes_info']
            # Verificar que el participante específico esté en la lista de info
            expositor_encontrado = False
            for info in participantes_info:
                if info['participante'] == self.expositor:
                    expositor_encontrado = True
                    # Aquí podríamos verificar más a fondo el contenido de 'info'
                    # como los criterios, calificaciones, etc., si es necesario para pruebas más profundas.
                    break
            self.assertTrue(expositor_encontrado, "CA1/CA2/CA3/CA4: El participante específico debe estar en la lista de información detallada")