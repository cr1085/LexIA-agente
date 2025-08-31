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
import sqlite3
import datetime
from datetime import timedelta
import asyncio

# Base de datos simple para casos
def init_db():
    conn = sqlite3.connect('casos_legales.db')
    c = conn.cursor()
    
    # Tabla de casos
    c.execute('''CREATE TABLE IF NOT EXISTS casos
                 (id INTEGER PRIMARY KEY, cliente TEXT, tipo TEXT, 
                 descripcion TEXT, fecha_creacion TEXT, fecha_vencimiento TEXT,
                 estado TEXT, usuario_id INTEGER)''')
    
    # Tabla de documentos
    c.execute('''CREATE TABLE IF NOT EXISTS documentos
                 (id INTEGER PRIMARY KEY, nombre TEXT, tipo TEXT, 
                 contenido TEXT, variables TEXT, usuario_id INTEGER)''')
    
    # Tabla de recordatorios
    c.execute('''CREATE TABLE IF NOT EXISTS recordatorios
                 (id INTEGER PRIMARY KEY, caso_id INTEGER, fecha TEXT, 
                 mensaje TEXT, usuario_id INTEGER)''')
    
    conn.commit()
    conn.close()

# Inicializar base de datos al iniciar
init_db()

# CONFIGURACIÓN INICIAL
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

# TÉRMINOS JURÍDICOS
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
    'recurso de amparo', 'recurso de protección', 'recurso de inconstitucionalidad', 'recurso de casación',
    'usufructo', 'nuda propiedad', 'nuda_propiedad', 'derecho real','derecho de uso', 'derecho de disfrute', 
    'propiedad', 'dominio','derechos reales', 'derecho de goce', 'derecho de disposición','derecho de superficie',
     'servidumbre', 'derecho real de garantía','hipoteca', 'prenda', 'anticresis', 'derecho de retención'
]

