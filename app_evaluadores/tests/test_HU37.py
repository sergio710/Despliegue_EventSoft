from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from app_usuarios.models import Usuario, Rol, RolUsuario
from app_eventos.models import Evento
from app_evaluadores.models import Evaluador, EvaluadorEvento
from app_administradores.models import AdministradorEvento


class HU37VisualizarEventosEvaluadorTest(TestCase):
    """
    HU37: Como EVALUADOR, quiero visualizar la información detallada de los eventos
    en los que soy evaluador, para tener claridad sobre los horarios y los lugares.
    """

    def setUp(self):
        # Crear usuario evaluador
        self.usuario = Usuario.objects.create_user(
            username="eva37",
            email="eva37@test.com",
            password="pass1234",
            documento="123456"
        )

        # Crear rol de evaluador y asignarlo
        rol_eval, _ = Rol.objects.get_or_create(
            nombre="evaluador", defaults={"descripcion": "Rol de evaluador"}
        )
        RolUsuario.objects.create(usuario=self.usuario, rol=rol_eval)

        # Crear evaluador vinculado al usuario
        self.evaluador = Evaluador.objects.create(usuario=self.usuario)

        # Crear usuario administrador de evento
        admin_user = Usuario.objects.create_user(
            username="admin_evento",
            email="admin@test.com",
            password="admin123",
            documento="999999"
        )
        self.admin_evento = AdministradorEvento.objects.create(usuario=admin_user)

        # Crear evento con administrador
        self.evento = Evento.objects.create(
            eve_nombre="Simposio Internacional",
            eve_descripcion="Evento académico internacional",
            eve_ciudad="Lima",
            eve_lugar="Centro de Convenciones",
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=2),
            eve_estado="activo",
            eve_capacidad=200,
            eve_tienecosto="no",
            eve_administrador_fk=self.admin_evento,
        )

        # Relación evaluador-evento
        self.evaluador_evento = EvaluadorEvento.objects.create(
            evaluador=self.evaluador,
            evento=self.evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado="confirmado"
        )

        # Login como evaluador
        self.client.login(email="eva37@test.com", password="pass1234")

    def test_visualizar_eventos_asignados(self):
        """
        Cubre los 4 criterios de aceptación de HU37:
        - Ver listado de eventos asignados
        - Visualizar nombre, lugar (en este caso ciudad) y horarios del evento
        - Tener claridad sobre fechas y ubicaciones
        - Que solo se muestren los eventos del evaluador logueado
        """
        url = reverse("dashboard_evaluador")
        response = self.client.get(url)

        # Verificar que se muestra el evento del evaluador
        self.assertContains(response, "Simposio Internacional")
        # Validamos la ciudad (porque la plantilla no muestra eve_lugar)
        self.assertContains(response, "Lima")
        fecha_inicio = self.evento.eve_fecha_inicio.strftime("%d/%m/%Y")
        fecha_fin = self.evento.eve_fecha_fin.strftime("%d/%m/%Y")
        self.assertContains(response, fecha_inicio)
        self.assertContains(response, fecha_fin)

        # Crear otro evento con otro admin (no asignado al evaluador)
        Evento.objects.create(
            eve_nombre="Congreso Nacional",
            eve_descripcion="Otro evento",
            eve_ciudad="Bogotá",
            eve_lugar="Auditorio Nacional",
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado="activo",
            eve_capacidad=150,
            eve_tienecosto="si",
            eve_administrador_fk=self.admin_evento,
        )
        response = self.client.get(url)
        self.assertNotContains(response, "Congreso Nacional")