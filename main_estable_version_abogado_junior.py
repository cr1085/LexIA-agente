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
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Para funcionar en entornos sin UI
import io
import pandas as pd
import numpy as np
from collections import Counter

# Configuración inicial
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# Configurar intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Base de datos mejorada para bufete de abogados
def init_db():
    conn = sqlite3.connect('bufete_legal.db')
    c = conn.cursor()
    
    # Tabla de casos
    c.execute('''CREATE TABLE IF NOT EXISTS casos
                 (id INTEGER PRIMARY KEY, cliente TEXT, tipo TEXT, 
                 descripcion TEXT, fecha_creacion TEXT, fecha_vencimiento TEXT,
                 estado TEXT, usuario_id INTEGER, prioridad TEXT, 
                 valor_estimado REAL, horas_invertidas REAL)''')
    
    # Tabla de documentos
    c.execute('''CREATE TABLE IF NOT EXISTS documentos
                 (id INTEGER PRIMARY KEY, nombre TEXT, tipo TEXT, 
                 contenido TEXT, variables TEXT, usuario_id INTEGER,
                 caso_id INTEGER, fecha_analisis TEXT)''')
    
    # Tabla de recordatorios
    c.execute('''CREATE TABLE IF NOT EXISTS recordatorios
                 (id INTEGER PRIMARY KEY, caso_id INTEGER, fecha TEXT, 
                 mensaje TEXT, usuario_id INTEGER, enviado INTEGER DEFAULT 0)''')
    
    # Tabla de aprendizaje (para mejorar respuestas)
    c.execute('''CREATE TABLE IF NOT EXISTS aprendizaje
                 (id INTEGER PRIMARY KEY, pregunta TEXT, respuesta TEXT, 
                  correcciones TEXT, calificacion INTEGER, fecha TEXT,
                  area_juridica TEXT)''')
    
    # Tabla de estadísticas
    c.execute('''CREATE TABLE IF NOT EXISTS estadisticas
                 (id INTEGER PRIMARY KEY, tipo TEXT, datos TEXT, 
                  fecha_creacion TEXT, usuario_id INTEGER)''')
    
    conn.commit()
    conn.close()

# Inicializar base de datos al iniciar
init_db()

# CONFIGURACIÓN PDF
try:
    import pypdf
    PdfReader = pypdf.PdfReader
    print("✅ Usando pypdf (nueva versión)")
except ImportError:
    import PyPDF2
    PdfReader = PyPDF2.PdfReader
    print("✅ Usando PyPDF2 (versión legacy)")

# Variables globales
syllabus_text = None

# TÉRMINOS JURÍDICOS AMPLIADOS
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
    'servidumbre', 'derecho real de garantía','hipoteca', 'prenda', 'anticresis', 'derecho de retención',
    'bufete', 'despacho', 'cliente', 'expediente', 'procura', 'procurador', 'audiencia', 'prueba', 'diligencias',
    'auto', 'resolución', 'recurso', 'alegato', 'informe', 'dictamen', 'peritación', 'tasación', 'embargo',
    'litis', 'pleito', 'controversia', 'litigio', 'acuerdo', 'transacción', 'conciliación', 'mediación',
    'árbitro', 'laudo', 'ejecución', 'sentencia', 'fallo', 'jurisprudencia', 'doctrina', 'normativa',
    'reglamento', 'directiva', 'decreto', 'ordenanza', 'instrucción', 'circular', 'resolución', 'edicto',
    'notificación', 'citación', 'emplazamiento', 'requerimiento', 'intimación', 'notificación', 'comunicación'
]

