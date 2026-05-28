import pandas as pd
from faker import Faker
import random
import os

def gerar_dados_inadimplentes(num_linhas=50, output_path="data/inadimplentes.csv"):
    fake = Faker('pt_BR')
    dados = []
    
    planos = ["Internet 500 Mega", "Internet 1 Giga", "Combo TV + Internet", "Plano Controle 50GB", "Plano Pós 100GB"]
    
    for _ in range(num_linhas):
        cliente = {
            "id_cliente": fake.unique.random_int(min=1000, max=9999),
            "nome_completo": fake.name(),
            "plano_atual": random.choice(planos),
            "valor_divida": round(random.uniform(100.0, 3000.0), 2),
            "dias_atraso": random.randint(15, 365),
            "desconto_maximo_permitido": random.randint(10, 40)
        }
        dados.append(cliente)
        
    df = pd.DataFrame(dados)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[{num_linhas}] registros gerados em '{output_path}'.")

if __name__ == "__main__":
    gerar_dados_inadimplentes()
