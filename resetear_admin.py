# ============================================================
# resetear_admin.py — Script de emergencia
# ============================================================
# Úsalo SOLO si perdiste acceso al panel de administrador.
#
# Cómo usarlo:
#   1. Asegúrate de que XAMPP esté corriendo
#   2. Abre la terminal en la carpeta del proyecto
#   3. Escribe: python resetear_admin.py
#   4. Sigue las instrucciones en pantalla
# ============================================================

import bcrypt
from dotenv import load_dotenv
from database import get_db

load_dotenv()


def resetear():
    print("=" * 55)
    print("🔐  RESETEAR CONTRASEÑA DE ADMINISTRADOR")
    print("=" * 55)

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Mostrar los admins disponibles
    cursor.execute("SELECT Aidadmin, nombre, usuario FROM administradores")
    admins = cursor.fetchall()

    if not admins:
        print("\n❌ No se encontraron administradores en la base de datos.")
        cursor.close()
        db.close()
        return

    print("\n👑 Administradores disponibles:")
    for admin in admins:
        print(f"   [{admin['Aidadmin']}] {admin['nombre']} — usuario: {admin['usuario']}")

    # Pedir cuál resetear
    print()
    usuario = input("Escribe el usuario del admin a resetear: ").strip()

    # Verificar que existe
    cursor.execute(
        "SELECT Aidadmin, nombre FROM administradores WHERE usuario = %s",
        (usuario,)
    )
    admin = cursor.fetchone()

    if not admin:
        print(f"\n❌ No se encontró ningún admin con usuario '{usuario}'")
        cursor.close()
        db.close()
        return

    print(f"\n✅ Admin encontrado: {admin['nombre']}")

    # Pedir nueva contraseña (dos veces para confirmar)
    while True:
        nueva = input("\nEscribe la nueva contraseña (mínimo 6 caracteres): ").strip()

        if len(nueva) < 6:
            print("❌ La contraseña debe tener al menos 6 caracteres. Intenta de nuevo.")
            continue

        confirmar = input("Confirma la nueva contraseña: ").strip()

        if nueva != confirmar:
            print("❌ Las contraseñas no coinciden. Intenta de nuevo.")
            continue

        break

    # Hashear y guardar
    nuevo_hash = bcrypt.hashpw(nueva.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    cursor.execute(
        "UPDATE administradores SET contrasena = %s WHERE usuario = %s",
        (nuevo_hash, usuario)
    )
    db.commit()
    cursor.close()
    db.close()

    print("\n" + "=" * 55)
    print(f"✅  Contraseña de '{usuario}' actualizada exitosamente.")
    print("   Ya puedes iniciar sesión con la nueva contraseña.")
    print("=" * 55)


if __name__ == "__main__":
    try:
        resetear()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Verifica que XAMPP esté corriendo y que el .env esté configurado.")