# PROMPT MEJORADO PARA ABOGADO NOVATO
SYSTEM_PROMPT_ABOGADO_NOVATO = """Eres un abogado junior (novato) que trabaja en un bufete de abogados. 
Estás aprendiendo pero tienes conocimientos sólidos de derecho. Tu función es asistir a abogados senior y clientes.

**TONO Y ACTITUD:**
- 👨‍⚖️ Profesional pero accesible
- 📚 Entusiasta por aprender y ayudar
- 🤝 Colaborativo con el equipo del bufete
- ⚠️ Cauto al dar consejos definitivos
- 🔍 Analítico pero reconociendo limitaciones

**FRASES CARACTERÍSTICAS:**
- "Como abogado en formación, mi análisis preliminar es..."
- "Basado en lo que he estudiado y la jurisprudencia reciente..."
- "Recomendaría consultar esto con un socio senior porque..."
- "En mi experiencia limitada, he visto que..."
- "Este caso me recuerda a uno similar que estudiamos donde..."

**ENFOQUE DE ANÁLISIS:**
1. 📋 Identificar el tipo de documento/caso
2. ⚖️ Determinar el área jurídica principal
3. 🔍 Señalar aspectos relevantes y puntos clave
4. ⚠️ Alertar sobre posibles problemas o irregularidades
5. 💡 Sugerir próximos pasos y consultas necesarias

**LÍMITES ÉTICOS:**
- 🚫 NUNCA dar garantías de éxito en casos
- 🚫 NUNCA proporcionar asesoramiento definitivo sin supervisión
- 🚫 NUNCA revelar información confidencial de otros casos
- ✅ SIEMPRE recomendar consultar con abogados senior para casos complejos
- ✅ SIEMPRE mantener confidencialidad de datos de clientes

**FORMATO DE RESPUESTAS:**
👨‍⚖️ **Análisis de [Nombre del Documento/Caso]**

📋 **Tipo identificado:** [Tipo de documento/caso]
⚖️ **Área jurídica:** [Área principal y secundarias]

🔍 **Puntos relevantes:**
• [Punto 1 importante]
• [Punto 2 importante]

⚠️ **Aspectos a verificar:**
• [Posible problema 1]
• [Posible problema 2]

💡 **Próximos pasos sugeridos:**
• [Paso 1 - Consultar con especialista en...]
• [Paso 2 - Revisar legislación sobre...]

📊 **Observaciones adicionales:** [Notas contextuales]

⚖️ **Aviso Legal:** Este es un análisis preliminar realizado por un abogado junior. No constituye asesoramiento legal definitivo y debe ser revisado por un abogado senior antes de cualquier acción.
"""

# Diccionario de conocimientos legales ampliado
BASE_CONOCIMIENTO = {
    "contratos": {
        "requisitos": "**Requisitos de validez (Art. 1261 Código Civil):**\n\n• 🤝 **Consentimiento:** Acuerdo libre y consciente entre las partes\n• 📦 **Objeto:** Prestación posible, lícita, determinada o determinable\n• 🎯 **Causa:** Fin lícito y real de la obligación\n• 👥 **Capacidad:** Mayores de edad no incapacitados legalmente\n• 📝 **Forma:** Modalidad requerida por ley (escrita, notarial, etc.)",
        "nulidad": "**Causas de nulidad contractual:**\n\n🚫 **Nulidad Absoluta:**\n- Incapacidad absoluta de las partes\n- Objeto ilícito o imposible\n- Causa ilícita\n- Contratos simulados\n\n⚖️ **Nulidad Relativa:**\n- Violencia o intimidación\n- Error esencial\n- Lesión en contratos\n- Incapacidad relativa",
        "tipos": "**Tipos principales de contratos:**\n\n📋 **Por su formación:**\n- Consensuales (acuerdo verbal/escrito)\n- Reales (entrega cosa)\n- Solemnes (forma específica)\n\n🏢 **Por su contenido:**\n- Compraventa (transferencia propiedad)\n- Arrendamiento (uso temporal)\n- Prestación servicios (actividad profesional)\n- Donación (gratuita)\n- Sociedad (aporte común)",
    },
    "derecho_laboral": {
        "contrato_trabajo": "**Contrato de trabajo:**\n\n📄 **Requisitos esenciales:**\n- Prestación personal de servicios\n- Remuneración\n- Subordinación jurídica\n- Ajenidad (riesgos del empresario)\n\n⏰ **Modalidades:**\n- Indefinido\n- Temporal\n- Formación\n- Prácticas",
        "despido": "**Tipos de despido:**\n\n🔴 **Despido disciplinario:**\n- Por incumplimiento grave del trabajador\n- Sin indemnización\n- Procedente o improcedente\n\n🔵 **Despido objetivo:**\n- Causas económicas, técnicas u organizativas\n- Indemnización 20 días por año\n- Máximo 12 mensualidades",
    },
    "derecho_civil": {
        "usufructo": "**Usufructo:** Derecho real a usar y disfrutar bienes ajenos sin alterar su sustancia\n• Titular: Usufructuario\n• Obligaciones: Conservar la cosa, pagar cargas\n• Extinción: Muerte, renuncia, prescripción",
        "nuda_propiedad": "**Nuda Propiedad:** Derecho de propiedad sin posesión ni disfrute\n• Titular: Nudo propietario\n• Derechos: Disposición futura, vigilancia\n• Recupera plena propiedad al extinguirse usufructo",
    },
    "derecho_mercantil": {
        "sociedades": "**Tipos de Sociedades Mercantiles:**\n• SL (Sociedad Limitada)\n• SA (Sociedad Anónima)\n• SCoop (Sociedad Cooperativa)\n• SCom (Sociedad Comanditaria)",
        "contratos_mercantiles": "**Contratos Mercantiles Especiales:**\n• Compraventa mercantil\n• Suministro\n• Transporte\n• Seguro\n• Franquicia",
    },
    "derecho_penal": {
        "delitos": "**Clasificación de delitos:**\n• Delitos graves: pena > 5 años\n• Delitos menos graves: pena 1-5 años\n• Delitos leves: pena < 1 año\n• Faltas: infracciones menores",
        "penas": "**Tipos de penas:**\n• Privación de libertad\n• Multa económica\n• Trabajos en beneficio de la comunidad\n• Inhabilitación profesional",
    },
    "derecho_familiar": {
        "divorcio": "**Procedimiento de divorcio:**\n\n📋 **Tipos:**\n- Mutuo acuerdo\n- Contencioso\n\n⏱️ **Plazos:**\n- 3 meses desde matrimonio (mutuo acuerdo)\n- No hay plazo mínimo (contencioso)",
        "patria_potestad": "**Patria Potestad:**\n• Derechos y deberes sobre hijos menores\n• Ejercicio conjunto por ambos progenitores\n• Puede ser modificada judicialmente",
    }
}

