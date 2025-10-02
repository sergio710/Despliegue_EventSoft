# app_evaluadores/tests.py (Versión Final Corregida)

from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q # Importación necesaria para la lógica de búsqueda en procesar_registro_con_codigo

# ----------------------------------------------------
# 📌 Importaciones de Modelos CONFIRMADAS
# ----------------------------------------------------
from app_usuarios.models import Usuario, Rol, RolUsuario
from app_administradores.models import AdministradorEvento, CodigoInvitacionEvento
from app_eventos.models import Evento
from app_asistentes.models import Asistente
from app_participantes.models import Participante, ParticipanteEvento # Se requiere para la validación de duplicidad
from app_evaluadores.models import Evaluador, EvaluadorEvento

class PruebasPreinscripcionEvaluador(TestCase):

    def setUp(self):
        """Configuración inicial para las pruebas de registro de Evaluador."""
        self.client = Client()

        # 1. Crear Administrador y Evento
        self.admin_user = Usuario.objects.create_user(
            username='admin_evento', email='admin@test.com', password='password123', documento='222',
            first_name='Admin', last_name='Evento'
        )
        self.administrador_evento = AdministradorEvento.objects.create(usuario=self.admin_user)
        
        # 2. Crear roles necesarios
        self.rol_evaluador = Rol.objects.create(nombre='evaluador', descripcion='Rol para evaluadores')
        self.rol_asistente = Rol.objects.create(nombre='asistente', descripcion='Rol para asistentes')
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_evaluador) # Darle un rol para evitar fallos de lógica si se usa
        RolUsuario.objects.create(usuario=self.admin_user, rol=self.rol_asistente)

        # 3. Crear un evento de prueba
        self.evento = Evento.objects.create(
            eve_nombre="Congreso de Ingeniería de Software 2025",
            eve_descripcion="Evento de prueba para evaluadores",
            eve_ciudad="Manizales",
            eve_lugar="Campus La Nubia",
            eve_fecha_inicio=timezone.now().date(),
            eve_fecha_fin=timezone.now().date() + timedelta(days=2),
            eve_estado="Aprobado", 
            eve_capacidad=100,
            eve_tienecosto="No",
            eve_administrador_fk=self.administrador_evento
        )
        
        # 4. Crear CÓDIGO DE INVITACIÓN BASE para Evaluador
        self.codigo_valido = CodigoInvitacionEvento.objects.create(
            codigo='EVALTEST123',
            evento=self.evento,
            tipo='evaluador',
            email_destino='temp@code.com',
            estado='activo',
            administrador_creador=self.administrador_evento
        )
        
        # 5. URL de prueba CORREGIDA: Se debe probar la vista que maneja el código de invitación
        self.url_preinscripcion_base = reverse('registro_con_codigo', args=[self.codigo_valido.codigo])

        # 6. Archivo mock
        self.documento_mock = SimpleUploadedFile(
            "cv_evaluador.pdf", 
            b"Contenido del CV en bytes.", 
            content_type="application/pdf"
        )
        
        # 7. Datos base válidos ajustados a los nombres de campos en la vista 'procesar_registro_con_codigo'
        self.datos_validos_nuevo_usuario = {
            'eva_nombres': 'Juan', # Mapea a first_name
            'eva_apellidos': 'Perez', # Mapea a last_name
            'eva_id': '123456789', # Mapea a documento
            'eva_telefono': '3001234567',
            'documentacion': self.documento_mock, # Mapea a 'archivo'
            'codigo': self.codigo_valido.codigo, # Necesario para la redirección en caso de error
        }

    # ====================================================================
    # ✅ CASOS DE PRUEBA POSITIVOS
    # ====================================================================

    def test_registro_exitoso_nuevo_evaluador(self):
        """CP-EVAL-30.1: Prueba el registro exitoso de un VISITANTE (nuevo usuario)."""
        
        # 1. Crear un nuevo código con un email único
        codigo_nuevo = CodigoInvitacionEvento.objects.create(
            codigo='NUEVOREG', evento=self.evento, tipo='evaluador', 
            email_destino='nuevo.evaluador@test.com', estado='activo',
            administrador_creador=self.administrador_evento
        )
        
        datos_formulario = self.datos_validos_nuevo_usuario.copy()
        datos_formulario['codigo'] = codigo_nuevo.codigo
        
        # 2. Enviar POST a la URL específica del código
        url = reverse('registro_con_codigo', args=[codigo_nuevo.codigo])
        response = self.client.post(url, data=datos_formulario, follow=True) # Usar follow=True para obtener el 200 de la página final

        # 3. Verificar el resultado (Debe redirigir al listado de eventos con éxito)
        self.assertEqual(response.status_code, 200, "Debe redirigir exitosamente a 'ver_eventos' (200 después de follow).")
        self.assertContains(response, f"Te has registrado exitosamente como evaluador en el evento {self.evento.eve_nombre}", status_code=200)
        
        # 4. Verificar la creación de los objetos (¡CORRECCIÓN! El error estaba en no verificar la existencia del Usuario)
        self.assertTrue(Usuario.objects.filter(email='nuevo.evaluador@test.com').exists(), "El Usuario debe ser creado.")
        nuevo_usuario = Usuario.objects.get(email='nuevo.evaluador@test.com')
        self.assertTrue(Evaluador.objects.filter(usuario=nuevo_usuario).exists(), "El perfil Evaluador debe ser creado.")
        self.assertTrue(EvaluadorEvento.objects.filter(
            evaluador__usuario=nuevo_usuario, 
            evento=self.evento
        ).exists(), "El registro EvaluadorEvento debe ser creado.")
        self.assertEqual(CodigoInvitacionEvento.objects.get(codigo='NUEVOREG').estado, 'usado', "El código debe estar marcado como usado.")


    def test_postulacion_usuario_existente_como_evaluador(self):
        """CP-EVAL-30.2: Prueba la postulación de un usuario ya existente (ej: Asistente) como Evaluador."""
        
        # 1. Crear un usuario existente (Asistente)
        usuario_existente = Usuario.objects.create_user(
            username='asistente_interesado', email='asistente@test.com', password='password123', 
            documento='999999', first_name='Asistente', last_name='Test'
        )
        RolUsuario.objects.create(usuario=usuario_existente, rol=self.rol_asistente)
        Asistente.objects.create(usuario=usuario_existente)

        # 2. Crear código de invitación con el email del existente
        codigo_asistente = CodigoInvitacionEvento.objects.create(
            codigo='ASISTENTE', evento=self.evento, tipo='evaluador', 
            email_destino='asistente@test.com', estado='activo',
            administrador_creador=self.administrador_evento
        )
        
        # 3. Datos de postulación (deben coincidir con los datos del usuario existente para pasar la validación)
        datos_postulacion = {
            'eva_nombres': 'Asistente',
            'eva_apellidos': 'Test',
            'eva_id': '999999',
            'eva_telefono': '3001234567',
            'documentacion': self.documento_mock,
            'codigo': codigo_asistente.codigo,
        }
        
        # 4. Enviar la solicitud POST
        url = reverse('registro_con_codigo', args=[codigo_asistente.codigo])
        response = self.client.post(url, data=datos_postulacion, follow=True)

        # 5. Verificar el resultado
        self.assertEqual(response.status_code, 200, "Debe redirigir a una página de éxito (200).")
        
        # 6. Verificar la creación del perfil Evaluador (¡CORREGIDO!)
        usuario_verificar = Usuario.objects.get(email='asistente@test.com')
        # La vista usa get_or_create, lo que resuelve el error original.
        self.assertTrue(Evaluador.objects.filter(usuario=usuario_verificar).exists(), "Se debe crear el perfil Evaluador para el usuario existente.")
        
        self.assertTrue(EvaluadorEvento.objects.filter(
            evaluador__usuario=usuario_verificar, evento=self.evento
        ).exists(), "Se debe crear la inscripción EvaluadorEvento.")
        
        # 7. Verificar que NO se creó un nuevo usuario
        self.assertEqual(Usuario.objects.filter(email='asistente@test.com').count(), 1, "No se debe crear un usuario duplicado.")

    # ====================================================================
    # ❌ CASOS DE PRUEBA NEGATIVOS (FALLOS DE REDIRECCIÓN Y LÓGICA)
    # ====================================================================

    def test_registro_falla_por_datos_incompletos(self):
        """CP-EVAL-30.3: Prueba el fallo por campos obligatorios vacíos."""
        
        # Crear código de invitación para esta prueba
        codigo_incompleto = CodigoInvitacionEvento.objects.create(
            codigo='INCOMPLETO', evento=self.evento, tipo='evaluador', 
            email_destino='incompleto@test.com', estado='activo',
            administrador_creador=self.administrador_evento
        )
        
        # Datos incompletos (falta 'eva_id' que se mapea a 'documento')
        datos_formulario_incompletos = {
            'eva_nombres': 'Ana',
            'eva_apellidos': 'Gomez',
            # 'eva_id': '' -> Campo clave vacío
            'eva_telefono': '3001234567',
            'documentacion': self.documento_mock,
            'codigo': codigo_incompleto.codigo,
        }

        # La vista, al fallar la validación, hace: return redirect('registro_con_codigo', codigo=...)
        url = reverse('registro_con_codigo', args=[codigo_incompleto.codigo])
        response = self.client.post(url, data=datos_formulario_incompletos)
        
        # 1. Verificar el resultado (¡CORREGIDO! El error original esperaba 200, pero la vista devuelve 302)
        self.assertEqual(response.status_code, 302, "Debe redirigir (302) de vuelta al formulario para mostrar errores.")
        
        # 2. Verificar que no se creó ningún usuario
        self.assertFalse(Usuario.objects.filter(first_name='Ana').exists(), "No se debe crear ningún registro de usuario.")

    def test_registro_falla_por_email_duplicado(self):
        """CP-EVAL-30.4: Prueba el fallo por email duplicado con datos no coincidentes."""
        
        # 1. Crear previamente un usuario
        Usuario.objects.create_user(
            username='usuarioexistente', 
            email='usuario.existente@test.com', 
            password='password123', 
            documento='987654',
            first_name='Pedro',
            last_name='Ramirez'
        )
        
        # 2. Crear código de invitación con el email duplicado
        codigo_duplicado = CodigoInvitacionEvento.objects.create(
            codigo='DUPLICADO', evento=self.evento, tipo='evaluador', 
            email_destino='usuario.existente@test.com', estado='activo',
            administrador_creador=self.administrador_evento
        )

        # 3. Intentar registrar un nuevo usuario con datos *no coincidentes* (ej: nombre diferente)
        datos_formulario_duplicado = {
            'eva_nombres': 'Juan', # Nombre diferente
            'eva_apellidos': 'Duplicado', 
            'eva_id': '987654',
            'eva_telefono': '3001234567',
            'documentacion': self.documento_mock,
            'codigo': codigo_duplicado.codigo,
        }
        
        # La vista detecta: Usuario encontrado, pero datos (nombre/apellido) no coinciden.
        url = reverse('registro_con_codigo', args=[codigo_duplicado.codigo])
        response = self.client.post(url, data=datos_formulario_duplicado)

        # 4. Verificar el resultado (¡CORREGIDO! El error original esperaba 200, pero la vista devuelve 302)
        self.assertEqual(response.status_code, 302, "Debe redirigir (302) de vuelta al formulario para mostrar el error de inconsistencia de datos.")
        
        # 5. Asegurarse que solo existe el usuario original
        self.assertEqual(Usuario.objects.filter(email='usuario.existente@test.com').count(), 1, "Solo debe existir un registro de usuario con ese email.")


    def test_preinscripcion_duplicada_al_mismo_evento(self):
        """CP-EVAL-30.5: Prueba que un usuario no pueda inscribirse dos veces al mismo evento (rol evaluador)."""
        
        # 1. Crear un usuario y preinscribirlo como evaluador
        evaluador_user = Usuario.objects.create_user(
            username='evaluadorinscrito', email='evaluador.inscrito@test.com', password='password123', 
            documento='777888', first_name='Evaluador', last_name='Inscrito'
        )
        RolUsuario.objects.create(usuario=evaluador_user, rol=self.rol_evaluador)
        evaluador_perfil = Evaluador.objects.create(usuario=evaluador_user)
        EvaluadorEvento.objects.create(
            evaluador=evaluador_perfil,
            evento=self.evento,
            eva_eve_estado='Pendiente',
            eva_eve_fecha_hora=timezone.now(),
            confirmado=True # Ya está confirmado
        )
        
        # 2. Crear un código de invitación para intentar la segunda inscripción
        codigo_existente = CodigoInvitacionEvento.objects.create(
            codigo='EXISTENTE', evento=self.evento, tipo='evaluador', 
            email_destino='evaluador.inscrito@test.com', estado='activo',
            administrador_creador=self.administrador_evento
        )
        
        # 3. Datos del formulario (deben coincidir con el usuario existente)
        datos_formulario = {
            'eva_nombres': 'Evaluador',
            'eva_apellidos': 'Inscrito',
            'eva_id': '777888',
            'eva_telefono': '3001234567',
            'documentacion': self.documento_mock,
            'codigo': codigo_existente.codigo,
        }
        
        # 4. Enviar el POST (intento de duplicidad)
        url = reverse('registro_con_codigo', args=[codigo_existente.codigo])
        response = self.client.post(url, data=datos_formulario, follow=True)

        # 5. Verificar el resultado (¡CORREGIDO! El error original esperaba 200 en la primera respuesta,
        # pero la vista redirige a 'ver_eventos', resultando en 200 después de follow)
        self.assertEqual(response.status_code, 200, "Debe redirigir a 'ver_eventos' (200 después de follow) con el mensaje de 'Ya estás inscrito'.")
        
        # 6. Verificar el mensaje de error o info en la página de destino
        self.assertContains(response, "Ya estás inscrito como evaluador en este evento.", status_code=200)
        
        # 7. Verificar que NO se creó un EvaluadorEvento duplicado
        self.assertEqual(EvaluadorEvento.objects.filter(
            evaluador=evaluador_perfil, evento=self.evento
        ).count(), 1, "Solo debe existir un registro EvaluadorEvento para el par usuario/evento.")