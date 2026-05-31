import asyncio
import io
from datetime import datetime
from typing import Any, Optional

import discord
from discord.ext import commands
from gtts import gTTS


class VCInfoView(discord.ui.View):
    def __init__(self, cog, author_id):
        super().__init__(timeout=60)
        self.cog = cog
        self.author_id = author_id

    async def get_vc_info_embed(self, guild):
        vc = guild.voice_client
        if not vc:
            return None

        embed = discord.Embed(title="🎤 ข้อมูลช่องเสียง", color=discord.Color.blurple())
        embed.add_field(name="ช่อง", value=vc.channel.mention, inline=True)
        embed.add_field(name="เซิร์ฟเวอร์", value=guild.name, inline=True)
        embed.add_field(name="เชื่อมต่อ", value="✅ ใช่" if vc.is_connected() else "❌ ไม่", inline=True)
        embed.add_field(name="กำลังเล่น", value="▶️ ใช่" if vc.is_playing() else "⏸️ ไม่", inline=True)
        embed.add_field(name="หยุดชั่วคราว", value="⏸️ ใช่" if vc.is_paused() else "▶️ ไม่", inline=True)
        embed.add_field(name="ปิดเสียง", value="🔇 ใช่" if vc.mute else "🔊 ไม่", inline=True)
        embed.add_field(name="ปิดหู", value="🔇 ใช่" if vc.deaf else "🔊 ไม่", inline=True)
        embed.add_field(name="ผู้ใช้", value=len(vc.channel.members), inline=True)
        embed.timestamp = datetime.now()
        return embed

    @discord.ui.button(label="รีเฟรช", style=discord.ButtonStyle.primary, emoji="🔄")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ นี่ไม่ใช่คำสั่งของคุณ!", ephemeral=True)
            return

        embed = await self.get_vc_info_embed(interaction.guild)
        if not embed:
            await interaction.response.send_message("❌ ยังไม่ได้เชื่อมต่อกับช่องเสียง", ephemeral=True)
            return

        await interaction.response.edit_message(embed=embed)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass


