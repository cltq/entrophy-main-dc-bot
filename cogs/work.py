import json
import os
import random
import re
import string
from datetime import datetime, timedelta
from typing import Any, Optional, Sequence

import discord
from discord import app_commands
from discord.ext import commands, tasks

DATA_FILE: str = "data/user_data.json"
THAI_LAYOUT_CONFIG_FILE: str = "data/guild_thai_layout_config.json"
TEMP_NOTE_CODES: dict[int, dict[str, Any]] = {}

QWERTY_TO_THAI_MAP: dict[str, str] = {
    'q': 'ๆ', 'w': 'ไ', 'e': 'ำ', 'r': 'พ', 't': 'ะ', 'y': 'า', 'u': 'ส', 'i': 'ด', 'o': 'ฟ', 'p': 'ก', '[': 'ฮ', ']': 'ฺ',
    'a': 'ฤ', 's': 'ฆ', 'd': 'ฏ', 'f': 'โ', 'g': 'ฌ', 'h': '็', 'j': '๋', 'k': 'ษ', 'l': 'ศ', ';': 'ซ', "'": 'ฅ',
    'z': 'ผ', 'x': 'ป', 'c': 'ฉ', 'v': 'ฮ', 'b': 'ิ', 'n': 'ื', 'm': 'ท', ',': 'ม', '.': 'ใ', '/': 'ฝ',
    '1': '๑', '2': '๒', '3': '๓', '4': '๔', '5': '๕', '6': '๖', '7': '๗', '8': '๘', '9': '๙', '0': '๐'
}


def qwerty_to_thai_text(text: str) -> str:
    """แปลงข้อความที่พิมพ์ด้วย QWERTY เป็นตัวอักษรไทย"""
    result_chars = []
    for char in text:
        lower = char.lower()
        if lower in QWERTY_TO_THAI_MAP:
            thai_char = QWERTY_TO_THAI_MAP[lower]
            result_chars.append(thai_char)
        else:
            result_chars.append(char)
    return ''.join(result_chars)


def convert_to_thai(text: str) -> str:
    """นามแฝงสำหรับการแปลง QWERTY->ไทย"""
    return qwerty_to_thai_text(text)


