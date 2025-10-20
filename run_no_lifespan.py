# Lightweight runner to start the FastAPI app without running lifespan startup (no model load)
import os
import uvicorn

# Ensure the app imports from repo root
os.environ.setdefault('PYTHONPATH', os.path.dirname(os.path.abspath(__file__)))

# Optionally set a test AIBANK_API_KEY for local testing
os.environ.setdefault('AIBANK_API_KEY', 'test_aibank_key_from_rnn_server')
# Make sure callback is not set so we don't attempt outbound callbacks during tests
os.environ.pop('AIBANK_CALLBACK_URL', None)
os.environ.pop('CALLBACK_SHARED_SECRET', None)
# Skip importing heavy TensorFlow-dependent predictor
os.environ.setdefault('SKIP_RNN_IMPORT', '1')

if __name__ == '__main__':
    # Import the FastAPI app defined in app.py
    from app import fastapi_app
    # Run uvicorn with lifespan disabled so startup lifecycle (model loading) doesn't run
    uvicorn.run(fastapi_app, host='127.0.0.1', port=8000, lifespan='off')