class VCPanelView(discord.ui.View):
    def __init__(self, cog, author_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.author_id = author_id

    async def get_panel_embed(self, guild):
        vc = guild.voice_client
        embed = discord.Embed(title="🎛️ แผงควบคุมช่องเสียง", color=discord.Color.blurple())
        
        if vc:
            embed.description = f"เชื่อมต่อกับ {vc.channel.mention}"
            embed.add_field(name="สถานะ", value="✅ เชื่อมต่อ", inline=True)
            bot_member = guild.me
            is_muted = bot_member.voice.mute if bot_member.voice else False
            is_deaf = bot_member.voice.deaf if bot_member.voice else False
            embed.add_field(name="ปิดเสียง", value="🔇 ใช่" if is_muted else "🔊 ไม่", inline=True)
            embed.add_field(name="ปิดหู", value="🔇 ใช่" if is_deaf else "🔊 ไม่", inline=True)
            embed.add_field(name="ผู้ใช้", value=str(len(vc.channel.members)), inline=True)
        else:
            embed.description = "ยังไม่ได้เชื่อมต่อกับช่องเสียงใดๆ"
            embed.add_field(name="สถานะ", value="❌ ตัดการเชื่อมต่อ", inline=True)
        
        embed.timestamp = datetime.now()
        return embed

    async def update_message(self, interaction: discord.Interaction):
        embed = await self.get_panel_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="เข้าร่วม", style=discord.ButtonStyle.success, emoji="▶️")
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ นี่ไม่ใช่แผงควบคุมของคุณ!", ephemeral=True)
            return

        if not interaction.user.voice:
            await interaction.response.send_message("❌ คุณไม่ได้อยู่ในช่องเสียง", ephemeral=True)
            return

        try:
            if interaction.guild.voice_client:
                await interaction.guild.voice_client.move_to(interaction.user.voice.channel)
            else:
                await interaction.user.voice.channel.connect()
            await self.update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @discord.ui.button(label="ออก", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def leave_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ นี่ไม่ใช่แผงควบคุมของคุณ!", ephemeral=True)
            return

        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ ยังไม่ได้เชื่อมต่อกับช่องเสียง", ephemeral=True)
            return

        try:
            await interaction.guild.voice_client.disconnect()
            await self.update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @discord.ui.button(label="ปิดเสียง", style=discord.ButtonStyle.secondary, emoji="🔇")
    async def mute_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ นี่ไม่ใช่แผงควบคุมของคุณ!", ephemeral=True)
            return

        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ ยังไม่ได้เชื่อมต่อกับช่องเสียง", ephemeral=True)
            return

        try:
            member = interaction.guild.me
            await member.edit(mute=not member.voice.mute)
            await self.update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @discord.ui.button(label="เปิดหู", style=discord.ButtonStyle.secondary, emoji="🎧")
    async def deafen_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ นี่ไม่ใช่แผงควบคุมของคุณ!", ephemeral=True)
            return

        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ ยังไม่ได้เชื่อมต่อกับช่องเสียง", ephemeral=True)
            return

        try:
            member = interaction.guild.me
            await member.edit(deafen=not member.voice.deaf)
            await self.update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass


class VC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="join", aliases=["j", "connect"])
    async def join(self, ctx, channel_id: int = None):
        try:
            if channel_id:
                channel = self.bot.get_channel(channel_id)
                if not channel or not isinstance(channel, discord.VoiceChannel):
                    await ctx.send("❌ ไม่พบ ID ช่องเสียงที่ถูกต้อง")
                    return
            else:
                if not ctx.author.voice:
                    await ctx.send("❌ คุณยังไม่ได้เชื่อมต่อกับช่องเสียง")
                    return
                channel = ctx.author.voice.channel

            if ctx.voice_client:
                await ctx.voice_client.move_to(channel)
            else:
                await channel.connect()

            await ctx.send(f"✅ เข้าร่วม {channel.mention}")
        except Exception as e:
            await ctx.send(f"❌ ข้อผิดพลาด: {e}")

    @discord.app_commands.command(name="join", description="เข้าร่วมช่องเสียง")
    async def slash_join(self, interaction: discord.Interaction, channel: discord.VoiceChannel = None):
        try:
            if channel:
                target = channel
            else:
                if not interaction.user.voice:
                    await interaction.response.send_message("❌ คุณยังไม่ได้เชื่อมต่อกับช่องเสียง", ephemeral=True)
                    return
                target = interaction.user.voice.channel

            if interaction.guild.voice_client:
                await interaction.guild.voice_client.move_to(target)
            else:
                await target.connect()

            await interaction.response.send_message(f"✅ เข้าร่วม {target.mention}")
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @commands.command(name="leave", aliases=["l", "disconnect", "dc"])
    async def leave(self, ctx):
        if not ctx.voice_client:
            await ctx.send("❌ ฉันยังไม่ได้เชื่อมต่อกับช่องเสียง")
            return

        await ctx.voice_client.disconnect()
        await ctx.send("✅ ออกจากช่องเสียงแล้ว")

    @discord.app_commands.command(name="leave", description="ออกจากช่องเสียง")
    async def slash_leave(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ ฉันยังไม่ได้เชื่อมต่อกับช่องเสียง", ephemeral=True)
            return

        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("✅ ออกจากช่องเสียงแล้ว")

    @commands.command(name="vcinfo")
    async def vcinfo(self, ctx):
        if not ctx.voice_client:
            await ctx.send("❌ ฉันยังไม่ได้เชื่อมต่อกับช่องเสียง")
            return

        view = VCInfoView(self, ctx.author.id)
        embed = await view.get_vc_info_embed(ctx.guild)
        view.message = await ctx.send(embed=embed, view=view)

    @discord.app_commands.command(name="vcinfo", description="แสดงข้อมูลช่องเสียง")
    async def slash_vcinfo(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ ฉันยังไม่ได้เชื่อมต่อกับช่องเสียง", ephemeral=True)
            return

        view = VCInfoView(self, interaction.user.id)
        embed = await view.get_vc_info_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        view.message = message

    @commands.command(name="vcmove")
    async def vcmove(self, ctx, channel_id: int):
        if not ctx.voice_client:
            await ctx.send("❌ ฉันยังไม่ได้เชื่อมต่อกับช่องเสียง")
            return

        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            await ctx.send("❌ ไม่พบ ID ช่องเสียงที่ถูกต้อง")
            return

        await ctx.voice_client.move_to(channel)
        await ctx.send(f"✅ ย้ายไปยัง {channel.mention}")

    @discord.app_commands.command(name="vcpanel", description="แผงควบคุมช่องเสียง")
    async def vcpanel(self, interaction: discord.Interaction):
        try:
            view = VCPanelView(self, interaction.user.id)
            embed = await view.get_panel_embed(interaction.guild)
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()
        except Exception as e:
            try:
                await interaction.response.send_message(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)
            except:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @discord.app_commands.command(name="ttshere", description="อ่านข้อความในช่องเสียง (ไทย/อังกฤษ/เกาหลี/ญี่ปุ่น)")
    @discord.app_commands.describe(
        language="ภาษา: th, en, ko, ja",
        include_name="รวมชื่อของคุณก่อนข้อความ",
        text="ข้อความที่จะอ่าน (เว้นว่างเพื่อฟังข้อความใหม่)"
    )
    async def ttshere(self, interaction: discord.Interaction, language: str = "en", include_name: bool = False, text: str = None):
        try:
            vc = interaction.guild.voice_client
            if not vc:
                await interaction.response.send_message("❌ ไม่ได้เชื่อมต่อกับช่องเสียง", ephemeral=True)
                return

            lang_map = {"th": "th", "en": "en", "ko": "ko", "ja": "ja"}
            lang_code = lang_map.get(language.lower(), "en")

            if not hasattr(self, "tts_listeners"):
                self.tts_listeners = {}

            guild_id = interaction.guild.id
            self.tts_listeners[guild_id] = {
                "language": lang_code,
                "include_name": include_name,
                "user_id": interaction.user.id,
                "channel": interaction.channel_id
            }

            if text:
                speak_text = text
                if include_name:
                    speak_text = f"{interaction.user.display_name} พูดว่า {text}"

                await interaction.response.defer()

                tts = gTTS(text=speak_text, lang=lang_code)
                audio_buffer = io.BytesIO()
                tts.write_to_fp(audio_buffer)
                audio_buffer.seek(0)

                vc.play(discord.FFmpegPCMAudio(audio_buffer, pipe=True))
                await interaction.followup.send(f"🔊 กำลังเล่น TTS ({language}): {speak_text[:100]}")
            else:
                await interaction.response.send_message(
                    f"🔊 กำลังฟังข้อความใหม่ใน {interaction.channel.mention} (ภาษา: {language}, include_name: {include_name})\n"
                    f"ใช้ `/ttsstop` เพื่อหยุดฟัง",
                    ephemeral=True
                )
        except Exception as e:
            try:
                await interaction.response.send_message(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)
            except:
                await interaction.followup.send(f"❌ ข้อผิดพลาด: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if not hasattr(self, "tts_listeners"):
            return

        guild_id = message.guild.id
        if guild_id not in self.tts_listeners:
            return

        listener = self.tts_listeners[guild_id]
        if message.channel.id != listener["channel"]:
            return

        vc = message.guild.voice_client
        if not vc:
            return

        speak_text = message.content
        if listener["include_name"]:
            speak_text = f"{message.author.display_name} พูดว่า {speak_text}"

        try:
            tts = gTTS(text=speak_text, lang=listener["language"])
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)

            if vc.is_playing():
                vc.stop()
            vc.play(discord.FFmpegPCMAudio(audio_buffer, pipe=True))
        except Exception:
            pass

    @discord.app_commands.command(name="ttsstop", description="หยุดเล่น TTS และฟังข้อความ")
    async def ttsstop(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id

        if hasattr(self, "tts_listeners") and guild_id in self.tts_listeners:
            del self.tts_listeners[guild_id]
            stopped_listening = True
        else:
            stopped_listening = False

        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            stopped_playing = True
        else:
            stopped_playing = False

        if stopped_listening or stopped_playing:
            await interaction.response.send_message("⏹️ หยุด TTS แล้ว", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ไม่มีอะไรกำลังเล่นหรือฟังอยู่", ephemeral=True)


async def setup(bot):
    await bot.add_cog(VC(bot))
