"""
Management command to seed sample medications and prescription templates.

Usage: python manage.py seed_prescriptions
"""

from django.core.management.base import BaseCommand
from prescriptions.models import Medication, PrescriptionTemplate, PrescriptionTemplateItem


SAMPLE_MEDICATIONS = [
    # Common antibiotics
    {"name": "Amoxicillin", "form": "capsule", "strength": "500mg"},
    {"name": "Amoxicillin", "form": "suspension", "strength": "250mg/5ml"},
    {"name": "Azithromycin", "form": "tablet", "strength": "500mg"},
    {"name": "Azithromycin", "form": "suspension", "strength": "200mg/5ml"},
    {"name": "Ciprofloxacin", "form": "tablet", "strength": "500mg"},
    {"name": "Metronidazole", "form": "tablet", "strength": "400mg"},
    {"name": "Doxycycline", "form": "capsule", "strength": "100mg"},
    {"name": "Cotrimoxazole", "form": "tablet", "strength": "480mg"},
    {"name": "Ceftriaxone", "form": "injection", "strength": "1g"},
    {"name": "Gentamicin", "form": "injection", "strength": "80mg/2ml"},

    # Pain relievers / NSAIDs
    {"name": "Paracetamol", "form": "tablet", "strength": "500mg"},
    {"name": "Paracetamol", "form": "syrup", "strength": "120mg/5ml"},
    {"name": "Ibuprofen", "form": "tablet", "strength": "400mg"},
    {"name": "Ibuprofen", "form": "suspension", "strength": "100mg/5ml"},
    {"name": "Diclofenac", "form": "tablet", "strength": "50mg"},
    {"name": "Diclofenac", "form": "injection", "strength": "75mg/3ml"},
    {"name": "Tramadol", "form": "capsule", "strength": "50mg"},

    # Antimalarials
    {"name": "Artemether-Lumefantrine", "form": "tablet", "strength": "20/120mg"},
    {"name": "Artesunate", "form": "injection", "strength": "60mg"},
    {"name": "Quinine", "form": "tablet", "strength": "300mg"},
    {"name": "Quinine", "form": "injection", "strength": "600mg/2ml"},

    # GI medications
    {"name": "Omeprazole", "form": "capsule", "strength": "20mg"},
    {"name": "Ranitidine", "form": "tablet", "strength": "150mg"},
    {"name": "Metoclopramide", "form": "tablet", "strength": "10mg"},
    {"name": "Loperamide", "form": "capsule", "strength": "2mg"},
    {"name": "ORS", "form": "sachet", "strength": "20.5g"},
    {"name": "Zinc Sulfate", "form": "tablet", "strength": "20mg"},

    # Antihistamines / Allergy
    {"name": "Cetirizine", "form": "tablet", "strength": "10mg"},
    {"name": "Loratadine", "form": "tablet", "strength": "10mg"},
    {"name": "Chlorpheniramine", "form": "tablet", "strength": "4mg"},
    {"name": "Promethazine", "form": "tablet", "strength": "25mg"},

    # Respiratory
    {"name": "Salbutamol", "form": "inhaler", "strength": "100mcg"},
    {"name": "Salbutamol", "form": "nebulizer solution", "strength": "5mg/ml"},
    {"name": "Prednisolone", "form": "tablet", "strength": "5mg"},
    {"name": "Dextromethorphan", "form": "syrup", "strength": "15mg/5ml"},

    # Cardiovascular
    {"name": "Amlodipine", "form": "tablet", "strength": "5mg"},
    {"name": "Lisinopril", "form": "tablet", "strength": "10mg"},
    {"name": "Hydrochlorothiazide", "form": "tablet", "strength": "25mg"},
    {"name": "Atenolol", "form": "tablet", "strength": "50mg"},
    {"name": "Aspirin", "form": "tablet", "strength": "75mg"},

    # Diabetes
    {"name": "Metformin", "form": "tablet", "strength": "500mg"},
    {"name": "Glibenclamide", "form": "tablet", "strength": "5mg"},
    {"name": "Insulin Regular", "form": "injection", "strength": "100IU/ml"},

    # Vitamins / Supplements
    {"name": "Vitamin B Complex", "form": "tablet", "strength": ""},
    {"name": "Vitamin C", "form": "tablet", "strength": "500mg"},
    {"name": "Folic Acid", "form": "tablet", "strength": "5mg"},
    {"name": "Ferrous Sulfate", "form": "tablet", "strength": "200mg"},
    {"name": "Multivitamin", "form": "tablet", "strength": ""},

    # Dermatological
    {"name": "Hydrocortisone", "form": "cream", "strength": "1%"},
    {"name": "Clotrimazole", "form": "cream", "strength": "1%"},
    {"name": "Miconazole", "form": "cream", "strength": "2%"},

    # Eye/Ear
    {"name": "Chloramphenicol", "form": "eye drops", "strength": "0.5%"},
    {"name": "Ciprofloxacin", "form": "eye drops", "strength": "0.3%"},
]


