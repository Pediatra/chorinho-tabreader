"""Transcricao de tablatura de violao a partir de video, com tempo de execucao.

Os modulos ficam em subpastas por trilha (decisao 9001). Os nomes antigos, de quando
``tab/`` era plano (``tab.maos_braco_ciclo``, ``tab.caminhos``...), continuam valendo
por um localizador de modulos: ``import tab.<antigo>``, ``from tab.<antigo> import f``,
``from tab import <antigo>`` e ``python -m tab.<antigo>`` devolvem ou rodam o modulo
novo. O nome antigo e o novo sao o MESMO objeto, entao um ``monkeypatch`` num vale no
outro. A tabela fica em ``tab/_apelidos.py``.

Este arquivo usa so a stdlib e a sintaxe do Python 3.10: a imagem do transcritor (3.10)
e o ``celular`` (Python do host) importam ``tab``. Um teste do gate trava isso.
"""

import importlib
import importlib.abc
import importlib.util
import sys

from tab._apelidos import APELIDOS


class _LocalizadorDeApelidos(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Resolve um nome antigo de modulo para o modulo novo, sem duplicar o modulo."""

    def find_spec(self, nome, caminho=None, alvo=None):
        """Spec do nome antigo, apontando para o arquivo do novo.

        Args:
            nome: nome pontuado pedido (``tab.<antigo>``).
            caminho: ignorado.
            alvo: ignorado.

        Returns:
            A spec, ou None quando o nome nao e um apelido.
        """
        if nome not in APELIDOS:
            return None
        novo = importlib.util.find_spec(APELIDOS[nome])
        if novo is None:
            return None
        return importlib.util.spec_from_loader(nome, self, origin=novo.origin)

    def create_module(self, spec):
        """Devolve o proprio modulo novo (importado uma vez so).

        Args:
            spec: a spec do nome antigo.

        Returns:
            O modulo novo.
        """
        return importlib.import_module(APELIDOS[spec.name])

    def exec_module(self, modulo):
        """Nada a executar: o modulo novo ja rodou no import.

        Args:
            modulo: o modulo novo.
        """

    def get_code(self, nome):
        """Codigo do modulo novo, para ``python -m tab.<antigo>``.

        Args:
            nome: o nome antigo.

        Returns:
            O codigo compilado do arquivo novo.
        """
        alvo = APELIDOS[nome]
        return importlib.util.find_spec(alvo).loader.get_code(alvo)


if not any(isinstance(f, _LocalizadorDeApelidos) for f in sys.meta_path):
    sys.meta_path.insert(0, _LocalizadorDeApelidos())
