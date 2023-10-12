from pydantic import BaseModel
from datetime import date, time

# Clase para representar un mensaje
class Message(BaseModel):
    idmessage: int
    points: int
    hour: time
    idconversation: int