import torch
from stable_baselines3 import PPO
from pathlib import Path
import numpy as np
import gym

zip_path = Path('src/model/ppo_custom_deep_portfolio_agent.zip')
if not zip_path.exists():
    print('model zip not found:', zip_path)
    raise SystemExit(2)

print('Preparing portable loader for new-rede-a (if available)')
try:
    from new_rede_a_portable_import import load_portable
    portable = load_portable()
    # ensure portable modules are importable via sys.modules by loading them
    try:
        portable.load_module('new-rede-a.portfolio_features_extractor_torch')
        print('Loaded portable module new-rede-a.portfolio_features_extractor_torch')
    except Exception as e:
        print('Portable module load failed or not necessary:', e)
except Exception:
    print('Portable loader not available; continuing')

print('Loading SB3 model from', zip_path)
model = PPO.load(str(zip_path), device='cpu')
print('Loaded model:', model)

# Try to infer observation space
obs_space = None
if hasattr(model, 'observation_space') and model.observation_space is not None:
    obs_space = model.observation_space
elif hasattr(model, 'policy') and hasattr(model.policy, 'observation_space'):
    obs_space = model.policy.observation_space

print('Observation space:', obs_space)

# Build a dummy observation
if obs_space is not None:
    try:
        if isinstance(obs_space, gym.spaces.Box):
            shape = obs_space.shape
            dummy = np.zeros(shape, dtype=np.float32)
            # SB3 expects batch-less observation; pass 1D
            if dummy.ndim == 2 and dummy.shape[0] == 1:
                dummy = dummy[0]
        else:
            # fallback: create a 1D vector
            dummy = np.zeros((model.policy.observation_space.shape[0],), dtype=np.float32)
    except Exception:
        dummy = np.zeros((model.observation_space.shape[0],), dtype=np.float32)
else:
    # As a last resort, create a vector of size 100
    dummy = np.zeros((100,), dtype=np.float32)

print('Dummy obs shape:', getattr(dummy, 'shape', None))

try:
    action, state = model.predict(dummy, deterministic=True)
    print('Predict succeeded. action:', action, 'state:', state)
except Exception as e:
    print('Predict failed:', e)

# Try to script the policy
try:
    policy = model.policy
    policy.eval()
    try:
        scripted = torch.jit.script(policy)
        out = Path('src/model/ppo_custom_deep_portfolio_agent_policy_scripted.pt')
        scripted.save(str(out))
        print('Saved scripted policy to', out)
    except Exception as se:
        print('Scripting via torch.jit.script failed:', se)
        # Try tracing with a tensor input
        try:
            import torch
            inp = torch.as_tensor(dummy, dtype=torch.float32).unsqueeze(0)
            traced = torch.jit.trace(policy, inp)
            out = Path('src/model/ppo_custom_deep_portfolio_agent_policy_traced.pt')
            traced.save(str(out))
            print('Saved traced policy to', out)
        except Exception as te:
            print('Tracing also failed:', te)
            # fallback: save state_dict
            sd_out = Path('src/model/ppo_custom_deep_portfolio_agent_policy_state_dict.pth')
            torch.save(policy.state_dict(), sd_out)
            print('Saved policy state_dict to', sd_out)
except Exception as e:
    print('Could not script policy:', e)
    raise

print('Done')
