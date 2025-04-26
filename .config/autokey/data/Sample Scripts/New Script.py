import pyperclip

try:
    pyperclip.set_clipboard("xclip")

    # Copiar texto al portapapeles
    pyperclip.copy("Texto de prueba desde pyperclip dentro de AutoKey")

    # Recuperar el texto desde el portapapeles
    copied_text = pyperclip.paste()

    # Mostrar el texto copiado en un cuadro de diálogo
    dialog.info_dialog("Prueba de pyperclip", f"Texto copiado: {copied_text}")
except Exception as e:
    # Mostrar cualquier error en un cuadro de diálogo
    dialog.info_dialog("Error", f"Error al usar pyperclip: {e}")
