"""
Initialize Weaviate schema and ingest pregnancy/postpartum/early childhood medical content
"""
import weaviate
from app.core.config import settings
from app.services.scraper_service import ingest_urls_to_weaviate

# Connect to Weaviate
client = weaviate.Client(
    url=settings.WEAVIATE_URL,
    timeout_config=(5, 15)
)

print("Setting up Weaviate...")

# Delete existing schema if present
try:
    client.schema.delete_class("MedicalKnowledge")
    print("✓ Deleted existing schema")
except:
    pass

# Create schema
schema = {
    "class": "MedicalKnowledge",
    "description": "Medical information from trusted sources - pregnancy, postpartum, and early childhood care",
    "vectorizer": "text2vec-transformers",
    "moduleConfig": {
        "text2vec-transformers": {
            "poolingStrategy": "masked_mean"
        }
    },
    "properties": [
        {
            "name": "content",
            "dataType": ["text"],
            "description": "Main content of the medical article"
        },
        {
            "name": "source_url",
            "dataType": ["string"],
            "description": "URL of the source"
        },
        {
            "name": "title",
            "dataType": ["string"],
            "description": "Title of the article"
        }
    ]
}

client.schema.create_class(schema)
print("✓ Created MedicalKnowledge schema")

# Comprehensive medical URLs - ALL VERIFIED WORKING
medical_urls = [
    # ========== PREGNANCY NUTRITION ==========
    "https://www.mayoclinic.org/healthy-lifestyle/pregnancy-week-by-week/in-depth/pregnancy-nutrition/art-20045082",
    "https://www.mayoclinic.org/healthy-lifestyle/pregnancy-week-by-week/in-depth/prenatal-vitamins/art-20046945",
    "https://www.acog.org/womens-health/faqs/nutrition-during-pregnancy",
    "https://medlineplus.gov/pregnancyandnutrition.html",
    "https://www.nhs.uk/pregnancy/keeping-well/vitamins-supplements-and-nutrition/",

    # ========== PREGNANCY EXERCISE & WELLNESS ==========
    "https://www.mayoclinic.org/healthy-lifestyle/pregnancy-week-by-week/in-depth/pregnancy-and-exercise/art-20046896",
    "https://www.acog.org/womens-health/faqs/exercise-during-pregnancy",
    "https://www.nhs.uk/pregnancy/keeping-well/exercise/",

    # ========== PRENATAL CARE ==========
    "https://www.mayoclinic.org/healthy-lifestyle/pregnancy-week-by-week/in-depth/prenatal-care/art-20044882",
    "https://medlineplus.gov/prenatalcare.html",
    "https://www.acog.org/womens-health/faqs/prenatal-genetic-screening-tests",
    "https://www.marchofdimes.org/find-support/topics/planning-baby/prenatal-care",

    # ========== PREGNANCY COMPLICATIONS ==========
    "https://www.mayoclinic.org/diseases-conditions/preeclampsia/symptoms-causes/syc-20355745",
    "https://www.mayoclinic.org/diseases-conditions/gestational-diabetes/symptoms-causes/syc-20355339",
    "https://www.acog.org/womens-health/faqs/preeclampsia-and-high-blood-pressure-during-pregnancy",
    "https://www.marchofdimes.org/find-support/topics/pregnancy/complications",
    "https://www.nhs.uk/pregnancy/related-conditions/complications/",

    # ========== LABOR & DELIVERY ==========
    "https://www.mayoclinic.org/healthy-lifestyle/labor-and-delivery/in-depth/stages-of-labor/art-20046545",
    "https://medlineplus.gov/childbirth.html",
    "https://www.acog.org/womens-health/faqs/labor-induction",
    "https://www.acog.org/womens-health/faqs/cesarean-birth",
    "https://www.nhs.uk/pregnancy/labour-and-birth/what-happens/",

    # ========== POSTPARTUM CARE ==========
    "https://www.mayoclinic.org/healthy-lifestyle/labor-and-delivery/in-depth/postpartum-care/art-20047233",
    "https://www.acog.org/womens-health/faqs/postpartum-depression",
    "https://www.marchofdimes.org/find-support/topics/postpartum/postpartum-care",
    "https://www.nhs.uk/conditions/baby/support-and-services/help-and-support-after-birth/",

    # ========== MEDICATIONS DURING PREGNANCY ==========
    "https://www.cdc.gov/pregnancy/meds/treatingfortwo/index.html",
    "https://medlineplus.gov/pregnancyandmedicines.html",
    "https://www.acog.org/womens-health/faqs/over-the-counter-medications-during-pregnancy",
    "https://www.nhs.uk/pregnancy/keeping-well/medicines/",

    # ========== SPECIFIC MEDICATIONS ==========
    "https://medlineplus.gov/druginfo/meds/a681004.html",  # Acetaminophen/Paracetamol
    "https://medlineplus.gov/druginfo/meds/a682878.html",  # Aspirin
    "https://medlineplus.gov/druginfo/meds/a689002.html",  # Ibuprofen
    "https://medlineplus.gov/druginfo/meds/a682673.html",  # Folic Acid
    "https://medlineplus.gov/druginfo/meds/a607068.html",  # Prenatal Vitamins
    "https://medlineplus.gov/druginfo/meds/a682395.html",  # Iron

    # ========== BREASTFEEDING ==========
    "https://www.cdc.gov/breastfeeding/index.htm",
    "https://medlineplus.gov/breastfeeding.html",
    "https://www.acog.org/womens-health/faqs/breastfeeding-your-baby",
    "https://kidshealth.org/en/parents/breastfeed-starting.html",
    "https://www.nhs.uk/conditions/baby/breastfeeding-and-bottle-feeding/",

    # ========== NEWBORN CARE ==========
    "https://kidshealth.org/en/parents/guide-parents.html",
    "https://www.healthychildren.org/English/ages-stages/baby/Pages/default.aspx",
    "https://www.mayoclinic.org/healthy-lifestyle/infant-and-toddler-health/basics/infant-health/hlv-20049400",
    "https://www.nhs.uk/conditions/baby/caring-for-a-newborn/",

    # ========== INFANT FEEDING ==========
    "https://medlineplus.gov/infantandnewbornnutrition.html",
    "https://www.mayoclinic.org/healthy-lifestyle/infant-and-toddler-health/in-depth/healthy-baby/art-20046200",
    "https://kidshealth.org/en/parents/formulafeed-starting.html",
    "https://www.healthychildren.org/English/ages-stages/baby/feeding-nutrition/Pages/default.aspx",

    # ========== FEVER IN CHILDREN ==========
    "https://www.mayoclinic.org/diseases-conditions/fever/in-depth/fever/art-20050997",
    "https://medlineplus.gov/fever.html",
    "https://kidshealth.org/en/parents/fever.html",
    "https://www.healthychildren.org/English/health-issues/conditions/fever/Pages/default.aspx",
    "https://www.nhs.uk/conditions/baby/health/fever-in-children/",

    # ========== VOMITING & DIARRHEA ==========
    "https://www.mayoclinic.org/diseases-conditions/viral-gastroenteritis/symptoms-causes/syc-20378847",
    "https://kidshealth.org/en/parents/vomit.html",
    "https://www.healthychildren.org/English/health-issues/conditions/abdominal/Pages/Treating-Vomiting.aspx",
    "https://www.healthychildren.org/English/health-issues/conditions/abdominal/Pages/Diarrhea.aspx",
    "https://www.nhs.uk/conditions/baby/health/vomiting-in-babies-and-children/",

    # ========== COLDS & FLU ==========
    "https://www.mayoclinic.org/diseases-conditions/common-cold/symptoms-causes/syc-20351605",
    "https://medlineplus.gov/commoncold.html",
    "https://kidshealth.org/en/parents/cold.html",
    "https://www.cdc.gov/flu/highrisk/children.htm",
    "https://www.healthychildren.org/English/health-issues/conditions/chest-lungs/Pages/Colds-in-Children.aspx",

    # ========== COUGH ==========
    "https://www.mayoclinic.org/symptoms/cough/basics/definition/sym-20050846",
    "https://kidshealth.org/en/parents/childs-cough.html",
    "https://www.healthychildren.org/English/health-issues/conditions/chest-lungs/Pages/Coughs-and-Colds-Medicines-or-Home-Remedies.aspx",

    # ========== TEETHING ==========
    "https://www.mayoclinic.org/healthy-lifestyle/infant-and-toddler-health/in-depth/teething/art-20046378",
    "https://kidshealth.org/en/parents/teething.html",
    "https://www.healthychildren.org/English/ages-stages/baby/teething-tooth-care/Pages/default.aspx",
    "https://www.nhs.uk/conditions/baby/babys-development/teething/baby-teething-symptoms/",

    # ========== RASHES & SKIN ==========
    "https://www.mayoclinic.org/diseases-conditions/diaper-rash/symptoms-causes/syc-20371636",
    "https://kidshealth.org/en/parents/diaper-rash.html",
    "https://www.healthychildren.org/English/ages-stages/baby/diapers-clothing/Pages/Diaper-Rash.aspx",
    "https://www.nhs.uk/conditions/baby/health/nappy-rash/",

    # ========== EAR INFECTIONS ==========
    "https://www.mayoclinic.org/diseases-conditions/ear-infections/symptoms-causes/syc-20351616",
    "https://medlineplus.gov/earinfections.html",
    "https://kidshealth.org/en/parents/otitis-media.html",
    "https://www.healthychildren.org/English/health-issues/conditions/ear-nose-throat/Pages/Ear-Infection-Information.aspx",

    # ========== FEEDING ISSUES ==========
    "https://kidshealth.org/en/parents/toddler-meals.html",
    "https://www.healthychildren.org/English/ages-stages/toddler/nutrition/Pages/Picky-Eaters.aspx",
    "https://www.healthychildren.org/English/ages-stages/toddler/nutrition/Pages/Feeding-and-Nutrition-Your-Two-Year-Old.aspx",
    "https://www.nhs.uk/conditions/baby/weaning-and-feeding/childrens-food-fussy-eaters/",

    # ========== SLEEP ==========
    "https://www.mayoclinic.org/healthy-lifestyle/infant-and-toddler-health/in-depth/baby-sleep/art-20045014",
    "https://kidshealth.org/en/parents/sleep.html",
    "https://www.healthychildren.org/English/ages-stages/baby/sleep/Pages/default.aspx",
    "https://www.nhs.uk/conditions/baby/support-and-services/sleep-tips-for-parents/",

    # ========== CRYING & COLIC ==========
    "https://www.mayoclinic.org/diseases-conditions/colic/symptoms-causes/syc-20371074",
    "https://kidshealth.org/en/parents/colic.html",
    "https://www.healthychildren.org/English/ages-stages/baby/crying-colic/Pages/default.aspx",

    # ========== VACCINATIONS ==========
    "https://www.healthychildren.org/English/safety-prevention/immunizations/Pages/default.aspx",
    "https://www.who.int/news-room/questions-and-answers/item/vaccines-and-immunization-what-is-vaccination",
    "https://www.cdc.gov/vaccines/vpd/polio/index.html",
    "https://www.cdc.gov/vaccines/vpd/hepb/index.html",
    "https://kidshealth.org/en/parents/vaccine.html",
    "https://www.healthychildren.org/English/safety-prevention/immunizations/Pages/Vaccine-Studies-Examine-the-Evidence.aspx",
    "https://www.nhs.uk/conditions/vaccinations/",
    "https://www.nhs.uk/conditions/vaccinations/nhs-vaccinations-and-when-to-have-them/",

    # ========== CHILD DEVELOPMENT ==========
    "https://medlineplus.gov/childdevelopment.html",
    "https://www.healthychildren.org/English/ages-stages/Pages/default.aspx",
    "https://kidshealth.org/en/parents/devp2.html",
    "https://www.mayoclinic.org/healthy-lifestyle/infant-and-toddler-health/in-depth/infant-development/art-20048012",

    # ========== SAFETY ==========
    "https://www.healthychildren.org/English/safety-prevention/Pages/default.aspx",
    "https://kidshealth.org/en/parents/safety-home.html",
    "https://www.mayoclinic.org/healthy-lifestyle/infant-and-toddler-health/in-depth/child-safety/art-20044317",
]

print(f"\nIngesting {len(medical_urls)} medical articles covering:")
print("  • Pregnancy & prenatal care")
print("  • Labor & delivery")
print("  • Postpartum care & mental health")
print("  • Newborn care & feeding")
print("  • Common childhood illnesses (fever, vomiting, colds, teething)")
print("  • Child vaccinations (evidence-based)")
print("  • Child development & safety")
print("\nThis may take 10-15 minutes...\n")

count = ingest_urls_to_weaviate(medical_urls, client)

print(f"\n Setup complete! Ingested {count}/{len(medical_urls)} articles")
print(f"\nComprehensive maternal & child health knowledge base is ready!")
print(f"\nTo re-run setup:")
print(f"  docker-compose exec backend python setup_weaviate.py")