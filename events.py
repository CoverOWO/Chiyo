import time
import discord
from ext import glob
from WebLamp import log
from ext.glob import bot
from objects import Mods
from WebLamp import Fore
from objects import Score
from discord import Embed
from discord import Member
from objects import Player
from objects import Server
from pprint import pformat
from objects import Beatmap
from objects import BOT_OWNER_ID
from discord.message import Message
from discord.reaction import Reaction
from discord.ext.commands import Context
from discord.ext.commands.errors import (
    CommandNotFound, CommandOnCooldown
)
from helpers import (
    BEATMAP, TWELVEHOURS, USERS
)

@bot.event
async def on_ready():
    servers = len(bot.guilds)
    msg = f'{bot.user} is online! | Currently in {servers} server(s)!'
    log(msg, Fore.GREEN)

    await bot.change_presence(
        status = discord.Status.online, 
        activity = discord.Activity(
        type = discord.ActivityType.playing, 
        name = f"in {servers} Servers! | Supports Akatsuki & Bancho!")
    )

get_user = {
    'osu': Player.from_bancho,
    'akatsuki': Player.from_akatsuki
}
@bot.event
async def on_message(message: Message):
    await bot.wait_until_ready()
    await bot.process_commands(message)
    start_time = time.time()

    m = f'{message.content}'
    if message.embeds:
        m += f' | Embeds: {message.embeds}'
    
    if message.attachments:
        m += f' | Attachments: {message.attachments}'

    log(
        f'[{message.guild}] [{message.channel}] {message.author}: {m}',
        Fore.BLUE
    )
    
    users = USERS.findall(message.content)
    if users:
        for u in users:
            server, user = [x for x in u if x]
            
            if user.isdecimal():
                user = int(user)

            p = await get_user[server](user)
            if not p:
                continue

            e = p.embed
            e.colour = message.author.color

            await message.channel.send(
                content = f'{time.time()-start_time:.2f}s',
                embed = e
            )

    beatmapids = BEATMAP.match(message.content)
    if not beatmapids:
        return
    
    setid, bid, setidd, id = beatmapids.groupdict().values()
    
    if (
        any((setid, setidd)) and 
        not any((bid, id))
    ):
        bmap = await Beatmap.get_id_from_set(setid or setidd)
    else:
        bmap_id = int(bid or id)
        bmap = await Beatmap.from_id(bmap_id)

    if not bmap:
        return
    
    e = bmap.embed
    e.colour = message.author.color

    glob.cache.channel_beatmaps[message.channel.id] = (
        bmap, time.time() + TWELVEHOURS
    )
    
    await message.channel.send(
        content = f'{time.time()-start_time:.2f}s',
        embed = e
    )
    return

top = {
    Server.Bancho: Score.from_bancho_top,
    Server.Akatsuki: Score.from_akatsuki_top
}
recent = {
    Server.Bancho: Score.from_bancho_recent,
    Server.Akatsuki: Score.from_akatsuki_recent
}
scores = {
    Server.Bancho: Score.from_bancho,
    Server.Akatsuki: Score.from_akatsuki
}
@bot.event
async def on_reaction_add(reaction: Reaction, user: Member):
    if (
        user.bot or
        reaction.custom_emoji or
        reaction.emoji not in ('⬅️', '➡️')
    ): 
        return
    
    start_time = time.time()
    msg: Message = reaction.message
    if not msg.embeds:
        return
    
    embed: Embed = msg.embeds[0]
    userid = int(embed._thumbnail['url'].split('/')[-1:][0])
    server = Server.from_name(embed._footer['text'].split()[3][:-1])
    
    if (userid, server) not in glob.cache.scores:
        return
    
    s, _type = glob.cache.scores[(userid, server)][:-1]
    
    if _type == 'c':
        iterate = scores
    elif _type == 'r':
        iterate = recent
    elif _type == 't':
        iterate = top

    if reaction.emoji == '➡️':
        change = 1
    else:
        change = -1

    kwargs = {
        'user': s.player,
        'mode': s.mode,
        'index': s.index + change
    }
    
    if s.mods & Mods.RELAX:
        kwargs['relax'] = 1

    score: Score = await iterate[server](**kwargs)
    
    if not score:
        await msg.edit(
            content = 'No score found.',
            embed = None
        )
        glob.cache.scores[(userid, server)] = (
            s, _type, time.time() + TWELVEHOURS
        )
        return
    
    glob.cache.scores[(userid, server)] = (
        score, _type, time.time() + TWELVEHOURS
    )
    glob.cache.channel_beatmaps[msg.channel.id] = score.bmap
    
    e = score.embed
    e.colour = user.color
    await msg.edit(
        content = f'{time.time()-start_time:.2f}s',
        embed = e
    )
    return

ERROR_CHANNEL = 713072038557777942

@bot.event
async def on_command_error(ctx: Context, error) -> None:
    if isinstance(error, CommandNotFound):
        return
    
    if isinstance(error, CommandOnCooldown):
        await ctx.send(*error.args)
        return

    ctxdict = ctx.__dict__
    cover = bot.get_channel(ERROR_CHANNEL)
    msg = (
        f'<@{BOT_OWNER_ID}>\n'
        f'```py\n{pformat(ctxdict)}\n\n'
        f'{repr(error)}```'
    )
    await cover.send(msg)

# Code passed this point is
# meant for my server that 
# can help with my development

# drag vc: 784646271838191616
# private vc: 743562646795714667
# Hideout guild id: 705649421857325139

DRAG_VC = 784646271838191616
PRIVATE_VC = 743562646795714667
HIDEOUT_ID = 705649421857325139

@bot.event
async def on_voice_state_update(member: Member, before, after) -> None:
    if member.guild.id != HIDEOUT_ID:
        return
    
    private_vc = bot.get_channel(PRIVATE_VC)
    if not glob.mode or not (channel := after.channel):
        return
    
    channel = after.channel
    if channel.id != DRAG_VC:
        return
    
    await member.move_to(private_vc)