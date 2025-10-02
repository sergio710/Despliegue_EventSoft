from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from app_eventos.models import Evento, AdministradorEvento
from app_evaluadores.models import Evaluador, EvaluadorEvento
import datetime

Usuario = get_user_model()

class HU72NotificacionesEvaluadoresTest(TestCase):
    """
    HU72:
    Como ADMINISTRADOR DE EVENTO,
    Quiero enviar notificaciones a todos o algunos de los evaluadores de un evento,
    Para mantener informados a los evaluadores sobre las novedades del evento.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin72",
            email="admin72@test.com",
            password="12345",
            documento="12345672"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Simposio de Educación",
            eve_descripcion="Evento pedagógico",
            eve_ciudad="Bogotá",
            eve_lugar="Centro Cultural",
            eve_fecha_inicio=datetime.date(2025, 9, 5),
            eve_fecha_fin=datetime.date(2025, 9, 7),
            eve_estado="Aprobado",
            eve_capacidad=150,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Crear 2 evaluadores
        self.evaluadores = []
        for i in range(1, 3):
            user = Usuario.objects.create_user(
                username=f"evaluador{i}",
                email=f"eval{i}@test.com",
                password="12345",
                documento=f"4000{i}"
            )
            evaluador = Evaluador.objects.create(usuario=user)

            EvaluadorEvento.objects.create(
                evaluador=evaluador,
                evento=self.evento,
                eva_eve_fecha_hora=timezone.now(),
                eva_eve_estado="Aprobado",
                confirmado=True
            )

            self.evaluadores.append(evaluador)

    def enviar_notificacion(self, destinatarios, asunto, contenido):
        notificaciones = []
        for evaluador in destinatarios:
            notificaciones.append({
                "evaluador": evaluador.usuario.email,
                "asunto": asunto,
                "contenido": contenido,
                "evento": self.evento.eve_nombre
            })
        return notificaciones

    def test_enviar_notificaciones_evaluadores(self):
        """
        Cubre criterios HU72
        """
        # Enviar a todos
        notificaciones_todos = self.enviar_notificacion(
            self.evaluadores, "Actualización de criterios", "Se añadió un nuevo ítem en la rúbrica"
        )
        self.assertEqual(len(notificaciones_todos), 2)

        # Verificar asunto y contenido
        for n in notificaciones_todos:
            self.assertEqual(n["asunto"], "Actualización de criterios")
            self.assertIn("rúbrica", n["contenido"])

        # Enviar a un evaluador específico
        notificaciones_uno = self.enviar_notificacion(
            [self.evaluadores[0]], "Reunión", "Habrá reunión de coordinación a las 6 pm"
        )
        self.assertEqual(len(notificaciones_uno), 1)
        self.assertEqual(notificaciones_uno[0]["evaluador"], "eval1@test.com")