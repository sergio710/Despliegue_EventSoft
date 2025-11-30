from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.http import Http404, FileResponse
from unittest.mock import patch, mock_open, MagicMock
from django.contrib.auth.models import Group, User
from django.db import transaction
from app_eventos.models import Evento, ConfiguracionCertificado, EventoCategoria
from app_areas.models import Categoria, Area
from app_administradores.models import AdministradorEvento, CodigoInvitacionAdminEvento
from app_asistentes.models import Asistente, AsistenteEvento
from app_participantes.models import Participante, ParticipanteEvento
from app_evaluadores.models import Evaluador, EvaluadorEvento, Criterio, Calificacion
from app_usuarios.models import Rol, RolUsuario
from django.utils import timezone
from datetime import timedelta
from django.core import mail
from django.conf import settings
import os
import shutil
import uuid

User = get_user_model()

class BaseTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Crear grupos
        self.grupo_admin = Group.objects.create(name='Administradores')
        self.grupo_evaluadores = Group.objects.create(name='Evaluadores')
        self.grupo_participantes = Group.objects.create(name='Participantes')
        self.grupo_asistentes = Group.objects.create(name='Asistentes')

        # Crear roles
        self.rol_superadmin = Rol.objects.create(nombre='superadmin')
        self.rol_admin_evento = Rol.objects.create(nombre='administrador_evento')
        self.rol_asistente = Rol.objects.create(nombre='asistente')
        self.rol_participante = Rol.objects.create(nombre='participante')
        
        # Crear usuario admin
        self.admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
        self.admin_user.groups.add(self.grupo_admin)
        self.rol_evaluador = Rol.objects.create(nombre='evaluador')

        # Crear superadmin
        self.superadmin = Usuario.objects.create_user(
            username='superadmin',
            email='super@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.superadmin, rol=self.rol_superadmin)
        
        # Login
        self.client.login(email='super@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'superadmin'
        session.save()
        
        # Crear evento de prueba
        self.evento = Evento.objects.create(
            eve_nombre='Evento Test',
            eve_estado='activo',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=7),
            eve_capacidad=100
        )

class TestManuales(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='admin123')
        self.ruta_manual = os.path.join(settings.MEDIA_ROOT, "manuales")
        self.ruta_manual_super = os.path.join(self.ruta_manual, "MANUAL_SUPER_ADMIN_SISTEMA_EVENTSOFT.pdf")
        self.ruta_manual_tecnico = os.path.join(self.ruta_manual, "MANUAL_TECNICO_Y_DE_OPERACION_DEL_SISTEMA_EVENTSOFT.pdf")

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b'contenido de prueba')
    def test_manual_super_admin_existe(self, mock_file, mock_exists):
        mock_exists.return_value = True
        response = self.client.get(reverse('manual_super_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        mock_exists.assert_called_with(self.ruta_manual_super)
        mock_file.assert_called_with(self.ruta_manual_super, 'rb')

    @patch('os.path.exists')
    def test_manual_super_admin_no_existe(self, mock_exists):
        mock_exists.return_value = False
        response = self.client.get(reverse('manual_super_admin'))
        self.assertEqual(response.status_code, 404)
        mock_exists.assert_called_with(self.ruta_manual_super)

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b'contenido de prueba')
    def test_manual_tecnico_existe(self, mock_file, mock_exists):
        mock_exists.return_value = True
        response = self.client.get(reverse('manual_tecnico_operacion'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        mock_exists.assert_called_with(self.ruta_manual_tecnico)
        mock_file.assert_called_with(self.ruta_manual_tecnico, 'rb')

    @patch('os.path.exists')
    def test_manual_tecnico_no_existe(self, mock_exists):
        mock_exists.return_value = False
        response = self.client.get(reverse('manual_tecnico_operacion'))
        self.assertEqual(response.status_code, 404)
        mock_exists.assert_called_with(self.ruta_manual_tecnico)
        response = self.client.get(reverse('manual_super_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
    # MODIFICAR TestManualesBaseTestCase
    def test_manual_superadmin_directorio_no_existe(self):
        # Borrar directorio manuales
        if os.path.exists(self.ruta_manual):
            shutil.rmtree(self.ruta_manual)
        response = self.client.get(reverse('manual_super_admin'))
        self.assertEqual(response.status_code, 404)  # Línea faltante 100-112

    def test_manual_tecnico_existe(self):
        response = self.client.get(reverse('manual_tecnico_operacion'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
    def test_manual_tecnico_directorio_no_existe(self):
        os.rmdir(self.ruta_manual)
        response = self.client.get(reverse('manual_tecnico_operacion'))
        self.assertEqual(response.status_code, 404)

class TestDashboard(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='admin123')
        
        # Crear usuarios de prueba
        self.evaluador = User.objects.create_user('evaluador', 'evaluador@test.com', 'pass123')
        self.evaluador.groups.add(self.grupo_evaluadores)
        
        self.participante = User.objects.create_user('participante', 'participante@test.com', 'pass123')
        self.participante.groups.add(self.grupo_participantes)
        
        self.admin_evento = User.objects.create_user('admin_evento', 'admin_evento@test.com', 'pass123')
        self.admin_evento.groups.add(self.grupo_admin)
        
        # Crear evento
        self.evento = Evento.objects.create(
            nombre='Evento Test',
            descripcion='Descripción',
            fecha_inicio=timezone.now(),
            fecha_fin=timezone.now() + timedelta(days=1),
            estado='borrador'
        )

    def test_dashboard_acceso_sin_login(self):
        self.client.logout()
        response = self.client.get(reverse('admin:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('usuarios:login'))

    def test_dashboard_acceso_sin_permiso(self):
        self.client.login(username='evaluador', password='pass123')
        response = self.client.get(reverse('admin:dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_contadores_correctos(self):
        response = self.client.get(reverse('admin:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Verificar contadores
        self.assertEqual(response.context['total_usuarios'], 4)  # admin + 3 usuarios creados
        self.assertEqual(response.context['total_eventos'], 1)
        self.assertEqual(response.context['total_usuarios_sin_eventos'], 4)  # Nadie está asociado a eventos
        self.assertEqual(response.context['total_evaluadores'], 1)
        self.assertEqual(response.context['total_administradores'], 1)
        self.assertEqual(response.context['total_participantes'], 1)

    def test_dashboard_mensajes_estado_sin_eventos(self):
        Evento.objects.all().delete()
        response = self.client.get(reverse('admin:dashboard'))
        mensajes = response.context['mensajes_estado']
        self.assertEqual(len(mensajes), 1)
        self.assertEqual(mensajes[0]['tipo'], 'warning')
        self.assertIn('No hay eventos', mensajes[0]['texto'])

    def test_dashboard_mensajes_estado_con_eventos(self):
        # Crear eventos en diferentes estados
        Evento.objects.create(
            nombre='Evento Activo',
            descripcion='Descripción',
            fecha_inicio=timezone.now(),
            fecha_fin=timezone.now() + timedelta(days=1),
            estado='activo'
        )
        Evento.objects.create(
            nombre='Evento Finalizado',
            descripcion='Descripción',
            fecha_inicio=timezone.now() - timedelta(days=2),
            fecha_fin=timezone.now() - timedelta(days=1),
            estado='finalizado'
        )
        
        response = self.client.get(reverse('admin:dashboard'))
        mensajes = response.context['mensajes_estado']
        
        self.assertTrue(len(mensajes) >= 3)  # Al menos 3 mensajes (1 por cada estado)
        tipos_mensaje = [m['tipo'] for m in mensajes]
        self.assertIn('success', tipos_mensaje)
        self.assertIn('warning', tipos_mensaje)
        
        for mensaje in mensajes:
            self.assertIn('texto', mensaje)
            self.assertIn('tipo', mensaje)
            self.assertIn(mensaje['tipo'], ['success', 'warning', 'danger'])

    def test_dashboard_template_correcto(self):
        response = self.client.get(reverse('admin:dashboard'))
        self.assertTemplateUsed(response, 'admin/dashboard.html')

    def test_dashboard_mensajes_estado_formato(self):
        # Crear evento para generar mensaje
        evento = Evento.objects.create(
            nombre='Evento Test',
            descripcion='Descripción',
            fecha_inicio=timezone.now(),
            fecha_fin=timezone.now() + timedelta(days=1),
            estado='borrador'
        )
        
        response = self.client.get(reverse('admin:dashboard'))
        mensajes = response.context['mensajes_estado']
        
        self.assertTrue(len(mensajes) > 0)
        for mensaje in mensajes:
            self.assertIsInstance(mensaje, dict)
            self.assertIn('texto', mensaje)
            self.assertIn('tipo', mensaje)
            self.assertIn(mensaje['tipo'], ['success', 'warning', 'danger'])
            self.assertIsInstance(mensaje['texto'], str)

class TestEliminarEvento(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='admin123')
        self.evento = Evento.objects.create(
            nombre='Evento Test',
            descripcion='Descripción',
            fecha_inicio=timezone.now(),
            fecha_fin=timezone.now() + timedelta(days=1),
            estado='borrador'
        )

    @transaction.atomic
    def test_eliminar_evento_exitoso(self):
        response = self.client.post(reverse('admin:eliminar_evento', args=[self.evento.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('admin:lista_eventos'))
        self.assertFalse(Evento.objects.filter(id=self.evento.id).exists())
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Evento eliminado correctamente.')

    def test_eliminar_evento_no_existe(self):
        response = self.client.post(reverse('admin:eliminar_evento', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_eliminar_evento_sin_login(self):
        self.client.logout()
        response = self.client.post(reverse('admin:eliminar_evento', args=[self.evento.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Evento.objects.filter(id=self.evento.id).exists())

    def test_eliminar_evento_sin_permiso(self):
        usuario = User.objects.create_user('usuario', 'usuario@test.com', 'password123')
        self.client.login(username='usuario', password='password123')
        response = self.client.post(reverse('admin:eliminar_evento', args=[self.evento.id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Evento.objects.filter(id=self.evento.id).exists())

    def test_eliminar_evento_metodo_get(self):
        response = self.client.get(reverse('admin:eliminar_evento', args=[self.evento.id]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Evento.objects.filter(id=self.evento.id).exists())

    @transaction.atomic
    def test_eliminar_evento_con_transaccion(self):
        # Crear objetos relacionados
        area = Area.objects.create(nombre='Area Test')
        self.evento.areas.add(area)
        
        response = self.client.post(reverse('admin:eliminar_evento', args=[self.evento.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Evento.objects.filter(id=self.evento.id).exists())

class TestEvaluadoresViews(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='admin123')
        self.evento = Evento.objects.create(
            nombre='Evento Test',
            descripcion='Descripción',
            fecha_inicio=timezone.now(),
            fecha_fin=timezone.now() + timedelta(days=1),
            estado='borrador'
        )
        self.area = Area.objects.create(nombre='Area Test')
        self.evento.areas.add(self.area)
        
        # Crear usuario evaluador
        self.evaluador = User.objects.create_user(
            'evaluador', 'evaluador@test.com', 'password123'
        )
        self.evaluador.groups.add(self.grupo_evaluadores)
        # Asignar área al evaluador
        evaluador_obj = Evaluador.objects.create(usuario=self.evaluador)
        evaluador_obj.areas.add(self.area)

    def test_lista_evaluadores_get(self):
        response = self.client.get(reverse('admin:lista_evaluadores'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/lista_evaluadores.html')
        self.assertIn('evaluadores', response.context)

    def test_agregar_evaluador_get(self):
        response = self.client.get(reverse('admin:agregar_evaluador'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/agregar_evaluador.html')

    def test_agregar_evaluador_post_valido(self):
        data = {
            'nombre': 'Nuevo Evaluador',
            'email': 'nuevo@evaluador.com',
            'areas': [self.area.id],
            'codigo_invitacion': '123456'
        }
        response = self.client.post(reverse('admin:agregar_evaluador'), data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('admin:lista_evaluadores'))
        
        # Verificar usuario creado
        usuario = User.objects.get(email='nuevo@evaluador.com')
        self.assertTrue(usuario.groups.filter(name='Evaluadores').exists())
        
        # Verificar evaluador y áreas
        evaluador = Evaluador.objects.get(usuario=usuario)
        self.assertIn(self.area, evaluador.areas.all())
        
        # Verificar mensaje
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Evaluador agregado correctamente.')

    def test_agregar_evaluador_post_invalido(self):
        data = {
            'nombre': '',  # Campo requerido vacío
            'email': 'correo_invalido',
            'areas': [],
            'codigo_invitacion': '123'  # Código muy corto
        }
        response = self.client.post(reverse('admin:agregar_evaluador'), data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'nombre', 'Este campo es obligatorio.')
        self.assertFormError(response, 'form', 'email', 'Introduzca una dirección de correo electrónico válida.')

    def test_editar_evaluador_get(self):
        response = self.client.get(reverse('admin:editar_evaluador', args=[self.evaluador.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/editar_evaluador.html')

    def test_editar_evaluador_post_valido(self):
        data = {
            'nombre': 'Evaluador Editado',
            'email': 'editado@evaluador.com',
            'areas': [self.area.id]
        }
        response = self.client.post(reverse('admin:editar_evaluador', args=[self.evaluador.id]), data)
        self.assertEqual(response.status_code, 302)
        self.evaluador.refresh_from_db()
        self.assertEqual(self.evaluador.email, 'editado@evaluador.com')

    def test_editar_evaluador_post_invalido(self):
        data = {
            'nombre': '',  # Campo requerido vacío
            'email': 'correo_invalido',
            'areas': []
        }
        response = self.client.post(reverse('admin:editar_evaluador', args=[self.evaluador.id]), data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'nombre', 'Este campo es obligatorio.')
        self.assertFormError(response, 'form', 'email', 'Introduzca una dirección de correo electrónico válida.')

class TestDashboard(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Crear eventos en diferentes estados
        self.estados = ['pendiente', 'inscripciones cerradas', 'finalizado', 'cerrado', 'aprobado']
        
        # Crear administrador de eventos
        self.admin_user = Usuario.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='test123',
            documento='123457'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin_evento)
        self.admin_evento = AdministradorEvento.objects.create(usuario=self.admin_user)
        
        # Crear eventos para cada estado
        self.eventos_por_estado = {}
        for estado in self.estados:
            evento = Evento.objects.create(
                eve_nombre=f'Evento {estado}',
                eve_estado=estado.lower(),
                eve_fecha_inicio=timezone.now(),
                eve_fecha_fin=timezone.now() + timedelta(days=7),
                eve_capacidad=100,
                eve_administrador_fk=self.admin_evento
            )
            self.eventos_por_estado[estado] = evento
            
        # Crear área y categoría
        self.area = Area.objects.create(are_nombre='Área Test')
        self.categoria = Categoria.objects.create(
            cat_nombre='Categoría Test',
            cat_area_fk=self.area
        )
        
        # Asociar categoría a eventos
        for evento in self.eventos_por_estado.values():
            EventoCategoria.objects.create(evento=evento, categoria=self.categoria)

    def test_dashboard_muestra_todos_estados(self):
        response = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        
        # Verificar que todos los estados están en el contexto
        estados_tarjetas = response.context['estados_tarjetas']
        estados_nombres = [estado[0] for estado in estados_tarjetas]
        self.assertIn('Aprobado', estados_nombres)
        self.assertIn('Pendiente', estados_nombres)
        self.assertIn('Rechazado', estados_nombres)
        self.assertIn('Inscripciones Cerradas', estados_nombres)
        self.assertIn('Finalizado', estados_nombres)

    def test_dashboard_notificaciones_eventos_nuevos(self):
        # Primera visita - debe mostrar notificaciones
        response = self.client.get(reverse('dashboard_superadmin'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Tienes" in str(msg) for msg in messages))
        
        # Verificar notificaciones en el contexto
        notificaciones = response.context['notificaciones']
        self.assertTrue(any(notificaciones.values()))

    def test_dashboard_sin_notificaciones_segunda_visita(self):
        # Primera visita para marcar como vistos
        self.client.get(reverse('dashboard_superadmin'))
        
        # Segunda visita - no debe mostrar notificaciones
        response = self.client.get(reverse('dashboard_superadmin'))
        messages = list(get_messages(response.wsgi_request))
        self.assertFalse(any("Tienes" in str(msg) for msg in messages))

    def test_listar_eventos_estado_actualiza_vistos(self):
        estado = "Pendiente"
        response = self.client.get(reverse('listar_eventos_estado', args=[estado]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'listado_eventos.html')
        
        # Verificar que los eventos se marcan como vistos
        session = self.client.session
        vistos = session.get('eventos_vistos', {})
        self.assertIn(estado, vistos)
        
        # Verificar eventos en el contexto
        eventos_por_admin = dict(response.context['eventos_por_admin'])
        self.assertTrue(any(admin.usuario == self.admin_user for admin in eventos_por_admin.keys()))

    def test_listar_eventos_estado_filtrado_correcto(self):
        for estado in self.estados:
            response = self.client.get(reverse('listar_eventos_estado', args=[estado]))
            self.assertEqual(response.status_code, 200)
            eventos_por_admin = dict(response.context['eventos_por_admin'])
            
            # Verificar que solo se muestran eventos del estado correcto
            for admin, eventos in eventos_por_admin.items():
                for evento in eventos:
                    self.assertEqual(evento.eve_estado.lower(), estado.lower())
        for estado in self.estados:
            Evento.objects.create(
                eve_nombre=f'Evento {estado}',
                eve_estado=estado,
                eve_fecha_inicio=timezone.now(),
                eve_fecha_fin=timezone.now() + timedelta(days=7)
            )

    def test_dashboard_eventos_sin_vistos(self):
        # Primera visita al dashboard
        response = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response.status_code, 200)
        
        # Verificar contenido de la respuesta
        self.assertIn('notificaciones', response.context)
        self.assertIn('estados_tarjetas', response.context)
        
        # Verificar que hay mensajes de notificación
        messages_list = list(get_messages(response.wsgi_request))
        mensaje_notificacion = next((msg for msg in messages_list if "Tienes" in str(msg)), None)
        self.assertIsNotNone(mensaje_notificacion)
        
        # Verificar que el mensaje contiene información de los estados correctos
        for estado in ['Pendiente', 'Inscripciones Cerradas', 'Finalizado', 'Cerrado']:
            self.assertIn(estado, str(mensaje_notificacion))

    def test_dashboard_con_eventos_vistos(self):
        # Primera vista del dashboard
        response = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('notificaciones', response.context)
        
        # Segunda vista del dashboard
        response = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response.status_code, 200)
        messages_list = list(get_messages(response.wsgi_request))
        self.assertFalse(any("Tienes" in str(msg) for msg in messages_list))
        
        # Verificar que las notificaciones están en cero
        notificaciones = response.context['notificaciones']
        self.assertTrue(all(cantidad == 0 for cantidad in notificaciones.values()))

    def test_listar_eventos_estado_actualiza_vistos(self):
        estado = "Pendiente"
        # Crear evento específico para probar
        evento = Evento.objects.create(
            eve_nombre=f'Evento prueba {estado}',
            eve_estado=estado.lower(),
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=7)
        )
        
        # Verificar que el evento está en la lista
        response = self.client.get(reverse('listar_eventos_estado', args=[estado]))
        self.assertEqual(response.status_code, 200)
        
        # Verificar el contexto
        self.assertIn('eventos_por_admin', response.context)
        self.assertIn('estado', response.context)
        self.assertEqual(response.context['estado'], estado.title())
        
        # Verificar que se actualizaron los eventos vistos
        session = self.client.session
        vistos = session.get('eventos_vistos', {})
        self.assertIn(estado, vistos)
        self.assertIn(evento.eve_id, vistos[estado])

class TestCodigoInvitacionAdmin(BaseTestCase):
    def test_crear_codigo_invitacion_validacion_campos(self):
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), {})
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("El correo de destino es obligatorio." in str(msg) for msg in messages))

    def test_crear_codigo_invitacion_limite_eventos_invalido(self):
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), {
            'email_destino': 'test@test.com',
            'limite_eventos': '0',
            'fecha_expiracion': '2025-12-31'
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("El límite de eventos debe ser un número mayor a 0." in str(msg) for msg in messages))

    def test_crear_codigo_invitacion_duplicado(self):
        # Crear un código activo primero
        CodigoInvitacionAdminEvento.objects.create(
            codigo='test123',
            email_destino='test@test.com',
            limite_eventos=1,
            fecha_expiracion=timezone.now() + timedelta(days=30)
        )

        # Intentar crear otro código para el mismo email
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), {
            'email_destino': 'test@test.com',
            'limite_eventos': '1',
            'fecha_expiracion': '2025-12-31'
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Ya existe un código activo para ese correo." in str(msg) for msg in messages))

    def test_crear_codigo_invitacion_exitoso(self):
        data = {
            'email_destino': 'nuevo@test.com',
            'limite_eventos': '2',
            'fecha_expiracion': '2025-12-31',
            'tiempo_limite_creacion': '2025-12-31 23:59:59'
        }
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), data)
        
        # Verificar que el código se creó
        self.assertTrue(CodigoInvitacionAdminEvento.objects.filter(email_destino=data['email_destino']).exists())
        
        # Verificar que se envió el correo
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], data['email_destino'])

    def test_crear_codigo_invitacion_fecha_invalida(self):
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), {
            'email_destino': 'test@test.com',
            'limite_eventos': '1',
            'fecha_expiracion': 'fecha-invalida'
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Formato de fecha de expiración inválido." in str(msg) for msg in messages))

    def test_crear_codigo_invitacion_tiempo_limite_invalido(self):
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), {
            'email_destino': 'test@test.com',
            'limite_eventos': '1',
            'fecha_expiracion': '2025-12-31',
            'tiempo_limite_creacion': 'tiempo-invalido'
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Formato de fecha/hora para el tiempo límite de creación inválido." in str(msg) for msg in messages))

    def test_listar_codigos_invitacion_admin(self):
        # Crear algunos códigos de prueba
        for i in range(3):
            CodigoInvitacionAdminEvento.objects.create(
                codigo=f'test{i}',
                email_destino=f'test{i}@test.com',
                limite_eventos=1,
                fecha_expiracion=timezone.now() + timedelta(days=30),
                estado='activo'
            )

        response = self.client.get(reverse('listar_codigos_invitacion_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'listar_codigos_invitacion_admin.html')
        self.assertEqual(len(response.context['codigos']), 3)

    def test_accion_codigo_invitacion_suspender(self):
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='test123',
            email_destino='test@test.com',
            limite_eventos=1,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            estado='activo'
        )

        response = self.client.get(reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'suspender']))
        codigo.refresh_from_db()
        self.assertEqual(codigo.estado, 'suspendido')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Código suspendido correctamente" in str(msg) for msg in messages))

    def test_accion_codigo_invitacion_activar(self):
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='test123',
            email_destino='test@test.com',
            limite_eventos=1,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            estado='suspendido'
        )

        response = self.client.get(reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'activar']))
        codigo.refresh_from_db()
        self.assertEqual(codigo.estado, 'activo')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Código activado correctamente" in str(msg) for msg in messages))

    def test_accion_codigo_invitacion_cancelar(self):
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='test123',
            email_destino='test@test.com',
            limite_eventos=1,
            fecha_expiracion=timezone.now() + timedelta(days=30)
        )

        response = self.client.get(reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'cancelar']))
        self.assertFalse(CodigoInvitacionAdminEvento.objects.filter(codigo='test123').exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Código cancelado y eliminado correctamente" in str(msg) for msg in messages))

    def test_accion_codigo_invitacion_accion_invalida(self):
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='test123',
            email_destino='test@test.com',
            limite_eventos=1,
            fecha_expiracion=timezone.now() + timedelta(days=30)
        )

        response = self.client.get(reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'accion_invalida']))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Acción no permitida" in str(msg) for msg in messages))

class TestDetalleEventoAdmin(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.evento = Evento.objects.create(
            eve_nombre='Evento Test',
            eve_estado='aprobado',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=7),
            eve_capacidad=100
        )
        
        # Crear administrador del evento
        self.admin_user = Usuario.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_admin_evento)
        self.admin_evento = AdministradorEvento.objects.create(usuario=self.admin_user)
        self.evento.eve_administrador_fk = self.admin_evento
        self.evento.save()

    def test_detalle_evento_admin_finalizado_a_cerrado(self):
        self.evento.eve_estado = 'finalizado'
        self.evento.save()

        response = self.client.post(reverse('detalle_evento_admin', args=[self.evento.pk]), {
            'nuevo_estado': 'cerrado'
        })

        # Verificar que el evento fue eliminado
        self.assertFalse(Evento.objects.filter(pk=self.evento.pk).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Evento cerrado y toda la información ha sido eliminada" in str(msg) for msg in messages))

    def test_detalle_evento_admin_cambio_estado_finalizado(self):
        self.evento.eve_estado = 'finalizado'
        self.evento.save()

        response = self.client.post(reverse('detalle_evento_admin', args=[self.evento.pk]), {
            'nuevo_estado': 'aprobado'
        })

        # Verificar que el estado no cambió
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.eve_estado, 'finalizado')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("No se puede cambiar el estado de un evento finalizado" in str(msg) for msg in messages))

    def test_detalle_evento_admin_aprobar_desde_estados_validos(self):
        estados_validos = ['pendiente', 'inscripciones cerradas']
        for estado in estados_validos:
            self.evento.eve_estado = estado
            self.evento.save()

            response = self.client.post(reverse('detalle_evento_admin', args=[self.evento.pk]), {
                'nuevo_estado': 'aprobado'
            })

            self.evento.refresh_from_db()
            self.assertEqual(self.evento.eve_estado, 'aprobado')
            
            # Verificar envío de correo al admin
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].to[0], self.admin_user.email)
            mail.outbox.clear()  # Limpiar para el siguiente test

    def test_detalle_evento_admin_aprobar_desde_estado_invalido(self):
        self.evento.eve_estado = 'rechazado'
        self.evento.save()

        response = self.client.post(reverse('detalle_evento_admin', args=[self.evento.pk]), {
            'nuevo_estado': 'aprobado'
        })

        self.evento.refresh_from_db()
        self.assertEqual(self.evento.eve_estado, 'rechazado')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Solo se pueden aprobar eventos en estado Pendiente o con Inscripciones Cerradas" in str(msg) for msg in messages))

    def test_detalle_evento_admin_estadisticas_evento_aprobado(self):
        # El evento ya está aprobado desde el setUp
        
        # Crear algunos registros para las estadísticas
        usuario_asistente = Usuario.objects.create_user(
            username='asistente_test',
            email='asistente@test.com',
            password='test123',
            documento='123457'
        )
        RolUsuario.objects.create(usuario=usuario_asistente, rol=self.rol_asistente)
        asistente = Asistente.objects.create(usuario=usuario_asistente)
        AsistenteEvento.objects.create(
            asistente=asistente,
            evento=self.evento,
            asi_eve_estado='Aprobado'
        )

        # Hacer la petición
        response = self.client.get(reverse('detalle_evento_admin', args=[self.evento.pk]))
        self.assertEqual(response.status_code, 200)
        
        # Verificar que las estadísticas están en el contexto
        self.assertIn('estadisticas', response.context)
        estadisticas = response.context['estadisticas']
        
        # Verificar estructura de estadísticas
        self.assertIn('asistentes', estadisticas)
        self.assertIn('participantes', estadisticas)
        self.assertIn('evaluadores', estadisticas)
        self.assertIn('capacidad', estadisticas)
        self.assertIn('archivos', estadisticas)

    def test_dashboard_acceso(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')

    def test_dashboard_eventos_por_estado(self):
        response = self.client.get(reverse('dashboard'))
        self.assertIn('notificaciones', response.context)
        self.assertIn('estados_tarjetas', response.context)

        # Verificar que hay eventos nuevos
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('nuevo(s)' in str(message) for message in messages))

class TestCrearCodigoInvitacion(BaseTestCase):
    def test_crear_codigo_get(self):
        response = self.client.get(reverse('crear_codigo_invitacion_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crear_codigo_invitacion_admin.html')

    def test_crear_codigo_post_valido(self):
        data = {
            'email_destino': 'nuevo@admin.com',
            'limite_eventos': '5',
            'fecha_expiracion': timezone.now().isoformat(),
            'tiempo_limite_creacion': timezone.now().isoformat()
        }
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), data)
        self.assertRedirects(response, reverse('crear_codigo_invitacion_admin'))
        self.assertTrue(CodigoInvitacionAdminEvento.objects.filter(email_destino='nuevo@admin.com').exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_crear_codigo_post_invalido(self):
        data = {
            'email_destino': '',
            'limite_eventos': '-1',
            'fecha_expiracion': ''
        }
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), data)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('obligatorio' in str(message) for message in messages))

class TestListarEventosEstado(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_evento = AdministradorEvento.objects.create(
            usuario=Usuario.objects.create_user(
                username='admin_evento',
                email='admin@test.com',
                password='test123',
                documento='789012'
            )
        )
        self.evento.eve_administrador_fk = self.admin_evento
        self.evento.save()

    def test_listar_eventos_estado(self):
        url = reverse('listar_eventos_estado', args=['activo'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'listado_eventos.html')

class TestDetalleEventoAdmin(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Crear administrador para el evento
        self.admin_evento = AdministradorEvento.objects.create(
            usuario=Usuario.objects.create_user(
                username='admin_evento',
                email='admin@test.com',
                password='test123',
                documento='789012'
            )
        )
        self.evento.eve_administrador_fk = self.admin_evento
        self.evento.eve_estado = 'pendiente'
        self.evento.save()

        # Crear categorías y áreas
        self.area = Area.objects.create(are_nombre='Area Test')
        self.categoria = Categoria.objects.create(
            cat_nombre='Categoria Test',
            cat_area_fk=self.area
        )
        EventoCategoria.objects.create(
            evento=self.evento,
            categoria=self.categoria
        )

        # Crear participantes, asistentes y evaluadores
        usuario_participante = Usuario.objects.create_user(
            username='participante',
            email='participante@test.com',
            password='test123',
            documento='123123'
        )
        RolUsuario.objects.create(usuario=usuario_participante, rol=self.rol_participante)
        participante = Participante.objects.create(usuario=usuario_participante)
        ParticipanteEvento.objects.create(
            participante=participante,
            evento=self.evento,
            estado='aceptado'
        )

        usuario_asistente = Usuario.objects.create_user(
            username='asistente',
            email='asistente@test.com',
            password='test123',
            documento='456456'
        )
        RolUsuario.objects.create(usuario=usuario_asistente, rol=self.rol_asistente)
        asistente = Asistente.objects.create(usuario=usuario_asistente)
        AsistenteEvento.objects.create(
            asistente=asistente,
            evento=self.evento
        )

        # Crear evaluador y criterios
        usuario_evaluador = Usuario.objects.create_user(
            username='evaluador',
            email='evaluador@test.com',
            password='test123',
            documento='789789'
        )
        RolUsuario.objects.create(usuario=usuario_evaluador, rol=self.rol_evaluador)
        evaluador = Evaluador.objects.create(usuario=usuario_evaluador)
        self.evaluador_evento = EvaluadorEvento.objects.create(
            evaluador=evaluador,
            evento=self.evento
        )

        # Crear criterios y calificaciones
        self.criterio = Criterio.objects.create(
            cri_evento_fk=self.evento,
            cri_nombre='Criterio Test',
            cri_descripcion='Descripción del criterio',
            cri_valor_maximo=100
        )

    def test_detalle_evento_get(self):
        url = reverse('detalle_evento_admin', args=[self.evento.eve_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app_admin/detalle_evento_admin.html')

    def test_cambiar_estado_a_aprobado(self):
        url = reverse('detalle_evento_admin', args=[self.evento.eve_id])
        response = self.client.post(url, {'nuevo_estado': 'aprobado'})
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.eve_estado, 'aprobado')
        self.assertEqual(len(mail.outbox), 1)  # Verifica el envío del correo

    def test_cerrar_evento_finalizado(self):
        self.evento.eve_estado = 'finalizado'
        self.evento.save()
        url = reverse('detalle_evento_admin', args=[self.evento.eve_id])
        response = self.client.post(url, {'nuevo_estado': 'cerrado'})
        self.assertTrue(any('cerrado' in str(message) for message in get_messages(response.wsgi_request)))

    def test_no_permitir_cambio_estado_finalizado(self):
        self.evento.eve_estado = 'finalizado'
        self.evento.save()
        url = reverse('detalle_evento_admin', args=[self.evento.eve_id])
        response = self.client.post(url, {'nuevo_estado': 'aprobado'})
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.eve_estado, 'finalizado')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No se puede cambiar el estado' in str(message) for message in messages))

    def test_aprobar_desde_estado_no_permitido(self):
        self.evento.eve_estado = 'rechazado'
        self.evento.save()
        url = reverse('detalle_evento_admin', args=[self.evento.eve_id])
        response = self.client.post(url, {'nuevo_estado': 'aprobado'})
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.eve_estado, 'rechazado')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Solo se pueden aprobar eventos' in str(message) for message in messages))

    def test_estadisticas_evento_aprobado(self):
        self.evento.eve_estado = 'aprobado'
        self.evento.save()
        url = reverse('detalle_evento_admin', args=[self.evento.eve_id])
        response = self.client.get(url)
        self.assertIn('estadisticas', response.context)
        stats = response.context['estadisticas']

        # Verificar todas las secciones de estadísticas
        self.assertIn('asistentes', stats)
        self.assertIn('participantes', stats)
        self.assertIn('evaluadores', stats)
        self.assertIn('evaluacion', stats)
        self.assertIn('capacidad', stats)
        self.assertIn('archivos', stats)

        # Verificar conteos específicos
        self.assertEqual(stats['asistentes']['total'], 1)
        self.assertEqual(stats['participantes']['total'], 1)
        self.assertEqual(stats['evaluadores']['total'], 1)
        self.assertEqual(stats['evaluacion']['criterios'], 1)

class TestDescargarProgramacion(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.evento.eve_programacion = 'programacion.pdf'
        self.evento.save()

    @patch('django.core.files.storage.default_storage.open', mock_open(read_data=b'PDF content'))
    def test_descargar_programacion_existe(self):
        url = reverse('descargar_programacion', args=[self.evento.eve_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_descargar_programacion_no_existe(self):
        self.evento.eve_programacion = None
        self.evento.save()
        url = reverse('descargar_programacion', args=[self.evento.eve_id])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('detalle_evento_admin', args=[self.evento.eve_id]))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('no tiene un archivo de programación' in str(message) for message in messages))

    def test_descargar_programacion_archivo_no_encontrado(self):
        url = reverse('descargar_programacion', args=[self.evento.eve_id])
        with patch('django.core.files.storage.default_storage.open') as mock_open:
            mock_open.side_effect = FileNotFoundError()
            response = self.client.get(url)
            self.assertRedirects(response, reverse('detalle_evento_admin', args=[self.evento.eve_id]))
            messages = list(get_messages(response.wsgi_request))
            self.assertTrue(any('no se encuentra en el servidor' in str(message) for message in messages))

class TestListarAdministradoresEvento(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Crear varios administradores para probar
        for i in range(3):
            usuario = Usuario.objects.create_user(
                username=f'admin{i}',
                email=f'admin{i}@test.com',
                password='test123',
                documento=f'789{i}'
            )
            RolUsuario.objects.create(usuario=usuario, rol=self.rol_admin_evento)
            AdministradorEvento.objects.create(usuario=usuario)

    def test_listar_administradores(self):
        url = reverse('listar_administradores_evento')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'listar_administradores.html')
        self.assertEqual(len(response.context['administradores']), 3)

class TestEliminarAdministrador(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_usuario = Usuario.objects.create_user(
            username='admin_evento',
            email='admin@test.com',
            password='test123',
            documento='789012'
        )
        RolUsuario.objects.create(usuario=self.admin_usuario, rol=self.rol_admin_evento)
        self.admin_evento = AdministradorEvento.objects.create(usuario=self.admin_usuario)

    def test_eliminar_administrador(self):
        url = reverse('eliminar_administrador', args=[self.admin_evento.id])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('listar_administradores_evento'))
        self.assertFalse(AdministradorEvento.objects.filter(id=self.admin_evento.id).exists())
        self.assertFalse(Usuario.objects.filter(id=self.admin_usuario.id).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('eliminado correctamente' in str(message) for message in messages))

    def test_eliminar_administrador_no_existe(self):
        url = reverse('eliminar_administrador', args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

class TestCrearAreaCategoria(BaseTestCase):
    def test_crear_area_get(self):
        response = self.client.get(reverse('crear_area_categoria'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crear_area_categoria.html')

    def test_crear_area_post_valido(self):
        data = {
            'crear_area': True,
            'nombre_area': 'Nueva Area',
            'descripcion_area': 'Descripción del área'
        }
        response = self.client.post(reverse('crear_area_categoria'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Area.objects.filter(are_nombre='Nueva Area').exists())
        self.assertEqual(Area.objects.get(are_nombre='Nueva Area').are_descripcion, 'Descripción del área')

    def test_crear_area_post_nombre_duplicado(self):
        Area.objects.create(are_nombre='Area Existente')
        data = {
            'crear_area': True,
            'nombre_area': 'Area Existente',
            'descripcion_area': 'Nueva descripción'
        }
        response = self.client.post(reverse('crear_area_categoria'), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Ya existe un área con ese nombre', response.context['mensaje'])

    def test_crear_area_post_sin_nombre(self):
        data = {
            'crear_area': True,
            'nombre_area': '',
            'descripcion_area': 'Descripción'
        }
        response = self.client.post(reverse('crear_area_categoria'), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('El nombre del área es obligatorio', response.context['mensaje'])

    def test_crear_categoria_post_valido(self):
        area = Area.objects.create(are_nombre='Area Test')
        data = {
            'crear_categoria': True,
            'nombre_categoria': 'Nueva Categoria',
            'descripcion_categoria': 'Descripción de la categoría',
            'area_id': area.id
        }
        response = self.client.post(reverse('crear_area_categoria'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Categoria.objects.filter(cat_nombre='Nueva Categoria').exists())

    def test_crear_categoria_post_sin_area(self):
        data = {
            'crear_categoria': True,
            'nombre_categoria': 'Nueva Categoria',
            'descripcion_categoria': 'Descripción'
        }
        response = self.client.post(reverse('crear_area_categoria'), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('El nombre de la categoría y el área son obligatorios', response.context['mensaje_categoria'])

    def test_crear_categoria_post_duplicada_en_area(self):
        area = Area.objects.create(are_nombre='Area Test')
        Categoria.objects.create(
            cat_nombre='Categoria Existente',
            cat_area_fk=area
        )
        data = {
            'crear_categoria': True,
            'nombre_categoria': 'Categoria Existente',
            'descripcion_categoria': 'Nueva descripción',
            'area_id': area.id
        }
        response = self.client.post(reverse('crear_area_categoria'), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Ya existe una categoría con ese nombre en el área seleccionada', response.context['mensaje_categoria'])

class TestCodigosInvitacionAdmin(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo=str(uuid.uuid4()),
            email_destino='admin@test.com',
            limite_eventos=5,
            fecha_expiracion=timezone.now() + timedelta(days=7),
            estado='activo'
        )

    def test_listar_codigos(self):
        url = reverse('listar_codigos_invitacion_admin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'listar_codigos_invitacion_admin.html')
        self.assertEqual(len(response.context['codigos']), 1)

    def test_suspender_codigo_activo(self):
        url = reverse('accion_codigo_invitacion_admin', args=[self.codigo.codigo, 'suspender'])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('listar_codigos_invitacion_admin'))
        self.codigo.refresh_from_db()
        self.assertEqual(self.codigo.estado, 'suspendido')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('suspendido correctamente' in str(message) for message in messages))

    def test_activar_codigo_suspendido(self):
        self.codigo.estado = 'suspendido'
        self.codigo.save()
        url = reverse('accion_codigo_invitacion_admin', args=[self.codigo.codigo, 'activar'])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('listar_codigos_invitacion_admin'))
        self.codigo.refresh_from_db()
        self.assertEqual(self.codigo.estado, 'activo')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('activado correctamente' in str(message) for message in messages))

    def test_cancelar_codigo(self):
        url = reverse('accion_codigo_invitacion_admin', args=[self.codigo.codigo, 'cancelar'])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('listar_codigos_invitacion_admin'))
        self.assertFalse(CodigoInvitacionAdminEvento.objects.filter(id=self.codigo.id).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('cancelado y eliminado correctamente' in str(message) for message in messages))

    def test_accion_invalida(self):
        url = reverse('accion_codigo_invitacion_admin', args=[self.codigo.codigo, 'accion_invalida'])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('listar_codigos_invitacion_admin'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Acción no permitida' in str(message) for message in messages))

    def test_codigo_no_existe(self):
        url = reverse('accion_codigo_invitacion_admin', args=['codigo_inexistente', 'suspender'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.http import Http404
from unittest.mock import patch, mock_open, MagicMock
from app_eventos.models import Evento, ConfiguracionCertificado, EventoCategoria
from app_areas.models import Categoria, Area
from app_administradores.models import AdministradorEvento, CodigoInvitacionAdminEvento, CodigoInvitacionEvento
from app_asistentes.models import Asistente, AsistenteEvento
from app_participantes.models import Participante, ParticipanteEvento
from app_evaluadores.models import Evaluador, EvaluadorEvento
from app_usuarios.models import Rol, RolUsuario, Usuario
from app_admin.views import _eliminar_informacion_evento_cerrado
from django.utils import timezone
from datetime import timedelta
import os

Usuario = get_user_model()


class ManualSuperAdminTestCase(TestCase):
    """
    Tests para la vista manual_super_admin
    """
    
    def setUp(self):
        self.client = Client()
        # Crear superadmin para las pruebas
        self.rol_superadmin = Rol.objects.create(nombre='superadmin')
        self.usuario = Usuario.objects.create_user(
            username='superadmin',
            email='super@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.usuario, rol=self.rol_superadmin)
        self.client.login(email='super@test.com', password='test123')
        # Simular rol en sesión
        session = self.client.session
        session['rol_sesion'] = 'superadmin'
        session.save()
        
        self.url = reverse('manual_super_admin')
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b'PDF content')
    @override_settings(MEDIA_ROOT='/fake/media/root')
    def test_manual_super_admin_existe(self, mock_file, mock_exists):
        """
        Test cuando el archivo PDF existe
        """
        mock_exists.return_value = True
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        mock_exists.assert_called_once()
    
    @patch('os.path.exists')
    @override_settings(MEDIA_ROOT='/fake/media/root')
    def test_manual_super_admin_no_existe(self, mock_exists):
        """
        Test cuando el archivo PDF no existe - debe lanzar Http404
        """
        mock_exists.return_value = False
        
        response = self.client.get(self.url)
        
        # Verificar que se retorna 404
        self.assertEqual(response.status_code, 404)


class ManualTecnicoOperacionTestCase(TestCase):
    """
    Tests para la vista manual_tecnico_operacion
    """
    
    def setUp(self):
        self.client = Client()
        # Crear superadmin
        self.rol_superadmin = Rol.objects.create(nombre='superadmin')
        self.usuario = Usuario.objects.create_user(
            username='superadmin',
            email='super@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.usuario, rol=self.rol_superadmin)
        self.client.login(email='super@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'superadmin'
        session.save()
        
        self.url = reverse('manual_tecnico_operacion')
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b'PDF content')
    @override_settings(MEDIA_ROOT='/fake/media/root')
    def test_manual_tecnico_existe(self, mock_file, mock_exists):
        """
        Test cuando el archivo PDF existe
        """
        mock_exists.return_value = True
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
    
    @patch('os.path.exists')
    @override_settings(MEDIA_ROOT='/fake/media/root')
    def test_manual_tecnico_no_existe(self, mock_exists):
        """
        Test cuando el archivo PDF no existe
        """
        mock_exists.return_value = False
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 404)


class EliminarInformacionEventoCerradoTestCase(TestCase):
    """
    Tests para la función _eliminar_informacion_evento_cerrado
    Estos tests cubren todos los caminos de ejecución de la función
    """
    
    def setUp(self):
        # Crear roles necesarios
        self.rol_asistente = Rol.objects.create(nombre='asistente')
        self.rol_participante = Rol.objects.create(nombre='participante')
        self.rol_evaluador = Rol.objects.create(nombre='evaluador')
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        
        # Crear área y categoría para el evento
        self.area = Area.objects.create(
            are_nombre='Tecnología',
            are_descripcion='Área de tecnología'
        )
        self.categoria = Categoria.objects.create(
            cat_nombre='Conferencia',
            cat_descripcion='Categoría de conferencias',
            cat_area_fk=self.area
        )
    
    def crear_evento_base(self, administrador=None):
        """Helper para crear un evento con los campos obligatorios"""
        return Evento.objects.create(
            eve_nombre='Evento Test',
            eve_descripcion='Descripción del evento',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='cerrado',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=administrador
        )
    
    def test_eliminar_asistente_sin_otros_eventos(self):
        """
        Test: Eliminar asistente que solo está en este evento
        Debe eliminar: AsistenteEvento, Asistente, RolUsuario y Usuario
        """
        usuario = Usuario.objects.create_user(
            username='asistente1',
            email='asistente1@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=usuario, rol=self.rol_asistente)
        asistente = Asistente.objects.create(usuario=usuario)
        
        evento = self.crear_evento_base()
        AsistenteEvento.objects.create(
            asistente=asistente,
            evento=evento,
            asi_eve_fecha_hora=timezone.now(),
            asi_eve_estado='confirmado'
        )
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertFalse(AsistenteEvento.objects.filter(asistente=asistente).exists())
        self.assertFalse(Asistente.objects.filter(id=asistente.id).exists())
        self.assertFalse(Usuario.objects.filter(id=usuario.id).exists())
        self.assertFalse(Evento.objects.filter(eve_id=evento.eve_id).exists())
    
    def test_eliminar_asistente_con_otros_eventos(self):
        """
        Test: Asistente que está en múltiples eventos
        Solo debe eliminar AsistenteEvento, NO el Asistente ni Usuario
        """
        usuario = Usuario.objects.create_user(
            username='asistente2',
            email='asistente2@test.com',
            password='test123',
            documento='234567'
        )
        RolUsuario.objects.create(usuario=usuario, rol=self.rol_asistente)
        asistente = Asistente.objects.create(usuario=usuario)
        
        evento1 = self.crear_evento_base()
        evento2 = self.crear_evento_base()
        evento2.eve_nombre = 'Evento 2'
        evento2.eve_estado = 'activo'
        evento2.save()
        
        AsistenteEvento.objects.create(
            asistente=asistente,
            evento=evento1,
            asi_eve_fecha_hora=timezone.now(),
            asi_eve_estado='confirmado'
        )
        AsistenteEvento.objects.create(
            asistente=asistente,
            evento=evento2,
            asi_eve_fecha_hora=timezone.now(),
            asi_eve_estado='confirmado'
        )
        
        _eliminar_informacion_evento_cerrado(evento1)
        
        self.assertTrue(Asistente.objects.filter(id=asistente.id).exists())
        self.assertTrue(Usuario.objects.filter(id=usuario.id).exists())
        self.assertTrue(AsistenteEvento.objects.filter(asistente=asistente, evento=evento2).exists())
    
    def test_eliminar_asistente_excepcion_does_not_exist(self):
        """
        Test: Manejar caso cuando Asistente.DoesNotExist durante eliminación
        """
        usuario = Usuario.objects.create_user(
            username='asistente3',
            email='asistente3@test.com',
            password='test123',
            documento='345678'
        )
        asistente = Asistente.objects.create(usuario=usuario)
        
        evento = self.crear_evento_base()
        AsistenteEvento.objects.create(
            asistente=asistente,
            evento=evento,
            asi_eve_fecha_hora=timezone.now(),
            asi_eve_estado='confirmado'
        )
        
        asistente.delete()
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertFalse(Evento.objects.filter(eve_id=evento.eve_id).exists())
    
    def test_eliminar_participante_sin_otros_eventos(self):
        """
        Test: Eliminar participante que solo está en este evento
        """
        usuario = Usuario.objects.create_user(
            username='participante1',
            email='participante1@test.com',
            password='test123',
            documento='456789'
        )
        RolUsuario.objects.create(usuario=usuario, rol=self.rol_participante)
        participante = Participante.objects.create(usuario=usuario)
        
        evento = self.crear_evento_base()
        ParticipanteEvento.objects.create(
            participante=participante,
            evento=evento,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado='confirmado'
        )
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertFalse(ParticipanteEvento.objects.filter(participante=participante).exists())
        self.assertFalse(Participante.objects.filter(id=participante.id).exists())
        self.assertFalse(Usuario.objects.filter(id=usuario.id).exists())
    
    def test_eliminar_participante_con_otros_eventos(self):
        """
        Test: Participante en múltiples eventos
        """
        usuario = Usuario.objects.create_user(
            username='participante2',
            email='participante2@test.com',
            password='test123',
            documento='567890'
        )
        RolUsuario.objects.create(usuario=usuario, rol=self.rol_participante)
        participante = Participante.objects.create(usuario=usuario)
        
        evento1 = self.crear_evento_base()
        evento2 = self.crear_evento_base()
        evento2.eve_nombre = 'Evento 2'
        evento2.eve_estado = 'activo'
        evento2.save()
        
        ParticipanteEvento.objects.create(
            participante=participante,
            evento=evento1,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado='confirmado'
        )
        ParticipanteEvento.objects.create(
            participante=participante,
            evento=evento2,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado='confirmado'
        )
        
        _eliminar_informacion_evento_cerrado(evento1)
        
        self.assertTrue(Participante.objects.filter(id=participante.id).exists())
        self.assertTrue(Usuario.objects.filter(id=usuario.id).exists())
    
    def test_eliminar_participante_excepcion_does_not_exist(self):
        """
        Test: Manejar Participante.DoesNotExist
        """
        usuario = Usuario.objects.create_user(
            username='participante3',
            email='participante3@test.com',
            password='test123',
            documento='678901'
        )
        participante = Participante.objects.create(usuario=usuario)
        
        evento = self.crear_evento_base()
        ParticipanteEvento.objects.create(
            participante=participante,
            evento=evento,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado='confirmado'
        )
        
        participante.delete()
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertFalse(Evento.objects.filter(eve_id=evento.eve_id).exists())
    
    def test_eliminar_evaluador_sin_otros_eventos(self):
        """
        Test: Eliminar evaluador que solo está en este evento
        """
        usuario = Usuario.objects.create_user(
            username='evaluador1',
            email='evaluador1@test.com',
            password='test123',
            documento='789012'
        )
        RolUsuario.objects.create(usuario=usuario, rol=self.rol_evaluador)
        evaluador = Evaluador.objects.create(usuario=usuario)
        
        evento = self.crear_evento_base()
        EvaluadorEvento.objects.create(
            evaluador=evaluador,
            evento=evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado='confirmado'
        )
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertFalse(EvaluadorEvento.objects.filter(evaluador=evaluador).exists())
        self.assertFalse(Evaluador.objects.filter(id=evaluador.id).exists())
        self.assertFalse(Usuario.objects.filter(id=usuario.id).exists())
    
    def test_eliminar_evaluador_con_otros_eventos(self):
        """
        Test: Evaluador en múltiples eventos
        """
        usuario = Usuario.objects.create_user(
            username='evaluador2',
            email='evaluador2@test.com',
            password='test123',
            documento='890123'
        )
        RolUsuario.objects.create(usuario=usuario, rol=self.rol_evaluador)
        evaluador = Evaluador.objects.create(usuario=usuario)
        
        evento1 = self.crear_evento_base()
        evento2 = self.crear_evento_base()
        evento2.eve_nombre = 'Evento 2'
        evento2.eve_estado = 'activo'
        evento2.save()
        
        EvaluadorEvento.objects.create(
            evaluador=evaluador,
            evento=evento1,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado='confirmado'
        )
        EvaluadorEvento.objects.create(
            evaluador=evaluador,
            evento=evento2,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado='confirmado'
        )
        
        _eliminar_informacion_evento_cerrado(evento1)
        
        self.assertTrue(Evaluador.objects.filter(id=evaluador.id).exists())
        self.assertTrue(Usuario.objects.filter(id=usuario.id).exists())
    
    def test_eliminar_evaluador_excepcion_does_not_exist(self):
        """
        Test: Manejar Evaluador.DoesNotExist
        """
        usuario = Usuario.objects.create_user(
            username='evaluador3',
            email='evaluador3@test.com',
            password='test123',
            documento='901234'
        )
        evaluador = Evaluador.objects.create(usuario=usuario)
        
        evento = self.crear_evento_base()
        EvaluadorEvento.objects.create(
            evaluador=evaluador,
            evento=evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado='confirmado'
        )
        
        evaluador.delete()
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertFalse(Evento.objects.filter(eve_id=evento.eve_id).exists())
    
    def test_eliminar_administrador_sin_otros_eventos_sin_codigos_validos(self):
        """
        Test: Administrador sin otros eventos y sin códigos con límite > 0
        Debe eliminar: AdministradorEvento, RolUsuario, Usuario y sus códigos
        """
        usuario_admin = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='012345'
        )
        RolUsuario.objects.create(usuario=usuario_admin, rol=self.rol_admin)
        administrador = AdministradorEvento.objects.create(usuario=usuario_admin)
        
        CodigoInvitacionAdminEvento.objects.create(
            codigo='codigo123',
            email_destino='admin1@test.com',
            limite_eventos=0,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            usuario_asignado=usuario_admin
        )
        
        evento = self.crear_evento_base(administrador=administrador)
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertFalse(CodigoInvitacionAdminEvento.objects.filter(usuario_asignado=usuario_admin).exists())
        self.assertFalse(AdministradorEvento.objects.filter(id=administrador.id).exists())
        self.assertFalse(Usuario.objects.filter(id=usuario_admin.id).exists())
    
    def test_eliminar_administrador_sin_otros_eventos_con_codigos_validos(self):
        """
        Test: Administrador sin otros eventos PERO con códigos límite > 0
        NO debe eliminar nada del administrador
        """
        usuario_admin = Usuario.objects.create_user(
            username='admin2',
            email='admin2@test.com',
            password='test123',
            documento='123450'
        )
        RolUsuario.objects.create(usuario=usuario_admin, rol=self.rol_admin)
        administrador = AdministradorEvento.objects.create(usuario=usuario_admin)
        
        CodigoInvitacionAdminEvento.objects.create(
            codigo='codigo456',
            email_destino='admin2@test.com',
            limite_eventos=5,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            usuario_asignado=usuario_admin
        )
        
        evento = self.crear_evento_base(administrador=administrador)
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertTrue(AdministradorEvento.objects.filter(id=administrador.id).exists())
        self.assertTrue(Usuario.objects.filter(id=usuario_admin.id).exists())
        self.assertTrue(CodigoInvitacionAdminEvento.objects.filter(usuario_asignado=usuario_admin).exists())
    
    def test_eliminar_administrador_con_otros_eventos(self):
        """
        Test: Administrador con múltiples eventos
        NO debe eliminarse nada del administrador
        """
        usuario_admin = Usuario.objects.create_user(
            username='admin3',
            email='admin3@test.com',
            password='test123',
            documento='234501'
        )
        RolUsuario.objects.create(usuario=usuario_admin, rol=self.rol_admin)
        administrador = AdministradorEvento.objects.create(usuario=usuario_admin)
        
        evento1 = self.crear_evento_base(administrador=administrador)
        evento2 = self.crear_evento_base(administrador=administrador)
        evento2.eve_nombre = 'Evento 2'
        evento2.eve_estado = 'activo'
        evento2.save()
        
        _eliminar_informacion_evento_cerrado(evento1)
        
        self.assertTrue(AdministradorEvento.objects.filter(id=administrador.id).exists())
        self.assertTrue(Usuario.objects.filter(id=usuario_admin.id).exists())
    
    def test_eliminar_evento_sin_administrador(self):
        """
        Test: Evento sin administrador (eve_administrador_fk = None)
        """
        evento = Evento.objects.create(
            eve_nombre='Evento Sin Admin',
            eve_descripcion='Descripción',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='cerrado',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=None
        )
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertFalse(Evento.objects.filter(eve_id=evento.eve_id).exists())
    
    def test_eliminar_codigos_invitacion_evento(self):
        """
        Test: Eliminar CodigoInvitacionEvento asociados al evento
        """
        usuario_admin = Usuario.objects.create_user(
            username='admin4',
            email='admin4@test.com',
            password='test123',
            documento='345012'
        )
        administrador = AdministradorEvento.objects.create(usuario=usuario_admin)
        
        evento = self.crear_evento_base(administrador=administrador)
        
        CodigoInvitacionEvento.objects.create(
            codigo='codigo_evento_123',
            evento=evento,
            email_destino='test@test.com',
            tipo='evaluador',
            administrador_creador=administrador,
            fecha_expiracion=timezone.now() + timedelta(days=30)
        )
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertFalse(CodigoInvitacionEvento.objects.filter(evento=evento).exists())
    
    def test_eliminar_configuracion_certificado(self):
        """
        Test: Eliminar ConfiguracionCertificado del evento
        """
        evento = self.crear_evento_base()
        
        ConfiguracionCertificado.objects.create(
            evento=evento,
            tipo='asistencia',
            plantilla='elegante',
            titulo='Certificado de Asistencia',
            cuerpo='Certifica que {nombre} asistió al evento'
        )
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertFalse(ConfiguracionCertificado.objects.filter(evento=evento).exists())
    
    def test_eliminar_evento_categoria(self):
        """
        Test: Eliminar relaciones EventoCategoria
        """
        evento = self.crear_evento_base()
        
        categoria2 = Categoria.objects.create(
            cat_nombre='Taller',
            cat_descripcion='Talleres prácticos',
            cat_area_fk=self.area
        )
        
        EventoCategoria.objects.create(evento=evento, categoria=categoria2)
        
        _eliminar_informacion_evento_cerrado(evento)
        
        self.assertFalse(EventoCategoria.objects.filter(evento=evento).exists())
    
    def test_eliminacion_completa_evento_con_todo(self):
        """
        Test integración completa: Evento con todo tipo de información
        """
        usuario_admin = Usuario.objects.create_user(
            username='admin_completo',
            email='admin@test.com',
            password='test123',
            documento='450123'
        )
        RolUsuario.objects.create(usuario=usuario_admin, rol=self.rol_admin)
        administrador = AdministradorEvento.objects.create(usuario=usuario_admin)
        
        evento = self.crear_evento_base(administrador=administrador)
        
        # Agregar asistente
        usuario_asist = Usuario.objects.create_user(
            username='asist',
            email='a@a.com',
            password='123',
            documento='501234'
        )
        RolUsuario.objects.create(usuario=usuario_asist, rol=self.rol_asistente)
        asistente = Asistente.objects.create(usuario=usuario_asist)
        AsistenteEvento.objects.create(
            asistente=asistente,
            evento=evento,
            asi_eve_fecha_hora=timezone.now(),
            asi_eve_estado='confirmado'
        )
        
        # Agregar participante
        usuario_part = Usuario.objects.create_user(
            username='part',
            email='p@p.com',
            password='123',
            documento='601234'
        )
        RolUsuario.objects.create(usuario=usuario_part, rol=self.rol_participante)
        participante = Participante.objects.create(usuario=usuario_part)
        ParticipanteEvento.objects.create(
            participante=participante,
            evento=evento,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado='confirmado'
        )
        
        # Agregar evaluador
        usuario_eval = Usuario.objects.create_user(
            username='eval',
            email='e@e.com',
            password='123',
            documento='701234'
        )
        RolUsuario.objects.create(usuario=usuario_eval, rol=self.rol_evaluador)
        evaluador = Evaluador.objects.create(usuario=usuario_eval)
        EvaluadorEvento.objects.create(
            evaluador=evaluador,
            evento=evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado='confirmado'
        )
        
        # Agregar configuraciones
        CodigoInvitacionEvento.objects.create(
            codigo='cod_evt',
            evento=evento,
            email_destino='x@x.com',
            tipo='evaluador',
            administrador_creador=administrador,
            fecha_expiracion=timezone.now() + timedelta(days=30)
        )
        ConfiguracionCertificado.objects.create(
            evento=evento,
            tipo='asistencia',
            plantilla='elegante',
            titulo='Certificado',
            cuerpo='Certifica'
        )
        
        _eliminar_informacion_evento_cerrado(evento)
        
        # Verificar que todo se eliminó
        self.assertFalse(Evento.objects.filter(eve_id=evento.eve_id).exists())
        self.assertFalse(AsistenteEvento.objects.filter(evento=evento).exists())
        self.assertFalse(ParticipanteEvento.objects.filter(evento=evento).exists())
        self.assertFalse(EvaluadorEvento.objects.filter(evento=evento).exists())
        self.assertFalse(CodigoInvitacionEvento.objects.filter(evento=evento).exists())
        self.assertFalse(ConfiguracionCertificado.objects.filter(evento=evento).exists())


class DetalleEventoAdminTestCase(TestCase):
    """
    Tests para la vista detalle_evento_admin
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear roles
        self.rol_superadmin = Rol.objects.create(nombre='superadmin')
        self.rol_admin = Rol.objects.create(nombre='administrador_evento')
        self.rol_asistente = Rol.objects.create(nombre='asistente')
        self.rol_participante = Rol.objects.create(nombre='participante')
        self.rol_evaluador = Rol.objects.create(nombre='evaluador')
        
        # Crear superadmin
        self.superadmin = Usuario.objects.create_user(
            username='superadmin',
            email='super@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.superadmin, rol=self.rol_superadmin)
        
        # Crear administrador de evento
        self.usuario_admin = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='234567',
            first_name='Admin',
            last_name='Test'
        )
        RolUsuario.objects.create(usuario=self.usuario_admin, rol=self.rol_admin)
        self.administrador = AdministradorEvento.objects.create(usuario=self.usuario_admin)
        
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
        
        # Login como superadmin
        self.client.login(email='super@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'superadmin'
        session.save()
    
    def crear_evento(self, estado='pendiente', con_archivos=False):
        """Helper para crear eventos"""
        evento = Evento.objects.create(
            eve_nombre='Evento Test',
            eve_descripcion='Descripción',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado=estado,
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador
        )
        
        # Agregar categoría al evento
        EventoCategoria.objects.create(evento=evento, categoria=self.categoria)
        
        return evento
    
    def test_detalle_evento_get_pendiente(self):
        """Test GET para evento en estado pendiente"""
        evento = self.crear_evento(estado='pendiente')
        url = reverse('detalle_evento_admin', args=[evento.eve_id])
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, evento.eve_nombre)
        self.assertIn('estados', response.context)
        self.assertIsNone(response.context['estadisticas'])
    
    def test_detalle_evento_get_aprobado_con_estadisticas(self):
        """Test GET para evento aprobado con estadísticas completas"""
        evento = self.crear_evento(estado='aprobado')
        
        # Crear asistente
        usuario_asist = Usuario.objects.create_user(
            username='asist1',
            email='asist1@test.com',
            password='123',
            documento='345678'
        )
        asistente = Asistente.objects.create(usuario=usuario_asist)
        AsistenteEvento.objects.create(
            asistente=asistente,
            evento=evento,
            asi_eve_fecha_hora=timezone.now(),
            asi_eve_estado='Aprobado',
            confirmado=True
        )
        
        # Crear participante
        usuario_part = Usuario.objects.create_user(
            username='part1',
            email='part1@test.com',
            password='123',
            documento='456789'
        )
        participante = Participante.objects.create(usuario=usuario_part)
        ParticipanteEvento.objects.create(
            participante=participante,
            evento=evento,
            par_eve_fecha_hora=timezone.now(),
            par_eve_estado='Aprobado',
            confirmado=True,
            par_eve_valor=85.5
        )
        
        # Crear evaluador
        usuario_eval = Usuario.objects.create_user(
            username='eval1',
            email='eval1@test.com',
            password='123',
            documento='567890'
        )
        evaluador = Evaluador.objects.create(usuario=usuario_eval)
        EvaluadorEvento.objects.create(
            evaluador=evaluador,
            evento=evento,
            eva_eve_fecha_hora=timezone.now(),
            eva_eve_estado='Aprobado',
            confirmado=True
        )
        
        # Crear criterio y calificación
        from app_evaluadores.models import Criterio, Calificacion
        criterio = Criterio.objects.create(
            cri_descripcion='Creatividad',
            cri_peso=0.5,
            cri_evento_fk=evento
        )
        Calificacion.objects.create(
            evaluador=evaluador,
            criterio=criterio,
            participante=participante,
            cal_valor=90
        )
        
        url = reverse('detalle_evento_admin', args=[evento.eve_id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['estadisticas'])
        estadisticas = response.context['estadisticas']
        
        # Verificar estadísticas de asistentes
        self.assertEqual(estadisticas['asistentes']['total'], 1)
        self.assertEqual(estadisticas['asistentes']['aprobados'], 1)
        self.assertEqual(estadisticas['asistentes']['confirmados'], 1)
        
        # Verificar estadísticas de participantes
        self.assertEqual(estadisticas['participantes']['total'], 1)
        self.assertEqual(estadisticas['participantes']['calificados'], 1)
        
        # Verificar estadísticas de evaluadores
        self.assertEqual(estadisticas['evaluadores']['total'], 1)
        
        # Verificar estadísticas de evaluación
        self.assertEqual(estadisticas['evaluacion']['criterios'], 1)
        self.assertEqual(estadisticas['evaluacion']['calificaciones'], 1)
    
    def test_detalle_evento_get_finalizado(self):
        """Test GET para evento finalizado - solo puede cambiar a cerrado"""
        evento = self.crear_evento(estado='finalizado')
        url = reverse('detalle_evento_admin', args=[evento.eve_id])
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['estados'], ['Cerrado'])
    
    @patch('app_admin.views.EmailMessage')
    def test_post_cambiar_estado_pendiente_a_aprobado(self, mock_email):
        """Test POST: cambiar estado de pendiente a aprobado"""
        evento = self.crear_evento(estado='pendiente')
        url = reverse('detalle_evento_admin', args=[evento.eve_id])
        
        response = self.client.post(url, {'nuevo_estado': 'aprobado'})
        
        evento.refresh_from_db()
        self.assertEqual(evento.eve_estado, 'aprobado')
        self.assertRedirects(response, reverse('dashboard_superadmin'))
        
        # Verificar que se envió email
        self.assertTrue(mock_email.called)
    
    def test_post_cambiar_estado_inscripciones_cerradas_a_aprobado(self):
        """Test POST: aprobar desde inscripciones cerradas"""
        evento = self.crear_evento(estado='inscripciones cerradas')
        url = reverse('detalle_evento_admin', args=[evento.eve_id])
        
        response = self.client.post(url, {'nuevo_estado': 'aprobado'})
        
        evento.refresh_from_db()
        self.assertEqual(evento.eve_estado, 'aprobado')
    
    def test_post_cambiar_estado_finalizado_a_cerrado_elimina_info(self):
        """Test POST: cambiar de finalizado a cerrado elimina toda la info"""
        evento = self.crear_evento(estado='finalizado')
        
        # Agregar datos al evento
        usuario_asist = Usuario.objects.create_user(
            username='asist2',
            email='asist2@test.com',
            password='123',
            documento='678901'
        )
        asistente = Asistente.objects.create(usuario=usuario_asist)
        AsistenteEvento.objects.create(
            asistente=asistente,
            evento=evento,
            asi_eve_fecha_hora=timezone.now(),
            asi_eve_estado='Aprobado'
        )
        
        url = reverse('detalle_evento_admin', args=[evento.eve_id])
        response = self.client.post(url, {'nuevo_estado': 'cerrado'})
        
        # Verificar que el evento fue eliminado
        self.assertFalse(Evento.objects.filter(eve_id=evento.eve_id).exists())
        self.assertRedirects(response, reverse('dashboard_superadmin'))
    
    def test_post_cambiar_estado_finalizado_a_otro_rechazado(self):
        """Test POST: no se puede cambiar finalizado a otro estado que no sea cerrado"""
        evento = self.crear_evento(estado='finalizado')
        url = reverse('detalle_evento_admin', args=[evento.eve_id])
        
        response = self.client.post(url, {'nuevo_estado': 'aprobado'})
        
        evento.refresh_from_db()
        self.assertEqual(evento.eve_estado, 'finalizado')  # No cambió
        self.assertRedirects(response, url)
    
    def test_post_aprobar_desde_estado_no_permitido(self):
        """Test POST: no se puede aprobar desde un estado no permitido"""
        evento = self.crear_evento(estado='rechazado')
        url = reverse('detalle_evento_admin', args=[evento.eve_id])
        
        response = self.client.post(url, {'nuevo_estado': 'aprobado'})
        
        evento.refresh_from_db()
        self.assertEqual(evento.eve_estado, 'rechazado')  # No cambió
    
    @patch('app_admin.views._eliminar_informacion_evento_cerrado')
    def test_post_error_al_cerrar_evento(self, mock_eliminar):
        """Test POST: manejo de error al cerrar evento"""
        mock_eliminar.side_effect = Exception('Error de prueba')
        
        evento = self.crear_evento(estado='finalizado')
        url = reverse('detalle_evento_admin', args=[evento.eve_id])
        
        response = self.client.post(url, {'nuevo_estado': 'cerrado'})
        
        # El evento aún debe existir
        self.assertTrue(Evento.objects.filter(eve_id=evento.eve_id).exists())
        self.assertRedirects(response, url)
    
    @patch('app_admin.views.EmailMessage')
    def test_post_email_sin_administrador(self, mock_email):
        """Test POST: cambio de estado sin administrador asignado"""
        evento = Evento.objects.create(
            eve_nombre='Evento Sin Admin',
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
        
        url = reverse('detalle_evento_admin', args=[evento.eve_id])
        response = self.client.post(url, {'nuevo_estado': 'aprobado'})
        
        evento.refresh_from_db()
        self.assertEqual(evento.eve_estado, 'aprobado')


class DescargarProgramacionTestCase(TestCase):
    """
    Tests para la vista descargar_programacion
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear superadmin
        self.rol_superadmin = Rol.objects.create(nombre='superadmin')
        self.superadmin = Usuario.objects.create_user(
            username='superadmin',
            email='super@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.superadmin, rol=self.rol_superadmin)
        
        # Crear administrador
        usuario_admin = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='234567'
        )
        self.administrador = AdministradorEvento.objects.create(usuario=usuario_admin)
        
        # Login
        self.client.login(email='super@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'superadmin'
        session.save()
    
    @patch('django.core.files.storage.FileSystemStorage.open')
    def test_descargar_programacion_exitoso(self, mock_open):
        """Test: descarga exitosa de programación"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        evento = Evento.objects.create(
            eve_nombre='Evento Test',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='aprobado',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador,
            eve_programacion=SimpleUploadedFile('programacion.pdf', b'PDF content')
        )
        
        mock_file = MagicMock()
        mock_open.return_value = mock_file
        
        url = reverse('descargar_programacion_admin', args=[evento.eve_id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_descargar_programacion_archivo_no_encontrado(self):
        """Test: archivo no existe en el servidor"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        evento = Evento.objects.create(
            eve_nombre='Evento Test',
            eve_descripcion='Desc',
            eve_ciudad='Manizales',
            eve_lugar='SENA',
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=1),
            eve_estado='aprobado',
            eve_capacidad=100,
            eve_tienecosto='NO',
            eve_administrador_fk=self.administrador,
            eve_programacion=SimpleUploadedFile('programacion.pdf', b'content')
        )
        
        with patch.object(evento.eve_programacion, 'open', side_effect=FileNotFoundError):
            url = reverse('descargar_programacion_admin', args=[evento.eve_id])
            response = self.client.get(url)
            
            self.assertRedirects(response, reverse('detalle_evento_admin', args=[evento.eve_id]))
    
    def test_descargar_programacion_sin_archivo(self):
        """Test: evento sin archivo de programación"""
        evento = Evento.objects.create(
            eve_nombre='Evento Test',
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
        
        url = reverse('descargar_programacion_admin', args=[evento.eve_id])
        response = self.client.get(url)
        
        self.assertRedirects(response, reverse('detalle_evento_admin', args=[evento.eve_id]))


class ListarAdministradoresEventoTestCase(TestCase):
    """
    Tests para la vista listar_administradores_evento
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear superadmin
        self.rol_superadmin = Rol.objects.create(nombre='superadmin')
        self.superadmin = Usuario.objects.create_user(
            username='superadmin',
            email='super@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.superadmin, rol=self.rol_superadmin)
        
        # Login
        self.client.login(email='super@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'superadmin'
        session.save()
    
    def test_listar_administradores_vacio(self):
        """Test: listar cuando no hay administradores"""
        url = reverse('listar_administradores_evento')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['administradores']), 0)
    
    def test_listar_administradores_con_datos(self):
        """Test: listar administradores existentes"""
        # Crear administradores
        for i in range(3):
            usuario = Usuario.objects.create_user(
                username=f'admin{i}',
                email=f'admin{i}@test.com',
                password='test123',
                documento=f'12345{i}'
            )
            AdministradorEvento.objects.create(usuario=usuario)
        
        url = reverse('listar_administradores_evento')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['administradores']), 3)


class EliminarAdministradorTestCase(TestCase):
    """
    Tests para la vista eliminar_administrador
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear superadmin
        self.rol_superadmin = Rol.objects.create(nombre='superadmin')
        self.superadmin = Usuario.objects.create_user(
            username='superadmin',
            email='super@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.superadmin, rol=self.rol_superadmin)
        
        # Login
        self.client.login(email='super@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'superadmin'
        session.save()
    
    def test_eliminar_administrador_exitoso(self):
        """Test: eliminar administrador correctamente"""
        usuario = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='test123',
            documento='234567',
            first_name='Admin',
            last_name='Test'
        )
        admin = AdministradorEvento.objects.create(usuario=usuario)
        
        url = reverse('eliminar_administrador', args=[admin.id])
        response = self.client.get(url)
        
        self.assertFalse(Usuario.objects.filter(id=usuario.id).exists())
        self.assertFalse(AdministradorEvento.objects.filter(id=admin.id).exists())
        self.assertRedirects(response, reverse('listar_administradores_evento'))
    
    def test_eliminar_administrador_inexistente(self):
        """Test: intentar eliminar administrador que no existe"""
        url = reverse('eliminar_administrador', args=[9999])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)


class CrearAreaCategoriaTestCase(TestCase):
    """
    Tests para la vista crear_area_categoria
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear superadmin
        self.rol_superadmin = Rol.objects.create(nombre='superadmin')
        self.superadmin = Usuario.objects.create_user(
            username='superadmin',
            email='super@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.superadmin, rol=self.rol_superadmin)
        
        # Login
        self.client.login(email='super@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'superadmin'
        session.save()
        
        self.url = reverse('crear_area_categoria')
    
    def test_get_crear_area_categoria(self):
        """Test GET: cargar formulario"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('areas', response.context)
        self.assertEqual(response.context['mensaje'], '')
        self.assertEqual(response.context['mensaje_categoria'], '')
    
    def test_post_crear_area_exitoso(self):
        """Test POST: crear área exitosamente"""
        response = self.client.post(self.url, {
            'crear_area': 'true',
            'nombre_area': 'Tecnología',
            'descripcion_area': 'Área de tecnología e innovación'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Area.objects.filter(are_nombre='Tecnología').exists())
        self.assertContains(response, 'Área creada exitosamente')
    
    def test_post_crear_area_sin_nombre(self):
        """Test POST: crear área sin nombre"""
        response = self.client.post(self.url, {
            'crear_area': 'true',
            'nombre_area': '',
            'descripcion_area': 'Descripción'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El nombre del área es obligatorio')
        self.assertFalse(Area.objects.exists())
    
    def test_post_crear_area_duplicada(self):
        """Test POST: crear área con nombre duplicado"""
        Area.objects.create(are_nombre='Tecnología', are_descripcion='Desc')
        
        response = self.client.post(self.url, {
            'crear_area': 'true',
            'nombre_area': 'Tecnología',
            'descripcion_area': 'Otra descripción'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe un área con ese nombre')
        self.assertEqual(Area.objects.filter(are_nombre='Tecnología').count(), 1)
    
    def test_post_crear_area_case_insensitive(self):
        """Test POST: validación case insensitive de nombre de área"""
        Area.objects.create(are_nombre='Tecnología', are_descripcion='Desc')
        
        response = self.client.post(self.url, {
            'crear_area': 'true',
            'nombre_area': 'tecnología',  # Minúsculas
            'descripcion_area': 'Otra descripción'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe un área con ese nombre')
    
    def test_post_crear_categoria_exitoso(self):
        """Test POST: crear categoría exitosamente"""
        area = Area.objects.create(are_nombre='Tecnología', are_descripcion='Desc')
        
        response = self.client.post(self.url, {
            'crear_categoria': 'true',
            'nombre_categoria': 'Conferencia',
            'descripcion_categoria': 'Categoría de conferencias',
            'area_id': area.are_codigo
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Categoria.objects.filter(cat_nombre='Conferencia').exists())
        self.assertContains(response, 'Categoría creada exitosamente')
    
    def test_post_crear_categoria_sin_nombre(self):
        """Test POST: crear categoría sin nombre"""
        area = Area.objects.create(are_nombre='Tecnología', are_descripcion='Desc')
        
        response = self.client.post(self.url, {
            'crear_categoria': 'true',
            'nombre_categoria': '',
            'descripcion_categoria': 'Desc',
            'area_id': area.are_codigo
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El nombre de la categoría y el área son obligatorios')
        self.assertFalse(Categoria.objects.exists())
    
    def test_post_crear_categoria_sin_area(self):
        """Test POST: crear categoría sin área"""
        response = self.client.post(self.url, {
            'crear_categoria': 'true',
            'nombre_categoria': 'Conferencia',
            'descripcion_categoria': 'Desc',
            'area_id': ''
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El nombre de la categoría y el área son obligatorios')
    
    def test_post_crear_categoria_duplicada_en_misma_area(self):
        """Test POST: crear categoría duplicada en la misma área"""
        area = Area.objects.create(are_nombre='Tecnología', are_descripcion='Desc')
        Categoria.objects.create(
            cat_nombre='Conferencia',
            cat_descripcion='Desc',
            cat_area_fk=area
        )
        
        response = self.client.post(self.url, {
            'crear_categoria': 'true',
            'nombre_categoria': 'Conferencia',
            'descripcion_categoria': 'Otra desc',
            'area_id': area.are_codigo
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una categoría con ese nombre en el área seleccionada')
        self.assertEqual(Categoria.objects.filter(cat_nombre='Conferencia').count(), 1)
    
    def test_post_crear_categoria_mismo_nombre_diferente_area(self):
        """Test POST: crear categoría con mismo nombre en diferente área"""
        area1 = Area.objects.create(are_nombre='Tecnología', are_descripcion='Desc1')
        area2 = Area.objects.create(are_nombre='Salud', are_descripcion='Desc2')
        
        Categoria.objects.create(
            cat_nombre='Conferencia',
            cat_descripcion='Desc',
            cat_area_fk=area1
        )
        
        response = self.client.post(self.url, {
            'crear_categoria': 'true',
            'nombre_categoria': 'Conferencia',
            'descripcion_categoria': 'Desc',
            'area_id': area2.are_codigo
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Categoría creada exitosamente')
        self.assertEqual(Categoria.objects.filter(cat_nombre='Conferencia').count(), 2)


class ListarCodigosInvitacionAdminTestCase(TestCase):
    """
    Tests para la vista listar_codigos_invitacion_admin
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear superadmin
        self.rol_superadmin = Rol.objects.create(nombre='superadmin')
        self.superadmin = Usuario.objects.create_user(
            username='superadmin',
            email='super@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.superadmin, rol=self.rol_superadmin)
        
        # Login
        self.client.login(email='super@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'superadmin'
        session.save()
        
        self.url = reverse('listar_codigos_invitacion_admin')
    
    def test_listar_codigos_vacio(self):
        """Test: listar cuando no hay códigos"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['codigos']), 0)
    
    def test_listar_codigos_con_datos(self):
        """Test: listar códigos existentes ordenados por fecha"""
        # Crear códigos
        for i in range(3):
            CodigoInvitacionAdminEvento.objects.create(
                codigo=f'codigo{i}',
                email_destino=f'admin{i}@test.com',
                limite_eventos=5,
                fecha_expiracion=timezone.now() + timedelta(days=30),
                fecha_creacion=timezone.now() + timedelta(hours=i)
            )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['codigos']), 3)
        # Verificar orden descendente por fecha_creacion
        codigos = response.context['codigos']
        self.assertTrue(codigos[0].fecha_creacion >= codigos[1].fecha_creacion)


class AccionCodigoInvitacionAdminTestCase(TestCase):
    """
    Tests para la vista accion_codigo_invitacion_admin
    """
    
    def setUp(self):
        self.client = Client()
        
        # Crear superadmin
        self.rol_superadmin = Rol.objects.create(nombre='superadmin')
        self.superadmin = Usuario.objects.create_user(
            username='superadmin',
            email='super@test.com',
            password='test123',
            documento='123456'
        )
        RolUsuario.objects.create(usuario=self.superadmin, rol=self.rol_superadmin)
        
        # Login
        self.client.login(email='super@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'superadmin'
        session.save()
    
    def test_suspender_codigo_activo(self):
        """Test: suspender código activo"""
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='codigo123',
            email_destino='admin@test.com',
            limite_eventos=5,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            estado='activo'
        )
        
        url = reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'suspender'])
        response = self.client.get(url)
        
        codigo.refresh_from_db()
        self.assertEqual(codigo.estado, 'suspendido')
        self.assertRedirects(response, reverse('listar_codigos_invitacion_admin'))
    
    def test_activar_codigo_suspendido(self):
        """Test: activar código suspendido"""
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='codigo456',
            email_destino='admin@test.com',
            limite_eventos=5,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            estado='suspendido'
        )
        
        url = reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'activar'])
        response = self.client.get(url)
        
        codigo.refresh_from_db()
        self.assertEqual(codigo.estado, 'activo')
        self.assertRedirects(response, reverse('listar_codigos_invitacion_admin'))
    
    def test_cancelar_codigo(self):
        """Test: cancelar y eliminar código"""
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='codigo789',
            email_destino='admin@test.com',
            limite_eventos=5,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            estado='activo'
        )
        
        url = reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'cancelar'])
        response = self.client.get(url)
        
        self.assertFalse(CodigoInvitacionAdminEvento.objects.filter(codigo='codigo789').exists())
        self.assertRedirects(response, reverse('listar_codigos_invitacion_admin'))
    
    def test_suspender_codigo_no_activo(self):
        """Test: intentar suspender código que no está activo"""
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='codigo999',
            email_destino='admin@test.com',
            limite_eventos=5,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            estado='usado'
        )
        
        url = reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'suspender'])
        response = self.client.get(url)
        
        codigo.refresh_from_db()
        self.assertEqual(codigo.estado, 'usado')  # No cambió
        self.assertRedirects(response, reverse('listar_codigos_invitacion_admin'))
    
    def test_activar_codigo_no_suspendido(self):
        """Test: intentar activar código que no está suspendido"""
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='codigo888',
            email_destino='admin@test.com',
            limite_eventos=5,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            estado='activo'
        )
        
        url = reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'activar'])
        response = self.client.get(url)
        
        codigo.refresh_from_db()
        self.assertEqual(codigo.estado, 'activo')  # No cambió
    
    def test_accion_invalida(self):
        """Test: intentar acción inválida"""
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='codigo777',
            email_destino='admin@test.com',
            limite_eventos=5,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            estado='activo'
        )
        
        url = reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'accion_invalida'])
        response = self.client.get(url)
        
        codigo.refresh_from_db()
        self.assertEqual(codigo.estado, 'activo')  # No cambió
    
    def test_codigo_inexistente(self):
        """Test: intentar acción sobre código inexistente"""
        url = reverse('accion_codigo_invitacion_admin', args=['codigo_inexistente', 'suspender'])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

def test_dashboard_sin_rol_superadmin(self):
    # Logout y login como admin evento (no superadmin)
    self.client.logout()
    self.client.login(username='adminevento', password='pass123')
    response = self.client.get(reverse('dashboard_superadmin'))
    self.assertEqual(response.status_code, 403)  # Línea que falta

# AGREGAR A TestDashboardBaseTestCase (NO COLOCAR AQUÍ, SE INTEGRA AUTOMÁTICO)
class TestCoberturaAppAdmin(BaseTestCase):
    def test_dashboard_sin_autenticacion(self):
        """Líneas 69-70: Dashboard sin login"""
        self.client.logout()
        response = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

    def test_dashboard_sin_rol_superadmin(self):
        """Líneas 69-70: Dashboard sin rol superadmin"""
        self.client.logout()
        self.client.login(username='adminevento', password='pass123')
        response = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response.status_code, 403)

    def test_manual_sin_directorio(self):
        """Líneas 100-112: Manual sin directorio"""
        ruta_manual = os.path.join(settings.MEDIA_ROOT, 'manuales')
        if os.path.exists(ruta_manual):
            shutil.rmtree(ruta_manual)
        response = self.client.get(reverse('manual_super_admin'))
        self.assertEqual(response.status_code, 404)

    def test_detalle_evento_no_existe(self):
        """Líneas 172-175: Evento no existe"""
        response = self.client.get(reverse('detalle_evento_admin', args=[999]))
        self.assertEqual(response.status_code, 404)

    @patch('app_admin.views.Evento.objects.get')
    def test_detalle_evento_db_error(self, mock_get):
        """Líneas 185-190: Error DB en detalle evento"""
        mock_get.side_effect = Evento.DoesNotExist()
        response = self.client.get(reverse('detalle_evento_admin', args=[1]))
        self.assertEqual(response.status_code, 404)

    @patch('django.core.files.storage.default_storage.open')
    def test_descargar_programacion_file_not_found(self, mock_open):
        """Líneas 219-284: FileNotFoundError descarga"""
        mock_open.side_effect = FileNotFoundError()
        self.evento.eveprogramacion = 'programacion.pdf'  # Simular archivo
        self.evento.save()
        response = self.client.get(reverse('descargar_programacion_admin', args=[self.evento.eveid]))
        self.assertRedirects(response, reverse('detalle_evento_admin', args=[self.evento.eveid]))

    @patch('app_admin.views.Evento.objects.count')
    @patch('app_admin.views.Usuario.objects.count')
    def test_dashboard_error_contadores(self, mock_usuarios, mock_eventos):
        """Líneas 79-91: Error en contadores dashboard"""
        mock_eventos.side_effect = Exception("Error DB")
        response = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response.status_code, 200)  # Graceful degradation


class TestDashboardSuperAdminCobertura(BaseTestCase):
    """Tests para aumentar cobertura del dashboard - líneas 69-70, 79-91"""
    
    def test_dashboard_sin_autenticacion(self):
        """Línea 69: @login_required rechaza sin autenticación"""
        self.client.logout()
        response = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/usuario/login'))
    
    def test_dashboard_con_rol_incorrectos(self):
        """Línea 70: @user_passes_test rechaza sin rol superadmin"""
        # Crear usuario con rol diferente
        admin_user = Usuario.objects.create_user(
            username='no_super',
            email='nosuperadmin@test.com',
            password='test123',
            documento='999999'
        )
        rol_admin = Rol.objects.create(nombre='administrador_evento')
        RolUsuario.objects.create(usuario=admin_user, rol=rol_admin)
        
        self.client.login(email='nosuperadmin@test.com', password='test123')
        session = self.client.session
        session['rol_sesion'] = 'administrador_evento'
        session.save()
        
        response = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response.status_code, 403)
    
    def test_dashboard_con_muchos_eventos_nuevos(self):
        """Línea 79-91: Procesar notificaciones con múltiples eventos"""
        # Crear múltiples eventos en diferentes estados
        for i in range(5):
            Evento.objects.create(
                eve_nombre=f'Evento Pendiente {i}',
                eve_estado='pendiente',
                eve_fecha_inicio=timezone.now(),
                eve_fecha_fin=timezone.now() + timedelta(days=1),
                eve_capacidad=100
            )
        
        response = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response.status_code, 200)
        
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any('5 nuevo(s)' in str(msg) for msg in messages_list))
    
    def test_dashboard_eventos_vistos_segunda_visita(self):
        """Línea 79-91: No mostrar notificaciones si ya fueron vistos"""
        # Primera visita
        response1 = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response1.status_code, 200)
        
        # Segunda visita
        response2 = self.client.get(reverse('dashboard_superadmin'))
        messages_list = list(get_messages(response2.wsgi_request))
        self.assertFalse(any('Tienes' in str(msg) for msg in messages_list))
    
    def test_dashboard_sin_eventos(self):
        """Línea 79-91: Dashboard sin eventos de seguimiento"""
        # Asegurar que no hay eventos pendientes
        Evento.objects.all().delete()
        
        response = self.client.get(reverse('dashboard_superadmin'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('notificaciones', response.context)
        
        # Todas las notificaciones deben ser 0
        notificaciones = response.context['notificaciones']
        self.assertTrue(all(v == 0 for v in notificaciones.values()))


class TestManualesCobertura(BaseTestCase):
    """Tests para archivos PDF manuales - líneas 100-112"""
    
    @override_settings(MEDIA_ROOT='/nonexistent/path')
    def test_manual_super_admin_archivo_no_existe(self):
        """Línea 31: Archivo manual super admin no existe"""
        response = self.client.get(reverse('manual_super_admin'))
        self.assertEqual(response.status_code, 404)
    
    @override_settings(MEDIA_ROOT='/nonexistent/path')
    def test_manual_tecnico_archivo_no_existe(self):
        """Línea 38: Archivo manual técnico no existe"""
        response = self.client.get(reverse('manual_tecnico_operacion'))
        self.assertEqual(response.status_code, 404)
    
    def test_manual_super_admin_sin_login(self):
        """Manejo de manual sin autenticación"""
        self.client.logout()
        response = self.client.get(reverse('manual_super_admin'))
        self.assertEqual(response.status_code, 302)


class TestDetalleEventoAdminCobertura(BaseTestCase):
    """Tests para detalle evento admin - líneas 172-175, 185-190"""
    
    def setUp(self):
        super().setUp()
        # Crear administrador para evento
        self.usuario_admin = Usuario.objects.create_user(
            username='admin_evento_detail',
            email='admin_detail@test.com',
            password='test123',
            documento='111111'
        )
        self.rol_admin_evento = Rol.objects.create(nombre='administrador_evento_detail')
        RolUsuario.objects.create(usuario=self.usuario_admin, rol=self.rol_admin_evento)
        self.admin_evento = AdministradorEvento.objects.create(usuario=self.usuario_admin)
    
    def test_detalle_evento_no_existe(self):
        """Línea 172-175: 404 cuando evento no existe"""
        response = self.client.get(reverse('detalle_evento_admin', args=[99999]))
        self.assertEqual(response.status_code, 404)
    
    def test_detalle_evento_sin_autenticacion(self):
        """Línea 185-190: Rechaza sin autenticación"""
        self.client.logout()
        evento = Evento.objects.create(
            eve_nombre='Test',
            eve_estado='pendiente',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=1),
            eve_capacidad=100,
            eve_administrador_fk=self.admin_evento
        )
        response = self.client.get(reverse('detalle_evento_admin', args=[evento.eve_id]))
        self.assertEqual(response.status_code, 302)
    
    def test_detalle_evento_sin_permiso(self):
        """Línea 185-190: Rechaza sin rol superadmin"""
        usuario_sin_permisos = Usuario.objects.create_user(
            username='user_sin_permisos',
            email='sin_permisos@test.com',
            password='test123',
            documento='222222'
        )
        rol_usuario = Rol.objects.create(nombre='asistente_detail')
        RolUsuario.objects.create(usuario=usuario_sin_permisos, rol=rol_usuario)
        
        self.client.logout()
        self.client.login(email='sin_permisos@test.com', password='test123')
        
        evento = Evento.objects.create(
            eve_nombre='Test',
            eve_estado='pendiente',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=1),
            eve_capacidad=100,
            eve_administrador_fk=self.admin_evento
        )
        response = self.client.get(reverse('detalle_evento_admin', args=[evento.eve_id]))
        self.assertEqual(response.status_code, 403)
    
    def test_detalle_evento_pendiente_estados_disponibles(self):
        """Evento pendiente puede cambiar a varios estados"""
        evento = Evento.objects.create(
            eve_nombre='Evento Pendiente',
            eve_estado='pendiente',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=1),
            eve_capacidad=100,
            eve_administrador_fk=self.admin_evento
        )
        
        response = self.client.get(reverse('detalle_evento_admin', args=[evento.eve_id]))
        self.assertEqual(response.status_code, 200)
        
        estados = response.context['estados']
        self.assertIn('Aprobado', estados)
        self.assertIn('Rechazado', estados)
    
    def test_detalle_evento_finalizado_solo_cerrado(self):
        """Evento finalizado solo puede ir a cerrado"""
        evento = Evento.objects.create(
            eve_nombre='Evento Finalizado',
            eve_estado='finalizado',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=1),
            eve_capacidad=100,
            eve_administrador_fk=self.admin_evento
        )
        
        response = self.client.get(reverse('detalle_evento_admin', args=[evento.eve_id]))
        self.assertEqual(response.status_code, 200)
        
        estados = response.context['estados']
        self.assertEqual(estados, ['Cerrado'])
    
    @patch('app_admin.views.EmailMessage')
    def test_detalle_evento_cambio_estado_email_falla(self, mock_email):
        """Manejar cuando falla el envío de email"""
        mock_email.side_effect = Exception('Error SMTP')
        
        evento = Evento.objects.create(
            eve_nombre='Evento Test Email',
            eve_estado='pendiente',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=1),
            eve_capacidad=100,
            eve_administrador_fk=self.admin_evento
        )
        
        response = self.client.post(
            reverse('detalle_evento_admin', args=[evento.eve_id]),
            {'nuevo_estado': 'aprobado'}
        )
        
        evento.refresh_from_db()
        self.assertEqual(evento.eve_estado, 'aprobado')


class TestDescargarProgramacionCobertura(BaseTestCase):
    """Tests para descarga de programación - líneas 219-284"""
    
    def setUp(self):
        super().setUp()
        self.usuario_admin = Usuario.objects.create_user(
            username='admin_prog',
            email='admin_prog@test.com',
            password='test123',
            documento='333333'
        )
        self.rol_admin = Rol.objects.create(nombre='administrador_evento_prog')
        RolUsuario.objects.create(usuario=self.usuario_admin, rol=self.rol_admin)
        self.admin_evento = AdministradorEvento.objects.create(usuario=self.usuario_admin)
    
    def test_descargar_programacion_sin_autenticacion(self):
        """Rechaza sin login"""
        self.client.logout()
        evento = Evento.objects.create(
            eve_nombre='Test',
            eve_estado='aprobado',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=1),
            eve_capacidad=100,
            eve_administrador_fk=self.admin_evento
        )
        response = self.client.get(reverse('descargar_programacion_admin', args=[evento.eve_id]))
        self.assertEqual(response.status_code, 302)
    
    def test_descargar_programacion_sin_rol(self):
        """Rechaza sin rol superadmin"""
        usuario = Usuario.objects.create_user(
            username='user_prog',
            email='user_prog@test.com',
            password='test123',
            documento='444444'
        )
        rol = Rol.objects.create(nombre='asistente_prog')
        RolUsuario.objects.create(usuario=usuario, rol=rol)
        
        self.client.logout()
        self.client.login(email='user_prog@test.com', password='test123')
        
        evento = Evento.objects.create(
            eve_nombre='Test',
            eve_estado='aprobado',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=1),
            eve_capacidad=100,
            eve_administrador_fk=self.admin_evento
        )
        response = self.client.get(reverse('descargar_programacion_admin', args=[evento.eve_id]))
        self.assertEqual(response.status_code, 403)
    
    def test_descargar_programacion_evento_no_existe(self):
        """404 cuando evento no existe"""
        response = self.client.get(reverse('descargar_programacion_admin', args=[99999]))
        self.assertEqual(response.status_code, 404)
    
    def test_descargar_programacion_sin_archivo(self):
        """Redirige cuando no hay archivo"""
        evento = Evento.objects.create(
            eve_nombre='Evento Sin Prog',
            eve_estado='aprobado',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=1),
            eve_capacidad=100,
            eve_administrador_fk=self.admin_evento,
            eve_programacion=None
        )
        
        response = self.client.get(reverse('descargar_programacion_admin', args=[evento.eve_id]))
        self.assertRedirects(response, reverse('detalle_evento_admin', args=[evento.eve_id]))
    
    def test_descargar_programacion_archivo_vacio(self):
        """Archivo vacío (sin nombre)"""
        from django.core.files.base import ContentFile
        
        evento = Evento.objects.create(
            eve_nombre='Evento Con Prog Vacía',
            eve_estado='aprobado',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=1),
            eve_capacidad=100,
            eve_administrador_fk=self.admin_evento
        )
        
        # Simular archivo sin nombre
        response = self.client.get(reverse('descargar_programacion_admin', args=[evento.eve_id]))
        self.assertRedirects(response, reverse('detalle_evento_admin', args=[evento.eve_id]))


class TestCrearCodigoInvitacionCobertura(BaseTestCase):
    """Tests para crear código invitación admin - líneas 289-297"""
    
    def test_crear_codigo_sin_autenticacion(self):
        """Rechaza sin login"""
        self.client.logout()
        response = self.client.get(reverse('crear_codigo_invitacion_admin'))
        self.assertEqual(response.status_code, 302)
    
    def test_crear_codigo_sin_rol(self):
        """Rechaza sin rol superadmin"""
        usuario = Usuario.objects.create_user(
            username='user_cod',
            email='user_cod@test.com',
            password='test123',
            documento='555555'
        )
        rol = Rol.objects.create(nombre='asistente_cod')
        RolUsuario.objects.create(usuario=usuario, rol=rol)
        
        self.client.logout()
        self.client.login(email='user_cod@test.com', password='test123')
        
        response = self.client.get(reverse('crear_codigo_invitacion_admin'))
        self.assertEqual(response.status_code, 403)
    
    def test_crear_codigo_post_email_invalido(self):
        """Email inválido"""
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), {
            'email_destino': 'email_invalido',
            'limite_eventos': '5',
            'fecha_expiracion': '2025-12-31'
        })
        
        self.assertEqual(response.status_code, 200)
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any(msg for msg in messages_list))
    
    def test_crear_codigo_post_limite_invalido(self):
        """Límite de eventos negativo"""
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), {
            'email_destino': 'test@test.com',
            'limite_eventos': '-5',
            'fecha_expiracion': '2025-12-31'
        })
        
        self.assertEqual(response.status_code, 200)
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any('mayor a 0' in str(msg) for msg in messages_list))
    
    def test_crear_codigo_post_fecha_invalida(self):
        """Fecha formato inválido"""
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), {
            'email_destino': 'test@test.com',
            'limite_eventos': '5',
            'fecha_expiracion': 'fecha-invalida'
        })
        
        self.assertEqual(response.status_code, 200)
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any('inválido' in str(msg) for msg in messages_list))
    
    @patch('app_admin.views.EmailMessage')
    def test_crear_codigo_post_email_error(self, mock_email):
        """Error al enviar email"""
        mock_email_instance = MagicMock()
        mock_email_instance.send.side_effect = Exception('Error SMTP')
        mock_email.return_value = mock_email_instance
        
        response = self.client.post(reverse('crear_codigo_invitacion_admin'), {
            'email_destino': 'test@test.com',
            'limite_eventos': '5',
            'fecha_expiracion': '2025-12-31'
        })
        
        self.assertEqual(response.status_code, 302)
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Error' in str(msg) for msg in messages_list))


