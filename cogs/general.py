import discord
from discord.ext import commands

class HelpView(discord.ui.View):
    def __init__(self, mapping, context, help_command):
        super().__init__(timeout=60)
        self.mapping = mapping
        self.context = context
        self.help_command = help_command
        self.message = None
        self.author_id = context.author.id

        # Create dropdown with categories
        options = []
        for cog in mapping.keys():
            if cog and mapping[cog]:  # Only add if cog exists and has commands
                cog_name = cog.qualified_name if cog else "No Category"
                description = cog.description[:50] if cog and cog.description else "No description"
                options.append(
                    discord.SelectOption(
                        label=cog_name,
                        description=description,
                        emoji="📁"
                    )
                )

        if not options:
            options.append(
                discord.SelectOption(
                    label="No Categories",
                    description="No commands available",
                    emoji="❌"
                )
            )

        self.category_select.options = options

    @discord.ui.select(placeholder="Select a category...", min_values=1, max_values=1)
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This help menu is not for you!", ephemeral=True)
            return

        selected_category = select.values[0]

        # Find the selected cog
        selected_cog = None
        for cog in self.mapping.keys():
            if cog and cog.qualified_name == selected_category:
                selected_cog = cog
                break

        if not selected_cog:
            await interaction.response.send_message("❌ Category not found!", ephemeral=True)
            return

        # Create embed for selected category
        embed = discord.Embed(
            title=f"📚 {selected_cog.qualified_name}",
            description=selected_cog.description or "No description available.",
            color=discord.Color.blurple()
        )

        # Get filtered commands
        filtered = []
        for cmd in selected_cog.get_commands():
            try:
                can_run = await cmd.can_run(self.context)
                if can_run:
                    filtered.append(cmd)
            except commands.CheckFailure:
                continue
            except Exception:
                filtered.append(cmd)

        if filtered:
            for cmd in sorted(filtered, key=lambda c: c.name):
                embed.add_field(
                    name=f"`{self.context.clean_prefix}{cmd.name} {cmd.signature}`",
                    value=cmd.help or "No description available.",
                    inline=False
                )
        else:
            embed.add_field(name="Commands", value="No available commands", inline=False)

        embed.set_footer(text="React with ❌ to close this menu")

        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        # Disable all components when timeout
        for item in self.children:
            item.disabled = True

        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass


class CustomHelp(commands.MinimalHelpCommand):
    async def send_bot_help(self, mapping):
        # Filter out empty cogs
        filtered_mapping = {}
        for cog, cmds in mapping.items():
            filtered = []
            for cmd in cmds:
                try:
                    can_run = await cmd.can_run(self.context)
                    if can_run:
                        filtered.append(cmd)
                except commands.CheckFailure:
                    continue
                except Exception:
                    filtered.append(cmd)

            if filtered:
                filtered_mapping[cog] = filtered

        # Create main embed
        embed = discord.Embed(
            title="🤖 Bot Commands",
            description="Select a category from the dropdown below to view commands.\nUse `!help <command>` for detailed command syntax.",
            color=discord.Color.blurple()
        )

        # Add overview of categories
        if filtered_mapping:
            categories_text = []
            for cog in filtered_mapping.keys():
                cog_name = cog.qualified_name if cog else "No Category"
                cmd_count = len(filtered_mapping[cog])
                categories_text.append(f"📁 **{cog_name}** - {cmd_count} command(s)")

            embed.add_field(
                name="Available Categories",
                value="\n".join(categories_text),
                inline=False
            )

        embed.set_footer(text="React with ❌ to close this menu | Menu expires in 60 seconds")

        # Create view with dropdown
        view = HelpView(filtered_mapping, self.context, self)
        channel = self.get_destination()
        message = await channel.send(embed=embed, view=view)
        view.message = message

        # Add X reaction for closing
        await message.add_reaction("❌")

        def check(reaction, user):
            return (
                user.id == self.context.author.id
                and str(reaction.emoji) == "❌"
                and reaction.message.id == message.id
            )

        try:
            # Wait for reaction
            await self.context.bot.wait_for('reaction_add', timeout=60.0, check=check)
            await message.delete()
        except:
            # Timeout or error, just disable the view
            pass

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=f"ℹ️ Command: {command.name}",
            description=command.help or "No description available.",
            color=discord.Color.blurple()
        )

        # Syntax/Usage
        embed.add_field(
            name="📝 Syntax",
            value=f"`{self.context.clean_prefix}{command.name} {command.signature}`",
            inline=False
        )

        # Aliases if available
        if command.aliases:
            embed.add_field(
                name="🔄 Aliases",
                value=", ".join(f"`{alias}`" for alias in command.aliases),
                inline=False
            )

        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=f"📚 {cog.qualified_name}",
            description=cog.description or "No description available.",
            color=discord.Color.blurple()
        )

        filtered = []
        for cmd in cog.get_commands():
            try:
                can_run = await cmd.can_run(self.context)
                if can_run:
                    filtered.append(cmd)
            except commands.CheckFailure:
                continue
            except Exception:
                filtered.append(cmd)

        if filtered:
            for cmd in sorted(filtered, key=lambda c: c.name):
                embed.add_field(
                    name=f"`{self.context.clean_prefix}{cmd.name} {cmd.signature}`",
                    value=cmd.help or "No description available.",
                    inline=False
                )
        else:
            embed.add_field(name="Commands", value="No available commands", inline=False)

        await self.get_destination().send(embed=embed)


class General(commands.Cog):
    """General user commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx):
        """Check bot latency (prefix)"""
        await ctx.send(f"Pong! 🏓 `{round(self.bot.latency*1000)}ms`")

    @discord.app_commands.command(name="ping", description="Check bot latency (slash)")
    async def slash_ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! 🏓 `{round(self.bot.latency*1000)}ms`")

async def setup(bot):
    bot.help_command = CustomHelp()
    await bot.add_cog(General(bot))
