# Tu carpeta de trabajo — TP07

> **Guía fácil de todo el sistema LSA (recomendado leer primero):**  
> [`../COMO_FUNCIONA.md`](../COMO_FUNCIONA.md)

| Archivo | Para qué |
|---|---|
| `mi_tp07.py` | Acá escribís tu agente. **Es lo que entregás.** |
| `casos_prueba.json` | Los 25 casos de la cátedra. Dados hechos. |
| `evaluar.py` | Dado hecho. Calcula tu accuracy y la tabla de fallos. |
| `ejecutor.py` | Dado hecho. Convierte a velocidad y tiempo, y manda al robot. |
| `robot.py` | No lo toques. |
| `vocabulario_dataset.py` | Las 8 palabras del dataset LSA + alias. |
| `dataset.csv` | **Extensión**: 5 ejemplos para que veas el formato. Completalo vos. |
| `entrenar.py` | Dado hecho. Entrena con tu dataset y te da las métricas. |

## Cómo lo ejecutás

**Con robot** (para ver al G1 hacerte caso):

1. Abrí `INICIAR_SIMULADOR` y elegí el robot.
2. Doble clic en `EJECUTAR_MI_CODIGO`, o `python3 mi_desarrollo/mi_tp07.py`.

**Sin robot** (para trabajar el clasificador tranquilo):

```
python3 mi_desarrollo/mi_tp07.py --sin-robot
```

Corre los 25 casos y te da la accuracy, sin abrir nada.

## Modo interactivo

Con el robot conectado, después de la evaluación podés escribirle órdenes:

```
  > avanzá 2 metros
  > girá 90 grados a la derecha
  > salta desde la mesa
```

Es la mejor forma de encontrar los casos que tu agente no cubre.

## Modo voz: speech-to-text

El modo voz escucha una frase en español, la convierte a texto y la manda por
el mismo pipeline. Si la frase contiene palabras del diccionario de señas, el
G1 ejecuta esas señas en el simulador.

Instalá las librerías una sola vez desde la carpeta `mi_desarrollo`:

```powershell
py -3 -m pip install -r requirements-voz.txt
```

Con el G1 ya abierto, ejecutá:

```powershell
py -3 mi_desarrollo/mi_tp07.py --voz
```

También podés usar `EJECUTAR_MI_CODIGO.bat --voz`. El programa calibra el ruido
ambiente al inicio; después decí, por ejemplo, `hola gracias`. Para terminar,
decí `salir` o presioná `Ctrl+C`.

El reconocimiento usa el servicio de Google y requiere internet. El modo de
texto escrito sigue disponible sin instalar estas librerías.

## Dataset chico: español argentino → señas

Hay un vocabulario fijo de **8 palabras** en `vocabulario_dataset.py`:

`hola`, `gracias`, `chau`, `si`, `no`, `ayuda`, `agua`, `amigo`

Con el simulador abierto:

```bash
# Escribís las palabras y el G1 las firma
python3 mi_desarrollo/mi_tp07.py --dataset

# Primero recorre las 8 senas y despues queda interactivo
python3 mi_desarrollo/mi_tp07.py --dataset --demo

# Mejor: las escucha por microfono (es-AR) y las traduce a senas
python3 mi_desarrollo/mi_tp07.py --dataset --voz
```

Si decís o escribís algo fuera del vocabulario, te avisa y lista las palabras
válidas. Alias como `chau`/`adios` o `si`/`dale` también entran.

## Capa robot real (Inspire) — `tp07_lsa/`

Para la prueba con el G1 físico (mano Inspire de 5 dedos) usá el paquete
nuevo **sin borrar** este flujo de simulación:

```bash
cd ../tp07_lsa
python3 main.py --modo simulacion --demo
python3 main.py --modo real --interfaz eth0 --demo
```

Detalle de instalación DDS/SDK y supuestos a confirmar: `../tp07_lsa/README.md`.

También: `python3 mi_tp07.py --modo real --interfaz eth0 --palabra hola`.

## Extensión: entrenar un modelo (nivel 2)

Con reglas alcanza para aprobar. Si querés ir más lejos:

**1. Armá tu dataset.** `dataset.csv` trae 5 ejemplos para que veas el formato:

```
texto,intencion
dale para adelante,MOVER
frená ahí,DETENERSE
```

Completalo hasta unos 80. Las intenciones válidas son `MOVER`, `GIRAR`,
`DETENERSE`, `SALUDO`, `CONSULTAR_ESTADO` y `DESCONOCIDO`.

**2. Entrená y mirá tus métricas:**

```
python3 mi_desarrollo/entrenar.py
```

Te avisa si al dataset le falta algo: pocas filas, una intención sin ejemplos,
textos repetidos.

**3. Usalo en tu agente.** En `ClasificadorIntencion.__init__` hay dos líneas
comentadas:

```python
from entrenar import entrenar_desde_csv
self.modelo = entrenar_desde_csv()
```

Y en `clasificar()`:

```python
if self.modelo is not None:
    return self.modelo.predict([texto])[0]
```

Dejá las reglas de respaldo: si el dataset no está, el agente sigue andando.

**El extractor, el validador y el ejecutor no se enteran.** Cambiás una sola
clase.

**4. Compará.** ¿El modelo le gana a tus reglas? ¿En qué casos pierde? Esa
comparación es parte del informe.

> Necesitás `scikit-learn`: `pip install --user scikit-learn`.
> Sin él, el TP se hace igual con reglas.

## Qué entregás si hiciste la extensión

Una **carpeta** con los dos archivos:

```
tp07_apellido/
├── mi_tp07.py
└── dataset.csv
```

No hace falta que entregues el modelo entrenado: se entrena solo al arrancar,
en milisegundos. Y así el profesor puede **leer** tu dataset.