# Diccionario de conocimientos legales
BASE_CONOCIMIENTO = {
    "contratos": {
        "requisitos": "**Requisitos de validez (Art. 1261 Código Civil):**\n\n• 🤝 **Consentimiento:** Acuerdo libre y consciente entre las partes\n• 📦 **Objeto:** Prestación posible, lícita, determinada o determinable\n• 🎯 **Causa:** Fin lícito y real de la obligación\n• 👥 **Capacidad:** Mayores de edad no incapacitados legalmente\n• 📝 **Forma:** Modalidad requerida por ley (escrita, notarial, etc.)",
        
        "nulidad": "**Causas de nulidad contractual:**\n\n🚫 **Nulidad Absoluta:**\n- Incapacidad absoluta de las partes\n- Objeto ilícito o imposible\n- Causa ilícita\n- Contratos simulados\n\n⚖️ **Nulidad Relativa:**\n- Violencia o intimidación\n- Error esencial\n- Lesión en contratos\n- Incapacidad relativa",
        
        "tipos": "**Tipos principales de contratos:**\n\n📋 **Por su formación:**\n- Consensuales (acuerdo verbal/escrito)\n- Reales (entrega cosa)\n- Solemnes (forma específica)\n\n🏢 **Por su contenido:**\n- Compraventa (transferencia propiedad)\n- Arrendamiento (uso temporal)\n- Prestación servicios (actividad profesional)\n- Donación (gratuita)\n- Sociedad (aporte común)",
        
        "elementos": "**Elementos del contrato:**\n\n🔧 **Esenciales:** Sin ellos no existe contrato\n- Consentimiento, objeto, causa\n\n⚙️ **Naturales:** Se presumen pero pueden excluirse\n- Responsabilidad por vicios ocultos\n- Obligaciones accesorias\n\n🎛️ **Accidentales:** Cláusulas especiales\n- Condición (hecho futuro)\n- Término (plazo)\n- Modo (carga en donaciones)",
        
        "interpretacion": "**Reglas de interpretación:**\n\n📖 **Principios generales:**\n- Buena fe contractual\n- Intención común de las partes\n- Efectos útiles y prácticos\n- Contra el predisponente en caso de dudas\n\n🔍 **Criterios específicos:**\n- Sentido natural de las palabras\n- Contexto y circunstancias\n- Conducta posterior de las partes"
    },
    
    "derecho_laboral": {
        "contrato_trabajo": "**Contrato de trabajo:**\n\n📄 **Requisitos esenciales:**\n- Prestación personal de servicios\n- Remuneración\n- Subordinación jurídica\n- Ajenidad (riesgos del empresario)\n\n⏰ **Modalidades:**\n- Indefinido\n- Temporal\n- Formación\n- Prácticas\n\n📋 **Contenido mínimo:**\n- Identificación partes\n- Duración y jornada\n- Salario and pagas\n- Función y lugar trabajo",
        
        "despido": "**Tipos de despido:**\n\n🔴 **Despido disciplinario:**\n- Por incumplimiento grave del trabajador\n- Sin indemnización\n- Procedente o improcedente\n\n🔵 **Despido objetivo:**\n- Causas económicas, técnicas u organizativas\n- Indemnización 20 días por año\n- Máximo 12 mensualidades\n\n🟢 **Despido colectivo:**\n- Afecta a múltiples trabajadores\n- Requiere procedimiento específico\n- Consultas con representantes",
        
        "jornada": "**Jornada laboral:**\n\n⏱️ **Límites legales:**\n- 40 horas semanales\n- 9 horas diarias\n- Descanso mínimo 12 horas entre jornadas\n- Descanso semanal 1.5 días\n\n📊 **Horas extraordinarias:**\n- Máximo 80 horas anuales\n- Voluntarias y retribuidas\n- No recuperables salvo convenio\n\n🏖️ **Descansos y vacaciones:**\n- 30 días naturales de vacaciones\n- Descanso en festivos\n- Permisos retribuidos"
    },
    "derecho_civil": {
        "usufructo": "**Usufructo:** Derecho real a usar y disfrutar bienes ajenos sin alterar su sustancia\n• Titular: Usufructuario\n• Obligaciones: Conservar la cosa, pagar cargas\n• Extinción: Muerte, renuncia, prescripción",
        "nuda_propiedad": "**Nuda Propiedad:** Derecho de propiedad sin posesión ni disfrute\n• Titular: Nudo propietario\n• Derechos: Disposición futura, vigilancia\n• Recupera plena propiedad al extinguirse usufructo",
        "diferencias": "**Diferencias Usufructo vs Nuda Propiedad:**\n• Usufructo: Derecho de uso y disfrute\n• Nuda Propiedad: Derecho de disposición futura\n• El usufructuario posee, el nudo propietario es dueño\n• Usufructo es temporal, nuda propiedad es permanente"
    },
    
    "derecho_mercantil": {
        "sociedades": "**Tipos de Sociedades Mercantiles:**\n• SL (Sociedad Limitada)\n• SA (Sociedad Anónima)\n• SCoop (Sociedad Cooperativa)\n• SCom (Sociedad Comanditaria)",
        "contratos_mercantiles": "**Contratos Mercantiles Especiales:**\n• Compraventa mercantil\n• Suministro\n• Transporte\n• Seguro\n• Franquicia",
        "quiebra": "**Procedimiento Concursal:**\n• Concurso de acreedores\n• Sección de acreedores\n• Convenio concursal\n• Liquidación"
    }
}

# PROMPT FORTALECIDO DEL SISTEMA
SYSTEM_PROMPT_FORTALECIDO = """Eres un asistente especializado EXCLUSIVAMENTE en derecho y asuntos jurídicos. 

**REGLAS ESTRICTAS:**
1. 🚫 SOLO respondes preguntas sobre DERECHO
2. 🚫 NUNCA respondas sobre tecnología, ciencia, salud, finanzas, entretenimiento u otros temas
3. 🚫 Si la pregunta no es sobre derecho, responde ÚNICAMENTE con el mensaje de error
4. ✅ Provee información general educativa sobre conceptos legales
5. ✅ Siempre aclara que es información general, no asesoramiento legal

**RESPUESTA PARA TEMAS NO JURÍDICOS:**
"⚠️ Lo siento, solo puedo responder preguntas relacionadas con derecho y asuntos jurídicos. Por favor, formula tu pregunta sobre temas legales, leyes, contratos o procesos judiciales."

**EJEMPLOS DE TEMAS VÁLIDOS:**
- Contratos, testamentos, poderes notariales
- Demandas, procesos judiciales, pleitos
- Derecho laboral, civil, penal, mercantil
- Leyes, regulaciones, normativas
- Derechos y obligaciones legales

**FORMATO DE RESPUESTA:**
⚖️ [Título del tema]

📋 [Información principal]

🔍 Puntos clave:
• [Punto 1]
• [Punto 2]

⚠️ Importante: [Advertencia específica]

💡 Recomendación: [Sugerencia práctica]

⚖️ Aviso Legal: Esta es información general educativa. No sustituye el asesoramiento de un abogado.
"""

