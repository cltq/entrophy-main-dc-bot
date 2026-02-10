import discord
from discord import app_commands
from discord.ext import commands
import google.genai as genai
from google.genai import types
import json
import os
import aiohttp
import re
from typing import Literal
from pathlib import Path
import urllib.request

# --- Load mcplib from Gitea ---
MCPLIB_URL = 'http://asane.local:3002/fumi/SernaCore-MCPLibrary/raw/branch/main/mcplib.py'
try:
    exec(urllib.request.urlopen(MCPLIB_URL, timeout=10).read().decode('utf-8'))
    MCPLIB_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Warning: Could not load mcplib from {MCPLIB_URL}: {e}")
    MCPLIB_AVAILABLE = False

# --- การตั้งค่า Configuration (Global) ---
# หมายเหตุ: ควรย้าย API Key ไปไว้ใน .env หรือ config หลักถ้าทำได้
GEMINI_API_KEY = str(os.getenv("GEMINI_API_KEY")) # ใส่ API Key ของ Gemini ที่นี่
AIMODEL = 'gemini-2.5-flash'  # ตั้งค่าโมเดลเริ่มต้น
CONFIG_FILE = './config/ai_channel_config.json'
PROJECT_ROOT = Path(__file__).parent.parent.resolve()  # Root of project for file tools

# คำสั่งภาษาอังกฤษ (Default)
INSTRUCTIONS_EN = """You are an all-purpose AI assistant designed to help the user with any task, question, or problem across all topics and domains. Your role is to provide accurate, clear, thoughtful, and practical assistance at all times. Your answers should be polite, friendly, and easy to understand, while adapting the depth and complexity of explanations to suit the user's needs. You should strive to be helpful in areas such as learning, problem-solving, programming, writing, translation, planning, analysis, creativity, and general advice. If a request is unclear or lacks necessary information, you should ask for clarification in a respectful manner. When multiple approaches or solutions exist, present the most suitable one first and explain it clearly, while also mentioning alternatives when relevant. You must prioritize correctness, safety, and usefulness, avoid providing harmful, illegal, or misleading information, and remain neutral and supportive in all interactions. Your ultimate goal is to assist the user effectively, helping them understand concepts, overcome challenges, and achieve their goals with confidence and clarity."""

# คำสั่งภาษาไทย
INSTRUCTIONS_TH = """คุณคือผู้ช่วย AI อเนกประสงค์ที่ออกแบบมาเพื่อช่วยเหลือผู้ใช้ในงาน คำถาม หรือปัญหาใดๆ ในทุกหัวข้อและสาขา บทบาทของคุณคือให้ความช่วยเหลือที่แม่นยำ ชัดเจน รอบคอบ และใช้งานได้จริงตลอดเวลา คุณต้องตอบกลับเป็นภาษาไทยเท่านั้น ไม่ว่าผู้ใช้จะใช้ภาษาใดก็ตาม คำตอบของคุณควรสุภาพ เป็นมิตร และเข้าใจง่าย พร้อมปรับความลึกและความซับซ้อนของคำอธิบายให้เหมาะกับความต้องการของผู้ใช้ คุณควรพยายามช่วยเหลือในด้านต่างๆ เช่น การเรียนรู้ การแก้ปัญหา การเขียนโปรแกรม การเขียน การแปล การวางแผน การวิเคราะห์ ความคิดสร้างสรรค์ และคำแนะนำทั่วไป หากคำขอไม่ชัดเจนหรือขาดข้อมูลที่จำเป็น คุณควรขอคำชี้แจงอย่างสุภาพ เมื่อมีแนวทางหรือวิธีแก้ปัญหาหลายวิธี ให้นำเสนอวิธีที่เหมาะสมที่สุดก่อนและอธิบายอย่างชัดเจน พร้อมกล่าวถึงทางเลือกอื่นเมื่อเกี่ยวข้อง คุณต้องให้ความสำคัญกับความถูกต้อง ความปลอดภัย และความเป็นประโยชน์ หลีกเลี่ยงการให้ข้อมูลที่เป็นอันตราย ผิดกฎหมาย หรือทำให้เข้าใจผิด และรักษาความเป็นกลางและให้การสนับสนุนในทุกการโต้ตอบ เป้าหมายสูงสุดของคุณคือช่วยเหลือผู้ใช้อย่างมีประสิทธิภาพ ช่วยให้พวกเขาเข้าใจแนวคิด เอาชนะความท้าทาย และบรรลุเป้าหมายด้วยความมั่นใจและความชัดเจน"""

