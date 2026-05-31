import json
import os
from pathlib import Path
from typing import Any, Optional, Literal

import discord
from discord import app_commands
from discord.ext import commands
import google.genai as genai
from google.genai import types

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
AIMODEL: str = "gemini-2.5-flash"
CONFIG_FILE: str = "./config/ai_channel_config.json"
PROJECT_ROOT: Path = Path(__file__).parent.parent.resolve()

# แผนที่ชื่อภาษา (สำหรับแสดงผล)
LANG_DISPLAY: dict[str, str] = {"English": "อังกฤษ", "Thai": "ไทย"}

INSTRUCTIONS_EN: str = """คุณคือผู้ช่วย AI ที่พร้อมช่วยเหลือผู้ใช้ในทุกด้าน ไม่ว่าจะเป็นการตอบคำถาม แก้ปัญหา ให้คำแนะนำ หรือช่วยในเรื่องต่างๆ คุณควรตอบอย่างถูกต้อง ชัดเจน และเป็นประโยชน์ โดยปรับระดับความลึกของคำตอบให้เหมาะสมกับผู้ใช้ คุณควรตอบในภาษาเดียวกับที่ผู้ใช้ถาม เป้าหมายของคุณคือการช่วยเหลืออย่างมีประสิทธิภาพสูงสุด ช่วยให้ผู้ใช้เข้าใจแนวคิด เอาชนะความท้าทาย และบรรลุเป้าหมาย"""

INSTRUCTIONS_TH: str = """คุณคือผู้ช่วย AI อเนกประสงค์ที่ออกแบบมาเพื่อช่วยเหลือผู้ใช้ในงาน คำถาม หรือปัญหาใดๆ ในทุกหัวข้อและสาขา บทบาทของคุณคือให้ความช่วยเหลือที่แม่นยำ ชัดเจน รอบคอบ และใช้งานได้จริงตลอดเวลา คุณต้องตอบกลับเป็นภาษาไทยเท่านั้น ไม่ว่าผู้ใช้จะใช้ภาษาใดก็ตาม คำตอบของคุณควรสุภาพ เป็นมิตร และเข้าใจง่าย พร้อมปรับความลึกและความซับซ้อนของคำอธิบายให้เหมาะกับความต้องการของผู้ใช้ คุณควรพยายามช่วยเหลือในด้านต่างๆ เช่น การเรียนรู้ การแก้ปัญหา การเขียนโปรแกรม การเขียน การแปล การวางแผน การวิเคราะห์ ความคิดสร้างสรรค์ และคำแนะนำทั่วไป หากคำขอไม่ชัดเจนหรือขาดข้อมูลที่จำเป็น คุณควรขอคำชี้แจงอย่างสุภาพ เมื่อมีแนวทางหรือวิธีแก้ปัญหาหลายวิธี ให้นำเสนอวิธีที่เหมาะสมที่สุดก่อนและอธิบายอย่างชัดเจน พร้อมกล่าวถึงทางเลือกอื่นเมื่อเกี่ยวข้อง คุณต้องให้ความสำคัญกับความถูกต้อง ความปลอดภัย และความเป็นประโยชน์ หลีกเลี่ยงการให้ข้อมูลที่เป็นอันตราย ผิดกฎหมาย หรือทำให้เข้าใจผิด และรักษาความเป็นกลางและให้การสนับสนุนในทุกการโต้ตอบ เป้าหมายสูงสุดของคุณคือช่วยเหลือผู้ใช้อย่างมีประสิทธิภาพ ช่วยให้พวกเขาเข้าใจแนวคิด เอาชนะความท้าทาย และบรรลุเป้าหมายด้วยความมั่นใจและความชัดเจนและให้คำตอบสั้นๆแต่เข้าใจได้"""


def load_config() -> dict[str, Any]:
    """โหลดการตั้งค่าจากไฟล์"""
    if not os.path.exists(CONFIG_FILE):
        return {"channels": {}}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "channels" not in data:
                return {"channels": {}}
            return data
    except Exception:
        return {"channels": {}}