def limitar_respuesta_inteligente(respuesta, max_length=2800):
    """Limita la respuesta respetando frases completas SIN puntos suspensivos"""
    if len(respuesta) <= max_length:
        return respuesta
    
    # Buscar el último punto dentro del límite
    ultimo_punto = respuesta.rfind('.', 0, max_length)
    
    # Si no hay punto, buscar el último signo de puntuación
    if ultimo_punto == -1:
        ultimo_signo = max(
            respuesta.rfind('?', 0, max_length),
            respuesta.rfind('!', 0, max_length),
            respuesta.rfind(';', 0, max_length)
        )
        if ultimo_signo != -1:
            return respuesta[:ultimo_signo + 1]
    
    # Si no hay signos de puntuación, buscar el último espacio
    if ultimo_punto == -1:
        ultimo_espacio = respuesta.rfind(' ', 0, max_length)
        if ultimo_espacio != -1:
            return respuesta[:ultimo_espacio]
    
    # Cortar en el último punto completo (sin puntos suspensivos)
    if ultimo_punto != -1:
        return respuesta[:ultimo_punto + 1]
    
    return respuesta[:max_length]

def obtener_sinonimos(termino):
    """Sistema de sinónimos para búsquedas inteligentes"""
    sinónimos_completos = {
        "requisitos": ["requisito", "requiere", "necesita", "exige", "condiciones", "exigencias", "necesidades"],
        "nulidad": ["nulo", "invalido", "anulable", "invalidar", "nulificar", "invalidéz", "anulación"],
        "tipos": ["tipo", "clases", "modalidades", "variedades", "categorías", "clasificación"],
        "elementos": ["elemento", "componentes", "partes", "ingredientes", "factores", "aspectos"],
        "interpretacion": ["interpretar", "entender", "comprender", "explicación", "significado", "hermenéutica"],
        "contrato_trabajo": ["contrato laboral", "contrato de trabajo", "relación laboral", "vínculo laboral"],
        "despido": ["despedir", "terminación", "fin contrato", "cese", "finalización", "rescisión"],
        "jornada": ["horario", "horas", "tiempo trabajo", "jornada laboral", "horas laborales", "turnos"]
    }
    return sinónimos_completos.get(termino, [])

