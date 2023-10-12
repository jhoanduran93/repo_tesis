import mysql.connector
from mysql.connector import errorcode

# Configura la conexión a la base de datos
db_config = {
    "host": "bls0lv8b15zncfgr7bde-mysql.services.clever-cloud.com",  
    "user": "u2i1vzpgkh9zegil",
    "password": "RTfrtrFKOovCPvgjMi84",
    "database": "bls0lv8b15zncfgr7bde",  
}
try:
    # Intenta establecer la conexión
    conn = mysql.connector.connect(**db_config)
    print("Conexión a la base de datos exitosa.")
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Error: Acceso denegado. Verifica tus credenciales.")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Error: La base de datos no existe.")
    else:
        print(f"Error: {err}")