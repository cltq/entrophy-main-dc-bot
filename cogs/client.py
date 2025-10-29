import discord
from discord import app_commands
from discord.ext import commands

class ClientCog(commands.Cog):
    """Handles the /say command for bot owner only"""

    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 969088519161139270  # Replace with your Discord user ID

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the cog is ready"""
        print(f'ClientCog loaded - /say command ready')
        print(f'Only user ID {self.owner_id} can use this bot')

    async def is_owner(self, interaction: discord.Interaction) -> bool:
        """Check if the user is the bot owner"""
        return interaction.user.id == self.owner_id

    @app_commands.command(name="say", description="Make the bot send a message (Owner only)")
    @app_commands.describe(message="The message to send")
    async def say(self, interaction: discord.Interaction, message: str):
        """
        Send a message through the bot
        Only the bot owner can use this command
        """
        # Check if user is the owner
        if not await self.is_owner(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return

        # Check if we're in a guild channel
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )
            return

        # Check if bot has permission to send messages
        if not interaction.channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(
                "❌ I don't have permission to send messages in this channel.",
                ephemeral=True
            )
            return

        try:
            # Send the message
            await interaction.channel.send(message)

            # Confirm to the owner (only they can see this)
            await interaction.response.send_message(
                f"✅ Message sent successfully!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to send messages here.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error sending message: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    """Required function to load the cog"""
    await bot.add_cog(ClientCog(bot))
    print('ClientCog setup complete')