def limitar_respuesta_inteligente(respuesta, max_length=2800):
    """Limita la respuesta respetando frases completas SIN puntos suspensivos"""
    if len(respuesta) <= max_length:
        return respuesta
    
    ultimo_punto = respuesta.rfind('.', 0, max_length)
    if ultimo_punto != -1:
        return respuesta[:ultimo_punto + 1]
    
    ultimo_signo = max(
        respuesta.rfind('?', 0, max_length),
        respuesta.rfind('!', 0, max_length),
        respuesta.rfind(';', 0, max_length)
    )
    if ultimo_signo != -1:
        return respuesta[:ultimo_signo + 1]
    
    ultimo_espacio = respuesta.rfind(' ', 0, max_length)
    if ultimo_espacio != -1:
        return respuesta[:ultimo_espacio]
    
    return respuesta[:max_length]

def obtener_sinonimos(termino):
    """Sistema de sinónimos para búsquedas inteligentes"""
    sinónimos_completos = {
        "requisitos": ["requisito", "requiere", "necesita", "exige", "condiciones"],
        "nulidad": ["nulo", "invalido", "anulable", "invalidar", "nulificar"],
        "tipos": ["tipo", "clases", "modalidades", "variedades", "categorías"],
    }
    return sinónimos_completos.get(termino, [])

