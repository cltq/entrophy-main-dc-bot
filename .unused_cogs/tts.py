import discord
from discord.ext import commands
from discord import app_commands
import gtts
import os
import asyncio
from io import BytesIO
import tempfile

class TTS(commands.Cog):
    """ฟังก์ชันข้อความเป็นเสียงสำหรับช่องเสียง"""

    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # เก็บการเชื่อมต่อ voice client ตามกิลด์

    def cleanup(self):
        """ลบไฟล์ชั่วคราว"""
        pass

    async def speak_text(self, voice_client: discord.VoiceClient, text: str, language: str = "en"):
        """แปลงข้อความเป็นเสียงและเล่นในช่องเสียง"""
        try:
            # สร้าง TTS
            tts = gtts.gTTS(text=text, lang=language, slow=False)

            # สร้างไฟล์ชั่วคราว
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_file = fp.name
                tts.save(temp_file)

            # สร้างแหล่งเสียง
            audio_source = discord.FFmpegPCMAudio(temp_file)

            # เล่นเสียง
            if not voice_client.is_playing():
                voice_client.play(
                    audio_source,
                    after=lambda e: self.cleanup_audio(temp_file)
                )
            else:
                # เข้าคิวหากกำลังเล่นอยู่
                await asyncio.sleep(1)
                voice_client.play(
                    audio_source,
                    after=lambda e: self.cleanup_audio(temp_file)
                )

        except Exception as e:
            print(f"[TTS ERROR] {e}")
            raise

    def cleanup_audio(self, file_path: str):
        """ลบไฟล์เสียงชั่วคราว"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"[TTS CLEANUP ERROR] {e}")

    voice_group = app_commands.Group(name="bot", description="🤖 คำสั่งเสียงบอท")
    voice_group.allowed_contexts(guilds=True)

    @voice_group.command(name="join", description="เข้าร่วมช่องเสียงปัจจุบันของคุณ")
    @app_commands.describe()
    async def join(self, interaction: discord.Interaction):
        """เข้าร่วมช่องเสียงของผู้ใช้"""
        await interaction.response.defer(ephemeral=True)

        try:
            # ตรวจสอบว่าผู้ใช้อยู่ในช่องเสียงหรือไม่
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send(
                    "❌ คุณต้องอยู่ในช่องเสียงเพื่อใช้คำสั่งนี้!",
                    ephemeral=True
                )
                return

            voice_channel = interaction.user.voice.channel

            # ตรวจสอบว่าบอทอยู่ในช่องเสียงอยู่แล้วหรือไม่
            if interaction.guild.voice_client:
                if interaction.guild.voice_client.channel == voice_channel:
                    await interaction.followup.send(
                        f"✅ ฉันอยู่ใน {voice_channel.mention} อยู่แล้ว!",
                        ephemeral=True
                    )
                    return
                else:
                    # ตัดการเชื่อมต่อจากช่องปัจจุบัน
                    await interaction.guild.voice_client.disconnect()

            # เข้าร่วมช่องเสียง
            voice_client = await voice_channel.connect()
            self.voice_clients[interaction.guild.id] = voice_client

            embed = discord.Embed(
                title="✅ เข้าร่วมช่องเสียงแล้ว",
                description=f"เชื่อมต่อกับ {voice_channel.mention}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.ClientException:
            await interaction.followup.send(
                "❌ ฉันเชื่อมต่อกับช่องเสียงอยู่แล้ว!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ เกิดข้อผิดพลาดในการเข้าร่วมช่องเสียง: {str(e)}",
                ephemeral=True
            )

    @voice_group.command(name="leave", description="ออกจากช่องเสียง")
    @app_commands.describe()
    async def leave(self, interaction: discord.Interaction):
        """ออกจากช่องเสียง"""
        await interaction.response.defer(ephemeral=True)

        try:
            # ตรวจสอบว่าบอทอยู่ในช่องเสียงหรือไม่
            if not interaction.guild.voice_client:
                await interaction.followup.send(
                    "❌ ฉันไม่ได้อยู่ในช่องเสียง!",
                    ephemeral=True
                )
                return

            voice_channel = interaction.guild.voice_client.channel
            await interaction.guild.voice_client.disconnect()

            if interaction.guild.id in self.voice_clients:
                del self.voice_clients[interaction.guild.id]

            embed = discord.Embed(
                title="✅ ออกจากช่องเสียงแล้ว",
                description=f"ตัดการเชื่อมต่อจาก {voice_channel.mention}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                f"❌ เกิดข้อผิดพลาดในการออกจากช่องเสียง: {str(e)}",
                ephemeral=True
            )

    @voice_group.command(name="speak", description="พูดข้อความในช่องเสียง")
    @app_commands.describe(text="ข้อความที่จะพูด", language="ภาษา (en=อังกฤษ, th=ไทย)")
    async def speak(self, interaction: discord.Interaction, text: str, language: str = "en"):
        """พูดข้อความในช่องเสียง"""
        await interaction.response.defer(ephemeral=True)

        try:
            # ตรวจสอบภาษา
            supported_languages = {
                "en": "English",
                "th": "Thai"
            }

            lang_code = language.lower()
            if lang_code not in supported_languages:
                await interaction.followup.send(
                    f"❌ ไม่รองรับภาษา: `{language}`. รองรับ: en (อังกฤษ), th (ไทย)",
                    ephemeral=True
                )
                return

            # ตรวจสอบว่าบอทอยู่ในช่องเสียงหรือไม่
            if not interaction.guild.voice_client:
                await interaction.followup.send(
                    "❌ ฉันไม่ได้อยู่ในช่องเสียง! ใช้ `/bot join` ก่อน",
                    ephemeral=True
                )
                return

            # ตรวจสอบความยาวข้อความ
            if len(text) > 500:
                await interaction.followup.send(
                    "❌ ข้อความยาวเกินไป! สูงสุด 500 ตัวอักษร",
                    ephemeral=True
                )
                return

            voice_client = interaction.guild.voice_client

            # ตรวจสอบว่าผู้ใช่อยู่ในช่องเสียงเดียวกัน
            if not interaction.user.voice or interaction.user.voice.channel != voice_client.channel:
                await interaction.followup.send(
                    f"❌ คุณต้องอยู่ใน {voice_client.channel.mention} เพื่อใช้คำสั่งนี้!",
                    ephemeral=True
                )
                return

            # สร้าง TTS ด้วยภาษาที่เลือก
            tts = gtts.gTTS(text=text, lang=lang_code, slow=False)

            # สร้างไฟล์ชั่วคราว
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_file = fp.name
                tts.save(temp_file)

            # สร้างแหล่งเสียงและเล่น
            audio_source = discord.FFmpegPCMAudio(temp_file)
            voice_client.play(
                audio_source,
                after=lambda e: self.cleanup_audio(temp_file) if e is None else print(f"Playback error: {e}")
            )

            embed = discord.Embed(
                title="🔊 กำลังพูด",
                description=f"**ภาษา:** {supported_languages[lang_code]}\n**ข้อความ:** {text[:100]}{'...' if len(text) > 100 else ''}",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                f"❌ เกิดข้อผิดพลาดในการพูดข้อความ: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    """ฟังก์ชันที่จำเป็นสำหรับโหลด cog"""
    await bot.add_cog(TTS(bot))