# --- Helper Functions ---
def load_config():
    """โหลดไฟล์ Config"""
    if not os.path.exists(CONFIG_FILE):
        return {"channels": {}}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "channels" not in data:
                return {"channels": {}}
            return data
    except:
        return {"channels": {}}

def save_config(data):
    """บันทึกไฟล์ Config"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_instruction_by_language(language: str) -> str:
    """ดึงคำสั่งตามภาษาที่เลือก"""
    if language.lower() == "thai":
        return INSTRUCTIONS_TH
    else:  # default to english
        return INSTRUCTIONS_EN


# --- Tool wrapper functions using mcplib ---

def tool_read_file(file_path: str) -> dict:
    """Read contents of a file using mcplib"""
    if not MCPLIB_AVAILABLE:
        return {"error": "mcplib not available"}
    full_path = str((PROJECT_ROOT / file_path).resolve())
    return read_file(full_path)

def tool_list_files(directory: str = ".") -> dict:
    """List files in a directory using mcplib"""
    if not MCPLIB_AVAILABLE:
        return {"error": "mcplib not available"}
    full_path = str((PROJECT_ROOT / directory).resolve())
    return list_files(full_path)

def tool_create_file(file_path: str, content: str) -> dict:
    """Create a new file using mcplib"""
    if not MCPLIB_AVAILABLE:
        return {"error": "mcplib not available"}
    full_path = str((PROJECT_ROOT / file_path).resolve())
    return create_file(full_path, content)

def tool_delete_file(file_path: str) -> dict:
    """Delete a file using mcplib"""
    if not MCPLIB_AVAILABLE:
        return {"error": "mcplib not available"}
    full_path = str((PROJECT_ROOT / file_path).resolve())
    return delete_file(full_path)

async def tool_browse_url(url: str) -> dict:
    """Browse a URL using mcplib"""
    if not MCPLIB_AVAILABLE:
        return {"error": "mcplib not available"}
    return browse_web(url)

async def tool_web_search(query: str, num_results: int = 5) -> dict:
    """Search the web using mcplib"""
    if not MCPLIB_AVAILABLE:
        return {"error": "mcplib not available"}
    return search_web(query, num_results=num_results)

async def tool_execute_command(command: str, cwd: str = None) -> dict:
    """Execute a shell command using mcplib"""
    if not MCPLIB_AVAILABLE:
        return {"error": "mcplib not available"}
    working_dir = cwd if cwd else str(PROJECT_ROOT)
    return execute_command(command, cwd=working_dir, timeout=30)

# Tool dispatch map (sync tools)
TOOL_FUNCTIONS = {
    "read_file": tool_read_file,
    "list_files": tool_list_files,
    "create_file": tool_create_file,
    "delete_file": tool_delete_file,
}

# Async tool dispatch map
ASYNC_TOOL_FUNCTIONS = {
    "browse_url": tool_browse_url,
    "web_search": tool_web_search,
    "execute_command": tool_execute_command,
}

# Gemini Tool Definitions
FILE_TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="read_file",
            description="Read the contents of a file from the project. Returns file content, line count, and size.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "file_path": types.Schema(
                        type=types.Type.STRING,
                        description="Relative path to the file from project root (e.g., 'main.py' or 'cogs/ai.py')"
                    )
                },
                required=["file_path"]
            )
        ),
        types.FunctionDeclaration(
            name="list_files",
            description="List all files and directories in a given directory.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "directory": types.Schema(
                        type=types.Type.STRING,
                        description="Relative path to directory (default: '.' for project root)"
                    )
                }
            )
        ),
        types.FunctionDeclaration(
            name="create_file",
            description="Create a new file with the specified content.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "file_path": types.Schema(
                        type=types.Type.STRING,
                        description="Relative path for the new file (e.g., 'scripts/hello.py')"
                    ),
                    "content": types.Schema(
                        type=types.Type.STRING,
                        description="Content to write to the file"
                    )
                },
                required=["file_path", "content"]
            )
        ),
        types.FunctionDeclaration(
            name="delete_file",
            description="Delete a file from the project.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "file_path": types.Schema(
                        type=types.Type.STRING,
                        description="Relative path to the file to delete"
                    )
                },
                required=["file_path"]
            )
        ),
        types.FunctionDeclaration(
            name="browse_url",
            description="Browse a webpage and return its text content. Use this to access external websites, documentation, or any URL.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(
                        type=types.Type.STRING,
                        description="Full URL to browse (must start with http:// or https://)"
                    )
                },
                required=["url"]
            )
        ),
        types.FunctionDeclaration(
            name="web_search",
            description="Search the web for information using DuckDuckGo. Returns titles, URLs, and snippets of matching results.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="Search query (e.g., 'Python async tutorial', 'latest news about AI')"
                    ),
                    "num_results": types.Schema(
                        type=types.Type.INTEGER,
                        description="Number of results to return (1-10, default: 5)"
                    )
                },
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="execute_command",
            description="Execute a shell command in the project directory. Use for running scripts, checking status, etc.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "command": types.Schema(
                        type=types.Type.STRING,
                        description="Shell command to execute (e.g., 'ls -la', 'python script.py')"
                    ),
                    "cwd": types.Schema(
                        type=types.Type.STRING,
                        description="Working directory for the command (optional, defaults to project root)"
                    )
                },
                required=["command"]
            )
        ),
    ]
)


async def execute_tool_call(tool_name: str, tool_args: dict) -> dict:
    """Execute a tool call and return the result (handles both sync and async tools)"""
    if tool_name in TOOL_FUNCTIONS:
        return TOOL_FUNCTIONS[tool_name](**tool_args)
    if tool_name in ASYNC_TOOL_FUNCTIONS:
        return await ASYNC_TOOL_FUNCTIONS[tool_name](**tool_args)
    return {"error": f"Unknown tool: {tool_name}"}

class AI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # ตั้งค่า Gemini เมื่อโหลด Cog
        if GEMINI_API_KEY:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        else:
            print("⚠️ Warning: GEMINI_API_KEY is missing in cogs/ai.py")
            self.client = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
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
                await message.channel.send("❌ AI client not configured. Please check GEMINI_API_KEY.")
                return
                
            async with message.channel.typing():
                try:
                    # ดึง Custom Prompt ของห้องนี้
                    channel_config = config["channels"][channel_id]
                    system_prompt = channel_config.get("prompt", INSTRUCTIONS_EN)
                    
                    # สร้าง Model Object และเรียกใช้งาน
                    response = self.client.models.generate_content(
                        model=AIMODEL,
                        contents=message.content,
                        config={"system_instruction": system_prompt}
                    )
                    response_text = response.text
                    
                    if len(response_text) > 2000:
                        for i in range(0, len(response_text), 2000):
                            await message.channel.send(response_text[i:i+2000])
                    else:
                        await message.channel.send(response_text)
                except Exception as e:
                    await message.channel.send(f"⚠️ Error: {e}")

    # --- Prefix Commands ---

    @commands.command(name="aisetup")
    async def prefix_setup(self, ctx: commands.Context, language: str = "English", *, custom_prompt: str = None):
        """ตั้งค่าห้องแชทและบุคลิกบอท (Prefix)"""
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
            prompt_status = f"✅ ใช้บุคลิกเริ่มต้น ({language.capitalize()})"

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
            channels_list.append(f"• <#{ch_id}> - Language: {lang}")
        
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
        
        # Simple Argument Parsing
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
            await ctx.send("❌ AI client not configured. Please check GEMINI_API_KEY.")
            return
        
        async with ctx.typing():
            try:
                final_prompt = get_instruction_by_language(language)
                
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=question,
                    config={"system_instruction": final_prompt}
                )
                response_text = response.text

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
        language="เลือกภาษาของคำสั่ง (Default: English)",
        custom_prompt="คำสั่งแบบกำหนดเอง (ถ้าต้องการ)"
    )
    async def slash_setup(
        self,
        interaction: discord.Interaction, 
        language: Literal["English", "Thai"] = "English",
        custom_prompt: str = None
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
            prompt_status = f"✅ ใช้บุคลิกเริ่มต้น ({language})"

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
            channels_list.append(f"• <#{ch_id}> - Language: {lang}")
        
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
        
    @app_commands.command(name="ask", description="Ask AI a question/ถามคำถาม AI")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        question="คำถามที่คุณต้องการถาม",
        language="เลือกภาษาของคำสั่ง (Default: English)",
        custom_prompt="คำสั่งแบบกำหนดเอง (ถ้าต้องการ)",
        model="รุ่นโมเดล"
    )
    async def slash_ask(
        self,
        interaction: discord.Interaction, 
        question: str,
        language: Literal["English", "Thai"] = "English",
        custom_prompt: str = None,
        model: str = AIMODEL
    ):
        await interaction.response.defer()

        if not self.client:
            await interaction.followup.send("❌ AI client not configured. Please check GEMINI_API_KEY.")
            return

        try:
            if custom_prompt:
                final_prompt = custom_prompt.strip()
            else:
                final_prompt = get_instruction_by_language(language)
            
            # Build config with tools enabled by default
            config = types.GenerateContentConfig(
                system_instruction=final_prompt,
                tools=[FILE_TOOLS]
            )
            
            # Initial request
            contents = [types.Content(role="user", parts=[types.Part(text=question)])]
            
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            
            # Handle function calling loop (max 5 iterations)
            max_iterations = 5
            iteration = 0
            
            while iteration < max_iterations:
                # Check if response has function calls
                if not response.candidates or not response.candidates[0].content.parts:
                    break
                    
                function_calls = [
                    part.function_call 
                    for part in response.candidates[0].content.parts 
                    if hasattr(part, 'function_call') and part.function_call
                ]
                
                if not function_calls:
                    break  # No more function calls, we have the final response
                
                # Add assistant response to conversation
                contents.append(response.candidates[0].content)
                
                # Execute each function call and collect results
                function_responses = []
                for fc in function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}
                    
                    # Execute the tool
                    result = await execute_tool_call(tool_name, tool_args)
                    
                    function_responses.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=tool_name,
                                response=result
                            )
                        )
                    )
                
                # Add function responses to conversation
                contents.append(types.Content(role="user", parts=function_responses))
                
                # Get next response
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config
                )
                
                iteration += 1
            
            # Extract final text response
            response_text = response.text if response.text else "No response generated."

            header = f"**Q:** {question}\n"
            header += "🔧 *Tools enabled*\n"
                
            if len(response_text) > 1900:
                await interaction.followup.send(f"{header}**A:** (คำตอบยาวเกินไป กำลังส่งแยก...)")
                for i in range(0, len(response_text), 2000):
                    await interaction.channel.send(response_text[i:i+2000])
            else:
                await interaction.followup.send(f"{header}**A:** {response_text}")

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AI(bot))