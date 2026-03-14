from email.mime import message
import os
import logging
import discord
import random
import re
from discord.ext import commands
from dotenv import load_dotenv
import threading
from flask import Flask
import threading
import time
import json
import requests
import aiohttp
import google.generativeai as genai
# =========================
# Load Environment
# =========================
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
ZENSERP_API_KEY = os.getenv("ZENSERP_API_KEY")
USERS_FILE = "users.json"
vc_tracking = {}
xp_cooldowns = {}

def create_xp_bar(current_xp, required_xp, bar_length=15):
    percent = current_xp / required_xp
    filled_length = int(bar_length * percent)

    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    percentage = int(percent * 100)

    return bar, percentage


def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables")

LEVELS_FILE = "levels.json"
import math

def xp_required(level):
    return int(50 * (level ** 1.5))

def load_levels():
    if not os.path.exists(LEVELS_FILE):
        return {}
    with open(LEVELS_FILE, "r") as f:
        return json.load(f)

def save_levels(data):
    with open(LEVELS_FILE, "w") as f:
        json.dump(data, f, indent=4)

levels = load_levels()

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

active_channels = set()
channel_owners = {}

# =========================
# Events
# =========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

    
@bot.event
async def on_member_join(member):
    General_id = 1480002705945788558
    emoji = bot.get_emoji(1480623628516069399)
    channel = bot.get_channel(General_id)
    await channel.send(f"*Welcome {member.mention}* ! {emoji}")

@bot.command()
async def chup(ctx, member: discord.Member):
    await ctx.send(f"Chup muji {member.mention}")

@bot.command()
async def sut(ctx, member: discord.Member):
    await ctx.send(f"sut muji {member.mention}")

@bot.command()
async def sorry(ctx, member: discord.Member):
    embed = discord.Embed()
    embed.set_image(url="https://c.tenor.com/WpXfUhL-rZQAAAAd/tenor.gif")
    await ctx.send(content=f"Sorry!! {member.mention}", embed=embed)

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


Fluffy = [
    903299362912890891,
    1139607940232384524,
    1459529835331321981
]

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    mommy = bot.get_emoji(1481001314845724802)
    content = message.content.lower()
    
    for word in Fluffy:
        if content == "mommy" and message.author.id == word:
            await message.channel.send(f"hi <@1459629173604749524> {mommy}")

    if content == "good boy" and message.author.id == 1459629173604749524:
        await message.channel.send("<@1139607940232384524>") 
           
    
    await bot.process_commands(message)

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def google(ctx, *, query: str):
    async with ctx.channel.typing():
        try:
            url = "https://app.zenserp.com/api/v2/search"
            params = {
                "q": query,
                "apikey": ZENSERP_API_KEY,
                "gl": "us",
                "hl": "en",
                "num": 5
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        await ctx.send(f"❌ Zenserp API error {resp.status}")
                        print(error_text)
                        return

                    data = await resp.json()

            organic = data.get("organic")
            if not organic:
                await ctx.send("❌ No results found.")
                return

            message = f"🔎 **Results for:** {query}\n\n"

            for i, result in enumerate(organic[:5], 1):
                title = result.get("title", "No title")
                link = result.get("url", "No link")
                message += f"**{i}.** {title}\n{link}\n\n"

            if len(message) > 2000:
                message = message[:1990] + "..."

            await ctx.send(message)

        except Exception as e:
            print("Zenserp error:", e)
            # Only send error if nothing else was sent
            if not ctx.channel.last_message or ctx.channel.last_message.author != bot.user:
                await ctx.send("❌ Something went wrong while searching.")

ALLOWED_CHANNEL_ID = 1475925227816091900


# 🔒 Channel restriction check
def is_allowed_channel():
    async def predicate(ctx):
        if ctx.channel.id != ALLOWED_CHANNEL_ID:
            await ctx.send("❌ This command only works in the singers channel.")
            return False
        return True
    return commands.check(predicate)


# 🎤 REGISTER COMMAND
@bot.command()
@is_allowed_channel()
async def register(ctx,member: discord.Member ):
    users = load_users()

    user_id = str(member.id)

    if user_id in users:
        await ctx.send("⚠️ You are already registered.")
        return

    users.append(user_id)
    save_users(users)

    await ctx.send(f"✅ {member.mention} has been registered!")


# 📋 SINGERS LIST (EMBED)
@bot.command()
@is_allowed_channel()
async def participantslist(ctx):
    users = load_users()

    if not users:
        await ctx.send("No one is registered yet.")
        return

    embed = discord.Embed(
        title="🎤 Registered Singers",
        color=0x3498db
    )

    description = ""

    for index, user_id in enumerate(users):
        try:
            user = await bot.fetch_user(int(user_id))
            description += f"**{index + 1}.** {user.name}\n"
        except:
            description += f"**{index + 1}.** Unknown User\n"

    embed.description = description
    embed.set_footer(text="Commands only work in this channel.")

    await ctx.send(embed=embed)


# ❌ REMOVE USER COMMAND
@bot.command()
@is_allowed_channel()
async def remove(ctx, member: discord.Member):
    users = load_users()
    user_id = str(member.id)

    if user_id not in users:
        await ctx.send("❌ That user is not registered.")
        return

    users.remove(user_id)
    save_users(users)

    await ctx.send(f"🗑️ {member.mention} has been removed from the list.")


@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_id = str(member.id)

    if user_id not in levels:
        levels[user_id] = {"xp": 0, "level": 1}
        save_levels(levels)

    xp = levels[user_id]["xp"]
    level = levels[user_id]["level"]
    xp_needed = level * 100

    bar, percentage = create_xp_bar(xp, xp_needed)

    embed = discord.Embed(
        title=f"{member.display_name}'s Profile",
        color=0x3498db
    )

    embed.add_field(name="⭐ Level", value=level, inline=True)
    embed.add_field(name="📊 XP", value=f"{xp}/{xp_needed}", inline=True)
    embed.add_field(
        name="Progress",
        value=f"`{bar}`\n{percentage}%",
        inline=False
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

@bot.command()
async def ai(ctx, *, prompt):
    await ctx.typing()

    try:
        response = model.generate_content(prompt)
        text = response.text
        # Discord message limit
        if len(text) > 2000:
            text = text[:1990] + "..."

        await ctx.reply(text)

    except Exception as e:
        await ctx.reply(f"Error: {e}")

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

bot.run(TOKEN)

