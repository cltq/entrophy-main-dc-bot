import discord
from discord.ext import commands
import discord.app_commands
import os
import io
import re
import qrcode
from dotenv import load_dotenv

load_dotenv()

# ======================================================
# PromptPay EMV helpers (equivalent to promptpay-qr npm)
# ======================================================

def _crc16_xmodem(data: bytes) -> str:
    crc = 0x0000
    poly = 0x1021
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) & 0xFFFF) ^ poly
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"

def _tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"

def _normalize_promptpay_id(pid: str) -> str:
    digits = re.sub(r"\D", "", pid)
    if len(digits) == 10 and digits.startswith("0"):
        return "66" + digits[1:]  # Thai phone number
    return digits               # National ID or e-wallet

def _generate_promptpay_payload(pid: str, amount: float | None) -> str:
    pid = _normalize_promptpay_id(pid)

    payload = ""
    payload += _tlv("00", "01")                       # Payload Format
    payload += _tlv("01", "12" if amount else "11")   # Dynamic / Static

    merchant = ""
    merchant += _tlv("00", "A000000677010111")        # PromptPay AID
    merchant += _tlv("01", pid)                       # PromptPay ID
    payload += _tlv("29", merchant)

    payload += _tlv("53", "764")                      # THB

    if amount is not None:
        payload += _tlv("54", f"{amount:.2f}")

    payload += _tlv("58", "TH")                       # Country

    payload_crc = payload + "6304"
    payload += _tlv("63", _crc16_xmodem(payload_crc.encode()))

    return payload


def generate_promptpay_qr(phone_or_id: str, amount: float = None) -> discord.File:
    payload = _generate_promptpay_payload(phone_or_id, amount)

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return discord.File(buffer, filename="promptpay_qr.png")

# ======================================================
# Discord UI
# ======================================================

class PromptPayQRView(discord.ui.View):
    def __init__(self, user_id: int, promptpay_number: str, amount: float = None):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.promptpay_number = promptpay_number
        self.amount = amount

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(label="Regenerate QR", style=discord.ButtonStyle.primary, emoji="🔄")
    async def regenerate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        qr_image = generate_promptpay_qr(self.promptpay_number, self.amount)
        await interaction.response.edit_message(attachments=[qr_image])

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()


class PromptPayNumberSelect(discord.ui.View):
    def __init__(self, numbers: dict, user_id: int, split: int = None, amount: float = None):
        super().__init__(timeout=300)
        self.numbers = numbers
        self.user_id = user_id
        self.split = split
        self.amount = amount
        self.response_sent = False

        self.number_select.options = [
            discord.SelectOption(
                label=f"Account {i + 1}: {num[:2]}****{num[-4:]}",
                description=f"PromptPay: {num}",
                value=num,
                emoji="💳"
            )
            for i, num in enumerate(numbers.keys())
        ]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.select(placeholder="Select a PromptPay number...", min_values=1, max_values=1)
    async def number_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_number = select.values[0]
        qr_image = generate_promptpay_qr(selected_number, self.amount)

        embed = discord.Embed(
            title="💳 PromptPay QR Code",
            description="Scan this QR code to pay via PromptPay",
            color=discord.Color.green()
        )

        embed.add_field(
            name="PromptPay Number",
            value=f"`{selected_number[:2]}****{selected_number[-4:]}`",
            inline=True
        )

        if self.amount:
            embed.add_field(name="Amount", value=f"฿ {self.amount:,.2f}", inline=True)

        if self.split:
            embed.add_field(name="Split", value=f"{self.split} ways", inline=True)
            if self.amount:
                embed.add_field(
                    name="Per Person",
                    value=f"฿ {self.amount / self.split:,.2f}",
                    inline=True
                )

        embed.set_image(url="attachment://promptpay_qr.png")
        embed.set_footer(text="PromptPay Payment Request")

        if not self.response_sent:
            await interaction.response.send_message(
                embed=embed,
                file=qr_image,
                view=PromptPayQRView(interaction.user.id, selected_number, self.amount),
                ephemeral=False
            )
            self.response_sent = True
        else:
            await interaction.response.defer()

# ======================================================
# Cog
# ======================================================

class Payment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.promptpay_numbers = {}
        self._load_promptpay_numbers()

    def _load_promptpay_numbers(self):
        i = 1
        while True:
            num = os.getenv(f"PROMPTPAY_N{i}")
            if not num:
                break
            self.promptpay_numbers[num] = f"Account {i}"
            i += 1

    @discord.app_commands.command(
        name="promptpay",
        description="Generate a PromptPay QR code"
    )
    async def promptpay(
        self,
        interaction: discord.Interaction,
        number: int = None,
        amount: float = None,
        split: int = None
    ):
        if not self.promptpay_numbers:
            await interaction.response.send_message(
                "❌ No PromptPay numbers configured.",
                ephemeral=True
            )
            return

        if number:
            selected = list(self.promptpay_numbers.keys())[number - 1]
            qr_image = generate_promptpay_qr(selected, amount)

            embed = discord.Embed(
                title="💳 PromptPay QR Code",
                description="Scan to pay",
                color=discord.Color.green()
            )

            embed.set_image(url="attachment://promptpay_qr.png")

            await interaction.response.send_message(
                embed=embed,
                file=qr_image,
                view=PromptPayQRView(interaction.user.id, selected, amount)
            )
        else:
            view = PromptPayNumberSelect(self.promptpay_numbers, interaction.user.id, split, amount)
            await interaction.response.send_message(
                "Select PromptPay account:",
                view=view,
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Payment(bot))
