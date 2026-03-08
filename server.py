from flask import Flask, jsonify, request
from flask_cors import CORS
import requests, os

app = Flask(__name__)
CORS(app)  # Permite llamadas desde cualquier origen

# ─── YAHOO FINANCE ────────────────────────────────────────────────────────
def fetch_yahoo(symbol, range_='1mo', interval='1d'):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    params  = {'interval': interval, 'range': range_}
    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def parse_yahoo(data):
    res = data['chart']['result'][0]
    ts  = res['timestamp']
    q   = res['indicators']['quote'][0]
    candles, closes = [], []
    for i in range(len(ts)):
        if not q['close'][i] or not q['open'][i]:
            continue
        from datetime import datetime, timezone
        d = datetime.fromtimestamp(ts[i], tz=timezone.utc).strftime('%Y-%m-%d')
        candles.append({
            'date':  d,
            'open':  round(q['open'][i],  4),
            'high':  round(q['high'][i],  4),
            'low':   round(q['low'][i],   4),
            'close': round(q['close'][i], 4),
        })
        closes.append(round(q['close'][i], 4))
    meta  = res['meta']
    price = meta.get('regularMarketPrice') or (closes[-1] if closes else 0)
    prev  = meta.get('chartPreviousClose') or (closes[-2] if len(closes)>1 else price)
    chg   = round((price - prev) / prev * 100, 2) if prev else 0
    return {'price': price, 'chg24h': chg, 'candles': candles, 'closes': closes}

# ─── ROUTES ───────────────────────────────────────────────────────────────

@app.route('/api/asset')
def asset():
    """
    ?symbol=GC=F   → Oro
    ?symbol=CL=F   → Petróleo WTI
    ?symbol=SPY    → S&P 500
    ?symbol=USDCOP=X → USD/COP
    ?symbol=EURCOP=X → EUR/COP
    """
    symbol = request.args.get('symbol', 'GC=F')
    days   = request.args.get('days', '30')
    range_map = {'7':'1mo','14':'1mo','30':'1mo','90':'3mo','365':'1y'}
    rng = range_map.get(days, '1mo')
    try:
        raw  = fetch_yahoo(symbol, range_=rng)
        data = parse_yahoo(raw)
        return jsonify({'ok': True, 'data': data})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/crypto')
def crypto():
    """CoinGecko proxy — Bitcoin, Ethereum con sparkline"""
    ids = request.args.get('ids', 'bitcoin,ethereum')
    url = f'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'ids': ids,
        'sparkline': 'true',
        'price_change_percentage': '24h'
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return jsonify({'ok': True, 'data': r.json()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/fx')
def fx():
    """Tipos de cambio reales"""
    try:
        r = requests.get('https://open.er-api.com/v6/latest/USD', timeout=10)
        r.raise_for_status()
        return jsonify({'ok': True, 'data': r.json()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/feargreed')
def feargreed():
    """Fear & Greed Index"""
    try:
        r = requests.get('https://api.alternative.me/fng/?limit=1&format=json', timeout=10)
        r.raise_for_status()
        d = r.json()
        return jsonify({'ok': True, 'data': d['data'][0]})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'TradeBot Server funcionando'})

@app.route('/')
def index():
    return jsonify({'name': 'TradeBot Pro API', 'version': '1.0', 'status': 'online'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
