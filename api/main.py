from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from endpoints.predict import router as predict_router
from agents.dataset_update_agent import router as dataset_router
from agents.financial_data_agent import router as finance_router
from agents.investment_agent import router as invest_router
from agents.rl_agent import router as rl_router
from utils.logger import get_logger
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
import os




logger = get_logger()

app = FastAPI(title="ATCoin Neural Agents")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rotas
app.include_router(predict_router)
app.include_router(dataset_router, prefix="/dataset")
app.include_router(finance_router, prefix="/finance")
app.include_router(invest_router, prefix="/invest")
app.include_router(rl_router, prefix="/rl")




@app.get("/", response_class=HTMLResponse)
async def index():
    agentes = [
        {
            "nome": "Captura de Dados",
            "status": "Ativo",
            "ultima_acao": "08/05/2025 10:00",
            "proxima_execucao": "09/05/2025 10:00",
            "resultado": "12 ativos atualizados"
        },
        {
            "nome": "PPO Trainer",
            "status": "Treinando",
            "ultima_acao": "08/05/2025 12:00",
            "proxima_execucao": "09/05/2025 12:00",
            "resultado": "Reward: 0.89"
        },
        # outros agentes...
    ]

    template = templates.get_template("index.html")
    return HTMLResponse(template.render(agentes=agentes))