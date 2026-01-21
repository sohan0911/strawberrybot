import os
import logging
import discord
import random
import re
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
    "DUO_CHANNEL_ID": 1462581424153559165,
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
        active_channels.add(new_channel.id)
        channel_owners[new_channel.id] = member.id
        
        embed = discord.Embed(
            title="🔊 Temporary Voice Channel Created", 
            description=f"Welcome, {member.mention}! You are the owner of this channel.", 
            color=0x3498db
        )
        embed.add_field(name="Available Commands", value=(
            "`!vc-limit <n>` - Set user limit\n"
            "`!vc-transfer @user` - Transfer ownership\n"
            "`!vc-claim` - Claim ownership\n"
            "`!vc-owner` - Show current owner\n"
            "`!vc-kick @user` - Kick a user\n"
            "`!vc-ban @user` - Ban a user\n"
            "`!vc-uban @user` - Unban a user\n"
            "`!vc-lock` - Lock the channel\n"
            "`!vc-unlock` - Unlock the channel"
        ), inline=False)
        embed.set_footer(text="Commands only work in this channel's chat.")
        
        await new_channel.send(embed=embed)

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

@bot.command(name="vc-lock")
@is_vc_owner()
async def vc_lock(ctx):
    channel = ctx.author.voice.channel if ctx.author.voice else None

    if not channel or channel.id not in active_channels:
        return await ctx.send("❌ You must be in your temporary voice channel.")

    await channel.set_permissions(
        ctx.guild.default_role,
        connect=False
    )

    await ctx.send("🔒 Voice channel locked. No one else can join.")

@bot.command(name="vc-unlock")
@is_vc_owner()
async def vc_unlock(ctx):
    channel = ctx.author.voice.channel if ctx.author.voice else None

    if not channel or channel.id not in active_channels:
        return await ctx.send("❌ You must be in your temporary voice channel.")

    await channel.set_permissions(
        ctx.guild.default_role,
        connect=True
    )

    await ctx.send("🔓 Voice channel unlocked. Anyone can join.")

@bot.command()
async def chup(ctx, member: discord.Member):
    await ctx.send(f"Chup muji {member.mention}")

@bot.command()
async def sut(ctx, member: discord.Member):
    await ctx.send(f"sut muji {member.mention}")

@bot.command()
async def sorry(ctx, member: discord.Member):
    embed = discord.Embed()
    embed.set_image(url="https://c.tenor.com/xcWphzVquJ8AAAAd/tenor.gif")
    await ctx.send(content=member.mention, embed=embed)

