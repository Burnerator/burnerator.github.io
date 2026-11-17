---
title: El mismo modelo, dos mundos: la nube de NVIDIA frente a un portátil
date: 2026-11-17
summary: Ejecutamos los mismos modelos abiertos en la API de NVIDIA y en local con Ollama en un MacBook. Velocidad, latencia, aciertos, y por qué un modelo en la nube nunca llegó a responder.
tags: benchmark, nvidia, ollama, ia-local
mascot_says: Cronometré cada martillazo. El portátil ganó un asalto, la nube ganó otro, y un modelo ni siquiera se presentó en la forja.
---

**Resumen rápido:** con un modelo de 20B, un portátil reciente respondió bien a todas las preguntas a unos 63 tokens por segundo. El endpoint gratuito de NVIDIA para ese mismo modelo no respondió en 3 minutos. Con otros modelos, la nube de NVIDIA fue rapidísima: hasta **139 tokens por segundo** y respuestas en **menos de medio segundo**.

## Qué queríamos saber

¿Puedes ejecutar «el mismo modelo» en tu portátil en lugar de llamar a una API en la nube? ¿Y qué pierdes por el camino? Comparamos la API de NVIDIA (`integrate.api.nvidia.com`) con [Ollama](https://ollama.com) ejecutándose en local.

## El montaje

- **Portátil:** Apple M5 Pro con 24 GB de memoria unificada y Ollama 0.35.
- **Nube:** catálogo de la API de NVIDIA, nivel gratuito.
- **Preguntas:** 6 preguntas (una cuenta, una capital, una diferencia de horas, escribir una función pequeña, un resumen en una frase y una explicación de unas 300 palabras), cada una repetida 3 veces.
- **Comparación justa:** los dos lados usan el mismo protocolo de streaming compatible con OpenAI. Los proveedores se van turnando en quién empieza, hay una llamada de calentamiento que no se mide y se registra cada reintento.
- **Qué modelos:** solo los que existen en los dos lados *y* caben en 24 GB. Quedaron `gpt-oss-20b` y dos Nemotron 3.5. Gemma 3 aparece en el catálogo de NVIDIA, pero nuestra cuenta recibió `404 Function not found`.

## Resultados

| Modelo | Dónde | OK | Primer token visible | Velocidad (tok/s) | Aciertos |
|---|---|---|---|---|---|
| gpt-oss-20b | Portátil (Ollama) | 18/18 | 1,43 s | 62,8 | 100 % |
| gpt-oss-20b | Nube de NVIDIA | 0/18 | no respondió en 180 s | — | — |
| nemotron-3.5-bolt-e4b | Nube de NVIDIA | 18/18 | 0,19 s | 72,5 | 100 % |
| nemotron-3.5-lightning-30b | Nube de NVIDIA | 18/18 | 2,22 s | 139,1 | 78 % |

*Medianas. «Velocidad» es la velocidad de generación en la pregunta larga. «Aciertos» cuenta las respuestas exactas a las preguntas que tienen una única respuesta correcta.*

## Qué significa (en palabras sencillas)

- **Lo local puede ganar a la nube.** En el nivel gratuito, el endpoint de `gpt-oss-20b` de NVIDIA estaba tan saturado que no llegó a responder, ni siquiera después del calentamiento. El mismo modelo en el portátil acertó todo en algo más de un segundo y medio.
- **La nube es rápida cuando está disponible.** Nemotron Bolt respondió en menos de medio segundo. Lightning generó texto unas **2 veces más rápido** que el portátil con `gpt-oss-20b`.
- **El 78 % no es que sea «tonto», es que es «parlanchín».** Lightning *piensa en voz alta* antes de responder, y 9 de sus 18 respuestas llegaron al límite de 512 tokens antes de dar la respuesta. Con un límite mayor, la mayoría se arreglará. Lo repetiremos.

## Límites, con honestidad

- Esto compara **despliegues, no modelos idénticos**. La nube y el portátil usan cuantizaciones y sistemas de servicio distintos.
- Todos los tiempos se miden **desde nuestro lado**, así que incluyen la latencia de red.
- **Aún no tenemos cifras de Nemotron en local**: nuestra versión de Ollama era demasiado antigua para esos modelos. Será la siguiente prueba.
- El nivel gratuito cambia de una hora a otra. Tómalo como una foto del momento, no como un veredicto.

## Pruébalo tú

El banco de pruebas es open source y está en [Burnerator/anvil](https://github.com/Burnerator/anvil):

    python -m nvidia_ai bench --pairs gpt-oss-20b --runs 3

Lo próximo en el yunque: el mismo benchmark con Nemotron en local y un límite de tokens más alto para los modelos parlanchines.