def load_thai_layout_config():
    os.makedirs('data', exist_ok=True)
    if not os.path.exists(THAI_LAYOUT_CONFIG_FILE):
        return {}
    try:
        with open(THAI_LAYOUT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_thai_layout_config(data):
    os.makedirs('data', exist_ok=True)
    with open(THAI_LAYOUT_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_likely_mistyped_thai(text: str) -> bool:
    if not text or len(text.strip()) < 2:
        return False

    if re.search('[\u0E00-\u0E7F]', text):
        return False

    mappable = sum(1 for c in text if c in QWERTY_TO_THAI_MAP)
    total = sum(1 for c in text if c.isalnum() or c in "[]{};:'\",.<>/?`~!@#$%^&*()-_=+")
    if total == 0:
        return False

    ratio = mappable / total
    words = [w for w in re.split(r'\s+', text.strip()) if w]

    if ratio >= 0.55 and len(words) > 1:
        return True
    if ratio >= 0.70 and len(text) >= 4:
        return True

    return False


class TodoListView(discord.ui.View):
    """มุมมองโต้ตอบสำหรับจัดการรายการสิ่งที่ต้องทำ"""
    def __init__(self, user_id: int, todos: list[dict], context: Any) -> None:
        super().__init__(timeout=300)
        self.user_id = user_id
        self.todos = todos
        self.context = context

    @discord.ui.button(label="✅ ทำเสร็จแล้ว", style=discord.ButtonStyle.green)
    async def mark_complete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ คุณไม่สามารถโต้ตอบกับสิ่งนี้ได้!", ephemeral=True)
            return
        
        if not self.todos:
            await interaction.response.send_message("❌ ไม่มีรายการที่ต้องทำ!", ephemeral=True)
            return

        # สร้างเมนูเลือกเพื่อเลือกรายการที่ทำเสร็จ
        options = [
            discord.SelectOption(
                label=todo['text'][:100],
                value=str(idx),
                emoji="📝"
            )
            for idx, todo in enumerate(self.todos)
        ]

        class CompleteSelect(discord.ui.View):
            def __init__(self, parent):
                super().__init__(timeout=60)
                self.parent = parent

            @discord.ui.select(
                placeholder="เลือกรายการที่ทำเสร็จ...",
                options=options[:25]  # Discord limit
            )
            async def select_todo(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                if select_interaction.user.id != self.parent.user_id:
                    await select_interaction.response.send_message("❌ ไม่ใช่รายการของคุณ!", ephemeral=True)
                    return

                idx = int(select.values[0])
                self.parent.todos[idx]['completed'] = True
                self.parent.todos[idx]['completed_at'] = datetime.now().isoformat()
                save_user_data(self.parent.user_id, self.parent.todos)
                
                await select_interaction.response.send_message(
                    f"✅ ทำเครื่องหมาย **{self.parent.todos[idx]['text']}** ว่าเสร็จแล้ว!",
                    ephemeral=True
                )

        view = CompleteSelect(self)
        await interaction.response.send_message("เลือกรายการที่ทำเสร็จ:", view=view, ephemeral=True)

    @discord.ui.button(label="🗑️ ลบ", style=discord.ButtonStyle.red)
    async def delete_todo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ คุณไม่สามารถโต้ตอบกับสิ่งนี้ได้!", ephemeral=True)
            return
        
        if not self.todos:
            await interaction.response.send_message("❌ ไม่มีรายการที่ต้องลบ!", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=todo['text'][:100],
                value=str(idx),
                emoji="🗑️"
            )
            for idx, todo in enumerate(self.todos)
        ]

        class DeleteSelect(discord.ui.View):
            def __init__(self, parent):
                super().__init__(timeout=60)
                self.parent = parent

            @discord.ui.select(
                placeholder="เลือกรายการที่จะลบ...",
                options=options[:25]
            )
            async def select_delete(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                if select_interaction.user.id != self.parent.user_id:
                    await select_interaction.response.send_message("❌ ไม่ใช่รายการของคุณ!", ephemeral=True)
                    return

                idx = int(select.values[0])
                deleted_text = self.parent.todos[idx]['text']
                del self.parent.todos[idx]
                save_user_data(self.parent.user_id, self.parent.todos)
                
                await select_interaction.response.send_message(
                    f"🗑️ ลบ **{deleted_text}** แล้ว!",
                    ephemeral=True
                )

        view = DeleteSelect(self)
        await interaction.response.send_message("เลือกรายการที่จะลบ:", view=view, ephemeral=True)

    @discord.ui.button(label="📋 ดูทั้งหมด", style=discord.ButtonStyle.blurple)
    async def view_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ คุณไม่สามารถโต้ตอบกับสิ่งนี้ได้!", ephemeral=True)
            return

        embed = create_todo_embed(self.todos, self.user_id)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class NotesView(discord.ui.View):
    """มุมมองโต้ตอบสำหรับจัดการบันทึก"""
    def __init__(self, user_id: int, notes: list[dict], context: Any) -> None:
        super().__init__(timeout=300)
        self.user_id = user_id
        self.notes = notes
        self.context = context

    @discord.ui.button(label="📝 ดูบันทึก", style=discord.ButtonStyle.blurple)
    async def view_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ ไม่ใช่บันทึกของคุณ!", ephemeral=True)
            return

        if not self.notes:
            await interaction.response.send_message("❌ ไม่พบบันทึก!", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=note['title'][:100],
                value=str(idx),
                emoji="📄"
            )
            for idx, note in enumerate(self.notes)
        ]

        class ViewSelect(discord.ui.View):
            def __init__(self, parent):
                super().__init__(timeout=60)
                self.parent = parent

            @discord.ui.select(
                placeholder="เลือกบันทึกที่จะดู...",
                options=options[:25]
            )
            async def select_note(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                if select_interaction.user.id != self.parent.user_id:
                    await select_interaction.response.send_message("❌ ไม่ใช่บันทึกของคุณ!", ephemeral=True)
                    return

                idx = int(select.values[0])
                note = self.parent.notes[idx]
                
                embed = discord.Embed(
                    title=f"📝 {note['title']}",
                    description=note['content'],
                    color=discord.Color.gold(),
                    timestamp=datetime.fromisoformat(note['created_at'])
                )
                embed.set_footer(text="สร้างเมื่อ")
                
                # แสดงไฟล์แนบถ้ามีพร้อมลิงก์ที่คลิกได้
                if note.get('attachments'):
                    attachment_links = []
                    for att in note['attachments']:
                        file_size = att.get('size', 0)
                        size_str = f"{file_size / 1024 / 1024:.2f}MB" if file_size > 1024 * 1024 else f"{file_size / 1024:.2f}KB"
                        link = f"[📎 {att['filename']}]({att['url']}) ({size_str})"
                        attachment_links.append(link)
                    
                    attachment_info = "\n".join(attachment_links)
                    embed.add_field(name="🔗 ไฟล์แนบ", value=attachment_info, inline=False)
                
                await select_interaction.response.send_message(embed=embed, ephemeral=True)

        view = ViewSelect(self)
        await interaction.response.send_message("เลือกบันทึกที่จะดู:", view=view, ephemeral=True)

    @discord.ui.button(label="🗑️ ลบ", style=discord.ButtonStyle.red)
    async def delete_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ ไม่ใช่บันทึกของคุณ!", ephemeral=True)
            return

        if not self.notes:
            await interaction.response.send_message("❌ ไม่มีบันทึกที่ต้องลบ!", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=note['title'][:100],
                value=str(idx),
                emoji="🗑️"
            )
            for idx, note in enumerate(self.notes)
        ]

        class DeleteSelect(discord.ui.View):
            def __init__(self, parent):
                super().__init__(timeout=60)
                self.parent = parent

            @discord.ui.select(
                placeholder="เลือกบันทึกที่จะลบ...",
                options=options[:25]
            )
            async def select_delete(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                if select_interaction.user.id != self.parent.user_id:
                    await select_interaction.response.send_message("❌ ไม่ใช่บันทึกของคุณ!", ephemeral=True)
                    return

                idx = int(select.values[0])
                deleted_title = self.parent.notes[idx]['title']
                del self.parent.notes[idx]
                save_user_data(self.parent.user_id, self.parent.notes, notes=True)
                
                await select_interaction.response.send_message(
                    f"🗑️ ลบบันทึก **{deleted_title}** แล้ว!",
                    ephemeral=True
                )

        view = DeleteSelect(self)
        await interaction.response.send_message("เลือกบันทึกที่จะลบ:", view=view, ephemeral=True)


def generate_temp_code():
    """สร้างรหัสชั่วคราวแบบสุ่ม (a-z, A-Z, 0-9)"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(10))


def create_temp_note_code(user_id: int, duration_minutes: int = 5) -> str:
    """สร้างรหัสชั่วคราวสำหรับบันทึกของผู้ใช้"""
    code = generate_temp_code()
    TEMP_NOTE_CODES[user_id] = {
        "code": code,
        "expires_at": datetime.now() + timedelta(minutes=duration_minutes)
    }
    return code


def is_temp_code_valid(user_id: int, code: str) -> bool:
    """ตรวจสอบว่ารหัสชั่วคราวถูกต้องและไม่หมดอายุ"""
    code = code.strip().lower()
    
    if user_id not in TEMP_NOTE_CODES:
        return False
    
    stored = TEMP_NOTE_CODES[user_id]
    if stored["code"].lower() != code:
        return False
    
    if datetime.now() > stored["expires_at"]:
        del TEMP_NOTE_CODES[user_id]
        return False
    
    return True


def cleanup_expired_codes():
    """ลบรหัสชั่วคราวที่หมดอายุ"""
    expired_users = [
        user_id for user_id, data in TEMP_NOTE_CODES.items()
        if datetime.now() > data["expires_at"]
    ]
    for user_id in expired_users:
        del TEMP_NOTE_CODES[user_id]


class NoteActionView(discord.ui.View):
    """มุมมองสำหรับเลือกการดำเนินการกับบันทึก (สร้าง, ดู, ลบ)"""
    def __init__(self, user_id: int, context):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.context = context

    @discord.ui.button(label="📝 สร้างบันทึก", style=discord.ButtonStyle.green, emoji="✏️")
    async def create_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ คุณไม่สามารถโต้ตอบกับสิ่งนี้ได้!", ephemeral=True)
            return
        
        # มุมมองเลือกวิธีการสร้าง
        class CreateMethodView(discord.ui.View):
            def __init__(self, user_id, parent_cog):
                super().__init__(timeout=300)
                self.user_id = user_id
                self.parent_cog = parent_cog
            
            @discord.ui.button(label="ฟอร์ม GUI", style=discord.ButtonStyle.blurple, emoji="📋")
            async def gui_method(self, method_interaction: discord.Interaction, button: discord.ui.Button):
                if method_interaction.user.id != self.user_id:
                    await method_interaction.response.send_message("❌ ไม่ใช่การกระทำของคุณ!", ephemeral=True)
                    return
                
                await self._show_gui_method(method_interaction)
            
            @discord.ui.button(label="วิธีใช้คำสั่ง", style=discord.ButtonStyle.blurple, emoji="💬")
            async def command_method(self, method_interaction: discord.Interaction, button: discord.ui.Button):
                if method_interaction.user.id != self.user_id:
                    await method_interaction.response.send_message("❌ ไม่ใช่การกระทำของคุณ!", ephemeral=True)
                    return
                
                await self._show_command_method(method_interaction)
            
            async def _show_gui_method(self, method_interaction: discord.Interaction):
                """แสดงวิธีการใช้ฟอร์ม GUI"""
                # สร้าง modal สำหรับสร้างบันทึก
                class NoteModal(discord.ui.Modal, title="สร้างบันทึกใหม่"):
                    title_input = discord.ui.TextInput(
                        label="ชื่อบันทึก",
                        placeholder="ป้อนชื่อบันทึก...",
                        max_length=256,
                        required=True
                    )
                    content_input = discord.ui.TextInput(
                        label="เนื้อหาบันทึก",
                        placeholder="ป้อนเนื้อหาบันทึก...",
                        style=discord.TextStyle.long,
                        max_length=4000,
                        required=True
                    )

                    async def on_submit(self, modal_interaction: discord.Interaction):
                        user_id = modal_interaction.user.id
                        notes = load_user_data(user_id, notes=True)
                        
                        attachments = []
                        if hasattr(self, 'stored_attachments'):
                            attachments = self.stored_attachments
                        
                        note_item = {
                            "title": self.title_input.value,
                            "content": self.content_input.value,
                            "created_at": datetime.now().isoformat(),
                            "attachments": attachments
                        }
                        notes.append(note_item)
                        save_user_data(user_id, notes, notes=True)
                        
                        embed = discord.Embed(
                            title="📝 สร้างบันทึกแล้ว!",
                            description=f"**{self.title_input.value}**\n\n{self.content_input.value[:200]}...",
                            color=discord.Color.gold()
                        )
                        if attachments:
                            attachment_info = "\n".join([f"📎 {att['filename']}" for att in attachments])
                            embed.add_field(name="ไฟล์แนบ", value=attachment_info, inline=False)
                        
                        await modal_interaction.response.send_message(embed=embed, ephemeral=True)

                # ตรวจสอบว่าผู้ใช้มีไฟล์แนบล่าสุดหรือไม่
                class AttachmentView(discord.ui.View):
                    def __init__(self, user_id):
                        super().__init__(timeout=300)
                        self.user_id = user_id
                        self.attachments = []
                    
                    @discord.ui.button(label="ดำเนินการต่อ", style=discord.ButtonStyle.green)
                    async def continue_create(self, att_interaction: discord.Interaction, button: discord.ui.Button):
                        if att_interaction.user.id != self.user_id:
                            await att_interaction.response.send_message("❌ ไม่ใช่การกระทำของคุณ!", ephemeral=True)
                            return
                        
                        modal = NoteModal()
                        modal.stored_attachments = self.attachments
                        await att_interaction.response.send_modal(modal)
                
                view = AttachmentView(self.user_id)
                
                # ลองดึงไฟล์แนบจากข้อความล่าสุด
                try:
                    async for message in method_interaction.channel.history(limit=100):
                        if message.author.id == method_interaction.user.id and message.attachments:
                            view.attachments = [
                                {
                                    "filename": att.filename,
                                    "url": att.url,
                                    "size": att.size
                                }
                                for att in message.attachments
                            ]
                            break
                except:
                    pass
                
                attachment_text = ""
                if view.attachments:
                    attachment_text = "\n\n**📎 พบไฟล์แนบ:**\n" + "\n".join([f"• {att['filename']}" for att in view.attachments])
                
                embed = discord.Embed(
                    title="📋 วิธีฟอร์ม GUI",
                    description=f"กรอกฟอร์มเพื่อสร้างบันทึกของคุณ{attachment_text}",
                    color=discord.Color.gold()
                )
                await method_interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            async def _show_command_method(self, method_interaction: discord.Interaction):
                """แสดงวิธีการใช้คำสั่งพร้อมรหัสชั่วคราว"""
                # สร้างรหัสชั่วคราวสำหรับผู้ใช้
                temp_code = create_temp_note_code(method_interaction.user.id, duration_minutes=5)
                
                class CodeCopyView(discord.ui.View):
                    def __init__(self, code):
                        super().__init__(timeout=300)
                        self.code = code
                    
                    @discord.ui.button(label="📋 คัดลอกรหัส", style=discord.ButtonStyle.primary, emoji="📌")
                    async def copy_code(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        await button_interaction.response.send_message(
                            f"รหัสของคุณที่ต้องการคัดลอก:\n```\n{self.code}\n```",
                            ephemeral=True
                        )
                
                embed = discord.Embed(
                    title="💬 วิธีใช้รหัสชั่วคราว",
                    description=f"รหัสชั่วคราวของคุณพร้อมใช้งาน 5 นาที:\n\n**รหัส:** `{temp_code}`\n\n**รูปแบบคำสั่ง:**\n```\n/notecreate\ntempcode: {temp_code}\ntitle: ชื่อเรื่อง\ncontent: เนื้อหา\nattachment: [ไฟล์ของคุณ]\n```\n\n**ขั้นตอน:**\n1. กดปุ่มด้านล่างเพื่อคัดลอกรหัส\n2. ใช้คำสั่ง `/notecreate`\n3. วางรหัสของคุณในช่อง `tempcode`\n4. กรอกชื่อ เนื้อหา และแนบไฟล์\n5. เสร็จ! ✅",
                    color=discord.Color.gold()
                )
                embed.set_footer(text="⏱️ รหัสหมดอายุใน 5 นาที | หรือหลังจากใช้ครั้งแรก")
                
                await method_interaction.response.send_message(embed=embed, view=CodeCopyView(temp_code), ephemeral=True)
        
        method_view = CreateMethodView(interaction.user.id, self)
        embed = discord.Embed(
            title="📝 เลือกวิธีสร้าง",
            description="เลือกวิธีที่คุณต้องการสร้างบันทึก:",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=method_view, ephemeral=True)

    @discord.ui.button(label="📋 รายการบันทึก", style=discord.ButtonStyle.blurple, emoji="📚")
    async def list_notes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ คุณไม่สามารถโต้ตอบกับสิ่งนี้ได้!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        notes = load_user_data(interaction.user.id, notes=True)
        
        if not notes:
            embed = discord.Embed(
                title="📝 บันทึกของคุณ",
                description="✨ ยังไม่มีบันทึก! กดปุ่มสร้างบันทึกเพื่อสร้าง",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📝 บันทึกของคุณ",
            color=discord.Color.gold()
        )
        
        for idx, note in enumerate(notes, 1):
            attachment_count = len(note.get('attachments', []))
            attachment_str = f" 📎 ({attachment_count})" if attachment_count > 0 else ""
            
            content_preview = note['content'][:100] + "..." if len(note['content']) > 100 else note['content']
            
            if note.get('attachments') and attachment_count > 0:
                content_preview += f"\n\n**ไฟล์แนบ:** "
                attachment_links = []
                for att in note.get('attachments', []):
                    link = f"[{att['filename']}]({att['url']})"
                    attachment_links.append(link)
                content_preview += ", ".join(attachment_links)
            
            embed.add_field(
                name=f"{idx}. {note['title']}{attachment_str}",
                value=content_preview,
                inline=False
            )
        
        embed.set_footer(text=f"ทั้งหมด: {len(notes)} บันทึก | กด 'ดูบันทึก' เพื่อดูรายละเอียด")
        view = NotesView(self.user_id, notes, interaction)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🗑️ ลบบันทึก", style=discord.ButtonStyle.red, emoji="❌")
    async def delete_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ คุณไม่สามารถโต้ตอบกับสิ่งนี้ได้!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        notes = load_user_data(interaction.user.id, notes=True)
        
        if not notes:
            await interaction.followup.send("❌ ไม่มีบันทึกที่ต้องลบ!", ephemeral=True)
            return
        
        options = [
            discord.SelectOption(
                label=note['title'][:100],
                value=str(idx),
                emoji="🗑️"
            )
            for idx, note in enumerate(notes)
        ]

        class DeleteSelect(discord.ui.View):
            def __init__(self, parent):
                super().__init__(timeout=60)
                self.parent = parent

            @discord.ui.select(
                placeholder="เลือกบันทึกที่จะลบ...",
                options=options[:25]
            )
            async def select_delete(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                if select_interaction.user.id != self.parent.user_id:
                    await select_interaction.response.send_message("❌ ไม่ใช่บันทึกของคุณ!", ephemeral=True)
                    return

                idx = int(select.values[0])
                deleted_title = notes[idx]['title']
                del notes[idx]
                save_user_data(self.parent.user_id, notes, notes=True)
                
                await select_interaction.response.send_message(
                    f"🗑️ ลบบันทึก **{deleted_title}** แล้ว!",
                    ephemeral=True
                )

        view = DeleteSelect(self)
        await interaction.followup.send("เลือกบันทึกที่จะลบ:", view=view, ephemeral=True)


def ensure_data_dir():
    """ตรวจสอบให้แน่ใจว่าไดเรกทอรี data มีอยู่"""
    os.makedirs("data", exist_ok=True)


def load_user_data(user_id: int, notes: bool = False):
    """โหลดรายการสิ่งที่ต้องทำหรือบันทึกของผู้ใช้จากไฟล์ JSON"""
    ensure_data_dir()
    
    if not os.path.exists(DATA_FILE):
        return [] if not notes else []
    
    try:
        with open(DATA_FILE, 'r') as f:
            all_data = json.load(f)
        
        user_key = f"user_{user_id}"
        if user_key in all_data:
            return all_data[user_key].get("notes" if notes else "todos", [])
        return []
    except:
        return []


def save_user_data(user_id: int, data: list[dict], notes: bool = False) -> None:
    """บันทึกรายการสิ่งที่ต้องทำหรือบันทึกของผู้ใช้ไปยังไฟล์ JSON"""
    ensure_data_dir()
    
    all_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                all_data = json.load(f)
        except:
            all_data = {}
    
    user_key = f"user_{user_id}"
    if user_key not in all_data:
        all_data[user_key] = {"todos": [], "notes": []}
    
    if notes:
        all_data[user_key]["notes"] = data
    else:
        all_data[user_key]["todos"] = data
    
    with open(DATA_FILE, 'w') as f:
        json.dump(all_data, f, indent=2)


def create_todo_embed(todos: list[dict], user_id: int) -> discord.Embed:
    """สร้าง embed แสดงรายการสิ่งที่ต้องทำ"""
    embed = discord.Embed(
        title="📋 รายการสิ่งที่ต้องทำ",
        color=discord.Color.blue(),
        description="นี่คือรายการสิ่งที่ต้องทำของคุณ:"
    )
    
    if not todos:
        embed.description = "✨ ยังไม่มีรายการ! เพิ่มด้วย `/todo add`"
        return embed
    
    pending = [t for t in todos if not t.get('completed', False)]
    completed = [t for t in todos if t.get('completed', False)]
    
    if pending:
        pending_text = "\n".join([f"• {t['text']}" for t in pending])
        embed.add_field(name="📝 รอดำเนินการ", value=pending_text or "ไม่มี", inline=False)
    
    if completed:
        completed_text = "\n".join([f"✅ {t['text']}" for t in completed])
        embed.add_field(name="✅ เสร็จแล้ว", value=completed_text or "ไม่มี", inline=False)
    
    embed.set_footer(text=f"ทั้งหมด: {len(todos)} | เสร็จแล้ว: {len(completed)}")
    return embed


class WorkCog(commands.Cog):
    """คำสั่งรายการสิ่งที่ต้องทำและบันทึก + แก้ไข QWERTY->ไทย"""
    
    def __init__(self, bot):
        self.bot = bot
        self.cleanup_expired_codes.start()
        self.layout_config = load_thai_layout_config()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        await self.bot.process_commands(message)

        if not message.content or not message.content.strip():
            return

        guild_id = str(message.guild.id) if message.guild else 'dm'
        if not self.layout_config.get(guild_id, True):
            return

        if not is_likely_mistyped_thai(message.content):
            return

        corrected = convert_to_thai(message.content)
        if corrected == message.content:
            return

        if message.guild and message.channel.permissions_for(message.guild.me).manage_messages:
            try:
                await message.edit(content=corrected)
                await message.channel.send(f"✍️ {message.author.mention}, ปรับข้อความของคุณเป็นไทยเรียบร้อยแล้ว")
                return
            except Exception:
                pass

        await message.reply(f"🔁 ดูเหมือนคุณพิมพ์คีย์บอร์ดผิด ลองดูข้อความที่แก้ไขแล้ว:\n{corrected}", mention_author=False)

    @commands.command(name='thai_layout_toggle')
    @commands.has_permissions(administrator=True)
    async def thai_layout_toggle(self, ctx: commands.Context, enabled: bool):
        guild_id = str(ctx.guild.id) if ctx.guild else 'dm'
        self.layout_config[guild_id] = enabled
        save_thai_layout_config(self.layout_config)
        await ctx.send(f"✅ การแก้ไข QWERTY->ไทย ถูก{'เปิด' if enabled else 'ปิด'}ใช้งานแล้ว")

    @app_commands.command(name='thai_layout_toggle', description='เปิด/ปิดการแก้ไข QWERTY->ไทย')
    @app_commands.checks.has_permissions(administrator=True)
    async def thai_layout_toggle_slash(self, interaction: discord.Interaction, enabled: bool):
        guild_id = str(interaction.guild.id) if interaction.guild else 'dm'
        self.layout_config[guild_id] = enabled
        save_thai_layout_config(self.layout_config)
        await interaction.response.send_message(f"✅ การแก้ไข QWERTY->ไทย ถูก{'เปิด' if enabled else 'ปิด'}ใช้งานแล้ว", ephemeral=True)

    @commands.command(name='qwerty_to_thai')
    async def qwerty_to_thai_cmd(self, ctx: commands.Context, *, text: str):
        converted = convert_to_thai(text)
        await ctx.send(f"🔁 ข้อความที่แปลงแล้ว:\n{converted}")

    @app_commands.command(name='qtt', description='แปลงข้อความ QWERTY เป็นภาษาไทย')
    async def qwerty_to_thai_cmd_slash(self, interaction: discord.Interaction, text: str):
        converted = convert_to_thai(text)
        await interaction.response.send_message(f"🔁 ข้อความที่แปลงแล้ว:\n{converted}", ephemeral=True)

    @tasks.loop(minutes=1)
    async def cleanup_expired_codes(self):
        """ลบรหัสชั่วคราวที่หมดอายุเป็นระยะ"""
        cleanup_expired_codes()
    
    @cleanup_expired_codes.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()
    
    def cog_unload(self):
        """หยุดงานล้างข้อมูลเมื่อ cog ถูกยกเลิกโหลด"""
        self.cleanup_expired_codes.cancel()

    @app_commands.command(name="todo", description="จัดการรายการสิ่งที่ต้องทำ")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        action="การดำเนินการ: add, view, หรือ clear",
        text="ข้อความสำหรับรายการ (จำเป็นสำหรับ 'add')"
    )
    async def todo(
        self, 
        interaction: discord.Interaction, 
        action: str = "view",
        text: Optional[str] = None
    ):
        """จัดการรายการสิ่งที่ต้องทำด้วย /todo add|view|clear"""
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        todos = load_user_data(user_id, notes=False)
        
        if action.lower() == "add":
            if not text:
                await interaction.followup.send("❌ กรุณาระบุข้อความสำหรับรายการ!", ephemeral=True)
                return
            
            todo_item = {
                "text": text,
                "created_at": datetime.now().isoformat(),
                "completed": False
            }
            todos.append(todo_item)
            save_user_data(user_id, todos, notes=False)
            
            embed = discord.Embed(
                title="✅ เพิ่มรายการแล้ว!",
                description=f"เพิ่ม: **{text}**",
                color=discord.Color.green()
            )
            view = TodoListView(user_id, todos, interaction)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        elif action.lower() == "view":
            embed = create_todo_embed(todos, user_id)
            view = TodoListView(user_id, todos, interaction)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        elif action.lower() == "clear":
            todos.clear()
            save_user_data(user_id, todos, notes=False)
            await interaction.followup.send("🗑️ ลบรายการทั้งหมดแล้ว!", ephemeral=True)
        
        else:
            await interaction.followup.send(
                "❌ การดำเนินการไม่ถูกต้อง! ใช้: `add`, `view`, หรือ `clear`",
                ephemeral=True
            )

    @app_commands.command(name="note", description="สร้างและจัดการบันทึก")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def note(self, interaction: discord.Interaction):
        """จัดการบันทึกด้วยเมนูโต้ตอบ"""
        embed = discord.Embed(
            title="📝 ตัวจัดการบันทึก",
            description="เลือกสิ่งที่คุณต้องการทำกับบันทึกของคุณ:",
            color=discord.Color.gold()
        )
        embed.set_footer(text="กดปุ่มเพื่อเริ่มต้น")
        
        view = NoteActionView(interaction.user.id, interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="notecreate", description="สร้างบันทึกพร้อมไฟล์แนบ")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        tempcode="รหัสชั่วคราวของคุณ (จาก /note Create Note > Command Method)",
        title="ชื่อเรื่องสำหรับบันทึก",
        content="เนื้อหาสำหรับบันทึก",
        attachment="แนบไฟล์ (จำเป็น)"
    )
    async def notecreate(
        self,
        interaction: discord.Interaction,
        tempcode: str,
        title: str,
        content: str,
        attachment: discord.Attachment
    ):
        """สร้างบันทึกพร้อมไฟล์แนบโดยใช้รหัสชั่วคราว"""
        user_id = interaction.user.id
        
        # ดีบัก: ตรวจสอบว่ามีรหัสหรือไม่
        has_code = user_id in TEMP_NOTE_CODES
        
        # ตรวจสอบรหัสชั่วคราว
        if not is_temp_code_valid(user_id, tempcode):
            if not has_code:
                error_msg = "ไม่พบรหัสสำหรับบัญชีของคุณ สร้างได้ที่ `/note` → Create Note → Command Method"
            else:
                error_msg = "รหัสชั่วคราวของคุณไม่ถูกต้องหรือหมดอายุ\n\nสร้างใหม่ได้ที่ `/note` → Create Note → Command Method"
            
            embed = discord.Embed(
                title="❌ รหัสไม่ถูกต้องหรือหมดอายุ",
                description=error_msg,
                color=discord.Color.red()
            )
            embed.add_field(name="ข้อมูลดีบัก", value=f"รหัสที่ให้: `{tempcode.strip()}`\nรหัสมีอยู่: `{has_code}`", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # รหัสถูกต้อง สร้างบันทึก
        notes = load_user_data(user_id, notes=True)
        
        attachments = [
            {
                "filename": attachment.filename,
                "url": attachment.url,
                "size": attachment.size
            }
        ]
        
        note_item = {
            "title": title,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "attachments": attachments
        }
        notes.append(note_item)
        save_user_data(user_id, notes, notes=True)
        
        # ทำให้รหัสหมดอายุหลังการใช้งาน
        if user_id in TEMP_NOTE_CODES:
            del TEMP_NOTE_CODES[user_id]
        
        class CodeExpireView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)
            
            @discord.ui.button(label="🔓 รหัสหมดอายุแล้ว", style=discord.ButtonStyle.red, disabled=True)
            async def code_expired_btn(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                pass
        
        embed = discord.Embed(
            title="📝 สร้างบันทึกแล้ว!",
            description=f"**{title}**\n\n{content[:200]}...",
            color=discord.Color.gold()
        )
        if attachments:
            attachment_links = []
            for att in attachments:
                file_size = att.get('size', 0)
                size_str = f"{file_size / 1024 / 1024:.2f}MB" if file_size > 1024 * 1024 else f"{file_size / 1024:.2f}KB"
                link = f"[📎 {att['filename']}]({att['url']}) ({size_str})"
                attachment_links.append(link)
            
            attachment_info = "\n".join(attachment_links)
            embed.add_field(name="🔗 ไฟล์แนบ", value=attachment_info, inline=False)
        
        embed.set_footer(text="✅ รหัสถูกทำให้หมดอายุโดยอัตโนมัติหลังการใช้งาน")
        
        await interaction.response.send_message(embed=embed, view=CodeExpireView(), ephemeral=True)

    @app_commands.command(name="reminder", description="ตั้งการแจ้งเตือน")
    @app_commands.describe(
        text="สิ่งที่ต้องการแจ้งเตือน",
        importance="ระดับความสำคัญ: low, medium, หรือ high"
    )
    async def reminder(
        self,
        interaction: discord.Interaction,
        text: str,
        importance: Optional[str] = "medium"
    ):
        """สร้างการแจ้งเตือนด้วย /reminder"""
        await interaction.response.defer(ephemeral=True)
        
        importance = importance.lower() if importance else "medium"
        if importance not in ["low", "medium", "high"]:
            await interaction.followup.send(
                "❌ ระดับความสำคัญต้องเป็น: low, medium, หรือ high",
                ephemeral=True
            )
            return
        
        # การแจ้งเตือนถูกเก็บใน todos ด้วยเครื่องหมายพิเศษ
        user_id = interaction.user.id
        todos = load_user_data(user_id, notes=False)
        
        reminder_item = {
            "text": f"🔔 [{importance.upper()}] {text}",
            "created_at": datetime.now().isoformat(),
            "completed": False,
            "is_reminder": True,
            "importance": importance
        }
        todos.append(reminder_item)
        save_user_data(user_id, todos, notes=False)
        
        emoji_map = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        
        embed = discord.Embed(
            title=f"{emoji_map[importance]} ตั้งการแจ้งเตือนแล้ว!",
            description=f"**{text}**",
            color=discord.Color.red() if importance == "high" else (discord.Color.gold() if importance == "medium" else discord.Color.green())
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="notes", description="ทางลัดไปยังตัวจัดการบันทึก")
    async def notes(self, interaction: discord.Interaction):
        """เข้าถึงบันทึกอย่างรวดเร็ว - เหมือน /note"""
        embed = discord.Embed(
            title="📝 ตัวจัดการบันทึก",
            description="เลือกสิ่งที่คุณต้องการทำกับบันทึกของคุณ:",
            color=discord.Color.gold()
        )
        embed.set_footer(text="กดปุ่มเพื่อเริ่มต้น")
        
        view = NoteActionView(interaction.user.id, interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="todos", description="ทางลัดไปยังรายการสิ่งที่ต้องทำ")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def todos(self, interaction: discord.Interaction):
        """ดูรายการสิ่งที่ต้องทำอย่างรวดเร็ว - ทางลัดสำหรับ /todo view"""
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        todos = load_user_data(user_id, notes=False)
        
        embed = create_todo_embed(todos, user_id)
        view = TodoListView(user_id, todos, interaction)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="qwerty_to_thai", description="แปลงแป้นพิมพ์ QWERTY เป็นภาษาไทย")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(text="ข้อความที่พิมพ์ด้วย QWERTY ที่ควรจะถูกแปลงเป็นแป้นพิมพ์ไทย")
    async def qwerty_to_thai(self, interaction: discord.Interaction, text: str):
        """แปลงข้อความจากแป้นพิมพ์ QWERTY เป็นตัวอักษรไทยและส่งผลลัพธ์"""
        await interaction.response.defer(ephemeral=True)

        converted = qwerty_to_thai_text(text)

        embed = discord.Embed(
            title="🔤 QWERTY -> ไทย",
            description=f"อินพุต: {text}\nเอาต์พุต: {converted}",
            color=discord.Color.teal()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """โหลด WorkCog เข้าสู่บอท"""
    await bot.add_cog(WorkCog(bot))
