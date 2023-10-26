import os
import sys
import mysql.connector
from datetime import date, datetime, timedelta
from typing import List, Union
import logging 
import socketio

from fastapi import FastAPI, HTTPException, status, WebSocket, Depends, HTTPException,  WebSocketDisconnect, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.encoders import jsonable_encoder
import jwt
import openai

from mysql.connector import errorcode

from app.db.database import conn
from app.models.user import User
from app.db.database import reconnect_to_database
from app.models.conversation import Conversation
from app.models.loginRequest import  LoginRequest
from app.models.message import Message
from app.security import Security, create_access_token, decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from dotenv import load_dotenv



sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI()


origins = [
    "http://localhost:3000",
    "https://tu-app-react-en-produccion.com",
     "https://famous-fairy-a237ea.netlify.app",
    # Otros orígenes permitidos
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

# Configura tu clave API de GPT-3
#openai.api_key = Security.GPT3_API_KEY

# Obtener la clave de API
#api_key = os.getenv("GPT3_API_KEY")

# Asignar la clave de API a OpenAI
#openai.api_key = api_key

openai.api_key = os.getenv("GPT3_API_KEY")

# Crea una instancia de socket.io
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
app.mount("/chatbot", socketio.ASGIApp(sio))

@app.websocket("/chatbot")
async def chatbot_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        await websocket.send_text("¡Bienvenido! Puedes comenzar a hacer preguntas!")

        # Configurar el sistema de registro
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)

        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Mensaje del cliente: {data}")

                # Verificar si el mensaje del cliente no está vacío
                if not data.strip():
                    await websocket.send_text("Por favor, ingresa una pregunta válida.")
                    continue  # Saltar al siguiente ciclo

                try:
                    # Usa GPT-3 para generar una respuesta
                    response = openai.Completion.create(
                        engine="text-davinci-002",
                        prompt=f"Responder a la siguiente pregunta: {data}",
                        max_tokens=400  # Cantidad de caracteres
                    )

                    # Extrae la respuesta generada por GPT-3
                    answer = response.choices[0].text

                    logger.debug(f"Respuesta al cliente: {answer}")
                    await websocket.send_text(answer)

                except Exception as e:
                    await websocket.send_text(f"Error en la generación de respuesta: {str(e)}")
            except Exception as e:
                await websocket.send_text(f"Error inesperado: {str(e)}")
    except Exception as e:
        await websocket.send_text(f"Error inesperado: {str(e)}")
        
@app.post("/create_user", status_code=status.HTTP_201_CREATED, response_model=User, tags=["user"])
async def create_user(user: User):
    """
    Ruta para crear un nuevo usuario en la base de datos.

    Permite a los usuarios registrar una nueva cuenta proporcionando su nombre, correo electrónico y contraseña.

    Args:
        user (User): Datos del usuario a registrar.

    Returns:
        User: El usuario registrado.
    """
    cursor = conn.cursor()
    try:
        # Inserta el nuevo usuario en la base de datos
        query = "INSERT INTO user (name, email, password) VALUES (%s, %s, %s)"
        cursor.execute(query, (user.name, user.email, user.password))
        conn.commit()
        return user
    except mysql.connector.Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            #manejo de un error (entrada duplicada)
            raise HTTPException(status_code=400, detail="El correo electrónico ya está registradoo")
        else:
            # Manejo genérico de otros errores
            raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    finally:
        cursor.close()
        
@app.get("/get_user", status_code=status.HTTP_200_OK, response_model=User, tags=["user"])
async def get_user_by_email(email: str):
    """
    Obtener información de un usuario por su correo electrónico.

    Args:
        email (str): El correo electrónico del usuario a buscar.

    Returns:
        dict: La información del usuario encontrado.

    Raises:
        HTTPException 404: Si el usuario no se encuentra.
        HTTPException 500: Si hay un error en el servidor al obtener el usuario.
    """
    cursor = conn.cursor()
    try:
        # Consulta el usuario por correo electrónico en la base de datos
        query = "SELECT * FROM user WHERE email = %s"
        cursor.execute(query, (email,))
        user_data = cursor.fetchone()
        if not user_data:
            raise HTTPException(status_code=404, detail=f"Usuario con correo electrónico {email} no encontrado")
        
        # Crear una instancia de User con los datos obtenidos de la base de datos
        user = User(iduser=user_data[0], name=user_data[1], email=user_data[2], password=user_data[3])
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el usuario {str(e)}")
    finally:
        cursor.close()

