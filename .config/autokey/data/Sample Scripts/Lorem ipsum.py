import lorem
import pyperclip

def generate_lorem_ipsum(characters):
    """
    Genera texto Lorem Ipsum con la cantidad especificada de caracteres.

    Args:
        characters (int): Número deseado de caracteres.

    Returns:
        str: Texto Lorem Ipsum generado.
    """
    if characters <= 0:
        return ""

    lorem_text = ""
    while len(lorem_text) < characters:
        # Añadir párrafos de Lorem Ipsum hasta alcanzar la longitud deseada
        lorem_text += lorem.paragraph() + " "
    
    # Recortar el texto a la longitud exacta de caracteres
    return lorem_text[:characters]

# Solicitar al usuario el número de caracteres
retCode, input_value = dialog.input_dialog("Generar Lorem Ipsum", "Ingrese el número de caracteres:")
if retCode == 0 and input_value:
    try:
        # Convertir la entrada en un número entero
        num_chars = int(input_value)

        # Generar el texto Lorem Ipsum
        lorem_ipsum_text = generate_lorem_ipsum(num_chars)

        pyperclip.set_clipboard("xclip")
        # Copiar el texto generado al portapapeles
        pyperclip.copy(lorem_ipsum_text)
    except ValueError:
        # Mostrar un mensaje de error si la entrada no es un número válido
        dialog.info_dialog("Entrada Inválida", "Por favor, ingrese un número válido.")
