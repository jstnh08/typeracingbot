import asyncio
import time
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import discord
from discord.ext import commands
from colour import Color
from wonderwords import RandomWord

client = commands.Bot(command_prefix="t!", intents=discord.Intents.default()) #probably dont need intents but i havent tested without intents 
word_maker = RandomWord()


def calc_grade(num: int):
    if num < 60:
        return "F"
    if num >= 100:
        return "A++"

    grade_dict = {"6": "D", "7": "C", "8": "B", "9": "A"}
    grade = grade_dict[str(num)[0]]
    if int(str(num)[1]) <= 3:
        grade += "-"
    elif int(str(num)[1]) >= 7:
        grade += "+"
    return grade


def calc_accuracy(phrase_, response_):
    phrase = phrase_.lower().split(" ")
    response = response_.lower().split(" ")
    correct = 0
    words = []

    for word in response:
        if word == "":
            response.remove(word)

    add = 0
    for i in range(len(phrase)):
        try:
            if phrase[i] == response[i - (add + 1)]:
                add += 1
            if phrase[i] == response[i - add]:
                words.append(f"{phrase[i]}")
                correct += 1
                continue

        except IndexError:
            pass

        words.append(f"~~{phrase[i]}~~")

    accuracy = round((correct / len(phrase)) * 100)
    return accuracy, words


def get_color(grade):
    grade_index = {"f": 0, "d": 2, "c": 5, "b": 8, "a": 11, "a++": 13}
    index = grade_index[grade[0]]
    if len(grade) == 2:
        if grade[1] == "+":
            index += 1
        else:
            index -= 1

    red = Color("red")
    colors = list(red.range_to(Color("green"), 14))
    color = list(colors[index].get_rgb())
    color[2] = 0
    for i in range(len(color)):
        color[i] = round(color[i] * 255)
    return color[0], color[1], color[2]


def set_thumbnail(grade, embed, r, g, b):
    font = ImageFont.truetype("Jaldi/jaldi/Jaldi-Regular.ttf", 50)
    im = Image.new('RGBA', font.getsize(grade), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.text((0, 0), grade, font=font, fill=(r, g, b))
    buffer = BytesIO()
    im.save(buffer, format="PNG")
    buffer.seek(0)
    f = discord.File(buffer, filename="image.png")
    embed.set_thumbnail(url="attachment://image.png")
    return f, embed


def display_prompt(text):
    font = ImageFont.truetype("Jaldi/jaldi/Jaldi-Regular.ttf", 25)
    height = sum(font.getsize(line)[1] for line in textwrap.wrap(text, width=40)) + 10
    im = Image.new('RGBA', (450, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    margin = offset = 0
    for line in textwrap.wrap(text, width=40):
        draw.text((margin, offset), line, font=font, fill=(255, 255, 255))
        offset += font.getsize(line)[1]
    buffer = BytesIO()
    im.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def calc_scores(start_time, text, msg):
    time_elapsed = round(time.time() - start_time) / 60
    wpm = round(len(text.replace(" ", "")) / 5 / time_elapsed)
    accuracy, words = calc_accuracy(text, msg.content)
    netwpm = round(wpm * (accuracy / 100))
    return time_elapsed, wpm, accuracy, words, netwpm


def create_embed(ctx, accuracy, wpm, netwpm, words, r, g, b):
    embed = discord.Embed(colour=discord.Color.from_rgb(r, g, b))
    embed.set_author(name=f"{ctx.author.name}'s typing results", icon_url=ctx.author.avatar_url)
    embed.add_field(name="Accuracy", value=f"{accuracy}%")
    embed.add_field(name="WPM", value=f"{wpm}")
    embed.add_field(name="Net WPM", value=f"{netwpm}")
    embed.add_field(name="Sentence", value=" ".join(words))
    return embed


async def countdown(ctx):
    timeleft = 2
    msg = await ctx.reply(f"Test in {timeleft + 1}...")
    while timeleft > 0:
        await msg.edit(content=f"Test in {timeleft}...")
        timeleft -= 1
        await asyncio.sleep(1)
    await msg.delete()

async def timeout_embed(ctx):
    embed = discord.Embed(title="Type Race Timed Out", description="You didn't respond to the prompt in time.", color=discord.Color.blurple())
    await ctx.reply(embed=embed)

@client.event
async def on_ready():
    print("Bot is ready.")


@client.command()
async def race(ctx):
    text = f" ".join(word_maker.random_words(15, word_max_length=7)).capitalize()

    buffer = display_prompt(text)
    await countdown(ctx)

    await ctx.reply(content="**Type what you see:**", file=discord.File(buffer, filename="image.png"))

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    start_time = time.time()

    try:
        msg = await client.wait_for("message", timeout=100, check=check)

        time_elapsed, wpm, accuracy, words, netwpm = calc_scores(start_time, text, msg)
        grade = calc_grade(netwpm)
        r, g, b = get_color(grade.lower())

        embed = create_embed(ctx, accuracy, wpm, netwpm, words, r, g, b)
        f, embed = set_thumbnail(grade, embed, r, g, b)

        await ctx.reply(embed=embed, file=f)

    except asyncio.TimeoutError:
        await timeout_embed(ctx)


client.run("TOKEN")