@app.delete("/delete_user/{user_email}", status_code=status.HTTP_201_CREATED, response_model=User, tags=["user"])
async def delete_user(user_email: str = Path(..., description="Email del usuario")):
    """
    Elimina un usuario por su correo electrónico.

    Permite eliminar un usuario existente proporcionando su correo electrónico.
    """
    cursor = conn.cursor()
    try:
        # Elimina el usuario por correo electrónico en la base de datos
        query = "DELETE FROM user WHERE email = %s"
        cursor.execute(query, (user_email,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return {"message": "Usuario eliminado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.put("/update_user/{user_email}", status_code=status.HTTP_201_CREATED, response_model=User, tags=["user"])
async def update_user(user_email: str, updated_user: User):
    """
    Actualiza la información de un usuario por su correo electrónico.

    Permite actualizar la información de un usuario existente proporcionando su correo electrónico y los datos actualizados.

    Args:
        user_email (str): El correo electrónico del usuario a actualizar.

    Returns:
        User: El usuario actualizado.

    Raises:
        HTTPException: Si el usuario no se encuentra.
    """
    cursor = conn.cursor()
    try:
        # Actualiza el usuario por correo electrónico en la base de datos
        query = "UPDATE user SET name = %s, email = %s, password = %s WHERE email = %s"
        cursor.execute(query, (updated_user.name, updated_user.email, updated_user.password, user_email))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return updated_user
    except Exception as e:
        raise HTTPException(status_code=500, detail= "Usuario no encontrado")
    finally:
        cursor.close()

# Endpoint para crear una conversación
@app.post("/create_conversation", status_code=201, response_model=Conversation, tags=["conversation"])
async def create_conversation(email: str, type_conversation: str):
    """
    Crea una nueva conversación para un usuario.

    Permite a un usuario iniciar una nueva conversación y devuelve detalles de la conversación creada.

    :param email: Correo electrónico del usuario.
    :param type_conversation: Tipo de conversación.
    :return: Detalles de la conversación creada.
    """
    cursor = conn.cursor()

    try:
        # Obtener el ID del usuario usando el correo electrónico
        query_user_id = "SELECT iduser FROM user WHERE email = %s"
        cursor.execute(query_user_id, (email,))
        user_id = cursor.fetchone()

        if not user_id:
            raise HTTPException(status_code=404, detail=f"Usuario con correo electrónico {email} no encontrado")

        user_id = user_id[0]

        # Insertar una nueva conversación en la base de datos
        today = date.today()
        query = "INSERT INTO conversation (star_date, end_date, iduser, type_conversation) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (today, today, user_id, type_conversation))
        conn.commit()

        # Obtener el ID de la conversación recién creada
        conversation_id = cursor.lastrowid

        # Construir y devolver una instancia del modelo Conversation con los datos relevantes
        new_conversation = Conversation(
            idconversation=conversation_id,
            star_date=today,
            end_date=today,
            iduser=user_id,
            type_conversation=type_conversation
        )
        return new_conversation

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

    finally:
        cursor.close()
        

# Endpoint para ver conversaciónes de usuario
@app.get("/get_conversations/{email}", response_model=List[Conversation], tags=["conversation"])
async def get_conversations(email: str):
    """
    Obtiene todas las conversaciones de un usuario.

    :param email: Correo electrónico del usuario.
    :return: Lista de conversaciones del usuario.
    """
    cursor = conn.cursor()

    try:
        # Obtener el ID del usuario usando el correo electrónico
        query_user_id = "SELECT iduser FROM user WHERE email = %s"
        cursor.execute(query_user_id, (email,))
        user_id = cursor.fetchone()

        if not user_id:
            raise HTTPException(status_code=404, detail=f"Usuario con correo electrónico {email} no encontrado")

        user_id = user_id[0]

        # Obtener todas las conversaciones del usuario
        query_conversations = "SELECT idconversation, star_date, end_date, iduser, type_conversation FROM conversation WHERE iduser = %s"
        cursor.execute(query_conversations, (user_id,))
        conversations = cursor.fetchall()

        # Construir una lista de instancias del modelo Conversation con los datos relevantes
        conversation_list = [
            Conversation(idconversation=conv[0], star_date=conv[1], end_date=conv[2], iduser=conv[3], type_conversation=conv[4])
            for conv in conversations
        ]

        return conversation_list

    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    finally:
        cursor.close()

# Endpoint para ver enviar msj 
@app.post("/send_message", status_code=status.HTTP_201_CREATED, response_model=Message, tags=["message"])
async def send_message(idconversation: int, points: int):
    """
    Envía un mensaje en una conversación existente y devuelve detalles del mensaje creado.

    :param idconversation: ID de la conversación en la que se enviará el mensaje.
    :param points: Puntos del mensaje.
    :return: Detalles del mensaje creado.
    """
    cursor = conn.cursor()

    try:
        # Verificar si la conversación existe
        query_conversation = "SELECT idconversation FROM conversation WHERE idconversation = %s"
        cursor.execute(query_conversation, (idconversation,))
        existing_conversation = cursor.fetchone()

        if not existing_conversation:
            raise HTTPException(status_code=404, detail=f"Conversación con ID {idconversation} no encontrada")

        # Insertar un nuevo mensaje en la base de datos
        current_time = datetime.now().time()
        query = "INSERT INTO message (points, hour, idconversation) VALUES (%s, %s, %s)"
        cursor.execute(query, (points, current_time, idconversation))
        conn.commit()

        # Obtener el ID del mensaje recién creado
        message_id = cursor.lastrowid

        # Construir y devolver una instancia del modelo Message con los datos relevantes
        new_message = Message(idmessage=message_id, points=points, hour=current_time, idconversation=idconversation)
        return new_message

    except Exception as e:
        print(e)  # Imprimir la excepción completa
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    finally:
        cursor.close()


@app.post("/login", status_code=status.HTTP_200_OK, tags=["Login"])
async def login(request: LoginRequest):
    """
    Inicia sesión de usuario.

    Permite a un usuario iniciar sesión proporcionando su correo electrónico y contraseña.
    """
    if not conn.is_connected():
       # Si la conexión no está activa, lanzar un error 500
        conn = reconnect_to_database()
    
    
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM user WHERE email = %s AND password = %s"
        cursor.execute(query, (request.email, request.password))
        user_data = cursor.fetchone()
        if not user_data:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        
        # Crea un token JWT
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"user_id": user_data[0]}, expires_delta=access_token_expires)
        
        # Retorna el token JWT junto con un mensaje de éxito
        return {"message": "Inicio de sesión exitoso", "access_token": access_token}
    except Exception as e:
       
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        

@app.post("/logout", status_code=status.HTTP_200_OK, tags=["Login"])
async def logout(token: str = Depends(decode_access_token)):
    """
    Cierra la sesión de usuario.

    Permite a un usuario cerrar su sesión proporcionando un token JWT válido.
    """
    try:
        # Extrae el valor del campo "exp" del token JWT
        token_exp = token.get("exp", None)
        if token_exp is None:
            raise HTTPException(status_code=401, detail="Token JWT no válido")
        
        # Convierte el valor "exp" en un objeto datetime
        expire = datetime.fromtimestamp(token_exp)
        
        # Obtiene la fecha y hora actual
        now = datetime.utcnow()
        
        # Comprueba si el token ha expirado
        if now > expire:
            raise HTTPException(status_code=401, detail="Token expirado")
        
        # Aquí puedes realizar cualquier otra lógica de cierre de sesión
        
        return {"message": "Sesión cerrada exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

