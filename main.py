import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

# =========================
# Load Environment
# =========================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables")

# =========================
# Logging
# =========================
handler = logging.FileHandler(
    filename="discord.log",
    encoding="utf-8",
    mode="w"
)

# =========================
# Intents (ONE TIME)
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# Config
# =========================
CONFIG = {
    "DUO_CHANNEL_ID": 1139607940232384524,
    "SQUAD_CHANNEL_ID": 1462581501613969408,
    "TEAM_CHANNEL_ID": 1462581604000989298,
    "CATEGORY_ID": None
}


active_channels = set()
channel_owners = {}

# =========================
# Events
# =========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and (not before.channel or before.channel.id != after.channel.id):
        await handle_join(member, after.channel)

    if before.channel and (not after.channel or before.channel.id != after.channel.id):
        await handle_leave(member, before.channel)

async def handle_join(member, channel):
    limit = 0
    prefix = ""

    if channel.id == CONFIG["DUO_CHANNEL_ID"]:
        limit, prefix = 2, "DUO"
    elif channel.id == CONFIG["SQUAD_CHANNEL_ID"]:
        limit, prefix = 4, "SQUAD"
    elif channel.id == CONFIG["TEAM_CHANNEL_ID"]:
        limit, prefix = 10, "TEAM"
    else:
        return

    guild = member.guild
    category = guild.get_channel(CONFIG["CATEGORY_ID"]) if CONFIG["CATEGORY_ID"] else channel.category

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            connect=True,
            speak=True,
            use_soundboard=True,
            use_embedded_activities=True,
            use_voice_activation=True,
            stream=True,
        ),
        member: discord.PermissionOverwrite(
            connect=True,
            speak=True,
            use_soundboard=True,
            use_embedded_activities=True,
            use_voice_activation=True,
            stream=True,
        ),
        guild.me: discord.PermissionOverwrite(
            connect=True,
            speak=True,
            use_soundboard=True,
            use_embedded_activities=True,
            use_voice_activation=True,
            stream=True,
        )
        }
    
    try:
        # Create the voice channel
        new_channel = await guild.create_voice_channel(
            name=f"{member.name} - {prefix}",
            category=category,
            user_limit=limit,
            overwrites=overwrites
        )

        await member.move_to(new_channel)

        # Track the channel and owner
        active_channels.add(new_channel.id)
        channel_owners[new_channel.id] = member.id

        # ----------------------------
        # Send VC help embed
        # ----------------------------

        # Option 1: Send in a fixed text channel in the same category
        text_channel = None
        for ch in category.active_channels:
            text_channel = ch
            break

        if text_channel is not None:
            embed = discord.Embed(
                title="🔊 Voice Channel Commands",
                description="Here are the commands you can use for managing your temporary voice channel:",
                color=0x3498db
            )

            embed.add_field(name="!vc-limit <n>", value="Set the user limit for your channel", inline=False)
            embed.add_field(name="!vc-transfer @user", value="Transfer ownership to another member", inline=False)
            embed.add_field(name="!vc-claim", value="Claim ownership if the current owner is inactive", inline=False)
            embed.add_field(name="!vc-owner", value="Show the current owner of the channel", inline=False)
            embed.add_field(name="!vc-kick @user", value="Kick a member from the channel", inline=False)
            embed.add_field(name="!vc-ban @user", value="Ban a member from your channel", inline=False)
            embed.add_field(name="!vc-uban @user", value="Unban a previously banned member", inline=False)
            embed.add_field(
                name="Notes",
                value="• Commands only work in this channel’s chat.\n• Make sure you have the necessary permissions to manage the channel.",
                inline=False
            )

            await text_channel.send(embed=embed)

    except Exception as e:
        print(f"❌ Error creating VC: {e}")

async def handle_leave(member, channel):
    if channel.id in active_channels and len(channel.members) == 0:
        try:
            await channel.delete()
            active_channels.discard(channel.id)
            channel_owners.pop(channel.id, None)
        except Exception as e:
            print(f"❌ Error deleting VC: {e}")

