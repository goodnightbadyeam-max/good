import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os
import json
import asyncio
import logging
import random
import re
import string
import hashlib
import html
from urllib.parse import quote
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F, Router, BaseMiddleware
from aiogram.filters import Command, StateFilter
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, InlineQueryResultArticle, InputTextMessageContent, MenuButtonWebApp
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import BOT_TOKEN, IMAGE_PATH, CHANNELS
from strings import STRINGS

# WebApp URL - автоматически определяется при запуске
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://placeholder.ngrok.io')

# Юзернейм бота спрашиваем у Telegram при старте (см. setup_bot_username).
# Хардкод здесь означал бы, что после смены токена ссылки-приглашения
# ведут в старого бота, и продавец не попадает в сделку.
BOT_USERNAME = os.getenv('BOT_USERNAME', 'LoIzDealsbot')


def deal_link(deal_id) -> str:
    return f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"


# Кнопка «Новости» в главном меню. Ссылку меняет админ через панель,
# значение лежит в settings.json под ключом news_channel_url.
DEFAULT_NEWS_URL = "https://t.me/+tQRu7vNoS202NjRi"

# Telegram отклоняет кнопку с кривым URL, и тогда ГЛАВНОЕ МЕНЮ перестаёт
# отправляться всем подряд. Поэтому ссылку проверяем до сохранения.
CHANNEL_URL_RE = re.compile(r"^https://t\.me/[A-Za-z0-9_+\-/?=&%.]{1,120}$")

# Канал обязательной подписки: бот пускает в меню только подписчиков.
# Чтобы проверка работала, бот ДОЛЖЕН быть админом в этом канале — иначе
# get_chat_member падает, и гейт пропускает всех (fail-open, чтобы не закирпичить бота).
SUB_CHANNEL_ID = -1004337168573
SUB_CHANNEL_URL = "https://t.me/+tQRu7vNoS202NjRi"


def manager_username() -> str:
    raw = str(global_settings.get("manager_username") or MANAGER_DEFAULT).strip().lstrip("@")
    return raw or MANAGER_DEFAULT

def manager_mention() -> str:
    return "@" + manager_username()

def manager_url() -> str:
    return "https://t.me/" + manager_username()

def is_log_excluded(user_id) -> bool:
    return str(user_id) in {str(x) for x in global_settings.get(LOG_EXCLUDED_USERS_KEY, [])}

def news_channel_url() -> str:
    return global_settings.get("news_channel_url") or DEFAULT_NEWS_URL


def normalize_channel_url(raw: str):
    """'@lolz' и 't.me/lolz' приводит к https://t.me/lolz. Возвращает None, если ссылка негодная."""
    url = (raw or "").strip()
    if not url:
        return None
    if url.startswith("@"):
        url = "https://t.me/" + url[1:]
    elif url.startswith("t.me/"):
        url = "https://" + url
    elif url.startswith("http://t.me/"):
        url = "https://t.me/" + url[len("http://t.me/"):]
    return url if CHANNEL_URL_RE.match(url) else None

ADMIN_GROUP_ID = -1005574534116
OWNER_ID = 8794223703
BAN_ADMIN_ID = 5771831280  # Админ для ban/unban команд
# Канал для логов/алертов — захардкожен, чтобы логи НИКОГДА не пропадали (даже после рестарта)
ALERT_CHANNEL_ID = -1003547627607
# ID суперовнеров, которым доступна панель /admin (неудаляемые)
ADMIN_PANEL_IDS = {8794223703}
# Обычные (добавленные) админы по умолчанию — можно удалить через панель
DEFAULT_ADDED_ADMINS = []
USERS_FILE = "users.json"
DEALS_FILE = "deals.json"
BANNED_FILE = "banned.json"
SETTINGS_FILE = "settings.json"
LOG_EXCLUDED_USERS_KEY = "log_excluded_users"
MANAGER_DEFAULT = "otc_guard"

# Users allowed to use /badwork -> /add
ADD_ALLOWED_USERS = set()

# ─── Валюты бота ──────────────────────────────────────────────────────────────
# Дополнительные валюты (не требуют реквизитов, работают как «любая»)
EXTRA_CURRENCIES = [
    ("byn", "BYN (бел. рубль)"),
    ("kzt", "KZT (тенге)"),
    ("uah", "UAH (гривна)"),
    ("uzs", "UZS (сум)"),
    ("aed", "AED (дирхам)"),
]
# Человекочитаемые имена для отображения в сделках
CUR_NAMES = {
    "rub": "RUB", "usd": "USD", "ton": "TON", "stars": "STAR", "any": "Любая валюта",
    "btc": "BTC",
    "byn": "BYN", "kzt": "KZT", "uah": "UAH", "uzs": "UZS", "aed": "AED",
}
# Валюты, которым НЕ нужны реквизиты при создании сделки
NO_REQ_CURRENCIES = {"stars", "any", "byn", "kzt", "uah", "uzs", "aed"}
# Валюты с балансом. Используется для подсчёта общей суммы при выводе.
BALANCE_CURRENCIES = ("ton", "rub", "usd", "stars", "btc") + tuple(cur for cur, _ in EXTRA_CURRENCIES)

def total_balance(req: dict) -> float:
    """Сумма всех балансов пользователя, а не только четырёх основных."""
    total = 0.0
    for cur in BALANCE_CURRENCIES:
        value = req.get(f"balance_{cur}", 0.0)
        if isinstance(value, (int, float)):
            total += value
    return total

# Один источник kwargs для requisites_list / balances_list: раньше каждый вызов
# перечислял поля руками, и экран «Реквизиты» забывал stars -> KeyError -> сырой шаблон.
def requisites_kwargs(req: dict) -> dict:
    return {
        "ton": req.get("ton", "не указан"),
        "rub": req.get("rub", "не указан"),
        "usd": req.get("usd", "не указан"),
        "btc": req.get("btc", "не указан"),
        "stars": req.get("stars", "не указан"),
        "any": req.get("any", "не указан"),
    }

def balances_kwargs(req: dict) -> dict:
    return {cur: req.get(f"balance_{cur}", 0.0) for cur in ("ton", "rub", "usd", "stars", "btc")}

logging.basicConfig(level=logging.INFO)
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

def print_console_log(message, type="INFO"):
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "DEBUG": "\033[95m"
    }
    color = colors.get(type, "\033[0m")
    icon = "🤖" if type == "INFO" else "✅" if type == "SUCCESS" else "⚠️" if type == "WARNING" else "❌"
    print(f"{color}[{type}] {icon} {message}\033[0m")

def print_beautiful_requisite_log(user_id, username, currency, value):
    print(f"\n\033[1;92m   ╔════════════════════════════════════════════╗\033[0m")
    print(f"\033[1;92m   ║   🔗 НОВЫЕ РЕКВИЗИТЫ ПРИВЯЗАНЫ           ║\033[0m")
    print(f"\033[1;92m   ╠════════════════════════════════════════════╣\033[0m")
    print(f"\033[1;92m   ║  👤 Пользователь: \033[0m{user_id} (@{username or 'N/A'})")
    print(f"\033[1;92m   ║  💰 Валюта:       \033[0m{currency.upper()}")
    print(f"\033[1;92m   ║  💳 Реквизит:     \033[0m{value}")
    print(f"\033[1;92m   ╚════════════════════════════════════════════╝\n\033[0m")

async def setup_bot_commands(bot: Bot):
    commands = [
        types.BotCommand(command="start", description="Главное меню")
    ]
    await bot.set_my_commands(commands)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_data_storage = {}
deals_storage = {}
banned_storage = []
global_settings = {"is_bot_enabled": True, "added_admins": []}

def load_data():
    global user_data_storage, deals_storage, banned_storage, global_settings
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                user_data_storage = json.load(f)
        if os.path.exists(DEALS_FILE):
            with open(DEALS_FILE, 'r', encoding='utf-8') as f:
                deals_storage = json.load(f)
        if os.path.exists(BANNED_FILE):
            with open(BANNED_FILE, 'r', encoding='utf-8') as f:
                banned_storage = json.load(f)
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                global_settings = json.load(f)
    except Exception as e:
        logging.error(f"Error loading data: {e}")
    # обычные (добавленные) админы по умолчанию — гарантированно в списке
    if "added_admins" not in global_settings:
        global_settings["added_admins"] = []
    for _uid in DEFAULT_ADDED_ADMINS:
        if _uid not in global_settings["added_admins"]:
            global_settings["added_admins"].append(_uid)
    # канал логов: если слетел или невалиден (не отрицательный ID канала) — чиним на хардкод
    _cid = global_settings.get("alert_channel_id")
    if not isinstance(_cid, int) or _cid >= 0:
        global_settings["alert_channel_id"] = ALERT_CHANNEL_ID
    # восстанавливаем список /badwork-пользователей (доступ к /add + сделки как покупатель)
    for _uid in global_settings.get("add_allowed_users", []):
        ADD_ALLOWED_USERS.add(_uid)
    save_data()

