from config import Config
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
import random
import asyncio
from helper.db import manage_db
from pyrogram.errors import UserNotParticipant
from helper.markup import MakeCaptchaMarkup
from helper.captcha_maker import number_, emoji_


# Prepare bot
app = Client(Config.SESSION_NAME, api_id=Config.APP_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)
# Local database for saving user info
LocalDB = {}
ch_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text="機器人有問題請找", url="https://t.me/Kevin_RX"),
                                    InlineKeyboardButton(text="喜歡玩PlayStation可以進來討論喔", url="https://t.me/PlayStationTw")]])


@app.on_chat_member_updated()
async def check_chat_captcha(client, message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    chat = manage_db().chat_in_db(chat_id)
    if not chat:
        return
    try:
        user_s = await client.get_chat_member(chat_id, user_id)
        if (user_s.is_member is False) and (LocalDB.get(user_id, None) is not None):
            try:
                await client.delete_messages(
                    chat_id=chat_id,
                    message_ids=LocalDB[user_id]["msg_id"]
                )
            except:
                pass
            return
        elif (user_s.is_member is False):
            return
    except UserNotParticipant:
        return
    chat_member = await client.get_chat_member(chat_id, user_id)
    if chat_member.restricted_by:
        if chat_member.restricted_by.id == (await client.get_me()).id:
            pass
        else:
            return
    try:
        if LocalDB.get(user_id, None) is not None:
            try:
                await client.send_message(
                    chat_id=chat_id,
                    text=f"{message.from_user.mention} 未通過驗證再次加入群！\n\n"
                         f"他可以在 5 分鐘後重試。",
                    disable_web_page_preview=True
                )
                await client.delete_messages(chat_id=chat_id,
                                             message_ids=LocalDB[user_id]["msg_id"])
            except:
                pass
            await asyncio.sleep(300)
            del LocalDB[user_id]
    except:
        pass
    try:
        await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
    except:
        return
    await client.send_message(chat_id,
                              text=f"{message.from_user.mention} 請確認你是真人，不是機器人!",
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="立即驗證", callback_data=f"verify_{chat_id}_{user_id}")]]))
        
@app.on_message(filters.command(["captcha"]) & ~filters.private)
async def add_chat(bot, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user = await bot.get_chat_member(chat_id, user_id)
    if user.status == "creator" or user.status == "administrator" or user.user.id in Config.SUDO_USERS:
        chat = manage_db().chat_in_db(chat_id)
        if chat:
            await message.reply_text("驗證碼已在此處啟用，使用 /remove 關閉")
        else:
            await message.reply_text(text=f"請選擇驗證碼類型",
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="數字", callback_data=f"new_{chat_id}_{user_id}_N"),
                                                                        InlineKeyboardButton(text="表情符號", callback_data=f"new_{chat_id}_{user_id}_E")]]))
        
@app.on_message(filters.command(["help"]))
async def start_chat(bot, message):
    await message.reply_text(text="/captcha - 打開驗證碼：有兩種類型的驗證碼\n/remove - 關閉驗證碼",
                             reply_markup=ch_markup)
    
@app.on_message(filters.command(["start"]))
async def help_chat(bot, message):
    await message.reply_text(text="我可以幫助您保護您的群組免受機器人的侵害。\n\n查看 /help 了解更多。",
                             reply_markup=ch_markup)
    
@app.on_message(filters.command(["remove"]) & ~filters.private)
async def del_chat(bot, message):
    chat_id = message.chat.id
    user = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if user.status == "creator" or user.status == "administrator" or user.user.id in Config.SUDO_USERS:
        j = manage_db().delete_chat(chat_id)
        if j:
            await message.reply_text("驗證碼已關閉")
        
