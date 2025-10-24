"""Export SB3/PyTorch policy from a Stable-Baselines3 zip artifact.

This script will:
- ensure repo root is on sys.path
- dynamically load vendored modules from `new-rede-a` and register them under expected module names
- attempt `PPO.load()` on the provided zip
- try to script/trace the policy to TorchScript and save to `out/ppo_policy.pt`
- fallback to saving `state_dict` to `out/ppo_state_dict.pt`

Usage: python scripts/export_sb3_policy.py
"""
import sys
import logging
from pathlib import Path
import importlib.util
import types
import zipfile

logger = logging.getLogger('sb3_export')
logging.basicConfig(level=logging.INFO)


def load_module_from_path(module_name: str, path: Path):
    """Load a module from a file path and register it under module_name in sys.modules."""
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    # register early to help with recursive imports
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        # Remove partial module on failure
        sys.modules.pop(module_name, None)
        raise
    return mod


def register_vendored_modules(repo_root: Path):
    """Register expected vendored modules so cloudpickle can find them during SB3 load.

    This registers:
    - deep_portfolio_torch -> new-rede-a/deep_portfolio_torch.py
    - new_rede_a_portfolio_features_extractor_torch -> new-rede-a/portfolio_features_extractor_torch.py
    Also registers dotted variants for safety.
    """
    vendored_dir = repo_root / 'new-rede-a'
    if not vendored_dir.exists():
        logger.warning('Vendored folder new-rede-a not found; skipping vendored registration')
        return

    # deep_portfolio_torch (imported by portfolio_features_extractor_torch)
    dpt_path = vendored_dir / 'deep_portfolio_torch.py'
    if dpt_path.exists():
        logger.info('Registering deep_portfolio_torch from %s', dpt_path)
        mod = load_module_from_path('deep_portfolio_torch', dpt_path)
        sys.modules['new_rede_a.deep_portfolio_torch'] = mod

    pfe_path = vendored_dir / 'portfolio_features_extractor_torch.py'
    if pfe_path.exists():
        logger.info('Registering portfolio_features_extractor_torch from %s', pfe_path)
        # load under simple name expected by file imports
        mod = load_module_from_path('portfolio_features_extractor_torch', pfe_path)
        # register the names cloudpickle is likely to look for
        sys.modules['new_rede_a_portfolio_features_extractor_torch'] = mod
        sys.modules['new_rede_a.portfolio_features_extractor_torch'] = mod
        sys.modules['new_rede_a_portfolio_features_extractor_torch'] = mod


def inspect_sb3_zip(sb3_zip: Path):
    if not sb3_zip.exists():
        raise FileNotFoundError(sb3_zip)
    with zipfile.ZipFile(sb3_zip, 'r') as z:
        logger.info('SB3 zip contents:')
        for e in z.infolist():
            logger.info(' - %s (len=%d)', e.filename, e.file_size)
        # try to read data/ to inspect cloudpickle payload if present
        try:
            with z.open('data', 'r') as f:
                data_preview = f.read(1024)
                logger.info('Read %d bytes from data entry (preview).', len(data_preview))
        except KeyError:
            logger.debug('No data entry in zip')


def export_policy_from_sb3(sb3_zip: Path, out_dir: Path):
    import torch
    try:
        from stable_baselines3 import PPO
    except Exception as e:
        logger.error('stable_baselines3 import failed: %s', e)
        raise

    inspect_sb3_zip(sb3_zip)

    logger.info('Attempting to load SB3 model from %s', sb3_zip)
    # Let SB3 handle deserialization; vendored modules should already be in sys.modules
    model = None
    try:
        model = PPO.load(str(sb3_zip), device='cpu')
    except Exception as e:
        logger.exception('PPO.load failed')
        raise

    logger.info('Model loaded: %s', type(model))

    # Ensure output dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Try to get observation space and prepare dummy input
    obs_space = getattr(model, 'observation_space', None)
    if obs_space is None:
        logger.warning('Model does not have observation_space; saving state_dict only')
        torch.save(model.policy.state_dict(), out_dir / 'ppo_state_dict.pt')
        return

    try:
        import numpy as np
        # Only handle Box for now
        from gymnasium.spaces import Box
        if isinstance(obs_space, Box):
            shape = obs_space.shape
            # Create a dummy observation batch of size 1
            example_obs = np.zeros((1,) + shape, dtype=np.float32)
            # Convert to tensor
            example_tensor = torch.as_tensor(example_obs)

            policy = model.policy
            policy.to('cpu')

            # Try tracing forward method that accepts observations
            try:
                logger.info('Attempting torch.jit.trace on policy.forward')
                # Some SB3 policies expect flattened input; attempt to call with tensor
                traced = torch.jit.trace(policy, example_tensor, strict=False)
                traced_path = out_dir / 'ppo_policy_traced.pt'
                traced.save(str(traced_path))
                logger.info('Saved traced policy to %s', traced_path)
                return
            except Exception as e_trace:
                logger.exception('Tracing failed, will try scripting or saving state_dict')

            # as fallback try scripting
            try:
                scripted = torch.jit.script(policy)
                scripted_path = out_dir / 'ppo_policy_scripted.pt'
                scripted.save(str(scripted_path))
                logger.info('Saved scripted policy to %s', scripted_path)
                return
            except Exception:
                logger.exception('Scripting failed; saving state_dict as fallback')
                torch.save(policy.state_dict(), out_dir / 'ppo_state_dict.pt')
                logger.info('Saved state_dict to %s', out_dir / 'ppo_state_dict.pt')
                return
        else:
            logger.warning('Observation space is not Box (type=%s). Saving state_dict only.', type(obs_space))
            import torch
            torch.save(model.policy.state_dict(), out_dir / 'ppo_state_dict.pt')
            return
    except Exception:
        logger.exception('Unexpected error while exporting policy; saving state_dict')
        import torch
        torch.save(model.policy.state_dict(), out_dir / 'ppo_state_dict.pt')


