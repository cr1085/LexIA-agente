import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import PyPDF2
import pypdf
import requests
import json
import logging
from typing import Optional
import re

# CONFIGURACIÓN INICIAL (igual que antes)
try:
    import pypdf
    PdfReader = pypdf.PdfReader
    print("✅ Usando pypdf (nueva versión)")
except ImportError:
    import PyPDF2
    PdfReader = PyPDF2.PdfReader
    print("✅ Usando PyPDF2 (versión legacy)")

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

# TÉRMINOS JURÍDICOS (reemplazan los de ciberseguridad)
LEGAL_TERMS = [
    'derecho', 'ley', 'legal', 'jurídico', 'juridico', 'abogado', 'abogada', 
    'proceso', 'juicio', 'demanda', 'demandar', 'demandado', 'demandante',
    'contrato', 'cláusula', 'clausula', 'testamento', 'herencia', 'sucesión', 'sucesion',
    'penal', 'civil', 'mercantil', 'laboral', 'administrativo', 'constitucional',
    'recurso', 'apelación', 'apelacion', 'casación', 'sentencia', 'fallo', 'juez', 'jueza',
    'tribunal', 'juzgado', 'fiscal', 'fiscalía', 'fiscalia', 'notario', 'notaría', 'notaria',
    'documento', 'escritura', 'poder', 'poder notarial', 'arrendamiento', 'compraventa',
    'sociedad', 'empresa', 'mercantil', 'comercial', 'patente', 'marca', 'propiedad intelectual',
    'derechos de autor', 'familia', 'divorcio', 'patria potestad', 'alimentos', 'guarda y custodia',
    'hipoteca', 'prenda', 'garantía', 'garantia', 'obligación', 'obligacion', 'deuda', 'moroso',
    'despido', 'despido improcedente', 'despido nulo', 'despido procedente', 'contrato laboral',
    'convenio colectivo', 'negociación colectiva', 'negociacion colectiva', 'huelga', 'conflicto laboral',
    'delito', 'falta', 'infracción', 'infraccion', 'pena', 'multa', 'prisión', 'prision', 'arresto',
    'detención', 'detencion', 'habeas corpus', 'prueba', 'testigo', 'perito', 'peritaje',
    'mediación', 'mediacion', 'arbitraje', 'conciliación', 'conciliacion', 'transacción', 'transaccion',
    'responsabilidad civil', 'daños y perjuicios', 'indemnización', 'indemnizacion', 'prejuicio',
    'competencia', 'competencia desleal', 'protección de datos', 'proteccion de datos', 'rgpd',
    'derecho al honor', 'derecho a la intimidad', 'derecho a la propia imagen', 'derechos fundamentales',
    'recurso de amparo', 'recurso de protección', 'recurso de inconstitucionalidad', 'recurso de casación'
]

class AIAssistant:
    def __init__(self):
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    
    def is_legal_related(self, prompt: str) -> bool:
        """Verifica si el prompt está relacionado con derecho"""
        prompt_lower = prompt.lower()
        
        # Buscar términos jurídicos
        for term in LEGAL_TERMS:
            if term in prompt_lower:
                return True
        
        # Buscar patrones comunes de preguntas legales
        patterns = [
            r'(cómo|como)\s+(demandar|demandar|demanda|reclamar).*',
            r'(qué|que)\s+(debo|debería|deberia).*(hacer|hacerlo|proceder).*(legal|ley|derecho)',
            r'(necesito|quiero)\s+(hacer|redactar).*(contrato|testamento|poder)',
            r'(cuánto|cuanto)\s+(tiempo|dura|tarda).*(proceso|juicio|demanda)',
            r'(qué|que)\s+(derechos|obligaciones).*(tengo|tiene)',
            r'(es|son)\s+(legal|legales|ilegal|ilegales).*',
            r'(cómo|como)\s+(defender|proteger).*(derechos|intereses)',
            r'(qué|que)\s+(ley|norma|regula).*',
            r'(requisitos|documentos).*(necesarios|precisos).*(para|para)',
            r'(responsabilidad|culpa).*(civil|penal)'
        ]
        
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                return True
                
        return False
    
    def groq_assistant(self, prompt: str) -> Optional[str]:
        """Usa Groq API con Llama 3.1 para temas legales"""
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
                        "content": "Eres un asistente especializado EXCLUSIVAMENTE en derecho y asuntos jurídicos. Solo debes responder preguntas relacionadas con leyes, procesos judiciales, contratos, derechos y obligaciones legales. Si recibes una pregunta fuera de estos temas, responde educadamente que solo puedes ayudar con temas jurídicos. IMPORTANTE: Aclara siempre que no sustituyes el consejo de un abogado y recomienda consultar con un profesional para casos específicos."
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
        """Usa OpenRouter como alternativa para temas legales"""
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
                        "content": "Eres un experto en derecho y asuntos legales. Solo puedes responder preguntas sobre leyes, procesos judiciales, contratos, derechos y obligaciones legales. Si la pregunta no es sobre derecho, responde amablemente que solo estás capacitado para ayudar con temas jurídicos. Aclara que no sustituyes el consejo de un abogado y recomienda consultar con un profesional para casos específicos."
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
        """Obtiene respuesta de la IA disponible para temas legales"""
        # Primero verifica si es sobre derecho
        if not self.is_legal_related(prompt):
            return "⚠️ Lo siento, solo puedo responder preguntas relacionadas con derecho y asuntos jurídicos. Por favor, formula tu pregunta sobre temas legales, leyes, contratos o procesos judiciales."
            
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
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error leyendo PDF: {e}")
        return None

