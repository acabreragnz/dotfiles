---
name: run-prep
description: Genera plan de preparacion para carreras y entrenamientos intensos de running. Incluye timing de comidas, hidratacion y descanso. Usar cuando el usuario pregunta por "la proxima carrera", "hoy", "mañana", o menciona prepararse para correr.
allowed-tools: Read, Glob
---

# Run Prep

Genera un plan detallado de preparacion para el evento de running indicado.

## Contexto del calendario

Fecha de hoy: !`date +%d-%m-%Y`

Calendario 2026:
!`cat "/home/tcabrera/personal/obsidian/second-brain/Projects/Running/Calendario de Carreras 2026.md"`

Calendario 2027:
!`cat "/home/tcabrera/personal/obsidian/second-brain/Projects/Running/Calendario de Carreras 2027.md"`

## Argumento recibido

$ARGUMENTS

## Instrucciones

### Paso 1: Identificar el evento

Segun el argumento:
- "la proxima carrera" / "la proxima" → buscar la primera carrera con estado `segura` o `pagada` cuya fecha sea posterior a hoy
- "hoy" → buscar carrera hoy; si no hay, detectar si es martes, jueves (clase grupal 19:00) o domingo (fondo largo)
- "mañana" → idem pero para el dia siguiente
- fecha especifica → buscar esa fecha exacta en el calendario

Si no hay carrera ese dia, verificar si es dia de entrenamiento intenso:
- Martes o jueves → clase grupal 19:00
- Domingo → fondo largo (hora variable, preguntar si no se sabe)

Al identificar la carrera, tomar nota de:
- **Hora de largada** (H)
- **Distancia** (5k, 21k, etc.)
- **Columna Notas** → si dice "Pacer de Flor", activar modo pacer

### Paso 2: Determinar tipo de plan

**CARRERA** → generar plan "Dia anterior" + "Dia de carrera"
**ENTRENAMIENTO INTENSO** → generar plan "Dia del entrenamiento"

---

## Plan para CARRERA

Usar la hora de largada (H) y la distancia para calcular todos los horarios.

### Casos especiales segun hora de largada

**Carrera mañanera (H antes de las 10:00):**
- No aplica almuerzo previo ni desayuno completo
- Despertar H - 1.5h
- Desayuno muy liviano (banana + te, o tostada ligera) 1h antes de H, o en ayunas si la distancia es 5k y el cuerpo lo tolera
- Hidratacion: 300ml al despertar
- Cena del dia anterior es mas importante: pastas mas abundantes que lo habitual

**Carrera normal (H entre 10:00 y 14:59):**
- Solo desayuno, sin almuerzo previo
- Despertar H - 3h (5k) o H - 3.5h (21k)
- Desayuno fijo 2.5h antes de H

**Carrera tarde (H a las 15:00 o mas):**
- Aplica almuerzo + desayuno
- Despertar H - 4h (5k) o H - 4.5h (21k)

### Ajustes por distancia

**5k:** hidratacion estandar, entrada en calor 15-20min
**21k o mas:** dia anterior minimo 2.5L de agua (no 2L), almuerzo del dia de carrera OBLIGATORIO aunque H sea temprana, entrada en calor 25-30min

### Modo Pacer

Si la columna Notas dice "Pacer de Flor":
- Flor corre a ritmo 6:00-7:00/km, lo que para el usuario es menos que un regenerativo — esfuerzo minimo
- NO dar recomendaciones de rendimiento, hidratacion extra, ni ajustes nutricionales especiales
- El plan de comidas es el habitual de un dia normal, sin restricciones
- Aclarar en el plan: "Vas como pacer de Flor — ritmo ~6-7 min/km, equivale a un paseo. Come y viví normal, no es un dia de carrera exigente."
- Simplificar el timeline: no hace falta precision de horarios al minuto, solo los basicos (desayuno, salida de casa, llegada)

### Dia anterior

- **Hidratacion:** minimo 2L (2.5L si es 21k o mas)
- **Almuerzo:** comida normal, sin experimentar. Evitar legumbres, comida muy grasa o picante
- **Merienda:** liviana, algo conocido (fruta, tostadas)
- **Cena (FIJA):** pastas con salsa simple (tomate, fileto). Hora sugerida: 3h antes de dormir. Si es carrera mañanera, porcion mas generosa de lo habitual
- **Descanso:** sugerir hora de dormir concreta segun hora de despertar del dia de carrera
- **Preparar:** ropa, zapatillas, numero/chip, agua, lo que haya que llevar

