import discord
import os
from dotenv import load_dotenv
from random import randint
from discord.ext import commands
from classes import Game
import asyncio



load_dotenv()
TOKEN = os.getenv("TOKEN")



intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)


    

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    print("Bot is ready!")


games = {}  # key: user_id or channel_id, value: Game instance
loops = {}  # key: user_id or channel_id, value: logic_loop task

@bot.command()
async def start(ctx, arg: str = "1"):
    user_id = ctx.author.id  # or ctx.channel.id for per-channel games

    if user_id in games:
        await ctx.send("You already have a game running!")
        return
    if not arg.isdigit():
        await ctx.send("Please enter a number between 1 and 6. or leave blank for night 1")
        return

    arg = int(arg)

    if 1 <= arg <= 6:
        try:
            power_message = await ctx.send(f'game started')
            time_message = await ctx.send(f'12am')
            with open("./pics/desk_.png", "rb") as file:
                img_message = await ctx.send(file=discord.File(file, "image.jpg"))

            game = Game(ctx, power_message, time_message, img_message, arg)
            games[user_id] = game

            # Start a new logic loop for this game
            async def user_logic_loop():
                while game.playing:
                    await asyncio.sleep(1)
                    await game.logic_step()
            task = asyncio.create_task(user_logic_loop())
            loops[user_id] = task

        except ValueError:
            await ctx.send("something went wrong")
    else:
        await ctx.send("pick a correct night (1-6, blank = 1)")
        return

@bot.command()
async def c(ctx, arg: str):
    user_id = ctx.author.id
    game = games.get(user_id)
    if game and game.playing:
        if ctx.author.id != game.player.author.id or ctx.channel.id != game.player.channel.id:
            return
        game.current_room = str(arg).lower()
        await ctx.message.delete()
        await game.draw()

@bot.command()
async def desk(ctx):
    user_id = ctx.author.id
    game = games.get(user_id)
    if game and game.playing:
        if ctx.author.id != game.player.author.id or ctx.channel.id != game.player.channel.id:
            return

        game.current_room = "desk"
        game.foxy.timer = randint(1, 17)

        if game.bonnie.locked:
            await game.jumpscare(game.bonnie)
            return
        elif game.chica.locked:
            await game.jumpscare(game.chica)
            return
        elif game.foxy.room == "desk":
            if not game.elec["doors"][0]:
                await game.jumpscare(game.foxy)
                return
            else:
                game.power -= 1 + (5 * game.foxy.times_out)
                game.foxy.times_out += 1
                game.foxy.room = "1c"
                game.foxy.stage = 1
                game.foxy.locked = None
        elif game.freddy.room == "desk":
            await game.jumpscare(game.freddy)
            return
        elif game.freddy.room is None:
            game.freddy.room = "4a"
            game.freddy.room_index = game.freddy.path.index("4a")
        await ctx.message.delete()
        await game.draw()
        
@bot.command()
async def d(ctx, arg: str):
    user_id = ctx.author.id
    game = games.get(user_id)
    if game.current_room != "desk":
        return
    if game and game.playing:
        if ctx.author.id != game.player.author.id or ctx.channel.id != game.player.channel.id:
            return

        if arg.lower() == "l" and not game.bonnie.locked:
            game.elec["doors"][0] = not game.elec["doors"][0]
        if arg.lower() == "r" and not game.chica.locked:
            game.elec["doors"][1] = not game.elec["doors"][1]

        await ctx.message.delete()
        await game.draw()

@bot.command()
async def l(ctx, arg: str):
    user_id = ctx.author.id
    game = games.get(user_id)
    if game.current_room != "desk":
        return
    if game and game.playing:
        if ctx.author.id != game.player.author.id or ctx.channel.id != game.player.channel.id:
            return

        if arg.lower() == "l":
            game.elec["lights"][0] = not game.elec["lights"][0]
        if arg.lower() == "r":
            game.elec["lights"][1] = not game.elec["lights"][1]

        await ctx.message.delete()
        await game.draw()

@bot.command()
async def stop(ctx):
    user_id = ctx.author.id
    game = games.get(user_id)
    if game:
        if ctx.author.id == game.player.author.id or ctx.channel.id == game.player.channel.id:
            await ctx.send("Game stopped.")
            # Optionally, clean up the game and loop
            games.pop(user_id, None)
            task = loops.pop(user_id, None)
            if task:
                task.cancel()

bot.run(TOKEN)