def save_config(data: dict[str, Any]) -> None:
    """บันทึกการตั้งค่าไปยังไฟล์"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_instruction_by_language(language: str) -> str:
    """คืนค่า system prompt ตามภาษาที่เลือก"""
    if language.lower() == "thai":
        return INSTRUCTIONS_TH
    return INSTRUCTIONS_EN




class AI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # ตั้งค่า Gemini เมื่อโหลด Cog
        if GEMINI_API_KEY:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        else:
            print("⚠️ คำเตือน: ไม่พบ GEMINI_API_KEY ใน cogs/ai.py")
            self.client = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """รับข้อความจากผู้ใช้เพื่อตอบอัตโนมัติในห้องที่ตั้งค่าไว้"""
        if message.author == self.bot.user:
            return

        # ตรวจสอบว่าเป็นคำสั่ง Prefix หรือไม่ (ถ้าใช่ ให้ข้ามไป เพื่อไม่ให้ AI ตอบทับซ้อนกับคำสั่ง)
        # หมายเหตุ: ใน listener ของ Cog เราไม่ต้องเรียก process_commands
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        # ฟีเจอร์ Talking Channel
        config = load_config()
        channel_id = str(message.channel.id)

        # ตรวจสอบว่า channel นี้ถูก setup ไว้หรือไม่
        if channel_id in config.get("channels", {}):
            if not self.client:
                await message.channel.send("❌ ไม่ได้ตั้งค่า AI client กรุณาตรวจสอบ GEMINI_API_KEY")
                return

            async with message.channel.typing():
                try:
                    # ดึง Custom Prompt ของห้องนี้
                    channel_config = config["channels"][channel_id]
                    system_prompt = channel_config.get("prompt", INSTRUCTIONS_EN)

                    response = self.client.models.generate_content(
                        model=AIMODEL,
                        contents=message.content,
                        config={"system_instruction": system_prompt}
                    )
                    response_text: str = response.text or ""

                    if len(response_text) > 2000:
                        for i in range(0, len(response_text), 2000):
                            await message.channel.send(response_text[i:i+2000])
                    else:
                        await message.channel.send(response_text)
                except Exception as e:
                    await message.channel.send(f"⚠️ ข้อผิดพลาด: {e}")

    # --- Prefix Commands ---

    @commands.command(name="aisetup")
    async def prefix_setup(self, ctx: commands.Context, language: str = "English", *, custom_prompt: Optional[str] = None):
        """ตั้งค่าห้อง AI และบุคลิก (Prefix)"""
        if not ctx.guild:
            await ctx.send("คำสั่งนี้ใช้ได้เฉพาะใน Server เท่านั้น")
            return

        target_channel_id = str(ctx.channel.id)
        guild_id = str(ctx.guild.id)

        if language.lower() not in ["english", "thai"]:
            await ctx.send(f"❌ ภาษาไม่ถูกต้อง! กรุณาเลือก 'English' หรือ 'Thai'")
            return

        if custom_prompt:
            final_prompt = custom_prompt.strip()
            prompt_status = f"✅ ตั้งค่าบุคลิกแบบกำหนดเอง"
        else:
            final_prompt = get_instruction_by_language(language)
            prompt_status = f"✅ ใช้บุคลิกเริ่มต้น ({LANG_DISPLAY.get(language.capitalize(), language.capitalize())})"

        config = load_config()

        config["channels"][target_channel_id] = {
            "prompt": final_prompt,
            "language": language.capitalize(),
            "guild_id": guild_id
        }

        save_config(config)

        await ctx.send(
            f"✅ ตั้งค่าห้องแชทเรียบร้อย! บอทจะคุยในห้อง <#{target_channel_id}>\n{prompt_status}"
        )

    @commands.command(name="ailistchannels")
    async def prefix_list(self, ctx: commands.Context):
        """แสดงรายการห้องที่ตั้งค่าไว้ใน Server นี้ (Prefix)"""
        if not ctx.guild:
            await ctx.send("คำสั่งนี้ใช้ได้เฉพาะใน Server เท่านั้น")
            return

        config = load_config()
        guild_id = str(ctx.guild.id)

        channels_in_guild = {
            ch_id: ch_config
            for ch_id, ch_config in config.get("channels", {}).items()
            if ch_config.get("guild_id") == guild_id
        }

        if not channels_in_guild:
            await ctx.send("ยังไม่มีห้องที่ตั้งค่าไว้ใน Server นี้")
            return

        channels_list = []
        for ch_id, ch_config in channels_in_guild.items():
            lang = ch_config.get("language", "Unknown")
            channels_list.append(f"• <#{ch_id}> - ภาษา: {LANG_DISPLAY.get(lang, lang)}")

        message = "**ห้องที่ตั้งค่าไว้:**\n" + "\n".join(channels_list)
        await ctx.send(message)

    @commands.command(name="airemove")
    async def prefix_remove(self, ctx: commands.Context):
        """ลบการตั้งค่าห้องแชทปัจจุบัน (Prefix)"""
        if not ctx.guild:
            await ctx.send("คำสั่งนี้ใช้ได้เฉพาะใน Server เท่านั้น")
            return

        target_channel_id = str(ctx.channel.id)
        config = load_config()

        if target_channel_id not in config.get("channels", {}):
            await ctx.send(f"ไม่พบการตั้งค่าสำหรับห้องนี้")
            return

        del config["channels"][target_channel_id]
        save_config(config)

        await ctx.send(f"✅ ลบการตั้งค่าห้องนี้เรียบร้อยแล้ว")

    @commands.command(name="ask")
    async def prefix_ask(self, ctx: commands.Context, *, args: str):
        """ถามคำถาม AI (Prefix)"""
        parts = args.split(maxsplit=2)

        language = "English"
        model_name = AIMODEL
        question = args

        # แยกพารามิเตอร์แบบง่าย
        if len(parts) >= 1 and parts[0].lower() in ["english", "thai"]:
            language = parts[0].capitalize()
            if len(parts) >= 2:
                if parts[1].startswith("gemini"):
                    model_name = parts[1]
                    question = parts[2] if len(parts) >= 3 else ""
                else:
                    question = " ".join(parts[1:])

        if not question:
            await ctx.send("❌ กรุณาใส่คำถาม!")
            return

        if not self.client:
            await ctx.send("❌ ไม่ได้ตั้งค่า AI client กรุณาตรวจสอบ GEMINI_API_KEY")
            return

        async with ctx.typing():
            try:
                final_prompt = get_instruction_by_language(language)

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=question,
                    config={"system_instruction": final_prompt}
                )
                response_text: str = response.text or ""

                header = f"**Q:** {question}\n"

                if len(response_text) > 1900:
                    await ctx.send(f"{header}**A:** (คำตอบยาวเกินไป กำลังส่งแยก...)")
                    for i in range(0, len(response_text), 2000):
                        await ctx.send(response_text[i:i+2000])
                else:
                    await ctx.send(f"{header}**A:** {response_text}")

            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")

    # --- Slash Commands ---

    @app_commands.command(name="setup", description="ตั้งค่าห้องแชทและบุคลิกบอทใน Server นี้")
    @app_commands.describe(
        language="เลือกภาษาของคำสั่ง (ค่าเริ่มต้น: อังกฤษ)",
        custom_prompt="คำสั่งแบบกำหนดเอง (ถ้าต้องการ)"
    )
    async def slash_setup(
        self,
        interaction: discord.Interaction,
        language: Literal["English", "Thai"] = "English",
        custom_prompt: Optional[str] = None
    ):
        if not interaction.guild:
            await interaction.response.send_message("คำสั่งนี้ใช้ได้เฉพาะใน Server เท่านั้น")
            return

        target_channel_id = str(interaction.channel_id)
        guild_id = str(interaction.guild.id)

        if custom_prompt:
            final_prompt = custom_prompt.strip()
            prompt_status = f"✅ ตั้งค่าบุคลิกแบบกำหนดเอง"
        else:
            final_prompt = get_instruction_by_language(language)
            prompt_status = f"✅ ใช้บุคลิกเริ่มต้น ({LANG_DISPLAY.get(language, language)})"

        config = load_config()

        config["channels"][target_channel_id] = {
            "prompt": final_prompt,
            "language": language,
            "guild_id": guild_id
        }

        save_config(config)

        await interaction.response.send_message(
            f"✅ ตั้งค่าห้องแชทเรียบร้อย! บอทจะคุยในห้อง <#{target_channel_id}>\n{prompt_status}"
        )

    @app_commands.command(name="list_channels", description="แสดงรายการห้องที่ตั้งค่าไว้ใน Server นี้")
    async def slash_list_channels(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("คำสั่งนี้ใช้ได้เฉพาะใน Server เท่านั้น")
            return

        config = load_config()
        guild_id = str(interaction.guild.id)

        channels_in_guild = {
            ch_id: ch_config
            for ch_id, ch_config in config.get("channels", {}).items()
            if ch_config.get("guild_id") == guild_id
        }

        if not channels_in_guild:
            await interaction.response.send_message("ยังไม่มีห้องที่ตั้งค่าไว้ใน Server นี้")
            return

        channels_list = []
        for ch_id, ch_config in channels_in_guild.items():
            lang = ch_config.get("language", "Unknown")
            channels_list.append(f"• <#{ch_id}> - ภาษา: {LANG_DISPLAY.get(lang, lang)}")

        message = "**ห้องที่ตั้งค่าไว้:**\n" + "\n".join(channels_list)
        await interaction.response.send_message(message)

    @app_commands.command(name="remove_channel", description="ลบการตั้งค่าห้องแชทใน Server นี้")
    async def slash_remove_channel(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("คำสั่งนี้ใช้ได้เฉพาะใน Server เท่านั้น")
            return

        target_channel_id = str(interaction.channel_id)
        config = load_config()

        if target_channel_id not in config.get("channels", {}):
            await interaction.response.send_message(f"ไม่พบการตั้งค่าสำหรับห้องนี้")
            return

        del config["channels"][target_channel_id]
        save_config(config)

        await interaction.response.send_message(f"✅ ลบการตั้งค่าห้องนี้เรียบร้อยแล้ว")

    @app_commands.command(name="ask", description="ถามคำถาม AI / Ask AI a question")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        question="คำถามที่คุณต้องการถาม",
        language="เลือกภาษาของคำสั่ง (ค่าเริ่มต้น: อังกฤษ)",
        custom_prompt="คำสั่งแบบกำหนดเอง (ถ้าต้องการ)",
        model="รุ่นโมเดล"
    )
    async def slash_ask(
        self,
        interaction: discord.Interaction,
        question: str,
        language: Literal["English", "Thai"] = "English",
        custom_prompt: Optional[str] = None,
        model: str = AIMODEL
    ):
        await interaction.response.defer()

        if not self.client:
            await interaction.followup.send("❌ ไม่ได้ตั้งค่า AI client กรุณาตรวจสอบ GEMINI_API_KEY")
            return

        try:
            if custom_prompt:
                final_prompt = custom_prompt.strip()
            else:
                final_prompt = get_instruction_by_language(language)

            # สร้าง config โดยไม่ใช้ external tool integrations
            response = self.client.models.generate_content(
                model=model,
                contents=[types.Content(role="user", parts=[types.Part(text=question)])],
                config=types.GenerateContentConfig(system_instruction=final_prompt)
            )

            response_text = response.text if response.text else "No response generated."
            header = f"**Q:** {question}\n"

            if len(response_text) > 1900:
                await interaction.followup.send(f"{header}**A:** (คำตอบยาวเกินไป กำลังส่งแยก...)")
                for i in range(0, len(response_text), 2000):
                    await interaction.followup.send(response_text[i:i+2000])
            else:
                await interaction.followup.send(f"{header}**A:** {response_text}")

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AI(bot))
