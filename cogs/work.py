import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime
from typing import Optional, List

# Data file path for persisting todos and notes
DATA_FILE = "data/user_data.json"

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
    @app_commands.describe(
        action="Action to perform: create or list",
        title="Title for the note",
        content="Content for the note"
    )
    async def note(
        self,
        interaction: discord.Interaction,
        action: str = "list",
        title: Optional[str] = None,
        content: Optional[str] = None
    ):
        """Create and manage notes with /note create|list"""
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        notes = load_user_data(user_id, notes=True)
        
        if action.lower() == "create":
            if not title or not content:
                await interaction.followup.send(
                    "❌ Please provide both title and content!",
                    ephemeral=True
                )
                return
            
            note_item = {
                "title": title,
                "content": content,
                "created_at": datetime.now().isoformat()
            }
            notes.append(note_item)
            save_user_data(user_id, notes, notes=True)
            
            embed = discord.Embed(
                title="📝 Note Created!",
                description=f"**{title}**\n\n{content[:200]}...",
                color=discord.Color.gold()
            )
            view = NotesView(user_id, notes, interaction)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        elif action.lower() == "list":
            if not notes:
                embed = discord.Embed(
                    title="📝 Your Notes",
                    description="✨ No notes yet! Create one with `/note create`",
                    color=discord.Color.gold()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📝 Your Notes",
                color=discord.Color.gold()
            )
            
            for idx, note in enumerate(notes, 1):
                embed.add_field(
                    name=f"{idx}. {note['title']}",
                    value=note['content'][:100] + "..." if len(note['content']) > 100 else note['content'],
                    inline=False
                )
            
            embed.set_footer(text=f"Total: {len(notes)} notes")
            view = NotesView(user_id, notes, interaction)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        else:
            await interaction.followup.send(
                "❌ Invalid action! Use: `create` or `list`",
                ephemeral=True
            )

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

    @app_commands.command(name="notes", description="Quick alias for note list")
    async def notes(self, interaction: discord.Interaction):
        """Quick view of all notes - alias for /note list"""
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        notes_list = load_user_data(user_id, notes=True)
        
        if not notes_list:
            embed = discord.Embed(
                title="📝 Your Notes",
                description="✨ No notes yet! Create one with `/note create`",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📝 Your Notes",
            color=discord.Color.gold()
        )
        
        for idx, note in enumerate(notes_list, 1):
            embed.add_field(
                name=f"{idx}. {note['title']}",
                value=note['content'][:100] + "..." if len(note['content']) > 100 else note['content'],
                inline=False
            )
        
        embed.set_footer(text=f"Total: {len(notes_list)} notes")
        view = NotesView(user_id, notes_list, interaction)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

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