class AIAssistant:
    def __init__(self):
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    
    def is_legal_related(self, prompt: str) -> bool:
        """Verifica SIEMPRE si el prompt está relacionado con derecho"""
        prompt_lower = prompt.lower()
        
        palabras_no_juridicas = [
            'tecnología', 'tecnologia', 'ciencia', 'salud', 'bienestar', 'finanzas',
            'negocios', 'cultura', 'educación', 'educacion', 'historia', 'geografía',
            'geografia', 'entretenimiento', 'videojuegos', 'deportes', 'cocina',
            'música', 'musica', 'arte', 'cine', 'películas', 'series', 'programación',
            'programacion', 'matemáticas', 'matematicas', 'física', 'fisica', 'química',
            'quimica', 'biología', 'biologia', 'medicina', 'deporte', 'ejercicio',
            'video', 'juego', 'juguete', 'comida', 'receta', 'música', 'deporte', 'ejercicio',
        ]
        
        excepciones_juridicas = [
            'propiedad', 'derecho', 'contrato', 'ley', 'legal', 'jurídico', 'juicio',
            'proceso', 'demanda', 'testamento', 'herencia', 'usufructo', 'nuda propiedad'
        ]
        
        for palabra in palabras_no_juridicas:
            if palabra in prompt_lower and not any(exc in prompt_lower for exc in excepciones_juridicas):
                return False
        
        for term in LEGAL_TERMS:
            if term in prompt_lower:
                return True
        
        patterns = [
            r'(cómo|como)\s+(demandar|demandar|demanda|reclamar).*',
            r'(qué|que)\s+(debo|debería|deberia).*(hacer|hacerlo|proceder).*(legal|ley|derecho)',
            r'(necesito|quiero)\s+(hacer|redactar).*(contrato|testamento|poder)',
            r'(cuánto|cuanto)\s+(tiempo|dura|tarda).*(proceso|juicio|demanda)',
            r'(qué|que)\s+(derechos|obligaciones).*(tengo|tiene)',
            r'(es|son)\s+(legal|legales|ilegal|ilegales).*',
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
                        "content": SYSTEM_PROMPT_ABOGADO_NOVATO
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2500
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
                        "content": SYSTEM_PROMPT_ABOGADO_NOVATO
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
        if not self.is_legal_related(prompt):
            return "⚠️ Lo siento, solo puedo responder preguntas relacionadas con derecho y asuntos jurídicos. Como abogado junior, debo mantenerme dentro de mi área de expertise."
            
        response = self.groq_assistant(prompt)
        if response:
            return response
            
        response = self.openrouter_assistant(prompt)
        if response:
            return response
            
        return "⚠️ Los servicios de IA no están disponibles temporalmente. Como abogado junior, recomiendo consultar directamente con un socio senior."

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

def analizar_texto_juridico(texto: str) -> dict:
    """Analiza texto jurídico para identificar conceptos clave"""
    resultados = {
        'areas_juridicas': [],
        'terminos_clave': [],
        'plazos': [],
        'referencias_legales': [],
        'partes_involucradas': []
    }
    
    # Detectar áreas jurídicas
    areas = ['civil', 'penal', 'laboral', 'mercantil', 'administrativo', 'constitucional', 'familiar']
    for area in areas:
        if area in texto.lower():
            resultados['areas_juridicas'].append(area)
    
    # Detectar términos jurídicos clave
    for termino in LEGAL_TERMS:
        if termino in texto.lower():
            resultados['terminos_clave'].append(termino)
    
    # Detectar plazos (patrones como "días", "meses", "años")
    plazos = re.findall(r'(\d+)\s*(día|días|mes|meses|año|años)', texto, re.IGNORECASE)
    resultados['plazos'] = plazos
    
    # Detectar referencias legales
    referencias = re.findall(r'(ley|artículo|art|Ley|Artículo|Art)\s*(\d+[/\-]\d+|\d+)', texto)
    resultados['referencias_legales'] = referencias
    
    return resultados

# Inicializar asistente de IA para derecho
ai_assistant = AIAssistant()

# Tarea programada para recordatorios
async def check_recordatorios():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            conn = sqlite3.connect('bufete_legal.db')
            c = conn.cursor()
            hoy = datetime.datetime.now().strftime("%Y-%m-%d")
            
            c.execute("SELECT r.id, r.caso_id, r.mensaje, c.cliente, c.usuario_id FROM recordatorios r JOIN casos c ON r.caso_id = c.id WHERE r.fecha = ? AND r.enviado = 0", (hoy,))
            recordatorios = c.fetchall()
            
            for recordatorio in recordatorios:
                user_id = recordatorio[4]
                try:
                    user = await bot.fetch_user(user_id)
                    if user:
                        await user.send(f"⏰ **Recordatorio de caso**: {recordatorio[3]}\n{recordatorio[2]}")
                        # Marcar como enviado
                        c.execute("UPDATE recordatorios SET enviado = 1 WHERE id = ?", (recordatorio[0],))
                except Exception as e:
                    print(f"No se pudo enviar recordatorio al usuario {user_id}: {e}")
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error en check_recordatorios: {e}")
        
        await asyncio.sleep(3600)  # Revisar cada hora

@bot.event
async def on_ready():
    global syllabus_text
    
    print(f'✅ Bot {bot.user} conectado como Abogado Junior!')
    print(f'📊 En {len(bot.guilds)} servidores')
    
    # Cargar syllabus si existe
    if os.path.exists("syllabus.pdf"):
        syllabus_text = extract_text_from_pdf("syllabus.pdf")
        if syllabus_text:
            print("📄 Syllabus legal cargado correctamente")
        else:
            print("❌ Error cargando el syllabus legal")
    else:
        print("ℹ️ No se encontró syllabus.pdf")
    
    # Iniciar la tarea de recordatorios
    bot.loop.create_task(check_recordatorios())
    print("⏰ Sistema de recordatorios iniciado")

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
        
        elif msg.startswith(('asistente ', 'ia ', 'chat ', 'ai ', 'abogado ', 'analizar ')):
            mensaje = message.content.split(' ', 1)[1]
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('asistente'), mensaje=mensaje)
            return
        
        elif msg in ['hola', 'saludos', 'hi', 'hello', 'buenos días']:
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('hola'))
            return
        
        elif msg in ['estadisticas', 'estadísticas', 'métricas', 'métricas']:
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('estadisticas'))
            return
        
        elif msg in ['ayuda', 'help', 'comandos']:
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('ayuda'))
            return
    
    await bot.process_commands(message)

