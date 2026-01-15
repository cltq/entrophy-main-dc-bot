import discord
from discord.ext import commands
import os
import io
import qrcode
from dotenv import load_dotenv

load_dotenv()

class PromptPayQRView(discord.ui.View):
    """View for PromptPay QR code interaction"""
    def __init__(self, user_id: int, promptpay_number: str, amount: float = None):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.promptpay_number = promptpay_number
        self.amount = amount

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the user who initiated the command to interact"""
        return interaction.user.id == self.user_id

    @discord.ui.button(label="Regenerate QR", style=discord.ButtonStyle.primary, emoji="🔄")
    async def regenerate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Regenerate the QR code"""
        qr_image = generate_promptpay_qr(self.promptpay_number, self.amount)
        await interaction.response.edit_message(attachments=[qr_image])

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the menu"""
        await interaction.response.defer()
        await interaction.delete_original_response()


class PromptPayNumberSelect(discord.ui.View):
    """Select view for choosing PromptPay number"""
    def __init__(self, numbers: dict, user_id: int, split: int = None, amount: float = None):
        super().__init__(timeout=300)
        self.numbers = numbers
        self.user_id = user_id
        self.split = split
        self.amount = amount
        self.response_sent = False

        # Create select dropdown
        options = [
            discord.SelectOption(
                label=f"Account {i + 1}: {num[:2]}****{num[-4:]}",
                description=f"PromptPay: {num}",
                value=num,
                emoji="💳"
            )
            for i, num in enumerate(numbers.keys())
        ]

        self.number_select.options = options

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the user who initiated the command to interact"""
        return interaction.user.id == self.user_id

    @discord.ui.select(placeholder="Select a PromptPay number...", min_values=1, max_values=1)
    async def number_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle PromptPay number selection"""
        selected_number = select.values[0]

        # Generate QR code
        qr_image = generate_promptpay_qr(selected_number, self.amount)

        # Create embed
        embed = discord.Embed(
            title="💳 PromptPay QR Code",
            color=discord.Color.green(),
            description="Scan this QR code to pay via PromptPay"
        )

        embed.add_field(name="PromptPay Number", value=f"`{selected_number[:2]}****{selected_number[-4:]}`", inline=True)

        if self.amount:
            embed.add_field(name="Amount", value=f"฿ {self.amount:,.2f}", inline=True)

        if self.split:
            embed.add_field(name="Split", value=f"{self.split} ways", inline=True)
            if self.amount:
                per_person = self.amount / self.split
                embed.add_field(name="Per Person", value=f"฿ {per_person:,.2f}", inline=True)

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


def generate_promptpay_qr(phone_or_id: str, amount: float = None) -> discord.File:
    """
    Generate a PromptPay QR code
    
    Args:
        phone_or_id: Phone number (10 digits) or ID (13 digits)
        amount: Optional amount in THB
    
    Returns:
        discord.File: QR code as PNG file
    """
    # Clean the input
    phone_or_id = phone_or_id.replace("-", "").replace(" ", "")

    # Determine type (0 for phone, 1 for ID)
    if len(phone_or_id) == 10:
        # Phone number format: 0XXXXXXXXX
        qr_type = "0"
    elif len(phone_or_id) == 13:
        # ID number format
        qr_type = "1"
    else:
        raise ValueError("PromptPay must be 10-digit phone number or 13-digit ID")

    # Build PromptPay string
    # Format: 00020126360014com.PromptPay0...
    # This is a simplified version - full EMV standards apply

    if amount:
        # Format: 00|0201|26|36|0014|com.PromptPay|00|{type}{data}|54|amount
        promptpay_data = f"00020126360014com.PromptPay00{qr_type}{phone_or_id}5403{int(amount)}"
    else:
        promptpay_data = f"00020126360014com.PromptPay00{qr_type}{phone_or_id}"

    # Generate QR code
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(promptpay_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to file
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return discord.File(buffer, filename="promptpay_qr.png")


class Payment(commands.Cog):
    """Payment commands for PromptPay QR code generation"""

    def __init__(self, bot):
        self.bot = bot
        # Load PromptPay numbers from environment
        self.promptpay_numbers = {}
        self._load_promptpay_numbers()

    def _load_promptpay_numbers(self):
        """Load PromptPay numbers from environment variables"""
        i = 1
        while True:
            env_key = f"PROMPTPAY_N{i}"
            number = os.getenv(env_key)
            if not number:
                break
            self.promptpay_numbers[number] = f"Account {i}"
            i += 1

    @discord.app_commands.command(
        name="promptpay",
        description="Generate a PromptPay QR code for payment"
    )
    @discord.app_commands.describe(
        number="Select account number (1, 2, 3...) - optional, shows selector if not provided",
        amount="Amount in THB (leave empty for no amount)",
        split="Number of ways to split the payment (leave empty for no split)",
        custom_amount="Override amount with custom value (optional)"
    )
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def promptpay(
        self,
        interaction: discord.Interaction,
        number: int = None,
        amount: float = None,
        split: int = None,
        custom_amount: float = None
    ):
        """Generate a PromptPay QR code with optional amount and split options"""

        # Check if PromptPay numbers are configured
        if not self.promptpay_numbers:
            embed = discord.Embed(
                title="❌ Configuration Error",
                description="No PromptPay numbers configured. Please add `PROMPTPAY_N1`, `PROMPTPAY_N2`, etc. to your `.env` file.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Use custom amount if provided
        final_amount = custom_amount or amount

        # Validate split
        if split and split < 2:
            embed = discord.Embed(
                title="❌ Invalid Split",
                description="Split must be at least 2",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # If number is specified, use that directly
        if number is not None:
            # Validate number range
            if number < 1 or number > len(self.promptpay_numbers):
                embed = discord.Embed(
                    title="❌ Invalid Account Number",
                    description=f"Please select a number between 1 and {len(self.promptpay_numbers)}",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Get the requested number
            selected_number = list(self.promptpay_numbers.keys())[number - 1]
            qr_image = generate_promptpay_qr(selected_number, final_amount)

            embed = discord.Embed(
                title="💳 PromptPay QR Code",
                color=discord.Color.green(),
                description="Scan this QR code to pay via PromptPay"
            )

            embed.add_field(name="PromptPay Number", value=f"`{selected_number[:2]}****{selected_number[-4:]}`", inline=True)
            embed.add_field(name="Account", value=f"#{number}", inline=True)

            if final_amount:
                embed.add_field(name="Amount", value=f"฿ {final_amount:,.2f}", inline=True)

            if split:
                embed.add_field(name="Split", value=f"{split} ways", inline=True)
                if final_amount:
                    per_person = final_amount / split
                    embed.add_field(name="Per Person", value=f"฿ {per_person:,.2f}", inline=True)

            embed.set_image(url="attachment://promptpay_qr.png")
            embed.set_footer(text="PromptPay Payment Request")

            await interaction.response.send_message(
                embed=embed,
                file=qr_image,
                view=PromptPayQRView(interaction.user.id, selected_number, final_amount),
                ephemeral=False
            )
        elif len(self.promptpay_numbers) == 1:
            # If only one PromptPay number and no number specified, generate directly
            selected_number = list(self.promptpay_numbers.keys())[0]
            qr_image = generate_promptpay_qr(selected_number, final_amount)

            embed = discord.Embed(
                title="💳 PromptPay QR Code",
                color=discord.Color.green(),
                description="Scan this QR code to pay via PromptPay"
            )

            embed.add_field(name="PromptPay Number", value=f"`{selected_number[:2]}****{selected_number[-4:]}`", inline=True)

            if final_amount:
                embed.add_field(name="Amount", value=f"฿ {final_amount:,.2f}", inline=True)

            if split:
                embed.add_field(name="Split", value=f"{split} ways", inline=True)
                if final_amount:
                    per_person = final_amount / split
                    embed.add_field(name="Per Person", value=f"฿ {per_person:,.2f}", inline=True)

            embed.set_image(url="attachment://promptpay_qr.png")
            embed.set_footer(text="PromptPay Payment Request")

            await interaction.response.send_message(
                embed=embed,
                file=qr_image,
                view=PromptPayQRView(interaction.user.id, selected_number, final_amount),
                ephemeral=False
            )
        else:
            # Show selector dialog if no number specified and multiple numbers available
            view = PromptPayNumberSelect(self.promptpay_numbers, interaction.user.id, split, final_amount)
            embed = discord.Embed(
                title="💳 PromptPay QR Code Generator",
                description="Select which PromptPay account to use",
                color=discord.Color.blue()
            )

            if final_amount:
                embed.add_field(name="Amount", value=f"฿ {final_amount:,.2f}", inline=True)

            if split:
                embed.add_field(name="Split", value=f"{split} ways", inline=True)
                if final_amount:
                    per_person = final_amount / split
                    embed.add_field(name="Per Person", value=f"฿ {per_person:,.2f}", inline=True)

            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True
            )


async def setup(bot):
    """Load the Payment cog"""
    await bot.add_cog(Payment(bot))
