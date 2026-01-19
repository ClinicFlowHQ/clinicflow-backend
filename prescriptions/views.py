from io import BytesIO
from django.http import HttpResponse
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .models import Prescription, Medication, PrescriptionTemplate
from .serializers import (
    MedicationSerializer,
    PrescriptionSerializer,
    PrescriptionDetailSerializer,
    PrescriptionTemplateSerializer,
    PrescriptionTemplateDetailSerializer,
    PrescriptionTemplateWriteSerializer,
)


# PDF translations
PDF_TRANSLATIONS = {
    "en": {
        "title": "Medical Prescription",
        "patient": "Patient:",
        "code": "Code:",
        "visit_date": "Visit Date:",
        "prescription_num": "Prescription #:",
        "created": "Created:",
        "prescriber": "Prescriber:",
        "license": "License #:",
        "medications": "Medications",
        "med_num": "#",
        "medication": "Medication",
        "dosage": "Dosage",
        "route": "Route",
        "frequency": "Frequency",
        "duration": "Duration",
        "instructions": "Instructions",
        "no_medications": "No medications listed.",
        "additional_notes": "Additional Notes",
        "signature": "Prescriber Signature",
        "date": "Date:",
        "stamp": "Stamp",
    },
    "fr": {
        "title": "Ordonnance Médicale",
        "patient": "Patient :",
        "code": "Code :",
        "visit_date": "Date de visite :",
        "prescription_num": "Ordonnance N° :",
        "created": "Créée le :",
        "prescriber": "Prescripteur :",
        "license": "N° Licence :",
        "medications": "Médicaments",
        "med_num": "N°",
        "medication": "Médicament",
        "dosage": "Posologie",
        "route": "Voie",
        "frequency": "Fréquence",
        "duration": "Durée",
        "instructions": "Instructions",
        "no_medications": "Aucun médicament listé.",
        "additional_notes": "Notes supplémentaires",
        "signature": "Signature du prescripteur",
        "date": "Date :",
        "stamp": "Cachet",
    },
}


class MedicationListCreateAPIView(generics.ListCreateAPIView):
    queryset = Medication.objects.filter(is_active=True).order_by("name")
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated]


class PrescriptionListCreateAPIView(generics.ListCreateAPIView):
    queryset = (
        Prescription.objects
        .select_related("visit", "visit__patient", "template_used")
        .prefetch_related("items__medication")
        .all()
    )
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return PrescriptionDetailSerializer
        return PrescriptionSerializer


class PrescriptionDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = (
        Prescription.objects
        .select_related("visit", "visit__patient", "template_used")
        .prefetch_related("items__medication")
        .all()
    )
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrescriptionSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return PrescriptionDetailSerializer
        return PrescriptionSerializer


