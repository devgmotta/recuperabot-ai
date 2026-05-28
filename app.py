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

generation_config = {
  "temperature": 0.7,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 1024,
}

system_instruction = """Você é o RecuperaBot, um Especialista em Retenção e Renegociação de Dívidas.
Sua persona é empática, amigável e respeitosa.

REGRAS:
1. Peça NOME COMPLETO ou ID DO CLIENTE para consultar no sistema se não souber.
2. Com os dados injetados, use-os para negociar.
3. Se o cliente não tiver como pagar, ofereça parcelamento ou o DESCONTO MÁXIMO PERMITIDO (injetado).
4. NUNCA ofereça desconto maior do que o permitido.
5. Seja conciso e direto.
6. Tente valor total ou parcelamento sem desconto primeiro.
"""

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
  system_instruction=system_instruction
)

dados_clientes = None

def carregar_dados():
    global dados_clientes
    try:
        dados_clientes = pd.read_csv("data/inadimplentes.csv")
        dados_clientes['id_cliente'] = dados_clientes['id_cliente'].astype(str)
    except Exception:
        dados_clientes = pd.DataFrame()

def buscar_cliente(termo_busca):
    if dados_clientes is None or dados_clientes.empty:
        return None
    
    cliente = dados_clientes[dados_clientes['id_cliente'] == str(termo_busca).strip()]
    if not cliente.empty:
        return cliente.iloc[0]
    
    if len(termo_busca) > 3:
        cliente = dados_clientes[dados_clientes['nome_completo'].str.contains(termo_busca, case=False, na=False)]
        if not cliente.empty:
            return cliente.iloc[0]
    
    return None

def chatbot_responder(mensagem, historico):
    historico_gemini = []
    
    for conversa in historico:
        user_msg, bot_msg = conversa
        historico_gemini.append({"role": "user", "parts": [user_msg]})
        historico_gemini.append({"role": "model", "parts": [bot_msg]})
        
    chat = model.start_chat(history=historico_gemini)
    
    cliente_encontrado = buscar_cliente(mensagem)
    mensagem_para_api = mensagem
    
    if cliente_encontrado is not None:
        contexto_injetado = (
            f"\n\n--- INFORMAÇÃO INTERNA DE SISTEMA ---\n"
            f"Nome Completo: {cliente_encontrado['nome_completo']}\n"
            f"Plano Atual: {cliente_encontrado['plano_atual']}\n"
            f"Valor da Dívida Atualizada: R$ {cliente_encontrado['valor_divida']:.2f}\n"
            f"Dias de Atraso: {cliente_encontrado['dias_atraso']} dias\n"
            f"Desconto Máximo Autorizado: {cliente_encontrado['desconto_maximo_permitido']}%\n"
            f"----------------------------------------"
        )
        mensagem_para_api += contexto_injetado
    
    try:
        response = chat.send_message(mensagem_para_api)
        return response.text
    except Exception as e:
        return f"Erro de conexão: {str(e)}"

carregar_dados()

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 RecuperaBot")
    gr.Markdown("Assistente de Renegociação de Dívidas.")
    
    gr.ChatInterface(
        fn=chatbot_responder,
        examples=["Olá, gostaria de negociar minha dívida.", "Meu ID é 1234", "Não tenho como pagar o valor total."],
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
