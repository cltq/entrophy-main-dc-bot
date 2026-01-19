import discord
from discord.ext import commands
import discord.app_commands
import io, os, re, uuid, asyncio
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image
from datetime import datetime

# =========================
# ⚙️ CONFIGURATION
# =========================
LOGO_PATH = "promptpay_logo.png" 

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
            max_size = int(qr_width * 0.22)
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

def build_embed(user, pp, amount):
    masked = f"{pp[:3]}-xxx-{pp[-4:]}" if len(pp) >= 10 else pp
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    embed = discord.Embed(title="💳 PromptPay QR Payment", color=0x000000)
    embed.description = f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n**ผู้รับเงิน:** `{masked}`"
    embed.set_author(name=f"Requested by {user.display_name}", icon_url=user.display_avatar.url)
    amt_text = f"**฿ {amount:,.2f}**" if amount > 0 else "*- ระบุยอดเงินเอง -*"
    embed.add_field(name="💰 จำนวนเงิน", value=amt_text, inline=False)
    embed.set_image(url="attachment://qr.png")
    embed.set_footer(text=f"Ref: {uuid.uuid4().hex[:6].upper()} • วันที่สร้าง: {now}")
    return embed

# =========================
# 🕹️ VIEWS & FLOW
# =========================

class QRView(discord.ui.View):
    """ปุ่มสำหรับจัดการ QR Code ที่ส่งแบบ Public"""
    def __init__(self, user):
        super().__init__(timeout=600) # แสดงผลนาน 10 นาที
        self.user = user

    @discord.ui.button(label="ปิด (Close)", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def close(self, interaction: discord.Interaction, _):
        if interaction.user.id == self.user.id:
            # สำหรับข้อความ Public เราจะลบทิ้งทันทีโดยไม่ edit เพราะทุกคนเห็นข้อความอยู่
            await interaction.message.delete()
        else:
            await interaction.response.send_message("คุณไม่ใช่เจ้าของรายการนี้", ephemeral=True)

class AccountSelectView(discord.ui.View):
    def __init__(self, accounts, amount, user):
        super().__init__(timeout=60)
        self.accounts, self.amount, self.user = accounts, amount, user
        options = [discord.SelectOption(label=f"บัญชี: {a[:3]}-xxx-{a[-4:]}", value=a, emoji="🏦") for a in accounts]
        select = discord.ui.Select(placeholder="📌 เลือกบัญชีที่จะรับเงิน...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id: return
        file, _ = create_qr_with_logo(interaction.data['values'][0], self.amount)
        embed = build_embed(self.user, interaction.data['values'][0], self.amount)
        
        # ลบข้อความ Ephemeral เดิมทิ้งก่อน แล้วส่งอันใหม่แบบ Public
        await interaction.response.edit_message(content="✅ สร้าง QR เรียบร้อยแล้ว!", view=None, embed=None)
        await interaction.channel.send(embed=embed, file=file, view=QRView(self.user))
        # ลบ ephemeral message หลังจากผ่านไป 2 วิ
        await asyncio.sleep(2)
        await interaction.delete_original_response()

class AmountModal(discord.ui.Modal, title="ระบุยอดเงิน"):
    amount_input = discord.ui.TextInput(label="จำนวนเงิน (บาท)", placeholder="เช่น 100", min_length=1)
    def __init__(self, accounts, user):
        super().__init__(); self.accounts, self.user = accounts, user
    async def on_submit(self, interaction: discord.Interaction):
        try: amt = float(self.amount_input.value.replace(",", ""))
        except: return await interaction.response.send_message("❌ กรอกตัวเลขเท่านั้น", ephemeral=True)
        
        if len(self.accounts) == 1:
            file, _ = create_qr_with_logo(self.accounts[0], amt)
            embed = build_embed(self.user, self.accounts[0], amt)
            await interaction.response.edit_message(content="✅ สร้าง QR เรียบร้อยแล้ว!", view=None, embed=None)
            await interaction.channel.send(embed=embed, file=file, view=QRView(self.user))
            await asyncio.sleep(2)
            await interaction.delete_original_response()
        else:
            await interaction.response.edit_message(content="🏦 **เลือกบัญชี:**", view=AccountSelectView(self.accounts, amt, self.user))

class MainChoiceView(discord.ui.View):
    def __init__(self, accounts, user):
        super().__init__(timeout=60); self.accounts, self.user = accounts, user
    @discord.ui.button(label="ระบุยอดเงิน", style=discord.ButtonStyle.success, emoji="💵")
    async def set_amt(self, interaction, _): await interaction.response.send_modal(AmountModal(self.accounts, self.user))
    @discord.ui.button(label="ไม่ระบุยอดเงิน", style=discord.ButtonStyle.primary, emoji="⏭️")
    async def no_amt(self, interaction, _):
        if len(self.accounts) == 1:
            file, _ = create_qr_with_logo(self.accounts[0], 0)
            embed = build_embed(self.user, self.accounts[0], 0)
            await interaction.response.edit_message(content="✅ สร้าง QR เรียบร้อยแล้ว!", view=None, embed=None)
            await interaction.channel.send(embed=embed, file=file, view=QRView(self.user))
            await asyncio.sleep(2)
            await interaction.delete_original_response()
        else:
            await interaction.response.edit_message(content="🏦 **เลือกบัญชี:**", view=AccountSelectView(self.accounts, 0, self.user))
    @discord.ui.button(label="ยกเลิก", style=discord.ButtonStyle.danger, emoji="✖️")
    async def cancel(self, interaction, _): await close_session(interaction)

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
    async def promptpay(self, interaction: discord.Interaction):
        if not self.accounts: return await interaction.response.send_message("❌ ไม่พบการตั้งค่าบัญชี", ephemeral=True)
        view = MainChoiceView(self.accounts, interaction.user)
        await interaction.response.send_message(content="💳 **PromptPay QR Wizard**", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PaymentWizard(bot))