ROASTS = [
    "yo momma so old her birth certificate says expired",
    "yo momma so poor when i saw her kickin a can down the street i asked what she was doin she said movin",
    "yo momma so ugly she made u",
    "yo momma so stupid she put airbags on her computer in case it crashed",
    "yo momma so fat when she skips a meal the stock market drops",
    "yo momma so lazy she stuck her nose out the window and let the wind blow it",
    "yo momma so dumb she thought a quarterback was a refund",
    "yo momma so poor she can't even pay attention",
    "yo momma so fat when she goes to the beach the whales sing 'we are family'",
    "yo momma so ugly when she tried to join an ugly contest they said sorry not today",
    "You must have a Ph.D. in stupidology.",
    "You are like a software update. Every time I see you, I immediately think, 'Not now.'",
    "All mistakes are fixable—except for you.",
    "You’re the reason the divorce rate is so high.",
    "If I don’t answer you the first time, what makes you think the next 25 will work?",
    "I gave out all my trophies a while ago, but here’s a participation award.",
    "A glowstick has a brighter future than you.",
    "It’s sad what happened to your face. Oh, wait, that’s how it’s always looked?",
    "I’m listening. I just need a minute to process so much stupid information at once.",
    "When I look at you, I think, 'Where have you been my whole life? And can you go back there?'",
    "Beauty is only skin deep, but ugly goes clean to the bone.",
    "I would agree with you, but then we’d both be wrong.",
    "You look like something that came out of a slow cooker.",
    "It would be a great day if you accidentally used a glue stick instead of a Chapstick.",
    "I bet I could remove 90 percent of your good looks with a moist towelette.",
    "You’re so fake, even Barbie is jealous.",
    "I suggest you do a little soul-searching—you may actually find one.",
    "I know I make a lot of stupid choices, but hanging out with you was the worst of them all.",
    "Stupidity isn’t a crime, so you’re free to go.",
    "I was going to make a joke about your life, but I see life beat me to the punch.",
    "It must be fun to wake up each morning knowing that you are that much closer to achieving your dreams of complete and utter mediocrity.",
    "The truth will set you free: you’re the worst. Okay, you’re free to go.",
    "You remind me of the end pieces of a loaf of bread—nobody wants you.",
    "Calling you an idiot would be an insult to stupid people. You’re much worse than that.",
    "It’s a parent’s job to raise their children right. So, looking at you, it’s obvious that yours quit after just one day.",
    "You’re so fat, the photo I took of you last Christmas is still printing.",
    "Your birth certificate needs to be rewritten as a letter of apology.",
    "It must be nice to never use your brain.",
    "Hey, don’t stand too close to the fire. Plastic melts, you know.",
    "I’ll never forget the first time we met each other—but I promise I’ll keep trying.",
    "You’re just like a broken pencil—totally pointless.",
    "If idiots could fly, your house would be an airport.",
    "You bring everyone so much joy, especially when you leave a room.",
    "You have miles to go before you reach mediocre.",
    "You say I look ugly today? Good, I was trying to look like you.",
    "You’re dumber than a rock. At least a rock can hold a door open. What can you do?",
    "I used to believe in evolution until I met you. Now I’m not so sure.",
    "Don’t worry about me. Just worry about your eyebrows.",
    "I promise I’m not insulting you, I’m just describing you.",
    "I’d love to stay and chat, but I’d rather have open-heart surgery.",
    "Your face looks like something I’d draw with my left hand.",
    "You’re the reason that tubes of toothpaste have instructions on them.",
    "Uh oh! I smell smoke… are you thinking too hard again?",
    "Look on the bright side, if genius skips a generation, your kids will be absolutely brilliant.",
    "If I throw a stick for you, will you leave?",
    "I am unwilling to have a battle of wits with an unarmed opponent like yourself.",
    "The closest you’ll ever come to a brainstorm is a light drizzle.",
    "I don’t have the time (or enough crayons) to explain this to you.",
    "Congrats on getting your PhD in annoyance.",
    "If I had just one wish, it would be that you step on a LEGO while barefoot today."
    ]


@bot.command()
async def roast(ctx, member: discord.Member):
    if member.bot:
        await ctx.send("🤖 Roasting bots is unfair… they have feelings too.")
        return

    roast = random.choice(ROASTS)
    await ctx.send(f"🔥 {member.mention} {roast}")


