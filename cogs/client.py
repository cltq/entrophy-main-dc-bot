import discord
from discord import app_commands
from discord.ext import commands

class Client(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Add authorized user IDs here
        self.authorized_users = [
            969088519161139270
            # Add more user IDs as needed
        ]

    @app_commands.command(name="sc", description="Send a message through the bot")
    @app_commands.describe(message="The message to send (use \\n for new lines)")
    async def send_command(self, interaction: discord.Interaction, message: str):
        """
        Allows authorized users to send messages through the bot in the current channel.
        Supports multiple lines by converting \\n to actual line breaks.

        Parameters:
        - message: The message content to send
        """
        # Check if user is authorized
        if interaction.user.id not in self.authorized_users:
            await interaction.response.send_message(
                "❌ You are not authorized to use this command.",
                ephemeral=True
            )
            return

        # Convert \n to actual newlines for multi-line support
        message = message.replace('\\n', '\n')

        # Check bot's permissions in the current channel
        bot_permissions = interaction.channel.permissions_for(interaction.guild.me)

        if not bot_permissions.send_messages:
            # Bot doesn't have permission, provide helpful error
            await interaction.response.send_message(
                "❌ I don't have permission to send messages in this channel.\n\n"
                "**To fix this:**\n"
                "1. Go to Channel Settings → Permissions\n"
                "2. Add my role or add me specifically\n"
                "3. Enable 'Send Messages' permission\n\n"
                f"**Note:** Even though you have permission to send messages here, "
                f"I (the bot) need my own permission to send messages on your behalf.",
                ephemeral=True
            )
            return

        # Send the message to the current channel
        try:
            await interaction.channel.send(message)
            await interaction.response.send_message(
                "✅ Message sent successfully!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Failed to send message due to missing permissions.\n"
                "This shouldn't happen - please check my role permissions.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Client(bot))