# Inicializar asistente de IA para derecho
ai_assistant = AIAssistant()

@bot.event
async def on_ready():
    global syllabus_text
    
    print(f'✅ Bot {bot.user} conectado!')
    print(f'📊 En {len(bot.guilds)} servidores')
    
    # Cargar syllabus (debes tener un syllabus legal)
    syllabus_text = extract_text_from_pdf("syllabus.pdf")
    if syllabus_text:
        print("📄 Syllabus legal cargado correctamente")
    else:
        print("❌ Error cargando el syllabus legal")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Si el mensaje NO empieza con !, verificar si es un comando natural
    if not message.content.startswith('!'):
        msg = message.content.lower()
        
        if msg.startswith(('preguntar ', 'consulta ', 'duda ')):
            pregunta = message.content.split(' ', 1)[1]
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('preguntar'), pregunta=pregunta)
            return
        
        elif msg.startswith(('asistente ', 'ia ', 'chat ', 'ai ', 'abogado ')):
            mensaje = message.content.split(' ', 1)[1]
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('asistente'), mensaje=mensaje)
            return
        
        elif msg in ['hola', 'saludos', 'hi', 'hello']:
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('hola'))
            return
        
        elif msg in ['syllabus', 'temario', 'contenido', 'curso']:
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('syllabus'))
            return
        
        elif msg in ['módulos', 'modulos', 'unidades', 'temas']:
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('modulos'))
            return
        
        elif msg == 'ping':
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('ping'))
            return
        
        elif msg in ['ayuda', 'help', 'comandos']:
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('ayuda'))
            return
    
    # Procesar comandos normales con !
    await bot.process_commands(message)


@bot.command()
async def preguntar(ctx, *, pregunta):
    """Responde preguntas sobre el syllabus de derecho"""
    global syllabus_text
    
    if not syllabus_text:
        await ctx.send("❌ El syllabus no está disponible.")
        return
    
    # Verificar si la pregunta está relacionada con derecho
    if not ai_assistant.is_legal_related(pregunta):
        embed = discord.Embed(
            title="⚠️ Tema no relacionado",
            description="Solo puedo responder preguntas sobre derecho y asuntos jurídicos. Por favor, formula tu pregunta sobre temas legales.",
            color=0xff0000
        )
        embed.add_field(
            name="Ejemplos de temas válidos", 
            value="• Contratos y documentos\n• Procesos judiciales\n• Derechos y obligaciones\n• Áreas del derecho (civil, penal, laboral)\n• Consultas legales generales",
            inline=False
        )
        await ctx.send(embed=embed)
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
            title="📚 Respuesta del Syllabus Legal",
            description=respuesta,
            color=0x00ff00
        )
        embed.add_field(name="Pregunta", value=pregunta, inline=False)
        embed.set_footer(text="Información basada en el syllabus del curso de derecho")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error procesando pregunta: {e}")
        await ctx.send("❌ Error procesando tu pregunta. Intenta de nuevo.")