def main():
    repo_root = Path(__file__).resolve().parents[1]
    # ensure repo root is importable
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    sb3_zip = repo_root / 'src' / 'model' / 'ppo_custom_deep_portfolio_agent.zip'
    out_dir = repo_root / 'out' / 'sb3_export'

    # register vendored modules to satisfy cloudpickle during SB3 load
    try:
        register_vendored_modules(repo_root)
    except Exception:
        logger.exception('Failed to register vendored modules; continuing and attempting to load anyway')

    try:
        export_policy_from_sb3(sb3_zip, out_dir)
    except Exception as e:
        logger.error('Export failed: %s', e)


if __name__ == '__main__':
    main()
"""Export SB3 policy from a .zip artifact to TorchScript or state_dict fallback.
Usage: python scripts/export_sb3_policy.py
"""
import sys
from pathlib import Path
import logging

repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('export_sb3')

try:
    # Import here to ensure our repo is on sys.path
    import torch
    from stable_baselines3 import PPO
except Exception as e:
    logger.error('Missing runtime dependency: %s', e)
    raise


def preload_vendored():
    """Try to make vendored modules importable for cloudpickle deserialization."""
    try:
        # The repository contains a folder 'new-rede-a' with the torch extractor
        import importlib.util
        vendored = Path(repo_root) / 'new-rede-a'
        if vendored.exists():
            # add repo root already done; attempt to import the expected module name
            try:
                import new_rede_a_portable_import as p
                p.load_portable()
                logger.info('Portable vendored modules registered via new_rede_a_portable_import.load_portable()')
                return True
            except Exception:
                logger.debug('Could not use new_rede_a_portable_import loader, attempting direct package import')
            # try importing the torch extractor directly or load file dynamically
            try:
                import new_rede_a.portfolio_features_extractor_torch as extr
                logger.info('Imported vendored new_rede_a.portfolio_features_extractor_torch')
                return True
            except Exception:
                logger.debug('Direct import of vendored package failed; will attempt dynamic load')
                # attempt to locate the file and load it as the module name expected by cloudpickle
                possible = vendored / 'portfolio_features_extractor_torch.py'
                if possible.exists():
                    spec = importlib.util.spec_from_file_location('new_rede_a_portfolio_features_extractor_torch', str(possible))
                    mod = importlib.util.module_from_spec(spec)
                    try:
                        spec.loader.exec_module(mod)
                        # register both dotted and underscored names to increase chances
                        import sys as _sys
                        _sys.modules['new_rede_a.portfolio_features_extractor_torch'] = mod
                        _sys.modules['new_rede_a_portfolio_features_extractor_torch'] = mod
                        logger.info('Dynamically loaded vendored extractor and registered module names')
                        return True
                    except Exception as e_mod:
                        logger.exception('Failed to exec vendored extractor module: %s', e_mod)
        else:
            logger.debug('Vendored folder new-rede-a not found')
    except Exception as e:
        logger.exception('Error while preloading vendored modules: %s', e)
    return False




def export_policy(zip_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    preload_vendored()

    logger.info('Attempting to load SB3 model from %s', zip_path)
    try:
        model = PPO.load(str(zip_path))
    except Exception as e:
        logger.exception('Failed to load SB3 model: %s', e)
        return False

    logger.info('SB3 model loaded. Attempting to access policy network')
    try:
        policy = model.policy
        # Prepare a dummy observation tensor
        import numpy as np
        obs_space = model.observation_space
        if hasattr(obs_space, 'shape') and obs_space.shape is not None:
            dummy_obs = np.zeros((1,) + obs_space.shape, dtype=np.float32)
            # Convert to torch tensor using model.device
            dummy_t = torch.as_tensor(dummy_obs).to(next(model.policy.parameters()).device)
        else:
            dummy_t = None

        # Try to script the policy forward using torch.jit.trace (best-effort)
        try:
            model.policy.eval()
            if dummy_t is not None:
                traced = torch.jit.trace(model.policy, dummy_t, strict=False)
                out_ts = out_dir / 'policy_traced.pt'
                traced.save(str(out_ts))
                logger.info('Saved traced policy to %s', out_ts)
            else:
                logger.warning('Observation space shape unknown; skipping trace')
        except Exception as e_trace:
            logger.exception('TorchScript trace failed: %s', e_trace)

        # Always save state_dict as fallback
        try:
            sd_path = out_dir / 'policy_state_dict.pt'
            torch.save(model.policy.state_dict(), str(sd_path))
            logger.info('Saved policy state_dict to %s', sd_path)
        except Exception as e_sd:
            logger.exception('Failed to save state_dict: %s', e_sd)

        return True
    except Exception as e:
        logger.exception('Error while exporting policy: %s', e)
        return False


if __name__ == '__main__':
    zip_path = Path('src/model/ppo_custom_deep_portfolio_agent.zip')
    out_dir = Path('out/sb3_export')
    ok = export_policy(zip_path, out_dir)
    if ok:
        logger.info('Export completed')
    else:
        logger.error('Export failed')