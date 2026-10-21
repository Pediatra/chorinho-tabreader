import importlib.metadata as md

for nome in ["onnxruntime", "onnxruntime-gpu", "rtmlib", "torch", "numpy", "opencv-python", "opencv-python-headless", "opencv-contrib-python"]:
    try:
        print(nome, md.version(nome))
    except md.PackageNotFoundError:
        print(nome, "NAO INSTALADO")
import onnxruntime as o

print("ort", o.__version__, "providers:", o.get_available_providers())