class PrescriptionPDFView(APIView):
    """Generate PDF for a prescription (supports French/English)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        # Get language from query param (default to French)
        lang = request.query_params.get("lang", "fr")
        if lang not in PDF_TRANSLATIONS:
            lang = "fr"
        t = PDF_TRANSLATIONS[lang]

        try:
            prescription = (
                Prescription.objects
                .select_related("visit", "visit__patient")
                .prefetch_related("items__medication")
                .get(pk=pk)
            )
        except Prescription.DoesNotExist:
            return Response(
                {"detail": "Prescription not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get prescriber info (current user making the request)
        user = request.user
        prescriber_name = f"Dr. {user.first_name} {user.last_name}".strip()
        if prescriber_name == "Dr.":
            prescriber_name = f"Dr. {user.username}"

        # Try to get license number from profile
        license_number = ""
        try:
            if hasattr(user, 'profile') and user.profile.license_number:
                license_number = user.profile.license_number
        except Exception:
            pass

        # Generate PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=6,
            textColor=colors.HexColor('#10b981'),
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=12,
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor('#1f2937'),
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=4,
        )
        prescriber_style = ParagraphStyle(
            'PrescriberStyle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=2,
            textColor=colors.HexColor('#374151'),
        )

        # Build content
        content = []

        # Header
        content.append(Paragraph("ClinicFlowHQ", title_style))
        content.append(Paragraph(t["title"], subtitle_style))
        content.append(Spacer(1, 10))

        # Prescription info
        patient = prescription.visit.patient
        patient_name = f"{patient.first_name} {patient.last_name}"
        patient_code = patient.patient_code or "-"
        visit_date = prescription.visit.visit_date.strftime("%d/%m/%Y %H:%M") if prescription.visit.visit_date else "-"
        created_date = prescription.created_at.strftime("%d/%m/%Y %H:%M") if prescription.created_at else "-"

        # Patient info table
        patient_data = [
            [t["patient"], patient_name, t["code"], patient_code],
            [t["visit_date"], visit_date, t["prescription_num"], str(prescription.id)],
            [t["created"], created_date, "", ""],
        ]
        patient_table = Table(patient_data, colWidths=[80, 140, 80, 90])
        patient_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        content.append(patient_table)
        content.append(Spacer(1, 15))

        # Medications section
        content.append(Paragraph(t["medications"], heading_style))

        items = prescription.items.all()
        if items.exists():
            # Medications table header
            med_data = [[t["med_num"], t["medication"], t["dosage"], t["route"], t["frequency"], t["duration"]]]
            for i, item in enumerate(items, 1):
                med_name = str(item.medication) if item.medication else "-"
                med_data.append([
                    str(i),
                    med_name,
                    item.dosage or "-",
                    item.route or "-",
                    item.frequency or "-",
                    item.duration or "-",
                ])

            med_table = Table(med_data, colWidths=[20, 130, 70, 50, 70, 50])
            med_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ]))
            content.append(med_table)

            # Instructions for each medication
            has_instructions = any(item.instructions for item in items)
            if has_instructions:
                content.append(Spacer(1, 10))
                content.append(Paragraph(t["instructions"], heading_style))
                for i, item in enumerate(items, 1):
                    if item.instructions:
                        med_name = str(item.medication) if item.medication else f"Item {i}"
                        content.append(Paragraph(f"<b>{med_name}:</b> {item.instructions}", normal_style))
        else:
            content.append(Paragraph(t["no_medications"], normal_style))

        # Notes section
        if prescription.notes:
            content.append(Spacer(1, 15))
            content.append(Paragraph(t["additional_notes"], heading_style))
            # Handle multiline notes
            for line in prescription.notes.split('\n'):
                if line.strip():
                    content.append(Paragraph(line, normal_style))

        # Prescriber section
        content.append(Spacer(1, 30))

        # Create prescriber info box
        prescriber_data = [
            [t["prescriber"], prescriber_name],
        ]
        if license_number:
            prescriber_data.append([t["license"], license_number])
        prescriber_data.append([t["date"], created_date])

        prescriber_table = Table(prescriber_data, colWidths=[100, 200])
        prescriber_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        content.append(prescriber_table)

        # Signature line
        content.append(Spacer(1, 20))
        signature_data = [
            ["_" * 35, "_" * 25],
            [t["signature"], t["stamp"]],
        ]
        signature_table = Table(signature_data, colWidths=[200, 150])
        signature_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        content.append(signature_table)

        # Build PDF
        doc.build(content)

        # Return response
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ordonnance_{prescription.id}.pdf"'
        return response


class PrescriptionTemplateListCreateAPIView(generics.ListCreateAPIView):
    queryset = PrescriptionTemplate.objects.prefetch_related("items__medication").all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PrescriptionTemplateWriteSerializer
        return PrescriptionTemplateSerializer


class PrescriptionTemplateDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PrescriptionTemplate.objects.prefetch_related("items__medication").all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return PrescriptionTemplateWriteSerializer
        return PrescriptionTemplateDetailSerializer
