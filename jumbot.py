import discord
from discord.ext import commands
import youtube_dl
import os
from dotenv import load_dotenv

bot = commands.Bot(command_prefix='!')
queue_dict = {}


async def check_queue(ctx, server_id):
    if len(queue_dict) != 0 and queue_dict[server_id]:
        voice_client = ctx.message.guild.voice_client

        info = queue_dict[server_id][0]
        song_id = info.get('id')
        uploader = info.get('uploader')
        song_title = info.get('title')
        duration = info.get('duration')
        video_link = info.get('url')
        del queue_dict[server_id][0]

        async with ctx.typing():
            ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                              'options': '-vn'}
            voice_client.play(
                discord.FFmpegPCMAudio(video_link, **ffmpeg_options),
                after=lambda e:
                print('Player error: %s' % e) if e else bot.loop.create_task(check_queue(ctx, ctx.message.guild.id))
            )
        embed_msg = discord.Embed(title=song_title, url="https://youtu.be/{}".format(song_id), color=0xd9155a)
        embed_msg.set_thumbnail(url="https://img.youtube.com/vi/{}/0.jpg".format(song_id))
        embed_msg.add_field(name="Uploaded by", value=uploader, inline=False)
        embed_msg.add_field(name="Duration", value='{:02d}:{:02d}'.format(duration // 60, duration % 60), inline=True)
        embed_msg.add_field(name="Requested by", value=ctx.message.author.name, inline=True)
        await ctx.message.channel.send(embed=embed_msg)


@bot.command(name="play", help="Plays or queues a song")
async def play(ctx, *, url: str):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel yet!")
        return
    elif ctx.message.author.voice and voice_client is None:
        voice_channel = ctx.message.author.voice.channel
        await voice_channel.connect()

    voice_client = ctx.message.guild.voice_client
    server_id = ctx.message.guild.id

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': 'True',
        'default_search': 'auto'
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            video_link = info['entries'][0]['formats'][0]['url']
            song_id = info['entries'][0].get('id')
            uploader = info['entries'][0].get('uploader')
            song_title = info['entries'][0].get('title')
            duration = info['entries'][0].get('duration')
        elif 'formats' in info:
            video_link = info['formats'][0]['url']
            song_id = info.get('id')
            uploader = info.get('uploader')
            song_title = info.get('title')
            duration = info.get('duration')

    if voice_client.is_playing():
        async with ctx.typing():
            if server_id in queue_dict:
                queue_dict[server_id].append({'id': song_id, 'uploader': uploader, 'title': song_title,
                                              'duration': duration, 'url': video_link})
            else:
                queue_dict[server_id] = [{'id': song_id, 'uploader': uploader, 'title': song_title,
                                          'duration': duration, 'url': video_link}]
        await ctx.send('Added `{}` to the queue'.format(song_title))
    else:
        async with ctx.typing():
            ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                              'options': '-vn'}
            voice_client.play(
                discord.FFmpegPCMAudio(video_link, **ffmpeg_options),
                after=lambda e:
                print('Player error: %s' % e) if e else bot.loop.create_task(check_queue(ctx, ctx.message.guild.id))
            )
        embed_msg = discord.Embed(title=song_title, url="https://youtu.be/{}".format(song_id), color=0xd9155a)
        embed_msg.set_thumbnail(url="https://img.youtube.com/vi/{}/0.jpg".format(song_id))
        embed_msg.add_field(name="Uploaded by", value=uploader, inline=False)
        embed_msg.add_field(name="Duration", value='{:02d}:{:02d}'.format(duration // 60, duration % 60), inline=True)
        embed_msg.add_field(name="Requested by", value=ctx.message.author.name, inline=True)
        await ctx.message.channel.send(embed=embed_msg)


@bot.command(name="pause", help="Pauses the current song")
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("JumBot is not singing currently")


@bot.command(name="resume", help="Resumes the currently paused song")
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    elif not voice_client.is_playing():
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


@bot.command(name="skip", help="Skips to the next song in the queue")
async def skip(ctx):
    voice_client = ctx.message.guild.voice_client
    server_id = ctx.message.guild.id

    if voice_client.is_playing():
        if len(queue_dict[server_id]) > 0:
            voice_client.pause()
            await check_queue(ctx, ctx.message.guild.id)
        else:
            voice_client.stop()
    else:
        await ctx.send("JumBot is not playing anything currently")


@bot.command(name="remove", help="Removes a song from the queue")
async def remove(ctx, index: int):
    server_id = ctx.message.guild.id
    if len(queue_dict[server_id]) == 0:
        ctx.send('There are no songs in the queue')
    elif index >= len(queue_dict[server_id])+1 or index < 1:
        ctx.send('Song does not exist in the queue')
    else:
        del queue_dict[server_id][index-1]


@bot.command(name="queue", help="Displays the current queue of songs")
async def queue(ctx):
    server_id = ctx.message.guild.id
    if len(queue_dict[server_id]) == 0:
        await ctx.send('```There are no songs in the queue currently```')
    else:
        display_str = "```Upcoming queue of songs:\n"
        index = 1
        for info in queue_dict[server_id]:
            song_title = info.get('title')
            display_str += '{}: {}\n'.format(index, song_title)
            index += 1
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
