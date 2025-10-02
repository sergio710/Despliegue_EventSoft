# app_evaluadores/tests/test_HU32_cancelar.py

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from app_usuarios.models import Usuario, Rol, RolUsuario
from app_administradores.models import AdministradorEvento
from app_eventos.models import Evento
from app_evaluadores.models import Evaluador, EvaluadorEvento 

class PruebasCancelarPreinscripcionEvaluador(TestCase):

    def setUp(self):
        """Configuración base para la cancelación de preinscripción (HU32)."""
        self.client = Client()
        self.ROL_NAME = 'evaluador'
        
        # 1. Configuración de Modelos Base
        self.admin_user = Usuario.objects.create_user(username='admin_test', email='admin@test.com', password='password123', documento='999')
        self.administrador_evento = AdministradorEvento.objects.create(usuario=self.admin_user)
        self.rol_evaluador = Rol.objects.create(nombre=self.ROL_NAME, descripcion='Rol para evaluadores')
        
        # 2. Evento A (Target de la cancelación)
        self.evento_a = Evento.objects.create(
            eve_nombre="Evento A - Cancelar", eve_estado="Aprobado", eve_capacidad=100, eve_tienecosto="No",
            eve_fecha_inicio=timezone.now().date(), eve_fecha_fin=timezone.now().date() + timedelta(days=2),
            eve_administrador_fk=self.administrador_evento,
        )
        self.url_cancelar_a = reverse('cancelar_inscripcion_evaluador', args=[self.evento_a.pk])
        
        # 3. Datos POST (Vacío ya que es solo una confirmación)
        self.post_data = {} 
        
        # URL de redirección esperada si el usuario es eliminado
        self.url_login = reverse('login')
        # URL de redirección esperada si el usuario persiste
        self.url_dashboard = reverse('dashboard_evaluador')

    def crear_evaluador_con_inscripcion(self, email, documento, estado_a, evento):
        """Función auxiliar para crear un evaluador y su inscripción."""
        user = Usuario.objects.create_user(
            username=email.split('@')[0], email=email, password='password123', 
            documento=documento, first_name='Eva', last_name='Test'
        )
        RolUsuario.objects.create(usuario=user, rol=self.rol_evaluador)
        evaluador_profile = Evaluador.objects.create(usuario=user)
        
        inscripcion = EvaluadorEvento.objects.create(
            evaluador=evaluador_profile,
            evento=evento,
            eva_eve_estado=estado_a,
            confirmado=True,
            # 💡 CORRECCIÓN: Agregar la fecha y hora de inscripción, que es NOT NULL
            eva_eve_fecha_hora=timezone.now() 
        )
        return user, evaluador_profile, inscripcion

    # ====================================================================
    # ✅ CP32.1: Cancelación y Eliminación Total (Caso Límite)
    # ====================================================================

    def test_cancelacion_exitosa_y_eliminacion_total_de_usuario(self):
        """Prueba CA32.1, CA32.3, CA32.4: Cancelación de única preinscripción en Pendiente."""
        # Arrange: Un evaluador con SOLO 1 inscripción (Evento A)
        user, evaluador, inscripcion_a = self.crear_evaluador_con_inscripcion(
            'eva_unica@test.com', '100', 'Pendiente', self.evento_a
        )
        self.client.login(email='eva_unica@test.com', password='password123')

        # Act: Intenta cancelar
        # La vista espera un POST, el cual dispara la eliminación
        response = self.client.post(self.url_cancelar_a, self.post_data, follow=True)

        # Assert 1: Verificación de la Redirección y Mensaje
        self.assertRedirects(response, self.url_login)
        self.assertContains(response, "Se canceló tu inscripción y se eliminó el usuario")
        
        # Assert 2: Verificación de la Eliminación
        # EvaluadorEvento debe ser 0 para este evento y usuario
        self.assertEqual(EvaluadorEvento.objects.filter(evaluador=evaluador, evento=self.evento_a).count(), 0)
        # Perfil Evaluador debe ser eliminado
        self.assertFalse(Evaluador.objects.filter(pk=evaluador.pk).exists())
        # Usuario debe ser eliminado (no existe)
        self.assertFalse(Usuario.objects.filter(pk=user.pk).exists())


    # ====================================================================
    # ✅ CP32.2: Cancelación exitosa sin eliminación de usuario (Caso Positivo)
    # ====================================================================

    def test_cancelacion_exitosa_persistencia_de_usuario(self):
        """Prueba CA32.1, CA32.3, CA32.5: Cancelación de una inscripción, persistencia de usuario."""
        
        # Arrange 1: Evento B adicional
        evento_b = Evento.objects.create(
            eve_nombre="Evento B - Persiste", eve_estado="Aprobado", eve_capacidad=100, eve_tienecosto="No",
            eve_fecha_inicio=timezone.now().date(), eve_fecha_fin=timezone.now().date() + timedelta(days=2),
            eve_administrador_fk=self.administrador_evento,
        )
        
        # Arrange 2: Evaluador con 2 inscripciones (A='Pendiente', B='Aprobado')
        # Usamos la función auxiliar corregida para la inscripción A
        user, evaluador, inscripcion_a = self.crear_evaluador_con_inscripcion(
            'eva_doble@test.com', '200', 'Pendiente', self.evento_a
        )
        
        # Segunda inscripción (mantiene el usuario)
        inscripcion_b = EvaluadorEvento.objects.create(
            evaluador=evaluador, 
            evento=evento_b, 
            eva_eve_estado='Aprobado', 
            confirmado=True,
            # 💡 CORRECCIÓN APLICADA AQUÍ: Se añade el campo requerido
            eva_eve_fecha_hora=timezone.now() 
        )
        
        self.client.login(email='eva_doble@test.com', password='password123')
        
        # Act: Intenta cancelar Evento A (Pendiente)
        response = self.client.post(self.url_cancelar_a, self.post_data, follow=True)

        # Assert 1: Verificación de la Redirección y Mensaje
        self.assertRedirects(response, self.url_dashboard)
        self.assertContains(response, "Inscripción cancelada con éxito.")
        
        # Assert 2: Verificación de la Eliminación y Persistencia
        # Inscripción A eliminada
        self.assertFalse(EvaluadorEvento.objects.filter(pk=inscripcion_a.pk).exists())
        # Inscripción B persiste
        self.assertTrue(EvaluadorEvento.objects.filter(pk=inscripcion_b.pk).exists())
        # Perfil Evaluador persiste
        self.assertTrue(Evaluador.objects.filter(pk=evaluador.pk).exists())
        # Usuario persiste
        self.assertTrue(Usuario.objects.filter(pk=user.pk).exists())