# COMANDOS PRINCIPALES MEJORADOS
@bot.command()
async def analizar_documento(ctx, documento_url: str = None):
    """Analiza documentos legales adjuntos o desde URL"""
    try:
        # Verificar si hay archivos adjuntos
        if not documento_url and not ctx.message.attachments:
            await ctx.send("❌ Por favor, adjunta un documento o proporciona una URL")
            return
        
        processing_msg = await ctx.send("📄 **Abogado Junior analizando documento...** ⚖️")
        
        texto_documento = ""
        nombre_documento = ""
        
        if documento_url:
            # Descargar desde URL (implementación básica)
            try:
                response = requests.get(documento_url, timeout=10)
                if response.status_code == 200:
                    # Aquí se podría implementar extracción de texto según el tipo
                    texto_documento = "Contenido del documento desde URL (análisis simulado)"
                    nombre_documento = documento_url.split('/')[-1]
                else:
                    await processing_msg.delete()
                    await ctx.send("❌ No se pudo descargar el documento desde la URL")
                    return
            except:
                await processing_msg.delete()
                await ctx.send("❌ Error al acceder a la URL proporcionada")
                return
        else:
            # Procesar archivo adjunto
            archivo = ctx.message.attachments[0]
            nombre_documento = archivo.filename
            
            if nombre_documento.lower().endswith('.pdf'):
                # Guardar temporalmente y extraer texto
                await archivo.save(f"temp_{nombre_documento}")
                texto_documento = extract_text_from_pdf(f"temp_{nombre_documento}")
                os.remove(f"temp_{nombre_documento}")
                
                if not texto_documento:
                    await processing_msg.delete()
                    await ctx.send("❌ No se pudo extraer texto del PDF")
                    return
            else:
                # Para otros tipos de archivo (simulado)
                texto_documento = f"Contenido del documento {nombre_documento} (análisis simulado)"
        
        # Análisis con IA
        prompt_analisis = f"""
        Como abogado junior, analiza este documento legal y proporciona un dictamen profesional:
        
        DOCUMENTO: {nombre_documento}
        CONTENIDO: {texto_documento[:3000]}
        
        Proporciona un análisis estructurado con:
        1. 📋 Tipo de documento identificado
        2. ⚖️ Área jurídica principal y secundarias
        3. 🔍 Puntos clave relevantes
        4. ⚠️ Posibles problemas o irregularidades
        5. 💡 Recomendaciones y próximos pasos
        
        Mantén el tono de un abogado junior: profesional pero reconociendo limitaciones.
        """
        
        analisis = ai_assistant.get_response(prompt_analisis)
        
        # Guardar análisis en base de datos
        try:
            conn = sqlite3.connect('bufete_legal.db')
            c = conn.cursor()
            fecha_analisis = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("INSERT INTO documentos (nombre, tipo, contenido, usuario_id, fecha_analisis) VALUES (?, ?, ?, ?, ?)",
                     (nombre_documento, "analizado", texto_documento[:1000], ctx.author.id, fecha_analisis))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error guardando análisis: {e}")
        
        # Enviar resultados
        await processing_msg.delete()
        
        if len(analisis) > 1900:
            # Dividir si es muy largo
            partes = [analisis[i:i+1900] for i in range(0, len(analisis), 1900)]
            for i, parte in enumerate(partes):
                embed = discord.Embed(
                    title=f"📄 Dictamen Legal - Parte {i+1}",
                    description=parte,
                    color=0x0099ff
                )
                if i == 0:
                    embed.set_author(name=f"Análisis de {nombre_documento}")
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="📄 Dictamen Legal",
                description=analisis,
                color=0x0099ff
            )
            embed.set_author(name=f"Análisis de {nombre_documento}")
            embed.set_footer(text="Análisis realizado por Abogado Junior - Revisar con socio senior")
            await ctx.send(embed=embed)
            
    except Exception as e:
        logger.error(f"Error analizando documento: {e}")
        await ctx.send("❌ Error procesando el documento. Intenta más tarde.")

