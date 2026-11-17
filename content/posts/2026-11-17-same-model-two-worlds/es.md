---
title: El mismo modelo, dos mundos: la nube de NVIDIA frente a un portátil
date: 2026-11-17
summary: Ejecutamos los mismos modelos abiertos en la API de NVIDIA y en local con Ollama en un MacBook. Velocidad, latencia, aciertos, y por qué un modelo en la nube agotó el tiempo de espera en nuestra prueba.
tags: benchmark, nvidia, ollama, ia-local
mascot_says: Cronometré cada martillazo. El portátil ganó un asalto, la nube ganó otro, y un modelo ni siquiera se presentó en la forja.
---

**Resumen rápido:** con un modelo de 20B, un portátil reciente acertó las 9 respuestas puntuadas (las preguntas con una única respuesta correcta). Mostró sus primeras palabras en 1,4 s y generó unos 63 tokens por segundo. El endpoint gratuito de NVIDIA para ese mismo modelo no respondió en 3 minutos durante nuestra prueba. Con otros modelos, la nube de NVIDIA fue rapidísima: hasta **139 tokens por segundo** y respuestas en **menos de medio segundo**.

## Qué queríamos saber

¿Puedes ejecutar «el mismo modelo» en tu portátil en lugar de llamar a una API en la nube? ¿Y qué pierdes por el camino? Comparamos la API de NVIDIA (`integrate.api.nvidia.com`) con [Ollama](https://ollama.com) ejecutándose en local.

## El montaje

- **Portátil:** Apple M5 Pro con 24 GB de memoria unificada y Ollama 0.35.
- **Nube:** catálogo de la API de NVIDIA, nivel gratuito.
- **Preguntas:** 6 preguntas, cada una repetida 3 veces: `cuánto es 17*23`, *la capital de Australia*, *los minutos entre las 14:35 y las 17:10*, *escribe `is_prime(n)`*, *un resumen en una frase* y *una explicación de unas 300 palabras sobre las tablas hash*. Solo las tres primeras tienen una única respuesta correcta y son las que se puntúan. Los textos exactos están en el archivo de datos de abajo.
- **Comparación justa:** los dos lados usan el mismo protocolo de streaming compatible con OpenAI. Los proveedores se van turnando en quién empieza, hay una llamada de calentamiento que no se mide y se registra cada reintento.
- **Qué modelos:** solo los que existen en los dos lados *y* caben en 24 GB. Quedaron `gpt-oss-20b` y dos Nemotron 3.5. Gemma 3 aparece en el catálogo de NVIDIA, pero nuestra cuenta recibió `404 Function not found`.

## Resultados

| Modelo | Dónde | OK | Primer token visible | Velocidad (tok/s) | Aciertos |
|---|---|---|---|---|---|
| gpt-oss-20b | Portátil (Ollama) | 18/18 | 1,43 s | 62,8 | 100 % |
| gpt-oss-20b | Nube de NVIDIA | 0/18 | tiempo agotado (180 s) | — | — |
| nemotron-3.5-bolt-e4b | Nube de NVIDIA | 18/18 | 0,19 s | 72,5 | 100 % |
| nemotron-3.5-lightning-30b | Nube de NVIDIA | 18/18 | 2,22 s | 139,1 | 78 % |

*Medianas sobre las peticiones correctas. «Primer token visible» es cuando aparecen las primeras palabras de la respuesta (los modelos que razonan piensan antes); las respuestas completas de gpt-oss-20b en el portátil tardaron unos 2,4 s. «Velocidad» es la velocidad de generación en la pregunta larga. «Aciertos» cuenta las respuestas exactas a las 3 preguntas puntuadas (9 intentos); los fallos cuentan como errores.*

## Qué significa (en palabras sencillas)

- **Lo local puede ganar a la nube.** En nuestra prueba, el endpoint gratuito de `gpt-oss-20b` de NVIDIA agotó el tiempo de espera todas las veces, incluido el calentamiento; una prueba suelta anterior tardó 63 s en responder. No sabemos por qué: una carga alta es una hipótesis razonable, pero no la hemos medido. El mismo modelo en el portátil acertó todas las respuestas puntuadas, con las primeras palabras en ~1,4 s.
- **La nube es rápida cuando está disponible.** Nemotron Bolt respondió en menos de medio segundo. Lightning generó texto unas **2 veces más rápido** que el portátil con `gpt-oss-20b`.
- **El 78 % no es que sea «tonto», es que es «parlanchín».** Lightning *piensa en voz alta* antes de responder, y 9 de sus 18 respuestas llegaron al límite de 512 tokens antes de dar la respuesta. Con un límite mayor, la mayoría se arreglará. Lo repetiremos.

## Límites, con honestidad

- Esto compara **despliegues, no modelos idénticos**. La nube y el portátil usan cuantizaciones y sistemas de servicio distintos.
- Todos los tiempos se miden **desde nuestro lado**, así que incluyen la latencia de red.
- **Aún no tenemos cifras de Nemotron en local**: nuestra versión de Ollama era demasiado antigua para esos modelos. Será la siguiente prueba.
- El nivel gratuito cambia de una hora a otra. Tómalo como una foto del momento, no como un veredicto.

## Datos y código

- **Números en bruto** (saneados), preguntas exactas y configuración: [results.json](../results.json)
- **Banco de pruebas** en el commit exacto que usamos: [bench.py @ 6cd8286](https://github.com/Burnerator/anvil/blob/6cd8286a0dcb85fec7e604683e7da74d49f800c6/src/nvidia_ai/bench.py)

## Pruébalo tú

El banco de pruebas es open source y está en [Burnerator/anvil](https://github.com/Burnerator/anvil):

    python -m nvidia_ai bench --pairs gpt-oss-20b --runs 3

Lo próximo en el yunque: el mismo benchmark con Nemotron en local y un límite de tokens más alto para los modelos parlanchines.
