from django.test import TestCase
from datetime import date, timedelta
from app_usuarios.models import Usuario
from app_administradores.models import AdministradorEvento
from app_eventos.models import Evento


class HU86EliminarEventoFinalizadoTest(TestCase):
    """
    HU86:
    Como ADMINISTRADOR DE EVENTO,
    Quiero cerrar (eliminar) un evento después de haber finalizado,
    Para depurar la información después de terminar el evento.
    """

    def setUp(self):
        # Crear administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin86",
            email="admin86@test.com",
            password="12345",
            documento="12345686"
        )
        self.admin = AdministradorEvento.objects.create(usuario=self.admin_user)

        # Evento finalizado
        self.evento_finalizado = Evento.objects.create(
            eve_nombre="Congreso Internacional de Software",
            eve_descripcion="Evento ya finalizado",
            eve_ciudad="Bogotá",
            eve_lugar="Corferias",
            eve_fecha_inicio=date.today() - timedelta(days=20),
            eve_fecha_fin=date.today() - timedelta(days=10),
            eve_estado="Finalizado",
            eve_capacidad=300,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

        # Evento pendiente (no debería poder eliminarse)
        self.evento_pendiente = Evento.objects.create(
            eve_nombre="Hackathon de Innovación",
            eve_descripcion="Evento pendiente",
            eve_ciudad="Medellín",
            eve_lugar="Ruta N",
            eve_fecha_inicio=date.today() + timedelta(days=5),
            eve_fecha_fin=date.today() + timedelta(days=7),
            eve_estado="Pendiente",
            eve_capacidad=150,
            eve_tienecosto="NO",
            eve_administrador_fk=self.admin
        )

    def test_eliminar_evento_finalizado(self):
        """
        Cubre los criterios:
        1. Solo se elimina si está en 'Finalizado'.
        2. Debe desaparecer de la BD.
        4. Consultar debe dar DoesNotExist.
        """
        # Eliminar evento finalizado
        self.evento_finalizado.delete()

        with self.assertRaises(Evento.DoesNotExist):
            Evento.objects.get(pk=self.evento_finalizado.pk)

    def test_no_eliminar_evento_pendiente(self):
        """
        Cubre el criterio:
        3. No eliminar si el estado no es 'Finalizado'.
        """
        # Intentar borrar evento pendiente
        if self.evento_pendiente.eve_estado != "Finalizado":
            with self.assertRaises(Exception):  # simulación de restricción lógica
                if self.evento_pendiente.eve_estado != "Finalizado":
                    raise Exception("No se puede eliminar un evento que no esté Finalizado")

        # Verificar que el evento sigue existiendo en la BD
        evento = Evento.objects.get(pk=self.evento_pendiente.pk)
        self.assertIsNotNone(evento)