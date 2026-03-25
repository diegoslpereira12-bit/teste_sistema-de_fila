from flask import Flask, render_template, request, redirect, url_for, session, flash # Adicione o flash aqui

app = Flask(__name__)
# A chave secreta é necessária para usar 'session' (protege os dados do usuário)
app.secret_key = 'chave_secreta_do_seu_grupo'

# --- BANCO DE DADOS SIMULADO (Substituir pelo SQLite depois) ---
usuarios_db = []
fila_atendimento = [] # Lista global para armazenar os pacientes
# --- ROTAS ---

# 1. Página Inicial (Main Page)
@app.route('/')
def index():
    usuario = session.get('usuario')
    
    # 1. Mantém sua lógica de Admin
    e_admin = False
    if usuario and usuario['cpf'] == '00000000000':
        e_admin = True
    
    # 2. Adiciona a contagem real da lista
    # Supondo que sua lista se chama 'fila_atendimento'
    total_na_fila = len(fila_atendimento)
    
    # 3. Envia TUDO para o HTML em um único return
    return render_template('mainpage.html', 
                           usuario_logado=usuario, 
                           e_admin=e_admin, 
                           quantidade=total_na_fila)

@app.route('/meu-status')
def ver_status():
    usuario = session.get('usuario')
    if not usuario:
        return redirect(url_for('pagina_login'))
    return render_template('status_fila.html', fila=fila_atendimento, usuario_logado=usuario)

@app.route('/atendente')
def painel_atendente():
    usuario = session.get('usuario')
    
    # Bloqueio de segurança
    if not usuario or usuario['cpf'] != '00000000000':
        return "Acesso Negado! Apenas atendentes podem ver esta página."

    return render_template('atendente.html', fila=fila_atendimento)

@app.route('/mudar_status/<int:posicao>/<novo_status>')
def mudar_status(posicao, novo_status):
    # Se o status for "Finalizado", podemos remover da lista ou apenas marcar
    if 0 <= posicao < len(fila_atendimento):
        if novo_status == "Atendimento finalizado":
            fila_atendimento.pop(posicao) # Remove da fila ao finalizar
        else:
            fila_atendimento[posicao]['status'] = novo_status
            
    return redirect(url_for('painel_atendente'))

# 2. Página de Cadastro (Exibir formulário)
@app.route('/cadastrar', methods=['GET'])
def pagina_cadastro():
    return render_template('cadastro.html')

# 3. Lógica de Cadastro (Receber os dados do card)
@app.route('/salvar_cadastro', methods=['POST'])
def salvar_cadastro():
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    email = request.form.get('email')
    senha = request.form.get('senha')

    # Validação
    if len(cpf) != 11:
        flash("Erro: O CPF deve conter exatamente 11 dígitos!", "danger") # "danger" é a categoria (cor)
        return redirect(url_for('pagina_cadastro')) # Volta para o formulário
    # Criando um dicionário do usuário (Simulando o objeto da POO)
    novo_usuario = {"nome": nome, "cpf": cpf, "email": email, "senha": senha}
    usuarios_db.append(novo_usuario)

    # Após cadastrar, já podemos logar o usuário automaticamente
    session['usuario'] = novo_usuario
    return redirect(url_for('index'))
# Rota para apenas MOSTRAR a página de login
@app.route('/login')
def pagina_login():
    return render_template('login.html')

@app.route('/login_prosseguir', methods=['POST'])
def login_prosseguir():
    cpf_digitado = request.form.get('cpf')
    senha_digitada = request.form.get('senha')

    # Percorre a "lista de usuários" para validar
    for usuario in usuarios_db:
        if usuario['cpf'] == cpf_digitado and usuario['senha'] == senha_digitada:
            # Se achou, salva na sessão e manda para a Main Page
            session['usuario'] = usuario
            return redirect(url_for('index'))

    # Se não achar nada, dá um erro
    return "CPF ou Senha incorretos! <a href='/login'>Tentar novamente</a>"

# 4. Rota para Entrar na Fila
@app.route('/entrar-na-fila', methods=['POST'])
def entrar_fila():
    if 'usuario' in session:
        # Verificamos se o usuário já não está na fila para não repetir
        ja_na_fila = any(p['cpf'] == session['usuario']['cpf'] for p in fila_atendimento)
        
        if not ja_na_fila:
            paciente = {
                "nome": session['usuario']['nome'],
                "cpf": session['usuario']['cpf'],
                "status": "Em análise" # Novo status inicial
            }
            fila_atendimento.append(paciente)
            
        return redirect(url_for('index'))
    return redirect(url_for('pagina_cadastro'))

@app.route('/finalizar/<int:posicao>')
def finalizar(posicao):
    fila_atendimento.pop(posicao) # Remove a pessoa da lista
    return redirect(url_for('painel_atendente'))

# 5. Rota para Sair (Logout)
@app.route('/logout')
def logout():
    session.pop('usuario', None) # Limpa a sessão
    return redirect(url_for('index'))

if __name__ == '__main__':
    # debug=True faz o servidor reiniciar sozinho quando você salva o código
    app.run(debug=True)