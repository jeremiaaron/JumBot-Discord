import discord
from discord.ext import commands
import youtube_dl
import os
from dotenv import load_dotenv
from math import ceil

# Initialize bot with prefix '=' and queue dictionary
bot = commands.Bot(command_prefix='=')
queue_dict = {}


# Function to check queue for the next available song
async def check_queue(ctx, server_id):
    if len(queue_dict) != 0 and queue_dict[server_id]:
        voice_client = ctx.message.guild.voice_client

        # Obtain information from queue dictionary
        info = queue_dict[server_id][0]
        song_id = info.get('id')
        uploader = info.get('uploader')
        song_title = info.get('title')
        duration = info.get('duration')
        video_link = info.get('url')
        requester = info.get('requester')
        del queue_dict[server_id][0]

        # Play the song and display song information with embed message
        async with ctx.typing():
            ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                              'options': '-vn'}
            voice_client.play(
                await discord.FFmpegOpusAudio.from_probe(video_link, **ffmpeg_options),
                after=lambda e:
                print('Player error: %s' % e) if e else bot.loop.create_task(check_queue(ctx, ctx.message.guild.id))
            )

            embed_msg = discord.Embed(title=song_title, url="https://youtu.be/{}".format(song_id), color=0xd9155a)
            embed_msg.set_thumbnail(url="https://img.youtube.com/vi/{}/0.jpg".format(song_id))
            embed_msg.add_field(name="Uploaded by", value=uploader, inline=False)
            embed_msg.add_field(name="Duration", value='{:02d}:{:02d}'.format(duration // 60, duration % 60), inline=True)
            embed_msg.add_field(name="Requested by", value=requester, inline=True)
        await ctx.message.channel.send(embed=embed_msg)


# Function to queue every song in a playlist
async def queue_playlist(ctx, info):
    server_id = ctx.message.guild.id
    requester = ctx.message.author.name

    # Loops through every song in the playlist and add them to the queue
    for i in range(0, len(info['entries'])):
        video_link = info['entries'][i]['formats'][0]['url']
        song_id = info['entries'][i].get('id')
        uploader = info['entries'][i].get('uploader')
        song_title = info['entries'][i].get('title')
        duration = info['entries'][i].get('duration')
        if server_id in queue_dict:
            queue_dict[server_id].append({'id': song_id, 'uploader': uploader, 'title': song_title,
                                          'duration': duration, 'url': video_link, 'requester': requester})
        else:
            queue_dict[server_id] = [{'id': song_id, 'uploader': uploader, 'title': song_title,
                                      'duration': duration, 'url': video_link, 'requester': requester}]


# Command to play song with 'play'
@bot.command(name="play", help="Plays or queues a song")
async def play(ctx, *, url: str):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    # Tell user to connect to a voice channel, else connect to the voice channel
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
        'default_search': 'auto'
    }
    is_playlist = False

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        async with ctx.typing():
            info = ydl.extract_info(url, download=False)

            # Check whether user searched by keywords or played using URL
            if 'entries' in info:
                if len(info['entries']) > 1:
                    is_playlist = True
                    playlist_title = info['entries'][0]['playlist_title']
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
    requester = ctx.message.author.name

    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                      'options': '-vn'}

    # Nested function to start playing a song
    async def play_song():
        async with ctx.typing():
            voice_client.play(
                await discord.FFmpegOpusAudio.from_probe(video_link, **ffmpeg_options),
                after=lambda e:
                print('Player error: %s' % e) if e else bot.loop.create_task(check_queue(ctx, ctx.message.guild.id))
            )
            embed_msg = discord.Embed(title=song_title, url="https://youtu.be/{}".format(song_id), color=0xd9155a)
            embed_msg.set_thumbnail(url="https://img.youtube.com/vi/{}/0.jpg".format(song_id))
            embed_msg.add_field(name="Uploaded by", value=uploader, inline=False)
            embed_msg.add_field(name="Duration", value='{:02d}:{:02d}'.format(duration // 60, duration % 60), inline=True)
            embed_msg.add_field(name="Requested by", value=requester, inline=True)
        await ctx.message.channel.send(embed=embed_msg)

    # If the URL is not a playlist and the bot is playing a song
    if not is_playlist and voice_client.is_playing():
        async with ctx.typing():
            if server_id in queue_dict:
                queue_dict[server_id].append({'id': song_id, 'uploader': uploader, 'title': song_title,
                                              'duration': duration, 'url': video_link, 'requester': requester})
            else:
                queue_dict[server_id] = [{'id': song_id, 'uploader': uploader, 'title': song_title,
                                          'duration': duration, 'url': video_link, 'requester': requester}]
        await ctx.send('Added `{}` to the queue at number `{}`'.format(song_title, len(queue_dict[server_id])))
    # If the URL is a playlist and the bot is playing a song
    elif is_playlist and voice_client.is_playing():
        async with ctx.typing():
            await queue_playlist(ctx, info)
        await ctx.send('Added `{}` playlist to the queue'.format(playlist_title))
    # If the URL is a playlist and the bot is not playing a song
    elif is_playlist and not voice_client.is_playing():
        async with ctx.typing():
            await queue_playlist(ctx, info)
        await ctx.send('Added `{}` playlist to the queue'.format(playlist_title))
        queue_dict[server_id].pop(0)
        await play_song()
    # If the URL is not a playlist and the bot is not playing a song
    else:
        await play_song()


# Command to pause the current song
@bot.command(name="pause", help="Pauses the current song")
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("JumBot is not singing currently")


# Command to resume the paused song
@bot.command(name="resume", help="Resumes the currently paused song")
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    elif not voice_client.is_playing():
        await ctx.send("JumBot is not singing currently")
    else:
        await ctx.send("JumBot is already singing currently")


# Command to stop and disconnect the bot
@bot.command(name="stop", help="Stops playing the current music and disconnects JumBot")
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("JumBot is not connected to any channel yet")


# Skip the current song and play the next song in queue
@bot.command(name="skip", help="Skips to the next song in the queue")
async def skip(ctx):
    voice_client = ctx.message.guild.voice_client
    server_id = ctx.message.guild.id

    if voice_client.is_playing():
        # Check queue if there is a song in queue, else stop the bot
        if len(queue_dict) > 0 and len(queue_dict[server_id]) > 0:
            voice_client.pause()
            await ctx.send('Skipped current song, playing the next one...')
            await check_queue(ctx, ctx.message.guild.id)
        else:
            voice_client.stop()
            await ctx.send('Skipped current song, next song is not available')
    else:
        await ctx.send("JumBot is not playing anything currently")


# Command to remove a song from the queue
@bot.command(name="remove", help="Removes a song from the queue")
async def remove(ctx, index: int):
    server_id = ctx.message.guild.id

    # Check if the index input corresponds to a song in the queue
    if len(queue_dict[server_id]) == 0:
        await ctx.send('There are no songs in the queue')
    elif index >= len(queue_dict[server_id])+1 or index < 1:
        await ctx.send('Song does not exist in the queue')
    else:
        async with ctx.typing():
            info = queue_dict[server_id][index-1]
            song_title = info.get('title')
            del queue_dict[server_id][index-1]
        await ctx.send("Removed `{}` from queue number `{}`".format(song_title, index))


# Command to display the queue
@bot.command(name="queue", help="Displays the current queue of songs")
async def queue(ctx, page: int = None):
    songs_per_page = 10  # Number of songs to be displayed in a queue page
    server_id = ctx.message.guild.id

    # Check if there are songs in the queue
    if len(queue_dict) == 0 or server_id not in queue_dict or len(queue_dict[server_id]) == 0:
        await ctx.send('```There are no songs in the queue currently```')
        return
    else:
        total_page = ceil(len(queue_dict[server_id]) / songs_per_page)  # Calculate total page(s)

    # Check every possible parameter input
    if page is None:
        page = total_page  # set displayed page to the last one if no parameter exists
    else:
        if page < 1:
            page = 1
        elif page > total_page:
            page = total_page

    # Print songs in the selected page
    display_str = "```Queue page: {}/{}\n\n".format(page, total_page)
    starting_index = songs_per_page * (page-1)  # starting index of songs in one page
    for index in range(starting_index, starting_index + songs_per_page):
        if index >= len(queue_dict[server_id]):
            break
        song_title = queue_dict[server_id][index].get('title')
        display_str += '{}: {}\n'.format(index+1, song_title)
        index += 1
    display_str += "```"
    await ctx.send(display_str)


# Command to clear the queue
@bot.command(name="clear", help="Clears the current song queue")
async def clear(ctx):
    async with ctx.typing():
        server_id = ctx.message.guild.id
        if len(queue_dict) == 0 or server_id not in queue_dict or len(queue_dict[server_id]) == 0:
            await ctx.send('The queue is already empty')
        else:
            del queue_dict[server_id]
    await ctx.send('Cleared the whole queue')


# Print a message to the console when bot is ready
@bot.event
async def on_ready():
    print('JumBot is online!')


# Sends an error message for wrong user input
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Incorrect command input!")


# Run bot using secret token stored in environment variable
load_dotenv()
SECRET_TOKEN = os.getenv('SECRET_TOKEN')
bot.run(SECRET_TOKEN)
