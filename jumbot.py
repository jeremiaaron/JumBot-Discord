import discord
from discord.ext import commands
import youtube_dl
import os
from dotenv import load_dotenv

bot = commands.Bot(command_prefix='!')
queue_dict = {}


async def check_queue(ctx, server_id):
    print('check_queue ran')
    if len(queue_dict) != 0 and queue_dict[server_id]:
        voice_client = ctx.message.guild.voice_client

        song_title, video_link = queue_dict[server_id][0]
        del queue_dict[server_id][0]

        print('Queue length after popped: ' + str(len(queue_dict[server_id])))

        async with ctx.typing():
            ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                              'options': '-vn'}
            voice_client.play(
                discord.FFmpegPCMAudio(video_link, **ffmpeg_options),
                after=lambda e:
                print('Player error: %s' % e) if e else bot.loop.create_task(check_queue(ctx, ctx.message.guild.id))
            )
        await ctx.send('Now playing `{}`'.format(song_title))


@bot.command(name="play", help="Plays a song")
async def play(ctx, url: str):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel yet!")
        return
    elif ctx.message.author.voice and voice_client is None:
        voice_channel = ctx.message.author.voice.channel
        await voice_channel.connect()

    voice_client = ctx.message.guild.voice_client
    server_id = ctx.message.guild.id

    ydl_opts = {'format': 'bestaudio/best', 'noplaylist': 'True'}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        song_title = info.get('title')
        video_link = info['formats'][0]['url']

    if voice_client.is_playing():
        async with ctx.typing():
            if server_id in queue_dict:
                queue_dict[server_id].append((song_title, video_link))
            else:
                queue_dict[server_id] = [(song_title, video_link)]
        await ctx.send('Added `{}` to the queue'.format(song_title))
        print('Queue length initially: ' + str(len(queue_dict[server_id])))
    else:
        async with ctx.typing():
            ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                              'options': '-vn'}
            voice_client.play(
                discord.FFmpegPCMAudio(video_link, **ffmpeg_options),
                after=lambda e:
                print('Player error: %s' % e) if e else bot.loop.create_task(check_queue(ctx, ctx.message.guild.id))
            )
        await ctx.send('Now playing `{}`'.format(song_title))


@bot.command()
async def pause(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
    else:
        await ctx.send("JumBot is not singing currently")


@bot.command()
async def resume(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        await voice.resume()
    elif not voice.is_playing():
        await ctx.send("JumBot is not singing currently")
    else:
        await ctx.send("JumBot is already singing currently")


@bot.command(name="stop", help="Stops playing the current music and disconnects JumBot from the voice channel")
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("JumBot is not connected to any channel yet")


@bot.command()
async def remove(ctx, index: int):
    if len(queue_dict) == 0:
        ctx.send('There is no song in the queue')
    elif index >= len(queue_dict)+1 or index < 1:
        ctx.send('Song does not exist in the queue')
    else:
        queue.pop(index-1)


@bot.command(name="queue", help="Displays the current playlist of songs")
async def queue(ctx):
    server_id = ctx.message.guild.id
    if len(queue_dict[server_id]) == 0:
        await ctx.send('```There is no song in the queue currently```')
    else:
        display_str = "```Current playlist of songs:\n"
        for song_title, video_link in queue_dict[server_id]:
            display_str += ('{}\n'.format(song_title))
        display_str += "```"
        await ctx.send(display_str)


@bot.event
async def on_ready():
    print('JumBot is online!')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Incorrect command input!")


load_dotenv()
SECRET_TOKEN = os.getenv('SECRET_TOKEN')
bot.run(SECRET_TOKEN)
