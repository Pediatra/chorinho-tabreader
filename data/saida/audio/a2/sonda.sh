#!/bin/sh
sh /var/home/gabriel/Projects/chorinho-dataset/data/saida/audio/a2/base.sh 'python -c "
import numpy, sys
print(\"numpy\", numpy.__version__, \"py\", sys.version.split()[0])
from tab.audio_extrair import garantir
f,m=garantir(\"/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4\")
print(f, m[\"cache\"], m[\"t_amostra0\"], m[\"taxa\"])
"'
