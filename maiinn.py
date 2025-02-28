import threading
from config import API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES, BOT_ID, PREFIX,AUTORESTART,ADMIN
from zlapi import ZaloAPI
from zlapi.models import Message
from modules.nscl import SCLHandler
from colorama import Fore, Style, init
import time
from datetime import datetime
import json
import os
from zlapi import *
from zlapi.models import *
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys
import requests
from huang import CommandHandler

class ResetBot:
    def __init__(self, reset_interval=38800):
        self.reset_event = threading.Event()
        self.reset_interval = reset_interval
        self.load_autorestart_setting()

    def load_autorestart_setting(self):
        try:
            self.autorestart = AUTORESTART

            if self.autorestart:
                logger.info("Chế độ auto restart đang được bật")
                threading.Thread(target=self.reset_code_periodically, daemon=True).start()
            else:
                logger.info("Chế độ auto restart đang được tắt")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình autorestart: {e}")
            self.autorestart = False

    def reset_code_periodically(self):
        while not self.reset_event.is_set():
            time.sleep(self.reset_interval)
            logger.restart("Đang tiến hành khởi động lại bot...")
            self.restart_bot()

    def restart_bot(self):
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            gui_message = f"Bot khởi động lại thành công vào lúc: {current_time}"
            logger.restart(gui_message)
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            logger.error(f"Lỗi khi khởi động lại bot: {e}")

init(autoreset=True)


background_path = 'background.jpg'
current_time = datetime.now()
formatted_time = current_time.strftime("%d/%m/%Y [%H:%M:%S]")

def delete_file(filename):
    try:
        os.remove(filename)
    except OSError as e:
        print(f"Error deleting file {filename}: {e}")

def make_round_avatar(avatar):
    mask = Image.new('L', avatar.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, avatar.size[0], avatar.size[1]), fill=255)
    round_avatar = Image.new('RGBA', avatar.size)
    round_avatar.paste(avatar, (0, 0), mask)
    return round_avatar

def initialize_group_info(bot, allowed_thread_ids):
    for thread_id in allowed_thread_ids:
        group_info = bot.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id, None)
        if group_info:
            bot.group_info_cache[thread_id] = {
                "name": group_info['name'],
                "member_list": group_info['memVerList'],
                "total_member": group_info['totalMember']
            }
        else:
            print(f"Bỏ qua nhóm {thread_id}")

def check_member_changes(bot, thread_id):
    current_group_info = bot.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id, None)
    cached_group_info = bot.group_info_cache.get(thread_id, None)
    if not cached_group_info or not current_group_info:
        return [], []
    old_members = set([member.split('_')[0] for member in cached_group_info["member_list"]])
    new_members = set([member.split('_')[0] for member in current_group_info['memVerList']])
    joined_members = new_members - old_members
    left_members = old_members - new_members
    bot.group_info_cache[thread_id] = {
        "name": current_group_info['name'],
        "member_list": current_group_info['memVerList'],
        "total_member": current_group_info['totalMember']
    }
    return joined_members, left_members

