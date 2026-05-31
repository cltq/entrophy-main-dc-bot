import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal

class Moderation(commands.Cog):
    """คำสั่งดูแลสำหรับจัดการเซิร์ฟเวอร์"""

    def __init__(self, bot):
        self.bot = bot
        self.user_warnings_data = {}

    async def moderation_check(interaction: discord.Interaction) -> bool:
        """ตรวจสอบว่าผู้ใช้มีบทบาท 'Moderation Access' หรือเป็นเจ้าของเซิร์ฟเวอร์"""
        role = discord.utils.get(interaction.guild.roles, name="Moderation Access")
        if role and role in interaction.user.roles:
            return True
        if interaction.user.id == interaction.guild.owner_id:
            return True
        await interaction.response.send_message("❌ คุณต้องมีบทบาท 'Moderation Access' เพื่อใช้คำสั่งนี้", ephemeral=True)
        return False

    async def send_log(self, interaction: discord.Interaction, action: str, target: discord.User, reason: str = None):
        """ส่งบันทึกการดำเนินการไปยังช่องบันทึก"""
        log_channel = discord.utils.get(interaction.guild.text_channels, name="mod-logs")
        if not log_channel:
            return

        embed = discord.Embed(
            title=f"🔨 {action}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="เป้าหมาย", value=target.mention if hasattr(target, 'mention') else str(target), inline=True)
        embed.add_field(name="ผู้ดูแล", value=interaction.user.mention, inline=True)
        if reason:
            embed.add_field(name="เหตุผล", value=reason, inline=False)
        embed.set_footer(text=f"ID: {target.id}")

        await log_channel.send(embed=embed)

    mod = app_commands.Group(
        name="mod",
        description="🔨 คำสั่งดูแล",
        allowed_contexts=app_commands.AppCommandContext(guild=True)
    )

    @mod.command(name="kick", description="เตะสมาชิกออกจากเซิร์ฟเวอร์")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="สมาชิกที่ต้องการเตะ", reason="เหตุผลในการเตะ")
    async def mod_kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่มีเหตุผล"):
        """เตะสมาชิกออกจากเซิร์ฟเวอร์"""
        await interaction.response.defer(ephemeral=True)
        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="✅ เตะสมาชิกแล้ว",
                description=f"{member.mention} ถูกเตะแล้ว",
                color=discord.Color.green()
            )
            embed.add_field(name="เหตุผล", value=reason, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Kick", member, reason)
        except discord.Forbidden:
            await interaction.followup.send("❌ ฉันไม่มีสิทธิ์เตะสมาชิกนี้", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @mod.command(name="ban", description="แบนสมาชิกออกจากเซิร์ฟเวอร์")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="สมาชิกที่ต้องการแบน", reason="เหตุผลในการแบน")
    async def mod_ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่มีเหตุผล"):
        """แบนสมาชิกออกจากเซิร์ฟเวอร์"""
        await interaction.response.defer(ephemeral=True)
        try:
            await member.ban(reason=reason)
            embed = discord.Embed(
                title="✅ สมาชิกถูกแบนแล้ว",
                description=f"{member.mention} ถูกแบนแล้ว",
                color=discord.Color.green()
            )
            embed.add_field(name="เหตุผล", value=reason, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Ban", member, reason)
        except discord.Forbidden:
            await interaction.followup.send("❌ ฉันไม่มีสิทธิ์แบนสมาชิกนี้", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @mod.command(name="unban", description="ยกเลิกการแบนผู้ใช้ด้วย ID")
    @app_commands.check(moderation_check)
    @app_commands.describe(user_id="รหัสผู้ใช้ที่ต้องการยกเลิกแบน")
    async def mod_unban(self, interaction: discord.Interaction, user_id: int):
        """ยกเลิกการแบนผู้ใช้ด้วย ID"""
        await interaction.response.defer(ephemeral=True)
        try:
            user = await self.bot.fetch_user(user_id)
            await interaction.guild.unban(user)
            embed = discord.Embed(
                title="✅ ยกเลิกการแบนแล้ว",
                description=f"{user} ถูกยกเลิกแบนแล้ว",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Unban", user)
        except discord.NotFound:
            await interaction.followup.send("❌ ไม่พบผู้ใช้", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ ฉันไม่มีสิทธิ์ยกเลิกการแบน", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @mod.command(name="mute", description="ปิดเสียงสมาชิกในเซิร์ฟเวอร์")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="สมาชิกที่ต้องการปิดเสียง", reason="เหตุผลในการปิดเสียง")
    async def mod_mute(self, interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่มีเหตุผล"):
        """ปิดเสียงสมาชิกในเซิร์ฟเวอร์"""
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
                title="🔇 ปิดเสียงสมาชิกแล้ว",
                description=f"{member.mention} ถูกปิดเสียงแล้ว",
                color=discord.Color.orange()
            )
            embed.add_field(name="เหตุผล", value=reason, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Mute", member, reason)
        except discord.Forbidden:
            await interaction.followup.send("❌ ฉันไม่มีสิทธิ์ปิดเสียงสมาชิกนี้", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @mod.command(name="unmute", description="เปิดเสียงสมาชิกในเซิร์ฟเวอร์")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="สมาชิกที่ต้องการเปิดเสียง")
    async def mod_unmute(self, interaction: discord.Interaction, member: discord.Member):
        """เปิดเสียงสมาชิกในเซิร์ฟเวอร์"""
        await interaction.response.defer(ephemeral=True)
        try:
            muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if muted_role and muted_role in member.roles:
                await member.remove_roles(muted_role)
                embed = discord.Embed(
                    title="🔊 เปิดเสียงสมาชิกแล้ว",
                    description=f"{member.mention} ถูกเปิดเสียงแล้ว",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                await self.send_log(interaction, "Unmute", member)
            else:
                await interaction.followup.send("⚠️ สมาชิกนั้นไม่ได้ถูกปิดเสียง", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ ฉันไม่มีสิทธิ์เปิดเสียงสมาชิกนี้", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @mod.command(name="softban", description="ซอฟต์แบนสมาชิก (แบนแล้วยกเลิกแบทันทีเพื่อลบข้อความ)")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="สมาชิกที่ต้องการซอฟต์แบน", reason="เหตุผลในการซอฟต์แบน")
    async def mod_softban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่มีเหตุผล"):
        """ซอฟต์แบนสมาชิก (แบนแล้วยกเลิกแบทันทีเพื่อลบข้อความ)"""
        await interaction.response.defer(ephemeral=True)
        try:
            await member.ban(reason=reason)
            await interaction.guild.unban(member)
            embed = discord.Embed(
                title="🧹 ซอฟต์แบนสมาชิกแล้ว",
                description=f"{member.mention} ถูกซอฟต์แบนแล้ว (ลบข้อความแล้ว)",
                color=discord.Color.green()
            )
            embed.add_field(name="เหตุผล", value=reason, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Softban", member, reason)
        except discord.Forbidden:
            await interaction.followup.send("❌ ฉันไม่มีสิทธิ์ซอฟต์แบนสมาชิกนี้", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @mod.command(name="warn", description="เตือนสมาชิก")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="สมาชิกที่ต้องการเตือน", reason="เหตุผลในการเตือน")
    async def mod_warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่มีเหตุผล"):
        """เตือนสมาชิก"""
        await interaction.response.defer(ephemeral=True)
        self.user_warnings_data.setdefault(member.id, []).append(reason)
        embed = discord.Embed(
            title="⚠️ สมาชิกถูกเตือนแล้ว",
            description=f"{member.mention} ถูกเตือนแล้ว",
            color=discord.Color.orange()
        )
        embed.add_field(name="เหตุผล", value=reason, inline=False)
        embed.add_field(name="คำเตือนทั้งหมด", value=str(len(self.user_warnings_data[member.id])), inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)
        await self.send_log(interaction, "Warn", member, reason)

    @mod.command(name="warnings", description="ดูคำเตือนของสมาชิก")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="สมาชิกที่ต้องการดูคำเตือน")
    async def mod_warnings(self, interaction: discord.Interaction, member: discord.Member):
        """ดูคำเตือนของสมาชิก"""
        await interaction.response.defer(ephemeral=True)
        warns = self.user_warnings_data.get(member.id, [])
        if not warns:
            await interaction.followup.send(f"✅ {member.mention} ไม่มีคำเตือน", ephemeral=True)
        else:
            warning_list = "\n".join([f"{i+1}. {r}" for i, r in enumerate(warns)])
            embed = discord.Embed(
                title=f"⚠️ คำเตือนของ {member}",
                description=warning_list,
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"ทั้งหมด: {len(warns)} คำเตือน")
            await interaction.followup.send(embed=embed, ephemeral=True)

    @mod.command(name="delwarn", description="ลบคำเตือนตามลำดับที่")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="สมาชิกที่ต้องการลบคำเตือน", index="ลำดับคำเตือนที่จะลบ (เริ่มต้นที่ 1)")
    async def mod_delwarn(self, interaction: discord.Interaction, member: discord.Member, index: int):
        """ลบคำเตือนตามลำดับที่"""
        await interaction.response.defer(ephemeral=True)
        warns = self.user_warnings_data.get(member.id, [])
        if 0 < index <= len(warns):
            removed = warns.pop(index - 1)
            embed = discord.Embed(
                title="🗑️ ลบคำเตือนแล้ว",
                description=f"ลบคำเตือนจาก {member.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="คำเตือน", value=removed, inline=False)
            embed.add_field(name="คำเตือนที่เหลือ", value=str(len(warns)), inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_log(interaction, "Delete Warning", member, removed)
        else:
            await interaction.followup.send("⚠️ หมายเลขคำเตือนไม่ถูกต้อง", ephemeral=True)

    @mod.command(name="note", description="เพิ่มบันทึกผู้ดูแลสำหรับสมาชิก")
    @app_commands.check(moderation_check)
    @app_commands.describe(member="สมาชิกที่ต้องการเพิ่มบันทึก", note="ข้อความบันทึก")
    async def mod_note(self, interaction: discord.Interaction, member: discord.Member, note: str):
        """เพิ่มบันทึกผู้ดูแลสำหรับสมาชิก"""
        await interaction.response.defer(ephemeral=True)
        self.user_warnings_data.setdefault(member.id, []).append(f"📋 บันทึกผู้ดูแล: {note}")
        embed = discord.Embed(
            title="📋 เพิ่มบันทึกแล้ว",
            description=f"เพิ่มบันทึกสำหรับ {member.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(name="บันทึก", value=note, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
        await self.send_log(interaction, "Note Added", member, note)

    @mod.command(name="purge", description="ลบข้อความจำนวนหนึ่งในช่องปัจจุบัน (สูงสุด 100)")
    @app_commands.check(moderation_check)
    @app_commands.describe(amount="จำนวนข้อความที่จะลบ (1-100)")
    async def mod_purge(self, interaction: discord.Interaction, amount: int):
        """ลบข้อความจำนวนหนึ่งในช่องปัจจุบัน (สูงสุด 100)"""
        await interaction.response.defer(ephemeral=True)
        if amount < 1:
            await interaction.followup.send("⚠️ คุณต้องระบุจำนวนที่มากกว่า 0", ephemeral=True)
            return
        if amount > 100:
            await interaction.followup.send("⚠️ คุณสามารถลบได้สูงสุด 100 ข้อความในครั้งเดียว", ephemeral=True)
            return

        deleted = await interaction.channel.purge(limit=amount)
        embed = discord.Embed(
            title="🧹 ลบข้อความแล้ว",
            description=f"ลบ {len(deleted)} ข้อความใน {interaction.channel.mention}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

        try:
            await self.send_log(
                interaction,
                "Purge",
                interaction.user,
                f"ลบ {len(deleted)} ข้อความใน {interaction.channel.mention}"
            )
        except Exception:
            pass

async def setup(bot):
    """ฟังก์ชันที่จำเป็นสำหรับโหลด cog"""
    await bot.add_cog(Moderation(bot))
