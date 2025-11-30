from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
from unittest.mock import patch, MagicMock
from app_eventos.models import Evento, EventoCategoria
from app_areas.models import Area, Categoria
from app_administradores.models import (
    AdministradorEvento, CodigoInvitacionAdminEvento, CodigoInvitacionEvento
)
from app_evaluadores.models import Evaluador, EvaluadorEvento, Criterio, Calificacion
from app_participantes.models import Participante, ParticipanteEvento
from app_asistentes.models import Asistente, AsistenteEvento
from app_usuarios.models import Rol, RolUsuario, Usuario

Usuario = get_user_model()


class DashboardAdminEventoTestCase(TestCase):
    """
    Tests para la vista dashboard_adminevento
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear rol
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        
        # Crear usuario administrador
        self.admin_user = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.administrador = AdministradorEvento.objects.create(usuario=self.admin_user)
        
        # Login
        self.client.login(email='admin1@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
    
    def test_dashboard_get(self):
        """Test: acceso al dashboard"""
        url = reverse('dashboard_adminevento')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app_administradores/dashboard_adminevento.html')


class CrearEventoTestCase(TestCase):
    """
    Tests para la vista crear_evento
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear roles
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.rol_superadmin = Rol.objects.create(nombre='superadmin')
        
        # Crear usuario administrador
        self.admin_user = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.administrador = AdministradorEvento.objects.create(usuario=self.admin_user)
        
        # Crear superadmin para emails
        self.superadmin = Usuario.objects.create_user(
            username='super',
            email='super@test.com',
            password='test123',
            documento='234567'
        )
        RolUsuario.objects.create(usuario=self.superadmin, rol=self.rol_superadmin)
        
        # Crear código de invitación válido
        self.codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='codigo123',
            email_destino='admin1@test.com',
            limite_eventos=5,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            usuario_asignado=self.admin_user
        )
        
        # Crear área y categoría
        self.area = Area.objects.create(
            are_nombre='Tecnología',
            are_descripcion='Área de tecnología'
        )
        self.categoria = Categoria.objects.create(
            cat_nombre='Conferencia',
            cat_descripcion='Categoría de conferencias',
            cat_area_fk=self.area
        )
        
        # Login
        self.client.login(email='admin1@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
        
        self.url = reverse('crear_evento')
    
    def test_get_crear_evento(self):
        """Test GET: cargar formulario"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('areas', response.context)
        self.assertFalse(response.context['mostrar_mensajes_en_formulario'])
    
    @patch('app_administradores.views.EmailMessage')
    def test_post_crear_evento_exitoso(self, mock_email):
        """Test POST: crear evento exitosamente"""
        fecha_inicio = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        fecha_fin = (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        response = self.client.post(self.url, {
            'nombre': 'Evento Test',
            'descripcion': 'Descripción del evento',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Evento.objects.filter(eve_nombre='Evento Test').exists())
        
        # Verificar que se descontó el cupo
        self.codigo.refresh_from_db()
        self.assertEqual(self.codigo.limite_eventos, 4)
        
        # Verificar que se envió email
        self.assertTrue(mock_email.called)
    
    def test_post_crear_evento_sin_administrador(self):
        """Test POST: usuario sin AdministradorEvento asociado"""
        # Crear usuario sin administrador
        usuario_sin_admin = Usuario.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='test123',
            documento='345678'
        )
        RolUsuario.objects.create(usuario=usuario_sin_admin, rol=self.rol_admin)
        
        self.client.login(email='user1@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
        
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Evento.objects.filter(eve_nombre='Evento').exists())
    
    def test_post_crear_evento_sin_codigo_invitacion(self):
        """Test POST: sin código de invitación"""
        # Crear admin sin código
        usuario = Usuario.objects.create_user(
            username='admin2',
            email='admin2@test.com',
            password='test123',
            documento='345678'
        )
        RolUsuario.objects.create(usuario=usuario, rol=self.rol_admin)
        AdministradorEvento.objects.create(usuario=usuario)
        
        self.client.login(email='admin2@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
        
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Evento.objects.exists())
    
    def test_post_crear_evento_tiempo_limite_expirado(self):
        """Test POST: tiempo límite de creación expirado"""
        self.codigo.tiempo_limite_creacion = timezone.now() - timedelta(days=1)
        self.codigo.save()
        
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Evento.objects.exists())
    
    def test_post_crear_evento_sin_cupos(self):
        """Test POST: sin cupos disponibles"""
        self.codigo.limite_eventos = 0
        self.codigo.save()
        
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Evento.objects.exists())
    
    def test_post_crear_evento_fecha_fin_antes_inicio(self):
        """Test POST: fecha fin anterior a fecha inicio"""
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-10',
            'fecha_fin': '2025-12-05',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Evento.objects.exists())
    
    def test_post_crear_evento_fecha_invalida(self):
        """Test POST: formato de fecha inválido"""
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': 'fecha-invalida',
            'fecha_fin': '2025-12-02',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Evento.objects.exists())
    
    def test_post_crear_evento_capacidad_cero(self):
        """Test POST: capacidad cero"""
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': '0',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Evento.objects.exists())
    
    def test_post_crear_evento_capacidad_invalida(self):
        """Test POST: capacidad no numérica"""
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': 'abc',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Evento.objects.exists())
    
    def test_post_crear_evento_sin_categorias(self):
        """Test POST: sin categorías seleccionadas"""
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': []
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Evento.objects.exists())
    
    @patch('app_administradores.views.EmailMessage')
    def test_post_crear_evento_con_archivos(self, mock_email):
        """Test POST: crear evento con imagen y programación"""
        imagen = SimpleUploadedFile(
            "test.jpg",
            b"contenido de imagen",
            content_type="image/jpeg"
        )
        programacion = SimpleUploadedFile(
            "programa.pdf",
            b"contenido pdf",
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'nombre': 'Evento con archivos',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo],
            'imagen': imagen,
            'programacion': programacion
        })
        
        self.assertEqual(response.status_code, 302)
        evento = Evento.objects.get(eve_nombre='Evento con archivos')
        self.assertTrue(evento.eve_imagen)
        self.assertTrue(evento.eve_programacion)
    
    def test_post_crear_evento_categoria_inexistente(self):
        """Test POST: categoría que no existe se ignora"""
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo, 9999]  # 9999 no existe
        })
        
        self.assertEqual(response.status_code, 302)
        # El evento se crea con la categoría válida


class ObtenerCategoriasPorAreaTestCase(TestCase):
    """
    Tests para la vista obtener_categorias_por_area
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear rol y usuario
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.admin_user = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        AdministradorEvento.objects.create(usuario=self.admin_user)
        
        # Login
        self.client.login(email='admin1@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
        
        # Crear área y categorías
        self.area = Area.objects.create(
            are_nombre='Tecnología',
            are_descripcion='Desc'
        )
        self.cat1 = Categoria.objects.create(
            cat_nombre='Cat1',
            cat_descripcion='Desc1',
            cat_area_fk=self.area
        )
        self.cat2 = Categoria.objects.create(
            cat_nombre='Cat2',
            cat_descripcion='Desc2',
            cat_area_fk=self.area
        )
    
    def test_obtener_categorias_por_area(self):
        """Test: obtener categorías de un área"""
        url = reverse('obtener_categorias_por_area', args=[self.area.are_codigo])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['cat_nombre'], 'Cat1')


class ListarEventosTestCase(TestCase):
    """
    Tests para la vista listar_eventos
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear rol y usuario
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.admin_user = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.administrador = AdministradorEvento.objects.create(usuario=self.admin_user)
        
        # Login
        self.client.login(email='admin1@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
    
    def test_listar_eventos_vacio(self):
        """Test: listar sin eventos"""
        url = reverse('listar_eventos')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['eventos']), 0)
    
    def test_listar_eventos_con_datos(self):
        """Test: listar eventos del administrador"""
        # Crear eventos
        for i in range(3):
            Evento.objects.create(
                eve_nombre=f'Evento {i}',
                eve_descripcion='Desc',
                eve_ciudad='Manizales',
                eve_lugar='SENA',
                eve_fecha_inicio=timezone.now().date(),
                eve_fecha_fin=timezone.now().date() + timedelta(days=1),
                eve_estado='pendiente',
                eve_capacidad=100,
                eve_tienecosto='NO',
                eve_administrador_fk=self.administrador
            )
        
        url = reverse('listar_eventos')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['eventos']), 3)


class ModificarEventoTestCase(TestCase):
    """
    Tests para la vista modificar_evento
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear rol y usuario
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.admin_user = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.administrador = AdministradorEvento.objects.create(usuario=self.admin_user)
        
        # Crear área y categoría
        self.area = Area.objects.create(are_nombre='Tech', are_descripcion='Desc')
        self.categoria = Categoria.objects.create(
            cat_nombre='Conf',
            cat_descripcion='Desc',
            cat_area_fk=self.area
        )
        
        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre='Evento Original',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='pendiente',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador
        )
        EventoCategoria.objects.create(evento=self.evento, categoria=self.categoria)
        
        # Login
        self.client.login(email='admin1@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
        
        self.url = reverse('modificar_evento', args=[self.evento.eve_id])
    
    def test_get_modificar_evento(self):
        """Test GET: cargar formulario de modificación"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['evento'].eve_nombre, 'Evento Original')
        self.assertIn('todas_areas', response.context)
        self.assertIn('categorias_info', response.context)
    
    def test_post_modificar_evento_exitoso(self):
        """Test POST: modificar evento correctamente"""
        response = self.client.post(self.url, {
            'nombre': 'Evento Modificado',
            'descripcion': 'Nueva descripción',
            'ciudad': 'Bogotá',
            'lugar': 'Centro',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': '150',
            'tienecosto': 'SI',
            'categoria_id[]': [self.categoria.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 302)
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.eve_nombre, 'Evento Modificado')
        self.assertEqual(self.evento.eve_ciudad, 'Bogotá')
    
    def test_post_modificar_evento_fecha_fin_antes_inicio(self):
        """Test POST: fecha fin anterior a inicio"""
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-10',
            'fecha_fin': '2025-12-05',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 200)
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.eve_nombre, 'Evento Original')  # No cambió
    
    def test_post_modificar_evento_con_archivos(self):
        """Test POST: actualizar archivos"""
        imagen = SimpleUploadedFile("new.jpg", b"img", content_type="image/jpeg")
        programacion = SimpleUploadedFile("new.pdf", b"pdf", content_type="application/pdf")
        
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [self.categoria.cat_codigo],
            'imagen': imagen,
            'programacion': programacion
        })
        
        self.assertEqual(response.status_code, 302)
        self.evento.refresh_from_db()
        self.assertTrue(self.evento.eve_imagen)
        self.assertTrue(self.evento.eve_programacion)
    
    def test_post_modificar_evento_actualizar_categorias(self):
        """Test POST: actualizar categorías"""
        nueva_cat = Categoria.objects.create(
            cat_nombre='Nueva',
            cat_descripcion='Desc',
            cat_area_fk=self.area
        )
        
        response = self.client.post(self.url, {
            'nombre': 'Evento',
            'descripcion': 'Desc',
            'ciudad': 'Manizales',
            'lugar': 'SENA',
            'fecha_inicio': '2025-12-01',
            'fecha_fin': '2025-12-02',
            'capacidad': '100',
            'tienecosto': 'NO',
            'categoria_id[]': [nueva_cat.cat_codigo]
        })
        
        self.assertEqual(response.status_code, 302)
        # Verificar que se eliminó la categoría anterior y se agregó la nueva
        self.assertFalse(EventoCategoria.objects.filter(
            evento=self.evento,
            categoria=self.categoria
        ).exists())
        self.assertTrue(EventoCategoria.objects.filter(
            evento=self.evento,
            categoria=nueva_cat
        ).exists())


class EliminarEventoTestCase(TestCase):
    """
    Tests para la vista eliminar_evento
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear roles
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.rol_asistente = Rol.objects.create(nombre='asistente')
        
        # Crear usuario administrador
        self.admin_user = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.administrador = AdministradorEvento.objects.create(usuario=self.admin_user)
        
        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre='Evento Test',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='pendiente',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador
        )
        
        # Login
        self.client.login(email='admin1@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
        
        self.url = reverse('eliminar_evento', args=[self.evento.eve_id])
    
    def test_get_eliminar_evento_con_otros_eventos(self):
        """Test GET: mostrar confirmación con otros eventos"""
        # Crear segundo evento
        Evento.objects.create(
            eve_nombre='Evento 2',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='pendiente',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['advertencia_eliminacion_usuario'])
        self.assertTrue(response.context['otros_eventos'])
    
    def test_get_eliminar_evento_sin_otros_eventos_con_codigos(self):
        """Test GET: sin otros eventos pero con códigos válidos"""
        CodigoInvitacionAdminEvento.objects.create(
            codigo='codigo123',
            email_destino='admin1@test.com',
            limite_eventos=3,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            usuario_asignado=self.admin_user
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['advertencia_eliminacion_usuario'])
    
    def test_get_eliminar_evento_sin_otros_eventos_sin_codigos(self):
        """Test GET: sin otros eventos y sin códigos - se eliminará usuario"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['advertencia_eliminacion_usuario'])
    
    def test_post_eliminar_evento_confirmado(self):
        """Test POST: eliminar evento confirmado"""
        # Crear segundo evento para que no se elimine el usuario
        Evento.objects.create(
            eve_nombre='Evento 2',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='pendiente',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador
        )
        
        response = self.client.post(self.url, {
            'confirmacion_eliminacion': 'confirmar'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Evento.objects.filter(eve_id=self.evento.eve_id).exists())
    
    def test_post_eliminar_evento_sin_confirmacion(self):
        """Test POST: no confirmar eliminación"""
        response = self.client.post(self.url, {
            'confirmacion_eliminacion': 'no'
        })
        
        # El evento no se elimina
        self.assertTrue(Evento.objects.filter(eve_id=self.evento.eve_id).exists())
    
    def test_eliminar_evento_no_propio(self):
        """Test: intentar eliminar evento de otro administrador"""
        # Crear otro administrador y evento
        otro_admin_user = Usuario.objects.create_user(
            username='admin2',
            email='admin2@test.com',
            password='test123',
            documento='234567'
        )
        RolUsuario.objects.create(usuario=otro_admin_user, rol=self.rol_admin)
        otro_admin = AdministradorEvento.objects.create(usuario=otro_admin_user)
        
        evento_ajeno = Evento.objects.create(
            eve_nombre='Evento Ajeno',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='pendiente',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=otro_admin
        )
        
        url = reverse('eliminar_evento', args=[evento_ajeno.eve_id])
        response = self.client.post(url, {'confirmacion_eliminacion': 'confirmar'})
        
        # Debe redirigir sin eliminar
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Evento.objects.filter(eve_id=evento_ajeno.eve_id).exists())


class CerrarReabrirInscripcionesTestCase(TestCase):
    """
    Tests para cerrar_inscripciones y reabrir_inscripciones
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear rol y usuario
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.admin_user = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.administrador = AdministradorEvento.objects.create(usuario=self.admin_user)
        
        # Login
        self.client.login(email='admin1@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
    
    def test_cerrar_inscripciones_evento_aprobado(self):
        """Test: cerrar inscripciones de evento aprobado"""
        evento = Evento.objects.create(
            eve_nombre='Evento',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='aprobado',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador
        )
        
        url = reverse('cerrar_inscripcion_evento', args=[evento.eve_id])
        response = self.client.get(url)
        
        evento.refresh_from_db()
        self.assertEqual(evento.eve_estado, 'Inscripciones Cerradas')
        self.assertRedirects(response, reverse('listar_eventos'))
    
    def test_cerrar_inscripciones_evento_no_aprobado(self):
        """Test: intentar cerrar inscripciones de evento no aprobado"""
        evento = Evento.objects.create(
            eve_nombre='Evento',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='pendiente',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador
        )
        
        url = reverse('cerrar_inscripcion_evento', args=[evento.eve_id])
        response = self.client.get(url)
        
        evento.refresh_from_db()
        self.assertEqual(evento.eve_estado, 'pendiente')  # No cambió
    
    def test_reabrir_inscripciones_evento_cerrado(self):
        """Test: reabrir inscripciones"""
        evento = Evento.objects.create(
            eve_nombre='Evento',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='inscripciones cerradas',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador
        )
        
        url = reverse('reabrir_inscripcion_evento', args=[evento.eve_id])
        response = self.client.get(url)
        
        evento.refresh_from_db()
        self.assertEqual(evento.eve_estado, 'Aprobado')
    
    def test_reabrir_inscripciones_evento_no_cerrado(self):
        """Test: intentar reabrir inscripciones de evento no cerrado"""
        evento = Evento.objects.create(
            eve_nombre='Evento',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='pendiente',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador
        )
        
        url = reverse('reabrir_inscripcion_evento', args=[evento.eve_id])
        response = self.client.get(url)
        
        evento.refresh_from_db()
        self.assertEqual(evento.eve_estado, 'pendiente')  # No cambió


class VerInscripcionesTestCase(TestCase):
    """
    Tests para ver_inscripciones
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear rol y usuario
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.admin_user = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.administrador = AdministradorEvento.objects.create(usuario=self.admin_user)
        
        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre='Evento',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='aprobado',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador
        )
        
        # Login
        self.client.login(email='admin1@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
    
    def test_ver_inscripciones(self):
        """Test: ver inscripciones de evento"""
        url = reverse('ver_inscripciones_evento', args=[self.evento.eve_id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['evento'], self.evento)


class GestionAsistentesTestCase(TestCase):
    """
    Tests para gestion_asistentes
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear roles
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.rol_asistente = Rol.objects.create(nombre='asistente')
        
        # Crear usuario administrador
        self.admin_user = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin)
        self.administrador = AdministradorEvento.objects.create(usuario=self.admin_user)
        
        # Crear evento
        self.evento = Evento.objects.create(
            eve_nombre='Evento',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='aprobado',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador
        )
        
        # Crear asistente confirmado
        usuario_asist = Usuario.objects.create_user(
            username='asist1',
            email='asist1@test.com',
            password='test123',
            documento='234567'
        )
        RolUsuario.objects.create(usuario=usuario_asist, rol=self.rol_asistente)
        asistente = Asistente.objects.create(usuario=usuario_asist)
        AsistenteEvento.objects.create(
            asistente=asistente,
            evento=self.evento,
            asi_eve_fecha_hora=timezone.now(),
            asi_eve_estado='Aprobado',
            confirmado=True
        )
        
        # Login
        self.client.login(email='admin1@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
    
    def test_gestion_asistentes(self):
        """Test: listar asistentes confirmadCopos"""
        url = reverse('ver_asistentes_evento', args=[self.evento.eve_id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['evento'], self.evento)
        self.assertEqual(len(response.context['asistentes']), 1)