
from pathlib import Path
from tempfile import TemporaryDirectory
from pypdf import PdfReader, PdfWriter
import shutil
import sys


# ==========================================================
# 1. SOLICITAR A PASTA AO USUÁRIO
# ==========================================================

def solicitar_pasta():
    print("=" * 60)
    print("ORGANIZADOR E SEPARADOR DE PDFs")
    print("=" * 60)

    caminho = input(
        "\nDigite ou cole o caminho da pasta que deseja processar:\n> "
    ).strip()

    # Remove aspas caso o usuário cole um caminho entre aspas.
    caminho = caminho.strip('"').strip("'")

    if not caminho:
        print("\nERRO: nenhum caminho foi informado.")
        sys.exit(1)

    pasta = Path(caminho).expanduser()

    if not pasta.exists():
        print(f"\nERRO: a pasta não existe:\n{pasta}")
        sys.exit(1)

    if not pasta.is_dir():
        print(f"\nERRO: o caminho informado não é uma pasta:\n{pasta}")
        sys.exit(1)

    return pasta.resolve()


# ==========================================================
# 2. LOCALIZAR OS PDFs
# ==========================================================

def localizar_pdfs(pasta):
    return sorted(
        [
            arquivo
            for arquivo in pasta.iterdir()
            if arquivo.is_file()
            and arquivo.suffix.lower() == ".pdf"
        ],
        key=lambda arquivo: arquivo.name.lower()
    )


# ==========================================================
# 3. EXTRAIR AS PÁGINAS DE UM PDF
# ==========================================================

def extrair_paginas(pdf_origem, pasta_destino, validar=False):
    leitor = PdfReader(str(pdf_origem), strict=False)

    if leitor.is_encrypted:
        raise ValueError(
            f"O arquivo '{pdf_origem.name}' está protegido por senha."
        )

    total_paginas = len(leitor.pages)

    if total_paginas == 0:
        raise ValueError(
            f"O arquivo '{pdf_origem.name}' não possui páginas."
        )

    pasta_destino.mkdir(parents=True, exist_ok=True)

    for numero, pagina in enumerate(leitor.pages, start=1):
        nome_saida = (
            f"{pdf_origem.stem}_pagina_{numero:03d}.pdf"
        )

        arquivo_saida = pasta_destino / nome_saida

        escritor = PdfWriter()
        escritor.add_page(pagina)

        with arquivo_saida.open("wb") as arquivo:
            escritor.write(arquivo)

        # Confere se o PDF individual foi criado corretamente.
        if validar:
            verificador = PdfReader(
                str(arquivo_saida),
                strict=False
            )

            if (
                verificador.is_encrypted
                or len(verificador.pages) != 1
            ):
                raise ValueError(
                    f"Falha na validação de '{nome_saida}'."
                )

    return total_paginas


# ==========================================================
# 4. TESTAR TODOS OS PDFs SEM ALTERAR OS ORIGINAIS
# ==========================================================

def testar_pdfs(pdfs):
    resultados = []
    erros = []

    print("\n" + "=" * 60)
    print("FASE 1 — TESTE DOS ARQUIVOS")
    print("=" * 60)

    with TemporaryDirectory(prefix="teste_pdfs_") as temporario:
        pasta_teste = Path(temporario)

        for indice, pdf in enumerate(pdfs, start=1):
            try:
                destino_teste = pasta_teste / f"pdf_{indice}"

                paginas = extrair_paginas(
                    pdf_origem=pdf,
                    pasta_destino=destino_teste,
                    validar=True
                )

                resultados.append((pdf, paginas))

                print(
                    f"[OK] {pdf.name} — "
                    f"{paginas} página(s) testada(s)."
                )

            except Exception as erro:
                erros.append((pdf.name, str(erro)))
                print(f"[ERRO] {pdf.name}: {erro}")

    if erros:
        print("\nTESTE REPROVADO.")
        print("Nenhum PDF será movido.")

        for nome, mensagem in erros:
            print(f"- {nome}: {mensagem}")

        return None

    print("\nTESTE APROVADO.")
    print("Todos os arquivos passaram pelo teste.")

    return resultados


# ==========================================================
# 5. EXECUÇÃO PRINCIPAL
# ==========================================================

