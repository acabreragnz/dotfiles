---
name: automation-pay-psychologist
description: Use when paying the monthly psychologist session fee — executes a BROU bank transfer to Lucia Sosa using the saved template and sends the receipt via WhatsApp Web with a thank you message.
allowed-tools: mcp__chrome-devtools__list_pages, mcp__chrome-devtools__select_page, mcp__chrome-devtools__new_page, mcp__chrome-devtools__navigate_page, mcp__chrome-devtools__take_snapshot, mcp__chrome-devtools__click, mcp__chrome-devtools__fill, mcp__chrome-devtools__wait_for, mcp__chrome-devtools__evaluate_script, mcp__chrome-devtools__upload_file, mcp__chrome-devtools__press_key, Bash(date:*), Bash(notify-send:*), Bash(ls:*), Bash(pdftotext:*)
---

# Automation: Pagar Psicóloga

Pago mensual a la psicóloga + envío del comprobante por WhatsApp.

**Sub-skills:** `bank` · `whatsapp-web` · `money-keeper`

---

## Datos

| Campo | Valor |
|-------|-------|
| Plantilla BROU | `Lucia Psicologa ajuste 2026` |
| Contacto WhatsApp | `Psicologa Lucia Sosa` |
| Búsqueda WhatsApp | `Psicologa Lucia` |
| Mensaje (separado) | `"Hola! Te mando el comprobante del pago 🙌 graciaas!"` |

---

## Flujo

### 0 — Verificar que el pago no fue hecho ya ← OBLIGATORIO

**Riesgo:** doble transferencia. Verificar antes de proceder.

```bash
date +'%Y%m'  # obtener prefijo del mes actual, ej: 202602
ls ~/Downloads/Transferencia_a_terceros_*.pdf 2>/dev/null | sort -t_ -k4 | tail -5
```

Si hay un PDF del mes actual en `~/Downloads` → leerlo automáticamente para verificar si es para Lucia:

```bash
pdftotext ~/Downloads/Transferencia_a_terceros_<archivo_del_mes>.pdf -
```

- Si el contenido contiene "LUCIA SOSA" → detener y reportar: "Ya hay una transferencia a Lucia este mes. ¿Querés continuar igual?"
- Si el contenido es para otra persona → proceder normalmente con el paso 1.

Si no hay PDF local (o es de un mes anterior), verificar en los movimientos bancarios:

```
bank: login → navigate_page url="https://ebanking.brou.com.uy/frontend/accounts/balanceAndStatements/<hash_CA_Trabajo>"
→ buscar movimiento con descripción "Lucia" o "Psicologa" en el mes actual
```

- Si **existe** movimiento del mes actual → detener y reportar al usuario: "Ya hay una transferencia a Lucia este mes. ¿Querés continuar igual?"
- Si **no existe** → proceder con el paso 1.

### 1 — Transferencia bancaria

Seguir el skill `bank` con la plantilla **"Lucia Psicologa ajuste 2026"**.

> **Recordar:** hacer click en tab "BROU" antes de buscar la plantilla. La plantilla está en página 1 del tab BROU.

El skill `bank` descarga el PDF automáticamente al completar la transferencia. Retorna el path:

```
~/Downloads/Transferencia_a_terceros_<número_operación>.pdf
```

Usar ese path para el paso siguiente.

### 2 — Envío por WhatsApp

Seguir el skill `whatsapp-web` para enviar a **"Psicologa Lucia Sosa"**:

1. Abrir WhatsApp Web → chat "Psicologa Lucia Sosa" (visible en lista principal, no requiere buscar)
2. Adjuntar PDF — verificar que el archivo existe antes de adjuntar:
   ```bash
   ls ~/Downloads/Transferencia_a_terceros_<número_operación>.pdf
   ```
   Usar el path exacto con el número de operación retornado por el skill `bank`. No asumir el nombre.
3. Adjuntar el PDF y subirlo — usar `whatsapp-web` "Operación: Enviar documento".
   **[PAUSA — irreversible]** Después de subir el archivo, antes de enviarlo:
   ```bash
   notify-send "WhatsApp - Confirmación requerida" "Voy a enviar el comprobante PDF a Psicologa Lucia Sosa. Avisame cuando estés de acuerdo." --urgency=critical
   ```
   > Esperar confirmación del usuario. Luego enviar (usar snapshot+uid, NO `button[aria-label="Send"]` por querySelector — falla en el preview).
4. Escribir el mensaje de texto primero, **luego** pausar:
   - Escribir: `"Hola! Te mando el comprobante del pago 🙌 graciaas!"`
   - **[PAUSA — irreversible]** Después de escribir, antes de enviar:
   ```bash
   notify-send "WhatsApp - Confirmación requerida" "Voy a enviar el mensaje de texto a Psicologa Lucia Sosa. Avisame cuando estés de acuerdo." --urgency=critical
   ```
   > Esperar confirmación del usuario. Luego enviar con `press_key Enter`.

### 3 — Registrar gasto en Money Keeper

Seguir el skill `money-keeper` con los siguientes datos:

| Campo | Valor |
|-------|-------|
| Monto | monto de la transferencia (ej: `1700`) |
| Cuenta | `Banco` |
| Fecha | viernes anterior al día del pago (`date` para calcularlo) |
| Categoría | `Terapia` |
| Descripción | (vacía) |

### 4 — Marcar tarea en Todoist

Navegar a `https://app.todoist.com/app/today` y buscar la tarea de la psicóloga por keyword parcial:

```
take_snapshot { filePath: "/tmp/td_snap.txt" }
```

```bash
grep -i "psicolog" /tmp/td_snap.txt | grep checkbox | grep -oP 'uid=\K\S+' | head -1
```

> **Nunca buscar por el título exacto** — usar siempre `psicolog` (keyword parcial) para que el skill no se rompa si el usuario renombra la tarea.

```
click { uid: <uid_checkbox> }
```

Verificar que la tarea desapareció de la vista:
```bash
grep -i "psicolog" /tmp/td_snap.txt | head -3
# si no aparece → completada correctamente
```

### 5 — Confirmación

> "✅ Transferencia completada, comprobante enviado a Lucia, gasto registrado en Money Keeper y tarea marcada en Todoist."

---

## Reglas

- **Nunca transferir sin completar el paso 0** — doble transferencia es irreversible
- Si la transferencia falla → NO ejecutar ningún paso posterior (WhatsApp, Money Keeper, Todoist), reportar error
- Los pasos 2, 3 y 4 son dependientes del éxito del paso 1 — no ejecutar en orden diferente
- Buscar tarea de Todoist siempre por keyword parcial (`psicolog`), nunca por título exacto
- Siempre esperar revisión del usuario antes del paso "Confirmar" (llave digital)
- No enviar ningún mensaje de WhatsApp sin confirmación del usuario
