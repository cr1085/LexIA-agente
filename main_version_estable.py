import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import PyPDF2
import requests
import json
import logging
from typing import Optional

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configurar intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Variables globales
syllabus_text = None

class AIAssistant:
    def __init__(self):
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    
    def groq_assistant(self, prompt: str) -> Optional[str]:
        """Usa Groq API con Llama 3.1 (gratis y rápido)"""
        if not self.groq_api_key:
            return None
            
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": "Eres un asistente especializado en ciberseguridad. Responde preguntas técnicas de manera clara y concisa. Si no sabes algo, dilo honestamente."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Error con Groq API: {e}")
            return None
    
    def openrouter_assistant(self, prompt: str) -> Optional[str]:
        """Usa OpenRouter como alternativa"""
        if not self.openrouter_api_key:
            return None
            
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "google/gemma-7b-it:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "Eres un experto en ciberseguridad. Responde de manera técnica pero accesible."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Error con OpenRouter: {e}")
            return None
    
    def get_response(self, prompt: str) -> str:
        """Obtiene respuesta de la IA disponible"""
        # Primero intenta con Groq (más rápido)
        response = self.groq_assistant(prompt)
        if response:
            return response
            
        # Luego con OpenRouter
        response = self.openrouter_assistant(prompt)
        if response:
            return response
            
        # Fallback local simple
        return "⚠️ Los servicios de IA no están disponibles temporalmente. Intenta más tarde."

def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """Extrae texto del PDF del syllabus"""
    text = ""
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error leyendo PDF: {e}")
        return None

# Inicializar asistente de IA
ai_assistant = AIAssistant()

@bot.event
async def on_ready():
    global syllabus_text
    
    print(f'✅ Bot {bot.user} conectado!')
    print(f'📊 En {len(bot.guilds)} servidores')
    
    # Cargar syllabus
    syllabus_text = extract_text_from_pdf("syllabus.pdf")
    if syllabus_text:
        print("📄 Syllabus cargado correctamente")
    else:
        print("❌ Error cargando el syllabus")

@bot.command()
async def preguntar(ctx, *, pregunta):
    """Responde preguntas sobre el syllabus de ciberseguridad"""
    global syllabus_text
    
    if not syllabus_text:
        await ctx.send("❌ El syllabus no está disponible.")
        return
    
    try:
        # Búsqueda simple en el texto del syllabus
        pregunta_lower = pregunta.lower()
        syllabus_lower = syllabus_text.lower()
        
        # Buscar coincidencias relevantes
        lineas_relevantes = []
        for linea in syllabus_text.split('\n'):
            if any(palabra in linea.lower() for palabra in pregunta_lower.split()):
                if len(linea.strip()) > 20:  # Solo líneas con contenido
                    lineas_relevantes.append(linea.strip())
        
        if lineas_relevantes:
            respuesta = "\n".join(lineas_relevantes[:3])  # Máximo 3 líneas
            if len(respuesta) > 1000:
                respuesta = respuesta[:1000] + "..."
        else:
            respuesta = "No encontré información específica sobre eso en el syllabus."
        
        embed = discord.Embed(
            title="📚 Respuesta del Syllabus",
            description=respuesta,
            color=0x00ff00
        )
        embed.add_field(name="Pregunta", value=pregunta, inline=False)
        embed.set_footer(text="Información basada en el syllabus del curso")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error procesando pregunta: {e}")
        await ctx.send("❌ Error procesando tu pregunta. Intenta de nuevo.")

@bot.command()
async def asistente(ctx, *, mensaje):
    """Pregunta anything al asistente de IA especializado"""
    try:
        # Mostrar que está procesando
        processing_msg = await ctx.send("🤖 Procesando tu pregunta...")
        
        # Obtener respuesta de la IA
        respuesta = ai_assistant.get_response(mensaje)
        
        # Limitar longitud para Discord
        if len(respuesta) > 1500:
            respuesta = respuesta[:1500] + "..."
        
        embed = discord.Embed(
            title="🧠 Asistente de Ciberseguridad",
            description=respuesta,
            color=0x0099ff
        )
        embed.add_field(name="Pregunta", value=mensaje, inline=False)
        embed.set_footer(text="Respuesta generada por IA")
        
        await processing_msg.delete()
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error con asistente IA: {e}")
        await ctx.send("❌ Error conectando con el asistente IA. Intenta más tarde.")

@bot.command()
async def hola(ctx):
    """Saludo del bot"""
    await ctx.send("¡Hola! Soy tu asistente de Ciberseguridad. Usa `!ayuda` para ver comandos.")

@bot.command()
async def ayuda(ctx):
    """Muestra todos los comandos disponibles"""
    embed = discord.Embed(
        title="🤖 Comandos Disponibles",
        description="**Prefix: `!`**",
        color=0xff9900
    )
    embed.add_field(name="`!hola`", value="Saludo del bot", inline=False)
    embed.add_field(name="`!preguntar [pregunta]`", value="Busca en el syllabus", inline=False)
    embed.add_field(name="`!asistente [pregunta]`", value="Pregunta anything al IA", inline=False)
    embed.add_field(name="`!syllabus`", value="Info del curso", inline=False)
    embed.add_field(name="`!modulos`", value="Módulos del curso", inline=False)
    embed.add_field(name="`!ping`", value="Verifica latencia", inline=False)
    embed.add_field(name="`!ayuda`", value="Muestra esta ayuda", inline=False)
    
    await ctx.send(embed=embed)

# Comandos existentes (syllabus, modulos, ping, etc.)
@bot.command()
async def syllabus(ctx):
    """Muestra información sobre el syllabus"""
    embed = discord.Embed(
        title="📚 Syllabus de Ciberseguridad",
        description="Curso de 108 horas - Nivel Básico",
        color=0x0099ff
    )
    embed.add_field(name="Duración", value="108 horas", inline=True)
    embed.add_field(name="Nivel", value="Básico", inline=True)
    embed.add_field(name="Módulos", value="3 módulos principales", inline=True)
    embed.add_field(name="Temáticas", value="Fundamentos, Higiene Digital, Políticas de Seguridad", inline=False)
    embed.set_footer(text="Usa !preguntar para consultas específicas")
    await ctx.send(embed=embed)

@bot.command()
async def modulos(ctx):
    """Muestra los módulos del curso"""
    embed = discord.Embed(title="📦 Módulos del Curso", color=0xff9900)
    embed.add_field(name="1️⃣ Fundamentos", value="Introducción, modelos de seguridad, vulnerabilidades", inline=False)
    embed.add_field(name="2️⃣ Higiene Digital", value="Prácticas seguras, redes, configuración", inline=False)
    embed.add_field(name="3️⃣ Políticas", value="Desarrollo e implementación de políticas", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    """Verifica la latencia del bot"""
    await ctx.send(f'🏓 Pong! Latencia: {round(bot.latency * 1000)}ms')

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if TOKEN:
        try:
            bot.run(TOKEN)
        except Exception as e:
            logger.error(f"Error iniciando bot: {e}")
    else:
        print("❌ No se encontró DISCORD_TOKEN en .env")