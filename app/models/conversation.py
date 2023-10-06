from pydantic import BaseModel
from datetime import date, time
from typing import Optional  # Importa Optional

# Clase para representar una conversación
class Conversation(BaseModel):
    idconversation: int
    star_date: date
    end_date: date
    iduser: int
    