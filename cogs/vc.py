"""
Voice Interface Cog
Manages voice channels with advanced features like locking, hiding, claiming, and permissions
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
    """🎙️ Voice Interface - Manage voice channels with advanced features"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "config/vc_config.json"
        self.temp_channels = {}  # Track temporary channels {guild_id: {channel_id: creation_time}}
        self.voice_settings = {}  # Track voice settings per guild
        self.cleanup_task.start()
        self.load_config()
    
    def load_config(self):
        """Load voice control settings from JSON"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    self.voice_settings = json.load(f)
        except Exception as e:
            print(f"Error loading VC config: {e}")
            self.voice_settings = {}
    
    def save_config(self):
        """Save voice control settings to JSON"""
        try:
            os.makedirs("config", exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.voice_settings, f, indent=2)
        except Exception as e:
            print(f"Error saving VC config: {e}")
    
    # -------- VOICE INTERFACE COMMANDS --------
    voice_group = app_commands.Group(name="vc", description="🎙️ Voice Interface")
    
    # -------- CREATE TEMPORARY VC --------
    @voice_group.command(name="create", description="Create a temporary voice channel")
    @app_commands.describe(
        name="Voice channel name",
        limit="User limit (0 = unlimited)",
        bitrate="Audio bitrate in kbps (default 64)"
    )
    async def create_temp_vc(
        self,
        interaction: discord.Interaction,
        name: str,
        limit: int = 0,
        bitrate: int = 64
    ):
        """Create a temporary voice channel that auto-deletes when empty"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("❌ This command only works in servers.", ephemeral=True)
                return
            
            # Get parent category (optional)
            parent_category = interaction.channel.category if hasattr(interaction.channel, 'category') else None
            
            # Create voice channel
            voice_channel = await guild.create_voice_channel(
                name=name,
                user_limit=limit if limit > 0 else None,
                bitrate=min(bitrate * 1000, guild.bitrate_limit) if bitrate else 64000,
                category=parent_category
            )
            
            # Track temporary channel
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
                title="✅ Temporary Voice Channel Created",
                description=f"Channel: {voice_channel.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Name", value=f"`{name}`", inline=True)
            embed.add_field(name="User Limit", value=f"{'Unlimited' if limit == 0 else limit}", inline=True)
            embed.add_field(name="Bitrate", value=f"{bitrate} kbps", inline=True)
            embed.set_footer(text="This channel will auto-delete when empty")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Create Channel",
                description=f"Error: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # -------- LOCK VOICE CHANNEL --------
    @voice_group.command(name="lock", description="🔒 Lock the voice channel")
    @app_commands.describe(channel="Voice channel to lock (optional, uses current if in VC)")
    async def lock_vc(self, interaction: discord.Interaction, channel: Optional[discord.VoiceChannel] = None):
        """Lock voice channel from new members"""
        await interaction.response.defer(ephemeral=True)
        
        # Determine which channel to lock
        if channel:
            target_channel = channel
        elif interaction.user.voice:
            target_channel = interaction.user.voice.channel
        else:
            await interaction.followup.send("❌ You must be in a voice channel or specify one.", ephemeral=True)
            return
        
        # Check if user owns the channel
        guild_id = str(interaction.guild.id)
        channel_id = str(target_channel.id)
        
        is_owner = False
        if guild_id in self.temp_channels and channel_id in self.temp_channels[guild_id]:
            is_owner = self.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id
        
        if not is_owner and not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ You don't own this channel or have Manage Channels permission.", ephemeral=True)
            return
        
        try:
            everyone_role = interaction.guild.default_role
            await target_channel.set_permissions(everyone_role, connect=False)
            
            embed = discord.Embed(
                title="🔒 Voice Channel Locked",
                description=f"{target_channel.mention} is now locked",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Lock Failed",
                description=f"Error: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # -------- UNLOCK VOICE CHANNEL --------
    @voice_group.command(name="unlock", description="🔓 Unlock the voice channel")
    @app_commands.describe(channel="Voice channel to unlock (optional, uses current if in VC)")
    async def unlock_vc(self, interaction: discord.Interaction, channel: Optional[discord.VoiceChannel] = None):
        """Unlock voice channel"""
        await interaction.response.defer(ephemeral=True)
        
        # Determine which channel to unlock
        if channel:
            target_channel = channel
        elif interaction.user.voice:
            target_channel = interaction.user.voice.channel
        else:
            await interaction.followup.send("❌ You must be in a voice channel or specify one.", ephemeral=True)
            return
        
        # Check if user owns the channel
        guild_id = str(interaction.guild.id)
        channel_id = str(target_channel.id)
        
        is_owner = False
        if guild_id in self.temp_channels and channel_id in self.temp_channels[guild_id]:
            is_owner = self.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id
        
        if not is_owner and not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ You don't own this channel or have Manage Channels permission.", ephemeral=True)
            return
        
        try:
            everyone_role = interaction.guild.default_role
            await target_channel.set_permissions(everyone_role, connect=None)
            
            embed = discord.Embed(
                title="🔓 Voice Channel Unlocked",
                description=f"{target_channel.mention} is now unlocked",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Unlock Failed",
                description=f"Error: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # -------- HIDE VOICE CHANNEL --------
    @voice_group.command(name="hide", description="👁️ Hide the voice channel")
    @app_commands.describe(channel="Voice channel to hide (optional, uses current if in VC)")
    async def hide_vc(self, interaction: discord.Interaction, channel: Optional[discord.VoiceChannel] = None):
        """Hide voice channel from users who aren't in it"""
        await interaction.response.defer(ephemeral=True)
        
        if channel:
            target_channel = channel
        elif interaction.user.voice:
            target_channel = interaction.user.voice.channel
        else:
            await interaction.followup.send("❌ You must be in a voice channel or specify one.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        channel_id = str(target_channel.id)
        
        is_owner = False
        if guild_id in self.temp_channels and channel_id in self.temp_channels[guild_id]:
            is_owner = self.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id
        
        if not is_owner and not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ You don't own this channel or have Manage Channels permission.", ephemeral=True)
            return
        
        try:
            everyone_role = interaction.guild.default_role
            await target_channel.set_permissions(everyone_role, view_channel=False)
            
            embed = discord.Embed(
                title="👁️ Voice Channel Hidden",
                description=f"{target_channel.mention} is now hidden",
                color=discord.Color.purple()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Hide Failed",
                description=f"Error: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # -------- REVEAL VOICE CHANNEL --------
    @voice_group.command(name="reveal", description="🔍 Reveal the voice channel")
    @app_commands.describe(channel="Voice channel to reveal (optional, uses current if in VC)")
    async def reveal_vc(self, interaction: discord.Interaction, channel: Optional[discord.VoiceChannel] = None):
        """Reveal voice channel to all users"""
        await interaction.response.defer(ephemeral=True)
        
        if channel:
            target_channel = channel
        elif interaction.user.voice:
            target_channel = interaction.user.voice.channel
        else:
            await interaction.followup.send("❌ You must be in a voice channel or specify one.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        channel_id = str(target_channel.id)
        
        is_owner = False
        if guild_id in self.temp_channels and channel_id in self.temp_channels[guild_id]:
            is_owner = self.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id
        
        if not is_owner and not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ You don't own this channel or have Manage Channels permission.", ephemeral=True)
            return
        
        try:
            everyone_role = interaction.guild.default_role
            await target_channel.set_permissions(everyone_role, view_channel=None)
            
            embed = discord.Embed(
                title="🔍 Voice Channel Revealed",
                description=f"{target_channel.mention} is now visible",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Reveal Failed",
                description=f"Error: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # -------- CLAIM VOICE CHANNEL --------
    @voice_group.command(name="claim", description="👑 Claim the voice channel")
    @app_commands.describe(channel="Voice channel to claim (optional, uses current if in VC)")
    async def claim_vc(self, interaction: discord.Interaction, channel: Optional[discord.VoiceChannel] = None):
        """Claim ownership of a voice channel"""
        await interaction.response.defer(ephemeral=True)
        
        if channel:
            target_channel = channel
        elif interaction.user.voice:
            target_channel = interaction.user.voice.channel
        else:
            await interaction.followup.send("❌ You must be in a voice channel or specify one.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        channel_id = str(target_channel.id)
        
        # Check if channel is already owned
        if guild_id in self.temp_channels and channel_id in self.temp_channels[guild_id]:
            current_owner = self.temp_channels[guild_id][channel_id].get("owner")
            if current_owner and current_owner != interaction.user.id:
                await interaction.followup.send("❌ This channel is already owned by someone else.", ephemeral=True)
                return
        
        # Set ownership
        if guild_id not in self.temp_channels:
            self.temp_channels[guild_id] = {}
        
        if channel_id not in self.temp_channels[guild_id]:
            self.temp_channels[guild_id][channel_id] = {}
        
        self.temp_channels[guild_id][channel_id]["owner"] = interaction.user.id
        
        embed = discord.Embed(
            title="👑 Channel Claimed",
            description=f"{interaction.user.mention} is now the owner of {target_channel.mention}",
            color=discord.Color.gold()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    # -------- KICK USER FROM VOICE CHANNEL --------
    @voice_group.command(name="kick", description="🚪 Manage permitted & rejected users")
    @app_commands.describe(
        user="User to manage",
        action="Allow or Reject access"
    )
    @app_commands.choices(action=[
        discord.app_commands.Choice(name="Allow", value="allow"),
        discord.app_commands.Choice(name="Reject", value="reject"),
    ])
    async def kick_user(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        action: discord.app_commands.Choice[str]
    ):
        """Manage user access to voice channel"""
        await interaction.response.defer(ephemeral=True)
        
        if interaction.user.voice:
            target_channel = interaction.user.voice.channel
        else:
            await interaction.followup.send("❌ You must be in a voice channel.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        channel_id = str(target_channel.id)
        
        is_owner = False
        if guild_id in self.temp_channels and channel_id in self.temp_channels[guild_id]:
            is_owner = self.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id
        
        if not is_owner and not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ You don't own this channel or have Manage Channels permission.", ephemeral=True)
            return
        
        try:
            if action.value == "allow":
                await target_channel.set_permissions(user, connect=True)
                embed = discord.Embed(
                    title="✅ User Allowed",
                    description=f"{user.mention} can now join {target_channel.mention}",
                    color=discord.Color.green()
                )
            else:  # reject
                await target_channel.set_permissions(user, connect=False)
                # Disconnect user if in channel
                if user.voice and user.voice.channel == target_channel:
                    await user.move_to(None)
                embed = discord.Embed(
                    title="🚫 User Rejected",
                    description=f"{user.mention} cannot join {target_channel.mention}",
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Operation Failed",
                description=f"Error: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # -------- VOICE CHANNEL INFO --------
    @voice_group.command(name="info", description="ℹ️ Info about the voice channel")
    @app_commands.describe(channel="Voice channel to get info about (optional, uses current if in VC)")
    async def info_vc(self, interaction: discord.Interaction, channel: Optional[discord.VoiceChannel] = None):
        """Get information about a voice channel"""
        await interaction.response.defer(ephemeral=True)
        
        if channel:
            target_channel = channel
        elif interaction.user.voice:
            target_channel = interaction.user.voice.channel
        else:
            await interaction.followup.send("❌ You must be in a voice channel or specify one.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        channel_id = str(target_channel.id)
        
        embed = discord.Embed(
            title=f"ℹ️ {target_channel.name}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Channel ID", value=target_channel.id, inline=True)
        embed.add_field(name="Members", value=f"{len(target_channel.members)}", inline=True)
        embed.add_field(name="User Limit", value=f"{target_channel.user_limit if target_channel.user_limit else '∞'}", inline=True)
        embed.add_field(name="Bitrate", value=f"{target_channel.bitrate // 1000} kbps", inline=True)
        embed.add_field(name="Created", value=target_channel.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        is_temp = guild_id in self.temp_channels and channel_id in self.temp_channels[guild_id]
        is_locked = target_channel.permissions_for(interaction.guild.default_role).connect is False
        is_hidden = target_channel.permissions_for(interaction.guild.default_role).view_channel is False
        
        embed.add_field(name="Temporary", value="🌀 Yes" if is_temp else "❌ No", inline=True)
        embed.add_field(name="Locked", value="🔒 Yes" if is_locked else "🔓 No", inline=True)
        embed.add_field(name="Hidden", value="👁️ Yes" if is_hidden else "🔍 No", inline=True)
        
        if is_temp and guild_id in self.temp_channels and channel_id in self.temp_channels[guild_id]:
            owner_id = self.temp_channels[guild_id][channel_id].get("owner")
            if owner_id:
                owner = interaction.guild.get_member(owner_id)
                embed.add_field(name="Owner", value=owner.mention if owner else f"<@{owner_id}>", inline=True)
        
        members_str = ", ".join([m.mention for m in target_channel.members[:10]])
        if len(target_channel.members) > 10:
            members_str += f" +{len(target_channel.members) - 10} more"
        
        if target_channel.members:
            embed.add_field(name="Current Members", value=members_str or "None", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    # -------- RENAME VOICE CHANNEL --------
    @voice_group.command(name="rename", description="✏️ Rename the voice channel")
    @app_commands.describe(
        new_name="New channel name",
        channel="Voice channel to rename (optional, uses current if in VC)"
    )
    async def rename_vc(
        self,
        interaction: discord.Interaction,
        new_name: str,
        channel: Optional[discord.VoiceChannel] = None
    ):
        """Rename a voice channel"""
        await interaction.response.defer(ephemeral=True)
        
        if channel:
            target_channel = channel
        elif interaction.user.voice:
            target_channel = interaction.user.voice.channel
        else:
            await interaction.followup.send("❌ You must be in a voice channel or specify one.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        channel_id = str(target_channel.id)
        
        is_owner = False
        if guild_id in self.temp_channels and channel_id in self.temp_channels[guild_id]:
            is_owner = self.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id
        
        if not is_owner and not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ You don't own this channel or have Manage Channels permission.", ephemeral=True)
            return
        
        try:
            old_name = target_channel.name
            await target_channel.edit(name=new_name)
            
            embed = discord.Embed(
                title="✏️ Channel Renamed",
                description=f"`{old_name}` → `{new_name}`",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Rename Failed",
                description=f"Error: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # -------- INCREASE USER LIMIT --------
    @voice_group.command(name="increase", description="⬆️ Increase the user limit")
    @app_commands.describe(
        amount="Amount to increase by (default 1)",
        channel="Voice channel (optional, uses current if in VC)"
    )
    async def increase_limit(
        self,
        interaction: discord.Interaction,
        amount: int = 1,
        channel: Optional[discord.VoiceChannel] = None
    ):
        """Increase user limit of a voice channel"""
        await interaction.response.defer(ephemeral=True)
        
        if channel:
            target_channel = channel
        elif interaction.user.voice:
            target_channel = interaction.user.voice.channel
        else:
            await interaction.followup.send("❌ You must be in a voice channel or specify one.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        channel_id = str(target_channel.id)
        
        is_owner = False
        if guild_id in self.temp_channels and channel_id in self.temp_channels[guild_id]:
            is_owner = self.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id
        
        if not is_owner and not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ You don't own this channel or have Manage Channels permission.", ephemeral=True)
            return
        
        try:
            current_limit = target_channel.user_limit if target_channel.user_limit else 0
            new_limit = current_limit + amount if current_limit > 0 else amount
            
            await target_channel.edit(user_limit=new_limit)
            
            embed = discord.Embed(
                title="⬆️ User Limit Increased",
                description=f"{current_limit if current_limit > 0 else '∞'} → {new_limit}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Increase Failed",
                description=f"Error: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # -------- DECREASE USER LIMIT --------
    @voice_group.command(name="decrease", description="⬇️ Decrease the user limit")
    @app_commands.describe(
        amount="Amount to decrease by (default 1)",
        channel="Voice channel (optional, uses current if in VC)"
    )
    async def decrease_limit(
        self,
        interaction: discord.Interaction,
        amount: int = 1,
        channel: Optional[discord.VoiceChannel] = None
    ):
        """Decrease user limit of a voice channel"""
        await interaction.response.defer(ephemeral=True)
        
        if channel:
            target_channel = channel
        elif interaction.user.voice:
            target_channel = interaction.user.voice.channel
        else:
            await interaction.followup.send("❌ You must be in a voice channel or specify one.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        channel_id = str(target_channel.id)
        
        is_owner = False
        if guild_id in self.temp_channels and channel_id in self.temp_channels[guild_id]:
            is_owner = self.temp_channels[guild_id][channel_id].get("owner") == interaction.user.id
        
        if not is_owner and not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ You don't own this channel or have Manage Channels permission.", ephemeral=True)
            return
        
        try:
            current_limit = target_channel.user_limit if target_channel.user_limit else 0
            new_limit = max(1, current_limit - amount) if current_limit > 0 else max(1, amount)
            
            await target_channel.edit(user_limit=new_limit)
            
            embed = discord.Embed(
                title="⬇️ User Limit Decreased",
                description=f"{current_limit if current_limit > 0 else '∞'} → {new_limit}",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Decrease Failed",
                description=f"Error: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # -------- VOICE INTERFACE SETUP --------
    class VoiceInterfaceView(discord.ui.View):
        """Interactive voice interface with buttons"""
        
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog
        
        @discord.ui.button(label="📊 List Channels", style=discord.ButtonStyle.blurple, custom_id="vc_list")
        async def list_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """List all voice channels"""
            await interaction.response.defer(ephemeral=True)
            
            guild = interaction.guild
            voice_channels = [ch for ch in guild.channels if isinstance(ch, discord.VoiceChannel)]
            
            if not voice_channels:
                await interaction.followup.send("❌ No voice channels found.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🎙️ Voice Channels",
                color=discord.Color.blue(),
                description=f"Total: {len(voice_channels)}"
            )
            
            for vc in sorted(voice_channels, key=lambda x: x.position):
                member_count = len(vc.members)
                user_limit = vc.user_limit if vc.user_limit else "∞"
                
                guild_id = str(guild.id)
                is_temp = guild_id in self.cog.temp_channels and str(vc.id) in self.cog.temp_channels[guild_id]
                temp_badge = "🌀" if is_temp else ""
                
                embed.add_field(
                    name=f"{temp_badge} {vc.name}",
                    value=f"Members: {member_count}/{user_limit}\nBitrate: {vc.bitrate // 1000} kbps",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        @discord.ui.button(label="➕ Create Temp VC", style=discord.ButtonStyle.green, custom_id="vc_create_modal")
        async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """Show create channel modal"""
            await interaction.response.send_modal(self.cog.CreateVCModal(self.cog))
        
        @discord.ui.button(label="🔒 Lock Channel", style=discord.ButtonStyle.danger, custom_id="vc_lock_modal")
        async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """Show lock channel modal"""
            await interaction.response.send_modal(self.cog.LockVCModal(self.cog))
        
        @discord.ui.button(label="❌ Delete Channel", style=discord.ButtonStyle.red, custom_id="vc_delete_modal")
        async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """Show delete channel modal"""
            await interaction.response.send_modal(self.cog.DeleteVCModal(self.cog))
    
    # -------- MODAL FORMS --------
    class CreateVCModal(discord.ui.Modal, title="Create Voice Channel"):
        """Modal for creating voice channels"""
        
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
        
        name = discord.ui.TextInput(
            label="Channel Name",
            placeholder="Enter channel name",
            max_length=100
        )
        
        limit = discord.ui.TextInput(
            label="User Limit (0 = unlimited)",
            placeholder="0",
            max_length=3,
            default="0"
        )
        
        bitrate = discord.ui.TextInput(
            label="Bitrate (kbps)",
            placeholder="64",
            max_length=3,
            default="64"
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
            try:
                name_val = self.name.value
                limit_val = int(self.limit.value) if self.limit.value else 0
                bitrate_val = int(self.bitrate.value) if self.bitrate.value else 64
                
                guild = interaction.guild
                parent_category = interaction.channel.category if hasattr(interaction.channel, 'category') else None
                
                voice_channel = await guild.create_voice_channel(
                    name=name_val,
                    user_limit=limit_val if limit_val > 0 else None,
                    bitrate=min(bitrate_val * 1000, guild.bitrate_limit) if bitrate_val else 64000,
                    category=parent_category
                )
                
                guild_id = str(guild.id)
                if guild_id not in self.cog.temp_channels:
                    self.cog.temp_channels[guild_id] = {}
                
                self.cog.temp_channels[guild_id][str(voice_channel.id)] = {
                    "created_at": datetime.now().isoformat(),
                    "creator": interaction.user.id,
                    "temporary": True
                }
                
                embed = discord.Embed(
                    title="✅ Channel Created",
                    description=f"{voice_channel.mention}",
                    color=discord.Color.green()
                )
                embed.set_footer(text="Auto-deletes when empty after 5 minutes")
                await interaction.followup.send(embed=embed, ephemeral=True)
            
            except ValueError:
                await interaction.followup.send("❌ Invalid input. Check your numbers.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    class LockVCModal(discord.ui.Modal, title="Lock Voice Channel"):
        """Modal for locking voice channels"""
        
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
        
        channel_id = discord.ui.TextInput(
            label="Channel ID",
            placeholder="Paste voice channel ID",
            max_length=25
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
            try:
                channel = interaction.guild.get_channel(int(self.channel_id.value))
                
                if not channel or not isinstance(channel, discord.VoiceChannel):
                    await interaction.followup.send("❌ Invalid voice channel.", ephemeral=True)
                    return
                
                if not interaction.user.guild_permissions.manage_channels:
                    await interaction.followup.send("❌ You need Manage Channels permission.", ephemeral=True)
                    return
                
                everyone_role = interaction.guild.default_role
                await channel.set_permissions(everyone_role, connect=False)
                
                embed = discord.Embed(
                    title="🔒 Channel Locked",
                    description=f"{channel.mention} is now locked",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
            except ValueError:
                await interaction.followup.send("❌ Invalid channel ID.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    class DeleteVCModal(discord.ui.Modal, title="Delete Voice Channel"):
        """Modal for deleting voice channels"""
        
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
        
        channel_id = discord.ui.TextInput(
            label="Channel ID",
            placeholder="Paste voice channel ID",
            max_length=25
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
            try:
                channel = interaction.guild.get_channel(int(self.channel_id.value))
                
                if not channel or not isinstance(channel, discord.VoiceChannel):
                    await interaction.followup.send("❌ Invalid voice channel.", ephemeral=True)
                    return
                
                if not interaction.user.guild_permissions.manage_channels:
                    await interaction.followup.send("❌ You need Manage Channels permission.", ephemeral=True)
                    return
                
                channel_name = channel.name
                await channel.delete()
                
                guild_id = str(interaction.guild.id)
                if guild_id in self.cog.temp_channels and str(channel.id) in self.cog.temp_channels[guild_id]:
                    del self.cog.temp_channels[guild_id][str(channel.id)]
                
                embed = discord.Embed(
                    title="✅ Channel Deleted",
                    description=f"`{channel_name}` has been deleted",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
            except ValueError:
                await interaction.followup.send("❌ Invalid channel ID.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    # -------- VOICE INTERFACE SETUP --------
    @voice_group.command(name="setup", description="Setup voice interface in this channel")
    async def setup_panel(self, interaction: discord.Interaction):
        """Setup voice interface with buttons"""
        await interaction.response.defer(ephemeral=True)
        
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.followup.send("❌ You need Manage Server permission.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        
        if guild_id not in self.voice_settings:
            self.voice_settings[guild_id] = {}
        
        self.voice_settings[guild_id]["interface"] = channel_id
        self.save_config()
        
        # Send interface embed with buttons
        embed = discord.Embed(
            title="🎙️ Voice Interface",
            description="Use the buttons below to manage voice channels",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="📊 List Channels",
            value="View all voice channels and member counts",
            inline=False
        )
        embed.add_field(
            name="➕ Create Temp VC",
            value="Create a temporary voice channel (auto-deletes when empty)",
            inline=False
        )
        embed.add_field(
            name="🔒 Lock Channel",
            value="Lock a voice channel (prevent new joins)",
            inline=False
        )
        embed.add_field(
            name="❌ Delete Channel",
            value="Delete a voice channel",
            inline=False
        )
        embed.set_footer(text="Click the buttons below to perform actions")
        
        await interaction.channel.send(embed=embed, view=self.VoiceInterfaceView(self))
        
        confirm_embed = discord.Embed(
            title="✅ Voice Interface Setup",
            description=f"Interface activated in {interaction.channel.mention}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)
    
    # -------- AUTO-CLEANUP TASK --------
    @tasks.loop(minutes=1)
    async def cleanup_task(self):
        """Automatically delete empty temporary voice channels"""
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
                        
                        # Check if channel is empty
                        if len(channel.members) == 0:
                            # Check if channel has been empty for 5+ minutes
                            creation_time = datetime.fromisoformat(channel_info["created_at"])
                            if datetime.now() - creation_time > timedelta(minutes=5):
                                try:
                                    await channel.delete()
                                    channels_to_remove.append(channel_id)
                                except:
                                    pass
                    except:
                        pass
                
                # Remove tracked channels
                for channel_id in channels_to_remove:
                    if channel_id in channels:
                        del channels[channel_id]
            
            # Remove guilds with no tracked channels
            for guild_id in guilds_to_clean:
                if guild_id in self.temp_channels:
                    del self.temp_channels[guild_id]
        
        except Exception as e:
            print(f"Error in cleanup task: {e}")
    
    @cleanup_task.before_loop
    async def before_cleanup(self):
        """Wait for bot to be ready before cleanup"""
        await self.bot.wait_until_ready()
    
    # -------- VOICE STATE UPDATE EVENT --------
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        """Handle voice state changes"""
        # User joined a voice channel
        if before.channel is None and after.channel is not None:
            guild_id = str(member.guild.id)
            if guild_id in self.voice_settings and "welcome_msg" in self.voice_settings[guild_id]:
                # Log user join if configured
                pass
        
        # User left a voice channel
        if before.channel is not None and after.channel is None:
            channel = before.channel
            guild_id = str(member.guild.id)
            
            # Check if it's a temporary channel that should be deleted
            if guild_id in self.temp_channels and str(channel.id) in self.temp_channels[guild_id]:
                # If empty, mark for deletion by cleanup task
                if len(channel.members) == 0:
                    pass  # Cleanup task will handle it

async def setup(bot: commands.Bot):
    """Setup the Voice Interface cog"""
    await bot.add_cog(VoiceInterface(bot))
