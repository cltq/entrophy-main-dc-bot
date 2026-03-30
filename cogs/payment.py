import asyncio
import io
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Optional

import discord
from discord import app_commands
from discord.ext import commands
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image

LOGO_PATH: str = "promptpay_logo.png" 

# =========================
# 🛠️ PROMPTPAY & IMAGE LOGIC
# =========================

def crc16(data: bytes):
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"

def tlv(tag, value):
    return f"{tag}{len(value):02d}{value}"

def generate_payload(pp_number, amount=0.0):
    target = re.sub(r"\D", "", str(pp_number))
    if len(target) == 10 and target.startswith("0"):
        target_type = "MOBILE"
        target = "0066" + target[1:]
    elif len(target) == 13:
        target_type = "TAXID"
    else:
        raise ValueError("Invalid PromptPay ID")

    p_method = "12" if amount > 0 else "11"
    payload = [tlv("00", "01"), tlv("01", p_method)]
    merchant_data = [tlv("00", "A000000677010111")]
    merchant_data.append(tlv("01", target) if target_type == "MOBILE" else tlv("02", target))
    payload.append(tlv("29", "".join(merchant_data)))
    payload.append(tlv("53", "764"))
    payload.append(tlv("58", "TH"))
    if amount > 0:
        payload.append(tlv("54", f"{amount:.2f}"))
    raw_payload = "".join(payload) + "6304"
    raw_payload += crc16(raw_payload.encode())
    return raw_payload

