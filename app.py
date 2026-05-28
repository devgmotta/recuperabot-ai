import gradio as gr
import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY não configurada no .env.")

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={"temperature": 0.7, "max_output_tokens": 1024},
    system_instruction="""Você é a Clara, atendente virtual da ConectaNet Telecom, especialista em retenção e renegociação de dívidas.

PERSONALIDADE:
- Empática, acolhedora e profissional.
- Nunca faça o cliente se sentir constrangido.
- Fale de forma natural, como uma pessoa real em um chat.

FLUXO DE ATENDIMENTO:
1. Cumprimente o cliente de forma calorosa.
2. Pergunte o nome completo ou o número de identificação (ID) para localizar o cadastro.
3. Quando o sistema injetar os dados do cliente, use-os para conduzir a negociação.
4. Apresente o valor total da dívida e proponha o pagamento integral primeiro.
5. Se o cliente resistir ou disser que não pode pagar tudo, ofereça parcelamento (2x a 6x sem juros).
6. SOMENTE se o cliente insistir que não consegue pagar, ofereça o desconto máximo autorizado (que virá nos dados injetados).
7. NUNCA ofereça desconto maior do que o autorizado.
8. Se um acordo for fechado, confirme os termos e encerre o atendimento de forma positiva.

IMPORTANTE: Você NÃO tem acesso direto ao banco de dados. Quando o cliente informar nome ou ID, o sistema vai buscar e injetar os dados automaticamente na conversa. Se os dados não forem injetados, diga que não localizou e peça para o cliente confirmar a informação."""
)

# --- Dados ---

dados_clientes = None

def carregar_dados():
    global dados_clientes
    try:
        dados_clientes = pd.read_csv("data/inadimplentes.csv")
        dados_clientes["id_cliente"] = dados_clientes["id_cliente"].astype(str)
        print(f"Base carregada: {len(dados_clientes)} clientes.")
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        dados_clientes = pd.DataFrame()

def buscar_cliente(texto):
    if dados_clientes is None or dados_clientes.empty:
        return None
    texto = texto.strip()
    resultado = dados_clientes[dados_clientes["id_cliente"] == texto]
    if not resultado.empty:
        return resultado.iloc[0]
    if len(texto) > 3:
        resultado = dados_clientes[dados_clientes["nome_completo"].str.contains(texto, case=False, na=False)]
        if not resultado.empty:
            return resultado.iloc[0]
    return None

carregar_dados()

# --- Helpers ---

def extrair_texto(content):
    """Extrai texto puro do conteúdo, independente do formato do Gradio."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes = []
        for p in content:
            if isinstance(p, dict):
                partes.append(p.get("text", ""))
            elif isinstance(p, str):
                partes.append(p)
            elif hasattr(p, "text"):
                partes.append(p.text)
        return " ".join(partes)
    if hasattr(content, "text"):
        return content.text
    return str(content)

# --- Lógica do Chat ---

def responder(mensagem, historico):
    historico_gemini = []

    for msg in historico:
        if isinstance(msg, dict):
            role = msg.get("role", "")
            content = extrair_texto(msg.get("content", ""))
        elif hasattr(msg, "role") and hasattr(msg, "content"):
            role = msg.role
            content = extrair_texto(msg.content)
        else:
            continue

        if role == "user" and content:
            historico_gemini.append({"role": "user", "parts": [content]})
        elif role == "assistant" and content:
            historico_gemini.append({"role": "model", "parts": [content]})

    chat = model.start_chat(history=historico_gemini)

    cliente = buscar_cliente(mensagem)
    prompt = mensagem

    if cliente is not None:
        prompt += (
            f"\n\n[DADOS DO SISTEMA - NÃO EXIBA ISSO AO CLIENTE]\n"
            f"Cliente localizado: {cliente['nome_completo']}\n"
            f"Plano: {cliente['plano_atual']}\n"
            f"Dívida: R$ {cliente['valor_divida']:.2f}\n"
            f"Atraso: {cliente['dias_atraso']} dias\n"
            f"Desconto máximo autorizado: {cliente['desconto_maximo_permitido']}%"
        )

    try:
        resposta = chat.send_message(prompt)
        return resposta.text
    except Exception as e:
        return f"Desculpe, estou com dificuldades técnicas. Tente novamente.\n\n_(Erro: {e})_"

# --- Interface ---

CSS = """
.gradio-container { max-width: 800px !important; margin: auto !important; }
footer { display: none !important; }
"""

demo = gr.ChatInterface(
    fn=responder,
    title="ConectaNet Telecom",
    description="Central de Atendimento — Retenção e Renegociação",
    examples=[
        "Olá, gostaria de renegociar minha dívida",
        "Não estou conseguindo pagar o valor total",
    ],
)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, css=CSS)
