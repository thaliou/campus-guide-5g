"""Génère un QR code PNG par point de départ décrit dans app/data/campus.json.

Chaque QR code ouvre <adresse>?depart=<id> : l'application sait alors
où se trouve l'étudiant, sans GPS.

Installation :   pip install qrcode pillow
Utilisation :    python generer_qr.py                          (adresse par défaut)
                 python generer_qr.py http://192.168.70.135/   (autre adresse)
Résultat :       app/qr/qr_<id>.png, à imprimer et coller à l'endroit indiqué.
"""
import json
import sys
from pathlib import Path

try:
    import qrcode
except ImportError:
    sys.exit("Bibliothèque manquante : lancez d'abord  pip install qrcode pillow")

ADRESSE_PAR_DEFAUT = "http://192.168.70.140/"

# Chemins calculés à partir de l'emplacement du script (marche depuis n'importe quel dossier)
DOSSIER = Path(__file__).resolve().parent
FICHIER_CAMPUS = DOSSIER / "app" / "data" / "campus.json"
DOSSIER_QR = DOSSIER / "app" / "qr"


def main():
    adresse = sys.argv[1] if len(sys.argv) > 1 else ADRESSE_PAR_DEFAUT
    if not adresse.endswith("/"):
        adresse += "/"

    with open(FICHIER_CAMPUS, encoding="utf-8") as f:
        campus = json.load(f)

    DOSSIER_QR.mkdir(exist_ok=True)
    for depart in campus["departs"]:
        url = f"{adresse}?depart={depart['id']}"
        # Correction d'erreur élevée (H) : le QR reste lisible même un peu abîmé
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        fichier = DOSSIER_QR / f"qr_{depart['id']}.png"
        qr.make_image(fill_color="black", back_color="white").save(fichier)
        print(f"{fichier.relative_to(DOSSIER)}  ->  {url}   ({depart['nom']})")


if __name__ == "__main__":
    main()
