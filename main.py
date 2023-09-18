import os
import sys
from datetime import date, datetime, timedelta
from typing import List, Union

from fastapi import FastAPI, HTTPException, status, WebSocket, Depends
from fastapi.responses import RedirectResponse
from fastapi.encoders import jsonable_encoder
import jwt
import openai

from app.db.database import conn
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.security import Security, create_access_token, decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI()

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
    await websocket.accept()
    await websocket.send_text("¡Bienvenido! Puedes comenzar a hacer preguntas.")

    while True:
        data = await websocket.receive_text()

        try:
            # Usa GPT-3 para generar una respuesta
            response = openai.Completion.create(
                engine="text-davinci-002",
                prompt=f"Responder a la siguiente pregunta: {data}",
                max_tokens=80  # Ajusta este valor según tus necesidades
            )

            # Extrae la respuesta generada por GPT-3
            answer = response.choices[0].text

            await websocket.send_text(answer)
        except Exception as e:
            await websocket.send_text(f"Error: {str(e)}")


        
@app.post("/chatbot1user", status_code= status.HTTP_201_CREATED,tags=["Chatbot"])
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

@app.post("/create_user",status_code=status.HTTP_201_CREATED,response_model= User ,tags= ["user"])
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
    except Exception as e:
        raise HTTPException(status_code=500 , detail=str(e))
    finally:
        cursor.close()
        
@app.get("/get_user/{user_id}", status_code=status.HTTP_201_CREATED,response_model=User, tags=["user"])
async def get_user(user_id: int):
    """
    Obtener información de un usuario por su ID.

    Args:
        user_id (int): El ID del usuario a buscar.

    Returns:
        dict: La información del usuario encontrado.

    Raises:
        HTTPException: Si el usuario no se encuentra.
    """
    cursor = conn.cursor()
    try:
        # Consulta el usuario por ID en la base de datos
        query = "SELECT * FROM user WHERE iduser = %s"
        cursor.execute(query, (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        user = User(iduser=user_data[0], name=user_data[1], email=user_data[2], password=user_data[3])
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.delete("/delete_user/{user_id}", status_code=status.HTTP_201_CREATED,response_model=User, tags=["user"])
async def delete_user(user_id: int):
    """
    Elimina un usuario por su ID.

    Permite eliminar un usuario existente proporcionando su ID.
    """
    cursor = conn.cursor()
    try:
        # Elimina el usuario por ID en la base de datos
        query = "DELETE FROM user WHERE iduser = %s"
        cursor.execute(query, (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return {"message": "Usuario eliminado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.put("/update_user/{user_id}", status_code=status.HTTP_201_CREATED,response_model=User, tags=["user"])
async def update_user(user_id: int, updated_user: User):
    """
    Actualiza la información de un usuario por su ID.

    Permite actualizar la información de un usuario existente proporcionando su ID y los datos actualizados.
    """
    cursor = conn.cursor()
    try:
        # Actualiza el usuario por ID en la base de datos
        query = "UPDATE user SET name = %s, email = %s, password = %s WHERE iduser = %s"
        cursor.execute(query, (updated_user.name, updated_user.email, updated_user.password, user_id))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return updated_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()


@app.post("/create_conversation", status_code=status.HTTP_201_CREATED, response_model = Conversation, tags=["conversation"])
async def create_conversation(iduser: int):
    """
    Crea una nueva conversación para un usuario.

    Permite a un usuario iniciar una nueva conversación y devuelve detalles de la conversación creada.
    """
    cursor = conn.cursor()
    
    try:
        
        # Inserta una nueva conversación en la base de datos
        
        today = date.today()
        query = "INSERT INTO conversation (start_date, end_date, iduser) VALUES (%s, %s, %s)"
        cursor.execute(query, (today, today, iduser))
        conn.commit()
         # Obtén el ID de la conversación recién creada
        conversation_id = cursor.lastrowid

        # Construye y devuelve una instancia del modelo Conversation con los datos relevantes
        new_conversation = Conversation(idconversation=conversation_id, start_date=today, end_date=today, iduser=iduser)
        return new_conversation
     
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        
@app.get("/get_user_conversations/{user_id}", response_model=List[Conversation], tags=["conversation"])
async def get_user_conversations(user_id: int):
    """
    Obtiene todas las conversaciones de un usuario.

    Permite a un usuario obtener una lista de todas sus conversaciones.
    """
    cursor = conn.cursor()
    try:
        # Consulta todas las conversaciones de un usuario en la base de datos
        query = "SELECT * FROM conversation WHERE iduser = %s"
        cursor.execute(query, (user_id,))
        conversations = []
        for row in cursor.fetchall():
            conversations.append({"idconversation": row[0], "start_date": row[1], "end_date": row[2], "iduser": row[3]})
        return conversations
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
