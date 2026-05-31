from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


class Say(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @discord.app_commands.command(name="say", description="พูดอะไรก็ได้ทุกที่")
    @app_commands.describe(message="ข้อความที่บอทจะส่งแบบสาธารณะ", channel_id="ID ช่องที่ต้องการส่งข้อความไป (ไม่จำเป็น)", amount="จำนวนครั้งที่จะส่งข้อความ (ค่าเริ่มต้น: 1)")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def say(self, interaction: discord.Interaction, message: str, channel_id: Optional[str] = None, amount: int = 1) -> None:
        # ตรวจสอบจำนวนครั้ง
        if amount < 1 or amount > 100:
            await interaction.response.send_message("จำนวนต้องอยู่ระหว่าง 1 ถึง 100", ephemeral=True)
            return

        # สร้างข้อความเต็มพร้อมผู้ส่ง
        full_message = f"<@{interaction.user.id}> --> {message}"

        # ถ้ามีการระบุ channel_id ให้ลองส่งไปที่ช่องนั้น
        if channel_id:
            try:
                target_id = int(channel_id)
            except Exception:
                await interaction.response.send_message("รหัสช่องไม่ถูกต้อง", ephemeral=True)
                return

            target = self.bot.get_channel(target_id)
            if target is None:
                try:
                    target = await self.bot.fetch_channel(target_id)
                except Exception:
                    target = None

            if target is None or not hasattr(target, 'send'):
                await interaction.response.send_message("ไม่พบช่องที่สามารถส่งข้อความได้ด้วยรหัสนี้", ephemeral=True)
                return

            await interaction.response.send_message(f"✅ ส่งข้อความไปยังช่องเป้าหมายแล้ว ({amount}x)", ephemeral=True)

            try:
                for _ in range(amount):
                    await target.send(full_message, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                try:
                    await interaction.followup.send("ไม่สามารถส่งไปยังช่องเป้าหมาย (ไม่มีสิทธิ์?)", ephemeral=True)
                except Exception:
                    pass
            return

        # ถ้าใช้คำสั่งใน DM
        if isinstance(interaction.channel, discord.DMChannel):
            await interaction.response.send_message("✅ ส่งข้อความสำเร็จ", ephemeral=True)
            try:
                for _ in range(amount):
                    await interaction.followup.send(full_message, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                try:
                    for _ in range(amount):
                        await interaction.channel.send(full_message, allowed_mentions=discord.AllowedMentions.none())
                except Exception:
                    pass
            return

        # ถ้าใช้คำสั่งในเซิร์ฟเวอร์
        await interaction.response.send_message("สำเร็จ!", ephemeral=True)

        try:
            for _ in range(amount):
                await interaction.followup.send(full_message, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            try:
                for _ in range(amount):
                    await interaction.channel.send(full_message, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                try:
                    await interaction.followup.send("ไม่สามารถโพสต์ข้อความ (ไม่มีสิทธิ์?)", ephemeral=True)
                except Exception:
                    pass

    @discord.app_commands.command(name="ys", description="สั่งให้บอทพูด")
    @app_commands.describe(message="ข้อความที่บอทจะส่งแบบสาธารณะ")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ys(self, interaction: discord.Interaction, message: str, channel_id: Optional[str] = None, amount: int = 1) -> None:

        # สร้างข้อความเต็ม
        full_message = f"{message}"

        # ถ้าใช้คำสั่งใน DM
        if isinstance(interaction.channel, discord.DMChannel):
            await interaction.response.send_message("✅ ส่งข้อความสำเร็จ", ephemeral=True)
            await interaction.followup.send(full_message)

        # ถ้าใช้คำสั่งในเซิร์ฟเวอร์

            await interaction.response.send_message("สำเร็จ!", ephemeral=True)
            await interaction.followup.send(full_message)


async def setup(bot):
    await bot.add_cog(Say(bot))
