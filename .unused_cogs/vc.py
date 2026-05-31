"""
Voice Interface Cog
จัดการช่องเสียงด้วยฟีเจอร์ขั้นสูง เช่น การล็อก การซ่อน การอ้างสิทธิ์ และสิทธิ์การเข้าถึง
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
from typing import Optional

# ============================================
# VOICE CONTROL PANEL COG
# ============================================

class VoiceInterface(commands.Cog):
    """🎙️ Voice Interface - จัดการช่องเสียงด้วยฟีเจอร์ขั้นสูง"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "config/vc_config.json"
        self.temp_channels = {}  # ติดตามช่องชั่วคราว {guild_id: {channel_id: creation_time}}
        self.voice_settings = {}  # ติดตามการตั้งค่าเสียงตามกิลด์
        self.user_channel_count = {}  # ติดตามจำนวนช่องต่อผู้ใช้ {user_id: count}
        self.cleanup_task.start()
        self.load_config()

    def load_config(self):
        """โหลดการตั้งค่า Voice Control จาก JSON"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    self.voice_settings = json.load(f)
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการโหลด VC config: {e}")
            self.voice_settings = {}

    def save_config(self):
        """บันทึกการตั้งค่า Voice Control ไปยัง JSON"""
        try:
            os.makedirs("config", exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.voice_settings, f, indent=2)
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการบันทึก VC config: {e}")

    # -------- คำสั่ง VOICE INTERFACE --------
    voice_group = app_commands.Group(name="vc", description="🎙️ อินเทอร์เฟซเสียง")
    voice_group.allowed_contexts(guilds=True)

    # -------- สร้าง VC ชั่วคราว --------
    @voice_group.command(name="create", description="สร้างช่องเสียงชั่วคราว")
    @app_commands.describe(
        name="ชื่อช่องเสียง",
        limit="จำกัดผู้ใช้ (0 = ไม่จำกัด)",
        bitrate="อัตราบิตเสียงใน kbps (ค่าเริ่มต้น 64)"
    )
    async def create_temp_vc(
        self,
        interaction: discord.Interaction,
        name: str,
        limit: int = 0,
        bitrate: int = 64
    ):
        """สร้างช่องเสียงชั่วคราวที่ลบตัวเองเมื่อไม่มีคน"""
        await interaction.response.defer(ephemeral=True)

        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("❌ คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
                return

            # รับหมวดหมู่แม่ (ไม่บังคับ)
            parent_category = interaction.channel.category if hasattr(interaction.channel, 'category') else None

            # สร้างช่องเสียง
            voice_channel = await guild.create_voice_channel(
                name=name,
                user_limit=limit if limit > 0 else None,
                bitrate=min(bitrate * 1000, guild.bitrate_limit) if bitrate else 64000,
                category=parent_category
            )

            # ติดตามช่องชั่วคราว
            guild_id = str(guild.id)
            if guild_id not in self.temp_channels:
                self.temp_channels[guild_id] = {}

            self.temp_channels[guild_id][str(voice_channel.id)] = {
                "created_at": datetime.now().isoformat(),
                "creator": interaction.user.id,
                "temporary": True,
                "owner": interaction.user.id
            }

            embed = discord.Embed(
                title="✅ สร้างช่องเสียงชั่วคราวแล้ว",
                description=f"ช่อง: {voice_channel.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="ชื่อ", value=f"`{name}`", inline=True)
            embed.add_field(name="จำกัดผู้ใช้", value=f"{'ไม่จำกัด' if limit == 0 else limit}", inline=True)
            embed.add_field(name="อัตราบิต", value=f"{bitrate} kbps", inline=True)
            embed.set_footer(text="ช่องนี้จะถูกลบอัตโนมัติเมื่อไม่มีคน")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="❌ ไม่สามารถสร้างช่องได้",
                description=f"ข้อผิดพลาด: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ----------------
    class VoiceInterfaceView(discord.ui.View):
        """อินเทอร์เฟซเสียงแบบโต้ตอบพร้อมปุ่ม"""

        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="📊 รายการ", style=discord.ButtonStyle.blurple, custom_id="vc_list")
        async def list_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """แสดงรายการช่องเสียงทั้งหมด"""
            await interaction.response.defer(ephemeral=True)

            guild = interaction.guild
            voice_channels = [ch for ch in guild.channels if isinstance(ch, discord.VoiceChannel)]

            if not voice_channels:
                await interaction.followup.send("❌ ไม่พบช่องเสียง", ephemeral=True)
                return

            embed = discord.Embed(
                title="🎙️ ช่องเสียง",
                color=discord.Color.blue(),
                description=f"ทั้งหมด: {len(voice_channels)}"
            )

            for vc in sorted(voice_channels, key=lambda x: x.position):
                member_count = len(vc.members)
                user_limit = vc.user_limit if vc.user_limit else "∞"

                guild_id = str(guild.id)
                is_temp = guild_id in self.cog.temp_channels and str(vc.id) in self.cog.temp_channels[guild_id]
                temp_badge = "🌀" if is_temp else ""

                embed.add_field(
                    name=f"{temp_badge} {vc.name}",
                    value=f"สมาชิก: {member_count}/{user_limit}\nอัตราบิต: {vc.bitrate // 1000} kbps",
                    inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        @discord.ui.button(label="➕ สร้าง", style=discord.ButtonStyle.green, custom_id="vc_create_quick")
        async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """สร้าง VC ชั่วคราวด้วยชื่ออัตโนมัติ"""
            await interaction.response.defer(ephemeral=True)

            try:
                user_id = interaction.user.id
                guild = interaction.guild

                # นับครั้งถัดไปสำหรับผู้ใช้
                if user_id not in self.cog.user_channel_count:
                    self.cog.user_channel_count[user_id] = 1
                else:
                    self.cog.user_channel_count[user_id] += 1

                count = self.cog.user_channel_count[user_id]

                # สร้างชื่อช่อง: (ชื่อผู้ใช้)-(จำนวน)
                channel_name = f"{interaction.user.name}-{count}"

                # รับอัตราบิตสูงสุดของเซิร์ฟเวอร์
                max_bitrate = guild.bitrate_limit

                # รับหมวดหมู่แม่
                parent_category = interaction.channel.category if hasattr(interaction.channel, 'category') else None

                # สร้างช่องเสียง
                voice_channel = await guild.create_voice_channel(
                    name=channel_name,
                    user_limit=10,
                    bitrate=max_bitrate,
                    category=parent_category
                )

                # ติดตามช่องชั่วคราว
                guild_id = str(guild.id)
                if guild_id not in self.cog.temp_channels:
                    self.cog.temp_channels[guild_id] = {}

                self.cog.temp_channels[guild_id][str(voice_channel.id)] = {
                    "created_at": datetime.now().isoformat(),
                    "creator": user_id,
                    "temporary": True,
                    "owner": user_id
                }

                embed = discord.Embed(
                    title="✅ สร้างช่องแล้ว",
                    description=f"{voice_channel.mention}",
                    color=discord.Color.green()
                )
                embed.add_field(name="ชื่อ", value=f"`{channel_name}`", inline=True)
                embed.add_field(name="จำกัด", value="10", inline=True)
                embed.add_field(name="อัตราบิต", value=f"{max_bitrate // 1000} kbps", inline=True)
                embed.set_footer(text="ลบอัตโนมัติเมื่อไม่มีคน")

                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

        @discord.ui.button(label="🔒 ล็อก", style=discord.ButtonStyle.danger, custom_id="vc_lock")
        async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """ล็อกช่องเสียงปัจจุบัน"""
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.voice:
                await interaction.followup.send("❌ คุณต้องอยู่ในช่องเสียง", ephemeral=True)
                return

            target_channel = interaction.user.voice.channel
            guild_id = str(interaction.guild.id)
            channel_id = str(target_channel.id)

            is_owner = guild_id in self.cog.temp_channels and channel_id in self.cog.temp_channels[guild_id] and \
                      self.cog.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id

            if not is_owner and not interaction.user.guild_permissions.manage_channels:
                await interaction.followup.send("❌ คุณไม่ได้เป็นเจ้าของช่องนี้", ephemeral=True)
                return

            try:
                everyone_role = interaction.guild.default_role
                await target_channel.set_permissions(everyone_role, connect=False)
                embed = discord.Embed(title="🔒 ล็อกแล้ว", description=f"{target_channel.mention} ถูกล็อก", color=discord.Color.orange())
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

        @discord.ui.button(label="🔓 ปลดล็อก", style=discord.ButtonStyle.success, custom_id="vc_unlock")
        async def unlock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """ปลดล็อกช่องเสียงปัจจุบัน"""
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.voice:
                await interaction.followup.send("❌ คุณต้องอยู่ในช่องเสียง", ephemeral=True)
                return

            target_channel = interaction.user.voice.channel
            guild_id = str(interaction.guild.id)
            channel_id = str(target_channel.id)

            is_owner = guild_id in self.cog.temp_channels and channel_id in self.cog.temp_channels[guild_id] and \
                      self.cog.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id

            if not is_owner and not interaction.user.guild_permissions.manage_channels:
                await interaction.followup.send("❌ คุณไม่ได้เป็นเจ้าของช่องนี้", ephemeral=True)
                return

            try:
                everyone_role = interaction.guild.default_role
                await target_channel.set_permissions(everyone_role, connect=None)
                embed = discord.Embed(title="🔓 ปลดล็อกแล้ว", description=f"{target_channel.mention} ปลดล็อกแล้ว", color=discord.Color.green())
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

        @discord.ui.button(label="👁️ ซ่อน", style=discord.ButtonStyle.grey, custom_id="vc_hide")
        async def hide_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """ซ่อนช่องเสียงปัจจุบัน"""
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.voice:
                await interaction.followup.send("❌ คุณต้องอยู่ในช่องเสียง", ephemeral=True)
                return

            target_channel = interaction.user.voice.channel
            guild_id = str(interaction.guild.id)
            channel_id = str(target_channel.id)

            is_owner = guild_id in self.cog.temp_channels and channel_id in self.cog.temp_channels[guild_id] and \
                      self.cog.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id

            if not is_owner and not interaction.user.guild_permissions.manage_channels:
                await interaction.followup.send("❌ คุณไม่ได้เป็นเจ้าของช่องนี้", ephemeral=True)
                return

            try:
                everyone_role = interaction.guild.default_role
                await target_channel.set_permissions(everyone_role, view_channel=False)
                embed = discord.Embed(title="👁️ ซ่อนแล้ว", description=f"{target_channel.mention} ถูกซ่อน", color=discord.Color.purple())
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

        @discord.ui.button(label="🔍 แสดง", style=discord.ButtonStyle.grey, custom_id="vc_reveal")
        async def reveal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """แสดงช่องเสียงปัจจุบัน"""
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.voice:
                await interaction.followup.send("❌ คุณต้องอยู่ในช่องเสียง", ephemeral=True)
                return

            target_channel = interaction.user.voice.channel
            guild_id = str(interaction.guild.id)
            channel_id = str(target_channel.id)

            is_owner = guild_id in self.cog.temp_channels and channel_id in self.cog.temp_channels[guild_id] and \
                      self.cog.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id

            if not is_owner and not interaction.user.guild_permissions.manage_channels:
                await interaction.followup.send("❌ คุณไม่ได้เป็นเจ้าของช่องนี้", ephemeral=True)
                return

            try:
                everyone_role = interaction.guild.default_role
                await target_channel.set_permissions(everyone_role, view_channel=None)
                embed = discord.Embed(title="🔍 แสดงแล้ว", description=f"{target_channel.mention} มองเห็นได้", color=discord.Color.green())
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

        @discord.ui.button(label="👑 อ้างสิทธิ์", style=discord.ButtonStyle.blurple, custom_id="vc_claim")
        async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """อ้างสิทธิ์ความเป็นเจ้าของช่องเสียงปัจจุบัน"""
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.voice:
                await interaction.followup.send("❌ คุณต้องอยู่ในช่องเสียง", ephemeral=True)
                return

            target_channel = interaction.user.voice.channel
            guild_id = str(interaction.guild.id)
            channel_id = str(target_channel.id)

            if guild_id in self.cog.temp_channels and channel_id in self.cog.temp_channels[guild_id]:
                current_owner = self.cog.temp_channels[guild_id][channel_id].get("owner")
                if current_owner and current_owner != interaction.user.id:
                    await interaction.followup.send("❌ ช่องนี้มีเจ้าของแล้ว", ephemeral=True)
                    return

            if guild_id not in self.cog.temp_channels:
                self.cog.temp_channels[guild_id] = {}
            if channel_id not in self.cog.temp_channels[guild_id]:
                self.cog.temp_channels[guild_id][channel_id] = {}

            self.cog.temp_channels[guild_id][channel_id]["owner"] = interaction.user.id
            embed = discord.Embed(title="👑 อ้างสิทธิ์แล้ว", description=f"{interaction.user.mention} เป็นเจ้าของ {target_channel.mention}", color=discord.Color.gold())
            await interaction.followup.send(embed=embed, ephemeral=True)

        @discord.ui.button(label="🚪 Kick", style=discord.ButtonStyle.danger, custom_id="vc_kick_modal")
        async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """จัดการการเข้าถึงผู้ใช้"""
            await interaction.response.send_modal(self.cog.KickUserModal(self.cog))

        @discord.ui.button(label="ℹ️ ข้อมูล", style=discord.ButtonStyle.blurple, custom_id="vc_info")
        async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """ดูข้อมูลช่องเสียงปัจจุบัน"""
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.voice:
                await interaction.followup.send("❌ คุณต้องอยู่ในช่องเสียง", ephemeral=True)
                return

            target_channel = interaction.user.voice.channel
            guild_id = str(interaction.guild.id)
            channel_id = str(target_channel.id)

            embed = discord.Embed(title=f"ℹ️ {target_channel.name}", color=discord.Color.blue())
            embed.add_field(name="สมาชิก", value=f"{len(target_channel.members)}", inline=True)
            embed.add_field(name="จำกัด", value=f"{target_channel.user_limit if target_channel.user_limit else '∞'}", inline=True)
            embed.add_field(name="อัตราบิต", value=f"{target_channel.bitrate // 1000} kbps", inline=True)

            is_temp = guild_id in self.cog.temp_channels and channel_id in self.cog.temp_channels[guild_id]
            is_locked = target_channel.permissions_for(interaction.guild.default_role).connect is False
            is_hidden = target_channel.permissions_for(interaction.guild.default_role).view_channel is False

            embed.add_field(name="ชั่วคราว", value="🌀 ใช่" if is_temp else "❌ ไม่", inline=True)
            embed.add_field(name="ล็อก", value="🔒 ใช่" if is_locked else "🔓 ไม่", inline=True)
            embed.add_field(name="ซ่อน", value="👁️ ใช่" if is_hidden else "🔍 ไม่", inline=True)

            if is_temp and guild_id in self.cog.temp_channels and channel_id in self.cog.temp_channels[guild_id]:
                owner_id = self.cog.temp_channels[guild_id][channel_id].get("owner")
                if owner_id:
                    owner = interaction.guild.get_member(owner_id)
                    embed.add_field(name="เจ้าของ", value=owner.mention if owner else f"<@{owner_id}>", inline=True)

            members_str = ", ".join([m.mention for m in target_channel.members[:5]])
            if len(target_channel.members) > 5:
                members_str += f" +{len(target_channel.members) - 5}"
            if target_channel.members:
                embed.add_field(name="รายชื่อสมาชิก", value=members_str, inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        @discord.ui.button(label="✏️ เปลี่ยนชื่อ", style=discord.ButtonStyle.blurple, custom_id="vc_rename_modal")
        async def rename_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """เปลี่ยนชื่อช่องเสียงปัจจุบัน"""
            await interaction.response.send_modal(self.cog.RenameVCModal(self.cog))

        @discord.ui.button(label="⬆️ เพิ่ม", style=discord.ButtonStyle.green, custom_id="vc_increase_modal")
        async def increase_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """เพิ่มจำนวนผู้ใช้"""
            await interaction.response.send_modal(self.cog.IncreaseVCModal(self.cog))

        @discord.ui.button(label="⬇️ ลด", style=discord.ButtonStyle.red, custom_id="vc_decrease_modal")
        async def decrease_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """ลดจำนวนผู้ใช้"""
            await interaction.response.send_modal(self.cog.DecreaseVCModal(self.cog))

    # -------- ฟอร์ม MODAL --------
    class KickUserModal(discord.ui.Modal, title="จัดการการเข้าถึงผู้ใช้"):
        """Modal สำหรับจัดการการเข้าถึงผู้ใช้"""

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        user_id = discord.ui.TextInput(
            label="รหัสผู้ใช้",
            placeholder="วางรหัสผู้ใช้",
            max_length=25
        )

        action = discord.ui.TextInput(
            label="การดำเนินการ (allow/reject)",
            placeholder="allow หรือ reject",
            max_length=10
        )

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.voice:
                await interaction.followup.send("❌ คุณต้องอยู่ในช่องเสียง", ephemeral=True)
                return

            target_channel = interaction.user.voice.channel
            guild_id = str(interaction.guild.id)
            channel_id = str(target_channel.id)

            is_owner = guild_id in self.cog.temp_channels and channel_id in self.cog.temp_channels[guild_id] and \
                      self.cog.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id

            if not is_owner and not interaction.user.guild_permissions.manage_channels:
                await interaction.followup.send("❌ คุณไม่ได้เป็นเจ้าของช่องนี้", ephemeral=True)
                return

            try:
                user = interaction.guild.get_member(int(self.user_id.value))
                if not user:
                    await interaction.followup.send("❌ ไม่พบผู้ใช้", ephemeral=True)
                    return

                if self.action.value.lower() == "allow":
                    await target_channel.set_permissions(user, connect=True)
                    embed = discord.Embed(title="✅ อนุญาตแล้ว", description=f"{user.mention} สามารถเข้าร่วมได้", color=discord.Color.green())
                elif self.action.value.lower() == "reject":
                    await target_channel.set_permissions(user, connect=False)
                    if user.voice and user.voice.channel == target_channel:
                        await user.move_to(None)
                    embed = discord.Embed(title="🚫 ปฏิเสธแล้ว", description=f"{user.mention} ไม่สามารถเข้าร่วมได้", color=discord.Color.red())
                else:
                    await interaction.followup.send("❌ การดำเนินการไม่ถูกต้อง ใช้ 'allow' หรือ 'reject'", ephemeral=True)
                    return

                await interaction.followup.send(embed=embed, ephemeral=True)
            except ValueError:
                await interaction.followup.send("❌ รหัสผู้ใช้ไม่ถูกต้อง", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    class RenameVCModal(discord.ui.Modal, title="เปลี่ยนชื่อช่องเสียง"):
        """Modal สำหรับเปลี่ยนชื่อช่องเสียง"""

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        new_name = discord.ui.TextInput(
            label="ชื่อช่องใหม่",
            placeholder="ป้อนชื่อใหม่",
            max_length=100
        )

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.voice:
                await interaction.followup.send("❌ คุณต้องอยู่ในช่องเสียง", ephemeral=True)
                return

            target_channel = interaction.user.voice.channel
            guild_id = str(interaction.guild.id)
            channel_id = str(target_channel.id)

            is_owner = guild_id in self.cog.temp_channels and channel_id in self.cog.temp_channels[guild_id] and \
                      self.cog.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id

            if not is_owner and not interaction.user.guild_permissions.manage_channels:
                await interaction.followup.send("❌ คุณไม่ได้เป็นเจ้าของช่องนี้", ephemeral=True)
                return

            try:
                old_name = target_channel.name
                await target_channel.edit(name=self.new_name.value)
                embed = discord.Embed(title="✏️ เปลี่ยนชื่อแล้ว", description=f"`{old_name}` → `{self.new_name.value}`", color=discord.Color.blue())
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    class IncreaseVCModal(discord.ui.Modal, title="เพิ่มจำนวนผู้ใช้"):
        """Modal สำหรับเพิ่มจำนวนผู้ใช้"""

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        amount = discord.ui.TextInput(
            label="จำนวนที่ต้องการเพิ่ม",
            placeholder="1",
            max_length=3,
            default="1"
        )

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.voice:
                await interaction.followup.send("❌ คุณต้องอยู่ในช่องเสียง", ephemeral=True)
                return

            target_channel = interaction.user.voice.channel
            guild_id = str(interaction.guild.id)
            channel_id = str(target_channel.id)

            is_owner = guild_id in self.cog.temp_channels and channel_id in self.cog.temp_channels[guild_id] and \
                      self.cog.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id

            if not is_owner and not interaction.user.guild_permissions.manage_channels:
                await interaction.followup.send("❌ คุณไม่ได้เป็นเจ้าของช่องนี้", ephemeral=True)
                return

            try:
                amount = int(self.amount.value)
                current_limit = target_channel.user_limit if target_channel.user_limit else 0
                new_limit = current_limit + amount if current_limit > 0 else amount

                await target_channel.edit(user_limit=new_limit)
                embed = discord.Embed(title="⬆️ เพิ่มแล้ว", description=f"{current_limit if current_limit > 0 else '∞'} → {new_limit}", color=discord.Color.green())
                await interaction.followup.send(embed=embed, ephemeral=True)
            except ValueError:
                await interaction.followup.send("❌ ตัวเลขไม่ถูกต้อง", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    class DecreaseVCModal(discord.ui.Modal, title="ลดจำนวนผู้ใช้"):
        """Modal สำหรับลดจำนวนผู้ใช้"""

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        amount = discord.ui.TextInput(
            label="จำนวนที่ต้องการลด",
            placeholder="1",
            max_length=3,
            default="1"
        )

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.voice:
                await interaction.followup.send("❌ คุณต้องอยู่ในช่องเสียง", ephemeral=True)
                return

            target_channel = interaction.user.voice.channel
            guild_id = str(interaction.guild.id)
            channel_id = str(target_channel.id)

            is_owner = guild_id in self.cog.temp_channels and channel_id in self.cog.temp_channels[guild_id] and \
                      self.cog.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id

            if not is_owner and not interaction.user.guild_permissions.manage_channels:
                await interaction.followup.send("❌ คุณไม่ได้เป็นเจ้าของช่องนี้", ephemeral=True)
                return

            try:
                amount = int(self.amount.value)
                current_limit = target_channel.user_limit if target_channel.user_limit else 0
                new_limit = max(1, current_limit - amount) if current_limit > 0 else max(1, amount)

                await target_channel.edit(user_limit=new_limit)
                embed = discord.Embed(title="⬇️ ลดแล้ว", description=f"{current_limit if current_limit > 0 else '∞'} → {new_limit}", color=discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
            except ValueError:
                await interaction.followup.send("❌ ตัวเลขไม่ถูกต้อง", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    # -------- ตั้งค่า VOICE INTERFACE --------
    @voice_group.command(name="setup", description="ตั้งค่าอินเทอร์เฟซเสียงในช่องนี้")
    async def setup_panel(self, interaction: discord.Interaction):
        """ตั้งค่าอินเทอร์เฟซเสียงพร้อมปุ่ม"""
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.followup.send("❌ คุณต้องมีสิทธิ์จัดการเซิร์ฟเวอร์", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)

        if guild_id not in self.voice_settings:
            self.voice_settings[guild_id] = {}

        self.voice_settings[guild_id]["interface"] = channel_id
        self.save_config()

        # ส่งอินเทอร์เฟซ embed พร้อมปุ่ม
        embed = discord.Embed(
            title="🎙️ อินเทอร์เฟซเสียง",
            description="ใช้ปุ่มด้านล่างเพื่อจัดการช่องเสียง",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="📊 รายการช่อง",
            value="ดูช่องเสียงทั้งหมดและจำนวนสมาชิก",
            inline=False
        )
        embed.add_field(
            name="➕ สร้าง VC ชั่วคราว",
            value="สร้างช่องเสียงชั่วคราวที่ลบตัวเองเมื่อไม่มีคน",
            inline=False
        )
        embed.add_field(
            name="🔒 ล็อกช่อง",
            value="ล็อกช่องเสียง (ป้องกันการเข้าร่วมใหม่)",
            inline=False
        )
        embed.add_field(
            name="❌ ลบช่อง",
            value="ลบช่องเสียง",
            inline=False
        )
        embed.set_footer(text="คลิกปุ่มด้านล่างเพื่อดำเนินการ")

        await interaction.channel.send(embed=embed, view=self.VoiceInterfaceView(self))

        confirm_embed = discord.Embed(
            title="✅ ตั้งค่าอินเทอร์เฟซเสียงแล้ว",
            description=f"เปิดใช้งานอินเทอร์เฟซใน {interaction.channel.mention}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)

    # -------- งานล้างอัตโนมัติ --------
    @tasks.loop(minutes=1)
    async def cleanup_task(self):
        """ลบช่องเสียงชั่วคราวที่ไม่มีคนโดยอัตโนมัติ"""
        try:
            guilds_to_clean = []

            for guild_id, channels in list(self.temp_channels.items()):
                guild = self.bot.get_guild(int(guild_id))
                if not guild:
                    guilds_to_clean.append(guild_id)
                    continue

                channels_to_remove = []

                for channel_id, channel_info in list(channels.items()):
                    try:
                        channel = guild.get_channel(int(channel_id))

                        if not channel:
                            channels_to_remove.append(channel_id)
                            continue

                        # ตรวจสอบว่าช่องว่างหรือไม่
                        if len(channel.members) == 0:
                            # ตรวจสอบว่าช่องว่างมาแล้ว 5+ นาที
                            creation_time = datetime.fromisoformat(channel_info["created_at"])
                            if datetime.now() - creation_time > timedelta(minutes=5):
                                try:
                                    await channel.delete()
                                    channels_to_remove.append(channel_id)
                                except:
                                    pass
                    except:
                        pass

                # ลบช่องที่ติดตาม
                for channel_id in channels_to_remove:
                    if channel_id in channels:
                        del channels[channel_id]

            # ลบกิลด์ที่ไม่มีช่องที่ติดตาม
            for guild_id in guilds_to_clean:
                if guild_id in self.temp_channels:
                    del self.temp_channels[guild_id]

        except Exception as e:
            print(f"ข้อผิดพลาดในงานล้าง: {e}")

    @cleanup_task.before_loop
    async def before_cleanup(self):
        """รอให้บอทพร้อมก่อนล้าง"""
        await self.bot.wait_until_ready()

    # -------- อีเวนต์อัปเดตสถานะเสียง --------
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        """จัดการการเปลี่ยนแปลงสถานะเสียง"""
        # ผู้ใช้เข้าร่วมช่องเสียง
        if before.channel is None and after.channel is not None:
            guild_id = str(member.guild.id)
            if guild_id in self.voice_settings and "welcome_msg" in self.voice_settings[guild_id]:
                pass

        # ผู้ใช้ออกจากช่องเสียง
        if before.channel is not None and after.channel is None:
            channel = before.channel
            guild_id = str(member.guild.id)

            # ตรวจสอบว่าเป็นช่องชั่วคราวที่ควรลบหรือไม่
            if guild_id in self.temp_channels and str(channel.id) in self.temp_channels[guild_id]:
                if len(channel.members) == 0:
                    pass  # งานล้างจะจัดการให้

async def setup(bot: commands.Bot):
    """ตั้งค่า Voice Interface cog"""
    await bot.add_cog(VoiceInterface(bot))