def create_welcome_image_with_avatar(member_name, avatar_url, font_folder, group_name, member_number, background_path=None):
    os.makedirs(font_folder, exist_ok=True)
    
    width, height = 800, 400
    background = Image.new("RGB", (width, height))

    try:
        if background_path and os.path.exists(background_path):
            bg = Image.open(background_path).convert("RGB")
        else:
            bg = Image.open("background.jpg").convert("RGB")
        bg = bg.resize((width, height))
        background.paste(bg, (0, 0))
    except:
        draw = ImageDraw.Draw(background)
        for y in range(height):
            r = int(0 * (1 - y/height))
            g = int(20 * (1 - y/height))
            b = int(50 * (1 - y/height))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    draw = ImageDraw.Draw(background)

    card_width, card_height = 600, 300
    card_x, card_y = (width - card_width) // 2, (height - card_height) // 2
    
    overlay = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 120))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=5))
    
    mask = Image.new("L", (card_width, card_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (card_width, card_height)], radius=20, fill=255)
    
    background.paste(overlay, (card_x, card_y), mask)

    try:
        title_font = ImageFont.truetype(os.path.join(font_folder, "emoji.ttf"), 30)  # Nhỏ hơn
        regular_font = ImageFont.truetype(os.path.join(font_folder, "paci.ttf"), 25)  # Nhỏ hơn
    except:
        title_font = ImageFont.load_default()
        regular_font = ImageFont.load_default()

    try:
        avatar_size = 100
        avatar_response = requests.get(avatar_url)
        avatar = Image.open(BytesIO(avatar_response.content)).convert("RGBA")
        avatar = avatar.resize((avatar_size, avatar_size))
        
        frame_size = avatar_size + 10
        frame = Image.new('RGBA', (frame_size, frame_size))
        frame_draw = ImageDraw.Draw(frame)
        frame_draw.ellipse([0, 0, frame_size, frame_size], fill=(255, 165, 0, 255))
        
        mask = Image.new('L', (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)
        
        avatar_x, avatar_y = card_x + 50, card_y + 50
        background.paste(frame, (avatar_x - 5, avatar_y - 5), frame)
        background.paste(avatar, (avatar_x, avatar_y), mask)
    except Exception as e:
        print(f"Error processing avatar: {e}")

    text_x, text_y = card_x + 200, card_y + 40
    
    draw.text((text_x, text_y), f"Tên: {member_name}", font=regular_font, fill=(255, 255, 255))
    draw.text((text_x, text_y + 30), f"Thành viên thứ: {member_number}", font=regular_font, fill=(255, 255, 255))

    draw.line([(text_x, text_y + 60), (text_x + 280, text_y + 60)], fill=(255, 255, 255), width=2)  # Đường kẻ ngang

    draw.text((text_x, text_y + 80), "WELCOME TO GROUP:", font=title_font, fill=(0, 255, 255))
    draw.text((text_x, text_y + 110), f"> Chào mừng: {member_name}", font=regular_font, fill=(255, 255, 255))
    draw.text((text_x, text_y + 150), f"Đến với nhóm: {group_name}", font=regular_font, fill=(255, 255, 255))

    output_path = "welcome.jpg"
    background.save(output_path, quality=95)
    return output_path

def handle_group_member(bot, message_object, author_id, thread_id, thread_type, background_path=None):
    joined_members, left_members = check_member_changes(bot, thread_id)
    if joined_members:
        for member_id in joined_members:
            try:
                member_info = bot.fetchUserInfo(member_id).changed_profiles[member_id]
                welcome_image_path = create_welcome_image_with_avatar(
                    member_info.displayName,
                    member_info.avatar,
                    "font",
                    bot.group_info_cache[thread_id]['name'],
                    bot.group_info_cache[thread_id]['total_member'],
                    background_path
                )
                messagesend = Message(
                    text=f"🥳 Chào mừng {member_info.displayName} \n"
                         f"🎉 Đã tham gia {bot.group_info_cache[thread_id]['name']} \n"
                         f"🕒 Vào lúc {formatted_time} \n"
                         f"👥 Thành viên hiện tại: {bot.group_info_cache[thread_id]['total_member']}"
                )
                bot.sendLocalImage(welcome_image_path, thread_id, thread_type, message=messagesend, width=600, height=300, ttl=120000)
                delete_file(welcome_image_path)
            except Exception as e:
                print(f"Lỗi khi xử lý thành viên mới {member_id}: {e}")

    if left_members:
        for member_id in left_members:
            try:
                member_info = bot.fetchUserInfo(member_id).changed_profiles[member_id]
                farewell_image_path = create_farewell_image_with_avatar(
                    member_info.displayName,
                    member_info.avatar,
                    "font",
                    bot.group_info_cache[thread_id]['name'],
                    background_path
                )
                messagesend = Message(
                    text=f"💔 Chào tạm biệt {member_info.displayName} 🤧 \n"
                         f"vào lúc {formatted_time} \n"
                         f"số thành viên còn lại: {bot.group_info_cache[thread_id]['total_member']}"
                )
                bot.sendLocalImage(farewell_image_path, thread_id, thread_type, message=messagesend, width=600, height=300,ttl=120000)
                delete_file(farewell_image_path)
            except Exception as e:
                print(f"Lỗi khi xử lý thành viên rời {member_id}: {e}")


class Client(ZaloAPI):
    def __init__(self, api_key, secret_key, imei, session_cookies,reset_interval=7200):
        super().__init__(api_key, secret_key, imei=imei, session_cookies=session_cookies)
        self.scl_handler = SCLHandler(self)
        self.del_enabled = {}
        self.default_del_enabled = True
        self.reset_bot = ResetBot(reset_interval)
        self.command_handler = CommandHandler(self)
        self.group_info_cache = {}
        self.background_path = background_path
        all_group = self.fetchAllGroups()
        allowed_thread_ids = list(all_group.gridVerMap.keys())
        initialize_group_info(self, allowed_thread_ids)
        self.start_member_check_thread(allowed_thread_ids)
    
    def start_member_check_thread(self, allowed_thread_ids):
        def check_members_loop():
            while True:
                for thread_id in allowed_thread_ids:
                    handle_group_member(self, None, None, thread_id, ThreadType.GROUP, self.background_path)
                time.sleep(1)

        thread = threading.Thread(target=check_members_loop)
        thread.daemon = True
        thread.start()

    def handle_message(self, mid, author_id, message, message_object, thread_id, thread_type):
        try:
            message_text = message.text if isinstance(message, Message) else str(message)

            current_time = time.strftime("%H:%M:%S - %d/%m/%Y", time.localtime())
            print(f"------------------------------\n"
                  f"Tin Nhắn: {message_text}\n"
                  f" ID người dùng: {author_id}\n"
                  f"ID nhóm: {thread_id}\n"
                  f"Thread Type: {thread_type}\n"
                  f"thời gian: {current_time}\n"
                  f"------------------------------")

            if isinstance(message, str):
                self.command_handler.handle_command(
                    message, author_id, message_object, thread_id, thread_type
                )
            if message_text.startswith(PREFIX + "scl"):
                self.scl_handler.handle_scl_command(message_text, message_object, thread_id, thread_type, author_id)
            elif author_id in self.scl_handler.next_stepscl:
                self.scl_handler.handle_selection(message_text, message_object, thread_id, thread_type, author_id)
            else:
                print(f"Unrecognized message: {message_text}")

            if self.del_enabled.get(thread_id, self.default_del_enabled):
                self.check_and_delete_links(author_id, message_text, message_object, thread_id, thread_type)


        except Exception as e:
            print(f"Error handling message: {e}")

    def check_and_delete_links(self, author_id, message_text, message_object, thread_id, thread_type):
        try:
            # Use admin IDs from config
            admin_ids = ADMIN

            # Handle commands to enable/disable link deletion (only admins)
            if author_id in admin_ids:
                if message_text.lower() == 'dellink on':
                    self.default_del_enabled = True
                    self.replyMessage(Message(text="đã bật xóa link."), message_object, thread_id, thread_type)
                    print("Link deletion enabled")
                    return
                elif message_text.lower() == 'dellink off':
                    self.default_del_enabled = False
                    self.replyMessage(Message(text="đã tắt xóa link."), message_object, thread_id, thread_type)
                    print("Link deletion disabled")
                    return
                

            # Load banned links
            with open('modules/cache/banned_links.txt', 'r', encoding='utf-8') as file:
                banned_links = [line.strip().lower() for line in file.readlines() if line.strip()]

            # Check if message contains any banned link
            contains_link = any(link in message_text.lower() for link in banned_links)

            # If banned link found and author is not the bot itself, delete the message (if deletion is enabled)
            if self.default_del_enabled and contains_link :
                try:
                    self.deleteGroupMsg(
                        msgId=message_object.msgId,
                        ownerId=author_id,
                        clientMsgId=message_object.cliMsgId,
                        groupId=thread_id
                    )
                    print(f"Deleted a message containing a banned link from {author_id} in group {thread_id}")
                except Exception as e:
                    print(f"Error while deleting message: {e}")
        except Exception as e:
            print(f"Error loading banned links or processing message: {e}")


    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        threading.Thread(target=self.handle_message, args=(mid, author_id, message, message_object, thread_id, thread_type)).start()

if __name__ == "__main__":
    try:
        client = Client(API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES)
        client.listen(thread=True, delay=0,run_forever=True, type='websocket')
    except Exception as e:
        logger.error(f"Lỗi rồi, Không thể login...: {e}")
        python = sys.executable
        os.execl(python, python, *sys.argv)
        time.sleep(10)

