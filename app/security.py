import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException


SECRET_KEY = "502481xxc"  #clave segura
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # El tiempo de vencimiento del token (30)

class Security:
    GPT3_API_KEY = "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"

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Tiempo de expiración predeterminado
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Token inválido")
