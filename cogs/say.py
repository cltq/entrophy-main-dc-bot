import discord
from discord import app_commands
from discord.ext import commands

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="say", description="Say something anywhere.")
    @app_commands.describe(message="The message the bot will send publicly.", channel_id="Optional channel ID to send the message to", amount="Number of times to send the message (default: 1)")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def say(self, interaction: discord.Interaction, message: str, channel_id: str = None, amount: int = 1):
        # Validate amount
        if amount < 1 or amount > 100:
            await interaction.response.send_message("Amount must be between 1 and 100.", ephemeral=True)
            return

        # If a target channel_id was provided, try to send there (validate first)
        if channel_id:
            try:
                target_id = int(channel_id)
            except Exception:
                await interaction.response.send_message("Invalid channel id provided.", ephemeral=True)
                return

            target = self.bot.get_channel(target_id)
            if target is None:
                try:
                    target = await self.bot.fetch_channel(target_id)
                except Exception:
                    target = None

            if target is None or not hasattr(target, 'send'):
                await interaction.response.send_message("Could not find a sendable channel with that ID.", ephemeral=True)
                return

            # Try to send to the target channel
            await interaction.response.send_message(f":white_check_mark: Message queued to target channel ({amount}x).", ephemeral=True)

            try:
                for _ in range(amount):
                    await target.send(message, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                try:
                    await interaction.followup.send("Failed to send to target channel (missing permissions?).", ephemeral=True)
                except Exception:
                    pass
            return

        # If the command is used in DM
        if isinstance(interaction.channel, discord.DMChannel):
            # Send normal (non-ephemeral) success message
            await interaction.response.send_message(":white_check_mark: Message sent Successfully.", ephemeral=True)
            # Then send the message in the DM as a follow-up (no mentions)
            try:
                for _ in range(amount):
                    await interaction.followup.send(message, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                # Fallback: try sending directly to the channel
                try:
                    for _ in range(amount):
                        await interaction.channel.send(message, allowed_mentions=discord.AllowedMentions.none())
                except Exception:
                    # If all fails, silently ignore to avoid crashing the cog load
                    pass
            return

        # If the command is in a guild (server)
        # Step 1: ephemeral response to user
        await interaction.response.send_message("Success!", ephemeral=True)

        # Step 2: send public message as a follow-up to the interaction (no mentions)
        try:
            for _ in range(amount):
                await interaction.followup.send(message, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            # Fallback to channel send if followup fails
            try:
                for _ in range(amount):
                    await interaction.channel.send(message, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                # Give the user an ephemeral error message if possible
                try:
                    await interaction.followup.send("Failed to post message (missing permissions?)", ephemeral=True)
                except Exception:
                    pass



async def setup(bot):
    await bot.add_cog(Say(bot))