class AIAssistant:
    def __init__(self):
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    
    # def is_legal_related(self, prompt: str) -> bool:
    #     """Verifica SIEMPRE si el prompt está relacionado con derecho"""
    #     prompt_lower = prompt.lower()
        
    #     # Palabras que INDICAN que NO es derecho
    #     palabras_no_juridicas = [
    #         'tecnología', 'tecnologia', 'ciencia', 'salud', 'bienestar', 'finanzas',
    #         'negocios', 'cultura', 'educación', 'educacion', 'historia', 'geografía',
    #         'geografia', 'entretenimiento', 'videojuegos', 'deportes', 'cocina',
    #         'música', 'musica', 'arte', 'cine', 'películas', 'series', 'programación',
    #         'programacion', 'matemáticas', 'matematicas', 'física', 'fisica', 'química',
    #         'quimica', 'biología', 'biologia', 'medicina', 'deporte', 'ejercicio',
    #         'video', 'juego', 'juguete', 'comida', 'receta', 'música', 'deporte', 'ejercicio'
    #     ]
        
    #     # Si contiene palabras no jurídicas, BLOQUEAR
    #     if any(palabra in prompt_lower for palabra in palabras_no_juridicas):
    #         return False
        
    #     # Búsqueda de términos jurídicos
    #     for term in LEGAL_TERMS:
    #         if term in prompt_lower:
    #             return True
        
    #     # Patrones de preguntas legales
    #     patterns = [
    #         r'(cómo|como)\s+(demandar|demandar|demanda|reclamar).*',
    #         r'(qué|que)\s+(debo|debería|deberia).*(hacer|hacerlo|proceder).*(legal|ley|derecho)',
    #         r'(necesito|quiero)\s+(hacer|redactar).*(contrato|testamento|poder)',
    #         r'(cuánto|cuanto)\s+(tiempo|dura|tarda).*(proceso|juicio|demanda)',
    #         r'(qué|que)\s+(derechos|obligaciones).*(tengo|tiene)',
    #         r'(es|son)\s+(legal|legales|ilegal|ilegales).*',
    #         r'(cómo|como)\s+(defender|proteger).*(derechos|intereses)',
    #         r'(qué|que)\s+(ley|norma|regula).*',
    #         r'(requisitos|documentos).*(necesarios|precisos).*(para|para)',
    #         r'(responsabilidad|culpa).*(civil|penal)'
    #     ]
        
    #     for pattern in patterns:
    #         if re.search(pattern, prompt_lower):
    #             return True
                
    #     return False

    def is_legal_related(self, prompt: str) -> bool:
        """Verifica SIEMPRE si el prompt está relacionado con derecho"""
        prompt_lower = prompt.lower()
        
        # Palabras que INDICAN que NO es derecho (AFINAR esta lista)
        palabras_no_juridicas = [
            'tecnología', 'tecnologia', 'ciencia', 'salud', 'bienestar', 'finanzas',
            'negocios', 'cultura', 'educación', 'educacion', 'historia', 'geografía',
            'geografia', 'entretenimiento', 'videojuegos', 'deportes', 'cocina',
            'música', 'musica', 'arte', 'cine', 'películas', 'series', 'programación',
            'programacion', 'matemáticas', 'matematicas', 'física', 'fisica', 'química',
            'quimica', 'biología', 'biologia', 'medicina', 'deporte', 'ejercicio',
            'video', 'juego', 'juguete', 'comida', 'receta', 'música', 'deporte', 'ejercicio',
            # Remover términos que puedan ser ambiguos
            # 'propiedad'  ← ¡ESTE ERA EL PROBLEMA! "propiedad" puede ser jurídico
        ]
        
        # Excepciones - palabras que SUENAN no jurídicas pero SÍ lo son
        excepciones_juridicas = [
            'propiedad', 'derecho', 'contrato', 'ley', 'legal', 'jurídico', 'juicio',
            'proceso', 'demanda', 'testamento', 'herencia', 'usufructo', 'nuda propiedad'
        ]
        
        # Si contiene palabras no jurídicas PERO NO es excepción
        for palabra in palabras_no_juridicas:
            if palabra in prompt_lower and not any(exc in prompt_lower for exc in excepciones_juridicas):
                return False
        
        # Búsqueda de términos jurídicos (lista ampliada)
        for term in LEGAL_TERMS:
            if term in prompt_lower:
                return True
        
        # Patrones de preguntas legales
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
            r'(responsabilidad|culpa).*(civil|penal)',
            # Patrones específicos para propiedad
            r'(diferencia|diferencias|distinción).*(usufructo|nuda propiedad|propiedad)',
            r'(usufructo|nuda propiedad).*(qué|que|significa|definición)',
            r'(derecho real|derechos reales).*(usufructo|propiedad|superficie)'
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
                        "content": SYSTEM_PROMPT_FORTALECIDO
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
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
                        "content": SYSTEM_PROMPT_FORTALECIDO
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

