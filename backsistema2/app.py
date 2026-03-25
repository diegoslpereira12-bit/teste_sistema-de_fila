import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)

app.secret_key = '63f4945d921d599f27ae4fdf5bada3f1'

class BancoFila:
    def __init__(self, nome_banco):
        self.nome_banco = nome_banco
        self.criar_tabela()

    def conectar(self):
        conexao = sqlite3.connect(self.nome_banco)
        conexao.row_factory = sqlite3.Row  
        return conexao

    def criar_tabela(self):
        sql = """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'paciente',
            status TEXT DEFAULT 'Fora da fila'
        )
        """
        with self.conectar() as conexao:
            conexao.execute(sql)

            conexao.execute("INSERT OR IGNORE INTO usuarios (cpf, nome, senha, tipo) VALUES ('12345678910', 'Admin Atendente', '12345', 'atendente')")
            conexao.commit()

    def cadastrar(self, cpf, nome, senha):
        sql = "INSERT INTO usuarios (cpf, nome, senha) VALUES (?, ?, ?)"
        try:
            with self.conectar() as conexao:
                conexao.execute(sql, (cpf, nome, senha))
                conexao.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login(self, cpf, senha):
        sql = "SELECT * FROM usuarios WHERE cpf = ? AND senha = ?"
        with self.conectar() as conexao:
            return conexao.execute(sql, (cpf, senha)).fetchone()

    def listar_fila(self):
        sql = "SELECT * FROM usuarios WHERE status != 'Fora da fila' AND tipo = 'paciente' ORDER BY id ASC"
        with self.conectar() as conexao:
            return conexao.execute(sql).fetchall()

    def alterar_status(self, id, novo_status):
        sql = "UPDATE usuarios SET status = ? WHERE id = ?"
        with self.conectar() as conexao:
            conexao.execute(sql, (novo_status, id))
            conexao.commit()

    def buscar_usuario_por_id(self, id):
        sql = "SELECT * FROM usuarios WHERE id = ?"
        with self.conectar() as conexao:
            return conexao.execute(sql, (id,)).fetchone()

    def contar_fila(self):
        sql = "SELECT COUNT(*) as total FROM usuarios WHERE status != 'Fora da fila' AND tipo = 'paciente'"
        with self.conectar() as conexao:
            resultado = conexao.execute(sql).fetchone()
            return resultado['total']

banco = BancoFila("sistema_fila.db")

@app.route('/')
def index():
    usuario = session.get('usuario')
    e_admin = False
    
    if usuario and usuario['cpf'] == '12345678910':
        e_admin = True
    
    quantidade_fila = banco.contar_fila()
    
    return render_template('mainpage.html', usuario_logado=usuario, e_admin=e_admin, fila_count=quantidade_fila)

@app.route('/atendente')
def painel_atendente():
    usuario = session.get('usuario')
    
    if not usuario or usuario['cpf'] != '12345678910':
        flash("Acesso Negado! Apenas atendentes podem acessar.", "erro")
        return redirect(url_for('index'))

    fila = banco.listar_fila()
    
    return render_template('atendente.html', fila=fila)

@app.route('/cadastrar', methods=['GET'])
def pagina_cadastro():
    return render_template('cadastro.html')

@app.route('/salvar_cadastro', methods=['POST'])
def salvar_cadastro():
    nome = request.form.get('nome', '').strip()
    cpf = request.form.get('cpf', '').strip()
    email = request.form.get('email', '').strip()
    senha = request.form.get('senha', '').strip()

    if not nome or not cpf or not email or not senha:
        flash("Todos os campos são obrigatórios!", "erro")
        return redirect(url_for('pagina_cadastro'))

    if len(cpf) != 11 or not cpf.isdigit():
        flash("CPF deve ter exatamente 11 dígitos.", "erro")
        return redirect(url_for('pagina_cadastro'))

    if len(senha) < 4:
        flash("Senha deve ter no mínimo 4 caracteres.", "erro")
        return redirect(url_for('pagina_cadastro'))

    if banco.cadastrar(cpf, nome, senha):

        usuario = banco.login(cpf, senha)
        if usuario:

            session['usuario'] = {
                'id': usuario['id'],
                'nome': usuario['nome'],
                'cpf': usuario['cpf'],
                'tipo': usuario['tipo'],
                'status': usuario['status']
            }
            flash(f"Cadastro realizado com sucesso! Bem-vindo, {nome}!", "sucesso")
            return redirect(url_for('index'))
    else:
        flash("Erro: Esse CPF já está cadastrado.", "erro")
        return redirect(url_for('pagina_cadastro'))

@app.route('/login')
def pagina_login():
    return render_template('login.html')

@app.route('/login_prosseguir', methods=['POST'])
def login_prosseguir():
    cpf_digitado = request.form.get('cpf', '').strip()
    senha_digitada = request.form.get('senha', '').strip()

    if not cpf_digitado or not senha_digitada:
        flash("CPF e Senha são obrigatórios!", "erro")
        return redirect(url_for('pagina_login'))

    usuario = banco.login(cpf_digitado, senha_digitada)

    if usuario:
        session['usuario'] = {
            'id': usuario['id'],
            'nome': usuario['nome'],
            'cpf': usuario['cpf'],
            'tipo': usuario['tipo'],
            'status': usuario['status']
        }
        flash(f"Bem-vindo, {usuario['nome']}!", "sucesso")
        return redirect(url_for('index'))
    else:
        flash("CPF ou Senha incorretos!", "erro")
        return redirect(url_for('pagina_login'))

@app.route('/entrar-na-fila', methods=['POST'])
def entrar_fila():
    usuario = session.get('usuario')
    
    if not usuario:
        flash("Você precisa estar logado para entrar na fila.", "erro")
        return redirect(url_for('pagina_login'))

    if usuario['status'] != 'Fora da fila':
        flash(f"Você já está na fila! Status: {usuario['status']}", "alerta")
        return redirect(url_for('index'))

    banco.alterar_status(usuario['id'], 'Aguardando atendimento')

    session['usuario']['status'] = 'Aguardando atendimento'
    session.modified = True
    
    flash("Você entrou na fila com sucesso!", "sucesso")
    return redirect(url_for('index'))

@app.route('/mudar_status/<int:paciente_id>/<novo_status>')
def mudar_status(paciente_id, novo_status):
    usuario = session.get('usuario')

    if not usuario or usuario['cpf'] != '000':
        flash("Apenas atendentes podem fazer isso!", "erro")
        return redirect(url_for('index'))

    status_validos = ['Aguardando atendimento', 'Em atendimento', 'Atendido', 'Fora da fila']
    if novo_status not in status_validos:
        flash("Status inválido!", "erro")
        return redirect(url_for('painel_atendente'))

    banco.alterar_status(paciente_id, novo_status)
    
    flash(f"Status atualizado com sucesso!", "sucesso")
    return redirect(url_for('painel_atendente'))

@app.route('/sair-da-fila', methods=['POST'])
def sair_fila():
    usuario = session.get('usuario')
    
    if not usuario:
        return redirect(url_for('pagina_login'))

    banco.alterar_status(usuario['id'], 'Fora da fila')

    session['usuario']['status'] = 'Fora da fila'
    session.modified = True
    
    flash("Você saiu da fila.", "sucesso")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash("Você foi desconectado!", "sucesso")
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)