@bot.command()
async def estadisticas(ctx, tipo: str = "general"):
    """Genera estadísticas y gráficos del bufete"""
    try:
        processing_msg = await ctx.send("📊 Generando estadísticas...")
        
        conn = sqlite3.connect('bufete_legal.db')
        
        if tipo == "general" or tipo == "casos":
            # Estadísticas de casos
            df_casos = pd.read_sql_query("SELECT tipo, estado, prioridad, fecha_creacion FROM casos", conn)
            
            if not df_casos.empty:
                # Gráfico 1: Casos por tipo
                plt.figure(figsize=(10, 6))
                counts = df_casos['tipo'].value_counts()
                plt.bar(range(len(counts)), counts.values)
                plt.title('Casos por Tipo Legal')
                plt.xticks(range(len(counts)), counts.index, rotation=45, ha='right')
                plt.tight_layout()
                
                buf1 = io.BytesIO()
                plt.savefig(buf1, format='png')
                buf1.seek(0)
                plt.close()
                
                # Gráfico 2: Casos por estado
                plt.figure(figsize=(8, 8))
                estado_counts = df_casos['estado'].value_counts()
                plt.pie(estado_counts.values, labels=estado_counts.index, autopct='%1.1f%%')
                plt.title('Distribución de Estados de Casos')
                
                buf2 = io.BytesIO()
                plt.savefig(buf2, format='png')
                buf2.seek(0)
                plt.close()
                
                # Enviar gráficos
                await ctx.send(file=discord.File(buf1, 'casos_por_tipo.png'))
                await ctx.send(file=discord.File(buf2, 'estados_casos.png'))
                
                # Estadísticas numéricas
                total_casos = len(df_casos)
                casos_abiertos = len(df_casos[df_casos['estado'] == 'Abierto'])
                casos_cerrados = len(df_casos[df_casos['estado'] == 'Cerrado'])
                
                embed = discord.Embed(
                    title="📊 Estadísticas del Bufete",
                    description="Métricas generales de casos",
                    color=0x00ff00
                )
                embed.add_field(name="📈 Total de casos", value=str(total_casos), inline=True)
                embed.add_field(name="🔓 Casos abiertos", value=str(casos_abiertos), inline=True)
                embed.add_field(name="🔒 Casos cerrados", value=str(casos_cerrados), inline=True)
                embed.add_field(name="🎯 Tipo más común", value=counts.index[0] if len(counts) > 0 else "N/A", inline=True)
                embed.add_field(name="📅 Casos este mes", value=str(len(df_casos[df_casos['fecha_creacion'].str.contains(datetime.datetime.now().strftime("%Y-%m"))])), inline=True)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("ℹ️ No hay casos registrados para generar estadísticas.")
        
        elif tipo == "documentos":
            # Estadísticas de documentos
            df_docs = pd.read_sql_query("SELECT tipo, fecha_analisis FROM documentos WHERE tipo = 'analizado'", conn)
            
            if not df_docs.empty:
                plt.figure(figsize=(10, 6))
                # Agrupar por mes
                df_docs['mes'] = pd.to_datetime(df_docs['fecha_analisis']).dt.to_period('M')
                monthly_counts = df_docs['mes'].value_counts().sort_index()
                
                plt.plot(range(len(monthly_counts)), monthly_counts.values, marker='o')
                plt.title('Documentos Analizados por Mes')
                plt.xticks(range(len(monthly_counts)), [str(x) for x in monthly_counts.index], rotation=45)
                plt.tight_layout()
                
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                
                await ctx.send(file=discord.File(buf, 'documentos_analizados.png'))
                await ctx.send(f"📄 **Total de documentos analizados:** {len(df_docs)}")
            else:
                await ctx.send("ℹ️ No hay documentos analizados para generar estadísticas.")
        
        conn.close()
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error generando estadísticas: {e}")
        await ctx.send("❌ Error generando estadísticas. Intenta más tarde.")

# @bot.command()
# async def nuevo_caso(ctx, cliente: str, tipo: str, prioridad: str = "media", *, descripcion: str):
#     """Crea un nuevo caso legal con prioridad"""
#     try:
#         # Validar prioridad
#         prioridades_validas = ["baja", "media", "alta", "urgente"]
#         if prioridad.lower() not in prioridades_validas:
#             await ctx.send("❌ Prioridad no válida. Usa: baja, media, alta, urgente")
#             return
        
#         conn = sqlite3.connect('bufete_legal.db')
#         c = conn.cursor()
#         fecha_creacion = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
#         # Establecer fecha de vencimiento según prioridad
#         dias_vencimiento = {
#             "baja": 60,
#             "media": 30,
#             "alta": 15,
#             "urgente": 7
#         }
#         fecha_vencimiento = (datetime.datetime.now() + timedelta(days=dias_vencimiento[prioridad.lower()])).strftime("%Y-%m-%d")
        
#         c.execute("INSERT INTO casos (cliente, tipo, descripcion, fecha_creacion, fecha_vencimiento, estado, usuario_id, prioridad) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
#                  (cliente, tipo, descripcion, fecha_creacion, fecha_vencimiento, "Abierto", ctx.author.id, prioridad.lower()))
#         conn.commit()
#         caso_id = c.lastrowid
#         conn.close()
        
#         embed = discord.Embed(
#             title="✅ Caso Creado Exitosamente",
#             description=f"Caso #{caso_id}: {cliente} - {tipo}",
#             color=0x00ff00
#         )
#         embed.add_field(name="Descripción", value=descripcion, inline=False)
#         embed.add_field(name="Prioridad", value=prioridad.upper(), inline=True)
#         embed.add_field(name="Vencimiento", value=fecha_vencimiento, inline=True)
#         embed.add_field(name="Estado", value="Abierto", inline=True)
#         embed.set_footer(text=f"Creado por {ctx.author.name}")
        
#         await ctx.send(embed=embed)
#     except Exception as e:
#         await ctx.send(f"❌ Error creando el caso: {str(e)}")

