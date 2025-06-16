import discord
import os
import aiomysql
import random
from discord.ext import commands
from dotenv import load_dotenv
import conn_db



#Laden der Variablen aus Dotenv
load_dotenv()

Token = os.getenv('Discord_TokenTest')
Channel_ID = int(os.getenv('Channel_Test')) #Kanal ID als Int  
Guild_ID = int(os.getenv('Test_ID')) #Server ID als INT
Welcome_ID = int(os.getenv('welc_ID'))

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
channel = bot.get_channel(Welcome_ID) # oder mit Kanal-ID: 
channelAll = bot.get_channel(Channel_ID)


@bot.event
async def on_ready():
    print(f'Nagh Nagh. Logged in as {bot.user}')
    

@bot.event
async def on_member_join(member):
    
    # Hier den Kanal festlegen, in den die Begrüßung gesendet werden soll
    #'channel = discord.utils.get(member.guild.text_channels, name='willkommen')  # Kanalname
    greetings = await cursor.fetchall()
    if greetings:
        greeting = random.choice(greetings)[0]
        await member.send(greeting.format(name=member.name))

    async with cursor.execute('SELECT message FROM greetings') as cursor:
        greetings = await cursor.fetchall()
        if greetings:
            greeting = random.choice(greetings)[0]
            embed = discord.Embed(
                description=greeting.format(name=member.name),
                color=0x00ff00
            )
        greetings = await cursor.fetchall()
    if greetings:
        greeting = random.choice(greetings)[0]
        await member.send(greeting.format(name=member.name))
        embed.set_thumbnail(url=member.avatar.url)  # Profilbild als Thumbnail
        embed.set_footer(text=f"Willkommen im Server, {member.name}!")


        
bot.run(Token)

conn_db.run()


