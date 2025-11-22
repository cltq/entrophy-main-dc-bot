import discord
from discord import app_commands
from discord.ext import commands

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="say", description="Say something anywhere.")
    @app_commands.describe(message="The message the bot will send publicly.")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def say(self, interaction: discord.Interaction, message: str):

        # If the command is used in DM
        if isinstance(interaction.channel, discord.DMChannel):
            # Send normal (non-ephemeral) success message
            await interaction.response.send_message(":white_check_mark: Message sent Successfully.", ephemeral=True)
            # Then send the message in the DM as a follow-up (no mentions)
            try:
                await interaction.followup.send(message, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                # Fallback: try sending directly to the channel
                try:
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
            await interaction.followup.send(message, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            # Fallback to channel send if followup fails
            try:
                await interaction.channel.send(message, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                # Give the user an ephemeral error message if possible
                try:
                    await interaction.followup.send("Failed to post message (missing permissions?)", ephemeral=True)
                except Exception:
                    pass



async def setup(bot):
    await bot.add_cog(Say(bot))