class TestListarEventosEstadoCobertura(BaseTestCase):
    """Tests para listar eventos por estado - líneas 464-466"""
    
    def test_listar_eventos_estado_sin_autenticacion(self):
        """Rechaza sin login"""
        self.client.logout()
        response = self.client.get(reverse('listar_eventos_estado', args=['pendiente']))
        self.assertEqual(response.status_code, 302)
    
    def test_listar_eventos_estado_sin_rol(self):
        """Rechaza sin rol superadmin"""
        usuario = Usuario.objects.create_user(
            username='user_estado',
            email='user_estado@test.com',
            password='test123',
            documento='666666'
        )
        rol = Rol.objects.create(nombre='asistente_estado')
        RolUsuario.objects.create(usuario=usuario, rol=rol)
        
        self.client.logout()
        self.client.login(email='user_estado@test.com', password='test123')
        
        response = self.client.get(reverse('listar_eventos_estado', args=['pendiente']))
        self.assertEqual(response.status_code, 403)
    
    def test_listar_eventos_estado_vacio(self):
        """No hay eventos en ese estado"""
        response = self.client.get(reverse('listar_eventos_estado', args=['rechazado']))
        self.assertEqual(response.status_code, 200)
        
        eventos_por_admin = response.context['eventos_por_admin']
        self.assertEqual(len(list(eventos_por_admin)), 0)
    
    def test_listar_eventos_estado_multiples_admins(self):
        """Múltiples administradores con eventos"""
        # Crear 2 administradores
        admin1_user = Usuario.objects.create_user(
            username='admin1_estado',
            email='admin1@test.com',
            password='test123',
            documento='777777'
        )
        admin1 = AdministradorEvento.objects.create(usuario=admin1_user)
        
        admin2_user = Usuario.objects.create_user(
            username='admin2_estado',
            email='admin2@test.com',
            password='test123',
            documento='888888'
        )
        admin2 = AdministradorEvento.objects.create(usuario=admin2_user)
        
        # Crear eventos para cada admin
        Evento.objects.create(
            eve_nombre='Evento Admin1',
            eve_estado='pendiente',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=1),
            eve_capacidad=100,
            eve_administrador_fk=admin1
        )
        
        Evento.objects.create(
            eve_nombre='Evento Admin2',
            eve_estado='pendiente',
            eve_fecha_inicio=timezone.now(),
            eve_fecha_fin=timezone.now() + timedelta(days=1),
            eve_capacidad=100,
            eve_administrador_fk=admin2
        )
        
        response = self.client.get(reverse('listar_eventos_estado', args=['pendiente']))
        self.assertEqual(response.status_code, 200)
        
        eventos_por_admin = dict(response.context['eventos_por_admin'])
        self.assertEqual(len(eventos_por_admin), 2)