RIZZ = [
    "Timro nickname ta blanket hola hai, herdai patyau patyau lagne raixau. https://c.tenor.com/lkXE8nvV6JsAAAAd/tenor.gif",
    "Are you Bhimsen Thapa ?? because you just erected my dharahara https://c.tenor.com/hlXzfw9TqK8AAAAd/tenor.gif",
    "hamlai pani maya le hera na parbatiiiii https://c.tenor.com/Rd8FQYPG2EwAAAAd/tenor.gif",
    "Are you Rajesh Hamal? Cuz, every time I see you I just want to say HEYY!!! https://c.tenor.com/vRs8EyzQvY4AAAAd/tenor.gif",
    "Bango bango thiye, sidha bhaye ma. Timilai dekhera fida bhaye ma. Bhannu ta dherai thiyo, tara aaile chai muji bhandai bida bhaye ma. https://c.tenor.com/SJbT1KH73loAAAAd/tenor.gif",
    "Andi Mandi Jhandi Jo Mero Girlfriend Hudaina Tyo ____. https://c.tenor.com/ZARBViZffU4AAAAd/tenor.gif",
    "Are you Mommy ko kuchho, cause you hit different? https://c.tenor.com/OfbnNJxQWLkAAAAd/tenor.gif",
    "Timi vayena vane ta chini haleko chiya pani mitho hunna https://c.tenor.com/e0X4v3Y16xYAAAAd/tenor.gif",
    "I am not an insurance agent, but will you beema girl? https://c.tenor.com/DGqcg27wcqEAAAAd/tenor.gif",
    "Timi sirak ta haina, tara herdai pattauna manlagyo https://c.tenor.com/14v-uu0p2zkAAAAd/tenor.gif",
    "Timro photo pathau na, ma taas kheldai thiye, mero Rani nei harayo k https://c.tenor.com/kCsgnAmVWSQAAAAd/tenor.gif",
    "Are you from Samakhusi? Cause you made my Ama Khusi! https://c.tenor.com/ysITqa52me8AAAAd/tenor.gif",
    "Are you dozer? I can stare you all day! https://c.tenor.com/E0V4tZA72HIAAAAd/tenor.gif",
    "If you have two kids in future and i also have two kids how many total kids we will have? (She will say 4) Nah just two https://c.tenor.com/SJlh3ytXmzMAAAAd/tenor.gif",
    "Are you Kathmandu? Cause you took my breath away! https://c.tenor.com/8VXRYGhuKFAAAAAd/tenor.gif",
    "I am gonna love you till the Melamchi ko pani arrived! (Sadly it’s here) https://c.tenor.com/Iga6pdXRmJgAAAAd/tenor.gif",
    "Is your dad biplov? Cause you are a bomb? https://c.tenor.com/4NYOBe8vcqYAAAAd/tenor.gif",
    "Your eyes are Patan ko galli, I keep getting lost in them. https://c.tenor.com/LHapB3z7oKEAAAAd/tenor.gif",
    "Timilai sugar lagxa vanera matra ho natra mitho mitho guff hanna malai ni auxa https://c.tenor.com/QqFAbHAdhckAAAAd/tenor.gif",
    "Are you Momo? Cause I wanna eat you Gwamma! https://c.tenor.com/4-HxN-cvB5sAAAAd/tenor.gif",
    "(She: Hawa timi) You called me Hawa, I don’t think you can live without it. https://c.tenor.com/rdkHWmsaP5sAAAAd/tenor.gif",
    "Ani khana Khayou ta? https://c.tenor.com/l8vCgpAK2H8AAAAd/tenor.gif",
    "Girl everytime I see you I feel like Aasok darji. Cuz timi vanda ramri koi chaina sansar mai. https://c.tenor.com/GQ66j05SZA8AAAAd/tenor.gif",
    "Raksi ta esai badnam xa, asli nasa ta timro ankha ma xa! https://c.tenor.com/iMZrys9vF5AAAAAd/tenor.gif",
    "We go together like daal and bhaat! https://c.tenor.com/Et5Mnh02jsIAAAAd/tenor.gif",
    "Did you call pathao? Cause I am here to pick you up! https://c.tenor.com/UGKQ56JfNLYAAAAd/tenor.gif",
    "I am gonna leave you like Bagmati; wet, dirty and constantly flowing. https://c.tenor.com/v6SFpiB8oNIAAAAd/tenor.gif"
]

TENOR_REGEX = r"(https?://\S+\.gif)"

def create_rizz_embed(author: discord.Member):
    rizz = random.choice(RIZZ)

    gif = None
    match = re.search(TENOR_REGEX, rizz)
    if match:
        gif = match.group(1)
        rizz = rizz.replace(gif, "").strip()

    embed = discord.Embed(
        description=rizz,
        color=0xff4d6d
    )
    embed.set_footer(text=f"Rizz dropped by {author.display_name}")

    if gif:
        embed.set_image(url=gif)

    return embed


@bot.command()
async def rizz(ctx, member: discord.Member = None):
    embed = create_rizz_embed(ctx.author)

    if member:
        await ctx.send(content=member.mention, embed=embed)
    else:
        await ctx.send(embed=embed)


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

