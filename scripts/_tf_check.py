import sys
try:
    import tensorflow as tf
    print('OK', tf.__version__)
except Exception as e:
    print('ERROR', repr(e))
    sys.exit(2)