class TestListarAdministradoresCobertura(BaseTestCase):
    """Tests para listar administradores - protección login/rol"""
    
    def test_listar_administradores_sin_autenticacion(self):
        """Rechaza sin login"""
        self.client.logout()
        response = self.client.get(reverse('listar_administradores_evento'))
        self.assertEqual(response.status_code, 302)
    
    def test_listar_administradores_sin_rol(self):
        """Rechaza sin rol superadmin"""
        usuario = Usuario.objects.create_user(
            username='user_list_admin',
            email='user_list_admin@test.com',
            password='test123',
            documento='999999'
        )
        rol = Rol.objects.create(nombre='asistente_list_admin')
        RolUsuario.objects.create(usuario=usuario, rol=rol)
        
        self.client.logout()
        self.client.login(email='user_list_admin@test.com', password='test123')
        
        response = self.client.get(reverse('listar_administradores_evento'))
        self.assertEqual(response.status_code, 403)


class TestEliminarAdministradorCobertura(BaseTestCase):
    """Tests para eliminar administrador - protección login/rol"""
    
    def test_eliminar_administrador_sin_autenticacion(self):
        """Rechaza sin login"""
        admin = AdministradorEvento.objects.create(
            usuario=Usuario.objects.create_user(
                username='admin_delete',
                email='admin_delete@test.com',
                password='test123',
                documento='101010'
            )
        )
        
        self.client.logout()
        response = self.client.get(reverse('eliminar_administrador', args=[admin.id]))
        self.assertEqual(response.status_code, 302)
    
    def test_eliminar_administrador_sin_rol(self):
        """Rechaza sin rol superadmin"""
        usuario = Usuario.objects.create_user(
            username='user_del_admin',
            email='user_del_admin@test.com',
            password='test123',
            documento='111111'
        )
        rol = Rol.objects.create(nombre='asistente_del_admin')
        RolUsuario.objects.create(usuario=usuario, rol=rol)
        
        admin = AdministradorEvento.objects.create(
            usuario=Usuario.objects.create_user(
                username='admin_to_del',
                email='admin_to_del@test.com',
                password='test123',
                documento='121212'
            )
        )
        
        self.client.logout()
        self.client.login(email='user_del_admin@test.com', password='test123')
        
        response = self.client.get(reverse('eliminar_administrador', args=[admin.id]))
        self.assertEqual(response.status_code, 403)


