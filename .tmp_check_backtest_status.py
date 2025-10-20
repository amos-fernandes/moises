import json
from importlib import import_module
m = import_module('endpoints.backtest_status')
# call function
import asyncio
res = asyncio.get_event_loop().run_until_complete(m.backtest_status())
print(json.dumps(res, indent=2)
)
