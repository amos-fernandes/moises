"""
Export Stable-Baselines3 (PyTorch) policy stored in zip to TorchScript.
This is a best-effort exporter: it expects the repository to contain the
policy/network class used during training (DeepPortfolioAgentNetwork / DeepPortfolioAI).

It will:
 - extract policy.pth or pytorch_variables.pth from the zip
 - attempt to import the model class `DeepPortfolioAgentNetwork` or `DeepPortfolioAI`
 - instantiate the model with config defaults and load state_dict
 - script the model with torch.jit.script and save as .pt

If ONNX/TF conversion is required, install `onnx` and `onnx_tf` and convert the scripted model later.
"""
import sys
import zipfile
from pathlib import Path
import io

zip_path = Path('src/model/ppo_custom_deep_portfolio_agent.zip')
if not zip_path.exists():
    print('zip not found', zip_path)
    sys.exit(2)

# Read zip members
with zipfile.ZipFile(zip_path, 'r') as z:
    names = z.namelist()
    for n in names:
        print('zip contains:', n)

    # try to read policy.pth or pytorch_variables.pth
    for candidate in ('policy.pth', 'pytorch_variables.pth', 'policy.pkl', 'policy.pt'):
        if candidate in names:
            data = z.read(candidate)
            open('tmp_policy.pth','wb').write(data)
            policy_file = Path('tmp_policy.pth')
            print('extracted', candidate)
            break
    else:
        print('No recognized policy file found in zip; aborting exporter')
        sys.exit(3)

# Try to import torch and model class
try:
    import torch
except Exception as e:
    print('torch import failed:', e)
    sys.exit(4)

# Try to find model class in repo
ModelClass = None
candidates = [
    'agents.DeepPortfolioAgent.DeepPortfolioAgentNetwork',
    'DeepPortfolioAgent.DeepPortfolioAgentNetwork',
    'models.deep_portfolio.DeepPortfolioAI',
    'models.deep_portfolio.DeepPortfolioAgentNetwork'
]
for path in candidates:
    parts = path.split('.')
    module = '.'.join(parts[:-1])
    cls = parts[-1]
    try:
        mod = __import__(module, fromlist=[cls])
        ModelClass = getattr(mod, cls)
        print('Found model class:', path)
        break
    except Exception:
        continue

if ModelClass is None:
    print('Could not find model class in the repo. You may need to adjust candidates or provide a small wrapper that builds the model and loads the state_dict.')
    sys.exit(5)

# Instantiate with default config
try:
    model = ModelClass()
    print('Instantiated model with no args')
except Exception as e:
    print('Failed to instantiate without args:', e)
    try:
        # try with config import
        from src.config.config import *
        model = ModelClass()
        print('Instantiated model with config import')
    except Exception as e2:
        print('Failed to instantiate model; aborting:', e2)
        sys.exit(6)

# Load state dict
try:
    sd = torch.load('tmp_policy.pth', map_location='cpu')
    # sd might be a dict with 'state_dict' or be the state_dict itself
    if isinstance(sd, dict) and 'state_dict' in sd:
        state = sd['state_dict']
    else:
        state = sd
    # Attempt to load state into model
    try:
        model.load_state_dict(state)
    except Exception as e:
        # try keys mismatch: some SB3 policies prefix with 'policy.'; try stripping
        new_state = {}
        for k,v in state.items():
            nk = k
            if k.startswith('policy.'):
                nk = k.replace('policy.','')
            new_state[nk] = v
        model.load_state_dict(new_state)
    print('Loaded state_dict into model')
except Exception as e:
    print('Failed to load state dict:', e)
    sys.exit(7)

# Script the model
try:
    scripted = torch.jit.script(model)
    out_path = Path('src/model/ppo_custom_deep_portfolio_agent_scripted.pt')
    scripted.save(str(out_path))
    print('Saved scripted model to', out_path)
except Exception as e:
    print('Failed to script model:', e)
    sys.exit(8)

print('Exporter finished successfully')
