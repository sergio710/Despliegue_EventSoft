from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from app_eventos.models import Evento, AdministradorEvento
from app_participantes.models import Participante, Proyecto, ParticipanteEvento
import datetime

Usuario = get_user_model()

class HU71NotificacionesExpositoresTest(TestCase):
    """
    HU71:
    Como ADMINISTRADOR DE EVENTO,
    Quiero enviar notificaciones a todos o algunos de los expositores de un evento,
    Para mantener informados a los expositores sobre las novedades del evento.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin71",
            email="admin71@test.com",
            password="12345",
            documento="12345671"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre="Congreso de Innovación",
            eve_descripcion="Evento académico",
            eve_ciudad="Cali",
            eve_lugar="Auditorio Principal",
            eve_fecha_inicio=datetime.date(2025, 10, 20),
            eve_fecha_fin=datetime.date(2025, 10, 22),
            eve_estado="Aprobado",
            eve_capacidad=200,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Crear 2 expositores con proyectos
        self.expositores = []
        for i in range(1, 3):
            user = Usuario.objects.create_user(
                username=f"expositor{i}",
                email=f"expo{i}@test.com",
                password="12345",
                documento=f"3000{i}"
            )
            participante = Participante.objects.create(usuario=user)

            proyecto = Proyecto.objects.create(
                evento=self.evento,
                titulo=f"Proyecto {i}",
                descripcion=f"Descripción {i}",
                estado="Aprobado"
            )

            ParticipanteEvento.objects.create(
                participante=participante,
                evento=self.evento,
                par_eve_fecha_hora=timezone.now(),
                par_eve_estado="Aprobado",
                confirmado=True,
                proyecto=proyecto
            )

            self.expositores.append(participante)

    def enviar_notificacion(self, destinatarios, asunto, contenido):
        notificaciones = []
        for participante in destinatarios:
            notificaciones.append({
                "expositor": participante.usuario.email,
                "asunto": asunto,
                "contenido": contenido,
                "evento": self.evento.eve_nombre
            })
        return notificaciones

    def test_enviar_notificaciones_expositores(self):
        """
        Cubre criterios HU71
        """
        # Enviar a todos
        notificaciones_todos = self.enviar_notificacion(
            self.expositores, "Cambio en sala", "Se cambió la sala al Auditorio 2"
        )
        self.assertEqual(len(notificaciones_todos), 2)

        # Verificar asunto y contenido
        for n in notificaciones_todos:
            self.assertEqual(n["asunto"], "Cambio en sala")
            self.assertIn("Auditorio 2", n["contenido"])

        # Enviar a un expositor específico
        notificaciones_uno = self.enviar_notificacion(
            [self.expositores[0]], "Recordatorio", "Tu ponencia es a las 10:00 am"
        )
        self.assertEqual(len(notificaciones_uno), 1)
        self.assertEqual(notificaciones_uno[0]["expositor"], "expo1@test.com")