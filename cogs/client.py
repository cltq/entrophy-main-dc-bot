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
    @app_commands.describe(
        message="The message to send",
        channel_id="Channel ID where to send (optional - leave empty for current channel)",
        user_id="User ID to DM (optional - for sending DMs)"
    )
    async def say(
        self,
        interaction: discord.Interaction,
        message: str,
        channel_id: str = None,
        user_id: str = None
    ):
        """
        Send a message through the bot to any channel or DM
        Only the bot owner can use this command

        Examples:
        - /say message:Hello - Sends to current channel
        - /say message:Hello channel_id:123456789 - Sends to specific channel
        - /say message:Hello user_id:123456789 - Sends as DM to user
        """
        # Check if user is the owner
        if not await self.is_owner(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return

        # Defer response as fetching channels/users might take time
        await interaction.response.defer(ephemeral=True)

        try:
            target = None
            target_description = ""

            # Priority 1: Send to specific user (DM)
            if user_id:
                try:
                    user_id_int = int(user_id)
                    user = await self.bot.fetch_user(user_id_int)
                    target = user
                    target_description = f"DM to {user.name}"
                except ValueError:
                    await interaction.followup.send(
                        "❌ Invalid user ID format. Must be numbers only.",
                        ephemeral=True
                    )
                    return
                except discord.NotFound:
                    await interaction.followup.send(
                        f"❌ User with ID {user_id} not found.",
                        ephemeral=True
                    )
                    return
                except Exception as e:
                    await interaction.followup.send(
                        f"❌ Error fetching user: {str(e)}",
                        ephemeral=True
                    )
                    return

            # Priority 2: Send to specific channel
            elif channel_id:
                try:
                    channel_id_int = int(channel_id)
                    channel = self.bot.get_channel(channel_id_int)

                    # If channel not in cache, try fetching it
                    if not channel:
                        channel = await self.bot.fetch_channel(channel_id_int)

                    target = channel

                    if isinstance(channel, discord.TextChannel):
                        target_description = f"#{channel.name} in {channel.guild.name}"
                    elif isinstance(channel, discord.DMChannel):
                        target_description = f"DM with {channel.recipient.name}"
                    elif isinstance(channel, discord.GroupChannel):
                        target_description = f"Group: {channel.name}"
                    else:
                        target_description = f"Channel ID: {channel_id}"

                except ValueError:
                    await interaction.followup.send(
                        "❌ Invalid channel ID format. Must be numbers only.",
                        ephemeral=True
                    )
                    return
                except discord.NotFound:
                    await interaction.followup.send(
                        f"❌ Channel with ID {channel_id} not found or bot doesn't have access.",
                        ephemeral=True
                    )
                    return
                except discord.Forbidden:
                    await interaction.followup.send(
                        f"❌ Bot doesn't have permission to access channel {channel_id}.",
                        ephemeral=True
                    )
                    return
                except Exception as e:
                    await interaction.followup.send(
                        f"❌ Error fetching channel: {str(e)}",
                        ephemeral=True
                    )
                    return

            # Priority 3: Send to current channel
            else:
                if not interaction.channel:
                    await interaction.followup.send(
                        "❌ No channel context. Please specify channel_id or user_id.",
                        ephemeral=True
                    )
                    return
                target = interaction.channel

                if interaction.guild:
                    target_description = f"#{interaction.channel.name} in {interaction.guild.name}"
                else:
                    target_description = "this channel"

            # Send the message
            try:
                await target.send(message)

                # Confirm to the owner
                await interaction.followup.send(
                    f"✅ Message sent successfully to {target_description}!",
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    f"❌ I don't have permission to send messages to {target_description}.",
                    ephemeral=True
                )
            except discord.HTTPException as e:
                await interaction.followup.send(
                    f"❌ Failed to send message: {str(e)}",
                    ephemeral=True
                )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Unexpected error: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    """Required function to load the cog"""
    await bot.add_cog(ClientCog(bot))
    print('ClientCog setup complete')
