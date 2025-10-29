import discord
from discord import app_commands
from discord.ext import commands

class SendCog(commands.Cog):
    """Owner-only command to send messages anywhere (DMs or channels)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.owner_id = 969088519161139270  # Replace with your Discord user ID

    async def is_owner(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.owner_id

    @app_commands.command(name="send", description="Make the bot send a message anywhere (Owner only)")
    @app_commands.describe(
        message="The message to send",
        target_id="Channel ID or User ID (optional)"
    )
    async def send(self, interaction: discord.Interaction, message: str, target_id: str = None):
        """Send a message to any channel or DM"""
        # Check ownership
        if not await self.is_owner(interaction):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        target = None
        target_desc = "current channel"

        try:
            # Case 1️⃣: target ID provided
            if target_id:
                try:
                    target_id_int = int(target_id)
                except ValueError:
                    await interaction.followup.send("❌ Invalid target ID format. Must be numbers only.", ephemeral=True)
                    return

                # Try to fetch channel first
                target = self.bot.get_channel(target_id_int)
                if target:
                    target_desc = f"#{target.name}"
                else:
                    # Try fetching a user for DM
                    try:
                        user = await self.bot.fetch_user(target_id_int)
                        target = user
                        target_desc = f"DM to {user.name}"
                    except discord.NotFound:
                        await interaction.followup.send(f"❌ No user or channel found with ID `{target_id}`.", ephemeral=True)
                        return
                    except Exception as e:
                        await interaction.followup.send(f"❌ Error fetching user: {e}", ephemeral=True)
                        return

            # Case 2️⃣: No target → use current channel
            else:
                target = interaction.channel
                if interaction.guild:
                    target_desc = f"#{interaction.channel.name} in {interaction.guild.name}"
                else:
                    target_desc = "this DM"

            # Try to send message
            await target.send(message)
            await interaction.followup.send(f"✅ Message sent successfully to {target_desc}.", ephemeral=True)

        except discord.Forbidden as e:
            # Detect if DM blocked (Discord API code 50007)
            if hasattr(e, "code") and e.code == 50007:
                await interaction.followup.send(
                    "❌ Cannot send DM. The user likely has DMs disabled or doesn’t share a server with the bot.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"❌ I don't have permission to send messages to {target_desc}.",
                    ephemeral=True,
                )

        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Failed to send message: {e}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(SendCog(bot))
    print("✅ SendCog loaded - /send command ready")