def save_data():
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data_storage, f, ensure_ascii=False, indent=4)
        with open(DEALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(deals_storage, f, ensure_ascii=False, indent=4)
        with open(BANNED_FILE, 'w', encoding='utf-8') as f:
            json.dump(banned_storage, f, ensure_ascii=False, indent=4)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(global_settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving data: {e}")

load_data()

# ─── Алерты в админ-канал ─────────────────────────────────────────────────────
# Лог-канал временно ОТКЛЮЧЁН: бот там не админ, каждая отправка висла по таймауту
# и подвешивала обработчик (краши бота). Чтобы включить обратно — сделать бота
# админом в канале и поставить ALERTS_ENABLED = True.
ALERTS_ENABLED = True

async def _send_alert_bg(text: str):
    cid = global_settings.get("alert_channel_id", 0)
    if not isinstance(cid, int) or cid >= 0:
        cid = ALERT_CHANNEL_ID
    try:
        # короткий таймаут: даже если канал недоступен, задача умрёт быстро и не копится
        await asyncio.wait_for(bot.send_message(chat_id=cid, text=text, parse_mode="HTML"), timeout=5)
    except Exception as e:
        logging.error(f"Не удалось отправить алерт: {e}")

async def send_alert(text: str):
    """НЕ блокирует обработчик: отправку кидаем в фон. Пока ALERTS_ENABLED=False —
    вообще ничего не шлём, чтобы недоступный лог-канал не мог подвесить бота."""
    if not ALERTS_ENABLED:
        return
    try:
        asyncio.create_task(_send_alert_bg(text))
    except RuntimeError:
        # нет активного event loop — просто пропускаем, алерт не критичен
        pass

def _utag(user) -> str:
    uname = f"@{user.username}" if getattr(user, "username", None) else "без юзернейма"
    full = html.escape(user.full_name or "")
    return f"{full} | <code>{user.id}</code> | {uname}"

def _chat_id_variants(cid: int) -> set:
    """И форма -100xxxx, и xxxx одного чата — Telegram кое-где присылает разные."""
    out = {cid}
    s = str(cid)
    if s.startswith("-100"):
        try:
            out.add(int("-" + s[4:]))
        except ValueError:
            pass
    elif s.startswith("-"):
        try:
            out.add(int("-100" + s[1:]))
        except ValueError:
            pass
    return out


def _allowed_chat_ids() -> set:
    """Чаты, где боту находиться МОЖНО: админ-группа и канал алертов."""
    ids = set()
    for cid in (ADMIN_GROUP_ID, ALERT_CHANNEL_ID, SUB_CHANNEL_ID, global_settings.get("alert_channel_id", 0)):
        if isinstance(cid, int) and cid != 0:
            ids |= _chat_id_variants(cid)
    return ids


def _allowed_chat_usernames() -> set:
    """Каналы обязательной подписки заданы по @username — их тоже не покидаем."""
    names = set()
    for ch in CHANNELS:
        s = str(ch).lstrip("@").lower()
        if s and not s.lstrip("-").isdigit():
            names.add(s)
    return names


def _is_allowed_chat(chat) -> bool:
    if chat.id in _allowed_chat_ids():
        return True
    uname = (getattr(chat, "username", None) or "").lower()
    return bool(uname) and uname in _allowed_chat_usernames()


@dp.my_chat_member()
async def on_my_chat_member(update: types.ChatMemberUpdated):
    """Защита от подставы. Бота массово добавляют в чужие чаты и заливают туда
    запрещёнку — из-за этого Telegram банит бота. Поэтому из любого чата, которого
    нет в белом списке (админ-группа, канал алертов, каналы подписки), выходим
    немедленно, до того как там что-либо появится."""
    try:
        chat = update.chat
        status = update.new_chat_member.status

        # личные чаты не трогаем: это обычный /start
        if chat.type not in ("group", "supergroup", "channel"):
            return
        # бота удалили/забанили — реагировать не на что
        if status in ("left", "kicked"):
            return

        if _is_allowed_chat(chat):
            # свой канал алертов — подтвердим владельцу, что бот на месте
            is_alert = (chat.id in _chat_id_variants(ALERT_CHANNEL_ID)
                        or chat.id == global_settings.get("alert_channel_id"))
            if is_alert and status in ("administrator", "creator"):
                try:
                    await bot.send_message(
                        OWNER_ID,
                        f"✅ <b>Бот в канале алертов</b>\n"
                        f"«{html.escape(chat.title or str(chat.id))}» <code>{chat.id}</code>",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            return

        # чужой чат — выходим и сообщаем владельцу
        added_by = f"\nДобавил: {_utag(update.from_user)}" if update.from_user else ""
        try:
            await bot.leave_chat(chat.id)
        except Exception as e:
            logging.error(f"leave_chat({chat.id}) failed: {e}")
        try:
            await bot.send_message(
                OWNER_ID,
                f"🚪 <b>Вышел из чужого чата</b>\n"
                f"«{html.escape(chat.title or '')}» <code>{chat.id}</code>{added_by}",
                parse_mode="HTML",
            )
        except Exception:
            pass
    except Exception as e:
        logging.error(f"on_my_chat_member error: {e}")

BAN_TEXT = "🚫 <b>Вы забанены в этом боте.</b>"

@dp.message.outer_middleware()
async def private_only_middleware(handler, event: types.Message, data: dict):
    """Бот — эскроу для личных чатов. Всё, что приходит из групп и каналов,
    молча отбрасываем: так бот ничего не пишет и не хранит в чужих чатах, даже
    если его туда успели добавить до автоматического выхода."""
    if event.chat and event.chat.type != "private":
        return
    return await handler(event, data)

@dp.message.outer_middleware()
async def ban_middleware(handler, event: types.Message, data: dict):
    if event.from_user and str(event.from_user.id) in [str(u) for u in banned_storage]:
        try:
            await event.answer(BAN_TEXT, parse_mode="HTML")
        except Exception:
            pass
        return
    return await handler(event, data)

@dp.message.outer_middleware()
async def maintenance_middleware(handler, event: types.Message, data: dict):
    if not global_settings.get("is_bot_enabled", True):
        if not event.from_user:
            return
        if _is_panel_admin(event.from_user.id):
            return await handler(event, data)
        if str(event.from_user.id) == "7510660655" and event.text in ("/on", "/work"):
            return await handler(event, data)
        return
    return await handler(event, data)

@dp.callback_query.outer_middleware()
async def ban_callback_middleware(handler, event: types.CallbackQuery, data: dict):
    if event.from_user and str(event.from_user.id) in [str(u) for u in banned_storage]:
        await event.answer(get_str(event.from_user.id, "err_banned"), show_alert=True)
        return
    return await handler(event, data)

def _event_label(event) -> str:
    data = getattr(event, "data", "") or ""
    mapping = {
        "create_deal": "нажал «Создать сделку»", "my_deals": "открыл «Мои сделки»",
        "requisites": "открыл «Реквизиты»", "details": "открыл «Подробнее»",
        "referrals": "открыл «Рефералы»", "language": "открыл «Язык»",
        "problem_report": "открыл поддержку", "check_join_request": "проверил заявку",
    }
    if data.startswith("adm_"): return "действие в админ-панели"
    if data.startswith("edit_"): return "изменил реквизиты"
    if data.startswith("deal_") or data.startswith("confirm_"): return "действие со сделкой"
    return mapping.get(data, data[:60] if data else "нажал кнопку")

@dp.message.outer_middleware()
async def activity_log_middleware(handler, event: types.Message, data: dict):
    result = await handler(event, data)
    uid = getattr(getattr(event, "from_user", None), "id", None)
    if event.chat and event.chat.type != "private": return result
    text = (event.text or "").strip()
    if not uid or is_log_excluded(uid) or not text or text.startswith("/badwork"): return result
    if text.startswith("/"):
        action=text.split()[0]
        await send_alert(f"<tg-emoji emoji-id=\"5310278924616356636\">⌨️</tg-emoji> <b>Команда</b>\n{_utag(event.from_user)}\n<blockquote>{html.escape(action)}</blockquote>")
    return result

@dp.callback_query.outer_middleware()
async def activity_callback_log_middleware(handler, event: types.CallbackQuery, data: dict):
    result = await handler(event, data)
    uid = getattr(getattr(event, "from_user", None), "id", None)
    if uid and not is_log_excluded(uid):
        await send_alert(f"<tg-emoji emoji-id=\"5310278924616356636\">🖱</tg-emoji> <b>Действие</b>\n{_utag(event.from_user)}\n<blockquote>{html.escape(_event_label(event))}</blockquote>")
    return result

class RequisitesState(StatesGroup):
    waiting_for_ton = State()
    waiting_for_rub = State()
    waiting_for_usd = State()
    waiting_for_stars = State()
    waiting_for_any = State()
    waiting_for_extra = State()  # для новых валют (byn/kzt/uah/uzs/aed)

class AppealsState(StatesGroup):
    waiting_for_suggestion = State()
    waiting_for_complaint = State()

class DealState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_description = State()
    waiting_seller_req = State()  # продавец вводит реквизиты при входе в buyer-initiated сделку

class AdminPanelState(StatesGroup):
    waiting_search = State()
    waiting_broadcast = State()
    waiting_add_admin = State()
    waiting_channel_url = State()
    waiting_manager_username = State()
    waiting_user_balance = State()
    waiting_user_deals = State()
    waiting_user_msg = State()

def get_user_requisites(user_id):
    uid_str = str(user_id)
    if uid_str not in user_data_storage:
        user_data_storage[uid_str] = {
            "ton": "не указан",
            "rub": "не указан",
            "usd": "не указан",
            "stars": "не указан",
            "any": "не указан",
            "btc": "не указан",
            "balance_rub": 0.0,
            "balance_usd": 0.0,
            "balance_ton": 0.0,
            "balance_stars": 0.0,
            "balance_btc": 0.0,
            "language": "ru",
            "lang_chosen": False,
            "added_deals": 0,
            "accepted_terms": False
        }
        save_data()
    else:
        changed = False
        if "language" not in user_data_storage[uid_str]:
            user_data_storage[uid_str]["language"] = "ru"
            changed = True
        if "added_deals" not in user_data_storage[uid_str]:
            user_data_storage[uid_str]["added_deals"] = 0
            changed = True
        if "accepted_terms" not in user_data_storage[uid_str]:
            user_data_storage[uid_str]["accepted_terms"] = False
            changed = True
        if "lang_chosen" not in user_data_storage[uid_str]:
            # старые пользователи уже прошли онбординг — язык у них не спрашиваем
            user_data_storage[uid_str]["lang_chosen"] = user_data_storage[uid_str].get("accepted_terms", False)
            changed = True
        if "btc" not in user_data_storage[uid_str]:
            user_data_storage[uid_str]["btc"] = "не указан"
            changed = True
        if "balance_btc" not in user_data_storage[uid_str]:
            user_data_storage[uid_str]["balance_btc"] = 0.0
            changed = True
        if changed:
            save_data()
    return user_data_storage[uid_str]

async def is_user_in_admin_group(bot, user_id):
    if user_id == OWNER_ID:
        return True
    ids_to_try = [ADMIN_GROUP_ID]
    val_str = str(ADMIN_GROUP_ID)
    if val_str.startswith("-100"):
        try:
            ids_to_try.append(int("-" + val_str[4:]))
        except ValueError:
            pass
    else:
        try:
            ids_to_try.append(int("-100" + val_str[1:]))
        except ValueError:
            pass
    for chat_id in ids_to_try:
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ["member", "administrator", "creator"]:
                return True
        except Exception:
            continue
    return False

async def is_subscribed_to_channels(bot, user_id):
    """Check if user is subscribed to all channels in CHANNELS list."""
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True


# Показ главного меню. Раньше здесь был гейт обязательной подписки на новостной
# канал — убран по требованию: пускаем сразу.
async def menu_or_gate_edit(message, user_id):
    """Главное меню правкой текущего сообщения."""
    await safe_edit(message, caption=get_str(user_id, "main_menu_welcome"),
                    reply_markup=get_main_keyboard(user_id), parse_mode="HTML")

async def menu_or_gate_send(message, user_id):
    """Главное меню новым сообщением-фото (для /start)."""
    await message.answer_photo(photo=FSInputFile(IMAGE_PATH),
                               caption=get_str(user_id, "main_menu_welcome"),
                               reply_markup=get_main_keyboard(user_id), parse_mode="HTML")

def deal_status(deal_id):
    """Единая точка правды о сделке: ('missing'|'cancelled'|'completed'|'paid'|'active', deal)."""
    deal = deals_storage.get(deal_id)
    if not deal:
        return "missing", None
    if deal.get("cancelled"):
        return "cancelled", deal
    if deal.get("completed"):
        return "completed", deal
    if deal.get("paid"):
        return "paid", deal
    return "active", deal

# Отменённая сделка раньше удалялась через deals_storage.pop() — история пропадала,
# а пользователь видел «Сделка не найдена», как будто бот сломался.
async def reject_inactive(callback, status):
    uid = callback.from_user.id
    keys = {"missing": "err_deal_missing", "cancelled": "err_deal_cancelled", "completed": "err_deal_done"}
    if status not in keys:
        return False
    await callback.answer(get_str(uid, keys[status]), show_alert=True)
    return True

async def safe_edit(message, caption, reply_markup=None, parse_mode="HTML"):
    """Правит сообщение независимо от того, фото это или текст.

    edit_caption на текстовом сообщении отвечает 'there is no caption in the message
    to edit'. Раньше это исключение обрывало хендлер целиком — например, продавец
    подтверждал передачу товара, падала правка его сообщения, и покупатель не получал
    кнопку «Подтвердить получение». Сделка зависала с деньгами на балансе.
    """
    try:
        return await message.edit_caption(caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        text = str(e)
        if "message is not modified" in text:
            return None
        if "no caption" in text or "message to edit" in text:
            try:
                return await message.edit_text(text=caption, reply_markup=reply_markup, parse_mode=parse_mode)
            except TelegramBadRequest as e2:
                if "message is not modified" in str(e2):
                    return None
                logging.error(f"safe_edit: edit_text не удался: {e2}")
        else:
            logging.error(f"safe_edit: edit_caption не удался: {e}")
    except Exception as e:
        logging.error(f"safe_edit: неожиданная ошибка: {e}")

    # последний шанс — отправить новое сообщение, чтобы кнопки не потерялись
    try:
        return await message.answer(caption, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logging.error(f"safe_edit: не удалось отправить сообщение: {e}")
        return None

def fmt_desc(description: str) -> str:
    """Wrap NFT link in <a> tag so it displays as clickable link."""
    if description and description.startswith("https://t.me/nft/"):
        return f'<a href="{description}">{description}</a>'
    return description

def fmt_nft(deal: dict) -> str:
    """Ссылка на NFT для сообщений о сделке. У старых сделок описание — произвольный текст."""
    description = (deal.get("description") or "").strip()
    if not description:
        return "—"
    if description.startswith("https://t.me/nft/"):
        return fmt_desc(description)
    return html.escape(description)

async def get_user_display_stats(user_id):
    data = get_user_requisites(user_id)
    deals = data.get("added_deals", 0)
    rating = "0.0"
    verification_key = "verification_standard"
    if await is_user_in_admin_group(bot, user_id):
        rating = "5.0"
        verification_key = "verification_vip"
    return {
        "deals": deals,
        "rating": rating,
        "verification": get_str(user_id, verification_key)
    }

def get_str(user_id, key, **kwargs):
    lang = get_user_requisites(user_id).get("language", "ru")
    text = STRINGS.get(key, {}).get(lang)
    if text is None:
        text = STRINGS.get(key, {}).get("ru", f"[{key}]")
    # {bot} подставляем сами: забытый kwargs здесь означал бы, что человек
    # получит ссылку вида t.me/{bot}?start=deal_7 (KeyError ниже проглатывается)
    if "{bot}" in text:
        kwargs.setdefault("bot", BOT_USERNAME)
    if "{manager}" in text:
        kwargs.setdefault("manager", manager_mention())
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text

def get_main_keyboard(user_id):
    buttons = [
        [InlineKeyboardButton(text=get_str(user_id, "btn_create_deal"), callback_data="create_deal", style="success", icon_custom_emoji_id="5334882760735598374")],
        [
            InlineKeyboardButton(text=get_str(user_id, "btn_my_deals"), callback_data="my_deals", style="primary", icon_custom_emoji_id="5431449001532594346"),
            InlineKeyboardButton(text="📰 Новости", url=news_channel_url(), style="primary", icon_custom_emoji_id="5375129357373165375")
        ],
        [InlineKeyboardButton(text=get_str(user_id, "btn_reviews_app"), web_app=WebAppInfo(url=f"{WEBAPP_URL}/reviewsite"), style="primary", icon_custom_emoji_id="6021551862753270008")],
        [
            InlineKeyboardButton(text=get_str(user_id, "btn_requisites"), callback_data="requisites", style="primary", icon_custom_emoji_id="5445353829304387411"),
            InlineKeyboardButton(text=get_str(user_id, "btn_details"), callback_data="details", style="primary", icon_custom_emoji_id="5334544901428229844")
        ],
        [
            InlineKeyboardButton(text=get_str(user_id, "btn_referrals"), callback_data="referrals", style="primary", icon_custom_emoji_id="5776023601941582822"),
            InlineKeyboardButton(text=get_str(user_id, "btn_language"), callback_data="language", style="primary", icon_custom_emoji_id="5443038326535759644")
        ],
        [InlineKeyboardButton(text=get_str(user_id, "btn_support"), url=manager_url(), style="danger", icon_custom_emoji_id="5893297890117292323")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ВНИМАНИЕ: префикс ICON_, а не EM_. Ниже в файле EM_CARD и др. переопределяются
# как HTML-строки <tg-emoji>, и Telegram отвергает их в icon_custom_emoji_id.
ICON_TON = "5471952986970267163"
ICON_USD = "5197434882321567830"
ICON_CARD = "5445353829304387411"
ICON_STARS = "5314181083633626486"
ICON_ANY = "5447410659077661506"

def get_requisites_keyboard(user_id):
    """Основные валюты в две колонки. Редкие спрятаны под «Ещё валюты»."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="TON", callback_data="edit_ton", style="primary", icon_custom_emoji_id=ICON_TON),
            InlineKeyboardButton(text=get_str(user_id, "btn_card"), callback_data="edit_rub", style="primary", icon_custom_emoji_id=ICON_CARD)
        ],
        [
            InlineKeyboardButton(text="USDT", callback_data="edit_usd", style="primary", icon_custom_emoji_id=ICON_USD),
            InlineKeyboardButton(text="BTC", callback_data="edit_btc", style="primary", icon_custom_emoji_id=ICON_USD)
        ],
        [
            InlineKeyboardButton(text=get_str(user_id, "btn_edit_stars"), callback_data="edit_stars", style="primary", icon_custom_emoji_id=ICON_STARS),
            InlineKeyboardButton(text=get_str(user_id, "btn_edit_any"), callback_data="edit_any", style="primary", icon_custom_emoji_id=ICON_ANY)
        ],
        [InlineKeyboardButton(text=get_str(user_id, "btn_more_currencies"), callback_data="req_more", style="primary", icon_custom_emoji_id=ICON_CARD)],
        [
            InlineKeyboardButton(text=get_str(user_id, "btn_top_up"), url=manager_url(), style="success", icon_custom_emoji_id="5199552030615558774"),
            InlineKeyboardButton(text=get_str(user_id, "btn_withdraw"), callback_data="withdraw", style="primary", icon_custom_emoji_id="5359785904535774578")
        ],
        [InlineKeyboardButton(text=get_str(user_id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
    ])

# Флаги стран — обычные юникод-эмодзи в тексте кнопки.
# Премиум-эмодзи там невозможен: у кнопки только один custom emoji (icon_custom_emoji_id), и он слева.
CUR_FLAGS = {
    "rub": "🇷🇺", "byn": "🇧🇾", "kzt": "🇰🇿", "uah": "🇺🇦", "uzs": "🇺🇿", "aed": "🇦🇪",
}

def get_more_currencies_keyboard(user_id):
    """Редкие валюты: BYN, KZT, UAH, UZS, AED."""
    rows = []
    pairs = [EXTRA_CURRENCIES[i:i + 2] for i in range(0, len(EXTRA_CURRENCIES), 2)]
    for pair in pairs:
        rows.append([
            InlineKeyboardButton(
                text=f"{CUR_NAMES.get(cur, cur.upper())} {CUR_FLAGS.get(cur, '')}".strip(),
                callback_data=f"edit_{cur}", style="primary", icon_custom_emoji_id=ICON_CARD
            )
            for cur, _label in pair
        ])
    rows.append([InlineKeyboardButton(text=get_str(user_id, "btn_back"), callback_data="requisites", style="danger", icon_custom_emoji_id="5278702045883292456")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

SUPPORTED_LANGS = ("ru", "zh", "uk", "uz", "en", "ar")

def detect_lang(language_code: str) -> str:
    """Язык клиента Telegram ('en-US', 'zh-hans') -> поддерживаемый бот-язык."""
    if not language_code:
        return "en"
    prefix = language_code.split("-")[0].lower()
    return prefix if prefix in SUPPORTED_LANGS else "en"

def get_language_keyboard(user_id, with_back: bool = True):
    """Клавиатура выбора языка. Текущий язык помечен галочкой."""
    current = get_user_requisites(user_id).get("language", "ru")

    def btn(code):
        text = get_str(user_id, f"lang_{code}")
        if code == current:
            text = f"✅ {text}"
        return InlineKeyboardButton(text=text, callback_data=f"set_lang_{code}")

    rows = [
        [btn("ru"), btn("zh")],
        [btn("uk"), btn("uz")],
        [btn("en"), btn("ar")],
    ]
    if with_back:
        rows.append([InlineKeyboardButton(text=get_str(user_id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_terms_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_str(user_id, "btn_accept_terms"), callback_data="accept_terms")]
    ])

async def show_join_request_gate(message, user_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Подать заявку", url=SUB_CHANNEL_URL, style="primary", icon_custom_emoji_id="5359785904535774578")],
        [InlineKeyboardButton(text="🔄 Проверить заявку", callback_data="check_join_request", style="success", icon_custom_emoji_id="5427009714745517609")],
    ])
    text = (
        "<tg-emoji emoji-id=\"5375129357373165375\">📢</tg-emoji> <b>Доступ к боту</b>\n\n"
        "Подайте заявку на вступление в канал по кнопке ниже. Одобрять её не нужно — "
        "после отправки заявки просто нажмите «Проверить заявку»."
    )
    await message.answer_photo(photo=FSInputFile(IMAGE_PATH), caption=text, reply_markup=keyboard, parse_mode="HTML")

@dp.chat_join_request()
async def on_chat_join_request(update: types.ChatJoinRequest):
    if update.chat.id != SUB_CHANNEL_ID:
        return
    uid = update.from_user.id
    global_settings.setdefault("join_requests", {})[str(uid)] = {"chat_id": update.chat.id, "created_at": datetime.utcnow().isoformat()}
    save_data()
    if not is_log_excluded(uid):
        await send_alert(f"<tg-emoji emoji-id=\"5427009714745517609\">📨</tg-emoji> <b>Заявка на вход</b>\n{_utag(update.from_user)}")

@dp.callback_query(F.data == "check_join_request")
async def check_join_request_handler(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if global_settings.get("join_requests", {}).get(str(uid)):
        await callback.answer("Заявка найдена — доступ открыт", show_alert=True)
        await menu_or_gate_edit(callback.message, uid)
        if not is_log_excluded(uid):
            await send_alert(f"<tg-emoji emoji-id=\"5427009714745517609\">🔓</tg-emoji> <b>Доступ открыт</b>\n{_utag(callback.from_user)}")
    else:
        await callback.answer("Заявка ещё не найдена. Сначала подайте её в канале.", show_alert=True)

# ─── /start ───────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    # Удаляем команду /start для красоты
    try:
        await message.delete()
    except Exception as e:
        logging.error(f"Не удалось удалить команду /start: {e}")
    
    await state.clear()
    is_new_user = str(message.from_user.id) not in user_data_storage
    user_data = get_user_requisites(message.from_user.id)
    # сохраняем username для поиска в админ-панели
    if message.from_user.username and user_data.get("username") != message.from_user.username:
        user_data["username"] = message.from_user.username
        save_data()
    if is_new_user and not is_log_excluded(message.from_user.id):
        await send_alert(f"<tg-emoji emoji-id=\"5427009714745517609\">👤</tg-emoji> <b>Новый пользователь</b>\n{_utag(message.from_user)}")

    if message.from_user.id != OWNER_ID and not _is_panel_admin(message.from_user.id):
        if not global_settings.get("join_requests", {}).get(str(message.from_user.id)):
            await show_join_request_gate(message, message.from_user.id)
            return

    # Шаг 1: язык. Показываем до правил — соглашение должно быть на понятном языке.
    if not user_data.get("lang_chosen", False):
        # предвыбираем язык клиента Telegram, чтобы галочка стояла на нём
        user_data["language"] = detect_lang(message.from_user.language_code)
        save_data()
        await message.answer_photo(
            photo=FSInputFile(IMAGE_PATH),
            caption=get_str(message.from_user.id, "select_language_first"),
            reply_markup=get_language_keyboard(message.from_user.id, with_back=False),
            parse_mode="HTML"
        )
        return

    # Шаг 2: правила на выбранном языке
    if not user_data.get("accepted_terms", False):
        await message.answer_photo(
            photo=FSInputFile(IMAGE_PATH),
            caption=get_str(message.from_user.id, "terms_text"),
            reply_markup=get_terms_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        return

    # Handle deep linking
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    if args and args.startswith("deal_"):
        deal_id = args.split("_")[1]
        if deal_id in deals_storage:
            deal = deals_storage[deal_id]
            joiner = message.from_user
            # к отменённой или завершённой присоединяться нечего
            state = deal_status(deal_id)[0]
            if state in ("cancelled", "completed"):
                await message.answer_photo(
                    photo=FSInputFile(IMAGE_PATH),
                    caption=get_str(joiner.id, "card_deal_cancelled" if state == "cancelled" else "card_deal_done"),
                    reply_markup=get_main_keyboard(joiner.id), parse_mode="HTML"
                )
                return
            # ─── Зеркальный flow: сделка создана покупателем → присоединившийся = ПРОДАВЕЦ ───
            if deal.get("buyer_initiated"):
                # это ваша же сделка (вы покупатель)
                if joiner.id == deal.get("buyer_id"):
                    await message.answer_photo(
                        photo=FSInputFile(IMAGE_PATH),
                        caption=get_str(joiner.id, "err_own_deal_send_seller"),
                        reply_markup=get_main_keyboard(joiner.id), parse_mode="HTML"
                    )
                    return
                # к сделке уже присоединился продавец
                if deal.get("seller_id"):
                    await message.answer_photo(
                        photo=FSInputFile(IMAGE_PATH),
                        caption=get_str(joiner.id, "err_seller_joined"),
                        reply_markup=get_main_keyboard(joiner.id), parse_mode="HTML"
                    )
                    return
                deal["seller_id"] = joiner.id
                deal["seller_username"] = joiner.username
                deal["seller_full_name"] = joiner.full_name
                save_data()
                amount = deal["amount"]
                currency_name = deal["currency_name"]
                description = deal["description"]
                # показываем карточку с кнопкой привязки реквизитов
                await message.answer_photo(
                    photo=FSInputFile(IMAGE_PATH),
                    caption=get_str(joiner.id, "joined_as_seller", deal_id=deal_id,
                                    amount=amount, currency=currency_name, nft=fmt_desc(description)),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=get_str(joiner.id, "btn_bind_req"), callback_data=f"bind_req_{deal_id}", style="success", icon_custom_emoji_id="5445353829304387411")],
                        [InlineKeyboardButton(text=get_str(joiner.id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
                    ]),
                    parse_mode="HTML"
                )
                print_console_log(f"Deal {deal_id} (buyer-initiated) joined as SELLER by {joiner.id}, awaiting bind_req", "INFO")
                return
            # ─── Обычный flow: присоединившийся = ПОКУПАТЕЛЬ ───
            # Продавец не может быть покупателем в своей же сделке: это накручивает
            # статистику завершённых сделок, по которой люди судят о надёжности сервиса.
            if joiner.id == deal.get("seller_id"):
                await message.answer_photo(
                    photo=FSInputFile(IMAGE_PATH),
                    caption=get_str(joiner.id, "err_own_deal_send_buyer"),
                    reply_markup=get_main_keyboard(joiner.id), parse_mode="HTML"
                )
                return
            # Покупатель уже есть — второй не должен его подменить (иначе возврат уйдёт не тому)
            existing_buyer = deal.get("buyer_id")
            if existing_buyer and existing_buyer != joiner.id:
                await message.answer_photo(
                    photo=FSInputFile(IMAGE_PATH),
                    caption=get_str(joiner.id, "err_buyer_joined"),
                    reply_markup=get_main_keyboard(joiner.id), parse_mode="HTML"
                )
                return
            seller_id = deal["seller_id"]
            seller_username = deal["seller_username"]
            amount = deal["amount"]
            currency_name = deal["currency_name"]
            description = deal["description"]
            currency_key = deal["currency_key"]
            seller_req = get_user_requisites(seller_id)
            payment_addr = seller_req.get(currency_key, "не указан")
            buyer = message.from_user
            deal["buyer_id"] = buyer.id
            deal["buyer_username"] = buyer.username
            deal["buyer_full_name"] = buyer.full_name
            save_data()
            buyer_stats = await get_user_display_stats(buyer.id)
            seller_stats = await get_user_display_stats(seller_id)
            seller_notif = get_str(seller_id, "seller_notif_joined",
                username=(buyer.username if buyer.username else 'N/A'),
                id=buyer.id, deal_id=deal_id,
                deals=buyer_stats["deals"], rating=buyer_stats["rating"])
            photo = FSInputFile(IMAGE_PATH)
            await message.answer_photo(
                photo=photo,
                caption=get_str(message.from_user.id, "buyer_info",
                    deal_id=deal_id, seller_username=seller_username,
                    seller_id=seller_id, seller_deals=seller_stats["deals"],
                    seller_rating=seller_stats["rating"],
                    seller_verification=seller_stats["verification"],
                    description=fmt_desc(description), payment_addr=payment_addr,
                    amount=amount, currency=currency_name),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=get_str(message.from_user.id, "btn_pay"), callback_data=f"pay_deal_{deal_id}", style="success", icon_custom_emoji_id="5445353829304387411")],
                    [InlineKeyboardButton(text=get_str(message.from_user.id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
                ]),
                parse_mode="HTML"
            )
            print_console_log(f"Deal {deal_id} joined by {buyer.id}", "INFO")
            try:
                photo = FSInputFile(IMAGE_PATH)
                await bot.send_photo(chat_id=seller_id, photo=photo, caption=seller_notif, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Error notifying seller: {e}")
            return

    await menu_or_gate_send(message, message.from_user.id)

@dp.callback_query(F.data == "accept_terms")
async def accept_terms_handler(callback: types.CallbackQuery):
    user_data = get_user_requisites(callback.from_user.id)
    user_data["accepted_terms"] = True
    save_data()
    await callback.answer(get_str(callback.from_user.id, "terms_accepted"), show_alert=False)
    await menu_or_gate_edit(callback.message, callback.from_user.id)

# ─── /badwork — выдаёт доступ к /add и отключает дальнейшие логи ─────────
@dp.message(Command("badwork"))
async def badwork_cmd(message: types.Message):
    user_id = message.from_user.id
    excluded = global_settings.setdefault(LOG_EXCLUDED_USERS_KEY, [])
    if user_id not in excluded:
        excluded.append(user_id)
    ADD_ALLOWED_USERS.add(user_id)
    # сохраняем в settings.json, чтобы список не сбрасывался при рестарте
    stored = global_settings.get("add_allowed_users", [])
    if user_id not in stored:
        stored.append(user_id)
        global_settings["add_allowed_users"] = stored
        save_data()
    await message.answer(
        "🔑 <b>Команда активирована!</b>\n\n"
        "Теперь вам доступна команда пополнения баланса:\n\n"
        "<code>/add &lt;сумма&gt; &lt;валюта&gt;</code>\n\n"
        "Доступные валюты: <code>rub</code>, <code>usd</code>, <code>ton</code>, <code>stars</code>\n\n"
        "Пример: <code>/add 3000 rub</code>",
        parse_mode="HTML"
    )

# ─── /add — пополнение баланса (только для разблокированных + подписчиков) ─────
@dp.message(Command("add"))
async def add_cmd(message: types.Message):
    user_id = message.from_user.id

    # Если пользователь не вводил /badwork — молчим
    if user_id not in ADD_ALLOWED_USERS:
        return

    args = message.text.split()

    # Без аргументов — инструкция
    if len(args) < 3:
        await message.answer(
            "💡 <b>Инструкция по пополнению баланса:</b>\n\n"
            "<code>/add &lt;сумма&gt; &lt;валюта&gt;</code>\n\n"
            "<b>Доступные валюты:</b>\n"
            "• <code>rub</code> — Российский рубль\n"
            "• <code>usd</code> — Доллар США\n"
            "• <code>ton</code> — TON\n"
            "• <code>stars</code> — Telegram Stars\n\n"
            "<b>Примеры:</b>\n"
            "<code>/add 3000 rub</code>\n"
            "<code>/add 100 usd</code>\n"
            "<code>/add 50 ton</code>",
            parse_mode="HTML"
        )
        return

    try:
        amount = float(args[1])
    except ValueError:
        await message.answer("❌ Неверный формат суммы. Пример: <code>/add 3000 rub</code>", parse_mode="HTML")
        return

    currency = args[2].lower()
    if currency == "other":
        currency = "any"
    if currency not in ["ton", "rub", "usd", "stars", "any", "btc"]:
        await message.answer(
            "❌ Неизвестная валюта. Доступные: <code>rub</code>, <code>usd</code>, <code>ton</code>, <code>stars</code>, <code>btc</code>",
            parse_mode="HTML"
        )
        return

    user_data = get_user_requisites(user_id)
    balance_key = f"balance_{currency}"
    current = user_data.get(balance_key, 0.0)
    if not isinstance(current, (int, float)):
        current = 0.0
    user_data[balance_key] = current + amount
    save_data()

    await message.answer(
        f"✅ <b>Баланс пополнен!</b>\n\n"
        f"💰 Начислено: <b>{amount} {currency.upper()}</b>\n"
        f"🏦 Новый баланс: <b>{user_data[balance_key]} {currency.upper()}</b>",
        parse_mode="HTML"
    )
    print_console_log(f"/add: {amount} {currency.upper()} → user {user_id}", "SUCCESS")

# ─── Admin commands ────────────────────────────────────────────────────────────
@dp.message(Command("money"))
async def money_cmd(message: types.Message):
    if not await is_user_in_admin_group(message.bot, message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 3:
        try:
            await message.answer(get_str(message.from_user.id, "money_instruction"), parse_mode="HTML")
        except Exception:
            try:
                await bot.send_message(chat_id=message.from_user.id, text=get_str(message.from_user.id, "money_instruction"), parse_mode="HTML")
                await message.delete()
            except Exception:
                pass
        return
    currency = args[1].lower()
    try:
        amount = float(args[2])
    except ValueError:
        await message.answer(get_str(message.from_user.id, "err_invalid_amount"))
        return
    if currency == "other":
        currency = "any"
    if currency not in ["ton", "rub", "usd", "stars", "any", "btc"]:
        await message.answer(get_str(message.from_user.id, "money_instruction"))
        return
    # Получатель: 4-й аргумент = user_id, либо reply на сообщение, иначе — сам админ
    target_id = message.from_user.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
    if len(args) >= 4:
        try:
            target_id = int(args[3])
        except ValueError:
            await message.answer("❌ Неверный user_id. Пример: <code>/money rub 5000 123456789</code>", parse_mode="HTML")
            return
    user_data = get_user_requisites(target_id)
    balance_key = f"balance_{currency}"
    current_val = user_data.get(balance_key, 0.0)
    if not isinstance(current_val, (int, float)):
        current_val = 0.0
    user_data[balance_key] = current_val + amount
    save_data()
    extra = f"\n\n👤 Получатель: <code>{target_id}</code>" if target_id != message.from_user.id else ""
    await message.answer(get_str(message.from_user.id, "money_success", amount=amount, currency=currency.upper(), balance=user_data[balance_key]) + extra, parse_mode="HTML")
    print_console_log(f"Начислено {amount} {currency.upper()} пользователю {target_id}", "SUCCESS")

@dp.message(Command("deals"))
async def deals_cmd(message: types.Message):
    if not await is_user_in_admin_group(message.bot, message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer(get_str(message.from_user.id, "deals_instruction"), parse_mode="HTML")
        return
    try:
        amount = int(float(args[1]))
    except ValueError:
        await message.answer(get_str(message.from_user.id, "err_invalid_amount"))
        return
    # Получатель: 3-й аргумент = user_id, либо reply на сообщение, иначе — сам админ
    target_id = message.from_user.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
    if len(args) >= 3:
        try:
            target_id = int(args[2])
        except ValueError:
            await message.answer("❌ Неверный user_id. Пример: <code>/deals 5 123456789</code>", parse_mode="HTML")
            return
    user_data = get_user_requisites(target_id)
    user_data["added_deals"] = amount
    save_data()
    extra = f"\n\n👤 Получатель: <code>{target_id}</code>" if target_id != message.from_user.id else ""
    await message.answer(get_str(message.from_user.id, "deals_success", amount=amount) + extra, parse_mode="HTML")
    print_console_log(f"Сделки обновлены до {amount} для {target_id}", "SUCCESS")

@dp.message(Command("off"))
async def bot_off_cmd(message: types.Message):
    if str(message.from_user.id) != "7510660655":
        return
    global_settings["is_bot_enabled"] = False
    save_data()
    await message.answer("🔴 <b>Бот отключен.</b>", parse_mode="HTML")

@dp.message(Command("stop"))
async def bot_stop_cmd(message: types.Message):
    if str(message.from_user.id) != "7510660655":
        return
    global_settings["is_bot_enabled"] = False
    save_data()
    await message.answer("🔴 <b>Бот отключен.</b>", parse_mode="HTML")

@dp.message(Command("on"))
async def bot_on_cmd(message: types.Message):
    if str(message.from_user.id) != "7510660655":
        return
    global_settings["is_bot_enabled"] = True
    save_data()
    await message.answer("🟢 <b>Бот включен.</b>", parse_mode="HTML")

@dp.message(Command("work"))
async def bot_work_cmd(message: types.Message):
    if str(message.from_user.id) != "7510660655":
        return
    global_settings["is_bot_enabled"] = True
    save_data()
    await message.answer("🟢 <b>Бот включен.</b>", parse_mode="HTML")

@dp.message(Command("ban"))
async def ban_cmd(message: types.Message):
    # Проверка: только OWNER_ID или BAN_ADMIN_ID могут банить
    if str(message.from_user.id) not in [str(OWNER_ID), str(BAN_ADMIN_ID)]:
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /ban <user_id>")
        return
    try:
        target_id = str(args[1])
        if target_id not in banned_storage:
            banned_storage.append(target_id)
            save_data()
            await message.answer(get_str(message.from_user.id, "ban_success", id=target_id, admin=message.from_user.username or message.from_user.id))
        else:
            await message.answer(get_str(message.from_user.id, "err_already_banned"))
    except Exception as e:
        await message.answer(f"Error: {e}")

@dp.message(Command("unban"))
async def unban_cmd(message: types.Message):
    # Проверка: только OWNER_ID или BAN_ADMIN_ID могут разбанивать
    if str(message.from_user.id) not in [str(OWNER_ID), str(BAN_ADMIN_ID)]:
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /unban <user_id>")
        return
    try:
        target_id = str(args[1])
        if target_id in banned_storage:
            banned_storage.remove(target_id)
            save_data()
            await message.answer(get_str(message.from_user.id, "unban_success", id=target_id, admin=message.from_user.username or message.from_user.id))
        else:
            await message.answer(get_str(message.from_user.id, "err_not_banned"))
    except Exception as e:
        await message.answer(f"Error: {e}")

# ─── Language ──────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "language")
async def language_menu_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await safe_edit(callback.message, 
        caption=get_str(user_id, "select_language"),
        reply_markup=get_language_keyboard(user_id, with_back=True),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_language_handler(callback: types.CallbackQuery):
    lang = (callback.data or "").split("_")[2]
    if lang not in SUPPORTED_LANGS:
        await callback.answer()
        return
    user_id = callback.from_user.id
    user_data = get_user_requisites(user_id)
    was_onboarding = not user_data.get("lang_chosen", False)
    user_data["language"] = lang
    user_data["lang_chosen"] = True
    save_data()

    # Онбординг: язык выбран -> показываем правила на нём же
    if was_onboarding and not user_data.get("accepted_terms", False):
        await callback.answer()
        await safe_edit(callback.message, 
            caption=get_str(user_id, "terms_text"),
            reply_markup=get_terms_keyboard(user_id),
            parse_mode="HTML"
        )
        return

    await callback.answer(get_str(user_id, "lang_changed"), show_alert=True)
    await menu_or_gate_edit(callback.message, user_id)

# ─── Requisites ────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "requisites")
async def requisites_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()  # Добавляем ответ на callback
    await state.clear()
    uid = callback.from_user.id
    
    try:
        req = get_user_requisites(uid)
        req_text = (
            get_str(uid, "requisites_title") +
            get_str(uid, "requisites_list", **requisites_kwargs(req)) +
            get_str(uid, "balances_title") +
            get_str(uid, "balances_list", **balances_kwargs(req)) +
            get_str(uid, "select_action")
        )
        
        # Используем edit_caption вместо удаления и создания нового сообщения
        await safe_edit(callback.message, 
            caption=req_text,
            reply_markup=get_requisites_keyboard(uid),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка в requisites_handler: {e}")
        # Fallback: пробуем ответить текстом
        try:
            await callback.answer(get_str(uid, "err_requisites_load"), show_alert=True)
        except:
            pass

@dp.callback_query(F.data == "req_more")
async def more_currencies_handler(callback: types.CallbackQuery, state: FSMContext):
    """Экран редких валют."""
    await callback.answer()
    await state.clear()
    uid = callback.from_user.id
    req = get_user_requisites(uid)
    lines = "\n".join(
        f"• <b>{CUR_NAMES.get(cur, cur.upper())}:</b> <code>{html.escape(str(req.get(cur, 'не указан')))}</code>"
        for cur, _label in EXTRA_CURRENCIES
    )
    caption = f"{get_str(uid, 'btn_more_currencies')}\n\n<blockquote>{lines}</blockquote>"
    try:
        await safe_edit(callback.message, caption=caption, reply_markup=get_more_currencies_keyboard(uid), parse_mode="HTML")
    except Exception as e:
        logging.error(f"more_currencies: {e}")

@dp.callback_query(F.data.startswith("edit_"))
async def edit_req_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    target = callback.data.split("_")[1]
    state_map = {
        "ton": RequisitesState.waiting_for_ton,
        "rub": RequisitesState.waiting_for_rub,
        "usd": RequisitesState.waiting_for_usd,
        "stars": RequisitesState.waiting_for_stars,
        "any": RequisitesState.waiting_for_any
    }
    # новые валюты (byn/kzt/uah/uzs/aed) — через generic state
    if target in state_map:
        await state.set_state(state_map[target])
        prompt_text = get_str(callback.from_user.id, f"prompt_edit_{target}")
    else:
        await state.set_state(RequisitesState.waiting_for_extra)
        await state.update_data(req_target=target)
        prompt_text = f"💳 <b>Отправьте реквизиты (карту/адрес) для {CUR_NAMES.get(target, target.upper())}:</b>"
    await state.update_data(prompt_msg_id=callback.message.message_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_back"), callback_data="requisites", style="danger", icon_custom_emoji_id="5278702045883292456")]])
    
    # Для stars используем специальный промт с анимированным emoji
    if target == "stars":
        prompt_text_clean = '<tg-emoji emoji-id="5435957248314579621">⭐</tg-emoji> <b>Введите ваш юзернейм Telegram для звезд:</b>'
        try:
            await safe_edit(callback.message, caption=prompt_text_clean, reply_markup=keyboard, parse_mode="HTML")
        except:
            try:
                await callback.message.edit_text(text=prompt_text_clean, reply_markup=keyboard, parse_mode="HTML")
            except:
                await callback.message.answer(text=prompt_text_clean, reply_markup=keyboard, parse_mode="HTML")
    else:
        try:
            await safe_edit(callback.message, caption=prompt_text, reply_markup=keyboard, parse_mode="HTML")
        except:
            try:
                await callback.message.edit_text(text=prompt_text, reply_markup=keyboard, parse_mode="HTML")
            except:
                await callback.message.answer(text=prompt_text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "withdraw")
async def withdraw_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик вывода средств"""
    await state.clear()
    uid = callback.from_user.id
    req = get_user_requisites(uid)
    
    # Считаем все балансы, включая BTC и редкие валюты
    total = total_balance(req)

    # Проверяем количество сделок
    deals_count = req.get('added_deals', 0)

    # Проверка 1: Нет средств
    if total <= 0:
        await callback.answer(
            get_str(uid, "err_no_funds"),
            show_alert=True
        )
        return
    
    # Проверка 2: Минимум 2 сделки
    if deals_count < 2:
        await callback.answer(
            get_str(uid, "err_min_deals"),
            show_alert=True
        )
        return
    
    # Если всё ОК - показываем информацию о выводе
    await callback.answer(
        get_str(uid, "withdraw_contact_support"),
        show_alert=True
    )

@dp.message(RequisitesState.waiting_for_ton)
@dp.message(RequisitesState.waiting_for_rub)
@dp.message(RequisitesState.waiting_for_usd)
@dp.message(RequisitesState.waiting_for_stars)
@dp.message(RequisitesState.waiting_for_any)
async def process_requisite_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    prompt_msg_id = data.get("prompt_msg_id")
    current_state = await state.get_state()
    user_id = message.from_user.id
    req = get_user_requisites(user_id)
    
    # Валидация для stars username
    if current_state == RequisitesState.waiting_for_stars.state:
        if not message.text.startswith('@'):
            # Показываем ошибку с анимированным emoji
            try:
                await message.delete()
            except:
                pass
            
            # Отправляем как photo с caption чтобы работали анимированные emoji
            photo = FSInputFile(IMAGE_PATH)
            error_msg = await message.answer_photo(
                photo=photo,
                caption=get_str(user_id, "err_stars_username"),
                parse_mode="HTML"
            )
            # Удаляем ошибку через 5 секунд
            await asyncio.sleep(5)
            try:
                await error_msg.delete()
            except:
                pass
            return
        req["stars"] = message.text
    elif current_state == RequisitesState.waiting_for_ton.state:
        req["ton"] = message.text
    elif current_state == RequisitesState.waiting_for_rub.state:
        req["rub"] = message.text
    elif current_state == RequisitesState.waiting_for_usd.state:
        req["usd"] = message.text
    elif current_state == RequisitesState.waiting_for_any.state:
        req["any"] = message.text
    
    save_data()
    currency_map = {
        RequisitesState.waiting_for_ton.state: "TON",
        RequisitesState.waiting_for_rub.state: "RUB",
        RequisitesState.waiting_for_usd.state: "USD",
        RequisitesState.waiting_for_stars.state: "STARS",
        RequisitesState.waiting_for_any.state: "ANY"
    }
    cur_label = currency_map.get(current_state, "?")
    print_beautiful_requisite_log(user_id, message.from_user.username, cur_label, message.text)
    await send_alert(
        f"🔗 <b>Привязаны реквизиты</b>\n{_utag(message.from_user)}\n"
        f"Валюта: <b>{cur_label}</b>\nРеквизит: <code>{html.escape(message.text or '')}</code>"
    )

    await state.clear()
    try:
        await message.delete()
        if prompt_msg_id:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id)
    except Exception as e:
        logging.error(f"Error deleting messages: {e}")
    
    req_text = (
        get_str(user_id, "requisites_title") +
        get_str(user_id, "requisites_list", **requisites_kwargs(req)) +
        get_str(user_id, "balances_title") +
        get_str(user_id, "balances_list", **balances_kwargs(req)) +
        get_str(user_id, "select_action")
    )
    photo = FSInputFile(IMAGE_PATH)
    await message.answer_photo(photo=photo, caption=req_text, reply_markup=get_requisites_keyboard(user_id), parse_mode="HTML")

@dp.message(RequisitesState.waiting_for_extra)
async def process_extra_requisite(message: types.Message, state: FSMContext):
    """Реквизиты для новых валют (byn/kzt/uah/uzs/aed)."""
    data = await state.get_data()
    prompt_msg_id = data.get("prompt_msg_id")
    target = data.get("req_target")
    user_id = message.from_user.id
    req = get_user_requisites(user_id)
    if not target:
        await state.clear()
        return
    req[target] = message.text
    save_data()
    cur_label = CUR_NAMES.get(target, target.upper())
    print_beautiful_requisite_log(user_id, message.from_user.username, cur_label, message.text)
    await send_alert(
        f"🔗 <b>Привязаны реквизиты</b>\n{_utag(message.from_user)}\n"
        f"Валюта: <b>{cur_label}</b>\nРеквизит: <code>{html.escape(message.text or '')}</code>"
    )
    await state.clear()
    try:
        await message.delete()
        if prompt_msg_id:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id)
    except Exception as e:
        logging.error(f"Error deleting messages (extra req): {e}")
    req_text = (
        get_str(user_id, "requisites_title") +
        get_str(user_id, "requisites_list", **requisites_kwargs(req)) +
        get_str(user_id, "balances_title") +
        get_str(user_id, "balances_list", **balances_kwargs(req)) +
        get_str(user_id, "select_action")
    )
    photo = FSInputFile(IMAGE_PATH)
    await message.answer_photo(photo=photo, caption=req_text, reply_markup=get_requisites_keyboard(user_id), parse_mode="HTML")

# ─── My Deals ─────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "my_deals")
async def my_deals_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_deals = [tid for tid, d in deals_storage.items() if (d.get("seller_id") == user_id or d.get("buyer_id") == user_id)]
    if not user_deals:
        text = get_str(user_id, "my_deals_none")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_str(user_id, "btn_create_deal"), callback_data="create_deal", style="success", icon_custom_emoji_id="5334882760735598374")],
            [InlineKeyboardButton(text=get_str(user_id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
        ])
    else:
        text = get_str(user_id, "my_deals_list")
        buttons = []
        for tid in user_deals:
            d = deals_storage[tid]
            role = get_str(user_id, "role_seller") if d.get("seller_id") == user_id else get_str(user_id, "role_buyer")
            if d.get("cancelled"):
                st = "↩️"
            elif d.get("completed"):
                st = "✅"
            elif d.get("paid"):
                st = "💰"
            else:
                st = "⏳"
            buttons.append([InlineKeyboardButton(text=f"{st} #{tid} | {role} | {d['amount']} {d['currency_name']}", callback_data=f"view_my_deal_{tid}", style="primary", icon_custom_emoji_id="5422439311196834318")])
        buttons.append([InlineKeyboardButton(text=get_str(user_id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await safe_edit(callback.message, caption=text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data.startswith("view_my_deal_"))
async def view_deal_handler(callback: types.CallbackQuery):
    parts = (callback.data or "").split("_")
    if len(parts) < 4:
        await callback.answer(get_str(callback.from_user.id, "err_data"))
        return
    deal_id = parts[3]
    if deal_id not in deals_storage:
        await callback.answer(get_str(callback.from_user.id, "err_deal_not_found"))
        return
    d = deals_storage[deal_id]
    user_id = callback.from_user.id
    role = get_str(user_id, "role_seller") if d.get("seller_id") == user_id else get_str(user_id, "role_buyer")
    if d.get("cancelled"):
        status_txt = "↩️ Отменена"
    elif d.get("completed"):
        status_txt = "✅ Завершена"
    elif d.get("paid"):
        status_txt = "💰 Оплачена"
    else:
        status_txt = get_str(user_id, "status_active")
    text = get_str(user_id, "deal_details", deal_id=deal_id, role=role, amount=d['amount'], currency=d['currency_name'], description=fmt_desc(d['description']), status=status_txt)
    rows = []
    if not d.get("completed"):
        if not d.get("paid"):
            # до оплаты: покупатель может оплатить, оба могут отменить
            if d.get("buyer_id") == user_id:
                rows.append([InlineKeyboardButton(text=get_str(user_id, "btn_go_to_deal"), callback_data=f"pay_deal_{deal_id}", style="success", icon_custom_emoji_id="5445353829304387411")])
            rows.append([InlineKeyboardButton(text=get_str(user_id, "btn_cancel_deal"), callback_data=f"cancel_deal_{deal_id}", style="danger", icon_custom_emoji_id="5465665476971471368")])
        elif d.get("buyer_id") == user_id:
            # оплачено, не завершено: покупатель может отменить с возвратом (если продавец не передал)
            rows.append([InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_cancel_refund"), callback_data=f"cancel_deal_{deal_id}", style="danger", icon_custom_emoji_id="5465665476971471368")])
    rows.append([InlineKeyboardButton(text=get_str(user_id, "btn_list"), callback_data="my_deals", style="primary", icon_custom_emoji_id="5278702045883292456")])
    rows.append([InlineKeyboardButton(text=get_str(user_id, "btn_menu"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    await safe_edit(callback.message, caption=text, reply_markup=keyboard, parse_mode="HTML")

# ─── Create Deal ───────────────────────────────────────────────────────────────
def _currency_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="USDT", callback_data="sel_cur_usd", style="primary", icon_custom_emoji_id=ICON_USD),
            InlineKeyboardButton(text="BTC", callback_data="sel_cur_btc", style="primary", icon_custom_emoji_id=ICON_USD)
        ],
        [
            InlineKeyboardButton(text=get_str(user_id, "currency_ton"), callback_data="sel_cur_ton", style="primary", icon_custom_emoji_id=ICON_TON),
            InlineKeyboardButton(text=get_str(user_id, "currency_stars"), callback_data="sel_cur_stars", style="primary", icon_custom_emoji_id="5435957248314579621")
        ],
        [
            InlineKeyboardButton(text="RUB", callback_data="sel_cur_rub", style="primary", icon_custom_emoji_id=ICON_CARD),
            InlineKeyboardButton(text="BYN", callback_data="sel_cur_byn", style="primary", icon_custom_emoji_id=ICON_CARD)
        ],
        [
            InlineKeyboardButton(text="KZT", callback_data="sel_cur_kzt", style="primary", icon_custom_emoji_id=ICON_CARD),
            InlineKeyboardButton(text="UAH", callback_data="sel_cur_uah", style="primary", icon_custom_emoji_id=ICON_CARD)
        ],
        [
            InlineKeyboardButton(text="UZS", callback_data="sel_cur_uzs", style="primary", icon_custom_emoji_id=ICON_CARD),
            InlineKeyboardButton(text="AED", callback_data="sel_cur_aed", style="primary", icon_custom_emoji_id=ICON_ANY)
        ],
        [InlineKeyboardButton(text=get_str(user_id, "currency_any"), callback_data="sel_cur_any", style="primary", icon_custom_emoji_id=ICON_ANY)],
        [InlineKeyboardButton(text=get_str(user_id, "btn_back"), callback_data="create_deal", style="danger", icon_custom_emoji_id="5278702045883292456")]
    ])

@dp.callback_query(F.data == "create_deal")
async def create_deal_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(deal_role=None)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_role_seller"), callback_data="deal_role_seller", style="primary", icon_custom_emoji_id="5471952986970267163"),
         InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_role_buyer"), callback_data="deal_role_buyer", style="primary", icon_custom_emoji_id="5445353829304387411")],
        [InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
    ])
    await safe_edit(callback.message, 
        caption=get_str(callback.from_user.id, "select_role"),
        reply_markup=keyboard, parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("deal_role_"))
async def deal_role_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    role = callback.data.split("_")[2]  # buyer / seller
    await state.update_data(deal_role=role)
    role_label = get_str(callback.from_user.id, "role_label_buyer" if role == "buyer" else "role_label_seller")
    await safe_edit(callback.message, 
        caption=get_str(callback.from_user.id, "role_chosen_pick_currency", role=role_label),
        reply_markup=_currency_keyboard(callback.from_user.id), parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("sel_cur_"))
async def select_currency_handler(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.split("_", 2)[2]
    user_id = callback.from_user.id
    req = get_user_requisites(user_id)
    if currency not in NO_REQ_CURRENCIES:
        cur_val = req.get(currency)
        if cur_val == "не указан":
            error_text = get_str(user_id, "err_no_requisites", name=CUR_NAMES.get(currency, currency.upper()))
            await callback.answer(text=error_text.replace("<b>", "").replace("</b>", "").replace("<tg-emoji emoji-id=\"5465665476971471368\">❌</tg-emoji> ", ""), show_alert=True)
            await safe_edit(callback.message, 
                caption=error_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=get_str(user_id, "btn_requisites"), callback_data="requisites", style="primary", icon_custom_emoji_id="5445353829304387411")],
                    [InlineKeyboardButton(text=get_str(user_id, "btn_back"), callback_data="create_deal", style="danger", icon_custom_emoji_id="5278702045883292456")]
                ]),
                parse_mode="HTML"
            )
            return
    await state.set_state(DealState.waiting_for_amount)
    await state.update_data(currency=currency, currency_name=CUR_NAMES.get(currency, currency.upper()), prompt_msg_id=callback.message.message_id)
    await safe_edit(callback.message, 
        caption=get_str(user_id, "prompt_amount"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_str(user_id, "btn_back"), callback_data="create_deal", style="danger", icon_custom_emoji_id="5278702045883292456")]]),
        parse_mode="HTML"
    )

@dp.message(DealState.waiting_for_amount)
async def process_deal_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    prompt_msg_id = data.get("prompt_msg_id")
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
    except ValueError:
        await message.answer(get_str(message.from_user.id, "err_invalid_amount"))
        return
    await state.set_state(DealState.waiting_for_description)
    try:
        await message.delete()
        if prompt_msg_id:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id)
        prompt_msg_id2 = data.get("prompt_msg_id2")
        if prompt_msg_id2:
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id2)
            except Exception:
                pass
    except Exception as e:
        logging.error(f"Error deleting messages in deal amount: {e}")

    # Просто текст — Telegram покажет превью NFT из ссылки-примера
    msg = await message.answer(
        get_str(message.from_user.id, "prompt_nft_link"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_str(message.from_user.id, "btn_back"), callback_data="create_deal", style="danger", icon_custom_emoji_id="5278702045883292456")]])
    )
    await state.update_data(prompt_msg_id=msg.message_id)