# Tarea programada para recordatorios
async def check_recordatorios():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            conn = sqlite3.connect('casos_legales.db')
            c = conn.cursor()
            hoy = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # Buscar recordatorios para hoy
            c.execute("SELECT r.id, r.caso_id, r.mensaje, c.cliente, c.usuario_id FROM recordatorios r JOIN casos c ON r.caso_id = c.id WHERE r.fecha = ?", (hoy,))
            recordatorios = c.fetchall()
            
            for recordatorio in recordatorios:
                user_id = recordatorio[4]
                try:
                    user = await bot.fetch_user(user_id)
                    if user:
                        await user.send(f"⏰ **Recordatorio de caso**: {recordatorio[3]}\n{recordatorio[2]}")
                except:
                    print(f"No se pudo enviar recordatorio al usuario {user_id}")
            
            conn.close()
        except Exception as e:
            print(f"Error en check_recordatorios: {e}")
        
        await asyncio.sleep(3600)

@bot.event
async def on_ready():
    global syllabus_text
    
    print(f'✅ Bot {bot.user} conectado!')
    print(f'📊 En {len(bot.guilds)} servidores')
    
    # Cargar syllabus
    syllabus_text = extract_text_from_pdf("syllabus.pdf")
    if syllabus_text:
        print("📄 Syllabus legal cargado correctamente")
    else:
        print("❌ Error cargando el syllabus legal")
    
    # Iniciar la tarea de recordatorios
    bot.loop.create_task(check_recordatorios())

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Comandos naturales (sin !)
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
    
    await bot.process_commands(message)

@bot.command()
async def asesoria(ctx, area: str, *, pregunta: str):
    """Ofrece asesoría legal mejorada con base de conocimiento enriquecida"""
    
    # Normalizar área (aceptar con espacios o guiones)
    area_normalizada = area.lower().replace(" ", "_").replace("-", "_")
    
    if area_normalizada not in BASE_CONOCIMIENTO:
        # Sugerir áreas disponibles de forma amigable
        areas_disponibles = "\n".join([f"• {area.replace('_', ' ').title()}" for area in BASE_CONOCIMIENTO.keys()])
        
        embed = discord.Embed(
            title="❌ Área no reconocida",
            description=f"Las áreas disponibles son:",
            color=0xff0000
        )
        embed.add_field(name="📚 Áreas Jurídicas", value=areas_disponibles, inline=False)
        embed.set_footer(text="Usa: !asesoria [área] [tu pregunta]")
        
        await ctx.send(embed=embed)
        return
    
    conocimiento = BASE_CONOCIMIENTO[area_normalizada]
    pregunta_lower = pregunta.lower()
    
    # Búsqueda inteligente con sinónimos
    terminos_encontrados = []
    for termino, explicacion in conocimiento.items():
        if (termino in pregunta_lower or 
            any(sinonimo in pregunta_lower for sinonimo in obtener_sinonimos(termino))):
            terminos_encontrados.append((termino, explicacion))
    
    # Crear embed de respuesta
    embed = discord.Embed(
        title=f"⚖️ Asesoría en {area_normalizada.replace('_', ' ').title()}",
        description=f"**Consulta:** {pregunta}",
        color=0x0099ff
    )
    
    if terminos_encontrados:
        for termino, explicacion in terminos_encontrados:
            embed.add_field(
                name=f"📌 {termino.replace('_', ' ').title()}",
                value=explicacion,
                inline=False
            )
    else:
        # Usar IA para respuesta general si no encuentra términos específicos
        respuesta_ia = ai_assistant.get_response(f"Explica sobre {pregunta} en el área de {area_normalizada}")
        embed.add_field(
            name="💡 Información General",
            value=respuesta_ia[:2000] if len(respuesta_ia) > 2000 else respuesta_ia,
            inline=False
        )
    
    # Añadir términos relacionados disponibles
    otros_terminos = [f"• {t.replace('_', ' ').title()}" for t in conocimiento.keys() if t not in [t[0] for t in terminos_encontrados]]
    if otros_terminos:
        embed.add_field(
            name="📚 Temas Relacionados Disponibles",
            value="\n".join(otros_terminos[:5]),
            inline=False
        )
    
    # Advertencia legal
    embed.set_footer(text="⚠️ Información general educativa - Consulta con abogado para casos específicos")
    
    await ctx.send(embed=embed)

@bot.command()
async def programar_recordatorio(ctx, fecha: str, *, tarea: str):
    """Programa recordatorios de plazos legales"""
    await ctx.send(f"⏰ Recordatorio programado para {fecha}: {tarea}")

