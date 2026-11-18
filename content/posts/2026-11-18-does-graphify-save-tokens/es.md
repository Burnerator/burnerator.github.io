---
title: ¿graphify ahorra tokens? 280 sesiones con Claude Code y Codex
date: 2026-11-18
summary: Una herramienta de grafos de conocimiento promete que los agentes de IA leerán menos y gastarán menos. Usamos las instrucciones y los hooks que escribe su instalador oficial, lanzamos 280 sesiones con Claude Code y Codex, y con Claude todas las variantes de graphify consumieron más tokens.
tags: experimento, graphify, claude-code, codex, tokens
mascot_says: Les di a los dos aprendices un mapa de la forja. Se leyeron el mapa… y luego recorrieron los pasillos igual.
---

**En corto:** dimos a Claude Code y a Codex [graphify](https://github.com/Graphify-Labs/graphify) con el texto de instrucciones exacto que escribe su propio instalador y, solo en Claude, los hooks de graphify y su modo estricto (que activó nuestro arnés). Codex conservó el fichero de hooks del instalador, que no hace nada. Cambiamos dos cosas a propósito: los hooks de Claude pasaban por un pequeño registrador, y en la segunda ejecución un `graphify` a secas pasaba por un envoltorio seguro (detalles abajo). Después los pusimos a explicar y a revisar código real. **En Claude Code, todas las variantes con graphify tuvieron una mediana de tokens más alta que sin él: entre un 12 % y un 63 % más por sesión** (entre un 6 % y un 55 % si solo comparamos con las sesiones sin graphify del mismo día). En Codex las medianas observadas apenas cambiaron: del −11 % al +9 % con el texto oficial, según la referencia. La cobertura de las respuestas se movió unos pocos puntos en la mayoría de los casos. Son los volúmenes que observamos con el diseño que describimos abajo, no una prueba del porqué.

## Qué promete graphify

graphify convierte un repositorio en un grafo de conocimiento (`graphify-out/graph.json` y un informe). Su instalador añade instrucciones para que el agente consulte primero el grafo (`graphify query "..."`) en vez de buscar con grep y leer ficheros. En Claude Code también puede añadir **hooks** que empujan al agente hacia el grafo cuando busca (Bash, Grep) o lee (Read, Glob). El **modo estricto** va más allá: el primer `Read` o `Grep` directo *elegible* se deniega una vez, a modo de aviso, si no ha habido una consulta reciente al grafo, y si se repite se permite. "Reciente" es una marca de tiempo compartida por todo el checkout y válida 30 minutos, y nuestro arnés reutilizó cada checkout de strict entre repeticiones, así que una consulta de una sesión anterior podía evitar la denegación en una posterior. El bloqueo se aplica como mucho una vez por sesión. En nuestras pruebas una sesión registró una denegación; ese agente leyó después el mismo fichero con `Read` en vez de repetir el `Grep`.

El titular de "un 80 % menos de tokens" del README de graphify se refiere a **[Graphify Cloud](https://github.com/Graphify-Labs/graphify#graphify-cloud)**, un producto alojado. Nosotros probamos el **paquete open source** (`graphifyy` 0.9.111). Su benchmark del README mide la calidad de recuperación ([BENCHMARKS.md](https://github.com/Graphify-Labs/graphify/blob/v8/BENCHMARKS.md)). Su documentación también tiene un comando [`graphify benchmark`](https://docs.graphify.com/open-source/features/token-benchmark) que *estima* el ahorro por consulta frente a leer el repositorio entero, y la propia documentación dice que esa cifra es "una guía de escala, no una cifra de facturación". Nosotros medimos otra cosa: lo que los agentes consumieron de verdad, de principio a fin. Así que este artículo responde a una pregunta más concreta: *¿la herramienta open source, configurada de la forma oficial, reduce el volumen de tokens de los agentes?*

## Primero, una corrección

Esta es nuestra segunda ejecución. En la primera, la variante "con grafo" usaba el texto de reglas **genérico** de graphify, no el texto exacto que escriben `graphify claude install` y `graphify codex install`. Era una objeción justa, así que lo repetimos:

- **textos oficiales:** los ficheros de instrucciones son ahora la salida exacta del instalador, byte a byte;
- **hooks y modo estricto:** añadidos para Claude Code;
- **una tarea de revisión de código:** graphify documenta un [flujo para pull requests](https://docs.graphify.com/open-source/features/pr-impact), así que añadimos la revisión de 4 pull requests reales.

La primera ejecución se conserva en los datos como `rules-generic`. En Claude, y en las comparaciones agregadas de la tarea A, sus cifras apuntan en la misma dirección que las nuevas. En Codex sobre anvil no: frente a la referencia de su propio día, las reglas genéricas gastaron un 25 % más de tokens y las oficiales un 11 % menos.

## Cómo lo medimos

- **Agentes:**
  - Claude Code (`claude -p`, alias de modelo `sonnet`);
  - Codex (`codex exec`, sandbox de solo lectura, modelo por defecto).
- **Código, fijado a commits exactos:**
  - nuestro propio [anvil](https://github.com/Burnerator/anvil) (9 ficheros Python, 1.100 líneas);
  - [httpx 0.28.1](https://github.com/encode/httpx/tree/0.28.1) (60 ficheros, 17.800 líneas).
- **Tarea A, entender:** 8 preguntas de arquitectura, por ejemplo *"Traza qué pasa al llamar a httpx.get()"*.
- **Tarea B, revisar:** "revisa los cambios entre este commit y HEAD" sobre 4 PRs reales ya fusionados en httpx:
  - [#3377](https://github.com/encode/httpx/pull/3377), carga diferida de `certifi` y `httpcore`;
  - [#2879](https://github.com/encode/httpx/pull/2879), el nuevo parámetro `proxy`;
  - [#3139](https://github.com/encode/httpx/pull/3139), descompresión zstd;
  - [#3389](https://github.com/encode/httpx/pull/3389), mover funciones auxiliares fuera de `_utils.py`.

  El grafo se construye sobre el commit base del PR, como dice la guía de PRs de graphify ("ejecuta `graphify update .` primero en la rama base").
- **Variantes** (todas sobre copias idénticas del código):

  | Variante | Qué recibe el agente |
  |---|---|
  | `base` | nada extra |
  | `rules-official` | grafo + el texto exacto de `CLAUDE.md` / `AGENTS.md` del instalador de graphify (Claude sin hooks; Codex conserva el fichero de hooks del instalador, que no hace nada) |
  | `hooks` (Claude) | lo anterior + los hooks PreToolUse y SessionStart del propio graphify |
  | `strict` (Claude) | lo anterior + `GRAPHIFY_HOOK_STRICT=1` |
  | `rules-generic` (primera ejecución) | grafo + el texto de reglas genérico de graphify |

- **Repeticiones:** 3 por pregunta y variante, salvo las sesiones sin graphify de la tarea A en la segunda ejecución: 1 por pregunta, sumadas a las 3 de la primera. Dentro de cada tanda, el orden de las variantes se alternó. En la segunda ejecución, las sesiones sin graphify se lanzaron en tandas aparte (ver los límites).
- **Métricas:** los tokens, las llamadas a herramientas y los comandos de graphify salen del propio registro de eventos de cada agente; los disparos de hooks, de los logs de nuestro wrapper; la calidad, de la rúbrica aplicada a la respuesta final:
  - tokens: entrada sin caché, entrada en caché, escrituras en caché y salida;
  - llamadas a herramientas;
  - cada comando de consulta de graphify (`query`, `path`, `explain`, `section`), si su comando de shell funcionó y cuánto texto devolvió;
  - cada vez que saltó un hook de graphify en Claude y qué decidió, según los registros de nuestro envoltorio de hooks.
- **Calidad:** una rúbrica de 5 a 8 puntos clave por pregunta, cada uno comprobado en el código. En las revisiones de PRs, la rúbrica sale mecánicamente del diff, no del grafo: hasta 3 ficheros cambiados, hasta 3 funciones o clases tocadas y hasta 3 ficheros más que mencionan el mayor número de esos nombres distintos. Comprueba que la respuesta los menciona, no que sea correcta.
- **Controles:** las instrucciones dirigían a los agentes a un envoltorio con lista blanca, sin claves de API y sin LLM. En la segunda ejecución un `graphify` a secas apuntaba a él a través del `PATH` de los agentes; en la primera, las instrucciones nombraban el envoltorio explícitamente y los agentes conservaban nuestro `PATH` normal. El binario real de graphify seguía accesible por su ruta completa, y los instaladores oficiales se ejecutaron en copias desechables con un directorio personal falso. No es un sandbox: los dos agentes funcionaron con nuestra instalación y configuración global de siempre, que no cambiamos entre variantes. El informe detalla qué se forzó y qué no.

**280 sesiones en total, todas completadas correctamente.**

## ¿Llamaron de verdad a graphify?

Lo llamaron, según el recuento a nivel de shell de abajo, y por eso el resultado tiene sentido. Ese recuento puede incluir una consulta que solo imprimió un diagnóstico (por ejemplo "No node matching") o una tubería cuyo último comando terminó bien.

| | Sesiones con un comando de graphify detectado que funcionó* | Salida de graphify (mediana de caracteres serializados por variante, sobre las sesiones con salida†) | Hooks disparados por sesión (registrados por nuestro envoltorio) |
|---|---|---|---|
| Claude, tarea A | 100 % en todas las variantes con graphify | 6.700–14.500 caracteres | 4–6 (hooks / strict) |
| Claude, tarea B | 11/12 (oficial, hooks), 8/12 (strict) | 6.600–6.700 caracteres | 4–5 (hooks / strict) |
| Codex, tarea A | 100 % | 6.600–10.000 caracteres | — |
| Codex, tarea B | 100 % | 6.700 caracteres (5 de 12 sesiones**) | — |
| Cualquier agente, sin graphify | 0 sesiones | — | — |

*\* Detectado de forma heurística comparando el texto del comando de shell; cuenta como que funcionó si el comando terminó con código 0 (Codex) o su resultado no fue un error (Claude). La salida es el resultado tal y como quedó registrado, así que un `| head` la recorta. La salida solo cuenta los comandos que ejecutaron únicamente graphify (se aceptan tuberías a `head`/`tail`, separadores `echo`, `which graphify` y la comprobación `if test -f graphify-out/graph.json`, así que sus pocos caracteres extra se incluyen); los que lo mezclaban con otros comandos cuentan como llamadas, pero no como salida, y por eso solo 5 revisiones de Codex tienen cifra de salida.\*\* El informe tiene la tabla por variante.*

*† La mediana solo cuenta las sesiones con salida no vacía de comandos que funcionaron y ejecutaron solo graphify. Si las demás sesiones contaran como cero, algunas celdas bajarían: por ejemplo, Claude en modo estricto en la tarea B tiene 6.678 caracteres sobre 8 sesiones de ese tipo, y 3.985 sobre las 12.*

## Resultados

**Tarea B, revisar pull requests reales.** Seguimos el paso del grafo base de la guía de revisión de PRs de graphify y usamos nuestro propio prompt de revisión; el comando `graphify prs` de graphify no formó parte del experimento. Medianas de 12 sesiones por celda:

| Agente | Sin graphify | Reglas oficiales | Hooks | Estricto | Calidad (cobertura media) |
|---|---|---|---|---|---|
| Claude Code | 168.940 | 230.981 (**+37 %**) | 260.136 (**+54 %**) | 236.453 (**+40 %**) | 79 % → 83–84 % |
| Codex | 109.708 | 106.391 (**−3 %**) | — | — | 68 % → 71 % |

*Tokens totales por sesión (entrada sin caché + entrada en caché + escrituras en caché + salida, sumando todos los modelos que usó la sesión). En Claude, el coste equivalente de API pasó de 0,11 $ a 0,14–0,15 $ por revisión. Las dos filas comparan tandas del mismo día; la tarea B no tiene una comprobación con otra referencia (la de herramientas de más abajo sí la cubre).*

**Tarea A, explicar código**, mediana de tokens totales por sesión. La referencia sin graphify junta las dos ejecuciones: 12 sesiones en anvil y 20 en httpx.

| Agente | Código | Sin graphify | Reglas genéricas | Reglas oficiales | Hooks | Estricto |
|---|---|---|---|---|---|---|
| Claude Code | anvil | 186.602 | +19 % | +33 % | +23 % | +22 % |
| Claude Code | httpx | 204.540 | +36 % | +12 % | +58 % | +63 % |
| Codex | anvil | 67.634 | +14 % | +9 % | — | — |
| Codex | httpx | 64.732 | +33 % | +8 % | — | — |

**Comprobación de sensibilidad.** Si cada variante se compara solo con las sesiones sin graphify de su mismo día (en la segunda ejecución, solo 1 repetición por pregunta), las cifras de Claude en anvil se reducen (+16 % oficial, +8 % hooks, +7 % estricto), Claude en httpx sigue por encima (+6 % oficial, +49 % hooks, +55 % estricto) y Codex en anvil con el texto oficial pasa a −11 %. Diferencias tan pequeñas no quedan resueltas con estos datos. La tarea B tiene una sola referencia, así que no hay una comprobación con otra referencia para ella.

**Una segunda comprobación: cuántas herramientas tenía Claude.** Nuestra instalación le ofrecía a Claude 21 o 46 herramientas extra (todo lo que queda fuera de las herramientas propias del experimento: plugins, conectores y otras funciones del CLI), y no por igual en todas las variantes. En el subconjunto de sesiones con 21 herramientas extra, todos los aumentos de Claude mantienen el signo; los de las revisiones crecen (del +74 % al +96 %) y los de la tarea A cambian entre −3 y +18 puntos porcentuales. Que el número coincida no prueba que las herramientas sean las mismas, así que esto reduce la duda sobre la dirección, pero el desequilibrio sigue siendo un posible factor de confusión.

**Pregunta a pregunta** (la mediana de las repeticiones de cada pregunta, comparada solo con esa misma pregunta sin graphify), la mediana con graphify fue más baja **como mucho en 1 de cada 3–5 preguntas** para Claude, en cualquier variante. Con la media geométrica de las proporciones por pregunta, Claude gastó **entre 1,16 y 1,74 veces** los tokens de la versión sin graphify. Codex, **entre 1,04 y 1,21 veces**.

## Qué significa, en cristiano

- **El mapa no sustituyó al paseo, por lo que muestran las trazas.** En las variantes con graphify, las consultas al grafo y las búsquedas y lecturas directas de ficheros aparecen juntas, sin un orden fijo (una revisión ejecutó `git diff --stat` antes de su primera consulta). La salida de graphify, miles de caracteres, formaba parte del contexto. En las revisiones de PRs, la mediana de salida de herramientas de Claude (caracteres serializados por sesión) pasó de 12.400 a 14.400–15.900. No medimos qué ficheros leyó cada variante ni cuánta lectura sustituyó el grafo, así que esto no explica los totales más altos; solo describe lo que contienen las trazas.
- **Las variantes que más empujan tuvieron las medianas más altas en Claude.** Los hooks y el modo estricto, que empujan al agente hacia el grafo, tuvieron las medianas de tokens observadas más altas de Claude en httpx y en las revisiones. Con las salvedades de tandas y herramientas de más abajo, es lo que observamos, no una medida de lo que causan los hooks.
- **Codex apenas se movió.** Con el texto oficial ejecutó un comando de graphify en todas las sesiones y sus medianas observadas acabaron más o menos donde empezaron.
- **Calidad: un pequeño punto a favor en la mayoría de los casos, no en todos.** En las revisiones, las variantes con graphify cubrieron algún punto esperado más de media (cobertura media del 79 % al 83–84 % en Claude, del 68 % al 71 % en Codex). Pero Codex con el texto genérico en anvil bajó del 93 % al 84 %. Con 9–15 sesiones por celda con graphify y sin prueba de significación, son diferencias pequeñas, no hallazgos.

## Límites, sin trampa

- **Muestras pequeñas.** 3 repeticiones por pregunta y variante (1 en las sesiones sin graphify de la tarea A de la segunda ejecución). Entre un día y otro, la misma variante sin graphify varió entre un +1 % y un +33 % (3 repeticiones por pregunta el primer día, 1 el segundo, con una configuración de arranque de Claude ligeramente distinta: la segunda ejecución también preaprobaba `graphify` a secas y `git diff/log/show`). Eso demuestra que hay oscilaciones de ese tamaño, pero no permite fijar un umbral de ruido preciso. Las diferencias de ese orden (Codex y algunas celdas de Claude) no son concluyentes. Los aumentos de Claude en la tarea B, y con hooks y strict en httpx, son mayores y se mantienen también frente a la referencia del mismo día.
- **Las sesiones sin graphify se ejecutaron en tandas aparte.** En las tandas principales de la segunda ejecución (sin contar el piloto), la primera marca de tiempo registrada en cada traza de Claude cae entre las 08:58 y las 09:21 UTC en las sesiones con graphify de la tarea B y entre las 09:22 y las 09:37 en las sin graphify, y la repetición extra de la tarea A fue la última. Una repetición de un PR salió de un piloto lanzado antes de las tandas principales (reiniciado al menos una vez); allí, las primeras marcas de tiempo registradas son las 07:31–07:32 UTC en sus sesiones de Claude con graphify y las 07:42 en la sin graphify, así que allí se mantuvo el mismo orden: primero con graphify y después la referencia. En la tarea B no se descarta una influencia de la hora. La tarea A usa también las sesiones sin graphify de la primera ejecución. Esa ejecución fueron dos invocaciones sobre el mismo directorio: primero `--reps 1` y después `--reps 3`, que se saltó la primera repetición ya hecha y ejecutó las otras dos. Las dos variantes se alternaron dentro de cada pregunta y repetición.
- **Nuestra instalación habitual.** Los dos agentes funcionaron con nuestra configuración global, plugins y un hook de arranque de siempre. Añaden contexto, permiten a Claude ejecutar otros comandos de shell, y el número de herramientas que le ofrecían a Claude cambió durante las pruebas, de forma desigual entre variantes (ver la comprobación de herramientas). Con otra instalación, las cifras pueden cambiar.
- **Dos repositorios Python.** La documentación de graphify dice que el ahorro crece con el tamaño del código; no hemos probado uno muy grande.
- **Graphify Cloud** es otro producto, y aquí no se dice nada sobre él.
- **La rúbrica de calidad comprueba que se mencionan los puntos clave**, no que toda la explicación sea correcta.
- **Las cifras de Claude y de Codex no se comparan entre sí** (modelos, tokenizadores y cachés distintos). Hay que comparar variantes dentro del mismo agente.
- **Solo volumen de tokens y coste equivalente de API.** Las sesiones usaron suscripciones; no se facturó nada.

## Compruébalo, rómpelo, cuéntanoslo

Todo está en un único repositorio:

- el arnés de pruebas, las preguntas y sus rúbricas, y los commits del código analizado (fijados y clonados por el arnés);
- los ficheros de instrucciones tal y como los escribieron los instaladores de graphify, y la configuración de hooks tal y como la instrumentamos;
- **la traza de cada sesión**, y el registro de hooks de cada sesión `hooks` / `strict`, sin nuestros datos locales;
- el informe generado, con todas las tablas, la comprobación de sensibilidad y el método.

Repositorio: [github.com/Burnerator/graphify-tokens](https://github.com/Burnerator/graphify-tokens). Si lo ejecutas y te salen otras cifras, abre una issue. Para eso está.
