# ============================================================
# migrar_contrasenas.py
# ============================================================
# Corre este archivo UNA SOLA VEZ para convertir todas las
# contraseñas de texto plano a bcrypt en tu base de datos.
#
# Cómo usarlo:
#   1. Asegúrate de que XAMPP esté corriendo
#   2. Abre tu terminal en la carpeta del proyecto
#   3. Escribe: python migrar_contrasenas.py
#   4. Listo — nunca necesitas correrlo de nuevo
# ============================================================

import bcrypt
from dotenv import load_dotenv
from database import get_db

load_dotenv()


def es_hash_bcrypt(texto):
    """
    Detecta si una contraseña ya fue hasheada con bcrypt.
    Los hashes de bcrypt siempre empiezan con $2b$ o $2a$
    Esto evita hashear dos veces si corres el script por error.
    """
    if not texto:
        return False
    return texto.startswith('$2b$') or texto.startswith('$2a$')


def hashear_contrasena(texto_plano):
    """
    Convierte una contraseña de texto plano a bcrypt.
    - encode()  → convierte el texto a bytes (bcrypt lo necesita)
    - gensalt() → genera una "sal" aleatoria para que dos
                  contraseñas iguales tengan hashes distintos
    - decode()  → convierte el resultado de bytes a texto
                  para guardarlo en MySQL
    """
    return bcrypt.hashpw(texto_plano.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def migrar():
    print("=" * 55)
    print("🔐  MIGRACIÓN DE CONTRASEÑAS A BCRYPT")
    print("=" * 55)

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # ── Migrar administradores ───────────────────────────────
    print("\n👑 Migrando administradores...")
    cursor.execute("SELECT Aidadmin, usuario, contrasena FROM administradores")
    admins = cursor.fetchall()

    migrados_admin = 0
    saltados_admin = 0

    for admin in admins:
        if es_hash_bcrypt(admin['contrasena']):
            print(f"   ⏭️  {admin['usuario']} — ya tiene bcrypt, saltando")
            saltados_admin += 1
            continue

        nuevo_hash = hashear_contrasena(admin['contrasena'])
        cursor.execute(
            "UPDATE administradores SET contrasena = %s WHERE Aidadmin = %s",
            (nuevo_hash, admin['Aidadmin'])
        )
        print(f"   ✅  {admin['usuario']} — migrado correctamente")
        migrados_admin += 1

    # ── Migrar doctores ──────────────────────────────────────
    print("\n👨‍⚕️ Migrando doctores...")
    cursor.execute("SELECT Diddoctor, usuario, contrasena FROM doctores")
    doctores = cursor.fetchall()

    migrados_doc = 0
    saltados_doc = 0

    for doctor in doctores:
        if es_hash_bcrypt(doctor['contrasena']):
            print(f"   ⏭️  {doctor['usuario']} — ya tiene bcrypt, saltando")
            saltados_doc += 1
            continue

        nuevo_hash = hashear_contrasena(doctor['contrasena'])
        cursor.execute(
            "UPDATE doctores SET contrasena = %s WHERE Diddoctor = %s",
            (nuevo_hash, doctor['Diddoctor'])
        )
        print(f"   ✅  {doctor['usuario']} — migrado correctamente")
        migrados_doc += 1

    # ── Guardar cambios ──────────────────────────────────────
    db.commit()
    cursor.close()
    db.close()

    # ── Resumen ──────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("📊  RESUMEN:")
    print(f"   Administradores migrados : {migrados_admin}")
    print(f"   Administradores saltados : {saltados_admin} (ya tenían bcrypt)")
    print(f"   Doctores migrados        : {migrados_doc}")
    print(f"   Doctores saltados        : {saltados_doc} (ya tenían bcrypt)")
    print("=" * 55)
    print("\n✅  Migración completada. Ya puedes arrancar app.py")
    print("⚠️  No vuelvas a correr este script — no es necesario.")
    print("=" * 55)


if __name__ == "__main__":
    try:
        migrar()
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        print("   Verifica que XAMPP esté corriendo y que el .env esté configurado.")
