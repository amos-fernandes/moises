from new_rede_a_portable_import import load_portable
p = load_portable()
mod = p.load_module('new-rede-a.portfolio_features_extractor_torch')
print('loaded module:', mod.__name__)
