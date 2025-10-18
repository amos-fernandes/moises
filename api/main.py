from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

try:
    from utils.logger import get_logger
except Exception:
    try:
        from src.utils.logger import get_logger
    except Exception:
        get_logger = None


if get_logger is not None:
    logger = get_logger()
else:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('atcoin_fallback')

# initialize templates loader (safe fallback)
template_dir = Path(__file__).resolve().parents[1] / 'templates'
if not template_dir.exists():
    template_dir = Path('.')
templates = Environment(loader=FileSystemLoader(str(template_dir)))


app = FastAPI(title="ATCoin Neural Agents")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Defensive imports: some routers depend on heavy ML packages that may not be
# available at container build / import time. Import them only if possible.
def safe_import_router(module_path, symbol='router'):
    try:
        mod = __import__(module_path, fromlist=[symbol])
        return getattr(mod, symbol)
    except Exception as e:
        logger.warning(f"Could not import {module_path}: {e}")
        return None


predict_router = safe_import_router('endpoints.predict')
dataset_router = safe_import_router('agents.dataset_update_agent')
finance_router = safe_import_router('agents.financial_data_agent')
invest_router = safe_import_router('agents.investment_agent')
rl_router = safe_import_router('agents.rl_agent')
backtest_status_router = safe_import_router('endpoints.backtest_status')

if predict_router is not None:
    app.include_router(predict_router)
if dataset_router is not None:
    app.include_router(dataset_router, prefix='/dataset')
if finance_router is not None:
    app.include_router(finance_router, prefix='/finance')
if invest_router is not None:
    app.include_router(invest_router, prefix='/invest')
if rl_router is not None:
    app.include_router(rl_router, prefix='/rl')
if backtest_status_router is not None:
    app.include_router(backtest_status_router)


@app.get('/', response_class=HTMLResponse)
async def index():
    try:
        template = templates.get_template('index.html')
        content = template.render(agentes=[])
    except Exception:
        content = '<html><body><h1>ATCoin Neural Agents</h1></body></html>'
    return HTMLResponse(content)
    return HTMLResponse(content)