### Dia de carrera

Calcular todos los horarios a partir de H segun el caso (mañanera / normal / tarde).

- **Despertar:** segun caso arriba
- **Desayuno (FIJO salvo mañanera):** tostadas con mermelada + te. Cantidad moderada
- **Hidratacion manana:** 500ml entre desayuno y 1h antes de H (300ml si mañanera)
- **Almuerzo (segun caso):** arroz + atun + huevo duro. Comer 3.5h - 4h antes de H
- **Ultima ingesta solida:** cortar 2.5h - 3h antes de H
- **1h antes de H:** 200-300ml de agua, nada solido
- **Entrada en calor:** segun distancia, antes de H
- **Salida de casa:** calcular tiempo de viaje + llegar al lugar 45min antes de H

### Clima

Consultar el pronostico para el dia y lugar de la carrera usando el skill `weather` con ubicacion Ciudad de la Costa, Uruguay (o la ciudad de la carrera si es diferente).
Ajustar el plan segun temperatura:
- Menos de 15°C → hidratacion estandar, avisar que puede hacer frio al largar
- 15-25°C → condiciones normales
- Mas de 25°C → aumentar hidratacion pre-carrera en 200ml, mencionar riesgo de calor

### Post-carrera

Agregar al final del timeline una seccion de recuperacion:

- **Dentro de los 30-45min post-carrera:** comer algo con proteina + carbohidrato (banana + yogur, huevo + arroz, barra de proteina). No esperar a llegar a casa
- **Hidratacion:** 500ml en la primera hora post-carrera
- **Si hay entrenamiento al dia siguiente:** aclarar que debe ser recuperacion activa (trote suave o descanso), no sesion intensa

Incluir timeline visual completo con todos los eventos del dia:

```
[HH:MM] - Despertar
[HH:MM] - Desayuno (tostadas + mermelada + te)
[HH:MM] - Almuerzo (arroz + atun + huevo duro)  ← solo si corresponde
[HH:MM] - Ultima ingesta solida
[HH:MM] - Hidratacion final (300ml)
[HH:MM] - Salir de casa
[HH:MM] - Estar en el lugar
[HH:MM] - Entrada en calor
[HH:MM] - LARGADA
[HH:MM] - Post-carrera: comer + hidratacion
```

---

## Plan para ENTRENAMIENTO INTENSO

### Clase grupal (martes o jueves, 19:00)

- **Almuerzo:** 13:00-13:30. Comida completa pero no pesada. Evitar legumbres, frituras, comida muy grasa
- **Merienda pre-entreno:** 17:00-17:30. Banana + tostada con mermelada, o fruta + yogur. No mas tarde de 17:45
- **Hidratacion:** 500ml entre almuerzo y merienda. 300ml entre merienda y entreno
- **Antes del entreno:** nada solido despues de las 17:45
- **Post-entreno (~21:00):** cena liviana dentro de la hora de terminar. Proteina + carbohidrato simple (ej: huevos + arroz, pollo + pure, yogur + fruta)
- **Que evitar:** alcohol el dia anterior y ese dia, comida muy condimentada o indigesta

### Fondo largo (domingo, hora variable)

Si no se conoce la hora del fondo, preguntar antes de generar el plan.

Misma logica que dia de carrera pero sin el plan "dia anterior":
- Despertar H - 2.5h (fondos hasta 15k) o H - 3h (mas de 15k)
- Desayuno liviano: tostadas + te, 2h antes de H
- Hidratacion: 500ml entre despertar y salir
- Llevar agua o planificar donde hidratarse en ruta (cada 5-7km)
- Post-fondo: comida rica en proteina + carbohidrato dentro de los 45min de terminar

Consultar clima con skill `weather` para recomendar horario optimo si aun no esta definido (evitar pico de calor).

---

## Tono y formato

- Usar lenguaje directo, sin preambuos
- Siempre incluir el timeline visual con horarios concretos
- Si falta informacion (hora de carrera desconocida, dia de fondo sin hora), preguntar antes de generar el plan
- Agregar 1-2 recomendaciones concretas segun el tipo de carrera (distancia, terreno, hora del dia)
- Si es modo pacer, aclararlo prominentemente al inicio del plan y NO dar recomendaciones de rendimiento ni ajustes nutricionales