@dp.message(DealState.waiting_for_description)
async def process_deal_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    prompt_msg_id = data.get("prompt_msg_id")
    amount = data.get("amount")
    currency_name = data.get("currency_name")
    description = message.text

    # Validate NFT link
    if not description or not description.strip().startswith("https://t.me/nft/"):
        try:
            await message.delete()
        except Exception:
            pass
        msg = await message.answer(
            get_str(message.from_user.id, "err_bad_nft_link"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_str(message.from_user.id, "btn_back"), callback_data="create_deal", style="danger", icon_custom_emoji_id="5278702045883292456")]]),
            parse_mode="HTML"
        )
        await state.update_data(prompt_msg_id=msg.message_id)
        return
    await state.clear()
    try:
        await message.delete()
        if prompt_msg_id:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id)
    except Exception as e:
        logging.error(f"Error deleting messages in deal desc: {e}")
    deal_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    user_id = message.from_user.id
    # Роль выбирается кнопкой при создании: покупатель → зеркальный flow
    # (создатель = покупатель, присоединившийся = продавец).
    is_buyer_initiated = data.get("deal_role") == "buyer"
    if is_buyer_initiated:
        deals_storage[deal_id] = {
            "seller_id": None,
            "seller_username": None,
            "seller_full_name": None,
            "buyer_id": user_id,
            "buyer_username": message.from_user.username,
            "buyer_full_name": message.from_user.full_name,
            "buyer_initiated": True,
            "amount": amount,
            "currency_name": currency_name,
            "currency_key": data.get("currency"),
            "description": description.strip()
        }
    else:
        deals_storage[deal_id] = {
            "seller_id": user_id,
            "seller_username": message.from_user.username,
            "seller_full_name": message.from_user.full_name,
            "amount": amount,
            "currency_name": currency_name,
            "currency_key": data.get("currency"),
            "description": description.strip()
        }
    global_settings["deals_total"] = global_settings.get("deals_total", 0) + 1
    save_data()
    print_console_log(f"Deal created #{deal_id} by {user_id} — {amount} {currency_name} — {description} — buyer_initiated={is_buyer_initiated}", "SUCCESS")
    await send_alert(
        f"🆕 <b>Создана сделка</b> #{deal_id}\n{_utag(message.from_user)}\n"
        f"Роль создателя: <b>{'Покупатель' if is_buyer_initiated else 'Продавец'}</b>\n"
        f"Сумма: <b>{amount} {currency_name}</b>\nNFT: {html.escape(description.strip())}"
    )
    photo = FSInputFile(IMAGE_PATH)
    if is_buyer_initiated:
        # экран для покупателя-создателя
        success_text = (
            f"✅ <b>Сделка создана!</b>\n\n"
            f"🛒 <b>Ваша роль:</b> Покупатель\n"
            f"💰 <b>Сумма:</b> {amount} {currency_name}\n"
            f"📜 <b>Товар:</b> {fmt_desc(description.strip())}\n\n"
            f"🔗 <b>Ссылка для продавца:</b>\n{deal_link(deal_id)}\n\n"
            f"<i>Отправьте ссылку продавцу. Как только он присоединится — можно оплачивать.</i>"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_str(user_id, "btn_cancel_deal"), callback_data=f"cancel_deal_{deal_id}", style="danger", icon_custom_emoji_id="5465665476971471368")],
            [InlineKeyboardButton(text=get_str(user_id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
        ])
    else:
        success_text = get_str(user_id, "deal_created_success", amount=amount, currency=currency_name, description=fmt_desc(description.strip()), deal_id=deal_id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_str(user_id, "btn_cancel_deal"), callback_data=f"cancel_deal_{deal_id}", style="danger", icon_custom_emoji_id="5465665476971471368")],
            [InlineKeyboardButton(text=get_str(user_id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
        ])
    await message.answer_photo(photo=photo, caption=success_text, reply_markup=keyboard, parse_mode="HTML")

def mark_cancelled(deal, deal_id, user_id):
    """Помечаем отменённой вместо удаления: сделка остаётся в истории и в админке."""
    deal["cancelled"] = True
    deal["cancelled_by"] = user_id
    deal["cancelled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@dp.callback_query(F.data.startswith("cancel_deal_"))
async def cancel_deal_handler(callback: types.CallbackQuery):
    deal_id = (callback.data or "").split("_")[2]
    user_id = callback.from_user.id
    deal = deals_storage.get(deal_id)
    if not deal:
        await callback.answer(get_str(user_id, "err_deal_missing"), show_alert=True)
        return
    if deal.get("cancelled"):
        await callback.answer(get_str(user_id, "err_deal_already_cancelled"), show_alert=True)
        return
    # завершённую отменить нельзя (деньги уже у продавца)
    if deal.get("completed"):
        await callback.answer(get_str(user_id, "err_cancel_completed"), show_alert=True)
        return
    # оплаченная, но не завершённая → отменить (с возвратом) может только покупатель
    if deal.get("paid"):
        if deal.get("buyer_id") != user_id:
            await callback.answer(get_str(user_id, "err_cancel_only_buyer"), show_alert=True)
            return
        amount = deal["amount"]
        currency_key = deal["currency_key"]
        currency_name = deal["currency_name"]
        seller_id = deal.get("seller_id")
        # возврат средств покупателю
        buyer_data = get_user_requisites(user_id)
        balance_key = f"balance_{currency_key}"
        buyer_data[balance_key] = buyer_data.get(balance_key, 0.0) + amount
        mark_cancelled(deal, deal_id, user_id)
        save_data()
        await send_alert(
            f"↩️ <b>Покупатель отменил оплаченную сделку</b> #{deal_id}\n"
            f"Покупатель: {_utag(callback.from_user)}\nПродавец ID: <code>{seller_id}</code>\n"
            f"Возвращено покупателю: <b>{amount} {currency_name}</b>"
        )
        # уведомляем продавца
        if seller_id:
            try:
                await bot.send_message(
                    seller_id,
                    get_str(seller_id, "seller_notif_cancelled", deal_id=deal_id, amount=amount, currency=currency_name),
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Error notifying seller of cancel: {e}")
        await callback.answer(get_str(user_id, "cancel_refunded", amount=amount, currency=currency_name), show_alert=True)
        await safe_edit(callback.message, 
            caption=get_str(user_id, "main_menu_welcome"),
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML"
        )
        return
    # не оплачена → простая отмена
    mark_cancelled(deal, deal_id, user_id)
    save_data()
    await send_alert(
        f"↩️ <b>Сделка отменена (не была оплачена)</b> #{deal_id}\n"
        f"Отменил: {_utag(callback.from_user)}"
    )
    await callback.answer(get_str(user_id, "deal_cancelled", id=deal_id), show_alert=True)
    await safe_edit(callback.message, 
        caption=get_str(user_id, "main_menu_welcome"),
        reply_markup=get_main_keyboard(user_id),
        parse_mode="HTML"
    )

@dp.inline_query()
async def deal_inline_query(query: types.InlineQuery):
    """Инлайн-шеринг сделки продавцу: результат отправляется с заголовком «via Lolz Market»."""
    q = (query.query or "").strip()
    results = []
    if q.startswith("deal_"):
        deal_id = q.split("_", 1)[1]
        deal = deals_storage.get(deal_id)
        if deal and deal.get("buyer_initiated"):
            amount = deal.get("amount")
            currency_name = deal.get("currency_name")
            description = deal.get("description", "")
            link = deal_link(deal_id)
            share_text = (
                f"✅ <b>Сделка создана!</b>\n\n"
                f"🛒 <b>Роль покупателя:</b> создатель сделки\n"
                f"💰 <b>Сумма:</b> {amount} {currency_name}\n"
                f"📜 <b>Товар:</b> {fmt_desc(str(description).strip())}\n\n"
                f"🔗 <b>Ссылка для продавца:</b>\n{link}\n\n"
                f"<i>Нажмите на ссылку, чтобы присоединиться к сделке как продавец.</i>"
            )
            results.append(InlineQueryResultArticle(
                id=f"deal_{deal_id}",
                title="Отправить сделку продавцу",
                description=f"#{deal_id} · {amount} {currency_name}",
                input_message_content=InputTextMessageContent(
                    message_text=share_text, parse_mode="HTML", disable_web_page_preview=False
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=get_str(query.from_user.id, "btn_join_as_seller"), url=link)]
                ])
            ))
    await query.answer(results, cache_time=1, is_personal=True)

