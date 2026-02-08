import discord
from discord.ext import commands
from discord import app_commands
import gtts
import os
import asyncio
from io import BytesIO
import tempfile

class TTS(commands.Cog):
    """Text-To-Speech functionality for voice channels"""

    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # Store voice client connections per guild

    def cleanup(self):
        """Cleanup temp files"""
        pass

    async def speak_text(self, voice_client: discord.VoiceClient, text: str, language: str = "en"):
        """Convert text to speech and play in voice channel"""
        try:
            # Create TTS
            tts = gtts.gTTS(text=text, lang=language, slow=False)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_file = fp.name
                tts.save(temp_file)
            
            # Create audio source
            audio_source = discord.FFmpegPCMAudio(temp_file)
            
            # Play audio
            if not voice_client.is_playing():
                voice_client.play(
                    audio_source,
                    after=lambda e: self.cleanup_audio(temp_file)
                )
            else:
                # Queue if already playing
                await asyncio.sleep(1)
                voice_client.play(
                    audio_source,
                    after=lambda e: self.cleanup_audio(temp_file)
                )
                
        except Exception as e:
            print(f"[TTS ERROR] {e}")
            raise

    def cleanup_audio(self, file_path: str):
        """Cleanup temporary audio file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"[TTS CLEANUP ERROR] {e}")

    voice_group = app_commands.Group(name="bot", description="🤖 Bot voice commands")
    voice_group.allowed_contexts(guilds=True)

    @voice_group.command(name="join", description="Join your current voice channel")
    @app_commands.describe()
    async def join(self, interaction: discord.Interaction):
        """Join the voice channel of the user"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user is in a voice channel
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send(
                    "❌ You must be in a voice channel to use this command!",
                    ephemeral=True
                )
                return
            
            voice_channel = interaction.user.voice.channel
            
            # Check if bot is already in a voice channel
            if interaction.guild.voice_client:
                if interaction.guild.voice_client.channel == voice_channel:
                    await interaction.followup.send(
                        f"✅ I'm already in {voice_channel.mention}!",
                        ephemeral=True
                    )
                    return
                else:
                    # Disconnect from current channel
                    await interaction.guild.voice_client.disconnect()
            
            # Join the voice channel
            voice_client = await voice_channel.connect()
            self.voice_clients[interaction.guild.id] = voice_client
            
            embed = discord.Embed(
                title="✅ Joined Voice Channel",
                description=f"Connected to {voice_channel.mention}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except discord.ClientException:
            await interaction.followup.send(
                "❌ I'm already connected to a voice channel!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error joining voice channel: {str(e)}",
                ephemeral=True
            )

    @voice_group.command(name="leave", description="Leave the voice channel")
    @app_commands.describe()
    async def leave(self, interaction: discord.Interaction):
        """Leave the voice channel"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if bot is in a voice channel
            if not interaction.guild.voice_client:
                await interaction.followup.send(
                    "❌ I'm not in a voice channel!",
                    ephemeral=True
                )
                return
            
            voice_channel = interaction.guild.voice_client.channel
            await interaction.guild.voice_client.disconnect()
            
            if interaction.guild.id in self.voice_clients:
                del self.voice_clients[interaction.guild.id]
            
            embed = discord.Embed(
                title="✅ Left Voice Channel",
                description=f"Disconnected from {voice_channel.mention}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error leaving voice channel: {str(e)}",
                ephemeral=True
            )

    @voice_group.command(name="speak", description="Speak text in the voice channel")
    @app_commands.describe(text="Text to speak", language="Language (en=English, th=Thai)")
    async def speak(self, interaction: discord.Interaction, text: str, language: str = "en"):
        """Speak text in the voice channel"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate language
            supported_languages = {
                "en": "English",
                "th": "Thai"
            }
            
            lang_code = language.lower()
            if lang_code not in supported_languages:
                await interaction.followup.send(
                    f"❌ Unsupported language: `{language}`. Supported: en (English), th (Thai)",
                    ephemeral=True
                )
                return
            
            # Check if bot is in a voice channel
            if not interaction.guild.voice_client:
                await interaction.followup.send(
                    "❌ I'm not in a voice channel! Use `/bot join` first.",
                    ephemeral=True
                )
                return
            
            # Check text length
            if len(text) > 500:
                await interaction.followup.send(
                    "❌ Text is too long! Maximum 500 characters.",
                    ephemeral=True
                )
                return
            
            voice_client = interaction.guild.voice_client
            
            # Check if user is in the same voice channel
            if not interaction.user.voice or interaction.user.voice.channel != voice_client.channel:
                await interaction.followup.send(
                    f"❌ You must be in {voice_client.channel.mention} to use this command!",
                    ephemeral=True
                )
                return
            
            # Create TTS with selected language
            tts = gtts.gTTS(text=text, lang=lang_code, slow=False)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_file = fp.name
                tts.save(temp_file)
            
            # Create audio source and play
            audio_source = discord.FFmpegPCMAudio(temp_file)
            voice_client.play(
                audio_source,
                after=lambda e: self.cleanup_audio(temp_file) if e is None else print(f"Playback error: {e}")
            )
            
            embed = discord.Embed(
                title="🔊 Speaking",
                description=f"**Language:** {supported_languages[lang_code]}\n**Text:** {text[:100]}{'...' if len(text) > 100 else ''}",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error speaking text: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    """Required function to load the cog"""
    await bot.add_cog(TTS(bot))
