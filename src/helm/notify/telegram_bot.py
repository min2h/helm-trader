from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from helm.actors.control_actor import ControlActor
from helm.api.sse import status_payload


def _allowed(chat_id: str, incoming: int) -> bool:
    return str(incoming) == str(chat_id)


def build_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("현황", callback_data="status")],
            [
                InlineKeyboardButton("소프트 정지", callback_data="soft_stop"),
                InlineKeyboardButton("재개", callback_data="resume"),
            ],
            [InlineKeyboardButton("전량 청산 (2단계)", callback_data="kill_prepare")],
            [InlineKeyboardButton("오늘 리포트", callback_data="report")],
        ]
    )


def format_status(actor: ControlActor) -> str:
    payload = status_payload(actor)
    return (
        f"run_state: {payload['run_state']}\n"
        f"daily_pnl: {payload['daily_pnl_pct']:.2f}%\n"
        f"positions: {payload['open_positions']}\n"
        f"heartbeat: {payload['heartbeat_at']}\n"
        f"ai: {payload['ai_last_status']}\n"
        f"symbols: {', '.join(payload['active_symbols'])}"
    )


def build_application(actor: ControlActor, token: str, chat_id: str) -> Application:
    app = Application.builder().token(token).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not _allowed(chat_id, update.effective_chat.id):
            return
        await update.effective_chat.send_message("helm-trader", reply_markup=build_keyboard())

    async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or not query.message or not _allowed(chat_id, query.message.chat_id):
            return
        await query.answer()
        data = query.data or ""
        if data == "status":
            await query.message.reply_text(format_status(actor), reply_markup=build_keyboard())
        elif data == "soft_stop":
            actor.soft_stop("telegram")
            await query.message.reply_text("소프트 정지: 신규 진입만 중단", reply_markup=build_keyboard())
        elif data == "resume":
            try:
                actor.resume("telegram")
                await query.message.reply_text("재개", reply_markup=build_keyboard())
            except RuntimeError as exc:
                await query.message.reply_text(str(exc), reply_markup=build_keyboard())
        elif data == "kill_prepare":
            token_payload = actor.prepare_hard_kill()
            context.user_data["kill_token"] = token_payload["token"]
            await query.message.reply_text(
                "5초 안에 확인을 누르세요. 전 포지션이 시장가 청산됩니다.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("정말 전량 청산", callback_data="kill_confirm")]]
                ),
            )
        elif data == "kill_confirm":
            token_value = context.user_data.get("kill_token", "")
            try:
                actor.confirm_hard_kill(str(token_value), "telegram")
                await query.message.reply_text("하드 킬 실행", reply_markup=build_keyboard())
            except PermissionError:
                await query.message.reply_text("확인 토큰 만료. 다시 시도하세요.", reply_markup=build_keyboard())
        elif data == "report":
            await query.message.reply_text(format_status(actor), reply_markup=build_keyboard())

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_callback))
    return app