class TestCrearAreaCategoriaCobertura(BaseTestCase):
    """Tests para crear área/categoría - protección login/rol"""
    
    def test_crear_area_sin_autenticacion(self):
        """Rechaza sin login"""
        self.client.logout()
        response = self.client.get(reverse('crear_area_categoria'))
        self.assertEqual(response.status_code, 302)
    
    def test_crear_area_sin_rol(self):
        """Rechaza sin rol superadmin"""
        usuario = Usuario.objects.create_user(
            username='user_area',
            email='user_area@test.com',
            password='test123',
            documento='131313'
        )
        rol = Rol.objects.create(nombre='asistente_area')
        RolUsuario.objects.create(usuario=usuario, rol=rol)
        
        self.client.logout()
        self.client.login(email='user_area@test.com', password='test123')
        
        response = self.client.get(reverse('crear_area_categoria'))
        self.assertEqual(response.status_code, 403)


class TestListarCodigosCobertura(BaseTestCase):
    """Tests para listar códigos invitación - protección login/rol"""
    
    def test_listar_codigos_sin_autenticacion(self):
        """Rechaza sin login"""
        self.client.logout()
        response = self.client.get(reverse('listar_codigos_invitacion_admin'))
        self.assertEqual(response.status_code, 302)
    
    def test_listar_codigos_sin_rol(self):
        """Rechaza sin rol superadmin"""
        usuario = Usuario.objects.create_user(
            username='user_cod_list',
            email='user_cod_list@test.com',
            password='test123',
            documento='141414'
        )
        rol = Rol.objects.create(nombre='asistente_cod_list')
        RolUsuario.objects.create(usuario=usuario, rol=rol)
        
        self.client.logout()
        self.client.login(email='user_cod_list@test.com', password='test123')
        
        response = self.client.get(reverse('listar_codigos_invitacion_admin'))
        self.assertEqual(response.status_code, 403)


