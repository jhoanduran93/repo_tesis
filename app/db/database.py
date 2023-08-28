import mysql.connector
from mysql.connector import errorcode

# Configura la conexión a la base de datos
db_config = {
    "host": "localhost",  
    "user": "root",
    "password": "123456789",
    "database": "mydb",  
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