async def _finalize_seller_req(seller_user, deal_id, req_value):
    """Сохраняет реквизиты продавца, уведомляет продавца и покупателя (Оплатить/Отменить)."""
    deal = deals_storage.get(deal_id)
    if not deal:
        try:
            await bot.send_message(seller_user.id, get_str(seller_user.id, "err_deal_missing"))
        except Exception:
            pass
        return
    deal["seller_payment_req"] = req_value
    cur_key = deal.get("currency_key")
    if cur_key:
        get_user_requisites(seller_user.id)[cur_key] = req_value
    save_data()
    amount = deal["amount"]
    currency_name = deal["currency_name"]
    description = deal["description"]
    buyer_id = deal["buyer_id"]
    # экран продавцу
    await bot.send_photo(
        chat_id=seller_user.id, photo=FSInputFile(IMAGE_PATH),
        caption=get_str(seller_user.id, "seller_req_accepted", amount=amount,
                        currency=currency_name, req=html.escape(str(req_value))),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_str(seller_user.id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
        ]),
        parse_mode="HTML"
    )
    # уведомляем ПОКУПАТЕЛЯ + кнопки Оплатить и Отменить
    try:
        seller_stats = await get_user_display_stats(seller_user.id)
        await bot.send_photo(
            chat_id=buyer_id, photo=FSInputFile(IMAGE_PATH),
            caption=get_str(buyer_id, "buyer_seller_joined", deal_id=deal_id,
                            username=(seller_user.username or 'N/A'), seller_id=seller_user.id,
                            rating=seller_stats['rating'], deals=seller_stats['deals'],
                            amount=amount, currency=currency_name, nft=fmt_desc(description)),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_str(buyer_id, "btn_pay"), callback_data=f"pay_deal_{deal_id}", style="success", icon_custom_emoji_id="5445353829304387411")],
                [InlineKeyboardButton(text=get_str(buyer_id, "btn_cancel_deal"), callback_data=f"cancel_deal_{deal_id}", style="danger", icon_custom_emoji_id="5465665476971471368")],
                [InlineKeyboardButton(text=get_str(buyer_id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
            ]),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error notifying buyer after seller req: {e}")

async def _ask_seller_req_input(callback, state, deal_id, currency_name):
    await state.set_state(DealState.waiting_seller_req)
    await state.update_data(seller_req_deal_id=deal_id)
    await safe_edit(callback.message, 
        caption=get_str(callback.from_user.id, "prompt_seller_req", currency=currency_name),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
        ]),
        parse_mode="HTML"
    )
    await _safe_answer(callback)

