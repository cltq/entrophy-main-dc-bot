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

        # Send the message to the current channel
        try:
            await interaction.channel.send(message)
            await interaction.response.send_message(
                "✅ Message sent successfully!",
                ephemeral=False
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

    @app_commands.command(name="scc", description="Send a message through the bot to a specific channel")
    @app_commands.describe(
        message="The message to send (use \\n for new lines)",
        channel="The target channel (mention or ID)"
    )
    async def send_command_channel(
        self,
        interaction: discord.Interaction,
        message: str,
        channel: str
    ):
        """
        Allows authorized users to send messages through the bot to any specified channel.
        Supports multiple lines by converting \\n to actual line breaks.

        Parameters:
        - message: The message content to send
        - channel: Target channel (mention like #channel or ID like 123456789)
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

        # Try to parse channel mention or ID
        channel_id = None

        # Check if it's a mention like <#123456789>
        if channel.startswith('<#') and channel.endswith('>'):
            channel_id = int(channel[2:-1])
        else:
            # Try to parse as raw ID
            try:
                channel_id = int(channel)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid channel format. Use a channel mention (#channel) or channel ID.",
                    ephemeral=True
                )
                return

        # Get the channel object
        target_channel = self.bot.get_channel(channel_id)

        if not target_channel:
            await interaction.response.send_message(
                f"❌ Could not find channel with ID: {channel_id}",
                ephemeral=True
            )
            return

        # Try to send the message
        try:
            await target_channel.send(message)
            await interaction.response.send_message(
                f"✅ Message sent successfully to {target_channel.mention}!",
                ephemeral=False
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ I don't have permission to send messages in {target_channel.mention}.\n"
                f"**Required permissions:** Send Messages\n"
                f"**Bot needs:** A role with 'Send Messages' permission in that channel.",
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"❌ Failed to send message: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An unexpected error occurred: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Client(bot))