def create_qr_with_logo(pp_number, amount):
    try:
        data = generate_payload(pp_number, amount)
    except: return None, None

    qr = qrcode.QRCode(version=1, error_correction=ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGBA')
    qr_width, _ = qr_img.size

    if os.path.exists(LOGO_PATH):
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            max_size = int(qr_width * 0.12)
            logo.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            offset = ((qr_width - logo.size[0]) // 2, (qr_width - logo.size[1]) // 2)
            qr_img.paste(logo, offset, logo)
        except: pass

    final_img = qr_img.convert("RGB")
    buf = io.BytesIO()
    final_img.save(buf, "PNG")
    buf.seek(0)
    return discord.File(buf, "qr.png"), data

async def close_session(interaction):
    try:
        await interaction.response.edit_message(content="⌛ **ยกเลิกรายการ**", embed=None, view=None, attachments=[])
        await asyncio.sleep(2)
        await interaction.delete_original_response()
    except: pass

async def send_qr_log(bot, embed, file=None):
    """ส่ง embed ไปยัง logging channel"""
    try:
        guild = bot.get_guild(int(os.getenv("GUILD_ID")))
        if guild:
            channel = guild.get_channel(1461331433560739862)
            if channel:
                await channel.send(embed=embed, file=file)
    except Exception as e:
        print(f"Error sending QR log: {e}")

# =========================
# 💾 PAYMENT TRACKING & LOGGING
# =========================

PAYMENT_LOG_FILE = "payment_history.json"
PAYMENT_STATUS = {
    "PENDING": "⏳ รอตรวจสอบ",
    "PAID": "✅ ชำระแล้ว",
    "REFUSED": "❌ ปฏิเสธ",
    "CLOSED": "🔒 ปิดแล้ว"
}

def load_payment_history():
    """โหลดประวัติการชำระเงิน"""
    if os.path.exists(PAYMENT_LOG_FILE):
        try:
            with open(PAYMENT_LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_payment_history(history):
    """บันทึกประวัติการชำระเงิน"""
    try:
        with open(PAYMENT_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving payment history: {e}")

def create_payment_record(ref_id, user_id, user_name, account, amount, payment_type="regular"):
    """สร้างบันทึกการชำระเงิน"""
    return {
        "ref_id": ref_id,
        "user_id": user_id,
        "user_name": user_name,
        "account": account,
        "amount": amount,
        "type": payment_type,
        "status": "PENDING",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status_history": [
            {
                "status": "PENDING",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action_by": "system"
            }
        ]
    }

def update_payment_status(ref_id, new_status, action_by):
    """อัปเดตสถานะการชำระเงิน"""
    history = load_payment_history()
    if ref_id in history:
        old_status = history[ref_id]["status"]
        history[ref_id]["status"] = new_status
        history[ref_id]["status_history"].append({
            "status": new_status,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action_by": action_by,
            "from": old_status
        })
        save_payment_history(history)
        return True
    return False

async def send_payment_log(bot, embed):
    """ส่ง log การชำระเงินไปยัง logging channel"""
    try:
        guild = bot.get_guild(int(os.getenv("GUILD_ID")))
        if guild:
            channel = guild.get_channel(1461331433560739862)
            if channel:
                await channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending payment log: {e}")

def build_embed(user, pp, amount, status="⏳ รอตรวจสอบ"):
    masked = f"{pp[:3]}-xxx-{pp[-4:]}" if len(pp) >= 10 else pp
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    embed = discord.Embed(title="💳 PromptPay QR Payment", color=0xCCCCFF)
    embed.description = f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n**ผู้รับเงิน:** `{masked}`"
    embed.set_author(name=f"Requested by {user.display_name}", icon_url=user.display_avatar.url)
    amt_text = f"**฿ {amount:,.2f}**" if amount > 0 else "*- ระบุยอดเงินเอง -*"
    embed.add_field(name="💰 จำนวนเงิน", value=amt_text, inline=False)
    embed.add_field(name="📊 สถานะ", value=status, inline=False)
    embed.set_image(url="attachment://qr.png")
    embed.set_footer(text=f"Ref: {uuid.uuid4().hex[:6].upper()} • วันที่สร้าง: {now}")
    return embed

# =========================
# 🕹️ VIEWS & FLOW
# =========================

class QRView(discord.ui.View):
    """ปุ่มสำหรับจัดการ QR Code ที่ส่งแบบ Public"""
    def __init__(self, user, ref_id, bot):
        super().__init__(timeout=600) # แสดงผลนาน 10 นาที
        self.user = user
        self.ref_id = ref_id
        self.bot = bot
        self.message = None

    @discord.ui.button(label="ชำระแล้ว", style=discord.ButtonStyle.success, emoji="✅")
    async def paid_button(self, interaction: discord.Interaction, _):
        if interaction.user.id == self.user.id:
            update_payment_status(self.ref_id, "PAID", interaction.user.name)
            
            # สร้าง embed สำหรับ log
            embed = discord.Embed(
                title="💰 อัปเดตสถานะการชำระเงิน",
                description=f"**Ref:** `{self.ref_id}`\n**สถานะใหม่:** ✅ ชำระแล้ว",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="ผู้อัปเดต", value=interaction.user.mention, inline=True)
            embed.add_field(name="เวลา", value=datetime.now().strftime("%d/%m/%Y %H:%M:%S"), inline=True)
            await send_payment_log(self.bot, embed)
            
            await interaction.response.send_message("✅ บันทึกสถานะเป็น **ชำระแล้ว** แล้ว", ephemeral=True)
        else:
            await interaction.response.send_message("❌ คุณไม่ใช่เจ้าของรายการนี้", ephemeral=True)

    @discord.ui.button(label="ปฏิเสธ", style=discord.ButtonStyle.danger, emoji="❌")
    async def refuse_button(self, interaction: discord.Interaction, _):
        if interaction.user.id == self.user.id:
            update_payment_status(self.ref_id, "REFUSED", interaction.user.name)
            
            embed = discord.Embed(
                title="💰 อัปเดตสถานะการชำระเงิน",
                description=f"**Ref:** `{self.ref_id}`\n**สถานะใหม่:** ❌ ปฏิเสธ",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="ผู้อัปเดต", value=interaction.user.mention, inline=True)
            embed.add_field(name="เวลา", value=datetime.now().strftime("%d/%m/%Y %H:%M:%S"), inline=True)
            await send_payment_log(self.bot, embed)
            
            await interaction.response.send_message("✅ บันทึกสถานะเป็น **ปฏิเสธ** แล้ว", ephemeral=True)
        else:
            await interaction.response.send_message("❌ คุณไม่ใช่เจ้าของรายการนี้", ephemeral=True)

    @discord.ui.button(label="ปิด", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def close_button(self, interaction: discord.Interaction, _):
        if interaction.user.id == self.user.id:
            update_payment_status(self.ref_id, "CLOSED", interaction.user.name)
            
            embed = discord.Embed(
                title="💰 อัปเดตสถานะการชำระเงิน",
                description=f"**Ref:** `{self.ref_id}`\n**สถานะใหม่:** 🔒 ปิดแล้ว",
                color=discord.Color.greyple(),
                timestamp=datetime.now()
            )
            embed.add_field(name="ผู้อัปเดต", value=interaction.user.mention, inline=True)
            embed.add_field(name="เวลา", value=datetime.now().strftime("%d/%m/%Y %H:%M:%S"), inline=True)
            await send_payment_log(self.bot, embed)
            
            await interaction.response.edit_message(content="🔒 **ปิดรายการแล้ว**", embed=None, view=None)
        else:
            await interaction.response.send_message("❌ คุณไม่ใช่เจ้าของรายการนี้", ephemeral=True)

class AccountSelectView(discord.ui.View):
    def __init__(self, accounts, amount, user, bot):
        super().__init__(timeout=60)
        self.accounts, self.amount, self.user = accounts, amount, user
        self.bot = bot
        options = [discord.SelectOption(label=f"บัญชี: {a[:3]}-xxx-{a[-4:]}", value=a, emoji="🏦") for a in accounts]
        select = discord.ui.Select(placeholder="📌 เลือกบัญชีที่จะรับเงิน...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id: return
        selected_account = interaction.data['values'][0]
        file, _ = create_qr_with_logo(selected_account, self.amount)
        embed = build_embed(self.user, selected_account, self.amount)
        
        # สร้าง ref_id และบันทึกการชำระเงิน
        ref_id = embed.footer.text.split(" • ")[0].replace("Ref: ", "")
        record = create_payment_record(ref_id, self.user.id, self.user.name, selected_account, self.amount, "regular")
        history = load_payment_history()
        history[ref_id] = record
        save_payment_history(history)
        
        # ส่ง log สำหรับการสร้างรายการใหม่
        log_embed = discord.Embed(
            title="💳 สร้างรายการชำระเงินใหม่",
            description=f"**Ref:** `{ref_id}`\n**ประเภท:** Regular Payment",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        log_embed.add_field(name="👤 ผู้ขอ", value=self.user.mention, inline=True)
        log_embed.add_field(name="💰 จำนวนเงิน", value=f"**฿ {self.amount:,.2f}**", inline=True)
        log_embed.add_field(name="🏦 บัญชี", value=f"`{selected_account[:3]}-xxx-{selected_account[-4:]}`", inline=True)
        await send_payment_log(self.bot, log_embed)
        
        # ลบข้อความ Ephemeral เดิมทิ้งก่อน แล้วส่งอันใหม่แบบ Public
        await interaction.response.edit_message(content="✅ สร้าง QR เรียบร้อยแล้ว!", view=None, embed=None)
        msg = await interaction.channel.send(embed=embed, file=file, view=QRView(self.user, ref_id, self.bot))
        # ส่งไปยัง logging channel
        await send_qr_log(self.bot, embed, file)
        # ลบ ephemeral message หลังจากผ่านไป 2 วิ
        await asyncio.sleep(2)
        await interaction.delete_original_response()

class AmountModal(discord.ui.Modal, title="ระบุยอดเงิน"):
    amount_input = discord.ui.TextInput(label="จำนวนเงิน (บาท)", placeholder="เช่น 100", min_length=1)
    def __init__(self, accounts, user, bot):
        super().__init__()
        self.accounts = accounts
        self.user = user
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        try: 
            amt = float(self.amount_input.value.replace(",", ""))
        except: 
            return await interaction.response.send_message("❌ กรอกตัวเลขเท่านั้น", ephemeral=True)
        
        if len(self.accounts) == 1:
            file, _ = create_qr_with_logo(self.accounts[0], amt)
            embed = build_embed(self.user, self.accounts[0], amt)
            
            # สร้าง ref_id และบันทึกการชำระเงิน
            ref_id = embed.footer.text.split(" • ")[0].replace("Ref: ", "")
            record = create_payment_record(ref_id, self.user.id, self.user.name, self.accounts[0], amt, "regular")
            history = load_payment_history()
            history[ref_id] = record
            save_payment_history(history)
            
            # ส่ง log
            log_embed = discord.Embed(
                title="💳 สร้างรายการชำระเงินใหม่",
                description=f"**Ref:** `{ref_id}`\n**ประเภท:** Regular Payment",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            log_embed.add_field(name="👤 ผู้ขอ", value=self.user.mention, inline=True)
            log_embed.add_field(name="💰 จำนวนเงิน", value=f"**฿ {amt:,.2f}**", inline=True)
            log_embed.add_field(name="🏦 บัญชี", value=f"`{self.accounts[0][:3]}-xxx-{self.accounts[0][-4:]}`", inline=True)
            await send_payment_log(self.bot, log_embed)
            
            await interaction.response.edit_message(content="✅ สร้าง QR เรียบร้อยแล้ว!", view=None, embed=None)
            await interaction.channel.send(embed=embed, file=file, view=QRView(self.user, ref_id, self.bot))
            # ส่งไปยัง logging channel
            await send_qr_log(self.bot, embed, file)
            await asyncio.sleep(2)
            await interaction.delete_original_response()
        else:
            await interaction.response.edit_message(content="🏦 **เลือกบัญชี:**", view=AccountSelectView(self.accounts, amt, self.user, self.bot))

class LendAccountSelectView(discord.ui.View):
    def __init__(self, accounts, base, pct, interest, total, user, bot):
        super().__init__(timeout=60)
        self.accounts = accounts
        self.base = base
        self.pct = pct
        self.interest = interest
        self.total = total
        self.user = user
        self.bot = bot
        options = [discord.SelectOption(label=f"บัญชี: {a[:3]}-xxx-{a[-4:]}", value=a, emoji="🏦") for a in accounts]
        select = discord.ui.Select(placeholder="📌 เลือกบัญชีที่จะรับเงิน...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id: return
        selected_account = interaction.data['values'][0]
        file, _ = create_qr_with_logo(selected_account, self.total)
        
        embed = discord.Embed(title="💰 รายละเอียดคืนเงิน (QR Payment Ready)", color=0xCCCCFF)
        masked = f"{selected_account[:3]}-xxx-{selected_account[-4:]}" if len(selected_account) >= 10 else selected_account
        embed.add_field(name="🏦 บัญชีที่รับเงิน", value=f"`{masked}`", inline=False)
        embed.add_field(name="📊 จำนวนเงินฐาน", value=f"**฿ {self.base:,.2f}**", inline=False)
        embed.add_field(name="📈 เปอร์เซ็นต์ดอกเบี้ย", value=f"**{self.pct:.2f}%**", inline=False)
        embed.add_field(name="💸 จำนวนดอกเบี้ย", value=f"**฿ {self.interest:,.2f}**", inline=False)
        embed.add_field(name="💵 จำนวนเงินทั้งหมด", value=f"**฿ {self.total:,.2f}**", inline=False)
        embed.add_field(name="📊 สถานะ", value="⏳ รอตรวจสอบ", inline=False)
        embed.set_author(name=f"ผู้ยืม: {self.user.display_name}", icon_url=self.user.display_avatar.url)
        embed.set_image(url="attachment://qr.png")
        ref_id = uuid.uuid4().hex[:6].upper()
        embed.set_footer(text=f"Ref: {ref_id} • วันที่สร้าง: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        # สร้างบันทึกการชำระเงิน (ประเภท loan/return)
        record = create_payment_record(ref_id, self.user.id, self.user.name, selected_account, self.total, "loan_return")
        history = load_payment_history()
        history[ref_id] = record
        save_payment_history(history)
        
        # ส่ง log
        log_embed = discord.Embed(
            title="💳 สร้างรายการคืนเงินใหม่",
            description=f"**Ref:** `{ref_id}`\n**ประเภท:** Loan Return",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        log_embed.add_field(name="👤 ผู้ยืม", value=self.user.mention, inline=True)
        log_embed.add_field(name="💰 เงินต้น", value=f"**฿ {self.base:,.2f}**", inline=True)
        log_embed.add_field(name="📊 ดอกเบี้ย", value=f"**{self.pct:.2f}%**", inline=True)
        log_embed.add_field(name="💵 รวม", value=f"**฿ {self.total:,.2f}**", inline=True)
        log_embed.add_field(name="🏦 บัญชี", value=f"`{selected_account[:3]}-xxx-{selected_account[-4:]}`", inline=True)
        await send_payment_log(self.bot, log_embed)
        
        await interaction.response.send_message(embed=embed, file=file, ephemeral=False, view=QRView(self.user, ref_id, self.bot))
        # ส่งไปยัง logging channel
        await send_qr_log(self.bot, embed, file)
        # Remove the selector message after sending QR
        await asyncio.sleep(0.5)
        await interaction.message.delete()

class LendMoneyModal(discord.ui.Modal, title="รายละเอียดคืนเงิน"):
    base_amount = discord.ui.TextInput(label="จำนวนเงินฐาน (บาท)", placeholder="เช่น 1000", min_length=1)
    percentage = discord.ui.TextInput(label="เปอร์เซ็นต์ดอกเบี้ย (%)", placeholder="เช่น 5", min_length=1)
    def __init__(self, accounts, user, bot):
        super().__init__()
        self.accounts = accounts
        self.user = user
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            base = float(self.base_amount.value.replace(",", ""))
            pct = float(self.percentage.value.replace(",", ""))
        except:
            return await interaction.response.send_message("❌ กรอกตัวเลขเท่านั้น", ephemeral=True)
        
        if base <= 0 or pct < 0:
            return await interaction.response.send_message("❌ จำนวนเงินและเปอร์เซ็นต์ต้องมากกว่า 0", ephemeral=True)
        
        interest = (base * pct) / 100
        total = base + interest
        
        if len(self.accounts) == 1:
            file, _ = create_qr_with_logo(self.accounts[0], total)
            embed = discord.Embed(title="💰 รายละเอียดคืนเงิน (QR Payment Ready)", color=0xCCCCFF)
            masked = f"{self.accounts[0][:3]}-xxx-{self.accounts[0][-4:]}" if len(self.accounts[0]) >= 10 else self.accounts[0]
            embed.add_field(name="🏦 บัญชีที่รับเงิน", value=f"`{masked}`", inline=False)
            embed.add_field(name="📊 จำนวนเงินฐาน", value=f"**฿ {base:,.2f}**", inline=False)
            embed.add_field(name="📈 เปอร์เซ็นต์ดอกเบี้ย", value=f"**{pct:.2f}%**", inline=False)
            embed.add_field(name="💸 จำนวนดอกเบี้ย", value=f"**฿ {interest:,.2f}**", inline=False)
            embed.add_field(name="💵 จำนวนเงินทั้งหมด", value=f"**฿ {total:,.2f}**", inline=False)
            embed.add_field(name="📊 สถานะ", value="⏳ รอตรวจสอบ", inline=False)
            embed.set_author(name=f"ผู้ยืม: {self.user.display_name}", icon_url=self.user.display_avatar.url)
            embed.set_image(url="attachment://qr.png")
            ref_id = uuid.uuid4().hex[:6].upper()
            embed.set_footer(text=f"Ref: {ref_id} • วันที่สร้าง: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            
            # สร้างบันทึกการชำระเงิน
            record = create_payment_record(ref_id, self.user.id, self.user.name, self.accounts[0], total, "loan_return")
            history = load_payment_history()
            history[ref_id] = record
            save_payment_history(history)
            
            # ส่ง log
            log_embed = discord.Embed(
                title="💳 สร้างรายการคืนเงินใหม่",
                description=f"**Ref:** `{ref_id}`\n**ประเภท:** Loan Return",
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )
            log_embed.add_field(name="👤 ผู้ยืม", value=self.user.mention, inline=True)
            log_embed.add_field(name="💰 เงินต้น", value=f"**฿ {base:,.2f}**", inline=True)
            log_embed.add_field(name="📊 ดอกเบี้ย", value=f"**{pct:.2f}%**", inline=True)
            log_embed.add_field(name="💵 รวม", value=f"**฿ {total:,.2f}**", inline=True)
            log_embed.add_field(name="🏦 บัญชี", value=f"`{self.accounts[0][:3]}-xxx-{self.accounts[0][-4:]}`", inline=True)
            await send_payment_log(self.bot, log_embed)
            
            await interaction.response.send_message(embed=embed, file=file, ephemeral=False, view=QRView(self.user, ref_id, self.bot))
            # ส่งไปยัง logging channel
            await send_qr_log(self.bot, embed, file)
        else:
            embed = discord.Embed(title="💰 รายละเอียดคืนเงิน", color=0xCCCCFF)
            embed.add_field(name="📊 จำนวนเงินฐาน", value=f"**฿ {base:,.2f}**", inline=False)
            embed.add_field(name="📈 เปอร์เซ็นต์ดอกเบี้ย", value=f"**{pct:.2f}%**", inline=False)
            embed.add_field(name="💸 จำนวนดอกเบี้ย", value=f"**฿ {interest:,.2f}**", inline=False)
            embed.add_field(name="💵 จำนวนเงินทั้งหมด", value=f"**฿ {total:,.2f}**", inline=False)
            embed.set_footer(text="เลือกบัญชีด้านล่าง:")
            await interaction.response.send_message(embed=embed, view=LendAccountSelectView(self.accounts, base, pct, interest, total, self.user, self.bot), ephemeral=True)

class MainChoiceView(discord.ui.View):
    def __init__(self, accounts, user, bot):
        super().__init__(timeout=60)
        self.accounts = accounts
        self.user = user
        self.bot = bot
    
    @discord.ui.button(label="ระบุยอดเงิน", style=discord.ButtonStyle.success, emoji="💵")
    async def set_amt(self, interaction, _):
        await interaction.response.send_modal(AmountModal(self.accounts, self.user, self.bot))
    
    @discord.ui.button(label="ไม่ระบุยอดเงิน", style=discord.ButtonStyle.primary, emoji="⏭️")
    async def no_amt(self, interaction, _):
        if len(self.accounts) == 1:
            file, _ = create_qr_with_logo(self.accounts[0], 0)
            embed = build_embed(self.user, self.accounts[0], 0)
            
            # สร้าง ref_id และบันทึกการชำระเงิน
            ref_id = embed.footer.text.split(" • ")[0].replace("Ref: ", "")
            record = create_payment_record(ref_id, self.user.id, self.user.name, self.accounts[0], 0, "regular")
            history = load_payment_history()
            history[ref_id] = record
            save_payment_history(history)
            
            # ส่ง log
            log_embed = discord.Embed(
                title="💳 สร้างรายการชำระเงินใหม่",
                description=f"**Ref:** `{ref_id}`\n**ประเภท:** Regular Payment (No Amount)",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            log_embed.add_field(name="👤 ผู้ขอ", value=self.user.mention, inline=True)
            log_embed.add_field(name="💰 จำนวนเงิน", value="**ไม่ระบุ**", inline=True)
            log_embed.add_field(name="🏦 บัญชี", value=f"`{self.accounts[0][:3]}-xxx-{self.accounts[0][-4:]}`", inline=True)
            await send_payment_log(self.bot, log_embed)
            
            await interaction.response.edit_message(content="✅ สร้าง QR เรียบร้อยแล้ว!", view=None, embed=None)
            await interaction.channel.send(embed=embed, file=file, view=QRView(self.user, ref_id, self.bot))
            # ส่งไปยัง logging channel
            await send_qr_log(self.bot, embed, file)
            await asyncio.sleep(2)
            await interaction.delete_original_response()
        else:
            await interaction.response.edit_message(content="🏦 **เลือกบัญชี:**", view=AccountSelectView(self.accounts, 0, self.user, self.bot))
    
    @discord.ui.button(label="เก็บคืนเงิน", style=discord.ButtonStyle.primary, emoji="📊")
    async def collect_lend(self, interaction, _):
        await interaction.response.send_modal(LendMoneyModal(self.accounts, self.user, self.bot))
    
    @discord.ui.button(label="ยกเลิก", style=discord.ButtonStyle.danger, emoji="✖️")
    async def cancel(self, interaction, _):
        await close_session(interaction)

# =========================
# ⚙️ COG SETUP
# =========================

class PaymentWizard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.accounts = []
        i = 1
        while os.getenv(f"PROMPTPAY_N{i}"):
            self.accounts.append(os.getenv(f"PROMPTPAY_N{i}")); i += 1
        if not self.accounts and os.getenv("PROMPTPAY"): self.accounts.append(os.getenv("PROMPTPAY"))

    @discord.app_commands.command(name="pp", description="สร้าง QR Code (ส่งแบบสาธารณะในขั้นตอนสุดท้าย)")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def promptpay(self, interaction: discord.Interaction):
        if not self.accounts: return await interaction.response.send_message("❌ ไม่พบการตั้งค่าบัญชี", ephemeral=True)
        view = MainChoiceView(self.accounts, interaction.user, self.bot)
        await interaction.response.send_message(content="💳 **PromptPay QR Wizard**", view=view, ephemeral=True)

    @commands.command(name="pp", description="สร้าง QR Code (ส่งแบบสาธารณะในขั้นตอนสุดท้าย)")
    async def promptpay_prefix(self, ctx: commands.Context):
        """Prefix command version of /pp"""
        if not self.accounts: return await ctx.send("❌ ไม่พบการตั้งค่าบัญชี")
        view = MainChoiceView(self.accounts, ctx.author, self.bot)
        await ctx.send(content="💳 **PromptPay QR Wizard**", view=view)

async def setup(bot):
    await bot.add_cog(PaymentWizard(bot))