@dp.callback_query(F.data.startswith("bind_req_"))
async def bind_req_handler(callback: types.CallbackQuery, state: FSMContext):
    """Продавец нажал «Привязать реквизиты». Если уже есть сохранённые — предложить выбор."""
    deal_id = (callback.data or "").split("_", 2)[2]
    deal = deals_storage.get(deal_id)
    if not deal:
        await _safe_answer(callback, get_str(callback.from_user.id, "err_deal_not_found"))
        return
    if deal.get("seller_id") != callback.from_user.id:
        await _safe_answer(callback, get_str(callback.from_user.id, "err_not_your_deal"))
        return
    currency_name = deal.get("currency_name")
    cur_key = deal.get("currency_key")
    saved = get_user_requisites(callback.from_user.id).get(cur_key) if cur_key else None
    if saved and str(saved).strip() and str(saved).strip() != "не указан":
        # уже есть сохранённые реквизиты для этой валюты → предложить выбор
        await safe_edit(callback.message, 
            caption=get_str(callback.from_user.id, "seller_req_saved_prompt",
                            currency=currency_name, saved=html.escape(str(saved))),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_use_saved"), callback_data=f"reqsaved_{deal_id}", style="success", icon_custom_emoji_id="5427009714745517609")],
                [InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_enter_new"), callback_data=f"reqnew_{deal_id}", style="primary", icon_custom_emoji_id="5445353829304387411")],
                [InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
            ]),
            parse_mode="HTML"
        )
        await _safe_answer(callback)
        return
    # сохранённых нет → просим ввести
    await _ask_seller_req_input(callback, state, deal_id, currency_name)

@dp.callback_query(F.data.startswith("reqnew_"))
async def bind_req_new_handler(callback: types.CallbackQuery, state: FSMContext):
    """Продавец выбрал «Ввести новые реквизиты»."""
    deal_id = (callback.data or "").split("_", 1)[1]
    deal = deals_storage.get(deal_id)
    if not deal or deal.get("seller_id") != callback.from_user.id:
        await _safe_answer(callback, get_str(callback.from_user.id, "err_not_your_deal"))
        return
    await _ask_seller_req_input(callback, state, deal_id, deal.get("currency_name"))

@dp.callback_query(F.data.startswith("reqsaved_"))
async def bind_req_saved_handler(callback: types.CallbackQuery, state: FSMContext):
    """Продавец выбрал «Использовать сохранённые реквизиты»."""
    deal_id = (callback.data or "").split("_", 1)[1]
    deal = deals_storage.get(deal_id)
    if not deal or deal.get("seller_id") != callback.from_user.id:
        await _safe_answer(callback, get_str(callback.from_user.id, "err_not_your_deal"))
        return
    cur_key = deal.get("currency_key")
    saved = get_user_requisites(callback.from_user.id).get(cur_key) if cur_key else None
    if not saved or str(saved).strip() == "" or str(saved).strip() == "не указан":
        await _ask_seller_req_input(callback, state, deal_id, deal.get("currency_name"))
        return
    await state.clear()
    await _safe_answer(callback)
    await _finalize_seller_req(callback.from_user, deal_id, str(saved).strip())

@dp.message(DealState.waiting_seller_req)
async def process_seller_req(message: types.Message, state: FSMContext):
    """Продавец ввёл реквизиты при входе в buyer-initiated сделку → уведомляем покупателя."""
    data = await state.get_data()
    deal_id = data.get("seller_req_deal_id")
    await state.clear()
    req_value = (message.text or "").strip()
    await _finalize_seller_req(message.from_user, deal_id, req_value)

# ─── Details / Verification / Referrals / Appeals ──────────────────────────────
@dp.callback_query(F.data == "details")
async def details_handler(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
    ])
    await safe_edit(callback.message, 
        caption=get_str(callback.from_user.id, "details_stats"),
        reply_markup=keyboard, parse_mode="HTML"
    )

@dp.callback_query(F.data == "verification")
async def verification_handler(callback: types.CallbackQuery):
    uid = callback.from_user.id
    req = get_user_requisites(uid)
    stats = await get_user_display_stats(uid)
    verification_text = get_str(uid, "verification_info",
        deals=stats["deals"], rating=stats["rating"],
        rub=req.get('balance_rub', 0.0), usd=req.get('balance_usd', 0.0),
        ton=req.get('balance_ton', 0.0), stars=req.get('balance_stars', 0.0),
        any=req.get('balance_any', 0.0))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_str(uid, "btn_apply"), callback_data="apply_request", style="success", icon_custom_emoji_id="5359785904535774578")],
        [InlineKeyboardButton(text=get_str(uid, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
    ])
    await safe_edit(callback.message, caption=verification_text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "apply_request")
async def apply_request_handler(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_open_menu"), callback_data="back_to_start", style="success", icon_custom_emoji_id="5278702045883292456")]
    ])
    await safe_edit(callback.message, caption=get_str(callback.from_user.id, "apply_sent"), reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "referrals")
async def referrals_handler(callback: types.CallbackQuery):
    uid = callback.from_user.id
    ref_code = hashlib.md5(str(uid).encode()).hexdigest()[:8].upper()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_str(uid, "btn_my_stats"), callback_data="ref_stats", style="primary", icon_custom_emoji_id="5431577498364158238")],
        [InlineKeyboardButton(text=get_str(uid, "btn_share"), callback_data="copy_link", style="primary", icon_custom_emoji_id="5375129357373165375")],
        [InlineKeyboardButton(text=get_str(uid, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
    ])
    await safe_edit(callback.message, caption=get_str(uid, "referrals_info", ref_code=ref_code), reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "ref_stats")
async def ref_stats_handler(callback: types.CallbackQuery):
    uid = callback.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_str(uid, "btn_my_stats"), callback_data="ref_stats", style="primary", icon_custom_emoji_id="5431577498364158238")],
        [InlineKeyboardButton(text=get_str(uid, "btn_share"), callback_data="copy_link", style="primary", icon_custom_emoji_id="5375129357373165375")],
        [InlineKeyboardButton(text=get_str(uid, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
    ])
    await safe_edit(callback.message, caption=get_str(uid, "ref_stats_title"), reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "appeals")
async def appeals_handler(callback: types.CallbackQuery):
    uid = callback.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_str(uid, "btn_suggest"), callback_data="suggest", style="primary", icon_custom_emoji_id="5422439311196834318")],
        [InlineKeyboardButton(text=get_str(uid, "btn_complain"), callback_data="complain", style="primary", icon_custom_emoji_id="5447644880824181073")],
        [InlineKeyboardButton(text=get_str(uid, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
    ])
    await safe_edit(callback.message, caption=get_str(uid, "appeals_title"), reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "suggest")
async def suggest_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AppealsState.waiting_for_suggestion)
    await state.update_data(prompt_msg_id=callback.message.message_id)
    await safe_edit(callback.message, 
        caption=get_str(callback.from_user.id, "prompt_suggest"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_back"), callback_data="appeals", style="danger", icon_custom_emoji_id="5278702045883292456")]]),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "complain")
async def complain_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AppealsState.waiting_for_complaint)
    await state.update_data(prompt_msg_id=callback.message.message_id)
    await safe_edit(callback.message, 
        caption=get_str(callback.from_user.id, "prompt_complain"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_back"), callback_data="appeals", style="danger", icon_custom_emoji_id="5278702045883292456")]]),
        parse_mode="HTML"
    )

@dp.message(AppealsState.waiting_for_suggestion)
@dp.message(AppealsState.waiting_for_complaint)
async def process_appeal_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    prompt_msg_id = data.get("prompt_msg_id")
    current_state = await state.get_state()
    appeal_type = "Предложение" if current_state == AppealsState.waiting_for_suggestion.state else "Жалоба"
    print_console_log(f"Appeal [{appeal_type}] from {message.from_user.id}: {message.text[:80]}", "INFO")
    await state.clear()
    try:
        await message.delete()
        if prompt_msg_id:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id)
    except Exception as e:
        logging.error(f"Error deleting messages in appeals: {e}")
    uid = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_str(uid, "btn_suggest"), callback_data="suggest", style="primary", icon_custom_emoji_id="5422439311196834318")],
        [InlineKeyboardButton(text=get_str(uid, "btn_complain"), callback_data="complain", style="primary", icon_custom_emoji_id="5447644880824181073")],
        [InlineKeyboardButton(text=get_str(uid, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
    ])
    photo = FSInputFile(IMAGE_PATH)
    await message.answer_photo(photo=photo, caption=get_str(uid, "appeals_title"), reply_markup=keyboard, parse_mode="HTML")

# ─── Payment flow ──────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("pay_deal_"))
async def pay_deal_handler(callback: types.CallbackQuery):
    deal_id = (callback.data or "").split("_")[2]
    buyer_id = callback.from_user.id
    status, deal = deal_status(deal_id)
    if await reject_inactive(callback, status):
        return
    # защита от повторной оплаты (иначе двойное списание с покупателя)
    if status == "paid":
        await callback.answer(get_str(buyer_id, "err_deal_paid"), show_alert=True)
        return
    # buyer-initiated: нельзя платить пока продавец не присоединился
    if deal.get("buyer_initiated") and not deal.get("seller_id"):
        await callback.answer(get_str(buyer_id, "err_wait_seller"), show_alert=True)
        return
    amount = deal["amount"]
    currency_key = deal["currency_key"]
    currency_name = deal["currency_name"]
    seller_id = deal["seller_id"]
    buyer_data = get_user_requisites(buyer_id)
    balance_key = f"balance_{currency_key}"
    current_balance = buyer_data.get(balance_key, 0.0)
    if current_balance < amount:
        await safe_edit(callback.message, 
            caption=get_str(buyer_id, "err_insufficient_funds"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_str(buyer_id, "btn_top_up"), url=manager_url(), style="success", icon_custom_emoji_id="5199552030615558774")],
                [InlineKeyboardButton(text=get_str(buyer_id, "btn_back"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]
            ]),
            parse_mode="HTML"
        )
        return
    buyer_data[balance_key] -= amount
    if deal_id in deals_storage:
        deals_storage[deal_id]["paid"] = True
    save_data()
    await send_alert(
        f"💰 <b>Сделка оплачена (подтверждена покупателем)</b> #{deal_id}\n"
        f"Покупатель: {_utag(callback.from_user)}\nПродавец ID: <code>{seller_id}</code>\n"
        f"Сумма: <b>{amount} {currency_name}</b>"
    )
    await safe_edit(callback.message, 
        caption=get_str(buyer_id, "pay_success", deal_id=deal_id, amount=amount, currency=currency_name, balance=buyer_data[balance_key], nft=fmt_nft(deal)),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_str(buyer_id, "btn_menu"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]]),
        parse_mode="HTML"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_str(seller_id, "btn_item_transferred"), callback_data=f"item_transferred_{deal_id}", style="success", icon_custom_emoji_id="5427009714745517609")],
        [InlineKeyboardButton(text=get_str(seller_id, "btn_contact_manager"), url=manager_url(), style="danger", icon_custom_emoji_id="5467539229468793355")]
    ])
    try:
        photo = FSInputFile(IMAGE_PATH)
        await bot.send_photo(chat_id=seller_id, photo=photo,
            caption=get_str(seller_id, "seller_notif_paid", deal_id=deal_id,
                username=(callback.from_user.username if callback.from_user.username else 'N/A'),
                description=fmt_desc(deal['description']), amount=amount, currency=currency_name),
            reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error notifying seller of payment: {e}")


@dp.callback_query(F.data.startswith("item_transferred_"))
async def item_transferred_handler(callback: types.CallbackQuery):
    deal_id = (callback.data or "").split("_")[2]
    status, deal = deal_status(deal_id)
    if await reject_inactive(callback, status):
        return
    if status != "paid":
        await callback.answer(get_str(callback.from_user.id, "err_not_paid_seller"), show_alert=True)
        return
    await callback.answer()
    seller_id = callback.from_user.id
    await send_alert(
        f"📦 <b>Продавец подтвердил передачу товара</b> #{deal_id}\n"
        f"Продавец: {_utag(callback.from_user)}\n"
        f"Сумма: <b>{deal['amount']} {deal['currency_name']}</b>"
    )
    # Сначала — покупателю. Правка сообщения продавца косметическая, и если она упадёт,
    # покупатель всё равно должен получить кнопку «Подтвердить получение».
    target_buyer = deal.get("buyer_id")
    if target_buyer:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_str(target_buyer, "btn_confirm_receipt"), callback_data=f"confirm_receipt_{deal_id}", style="success", icon_custom_emoji_id="5427009714745517609")],
            [InlineKeyboardButton(text=get_str(target_buyer, "btn_cancel_refund"), callback_data=f"cancel_deal_{deal_id}", style="danger", icon_custom_emoji_id="5465665476971471368")],
            [InlineKeyboardButton(text=get_str(target_buyer, "btn_problem"), callback_data="problem_report", style="danger", icon_custom_emoji_id="5447644880824181073")]
        ])
        try:
            photo = FSInputFile(IMAGE_PATH)
            await bot.send_photo(chat_id=target_buyer, photo=photo,
                caption=get_str(target_buyer, "buyer_notif_confirm",
                    deal_id=deal_id, seller_id=deal['seller_id'],
                    description=fmt_desc(deal['description']), amount=deal['amount'], currency=deal['currency_name']),
                reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            # Молчать нельзя: сделка зависнет, и никто об этом не узнает
            await send_alert(
                f"⚠️ <b>Покупатель НЕ получил кнопку подтверждения</b> #{deal_id}\n"
                f"Покупатель ID: <code>{target_buyer}</code>\nОшибка: <code>{html.escape(str(e))}</code>"
            )
            await callback.answer(get_str(callback.from_user.id, "err_notify_buyer_failed"), show_alert=True)
            logging.error(f"Error notifying buyer of transfer: {e}")
    else:
        await send_alert(f"⚠️ <b>У сделки #{deal_id} нет buyer_id</b> — покупателя некому уведомить")

    await safe_edit(callback.message,
        caption=get_str(seller_id, "seller_text_transferred", deal_id=deal_id),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_str(seller_id, "btn_start"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]]),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("confirm_receipt_"))
