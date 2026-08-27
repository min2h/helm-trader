from __future__ import annotations

import argparse
import json

from helm.ai.reporter import render_daily_report, write_report
from helm.config.store import ParamsStore
from helm.research.data import fetch_klines, save_klines
from helm.research.donchian import backtest_donchian
from helm.settings import get_settings


def _public_ip() -> str | None:
    try:
        import httpx

        return httpx.get("https://api.ipify.org", timeout=5.0).text.strip() or None
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="helm")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("api")
    sub.add_parser("bot")
    sub.add_parser("engine")
    sub.add_parser("ai-batch")

    dl = sub.add_parser("download")
    dl.add_argument("--symbol", default="BTCUSDT")
    dl.add_argument("--interval", default="15m")
    dl.add_argument("--market", default="futures")
    dl.add_argument("--limit", type=int, default=1000)

    bt = sub.add_parser("backtest")
    bt.add_argument("--symbol", default="BTCUSDT")
    bt.add_argument("--interval", default="15m")
    bt.add_argument("--market", default="futures")

    args = parser.parse_args(argv)
    settings = get_settings()

    if args.cmd == "api":
        import uvicorn
        from helm.api.app import create_app

        print(f"helm api bind {settings.helm_host}:{settings.helm_port}")
        print(f"local  http://127.0.0.1:{settings.helm_port}")
        public = _public_ip()
        if public:
            print(f"public http://{public}:{settings.helm_port}  (공유기에서 이 포트 inbound 필요)")
        uvicorn.run(create_app(settings), host=settings.helm_host, port=settings.helm_port)
        return 0

    if args.cmd == "bot":
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            raise SystemExit("set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        from helm.actors.control_actor import ControlActor
        from helm.notify.telegram_bot import build_application

        actor = ControlActor(ParamsStore(settings.params_path))
        app = build_application(actor, settings.telegram_bot_token, settings.telegram_chat_id)
        app.run_polling()
        return 0

    if args.cmd == "engine":
        from helm.engine.node import run_live_node

        run_live_node(settings)
        return 0

    if args.cmd == "ai-batch":
        store = ParamsStore(settings.params_path)
        params = store.load()
        text = render_daily_report(
            params,
            daily_pnl_pct=0.0,
            trades=0,
            ai_status="skipped" if settings.helm_llm_provider == "off" else "manual",
            notes=["LLM skipped or not configured; engine keeps last params"],
        )
        path = write_report(text, settings.reports_dir)
        params.ai.last_status = "skipped"
        store.save(params)
        print(path)
        return 0

    if args.cmd == "download":
        frame = fetch_klines(args.symbol, args.interval, limit=args.limit, market=args.market)
        path = settings.research_dir / f"{args.market}_{args.symbol}_{args.interval}.parquet"
        save_klines(frame, path)
        print(path, len(frame))
        return 0

    if args.cmd == "backtest":
        from helm.research.data import load_klines

        path = settings.research_dir / f"{args.market}_{args.symbol}_{args.interval}.parquet"
        frame = load_klines(path) if path.exists() else fetch_klines(args.symbol, args.interval, market=args.market)
        result = backtest_donchian(frame)
        print(json.dumps(result.__dict__, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
