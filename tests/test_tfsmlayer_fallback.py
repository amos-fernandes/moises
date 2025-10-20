import importlib
import types
import pytest

rnn = importlib.import_module('src.model.rnn_predictor')


class DummyLayer:
    def __init__(self, path, call_endpoint='serving_default'):
        self.path = path
        self.call_endpoint = call_endpoint
        self.input_shape = (None, 60, 18)
    def __call__(self, inputs):
        import tensorflow as _tf
        # passthrough: return inputs unchanged (shape-preserving)
        return inputs


def test_tfsmlayer_fallback(monkeypatch):
    # Simulate load_model raising an error
    tf_mod = importlib.import_module('tensorflow')

    def fake_load_model(path):
        raise ValueError('simulated load failure')

    monkeypatch.setattr(tf_mod.keras.models, 'load_model', fake_load_model)

    # Provide a fake keras.layers.TFSMLayer
    keras_mod = importlib.import_module('keras')
    monkeypatch.setattr(keras_mod.layers, 'TFSMLayer', DummyLayer)

    # Prevent actual scaler loading from disk by monkeypatching load_scalers to return
    # simple fitted MinMaxScaler instances with expected widths.
    from sklearn.preprocessing import MinMaxScaler
    import numpy as np
    pv_s = MinMaxScaler()
    pv_s.fit(np.zeros((2, 27)))
    ind_s = MinMaxScaler()
    ind_s.fit(np.zeros((2, 36)))
    monkeypatch.setattr(rnn, 'load_scalers', lambda model_dir, a, b: (pv_s, ind_s, {'pv_n_features':27, 'ind_n_features':36}))

    predictor = rnn.RNNModelPredictor(model_dir='src/model', logger_instance=None)
    # Call loader; it should catch load_model failure and attempt fallback
    predictor._load_model_and_scalers()

    # After fallback, predictor.model should be set to a dummy object with input_shape attr
    assert predictor.model is not None
    assert hasattr(predictor.model, 'input_shape')
    assert predictor.model.input_shape == (None, 60, 18)


def test_tfsmlayer_wrapper_creates_keras_model(monkeypatch):
    # This test will monkeypatch load_model to fail and provide a fake TFSMLayer
    # that behaves like a Keras Layer (callable on tensors) so the fallback can
    # build a small Keras Model around it.
    tf_mod = importlib.import_module('tensorflow')

    def fake_load_model(path):
        raise ValueError('simulated load failure')

    monkeypatch.setattr(tf_mod.keras.models, 'load_model', fake_load_model)

    # Create a fake Keras layer class that can be instantiated and called on tensors
    class FakeKerasLayer:
        def __init__(self, path, call_endpoint='serving_default'):
            self.path = path

        def __call__(self, inputs):
            import tensorflow as _tf
            # For testing, just return inputs passed through a small Dense layer
            x = _tf.keras.layers.TimeDistributed(_tf.keras.layers.Dense(1))(inputs)
            return x

    keras_mod = importlib.import_module('keras')
    monkeypatch.setattr(keras_mod.layers, 'TFSMLayer', FakeKerasLayer)

    # Prevent actual scaler loading
    from sklearn.preprocessing import MinMaxScaler
    import numpy as np
    pv_s = MinMaxScaler()
    pv_s.fit(np.zeros((2, 27)))
    ind_s = MinMaxScaler()
    ind_s.fit(np.zeros((2, 36)))
    monkeypatch.setattr(rnn, 'load_scalers', lambda model_dir, a, b: (pv_s, ind_s, {'pv_n_features':27, 'ind_n_features':36}))

    predictor = rnn.RNNModelPredictor(model_dir='src/model', logger_instance=None)
    predictor._load_model_and_scalers()

    # Should be a Keras Model instance
    import tensorflow as _tf
    assert isinstance(predictor.model, _tf.keras.Model)

    # Call predict on a dummy input with shape (1, WINDOW_SIZE, num_features)
    num_features = len(rnn.EXPECTED_SCALED_FEATURES_FOR_MODEL)
    import numpy as np
    dummy = np.random.rand(1, rnn.WINDOW_SIZE, num_features).astype('float32')
    out = predictor.model.predict(dummy)
    assert out is not None