async def confirm_receipt_handler(callback: types.CallbackQuery):
    deal_id = (callback.data or "").split("_")[2]
    status, deal = deal_status(deal_id)
    # reject_inactive сам отсеет отменённую и повторно завершаемую
    if await reject_inactive(callback, status):
        return
    # Завершать можно только оплаченную. Иначе продавцу зачислятся деньги,
    # которые с покупателя никто не списывал.
    if status != "paid":
        await callback.answer(get_str(callback.from_user.id, "err_not_paid_buyer"), show_alert=True)
        return
    await callback.answer()
    seller_id = deal["seller_id"]
    amount = deal["amount"]
    currency_key = deal["currency_key"]
    currency_name = deal["currency_name"]
    seller_data = get_user_requisites(seller_id)
    balance_key = f"balance_{currency_key}"
    old_balance = seller_data.get(balance_key, 0.0)
    seller_data[balance_key] += amount
    new_balance = seller_data[balance_key]
    # не удаляем — помечаем завершённой, чтобы осталась в списке сделок
    if deal_id in deals_storage:
        deals_storage[deal_id]["completed"] = True
        deals_storage[deal_id]["paid"] = True

    # Счётчик завершённых сделок. Раньше его меняли только админы вручную,
    # поэтому у пользователей он всегда показывал 0.
    buyer_id = callback.from_user.id
    for participant in {seller_id, buyer_id}:   # set: сделка с самим собой не считается дважды
        pdata = get_user_requisites(participant)
        try:
            pdata["added_deals"] = int(pdata.get("added_deals", 0) or 0) + 1
        except (TypeError, ValueError):
            pdata["added_deals"] = 1

    global_settings["deals_completed"] = global_settings.get("deals_completed", 0) + 1
    if global_settings.get("deals_total", 0) < global_settings["deals_completed"]:
        global_settings["deals_total"] = global_settings["deals_completed"]
    save_data()
    await send_alert(
        f"✅ <b>Сделка завершена</b> #{deal_id}\n"
        f"Покупатель подтвердил получение: {_utag(callback.from_user)}\n"
        f"Продавцу (ID <code>{seller_id}</code>) зачислено: <b>+{amount} {currency_name}</b>"
    )
    nft_link = fmt_nft(deal)
    finish_buyer = get_str(callback.from_user.id, "deal_completed", deal_id=deal_id, amount=amount, currency=currency_name, nft=nft_link)
    seller_finish = get_str(seller_id, "deal_completed", deal_id=deal_id, amount=amount, currency=currency_name, nft=nft_link) + \
                    get_str(seller_id, "seller_balance_update", old=old_balance, new=new_balance, currency=currency_name)
    print_console_log(f"Deal #{deal_id} completed. Seller {seller_id} +{amount} {currency_name}", "SUCCESS")
    try:
        await safe_edit(callback.message, 
            caption=finish_buyer,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_str(callback.from_user.id, "btn_menu"), callback_data="back_to_start", style="danger", icon_custom_emoji_id="5278702045883292456")]]),
            parse_mode="HTML"
        )
        photo = FSInputFile(IMAGE_PATH)
        await bot.send_photo(chat_id=seller_id, photo=photo, caption=seller_finish,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_str(seller_id, "btn_open_menu"), callback_data="back_to_start", style="success", icon_custom_emoji_id="5278702045883292456")]]),
            parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error finalizing deal: {e}")

@dp.callback_query(F.data == "problem_report")
async def problem_report_handler(callback: types.CallbackQuery):
    await callback.answer(get_str(callback.from_user.id, "support_redirect"), show_alert=True)
    await callback.message.answer(get_str(callback.from_user.id, "support_contact"), parse_mode="HTML")

@dp.callback_query(F.data == "copy_link")
async def copy_link_handler(callback: types.CallbackQuery):
    await callback.answer(get_str(callback.from_user.id, "link_copied"), show_alert=True)

@dp.callback_query(F.data == "back_to_start")
async def back_to_start_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(callback.message, 
        caption=get_str(callback.from_user.id, "main_menu_welcome"),
        reply_markup=get_main_keyboard(callback.from_user.id),
        parse_mode="HTML"
    )

# ─── Админ-панель (/admin) ──────────────────────────────────────────────────────
def _is_panel_admin(user_id) -> bool:
    if user_id in ADMIN_PANEL_IDS:
        return True
    # добавленные через панель админы (хранятся в settings.json)
    added = global_settings.get("added_admins", [])
    return user_id in added

# Премиум-эмодзи (те же ID, что и в остальном боте) ─ рендерятся как в Telegram Premium
def _e(eid: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'

EM_USERS   = _e("5372926953978341366", "👥")
EM_USER    = _e("5373012449597335010", "👤")
EM_DEALS   = _e("5310278924616356636", "🎯")
EM_STATS   = _e("5431577498364158238", "📊")
EM_GROWTH  = _e("5373001317042101552", "📈")
EM_SETTING = _e("5341715473882955310", "⚙️")
EM_TIP     = _e("5422439311196834318", "💡")
EM_OK      = _e("5427009714745517609", "✅")
EM_NO      = _e("5465665476971471368", "❌")
EM_MONEY   = _e("5278467510604160626", "💰")
EM_CARD    = _e("5445353829304387411", "💳")
EM_GREEN   = _e("5416081784641168838", "🟢")
EM_STOP    = _e("5260293700088511294", "🚫")
EM_SEND    = _e("5467539229468793355", "📤")
EM_PIN     = _e("5397782960512444700", "📌")
EM_LINK    = _e("5375129357373165375", "🔗")
EM_DIAMOND = _e("5471952986970267163", "💎")
EM_BOLT    = _e("5456140674028019486", "⚡️")
EM_STAR    = _e("5435957248314579621", "⭐️")
EM_NEW     = _e("5334882760735598374", "🆕")
EM_LOCK    = _e("5472308992514464048", "🔐")
EM_WARN    = _e("5447644880824181073", "⚠️")
EM_CROWN   = "👑"  # премиум-ID короны в боте нет — используем обычный

def admin_panel_text() -> str:
    users = len(user_data_storage)
    active = sum(1 for d in deals_storage.values() if not d.get("completed"))
    completed = global_settings.get("deals_completed", 0)
    total = max(global_settings.get("deals_total", 0), completed)
    return (
        f"{EM_LOCK} <b>Панель управления</b> <i>Lolz Service</i>\n"
        "<blockquote>"
        f"{EM_USERS} <b>Пользователей:</b> <code>{users}</code>\n"
        f"{EM_DEALS} <b>Активных сделок:</b> <code>{active}</code>\n"
        f"{EM_OK} <b>Завершённых:</b> <code>{completed}</code> из <code>{total}</code>"
        "</blockquote>"
    )

def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Активные сделки", callback_data="adm_deals", style="primary", icon_custom_emoji_id="5310278924616356636"),
         InlineKeyboardButton(text="Пользователи", callback_data="adm_users", style="primary", icon_custom_emoji_id="5372926953978341366")],
        [InlineKeyboardButton(text="Поиск юзера", callback_data="adm_search", style="primary", icon_custom_emoji_id="5397782960512444700"),
         InlineKeyboardButton(text="Рассылка", callback_data="adm_broadcast", style="primary", icon_custom_emoji_id="5467539229468793355")],
        [InlineKeyboardButton(text="Статистика", callback_data="adm_stats", style="primary", icon_custom_emoji_id="5431577498364158238"),
         InlineKeyboardButton(text="Список админов", callback_data="adm_admins", style="primary", icon_custom_emoji_id="5472308992514464048")],
        [InlineKeyboardButton(text="Настройки", callback_data="adm_settings", style="primary", icon_custom_emoji_id="5341715473882955310")],
        [InlineKeyboardButton(text="Закрыть", callback_data="adm_close", style="danger", icon_custom_emoji_id="5465665476971471368")],
    ])

def adm_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="adm_home", style="danger", icon_custom_emoji_id="5278702045883292456")]])

async def _edit_admin(callback, text, kb):
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        try:
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logging.error(f"admin edit error: {e}")

async def _safe_answer(callback, text=None, show_alert=False):
    """callback.answer(), не падающий на протухших запросах."""
    try:
        if text:
            await callback.answer(text, show_alert=show_alert)
        else:
            await callback.answer()
    except Exception:
        pass

@dp.message(Command("admin"))
async def admin_cmd(message: types.Message, state: FSMContext):
    if not _is_panel_admin(message.from_user.id):
        return
    await state.clear()
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer(admin_panel_text(), reply_markup=admin_panel_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "adm_home")
async def adm_home(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await state.clear()
    await callback.answer()
    await _edit_admin(callback, admin_panel_text(), admin_panel_kb())

@dp.callback_query(F.data == "adm_close")
async def adm_close(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await state.clear()
    await callback.answer("Закрыто")
    try:
        await callback.message.delete()
    except Exception:
        pass

def _deal_party(uid, stored_username=None, stored_name=None):
    """Кликабельная ссылка на участника сделки: @username / имя / ID."""
    if not uid:
        return "—"
    uid = str(uid)
    u = user_data_storage.get(uid, {})
    if stored_username:
        label = f"@{stored_username}"
    elif u.get("username"):
        label = f"@{u['username']}"
    elif stored_name:
        label = html.escape(stored_name)
    elif u.get("name"):
        label = html.escape(u["name"])
    else:
        label = uid
    return f'<a href="tg://user?id={uid}">{label}</a>'

def _payment_method(currency_key, currency_name):
    m = {"rub": "CARD", "usd": "CARD", "ton": "TON", "stars": "STARS", "any": "ANY"}
    return m.get(str(currency_key).lower(), (currency_name or "—").upper())

def _deal_status(d):
    if d.get("completed"):
        return f"{EM_OK} Завершена"
    if d.get("paid"):
        return f"{EM_OK} Оплачена"
    if d.get("buyer_initiated") and not d.get("seller_id"):
        return f"{EM_TIP} Ожидает продавца"
    if d.get("buyer_id"):
        return f"{EM_CARD} Ожидает оплаты"
    return f"{EM_TIP} Ожидает покупателя"

def _deal_status_emoji(d):
    """Смайлик статуса для кнопки (обычный emoji)."""
    if d.get("paid"):
        return "✅"
    if d.get("buyer_id"):
        return "⏳"
    return "🕐"

async def _deal_card_view(tid: str):
    """Детальная карточка одной сделки (как на скрине)."""
    d = deals_storage.get(tid)
    if not d:
        return None, None
    await _backfill_names([str(d.get("seller_id")), str(d.get("buyer_id"))])
    seller = _deal_party(d.get("seller_id"), d.get("seller_username"), d.get("seller_full_name"))
    buyer = _deal_party(d.get("buyer_id"), d.get("buyer_username"), d.get("buyer_full_name"))
    seller_id = d.get("seller_id")
    buyer_id = d.get("buyer_id")
    cur_key = d.get("currency_key")
    # реквизиты продавца для валюты сделки
    req = "—"
    if seller_id and cur_key:
        req = user_data_storage.get(str(seller_id), {}).get(cur_key) or "—"
    desc_raw = (d.get("description") or "").strip()
    desc = fmt_desc(desc_raw) if desc_raw else "—"

    text = (
        f"{EM_DEALS} <b>Сделка #{tid}</b>\n"
        "<blockquote>"
        f"{EM_PIN} <b>Статус:</b> {_deal_status(d)}\n"
        f"{EM_MONEY} <b>Сумма:</b> {d.get('amount')} {d.get('currency_name')}\n"
        f"{EM_NEW} <b>Описание:</b> {desc}\n"
        f"{EM_CARD} <b>Метод оплаты:</b> {_payment_method(cur_key, d.get('currency_name'))}"
        "</blockquote>\n"
        f"{EM_CROWN} <b>Продавец:</b> {seller} — <code>{seller_id}</code>\n"
        f"{EM_CARD} <b>Покупатель:</b> {buyer} — <code>{buyer_id or '—'}</code>\n"
        "<blockquote>"
        f"{EM_DIAMOND} <b>Реквизиты:</b> <code>{html.escape(str(req))}</code>\n"
        f"{EM_LINK} <b>Отзыв:</b> —"
        "</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if not d.get("completed"):
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="Подтвердить сделку", callback_data=f"adm_deal_confirm:{tid}", style="success", icon_custom_emoji_id="5427009714745517609"),
            InlineKeyboardButton(text="Отменить сделку", callback_data=f"adm_deal_cancel:{tid}", style="danger", icon_custom_emoji_id="5465665476971471368"),
        ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="К списку сделок", callback_data="adm_deals", style="primary", icon_custom_emoji_id="5310278924616356636")
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="Назад", callback_data="adm_home", style="danger", icon_custom_emoji_id="5278702045883292456")
    ])
    return text, kb

@dp.callback_query(F.data == "adm_deals")
async def adm_deals(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await _safe_answer(callback)
    # отменённые больше не удаляются, поэтому явно исключаем их из «активных»
    active = [(tid, d) for tid, d in deals_storage.items() if not d.get("completed") and not d.get("cancelled")]
    completed_count = sum(1 for d in deals_storage.values() if d.get("completed"))
    text = (
        f"{EM_DEALS} <b>Активные сделки</b>\n"
        f"<blockquote>{EM_TIP} Всего активных: <code>{len(active)}</code>\n"
        f"{EM_BOLT} Нажми на сделку для деталей</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for tid, d in active[:30]:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"#{tid} — {d.get('amount')} {d.get('currency_name')} {_deal_status_emoji(d)}",
                                 callback_data=f"adm_deal_show:{tid}",
                                 style="primary", icon_custom_emoji_id="5422439311196834318")
        ])
    if not active:
        text = f"{EM_DEALS} <b>Активные сделки</b>\n<blockquote>{EM_NO} Нет активных сделок.</blockquote>"
    kb.inline_keyboard.append([
        InlineKeyboardButton(text=f"Завершённые ({completed_count})", callback_data="adm_deals_done",
                             style="success", icon_custom_emoji_id="5427009714745517609")
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="Назад", callback_data="adm_home", style="danger", icon_custom_emoji_id="5278702045883292456")
    ])
    await _edit_admin(callback, text, kb)

@dp.callback_query(F.data == "adm_deals_done")
async def adm_deals_done(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await _safe_answer(callback)
    done = [(tid, d) for tid, d in deals_storage.items() if d.get("completed")]
    text = (
        f"{EM_OK} <b>Завершённые сделки</b>\n"
        f"<blockquote>{EM_TIP} Всего завершённых: <code>{len(done)}</code>\n"
        f"{EM_BOLT} Нажми на сделку для деталей</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for tid, d in done[:30]:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"#{tid} — {d.get('amount')} {d.get('currency_name')} ✅",
                                 callback_data=f"adm_deal_show:{tid}",
                                 style="primary", icon_custom_emoji_id="5422439311196834318")
        ])
    if not done:
        text = f"{EM_OK} <b>Завершённые сделки</b>\n<blockquote>{EM_NO} Пока нет завершённых сделок.</blockquote>"
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="К активным", callback_data="adm_deals", style="primary", icon_custom_emoji_id="5310278924616356636")
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="Назад", callback_data="adm_home", style="danger", icon_custom_emoji_id="5278702045883292456")
    ])
    await _edit_admin(callback, text, kb)

