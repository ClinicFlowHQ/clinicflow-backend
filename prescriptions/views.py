# prescriptions/views.py
import logging
from io import BytesIO

from django.http import HttpResponse

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from .models import Medication, Prescription, PrescriptionTemplate
from .permissions import IsStaffOrReadOnly, IsDoctorOnly, IsAuthenticatedStaffRole
from .serializers import (
    MedicationSerializer,
    PrescriptionSerializer,
    PrescriptionDetailSerializer,
    PrescriptionListSerializer,
    PrescriptionTemplateSerializer,
    PrescriptionTemplateDetailSerializer,
    PrescriptionTemplateWriteSerializer,
)


# PDF translations (French only)
PDF_TRANSLATIONS = {
    "title": "ORDONNANCE MÉDICALE",
    "patient": "Patient :",
    "code": "Code :",
    "visit_date": "Date de visite :",
    "prescription_num": "Ordonnance N° :",
    "created": "Créée le :",
    "prescriber": "Prescripteur :",
    "license": "N° Licence :",
    "department": "Service :",
    "specialty": "Spécialité :",
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
}


class MedicationViewSet(viewsets.ModelViewSet):
    queryset = Medication.objects.all().order_by("name")
    serializer_class = MedicationSerializer
    permission_classes = [IsAuthenticatedStaffRole]
    filter_backends = [SearchFilter]
    search_fields = ["name", "strength", "form"]


class PrescriptionTemplateViewSet(viewsets.ModelViewSet):
    queryset = PrescriptionTemplate.objects.prefetch_related("items__medication").all().order_by("name")
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["name", "name_fr", "description", "description_fr"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PrescriptionTemplateDetailSerializer
        if self.action in ["create", "update", "partial_update"]:
            return PrescriptionTemplateWriteSerializer
        return PrescriptionTemplateSerializer


class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = (
        Prescription.objects.all()
        .select_related("patient", "visit")
        .prefetch_related("items__medication")
        .order_by("-created_at")
    )
    permission_classes = [IsDoctorOnly]

    def get_queryset(self):
        """
        Optional filters:
        /api/prescriptions/?visit=<visit_id>
        /api/prescriptions/?patient=<patient_id>
        """
        qs = super().get_queryset()

        visit_id = self.request.query_params.get("visit")
        if visit_id:
            qs = qs.filter(visit_id=visit_id)

        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PrescriptionListSerializer
        if self.action == "retrieve":
            return PrescriptionDetailSerializer
        return PrescriptionSerializer

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error listing prescriptions: {e}", exc_info=True)
            raise

    def create(self, request, *args, **kwargs):
        try:
            logger.info(f"Creating prescription with data: {request.data}")
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error creating prescription: {e}", exc_info=True)
            raise

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        """
        GET /api/prescriptions/{id}/pdf/
        Returns a PDF prescription in French.
        """
        rx = self.get_object()
        t = PDF_TRANSLATIONS

        # Get prescriber info (current user making the request)
        user = request.user
        prescriber_name = f"Dr. {user.first_name} {user.last_name}".strip()
        if prescriber_name == "Dr.":
            prescriber_name = f"Dr. {user.username}"

        # Try to get profile info (license, department, specialty, bio)
        license_number = ""
        department = ""
        specialty = ""
        bio = ""
        try:
            if hasattr(user, 'profile'):
                profile = user.profile
                license_number = profile.license_number or ""
                department = profile.department or ""
                specialty = profile.specialization or ""
                bio = profile.bio or ""
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
            fontSize=16,
            spaceAfter=6,
            alignment=1,  # Center
            textColor=colors.HexColor('#1f2937'),
        )
        doctor_name_style = ParagraphStyle(
            'DoctorName',
            parent=styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            spaceAfter=2,
        )
        doctor_info_style = ParagraphStyle(
            'DoctorInfo',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4b5563'),
            spaceAfter=1,
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

        # Build content
        content = []

        # Doctor bio at top left (with newlines preserved)
        if bio:
            for line in bio.split('\n'):
                if line.strip():
                    content.append(Paragraph(line.strip(), doctor_info_style))
            content.append(Spacer(1, 15))

        # Title centered
        content.append(Paragraph(t["title"], title_style))
        content.append(Spacer(1, 10))

        # Prescription info
        patient = rx.patient
        patient_name = f"{patient.first_name} {patient.last_name}"
        patient_code = getattr(patient, 'patient_code', None) or "-"
        visit_date = rx.visit.visit_date.strftime("%d/%m/%Y %H:%M") if rx.visit and rx.visit.visit_date else "-"
        created_date = rx.created_at.strftime("%d/%m/%Y %H:%M") if rx.created_at else "-"

        # Patient info table
        patient_data = [
            [t["patient"], patient_name, t["code"], patient_code],
            [t["visit_date"], visit_date, t["prescription_num"], str(rx.id)],
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

        items = rx.items.all()
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

            med_table = Table(med_data, colWidths=[25, 200, 80, 60, 90, 60])
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
        if rx.notes:
            content.append(Spacer(1, 15))
            content.append(Paragraph(t["additional_notes"], heading_style))
            # Handle multiline notes
            for line in rx.notes.split('\n'):
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
        response['Content-Disposition'] = f'attachment; filename="ordonnance_{rx.id}.pdf"'
        return response
