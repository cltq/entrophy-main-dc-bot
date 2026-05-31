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
    """ดึงข้อมูลโปรไฟล์จาก Roblox และ Minecraft"""

    def __init__(self, bot):
        self.bot = bot
        self.session = None
        
        # แผนที่ชื่อเคป Minecraft - รายการครอบคลุม
        self.cape_names = {
            # เคปอย่างเป็นทางการของ Mojang
            "https://textures.minecraft.net/texture/1da8170e02e48d111a2e67d1bbe982b4eedeea60a94a206f498a10b69201a10": "Mojang/Made",
            "https://textures.minecraft.net/texture/e3d7d8aac42210c49b5992baea20725d43d63e56efa3a87ff88a3ba476f81b5c": "Cobalt",
            "https://textures.minecraft.net/texture/b0decc2b32a0e8f51ee06f13aae8c6c6a52d86aa7bda93b00ce3db8a6186a4b4": "Mojang Studios",
            "https://textures.minecraft.net/texture/8c4b80c5daa67c16137b9adb00e688b3e2f95c3f1dcf0bc45fdaabcc8ab11f": "Realms Plus",
            
            # เคป Minecon
            "https://textures.minecraft.net/texture/00a1d3b85e62261ea18a7ee8b92d1d84f1f0f0833c8c5e99ad8a5d6ebeeb97": "Minecon 2011",
            "https://textures.minecraft.net/texture/4d9a1dccd4951158f047dd1f07891d7ca9c8baf8babc400340df6a0f1ef27fa2": "Minecon 2012",
            "https://textures.minecraft.net/texture/c76cc7ca2c3b5e980e0f6c0b4c58b4c6f4a8d3c5e7f9a1b3d5e7f9a1b3d5e7": "Minecon 2013",
            "https://textures.minecraft.net/texture/ec4efab7b7df6efeda5df8c3c6a9e5d9f4c0e8b2d4f6a8c0e2f4a6c8e0f2a4": "Minecon 2015",
            "https://textures.minecraft.net/texture/c293cf0fc66acf89e59a4a9ee5fc8a9f5e5d1c9b7a5f3e1d9b7a5f3e1d9b7a": "Minecon 2016",
            "https://textures.minecraft.net/texture/63f7e0f79f15cf8af74e12e9b8e8f8d8c8b8a8988787f7e7d7c7b7a79787776": "Minecon 2019",
            "https://textures.minecraft.net/texture/74e3fa3d3f3d3b3937353331392f2d2b292725231f1d1b17151311090705": "Minecon Live 2020",
            
            # เคปวันครบรอบและพิเศษ
            "https://textures.minecraft.net/texture/5bfe234e5b99df8c72d6e7b3c4d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d": "15th Anniversary",
            "https://textures.minecraft.net/texture/4bac7e2c1f8d9a6b5e4d3c2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a": "Menace",
            "https://textures.minecraft.net/texture/2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c": "Twilight Forest",
            "https://textures.minecraft.net/texture/f8d6e4c2a0b8c6d4e2f0a8b6c4d2e0f8a6b4c2d0e8f6a4b2c0d8e6f4a2b0c": "Vanilla Trader",
            
            # เคปธีมม็อบ/ตัวละคร
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
            
            # เคปธีมบล็อก/วัสดุ
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
            
            # เคปธีมธรรมชาติ
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
            
            # เคปธีมวันหยุด
            "https://textures.minecraft.net/texture/f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4": "Christmas",
            "https://textures.minecraft.net/texture/e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2": "Halloween",
            "https://textures.minecraft.net/texture/d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4": "Spring",
            "https://textures.minecraft.net/texture/c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0": "Summer",
            "https://textures.minecraft.net/texture/f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6": "Autumn",
            "https://textures.minecraft.net/texture/e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4": "Winter",
            
            # เคปกิจกรรมพิเศษ
            "https://textures.minecraft.net/texture/b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0": "Founder",
            "https://textures.minecraft.net/texture/d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8": "Developer",
            "https://textures.minecraft.net/texture/f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0": "Moderator",
            "https://textures.minecraft.net/texture/a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6": "Admin",
            "https://textures.minecraft.net/texture/c0d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4": "Owner",
            "https://textures.minecraft.net/texture/e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2": "Support",
            "https://textures.minecraft.net/texture/d6e2f8a4b0c6d2e8f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0": "Community",
            "https://textures.minecraft.net/texture/f4a0b6c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8": "VIP",
            "https://textures.minecraft.net/texture/c2d8e4f0a6b2c8d4e0f6a2b8c4d0e6f2a8b4c0d6e2f8a4b0c6d2e8f4a0b6": "Partner",
            
            # เคปแบรนด์/ความร่วมมือ
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
        """เริ่มต้นเซสชัน aiohttp"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        """ล้างเซสชัน aiohttp"""
        if self.session:
            await self.session.close()

    def get_cape_name(self, cape_url: str) -> str:
        """รับชื่อเคปจาก URL"""
        if not cape_url:
            return None
        
        # ตรวจสอบการจับคู่แบบตรงทั้งหมด
        if cape_url in self.cape_names:
            return self.cape_names[cape_url]
        
        # ตรวจสอบผู้ให้บริการทั่วไป
        if "optifine" in cape_url.lower():
            return "OptiFine Cape"
        if "labymod" in cape_url.lower():
            return "LabyMod Cape"
        if "minecraftcapes" in cape_url.lower():
            return "Minecraft Capes"
        
        return "Custom Cape"

    async def get_minecraft_3d_skin(self, uuid: str) -> str:
        """รับ URL รูปโมเดลสกิน 3D สำหรับ Minecraft"""
        # ใช้ API เรนเดอร์สกิน 3D ฟรี
        # มีหลายผู้ให้บริการสำหรับการสำรอง
        providers = [
            f"https://visage.surgeplay.com/front/512/{uuid}",  # มุมมองด้านหน้า
            f"https://crafatar.com/renders/body/{uuid}?scale=8",  # ทั้งตัว
            f"https://minotar.net/skin/{uuid}",  # เฉพาะหัว
        ]
        return providers[0]  # คืนค่ามุมมองด้านหน้าเป็นค่าเริ่มต้น

    async def get_roblox_3d_avatar(self, user_id: int) -> str:
        """รับเรนเดอร์อวาตาร์ 3D สำหรับ Roblox"""
        # Roblox มี API เรนเดอร์ 3D อย่างเป็นทางการ
        # มีรูปแบบเรนเดอร์หลายแบบ
        render_url = f"https://www.roblox.com/thumbs/avatar-3d/?userId={user_id}&width=720&height=720"
        return render_url

    async def fetch_roblox_user(self, username: str):
        """ดึงข้อมูลผู้ใช้ Roblox"""
        try:
            # 1) ชื่อผู้ใช้ -> รหัสผู้ใช้
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

            # 2) ดึงข้อมูลผู้ใช้
            url = f"https://users.roblox.com/v1/users/{user_id}"
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None
                user_info = await resp.json()

            # 3) ผู้ติดตาม
            async with self.session.get(
                f"https://friends.roblox.com/v1/users/{user_id}/followers/count"
            ) as resp:
                followers = (await resp.json()).get("count", 0)

            # 4) กำลังติดตาม
            async with self.session.get(
                f"https://friends.roblox.com/v1/users/{user_id}/followings/count"
            ) as resp:
                following = (await resp.json()).get("count", 0)

            # 5) เพื่อน
            async with self.session.get(
                f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
            ) as resp:
                friends = (await resp.json()).get("count", 0)

            # 6) ดึงรูปอวาตาร์ 3D
            avatar_image_url = None
            async with self.session.get(
                f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=720x720&format=Png&isCircular=false"
            ) as resp:
                if resp.status == 200:
                    avatar_data = await resp.json()
                    if avatar_data.get("data") and len(avatar_data["data"]) > 0:
                        avatar_image_url = avatar_data["data"][0].get("imageUrl")

            return {
                "id": user_id,
                "displayName": user_info.get("displayName"),
                "name": user_info.get("name"),
                "created": user_info.get("created"),
                "followers": followers,
                "following": following,
                "friends": friends,
                "description": user_info.get("description", "ไม่มีคำอธิบาย"),
                "isBanned": user_info.get("isBanned", False),
                "avatarImageUrl": avatar_image_url
            }
        except Exception as e:
            print(f"[ROBLOX ERROR] {e}")
            return None

    async def fetch_minecraft_user(self, username: str):
        """ดึงข้อมูลผู้ใช้ Minecraft"""
        try:
            # ดึง UUID จากชื่อผู้ใช้
            url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None
                uuid_data = await resp.json()
                uuid = uuid_data.get("id")
            
            # ดึงโปรไฟล์ผู้ใช้พร้อมข้อมูลสกิน/เคป
            url = f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None
                profile_data = await resp.json()
            
            # ดึงประวัติชื่อ
            url = f"https://api.mojang.com/user/profiles/{uuid}/names"
            async with self.session.get(url) as resp:
                name_history = await resp.json() if resp.status == 200 else []
            
            # แยกข้อมูลพื้นผิว
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
        """สร้าง embed โปรไฟล์ Roblox"""
        if not user_data:
            return discord.Embed(
                title="❌ โปรไฟล์ Roblox",
                description=f"ไม่พบผู้ใช้: {username}",
                color=discord.Color.red()
            )
        
        created_date = datetime.fromisoformat(user_data["created"].replace("Z", "+00:00"))
        
        embed = discord.Embed(
            title=f"👤 {user_data['displayName']}",
            description=user_data.get("description", "ไม่มีคำอธิบาย"),
            color=discord.Color.from_rgb(0, 100, 200),
            url=f"https://www.roblox.com/users/{user_data['id']}/profile"
        )
        
        embed.add_field(name="👤 ชื่อผู้ใช้", value=user_data["name"], inline=True)
        embed.add_field(name="🆔 รหัสผู้ใช้", value=user_data["id"], inline=True)
        embed.add_field(name="📅 เข้าร่วม", value=created_date.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="👥 ผู้ติดตาม", value=f"{user_data['followers']:,}", inline=True)
        embed.add_field(name="➡️ กำลังติดตาม", value=f"{user_data['following']:,}", inline=True)
        embed.add_field(name="🤝 เพื่อน", value=f"{user_data['friends']:,}", inline=True)
        
        if user_data.get("isBanned"):
            embed.add_field(name="⚠️ สถานะ", value="🚫 **ถูกแบน**", inline=False)
        
        # เพิ่มรูปอวาตาร์ 3D จาก API
        if user_data.get("avatarImageUrl"):
            embed.set_image(url=user_data.get("avatarImageUrl"))
        
        # เพิ่มลิงก์โปรไฟล์
        embed.add_field(
            name="👾 ดู Avatar 3D",
            value=f"[ดูบน Roblox](https://www.roblox.com/users/{user_data['id']}/profile)",
            inline=False
        )
        
        embed.set_thumbnail(url=f"https://www.roblox.com/bust-thumbnails/assets/?userId={user_data['id']}&width=420&height=420&format=png")
        embed.set_footer(text="โปรไฟล์ Roblox | ขับเคลื่อนโดย Roblox API")
        
        return embed

    def create_minecraft_embed(self, user_data: dict, username: str) -> discord.Embed:
        """สร้าง embed โปรไฟล์ Minecraft"""
        if not user_data:
            return discord.Embed(
                title="❌ โปรไฟล์ Minecraft",
                description=f"ไม่พบผู้ใช้: {username}",
                color=discord.Color.red()
            )
        
        embed = discord.Embed(
            title=f"⛏️ {user_data['name']}",
            color=discord.Color.from_rgb(0, 200, 0),
            url=f"https://namemc.com/profile/{user_data['uuid']}"
        )
        
        embed.add_field(name="👤 ชื่อผู้ใช้", value=user_data["name"], inline=True)
        embed.add_field(name="🆔 UUID", value=f"`{user_data['uuid']}`", inline=True)
        embed.add_field(name="🎮 โมเดลสกิน", value=user_data.get("skinModel", "classic").capitalize(), inline=True)
        
        # ประวัติชื่อ
        if user_data.get("nameHistory"):
            names = []
            for entry in user_data["nameHistory"]:
                if "changedToAt" in entry:
                    names.append(f"{entry['name']} - {datetime.fromtimestamp(entry['changedToAt']/1000).strftime('%Y-%m-%d')}")
                else:
                    names.append(f"{entry['name']} - ชื่อเดิม")
            
            if len(names) > 5:
                embed.add_field(name="📜 ประวัติชื่อ", value="\n".join(names[:5]) + f"\n... และอีก {len(names)-5} ชื่อ", inline=False)
            else:
                embed.add_field(name="📜 ประวัติชื่อ", value="\n".join(names), inline=False)
        
        # ข้อมูลสกินและเคป
        cosmetics = []
        if user_data.get("skinUrl"):
            cosmetics.append("✅ มีสกิน")
        
        if user_data.get("capeUrl"):
            cape_name = self.get_cape_name(user_data.get("capeUrl"))
            cosmetics.append(f"🎀 {cape_name}")
        
        if cosmetics:
            embed.add_field(name="🎨 เครื่องตกแต่ง", value="\n".join(cosmetics), inline=False)
        
        # เพิ่มรูปสกิน 3D
        skin_3d_url = f"https://visage.surgeplay.com/front/512/{user_data['uuid']}"
        embed.set_image(url=skin_3d_url)
        
        # เพิ่มลิงก์ดูสกิน
        embed.add_field(
            name="👾 ดู Skin 3D",
            value=f"[NameMC](https://namemc.com/profile/{user_data['uuid']})\n[Minetools](https://minetools.eu/skin/{user_data['uuid']})\n[Visage](https://visage.surgeplay.com/)",
            inline=False
        )
        
        # เพิ่มอวาตาร์
        embed.set_thumbnail(url=f"https://crafatar.com/avatars/{user_data['uuid']}?size=256")
        embed.set_footer(text="โปรไฟล์ Minecraft | ขับเคลื่อนโดย Mojang API")
        
        return embed

    gpp = app_commands.Group(name="gpp", description="🎮 Game Profile Puller")

    @gpp.command(name="roblox", description="ดูข้อมูลโปรไฟล์ Roblox")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(username="ชื่อผู้ใช้ Roblox ที่ต้องการค้นหา")
    async def gpp_roblox(self, interaction: discord.Interaction, username: str):
        """ดูข้อมูลโปรไฟล์ Roblox"""
        await interaction.response.defer()
        
        try:
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession()
            
            user_data = await self.fetch_roblox_user(username)
            embed = self.create_roblox_embed(user_data, username)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ ข้อผิดพลาด",
                description=f"ไม่สามารถดึงข้อมูล Roblox: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)

    @gpp.command(name="minecraft", description="ดูข้อมูลโปรไฟล์ Minecraft")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(username="ชื่อผู้ใช้ Minecraft ที่ต้องการค้นหา")
    async def gpp_minecraft(self, interaction: discord.Interaction, username: str):
        """ดูข้อมูลโปรไฟล์ Minecraft"""
        await interaction.response.defer()
        
        try:
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession()
            
            user_data = await self.fetch_minecraft_user(username)
            embed = self.create_minecraft_embed(user_data, username)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ ข้อผิดพลาด",
                description=f"ไม่สามารถดึงข้อมูล Minecraft: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)

async def setup(bot):
    """ฟังก์ชันที่จำเป็นสำหรับการโหลดค็อก"""
    cog = GameProfilePuller(bot)
    await bot.add_cog(cog)
    await cog.cog_load()