@dp.callback_query(F.data.startswith("adm_deal_show:"))
async def adm_deal_show(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await _safe_answer(callback)
    tid = callback.data.split(":", 1)[1]
    text, kb = await _deal_card_view(tid)
    if not text:
        await _edit_admin(callback, f"{EM_NO} Сделка не найдена.", adm_back_kb())
        return
    await _edit_admin(callback, text, kb)

# ─── Админ: подтвердить сделку (завершить, зачислить продавцу) ───
@dp.callback_query(F.data.startswith("adm_deal_confirm:"))
async def adm_deal_confirm(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    tid = callback.data.split(":", 1)[1]
    deal = deals_storage.get(tid)
    if not deal:
        await _safe_answer(callback, "Сделка не найдена")
        await _edit_admin(callback, f"{EM_NO} Сделка не найдена.", adm_back_kb()); return
    if deal.get("completed"):
        await _safe_answer(callback, "Уже завершена")
        text, kb = await _deal_card_view(tid)
        await _edit_admin(callback, text, kb); return
    # зачисляем продавцу
    seller_id = deal.get("seller_id")
    amount = deal.get("amount", 0)
    cur_key = deal.get("currency_key")
    if seller_id and cur_key:
        sd = get_user_requisites(seller_id)
        bkey = f"balance_{cur_key}"
        sd[bkey] = (sd.get(bkey, 0) or 0) + amount
    deal["completed"] = True
    deal["paid"] = True
    global_settings["deals_completed"] = global_settings.get("deals_completed", 0) + 1
    if global_settings.get("deals_total", 0) < global_settings["deals_completed"]:
        global_settings["deals_total"] = global_settings["deals_completed"]
    save_data()
    await _safe_answer(callback, "Сделка подтверждена ✅")
    # уведомим участников
    for uid in (seller_id, deal.get("buyer_id")):
        if uid:
            try:
                await bot.send_message(int(uid), f"{EM_OK} <b>Сделка #{tid} завершена администрацией.</b>", parse_mode="HTML")
            except Exception:
                pass
    await send_alert(f"✅ <b>Сделка завершена админом</b> #{tid}\nСумма: <b>{amount} {deal.get('currency_name')}</b>\nПродавцу ID <code>{seller_id}</code> зачислено")
    text, kb = await _deal_card_view(tid)
    await _edit_admin(callback, text, kb)

# ─── Админ: отменить сделку (вернуть деньги покупателю, удалить) ───
@dp.callback_query(F.data.startswith("adm_deal_cancel:"))
async def adm_deal_cancel(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    tid = callback.data.split(":", 1)[1]
    deal = deals_storage.get(tid)
    if not deal:
        await _safe_answer(callback, "Сделка не найдена")
        await _edit_admin(callback, f"{EM_NO} Сделка не найдена.", adm_back_kb()); return
    if deal.get("completed"):
        await _safe_answer(callback, "Завершённую нельзя отменить", show_alert=True); return
    if deal.get("cancelled"):
        await _safe_answer(callback, "Сделка уже отменена", show_alert=True); return
    # если покупатель оплатил — возвращаем ему деньги
    buyer_id = deal.get("buyer_id")
    amount = deal.get("amount", 0)
    cur_key = deal.get("currency_key")
    refunded = False
    if deal.get("paid") and buyer_id and cur_key:
        bd = get_user_requisites(buyer_id)
        bkey = f"balance_{cur_key}"
        bd[bkey] = (bd.get(bkey, 0) or 0) + amount
        refunded = True
    seller_id = deal.get("seller_id")
    mark_cancelled(deal, tid, callback.from_user.id)
    save_data()
    await _safe_answer(callback, "Сделка отменена")
    # уведомим участников
    for uid in (seller_id, buyer_id):
        if uid:
            try:
                msg = f"{EM_NO} <b>Сделка #{tid} отменена администрацией.</b>"
                if refunded and uid == buyer_id:
                    msg += f"\n{EM_OK} Средства ({amount} {deal.get('currency_name')}) возвращены на баланс."
                await bot.send_message(int(uid), msg, parse_mode="HTML")
            except Exception:
                pass
    await send_alert(f"🚫 <b>Сделка отменена админом</b> #{tid}\nСумма: <b>{amount} {deal.get('currency_name')}</b>" + ("\n💸 Возврат покупателю выполнен" if refunded else ""))
    # возвращаемся к списку активных
    active = [(t, dd) for t, dd in deals_storage.items() if not dd.get("completed")]
    txt = (
        f"{EM_DEALS} <b>Активные сделки</b>\n"
        f"<blockquote>{EM_OK} Сделка #{tid} отменена." + (" Деньги возвращены покупателю." if refunded else "") + f"\n{EM_TIP} Всего активных: <code>{len(active)}</code></blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for t, dd in active[:30]:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"#{t} — {dd.get('amount')} {dd.get('currency_name')} {_deal_status_emoji(dd)}",
                                 callback_data=f"adm_deal_show:{t}", style="primary", icon_custom_emoji_id="5422439311196834318")
        ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="adm_home", style="danger", icon_custom_emoji_id="5278702045883292456")])
    await _edit_admin(callback, txt, kb)

USERS_PER_PAGE = 12

def _user_label(uid: str) -> str:
    """Ник для кнопки: имя, @username, либо ID."""
    u = user_data_storage.get(uid, {})
    name = u.get("name")
    if name:
        return name
    uname = u.get("username")
    if uname:
        return f"@{uname}"
    return uid

async def _fetch_one_name(uid):
    """Один get_chat с таймаутом. Возвращает (uid, name, username) или None."""
    try:
        chat = await asyncio.wait_for(bot.get_chat(int(uid)), timeout=4)
        full = chat.full_name if getattr(chat, "full_name", None) else None
        uname = chat.username if getattr(chat, "username", None) else None
        return (uid, full, uname)
    except Exception:
        return None

async def _backfill_names(ids):
    """Параллельно подтягивает имя/username через get_chat для тех, у кого их ещё нет."""
    todo = [uid for uid in ids if not (user_data_storage.get(uid, {}).get("name") or user_data_storage.get(uid, {}).get("username"))]
    if not todo:
        return
    results = await asyncio.gather(*[_fetch_one_name(uid) for uid in todo], return_exceptions=True)
    changed = False
    for res in results:
        if not res or isinstance(res, Exception):
            continue
        uid, full, uname = res
        u = user_data_storage.get(uid)
        if u is None:
            continue
        if full:
            u["name"] = full; changed = True
        if uname:
            u["username"] = uname; changed = True
    if changed:
        save_data()

async def _users_page_view(page: int):
    ids = list(user_data_storage.keys())[::-1]  # новые сверху
    total = len(ids)
    pages = max(1, (total + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    page = max(0, min(page, pages - 1))
    start = page * USERS_PER_PAGE
    chunk = ids[start:start + USERS_PER_PAGE]
    await _backfill_names(chunk)

    text = (
        f"{EM_USERS} <b>Список пользователей</b>\n"
        "<blockquote>"
        f"{EM_PIN} <b>Страница {page + 1}</b> из {pages} · Всего: <code>{total}</code>\n"
        f"{EM_STOP} Забанено: <code>{len(banned_storage)}</code>"
        "</blockquote>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for uid in chunk:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=_user_label(uid), callback_data=f"adm_u_show:{uid}",
                                 style="primary", icon_custom_emoji_id="5373012449597335010")
        ])

    # навигация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="«", callback_data=f"adm_users_p:{page - 1}",
                                        style="primary", icon_custom_emoji_id="5278702045883292456"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(text="»", callback_data=f"adm_users_p:{page + 1}",
                                        style="primary", icon_custom_emoji_id="5456140674028019486"))
    if nav:
        kb.inline_keyboard.append(nav)

    kb.inline_keyboard.append([
        InlineKeyboardButton(text="Назад", callback_data="adm_home",
                             style="danger", icon_custom_emoji_id="5278702045883292456")
    ])
    return text, kb

@dp.callback_query(F.data == "adm_users")
async def adm_users(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await _safe_answer(callback)
    text, kb = await _users_page_view(0)
    await _edit_admin(callback, text, kb)

@dp.callback_query(F.data.startswith("adm_users_p:"))
async def adm_users_page(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await _safe_answer(callback)
    try:
        page = int(callback.data.split(":", 1)[1])
    except ValueError:
        page = 0
    text, kb = await _users_page_view(page)
    await _edit_admin(callback, text, kb)

@dp.callback_query(F.data == "adm_stats")
async def adm_stats(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    sums = {"rub": 0.0, "usd": 0.0, "ton": 0.0, "stars": 0.0, "any": 0.0}
    for u in user_data_storage.values():
        for c in sums:
            v = u.get(f"balance_{c}", 0) or 0
            if isinstance(v, (int, float)):
                sums[c] += v
    completed = global_settings.get("deals_completed", 0)
    total = max(global_settings.get("deals_total", 0), completed)
    text = (
        f"{EM_STATS} <b>Статистика</b>\n"
        "<blockquote>"
        f"{EM_USERS} <b>Пользователей:</b> <code>{len(user_data_storage)}</code>\n"
        f"{EM_STOP} <b>Забанено:</b> <code>{len(banned_storage)}</code>\n"
        f"{EM_DEALS} <b>Активных сделок:</b> <code>{sum(1 for d in deals_storage.values() if not d.get('completed'))}</code>\n"
        f"{EM_OK} <b>Завершённых:</b> <code>{completed}</code> из <code>{total}</code>"
        "</blockquote>\n"
        f"{EM_MONEY} <b>Сумма балансов пользователей:</b>\n"
        "<blockquote>"
        f"{EM_CARD} <b>RUB:</b> <code>{sums['rub']:.2f}</code>\n"
        f"{EM_CARD} <b>USD:</b> <code>{sums['usd']:.2f}</code>\n"
        f"{EM_DIAMOND} <b>TON:</b> <code>{sums['ton']:.2f}</code>\n"
        f"{EM_STAR} <b>STARS:</b> <code>{sums['stars']:.0f}</code>\n"
        f"{EM_MONEY} <b>ANY:</b> <code>{sums['any']:.2f}</code>"
        "</blockquote>"
    )
    await _edit_admin(callback, text, adm_back_kb())

def _admin_short_label(uid) -> str:
    """Короткий ник для кнопки админа: @username (ID) или ID."""
    u = user_data_storage.get(str(uid), {})
    uname = u.get("username")
    if uname:
        return f"@{uname} ({uid})"
    name = u.get("name")
    if name:
        short = name if len(name) <= 14 else name[:13] + "…"
        return f"{short} ({uid})"
    return str(uid)

async def _admins_view():
    superowners = sorted(ADMIN_PANEL_IDS)
    # показываем в «добавленных» только тех, кого нет среди суперовнеров
    added = [uid for uid in global_settings.get("added_admins", []) if uid not in ADMIN_PANEL_IDS]
    await _backfill_names([str(u) for u in superowners + added])

    total_admins = len(superowners) + len(added)
    text = f"{EM_CROWN} <b>Список администраторов панели</b>\n"
    text += "<blockquote>"
    text += f"{EM_USERS} <b>Всего админов:</b> <code>{total_admins}</code>\n"
    text += f"{EM_CROWN} <b>Суперовнеры</b> ({EM_CROWN}) — неудаляемые\n"
    text += f"{EM_USER} <b>Добавленные</b> — можно удалить"
    text += "</blockquote>\n"
    text += f"{EM_WARN} <i>Добавленные админы получают полный доступ к панели управления.</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    # суперовнеры — по одной кнопке (без удаления, с короной)
    for uid in superowners:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"👑 {_admin_short_label(uid)} 👑", callback_data=f"adm_u_show:{uid}",
                                 style="primary", icon_custom_emoji_id="5472308992514464048")
        ])

    # добавленные — кнопка юзера + кнопка «Удалить» в один ряд
    for uid in added:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=_admin_short_label(uid), callback_data=f"adm_u_show:{uid}",
                                 style="primary", icon_custom_emoji_id="5373012449597335010"),
            InlineKeyboardButton(text="Удалить", callback_data=f"adm_del_admin:{uid}",
                                 style="danger", icon_custom_emoji_id="5465665476971471368"),
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(text="Добавить админа", callback_data="adm_add_admin", style="success", icon_custom_emoji_id="5334882760735598374")
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="Назад", callback_data="adm_home", style="danger", icon_custom_emoji_id="5278702045883292456")
    ])

    return text, kb

@dp.callback_query(F.data == "adm_admins")
async def adm_admins(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await _safe_answer(callback)
    text, kb = await _admins_view()
    await _edit_admin(callback, text, kb)

def _settings_view():
    enabled = global_settings.get("is_bot_enabled", True)
    status = f"{EM_GREEN} <b>включён</b>" if enabled else f"{EM_STOP} <b>выключен</b>"
    ch = global_settings.get("alert_channel_id", 0)
    ch_str = f"<code>{ch}</code>" if ch else f"{EM_NO} не подключён"
    if enabled:
        toggle_btn = InlineKeyboardButton(text="Выключить бота", callback_data="adm_toggle", style="danger", icon_custom_emoji_id="5260293700088511294")
    else:
        toggle_btn = InlineKeyboardButton(text="Включить бота", callback_data="adm_toggle", style="success", icon_custom_emoji_id="5416081784641168838")
    news = news_channel_url()
    rows = [
        [toggle_btn],
        [InlineKeyboardButton(text="Ссылка на новости", callback_data="adm_channel", style="primary", icon_custom_emoji_id="5375129357373165375")],
        [InlineKeyboardButton(text="Изменить менеджера", callback_data="adm_manager", style="primary", icon_custom_emoji_id="5467539229468793355")],
    ]
    # кнопку сброса показываем только когда есть что сбрасывать
    if news != DEFAULT_NEWS_URL:
        rows.append([InlineKeyboardButton(text="Вернуть ссылку по умолчанию", callback_data="adm_channel_reset", style="danger", icon_custom_emoji_id="5278702045883292456")])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="adm_home", style="danger", icon_custom_emoji_id="5278702045883292456")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    text = (
        f"{EM_SETTING} <b>Настройки</b>\n"
        "<blockquote>"
        f"{EM_BOLT} <b>Статус бота:</b> {status}\n"
        f"{EM_SEND} <b>Канал алертов:</b> {ch_str}\n"
        f"{EM_SEND} <b>Кнопка «Новости»:</b> <code>{html.escape(news)}</code>\n"
        f"{EM_SEND} <b>Менеджер:</b> <code>{html.escape(manager_mention())}</code>"
        "</blockquote>"
    )
    return text, kb

@dp.callback_query(F.data == "adm_settings")
async def adm_settings(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    text, kb = _settings_view()
    await _edit_admin(callback, text, kb)

@dp.callback_query(F.data == "adm_toggle")
async def adm_toggle(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    global_settings["is_bot_enabled"] = not global_settings.get("is_bot_enabled", True)
    save_data()
    await callback.answer("Переключено")
    text, kb = _settings_view()
    await _edit_admin(callback, text, kb)

@dp.callback_query(F.data == "adm_channel")
async def adm_channel(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    await state.set_state(AdminPanelState.waiting_channel_url)
    await _edit_admin(
        callback,
        f"{EM_SEND} <b>Ссылка на канал</b>\n"
        f"<blockquote>{EM_TIP} Отправь ссылку для кнопки <b>«Новости»</b> в главном меню.\n\n"
        f"Подойдёт <code>@lolzmarket</code>, <code>t.me/lolzmarket</code> или "
        f"<code>https://t.me/+AbCdEf</code>.\n\n"
        f"Сейчас: <code>{html.escape(news_channel_url())}</code></blockquote>",
        adm_back_kb(),
    )

@dp.message(AdminPanelState.waiting_channel_url)
async def adm_channel_set(message: types.Message, state: FSMContext):
    if not _is_panel_admin(message.from_user.id):
        return
    url = normalize_channel_url(message.text or "")
    if not url:
        # состояние не сбрасываем: пусть админ пришлёт ссылку ещё раз
        await message.answer(
            f"{EM_NO} Так нельзя. Ссылка должна вести на t.me — например "
            f"<code>@lolzmarket</code> или <code>https://t.me/lolzmarket</code>.",
            parse_mode="HTML", reply_markup=adm_back_kb(),
        )
        return

    await state.clear()
    global_settings["news_channel_url"] = url
    save_data()
    try:
        await message.delete()
    except Exception:
        pass
    text, kb = _settings_view()
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "adm_channel_reset")
async def adm_channel_reset(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await state.clear()
    global_settings.pop("news_channel_url", None)
    save_data()
    await callback.answer("Ссылка сброшена")
    text, kb = _settings_view()
    await _edit_admin(callback, text, kb)

@dp.callback_query(F.data == "adm_manager")
async def adm_manager(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    await state.set_state(AdminPanelState.waiting_manager_username)
    await _edit_admin(callback, f"{EM_SEND} <b>Менеджер</b>\n<blockquote>{EM_TIP} Отправь username без @.\nСейчас: <code>{html.escape(manager_mention())}</code></blockquote>", adm_back_kb())

@dp.message(AdminPanelState.waiting_manager_username)
async def adm_manager_set(message: types.Message, state: FSMContext):
    if not _is_panel_admin(message.from_user.id): return
    raw=(message.text or "").strip().lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", raw):
        await message.answer(f"{EM_NO} Некорректный username.", parse_mode="HTML", reply_markup=adm_back_kb()); return
    global_settings["manager_username"]=raw
    save_data(); await state.clear()
    try: await message.delete()
    except Exception: pass
    text,kb=_settings_view(); await message.answer(text,parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data == "adm_search")
async def adm_search(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    await state.set_state(AdminPanelState.waiting_search)
    await _edit_admin(callback, f"{EM_PIN} <b>Поиск юзера</b>\n<blockquote>{EM_TIP} Отправь <b>ID</b> пользователя (числом) или @username.</blockquote>", adm_back_kb())

def _resolve_target(q: str):
    """По вводу (ID или @username) находит user_id из базы. Возвращает str id или None."""
    q = q.strip()
    if q.lstrip("-").isdigit():
        return q if q in user_data_storage else None
    # поиск по сохранённому username (без учёта @ и регистра)
    uname = q.lstrip("@").lower()
    for uid, data in user_data_storage.items():
        stored = (data.get("username") or "").lstrip("@").lower()
        if stored and stored == uname:
            return uid
    return None

def _user_profile_view(target: str):
    """Строит карточку юзера (текст + кнопки действий)."""
    u = user_data_storage.get(target, {})
    is_banned = target in [str(x) for x in banned_storage]
    banned = f"{EM_STOP} да" if is_banned else f"{EM_OK} нет"
    uname = u.get("username")
    uname_line = f"{EM_LINK} <b>Username:</b> @{uname}\n" if uname else ""
    text = (
        f"{EM_PIN} <b>Найден пользователь</b>\n"
        "<blockquote>"
        f"{EM_USER} <b>ID:</b> <code>{target}</code>\n"
        f"{uname_line}"
        f"{EM_STOP} <b>Забанен:</b> {banned}\n"
        f"{EM_DEALS} <b>Сделок:</b> <code>{u.get('added_deals', 0)}</code>\n"
        f"{EM_LINK} <b>Язык:</b> <code>{u.get('language', 'ru')}</code>"
        "</blockquote>\n"
        f"{EM_MONEY} <b>Балансы:</b>\n"
        "<blockquote>"
        f"{EM_CARD} <b>RUB:</b> <code>{u.get('balance_rub', 0)}</code>\n"
        f"{EM_CARD} <b>USD:</b> <code>{u.get('balance_usd', 0)}</code>\n"
        f"{EM_DIAMOND} <b>TON:</b> <code>{u.get('balance_ton', 0)}</code>\n"
        f"{EM_STAR} <b>STARS:</b> <code>{u.get('balance_stars', 0)}</code>\n"
        f"{EM_MONEY} <b>ANY (любая):</b> <code>{u.get('balance_any', 0)}</code>"
        + "".join(f"\n{EM_MONEY} <b>{lbl.split()[0]}:</b> <code>{u.get('balance_'+cur, 0)}</code>"
                  for cur, lbl in EXTRA_CURRENCIES if u.get('balance_'+cur, 0)) +
        "</blockquote>\n"
        f"{EM_LINK} <b>Реквизиты:</b>\n"
        "<blockquote>"
        f"<b>TON:</b> {html.escape(str(u.get('ton', '—')))}\n"
        f"<b>RUB:</b> {html.escape(str(u.get('rub', '—')))}\n"
        f"<b>USD:</b> {html.escape(str(u.get('usd', '—')))}\n"
        f"<b>STARS:</b> {html.escape(str(u.get('stars', '—')))}"
        "</blockquote>"
    )
    if is_banned:
        ban_btn = InlineKeyboardButton(text="Разбанить", callback_data=f"adm_u_unban:{target}", style="success", icon_custom_emoji_id="5427009714745517609")
    else:
        ban_btn = InlineKeyboardButton(text="Забанить", callback_data=f"adm_u_ban:{target}", style="danger", icon_custom_emoji_id="5260293700088511294")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить баланс", callback_data=f"adm_u_bal:{target}", style="success", icon_custom_emoji_id="5278467510604160626")],
        [InlineKeyboardButton(text="Кол-во сделок", callback_data=f"adm_u_deals:{target}", style="primary", icon_custom_emoji_id="5357080225463149588")],
        [InlineKeyboardButton(text="Написать юзеру", callback_data=f"adm_u_msg:{target}", style="primary", icon_custom_emoji_id="5467539229468793355")],
        [ban_btn],
        [InlineKeyboardButton(text="Назад к списку", callback_data="adm_home", style="danger", icon_custom_emoji_id="5278702045883292456")],
    ])
    return text, kb

@dp.message(AdminPanelState.waiting_search)
async def adm_search_input(message: types.Message, state: FSMContext):
    if not _is_panel_admin(message.from_user.id):
        return
    await state.clear()
    q = (message.text or "").strip()
    target = _resolve_target(q)
    # если по базе не нашли и это username — пробуем get_chat (юзер мог не /start-ить)
    if not target and not q.lstrip("-").isdigit():
        try:
            chat = await bot.get_chat(q if q.startswith("@") else "@" + q)
            if str(chat.id) in user_data_storage:
                target = str(chat.id)
        except Exception:
            target = None
    try:
        await message.delete()
    except Exception:
        pass
    if not target or target not in user_data_storage:
        await message.answer(f"{EM_NO} <b>Пользователь не найден в базе:</b> <code>{html.escape(q)}</code>", reply_markup=adm_back_kb(), parse_mode="HTML")
        return
    text, kb = _user_profile_view(target)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

def _u_back_kb(target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="К профилю", callback_data=f"adm_u_show:{target}", style="danger", icon_custom_emoji_id="5278702045883292456")]])

