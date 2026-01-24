import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from typing import Literal, Optional
from datetime import datetime
import io
from PIL import Image
import base64

class GameProfilePuller(commands.Cog):
    """Pull profiles from Roblox and Minecraft"""

    def __init__(self, bot):
        self.bot = bot
        self.session = None

    async def cog_load(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        """Cleanup aiohttp session"""
        if self.session:
            await self.session.close()

    async def fetch_roblox_user(self, username: str):
        """Fetch Roblox user data"""
        try:
            # Get user ID from username
            url = f"https://users.roblox.com/v1/users/search"
            params = {"keyword": username, "limit": 1}
            
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data.get("data"):
                    return None
                
                user = data["data"][0]
                user_id = user["id"]
                
            # Get detailed user info
            url = f"https://users.roblox.com/v1/users/{user_id}"
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None
                user_info = await resp.json()
            
            # Get follower info
            url = f"https://friends.roblox.com/v1/users/{user_id}/followers"
            async with self.session.get(url) as resp:
                followers_data = await resp.json() if resp.status == 200 else {"totalFollowerCount": 0}
            
            # Get following info
            url = f"https://friends.roblox.com/v1/users/{user_id}/followings"
            async with self.session.get(url) as resp:
                following_data = await resp.json() if resp.status == 200 else {"totalFollowingCount": 0}
            
            # Get connections/friends count
            url = f"https://friends.roblox.com/v1/users/{user_id}/friends"
            async with self.session.get(url) as resp:
                friends_data = await resp.json() if resp.status == 200 else {"totalFriendCount": 0}
            
            return {
                "id": user_id,
                "displayName": user_info.get("displayName"),
                "name": user_info.get("name"),
                "created": user_info.get("created"),
                "followers": followers_data.get("totalFollowerCount", 0),
                "following": following_data.get("totalFollowingCount", 0),
                "friends": friends_data.get("totalFriendCount", 0),
                "description": user_info.get("description", "No description"),
                "isBanned": user_info.get("isBanned", False)
            }
        except Exception as e:
            print(f"Error fetching Roblox user: {e}")
            return None

    async def fetch_minecraft_user(self, username: str):
        """Fetch Minecraft user data"""
        try:
            # Get UUID from username
            url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None
                uuid_data = await resp.json()
                uuid = uuid_data.get("id")
            
            # Get player profile with skin/cape data
            url = f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None
                profile_data = await resp.json()
            
            # Get name history
            url = f"https://api.mojang.com/user/profiles/{uuid}/names"
            async with self.session.get(url) as resp:
                name_history = await resp.json() if resp.status == 200 else []
            
            # Parse textures
            textures = {}
            for prop in profile_data.get("properties", []):
                if prop.get("name") == "textures":
                    try:
                        import base64
                        import json
                        decoded = base64.b64decode(prop.get("value", "")).decode()
                        textures = json.loads(decoded).get("textures", {})
                    except:
                        pass
            
            return {
                "uuid": uuid,
                "name": username,
                "nameHistory": name_history,
                "skinUrl": textures.get("SKIN", {}).get("url", None),
                "capeUrl": textures.get("CAPE", {}).get("url", None),
                "skinModel": textures.get("SKIN", {}).get("metadata", {}).get("model", "classic")
            }
        except Exception as e:
            print(f"Error fetching Minecraft user: {e}")
            return None

    def create_roblox_embed(self, user_data: dict, username: str) -> discord.Embed:
        """Create Roblox profile embed"""
        if not user_data:
            return discord.Embed(
                title="❌ Roblox Profile",
                description=f"Could not find user: {username}",
                color=discord.Color.red()
            )
        
        created_date = datetime.fromisoformat(user_data["created"].replace("Z", "+00:00"))
        
        embed = discord.Embed(
            title=f"👤 {user_data['displayName']}",
            description=user_data.get("description", "No description"),
            color=discord.Color.from_rgb(0, 100, 200),
            url=f"https://www.roblox.com/users/{user_data['id']}/profile"
        )
        
        embed.add_field(name="👤 Username", value=user_data["name"], inline=True)
        embed.add_field(name="🆔 User ID", value=user_data["id"], inline=True)
        embed.add_field(name="📅 Joined", value=created_date.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="👥 Followers", value=f"{user_data['followers']:,}", inline=True)
        embed.add_field(name="➡️ Following", value=f"{user_data['following']:,}", inline=True)
        embed.add_field(name="🤝 Friends", value=f"{user_data['friends']:,}", inline=True)
        
        if user_data.get("isBanned"):
            embed.add_field(name="⚠️ Status", value="🚫 **BANNED**", inline=False)
        
        # Add 3D avatar viewer link
        embed.add_field(
            name="👾 3D Avatar Viewer",
            value=f"[View on Roblox](https://www.roblox.com/users/{user_data['id']}/profile)",
            inline=False
        )
        
        embed.set_thumbnail(url=f"https://www.roblox.com/bust-thumbnails/assets/?userId={user_data['id']}&width=420&height=420&format=png")
        embed.set_footer(text="Roblox Profile | Powered by Roblox API")
        
        return embed

    def create_minecraft_embed(self, user_data: dict, username: str) -> discord.Embed:
        """Create Minecraft profile embed"""
        if not user_data:
            return discord.Embed(
                title="❌ Minecraft Profile",
                description=f"Could not find user: {username}",
                color=discord.Color.red()
            )
        
        embed = discord.Embed(
            title=f"⛏️ {user_data['name']}",
            color=discord.Color.from_rgb(0, 200, 0),
            url=f"https://namemc.com/profile/{user_data['uuid']}"
        )
        
        embed.add_field(name="👤 Username", value=user_data["name"], inline=True)
        embed.add_field(name="🆔 UUID", value=f"`{user_data['uuid']}`", inline=True)
        embed.add_field(name="🎮 Skin Model", value=user_data.get("skinModel", "classic").capitalize(), inline=True)
        
        # Name history
        if user_data.get("nameHistory"):
            names = []
            for entry in user_data["nameHistory"]:
                if "changedToAt" in entry:
                    names.append(f"{entry['name']} - {datetime.fromtimestamp(entry['changedToAt']/1000).strftime('%Y-%m-%d')}")
                else:
                    names.append(f"{entry['name']} - Original")
            
            if len(names) > 5:
                embed.add_field(name="📜 Name History", value="\n".join(names[:5]) + f"\n... and {len(names)-5} more", inline=False)
            else:
                embed.add_field(name="📜 Name History", value="\n".join(names), inline=False)
        
        # Skin and Cape info
        skin_info = []
        if user_data.get("skinUrl"):
            skin_info.append("✅ Has Skin")
        if user_data.get("capeUrl"):
            skin_info.append("✅ Has Cape")
        
        if skin_info:
            embed.add_field(name="🎨 Cosmetics", value=", ".join(skin_info), inline=False)
        
        # Add 3D skin viewer link
        embed.add_field(
            name="👾 3D Skin Viewer",
            value=f"[View Skin](https://namemc.com/profile/{user_data['uuid']})\n[Minetools Viewer](https://minetools.eu/skin/{user_data['uuid']})",
            inline=False
        )
        
        # Add avatar
        embed.set_thumbnail(url=f"https://crafatar.com/avatars/{user_data['uuid']}?size=256")
        embed.set_footer(text="Minecraft Profile | Powered by Mojang API")
        
        return embed

    gpp = app_commands.Group(name="gpp", description="🎮 Game Profile Puller")

    @gpp.command(name="roblox", description="Get Roblox profile information")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(username="Roblox username to look up")
    async def gpp_roblox(self, interaction: discord.Interaction, username: str):
        """Get Roblox profile information"""
        await interaction.response.defer()
        
        try:
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession()
            
            user_data = await self.fetch_roblox_user(username)
            embed = self.create_roblox_embed(user_data, username)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to fetch Roblox profile: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)

    @gpp.command(name="minecraft", description="Get Minecraft profile information")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(username="Minecraft username to look up")
    async def gpp_minecraft(self, interaction: discord.Interaction, username: str):
        """Get Minecraft profile information"""
        await interaction.response.defer()
        
        try:
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession()
            
            user_data = await self.fetch_minecraft_user(username)
            embed = self.create_minecraft_embed(user_data, username)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to fetch Minecraft profile: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)

async def setup(bot):
    """Required function to load the cog"""
    cog = GameProfilePuller(bot)
    await bot.add_cog(cog)
    await cog.cog_load()