# =========================
# Helpers
# =========================
def get_user_vc(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        return None
    return ctx.author.voice.channel

def is_vc_owner():
    async def predicate(ctx):
        vc = get_user_vc(ctx)

        if not vc:
            await ctx.send("❌ You must be in your voice channel.")
            return False

        if vc.id not in active_channels:
            await ctx.send("❌ This is not a managed voice channel.")
            return False

        if channel_owners.get(vc.id) != ctx.author.id:
            await ctx.send("❌ Only the channel owner can use this.")
            return False

        return True
    return commands.check(predicate)


# =========================
# Commands
# =========================
@bot.command(name="vc-limit")
@is_vc_owner()
async def vc_limit(ctx, n: int):
    vc = get_user_vc(ctx)
    await vc.edit(user_limit=n)
    await ctx.send(f"✅ User limit set to **{n}**")


@bot.command(name="vc-transfer")
@is_vc_owner()
async def vc_transfer(ctx, member: discord.Member):
    vc = get_user_vc(ctx)

    if member not in vc.members:
        await ctx.send("❌ User must be in the voice channel.")
        return

    channel_owners[vc.id] = member.id

    await vc.set_permissions(member, manage_channels=True, move_members=True)
    await vc.set_permissions(ctx.author, manage_channels=False, move_members=False)

    await ctx.send(f"👑 Ownership transferred to {member.mention}")

@bot.command(name="vc-claim")
async def vc_claim(ctx):
    vc = get_user_vc(ctx)

    if not vc or vc.id not in active_channels:
        return

    owner_id = channel_owners.get(vc.id)
    owner = ctx.guild.get_member(owner_id) if owner_id else None

    if owner and owner in vc.members:
        await ctx.send("❌ Owner is still in the channel.")
        return

    channel_owners[vc.id] = ctx.author.id
    await vc.set_permissions(ctx.author, manage_channels=True, move_members=True)

    await ctx.send("👑 You have claimed ownership.")

@bot.command(name="vc-owner")
async def vc_owner(ctx):
    vc = get_user_vc(ctx)

    if not vc or vc.id not in active_channels:
        return

    owner_id = channel_owners.get(vc.id)
    owner = ctx.guild.get_member(owner_id) if owner_id else None

    await ctx.send(f"👑 Current owner: {owner.mention if owner else 'Unknown'}")


@bot.command(name="vc-kick")
@is_vc_owner()
async def vc_kick(ctx, member: discord.Member):
    vc = get_user_vc(ctx)

    if member not in vc.members:
        await ctx.send("❌ User is not in your voice channel.")
        return

    await member.move_to(None)
    await ctx.send(f"👞 Kicked {member.mention}")

@bot.command(name="vc-ban")
@is_vc_owner()
async def vc_ban(ctx, member: discord.Member):
    vc = get_user_vc(ctx)

    await vc.set_permissions(member, connect=False)

    if member in vc.members:
        await member.move_to(None)

    await ctx.send(f"🚫 Banned {member.mention} from the channel.")


@bot.command(name="vc-uban")
@is_vc_owner()
async def vc_uban(ctx, member: discord.Member):
    vc = get_user_vc(ctx)

    await vc.set_permissions(member, overwrite=None)
    await ctx.send(f"✅ Unbanned {member.mention}")


@bot.command()
async def chup(ctx, member: discord.Member):
    await ctx.send(f"Chup muji {member.mention}")

@bot.command()
async def sorry(ctx, member: discord.Member):
    embed = discord.Embed()
    embed.set_image(url="https://c.tenor.com/xcWphzVquJ8AAAAd/tenor.gif")
    await ctx.send(content=member.mention, embed=embed)

# =========================
# Message Moderation
# =========================
BAD_WORDS = {"lado", "machikney", "randi", "rando", "turi"}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Let commands through first
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    if message.content.lower().startswith("hello"):
        await message.channel.send(f"Hello {message.author.mention}!")

    if any(word in message.content.lower() for word in BAD_WORDS):
        try:
            await message.delete()
        except:
            pass

        embed = discord.Embed()
        embed.set_image(url="https://c.tenor.com/KZF6Cke4FH4AAAAd/tenor.gif")
        await message.channel.send(message.author.mention, embed=embed)

# =========================
# Run
# =========================
bot.run(TOKEN)
