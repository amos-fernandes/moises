import os
from fastapi import APIRouter, Security, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import numpy as np
import tensorflow as tf
from rnn.models.deep_portfolio import DeepPortfolioAI


router = APIRouter()
security = HTTPBearer()
MODEL = DeepPortfolioAI(num_assets=10)
SECRET_KEY = os.getenv("SECRET_KEY")

class PredictionRequest(BaseModel):
    market_data: list
    news_data: list

def verify_jwt(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        return jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/predict")
async def predict(
    request: PredictionRequest,
    user=Depends(verify_jwt)
):
    try:
        market_tensor = tf.convert_to_tensor(request.market_data, dtype=tf.float32)
        prediction = MODEL([market_tensor, request.news_data])
        return {
            "success": True,
            "prediction": prediction.numpy().tolist(),
            "timestamp": np.datetime64('now').astype(str)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
