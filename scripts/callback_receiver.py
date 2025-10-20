import os
import hmac
import hashlib
import json
from fastapi import FastAPI, Request, Header
import uvicorn
from datetime import datetime

app = FastAPI()

LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'logs', 'callback_receiver.log')
if not os.path.exists(os.path.dirname(LOG_PATH)):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

CALLBACK_SHARED_SECRET = os.environ.get('CALLBACK_SHARED_SECRET', 'super_secret_for_callback_signing')

def write_log(entry: str):
    ts = datetime.utcnow().isoformat()
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"{ts} - {entry}\n")

@app.post('/api/rnn_investment_result_callback')
async def receive_callback(request: Request, x_rnn_signature: str = Header(None)):
    body = await request.body()
    body_text = body.decode('utf-8')
    signature = None
    if x_rnn_signature:
        signature = x_rnn_signature
    else:
        signature = request.headers.get('X-RNN-Signature')

    # Verify HMAC signature if secret is set
    verification = 'not_verified'
    if CALLBACK_SHARED_SECRET:
        try:
            computed = hmac.new(CALLBACK_SHARED_SECRET.encode('utf-8'), body, hashlib.sha256).hexdigest()
            verification = 'ok' if computed == signature else f'mismatch (computed={computed})'
        except Exception as e:
            verification = f'error:{e}'

    log_entry = f"Received callback; signature={signature}; verification={verification}; body={body_text}"
    write_log(log_entry)
    print(log_entry)
    return {"status": "received", "verification": verification}

if __name__ == '__main__':
    # Ensure receiver listens on port 8001
    uvicorn.run(app, host='127.0.0.1', port=8001)
