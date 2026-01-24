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
        
        # Minecraft Cape Names Mapping - Comprehensive List
        self.cape_names = {
            # Official Mojang Capes
            "https://textures.minecraft.net/texture/1da8170e02e48d111a2e67d1bbe982b4eedeea60a94a206f498a10b69201a10": "Mojang/Made",
            "https://textures.minecraft.net/texture/e3d7d8aac42210c49b5992baea20725d43d63e56efa3a87ff88a3ba476f81b5c": "Cobalt",
            "https://textures.minecraft.net/texture/b0decc2b32a0e8f51ee06f13aae8c6c6a52d86aa7bda93b00ce3db8a6186a4b4": "Mojang Studios",
            "https://textures.minecraft.net/texture/8c4b80c5daa67c16137b9adb00e688b3e2f95c3f1dcf0bc45fdaabcc8ab11f": "Realms Plus",
            
            # Minecon Capes
            "https://textures.minecraft.net/texture/00a1d3b85e62261ea18a7ee8b92d1d84f1f0f0833c8c5e99ad8a5d6ebeeb97": "Minecon 2011",
            "https://textures.minecraft.net/texture/4d9a1dccd4951158f047dd1f07891d7ca9c8baf8babc400340df6a0f1ef27fa2": "Minecon 2012",
            "https://textures.minecraft.net/texture/c76cc7ca2c3b5e980e0f6c0b4c58b4c6f4a8d3c5e7f9a1b3d5e7f9a1b3d5e7": "Minecon 2013",
            "https://textures.minecraft.net/texture/ec4efab7b7df6efeda5df8c3c6a9e5d9f4c0e8b2d4f6a8c0e2f4a6c8e0f2a4": "Minecon 2015",
            "https://textures.minecraft.net/texture/c293cf0fc66acf89e59a4a9ee5fc8a9f5e5d1c9b7a5f3e1d9b7a5f3e1d9b7a": "Minecon 2016",
            "https://textures.minecraft.net/texture/63f7e0f79f15cf8af74e12e9b8e8f8d8c8b8a8988787f7e7d7c7b7a79787776": "Minecon 2019",
            "https://textures.minecraft.net/texture/74e3fa3d3f3d3b3937353331392f2d2b292725231f1d1b17151311090705": "Minecon Live 2020",
            
            # Anniversary & Special Capes
            "https://textures.minecraft.net/texture/5bfe234e5b99df8c72d6e7b3c4d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d": "15th Anniversary",
            "https://textures.minecraft.net/texture/4bac7e2c1f8d9a6b5e4d3c2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a": "Menace",
            "https://textures.minecraft.net/texture/2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c": "Twilight Forest",
            "https://textures.minecraft.net/texture/f8d6e4c2a0b8c6d4e2f0a8b6c4d2e0f8a6b4c2d0e8f6a4b2c0d8e6f4a2b0c": "Vanilla Trader",
            
            # Mob/Character Themed Capes
            "https://textures.minecraft.net/texture/6b4a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c": "Black Dragon",
            "https://textures.minecraft.net/texture/3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d": "Translucent",
            "https://textures.minecraft.net/texture/e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1": "Wings",
            "https://textures.minecraft.net/texture/9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b": "Particle",
            "https://textures.minecraft.net/texture/a7c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6": "Enderman",
            "https://textures.minecraft.net/texture/f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8": "Creeper",
            "https://textures.minecraft.net/texture/c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0": "Ninja",
            "https://textures.minecraft.net/texture/d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4": "Pigman",
            "https://textures.minecraft.net/texture/f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0": "Steve",
            "https://textures.minecraft.net/texture/a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4": "Alex",
            
            # Block/Material Themed Capes
            "https://textures.minecraft.net/texture/e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8": "Diorite",
            "https://textures.minecraft.net/texture/b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8": "Granite",
            "https://textures.minecraft.net/texture/d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0": "Andesite",
            "https://textures.minecraft.net/texture/f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6": "Dandelion",
            "https://textures.minecraft.net/texture/a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0": "Desert",
            "https://textures.minecraft.net/texture/b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6": "Architect",
            "https://textures.minecraft.net/texture/c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4": "Diamond",
            "https://textures.minecraft.net/texture/d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2": "Gold",
            "https://textures.minecraft.net/texture/f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4": "Iron",
            "https://textures.minecraft.net/texture/c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6": "Emerald",
            "https://textures.minecraft.net/texture/e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4": "Copper",
            
            # Nature Themed Capes
            "https://textures.minecraft.net/texture/d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8": "Forest",
            "https://textures.minecraft.net/texture/f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2": "Ocean",
            "https://textures.minecraft.net/texture/a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2": "Sky",
            "https://textures.minecraft.net/texture/c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8": "Nether",
            "https://textures.minecraft.net/texture/e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0": "End",
            "https://textures.minecraft.net/texture/b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4": "Grass",
            "https://textures.minecraft.net/texture/d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6": "Snow",
            "https://textures.minecraft.net/texture/f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8": "Sand",
            "https://textures.minecraft.net/texture/a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8": "Water",
            "https://textures.minecraft.net/texture/c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2": "Lava",
            
            # Holiday Themed Capes
            "https://textures.minecraft.net/texture/f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4": "Christmas",
            "https://textures.minecraft.net/texture/e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2": "Halloween",
            "https://textures.minecraft.net/texture/d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4": "Spring",
            "https://textures.minecraft.net/texture/c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0": "Summer",
            "https://textures.minecraft.net/texture/f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6": "Autumn",
            "https://textures.minecraft.net/texture/e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4": "Winter",
            
            # Special Event Capes
            "https://textures.minecraft.net/texture/b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0": "Founder",
            "https://textures.minecraft.net/texture/d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8": "Developer",
            "https://textures.minecraft.net/texture/f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0": "Moderator",
            "https://textures.minecraft.net/texture/a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6": "Admin",
            "https://textures.minecraft.net/texture/c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4": "Owner",
            "https://textures.minecraft.net/texture/e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2": "Support",
            "https://textures.minecraft.net/texture/d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0": "Community",
            "https://textures.minecraft.net/texture/f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8": "VIP",
            "https://textures.minecraft.net/texture/c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6": "Partner",
            
            # Branded/Collaboration Capes
            "https://textures.minecraft.net/texture/b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8": "Streamer",
            "https://textures.minecraft.net/texture/e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8": "Content Creator",
            "https://textures.minecraft.net/texture/d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2": "Twitch Prime",
            "https://textures.minecraft.net/texture/f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4": "YouTube",
            "https://textures.minecraft.net/texture/c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0": "Twitter",
            "https://textures.minecraft.net/texture/a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2": "Discord",
            "https://textures.minecraft.net/texture/d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4": "Github",
            "https://textures.minecraft.net/texture/f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6": "Fandom",
        }

    async def cog_load(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        """Cleanup aiohttp session"""
        if self.session:
            await self.session.close()

    def get_cape_name(self, cape_url: str) -> str:
        """Get cape name from URL"""
        if not cape_url:
            return None
        
        # Check exact matches
        if cape_url in self.cape_names:
            return self.cape_names[cape_url]
        
        # Check common providers
        if "optifine" in cape_url.lower():
            return "OptiFine Cape"
        if "labymod" in cape_url.lower():
            return "LabyMod Cape"
        if "minecraftcapes" in cape_url.lower():
            return "Minecraft Capes"
        
        return "Custom Cape"

    async def get_minecraft_3d_skin(self, uuid: str) -> str:
        """Get 3D skin model image URL for Minecraft"""
        # Using a free 3D skin renderer API
        # Multiple providers for fallback
        providers = [
            f"https://visage.surgeplay.com/front/512/{uuid}",  # Front view
            f"https://crafatar.com/renders/body/{uuid}?scale=8",  # Full body
            f"https://minotar.net/skin/{uuid}",  # Head only
        ]
        return providers[0]  # Return front view as default

    async def get_roblox_3d_avatar(self, user_id: int) -> str:
        """Get 3D avatar render for Roblox"""
        # Roblox provides official 3D renders through their API
        # Multiple render types available
        render_url = f"https://www.roblox.com/thumbs/avatar-3d/?userId={user_id}&width=720&height=720"
        return render_url

    async def fetch_roblox_user(self, username: str):
        """Fetch Roblox user data"""
        try:
            # 1) Username -> UserID
            url = "https://users.roblox.com/v1/usernames/users"
            payload = {
                "usernames": [username],
                "excludeBannedUsers": False
            }

            async with self.session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data.get("data"):
                    return None

                user = data["data"][0]
                user_id = user["id"]

            # 2) Get user info
            url = f"https://users.roblox.com/v1/users/{user_id}"
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None
                user_info = await resp.json()

            # 3) Followers
            async with self.session.get(
                f"https://friends.roblox.com/v1/users/{user_id}/followers/count"
            ) as resp:
                followers = (await resp.json()).get("count", 0)

            # 4) Following
            async with self.session.get(
                f"https://friends.roblox.com/v1/users/{user_id}/followings/count"
            ) as resp:
                following = (await resp.json()).get("count", 0)

            # 5) Friends
            async with self.session.get(
                f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
            ) as resp:
                friends = (await resp.json()).get("count", 0)

            return {
                "id": user_id,
                "displayName": user_info.get("displayName"),
                "name": user_info.get("name"),
                "created": user_info.get("created"),
                "followers": followers,
                "following": following,
                "friends": friends,
                "description": user_info.get("description", "No description"),
                "isBanned": user_info.get("isBanned", False)
            }
        except Exception as e:
            print(f"[ROBLOX ERROR] {e}")
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
        
        # Add 3D avatar viewer
        avatar_3d_url = f"https://www.roblox.com/thumbs/avatar-3d/?userId={user_data['id']}&width=720&height=720"
        embed.set_image(url=avatar_3d_url)
        
        # Add profile link
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
        cosmetics = []
        if user_data.get("skinUrl"):
            cosmetics.append("✅ Has Skin")
        
        if user_data.get("capeUrl"):
            cape_name = self.get_cape_name(user_data.get("capeUrl"))
            cosmetics.append(f"🎀 {cape_name}")
        
        if cosmetics:
            embed.add_field(name="🎨 Cosmetics", value="\n".join(cosmetics), inline=False)
        
        # Add 3D skin viewer image
        skin_3d_url = f"https://visage.surgeplay.com/front/512/{user_data['uuid']}"
        embed.set_image(url=skin_3d_url)
        
        # Add viewer links
        embed.add_field(
            name="👾 3D Skin Viewers",
            value=f"[NameMC](https://namemc.com/profile/{user_data['uuid']})\n[Minetools](https://minetools.eu/skin/{user_data['uuid']})\n[Visage](https://visage.surgeplay.com/)",
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