@bot.command()
async def consultoria(ctx, *, pregunta: str):
    """Ofrece consultoría legal básica con IA"""
    respuesta = ai_assistant.get_response(f"Consulta de asesoría: {pregunta}")
    await ctx.send(f"🎓 Asesoría:\n{respuesta}")

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
        
        # Buscar coincidencias relevantes
        lineas_relevantes = []
        for linea in syllabus_text.split('\n'):
            if any(palabra in linea.lower() for palabra in pregunta_lower.split()):
                if len(linea.strip()) > 20:  # Solo líneas con contenido
                    lineas_relevantes.append(linea.strip())
        
        if lineas_relevantes:
            respuesta = "\n".join(lineas_relevantes[:3])  # Máximo 3 líneas
            if len(respuesta) > 1000:
                respuesta = respuesta[:1000]
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
        # Verificación EXTRA de tema jurídico
        if not ai_assistant.is_legal_related(mensaje):
            embed = discord.Embed(
                title="🚫 Tema No Jurídico",
                description="Solo puedo responder preguntas sobre derecho y asuntos jurídicos.",
                color=0xff0000
            )
            embed.add_field(
                name="Ejemplos de temas válidos",
                value="• Contratos y documentos legales\n• Procesos judiciales\n• Derechos y obligaciones\n• Leyes y regulaciones\n• Asesoría legal general",
                inline=False
            )
            embed.set_footer(text="Por favor, formula tu pregunta sobre temas legales")
            await ctx.send(embed=embed)
            return
        
        processing_msg = await ctx.send("⚖️ Procesando tu consulta legal...")
        
        # Obtener respuesta de la IA
        respuesta = ai_assistant.get_response(mensaje)
        
        # Limitar longitud RESPETANDO FRASES COMPLETAS
        respuesta = limitar_respuesta_inteligente(respuesta, 2800)
        
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
        await ctx.send("❌ Error técnico procesando tu consulta. Intenta más tarde.")

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

