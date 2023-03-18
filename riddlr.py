import os
import random
import discord
import openai
import requests
import signal
import sys
from bs4 import BeautifulSoup
from discord.ext import commands, tasks
from collections import defaultdict

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='!', intents=intents)

# Store users' scores
user_scores = defaultdict(int)

# Store current riddle answer
current_answer = ""

# Store the number of correct answers for the current riddle
correct_answers_count = 0

# Function to fetch random Wikipedia article and return its title and overview
def fetch_random_wikipedia_article():
    # Get a random Wikipedia article
    url = 'https://en.wikipedia.org/wiki/Special:Random'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    title = soup.find('h1', {'id': 'firstHeading'}).text
    overview = ' '.join([p.text for p in soup.find('div', {'class': 'mw-parser-output'}).find_all('p')[:2]])

    return title, overview

# Function to get riddle from ChatGPT API
async def get_riddle(overview):
    openai.api_key = OPENAI_API_KEY

    prompt = f"Generate a riddle or clue based on the following wikipedia overview do not supply the answer do not prefix the question with Q: {overview}"

    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=200,
        temperature=0.7,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    riddle = response.choices[0].text.strip()

    return riddle

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    daily_riddle.start()

@tasks.loop(hours=24)
async def daily_riddle():
    global current_answer, correct_answers_count
    title, overview = fetch_random_wikipedia_article()
    current_answer = title.lower()
    print(f"Today's riddle answer is: ({current_answer})")

    riddle = await get_riddle(overview)

    # Reset the correct_answers_count for the new riddle
    correct_answers_count = 0

    # Send riddle to a specific channel
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    await channel.send(f"Today's riddle is:\n{riddle}")
    await channel.send(f'Try and guess by DMing me the answer using the command `!answer "<answer>"`')

@bot.command(name='answer')
async def check_answer(ctx, url: str):
    # Check if the message was sent in a DM
    if isinstance(ctx.channel, discord.DMChannel):
        global user_scores, correct_answers_count
        if current_answer in url.lower() and correct_answers_count < 10:
            correct_answers_count += 1
            points_awarded = 11 - correct_answers_count
            user_scores[ctx.author.id] += points_awarded
            await ctx.send(f"Congratulations {ctx.author.mention}! You have earned {points_awarded} points!")
            channel = bot.get_channel(DISCORD_CHANNEL_ID)
            await channel.send(f"{ctx.author.mention} has gotten the answer to today's riddle earning {points_awarded} points!")
        elif correct_answers_count >= 10:
            await ctx.send(f"Sorry {ctx.author.mention}, the maximum number of correct answers for this riddle has been reached.")
        else:
            await ctx.send(f"Sorry {ctx.author.mention}, that's not the correct answer.")
    else:
        await ctx.send(f"{ctx.author.mention}, please send your answer via Direct Message to avoid spoiling the game for others.")

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    leaderboard_text = "Leaderboard:\n"
    for user_id, score in sorted_scores:
        user = await bot.fetch_user(user_id)
        leaderboard_text += f"{user.name}: {score} points\n"
    await ctx.send(leaderboard_text)

async def shutdown():
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    await channel.send("Shutting down...")
    await bot.close()

def signal_handler(sig, frame):
    print("Shutting down...")
    bot.loop.run_until_complete(shutdown())
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)
bot.run(TOKEN)
