from pydantic import BaseModel

# Clase para representar un usuario
class User(BaseModel):
     name: str
     email: str
     password: str
 
 