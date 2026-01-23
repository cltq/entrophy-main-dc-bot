import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import random
import string
from datetime import datetime, timedelta
from typing import Optional, List

# Data file path for persisting todos and notes
DATA_FILE = "data/user_data.json"

# Temporary note codes storage: {user_id: {"code": "ABC123", "expires_at": datetime}}
TEMP_NOTE_CODES = {}

class TodoListView(discord.ui.View):
    """Interactive view for todo list management"""
    def __init__(self, user_id: int, todos: List[dict], context):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.todos = todos
        self.context = context

    @discord.ui.button(label="✅ Mark Complete", style=discord.ButtonStyle.green)
    async def mark_complete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can't interact with this!", ephemeral=True)
            return
        
        if not self.todos:
            await interaction.response.send_message("❌ No todos to complete!", ephemeral=True)
            return

        # Create a select menu for choosing which todo to mark complete
        options = [
            discord.SelectOption(
                label=todo['text'][:100],
                value=str(idx),
                emoji="📝"
            )
            for idx, todo in enumerate(self.todos)
        ]

        class CompleteSelect(discord.ui.View):
            def __init__(self, parent):
                super().__init__(timeout=60)
                self.parent = parent

            @discord.ui.select(
                placeholder="Select a todo to mark complete...",
                options=options[:25]  # Discord limit
            )
            async def select_todo(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                if select_interaction.user.id != self.parent.user_id:
                    await select_interaction.response.send_message("❌ Not your list!", ephemeral=True)
                    return

                idx = int(select.values[0])
                self.parent.todos[idx]['completed'] = True
                self.parent.todos[idx]['completed_at'] = datetime.now().isoformat()
                save_user_data(self.parent.user_id, self.parent.todos)
                
                await select_interaction.response.send_message(
                    f"✅ Marked **{self.parent.todos[idx]['text']}** as complete!",
                    ephemeral=True
                )

        view = CompleteSelect(self)
        await interaction.response.send_message("Select a todo to mark complete:", view=view, ephemeral=True)

    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.red)
    async def delete_todo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can't interact with this!", ephemeral=True)
            return
        
        if not self.todos:
            await interaction.response.send_message("❌ No todos to delete!", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=todo['text'][:100],
                value=str(idx),
                emoji="🗑️"
            )
            for idx, todo in enumerate(self.todos)
        ]

        class DeleteSelect(discord.ui.View):
            def __init__(self, parent):
                super().__init__(timeout=60)
                self.parent = parent

            @discord.ui.select(
                placeholder="Select a todo to delete...",
                options=options[:25]
            )
            async def select_delete(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                if select_interaction.user.id != self.parent.user_id:
                    await select_interaction.response.send_message("❌ Not your list!", ephemeral=True)
                    return

                idx = int(select.values[0])
                deleted_text = self.parent.todos[idx]['text']
                del self.parent.todos[idx]
                save_user_data(self.parent.user_id, self.parent.todos)
                
                await select_interaction.response.send_message(
                    f"🗑️ Deleted **{deleted_text}**!",
                    ephemeral=True
                )

        view = DeleteSelect(self)
        await interaction.response.send_message("Select a todo to delete:", view=view, ephemeral=True)

    @discord.ui.button(label="📋 View All", style=discord.ButtonStyle.blurple)
    async def view_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can't interact with this!", ephemeral=True)
            return

        embed = create_todo_embed(self.todos, self.user_id)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class NotesView(discord.ui.View):
    """Interactive view for notes management"""
    def __init__(self, user_id: int, notes: List[dict], context):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.notes = notes
        self.context = context

    @discord.ui.button(label="📝 View Note", style=discord.ButtonStyle.blurple)
    async def view_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your notes!", ephemeral=True)
            return

        if not self.notes:
            await interaction.response.send_message("❌ No notes found!", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=note['title'][:100],
                value=str(idx),
                emoji="📄"
            )
            for idx, note in enumerate(self.notes)
        ]

        class ViewSelect(discord.ui.View):
            def __init__(self, parent):
                super().__init__(timeout=60)
                self.parent = parent

            @discord.ui.select(
                placeholder="Select a note to view...",
                options=options[:25]
            )
            async def select_note(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                if select_interaction.user.id != self.parent.user_id:
                    await select_interaction.response.send_message("❌ Not your notes!", ephemeral=True)
                    return

                idx = int(select.values[0])
                note = self.parent.notes[idx]
                
                embed = discord.Embed(
                    title=f"📝 {note['title']}",
                    description=note['content'],
                    color=discord.Color.gold(),
                    timestamp=datetime.fromisoformat(note['created_at'])
                )
                embed.set_footer(text="Created at")
                
                # Display attachments if available
                if note.get('attachments'):
                    attachment_info = "\n".join([f"📎 {att['filename']}" for att in note['attachments']])
                    embed.add_field(name="Attachments", value=attachment_info, inline=False)
                
                await select_interaction.response.send_message(embed=embed, ephemeral=True)

        view = ViewSelect(self)
        await interaction.response.send_message("Select a note to view:", view=view, ephemeral=True)

    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.red)
    async def delete_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your notes!", ephemeral=True)
            return

        if not self.notes:
            await interaction.response.send_message("❌ No notes to delete!", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=note['title'][:100],
                value=str(idx),
                emoji="🗑️"
            )
            for idx, note in enumerate(self.notes)
        ]

        class DeleteSelect(discord.ui.View):
            def __init__(self, parent):
                super().__init__(timeout=60)
                self.parent = parent

            @discord.ui.select(
                placeholder="Select a note to delete...",
                options=options[:25]
            )
            async def select_delete(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                if select_interaction.user.id != self.parent.user_id:
                    await select_interaction.response.send_message("❌ Not your notes!", ephemeral=True)
                    return

                idx = int(select.values[0])
                deleted_title = self.parent.notes[idx]['title']
                del self.parent.notes[idx]
                save_user_data(self.parent.user_id, self.parent.notes, notes=True)
                
                await select_interaction.response.send_message(
                    f"🗑️ Deleted note **{deleted_title}**!",
                    ephemeral=True
                )

        view = DeleteSelect(self)
        await interaction.response.send_message("Select a note to delete:", view=view, ephemeral=True)


def generate_temp_code():
    """Generate a random temporary command code (a-z, A-Z, 0-9)"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(10))


def create_temp_note_code(user_id: int, duration_minutes: int = 5) -> str:
    """Create a temporary note code for a user"""
    code = generate_temp_code()
    TEMP_NOTE_CODES[user_id] = {
        "code": code,
        "expires_at": datetime.now() + timedelta(minutes=duration_minutes)
    }
    return code


def is_temp_code_valid(user_id: int, code: str) -> bool:
    """Check if a temporary code is valid and not expired"""
    # Strip whitespace and convert to lowercase for comparison
    code = code.strip().lower()
    
    if user_id not in TEMP_NOTE_CODES:
        return False
    
    stored = TEMP_NOTE_CODES[user_id]
    if stored["code"].lower() != code:
        return False
    
    if datetime.now() > stored["expires_at"]:
        del TEMP_NOTE_CODES[user_id]
        return False
    
    return True


def cleanup_expired_codes():
    """Remove expired temporary codes"""
    expired_users = [
        user_id for user_id, data in TEMP_NOTE_CODES.items()
        if datetime.now() > data["expires_at"]
    ]
    for user_id in expired_users:
        del TEMP_NOTE_CODES[user_id]


class NoteActionView(discord.ui.View):
    """View for selecting note action (create, list, delete)"""
    def __init__(self, user_id: int, context):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.context = context

    @discord.ui.button(label="📝 Create Note", style=discord.ButtonStyle.green, emoji="✏️")
    async def create_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can't interact with this!", ephemeral=True)
            return
        
        # Selection view for create method
        class CreateMethodView(discord.ui.View):
            def __init__(self, user_id, parent_cog):
                super().__init__(timeout=300)
                self.user_id = user_id
                self.parent_cog = parent_cog
            
            @discord.ui.button(label="GUI Form", style=discord.ButtonStyle.blurple, emoji="📋")
            async def gui_method(self, method_interaction: discord.Interaction, button: discord.ui.Button):
                if method_interaction.user.id != self.user_id:
                    await method_interaction.response.send_message("❌ Not your action!", ephemeral=True)
                    return
                
                await self._show_gui_method(method_interaction)
            
            @discord.ui.button(label="Command Method", style=discord.ButtonStyle.blurple, emoji="💬")
            async def command_method(self, method_interaction: discord.Interaction, button: discord.ui.Button):
                if method_interaction.user.id != self.user_id:
                    await method_interaction.response.send_message("❌ Not your action!", ephemeral=True)
                    return
                
                await self._show_command_method(method_interaction)
            
            async def _show_gui_method(self, method_interaction: discord.Interaction):
                """Show the GUI form method"""
                # Create a modal for note creation
                class NoteModal(discord.ui.Modal, title="Create a New Note"):
                    title_input = discord.ui.TextInput(
                        label="Note Title",
                        placeholder="Enter note title...",
                        max_length=256,
                        required=True
                    )
                    content_input = discord.ui.TextInput(
                        label="Note Content",
                        placeholder="Enter note content...",
                        style=discord.TextStyle.long,
                        max_length=4000,
                        required=True
                    )

                    async def on_submit(self, modal_interaction: discord.Interaction):
                        user_id = modal_interaction.user.id
                        notes = load_user_data(user_id, notes=True)
                        
                        # Get attachments from the parent interaction context
                        attachments = []
                        if hasattr(self, 'stored_attachments'):
                            attachments = self.stored_attachments
                        
                        note_item = {
                            "title": self.title_input.value,
                            "content": self.content_input.value,
                            "created_at": datetime.now().isoformat(),
                            "attachments": attachments
                        }
                        notes.append(note_item)
                        save_user_data(user_id, notes, notes=True)
                        
                        embed = discord.Embed(
                            title="📝 Note Created!",
                            description=f"**{self.title_input.value}**\n\n{self.content_input.value[:200]}...",
                            color=discord.Color.gold()
                        )
                        if attachments:
                            attachment_info = "\n".join([f"📎 {att['filename']}" for att in attachments])
                            embed.add_field(name="Attachments", value=attachment_info, inline=False)
                        
                        await modal_interaction.response.send_message(embed=embed, ephemeral=True)

                # Check if the user has recent attachments
                class AttachmentView(discord.ui.View):
                    def __init__(self, user_id):
                        super().__init__(timeout=300)
                        self.user_id = user_id
                        self.attachments = []
                    
                    @discord.ui.button(label="Continue to Create", style=discord.ButtonStyle.green)
                    async def continue_create(self, att_interaction: discord.Interaction, button: discord.ui.Button):
                        if att_interaction.user.id != self.user_id:
                            await att_interaction.response.send_message("❌ Not your action!", ephemeral=True)
                            return
                        
                        modal = NoteModal()
                        modal.stored_attachments = self.attachments
                        await att_interaction.response.send_modal(modal)
                
                view = AttachmentView(self.user_id)
                
                # Try to get attachments from recent message if available
                try:
                    async for message in method_interaction.channel.history(limit=100):
                        if message.author.id == method_interaction.user.id and message.attachments:
                            view.attachments = [
                                {
                                    "filename": att.filename,
                                    "url": att.url,
                                    "size": att.size
                                }
                                for att in message.attachments
                            ]
                            break
                except:
                    pass
                
                attachment_text = ""
                if view.attachments:
                    attachment_text = "\n\n**📎 Found attachments:**\n" + "\n".join([f"• {att['filename']}" for att in view.attachments])
                
                embed = discord.Embed(
                    title="📋 GUI Form Method",
                    description=f"Fill in the form to create your note.{attachment_text}",
                    color=discord.Color.gold()
                )
                await method_interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            async def _show_command_method(self, method_interaction: discord.Interaction):
                """Show the command method with temporary code"""
                # Generate temporary code for this user
                temp_code = create_temp_note_code(method_interaction.user.id, duration_minutes=5)
                
                class CodeCopyView(discord.ui.View):
                    def __init__(self, code):
                        super().__init__(timeout=300)
                        self.code = code
                    
                    @discord.ui.button(label="📋 Copy Code", style=discord.ButtonStyle.primary, emoji="📌")
                    async def copy_code(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        # Copy code to clipboard via message
                        await button_interaction.response.send_message(
                            f"Your code to copy:\n```\n{self.code}\n```",
                            ephemeral=True
                        )
                
                embed = discord.Embed(
                    title="💬 Temporary Command Method",
                    description=f"Your temporary code is ready for 5 minutes:\n\n**Code:** `{temp_code}`\n\n**Command format:**\n```\n/notecreate\ntempcode: {temp_code}\ntitle: Your Title\ncontent: Your Content\nattachment: [your_file]\n```\n\n**Steps:**\n1. Click the button below to copy your code\n2. Use the `/notecreate` command\n3. Paste your code in the `tempcode` field\n4. Fill in title, content, and attach a file\n5. Done! ✅",
                    color=discord.Color.gold()
                )
                embed.set_footer(text="⏱️ Code expires in 5 minutes | Or after first use")
                
                await method_interaction.response.send_message(embed=embed, view=CodeCopyView(temp_code), ephemeral=True)
        
        method_view = CreateMethodView(interaction.user.id, self)
        embed = discord.Embed(
            title="📝 Choose Creation Method",
            description="Select how you want to create your note:",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=method_view, ephemeral=True)

    @discord.ui.button(label="📋 List Notes", style=discord.ButtonStyle.blurple, emoji="📚")
    async def list_notes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can't interact with this!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        notes = load_user_data(interaction.user.id, notes=True)
        
        if not notes:
            embed = discord.Embed(
                title="📝 Your Notes",
                description="✨ No notes yet! Click the Create Note button to make one.",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📝 Your Notes",
            color=discord.Color.gold()
        )
        
        for idx, note in enumerate(notes, 1):
            attachment_count = len(note.get('attachments', []))
            attachment_str = f" 📎 ({attachment_count})" if attachment_count > 0 else ""
            embed.add_field(
                name=f"{idx}. {note['title']}{attachment_str}",
                value=note['content'][:100] + "..." if len(note['content']) > 100 else note['content'],
                inline=False
            )
        
        embed.set_footer(text=f"Total: {len(notes)} notes")
        view = NotesView(self.user_id, notes, interaction)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🗑️ Delete Note", style=discord.ButtonStyle.red, emoji="❌")
    async def delete_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can't interact with this!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        notes = load_user_data(interaction.user.id, notes=True)
        
        if not notes:
            await interaction.followup.send("❌ No notes to delete!", ephemeral=True)
            return
        
        options = [
            discord.SelectOption(
                label=note['title'][:100],
                value=str(idx),
                emoji="🗑️"
            )
            for idx, note in enumerate(notes)
        ]

        class DeleteSelect(discord.ui.View):
            def __init__(self, parent):
                super().__init__(timeout=60)
                self.parent = parent

            @discord.ui.select(
                placeholder="Select a note to delete...",
                options=options[:25]
            )
            async def select_delete(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                if select_interaction.user.id != self.parent.user_id:
                    await select_interaction.response.send_message("❌ Not your notes!", ephemeral=True)
                    return

                idx = int(select.values[0])
                deleted_title = notes[idx]['title']
                del notes[idx]
                save_user_data(self.parent.user_id, notes, notes=True)
                
                await select_interaction.response.send_message(
                    f"🗑️ Deleted note **{deleted_title}**!",
                    ephemeral=True
                )

        view = DeleteSelect(self)
        await interaction.followup.send("Select a note to delete:", view=view, ephemeral=True)


def ensure_data_dir():
    """Ensure the data directory exists"""
    os.makedirs("data", exist_ok=True)


def load_user_data(user_id: int, notes: bool = False):
    """Load user todos or notes from JSON file"""
    ensure_data_dir()
    
    if not os.path.exists(DATA_FILE):
        return [] if not notes else []
    
    try:
        with open(DATA_FILE, 'r') as f:
            all_data = json.load(f)
        
        user_key = f"user_{user_id}"
        if user_key in all_data:
            return all_data[user_key].get("notes" if notes else "todos", [])
        return []
    except:
        return []


def save_user_data(user_id: int, data: List[dict], notes: bool = False):
    """Save user todos or notes to JSON file"""
    ensure_data_dir()
    
    all_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                all_data = json.load(f)
        except:
            all_data = {}
    
    user_key = f"user_{user_id}"
    if user_key not in all_data:
        all_data[user_key] = {"todos": [], "notes": []}
    
    if notes:
        all_data[user_key]["notes"] = data
    else:
        all_data[user_key]["todos"] = data
    
    with open(DATA_FILE, 'w') as f:
        json.dump(all_data, f, indent=2)


def create_todo_embed(todos: List[dict], user_id: int) -> discord.Embed:
    """Create an embed displaying todos"""
    embed = discord.Embed(
        title="📋 Your Todo List",
        color=discord.Color.blue(),
        description="Here are your current todos:"
    )
    
    if not todos:
        embed.description = "✨ No todos yet! Add one with `/todo add`"
        return embed
    
    pending = [t for t in todos if not t.get('completed', False)]
    completed = [t for t in todos if t.get('completed', False)]
    
    if pending:
        pending_text = "\n".join([f"• {t['text']}" for t in pending])
        embed.add_field(name="📝 Pending", value=pending_text or "None", inline=False)
    
    if completed:
        completed_text = "\n".join([f"✅ {t['text']}" for t in completed])
        embed.add_field(name="✅ Completed", value=completed_text or "None", inline=False)
    
    embed.set_footer(text=f"Total: {len(todos)} | Completed: {len(completed)}")
    return embed


class WorkCog(commands.Cog):
    """Todo list and note-taking commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.cleanup_expired_codes.start()
    
    @tasks.loop(minutes=1)
    async def cleanup_expired_codes(self):
        """Periodically clean up expired temporary codes"""
        cleanup_expired_codes()
    
    @cleanup_expired_codes.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()
    
    def cog_unload(self):
        """Stop the cleanup task when cog is unloaded"""
        self.cleanup_expired_codes.cancel()

    @app_commands.command(name="todo", description="Manage your todo list")
    @app_commands.describe(
        action="Action to perform: add, view, or clear",
        text="Text for the todo (required for 'add')"
    )
    async def todo(
        self, 
        interaction: discord.Interaction, 
        action: str = "view",
        text: Optional[str] = None
    ):
        """Manage your todo list with /todo add|view|clear"""
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        todos = load_user_data(user_id, notes=False)
        
        if action.lower() == "add":
            if not text:
                await interaction.followup.send("❌ Please provide text for the todo!", ephemeral=True)
                return
            
            todo_item = {
                "text": text,
                "created_at": datetime.now().isoformat(),
                "completed": False
            }
            todos.append(todo_item)
            save_user_data(user_id, todos, notes=False)
            
            embed = discord.Embed(
                title="✅ Todo Added!",
                description=f"Added: **{text}**",
                color=discord.Color.green()
            )
            view = TodoListView(user_id, todos, interaction)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        elif action.lower() == "view":
            embed = create_todo_embed(todos, user_id)
            view = TodoListView(user_id, todos, interaction)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        elif action.lower() == "clear":
            todos.clear()
            save_user_data(user_id, todos, notes=False)
            await interaction.followup.send("🗑️ All todos cleared!", ephemeral=True)
        
        else:
            await interaction.followup.send(
                "❌ Invalid action! Use: `add`, `view`, or `clear`",
                ephemeral=True
            )

    @app_commands.command(name="note", description="Create and manage notes")
    async def note(self, interaction: discord.Interaction):
        """Manage notes with interactive menu"""
        embed = discord.Embed(
            title="📝 Note Manager",
            description="Choose what you'd like to do with your notes:",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Click a button to get started")
        
        view = NoteActionView(interaction.user.id, interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="notecreate", description="Create a note with file attachments")
    @app_commands.describe(
        tempcode="Your temporary code (from /note Create Note > Command Method)",
        title="Title for your note",
        content="Content for your note",
        attachment="Attach a file (required)"
    )
    async def notecreate(
        self,
        interaction: discord.Interaction,
        tempcode: str,
        title: str,
        content: str,
        attachment: discord.Attachment
    ):
        """Create a note with attachments using command method with temporary code"""
        user_id = interaction.user.id
        
        # Debug: Check if code exists
        has_code = user_id in TEMP_NOTE_CODES
        
        # Verify the temporary code
        if not is_temp_code_valid(user_id, tempcode):
            if not has_code:
                error_msg = "No code found for your account. Generate one with `/note` → Create Note → Command Method"
            else:
                error_msg = "Your temporary code is invalid or has expired.\n\nGenerate a new one with `/note` → Create Note → Command Method"
            
            embed = discord.Embed(
                title="❌ Invalid or Expired Code",
                description=error_msg,
                color=discord.Color.red()
            )
            embed.add_field(name="Debug Info", value=f"Code provided: `{tempcode.strip()}`\nCode exists: `{has_code}`", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Code is valid, create the note
        notes = load_user_data(user_id, notes=True)
        
        # Convert attachment to the same format
        attachments = [
            {
                "filename": attachment.filename,
                "url": attachment.url,
                "size": attachment.size
            }
        ]
        
        note_item = {
            "title": title,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "attachments": attachments
        }
        notes.append(note_item)
        save_user_data(user_id, notes, notes=True)
        
        # Expire the code after use
        if user_id in TEMP_NOTE_CODES:
            del TEMP_NOTE_CODES[user_id]
        
        class CodeExpireView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)
            
            @discord.ui.button(label="🔓 Code Already Expired", style=discord.ButtonStyle.red, disabled=True)
            async def code_expired_btn(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                pass
        
        embed = discord.Embed(
            title="📝 Note Created!",
            description=f"**{title}**\n\n{content[:200]}...",
            color=discord.Color.gold()
        )
        if attachments:
            attachment_info = "\n".join([f"📎 {att['filename']}" for att in attachments])
            embed.add_field(name="Attachments", value=attachment_info, inline=False)
        
        embed.set_footer(text="✅ Code has been automatically expired after use")
        
        await interaction.response.send_message(embed=embed, view=CodeExpireView(), ephemeral=True)

    @app_commands.command(name="reminder", description="Set a reminder")
    @app_commands.describe(
        text="What to remind you about",
        importance="Importance level: low, medium, or high"
    )
    async def reminder(
        self,
        interaction: discord.Interaction,
        text: str,
        importance: Optional[str] = "medium"
    ):
        """Create a reminder with /reminder"""
        await interaction.response.defer(ephemeral=True)
        
        importance = importance.lower() if importance else "medium"
        if importance not in ["low", "medium", "high"]:
            await interaction.followup.send(
                "❌ Importance must be: low, medium, or high",
                ephemeral=True
            )
            return
        
        # Reminders are stored in todos with a special marker
        user_id = interaction.user.id
        todos = load_user_data(user_id, notes=False)
        
        reminder_item = {
            "text": f"🔔 [{importance.upper()}] {text}",
            "created_at": datetime.now().isoformat(),
            "completed": False,
            "is_reminder": True,
            "importance": importance
        }
        todos.append(reminder_item)
        save_user_data(user_id, todos, notes=False)
        
        emoji_map = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        
        embed = discord.Embed(
            title=f"{emoji_map[importance]} Reminder Set!",
            description=f"**{text}**",
            color=discord.Color.red() if importance == "high" else (discord.Color.gold() if importance == "medium" else discord.Color.green())
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="notes", description="Quick alias for note manager")
    async def notes(self, interaction: discord.Interaction):
        """Quick access to notes - same as /note"""
        embed = discord.Embed(
            title="📝 Note Manager",
            description="Choose what you'd like to do with your notes:",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Click a button to get started")
        
        view = NoteActionView(interaction.user.id, interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="todos", description="Quick alias for todo view")
    async def todos(self, interaction: discord.Interaction):
        """Quick view of all todos - alias for /todo view"""
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        todos = load_user_data(user_id, notes=False)
        
        embed = create_todo_embed(todos, user_id)
        view = TodoListView(user_id, todos, interaction)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    """Load the WorkCog into the bot"""
    await bot.add_cog(WorkCog(bot))
