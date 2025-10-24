#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera un PDF con etiquetas en una grilla de 3x10 (o configurable) con rectángulos de 51x25 mm.
- Limpia los nombres: elimina espacios antes de comas y elimina todas las comas.
- Descarta la línea de encabezado 'NOMBRE' si aparece como primera no vacía.
- Centra el texto en 1 o 2 líneas; reduce fuente levemente si es necesario.
Requiere: reportlab
"""

import argparse
import os
import re
from typing import List, Tuple

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def parse_args():
    p = argparse.ArgumentParser(description="Generar PDF de etiquetas desde un archivo de nombres (uno por línea)."),
    p = argparse.ArgumentParser(description="Generar PDF de etiquetas desde un archivo de nombres (uno por línea)." )
    p.add_argument("input", help="Ruta a invitados.txt (UTF-8)")
    p.add_argument("output", help="Ruta de salida del PDF, p. ej.: etiquetas.pdf")
    p.add_argument("--page", choices=["letter", "A4"], default="letter", help="Tamaño de página (default: letter)")
    p.add_argument("--cols", type=int, default=3, help="Columnas (default: 3)")
    p.add_argument("--rows", type=int, default=10, help="Filas (default: 10)")
    p.add_argument("--label-width-mm", type=float, default=51.0, help="Ancho etiqueta en mm (default: 51)")
    p.add_argument("--label-height-mm", type=float, default=25.0, help="Alto etiqueta en mm (default: 25)")
    p.add_argument("--hspace-mm", type=float, default=3.0, help="Espaciado horizontal en mm (default: 3)")
    p.add_argument("--vspace-mm", type=float, default=3.0, help="Espaciado vertical en mm (default: 3)")
    p.add_argument("--font-size", type=float, default=9.0, help="Tamaño base de fuente (default: 9)")
    p.add_argument("--min-font-size", type=float, default=8.0, help="Tamaño mínimo si requiere reducir (default: 8)")
    p.add_argument("--font-path", type=str, default="", help="Ruta opcional a fuente TTF con acentos (p. ej. DejaVuSans.ttf)")
    p.add_argument("--no-rect", action="store_true", help="No dibujar rectángulos (sólo texto)")
    p.add_argument("--debug", action="store_true", help="Dibujar guías de línea base para depurar")
    return p.parse_args()


def find_font(user_font_path: str = "") -> Tuple[str, str]:
    """Devuelve (font_name, font_src). Prefiere TTF con acentos; si no, Helvetica."""
    if user_font_path and os.path.isfile(user_font_path):
        pdfmetrics.registerFont(TTFont("CustomFont", user_font_path))
        return "CustomFont", user_font_path

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", path))
                return "DejaVuSans", path
            except Exception:
                continue
    return "Helvetica", "built-in"


def clean_names(lines: List[str]) -> List[str]:
    names = []
    for raw in lines:
        # Soporta BOM UTF-8 si existe
        s = raw.replace("\ufeff", "").strip()
        if not s:
            continue
        s = re.sub(r"\s+,", ",", s)  # quita espacios antes de coma
        s = s.replace(",", "")       # elimina comas
        names.append(s)

    # Si la primera no vacía es 'NOMBRE', descártala
    for i, s in enumerate(names):
        if s.strip().lower() == "nombre":
            names.pop(i)
            break
    return names


def wrap_two_lines(text: str, font_name: str, fs: float, max_width: float) -> List[str]:
    """Ajusta a 1 o 2 líneas midiendo ancho real."""
    if pdfmetrics.stringWidth(text, font_name, fs) <= max_width:
        return [text]

    words = text.split()
    line1 = []
    for w in words:
        cand = (" ".join(line1 + [w])).strip()
        if pdfmetrics.stringWidth(cand, font_name, fs) <= max_width:
            line1.append(w)
        else:
            break

    if not line1:
        # Si ni una palabra cabe, cortar a la mitad con guión
        mid = max(1, len(words[0]) // 2)
        l1 = words[0][:mid] + "-"
        l2 = words[0][mid:] + (" " + " ".join(words[1:]) if len(words) > 1 else "")
        return [l1, l2]

    line1_text = " ".join(line1).strip()
    line2_text = " ".join(words[len(line1):]).strip()

    if not line2_text:
        return [line1_text]

    # Si la segunda línea excede, intentar simple balance
    if pdfmetrics.stringWidth(line2_text, font_name, fs) > max_width:
        # mover una palabra de line1 a line2 si ayuda
        l1_words = line1_text.split()
        while l1_words:
            moved = l1_words.pop()  # mueve última
            new_l1 = " ".join(l1_words)
            new_l2 = (moved + " " + line2_text).strip()
            if (not new_l1) or pdfmetrics.stringWidth(new_l1, font_name, fs) <= max_width:
                line1_text = new_l1 if new_l1 else moved  # no dejes vacía
                line2_text = new_l2
                if pdfmetrics.stringWidth(line2_text, font_name, fs) <= max_width:
                    break
            else:
                # si no cabe la nueva l1, revertimos y salimos
                l1_words.append(moved)
                break

        # Si aún no cabe, dividir forzado
        if pdfmetrics.stringWidth(line2_text, font_name, fs) > max_width:
            half = max(1, len(line2_text) // 2)
            line2_text = line2_text[:half].rstrip() + "- " + line2_text[half:].lstrip()

    return [line1_text, line2_text] if line2_text else [line1_text]


def fit_text(text: str, font_name: str, base_fs: float, min_fs: float, max_width: float) -> Tuple[List[str], float]:
    fs = base_fs
    lines = wrap_two_lines(text, font_name, fs, max_width)
    def fits(ls, size):
        return all(pdfmetrics.stringWidth(l, font_name, size) <= max_width for l in ls if l)

    while (len(lines) > 2 or not fits(lines, fs)) and fs > min_fs:
        fs -= 0.2
        lines = wrap_two_lines(text, font_name, fs, max_width)

    if len(lines) > 2:
        lines = lines[:2]
    return lines, fs


def main():
    args = parse_args()

    page_size = letter if args.page == "letter" else A4
    page_w, page_h = page_size

    label_w = args.label_width_mm * mm
    label_h = args.label_height_mm * mm
    cols = args.cols
    rows = args.rows
    hspace = args.hspace_mm * mm
    vspace = args.vspace_mm * mm

    total_w = cols * label_w + (cols - 1) * hspace
    total_h = rows * label_h + (rows - 1) * vspace
    margin_x = (page_w - total_w) / 2.0
    margin_y = (page_h - total_h) / 2.0

    font_name, font_src = find_font(args.font_path)

    with open(args.input, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()
    names = clean_names(raw_lines)

    c = canvas.Canvas(args.output, pagesize=page_size)

    base_fs = args.font_size
    min_fs = args.min_font_size

    pad_x = 2.0 * mm
    max_text_w = label_w - 2 * pad_x

    x = margin_x
    y = page_h - margin_y - label_h

    for i, name in enumerate(names):
        if not args.no_rect:
            c.rect(x, y, label_w, label_h)

        lines, fs_used = fit_text(name, font_name, base_fs, min_fs, max_text_w)
        line_h = fs_used + 2
        block_h = len(lines) * line_h
        start_y = y + (label_h - block_h) / 2.0

        for li, line in enumerate(lines):
            c.setFont(font_name, fs_used)
            tw = pdfmetrics.stringWidth(line, font_name, fs_used)
            tx = x + (label_w - tw) / 2.0
            ty = start_y + (len(lines) - li - 1) * line_h
            c.drawString(tx, ty, line)
            if args.debug:
                c.line(x + pad_x, ty, x + label_w - pad_x, ty)

        x += label_w + hspace
        if (i + 1) % cols == 0:
            x = margin_x
            y -= (label_h + vspace)

        if (i + 1) % (cols * rows) == 0 and (i + 1) < len(names):
            c.showPage()
            x = margin_x
            y = page_h - margin_y - label_h

    c.save()

    print(f"Página: {args.page}")
    print(f"Grilla: {cols}x{rows}, Etiqueta: {args.label_width_mm}x{args.label_height_mm} mm, Espaciado: {args.hspace_mm}x{args.vspace_mm} mm")
    print(f"Fuente: {font_name} ({font_src}) base {base_fs} pt (mín {min_fs} pt)")
    print(f"Nombres (sin encabezado): {len(names)}")
    print(f"PDF: {args.output}")


if __name__ == "__main__":
    main()
