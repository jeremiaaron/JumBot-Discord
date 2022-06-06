import discord
from discord.ext import commands
import youtube_dl
import os

bot = commands.Bot(command_prefix='!')


@bot.command()
async def play(ctx, url: str):
    music = os.path.isfile("music.mp3")

    try:
        if music:
            os.remove("music.mp3")
    except PermissionError:
        await ctx.send("Please wait for me to stop singing or force me using the 'stop' command")
        return

    voice_channel = discord.utils.get(ctx.guild.voice_channels, name="General")

    await voice_channel.connect()
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    ydl_opts = {'format': 'bestaudio/best', 'noplaylist':'True'}
    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_link = info['formats'][0]['url']
        source = await discord.FFmpegOpusAudio.from_probe(video_link, **ffmpeg_options)
        voice.play(discord.FFmpegPCMAudio(video_link, **ffmpeg_options))


@bot.command()
async def leave(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_connected():
        await voice.disconnect()
    else:
        await ctx.send("JumBot is not connected to any channel yet")


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


@bot.command()
async def stop(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    voice.stop()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Wrong command input!")


bot.run("OTgzMzg4OTc4MzMxOTIyNDgy.Gj-dgj.dhrm5m2kSoy_YrsRR-M8yRcpxmXNrQCRmKHGxQ")
