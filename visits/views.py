# visits/views.py
from io import BytesIO

from django.http import HttpResponse

from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from .models import Visit, VitalSign
from .serializers import VisitSerializer, VitalSignSerializer
from patients.permissions import IsVisitOwnerOrAdmin, IsVitalSignOwnerOrAdmin, _can_edit_visit


# PDF translations (French only - for visit summary/discharge document)
VISIT_PDF_TRANSLATIONS = {
    "title": "RÉSUMÉ DE CONSULTATION",
    "patient": "Patient :",
    "code": "Code :",
    "visit_date": "Date de visite :",
    "visit_type": "Type :",
    "chief_complaint": "Motif de consultation",
    "medical_history": "Antécédents médicaux",
    "history_present_illness": "Histoire de la maladie",
    "physical_exam": "Examen physique",
    "complementary_exam": "Examens complémentaires",
    "assessment": "Diagnostic / Évaluation",
    "plan": "Plan de traitement",
    "treatment": "Traitement",
    "notes": "Notes supplémentaires",
    "vitals": "Signes vitaux",
    "temperature": "Température",
    "blood_pressure": "Tension artérielle",
    "heart_rate": "Fréquence cardiaque",
    "respiratory_rate": "Fréquence respiratoire",
    "oxygen_saturation": "Saturation O2",
    "weight": "Poids",
    "height": "Taille",
    "prescriber": "Médecin :",
    "license": "N°COM :",
    "date": "Date :",
    "location": "Lieu :",
    "signature": "Signature du médecin",
    "stamp": "Cachet",
    "consultation": "Consultation",
    "follow_up": "Suivi",
}


class VisitListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = VisitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        All authenticated staff can see all visits.
        Optional filter: ?patient=<patient_id>
        """
        qs = (
            Visit.objects.select_related("patient", "patient__created_by")
            .order_by("-visit_date")
        )

        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)

        return qs

    def perform_create(self, serializer):
        """
        Any authenticated user can create a visit for any patient.
        The visit's created_by is set to the current user (the doctor creating it).
        """
        patient = serializer.validated_data.get("patient")
        if not patient:
            raise PermissionDenied("Patient is required.")

        # Save with current user as visit owner
        serializer.save(created_by=self.request.user)


class VisitDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = VisitSerializer
    permission_classes = [permissions.IsAuthenticated, IsVisitOwnerOrAdmin]

    def get_queryset(self):
        # All authenticated staff can access any visit
        return Visit.objects.select_related("patient", "created_by")


class VitalSignListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = VitalSignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        All authenticated staff can see all vitals.
        Optional filter: ?visit=<visit_id>
        """
        qs = (
            VitalSign.objects.select_related(
                "visit",
                "visit__patient",
                "visit__patient__created_by",
            )
            .order_by("-measured_at")
        )

        visit_id = self.request.query_params.get("visit")
        if visit_id:
            qs = qs.filter(visit_id=visit_id)

        return qs

    def perform_create(self, serializer):
        """
        Only the visit's creator (or patient creator for legacy visits) or admin can add vitals.
        """
        visit = serializer.validated_data.get("visit")
        if not visit:
            raise PermissionDenied("Visit is required.")

        if not _can_edit_visit(self.request.user, visit):
            raise PermissionDenied("You do not have permission to add vitals to this visit.")

        serializer.save()


class VitalSignDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = VitalSignSerializer
    permission_classes = [permissions.IsAuthenticated, IsVitalSignOwnerOrAdmin]

    def get_queryset(self):
        # All authenticated staff can access any vital sign
        return VitalSign.objects.select_related(
            "visit",
            "visit__patient",
            "visit__patient__created_by",
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def visit_summary_pdf(request, pk):
    """
    GET /api/visits/{id}/pdf/
    Returns a PDF visit summary/discharge document in French.
    """
    try:
        visit = Visit.objects.select_related("patient").get(pk=pk)
    except Visit.DoesNotExist:
        return HttpResponse("Visit not found", status=404)

    t = VISIT_PDF_TRANSLATIONS

    # Get prescriber info (current user making the request)
    user = request.user

    # Try to get profile info
    license_number = ""
    clinic_address = ""
    bio = ""
    display_name = ""
    specialty = ""
    try:
        if hasattr(user, 'profile'):
            profile = user.profile
            license_number = profile.license_number or ""
            clinic_address = profile.clinic_address or ""
            bio = profile.bio or ""
            display_name = profile.display_name or ""
            specialty = profile.specialization or ""
    except Exception:
        pass

    # Use display_name if set, otherwise fall back to first/last name
    if display_name:
        prescriber_name = display_name
    else:
        prescriber_name = f"Dr. {user.first_name} {user.last_name}".strip()
        if prescriber_name == "Dr.":
            prescriber_name = f"Dr. {user.username}"

    # Get latest vitals for this visit
    latest_vitals = visit.vital_signs.order_by("-measured_at").first()

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
    content_style = ParagraphStyle(
        'ContentStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        leftIndent=10,
    )

    # Build content
    content = []

    # Doctor header at top left
    # Line 1: Display name (bold, larger font)
    content.append(Paragraph(prescriber_name, doctor_name_style))

    # Line 2: Specialty (bold, normal font)
    if specialty:
        specialty_style = ParagraphStyle(
            'SpecialtyStyle',
            parent=styles['Normal'],
            fontSize=11,
            fontName='Helvetica-Bold',
            spaceAfter=2,
        )
        content.append(Paragraph(specialty.upper(), specialty_style))

    # Additional bio info (normal font) - for things like certifications, clinic hours
    if bio:
        for line in bio.split('\n'):
            if line.strip():
                content.append(Paragraph(line.strip(), doctor_info_style))

    content.append(Spacer(1, 15))

    # Title centered
    content.append(Paragraph(t["title"], title_style))
    content.append(Spacer(1, 10))

    # Patient info
    patient = visit.patient
    patient_name = f"{patient.first_name} {patient.last_name}"
    patient_code = getattr(patient, 'patient_code', None) or "-"
    visit_date = visit.visit_date.strftime("%d/%m/%Y %H:%M") if visit.visit_date else "-"
    visit_type_display = t["consultation"] if visit.visit_type == "CONSULTATION" else t["follow_up"]

    # Patient info table
    patient_data = [
        [t["patient"], patient_name, t["code"], patient_code],
        [t["visit_date"], visit_date, t["visit_type"], visit_type_display],
    ]
    patient_table = Table(patient_data, colWidths=[90, 150, 70, 90])
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

    # Chief complaint
    if visit.chief_complaint:
        content.append(Paragraph(t["chief_complaint"], heading_style))
        content.append(Paragraph(visit.chief_complaint, content_style))

    # Medical history
    if visit.medical_history:
        content.append(Paragraph(t["medical_history"], heading_style))
        for line in visit.medical_history.split('\n'):
            if line.strip():
                content.append(Paragraph(line, content_style))

    # History of present illness
    if visit.history_of_present_illness:
        content.append(Paragraph(t["history_present_illness"], heading_style))
        for line in visit.history_of_present_illness.split('\n'):
            if line.strip():
                content.append(Paragraph(line, content_style))

    # Physical exam
    if visit.physical_exam:
        content.append(Paragraph(t["physical_exam"], heading_style))
        for line in visit.physical_exam.split('\n'):
            if line.strip():
                content.append(Paragraph(line, content_style))

    # Complementary exam
    if visit.complementary_exam:
        content.append(Paragraph(t["complementary_exam"], heading_style))
        for line in visit.complementary_exam.split('\n'):
            if line.strip():
                content.append(Paragraph(line, content_style))

    # Vitals section (if available)
    if latest_vitals:
        content.append(Paragraph(t["vitals"], heading_style))
        vitals_data = []
        if latest_vitals.temperature_c is not None:
            vitals_data.append([t["temperature"], f"{latest_vitals.temperature_c} °C"])
        if latest_vitals.bp_systolic is not None and latest_vitals.bp_diastolic is not None:
            vitals_data.append([t["blood_pressure"], f"{latest_vitals.bp_systolic}/{latest_vitals.bp_diastolic} mmHg"])
        if latest_vitals.heart_rate_bpm is not None:
            vitals_data.append([t["heart_rate"], f"{latest_vitals.heart_rate_bpm} bpm"])
        if latest_vitals.respiratory_rate_rpm is not None:
            vitals_data.append([t["respiratory_rate"], f"{latest_vitals.respiratory_rate_rpm} rpm"])
        if latest_vitals.oxygen_saturation_pct is not None:
            vitals_data.append([t["oxygen_saturation"], f"{latest_vitals.oxygen_saturation_pct}%"])
        if latest_vitals.weight_kg is not None:
            vitals_data.append([t["weight"], f"{latest_vitals.weight_kg} kg"])
        if latest_vitals.height_cm is not None:
            vitals_data.append([t["height"], f"{latest_vitals.height_cm} cm"])

        if vitals_data:
            vitals_table = Table(vitals_data, colWidths=[150, 100])
            vitals_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
            ]))
            content.append(vitals_table)

    # Assessment
    if visit.assessment:
        content.append(Paragraph(t["assessment"], heading_style))
        for line in visit.assessment.split('\n'):
            if line.strip():
                content.append(Paragraph(line, content_style))

    # Plan
    if visit.plan:
        content.append(Paragraph(t["plan"], heading_style))
        for line in visit.plan.split('\n'):
            if line.strip():
                content.append(Paragraph(line, content_style))

    # Treatment
    if visit.treatment:
        content.append(Paragraph(t["treatment"], heading_style))
        for line in visit.treatment.split('\n'):
            if line.strip():
                content.append(Paragraph(line, content_style))

    # Notes
    if visit.notes:
        content.append(Paragraph(t["notes"], heading_style))
        for line in visit.notes.split('\n'):
            if line.strip():
                content.append(Paragraph(line, content_style))

    # Prescriber section
    content.append(Spacer(1, 30))

    created_date = visit.visit_date.strftime("%d/%m/%Y") if visit.visit_date else "-"
    prescriber_data = [
        [t["prescriber"], prescriber_name],
    ]
    if license_number:
        prescriber_data.append([t["license"], license_number])
    prescriber_data.append([t["date"], created_date])
    if clinic_address:
        address_single_line = ", ".join(line.strip() for line in clinic_address.split('\n') if line.strip())
        prescriber_data.append([t["location"], address_single_line])

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
    response['Content-Disposition'] = f'attachment; filename="resume_visite_{visit.id}.pdf"'
    return response
