from pydantic import BaseModel
from datetime import date, time

# Clase para representar una conversación
class Conversation(BaseModel):
    idconversation: int
    start_date: date
    end_date: date
    iduser: int