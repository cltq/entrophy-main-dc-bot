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

        embed = discord.Embed(title="🎤 Voice Channel Info", color=discord.Color.blurple())
        embed.add_field(name="Channel", value=vc.channel.mention, inline=True)
        embed.add_field(name="Guild", value=guild.name, inline=True)
        embed.add_field(name="Connected", value="✅ Yes" if vc.is_connected() else "❌ No", inline=True)
        embed.add_field(name="Playing", value="▶️ Yes" if vc.is_playing() else "⏸️ No", inline=True)
        embed.add_field(name="Paused", value="⏸️ Yes" if vc.is_paused() else "▶️ No", inline=True)
        embed.add_field(name="Muted", value="🔇 Yes" if vc.mute else "🔊 No", inline=True)
        embed.add_field(name="Deafened", value="🔇 Yes" if vc.deaf else "🔊 No", inline=True)
        embed.add_field(name="Users", value=len(vc.channel.members), inline=True)
        embed.timestamp = datetime.now()
        return embed

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, emoji="🔄")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your command!", ephemeral=True)
            return

        embed = await self.get_vc_info_embed(interaction.guild)
        if not embed:
            await interaction.response.send_message("❌ Not connected to voice channel", ephemeral=True)
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
        embed = discord.Embed(title="🎛️ Voice Channel Control Panel", color=discord.Color.blurple())
        
        if vc:
            embed.description = f"Connected to {vc.channel.mention}"
            embed.add_field(name="Status", value="✅ Connected", inline=True)
            bot_member = guild.me
            is_muted = bot_member.voice.mute if bot_member.voice else False
            is_deaf = bot_member.voice.deaf if bot_member.voice else False
            embed.add_field(name="Muted", value="🔇 Yes" if is_muted else "🔊 No", inline=True)
            embed.add_field(name="Deafened", value="🔇 Yes" if is_deaf else "🔊 No", inline=True)
            embed.add_field(name="Users", value=str(len(vc.channel.members)), inline=True)
        else:
            embed.description = "Not connected to any voice channel"
            embed.add_field(name="Status", value="❌ Disconnected", inline=True)
        
        embed.timestamp = datetime.now()
        return embed

    async def update_message(self, interaction: discord.Interaction):
        embed = await self.get_panel_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, emoji="▶️")
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your panel!", ephemeral=True)
            return

        if not interaction.user.voice:
            await interaction.response.send_message("❌ You are not in a voice channel.", ephemeral=True)
            return

        try:
            if interaction.guild.voice_client:
                await interaction.guild.voice_client.move_to(interaction.user.voice.channel)
            else:
                await interaction.user.voice.channel.connect()
            await self.update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def leave_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your panel!", ephemeral=True)
            return

        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ Not connected to voice channel.", ephemeral=True)
            return

        try:
            await interaction.guild.voice_client.disconnect()
            await self.update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="Mute", style=discord.ButtonStyle.secondary, emoji="🔇")
    async def mute_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your panel!", ephemeral=True)
            return

        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ Not connected to voice channel.", ephemeral=True)
            return

        try:
            member = interaction.guild.me
            await member.edit(mute=not member.voice.mute)
            await self.update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="Deafen", style=discord.ButtonStyle.secondary, emoji="🎧")
    async def deafen_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your panel!", ephemeral=True)
            return

        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ Not connected to voice channel.", ephemeral=True)
            return

        try:
            member = interaction.guild.me
            await member.edit(deafen=not member.voice.deaf)
            await self.update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

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
                    await ctx.send("❌ Invalid voice channel ID provided.")
                    return
            else:
                if not ctx.author.voice:
                    await ctx.send("❌ You are not connected to a voice channel.")
                    return
                channel = ctx.author.voice.channel

            if ctx.voice_client:
                await ctx.voice_client.move_to(channel)
            else:
                await channel.connect()

            await ctx.send(f"✅ Joined {channel.mention}")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @discord.app_commands.command(name="join", description="Join a voice channel")
    async def slash_join(self, interaction: discord.Interaction, channel: discord.VoiceChannel = None):
        try:
            if channel:
                target = channel
            else:
                if not interaction.user.voice:
                    await interaction.response.send_message("❌ You are not connected to a voice channel.", ephemeral=True)
                    return
                target = interaction.user.voice.channel

            if interaction.guild.voice_client:
                await interaction.guild.voice_client.move_to(target)
            else:
                await target.connect()

            await interaction.response.send_message(f"✅ Joined {target.mention}")
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @commands.command(name="leave", aliases=["l", "disconnect", "dc"])
    async def leave(self, ctx):
        if not ctx.voice_client:
            await ctx.send("❌ I am not connected to a voice channel.")
            return

        await ctx.voice_client.disconnect()
        await ctx.send("✅ Disconnected from voice channel")

    @discord.app_commands.command(name="leave", description="Leave the voice channel")
    async def slash_leave(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ I am not connected to a voice channel.", ephemeral=True)
            return

        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("✅ Disconnected from voice channel")

    @commands.command(name="vcinfo")
    async def vcinfo(self, ctx):
        if not ctx.voice_client:
            await ctx.send("❌ I am not connected to a voice channel.")
            return

        view = VCInfoView(self, ctx.author.id)
        embed = await view.get_vc_info_embed(ctx.guild)
        view.message = await ctx.send(embed=embed, view=view)

    @discord.app_commands.command(name="vcinfo", description="Show voice channel info")
    async def slash_vcinfo(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ I am not connected to a voice channel.", ephemeral=True)
            return

        view = VCInfoView(self, interaction.user.id)
        embed = await view.get_vc_info_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        view.message = message

    @commands.command(name="vcmove")
    async def vcmove(self, ctx, channel_id: int):
        if not ctx.voice_client:
            await ctx.send("❌ I am not connected to a voice channel.")
            return

        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            await ctx.send("❌ Invalid voice channel ID provided.")
            return

        await ctx.voice_client.move_to(channel)
        await ctx.send(f"✅ Moved to {channel.mention}")

    @discord.app_commands.command(name="vcpanel", description="Voice channel control panel")
    async def vcpanel(self, interaction: discord.Interaction):
        try:
            view = VCPanelView(self, interaction.user.id)
            embed = await view.get_panel_embed(interaction.guild)
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()
        except Exception as e:
            try:
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            except:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @discord.app_commands.command(name="ttshere", description="Read messages in voice channel (Thai/English/Korean/Japanese)")
    @discord.app_commands.describe(
        language="Language: th, en, ko, ja",
        include_name="Include your name before the message",
        text="Text to read (leave empty to listen for new messages)"
    )
    async def ttshere(self, interaction: discord.Interaction, language: str = "en", include_name: bool = False, text: str = None):
        try:
            vc = interaction.guild.voice_client
            if not vc:
                await interaction.response.send_message("❌ Not connected to voice channel.", ephemeral=True)
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
                    speak_text = f"{interaction.user.display_name} says {text}"

                await interaction.response.defer()

                tts = gTTS(text=speak_text, lang=lang_code)
                audio_buffer = io.BytesIO()
                tts.write_to_fp(audio_buffer)
                audio_buffer.seek(0)

                vc.play(discord.FFmpegPCMAudio(audio_buffer, pipe=True))
                await interaction.followup.send(f"🔊 Playing TTS ({language}): {speak_text[:100]}")
            else:
                await interaction.response.send_message(
                    f"🔊 Listening for new messages in {interaction.channel.mention} (lang: {language}, include_name: {include_name})\n"
                    f"Use `/ttsstop` to stop listening.",
                    ephemeral=True
                )
        except Exception as e:
            try:
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            except:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

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
            speak_text = f"{message.author.display_name} says {speak_text}"

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

    @discord.app_commands.command(name="ttsstop", description="Stop TTS playback and listening")
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
            await interaction.response.send_message("⏹️ Stopped TTS", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing or listening.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(VC(bot))
