import os
import random
import discord
import openai
import requests
from bs4 import BeautifulSoup
from discord.ext import commands, tasks
from collections import defaultdict

TOKEN = 'your_bot_token'
OPENAI_API_KEY = 'your_openai_api_key'

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

    prompt = f"Generate a riddle or clue based on the following Wikipedia overview: {overview}"

    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.5,
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

    riddle = await get_riddle(overview)

    # Reset the correct_answers_count for the new riddle
    correct_answers_count = 0

    # Send riddle to a specific channel
    channel = bot.get_channel(YOUR_CHANNEL_ID)
    await channel.send(f"Today's riddle is:\n{riddle}")

@bot.command(name='answer')
async def check_answer(ctx, url: str):
    global user_scores, correct_answers_count
    if current_answer in url.lower() and correct_answers_count < 10:
        correct_answers_count += 1
        points_awarded = 11 - correct_answers_count
        user_scores[ctx.author.id] += points_awarded
        await ctx.send(f"Congratulations {ctx.author.mention}! You have earned {points_awarded} points!")
    elif correct_answers_count >= 10:
        await ctx.send(f"Sorry {ctx.author.mention}, the maximum number of correct answers for this riddle has been reached.")
    else:
        await ctx.send(f"Sorry {ctx.author.mention}, that's not the correct answer.")

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    leaderboard_text = "Leaderboard:\n"
    for user_id, score in sorted_scores:
        user = await bot.fetch_user(user_id)
        leaderboard_text += f"{user.name}: {score} points\n"
    await ctx.send(leaderboard_text)

