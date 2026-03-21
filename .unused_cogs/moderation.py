import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal

class Moderation(commands.Cog):
    """Moderation commands for server management"""

    def __init__(self, bot):
        self.bot = bot
        self.user_warnings_data = {}

    async def moderation_check(interaction: discord.Interaction) -> bool:
        """Check if user has 'Moderation Access' role or is owner"""
        role = discord.utils.get(interaction.guild.roles, name="Moderation Access")
        if role and role in interaction.user.roles:
            return True
        if interaction.user.id == interaction.guild.owner_id:
            return True
        await interaction.response.send_message("❌ You need the 'Moderation Access' role to use this command.", ephemeral=True)
        return False

    async def send_log(self, interaction: discord.Interaction, action: str, target: discord.User, reason: str = None):
        """Send moderation action to log channel"""
        # Find a channel named 'mod-logs' or similar
        log_channel = discord.utils.get(interaction.guild.text_channels, name="mod-logs")
        if not log_channel:
            return

        embed = discord.Embed(
            title=f"🔨 {action}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Target", value=target.mention if hasattr(target, 'mention') else str(target), inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"ID: {target.id}")

        await log_channel.send(embed=embed)

    mod = app_commands.Group(
        name="mod",
        description="🔨 Moderation commands",
        allowed_contexts=app_commands.AppCommandContext(guild=True)
    )

    @mod.command(name="kick", description="Kick a member from the server")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="Member to kick", reason="Reason for kicking")
    async def mod_kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        """Kick a member from the server"""
        await interaction.response.defer(ephemeral=True)
        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="✅ Member Kicked",
                description=f"{member.mention} was kicked.",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Kick", member, reason)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to kick this member.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @mod.command(name="ban", description="Ban a member from the server")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="Member to ban", reason="Reason for banning")
    async def mod_ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        """Ban a member from the server"""
        await interaction.response.defer(ephemeral=True)
        try:
            await member.ban(reason=reason)
            embed = discord.Embed(
                title="✅ Member Banned",
                description=f"{member.mention} was banned.",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Ban", member, reason)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to ban this member.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @mod.command(name="unban", description="Unban a user by their ID")
    @app_commands.check(moderation_check)
    @app_commands.describe(user_id="User ID to unban")
    async def mod_unban(self, interaction: discord.Interaction, user_id: int):
        """Unban a user by their ID"""
        await interaction.response.defer(ephemeral=True)
        try:
            user = await self.bot.fetch_user(user_id)
            await interaction.guild.unban(user)
            embed = discord.Embed(
                title="✅ User Unbanned",
                description=f"{user} was unbanned.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Unban", user)
        except discord.NotFound:
            await interaction.followup.send("❌ User not found.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to unban.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @mod.command(name="mute", description="Mute a member in the server")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="Member to mute", reason="Reason for muting")
    async def mod_mute(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        """Mute a member in the server"""
        await interaction.response.defer(ephemeral=True)
        try:
            muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if not muted_role:
                muted_role = await interaction.guild.create_role(name="Muted")
                for channel in interaction.guild.channels:
                    await channel.set_permissions(
                        muted_role,
                        speak=False,
                        send_messages=False,
                        read_message_history=True
                    )

            await member.add_roles(muted_role, reason=reason)
            embed = discord.Embed(
                title="🔇 Member Muted",
                description=f"{member.mention} was muted.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Mute", member, reason)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to mute this member.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @mod.command(name="unmute", description="Unmute a member in the server")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="Member to unmute")
    async def mod_unmute(self, interaction: discord.Interaction, member: discord.Member):
        """Unmute a member in the server"""
        await interaction.response.defer(ephemeral=True)
        try:
            muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if muted_role and muted_role in member.roles:
                await member.remove_roles(muted_role)
                embed = discord.Embed(
                    title="🔊 Member Unmuted",
                    description=f"{member.mention} was unmuted.",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                await self.send_log(interaction, "Unmute", member)
            else:
                await interaction.followup.send("⚠️ That member is not muted.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to unmute this member.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @mod.command(name="softban", description="Softban a member (ban and immediately unban to delete messages)")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="Member to softban", reason="Reason for softbanning")
    async def mod_softban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        """Softban a member (ban and immediately unban to delete messages)"""
        await interaction.response.defer(ephemeral=True)
        try:
            await member.ban(reason=reason)
            await interaction.guild.unban(member)
            embed = discord.Embed(
                title="🧹 Member Softbanned",
                description=f"{member.mention} was softbanned (messages deleted).",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Softban", member, reason)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to softban this member.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @mod.command(name="warn", description="Warn a member")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="Member to warn", reason="Reason for warning")
    async def mod_warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        """Warn a member"""
        await interaction.response.defer(ephemeral=True)
        self.user_warnings_data.setdefault(member.id, []).append(reason)
        embed = discord.Embed(
            title="⚠️ Member Warned",
            description=f"{member.mention} has been warned.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warnings", value=str(len(self.user_warnings_data[member.id])), inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)
        await self.send_log(interaction, "Warn", member, reason)

    @mod.command(name="warnings", description="View warnings for a member")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="Member to check warnings for")
    async def mod_warnings(self, interaction: discord.Interaction, member: discord.Member):
        """View warnings for a member"""
        await interaction.response.defer(ephemeral=True)
        warns = self.user_warnings_data.get(member.id, [])
        if not warns:
            await interaction.followup.send(f"✅ {member.mention} has no warnings.", ephemeral=True)
        else:
            warning_list = "\n".join([f"{i+1}. {r}" for i, r in enumerate(warns)])
            embed = discord.Embed(
                title=f"⚠️ Warnings for {member}",
                description=warning_list,
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Total: {len(warns)} warning(s)")
            await interaction.followup.send(embed=embed, ephemeral=True)

    @mod.command(name="delwarn", description="Delete a specific warning by index")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="Member to delete warning from", index="Warning index to delete (starting from 1)")
    async def mod_delwarn(self, interaction: discord.Interaction, member: discord.Member, index: int):
        """Delete a specific warning by index"""
        await interaction.response.defer(ephemeral=True)
        warns = self.user_warnings_data.get(member.id, [])
        if 0 < index <= len(warns):
            removed = warns.pop(index - 1)
            embed = discord.Embed(
                title="🗑️ Warning Deleted",
                description=f"Removed warning from {member.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Warning", value=removed, inline=False)
            embed.add_field(name="Remaining Warnings", value=str(len(warns)), inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Delete Warning", member, removed)
        else:
            await interaction.followup.send("⚠️ Invalid warning index.", ephemeral=True)

    @mod.command(name="note", description="Add a moderator note for a member")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="Member to add note for", note="The note to add")
    async def mod_note(self, interaction: discord.Interaction, member: discord.Member, note: str):
        """Add a moderator note for a member"""
        await interaction.response.defer(ephemeral=True)
        self.user_warnings_data.setdefault(member.id, []).append(f"📋 Mod Note: {note}")
        embed = discord.Embed(
            title="📋 Note Added",
            description=f"Added note for {member.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Note", value=note, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
        await self.send_log(interaction, "Note Added", member, note)

    @mod.command(name="purge", description="Delete a number of messages in the current channel (max 100)")
    @app_commands.check(moderation_check)
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    async def mod_purge(self, interaction: discord.Interaction, amount: int):
        """Delete a number of messages in the current channel (max 100)"""
        await interaction.response.defer(ephemeral=True)
        if amount < 1:
            await interaction.followup.send("⚠️ You must specify a number greater than 0.", ephemeral=True)
            return
        if amount > 100:
            await interaction.followup.send("⚠️ You can only purge up to 100 messages at once.", ephemeral=True)
            return

        deleted = await interaction.channel.purge(limit=amount)
        embed = discord.Embed(
            title="🧹 Messages Purged",
            description=f"Deleted {len(deleted)} messages in {interaction.channel.mention}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

        try:
            await self.send_log(
                interaction,
                "Purge",
                interaction.user,
                f"{len(deleted)} messages deleted in {interaction.channel.mention}"
            )
        except Exception:
            pass

async def setup(bot):
    """Required function to load the cog"""
    await bot.add_cog(Moderation(bot))
