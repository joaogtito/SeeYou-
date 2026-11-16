"""Pipeline offline de dados reais do SeeYou (Analog Finder).

Os scripts numerados em ``Server/pipeline/`` são finos: cada um lê o
``config.yaml`` e chama as funções deste pacote, que são puras e testáveis.
"""

__version__ = "0.1.0"
PIPELINE_VERSION = __version__


def main() -> None:
    print("SeeYou pipeline. Rode os scripts em Server/pipeline/ (ver README).")
