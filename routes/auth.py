# ============================================================
# routes/auth.py — Protección de endpoints con sesiones
# ============================================================
# Este archivo hace DOS cosas:
#
# 1. Define "decoradores" que protegen rutas.
#    Un decorador es como un guardia que se pone ANTES de
#    ejecutar cualquier función. Si no estás logueado, regresa
#    un error 401 antes de hacer cualquier cosa.
#
# 2. Provee funciones helper para manejar la sesión activa.
#
# Uso en cualquier ruta:
#   from routes.auth import requiere_login, requiere_admin
#
#   @app.route('/api/admin/stats')
#   @requiere_admin          ← solo admins pueden entrar
#   def admin_stats():
#       ...
#
#   @app.route('/api/citas')
#   @requiere_login          ← cualquier usuario logueado
#   def get_citas():
#       ...
# ============================================================

from functools import wraps
from flask import session, jsonify


def requiere_login(f):
    """
    Decorador que verifica que el usuario haya iniciado sesión.
    Si no hay sesión activa, devuelve error 401 (No autorizado).

    Funciona en cualquier ruta de doctor o admin.
    """
    @wraps(f)  # conserva el nombre original de la función
    def verificar(*args, **kwargs):
        if 'user_id' not in session:
            # El usuario no está logueado
            return jsonify({
                'success': False,
                'error': 'No autorizado. Por favor inicia sesión.',
                'redirect': '/'
            }), 401
        # Está logueado → ejecutar la función original
        return f(*args, **kwargs)
    return verificar


def requiere_admin(f):
    """
    Decorador que verifica que el usuario sea administrador.
    Si es doctor (no admin), devuelve error 403 (Acceso denegado).

    Úsalo en rutas que solo el admin debe poder usar, como:
    - /api/admin/stats
    - /api/delete-user
    - /api/ajustar-puntos
    - /api/entregar-resultado
    """
    @wraps(f)
    def verificar(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'error': 'No autorizado. Por favor inicia sesión.',
                'redirect': '/'
            }), 401

        if session.get('tipo') != 'admin':
            # Está logueado pero es doctor, no admin
            return jsonify({
                'success': False,
                'error': 'Acceso denegado. Se requieren permisos de administrador.'
            }), 403

        return f(*args, **kwargs)
    return verificar


def get_usuario_actual():
    """
    Devuelve los datos del usuario logueado actualmente.
    Útil si necesitas saber quién está haciendo una acción.

    Ejemplo:
        usuario = get_usuario_actual()
        print(usuario['user_id'])   # 'A001' o 'D001'
        print(usuario['tipo'])      # 'admin' o 'doctor'
        print(usuario['nombre'])    # 'Administrador' o 'dr.rodriguez'
    """
    return {
        'user_id': session.get('user_id'),
        'tipo':    session.get('tipo'),
        'nombre':  session.get('nombre')
    }
