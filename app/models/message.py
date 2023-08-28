from pydantic import BaseModel
from datetime import date, time

# Clase para representar un mensaje
class Message(BaseModel):
    idmessage: int
    content: str
    hour: time
    idconversation: int