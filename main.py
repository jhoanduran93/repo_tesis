import os
import sys
import mysql.connector
from datetime import date, datetime, timedelta
from typing import List, Union

from fastapi import FastAPI, HTTPException, status, WebSocket, Depends, HTTPException,  WebSocketDisconnect, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.encoders import jsonable_encoder
import jwt
import openai

from mysql.connector import errorcode

from app.db.database import conn
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.security import Security, create_access_token, decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI()

# Configuración CORS para permitir solicitudes desde tu dominio de React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tu-app-react.com"],  # Reemplaza la URL de tu aplicación React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configura tu clave API de GPT-3
openai.api_key = Security.GPT3_API_KEY


@app.websocket("/chatbot")
async def chatbot_endpoint(websocket: WebSocket):
    """
    Ruta WebSocket para interactuar con el chatbot.

    Permite a los usuarios enviar preguntas y recibe respuestas generadas por GPT-3.

    Args:
        websocket (WebSocket): La conexión WebSocket establecida.

    Returns:
        None
    """
    try:
        await websocket.accept()
        await websocket.send_text("¡Bienvenido! Puedes comenzar a hacer preguntas.")

        while True:
            data = await websocket.receive_text()

            try:
                # Usa GPT-3 para generar una respuesta
                response = openai.Completion.create(
                    engine="text-davinci-002",
                    prompt=f"Responder a la siguiente pregunta: {data}",
                    max_tokens= 200  # Ajusta este valor según tus necesidades
                )

                # Extrae la respuesta generada por GPT-3
                answer = response.choices[0].text

                await websocket.send_text(answer)
            except Exception as e:
                await websocket.send_text(f"Error en la generación de respuesta: {str(e)}")
    except WebSocketDisconnect as e:
        await websocket.close()
        # Puedes agregar lógica adicional para manejar desconexiones de WebSocket si es necesario
        print(f"Conexión cerrada: {e}")
    except HTTPException as e:
        await websocket.send_text(f"Error HTTP: {e.detail}")
    except Exception as e:
        await websocket.send_text(f"Error inesperado: {str(e)}")


        
@app.post("/cometa1user", status_code= status.HTTP_201_CREATED,tags=["Chatbot"])
def chatbot(question: str):
    """
    Ruta para obtener una respuesta del chatbot basada en una pregunta.

    Permite a los usuarios enviar preguntas y recibe respuestas generadas por GPT-3.

    Args:
        question (str): La pregunta del usuario.

    Returns:
        dict: Un diccionario que contiene la respuesta generada por el chatbot.
    """
    try:
        # Usa GPT-3 para generar una respuesta
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=f"Responder a la siguiente pregunta: {question}",
            max_tokens=50  # Ajusta este valor según tus necesidades
        )

        # Extrae la respuesta generada por GPT-3
        answer = response.choices[0].text

        return {"answer": answer}

    except Exception as e:
        return {"error": str(e)}
    

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
            raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")
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

@app.post("/create_conversation", status_code=status.HTTP_201_CREATED, response_model=Conversation, tags=["conversation"])
async def create_conversation(email: str):
    """
    Crea una nueva conversación para un usuario.

    Permite a un usuario iniciar una nueva conversación y devuelve detalles de la conversación creada.
    """
    cursor = conn.cursor()
    
    try:
        # Obtiene el ID del usuario usando el correo electrónico
        query_user_id = "SELECT iduser FROM user WHERE email = %s"
        cursor.execute(query_user_id, (email,))
        user_id = cursor.fetchone()

        if not user_id:
            raise HTTPException(status_code=404, detail=f"Usuario con correo electrónico {email} no encontrado")

        user_id = user_id[0]
        
        # Inserta una nueva conversación en la base de datos
        today = date.today()
        query = "INSERT INTO conversation (star_date, end_date, iduser) VALUES (%s, %s, %s)"
        cursor.execute(query, (today, today, user_id))
        conn.commit()
        
        # Obtiene el ID de la conversación recién creada
        conversation_id = cursor.lastrowid

        # Construye y devuelve una instancia del modelo Conversation con los datos relevantes
        new_conversation = Conversation(idconversation=conversation_id, start_date=today, end_date=today, iduser=user_id)
        return new_conversation
     
    except Exception as e:
        raise HTTPException(status_code=500, detail= "Usuario no encontrado")
    finally:
        cursor.close()
        
from fastapi import FastAPI, HTTPException, Path
from typing import List
from app.models.conversation import Conversation
import mysql.connector
from mysql.connector import errorcode

# ... (código anterior)

