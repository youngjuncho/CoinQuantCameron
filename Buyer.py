import ccxt
import pandas as pd
import pandas_ta as ta


def check_divergence(df):
    """최근 30일 내 상승 다이버전스 여부 판단"""
    # 가격 저점과 RSI 저점 비교 (최근 30일 데이터)
    current_low = df['low'].iloc[-1]
    prev_low = df['low'].iloc[-30:-5].min()

    current_rsi = df['RSI'].iloc[-1]
    prev_rsi = df['RSI'].iloc[-30:-5].min()

    # 상승 다이버전스: 가격은 낮아졌는데, RSI는 높아진 상태
    if current_low < prev_low and current_rsi > prev_rsi:
        return True
    return False


def scan_integrated():
    exchange = ccxt.bithumb()
    try:
        markets = exchange.fetch_tickers()
        krw_symbols = [s for s in markets.keys() if s.endswith('/KRW')]
        top_50 = sorted(krw_symbols, key=lambda x: markets[x]['quoteVolume'], reverse=True)[:50]
    except Exception as e:
        print(f"❌ 데이터 로딩 실패: {e}")
        return

    print(f"🔍 [통합 분석] 50개 종목 스캔 중 (일봉 기준)...\n")
    print("1단계 (RSI 과매도): 최근 15일 내 RSI 30 미만 경험 (공포 구간 통과 중)")
    print("2단계 (BB 하단이탈): 최근 10일 내 볼린저밴드 하단 터치 (과도한 투매 발생)")
    print("3단계 (MACD 반전): MACD가 시그널선을 상향 돌파 (하락 에너지 소멸 및 반등)")
    print("4단계 (현재 양봉): 오늘의 캔들이 양봉 (실제 매수세가 유입되는 확정 신호)\n")

    all_results = []
    for symbol in top_50:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=100)
            if len(ohlcv) < 30: continue

            df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
            df['RSI'] = ta.rsi(df['close'], length=14)
            macd = ta.macd(df['close'])
            df['MACD'] = macd.iloc[:, 0]
            df['MACD_S'] = macd.iloc[:, 2]
            bb = ta.bbands(df['close'], length=20, std=2)
            df['BBL'] = bb.iloc[:, 0]

            curr = df.iloc[-1]
            # 단계별 체크 (bool 리스트로 관리)
            s1 = df['RSI'].iloc[-15:].min() < 30
            s2 = (df['low'].iloc[-10:] < df['BBL'].iloc[-10:]).any()
            s3 = curr['MACD'] > curr['MACD_S']
            s4 = curr['close'] > curr['open']

            has_div = check_divergence(df)
            score = sum([s1, s2, s3, s4])

            all_results.append({
                'symbol': symbol, 'score': score, 'div': has_div, 'rsi': round(curr['RSI'], 1),
                'steps': [s1, s2, s3, s4], 'price': curr['close']
            })
        except:
            continue

    # 1. 통합 리스트 출력
    print(f"{'종목':<10} | {'점수'} | {'상태':<14} | {'다이버':<5} | {'RSI':<5}")
    print("-" * 65)
    for r in all_results:
        steps_str = "".join(["✅" if s else "❌" for s in r['steps']])
        div_str = " ⚡" if r['div'] else "  -  "

        # 3점 이상이거나 다이버전스가 있는 유의미한 종목만 강조 출력
        if r['score'] >= 3 or r['div']:
            print(f"{r['symbol']:<12} |  {r['score']}  | {steps_str:<14} | {div_str:<5} | {r['rsi']:<5}")

    # 2. 단계별 튜토리얼 (설명창)
    print("\n" + "=" * 65)
    print("📖 [단계별 가이드]")
    print("1단계: RSI 30 미만(공포) |  2단계: BB하단 터치(투매)")
    print("3단계: MACD 반전(에너지) |  4단계: 현재 양봉(확정)")
    print("⚡다이버전스: 가격 저점은 낮아지나 지표는 상승 (강력한 반전 신호)")
    print("=" * 65)

    # 3. 최종 요약
    super_spot = [r['symbol'] for r in all_results if r['score'] == 4 and r['div']]
    if super_spot:
        print(f"\n💎 [슈퍼 타점 포착!] 4점 만점 + 다이버전스: {', '.join(super_spot)}")
    else:
        print("\n🔔 현재 모든 조건을 동시에 만족하는 '슈퍼 타점' 종목은 없습니다.")


scan_integrated()
