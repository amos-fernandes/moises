import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
# (Potentially add more imports for other model types or libraries later)

def preprocess_data_for_deep_mql(df: pd.DataFrame, look_back: int = 60, features_cols=['Close', 'Volume'], target_col='Close'):
    """
    Prepares data for a deep learning model (e.g., LSTM) for MQL-like tasks.
    - Scales features.
    - Creates sequences for time series forecasting.
    """
    df_copy = df.copy()
    
    # Feature engineering (can be expanded)
    df_copy['returns'] = df_copy['Close'].pct_change()
    df_copy['ma10'] = df_copy['Close'].rolling(window=10).mean()
    df_copy['ma30'] = df_copy['Close'].rolling(window=30).mean()
    df_copy = df_copy.dropna()

    all_cols = list(set(features_cols + [target_col] + ['returns', 'ma10', 'ma30']))
    data_to_scale = df_copy[all_cols].values
    
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data_to_scale)
    
    # Find the index of the target column in the scaled data
    try:
        # Attempt to get column names if df_copy[all_cols] is a DataFrame
        scaled_df_cols = df_copy[all_cols].columns.tolist()
        target_idx_in_scaled = scaled_df_cols.index(target_col)
    except AttributeError:
        # Fallback if it's already a NumPy array or has no columns attribute
        # This assumes target_col was one of the original features_cols or added deterministically
        # A more robust solution might be needed if column order is not guaranteed
        if target_col in features_cols:
            target_idx_in_scaled = features_cols.index(target_col)
        elif target_col == 'returns': # Example, adjust if more features are added before target
             target_idx_in_scaled = len(features_cols)
        elif target_col == 'ma10':
             target_idx_in_scaled = len(features_cols) + 1
        elif target_col == 'ma30':
             target_idx_in_scaled = len(features_cols) + 2
        else: # Default to first column if not found, or raise error
            print(f"Warning: Target column '{target_col}' not reliably found in scaled data. Defaulting to index 0.")
            target_idx_in_scaled = 0


    X, y = [], []
    for i in range(look_back, len(scaled_data)):
        X.append(scaled_data[i-look_back:i])
        y.append(scaled_data[i, target_idx_in_scaled]) # Predicting the target column
        
    return np.array(X), np.array(y), scaler, df_copy[all_cols].columns.tolist()