@bot.command()
async def nuevo_caso(ctx, cliente: str, tipo: str, prioridad: str = "media", descripcion: str = None):
    """Crea un nuevo caso legal con prioridad
    Uso: !nuevo_caso "Cliente" "Tipo" [prioridad] "Descripción"
    Ejemplo: !nuevo_caso "Juan Pérez" "Divorcio" "alta" "Proceso de divorcio mutuo acuerdo"
    """
    try:
        # Si no se proporcionó descripción, pedirla
        if descripcion is None:
            await ctx.send("❌ Faltó la descripción. Usa: `!nuevo_caso \"Cliente\" \"Tipo\" [prioridad] \"Descripción\"`")
            return
        
        # Validar prioridad
        prioridades_validas = ["baja", "media", "alta", "urgente"]
        if prioridad.lower() not in prioridades_validas:
            await ctx.send("❌ Prioridad no válida. Usa: baja, media, alta, urgente")
            return
        
        conn = sqlite3.connect('bufete_legal.db')
        c = conn.cursor()
        fecha_creacion = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Establecer fecha de vencimiento según prioridad
        dias_vencimiento = {
            "baja": 60,
            "media": 30,
            "alta": 15,
            "urgente": 7
        }
        fecha_vencimiento = (datetime.datetime.now() + timedelta(days=dias_vencimiento[prioridad.lower()])).strftime("%Y-%m-%d")
        
        c.execute("INSERT INTO casos (cliente, tipo, descripcion, fecha_creacion, fecha_vencimiento, estado, usuario_id, prioridad) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (cliente, tipo, descripcion, fecha_creacion, fecha_vencimiento, "Abierto", ctx.author.id, prioridad.lower()))
        conn.commit()
        caso_id = c.lastrowid
        conn.close()
        
        embed = discord.Embed(
            title="✅ Caso Creado Exitosamente",
            description=f"Caso #{caso_id}: {cliente} - {tipo}",
            color=0x00ff00
        )
        embed.add_field(name="Descripción", value=descripcion, inline=False)
        embed.add_field(name="Prioridad", value=prioridad.upper(), inline=True)
        embed.add_field(name="Vencimiento", value=fecha_vencimiento, inline=True)
        embed.add_field(name="Estado", value="Abierto", inline=True)
        embed.set_footer(text=f"Creado por {ctx.author.name}")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error creando caso: {e}")
        await ctx.send("❌ Error creando el caso. Verifica la sintaxis: `!nuevo_caso \"Cliente\" \"Tipo\" [prioridad] \"Descripción\"`")

@bot.command()
async def mis_casos(ctx, estado: str = "todos"):
    """Muestra tus casos con filtro de estado"""
    try:
        conn = sqlite3.connect('bufete_legal.db')
        
        if estado.lower() == "todos":
            query = "SELECT id, cliente, tipo, descripcion, fecha_creacion, fecha_vencimiento, estado, prioridad FROM casos WHERE usuario_id = ?"
            params = (ctx.author.id,)
        else:
            query = "SELECT id, cliente, tipo, descripcion, fecha_creacion, fecha_vencimiento, estado, prioridad FROM casos WHERE usuario_id = ? AND estado = ?"
            params = (ctx.author.id, estado.capitalize())
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty:
            await ctx.send(f"📝 No tienes casos {estado if estado != 'todos' else ''}registrados.")
            return
            
        embed = discord.Embed(
            title=f"📋 Casos de {ctx.author.name}",
            description=f"Lista de casos ({estado})",
            color=0x0099ff
        )
        
        for _, caso in df.iterrows():
            # Emoji según prioridad
            emoji_prioridad = {
                "baja": "🔵",
                "media": "🟡",
                "alta": "🟠",
                "urgente": "🔴"
            }.get(caso['prioridad'], "⚪")
            
            # Emoji según estado
            emoji_estado = "🟢" if caso['estado'] == "Abierto" else "🔴"
            
            embed.add_field(
                name=f"{emoji_prioridad} {emoji_estado} Caso #{caso['id']}: {caso['cliente']}",
                value=f"**Tipo:** {caso['tipo']}\n**Vencimiento:** {caso['fecha_vencimiento']}\n**Prioridad:** {caso['prioridad'].upper()}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error recuperando casos: {str(e)}")

@bot.command()
async def asistente(ctx, *, mensaje):
    """Pregunta al asistente de IA especializado en derecho"""
    try:
        if not ai_assistant.is_legal_related(mensaje):
            embed = discord.Embed(
                title="🚫 Tema No Jurídico",
                description="Como abogado junior, solo puedo responder preguntas sobre derecho y asuntos jurídicos.",
                color=0xff0000
            )
            embed.add_field(
                name="Ejemplos de temas válidos",
                value="• Contratos y documentos legales\n• Procesos judiciales\n• Derechos y obligaciones\n• Leyes y regulaciones\n• Consultas legales generales",
                inline=False
            )
            embed.set_footer(text="Por favor, formula tu pregunta sobre temas legales")
            await ctx.send(embed=embed)
            return
        
        processing_msg = await ctx.send("⚖️ Abogado Junior procesando tu consulta...")
        
        respuesta = ai_assistant.get_response(mensaje)
        respuesta = limitar_respuesta_inteligente(respuesta, 2800)
        
        embed = discord.Embed(
            title="🧠 Asistente Jurídico IA",
            description=respuesta,
            color=0x0099ff
        )
        embed.add_field(name="Consulta", value=mensaje, inline=False)
        embed.set_footer(text="Respuesta generada por Abogado Junior IA | Revisar con socio senior para casos específicos")
        
        await processing_msg.delete()
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error con asistente IA: {e}")
        await ctx.send("❌ Error técnico procesando tu consulta. Intenta más tarde.")

@bot.command()
async def hola(ctx):
    """Saludo del bot como abogado junior"""
    embed = discord.Embed(
        title="👨‍⚖️ ¡Hola! Soy tu Abogado Junior Asistente",
        description="Estoy aquí para ayudarte con consultas jurídicas, análisis de documentos y gestión de casos.",
        color=0x0099ff
    )
    embed.add_field(
        name="📋 Puedo ayudarte con:",
        value="• Análisis de documentos legales\n• Consultas sobre legislación\n• Gestión de casos del bufete\n• Recordatorios de plazos\n• Estadísticas y métricas",
        inline=False
    )
    embed.add_field(
        name="⚖️ Áreas de expertise:",
        value="• Derecho Civil\n• Derecho Mercantil\n• Derecho Laboral\n• Derecho Penal\n• Derecho de Familia",
        inline=False
    )
    embed.set_footer(text="Usa !ayuda para ver todos los comandos disponibles")
    
    await ctx.send(embed=embed)

@bot.command()
async def ayuda(ctx):
    """Muestra todos los comandos disponibles"""
    embed = discord.Embed(
        title="🤖 Comandos Disponibles - Abogado Junior",
        description="**Prefix: `!`** o **mensajes directos** para algunos comandos",
        color=0xff9900
    )
    
    embed.add_field(name="`!hola`", value="Presentación del abogado junior", inline=False)
    embed.add_field(name="`!analizar_documento [url]`", value="Analiza un documento legal adjunto o desde URL", inline=False)
    embed.add_field(name="`!asistente [pregunta]` o `abogado [pregunta]`", value="Consulta al asistente jurídico IA", inline=False)
    embed.add_field(name="`!estadisticas [tipo]`", value="Genera estadísticas del bufete (general, casos, documentos)", inline=False)
    embed.add_field(name="`!nuevo_caso [cliente] [tipo] [prioridad] [descripción]`", value="Crea un nuevo caso legal", inline=False)
    embed.add_field(name="`!mis_casos [estado]`", value="Muestra tus casos (todos, abiertos, cerrados)", inline=False)
    embed.add_field(name="`!recordatorio [caso_id] [días] [mensaje]`", value="Programa un recordatorio para un caso", inline=False)
    
    embed.add_field(
        name="📋 Notas importantes", 
        value="• Como abogado junior, siempre recomiendo consultar con socios senior\n• Mantengo confidencialidad absoluta de los casos\n• Mi análisis es preliminar y debe ser revisado",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Comandos adicionales para gestión del bufete
@bot.command()
async def recordatorio(ctx, caso_id: int, dias: int, *, mensaje: str):
    """Programa un recordatorio para un caso específico"""
    try:
        conn = sqlite3.connect('bufete_legal.db')
        c = conn.cursor()
        
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
async def actualizar_caso(ctx, caso_id: int, estado: str, *, notas: str = ""):
    """Actualiza el estado de un caso"""
    try:
        estados_validos = ["abierto", "en_proceso", "en_revision", "cerrado", "archivado"]
        if estado.lower() not in estados_validos:
            await ctx.send(f"❌ Estado no válido. Usa: {', '.join(estados_validos)}")
            return
        
        conn = sqlite3.connect('bufete_legal.db')
        c = conn.cursor()
        
        # Verificar que el caso existe y pertenece al usuario
        c.execute("SELECT cliente FROM casos WHERE id = ? AND usuario_id = ?", (caso_id, ctx.author.id))
        caso = c.fetchone()
        if not caso:
            await ctx.send("❌ Caso no encontrado o no tienes permisos.")
            return
        
        c.execute("UPDATE casos SET estado = ? WHERE id = ?", (estado.capitalize(), caso_id))
        conn.commit()
        conn.close()
        
        await ctx.send(f"✅ Caso #{caso_id} ({caso[0]}) actualizado a: {estado.upper()}")
        if notas:
            await ctx.send(f"📝 Notas: {notas}")
            
    except Exception as e:
        await ctx.send(f"❌ Error actualizando caso: {str(e)}")

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if TOKEN:
        try:
            bot.run(TOKEN)
        except Exception as e:
            logger.error(f"Error iniciando bot: {e}")
    else:
        print("❌ No se encontró DISCORD_TOKEN en .env")