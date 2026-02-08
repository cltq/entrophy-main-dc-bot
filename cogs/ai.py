import discord
from discord import app_commands
from discord.ext import commands
import google.genai as genai
from google.genai import types
import json
import os
import glob
import fnmatch
from typing import Literal
from pathlib import Path

# --- การตั้งค่า Configuration (Global) ---
# หมายเหตุ: ควรย้าย API Key ไปไว้ใน .env หรือ config หลักถ้าทำได้
GEMINI_API_KEY = str(os.getenv("GEMINI_API_KEY")) # ใส่ API Key ของ Gemini ที่นี่
AIMODEL = 'gemini-2.5-flash'  # ตั้งค่าโมเดลเริ่มต้น
CONFIG_FILE = './config/ai_channel_config.json'
PROJECT_ROOT = Path(__file__).parent.parent.resolve()  # Root of project for file tools

# Blocked files/patterns for security
BLOCKED_PATTERNS = ['.env', '*.key', '*.pem', '*secret*', '*credential*', '*password*']

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


# --- File Tool Functions for Gemini ---

def is_path_safe(file_path: str) -> tuple[bool, str]:
    """Check if a file path is safe to access"""
    try:
        # Resolve the full path
        full_path = (PROJECT_ROOT / file_path).resolve()
        
        # Check if path is within project root
        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return False, "Access denied: Path is outside project directory"
        
        # Check against blocked patterns
        filename = full_path.name
        for pattern in BLOCKED_PATTERNS:
            if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                return False, f"Access denied: File matches blocked pattern '{pattern}'"
        
        return True, str(full_path)
    except Exception as e:
        return False, f"Invalid path: {e}"


def tool_read_file(file_path: str) -> dict:
    """Read contents of a file from the project"""
    safe, result = is_path_safe(file_path)
    if not safe:
        return {"error": result}
    
    full_path = Path(result)
    if not full_path.exists():
        return {"error": f"File not found: {file_path}"}
    if not full_path.is_file():
        return {"error": f"Not a file: {file_path}"}
    
    try:
        # Limit file size to 100KB
        if full_path.stat().st_size > 100 * 1024:
            return {"error": "File too large (max 100KB)"}
        
        content = full_path.read_text(encoding='utf-8', errors='replace')
        return {
            "file_path": file_path,
            "content": content,
            "lines": len(content.splitlines()),
            "size_bytes": len(content.encode('utf-8'))
        }
    except Exception as e:
        return {"error": f"Failed to read file: {e}"}


def tool_list_files(directory: str = ".") -> dict:
    """List files in a directory"""
    safe, result = is_path_safe(directory)
    if not safe:
        return {"error": result}
    
    full_path = Path(result)
    if not full_path.exists():
        return {"error": f"Directory not found: {directory}"}
    if not full_path.is_dir():
        return {"error": f"Not a directory: {directory}"}
    
    try:
        items = []
        for item in sorted(full_path.iterdir()):
            # Skip hidden files and blocked patterns
            if item.name.startswith('.'):
                continue
            safe_item, _ = is_path_safe(str(item.relative_to(PROJECT_ROOT)))
            if not safe_item:
                continue
            
            item_type = "directory" if item.is_dir() else "file"
            items.append({"name": item.name, "type": item_type})
        
        return {"directory": directory, "items": items, "count": len(items)}
    except Exception as e:
        return {"error": f"Failed to list directory: {e}"}


def tool_search_files(pattern: str, directory: str = ".") -> dict:
    """Search for files matching a pattern"""
    safe, result = is_path_safe(directory)
    if not safe:
        return {"error": result}
    
    full_path = Path(result)
    if not full_path.exists():
        return {"error": f"Directory not found: {directory}"}
    
    try:
        matches = []
        for item in full_path.rglob(pattern):
            # Skip if outside project or blocked
            try:
                rel_path = item.relative_to(PROJECT_ROOT)
                safe_item, _ = is_path_safe(str(rel_path))
                if safe_item and not any(part.startswith('.') for part in rel_path.parts):
                    matches.append(str(rel_path))
            except ValueError:
                continue
        
        # Limit results
        matches = matches[:50]
        return {"pattern": pattern, "directory": directory, "matches": matches, "count": len(matches)}
    except Exception as e:
        return {"error": f"Failed to search files: {e}"}


def tool_create_file(file_path: str, content: str) -> dict:
    """Create a new file with the given content"""
    safe, result = is_path_safe(file_path)
    if not safe:
        return {"error": result}
    
    full_path = Path(result)
    
    # Don't allow overwriting existing files for safety
    if full_path.exists():
        return {"error": f"File already exists: {file_path}. Use a different name or delete it first."}
    
    try:
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        full_path.write_text(content, encoding='utf-8')
        
        return {
            "success": True,
            "file_path": file_path,
            "size_bytes": len(content.encode('utf-8')),
            "lines": len(content.splitlines())
        }
    except Exception as e:
        return {"error": f"Failed to create file: {e}"}


# Tool dispatch map
TOOL_FUNCTIONS = {
    "read_file": tool_read_file,
    "list_files": tool_list_files,
    "search_files": tool_search_files,
    "create_file": tool_create_file,
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
            name="search_files",
            description="Search for files matching a glob pattern (e.g., '*.py', '**/*.json').",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "pattern": types.Schema(
                        type=types.Type.STRING,
                        description="Glob pattern to match files (e.g., '*.py', '**/*.md')"
                    ),
                    "directory": types.Schema(
                        type=types.Type.STRING,
                        description="Directory to search in (default: '.' for project root)"
                    )
                },
                required=["pattern"]
            )
        ),
        types.FunctionDeclaration(
            name="create_file",
            description="Create a new file with the specified content. Cannot overwrite existing files.",
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
    ]
)


def execute_tool_call(tool_name: str, tool_args: dict) -> dict:
    """Execute a tool call and return the result"""
    if tool_name in TOOL_FUNCTIONS:
        return TOOL_FUNCTIONS[tool_name](**tool_args)
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
        model="รุ่นโมเดล",
        use_tools="Enable file tools (read/list/search/create files)"
    )
    async def slash_ask(
        self,
        interaction: discord.Interaction, 
        question: str,
        language: Literal["English", "Thai"] = "English",
        custom_prompt: str = None,
        model: str = AIMODEL,
        use_tools: bool = False
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
            
            # Build config with optional tools
            config = types.GenerateContentConfig(
                system_instruction=final_prompt,
                tools=[FILE_TOOLS] if use_tools else None
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
                    result = execute_tool_call(tool_name, tool_args)
                    
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
            if use_tools:
                header += "🔧 *File tools enabled*\n"
                
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