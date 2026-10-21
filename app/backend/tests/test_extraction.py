"""Extraction du texte des fichiers déposés, PDF compris (garde-fou des mises à jour de pypdf)."""
import pytest

from qatag.extraction import FichierRefuse, extraire


def pdf(*pages: str) -> bytes:
    """PDF minimal valide, une ligne de texte Helvetica par page."""
    objets = ["<< /Type /Catalog /Pages 2 0 R >>", None,
              "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for texte in pages:
        flux = "BT /F1 12 Tf 72 720 Td (%s) Tj ET" % texte
        objets.append("<< /Length %d >>\nstream\n%s\nendstream" % (len(flux), flux))
        contenu = len(objets)
        objets.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                      "/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % contenu)
        kids.append("%d 0 R" % len(objets))
    objets[1] = "<< /Type /Pages /Kids [%s] /Count %d >>" % (" ".join(kids), len(kids))
    sortie, positions = b"%PDF-1.4\n", []
    for i, o in enumerate(objets, start=1):
        positions.append(len(sortie))
        sortie += ("%d 0 obj\n%s\nendobj\n" % (i, o)).encode("latin-1")
    xref = len(sortie)
    sortie += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objets) + 1)).encode()
    sortie += b"".join(b"%010d 00000 n \n" % p for p in positions)
    sortie += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
               % (len(objets) + 1, xref)).encode()
    return sortie


def test_pdf_texte_de_chaque_page():
    texte = extraire("sfd.pdf", pdf("US-042 Reinitialisation du mot de passe",
                                    "REQ-001 le lien expire apres 24 heures"))
    assert "US-042 Reinitialisation du mot de passe" in texte
    assert "REQ-001 le lien expire apres 24 heures" in texte
    assert texte.index("US-042") < texte.index("REQ-001")


def test_pdf_sans_texte_refuse():
    with pytest.raises(FichierRefuse, match="reconnaissance de texte"):
        extraire("scan.pdf", pdf(""))


def test_pdf_corrompu_refuse_proprement():
    with pytest.raises(FichierRefuse, match="illisible"):
        extraire("abime.pdf", b"%PDF-1.4\nceci n'est pas un pdf")


def test_extension_inconnue_refusee():
    with pytest.raises(FichierRefuse, match="non pris en charge"):
        extraire("note.odt", b"x")
