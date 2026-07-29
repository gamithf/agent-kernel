from agentkernel.knowledgebase.chroma import ChromaManager
from agentkernel.knowledgebase.knowledgebuilder import KnowledgeBuilder

DRUG_INTERACTIONS = [
    {
        "text": "ACE inhibitors (enalapril, benazepril) + potassium-sparing diuretics (spironolactone): risk of life-threatening hyperkalemia in dogs. Monitor serum potassium closely if concurrent use is necessary.",
        "metadata": {"severity": "high", "category": "cardiovascular", "species": "canine"},
    },
    {
        "text": "NSAIDs (carprofen, meloxicam, firocoxib) + corticosteroids (prednisone, prednisolone, dexamethasone): significantly increased risk of GI ulceration, perforation, and hemorrhage in dogs and cats. AVOID concurrent use.",
        "metadata": {"severity": "critical", "category": "gastrointestinal", "species": "canine+feline"},
    },
    {
        "text": "Fluoroquinolones (enrofloxacin, marbofloxacin) + NSAIDs: increased risk of CNS stimulation and seizures in dogs, especially in patients with a history of epilepsy.",
        "metadata": {"severity": "moderate", "category": "neurological", "species": "canine"},
    },
    {
        "text": "Metronidazole + warfarin: potentiates anticoagulant effect in dogs. Monitor PT/PTT if concurrent use is necessary and adjust warfarin dose accordingly.",
        "metadata": {"severity": "moderate", "category": "hematological", "species": "canine"},
    },
    {
        "text": "Ketoconazole + cisapride: CONTRAINDICATED — risk of fatal cardiac arrhythmias (QT prolongation) in dogs and cats.",
        "metadata": {"severity": "critical", "category": "cardiovascular", "species": "canine+feline"},
    },
    {
        "text": "Oclacitinib (Apoquel) + corticosteroids: increased risk of immunosuppression and secondary infections in dogs. Avoid long-term concurrent use unless specifically indicated.",
        "metadata": {"severity": "moderate", "category": "immunological", "species": "canine"},
    },
    {
        "text": "Oclacitinib (Apoquel) + cyclosporine (Atopica): additive immunosuppressive effects in dogs. Monitor for signs of infection if used together.",
        "metadata": {"severity": "moderate", "category": "immunological", "species": "canine"},
    },
    {
        "text": "Oclacitinib (Apoquel) + ketoconazole: ketoconazole increases Apoquel exposure by inhibiting CYP450 metabolism. Reduce Apoquel dose to 0.4 mg/kg once daily if used together.",
        "metadata": {"severity": "moderate", "category": "pharmacokinetic", "species": "canine"},
    },
    {
        "text": "NSAIDs (carprofen, meloxicam) + ACE inhibitors (enalapril): reduced renal function and increased risk of acute kidney injury in dogs, especially in dehydrated or geriatric patients.",
        "metadata": {"severity": "high", "category": "renal", "species": "canine"},
    },
    {
        "text": "Amoxicillin-clavulanic acid (Clavamox) + methotrexate: increased methotrexate toxicity in dogs due to reduced renal clearance. Monitor for bone marrow suppression.",
        "metadata": {"severity": "moderate", "category": "hematological", "species": "canine"},
    },
    {
        "text": "Phenobarbital + primidone: excessive sedation and hepatotoxicity in dogs. Avoid concurrent use; if necessary, monitor liver enzymes closely.",
        "metadata": {"severity": "high", "category": "neurological", "species": "canine"},
    },
    {
        "text": "Doxycycline + phenobarbital: reduced doxycycline efficacy due to increased hepatic metabolism in dogs. Consider increasing doxycycline dose or alternative antibiotic.",
        "metadata": {"severity": "moderate", "category": "pharmacokinetic", "species": "canine"},
    },
    {
        "text": "Furosemide (Lasix) + ACE inhibitors (enalapril): profound hypotension and risk of acute kidney injury in dogs with congestive heart failure. Monitor blood pressure and renal parameters.",
        "metadata": {"severity": "high", "category": "cardiovascular", "species": "canine"},
    },
    {
        "text": "Methimazole (Felimazole) + phenobarbital: reduced methimazole efficacy in hyperthyroid cats. Monitor T4 levels closely and adjust methimazole dose if needed.",
        "metadata": {"severity": "moderate", "category": "endocrine", "species": "feline"},
    },
    {
        "text": "Cisapride + erythromycin/clarithromycin: CONTRAINDICATED — risk of fatal cardiac arrhythmias (QT prolongation) in cats and dogs.",
        "metadata": {"severity": "critical", "category": "cardiovascular", "species": "canine+feline"},
    },
    {
        "text": "Ketoconazole + cyclosporine (Atopica): ketoconazole significantly increases cyclosporine blood levels in dogs. Reduce cyclosporine dose by 50% if used concurrently and monitor trough levels.",
        "metadata": {"severity": "high", "category": "pharmacokinetic", "species": "canine"},
    },
    {
        "text": "Phenylpropanolamine (PPA, Proin) + NSAIDs: increased risk of hypertension in dogs. Monitor blood pressure in geriatric patients on concurrent therapy.",
        "metadata": {"severity": "moderate", "category": "cardiovascular", "species": "canine"},
    },
    {
        "text": "Fluoxetine (Prozac, Reconcile) + tramadol: increased risk of serotonin syndrome in dogs. Signs include agitation, tremors, hyperthermia. Avoid concurrent use or monitor closely.",
        "metadata": {"severity": "high", "category": "neurological", "species": "canine"},
    },
    {
        "text": "Clomipramine (Clomicalm) + fluoxetine (Reconcile): CONTRAINDICATED — risk of serotonin syndrome. Allow a 5-week washout period between these medications in dogs.",
        "metadata": {"severity": "critical", "category": "neurological", "species": "canine"},
    },
    {
        "text": "Enrofloxacin (Baytril) + theophylline: increased theophylline levels and risk of toxicity in dogs. Monitor for signs of theophylline toxicity (vomiting, tachycardia, seizures).",
        "metadata": {"severity": "moderate", "category": "pharmacokinetic", "species": "canine"},
    },
    {
        "text": "Dexmedetomidine + ACE inhibitors: bradycardia and hypotension risk increased in dogs undergoing sedation. Use with caution and have emergency reversal agents (atipamezole) available.",
        "metadata": {"severity": "moderate", "category": "anesthesia", "species": "canine"},
    },
    {
        "text": "Maropitant (Cerenia) + NSAIDs: no significant interaction documented in dogs. Considered safe for concurrent use when treating motion sickness or vomiting in patients on NSAID therapy.",
        "metadata": {"severity": "none", "category": "gastrointestinal", "species": "canine"},
    },
    {
        "text": "Gabapentin + NSAIDs: no significant pharmacokinetic interaction in dogs. Safe to use concurrently for multimodal pain management.",
        "metadata": {"severity": "none", "category": "pain_management", "species": "canine"},
    },
    {
        "text": "Amantadine + NSAIDs: safe combination for chronic pain management in dogs. Amantadine provides NMDA antagonist effects complementary to NSAID analgesia.",
        "metadata": {"severity": "none", "category": "pain_management", "species": "canine"},
    },
    {
        "text": "Tramadol + NSAIDs: generally safe for multimodal analgesia in dogs. Monitor for additive GI effects when used with COX-2 selective NSAIDs.",
        "metadata": {"severity": "low", "category": "pain_management", "species": "canine"},
    },
]


def seed_drug_interactions(chroma_manager: ChromaManager) -> None:
    chroma_manager.write(DRUG_INTERACTIONS)


def create_vetra_knowledge_base() -> tuple[ChromaManager, KnowledgeBuilder]:
    chroma = ChromaManager(
        persist_path="./vetra_chroma",
        name="VetDrugDB",
        collection_name="vet_drug_interactions",
        description="Veterinary drug interaction knowledge base with severity ratings for canine, feline, and equine medications.",
    ).add_schema(
        {
            "description": "Semantic vector store of veterinary drug interactions. Contains known interactions, contraindications, and severity levels for common veterinary medications across species.",
            "store_payload": {
                "text": "string - drug interaction description with severity, affected species, and clinical recommendation",
                "source": "string - origin label (default: 'veterinary_formulary')",
            },
            "read_payload": {
                "query": "string - natural language query about drug interactions, e.g. 'Does Apoquel interact with anything?'",
                "limit": "int - max results to return (default: 5)",
            },
        }
    )

    seed_drug_interactions(chroma)

    kb = KnowledgeBuilder([chroma])

    return chroma, kb