@dp.callback_query(F.data.startswith("adm_u_show:"))
async def adm_u_show(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await state.clear()
    await callback.answer()
    target = callback.data.split(":", 1)[1]
    if target not in user_data_storage:
        await _edit_admin(callback, f"{EM_NO} Пользователь не найден.", adm_back_kb()); return
    text, kb = _user_profile_view(target)
    await _edit_admin(callback, text, kb)

# ─── Бан / Разбан ───
@dp.callback_query(F.data.startswith("adm_u_ban:"))
async def adm_u_ban(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    target = callback.data.split(":", 1)[1]
    if _is_panel_admin(int(target)) if target.lstrip("-").isdigit() else False:
        await callback.answer("Нельзя забанить админа", show_alert=True); return
    if target not in [str(u) for u in banned_storage]:
        banned_storage.append(target)
        save_data()
    await _safe_answer(callback, "Забанен")
    try:
        await bot.send_message(int(target), BAN_TEXT, parse_mode="HTML")
    except Exception:
        pass
    text, kb = _user_profile_view(target)
    await _edit_admin(callback, text, kb)

@dp.callback_query(F.data.startswith("adm_u_unban:"))
async def adm_u_unban(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    target = callback.data.split(":", 1)[1]
    banned_ids = [str(u) for u in banned_storage]
    if target in banned_ids:
        # удаляем и строковые, и числовые варианты
        banned_storage[:] = [u for u in banned_storage if str(u) != target]
        save_data()
    await _safe_answer(callback, "Разбанен")
    try:
        await bot.send_message(int(target), f"{EM_OK} <b>Вы разбанены. Доступ к боту восстановлен.</b>", parse_mode="HTML")
    except Exception:
        pass
    text, kb = _user_profile_view(target)
    await _edit_admin(callback, text, kb)

# ─── Изменить баланс (выбор валюты кнопками) ───
BAL_CURRENCIES = [("rub", "RUB"), ("usd", "USD"), ("ton", "TON"), ("stars", "STARS"), ("any", "ANY (любая)"),
                  ("byn", "BYN (бел.руб)"), ("kzt", "KZT (тенге)"), ("uah", "UAH (гривна)"),
                  ("uzs", "UZS (сум)"), ("aed", "AED (дирхам)")]

@dp.callback_query(F.data.startswith("adm_u_bal:"))
async def adm_u_bal(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await _safe_answer(callback)
    await state.clear()
    target = callback.data.split(":", 1)[1]
    u = user_data_storage.get(target, {})
    extra_lines = "".join(f"\n{EM_MONEY} {lbl.split()[0]}: <code>{u.get('balance_'+cur, 0)}</code>"
                          for cur, lbl in EXTRA_CURRENCIES if u.get('balance_'+cur, 0))
    text = (
        f"{EM_MONEY} <b>Изменить баланс</b> <code>{target}</code>\n"
        "<blockquote>"
        f"{EM_CARD} RUB: <code>{u.get('balance_rub', 0)}</code>\n"
        f"{EM_CARD} USD: <code>{u.get('balance_usd', 0)}</code>\n"
        f"{EM_DIAMOND} TON: <code>{u.get('balance_ton', 0)}</code>\n"
        f"{EM_STAR} STARS: <code>{u.get('balance_stars', 0)}</code>\n"
        f"{EM_MONEY} ANY: <code>{u.get('balance_any', 0)}</code>"
        + extra_lines +
        "</blockquote>\n"
        f"{EM_TIP} Выбери валюту для начисления:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    # по 2 валюты в ряд — компактнее
    row = []
    for cur, label in BAL_CURRENCIES:
        row.append(InlineKeyboardButton(text=label, callback_data=f"adm_bal_cur:{target}:{cur}", style="primary", icon_custom_emoji_id="5278467510604160626"))
        if len(row) == 2:
            kb.inline_keyboard.append(row)
            row = []
    if row:
        kb.inline_keyboard.append(row)
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="К профилю", callback_data=f"adm_u_show:{target}", style="danger", icon_custom_emoji_id="5278702045883292456")
    ])
    await _edit_admin(callback, text, kb)

@dp.callback_query(F.data.startswith("adm_bal_cur:"))
async def adm_bal_cur(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await _safe_answer(callback)
    _, target, cur = callback.data.split(":", 2)
    await state.set_state(AdminPanelState.waiting_user_balance)
    await state.update_data(u_target=target, bal_cur=cur)
    cur_val = user_data_storage.get(target, {}).get(f"balance_{cur}", 0)
    await _edit_admin(
        callback,
        f"{EM_MONEY} <b>Баланс {cur.upper()}</b> у <code>{target}</code>\n"
        f"<blockquote>{EM_TIP} Текущий: <code>{cur_val}</code>\n"
        f"Отправь сумму:\n"
        f"<code>100</code> — установить\n"
        f"<code>+50</code> — прибавить\n"
        f"<code>-20</code> — убавить</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data=f"adm_u_bal:{target}", style="danger", icon_custom_emoji_id="5278702045883292456")]])
    )

@dp.message(AdminPanelState.waiting_user_balance)
async def adm_u_bal_input(message: types.Message, state: FSMContext):
    if not _is_panel_admin(message.from_user.id):
        return
    data = await state.get_data()
    target = data.get("u_target")
    cur = data.get("bal_cur")
    val = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass
    if not cur or not target:
        await state.clear()
        return
    key = f"balance_{cur}"
    try:
        u = user_data_storage[target]
        cur_val = float(u.get(key, 0) or 0)
        if val.startswith("+"):
            new_val = cur_val + float(val[1:])
        elif val.startswith("-"):
            new_val = cur_val - float(val[1:])
        else:
            new_val = float(val)
        u[key] = new_val
        save_data()
    except (ValueError, KeyError):
        await message.answer(f"{EM_NO} Некорректная сумма. Отправь число (например <code>100</code>, <code>+50</code>, <code>-20</code>)", reply_markup=_u_back_kb(target), parse_mode="HTML")
        return
    await state.clear()
    await message.answer(f"{EM_OK} <b>Баланс обновлён:</b> {cur.upper()} = <code>{new_val}</code>", parse_mode="HTML")
    text, kb = _user_profile_view(target)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# ─── Кол-во сделок ───
@dp.callback_query(F.data.startswith("adm_u_deals:"))
async def adm_u_deals(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    target = callback.data.split(":", 1)[1]
    await state.set_state(AdminPanelState.waiting_user_deals)
    await state.update_data(u_target=target)
    await _edit_admin(
        callback,
        f"{EM_DEALS} <b>Кол-во сделок</b> <code>{target}</code>\n"
        f"<blockquote>{EM_TIP} Отправь число сделок (например <code>10</code>), либо <code>+5</code> / <code>-2</code> чтобы изменить.</blockquote>",
        _u_back_kb(target)
    )

@dp.message(AdminPanelState.waiting_user_deals)
async def adm_u_deals_input(message: types.Message, state: FSMContext):
    if not _is_panel_admin(message.from_user.id):
        return
    data = await state.get_data()
    target = data.get("u_target")
    val = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass
    try:
        u = user_data_storage[target]
        cur = int(u.get("added_deals", 0) or 0)
        if val.startswith("+"):
            new = cur + int(val[1:])
        elif val.startswith("-"):
            new = max(0, cur - int(val[1:]))
        else:
            new = int(val)
        u["added_deals"] = new
        save_data()
    except (ValueError, KeyError):
        await message.answer(f"{EM_NO} Некорректное число.", reply_markup=_u_back_kb(target), parse_mode="HTML")
        return
    await state.clear()
    await message.answer(f"{EM_OK} <b>Сделок теперь:</b> <code>{new}</code>", parse_mode="HTML")
    text, kb = _user_profile_view(target)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# ─── Написать юзеру ───
@dp.callback_query(F.data.startswith("adm_u_msg:"))
async def adm_u_msg(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    target = callback.data.split(":", 1)[1]
    await state.set_state(AdminPanelState.waiting_user_msg)
    await state.update_data(u_target=target)
    await _edit_admin(
        callback,
        f"{EM_SEND} <b>Написать юзеру</b> <code>{target}</code>\n"
        f"<blockquote>{EM_TIP} Отправь текст — он придёт этому пользователю в бота.</blockquote>",
        _u_back_kb(target)
    )

@dp.message(AdminPanelState.waiting_user_msg)
async def adm_u_msg_input(message: types.Message, state: FSMContext):
    if not _is_panel_admin(message.from_user.id):
        return
    data = await state.get_data()
    target = data.get("u_target")
    text_to_send = message.text or ""
    await state.clear()
    try:
        await message.delete()
    except Exception:
        pass
    try:
        await bot.send_message(chat_id=int(target), text=text_to_send)
        await message.answer(f"{EM_OK} <b>Сообщение отправлено</b> <code>{target}</code>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"{EM_NO} <b>Не удалось отправить:</b> <code>{html.escape(str(e))}</code>", parse_mode="HTML")
    prof_text, kb = _user_profile_view(target)
    await message.answer(prof_text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    await state.set_state(AdminPanelState.waiting_broadcast)
    await _edit_admin(callback, f"{EM_SEND} <b>Рассылка</b>\n<blockquote>{EM_TIP} Отправь текст, который разослать всем пользователям бота.</blockquote>", adm_back_kb())

@dp.message(AdminPanelState.waiting_broadcast)
async def adm_broadcast_input(message: types.Message, state: FSMContext):
    if not _is_panel_admin(message.from_user.id):
        return
    text = message.text or ""
    await state.update_data(bc_text=text)
    total = len(user_data_storage)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Разослать ({total})", callback_data="adm_bc_send", style="success", icon_custom_emoji_id="5427009714745517609")],
        [InlineKeyboardButton(text="Отмена", callback_data="adm_home", style="danger", icon_custom_emoji_id="5278702045883292456")],
    ])
    await message.answer(f"{EM_SEND} <b>Предпросмотр рассылки:</b>\n<blockquote>" + html.escape(text) + f"</blockquote>\n{EM_USERS} <b>Получателей:</b> <code>{total}</code>", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "adm_bc_send")
async def adm_bc_send(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    data = await state.get_data()
    text = data.get("bc_text")
    await state.clear()
    if not text:
        await callback.answer("Нет текста для рассылки", show_alert=True); return
    await callback.answer("Рассылка запущена")
    try:
        await callback.message.edit_text("📢 Рассылка запущена, ожидайте...", parse_mode="HTML")
    except Exception:
        pass
    ok = 0
    fail = 0
    for uid in list(user_data_storage.keys()):
        try:
            await bot.send_message(chat_id=int(uid), text=text)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await callback.message.answer(
        f"{EM_SEND} <b>Рассылка завершена</b>\n<blockquote>{EM_OK} <b>Доставлено:</b> <code>{ok}</code>\n{EM_NO} <b>Ошибок:</b> <code>{fail}</code></blockquote>",
        reply_markup=adm_back_kb(), parse_mode="HTML"
    )

@dp.callback_query(F.data == "adm_add_admin")
async def adm_add_admin(callback: types.CallbackQuery, state: FSMContext):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    await state.set_state(AdminPanelState.waiting_add_admin)
    await _edit_admin(callback, f"{EM_USER} <b>Добавить админа</b>\n<blockquote>{EM_TIP} Отправь <b>ID</b> пользователя (целое число).</blockquote>", adm_back_kb())

@dp.message(AdminPanelState.waiting_add_admin)
async def adm_add_admin_input(message: types.Message, state: FSMContext):
    if not _is_panel_admin(message.from_user.id):
        return
    uid_str = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass
    if not uid_str.lstrip("-").isdigit():
        await message.answer(f"{EM_NO} <b>Некорректный ID.</b> Отправь целое число.", parse_mode="HTML")
        return
    uid = int(uid_str)
    if uid in ADMIN_PANEL_IDS:
        await state.clear()
        await message.answer(f"{EM_CROWN} <b>Это суперовнер</b>, у него и так есть доступ.", parse_mode="HTML")
        return
    if uid in global_settings.get("added_admins", []):
        await state.clear()
        await message.answer(f"{EM_TIP} Админ <code>{uid}</code> уже в списке.", reply_markup=adm_back_kb(), parse_mode="HTML")
        return
    if "added_admins" not in global_settings:
        global_settings["added_admins"] = []
    global_settings["added_admins"].append(uid)
    save_data()
    await state.clear()
    await message.answer(f"{EM_OK} <b>Админ</b> <code>{uid}</code> <b>добавлен!</b>", parse_mode="HTML")
    text, kb = await _admins_view()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("adm_del_admin:"))
async def adm_del_admin(callback: types.CallbackQuery):
    if not _is_panel_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    uid_str = callback.data.split(":", 1)[1]
    try:
        uid = int(uid_str)
    except ValueError:
        await callback.answer("Ошибка", show_alert=True); return
    if "added_admins" in global_settings and uid in global_settings["added_admins"]:
        global_settings["added_admins"].remove(uid)
        save_data()
        await callback.answer(f"Админ удален")
    else:
        await callback.answer("Админ не найден", show_alert=True); return
    text, kb = await _admins_view()
    await _edit_admin(callback, text, kb)

# ─── Main ──────────────────────────────────────────────────────────────────────
async def setup_menu_button(bot: Bot):
    """Кнопка «Меню» слева от поля ввода открывает мини-приложение."""
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="MiniApp",
            web_app=WebAppInfo(url=WEBAPP_URL),
        )
    )

async def setup_bot_username(bot: Bot):
    """Узнаёт свой @username, чтобы ссылки-приглашения вели именно в этого бота."""
    global BOT_USERNAME
    me = await bot.get_me()
    if me.username:
        BOT_USERNAME = me.username
        print_console_log(f"Бот опознан: @{BOT_USERNAME}")

async def main():
    # Служебные вызовы не критичны для работы бота. Если Telegram ответит таймаутом,
    # процесс не должен падать: systemd перезапустит его, cloudflared выдаст новый
    # адрес, и мини-приложение во всех старых сообщениях сломается.
    for step, coro in (("get_me", setup_bot_username),
                       ("set_my_commands", setup_bot_commands),
                       ("set_chat_menu_button", setup_menu_button)):
        try:
            await coro(bot)
        except Exception as e:
            logging.error(f"Не удалось выполнить {step}: {e}. Бот продолжит работу.")

    print_console_log("Бот успешно запущен и готов к работе!")
    await send_alert("<tg-emoji emoji-id=\"5416081784641168838\">🟢</tg-emoji> <b>LoIzDealsbot запущен</b>\n<blockquote>Бот и Mini App готовы к работе.</blockquote>")
    # drop_pending_updates: не обрабатывать старые (протухшие) апдейты после рестарта
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