@app.get("/get_user_conversations/{email}", response_model=List[Conversation], tags=["conversation"])
async def get_user_conversations(email: str = Path(..., description="Email del usuario")):
    """
    Obtiene todas las conversaciones de un usuario por su correo electrónico.

    Permite a un usuario obtener una lista de todas sus conversaciones.

    Args:
        email (str): El correo electrónico del usuario.

    Returns:
        List[Conversation]: Lista de conversaciones del usuario.

    Raises:
        HTTPException 404: Si el usuario no tiene conversaciones.
        HTTPException 500: Si hay un error en el servidor al obtener las conversaciones.
    """
    cursor = conn.cursor(dictionary=True)  # Usar dictionary=True para obtener resultados como diccionarios
    try:
        # Consulta todas las conversaciones de un usuario en la base de datos
        query = "SELECT * FROM conversation WHERE iduser = (SELECT iduser FROM user WHERE email = %s)"
        cursor.execute(query, (email,))
        
        conversations = []
        for row in cursor.fetchall():
            conversation_model = Conversation(idconversation=row["idconversation"], star_date=row["star_date"], end_date=row["end_date"], iduser=row["iduser"])
            conversations.append(conversation_model)

        if not conversations:
            raise HTTPException(status_code=404, detail=f"Usuario con email {email} no tiene conversaciones")

        return conversations
    except mysql.connector.Error as e:
        if e.errno == errorcode.ER_NO_SUCH_TABLE:
            raise HTTPException(status_code=500, detail="Error en la base de datos: la tabla no existe")
        else:
            raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.post("/send_message", status_code=status.HTTP_201_CREATED, response_model= Message, tags=["message"])
async def send_message(idconversation: int, content: str):
    """
    Envía un mensaje en una conversación.

    Permite a un usuario enviar un mensaje en una conversación existente y devuelve detalles del mensaje enviado.
    """
    cursor = conn.cursor()
    try:
        # Inserta un nuevo mensaje en la base de datos
        now = datetime.now().time()
        query = "INSERT INTO message (content, hour, idconversation) VALUES (%s, %s, %s)"
        cursor.execute(query, (content, now, idconversation))
        conn.commit()
        message_id = cursor.lastrowid
        new_message = Message(idmessage=message_id, content = content, hour = now, idconversation = idconversation)
        return  new_message
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.get("/get_conversation_messages/{conversation_id}",status_code=status.HTTP_201_CREATED, response_model=List[Message], tags=["message"])
async def get_conversation_messages(conversation_id: int):
    """
    Obtiene todos los mensajes de una conversación.

    Permite obtener una lista de todos los mensajes de una conversación específica.
    """
    cursor = conn.cursor()
    try:
        # Consulta todos los mensajes de una conversación en la base de datos con la hora formateada
        query = f"SELECT idmessage, content, TIME_FORMAT(hour, '%H:%i:%s') AS formatted_hour, idconversation FROM message WHERE idconversation = {conversation_id}"
        cursor.execute(query)
        messages = []
        for row in cursor.fetchall():
            messages.append({"idmessage": row[0], "content": row[1], "hour": row[2], "idconversation": row[3]})
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.post("/login", status_code=status.HTTP_200_OK, tags=["Login"])
async def login(email: str, password: str):
    """
    Inicia sesión de usuario.

    Permite a un usuario iniciar sesión proporcionando su correo electrónico y contraseña.
    """
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM user WHERE email = %s AND password = %s"
        cursor.execute(query, (email, password))
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

@app.get("/get_user_conversations_all/{email}", response_model=List[Conversation], tags=["conversation"])
async def get_user_conversations(email: str):
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT conversation.idconversation, conversation.star_date, conversation.end_date, conversation.iduser,
                   message.idmessage, message.content, message.hour
            FROM conversation
            LEFT JOIN message ON conversation.idconversation = message.idconversation
            WHERE conversation.iduser = (SELECT iduser FROM user WHERE email = %s)
        """
        cursor.execute(query, (email,))
        rows = cursor.fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail=f"Usuario con email {email} no tiene conversaciones")

        conversations = []

        for row in rows:
            # Imprimir información para depurar
            print(f"Current row: {row}")
            print(f"Current conversations: {conversations}")

            # Verificar si es una nueva conversación
            print(f"Last conversation id: {conversations[-1]['idconversation'] if conversations else None}")
            print(f"Current conversation id: {row['idconversation']}")
            
            if not conversations or int(conversations[-1]["idconversation"]) != row["idconversation"]:
                conversation = {
                    "idconversation": row["idconversation"],
                    "star_date": row["star_date"],
                    "end_date": row["end_date"],
                    "iduser": row["iduser"],
                    "messages": []
                }
                conversations.append(conversation)

            # Agregar mensaje a la conversación actual
            if row["idmessage"] is not None:
                message = {
                    "idmessage": row["idmessage"],
                    "content": row["content"],
                    "hour": row["hour"]
                }
                print(f"Adding message to conversation: {message}")
                conversations[-1]["messages"].append(message)

        return conversations

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()