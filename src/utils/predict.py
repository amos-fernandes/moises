import numpy as np
import tensorflow as tf
from app.model.preprocess import preprocess_input_data

model = tf.keras.models.load_model("app/model/model.h5")

def predict_quality(raw_data):
    processed = preprocess_input_data(raw_data)
    preds = model.predict(processed)
    return [int(p > 0.5) for p in preds]