def main():

    # O usuário escolhe a pasta antes de qualquer operação.
    pasta_principal = solicitar_pasta()

    print(f"\nPasta selecionada:\n{pasta_principal}")

    # Localiza os PDFs diretamente nessa pasta.
    pdfs = localizar_pdfs(pasta_principal)

    if not pdfs:
        print("\nNenhum arquivo PDF foi encontrado nessa pasta.")
        return

    print(f"\nForam encontrados {len(pdfs)} arquivo(s):")

    for pdf in pdfs:
        print(f"  - {pdf.name}")

    # Verifica se duas extensões diferentes ou nomes equivalentes
    # resultariam na mesma pasta de destino.
    nomes_destino = [pdf.stem.casefold() for pdf in pdfs]

    if len(nomes_destino) != len(set(nomes_destino)):
        print(
            "\nOPERAÇÃO CANCELADA: existem PDFs com nomes "
            "que resultariam na mesma pasta."
        )
        print("Renomeie os arquivos conflitantes e tente novamente.")
        return

    # Evita utilizar pastas que já existem.
    conflitos = [
        pasta_principal / pdf.stem
        for pdf in pdfs
        if (pasta_principal / pdf.stem).exists()
    ]

    if conflitos:
        print("\nOPERAÇÃO CANCELADA.")
        print("Já existem pastas com nomes que seriam utilizados:")

        for pasta in conflitos:
            print(f"  - {pasta.name}")

        print("\nVerifique essas pastas antes de tentar novamente.")
        return

    # Testa todos os PDFs antes de mover qualquer original.
    resultados = testar_pdfs(pdfs)

    if resultados is None:
        return

    total_paginas = sum(paginas for _, paginas in resultados)

    print("\n" + "=" * 60)
    print("RESUMO DO TESTE")
    print("=" * 60)
    print(f"PDFs encontrados: {len(pdfs)}")
    print(f"Total de páginas a separar: {total_paginas}")
    print("Os PDFs originais não foram movidos.")

    # Solicita autorização explícita.
    resposta = input(
        "\nPara iniciar a organização, digite SIM:\n> "
    ).strip().upper()

    if resposta != "SIM":
        print("\nOperação cancelada. Nenhum PDF foi movido.")
        return

    pastas_criadas = []
    arquivos_movidos = []

    try:
        # Cria as pastas e extrai todas as páginas.
        # Os PDFs originais continuam na pasta selecionada.
        print("\n" + "=" * 60)
        print("FASE 2 — EXTRAÇÃO DAS PÁGINAS")
        print("=" * 60)

        for pdf, paginas_esperadas in resultados:
            pasta_destino = pasta_principal / pdf.stem

            pasta_destino.mkdir()
            pastas_criadas.append(pasta_destino)

            paginas_criadas = extrair_paginas(
                pdf_origem=pdf,
                pasta_destino=pasta_destino,
                validar=True
            )

            if paginas_criadas != paginas_esperadas:
                raise RuntimeError(
                    f"A quantidade de páginas de '{pdf.name}' "
                    "divergiu do teste inicial."
                )

            print(
                f"[OK] {pdf.name}: "
                f"{paginas_criadas} página(s) extraída(s)."
            )

        # Só move os originais depois de gerar e validar
        # todas as páginas de todos os arquivos.
        print("\n" + "=" * 60)
        print("FASE 3 — MOVIMENTAÇÃO DOS ORIGINAIS")
        print("=" * 60)

        for pdf, _ in resultados:
            pasta_destino = pasta_principal / pdf.stem
            destino_original = pasta_destino / pdf.name

            shutil.move(
                str(pdf),
                str(destino_original)
            )

            arquivos_movidos.append((pdf, destino_original))

            print(f"[OK] Original movido: {pdf.name}")

        print("\n" + "=" * 60)
        print("PROCESSO CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print(f"PDFs organizados: {len(pdfs)}")
        print(f"Páginas extraídas: {total_paginas}")
        print(f"Pasta processada:\n{pasta_principal}")

    except Exception as erro:
        print(f"\nERRO DURANTE A EXECUÇÃO: {erro}")
        print("Tentando reverter a operação...")

        reversao_ok = True

        # Tenta devolver os originais à pasta inicial.
        for origem, destino in reversed(arquivos_movidos):
            try:
                if destino.exists() and not origem.exists():
                    shutil.move(str(destino), str(origem))

            except Exception as erro_reversao:
                reversao_ok = False
                print(
                    f"[ERRO] Não foi possível restaurar "
                    f"{origem.name}: {erro_reversao}"
                )

        # Apaga as pastas criadas pelo programa somente
        # se os originais estiverem restaurados.
        originais_restaurados = all(
            pdf.exists() for pdf in pdfs
        )

        if reversao_ok and originais_restaurados:
            for pasta in reversed(pastas_criadas):
                try:
                    if pasta.exists():
                        shutil.rmtree(pasta)
                except Exception as erro_limpeza:
                    print(
                        f"[AVISO] Não foi possível remover "
                        f"{pasta.name}: {erro_limpeza}"
                    )

            print(
                "Os PDFs originais foram restaurados "
                "à pasta selecionada."
            )
        else:
            print(
                "ATENÇÃO: a reversão pode estar incompleta. "
                "Confira os arquivos antes de executar novamente."
            )

        sys.exit(1)


if __name__ == "__main__":
    main()
