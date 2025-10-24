"""Validate the traced TorchScript policy against the original SB3 PPO model.

Produces a numeric comparison between the SB3 policy outputs and the traced model outputs
on a dummy observation constructed from the model's observation space.
"""
import sys
from pathlib import Path
import logging

logger = logging.getLogger('validate_traced')
logging.basicConfig(level=logging.INFO)


def register_vendored(repo_root: Path):
    import importlib.util, sys
    vend = repo_root / 'new-rede-a'
    if not vend.exists():
        logger.warning('Vendored folder not found: %s', vend)
        return
    # load deep_portfolio_torch
    dpt = vend / 'deep_portfolio_torch.py'
    pfe = vend / 'portfolio_features_extractor_torch.py'
    if dpt.exists():
        spec = importlib.util.spec_from_file_location('deep_portfolio_torch', str(dpt))
        mod = importlib.util.module_from_spec(spec)
        sys.modules['deep_portfolio_torch'] = mod
        spec.loader.exec_module(mod)
        sys.modules['new_rede_a.deep_portfolio_torch'] = mod
    if pfe.exists():
        spec = importlib.util.spec_from_file_location('portfolio_features_extractor_torch', str(pfe))
        mod2 = importlib.util.module_from_spec(spec)
        sys.modules['portfolio_features_extractor_torch'] = mod2
        spec.loader.exec_module(mod2)
        sys.modules['new_rede_a.portfolio_features_extractor_torch'] = mod2
        sys.modules['new_rede_a_portfolio_features_extractor_torch'] = mod2


def main():
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    sb3_zip = repo_root / 'src' / 'model' / 'ppo_custom_deep_portfolio_agent.zip'
    traced_pt = repo_root / 'out' / 'sb3_export' / 'ppo_policy_traced.pt'
    if not sb3_zip.exists():
        logger.error('SB3 zip not found: %s', sb3_zip)
        return
    if not traced_pt.exists():
        logger.error('Traced TorchScript not found: %s', traced_pt)
        return

    register_vendored(repo_root)

    try:
        from stable_baselines3 import PPO
    except Exception as e:
        logger.error('stable_baselines3 not importable: %s', e)
        return

    import torch
    import numpy as np

    logger.info('Loading SB3 model...')
    model = PPO.load(str(sb3_zip), device='cpu')
    logger.info('Loaded SB3 model: %s', type(model))

    obs_space = getattr(model, 'observation_space', None)
    if obs_space is None:
        logger.error('Model has no observation_space; cannot create dummy observation')
        return

    # Build dummy observation for Box spaces
    try:
        from gymnasium.spaces import Box
        if not isinstance(obs_space, Box):
            logger.error('Observation space is not Box; type=%s', type(obs_space))
            return
        shape = obs_space.shape
        # Example: SB3 policies often expect shape=(features,) per observation
        example_np = np.zeros(shape, dtype=np.float32)
        # model.predict expects single observation; we will also test policy.forward with torch tensor
        # Get SB3 output
        logger.info('Calling model.predict on dummy observation')
        try:
            action, _state = model.predict(example_np, deterministic=True)
            logger.info('model.predict action shape/type: %s / %s', getattr(action, 'shape', None), type(action))
        except Exception as e:
            logger.exception('model.predict failed; attempting policy.forward with torch tensor')
            # fallback to policy.forward
            tensor_obs = torch.as_tensor(example_np).unsqueeze(0)
            model.policy.to('cpu')
            with torch.no_grad():
                sb3_out = model.policy.forward(tensor_obs)
            logger.info('model.policy.forward output type: %s', type(sb3_out))

        # Prepare tensor input for traced model
        tensor_in = torch.as_tensor(example_np).unsqueeze(0)
        logger.info('Loading traced TorchScript model from %s', traced_pt)
        traced = torch.jit.load(str(traced_pt), map_location='cpu')

        traced.eval()
        model.policy.to('cpu')
        with torch.no_grad():
            try:
                # Try to call policy.forward and traced with tensor input
                sb3_out = model.policy.forward(tensor_in)
                traced_out = traced(tensor_in)
            except Exception as e:
                # Some policies may require flattened input; try flattening
                flat = tensor_in.view(tensor_in.size(0), -1)
                sb3_out = model.policy.forward(flat)
                traced_out = traced(flat)

        # Compare outputs numerically
        def to_tensor(x):
            if isinstance(x, tuple) or isinstance(x, list):
                # pick first tensor-like
                for it in x:
                    if isinstance(it, torch.Tensor):
                        return it
                # fallback
                return torch.as_tensor(np.array(x))
            if isinstance(x, torch.Tensor):
                return x
            try:
                return torch.as_tensor(x)
            except Exception:
                return None

        t_sb3 = to_tensor(sb3_out)
        t_traced = to_tensor(traced_out)

        if t_sb3 is None or t_traced is None:
            logger.error('Could not convert outputs to tensors for comparison (types: %s, %s)', type(sb3_out), type(traced_out))
            return

        # ensure same shape
        if t_sb3.shape != t_traced.shape:
            logger.warning('Output shapes differ: sb3=%s traced=%s', t_sb3.shape, t_traced.shape)

        diff = (t_sb3 - t_traced).abs().mean().item()
        logger.info('Mean absolute difference between SB3 policy output and traced model: %g', diff)
        logger.info('Validation completed')

    except Exception as e:
        logger.exception('Validation failed: %s', e)


if __name__ == '__main__':
    main()
