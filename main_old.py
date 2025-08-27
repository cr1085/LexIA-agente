import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configurar intents - SOLO LOS NECESARIOS
intents = discord.Intents.default()
intents.message_content = True  # Necesita estar habilitado en el portal

# Si no necesitas presencia o miembros del servidor, no los habilites
# intents.presences = False  # Opcional: deshabilitar si no es necesario
# intents.members = False    # Opcional: deshabilitar si no es necesario

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f'✅ Bot {bot.user} conectado!')
    print(f'✅ Bot {bot.user} conectado!')
    print(f'📊 En {len(bot.guilds)} servidores')

@bot.command()
async def hola(ctx):
    await ctx.send("¡Hola! El bot está funcionando correctamente.")

@bot.command()
async def ping(ctx):
    await ctx.send(f'🏓 Pong! Latencia: {round(bot.latency * 1000)}ms')

@bot.command()
async def info(ctx):
    embed = discord.Embed(title="Información del Bot", color=0x00ff00)
    embed.add_field(name="Creado por", value="3cb soluciones", inline=False)
    embed.add_field(name="Prefijo", value="!", inline=True)
    embed.add_field(name="Servidores", value=len(bot.guilds), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def check_intents(ctx):
    """Verifica la configuración de intents"""
    embed = discord.Embed(title="Configuración de Intents", color=0x00ff00)
    embed.add_field(name="message_content", value=intents.message_content, inline=True)
    embed.add_field(name="presences", value=intents.presences, inline=True)
    embed.add_field(name="members", value=intents.members, inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def ayuda(ctx):
    """Muestra todos los comandos disponibles"""
    embed = discord.Embed(
        title="📚 Comandos Disponibles",
        description="Prefix: `!`",
        color=0x0099ff
    )
    embed.add_field(name="!hola", value="Saludo del bot", inline=False)
    embed.add_field(name="!ping", value="Verifica la latencia", inline=False)
    embed.add_field(name="!preguntar [pregunta]", value="Haz una pregunta", inline=False)
    embed.add_field(name="!ayuda", value="Muestra esta ayuda", inline=False)
    await ctx.send(embed=embed)



if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if TOKEN:
        logger.info("Iniciando bot...")
        try:
            bot.run(TOKEN)
        except discord.LoginFailure:
            logger.error("❌ Token de Discord inválido. Verifica tu token.")
            print("❌ Token de Discord inválido. Verifica tu token.")
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            print(f"❌ Error inesperado: {e}")
    else:
        logger.error("❌ No se encontró el token de Discord")
        print("❌ No se encontró el token de Discord")