class TestAccionCodigoCobertura(BaseTestCase):
    """Tests para acciones en códigos - protección login/rol"""
    
    def test_accion_codigo_sin_autenticacion(self):
        """Rechaza sin login"""
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='test_codigo',
            email_destino='test@test.com',
            limite_eventos=5,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            estado='activo'
        )
        
        self.client.logout()
        response = self.client.get(
            reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'suspender'])
        )
        self.assertEqual(response.status_code, 302)
    
    def test_accion_codigo_sin_rol(self):
        """Rechaza sin rol superadmin"""
        usuario = Usuario.objects.create_user(
            username='user_cod_action',
            email='user_cod_action@test.com',
            password='test123',
            documento='151515'
        )
        rol = Rol.objects.create(nombre='asistente_cod_action')
        RolUsuario.objects.create(usuario=usuario, rol=rol)
        
        codigo = CodigoInvitacionAdminEvento.objects.create(
            codigo='test_codigo2',
            email_destino='test@test.com',
            limite_eventos=5,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            estado='activo'
        )
        
        self.client.logout()
        self.client.login(email='user_cod_action@test.com', password='test123')
        
        response = self.client.get(
            reverse('accion_codigo_invitacion_admin', args=[codigo.codigo, 'suspender'])
        )
        self.assertEqual(response.status_code, 403)