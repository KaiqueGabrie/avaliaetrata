
const fs = require('node:fs');
const path = require('node:path');

const caminhos = {
  main: 'backend/main.py',
  models: 'backend/models/__init__.py',
  requirements: 'backend/requirements.txt',
  prontuario: 'src/app/paciente/[id].tsx',
};

const originais = {};
const atualizados = {};

function adicionarLinha(codigo, linha) {
  if (codigo.includes(linha)) return codigo;

  return codigo.trimEnd() + '\n' + linha + '\n';
}

function substituir(codigo, antigo, novo) {
  if (codigo.includes(novo)) return codigo;

  if (codigo.split(antigo).length !== 2) {
    throw new Error(
      'Trecho ausente ou duplicado: ' +
      antigo.slice(0, 100)
    );
  }

  return codigo.replace(antigo, () => novo);
}

try {
  const novosArquivos = [
    'backend/models/consentimento.py',
    'backend/routers/consentimento.py',
    'src/app/paciente/consentimento.tsx',
  ];

  for (const arquivo of novosArquivos) {
    if (!fs.existsSync(path.join(__dirname, arquivo))) {
      throw new Error(
        'Crie primeiro o arquivo: ' + arquivo
      );
    }
  }

  for (const [nome, arquivo] of Object.entries(caminhos)) {
    originais[nome] = fs.readFileSync(
      path.join(__dirname, arquivo),
      'utf8'
    );

    atualizados[nome] = originais[nome]
      .replace(/\r\n/g, '\n');
  }

  atualizados.models = adicionarLinha(
    atualizados.models,
    'from .consentimento import TermoConsentimento'
  );

  atualizados.requirements = adicionarLinha(
    atualizados.requirements,
    'reportlab>=4,<5'
  );

  atualizados.requirements = adicionarLinha(
    atualizados.requirements,
    'pypdf>=5,<7'
  );

  atualizados.main = substituir(
    atualizados.main,
    'from routers.pacientes import router as pacientes_router',
    'from routers.pacientes import router as pacientes_router\n' +
    'from routers.consentimento import router as consentimento_router'
  );

  atualizados.main = substituir(
    atualizados.main,
    'app.include_router(pacientes_router)',
    'app.include_router(pacientes_router)\n' +
    'app.include_router(consentimento_router)'
  );

  const referencia =
    '            <View style={styles.evolucaoPaciente}>';

  const botao = `            <TouchableOpacity
              accessibilityRole="button"
              accessibilityLabel="Consultar termo de consentimento"
              style={styles.botaoAnamnese}
              onPress={() => router.push({
                pathname: '/paciente/consentimento',
                params: {
                  pacienteId: String(paciente.id_paciente),
                },
              })}
            >
              <View style={styles.iconeAnamnese}>
                <IconeInterface
                  nome="escudo"
                  tamanho={25}
                />
              </View>

              <View style={styles.textosAnamnese}>
                <Text style={styles.tituloAnamnese}>
                  Termo de consentimento
                </Text>

                <Text style={styles.descricaoAnamnese}>
                  Gere e consulte os documentos assinados.
                </Text>
              </View>

              <IconeInterface
                nome="seta"
                tamanho={20}
                cor="#809bae"
              />
            </TouchableOpacity>

`;

  if (!atualizados.prontuario.includes(
    "pathname: '/paciente/consentimento'"
  )) {
    if (!atualizados.prontuario.includes(
      'styles.botaoAnamnese'
    )) {
      throw new Error(
        'O acesso à anamnese precisa estar instalado.'
      );
    }

    atualizados.prontuario = substituir(
      atualizados.prontuario,
      referencia,
      botao + referencia
    );
  }

  for (const [nome, arquivo] of Object.entries(caminhos)) {
    if (atualizados[nome] !== originais[nome]) {
      fs.writeFileSync(
        path.join(__dirname, arquivo),
        atualizados[nome],
        'utf8'
      );

      console.log('Atualizado:', arquivo);
    }
  }

  console.log(
    'Integração do consentimento concluída.'
  );

} catch (erro) {
  console.error('Erro:', erro.message);
  process.exitCode = 1;
}