@bot.command()
async def asistente(ctx, *, mensaje):
    """Pregunta anything al asistente de IA especializado en derecho"""
    try:
        # Mostrar que está procesando
        processing_msg = await ctx.send("⚖️ Procesando tu consulta legal...")
        
        # Obtener respuesta de la IA
        respuesta = ai_assistant.get_response(mensaje)
        
        # Limitar longitud para Discord
        if len(respuesta) > 1500:
            respuesta = respuesta[:1500] + "..."
        
        embed = discord.Embed(
            title="🧠 Asistente Jurídico IA",
            description=respuesta,
            color=0x0099ff
        )
        embed.add_field(name="Consulta", value=mensaje, inline=False)
        embed.set_footer(text="Respuesta generada por IA - Especializada en derecho | No sustituye asesoramiento legal profesional")
        
        await processing_msg.delete()
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error con asistente IA: {e}")
        await ctx.send("❌ Error conectando con el asistente IA. Intenta más tarde.")

@bot.command()
async def hola(ctx):
    """Saludo del bot"""
    await ctx.send("¡Hola! Soy tu asistente especializado en Derecho. Usa `!ayuda` para ver comandos.")

@bot.command()
async def ayuda(ctx):
    """Muestra todos los comandos disponibles"""
    embed = discord.Embed(
        title="🤖 Comandos Disponibles - Especializado en Derecho",
        description="**Prefix: `!`** o **Sin prefix** (solo algunos comandos)",
        color=0xff9900
    )
    embed.add_field(name="`!hola` o `hola`", value="Saludo del bot", inline=False)
    embed.add_field(name="`!preguntar [pregunta]` o `preguntar [pregunta]`", value="Busca en el syllabus de derecho", inline=False)
    embed.add_field(name="`!asistente [pregunta]` o `asistente [pregunta]`", value="Pregunta al IA especializado en derecho", inline=False)
    embed.add_field(name="`!syllabus` o `syllabus`", value="Info del curso de derecho", inline=False)
    embed.add_field(name="`!modulos` o `modulos`", value="Módulos del curso de derecho", inline=False)
    embed.add_field(name="`!ping` o `ping`", value="Verifica latencia", inline=False)
    embed.add_field(name="`!ayuda` o `ayuda`", value="Muestra esta ayuda", inline=False)
    embed.add_field(
        name="📋 Temas que puedo tratar", 
        value="• Derecho civil y mercantil\n• Derecho penal\n• Derecho laboral\n• Derecho administrativo\n• Contratos y documentos\n• Procesos judiciales",
        inline=False
    )
    embed.add_field(
        name="⚠️ Importante", 
        value="Este asistente no sustituye el consejo de un abogado. Para casos específicos, consulta siempre con un profesional.",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Comandos existentes adaptados a derecho
@bot.command()
async def syllabus(ctx):
    """Muestra información sobre el syllabus de derecho"""
    embed = discord.Embed(
        title="📚 Syllabus de Derecho con IA",
        description="Curso especializado para abogados - Nivel Avanzado",
        color=0x0099ff
    )
    embed.add_field(name="Duración", value="80 horas", inline=True)
    embed.add_field(name="Nivel", value="Avanzado", inline=True)
    embed.add_field(name="Módulos", value="4 módulos principales", inline=True)
    embed.add_field(name="Temáticas", value="IA aplicada al derecho, automatización, análisis jurisprudencial", inline=False)
    embed.set_footer(text="Usa !preguntar para consultas específicas sobre derecho")
    await ctx.send(embed=embed)

@bot.command()
async def modulos(ctx):
    """Muestra los módulos del curso de derecho con IA"""
    embed = discord.Embed(title="📦 Módulos del Curso de Derecho con IA", color=0xff9900)
    embed.add_field(name="1️⃣ Fundamentos de IA para abogados", value="Introducción, conceptos básicos, herramientas", inline=False)
    embed.add_field(name="2️⃣ Automatización de procesos legales", value="Documentos automatizados, contratos inteligentes", inline=False)
    embed.add_field(name="3️⃣ Análisis jurisprudencial con IA", value="Herramientas de análisis, predictibilidad", inline=False)
    embed.add_field(name="4️⃣ Ética y futuro del derecho con IA", value="Límites éticos, tendencias futuras", inline=False)
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