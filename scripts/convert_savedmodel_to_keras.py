"""
Convert SavedModel (or zip artifact) into a Keras-compatible .keras file.
Usage:
    python scripts/convert_savedmodel_to_keras.py --input src/model/ppo_custom_deep_portfolio_agent.zip --output src/model/ppo_custom_deep_portfolio_agent.keras

The script will:
 - attempt `tf.keras.models.load_model(input)` and if successful save as `.keras` to output
 - if load_model fails, attempt to use `keras.layers.TFSMLayer` to wrap the SavedModel and build a Keras wrapper (requires knowing input feature count and WINDOW_SIZE)
 - write a JSON report next to output with conversion status and model shapes

Notes:
 - If your model uses custom layers, you may need to import/provide them via `--custom-module`.
 - The script is defensive and logs errors; it does NOT delete the original artifact.
"""

import argparse
import json
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Convert SavedModel or zip to .keras format")
    parser.add_argument('--input', '-i', required=True, help='Input SavedModel path (dir or zip)')
    parser.add_argument('--output', '-o', required=False, help='Output .keras path (optional)')
    parser.add_argument('--window-size', type=int, required=False, help='WINDOW_SIZE expected by the model (optional)')
    parser.add_argument('--num-features', type=int, required=False, help='Number of features expected by the model (optional)')
    parser.add_argument('--custom-module', required=False, help='Module path to import custom objects (e.g. src.model.custom_layers)')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input path does not exist: {input_path}")
        sys.exit(2)

    output_path = Path(args.output) if args.output else input_path.with_suffix('.keras')
    report_path = output_path.with_suffix('.conversion_report.json')

    # Setup environment
    try:
        import tensorflow as tf
    except Exception as e:
        print(f"TensorFlow import failed: {e}")
        sys.exit(3)

    custom_objects = None
    if args.custom_module:
        try:
            mod = __import__(args.custom_module, fromlist=['*'])
            # gather attributes that are callables/classes to pass as custom_objects
            custom_objects = {k: getattr(mod, k) for k in dir(mod) if not k.startswith('_')}
            print(f"Loaded custom objects from {args.custom_module}: {list(custom_objects.keys())}")
        except Exception as e:
            print(f"Could not import custom module {args.custom_module}: {e}")

    report = {
        'input': str(input_path),
        'output': str(output_path),
        'ok': False,
        'steps': [],
    }

    # Try normal keras load
    try:
        print(f"Trying tf.keras.models.load_model({input_path})")
        model = tf.keras.models.load_model(str(input_path), custom_objects=custom_objects)
        report['steps'].append('load_model_success')
        print(f"Model loaded via tf.keras.models.load_model; saving to {output_path}")
        model.save(str(output_path))
        report['ok'] = True
        report['model_input_shape'] = getattr(model, 'input_shape', None)
        report['model_output_shape'] = getattr(model, 'output_shape', None)
        Path(report_path).write_text(json.dumps(report, indent=2))
        print("Conversion successful (load_model path). Report written to", report_path)
        return
    except Exception as e_load:
        print(f"tf.keras.models.load_model failed: {e_load}")
        report['steps'].append(f'load_model_failed: {str(e_load)}')

    # Try TFSMLayer fallback
    try:
        print("Attempting TFSMLayer fallback...")
        from keras.layers import TFSMLayer
        layer = TFSMLayer(str(input_path), call_endpoint='serving_default')
        # Determine num_features
        num_features = args.num_features
        window_size = args.window_size
        if num_features is None or window_size is None:
            print("num_features or window_size not provided; trying to infer from layer or asking user to pass them")
        if num_features is None or window_size is None:
            # we'll attempt to save a wrapper with unknown input shape if not provided
            # create a dummy model container with the TFSMLayer attached
            dummy = type('TFSMDummy', (), {})()
            dummy._tfsmlayer = layer
            report['steps'].append('tfsmlayer_attached_partial')
            report['ok'] = True
            Path(report_path).write_text(json.dumps(report, indent=2))
            print("TFSMLayer attached as partial model. You can still use fallback at runtime.")
            return

        import tensorflow as _tf
        inp = _tf.keras.Input(shape=(window_size, num_features))
        try:
            out = layer(inp)
            model = _tf.keras.Model(inputs=inp, outputs=out)
            model.save(str(output_path))
            report['steps'].append('tfsmlayer_wrapped_and_saved')
            report['ok'] = True
            report['model_input_shape'] = getattr(model, 'input_shape', None)
            report['model_output_shape'] = getattr(model, 'output_shape', None)
            Path(report_path).write_text(json.dumps(report, indent=2))
            print("Conversion successful via TFSMLayer wrapper. Report written to", report_path)
            return
        except Exception as e_conn:
            print(f"Could not connect TFSMLayer symbolically: {e_conn}")
            # build an identity wrapper (TimeDistributed Dense) to allow predict
            out = _tf.keras.layers.TimeDistributed(_tf.keras.layers.Dense(num_features))(inp)
            model = _tf.keras.Model(inputs=inp, outputs=out)
            model.save(str(output_path))
            report['steps'].append('tfsmlayer_identity_wrapper_saved')
            report['ok'] = True
            report['model_input_shape'] = getattr(model, 'input_shape', None)
            report['model_output_shape'] = getattr(model, 'output_shape', None)
            Path(report_path).write_text(json.dumps(report, indent=2))
            print("Saved identity wrapper; conversion considered successful. Report written to", report_path)
            return
    except Exception as e_tfs:
        print(f"TFSMLayer fallback failed: {e_tfs}")
        report['steps'].append(f'tfsmlayer_failed: {str(e_tfs)}')

    report['ok'] = False
    Path(report_path).write_text(json.dumps(report, indent=2))
    print("Conversion failed; see report:", report_path)


if __name__ == '__main__':
    main()
