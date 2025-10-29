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
    @app_commands.describe(message="The message to send")
    async def send_command(self, interaction: discord.Interaction, message: str):
        """
        Allows authorized users to send messages through the bot.

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

        # Send the message to the channel
        try:
            await interaction.channel.send(message)
            await interaction.response.send_message(
                "✅ Message sent successfully!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to send messages in this channel.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Client(bot))
