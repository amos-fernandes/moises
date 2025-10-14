import ccxt

class MarketMaker:
    def __init__(self, exchange, symbol, spread=0.01):
        self.exchange = ccxt.exchange({'apiKey': '...', 'secret': '...'})
        self.symbol = symbol
        self.spread = spread

    def place_orders(self):
        ticker = self.exchange.fetch_ticker(self.symbol)
        mid_price = (ticker['bid'] + ticker['ask']) / 2

        bid_price = mid_price * (1 - self.spread / 2)
        ask_price = mid_price * (1 + self.spread / 2)

        self.exchange.create_limit_buy_order(self.symbol, 1, bid_price)
        self.exchange.create_limit_sell_order(self.symbol, 1, ask_price)

    def run(self):
        while True:
            try:
                self.place_orders()
                time.sleep(60)  # Atualiza ordens a cada minuto
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    market_maker = MarketMaker("binance", "I*****ME/USDT")
    market_maker.run()