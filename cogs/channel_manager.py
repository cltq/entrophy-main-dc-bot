import os
import json
import asyncio
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


DATA_DIR = Path(__file__).parent.parent / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"
SERVERS_FILE = DATA_DIR / "servers.json"


def _load_data() -> dict:
    if CHANNELS_FILE.exists():
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_data(data: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_server_config() -> dict:
    if SERVERS_FILE.exists():
        with open(SERVERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_server_config(config: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with open(SERVERS_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def _get_guild_config(guild_id: int) -> dict:
    config = _load_server_config()
    return config.get(str(guild_id), {})


DASHBOARD_TITLE = "🎛️  แดชบอร์ดช่อง"


def _channel_info(channel_id: str, data: dict) -> dict:
    return data.get(str(channel_id), {})


def build_dashboard_embed(
    channel: discord.TextChannel,
    owner: discord.Member | discord.User,
    data: dict,
) -> discord.Embed:
    info = _channel_info(channel.id, data)

    slowmode = channel.slowmode_delay
    nsfw = channel.is_nsfw()
    topic = channel.topic or "*ยังไม่ได้ตั้งหัวข้อ*"
    member_count = len(channel.members) if hasattr(channel, "members") else "?"

    embed = discord.Embed(
        title=DASHBOARD_TITLE,
        description=(
            f"แผงควบคุมทั้งหมดสำหรับ **#{channel.name}**\n"
            f"ใช้ปุ่มและเมนูด้านล่างเพื่อจัดการช่องนี้"
        ),
        color=0x5865F2,
    )
    embed.add_field(name="👑 เจ้าของ", value=f"{owner.mention}", inline=True)
    embed.add_field(name="👥 สมาชิก", value=str(member_count), inline=True)
    embed.add_field(name="🐢 สโลว์โหมด", value=f"{slowmode} วินาที" if slowmode else "ปิด", inline=True)
    embed.add_field(name="📝 หัวข้อ", value=topic, inline=False)
    embed.add_field(name="🔞 NSFW", value="เปิด" if nsfw else "ปิด", inline=True)
    embed.add_field(
        name="🔒 การมองเห็น",
        value="สาธารณะ" if info.get("visibility", "Private") == "Public" else "ส่วนตัว",
        inline=True,
    )
    embed.set_footer(text="เฉพาะเจ้าของช่องเท่านั้นที่สามารถใช้การควบคุมเหล่านี้ได้")
    return embed


class CreateChannelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📁 สร้างช่องของฉัน",
        style=discord.ButtonStyle.success,
        custom_id="global:create_channel",
        emoji="✨",
    )
    async def create_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await _create_channel_for_user(interaction, already_deferred=True)


class DashboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _is_owner(self, interaction: discord.Interaction) -> bool:
        data = _load_data()
        info = data.get(str(interaction.channel_id), {})
        if info.get("owner_id") != interaction.user.id:
            await interaction.response.send_message(
                "❌ เฉพาะเจ้าของช่องเท่านั้นที่สามารถใช้แดชบอร์ดนี้ได้",
                ephemeral=True,
            )
            return False
        return True

    async def _refresh(self, interaction: discord.Interaction) -> None:
        data = _load_data()
        info = data.get(str(interaction.channel_id), {})
        guild = interaction.guild
        owner = guild.get_member(info.get("owner_id", 0)) or interaction.user
        embed = build_dashboard_embed(interaction.channel, owner, data)
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="✏️ เปลี่ยนชื่อ", style=discord.ButtonStyle.primary, custom_id="dash:rename", row=0)
    async def rename_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_owner(interaction):
            return
        await interaction.response.send_modal(RenameModal())

    @discord.ui.button(label="📝 ตั้งหัวข้อ", style=discord.ButtonStyle.primary, custom_id="dash:topic", row=0)
    async def topic_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_owner(interaction):
            return
        await interaction.response.send_modal(TopicModal())

    @discord.ui.button(label="🔞 สลับ NSFW", style=discord.ButtonStyle.secondary, custom_id="dash:nsfw", row=0)
    async def nsfw_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_owner(interaction):
            return
        channel = interaction.channel
        await channel.edit(nsfw=not channel.is_nsfw())
        await interaction.response.send_message(
            f"NSFW ตอนนี้ **{'เปิด' if channel.is_nsfw() else 'ปิด'}** แล้ว", ephemeral=True
        )
        await self._refresh(interaction)

    @discord.ui.button(label="👑 โอนสิทธิ์", style=discord.ButtonStyle.secondary, custom_id="dash:transfer", row=0)
    async def transfer_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_owner(interaction):
            return
        await interaction.response.send_modal(TransferOwnerModal())

    @discord.ui.button(label="➕ เพิ่มสมาชิก", style=discord.ButtonStyle.success, custom_id="dash:add_member", row=1)
    async def add_member_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_owner(interaction):
            return
        await interaction.response.send_modal(AddMemberModal())

    @discord.ui.button(label="➖ ลบสมาชิก", style=discord.ButtonStyle.danger, custom_id="dash:rm_member", row=1)
    async def remove_member_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_owner(interaction):
            return
        await interaction.response.send_modal(RemoveMemberModal())

    @discord.ui.button(label="🔓 เปิดสาธารณะ", style=discord.ButtonStyle.secondary, custom_id="dash:visibility", row=1)
    async def toggle_visibility_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_owner(interaction):
            return

        data = _load_data()
        info = data.get(str(interaction.channel_id), {})
        currently_private = info.get("visibility", "Private") == "Private"

        overwrites = interaction.channel.overwrites
        default_role = interaction.guild.default_role

        if currently_private:
            overwrites[default_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                read_message_history=True,
            )
            info["visibility"] = "Public"
            label = "🔒 ตั้งเป็นส่วนตัว"
        else:
            overwrites[default_role] = discord.PermissionOverwrite(
                view_channel=False,
                send_messages=False,
                read_message_history=False,
            )
            info["visibility"] = "Private"
            label = "🔓 เปิดสาธารณะ"

        await interaction.channel.edit(overwrites=overwrites)
        data[str(interaction.channel_id)] = info
        _save_data(data)

        button.label = label
        await interaction.response.send_message(
            f"ช่องตอนนี้เป็น **{'สาธารณะ' if info['visibility'] == 'Public' else 'ส่วนตัว'}** แล้ว", ephemeral=True
        )
        await self._refresh(interaction)

    @discord.ui.select(
        cls=discord.ui.Select,
        placeholder="🐢 ตั้งค่าสโลว์โหมด...",
        custom_id="dash:slowmode",
        row=2,
        options=[
            discord.SelectOption(label="ปิด", value="0"),
            discord.SelectOption(label="5 วินาที", value="5"),
            discord.SelectOption(label="10 วินาที", value="10"),
            discord.SelectOption(label="30 วินาที", value="30"),
            discord.SelectOption(label="1 นาที", value="60"),
            discord.SelectOption(label="5 นาที", value="300"),
            discord.SelectOption(label="10 นาที", value="600"),
            discord.SelectOption(label="30 นาที", value="1800"),
        ],
    )
    async def slowmode_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not await self._is_owner(interaction):
            return
        delay = int(select.values[0])
        await interaction.channel.edit(slowmode_delay=delay)
        label = f"{delay} วินาที" if delay else "ปิด"
        await interaction.response.send_message(
            f"ตั้งสโลว์โหมดเป็น **{label}** แล้ว", ephemeral=True
        )
        await self._refresh(interaction)

    @discord.ui.button(label="🧹 ลบข้อความ", style=discord.ButtonStyle.danger, custom_id="dash:purge", row=3)
    async def purge_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_owner(interaction):
            return
        await interaction.response.send_modal(PurgeModal())

    @discord.ui.button(label="🗑️ ลบช่อง", style=discord.ButtonStyle.danger, custom_id="dash:delete", row=3)
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_owner(interaction):
            return
        view = ConfirmDeleteView()
        await interaction.response.send_message(
            "⚠️ **คุณแน่ใจหรือไม่ว่าต้องการลบช่องนี้?** การกระทำนี้ไม่สามารถย้อนกลับได้",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="🔄 รีเฟรช", style=discord.ButtonStyle.secondary, custom_id="dash:refresh", row=4)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self._refresh(interaction)
        await interaction.followup.send("รีเฟรชแดชบอร์ดแล้ว! ✅", ephemeral=True)


class RenameModal(discord.ui.Modal, title="เปลี่ยนชื่อช่อง"):
    new_name = discord.ui.TextInput(
        label="ชื่อช่องใหม่",
        placeholder="ช่อง-สุดเจ๋ง",
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.channel.edit(name=self.new_name.value)
        await interaction.response.send_message(
            f"✅ เปลี่ยนชื่อช่องเป็น **#{self.new_name.value}** แล้ว", ephemeral=True
        )
        data = _load_data()
        info = data.get(str(interaction.channel_id), {})
        owner = interaction.guild.get_member(info.get("owner_id", 0)) or interaction.user
        embed = build_dashboard_embed(interaction.channel, owner, data)
        pins = await interaction.channel.pins()
        for msg in pins:
            if msg.author == interaction.client.user and msg.embeds and msg.embeds[0].title == DASHBOARD_TITLE:
                await msg.edit(embed=embed)
                break


class TopicModal(discord.ui.Modal, title="ตั้งหัวข้อช่อง"):
    topic = discord.ui.TextInput(
        label="หัวข้อช่อง",
        style=discord.TextStyle.paragraph,
        placeholder="ช่องนี้เกี่ยวกับอะไร?",
        max_length=1024,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.channel.edit(topic=self.topic.value or None)
        await interaction.response.send_message(
            "✅ อัปเดตหัวข้อแล้ว", ephemeral=True
        )
        data = _load_data()
        info = data.get(str(interaction.channel_id), {})
        owner = interaction.guild.get_member(info.get("owner_id", 0)) or interaction.user
        embed = build_dashboard_embed(interaction.channel, owner, data)
        pins = await interaction.channel.pins()
        for msg in pins:
            if msg.author == interaction.client.user and msg.embeds and msg.embeds[0].title == DASHBOARD_TITLE:
                await msg.edit(embed=embed)
                break


class AddMemberModal(discord.ui.Modal, title="เพิ่มสมาชิก"):
    member_input = discord.ui.TextInput(
        label="User ID หรือ @mention",
        placeholder="123456789012345678",
        max_length=30,
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.member_input.value.strip().strip("<@!>")
        try:
            member = interaction.guild.get_member(int(raw))
            if member is None:
                member = await interaction.guild.fetch_member(int(raw))
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("❌ ไม่พบสมาชิก", ephemeral=True)
            return

        await interaction.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        )
        await interaction.response.send_message(
            f"✅ เพิ่ม {member.mention} เข้าช่องแล้ว", ephemeral=True
        )
        data = _load_data()
        info = data.get(str(interaction.channel_id), {})
        owner = interaction.guild.get_member(info.get("owner_id", 0)) or interaction.user
        embed = build_dashboard_embed(interaction.channel, owner, data)
        pins = await interaction.channel.pins()
        for msg in pins:
            if msg.author == interaction.client.user and msg.embeds and msg.embeds[0].title == DASHBOARD_TITLE:
                await msg.edit(embed=embed)
                break


class RemoveMemberModal(discord.ui.Modal, title="ลบสมาชิก"):
    member_input = discord.ui.TextInput(
        label="User ID หรือ @mention",
        placeholder="123456789012345678",
        max_length=30,
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.member_input.value.strip().strip("<@!>")
        try:
            member = interaction.guild.get_member(int(raw))
            if member is None:
                member = await interaction.guild.fetch_member(int(raw))
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("❌ ไม่พบสมาชิก", ephemeral=True)
            return

        data = _load_data()
        info = data.get(str(interaction.channel_id), {})
        if member.id == info.get("owner_id"):
            await interaction.response.send_message("❌ ไม่สามารถลบเจ้าของช่องได้", ephemeral=True)
            return

        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(
            f"✅ ลบ {member.mention} ออกจากช่องแล้ว", ephemeral=True
        )
        owner = interaction.guild.get_member(info.get("owner_id", 0)) or interaction.user
        embed = build_dashboard_embed(interaction.channel, owner, data)
        pins = await interaction.channel.pins()
        for msg in pins:
            if msg.author == interaction.client.user and msg.embeds and msg.embeds[0].title == DASHBOARD_TITLE:
                await msg.edit(embed=embed)
                break


class TransferOwnerModal(discord.ui.Modal, title="โอนความเป็นเจ้าของ"):
    member_input = discord.ui.TextInput(
        label="User ID ของเจ้าของคนใหม่",
        placeholder="123456789012345678",
        max_length=30,
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.member_input.value.strip().strip("<@!>")
        try:
            member = interaction.guild.get_member(int(raw))
            if member is None:
                member = await interaction.guild.fetch_member(int(raw))
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("❌ ไม่พบสมาชิก", ephemeral=True)
            return

        data = _load_data()
        info = data.get(str(interaction.channel_id), {})
        info["owner_id"] = member.id
        data[str(interaction.channel_id)] = info
        _save_data(data)

        await interaction.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True,
            read_message_history=True,
        )

        await interaction.response.send_message(
            f"✅ โอนความเป็นเจ้าของให้ {member.mention} แล้ว", ephemeral=True
        )
        embed = build_dashboard_embed(interaction.channel, member, data)
        pins = await interaction.channel.pins()
        for msg in pins:
            if msg.author == interaction.client.user and msg.embeds and msg.embeds[0].title == DASHBOARD_TITLE:
                await msg.edit(embed=embed)
                break


class PurgeModal(discord.ui.Modal, title="ลบข้อความจำนวนมาก"):
    amount = discord.ui.TextInput(
        label="จำนวนข้อความที่ต้องการลบ",
        placeholder="50",
        max_length=4,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            count = int(self.amount.value)
            if count < 1 or count > 1000:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ กรุณาใส่ตัวเลขระหว่าง 1 ถึง 1000", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=count)
        await interaction.followup.send(f"🧹 ลบข้อความไปแล้ว **{len(deleted)}** ข้อความ", ephemeral=True)

        data = _load_data()
        info = data.get(str(interaction.channel_id), {})
        pins = await interaction.channel.pins()
        dashboard_exists = any(
            m.author == interaction.client.user and m.embeds and m.embeds[0].title == DASHBOARD_TITLE
            for m in pins
        )
        if not dashboard_exists and info:
            owner = interaction.guild.get_member(info.get("owner_id", 0)) or interaction.user
            embed = build_dashboard_embed(interaction.channel, owner, data)
            view = DashboardView()
            msg = await interaction.channel.send(embed=embed, view=view)
            await msg.pin()


class ConfirmDeleteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="ใช่ ลบเลย", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = _load_data()
        channel_id = str(interaction.channel_id)
        if channel_id in data:
            del data[channel_id]
            _save_data(data)
        channel = interaction.channel
        await interaction.response.send_message("ช่องจะถูกลบใน 3 วินาที…", ephemeral=True)
        await asyncio.sleep(3)
        await channel.delete(reason=f"ลบโดยเจ้าของช่อง {interaction.user}")

    @discord.ui.button(label="ยกเลิก", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("ยกเลิกแล้ว ✅", ephemeral=True)
        self.stop()


async def _create_channel_for_user(
    interaction: discord.Interaction,
    *,
    already_deferred: bool = False,
) -> None:
    guild = interaction.guild
    if guild is None:
        if not already_deferred:
            await interaction.response.send_message(
                "คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True
            )
        return

    if not already_deferred:
        await interaction.response.defer(ephemeral=True)

    guild_config = _get_guild_config(guild.id)
    category_id = guild_config.get("category_id")
    category = None
    if category_id:
        category = guild.get_channel(int(category_id))

    channel_name = f"ช่องของ{interaction.user.display_name}"

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False,
            send_messages=False,
            read_message_history=False,
        ),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True,
            manage_permissions=True,
            read_message_history=True,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True,
            read_message_history=True,
        ),
    }

    channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        category=category,
    )

    data = _load_data()
    data[str(channel.id)] = {
        "owner_id": interaction.user.id,
        "visibility": "Private",
    }
    _save_data(data)

    embed = build_dashboard_embed(channel, interaction.user, data)
    view = DashboardView()
    dashboard_msg = await channel.send(embed=embed, view=view)
    await dashboard_msg.pin()

    try:
        dm_embed = discord.Embed(
            title="🎉 สร้างช่องใหม่สำเร็จ!",
            description=(
                f"ช่องของคุณพร้อมใช้งานแล้ว\n\n"
                f"📌 **ช่อง:** {channel.mention}\n"
                f"🔗 **ลิงก์:** https://discord.com/channels/{guild.id}/{channel.id}\n\n"
                f"คุณเป็นเจ้าของช่องนี้ ใช้แดชบอร์ดในช่องเพื่อจัดการทุกอย่างได้เลย!"
            ),
            color=0x57F287,
        )
        await interaction.user.send(embed=dm_embed)
    except discord.Forbidden:
        pass

    msg = await interaction.followup.send(
        f"✅ สร้างช่อง {channel.mention} แล้ว! คุณเป็นเจ้าของ",
        ephemeral=True,
    )
    await asyncio.sleep(5)
    try:
        await msg.delete()
    except discord.NotFound:
        pass


class ChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create", description="สร้างช่องส่วนตัวใหม่ที่คุณเป็นเจ้าของ")
    async def create_channel(self, interaction: discord.Interaction):
        await _create_channel_for_user(interaction)

    @app_commands.command(name="setup", description="ตั้งค่าระบบสร้างช่อง (สำหรับแอดมิน)")
    @app_commands.describe(
        category="หมวดหมู่ที่จะสร้างช่องใหม่ข้างใน",
        button_channel="ช่องที่จะส่งปุ่ม 'สร้างช่อง' ไป",
    )
    @app_commands.default_permissions(administrator=True)
    async def setup_command(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
        button_channel: discord.TextChannel,
    ):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        config = _load_server_config()
        config[str(guild.id)] = {
            "category_id": category.id,
            "button_channel_id": button_channel.id,
        }
        _save_server_config(config)

        create_embed = discord.Embed(
            title="✨ สร้างช่องส่วนตัวของคุณ",
            description=(
                "กดปุ่มด้านล่างเพื่อสร้างช่องส่วนตัวใหม่!\n\n"
                "📁 ช่องจะถูกสร้างในหมวดหมู่ที่กำหนดไว้\n"
                "👑 คุณจะเป็นเจ้าของช่องและสามารถจัดการได้ทุกอย่าง\n"
                "🎛️ แดชบอร์ดควบคุมจะถูกส่งอัตโนมัติในช่องใหม่"
            ),
            color=0x57F287,
        )
        create_embed.set_footer(text=f"หมวดหมู่: {category.name}")

        view = CreateChannelView()
        await button_channel.send(embed=create_embed, view=view)

        await interaction.followup.send(
            f"✅ ตั้งค่าเสร็จแล้ว!\n\n"
            f"📁 **หมวดหมู่:** {category.mention}\n"
            f"📌 **ช่องปุ่มสร้าง:** {button_channel.mention}\n\n"
            f"ปุ่มสร้างช่องถูกส่งไปยัง {button_channel.mention} แล้ว",
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        data = _load_data()
        cid = str(channel.id)
        if cid in data:
            del data[cid]
            _save_data(data)

    async def cog_load(self):
        self.bot.add_view(DashboardView())
        self.bot.add_view(CreateChannelView())


async def setup(bot):
    await bot.add_cog(ChannelManager(bot))