@app.on_callback_query()
async def cb_handler(bot, query):
    cb_data = query.data
    if cb_data.startswith("new_"):
        chat_id = query.data.rsplit("_")[1]
        user_id = query.data.split("_")[2]
        captcha = query.data.split("_")[3]
        if query.from_user.id != int(user_id):
            await query.answer("此消息不適合您！", show_alert=True)
            return
        if captcha == "N":
            type_ = "數字"
        elif captcha == "E":
            type_ = "表情符號"
        chk = manage_db().add_chat(int(chat_id), captcha)
        if chk == 404:
            await query.message.edit("Captcha 已在此處啟用，請使用 /remove 關掉")
            return
        else:
            await query.message.edit(f"{type_} 驗證碼已打開。")
    elif cb_data.startswith("verify_"):
        chat_id = query.data.split("_")[1]
        user_id = query.data.split("_")[2]
        if query.from_user.id != int(user_id):
            await query.answer("此消息不適合您!", show_alert=True)
            return
        chat = manage_db().chat_in_db(int(chat_id))
        print("處理數據時")
        if chat:
            c = chat["captcha"]
            markup = [[],[],[]]
            if c == "N":
                print("處理號碼驗證碼")
                await query.answer("為您創建驗證碼")
                data_ = number_()
                _numbers = data_["answer"]
                list_ = ["0","1","2","3","5","6","7","8","9"]
                random.shuffle(list_)
                tot = 2
                LocalDB[int(user_id)] = {"answer": _numbers, "list": list_, "mistakes": 0, "captcha": "N", "total":tot, "msg_id": None}
                count = 0
                for i in range(3):
                    markup[0].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
                for i in range(3):
                    markup[1].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
                for i in range(3):
                    markup[2].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
            elif c == "E":
                print("處理號碼驗證碼")
                await query.answer("為您創建驗證碼")
                data_ = emoji_()
                _numbers = data_["answer"]
                list_ = data_["list"]
                count = 0
                tot = 3
                for i in range(5):
                    markup[0].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
                for i in range(5):
                    markup[1].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
                for i in range(5):
                    markup[2].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
                LocalDB[int(user_id)] = {"answer": _numbers, "list": list_, "mistakes": 0, "captcha": "E", "total":tot, "msg_id": None}
            c = LocalDB[query.from_user.id]['captcha']
            if c == "N":
                typ_ = "數字"
            if c == "E":
                typ_ = "表情符號"
            msg = await bot.send_photo(chat_id=chat_id,
                            photo=data_["captcha"],
                            caption=f"{query.from_user.mention} 選擇所有您在圖片中看到的 {typ_} , 你只能錯 {tot} 次。",
                            reply_markup=InlineKeyboardMarkup(markup))
            LocalDB[query.from_user.id]['msg_id'] = msg.message_id
            await query.message.delete()
    if cb_data.startswith("jv_"):
        chat_id = query.data.rsplit("_")[1]
        user_id = query.data.split("_")[2]
        _number = query.data.split("_")[3]
        if query.from_user.id != int(user_id):
            await query.answer("此消息不適合您！", show_alert=True)
            return
        if query.from_user.id not in LocalDB:
            await query.answer("重新加入後重試！", show_alert=True)
            return
        c = LocalDB[query.from_user.id]['captcha']
        tot = LocalDB[query.from_user.id]["total"]
        if c == "N":
            typ_ = "數字"
        if c == "E":
            typ_ = "表情符號"
        if _number not in LocalDB[query.from_user.id]["answer"]:
            LocalDB[query.from_user.id]["mistakes"] += 1
            await query.answer(f"You pressed wrong {typ_}!", show_alert=True)
            n = tot - LocalDB[query.from_user.id]['mistakes']
            if n == 0:
                await query.message.edit_caption(f"{query.from_user.mention}, 您沒有通過驗證碼！\n\n"
                                               f"您可以在 5 分鐘後重試。",
                                               reply_markup=None)
                await asyncio.sleep(300)
                del LocalDB[query.from_user.id]
                return
            markup = MakeCaptchaMarkup(query.message["reply_markup"]["inline_keyboard"], _number, "❌")
            await query.message.edit_caption(f"{query.from_user.mention}, 選擇所有您在圖片中看到的 {typ_} 。 "
                                           f"您只能 {n} 次錯誤。",
                                           reply_markup=InlineKeyboardMarkup(markup))
        else:
            LocalDB[query.from_user.id]["answer"].remove(_number)
            markup = MakeCaptchaMarkup(query.message["reply_markup"]["inline_keyboard"], _number, "✅")
            await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(markup))
            if not LocalDB[query.from_user.id]["answer"]:
                await query.answer("你通過了🥳驗證！", show_alert=True)
                del LocalDB[query.from_user.id]
                await bot.unban_chat_member(chat_id=query.message.chat.id, user_id=query.from_user.id)
                await query.message.delete(True)
            await query.answer()
    elif cb_data.startswith("done_"):
        await query.answer("不要再次單擊相同的按鈕", show_alert=True)
    elif cb_data.startswith("wrong_"):
        await query.answer("不要再次單擊相同的按鈕", show_alert=True)
        
if __name__ == "__main__":
    app.run()
