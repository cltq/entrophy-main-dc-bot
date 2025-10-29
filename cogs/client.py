import discord
from discord import app_commands
from discord.ext import commands

class SendAnywhere(commands.Cog):
    """Cog that lets users make the bot send messages anywhere."""

    def __init__(self, bot):
        self.bot = bot

    # Define the /send command
    @app_commands.command(
        name="send",
        description="Send a message in the current channel or DM a user."
    )
    @app_commands.describe(
        target_user="(Optional) The user to DM (leave empty to send in this channel)",
        message="The message content to send."
    )
    async def send(
        self,
        interaction: discord.Interaction,
        message: str,
        target_user: discord.User | None = None
    ):
        """Send message to current channel or as DM"""
        await interaction.response.defer(ephemeral=True)

        # If a user is provided → send a DM
        if target_user:
            try:
                await target_user.send(message)
                await interaction.followup.send(f"✅ Message sent to {target_user.display_name} via DM.")
            except discord.Forbidden:
                await interaction.followup.send(f"❌ I don't have permission to DM {target_user.display_name}. They might have DMs disabled or blocked the bot.")
        else:
            # Otherwise, send in the current channel
            try:
                await interaction.channel.send(message)
                await interaction.followup.send("✅ Message sent in this channel.")
            except discord.Forbidden:
                await interaction.followup.send("❌ I don't have permission to send messages in this channel.")

async def setup(bot: commands.Bot):
    await bot.add_cog(SendAnywhere(bot))
