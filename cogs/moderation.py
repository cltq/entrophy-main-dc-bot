import discord
from discord.ext import commands
from typing import Optional

class Moderation(commands.Cog):
    """Moderation commands for server management"""

    def __init__(self, bot):
        self.bot = bot
        self.user_warnings_data = {}

    def has_moderation_access():
        """Custom check to verify if user has 'Moderation Access' role or is owner"""
        async def predicate(ctx):
            role = discord.utils.get(ctx.guild.roles, name="Moderation Access") 
            if role in ctx.author.roles:
                return True
            await ctx.send("❌ You need the 'Moderation Access' role to use this command.")
            return False
        return commands.check(predicate)

    async def send_log(self, ctx, action: str, target: discord.Member, reason: str = None):
        """Send moderation action to log channel"""
        # Find a channel named 'mod-logs' or similar
        log_channel = discord.utils.get(ctx.guild.text_channels, name="mod-logs")
        if not log_channel:
            return

        embed = discord.Embed(
            title=f"🔨 {action}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Target", value=target.mention, inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"ID: {target.id}")

        await log_channel.send(embed=embed)

    @commands.command()
    @has_moderation_access()
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member from the server"""
        await member.kick(reason=reason)
        await ctx.send(f"👢 {member.mention} was kicked. Reason: {reason}")
        await self.send_log(ctx, "Kick", member, reason)

    @commands.command()
    @has_moderation_access()
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a member from the server"""
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member.mention} was banned. Reason: {reason}")
        await self.send_log(ctx, "Ban", member, reason)

    @commands.command()
    @has_moderation_access()
    async def mute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Mute a member in the server"""
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(
                    muted_role,
                    speak=False,
                    send_messages=False,
                    read_message_history=True
                )

        await member.add_roles(muted_role, reason=reason)
        await ctx.send(f"🔇 {member.mention} was muted. Reason: {reason}")
        await self.send_log(ctx, "Mute", member, reason)

    @commands.command()
    @has_moderation_access()
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member in the server"""
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role in member.roles:
            await member.remove_roles(muted_role)
            await ctx.send(f"🔊 {member.mention} unmuted.")
            await self.send_log(ctx, "Unmute", member)
        else:
            await ctx.send("⚠️ That user is not muted.")

    @commands.command()
    @has_moderation_access()
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a member"""
        self.user_warnings_data.setdefault(member.id, []).append(reason)
        await ctx.send(f"⚠️ {member.mention} warned. Reason: {reason}")
        await self.send_log(ctx, "Warn", member, reason)

    @commands.command()
    @has_moderation_access()
    async def warnings(self, ctx, member: discord.Member):
        """View warnings for a member"""
        warns = self.user_warnings_data.get(member.id, [])
        if not warns:
            await ctx.send(f"{member.mention} has no warnings.")
        else:
            warning_list = "\n".join([f"{i+1}. {r}" for i, r in enumerate(warns)])
            await ctx.send(f"**Warnings for {member.mention}:**\n{warning_list}")

    @commands.command()
    @has_moderation_access()
    async def delwarn(self, ctx, member: discord.Member, index: int):
        """Delete a specific warning by index"""
        warns = self.user_warnings_data.get(member.id, [])
        if 0 < index <= len(warns):
            removed = warns.pop(index - 1)
            await ctx.send(f"🗑️ Removed: {removed}")
            await self.send_log(ctx, "Delete Warning", member, removed)
        else:
            await ctx.send("⚠️ Invalid index.")

    @commands.command()
    @has_moderation_access()
    async def reason(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Add a moderator note for a member"""
        self.user_warnings_data.setdefault(member.id, []).append(f"Mod Note: {reason}")
        await ctx.send(f"📋 Added note for {member.mention}.")
        await self.send_log(ctx, "Note Added", member, reason)

    @commands.command()
    @has_moderation_access()
    async def unban(self, ctx, user_id: int):
        """Unban a user by their ID"""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await ctx.send(f"✅ Unbanned {user}")
            await self.send_log(ctx, "Unban", user)
        except discord.NotFound:
            await ctx.send("⚠️ User not found.")
        except discord.HTTPException:
            await ctx.send("⚠️ Failed to unban user.")

    @commands.command()
    @has_moderation_access()
    async def softban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Softban a member (ban and immediately unban to delete messages)"""
        await member.ban(reason=reason)
        await ctx.guild.unban(member)
        await ctx.send(f"🧹 Softbanned {member.mention}. Reason: {reason}")
        await self.send_log(ctx, "Softban", member, reason)

    @commands.command()
    @has_moderation_access()
    async def purge(self, ctx, amount: int):
        """Delete a number of messages in the current channel (max 100)"""
        if amount < 1:
            await ctx.send("⚠️ You must specify a number greater than 0.")
            return
        if amount > 100:
            await ctx.send("⚠️ You can only purge up to 100 messages at once.")
            return

        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"🧹 Deleted {len(deleted) - 1} messages.", delete_after=5)

        try:
            await self.send_log(
                ctx,
                "Purge",
                ctx.author,
                f"{len(deleted) - 1} messages deleted in {ctx.channel.mention}"
            )
        except Exception:
            pass

async def setup(bot):
    """Required function to load the cog"""
    await bot.add_cog(Moderation(bot))