SAMPLE_TEMPLATES = [
    {
        "name": "Common Cold / URTI",
        "name_fr": "Rhume / IVRS",
        "description": "Upper respiratory tract infection - mild to moderate",
        "description_fr": "Infection des voies respiratoires supérieures - légère à modérée",
        "items": [
            {"medication": "Paracetamol 500mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "every 6 hours", "duration": "3 days", "instructions": "Take with food. Max 4 tablets per day."},
            {"medication": "Cetirizine 10mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "once daily", "duration": "5 days", "instructions": "Take at night."},
            {"medication": "Dextromethorphan 15mg/5ml (syrup)", "dosage": "10ml", "route": "oral", "frequency": "every 8 hours", "duration": "5 days", "instructions": "For dry cough only."},
        ]
    },
    {
        "name": "Bacterial Throat Infection",
        "name_fr": "Angine bactérienne",
        "description": "Pharyngitis/Tonsillitis with bacterial etiology",
        "description_fr": "Pharyngite/Amygdalite d'origine bactérienne",
        "items": [
            {"medication": "Amoxicillin 500mg (capsule)", "dosage": "1 capsule", "route": "oral", "frequency": "every 8 hours", "duration": "7 days", "instructions": "Complete the full course even if feeling better."},
            {"medication": "Paracetamol 500mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "every 6 hours", "duration": "3 days", "instructions": "For fever and pain. Max 4 tablets per day."},
        ]
    },
    {
        "name": "Uncomplicated Malaria",
        "name_fr": "Paludisme non compliqué",
        "description": "P. falciparum malaria - artemisinin-based combination therapy",
        "description_fr": "Paludisme à P. falciparum - thérapie combinée à base d'artémisinine",
        "items": [
            {"medication": "Artemether-Lumefantrine 20/120mg (tablet)", "dosage": "4 tablets", "route": "oral", "frequency": "twice daily", "duration": "3 days", "instructions": "Take with fatty food for better absorption."},
            {"medication": "Paracetamol 500mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "every 6 hours", "duration": "3 days", "instructions": "For fever. Take as needed."},
        ]
    },
    {
        "name": "Acute Gastroenteritis - Adult",
        "name_fr": "Gastro-entérite aiguë - Adulte",
        "description": "Diarrhea and vomiting in adults",
        "description_fr": "Diarrhée et vomissements chez l'adulte",
        "items": [
            {"medication": "ORS 20.5g (sachet)", "dosage": "1 sachet in 1L water", "route": "oral", "frequency": "as needed", "duration": "until recovered", "instructions": "Drink small sips frequently. Prepare fresh daily."},
            {"medication": "Metoclopramide 10mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "every 8 hours", "duration": "2 days", "instructions": "Take 30 min before meals for nausea."},
            {"medication": "Loperamide 2mg (capsule)", "dosage": "2 capsules initially, then 1 after each loose stool", "route": "oral", "frequency": "as needed", "duration": "max 2 days", "instructions": "Max 8 capsules per day. Do not use if bloody diarrhea."},
        ]
    },
    {
        "name": "Acute Gastroenteritis - Pediatric",
        "name_fr": "Gastro-entérite aiguë - Pédiatrique",
        "description": "Diarrhea in children (under 12)",
        "description_fr": "Diarrhée chez l'enfant (moins de 12 ans)",
        "items": [
            {"medication": "ORS 20.5g (sachet)", "dosage": "1 sachet in 1L water", "route": "oral", "frequency": "after each loose stool", "duration": "until recovered", "instructions": "Give 50-100ml after each stool for children under 2, 100-200ml for older children."},
            {"medication": "Zinc Sulfate 20mg (tablet)", "dosage": "1 tablet (dissolve in water)", "route": "oral", "frequency": "once daily", "duration": "10-14 days", "instructions": "Continue for 10-14 days even after diarrhea stops."},
        ]
    },
    {
        "name": "Urinary Tract Infection - Uncomplicated",
        "name_fr": "Infection urinaire - Non compliquée",
        "description": "Simple UTI in adults",
        "description_fr": "Infection urinaire simple chez l'adulte",
        "items": [
            {"medication": "Ciprofloxacin 500mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "twice daily", "duration": "3-5 days", "instructions": "Take with plenty of water. Avoid dairy products."},
            {"medication": "Paracetamol 500mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "every 6 hours as needed", "duration": "3 days", "instructions": "For pain relief."},
        ]
    },
    {
        "name": "Peptic Ulcer Disease",
        "name_fr": "Ulcère gastroduodénal",
        "description": "Gastric/duodenal ulcer or gastritis",
        "description_fr": "Ulcère gastrique/duodénal ou gastrite",
        "items": [
            {"medication": "Omeprazole 20mg (capsule)", "dosage": "1 capsule", "route": "oral", "frequency": "once daily", "duration": "4-8 weeks", "instructions": "Take 30 minutes before breakfast."},
            {"medication": "Amoxicillin 500mg (capsule)", "dosage": "1 capsule", "route": "oral", "frequency": "every 8 hours", "duration": "14 days", "instructions": "Part of H. pylori eradication if positive."},
            {"medication": "Metronidazole 400mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "every 8 hours", "duration": "14 days", "instructions": "Avoid alcohol during treatment."},
        ]
    },
    {
        "name": "Hypertension - Initial Treatment",
        "name_fr": "Hypertension - Traitement initial",
        "description": "First-line treatment for essential hypertension",
        "description_fr": "Traitement de première intention pour l'hypertension essentielle",
        "items": [
            {"medication": "Amlodipine 5mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "once daily", "duration": "30 days (ongoing)", "instructions": "Take at the same time each day. Regular BP monitoring."},
            {"medication": "Hydrochlorothiazide 25mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "once daily", "duration": "30 days (ongoing)", "instructions": "Take in the morning. Monitor potassium levels."},
        ]
    },
    {
        "name": "Type 2 Diabetes - Initial",
        "name_fr": "Diabète type 2 - Initial",
        "description": "First-line oral hypoglycemic",
        "description_fr": "Hypoglycémiant oral de première intention",
        "items": [
            {"medication": "Metformin 500mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "twice daily", "duration": "30 days (ongoing)", "instructions": "Take with meals to reduce GI side effects. May increase to 850mg after 2 weeks if tolerated."},
        ]
    },
    {
        "name": "Allergic Reaction - Mild",
        "name_fr": "Réaction allergique - Légère",
        "description": "Urticaria, allergic rhinitis, mild allergic reactions",
        "description_fr": "Urticaire, rhinite allergique, réactions allergiques légères",
        "items": [
            {"medication": "Loratadine 10mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "once daily", "duration": "7 days", "instructions": "Non-drowsy antihistamine."},
            {"medication": "Prednisolone 5mg (tablet)", "dosage": "6 tablets (30mg)", "route": "oral", "frequency": "once daily", "duration": "3 days", "instructions": "Take in the morning with food. Short course only."},
        ]
    },
    {
        "name": "Skin Infection - Fungal",
        "name_fr": "Infection cutanée - Fongique",
        "description": "Tinea corporis, tinea pedis, candidiasis",
        "description_fr": "Teigne corporelle, pied d'athlète, candidose",
        "items": [
            {"medication": "Clotrimazole 1% (cream)", "dosage": "Apply thin layer", "route": "topical", "frequency": "twice daily", "duration": "2-4 weeks", "instructions": "Apply to affected area and surrounding skin. Continue for 1 week after symptoms resolve."},
        ]
    },
    {
        "name": "Asthma - Acute Exacerbation",
        "name_fr": "Asthme - Exacerbation aiguë",
        "description": "Mild to moderate asthma attack",
        "description_fr": "Crise d'asthme légère à modérée",
        "items": [
            {"medication": "Salbutamol 100mcg (inhaler)", "dosage": "2 puffs", "route": "inhalation", "frequency": "every 4-6 hours as needed", "duration": "until stable", "instructions": "Shake well before use. Rinse mouth after."},
            {"medication": "Prednisolone 5mg (tablet)", "dosage": "8 tablets (40mg)", "route": "oral", "frequency": "once daily", "duration": "5 days", "instructions": "Take in the morning with food."},
        ]
    },
    {
        "name": "Eye Infection - Bacterial Conjunctivitis",
        "name_fr": "Infection oculaire - Conjonctivite bactérienne",
        "description": "Pink eye / bacterial conjunctivitis",
        "description_fr": "Conjonctivite bactérienne / œil rose",
        "items": [
            {"medication": "Chloramphenicol 0.5% (eye drops)", "dosage": "1-2 drops", "route": "topical - eye", "frequency": "every 4 hours", "duration": "7 days", "instructions": "Apply to affected eye(s). Wash hands before and after."},
        ]
    },
    {
        "name": "Anemia - Iron Deficiency",
        "name_fr": "Anémie - Carence en fer",
        "description": "Iron supplementation for iron deficiency anemia",
        "description_fr": "Supplémentation en fer pour l'anémie ferriprive",
        "items": [
            {"medication": "Ferrous Sulfate 200mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "twice daily", "duration": "3 months", "instructions": "Take between meals for better absorption. Take with vitamin C."},
            {"medication": "Folic Acid 5mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "once daily", "duration": "3 months", "instructions": "Take with ferrous sulfate."},
            {"medication": "Vitamin C 500mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "twice daily", "duration": "3 months", "instructions": "Enhances iron absorption."},
        ]
    },
    {
        "name": "Pain Management - Musculoskeletal",
        "name_fr": "Gestion de la douleur - Musculosquelettique",
        "description": "Back pain, joint pain, muscle strain",
        "description_fr": "Mal de dos, douleur articulaire, tension musculaire",
        "items": [
            {"medication": "Diclofenac 50mg (tablet)", "dosage": "1 tablet", "route": "oral", "frequency": "every 8 hours", "duration": "5-7 days", "instructions": "Take with food. Not for long-term use."},
            {"medication": "Omeprazole 20mg (capsule)", "dosage": "1 capsule", "route": "oral", "frequency": "once daily", "duration": "5-7 days", "instructions": "For stomach protection while on NSAIDs."},
        ]
    },
]


class Command(BaseCommand):
    help = "Seed sample medications and prescription templates (bilingual EN/FR)"

    def handle(self, *args, **options):
        self.stdout.write("Seeding medications...")

        medications_created = 0
        medication_map = {}

        for med_data in SAMPLE_MEDICATIONS:
            med, created = Medication.objects.get_or_create(
                name=med_data["name"],
                form=med_data["form"],
                strength=med_data["strength"],
                defaults={"is_active": True}
            )
            if created:
                medications_created += 1
            # Store for template item lookup
            key = f"{med_data['name']} {med_data['strength']} ({med_data['form']})".strip()
            medication_map[key] = med

        self.stdout.write(self.style.SUCCESS(f"  Created {medications_created} new medications"))

        self.stdout.write("Seeding prescription templates (bilingual)...")

        templates_created = 0
        templates_updated = 0
        items_created = 0

        for tpl_data in SAMPLE_TEMPLATES:
            tpl, created = PrescriptionTemplate.objects.get_or_create(
                name=tpl_data["name"],
                defaults={
                    "name_fr": tpl_data.get("name_fr", ""),
                    "description": tpl_data.get("description", ""),
                    "description_fr": tpl_data.get("description_fr", ""),
                    "is_active": True
                }
            )

            if created:
                templates_created += 1

                # Add template items
                for item_data in tpl_data.get("items", []):
                    med_search = item_data["medication"]
                    # Try to find medication
                    med = medication_map.get(med_search)
                    if not med:
                        # Try partial match
                        for key, m in medication_map.items():
                            if med_search.lower() in key.lower() or key.lower() in med_search.lower():
                                med = m
                                break

                    if med:
                        PrescriptionTemplateItem.objects.create(
                            template=tpl,
                            medication=med,
                            dosage=item_data.get("dosage", ""),
                            route=item_data.get("route", ""),
                            frequency=item_data.get("frequency", ""),
                            duration=item_data.get("duration", ""),
                            instructions=item_data.get("instructions", ""),
                        )
                        items_created += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"  Medication not found: {med_search}")
                        )
            else:
                # Update existing template with French translations
                updated = False
                if not tpl.name_fr and tpl_data.get("name_fr"):
                    tpl.name_fr = tpl_data["name_fr"]
                    updated = True
                if not tpl.description_fr and tpl_data.get("description_fr"):
                    tpl.description_fr = tpl_data["description_fr"]
                    updated = True
                if updated:
                    tpl.save()
                    templates_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"  Created {templates_created} new templates with {items_created} items"
        ))
        if templates_updated > 0:
            self.stdout.write(self.style.SUCCESS(
                f"  Updated {templates_updated} existing templates with French translations"
            ))

        self.stdout.write(self.style.SUCCESS("Done!"))
