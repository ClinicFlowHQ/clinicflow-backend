# prescriptions/views.py
from io import BytesIO

from django.http import HttpResponse
from django.contrib.staticfiles import finders

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Medication, Prescription, PrescriptionTemplate
from .permissions import IsStaffOrReadOnly
from .serializers import (
    MedicationSerializer,
    PrescriptionSerializer,
    PrescriptionDetailSerializer,
    PrescriptionListSerializer,
    PrescriptionTemplateSerializer,
    PrescriptionTemplateDetailSerializer,
)


class MedicationViewSet(viewsets.ModelViewSet):
    queryset = Medication.objects.all().order_by("name")
    serializer_class = MedicationSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [SearchFilter]
    search_fields = ["name", "strength", "form"]


class PrescriptionTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PrescriptionTemplate.objects.all().order_by("name")
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["name", "description"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PrescriptionTemplateDetailSerializer
        return PrescriptionTemplateSerializer


class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = (
        Prescription.objects.all()
        .select_related("visit", "visit__patient")
        .order_by("-created_at")
    )
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optional filters:
        /api/prescriptions/?visit=<visit_id>
        /api/prescriptions/?patient=<patient_id>
        /api/prescriptions/?visit=<visit_id>&patient=<patient_id>
        """
        qs = super().get_queryset()

        visit_id = self.request.query_params.get("visit")
        if visit_id:
            qs = qs.filter(visit_id=visit_id)

        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(visit__patient_id=patient_id)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PrescriptionListSerializer
        if self.action == "retrieve":
            return PrescriptionDetailSerializer
        return PrescriptionSerializer

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        """
        GET /api/prescriptions/{id}/pdf/
        Returns a 1-page French PDF (ReportLab) with logo + centered title.
        """
        rx = self.get_object()

        try:
            from reportlab.lib.pagesizes import LETTER
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
        except Exception:
            return Response(
                {"detail": "reportlab is not installed. Run: pip install reportlab"},
                status=501,
            )

        from io import BytesIO
        import os
        from django.conf import settings

        # ---------- find logo.png ----------
        logo_path = None

        # 1) Staticfiles finder (best)
        try:
            from django.contrib.staticfiles import finders
            logo_path = finders.find("logo.png")
        except Exception:
            logo_path = None

        # 2) Common explicit locations (fallbacks)
        candidates = []
        try:
            candidates.append(os.path.join(str(settings.BASE_DIR), "static", "logo.png"))
            candidates.append(os.path.join(str(settings.BASE_DIR), "logo.png"))
        except Exception:
            pass

        # Also try current working directory (dev)
        candidates.append(os.path.join(os.getcwd(), "static", "logo.png"))
        candidates.append(os.path.join(os.getcwd(), "logo.png"))

        if not logo_path:
            logo_path = next((p for p in candidates if p and os.path.exists(p)), None)

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=LETTER)
        width, height = LETTER

        # -----------------------------
        # Layout constants (tuned to stay 1 page)
        # -----------------------------
        left = 54
        right = 54
        top = height - 54
        bottom = 54

        title_font = ("Helvetica-Bold", 16)
        h_font = ("Helvetica-Bold", 12)
        normal_font = ("Helvetica", 11)
        small_font = ("Helvetica", 10)

        line_gap = 14
        section_top_space = 18
        section_header_gap = 14
        item_gap = 10
        rule_gap = 10

        def hr(y_pos, thickness=1):
            c.setLineWidth(thickness)
            c.line(left, y_pos, width - right, y_pos)
            c.setLineWidth(1)

        def wrap_text(text, max_width, font_name="Helvetica", font_size=11):
            from reportlab.pdfbase.pdfmetrics import stringWidth
            if not text:
                return []
            words = str(text).split()
            lines = []
            cur = ""
            for w in words:
                test = (cur + " " + w).strip()
                if stringWidth(test, font_name, font_size) <= max_width:
                    cur = test
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            return lines

        def draw_wrapped_block(x, y_pos, text, font=("Helvetica", 11), max_width=460, gap=14):
            c.setFont(*font)
            lines = []
            for raw_line in str(text).split("\n"):
                raw_line = raw_line.rstrip()
                if not raw_line:
                    lines.append("")
                    continue
                lines.extend(wrap_text(raw_line, max_width, font[0], font[1]))
            for ln in lines:
                if ln == "":
                    y_pos -= gap
                else:
                    c.drawString(x, y_pos, ln)
                    y_pos -= gap
            return y_pos

        # -----------------------------
        # Header: Logo (centered) + Title (centered under logo)
        # -----------------------------
        y = top

        logo_w = 120
        logo_h = 36
        if logo_path:
            try:
                img = ImageReader(logo_path)
                x_logo = (width - logo_w) / 2
                c.drawImage(
                    img,
                    x_logo,
                    y - logo_h,
                    width=logo_w,
                    height=logo_h,
                    preserveAspectRatio=True,
                    mask="auto",
                )
                y -= (logo_h + 12)
            except Exception:
                y -= 20
        else:
            # if missing, keep spacing so layout stays consistent
            y -= 20

        c.setFont(*title_font)
        c.drawCentredString(width / 2, y, "Ordonnance")
        y -= 18

        hr(y)
        y -= (rule_gap + 2)

        # -----------------------------
        # Patient / visit details
        # -----------------------------
        patient = getattr(rx.visit, "patient", None)
        patient_name = ""
        patient_phone = ""
        if patient:
            fn = getattr(patient, "first_name", "") or ""
            ln = getattr(patient, "last_name", "") or ""
            patient_name = f"{fn} {ln}".strip()
            patient_phone = getattr(patient, "phone", "") or ""

        key_x = left
        val_x = left + 120

        def kv(y_pos, key, val):
            c.setFont(*small_font)
            c.drawString(key_x, y_pos, key)
            c.drawString(val_x, y_pos, str(val) if val is not None else "")
            return y_pos - 14

        y = kv(y, "ID Ordonnance :", rx.id)
        y = kv(y, "ID Visite :", rx.visit_id)
        y = kv(y, "Patient :", patient_name or "")
        y = kv(y, "Téléphone :", patient_phone or "")

        y -= section_top_space

        # -----------------------------
        # Médicaments
        # -----------------------------
        c.setFont(*h_font)
        c.drawString(left, y, "Médicaments")
        y -= 10
        hr(y)
        y -= section_header_gap

        max_w = width - left - right

        for idx, item in enumerate(rx.items.all(), start=1):
            med = getattr(item, "medication", None)
            med_label = str(med) if med else "Médicament (manquant)"

            y = draw_wrapped_block(
                left,
                y,
                f"{idx}) {med_label}",
                font=("Helvetica-Bold", 11),
                max_width=max_w,
                gap=line_gap,
            )

            allow_out = getattr(item, "allow_outside_purchase", False)
            allow_text = "Oui" if allow_out else "Non"

            details = (
                f"Posologie : {item.dosage or '-'} ; "
                f"Voie : {item.route or '-'} ; "
                f"Fréquence : {item.frequency or '-'} ; "
                f"Durée : {item.duration or '-'} ; "
                f"Achat externe : {allow_text}"
            )

            y = draw_wrapped_block(
                left + 18,
                y,
                details,
                font=("Helvetica", 10),
                max_width=max_w - 18,
                gap=13,
            )

            if item.instructions:
                y = draw_wrapped_block(
                    left + 18,
                    y,
                    f"Instructions : {item.instructions}",
                    font=("Helvetica-Oblique", 10),
                    max_width=max_w - 18,
                    gap=13,
                )

            y -= item_gap

            # Keep 1-page by tightening if needed
            if y < (bottom + 110):
                line_gap = 12
                item_gap = 6

        # -----------------------------
        # Notes
        # -----------------------------
        y -= 6
        c.setFont(*h_font)
        c.drawString(left, y, "Notes")
        y -= 10
        hr(y)
        y -= section_header_gap

        notes_text = rx.notes or ""
        if notes_text.strip():
            y = draw_wrapped_block(left, y, notes_text, font=("Helvetica", 10), max_width=max_w, gap=13)
        else:
            c.setFont(*small_font)
            c.drawString(left, y, "(Aucune note)")
            y -= 14

        # -----------------------------
        # Signature
        # -----------------------------
        y -= 18
        c.setFont(*small_font)
        c.drawString(left, y, "Signature du médecin :")
        c.line(left + 150, y - 2, width - right, y - 2)

        c.save()

        pdf_bytes = buffer.getvalue()
        buffer.close()

        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="ordonnance-{rx.id}.pdf"'
        return resp