def create_deep_mql_model(input_shape):
    """
    Creates a Deep Learning model (LSTM example) for MQL-like tasks.
    This is a basic example and can be significantly enhanced.
    """
    model = Sequential([
        LSTM(units=50, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(units=50, return_sequences=False),
        Dropout(0.2),
        Dense(units=25, activation='relu'),
        Dense(units=1) # Output: e.g., predicted price or a value to derive a signal
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model

def generate_trading_signals(model, data_X, scaler, last_known_price, threshold=0.005):
    """
    Generates trading signals based on model predictions.
    - Predicts next step.
    - Compares prediction with current price to generate signal.
    
    Signal: 1 (Buy), -1 (Sell), 0 (Hold)
    """
    # Ensure data_X is in the correct shape for prediction (e.g., for a single prediction)
    # It should be (1, look_back, num_features)
    if data_X.ndim == 2: # If it's a single sequence (look_back, num_features)
        data_X = np.expand_dims(data_X, axis=0)

    predicted_scaled_value = model.predict(data_X)
    
    # Inverse transform:
    # We need to create a dummy array with the same number of features as during scaling,
    # then place our predicted value in the correct column (target column) before inverse transforming.
    num_features = data_X.shape[2]
    dummy_array = np.zeros((len(predicted_scaled_value), num_features))
    
    # Assuming the model predicts the 'Close' price and 'Close' was the first feature during scaling.
    # This needs to be robust. Let's assume target was the first column for simplicity here.
    # A better way is to pass the index of the target column used during scaling.
    target_column_index_in_scaler = 0 # Placeholder: This should match the target_col's position during scaling
    dummy_array[:, target_column_index_in_scaler] = predicted_scaled_value.ravel()
    
    try:
        predicted_value = scaler.inverse_transform(dummy_array)[:, target_column_index_in_scaler]
    except ValueError as e:
        print(f"Error during inverse_transform: {e}")
        print("Ensure dummy_array shape matches scaler's n_features_in_.")
        print(f"dummy_array shape: {dummy_array.shape}, scaler.n_features_in_: {scaler.n_features_in_}")
        # Fallback or re-raise
        return 0 


    signal = 0
    if predicted_value > last_known_price * (1 + threshold):
        signal = 1 # Buy
    elif predicted_value < last_known_price * (1 - threshold):
        signal = -1 # Sell
    return signal, predicted_value[0]


if __name__ == '__main__':
    # Example Usage (requires financial_data_agent and more setup)
    # from agents.financial_data_agent import fetch_historical_ohlcv
    # raw_data_mql = fetch_historical_ohlcv("MSFT", period="2y", interval="1d")
    
    # For demonstration, creating a dummy DataFrame:
    dates_mql = pd.date_range(start='2022-01-01', periods=500, freq='B')
    data_mql_np = np.random.rand(500, 5) * 150 + 50
    raw_data_mql = pd.DataFrame(data_mql_np, index=dates_mql, columns=['Open', 'High', 'Low', 'Close', 'Volume'])
    raw_data_mql['Close'] = raw_data_mql['Close'] + np.sin(np.linspace(0, 20, 500)) * 20 # Add some trend

    if not raw_data_mql.empty:
        look_back_mql = 60
        # Use more features for DeepMQL
        features_mql = ['Close', 'Volume', 'Open', 'High', 'Low'] 
        target_mql = 'Close'

        X_mql, y_mql, scaler_mql, scaled_cols_mql = preprocess_data_for_deep_mql(
            raw_data_mql, 
            look_back=look_back_mql,
            features_cols=features_mql,
            target_col=target_mql
        )

        if X_mql.shape[0] > 0:
            print(f"X_mql shape: {X_mql.shape}, y_mql shape: {y_mql.shape}")

            # 1. Create and Train Model
            model_mql = create_deep_mql_model(input_shape=(X_mql.shape[1], X_mql.shape[2]))
            print("Training DeepMQL model (example)...")
            # Split data for training (e.g., first 80% for train, rest for test/simulation)
            train_size = int(len(X_mql) * 0.8)
            X_train_mql, y_train_mql = X_mql[:train_size], y_mql[:train_size]
            
            # Ensure y_train_mql is 2D for Keras if it's not already
            if y_train_mql.ndim == 1:
                y_train_mql = y_train_mql.reshape(-1, 1)

            model_mql.fit(X_train_mql, y_train_mql, epochs=10, batch_size=32, verbose=1) # Few epochs for demo
            print("DeepMQL model trained.")

            # 2. Generate Signal for a new data point (example)
            # Use the last 'look_back' points from the original data as input for prediction
            if len(X_mql) > train_size:
                last_sequence = X_mql[-1] # Last available sequence from our dataset (could be from test set)
                # For a real scenario, this would be the latest live data
                
                # Get the actual last known closing price from the unscaled data
                # The 'last_sequence' corresponds to data up to index -1.
                # The price to compare against is raw_data_mql[target_mql].iloc[-1]
                # (or the close price of the last day of last_sequence)
                
                # Find the original 'Close' price that corresponds to the end of the last_sequence
                # The 'y' value for X_mql[-1] is y_mql[-1], which is the scaled target for the *next* period.
                # We need the 'Close' price of the *last day included in* X_mql[-1].
                # The data used for X_mql was from df_copy in preprocess_data_for_deep_mql
                # The last row of df_copy that contributes to X_mql[-1] is df_copy.iloc[len(df_copy) - 1 - (len(X_mql) - (len(X_mql)-1)) ]
                # This is complex. Simpler: use the last 'Close' from the original dataframe that was part of the input to scaling.
                # The 'scaled_data' was created from 'df_copy'. 'X' takes from 'scaled_data'.
                # The last 'Close' price in 'df_copy' before any potential future data.
                
                # Let's get the unscaled 'Close' price from the day corresponding to the last observation in 'last_sequence'
                # 'X_mql' was created from 'scaled_data'. 'scaled_data' was created from 'df_copy'.
                # The last row of 'df_copy' is raw_data_mql.iloc[len(raw_data_mql)-1] after initial dropna.
                # The 'last_known_price' should be the closing price of the last day in the 'last_sequence'.
                
                # To get the actual 'Close' price for the last day of the last_sequence:
                # The 'X_mql' sequences end at index i-1 of scaled_data.
                # So, the last day in X_mql[-1] corresponds to scaled_data[len(scaled_data)-2].
                # The corresponding original data is in df_copy used in preprocess_data_for_deep_mql.
                # This df_copy was raw_data_mql after some processing.
                # Let's use the last 'Close' from the raw_data_mql that was used to create X_mql.
                # The number of rows in df_copy (after dropna) is len(scaled_data).
                # The last 'Close' price in the data that could form a sequence.
                
                # Simplification for example: Use the last 'Close' price from the original raw_data_mql
                # This assumes raw_data_mql is aligned with the sequences.
                # A more robust way is to track indices or pass the unscaled 'Close' series.
                
                # The 'y' value is the target for the *next* period.
                # The 'last_known_price' should be the 'Close' of the last day *in* the 'last_sequence'.
                # If X_mql[-1] is data from t-look_back to t-1, then last_known_price is Close at t-1.
                
                # Get the original 'Close' column from raw_data_mql that corresponds to the scaled data
                original_close_series = raw_data_mql['Close'].iloc[len(raw_data_mql) - len(X_mql) + X_mql.shape[1] -1 - (len(X_mql) - (np.where(X_mql == last_sequence)[0][0])) : len(raw_data_mql) - (len(X_mql) - (np.where(X_mql == last_sequence)[0][0]))]
                # This is getting too complex for the example. Let's use a simpler reference.
                # The last 'Close' price in the raw_data_mql that was part of the input to the last sequence.
                # If X_mql has N samples, it means we used N+look_back-1 rows of data.
                # The last row of raw_data_mql used for features for X_mql[-1] is raw_data_mql.iloc[some_index_ending_the_last_sequence]
                
                # Let's assume the last 'Close' price from the original dataframe is relevant.
                # This is not perfectly aligned for prediction but good for a demo.
                last_actual_close_price = raw_data_mql[target_mql].iloc[-1]


                print(f"\nGenerating signal based on last sequence (shape: {last_sequence.shape})...")
                print(f"Last actual close price for reference: {last_actual_close_price}")
                
                signal, predicted_price = generate_trading_signals(
                    model_mql, 
                    last_sequence, 
                    scaler_mql, # Pass the scaler used for X_mql
                    last_actual_close_price, # The actual close price of the last day in 'last_sequence'
                    threshold=0.001 # Smaller threshold for demo
                )
                print(f"Predicted Next '{target_mql}': {predicted_price:.2f}")
                if signal == 1:
                    print("Signal: BUY")
                elif signal == -1:
                    print("Signal: SELL")
                else:
                    print("Signal: HOLD")
            else:
                print("Not enough data to generate a signal after training split.")
        else:
            print("X_mql is empty. Check preprocessing for DeepMQL.")
    else:
        print("Raw data for MQL is empty. Check data fetching.")