# Nuevos comandos para asesorías y gestión de casos
@bot.command()
async def nuevo_caso(ctx, cliente: str, tipo: str, *, descripcion: str):
    """Crea un nuevo caso legal"""
    try:
        conn = sqlite3.connect('casos_legales.db')
        c = conn.cursor()
        fecha_creacion = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        # Establecer fecha de vencimiento por defecto (30 días)
        fecha_vencimiento = (datetime.datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        c.execute("INSERT INTO casos (cliente, tipo, descripcion, fecha_creacion, fecha_vencimiento, estado, usuario_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (cliente, tipo, descripcion, fecha_creacion, fecha_vencimiento, "Abierto", ctx.author.id))
        conn.commit()
        caso_id = c.lastrowid
        conn.close()
        
        embed = discord.Embed(
            title="✅ Caso Creado Exitosamente",
            description=f"Caso #{caso_id}: {cliente} - {tipo}",
            color=0x00ff00
        )
        embed.add_field(name="Descripción", value=descripcion, inline=False)
        embed.add_field(name="Fecha de vencimiento", value=fecha_vencimiento, inline=True)
        embed.add_field(name="Estado", value="Abierto", inline=True)
        embed.set_footer(text=f"Creado por {ctx.author.name}")
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error creando el caso: {str(e)}")

@bot.command()
async def mis_casos(ctx):
    """Muestra todos tus casos activos"""
    try:
        conn = sqlite3.connect('casos_legales.db')
        c = conn.cursor()
        c.execute("SELECT id, cliente, tipo, descripcion, fecha_creacion, fecha_vencimiento, estado FROM casos WHERE usuario_id = ?", (ctx.author.id,))
        casos = c.fetchall()
        conn.close()
        
        if not casos:
            await ctx.send("📝 No tienes casos registrados.")
            return
            
        embed = discord.Embed(
            title=f"📋 Casos de {ctx.author.name}",
            description="Lista de todos tus casos activos",
            color=0x0099ff
        )
        
        for caso in casos:
            estado_emoji = "🟢" if caso[6] == "Abierto" else "🔴"
            embed.add_field(
                name=f"{estado_emoji} Caso #{caso[0]}: {caso[1]}",
                value=f"**Tipo:** {caso[2]}\n**Vencimiento:** {caso[5]}\n**Estado:** {caso[6]}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error recuperando casos: {str(e)}")

@bot.command()
async def recordatorio(ctx, caso_id: int, dias: int, *, mensaje: str):
    """Programa un recordatorio para un caso específico"""
    try:
        conn = sqlite3.connect('casos_legales.db')
        c = conn.cursor()
        
        # Verificar que el caso existe y pertenece al usuario
        c.execute("SELECT id FROM casos WHERE id = ? AND usuario_id = ?", (caso_id, ctx.author.id))
        if not c.fetchone():
            await ctx.send("❌ Caso no encontrado o no tienes permisos.")
            return
        
        fecha_recordatorio = (datetime.datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
        c.execute("INSERT INTO recordatorios (caso_id, fecha, mensaje, usuario_id) VALUES (?, ?, ?, ?)",
                  (caso_id, fecha_recordatorio, mensaje, ctx.author.id))
        conn.commit()
        conn.close()
        
        await ctx.send(f"⏰ Recordatorio programado para el {fecha_recordatorio} para el caso #{caso_id}")
    except Exception as e:
        await ctx.send(f"❌ Error programando recordatorio: {str(e)}")

@bot.command()
async def plantilla(ctx, nombre: str, tipo: str, *, variables: str = ""):
    """Crea una plantilla de documento legal"""
    plantillas = {
        "contrato": "CONTRATO DE PRESTACIÓN DE SERVICIOS\nEntre {parte1} y {parte2}...",
        "poder": "PODER NOTARIAL\nYo {otorgante} otorgo poder a {apoderado}...",
        "demanda": "DEMANDA JUDICIAL\n{demandante} contra {demandado}...",
    }
    
    if tipo not in plantillas:
        await ctx.send("❌ Tipo de plantilla no válido. Usa: contrato, poder, demanda")
        return
        
    try:
        conn = sqlite3.connect('casos_legales.db')
        c = conn.cursor()
        c.execute("INSERT INTO documentos (nombre, tipo, contenido, variables, usuario_id) VALUES (?, ?, ?, ?, ?)",
                  (nombre, tipo, plantillas[tipo], variables, ctx.author.id))
        conn.commit()
        conn.close()
        
        await ctx.send(f"✅ Plantilla '{nombre}' creada exitosamente. Usa `!generar {nombre}` para generar un documento.")
    except Exception as e:
        await ctx.send(f"❌ Error creando plantilla: {str(e)}")

@bot.command()
async def generar(ctx, nombre_plantilla: str, *, valores: str):
    """Genera un documento a partir de una plantilla"""
    try:
        conn = sqlite3.connect('casos_legales.db')
        c = conn.cursor()
        c.execute("SELECT contenido, variables FROM documentos WHERE nombre = ? AND usuario_id = ?", 
                 (nombre_plantilla, ctx.author.id))
        plantilla = c.fetchone()
        conn.close()
        
        if not plantilla:
            await ctx.send("❌ Plantilla no encontrada.")
            return
            
        contenido, variables_esperadas = plantilla
        # Parsear los valores proporcionados
        valores_dict = {}
        for item in valores.split(','):
            if ':' in item:
                key, value = item.split(':', 1)
                valores_dict[key.strip()] = value.strip()
        
        # Reemplazar variables en la plantilla
        for key, value in valores_dict.items():
            contenido = contenido.replace(f"{{{key}}}", value)
            
        # Enviar el documento generado
        if len(contenido) > 1500:
            # Si es muy largo, dividirlo en partes
            partes = [contenido[i:i+1500] for i in range(0, len(contenido), 1500)]
            for i, parte in enumerate(partes):
                await ctx.send(f"📄 Documento (parte {i+1}):\n```{parte}```")
        else:
            await ctx.send(f"📄 Documento generado:\n```{contenido}```")
            
    except Exception as e:
        await ctx.send(f"❌ Error generando documento: {str(e)}")

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if TOKEN:
        try:
            bot.run(TOKEN)
        except Exception as e:
            logger.error(f"Error iniciando bot: {e}")
    else:
        print("❌ No se encontró DISCORD_TOKEN en .env")