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
current_riddle = ""

# Store current riddle answer
current_answer = ""

# Store the number of correct answers for the current riddle
correct_answers_count = 0

# number of guesses for current riddle
guesses = 0
cheaters_count = 0

# have correct answers
correct_users = []
cheaters = []

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
    print("Starting new riddle...")
    global current_answer, correct_answers_count, guesses, correct_users, cheaters_count, cheaters, current_riddle
    if current_answer != "":
        channel = bot.get_channel(DISCORD_CHANNEL_ID)
        await channel.send(f"Yesterday's riddle was: {current_riddle}\nand the answer is: {current_answer}.")
        await channel.send(f"There were {guesses} guesses made.\We had {correct_answers_count} correct answers, and {cheaters_count} cheaters.")
        ctx = await bot.get_context(channel.last_message)
        await leaderboard(ctx)

    title, overview = fetch_random_wikipedia_article()
    current_answer = title

    current_riddle = await get_riddle(overview)

    # Reset the correct_answers_count for the new riddle
    correct_answers_count = 0
    guesses = 0
    correct_users = []
    cheaters_count = 0
    cheaters = []

    # Send riddle to a specific channel
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    await channel.send(f"Today's riddle is:\n{current_riddle}")
    await channel.send(f'Try and guess by DMing me the answer using the command `!answer "<answer>"`')

@bot.command(name='riddle', help='Get the current riddle.')
async def the_riddle(ctx):
    global current_riddle
    await ctx.send(f"Here is today's riddle:\n{current_riddle}")

@bot.command(name='answer', help="(DM Only) Send your answer to the current riddle. Use quotes if your answer contains spaces")
async def check_answer(ctx, guess: str):
    # Check if the message was sent in a DM
    if isinstance(ctx.channel, discord.DMChannel):
        global user_scores, correct_answers_count, guesses, correct_users
        if ctx.author.id in correct_users:
            await ctx.send(f"{ctx.author.mention}, you have already answered this riddle correctly.")
            return
        guesses += 1
        if current_answer.lower() in guess.lower() and correct_answers_count < 6:
            correct_answers_count += 1
            points_awarded = 11 - correct_answers_count
            user_scores[ctx.author.id] += points_awarded
            correct_users.append(ctx.author.id)
            await ctx.send(f"Congratulations {ctx.author.mention}! You have earned {points_awarded} points!")
            channel = bot.get_channel(DISCORD_CHANNEL_ID)
            await channel.send(f"{ctx.author.mention} has gotten the answer to today's riddle earning {points_awarded} points!")
        elif correct_answers_count >= 5:
            await ctx.send(f"Sorry {ctx.author.mention}, the maximum number of correct answers for this riddle has been reached.")
        else:
            await ctx.send(f"Sorry {ctx.author.mention}, that's not the correct answer.")
    else:
        await ctx.send(f"{ctx.author.mention}, please send your answer via Direct Message to avoid spoiling the game for others.")

@bot.command(name='stats', help='Get the current stats for the current riddle.')
async def stats(ctx):
    global correct_answers_count, guesses, cheaters_count
    await ctx.send(f"Here are the current stats:\ncorrect answers: {correct_answers_count}\nguesses: {guesses}\ncheaters: {cheaters_count}")

@bot.command(name='cheatcode72', help='(DM only) Get the answer. Cheating can have consequences.')
async def check_answer(ctx):
    global cheaters, cheaters_count
    # Check if the message was sent in a DM
    if isinstance(ctx.channel, discord.DMChannel):
        global user_scores, current_answer
        if ctx.author.id in cheaters:
            await ctx.send(f"{ctx.author.mention}, you've already paid the price for cheating. The answer is: {current_answer}")
            return
        else:
            cheaters.append(ctx.author.id)
            cheaters_count += 1
        user_scores[ctx.author.id] -= 6
        await ctx.send(f"The answer is: {current_answer}\nAnd you've had 6 points deducted for cheating.")

@bot.command(name='leaderboard', help='Get the leaderboard for the lifetime of the current riddlr process.')
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
    await bot.logout()
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
